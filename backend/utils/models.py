from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    column_key: str
    extra: str


@dataclass
class TableInfo:
    name: str
    primary_key: str | None = None
    columns: list[ColumnInfo] = field(default_factory=list)


@dataclass
class ContextDocument:
    document_id: str
    table_name: str
    kind: str
    text: str
    primary_key: str | None = None
    primary_value: Any = None
    row_data: dict[str, Any] | None = None


class ChatRequest(BaseModel):
    chat_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)


class NewChatRequest(BaseModel):
    title: str | None = None


class ChatSessionSummary(BaseModel):
    chat_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ChatResponse(BaseModel):
    chat_id: str
    summary: str
    table_data: list[dict[str, Any]]
    raw_data: list[dict[str, Any]]
    markdown: str
    timestamp: str
    sources: list[str]
    sql_used: str | None = None

