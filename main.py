import logging
import time
from contextlib import asynccontextmanager

import redis
from sqlalchemy import text

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import chat, documents
from core.config import Config, configure_langsmith_runtime_env, validate_config, validate_startup_config
from core.security import verify_bearer_token
from db.database import Base, engine
from schemas import HealthResponse

logger = logging.getLogger("rag_backend.startup")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_langsmith_runtime_env()
    try:
        validate_config(require_model_keys=True)
        validate_startup_config()
    except EnvironmentError as exc:
        logger.error("配置校验失败: %s", exc)
        raise

    redis_client = redis.Redis.from_url(
        Config.REDIS_URL,
        socket_connect_timeout=2,
        socket_timeout=2,
        retry_on_timeout=False,
    )
    try:
        redis_client.ping()
    except Exception as exc:
        logger.error("Redis 连接失败 REDIS_URL=%s", Config.REDIS_URL)
        raise RuntimeError("启动失败：Redis 不可用，请检查 REDIS_URL 指向的服务。") from exc
    finally:
        redis_client.close()

    # PostgreSQL 在 compose 中虽已 healthy，首次 TCP/认证仍可能出现瞬时失败，做短重试避免 API 直接退出。
    last_exc: Exception | None = None
    for attempt in range(1, 11):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception as exc:
            last_exc = exc
            logger.warning("数据库连接失败（第 %s/10 次），2s 后重试: %s", attempt, exc)
            time.sleep(2)
    else:
        logger.error("数据库在多次重试后仍不可用 DATABASE_URL=%s", Config.DATABASE_URL)
        raise RuntimeError("启动失败：PostgreSQL 不可用，请检查 DATABASE_URL 与数据库服务。") from last_exc

    Base.metadata.create_all(bind=engine)
    logger.info("应用启动完成，监听 0.0.0.0:8000")
    yield

app = FastAPI(
    title=Config.APP_NAME,
    description="高性能 RAG 多智能体后端服务",
    version=Config.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, dependencies=[Depends(verify_bearer_token)])
app.include_router(documents.router, dependencies=[Depends(verify_bearer_token)])


@app.get("/")
async def root():
    return {"status": "ok", "message": f"{Config.APP_NAME} is running"}


@app.get(f"{Config.API_PREFIX}/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", service=Config.APP_NAME)
