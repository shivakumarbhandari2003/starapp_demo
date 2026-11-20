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
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM users
            WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?);
        """, (identifier, identifier))
        row = cur.fetchone()
        return dict(row) if row else None

    def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

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
