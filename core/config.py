"""
配置文件：集中管理 API、数据库、消息队列与可观测性配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _derive_result_backend(redis_url: str) -> str:
    """将 Redis broker URL 派生为 result backend URL。"""
    if redis_url.endswith("/0"):
        return f"{redis_url[:-2]}/1"
    return redis_url


class Config:
    """全局配置类"""

    APP_NAME = os.getenv("APP_NAME", "RAG Multi-Agent Backend")
    APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
    API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
    ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
        if origin.strip()
    ]
    API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "dev-static-token")

    # ==================== API 配置 ====================
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
    ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    ZHIPU_EMBEDDING_MODEL = os.getenv("ZHIPU_EMBEDDING_MODEL", "embedding-3")

    DEEPSEEK_API_KEY = os.getenv("OPENAI_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # ==================== 数据库配置 ====================
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@postgres:5432/rag_backend",
    )

    # ==================== 向量数据库配置 ====================
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "knowledge_base")

    # ==================== 文档处理配置 ====================
    TEXT_SPLITTER_CHUNK_SIZE = int(os.getenv("TEXT_SPLITTER_CHUNK_SIZE", "800"))
    TEXT_SPLITTER_CHUNK_OVERLAP = int(os.getenv("TEXT_SPLITTER_CHUNK_OVERLAP", "100"))
    RETRIEVER_SEARCH_K = int(os.getenv("RETRIEVER_SEARCH_K", "10"))
    OCR_DPI = int(os.getenv("OCR_DPI", "300"))
    OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "chi_sim+eng")
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data/uploads")

    # ==================== 模型参数 ====================
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    EMBEDDING_CHUNK_SIZE = int(os.getenv("EMBEDDING_CHUNK_SIZE", "60"))

    # ==================== 多智能体配置 ====================
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    # ==================== Celery 配置 ====================
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", _derive_result_backend(CELERY_BROKER_URL))

    # ==================== LangSmith 配置 ====================
    LANGCHAIN_TRACING_V2 = (
        os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        or os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    )
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    LANGCHAIN_PROJECT = (
        os.getenv("LANGCHAIN_PROJECT")
        or os.getenv("LANGSMITH_PROJECT")
        or "rag-multi-agent-backend"
    )

    # ==================== Prompt 配置 ====================
    SYSTEM_PROMPT = (
        "你是一个严谨的学术和阅读助手。请严格基于以下背景知识回答用户的问题。\n"
        "不要编造答案，如果背景知识中没有相关信息，请直接回答："
        "抱歉，在当前的知识库中未找到相关内容。\n\n"
        "背景知识：\n{context}"
    )
    SUMMARY_PROMPT = (
        "请基于以下候选信息给出最终回答，要求简洁、准确，并标注不确定性：\n\n"
        "{context}\n\n用户问题：{input}"
    )


def validate_config(require_model_keys: bool = True) -> bool:
    """验证必要的环境变量是否已配置"""
    missing_keys = []
    if require_model_keys and not Config.ZHIPU_API_KEY:
        missing_keys.append("ZHIPU_API_KEY")
    if require_model_keys and not Config.DEEPSEEK_API_KEY:
        missing_keys.append("OPENAI_API_KEY (for DeepSeek)")

    if missing_keys:
        raise EnvironmentError(
            f"缺少必要的环境变量: {', '.join(missing_keys)}\n"
            "请在项目根目录创建 .env 文件并配置这些变量。"
        )
    return True


def validate_startup_config() -> bool:
    """启动前硬校验，防止运行时才暴露关键配置缺失。"""
    missing_keys = []
    if not os.getenv("OPENAI_API_KEY"):
        missing_keys.append("OPENAI_API_KEY")
    if not os.getenv("REDIS_URL"):
        missing_keys.append("REDIS_URL")

    if missing_keys:
        raise EnvironmentError(
            f"启动失败，缺少关键环境变量: {', '.join(missing_keys)}\n"
            "请在 .env 中补齐后再启动服务。"
        )
    return True


def configure_langsmith_runtime_env() -> None:
    """
    将追踪相关配置写入进程环境变量，供 LangChain / LangSmith 客户端读取。

    LangSmith 控制台文档多写 LANGSMITH_*；LangChain 传统使用 LANGCHAIN_*。
    二者同时写入，避免「已配置但网页无轨迹」。
    """
    if not Config.LANGCHAIN_TRACING_V2:
        return
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    if Config.LANGCHAIN_API_KEY:
        key = Config.LANGCHAIN_API_KEY.strip()
        os.environ["LANGCHAIN_API_KEY"] = key
        os.environ["LANGSMITH_API_KEY"] = key
    project = (Config.LANGCHAIN_PROJECT or "default").strip()
    os.environ["LANGCHAIN_PROJECT"] = project
    os.environ["LANGSMITH_PROJECT"] = project
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com").strip()
    if endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = endpoint
