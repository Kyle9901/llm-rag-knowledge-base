import streamlit as st
import os
import fitz
import pytesseract
import tempfile
from dotenv import load_dotenv
from PIL import Image
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ================= 1. 页面基本设置 =================
st.set_page_config(page_title="我的AI阅读助手", page_icon="📚", layout="wide")
st.title("我的专属AI阅读与问答助手")
load_dotenv()

# ================= 2. 初始化 AI 核心引擎 =================
@st.cache_resource
def get_ai_engines():
    # 替换为你自己的配置
    embeddings = OpenAIEmbeddings(
        model="embedding-3",  # 模型名
        api_key=os.getenv("ZHIPU_API_KEY"),  # 秘钥
        base_url="https://open.bigmodel.cn/api/paas/v4",  # 接口地址
        chunk_size=60
    )
    llm = ChatOpenAI(
        model="deepseek-chat",  # 对话模型名
        api_key=os.getenv("OPENAI_API_KEY"),  # 秘钥
        base_url="https://api.deepseek.com",  # 接口地址
        temperature=0.3  # 让模型回答严谨一些
    )
    return embeddings, llm

def extract_text_with_ocr(file_path):
    """
    使用 PyMuPDF 将 PDF 按页转换为高分辨率图片，并调用 Tesseract 进行 OCR 识别。
    返回符合 LangChain 标准的 Document 列表。
    """
    doc = fitz.open(file_path)
    documents = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # 提高渲染分辨率 (dpi=300) 以保证 OCR 识别率
        pix = page.get_pixmap(dpi=300)

        # 将 PyMuPDF 的 pixmap 转换为 PIL Image 对象
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 调用 OCR 引擎，指定语言为简体中文+英文
        # 注意：如果运行时报错找不到 chi_sim，请检查第一步安装时是否勾选了中文包
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')

        if text.strip():
            # 将提取的文本封装为 LangChain Document 对象
            documents.append(Document(
                page_content=text,
                metadata={"source": file_path, "page": page_num}
            ))

    return documents

embeddings, llm = get_ai_engines()
persist_dir = "./chroma_db"

# ================= 3. 侧边栏：文件管理与数据源 =================
with st.sidebar:
    st.header("📁 知识库管理")
    st.markdown("在这里上传你的书籍、论文或文档。")

    uploaded_file = st.file_uploader("上传 PDF 文件", type=["pdf"])

    if uploaded_file is not None:
        if st.button("将文件加入大脑"):
            with st.spinner("正在解析文件并构建向量索引，请稍候..."):
                # 3.1 将上传的文件临时保存到本地
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name

                # 3.2 AI 知识切块逻辑
                loader = PyMuPDFLoader(tmp_file_path)
                docs = loader.load()

                has_text = False
                for doc in docs:
                    if doc.page_content.strip():
                        has_text = True
                        break

                # 3.3 智能兜底（Fallback）：如果基础提取为空，触发 OCR
                if not has_text:
                    st.warning(
                        "检测到扫描件或纯图片 PDF，正在启动底层 OCR 引擎进行像素级识别，请稍候... (这可能需要几分钟)")
                    docs = extract_text_with_ocr(tmp_file_path)

                # 3.4 终极安全拦截：如果 OCR 之后依然为空
                if not docs or len(docs) == 0:
                    st.error("解析失败：未能从该 PDF 中识别到任何文字内容。文件可能为空或图像质量过低。")
                    os.unlink(tmp_file_path)
                    st.stop()

                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=800,
                    chunk_overlap=100
                )
                splits = text_splitter.split_documents(docs)

                # 3.5 文本切分
                if not splits or len(splits) == 0:
                    st.error(
                        "⚠️ 解析失败：未能从该 PDF 中提取到任何文字！\n请检查：该文件是否为空？或者它是否是不可选中文本的纯图片/扫描件？")
                    # 删除临时文件并终止运行
                    os.unlink(tmp_file_path)
                    st.stop()

                # 3.3 存入 Chroma 向量数据库
                Chroma.from_documents(
                    documents=splits,
                    embedding=embeddings,
                    persist_directory=persist_dir
                )

                # 清理临时文件
                os.unlink(tmp_file_path)
                st.success(f"✅ {uploaded_file.name} 已成功存入知识库！切分为 {len(splits)} 个知识块。")

    st.divider()
    if st.button("⚠️ 清空整个知识库"):
        try:
            # 1. 像正常查阅一样，先连接到现在的数据库
            db_to_clear = Chroma(
                persist_directory="./chroma_db",
                embedding_function=embeddings  # 这里用你代码里定义的 embeddings 模型
            )

            # 2. 调用 Chroma 的官方 API：删除所有数据集合（不删文件夹本身，只清空内容）
            db_to_clear.delete_collection()

            st.success("✨ 知识库记忆已彻底擦除！")

            # 可选：让网页自动刷新一下，恢复初始状态
            # st.rerun()

        except Exception as e:
            st.error(f"清空失败: {e}")

# ================= 4. 初始化问答链 =================
def get_rag_chain():
    # 每次调用动态加载数据库，这样新上传的文件立刻生效
    if not os.path.exists(persist_dir):
        return None

    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    # k=10 表示每次检索 10 个相关片段
    retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

    system_prompt = (
        "你是一个严谨的学术和阅读助手。请严格基于以下【背景知识】回答用户的问题。\n"
        "不要编造答案，如果背景知识中没有相关信息，请直接回答“抱歉，在当前的知识库中未找到相关内容”。\n\n"
        "背景知识：\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    # create_retrieval_chain 这个工具天生就会把检索到的原文（context）连同答案一起返回给你
    return create_retrieval_chain(retriever, question_answer_chain)

rag_chain = get_rag_chain()

# ================= 5. 聊天界面UI =================
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("向你的知识库提问..."):
    if not rag_chain:
        st.warning("👈 请先在左侧上传文档，建立知识库！")
        st.stop()

    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("正在知识库中深度检索..."):
            response = rag_chain.invoke({"input": prompt})
            answer = response["answer"]
            source_documents = response["context"]  # 这里面装的就是检索出来的原文片段

            # 渲染大模型的回答
            st.markdown(answer)

            # 渲染引用的来源 (溯源功能)
            with st.expander("🔍 查看引用来源 (确保不瞎编)"):
                # 用一个集合去重，避免同一页被打印多次
                sources = set()
                for doc in source_documents:
                    # 获取文件名和页码 metadata
                    source_name = os.path.basename(doc.metadata.get('source', '未知文档'))
                    page = doc.metadata.get('page', '未知') + 1  # 页码通常从0开始，所以+1
                    sources.add(f"《{source_name}》 第 {page} 页")

                for s in sources:
                    st.markdown(f"- {s}")

    # 保存包含回答的完整消息
    st.session_state.messages.append({"role": "assistant", "content": answer})