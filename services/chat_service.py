import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from models import ChatHistory, User
from services.agent_graph import build_agent_graph
from utils.rag_engine import RAGEngine


class ChatService:
    _rag_engine: RAGEngine | None = None
    _graph = None

    def __init__(self, db: Session):
        self.db = db
        if ChatService._rag_engine is None:
            ChatService._rag_engine = RAGEngine()
        self.rag_engine = ChatService._rag_engine

        if ChatService._graph is None:
            ChatService._graph = build_agent_graph(self.rag_engine)
        self.graph = ChatService._graph

    def _get_or_create_user(self, user_id: str | None) -> User | None:
        if not user_id:
            return None
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if user:
            return user
        user = User(user_id=user_id)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def save_message(self, session_id: str, role: str, content: str, user_id: str | None = None) -> ChatHistory:
        user = self._get_or_create_user(user_id)
        msg = ChatHistory(
            session_id=session_id,
            role=role,
            content=content,
            user_id=user.id if user else None,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_session_history(self, session_id: str, limit: int = 20) -> list[ChatHistory]:
        messages = (
            self.db.query(ChatHistory)
            .filter(ChatHistory.session_id == session_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        messages.reverse()
        return messages

    def _build_history_context(self, session_id: str, query: str, max_turns: int = 6) -> str:
        history = self.get_session_history(session_id=session_id, limit=max_turns * 2)
        if not history:
            return ""

        lines: list[str] = []
        for item in history:
            role = "用户" if item.role == "user" else "助手"
            lines.append(f"{role}: {item.content}")
        lines.append(f"用户: {query}")
        return "\n".join(lines)

    async def run_chat(self, session_id: str, query: str, user_id: str | None = None) -> tuple[str, list[str]]:
        history_context = self._build_history_context(session_id=session_id, query=query)
        self.save_message(session_id=session_id, role="user", content=query, user_id=user_id)

        if self.graph is not None:
            state = {
                "query": query,
                "history": history_context,
                "intent": "",
                "rag_result": None,
                "web_result": None,
                "answer": "",
                "sources": [],
            }
            result = await asyncio.to_thread(self.graph.invoke, state)
            answer = result.get("answer", "")
            sources = result.get("sources", [])
        else:
            result = await asyncio.to_thread(self.rag_engine.query_with_sources, query, history_context)
            answer = result.get("answer", "")
            sources = result.get("sources", [])

        self.save_message(session_id=session_id, role="assistant", content=answer, user_id=user_id)
        return answer, sources

    async def stream_chat(self, session_id: str, query: str, user_id: str | None = None) -> AsyncGenerator[str, None]:
        history_context = self._build_history_context(session_id=session_id, query=query)
        self.save_message(session_id=session_id, role="user", content=query, user_id=user_id)
        chunks: list[str] = []

        for chunk in self.rag_engine.stream_answer(query, history_context):
            chunks.append(chunk)
            yield chunk

        answer = "".join(chunks)
        self.save_message(session_id=session_id, role="assistant", content=answer, user_id=user_id)
