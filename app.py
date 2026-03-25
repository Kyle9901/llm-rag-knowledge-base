"""
主应用文件：Streamlit Chat UI 界面
================================
使用原生 st.chat_message 和 st.chat_input 组件构建沉浸式对话界面
"""
import streamlit as st

from config import Config, validate_config
from utils.document_processor import DocumentProcessor
from utils.rag_engine import RAGEngine
from utils.chat_manager import ChatManager, SourceFormatter


# ==================== 1. 页面配置 ====================
st.set_page_config(
    page_title=Config.PAGE_TITLE,
    page_icon=Config.PAGE_ICON,
    layout=Config.LAYOUT
)

# 验证配置
try:
    validate_config()
except EnvironmentError as e:
    st.error(str(e))
    st.stop()


# ==================== 2. 初始化核心组件 ====================
@st.cache_resource
def init_rag_engine():
    """初始化 RAG 引擎（全局缓存）"""
    return RAGEngine()


@st.cache_resource
def init_document_processor():
    """初始化文档处理器"""
    rag_engine = init_rag_engine()
    return DocumentProcessor(rag_engine.embeddings)


# 初始化组件
rag_engine = init_rag_engine()
doc_processor = init_document_processor()
chat_manager = ChatManager()

# 初始化会话状态
chat_manager.init_session()


# ==================== 3. 侧边栏：知识库管理 ====================
with st.sidebar:
    st.header("知识库管理")
    st.markdown("上传书籍、论文或文档，构建你的专属知识库。")
    
    # 文件上传
    uploaded_file = st.file_uploader("上传 PDF 文件", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("将文件加入知识库", use_container_width=True):
            with st.status("正在处理文档...", expanded=True) as status:
                try:
                    status.write("正在保存上传文件...")
                    status.write("正在解析 PDF 文档...")
                    splits, tmp_path = doc_processor.process_pdf(uploaded_file)
                    
                    if not splits:
                        status.update(label="解析失败", state="error")
                        st.error(
                            "解析失败：未能从该 PDF 中提取到任何文字！\n"
                            "请检查：该文件是否为空？或图像质量过低？"
                        )
                        doc_processor.cleanup_temp_file(tmp_path)
                        st.stop()
                    
                    status.write(f"文本已切分为 {len(splits)} 个知识块")
                    status.write("正在生成向量嵌入...")
                    count = doc_processor.add_to_vectorstore(splits)
                    status.write("清理临时文件...")
                    doc_processor.cleanup_temp_file(tmp_path)
                    status.write("更新 RAG 引擎...")
                    rag_engine.reset_chain()
                    
                    status.update(
                        label=f"文档处理完成 - 共 {count} 个知识块",
                        state="complete",
                        expanded=False
                    )
                    
                    st.success(f"{uploaded_file.name} 已成功存入知识库！")
                    
                except Exception as e:
                    status.update(label="处理失败", state="error")
                    st.error(f"处理失败: {e}")
    
    st.divider()
    
    if st.button("清空整个知识库", use_container_width=True):
        with st.status("正在清空知识库...", expanded=True) as status:
            status.write("删除向量数据库...")
            
            if doc_processor.clear_vectorstore():
                status.write("重置 RAG 引擎...")
                rag_engine.reset_chain()
                status.write("清空聊天历史...")
                chat_manager.clear_messages()
                
                status.update(
                    label="知识库已清空",
                    state="complete",
                    expanded=False
                )
                
                st.success("知识库记忆已彻底擦除！")
                st.rerun()
            else:
                status.update(label="清空失败", state="error")
                st.error("清空失败，请重试。")
    
    st.divider()
    st.caption(f"{'知识库状态：已就绪' if RAGEngine.is_vectorstore_ready() else '知识库状态：空'}")


# ==================== 4. 主界面：Chat UI ====================
st.title("阅读与问答小助手")
st.caption("基于知识库的智能问答系统")

# 渲染聊天历史
chat_manager.render_chat_history()

# 聊天输入框
if prompt := st.chat_input("向你的知识库提问..."):
    if not RAGEngine.is_vectorstore_ready():
        st.warning("请先在左侧上传文档，建立知识库！")
        st.stop()
    
    chat_manager.render_user_message(prompt)
    
    try:
        chat_manager.render_assistant_message_with_status(
            rag_engine=rag_engine,
            question=prompt,
            use_streaming=True
        )
    except Exception as e:
        st.error(f"生成回复失败: {e}")


# ==================== 5. 页面底部信息 ====================
st.divider()
st.caption(
    "提示：上传文档后即可开始提问 | 所有回答均基于知识库内容生成 | "
    "点击「查看引用来源」验证答案真实性"
)
