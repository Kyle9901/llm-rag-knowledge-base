from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from database import Base, engine
from routers import chat, documents
from schemas import HealthResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=Config.APP_NAME,
    description="高性能 RAG 多智能体后端服务",
    version=Config.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(documents.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": f"{Config.APP_NAME} is running"}


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", service=Config.APP_NAME)
