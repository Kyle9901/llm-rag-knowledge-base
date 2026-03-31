from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from core.config import Config


def _build_engine():
    if Config.DATABASE_URL.startswith("sqlite"):
        return create_engine(
            Config.DATABASE_URL,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
    return create_engine(Config.DATABASE_URL, pool_pre_ping=True)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
