"""
RAG 引擎模块：负责检索增强生成的核心逻辑
"""
import os
import time
from typing import Optional, Dict, Any, Callable, List
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from config import Config


class RAGEngine:
    """RAG 引擎：检索 + 生成"""
    
    _instance = None  # 单例模式
    
    def __new__(cls, *args, **kwargs):
        """单例模式：确保全局只有一个 RAG 引擎实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化 RAG 引擎：加载 Embeddings 和 LLM"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 初始化 Embeddings 模型
        self.embeddings = OpenAIEmbeddings(
            model=Config.ZHIPU_EMBEDDING_MODEL,
            api_key=Config.ZHIPU_API_KEY,
            base_url=Config.ZHIPU_BASE_URL,
            chunk_size=Config.EMBEDDING_CHUNK_SIZE
        )
        
        # 初始化对话模型
        self.llm = ChatOpenAI(
            model=Config.DEEPSEEK_MODEL,
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_BASE_URL,
            temperature=Config.LLM_TEMPERATURE,
            streaming=True  # 启用流式输出
        )
        
        self._chain = None
        self._retriever = None
        self._initialized = True
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """创建系统提示词模板"""
        return ChatPromptTemplate.from_messages([
            ("system", Config.SYSTEM_PROMPT),
            ("human", "{input}"),
        ])
    
    def get_chain(self) -> Optional[Any]:
        """
        获取 RAG 链（带缓存）
        
        Returns:
            如果向量库存在，返回 RAG 链；否则返回 None
        """
        # 检查向量库是否存在
        if not os.path.exists(Config.CHROMA_PERSIST_DIR):
            return None
        
        # 懒加载：首次调用时创建链
        if self._chain is None:
            vectorstore = Chroma(
                persist_directory=Config.CHROMA_PERSIST_DIR,
                embedding_function=self.embeddings
            )
            self._retriever = vectorstore.as_retriever(
                search_kwargs={"k": Config.RETRIEVER_SEARCH_K}
            )
            
            prompt = self._create_prompt()
            question_answer_chain = create_stuff_documents_chain(self.llm, prompt)
            self._chain = create_retrieval_chain(self._retriever, question_answer_chain)
        
        return self._chain
    
    def reset_chain(self):
        """重置 RAG 链（当向量库更新时调用）"""
        self._chain = None
        self._retriever = None
    
    def ask(self, question: str) -> Dict[str, Any]:
        """
        执行问答
        
        Args:
            question: 用户问题
            
        Returns:
            包含答案和上下文的字典
        """
        chain = self.get_chain()
        if chain is None:
            return {
                "answer": "知识库为空，请先上传文档。",
                "context": []
            }
        
        response = chain.invoke({"input": question})
        return {
            "answer": response.get("answer", ""),
            "context": response.get("context", [])
        }
    
    def ask_with_steps(
        self,
        question: str,
        on_step: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行问答（带步骤回调）
        
        Args:
            question: 用户问题
            on_step: 步骤回调函数，接收步骤描述字符串
            
        Returns:
            包含答案和上下文的字典
        """
        def log(step: str):
            """内部日志辅助函数"""
            if on_step:
                on_step(step)
        
        # 步骤 1: 问题理解与分析
        log("正在理解问题语义...")
        time.sleep(0.3)  # 模拟处理时间
        
        # 步骤 2: 获取检索器
        log("连接向量数据库...")
        chain = self.get_chain()
        if chain is None:
            log("知识库为空")
            return {
                "answer": "知识库为空，请先上传文档。",
                "context": []
            }
        
        # 步骤 3: 向量检索
        log(f"正在检索 Top-{Config.RETRIEVER_SEARCH_K} 相关知识片段...")
        
        # 先单独执行检索，获取检索到的文档
        if self._retriever:
            retrieved_docs = self._retriever.invoke(question)
            log(f"检索到 {len(retrieved_docs)} 个相关片段")
            
            # 显示检索到的片段摘要
            for i, doc in enumerate(retrieved_docs[:3], 1):
                source = os.path.basename(doc.metadata.get("source", "未知"))
                page = doc.metadata.get("page", 0) + 1
                log(f"   └─ 片段 {i}: 《{source}》第 {page} 页")
        else:
            retrieved_docs = []
        
        # 步骤 4: 生成回答
        log("正在调用大语言模型生成回答...")
        
        response = chain.invoke({"input": question})
        answer = response.get("answer", "")
        context = response.get("context", retrieved_docs)
        
        # 步骤 5: 完成
        log("回答生成完成")
        
        return {
            "answer": answer,
            "context": context
        }
    
    def ask_stream(self, question: str):
        """
        流式问答（支持打字机效果）
        
        Args:
            question: 用户问题
            
        Yields:
            str: 流式输出的文本片段
        """
        chain = self.get_chain()
        if chain is None:
            yield "⚠️ 知识库为空，请先上传文档。"
            return
        
        # 流式调用
        for chunk in chain.stream({"input": question}):
            # 只返回答案部分的流式输出
            if "answer" in chunk:
                yield chunk["answer"]
    
    def ask_stream_with_steps(
        self,
        question: str,
        on_step: Optional[Callable[[str], None]] = None
    ):
        """
        流式问答（带步骤回调，支持打字机效果）
        
        Args:
            question: 用户问题
            on_step: 步骤回调函数
            
        Yields:
            str: 流式输出的文本片段
        """
        def log(step: str):
            if on_step:
                on_step(step)
        
        # 步骤 1-3: 检索阶段
        log("正在理解问题语义...")
        log("连接向量数据库...")
        
        chain = self.get_chain()
        if chain is None:
            log("知识库为空")
            yield "知识库为空，请先上传文档。"
            return
        
        log(f"正在检索相关知识片段...")
        
        # 步骤 4: 流式生成
        log("正在生成回答...")
        
        full_answer = ""
        for chunk in chain.stream({"input": question}):
            if "answer" in chunk:
                full_answer += chunk["answer"]
                yield chunk["answer"]
        
        # 步骤 5: 完成
        log("回答生成完成")
    
    @staticmethod
    def is_vectorstore_ready() -> bool:
        """检查向量库是否就绪"""
        return os.path.exists(Config.CHROMA_PERSIST_DIR)
