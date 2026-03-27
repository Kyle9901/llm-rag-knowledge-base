from __future__ import annotations

from typing import Any, TypedDict

from config import Config
from utils.rag_engine import RAGEngine

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover
    END = None
    StateGraph = None


class AgentState(TypedDict):
    query: str
    history: str
    intent: str
    rag_result: dict[str, Any] | None
    web_result: dict[str, Any] | None
    answer: str
    sources: list[str]


def _route_intent(state: AgentState) -> AgentState:
    query = state["query"].lower()
    web_keywords = (
        "最新",
        "今天",
        "新闻",
        "时事",
        "实时",
        "price",
        "stock",
        "weather",
        "汇率",
        "走势",
        "hot",
        "breaking",
    )
    intent = "web_search" if any(key in query for key in web_keywords) else "local_rag"
    state["intent"] = intent
    return state


def _compose_rag_query(state: AgentState) -> str:
    history = (state.get("history") or "").strip()
    if not history:
        return state["query"]
    return (
        "以下是对话历史，请结合历史上下文回答用户最新问题。\n\n"
        f"{history}\n\n"
        f"最新问题：{state['query']}"
    )


def _rag_node(state: AgentState, rag_engine: RAGEngine) -> AgentState:
    rag_result = rag_engine.query_with_sources(_compose_rag_query(state))
    state["rag_result"] = rag_result
    return state


def _search_with_tavily(query: str) -> list[dict[str, str]] | None:
    if not Config.TAVILY_API_KEY:
        return None

    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
    except ImportError:
        return None

    tool = TavilySearchResults(max_results=5, tavily_api_key=Config.TAVILY_API_KEY)
    try:
        results = tool.invoke({"query": query})
    except Exception:  # pragma: no cover
        return None

    normalized = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "title": str(item.get("title", "Untitled")),
                "content": str(item.get("content", "")),
                "url": str(item.get("url", "")),
            }
        )
    return normalized or None


def _search_with_duckduckgo(query: str) -> list[dict[str, str]] | None:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return None

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception:  # pragma: no cover
        return None

    normalized = []
    for item in results:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "title": str(item.get("title", "Untitled")),
                "content": str(item.get("body", "")),
                "url": str(item.get("href", "")),
            }
        )
    return normalized or None


def _format_web_answer(results: list[dict[str, str]]) -> tuple[str, list[str]]:
    lines = []
    sources = []
    for idx, item in enumerate(results, start=1):
        title = item.get("title", "Untitled")
        content = item.get("content", "").strip()
        url = item.get("url", "").strip()
        lines.append(f"{idx}. {title}\n{content}")
        if url:
            sources.append(url)
    answer = "Web Search 检索结果摘要：\n\n" + "\n\n".join(lines)
    return answer, sorted(set(sources))


def _web_node(state: AgentState) -> AgentState:
    if not Config.ENABLE_WEB_SEARCH:
        state["web_result"] = {"answer": "未启用 Web Search。", "sources": []}
        return state

    query = state["query"]
    results = _search_with_tavily(query) or _search_with_duckduckgo(query)
    if not results:
        state["web_result"] = {"answer": "Web Search 未返回有效结果。", "sources": []}
        return state

    answer, sources = _format_web_answer(results)
    state["web_result"] = {"answer": answer, "sources": sources}
    return state


def _summarize_node(state: AgentState, rag_engine: RAGEngine) -> AgentState:
    if state["intent"] == "web_search":
        web = state.get("web_result") or {}
        state["answer"] = web.get("answer", "未获取到 Web Search 结果。")
        state["sources"] = web.get("sources", [])
        return state

    rag = state.get("rag_result") or {}
    state["answer"] = rag.get("answer", "")
    state["sources"] = rag.get("sources", [])
    return state


def build_agent_graph(rag_engine: RAGEngine):
    """构建 Router -> RAG/Web -> Summarize 的 LangGraph 工作流。"""
    if StateGraph is None:
        return None

    workflow = StateGraph(AgentState)
    workflow.add_node("router", _route_intent)
    workflow.add_node("local_rag", lambda state: _rag_node(state, rag_engine))
    workflow.add_node("web_search", _web_node)
    workflow.add_node("summarize", lambda state: _summarize_node(state, rag_engine))

    workflow.set_entry_point("router")
    workflow.add_conditional_edges(
        "router",
        lambda state: state["intent"],
        {"local_rag": "local_rag", "web_search": "web_search"},
    )
    workflow.add_edge("local_rag", "summarize")
    workflow.add_edge("web_search", "summarize")
    workflow.add_edge("summarize", END)

    return workflow.compile()
