from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from utils.models import ContextDocument, TableInfo


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_session_title(message: str) -> str:
    cleaned = " ".join(message.strip().split())
    return cleaned[:42] + ("..." if len(cleaned) > 42 else "")


def format_schema_overview(schema: list[TableInfo]) -> str:
    lines: list[str] = []
    for table in schema:
        column_descriptions = ", ".join(
            f"{column.name} ({column.data_type}{' PK' if column.column_key == 'PRI' else ''})"
            for column in table.columns
        )
        lines.append(f"- {table.name}: {column_descriptions}")
    return "\n".join(lines)


def format_context_matches(matches: list[tuple[ContextDocument, float]]) -> str:
    lines: list[str] = []
    for document, score in matches:
        lines.append(f"- [{document.kind}] {document.table_name} | score={score:.4f} | {document.text}")
    return "\n".join(lines)


def to_json_safe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: _to_json_safe(value) for key, value in row.items()} for row in rows]


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return str(value)
    return value


def build_markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    headers = list(rows[0].keys())
    header_row = "| " + " | ".join(headers) + " |"
    divider_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    data_rows = [
        "| " + " | ".join(str(row.get(header, "")) for header in headers) + " |"
        for row in rows
    ]
    return "\n".join([header_row, divider_row, *data_rows])


def build_fallback_markdown(summary: str, rows: list[dict[str, Any]]) -> str:
    table = build_markdown_table(rows[:10])
    if table:
        return f"{summary}\n\n{table}"
    return summary

