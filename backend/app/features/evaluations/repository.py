"""
Evaluations repository layer.
"""
import sqlite3
import datetime
import uuid
from typing import Optional, List, Dict, Any


class EvaluationsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_submission_by_id(self, submission_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM project_submissions WHERE id = ?;", (submission_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def record_evaluation(self, data: Dict[str, Any]) -> str:
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        eval_id = f"eval-{uuid.uuid4().hex[:8]}"

        total = (
            data["business_understanding"] +
            data["architecture_report"] +
            data["technical_knowledge"] +
            data["presentation"] +
            data["qa"]
        )
        pct = (total / 50.0) * 100.0

        cur.execute("""
            INSERT INTO assessment_marksheets (
                id, submission_id, attempt_number, badge_id, cosmonaut_id,
                reviewer_id, reviewer_name, reviewed_at, decision,
                business_understanding, architecture_report, technical_knowledge,
                presentation, qa, total_marks, percentage,
                strength_areas, improvement_areas, overall_feedback
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            );
        """, (
            eval_id,
            data["submission_id"],
            data["attempt_number"],
            data["badge_id"],
            data["cosmonaut_id"],
            data["reviewer_id"],
            data["reviewer_name"],
            now_iso,
            data["decision"],
            data["business_understanding"],
            data["architecture_report"],
            data["technical_knowledge"],
            data["presentation"],
            data["qa"],
            total,
            pct,
            data.get("strength_areas", ""),
            data.get("improvement_areas", ""),
            data.get("overall_feedback", "")
        ))

        # Update submission status
        sub_status = "approved" if data["decision"] == "approved" else "resubmission_requested"
        cur.execute("UPDATE project_submissions SET status = ? WHERE id = ?;", (sub_status, data["submission_id"]))

        # If approved, update badge timeline actual award date
        if data["decision"] == "approved":
            cur.execute("""
                UPDATE badge_timelines
                SET actual_award_date = ?, status = 'completed'
                WHERE badge_id = ? AND cosmonaut_id = ?;
            """, (now_iso, data["badge_id"], data["cosmonaut_id"]))

        return eval_id

    def get_marksheets_for_cosmonaut(self, cosmonaut_id: str, badge_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        query = """
            SELECT m.*, b.code AS badge_code, b.title AS badge_title, b.target_band
            FROM assessment_marksheets m
            JOIN badges b ON m.badge_id = b.id
            WHERE m.cosmonaut_id = ?
        """
        params = [cosmonaut_id]
        if badge_id:
            query += " AND m.badge_id = ?"
            params.append(badge_id)
        query += " ORDER BY m.reviewed_at DESC;"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT u.id, u.name, u.email, u.band, u.role, u.learning_track,
                   COUNT(m.id) AS badges_evaluated,
                   SUM(CASE WHEN m.decision = 'approved' THEN 1 ELSE 0 END) AS badges_earned,
                   COALESCE(SUM(m.total_marks), 0.0) AS aggregate_score,
                   COALESCE(AVG(m.percentage), 0.0) AS average_percentage
            FROM users u
            LEFT JOIN assessment_marksheets m ON u.id = m.cosmonaut_id
            WHERE u.status = 'active'
            GROUP BY u.id
            ORDER BY badges_earned DESC, aggregate_score DESC, u.name ASC;
        """)
        return [dict(row) for row in cur.fetchall()]
