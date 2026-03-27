from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from config import Config
from database import get_db
from schemas import DocumentUploadResponse, TaskStatusResponse
from services.document_service import DocumentService
from tasks.document_tasks import process_document_task

router = APIRouter(prefix=Config.API_PREFIX, tags=["documents"])


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    session_id: str = Form(...),
    user_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    service = DocumentService(db)
    document = await service.save_upload(file=file, session_id=session_id, user_id=user_id)
    task = process_document_task.delay(document.id, document.file_path)
    service.mark_processing(document.id, task.id)
    return DocumentUploadResponse(document_id=document.id, task_id=task.id, status="processing")


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse, status_code=status.HTTP_200_OK)
async def get_task_status(task_id: str):
    result = AsyncResult(task_id)
    info = result.info if isinstance(result.info, dict) else {}
    return TaskStatusResponse(
        task_id=task_id,
        state=result.state,
        progress=info.get("progress"),
        detail=info.get("detail"),
    )
