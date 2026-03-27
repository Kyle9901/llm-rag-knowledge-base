import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import Config
from database import get_db
from schemas import ChatHistoryResponse, ChatRequest, ChatResponse
from services.chat_service import ChatService

router = APIRouter(prefix=Config.API_PREFIX, tags=["chat"])


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    service = ChatService(db)
    if not request.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query 不能为空")

    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="流式输出请调用 /chat/stream 接口",
        )

    answer, sources = await service.run_chat(
        session_id=request.session_id,
        query=request.query,
        user_id=request.user_id,
    )
    return ChatResponse(answer=answer, sources=sources, session_id=request.session_id)


@router.post("/chat/stream", status_code=status.HTTP_200_OK)
async def chat_stream_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    service = ChatService(db)
    if not request.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query 不能为空")

    async def event_stream():
        async for chunk in service.stream_chat(
            session_id=request.session_id,
            query=request.query,
            user_id=request.user_id,
        ):
            yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse, status_code=status.HTTP_200_OK)
async def chat_history_endpoint(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    messages = service.get_session_history(session_id=session_id, limit=limit)
    return ChatHistoryResponse(session_id=session_id, messages=messages)
