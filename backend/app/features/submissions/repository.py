"""
Submissions repository layer.
"""
import sqlite3
import datetime
import uuid
from typing import Optional, List, Dict, Any


class SubmissionsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_latest_attempt_number(self, badge_id: str, cosmonaut_id: str) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT MAX(attempt_number) FROM project_submissions
            WHERE badge_id = ? AND cosmonaut_id = ?;
        """, (badge_id, cosmonaut_id))
        row = cur.fetchone()
        return (row[0] or 0)

    def create_submission(self, data: Dict[str, Any]) -> Dict[str, Any]:
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        sub_id = f"sub-{uuid.uuid4().hex[:8]}"
        attempt = self.get_latest_attempt_number(data["badge_id"], data["cosmonaut_id"]) + 1

        cur.execute("""
            INSERT INTO project_submissions (
                id, badge_id, cosmonaut_id, attempt_number, submission_type,
                payload, file_name, submitted_at, status, pdf_name, pdf_payload,
                code_name, code_payload, github_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?);
        """, (
            sub_id,
            data["badge_id"],
            data["cosmonaut_id"],
            attempt,
            data.get("submission_type", "github"),
            data.get("payload", ""),
            data.get("file_name", "submission.txt"),
            now_iso,
            data.get("pdf_name", ""),
            data.get("pdf_payload", ""),
            data.get("code_name", ""),
            data.get("code_payload", ""),
            data.get("github_url", "")
        ))

        return {
            "id": sub_id,
            "badge_id": data["badge_id"],
            "cosmonaut_id": data["cosmonaut_id"],
            "attempt_number": attempt,
            "status": "pending",
            "submitted_at": now_iso
        }

    def get_submission_history(self, badge_id: str, cosmonaut_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT s.*, m.total_marks, m.decision AS marksheet_decision, m.reviewed_at
            FROM project_submissions s
            LEFT JOIN assessment_marksheets m ON s.id = m.submission_id
            WHERE s.badge_id = ? AND s.cosmonaut_id = ?
            ORDER BY s.attempt_number ASC;
        """, (badge_id, cosmonaut_id))
        return [dict(row) for row in cur.fetchall()]

    def get_pending_submissions(self, reviewer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        if not reviewer_id:
            cur.execute("""
                SELECT s.*, b.code AS badge_code, b.title AS badge_title, b.target_band,
                       u.name AS cosmonaut_name, u.band AS cosmonaut_band, u.email AS cosmonaut_email
                FROM project_submissions s
                JOIN badges b ON s.badge_id = b.id
                JOIN users u ON s.cosmonaut_id = u.id
                WHERE s.status = 'pending'
                ORDER BY s.submitted_at ASC;
            """)
            return [dict(row) for row in cur.fetchall()]

        # Filter strictly to submissions assigned to reviewer_id
        cur.execute("""
            SELECT s.*, b.code AS badge_code, b.title AS badge_title, b.target_band,
                   u.name AS cosmonaut_name, u.band AS cosmonaut_band, u.email AS cosmonaut_email
            FROM project_submissions s
            JOIN badges b ON s.badge_id = b.id
            JOIN users u ON s.cosmonaut_id = u.id
            WHERE s.status = 'pending'
            ORDER BY s.submitted_at ASC;
        """)
        all_pending = [dict(row) for row in cur.fetchall()]
        assigned = []
        for s in all_pending:
            # 1. Check badge_timelines
            cur.execute(
                "SELECT reviewer_id FROM badge_timelines WHERE badge_id = ? AND cosmonaut_id = ?;",
                (s["badge_id"], s["cosmonaut_id"])
            )
            tl_row = cur.fetchone()
            if tl_row and tl_row[0] == reviewer_id:
                assigned.append(s)
                continue

            # 2. Check band_mappings
            cur.execute(
                "SELECT data_json FROM band_mappings WHERE badge_id = ? OR badge_id = '' OR badge_id IS NULL;",
                (s["badge_id"],)
            )
            is_mapped = False
            for bm_row in cur.fetchall():
                try:
                    import json
                    bm = json.loads(bm_row[0])
                    if reviewer_id in bm.get("reviewers", []) and s["cosmonaut_id"] in bm.get("cosmonauts", []):
                        m_b = bm.get("badge_id") or bm.get("badge")
                        if not m_b or m_b in (s["badge_id"], s["badge_code"], s["badge_title"]):
                            is_mapped = True
                            break
                except Exception:
                    pass
            if is_mapped:
                assigned.append(s)

        return assigned
