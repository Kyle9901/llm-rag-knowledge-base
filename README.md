# 基于大模型的RAG智能知识库

![Build](https://img.shields.io/badge/build-active-blue)
![Version](https://img.shields.io/badge/version-v3.0-informational)
![License](https://img.shields.io/badge/license-MIT-green)

一个基于 **Streamlit**、**LangChain**、**Chroma** 与 **DeepSeek / 智谱 Embedding** 的本地知识库问答系统。项目面向 PDF 文档阅读与检索增强生成场景，解决“上传资料后如何进行可溯源问答”的核心问题。

应用支持 **PDF 解析**、**OCR 识别**、**向量检索**、**流式对话** 与 **引用来源展示**，适合作为个人知识库、课程资料问答、论文阅读助手的起步项目。

## Features

- 支持上传 **PDF** 文档并构建本地 **Chroma 向量数据库**
- 支持普通 PDF 文本提取，遇到扫描件时自动切换到 **Tesseract OCR**
- 使用 **RecursiveCharacterTextSplitter** 对文档进行切块，提升检索质量
- 使用 **智谱 Embedding** 生成向量，结合 **DeepSeek Chat** 完成 RAG 问答
- 使用 **Streamlit Chat UI** 构建对话式界面，支持历史消息保存在 `st.session_state`
- 提供基于 `st.status` 的处理过程展示，减少长耗时任务的黑盒等待感
- 支持查看答案引用来源，便于核验模型回答是否来自知识库内容
- 支持清空知识库并重置会话状态，便于多轮实验和本地调试

## Tech Stack

- 前端 / UI：
  - **Streamlit**
- 应用框架：
  - **Python**
  - **python-dotenv**
- 文档处理：
  - **PyMuPDF**
  - **Pillow**
  - **pytesseract**
- RAG / LLM：
  - **LangChain**
  - **langchain-openai**
  - **langchain-chroma**
  - **langchain-community**
  - **langchain-text-splitters**
  - **langchain-classic**
- 向量数据库：
  - **Chroma**
- 模型服务：
  - **DeepSeek Chat**
  - **Zhipu Embedding-3**

## Quick Start

### 1. 环境要求

- **Python 3.12**（建议）
- 已安装 **Tesseract OCR**
- 可用的 **DeepSeek API Key**
- 可用的 **Zhipu API Key**

> 当前代码中默认的 Tesseract 路径为 `C:\Program Files\Tesseract-OCR\tesseract.exe`。如果你的安装路径不同，请修改 `config.py` 中的 `TESSERACT_CMD`。

### 2. 克隆项目

```bash
git clone https://github.com/Kyle9901/llm-rag-knowledge-base
cd llm-rag-knowledge-base
```

### 3. 创建虚拟环境

```bash
python -m venv .venv
```

激活虚拟环境：

```bash
# Linux / macOS
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 4. 安装依赖

当前仓库中未包含 `requirements.txt`，可先按现有代码依赖手动安装：

```bash
pip install streamlit python-dotenv pymupdf pytesseract pillow chromadb langchain langchain-core langchain-openai langchain-chroma langchain-community langchain-text-splitters langchain-classic
```

### 5. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
ZHIPU_API_KEY=[请在此处填入：你的智谱 API Key]
OPENAI_API_KEY=[请在此处填入：你的 DeepSeek API Key]
```

说明：

- `ZHIPU_API_KEY`：用于 **Embedding** 模型 `embedding-3`
- `OPENAI_API_KEY`：在本项目中被用于 **DeepSeek Chat** 的 API 调用

### 6. 启动应用

```bash
streamlit run app.py
```

启动后，在浏览器中访问 Streamlit 默认地址：

```text
http://localhost:8501
```

### 7. 使用流程

1. 打开侧边栏并上传 PDF 文档
2. 点击“将文件加入知识库”完成解析、切块与向量化
3. 在主界面输入问题并发起对话
4. 查看生成答案以及“查看引用来源”中的溯源信息

## Project Structure

```text
llm-rag-knowledge-base/
├── app.py
├── config.py
├── README.md
├── .env
└── utils/
    ├── __init__.py
    ├── chat_manager.py
    ├── document_processor.py
    └── rag_engine.py
```

核心文件说明：

- `app.py`：Streamlit 应用入口，负责页面布局、文件上传、聊天交互与状态展示
- `config.py`：集中管理模型配置、路径配置、OCR 参数与环境变量校验
- `utils/document_processor.py`：负责 PDF 解析、OCR 识别、文本切块与向量库存储
- `utils/rag_engine.py`：负责向量检索、Prompt 构建、RAG Chain 初始化与问答调用
- `utils/chat_manager.py`：负责聊天记录状态管理、消息渲染、状态框与引用来源展示
- `chroma_db/`：运行后自动生成的本地向量数据库目录

## License

本项目默认采用 **MIT License**。
