"""
Bands and taxonomy repository layer.
"""
import sqlite3
import datetime
import uuid
from typing import List, Dict, Any


class BandsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_bands(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM bands ORDER BY order_idx ASC;")
        return [dict(row) for row in cur.fetchall()]

    def get_custom_capabilities(self) -> List[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM custom_capabilities ORDER BY name ASC;")
        return [row[0] for row in cur.fetchall()]

    def get_custom_skills(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT name, capability_name FROM custom_skills ORDER BY name ASC;")
        return [dict(row) for row in cur.fetchall()]

    def add_custom_capability(self, name: str, user_id: str = "admin") -> bool:
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cap_id = f"cap-{uuid.uuid4().hex[:8]}"
        try:
            cur.execute("""
                INSERT INTO custom_capabilities (id, name, created_by, created_at)
                VALUES (?, ?, ?, ?);
            """, (cap_id, name.strip(), user_id, now_iso))
            return True
        except sqlite3.IntegrityError:
            return False

    def add_custom_skill(self, name: str, capability_name: str = "", user_id: str = "admin") -> bool:
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        skill_id = f"skill-{uuid.uuid4().hex[:8]}"
        cur.execute("""
            INSERT INTO custom_skills (id, name, capability_name, created_by, created_at)
            VALUES (?, ?, ?, ?, ?);
        """, (skill_id, name.strip(), capability_name.strip(), user_id, now_iso))
        return True
