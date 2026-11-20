"""
Database migration management and schema initialization for StarApp persistent backend.
"""
import sqlite3
import datetime
import logging
from backend.app.database.connection import get_db_connection
from backend.app.core.security import hash_password

logger = logging.getLogger("starapp.migrations")


def apply_migrations():
    """Apply versioned schema migrations to the persistent SQLite database."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # 1. Create user_sessions table if not present
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_active_at TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);")
        
        # 2. Check if admin user exists; if not, create default admin/guardian
        cur.execute("SELECT COUNT(*) FROM users WHERE username = 'admin' OR id = 'admin';")
        if cur.fetchone()[0] == 0:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT OR IGNORE INTO users (
                    id, username, email, name, role, learning_track, track_code, band,
                    password, primary_role, status, is_demo, created_at
                ) VALUES (
                    'admin', 'admin', 'admin@starapp.io', 'Guardian Admin', 'Administrator',
                    'Leadership', 'EXEC', 'B6', ?, 'guardian', 'active', 0, ?
                );
            """, (hash_password("12345678"), now_iso))

        logger.info("Database migrations applied successfully.")


if __name__ == "__main__":
    apply_migrations()
    print("Migrations applied.")
