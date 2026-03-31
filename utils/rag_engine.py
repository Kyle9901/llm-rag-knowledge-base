"""
RAG 引擎模块：提供检索增强问答与流式输出能力
"""
import os
from typing import Any

from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from core.config import Config, configure_langsmith_runtime_env
from core.observability import traceable


class RAGEngine:
    """RAG 引擎单例。"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        configure_langsmith_runtime_env()

        self.embeddings = OpenAIEmbeddings(
            model=Config.ZHIPU_EMBEDDING_MODEL,
            api_key=Config.ZHIPU_API_KEY,
            base_url=Config.ZHIPU_BASE_URL,
            chunk_size=Config.EMBEDDING_CHUNK_SIZE,
        )
        self.llm = ChatOpenAI(
            model=Config.DEEPSEEK_MODEL,
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_BASE_URL,
            temperature=Config.LLM_TEMPERATURE,
            streaming=True,
        )
        # LangGraph 工具调用与 streaming=True 并存时，部分 OpenAI 兼容接口几乎不产生 tool_calls；
        # 决策节点单独使用非流式实例，检索链与最终生成仍用 self.llm（流式）。
        self.llm_for_tools = ChatOpenAI(
            model=Config.DEEPSEEK_MODEL,
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_BASE_URL,
            temperature=Config.LLM_TEMPERATURE,
            streaming=False,
        )

        self._retriever = None
        self._chain = None
        self._initialized = True

    def _prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [
                ("system", Config.SYSTEM_PROMPT),
                ("human", "{input}"),
            ]
        )

    @staticmethod
    def _compose_query(query: str, history: str | None = None) -> str:
        if not history:
            return query
        return (
            "请结合以下多轮对话历史理解当前问题。\n\n"
            f"{history}\n\n"
            f"当前问题：{query}"
        )

    @traceable(name="rag.get_chain", run_type="chain", tags=["rag", "retrieval_chain"])
    def get_chain(self):
        if not os.path.exists(Config.CHROMA_PERSIST_DIR):
            return None
        if self._chain is None:
            vectorstore = Chroma(
                persist_directory=Config.CHROMA_PERSIST_DIR,
                embedding_function=self.embeddings,
            )
            self._retriever = vectorstore.as_retriever(search_kwargs={"k": Config.RETRIEVER_SEARCH_K})
            qa_chain = create_stuff_documents_chain(self.llm, self._prompt())
            self._chain = create_retrieval_chain(self._retriever, qa_chain)
        return self._chain

    def reset_chain(self):
        self._chain = None
        self._retriever = None

    @traceable(name="rag.query_with_sources", run_type="chain", tags=["rag", "retrieval", "llm_generate"])
    def query_with_sources(self, query: str, history: str | None = None) -> dict[str, Any]:
        chain = self.get_chain()
        if chain is None:
            return {"answer": "知识库为空，请先上传文档。", "sources": [], "context": []}

        effective_query = self._compose_query(query, history)
        response = chain.invoke(
            {"input": effective_query},
            config={
                "tags": ["rag", "chat", "retrieval", "generation"],
                "metadata": {"component": "RAGEngine", "operation": "query_with_sources"},
            },
        )
        docs = response.get("context", []) or []
        sources = []
        for doc in docs:
            source_name = os.path.basename(doc.metadata.get("source", "未知文档"))
            page = int(doc.metadata.get("page", 0)) + 1
            sources.append(f"{source_name}#p{page}")
        return {"answer": response.get("answer", ""), "sources": sorted(set(sources)), "context": docs}

    @traceable(name="rag.stream_answer", run_type="chain", tags=["rag", "stream", "llm_generate"])
    def stream_answer(self, query: str, history: str | None = None):
        chain = self.get_chain()
        if chain is None:
            yield "知识库为空，请先上传文档。"
            return

        effective_query = self._compose_query(query, history)
        for chunk in chain.stream(
            {"input": effective_query},
            config={
                "tags": ["rag", "stream", "retrieval", "generation"],
                "metadata": {"component": "RAGEngine", "operation": "stream_answer"},
            },
        ):
            if "answer" in chunk:
                yield chunk["answer"]
