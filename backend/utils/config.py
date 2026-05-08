from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")

    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "")

    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))

    cors_origins: list[str] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    )

    vector_top_k: int = int(os.getenv("VECTOR_TOP_K", "8"))
    max_index_rows_per_table: int = int(os.getenv("MAX_INDEX_ROWS_PER_TABLE", "200"))
    max_sql_rows: int = int(os.getenv("MAX_SQL_ROWS", "200"))
    index_refresh_minutes: int = int(os.getenv("INDEX_REFRESH_MINUTES", "15"))

    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    groq_model: str = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile"
    )

    history_file: Path = ROOT_DIR / "backend" / "data" / "chat_history.json"
    frontend_dir: Path = ROOT_DIR / "frontend"

    @property
    def mysql_config(self) -> dict:
        return {
            "host": self.mysql_host,
            "port": self.mysql_port,
            "user": self.mysql_user,
            "password": self.mysql_password,
            "database": self.mysql_database,
        }


settings = Settings()
