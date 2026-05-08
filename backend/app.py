from __future__ import annotations

import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ai.query_service import ChatService
from routes.chat import router as chat_router
from utils.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Database Chatbot",
    description="A ChatGPT-inspired database chatbot backed by MySQL, FAISS, SentenceTransformers, and Groq.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_service = ChatService()
app.state.chat_service = chat_service
app.include_router(chat_router)

frontend_dir = settings.frontend_dir
static_mount_path = "/static"
if frontend_dir.exists():
    app.mount(static_mount_path, StaticFiles(directory=frontend_dir), name="static")


@app.on_event("startup")
def startup_event() -> None:
    try:
        chat_service.bootstrap()
        logger.info("Chat service bootstrapped successfully.")
    except Exception as exc:  # pragma: no cover - startup should remain resilient
        logger.warning("Startup bootstrap skipped: %s", exc)


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    index_path = frontend_dir / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(f"Frontend entrypoint not found: {index_path}")
    return FileResponse(index_path)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app:app", host=settings.backend_host, port=settings.backend_port, reload=True)

