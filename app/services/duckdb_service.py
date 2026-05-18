"""DuckDB SQL execution service."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from app.config import SQL_DIR


class DuckDBService:
    """Small wrapper that loads versioned SQL files and executes them in DuckDB."""

    def __init__(self, sql_dir: Path | None = None) -> None:
        self.sql_dir = sql_dir or SQL_DIR
        self.connection = duckdb.connect(database=":memory:")

    def __enter__(self) -> "DuckDBService":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def register(self, table_name: str, df: pd.DataFrame) -> None:
        self.connection.register(table_name, df)

    def load_sql(self, filename: str) -> str:
        path = self.sql_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"SQL file not found: {path}")
        return path.read_text(encoding="utf-8")

    def run_sql_file(self, filename: str, tables: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
        if tables:
            for table_name, df in tables.items():
                self.register(table_name, df)
        sql = self.load_sql(filename)
        return self.connection.execute(sql).df()

    def run_query(self, query: str, tables: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
        if tables:
            for table_name, df in tables.items():
                self.register(table_name, df)
        return self.connection.execute(query).df()

