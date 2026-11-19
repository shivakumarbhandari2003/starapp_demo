"""
STARAPP BASE REPOSITORY
Provides reusable SQLite connection handling, row mapping, and transaction helpers.
"""

from typing import Any, List, Dict, Optional, Tuple

class BaseRepository:
    def __init__(self, db_manager: Any):
        self.db = db_manager

    @property
    def conn(self) -> Any:
        return self.db.conn

    def execute(self, sql: str, params: Tuple = ()) -> Any:
        """Executes a parameterized SQL query with automatic foreign key guarantees."""
        if not self.conn:
            return None
        return self.conn.execute(sql, params)

    def fetchone(self, sql: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetches a single row converted into a Python dict."""
        if not self.conn:
            return None
        cur = self.conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetches all matching rows converted into a list of Python dicts."""
        if not self.conn:
            return []
        cur = self.conn.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def execute_in_transaction(self, operations: List[Tuple[str, Tuple]]):
        """Executes a series of statements inside a single atomic transaction block."""
        if not self.conn:
            return
        with self.conn:
            for sql, params in operations:
                self.conn.execute(sql, params)
