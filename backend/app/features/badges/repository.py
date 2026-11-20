"""
Badges repository layer.
"""
import sqlite3
import json
import datetime
import uuid
from typing import Optional, List, Dict, Any


class BadgesRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_badges(self, band: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        query = "SELECT * FROM badges WHERE 1=1"
        params = []
        if band:
            query += " AND UPPER(target_band) = UPPER(?)"
            params.append(band)
        if status:
            query += " AND workflow_status = ?"
            params.append(status)
        query += " ORDER BY target_band ASC, code ASC;"
        cur.execute(query, params)
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["learning_outcomes"] = json.loads(d.get("learning_outcomes_json") or "[]")
            d["learning_topics"] = json.loads(d.get("learning_topics_json") or "[]")
            result.append(d)
        return result

    def get_by_id(self, badge_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM badges WHERE id = ?;", (badge_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["learning_outcomes"] = json.loads(d.get("learning_outcomes_json") or "[]")
        d["learning_topics"] = json.loads(d.get("learning_topics_json") or "[]")
        return d

    def check_duplicate(self, code: str, title: str, band: str, exclude_id: str = None) -> bool:
        cur = self.conn.cursor()
        query = "SELECT COUNT(*) FROM badges WHERE UPPER(target_band) = UPPER(?) AND (LOWER(code) = LOWER(?) OR LOWER(title) = LOWER(?))"
        params = [band, code, title]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        cur.execute(query, params)
        return cur.fetchone()[0] > 0

    def create_badge(self, data: Dict[str, Any]) -> str:
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        badge_id = data.get("id") or f"badge-{uuid.uuid4().hex[:8]}"
        
        cur.execute("""
            INSERT INTO badges (
                id, code, title, category, description, learning_outcomes_json,
                learning_topics_json, project_requirements, is_published, is_allocated,
                target_band, power, capability, skill, prompt_json, workflow_status,
                creator_id, assigned_reviewer_id, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            );
        """, (
            badge_id,
            data["code"],
            data["title"],
            data["category"],
            data["description"],
            json.dumps(data.get("learning_outcomes", [])),
            json.dumps(data.get("learning_topics", [])),
            data.get("project_requirements", ""),
            1 if data.get("is_published", False) else 0,
            1 if data.get("is_allocated", False) else 0,
            data["target_band"],
            data.get("power", "Tech"),
            data.get("capability", "Data & Machine"),
            data.get("skill", "Hardware"),
            data.get("prompt_json", "{}"),
            data.get("workflow_status", "pending_review"),
            data.get("creator_id", "admin"),
            data.get("assigned_reviewer_id"),
            now_iso,
            now_iso
        ))
        return badge_id

    def update_badge(self, badge_id: str, updates: Dict[str, Any]) -> bool:
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        fields = []
        params = []
        for k, v in updates.items():
            if k == "learning_outcomes":
                fields.append("learning_outcomes_json = ?")
                params.append(json.dumps(v))
            elif k == "learning_topics":
                fields.append("learning_topics_json = ?")
                params.append(json.dumps(v))
            elif k in ("title", "description", "project_requirements", "workflow_status", "is_published", "assigned_reviewer_id"):
                fields.append(f"{k} = ?")
                params.append(v)
        if not fields:
            return False
        fields.append("updated_at = ?")
        params.append(now_iso)
        params.append(badge_id)
        
        cur.execute(f"UPDATE badges SET {', '.join(fields)} WHERE id = ?;", params)
        return cur.rowcount > 0
