from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from utils.models import ChatRequest, ChatResponse, ChatSessionSummary, NewChatRequest

router = APIRouter(tags=["chat"])


def get_chat_service(request: Request):
    return request.app.state.chat_service


@router.post("/chat", response_model=ChatResponse)
def chat(request_body: ChatRequest, request: Request) -> ChatResponse:
    service = get_chat_service(request)
    try:
        return service.process_chat(request_body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/history", response_model=list[ChatSessionSummary])
def history(request: Request) -> list[ChatSessionSummary]:
    service = get_chat_service(request)
    return service.get_history()


@router.post("/new-chat", response_model=ChatSessionSummary)
def new_chat(request_body: NewChatRequest, request: Request) -> ChatSessionSummary:
    service = get_chat_service(request)
    return service.create_new_chat(request_body.title)

