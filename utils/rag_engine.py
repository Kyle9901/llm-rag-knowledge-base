"""
RAG 引擎模块：提供检索增强问答与流式输出能力
"""
import os
from typing import Any, Optional

from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import Config


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

        if Config.LANGCHAIN_TRACING_V2:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = Config.LANGCHAIN_PROJECT
            if Config.LANGCHAIN_API_KEY:
                os.environ["LANGCHAIN_API_KEY"] = Config.LANGCHAIN_API_KEY

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

    def query_with_sources(self, query: str) -> dict[str, Any]:
        chain = self.get_chain()
        if chain is None:
            return {"answer": "知识库为空，请先上传文档。", "sources": [], "context": []}

        response = chain.invoke(
            {"input": query},
            config={"tags": ["rag", "chat"], "metadata": {"component": "RAGEngine"}},
        )
        docs = response.get("context", []) or []
        sources = []
        for doc in docs:
            source_name = os.path.basename(doc.metadata.get("source", "未知文档"))
            page = int(doc.metadata.get("page", 0)) + 1
            sources.append(f"{source_name}#p{page}")
        return {"answer": response.get("answer", ""), "sources": sorted(set(sources)), "context": docs}

    def stream_answer(self, query: str):
        chain = self.get_chain()
        if chain is None:
            yield "知识库为空，请先上传文档。"
            return

        for chunk in chain.stream(
            {"input": query},
            config={"tags": ["rag", "stream"], "metadata": {"component": "RAGEngine"}},
        ):
            if "answer" in chunk:
                yield chunk["answer"]

    # 兼容旧版 Streamlit 层的接口
    def ask_with_steps(self, question: str, on_step=None) -> dict[str, Any]:
        if on_step:
            on_step("正在理解问题语义...")
            on_step("连接向量数据库...")
            on_step(f"正在检索 Top-{Config.RETRIEVER_SEARCH_K} 相关知识片段...")
            on_step("正在调用大语言模型生成回答...")
        result = self.query_with_sources(question)
        if on_step:
            on_step("回答生成完成")
        return {"answer": result.get("answer", ""), "context": result.get("context", [])}

    def ask_stream(self, question: str):
        yield from self.stream_answer(question)


def get_rag_chain() -> Optional[Any]:
    """兼容函数接口，供旧代码或路由封装调用。"""
    return RAGEngine().get_chain()
