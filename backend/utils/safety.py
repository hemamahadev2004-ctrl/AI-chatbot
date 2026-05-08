from __future__ import annotations

import json
import re
from typing import Any

from utils.config import settings

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|rename|replace|grant|revoke|call|execute|attach|detach|merge|set)\b",
    re.IGNORECASE,
)
PLACEHOLDER_PATTERN = re.compile(r"(?<!%)%s")


def validate_message(message: str) -> str:
    cleaned = " ".join(message.strip().split())
    if not cleaned:
        raise ValueError("Message cannot be empty.")
    return cleaned


def extract_json_object(raw_text: str) -> dict[str, Any]:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            raise ValueError("The model did not return valid JSON.")
        return json.loads(match.group(0))


def validate_sql_plan(plan: dict[str, Any], allowed_tables: set[str]) -> tuple[str, list[Any]]:
    sql = normalize_sql(str(plan.get("sql", "")))
    params = plan.get("params", [])

    if not isinstance(params, list):
        raise ValueError("SQL params must be returned as a JSON array.")

    if not sql:
        raise ValueError("Generated SQL was empty.")
    if FORBIDDEN_SQL_PATTERN.search(sql):
        raise ValueError("Generated SQL contained a forbidden operation.")
    if not sql.lower().startswith(("select ", "with ")):
        raise ValueError("Only SELECT queries are allowed.")
    if "--" in sql or "/*" in sql or "*/" in sql:
        raise ValueError("SQL comments are not allowed.")

    _validate_referenced_tables(sql, allowed_tables)

    placeholder_count = len(PLACEHOLDER_PATTERN.findall(sql))
    if placeholder_count != len(params):
        raise ValueError("SQL placeholder count does not match the provided parameters.")

    safe_sql = enforce_limit(sql, settings.max_sql_rows)
    safe_params = [sanitize_param(param) for param in params]
    return safe_sql, safe_params


def normalize_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    return re.sub(r"\s+", " ", sql)


def sanitize_param(param: Any) -> Any:
    if isinstance(param, (str, int, float, bool)) or param is None:
        return param
    return str(param)


def enforce_limit(sql: str, max_rows: int) -> str:
    if re.search(r"\blimit\b", sql, re.IGNORECASE):
        return sql
    return f"{sql} LIMIT {max_rows}"


def _validate_referenced_tables(sql: str, allowed_tables: set[str]) -> None:
    cte_names = _extract_cte_names(sql)
    referenced = _extract_table_names(sql)
    invalid_tables = {
        table_name
        for table_name in referenced
        if table_name not in allowed_tables and table_name not in cte_names
    }
    if invalid_tables:
        raise ValueError(f"Generated SQL referenced unknown tables: {', '.join(sorted(invalid_tables))}")


def _extract_cte_names(sql: str) -> set[str]:
    return {
        _strip_identifier(name)
        for name in re.findall(r"(?:with|,)\s*([`A-Za-z0-9_]+)\s+as\s*\(", sql, re.IGNORECASE)
    }


def _extract_table_names(sql: str) -> set[str]:
    names = set()
    for match in re.findall(r"\b(?:from|join)\s+([`A-Za-z0-9_.]+)", sql, re.IGNORECASE):
        names.add(_strip_identifier(match.split(".")[-1]))
    return names


def _strip_identifier(identifier: str) -> str:
    return identifier.strip().strip("`")

