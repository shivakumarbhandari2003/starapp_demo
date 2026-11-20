"""
Users repository layer.
"""
import sqlite3
from typing import Optional, List, Dict, Any


class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_users(self, band: Optional[str] = None, track: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        query = "SELECT * FROM users WHERE status = 'active'"
        params = []
        if band:
            query += " AND band = ?"
            params.append(band.upper())
        if track:
            query += " AND (learning_track = ? OR track_code = ?)"
            params.extend([track, track])
        query += " ORDER BY band ASC, name ASC;"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        norm = user_id.replace("_", ".")
        cur.execute("""
            SELECT * FROM users
            WHERE id = ? OR LOWER(username) = LOWER(?) OR LOWER(username) = LOWER(?) OR LOWER(name) = LOWER(?);
        """, (user_id, user_id, norm, user_id))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_eligible_reviewers(self, higher_than_band_val: int) -> List[Dict[str, Any]]:
        band_map = {"B1": 1, "B2": 2, "B3": 3, "B4": 4, "B5": 5, "B6": 6}
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE status = 'active' ORDER BY band ASC, name ASC;")
        eligible = []
        for row in cur.fetchall():
            u = dict(row)
            b = u.get("band", "B1").upper()
            if band_map.get(b, 0) > higher_than_band_val:
                eligible.append(u)
        return eligible

    def get_hierarchy_tree(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, name, band, role, learning_track, reporting_manager_id, reporting_manager_name, reporting_manager_band
            FROM users
            ORDER BY band DESC, name ASC;
        """)
        return [dict(row) for row in cur.fetchall()]
