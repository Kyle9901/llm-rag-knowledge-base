import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from core.observability import traceable
from db.models import ChatHistory, User
from services.agent_graph import build_agent_graph, extract_graph_result
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
            .order_by(ChatHistory.created_at.desc(), ChatHistory.id.desc())
            .limit(limit)
            .all()
        )
        messages.reverse()
        return messages

    @staticmethod
    def _history_to_langchain_messages(history: list[ChatHistory]) -> list[HumanMessage | AIMessage]:
        converted: list[HumanMessage | AIMessage] = []
        for item in history:
            if item.role == "assistant":
                converted.append(AIMessage(content=item.content))
            else:
                converted.append(HumanMessage(content=item.content))
        return converted

    @staticmethod
    def _extract_text_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    value = item.get("text")
                    if isinstance(value, str):
                        texts.append(value)
            return "\n".join(texts).strip()
        return ""

    def _build_graph_state(self, history: list[ChatHistory], query: str) -> dict[str, Any]:
        messages = self._history_to_langchain_messages(history)
        messages.append(HumanMessage(content=query))
        return {"messages": messages}

    @staticmethod
    def _build_graph_config(
        session_id: str,
        mode: str,
        *,
        user_id: str | None = None,
        extra_tags: list[str] | None = None,
    ) -> dict[str, Any]:
        tags = ["chat", "agent_graph", mode]
        if extra_tags:
            tags.extend(extra_tags)
        return {
            "run_name": f"chat.{mode}",
            "tags": tags,
            "metadata": {
                "component": "chat_service",
                "mode": mode,
                "session_id": session_id,
                "user_id": user_id or "anonymous",
            },
            # 对齐 LangGraph 官方示例：显式传递 thread_id，便于 LangSmith Threads 聚合展示。
            "configurable": {"thread_id": session_id},
        }

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

    @traceable(name="chat.run_chat", run_type="chain", tags=["chat", "non_stream"])
    async def run_chat(self, session_id: str, query: str, user_id: str | None = None) -> tuple[str, list[str]]:
        history = self.get_session_history(session_id=session_id, limit=12)
        history_context = self._build_history_context(session_id=session_id, query=query)
        self.save_message(session_id=session_id, role="user", content=query, user_id=user_id)

        if self.graph is not None:
            state = self._build_graph_state(history=history, query=query)
            result = await self.graph.ainvoke(
                state,
                config=self._build_graph_config(session_id=session_id, mode="run_chat", user_id=user_id),
            )
            answer, sources = extract_graph_result(result)
            if not answer.strip():
                fallback = await asyncio.to_thread(self.rag_engine.query_with_sources, query, history_context)
                answer = fallback.get("answer", "")
                sources = fallback.get("sources", [])
        else:
            result = await asyncio.to_thread(self.rag_engine.query_with_sources, query, history_context)
            answer = result.get("answer", "")
            sources = result.get("sources", [])

        self.save_message(session_id=session_id, role="assistant", content=answer, user_id=user_id)
        return answer, sources

    async def stream_chat(self, session_id: str, query: str, user_id: str | None = None) -> AsyncGenerator[str, None]:
        history = self.get_session_history(session_id=session_id, limit=12)
        history_context = self._build_history_context(session_id=session_id, query=query)
        self.save_message(session_id=session_id, role="user", content=query, user_id=user_id)
        chunks: list[str] = []
        sources: list[str] = []

        if self.graph is not None:
            state = self._build_graph_state(history=history, query=query)
            final_state: dict[str, Any] | None = None

            try:
                async for event in self.graph.astream_events(
                    state,
                    version="v2",
                    config=self._build_graph_config(session_id=session_id, mode="stream_chat", user_id=user_id),
                ):
                    event_name = event.get("event")
                    data = event.get("data", {})

                    if event_name == "on_chat_model_stream":
                        chunk_obj = data.get("chunk")
                        content = self._extract_text_content(getattr(chunk_obj, "content", chunk_obj))
                        if content:
                            chunks.append(content)
                            yield content
                    elif event_name == "on_chain_end":
                        output = data.get("output")
                        if isinstance(output, dict) and "messages" in output:
                            final_state = output
            except Exception:
                try:
                    retry_result = await self.graph.ainvoke(
                        self._build_graph_state(history=history, query=query),
                        config=self._build_graph_config(
                            session_id=session_id,
                            mode="stream_chat_retry",
                            user_id=user_id,
                        ),
                    )
                    answer, sources = extract_graph_result(retry_result)
                    if answer:
                        yield answer
                    self.save_message(session_id=session_id, role="assistant", content=answer, user_id=user_id)
                    return
                except Exception:
                    fallback = await asyncio.to_thread(self.rag_engine.query_with_sources, query, history_context)
                    answer = fallback.get("answer", "")
                    sources = fallback.get("sources", [])
                    if answer:
                        yield answer
                    self.save_message(session_id=session_id, role="assistant", content=answer, user_id=user_id)
                    return

            answer = "".join(chunks).strip()
            if final_state is not None:
                final_answer, final_sources = extract_graph_result(final_state)
                if final_answer.strip():
                    if not chunks:
                        yield final_answer
                    answer = final_answer
                sources = final_sources

            if not answer:
                retry_result = await self.graph.ainvoke(
                    self._build_graph_state(history=history, query=query),
                    config=self._build_graph_config(
                        session_id=session_id,
                        mode="stream_chat_finalize",
                        user_id=user_id,
                    ),
                )
                answer, sources = extract_graph_result(retry_result)
            if not answer:
                fallback = await asyncio.to_thread(self.rag_engine.query_with_sources, query, history_context)
                answer = fallback.get("answer", "")
                sources = fallback.get("sources", [])
                if answer:
                    yield answer
        else:
            for chunk in self.rag_engine.stream_answer(query, history_context):
                chunks.append(chunk)
                yield chunk
            answer = "".join(chunks)

        self.save_message(session_id=session_id, role="assistant", content=answer, user_id=user_id)
