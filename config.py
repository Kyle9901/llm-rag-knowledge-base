"""
配置文件：集中管理 API 密钥、模型参数、路径等配置项
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """全局配置类"""
    
    # ==================== API 配置 ====================
    # 智谱 AI 配置（Embedding 模型）
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
    ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_EMBEDDING_MODEL = "embedding-3"
    
    # DeepSeek 配置（对话模型）
    DEEPSEEK_API_KEY = os.getenv("OPENAI_API_KEY")
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    DEEPSEEK_MODEL = "deepseek-chat"
    
    # ==================== 向量数据库配置 ====================
    CHROMA_PERSIST_DIR = "./chroma_db"
    CHROMA_COLLECTION_NAME = "knowledge_base"
    
    # ==================== 文档处理配置 ====================
    TEXT_SPLITTER_CHUNK_SIZE = 800      # 文本切分块大小
    TEXT_SPLITTER_CHUNK_OVERLAP = 100   # 切分重叠字符数
    RETRIEVER_SEARCH_K = 10             # 检索时返回的相关片段数量
    OCR_DPI = 300                       # OCR 渲染分辨率
    OCR_LANGUAGE = "chi_sim+eng"        # OCR 语言（简体中文+英文）
    TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    # ==================== 模型参数 ====================
    LLM_TEMPERATURE = 0.3               # 对话模型温度（越低越严谨）
    EMBEDDING_CHUNK_SIZE = 60           # Embedding 批处理大小
    
    # ==================== UI 配置 ====================
    PAGE_TITLE = "AI 阅读与问答助手"
    PAGE_ICON = "📚"
    LAYOUT = "wide"
    
    # 系统提示词
    SYSTEM_PROMPT = (
        "你是一个严谨的学术和阅读助手。请严格基于以下【背景知识】回答用户的问题。\n"
        "不要编造答案，如果背景知识中没有相关信息，请直接回答"
        "抱歉，在当前的知识库中未找到相关内容。\n\n"
        "背景知识：\n{context}"
    )


# 配置验证
def validate_config():
    """验证必要的环境变量是否已配置"""
    missing_keys = []
    
    if not Config.ZHIPU_API_KEY:
        missing_keys.append("ZHIPU_API_KEY")
    if not Config.DEEPSEEK_API_KEY:
        missing_keys.append("OPENAI_API_KEY (for DeepSeek)")
    
    if missing_keys:
        raise EnvironmentError(
            f"⚠️ 缺少必要的环境变量: {', '.join(missing_keys)}\n"
            "请在项目根目录创建 .env 文件并配置这些变量。"
        )
    
    return True
