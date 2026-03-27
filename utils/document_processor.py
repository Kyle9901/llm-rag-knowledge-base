"""
文档处理模块：负责 PDF 解析、OCR 识别、文本切分与向量化存储
"""
import os
import tempfile
from typing import List

import fitz
import pytesseract
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PIL import Image

from config import Config

# 配置 Tesseract OCR 路径
pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD


class DocumentProcessor:
    """文档处理器：解析 PDF 并构建向量索引"""
    
    def __init__(self, embeddings):
        """
        初始化文档处理器
        
        Args:
            embeddings: LangChain Embeddings 对象
        """
        self.embeddings = embeddings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.TEXT_SPLITTER_CHUNK_SIZE,
            chunk_overlap=Config.TEXT_SPLITTER_CHUNK_OVERLAP
        )
    
    def extract_text_with_ocr(self, file_path: str) -> List[Document]:
        """
        使用 PyMuPDF + Tesseract OCR 提取扫描件 PDF 文字
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            Document 对象列表，每个对象包含一页的 OCR 文本
        """
        doc = fitz.open(file_path)
        documents = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # 提高渲染分辨率以提升 OCR 识别率
            pix = page.get_pixmap(dpi=Config.OCR_DPI)
            
            # 转换为 PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # 调用 OCR 引擎
            text = pytesseract.image_to_string(img, lang=Config.OCR_LANGUAGE)
            
            if text.strip():
                documents.append(Document(
                    page_content=text,
                    metadata={"source": file_path, "page": page_num}
                ))
        
        return documents
    
    def process_pdf_path(self, file_path: str) -> List[Document]:
        """
        处理本地 PDF 文件：解析文本 -> OCR 兜底 -> 切分
        """
        loader = PyMuPDFLoader(file_path)
        docs = loader.load()

        has_text = any(doc.page_content.strip() for doc in docs)
        if not has_text:
            docs = self.extract_text_with_ocr(file_path)

        splits = self.text_splitter.split_documents(docs)
        return splits

    # 兼容旧版 Streamlit 上传对象接口
    def process_pdf(self, uploaded_file):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            data = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
            tmp_file.write(data)
            tmp_path = tmp_file.name
        return self.process_pdf_path(tmp_path), tmp_path
    
    def add_to_vectorstore(self, documents: List[Document]) -> int:
        """
        将文档添加到向量数据库
        
        Args:
            documents: Document 对象列表
            
        Returns:
            成功添加的文档块数量
        """
        if not documents:
            return 0
        
        Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=Config.CHROMA_PERSIST_DIR
        )
        
        return len(documents)
    
    def clear_vectorstore(self) -> bool:
        """
        清空向量数据库
        
        Returns:
            是否成功清空
        """
        try:
            db = Chroma(
                persist_directory=Config.CHROMA_PERSIST_DIR,
                embedding_function=self.embeddings
            )
            db.delete_collection()
            return True
        except Exception as e:
            print(f"清空向量库失败: {e}")
            return False
    
    @staticmethod
    def vectorstore_exists() -> bool:
        """检查向量数据库是否存在"""
        return os.path.exists(Config.CHROMA_PERSIST_DIR)
    
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"清理临时文件失败: {e}")
