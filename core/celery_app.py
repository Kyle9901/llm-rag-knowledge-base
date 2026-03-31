from celery import Celery

from core.config import Config

celery_app = Celery(
    "rag_backend",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Worker 仅加载本模块时，需显式 import 以注册 @celery_app.task
import tasks.document_tasks  # noqa: E402, F401
