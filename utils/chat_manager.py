"""
聊天管理模块：负责会话状态管理与消息处理
"""
import os
from typing import List, Dict, Any, Optional
import streamlit as st


class ChatManager:
    """聊天管理器：封装会话状态操作"""
    
    MESSAGES_KEY = "messages"
    
    @staticmethod
    def init_session():
        """初始化会话状态"""
        if ChatManager.MESSAGES_KEY not in st.session_state:
            st.session_state[ChatManager.MESSAGES_KEY] = []
    
    @staticmethod
    def get_messages() -> List[Dict[str, str]]:
        """获取所有历史消息"""
        return st.session_state.get(ChatManager.MESSAGES_KEY, [])
    
    @staticmethod
    def add_message(role: str, content: str):
        """添加一条消息到历史记录"""
        if ChatManager.MESSAGES_KEY not in st.session_state:
            st.session_state[ChatManager.MESSAGES_KEY] = []
        
        st.session_state[ChatManager.MESSAGES_KEY].append({
            "role": role,
            "content": content
        })
    
    @staticmethod
    def clear_messages():
        """清空所有历史消息"""
        st.session_state[ChatManager.MESSAGES_KEY] = []
    
    @staticmethod
    def render_chat_history():
        """渲染聊天历史"""
        messages = ChatManager.get_messages()
        
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    @staticmethod
    def render_user_message(content: str):
        """渲染用户消息并保存"""
        with st.chat_message("user"):
            st.markdown(content)
        
        ChatManager.add_message("user", content)
    
    @staticmethod
    def render_assistant_message(
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None
    ):
        """渲染助手消息并保存"""
        with st.chat_message("assistant"):
            st.markdown(content)
            
            if sources:
                with st.expander("查看引用来源"):
                    unique_sources = set()
                    for doc in sources:
                        source_name = os.path.basename(
                            doc.metadata.get("source", "未知文档")
                        )
                        page = doc.metadata.get("page", 0) + 1
                        unique_sources.add(f"《{source_name}》 第 {page} 页")
                    
                    for s in unique_sources:
                        st.markdown(f"- {s}")
        
        ChatManager.add_message("assistant", content)
    
    @staticmethod
    def render_assistant_message_with_status(
        rag_engine,
        question: str,
        use_streaming: bool = False
    ):
        """
        使用 st.status 组件渲染助手消息（透明化处理过程）
        
        Args:
            rag_engine: RAG 引擎实例
            question: 用户问题
            use_streaming: 是否使用流式输出
            
        Returns:
            回答内容
        """
        steps_log = []
        context = []
        
        def on_step(step_desc: str):
            """步骤回调函数"""
            steps_log.append(step_desc)
        
        with st.chat_message("assistant"):
            # 步骤 1: 在 chat_message 内优先构建 st.status 展示检索过程
            with st.status("正在思考中...", expanded=True) as status:
                
                # 执行检索并记录步骤
                response = rag_engine.ask_with_steps(question, on_step)
                context = response.get("context", [])
                
                # 显示所有步骤日志
                for step in steps_log:
                    status.write(step)
                
                # 完成后自动收起
                status.update(
                    label="思考完成",
                    state="complete",
                    expanded=False
                )
            
            # 步骤 2: 在 status 外部调用 st.write_stream 展示答案
            if use_streaming:
                answer = st.write_stream(rag_engine.ask_stream(question))
            else:
                answer = response.get("answer", "")
                st.markdown(answer)
            
            # 步骤 3: 在答案下方紧跟 expander 展示参考来源
            if context:
                with st.expander("查看引用来源"):
                    unique_sources = set()
                    for doc in context:
                        source_name = os.path.basename(
                            doc.metadata.get("source", "未知文档")
                        )
                        page = doc.metadata.get("page", 0) + 1
                        unique_sources.add(f"《{source_name}》 第 {page} 页")
                    
                    for s in unique_sources:
                        st.markdown(f"- {s}")
        
        ChatManager.add_message("assistant", answer)
        return answer
    
    @staticmethod
    def render_streaming_response(response_stream, sources: Optional[List] = None):
        """渲染流式响应"""
        with st.chat_message("assistant"):
            response = st.write_stream(response_stream)
            
            if sources:
                with st.expander("查看引用来源"):
                    unique_sources = set()
                    for doc in sources:
                        source_name = os.path.basename(
                            doc.metadata.get("source", "未知文档")
                        )
                        page = doc.metadata.get("page", 0) + 1
                        unique_sources.add(f"《{source_name}》 第 {page} 页")
                    
                    for s in unique_sources:
                        st.markdown(f"- {s}")
        
        ChatManager.add_message("assistant", response)
        return response


class SourceFormatter:
    """引用来源格式化工具"""
    
    @staticmethod
    def format_documents(documents: List[Any]) -> List[str]:
        """格式化文档来源列表"""
        sources = set()
        for doc in documents:
            source_name = os.path.basename(doc.metadata.get("source", "未知文档"))
            page = doc.metadata.get("page", 0) + 1
            sources.add(f"《{source_name}》 第 {page} 页")
        
        return list(sources)
