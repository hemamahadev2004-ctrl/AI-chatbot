from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from backend.ai.embeddings import EmbeddingService
from backend.ai.groq_client import GroqService
from backend.ai.vector_store import FaissVectorStore
from db.repository import MySQLRepository
from backend.utils.config import settings
from backend.utils.formatter import (
    build_fallback_markdown,
    build_session_title,
    format_context_matches,
    format_schema_overview,
    now_iso,
    to_json_safe_rows,
)
from utils.history_store import HistoryStore
from utils.models import ChatRequest, ChatResponse, ChatSessionSummary, ContextDocument, TableInfo
from utils.safety import extract_json_object, validate_message, validate_sql_plan


class ChatService:
    def __init__(self) -> None:
        self.repository = MySQLRepository()
        self.embedding_service = EmbeddingService()
        self.groq_service = GroqService()
        self.vector_store = FaissVectorStore()
        self.history_store = HistoryStore(settings.history_file)
        self.schema_map: dict[str, TableInfo] = {}

    def bootstrap(self) -> None:
        self.history_store.ensure_store()

    def create_new_chat(self, title: str | None = None) -> ChatSessionSummary:
        return self.history_store.create_session(title or "New chat")

    def get_history(self) -> list[ChatSessionSummary]:
        return self.history_store.list_sessions()

    def ensure_index(self, force: bool = False) -> None:
        if not force and not self.vector_store.needs_refresh(settings.index_refresh_minutes):
            return

        schema = self.repository.get_schema()
        if not schema:
            raise RuntimeError("No tables were found in the configured MySQL database.")

        documents = self.repository.build_context_documents(schema, settings.max_index_rows_per_table)
        vectors = self.embedding_service.embed_batch([document.text for document in documents])
        self.vector_store.rebuild(documents, vectors)
        self.schema_map = {table.name: table for table in schema}

    def process_chat(self, request_body: ChatRequest) -> ChatResponse:
        user_message = validate_message(request_body.message)
        self.ensure_index()

        chat_id = request_body.chat_id
        if not chat_id:
            session = self.create_new_chat(build_session_title(user_message))
            chat_id = session.chat_id

        matches = self._retrieve_context(user_message)
        candidate_tables = self._candidate_tables(matches)
        schema_excerpt = format_schema_overview(
            [self.schema_map[table] for table in candidate_tables if table in self.schema_map]
        )
        context_excerpt = format_context_matches(matches)

        sql = None
        rows: list[dict[str, Any]] = []
        try:
            sql_plan = self._generate_sql_plan(user_message, schema_excerpt, context_excerpt, candidate_tables)
            sql, params = validate_sql_plan(sql_plan, set(self.schema_map))
            rows = self.repository.execute_safe_query(sql, params)
        except Exception as exc:
            if "GROQ_API_KEY" in str(exc):
                raise
            sql = None
            rows = []

        if not rows:
            rows = self._fallback_rows(matches)

        json_safe_rows = to_json_safe_rows(rows)
        answer_payload = self._generate_answer(user_message, json_safe_rows, schema_excerpt, context_excerpt)

        summary = answer_payload.get("summary") or "No summary generated."
        markdown = answer_payload.get("markdown") or build_fallback_markdown(summary, json_safe_rows)
        sources = sorted({document.table_name for document, _ in matches})
        timestamp = now_iso()

        response = ChatResponse(
            chat_id=chat_id,
            summary=summary,
            table_data=json_safe_rows[:20],
            raw_data=json_safe_rows,
            markdown=markdown,
            timestamp=timestamp,
            sources=sources,
            sql_used=sql,
        )

        self.history_store.append_exchange(
            chat_id=chat_id,
            user_message=user_message,
            assistant_message=summary,
            sql_used=sql,
        )
        return response

    def _retrieve_context(self, question: str) -> list[tuple[ContextDocument, float]]:
        query_vector = self.embedding_service.embed_text(question)
        return self.vector_store.search(query_vector, settings.vector_top_k)

    def _candidate_tables(self, matches: list[tuple[ContextDocument, float]]) -> list[str]:
        ordered_tables: list[str] = []
        seen: set[str] = set()

        for document, _score in matches:
            if document.table_name not in seen:
                ordered_tables.append(document.table_name)
                seen.add(document.table_name)

        if not ordered_tables:
            ordered_tables = list(self.schema_map)[:4]

        return ordered_tables[:6]

    def _generate_sql_plan(
        self,
        question: str,
        schema_excerpt: str,
        context_excerpt: str,
        candidate_tables: list[str],
    ) -> dict[str, Any]:
        system_prompt = (
            "You are an AI database query planner for MySQL.\n"
            "Return only valid JSON with keys sql, params, and rationale.\n"
            "Rules:\n"
            "- Generate exactly one read-only SELECT query.\n"
            "- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, or multiple statements.\n"
            "- Use MySQL syntax only.\n"
            "- Use parameter placeholders %s when a literal user-derived value is needed.\n"
            "- Prefer explicit columns and aliases.\n"
            "- Add LIMIT for detail queries.\n"
            "- If the question asks for totals, trends, or comparisons, use aggregation.\n"
            "- Use only tables and columns present in the provided schema."
        )
        user_prompt = (
            f"Today's date: {datetime.now().date().isoformat()}\n\n"
            f"User question:\n{question}\n\n"
            f"Candidate tables:\n{', '.join(candidate_tables) if candidate_tables else 'None'}\n\n"
            f"Schema excerpt:\n{schema_excerpt}\n\n"
            f"Retrieved database context:\n{context_excerpt}\n"
        )
        raw_response = self.groq_service.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=800,
        )
        return extract_json_object(raw_response)

    def _generate_answer(
        self,
        question: str,
        rows: list[dict[str, Any]],
        schema_excerpt: str,
        context_excerpt: str,
    ) -> dict[str, str]:
        if not rows:
            summary = "I couldn't find matching records in the database for that question."
            return {
                "summary": summary,
                "markdown": (
                    f"{summary}\n\n"
                    "Try asking with a table, date range, employee, product, or other entity that exists in your data."
                ),
            }

        system_prompt = (
            "You are an AI database assistant.\n"
            "Only answer using the provided SQL result and retrieved database context.\n"
            "Do not hallucinate or invent missing facts.\n"
            "Return only valid JSON with keys summary and markdown.\n"
            "Write concise, professional answers.\n"
            "Use markdown tables when structured data would help.\n"
            "If the SQL result is insufficient, explicitly say so."
        )
        user_prompt = (
            f"User question:\n{question}\n\n"
            f"Schema excerpt:\n{schema_excerpt}\n\n"
            f"Retrieved context:\n{context_excerpt}\n\n"
            f"SQL result rows:\n{json.dumps(rows, ensure_ascii=False, default=str)}"
        )
        try:
            raw_response = self.groq_service.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=1200,
            )
            return extract_json_object(raw_response)
        except Exception as exc:
            if "GROQ_API_KEY" in str(exc):
                raise
            fallback_summary = f"Found {len(rows)} matching rows in the database."
            return {
                "summary": fallback_summary,
                "markdown": build_fallback_markdown(fallback_summary, rows),
            }

    def _fallback_rows(self, matches: list[tuple[ContextDocument, float]]) -> list[dict[str, Any]]:
        grouped_values: dict[str, list[Any]] = defaultdict(list)
        fallback_rows: list[dict[str, Any]] = []

        for document, _score in matches:
            if document.primary_key and document.primary_value is not None:
                grouped_values[document.table_name].append(document.primary_value)
            elif document.row_data:
                fallback_rows.append(document.row_data)

        for table_name, values in grouped_values.items():
            table = self.schema_map.get(table_name)
            if not table or not table.primary_key:
                continue
            fallback_rows.extend(self.repository.fetch_rows_by_primary_keys(table, values))

        return fallback_rows
