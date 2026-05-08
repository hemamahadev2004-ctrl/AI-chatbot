from __future__ import annotations

from typing import Any

from db.connection import db_pool
from utils.models import ColumnInfo, ContextDocument, TableInfo


def quote_identifier(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


class MySQLRepository:
    def get_schema(self) -> list[TableInfo]:
        query = """
            SELECT
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_KEY,
                EXTRA
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
        with db_pool.connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (connection.database,))
            rows = cursor.fetchall()

        tables: dict[str, TableInfo] = {}
        for row in rows:
            table_name = row["TABLE_NAME"]
            if table_name not in tables:
                tables[table_name] = TableInfo(name=table_name)

            column = ColumnInfo(
                name=row["COLUMN_NAME"],
                data_type=row["DATA_TYPE"],
                is_nullable=row["IS_NULLABLE"] == "YES",
                column_key=row["COLUMN_KEY"] or "",
                extra=row["EXTRA"] or "",
            )
            tables[table_name].columns.append(column)
            if row["COLUMN_KEY"] == "PRI" and tables[table_name].primary_key is None:
                tables[table_name].primary_key = row["COLUMN_NAME"]

        return list(tables.values())

    def build_context_documents(
        self,
        schema: list[TableInfo],
        max_rows_per_table: int,
    ) -> list[ContextDocument]:
        documents: list[ContextDocument] = []

        for table in schema:
            documents.append(
                ContextDocument(
                    document_id=f"schema::{table.name}",
                    table_name=table.name,
                    kind="schema",
                    text=self._table_to_text(table),
                )
            )

            rows = self.fetch_rows_for_index(table, max_rows_per_table)
            for index, row in enumerate(rows, start=1):
                primary_value = row.get(table.primary_key) if table.primary_key else None
                documents.append(
                    ContextDocument(
                        document_id=f"row::{table.name}::{index}",
                        table_name=table.name,
                        kind="row",
                        text=self._row_to_text(table, row),
                        primary_key=table.primary_key,
                        primary_value=primary_value,
                        row_data=row,
                    )
                )

        return documents

    def fetch_rows_for_index(self, table: TableInfo, limit: int) -> list[dict[str, Any]]:
        columns_sql = ", ".join(quote_identifier(column.name) for column in table.columns)
        query = f"SELECT {columns_sql} FROM {quote_identifier(table.name)} LIMIT %s"
        with db_pool.connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (limit,))
            return cursor.fetchall()

    def fetch_rows_by_primary_keys(self, table: TableInfo, primary_values: list[Any]) -> list[dict[str, Any]]:
        if not primary_values or not table.primary_key:
            return []

        unique_values = list(dict.fromkeys(primary_values))
        placeholders = ", ".join(["%s"] * len(unique_values))
        columns_sql = ", ".join(quote_identifier(column.name) for column in table.columns)
        query = (
            f"SELECT {columns_sql} FROM {quote_identifier(table.name)} "
            f"WHERE {quote_identifier(table.primary_key)} IN ({placeholders})"
        )
        with db_pool.connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(unique_values))
            return cursor.fetchall()

    def execute_safe_query(self, query: str, params: list[Any]) -> list[dict[str, Any]]:
        with db_pool.connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    def _table_to_text(self, table: TableInfo) -> str:
        column_text = ", ".join(
            f"{column.name} ({column.data_type}{' primary key' if column.column_key == 'PRI' else ''})"
            for column in table.columns
        )
        return f"Table {table.name}: {column_text}"

    def _row_to_text(self, table: TableInfo, row: dict[str, Any]) -> str:
        values = ", ".join(f"{key}={value}" for key, value in row.items())
        return f"Row from {table.name}: {values}"

