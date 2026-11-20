"""
SQLite3 persistent database connection manager.
Enforces WAL mode, foreign key constraints, and safe transactional boundaries.
"""
import sqlite3
import logging
from contextlib import contextmanager
from typing import Generator
from pathlib import Path
from backend.app.core.config import DATABASE_PATH

logger = logging.getLogger("starapp.database")


def get_connection(db_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Create and configure a connection to the persistent SQLite database."""
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(
        str(db_path),
        timeout=10.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    # Configure SQLite pragmas for durability and performance
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for obtaining a database connection with auto-commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}", exc_info=True)
        raise
    finally:
        conn.close()


def check_database_integrity() -> dict:
    """Run integrity and foreign key checks on the persistent database."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        integrity = cur.fetchone()[0]
        cur.execute("PRAGMA foreign_key_check;")
        fk_violations = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        table_count = cur.fetchone()[0]
        return {
            "integrity": integrity,
            "foreign_key_violations": len(fk_violations),
            "table_count": table_count,
            "status": "healthy" if integrity == "ok" and len(fk_violations) == 0 else "degraded",
        }
