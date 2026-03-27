from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    query: str = Field(..., min_length=1)
    stream: bool = False
    user_id: str | None = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    session_id: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class DocumentUploadResponse(BaseModel):
    document_id: int
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    state: str
    progress: str | None = None
    detail: str | None = None


class ChatHistoryItem(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatHistoryItem] = Field(default_factory=list)
