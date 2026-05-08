from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path

from utils.formatter import now_iso
from utils.models import ChatSessionSummary


class HistoryStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._lock = threading.Lock()

    def ensure_store(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text(json.dumps({"sessions": []}, indent=2), encoding="utf-8")

    def list_sessions(self) -> list[ChatSessionSummary]:
        self.ensure_store()
        data = self._read_store()
        sessions = []
        for session in data["sessions"]:
            sessions.append(
                ChatSessionSummary(
                    chat_id=session["chat_id"],
                    title=session["title"],
                    created_at=session["created_at"],
                    updated_at=session["updated_at"],
                    message_count=len(session["messages"]),
                )
            )
        return sorted(sessions, key=lambda item: item.updated_at, reverse=True)

    def create_session(self, title: str) -> ChatSessionSummary:
        self.ensure_store()
        timestamp = now_iso()
        session = {
            "chat_id": str(uuid.uuid4()),
            "title": title,
            "created_at": timestamp,
            "updated_at": timestamp,
            "messages": [],
        }
        with self._lock:
            data = self._read_store()
            data["sessions"].append(session)
            self._write_store(data)

        return ChatSessionSummary(
            chat_id=session["chat_id"],
            title=session["title"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
            message_count=0,
        )

    def append_exchange(
        self,
        *,
        chat_id: str,
        user_message: str,
        assistant_message: str,
        sql_used: str,
    ) -> None:
        self.ensure_store()
        with self._lock:
            data = self._read_store()
            session = next((item for item in data["sessions"] if item["chat_id"] == chat_id), None)

            if session is None:
                session = {
                    "chat_id": chat_id,
                    "title": user_message[:42],
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "messages": [],
                }
                data["sessions"].append(session)

            session["messages"].append(
                {
                    "timestamp": now_iso(),
                    "user": user_message,
                    "assistant": assistant_message,
                    "sql_used": sql_used,
                }
            )
            session["updated_at"] = now_iso()
            if len(session["messages"]) == 1 and session["title"] == "New chat":
                session["title"] = user_message[:42]

            self._write_store(data)

    def _read_store(self) -> dict:
        return json.loads(self.file_path.read_text(encoding="utf-8"))

    def _write_store(self, data: dict) -> None:
        self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

