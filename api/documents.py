from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
import redis
from sqlalchemy.orm import Session

from core.config import Config
from db.database import get_db
from schemas.payloads import DocumentUploadResponse, TaskStatusResponse
from services.document_service import DocumentService
from tasks.document_tasks import process_document_task

router = APIRouter(prefix=Config.API_PREFIX, tags=["documents"])


def _assert_broker_ready() -> None:
    client = redis.Redis.from_url(
        Config.CELERY_BROKER_URL,
        socket_connect_timeout=1,
        socket_timeout=1,
        retry_on_timeout=False,
    )
    try:
        client.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="任务队列不可用，请检查 Redis/Celery 服务。",
        ) from exc
    finally:
        client.close()


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    session_id: str = Form(...),
    user_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    _assert_broker_ready()
    service = DocumentService(db)
    document = await service.save_upload(file=file, session_id=session_id, user_id=user_id)
    try:
        # 队列不可用时快速失败，避免接口长时间阻塞。
        task = process_document_task.apply_async(args=(document.id, document.file_path), retry=False)
    except Exception as exc:
        service.update_status(document.id, "failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="任务队列不可用，请检查 Redis/Celery 服务。",
        ) from exc
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
