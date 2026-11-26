"""
Authentication repository layer.
"""
import sqlite3
import datetime
from typing import Optional, Dict, Any, List


class AuthRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def find_user_by_username_or_email(self, identifier: str) -> Optional[Dict[str, Any]]:
        import re
        cur = self.conn.cursor()
        ident = (identifier or "").strip().lower()
        cur.execute("""
            SELECT * FROM users
            WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?);
        """, (ident, ident))
        row = cur.fetchone()
        if not row:
            alias_match = re.match(r"^([a-z0-9._-]+)\.b[1-6]@([a-z0-9.-]+\.[a-z]{2,})$", ident)
            if alias_match:
                canonical_email = f"{alias_match.group(1)}@{alias_match.group(2)}"
                cur.execute("""
                    SELECT * FROM users
                    WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?);
                """, (canonical_email, alias_match.group(1)))
                row = cur.fetchone()
        return dict(row) if row else None

    def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_user_role_ids(self, user_id: str) -> List[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT role_id FROM user_role_assignments WHERE user_id = ?;", (user_id,))
        return [r[0] for r in cur.fetchall()]

    def create_session(self, session_id: str, user_id: str, role: str, expires_at: str, ip: str = None, ua: str = None):
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur.execute("""
            INSERT INTO user_sessions (id, user_id, role, created_at, expires_at, last_active_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (session_id, user_id, role, now_iso, expires_at, now_iso, ip, ua))

    def delete_session(self, session_id: str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM user_sessions WHERE id = ?;", (session_id,))

    def update_session_role(self, session_id: str, new_role: str):
        cur = self.conn.cursor()
        cur.execute("UPDATE user_sessions SET role = ? WHERE id = ?;", (new_role, session_id))

    def get_demo_users(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, name, username, email, band, role, learning_track, primary_role
            FROM users
            ORDER BY band ASC, name ASC;
        """)
        return [dict(row) for row in cur.fetchall()]
