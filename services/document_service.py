import os
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from config import Config
from models import Document, User


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        Path(Config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

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

    async def save_upload(self, file: UploadFile, session_id: str, user_id: str | None = None) -> Document:
        filename = file.filename or "uploaded.pdf"
        file_path = os.path.join(Config.UPLOAD_DIR, filename)
        user = self._get_or_create_user(user_id)

        content = await file.read()
        with open(file_path, "wb") as fp:
            fp.write(content)

        doc = Document(
            session_id=session_id,
            filename=filename,
            file_path=file_path,
            status="pending",
            user_id=user.id if user else None,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def mark_processing(self, document_id: int, task_id: str):
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return
        doc.status = "processing"
        doc.task_id = task_id
        self.db.commit()

    def update_status(self, document_id: int, status: str):
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return
        doc.status = status
        self.db.commit()
