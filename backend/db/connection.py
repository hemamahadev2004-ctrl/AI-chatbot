from __future__ import annotations

from contextlib import contextmanager

import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool

from utils.config import settings


class DatabasePool:
    def __init__(self) -> None:
        self._pool: MySQLConnectionPool | None = None

    def _create_pool(self) -> MySQLConnectionPool:
        return MySQLConnectionPool(
            pool_name="ai_database_chatbot_pool",
            pool_size=5,
            **settings.mysql_config,
        )

    @property
    def pool(self) -> MySQLConnectionPool:
        if self._pool is None:
            self._pool = self._create_pool()
        return self._pool

    @contextmanager
    def connection(self):
        connection = self.pool.get_connection()
        try:
            yield connection
        finally:
            connection.close()


db_pool = DatabasePool()

