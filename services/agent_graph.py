from __future__ import annotations

import json
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from core.config import Config
from core.observability import traceable
from utils.rag_engine import RAGEngine

try:
    from langchain_community.tools.tavily_search import TavilySearchResults
except ImportError:  # pragma: no cover
    TavilySearchResults = None

try:
    from langgraph.graph import END, START, StateGraph
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode
except ImportError:  # pragma: no cover
    END = None
    START = None
    StateGraph = None
    add_messages = None
    ToolNode = None


AGENT_SYSTEM_PROMPT = (
    "你是一个严谨的 RAG 智能体，必须通过工具获取事实后再作答。\n"
    "规则：\n"
    "1）用户问题明显依赖上传文档/内部资料（政策条款、手册、项目说明等）时，先调用 local_rag_retriever。\n"
    "2）下列情况禁止只凭常识直接回答，必须先调用 tavily_web_search（可用中文查询串）："
    "天气与气温、新闻时事、股价汇率、赛事比分、法律/政策最新修订、任意“今天/最新/当前/实时”类信息。\n"
    "3）可先 local_rag_retriever，若结果为空或与“今天/最新”矛盾，再 tavily_web_search。\n"
    "4）拿到工具返回的 JSON 后，用其中内容组织最终回答；若工具报错，据实说明错误原因，不要编造实时数据。\n"
    "5）回答中尽量附带来源链接或文档名。"
)


class AgentState(TypedDict):
    # 病历本：所有节点都只读写这一个字段，避免信息在流转中丢失。
    messages: Annotated[list[AnyMessage], add_messages]


def _message_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                value = item.get("text")
                if isinstance(value, str):
                    texts.append(value)
        return "\n".join(texts).strip()
    return str(content)


def _build_local_retriever_tool(rag_engine: RAGEngine):
    @tool("local_rag_retriever")
    @traceable(
        name="tool.local_rag_retriever",
        run_type="tool",
        tags=["agent", "tool", "rag", "internal_retrieval"],
    )
    def local_rag_retriever(query: str) -> str:
        """查询本地知识库（内部档案室），返回答案与来源。"""
        result = rag_engine.query_with_sources(query)
        payload = {
            "tool": "local_rag_retriever",
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
        }
        return json.dumps(payload, ensure_ascii=False)

    return local_rag_retriever


def _build_tavily_tool():
    @tool("tavily_web_search")
    @traceable(
        name="tool.tavily_web_search",
        run_type="tool",
        tags=["agent", "tool", "web_search", "tavily"],
    )
    def tavily_web_search(query: str) -> str:
        """执行 Tavily 联网检索（外部情报局），返回摘要片段和来源链接。"""
        if not Config.TAVILY_API_KEY:
            return json.dumps(
                {
                    "tool": "tavily_web_search",
                    "error": "缺少 TAVILY_API_KEY",
                    "sources": [],
                },
                ensure_ascii=False,
            )
        if TavilySearchResults is None:
            return json.dumps(
                {
                    "tool": "tavily_web_search",
                    "error": "缺少 langchain_community Tavily 依赖",
                    "sources": [],
                },
                ensure_ascii=False,
            )

        # LangChain 在 Tavily 请求失败时会把异常 repr 成 str 返回（不会抛到外层），
        # 若误把 str 当 list 遍历会得到空结果，模型会误判为“联网不可用”。
        search = TavilySearchResults(
            max_results=5,
            tavily_api_key=Config.TAVILY_API_KEY.strip(),
            search_depth="basic",
        )
        try:
            raw_results = search.invoke({"query": query})
        except Exception as exc:  # pragma: no cover
            return json.dumps(
                {
                    "tool": "tavily_web_search",
                    "error": f"Tavily 调用异常: {exc!s}",
                    "sources": [],
                },
                ensure_ascii=False,
            )

        if isinstance(raw_results, str):
            return json.dumps(
                {
                    "tool": "tavily_web_search",
                    "error": raw_results,
                    "hint": "多为 Key 无效、网络无法访问 api.tavily.com，或账户额度/权限问题。请检查 TAVILY_API_KEY 与容器/本机出境网络。",
                    "sources": [],
                },
                ensure_ascii=False,
            )

        normalized: list[dict[str, str]] = []
        sources: list[str] = []
        for item in raw_results or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            normalized.append(
                {
                    "title": str(item.get("title", "Untitled")),
                    "content": str(item.get("content", "")),
                    "url": url,
                }
            )
            if url:
                sources.append(url)

        if not normalized:
            return json.dumps(
                {
                    "tool": "tavily_web_search",
                    "error": "Tavily 未返回任何结果（results 为空）。",
                    "hint": "若刚配置 Key，请重启 API；在中国大陆环境需确认本机/容器能访问 https://api.tavily.com。",
                    "sources": [],
                },
                ensure_ascii=False,
            )

        payload = {
            "tool": "tavily_web_search",
            "results": normalized,
            "sources": sorted(set(sources)),
        }
        return json.dumps(payload, ensure_ascii=False)

    return tavily_web_search


@traceable(name="graph.should_continue", run_type="chain", tags=["agent", "routing"])
def _should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"


def _build_agent_node(llm_with_tools):
    @traceable(name="graph.agent_node", run_type="chain", tags=["agent", "llm_decision"])
    async def agent_node(state: AgentState) -> AgentState:
        current_messages = state["messages"]
        model_input = [SystemMessage(content=AGENT_SYSTEM_PROMPT), *current_messages]
        response = await llm_with_tools.ainvoke(
            model_input,
            config={
                "tags": ["agent", "llm", "decision"],
                "metadata": {"component": "agent_graph", "node": "agent"},
            },
        )
        return {"messages": [response]}

    return agent_node


def _extract_sources_from_tool_messages(messages: list[AnyMessage]) -> list[str]:
    sources: set[str] = set()
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        content = _message_to_text(msg.content)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        raw_sources = payload.get("sources", [])
        if isinstance(raw_sources, list):
            for item in raw_sources:
                if isinstance(item, str) and item.strip():
                    sources.add(item.strip())
    return sorted(sources)


def extract_graph_result(graph_state: dict[str, Any]) -> tuple[str, list[str]]:
    messages = graph_state.get("messages", [])
    answer = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            text = _message_to_text(msg.content).strip()
            if text:
                answer = text
                break
    sources = _extract_sources_from_tool_messages(messages)
    return answer, sources


def build_agent_graph(rag_engine: RAGEngine):
    """构建 START -> agent -> tools -> agent 的闭环图。"""
    if StateGraph is None or ToolNode is None:
        return None

    tools = [_build_local_retriever_tool(rag_engine), _build_tavily_tool()]
    llm_with_tools = rag_engine.llm_for_tools.bind_tools(tools, parallel_tool_calls=False)

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", _build_agent_node(llm_with_tools))
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        _should_continue,
        {"tools": "tools", "end": END},
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()
