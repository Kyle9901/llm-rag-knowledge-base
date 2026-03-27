from celery.utils.log import get_task_logger

from celery_app import celery_app
from database import SessionLocal
from models import Document
from utils.rag_engine import RAGEngine
from utils.document_processor import DocumentProcessor

logger = get_task_logger(__name__)


@celery_app.task(bind=True, name="tasks.process_document")
def process_document_task(self, document_id: int, file_path: str):
    db = SessionLocal()
    try:
        self.update_state(state="PROGRESS", meta={"progress": "20%", "detail": "初始化文档处理器"})
        rag_engine = RAGEngine()
        processor = DocumentProcessor(rag_engine.embeddings)

        self.update_state(state="PROGRESS", meta={"progress": "45%", "detail": "PDF 解析与 OCR 识别"})
        splits = processor.process_pdf_path(file_path)

        self.update_state(state="PROGRESS", meta={"progress": "75%", "detail": "向量化并写入 Chroma"})
        processor.add_to_vectorstore(splits)
        rag_engine.reset_chain()

        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "completed"
            db.commit()

        return {"progress": "100%", "detail": f"完成，知识块数量: {len(splits)}"}
    except Exception as exc:  # pragma: no cover
        logger.exception("文档异步处理失败")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "failed"
            db.commit()
        raise exc
    finally:
        db.close()
