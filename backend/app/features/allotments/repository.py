"""
Allotments and roadmap repository layer.
"""
import sqlite3
import datetime
import uuid
import json
from typing import Optional, List, Dict, Any


class AllotmentsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def allot_badge_to_cosmonauts(self, badge_id: str, cosmonaut_ids: List[str], timeline: Dict[str, str] = None) -> int:
        cur = self.conn.cursor()
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now_dt.isoformat()
        count = 0
        
        # Default milestones
        t_learning_start = timeline.get("learning_start_date") if timeline else (now_dt + datetime.timedelta(days=1)).isoformat()
        t_learning_end = timeline.get("learning_end_date") if timeline else (now_dt + datetime.timedelta(days=7)).isoformat()
        t_project_start = timeline.get("project_start_date") if timeline else (now_dt + datetime.timedelta(days=8)).isoformat()
        t_project_end = timeline.get("project_end_date") if timeline else (now_dt + datetime.timedelta(days=21)).isoformat()
        t_deadline = timeline.get("submission_deadline") if timeline else (now_dt + datetime.timedelta(days=28)).isoformat()
        t_expected_award = timeline.get("expected_award_date") if timeline else (now_dt + datetime.timedelta(days=35)).isoformat()

        for cid in cosmonaut_ids:
            cur.execute("""
                INSERT INTO badge_timelines (
                    badge_id, cosmonaut_id, assignment_date, publication_date,
                    learning_start_date, learning_end_date, project_start_date, project_end_date,
                    submission_deadline, expected_award_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
                ON CONFLICT(badge_id, cosmonaut_id) DO UPDATE SET
                    assignment_date = excluded.assignment_date,
                    submission_deadline = excluded.submission_deadline;
            """, (badge_id, cid, now_iso, now_iso, t_learning_start, t_learning_end, t_project_start, t_project_end, t_deadline, t_expected_award))
            count += 1
            
        return count

    def get_cosmonaut_roadmap(self, cosmonaut_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        # Find user's band
        cur.execute("SELECT band FROM users WHERE id = ?;", (cosmonaut_id,))
        user_row = cur.fetchone()
        band = user_row[0] if user_row else "B1"

        # Return badges in user's band or allotted
        cur.execute("""
            SELECT b.id, b.code, b.title, b.category, b.description, b.target_band, b.power, b.capability, b.skill,
                   b.workflow_status, b.is_published,
                   t.assignment_date, t.submission_deadline, t.status AS timeline_status,
                   (SELECT COUNT(*) FROM project_submissions s WHERE s.badge_id = b.id AND s.cosmonaut_id = ?) AS submission_count,
                   (SELECT decision FROM assessment_marksheets m WHERE m.badge_id = b.id AND m.cosmonaut_id = ? ORDER BY reviewed_at DESC LIMIT 1) AS latest_decision
            FROM badges b
            LEFT JOIN badge_timelines t ON b.id = t.badge_id AND t.cosmonaut_id = ?
            WHERE UPPER(b.target_band) = UPPER(?) OR t.cosmonaut_id IS NOT NULL
            ORDER BY b.code ASC;
        """, (cosmonaut_id, cosmonaut_id, cosmonaut_id, band))
        return [dict(row) for row in cur.fetchall()]

    def get_allotments_for_guardian(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT t.badge_id, t.cosmonaut_id, t.assignment_date, t.submission_deadline, t.status,
                   b.code AS badge_code, b.title AS badge_title, b.target_band,
                   u.name AS cosmonaut_name, u.email AS cosmonaut_email, u.band AS cosmonaut_band
            FROM badge_timelines t
            JOIN badges b ON t.badge_id = b.id
            JOIN users u ON t.cosmonaut_id = u.id
            ORDER BY t.assignment_date DESC;
        """)
        return [dict(row) for row in cur.fetchall()]

    def create_extension_request(self, badge_id: str, cosmonaut_id: str, proposed_deadline: str, reason: str) -> str:
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ext_id = f"ext-{uuid.uuid4().hex[:8]}"

        # Lookup current deadline
        cur.execute("SELECT submission_deadline FROM badge_timelines WHERE badge_id = ? AND cosmonaut_id = ?;", (badge_id, cosmonaut_id))
        row = cur.fetchone()
        current_deadline = row[0] if row and row[0] else now_iso

        cur.execute("""
            INSERT INTO deadline_extensions (
                id, badge_id, cosmonaut_id, current_deadline, proposed_deadline,
                reason, status, requested_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?);
        """, (ext_id, badge_id, cosmonaut_id, current_deadline, proposed_deadline, reason, now_iso))
        return ext_id

    def list_extensions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        query = """
            SELECT e.*, b.code AS badge_code, b.title AS badge_title, u.name AS cosmonaut_name, u.band AS cosmonaut_band
            FROM deadline_extensions e
            JOIN badges b ON e.badge_id = b.id
            JOIN users u ON e.cosmonaut_id = u.id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND e.status = ?"
            params.append(status)
        query += " ORDER BY e.requested_at DESC;"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    def decide_extension(self, extension_id: str, status: str, notes: str) -> bool:
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur.execute("SELECT badge_id, cosmonaut_id, proposed_deadline FROM deadline_extensions WHERE id = ?;", (extension_id,))
        row = cur.fetchone()
        if not row:
            return False

        badge_id, cosmonaut_id, proposed_deadline = row[0], row[1], row[2]

        cur.execute("""
            UPDATE deadline_extensions
            SET status = ?, guardian_response = ?, decided_at = ?
            WHERE id = ?;
        """, (status, notes, now_iso, extension_id))

        if status == "approved":
            # Update the actual timeline deadline
            cur.execute("""
                UPDATE badge_timelines
                SET submission_deadline = ?
                WHERE badge_id = ? AND cosmonaut_id = ?;
            """, (proposed_deadline, badge_id, cosmonaut_id))

        return True
