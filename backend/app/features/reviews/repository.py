"""
Reviews repository layer.
"""
import sqlite3
import datetime
import uuid
from typing import Optional, List, Dict, Any


class ReviewsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_assignment(self, badge_id: str, reviewer_id: str, notes: str = "") -> str:
        cur = self.conn.cursor()
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now_dt.isoformat()
        due_iso = (now_dt + datetime.timedelta(days=7)).isoformat()
        assign_id = f"asn-{uuid.uuid4().hex[:8]}"

        # Insert assignment
        cur.execute("""
            INSERT INTO badge_reviewer_assignments (id, badge_id, reviewer_id, assigned_at, review_due_at, status, decision_notes)
            VALUES (?, ?, ?, ?, ?, 'pending', ?);
        """, (assign_id, badge_id, reviewer_id, now_iso, due_iso, notes))

        # Log event
        event_id = f"evt-{uuid.uuid4().hex[:8]}"
        cur.execute("""
            INSERT INTO badge_review_events (id, badge_id, actor_id, event_type, previous_status, new_status, notes, timestamp)
            VALUES (?, ?, ?, 'created_and_submitted', 'draft', 'pending_review', ?, ?);
        """, (event_id, badge_id, reviewer_id, notes, now_iso))

        # Update badge assigned reviewer and status
        cur.execute("""
            UPDATE badges
            SET assigned_reviewer_id = ?, workflow_status = 'pending_review', updated_at = ?
            WHERE id = ?;
        """, (reviewer_id, now_iso, badge_id))

        return assign_id

    def get_reviewer_inbox(self, reviewer_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT a.id AS assignment_id, a.assigned_at, a.review_due_at, a.status AS assignment_status,
                   b.id AS badge_id, b.code, b.title, b.target_band, b.power, b.capability, b.skill,
                   b.description, b.learning_outcomes_json, b.learning_topics_json, b.workflow_status
            FROM badge_reviewer_assignments a
            JOIN badges b ON a.badge_id = b.id
            WHERE a.reviewer_id = ?
            ORDER BY a.assigned_at DESC;
        """, (reviewer_id,))
        return [dict(row) for row in cur.fetchall()]

    def record_decision(self, badge_id: str, reviewer_id: str, decision: str, notes: str) -> bool:
        cur = self.conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        new_badge_status = "approved" if decision == "approved" else "returned"
        is_published = 1 if decision == "approved" else 0

        # Update assignment
        cur.execute("""
            UPDATE badge_reviewer_assignments
            SET status = ?, decision_notes = ?, decided_at = ?
            WHERE badge_id = ? AND reviewer_id = ?;
        """, (new_badge_status, notes, now_iso, badge_id, reviewer_id))

        # Update badge
        cur.execute("""
            UPDATE badges
            SET workflow_status = ?, is_published = ?, updated_at = ?
            WHERE id = ?;
        """, (new_badge_status, is_published, now_iso, badge_id))

        # Log event
        event_id = f"evt-{uuid.uuid4().hex[:8]}"
        cur.execute("""
            INSERT INTO badge_review_events (id, badge_id, actor_id, event_type, previous_status, new_status, notes, timestamp)
            VALUES (?, ?, ?, ?, 'pending_review', ?, ?, ?);
        """, (event_id, badge_id, reviewer_id, decision, new_badge_status, notes, now_iso))

        return True

    def get_review_requests_for_guardian(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT a.id AS assignment_id, a.assigned_at, a.status AS assignment_status, a.decided_at, a.decision_notes,
                   b.id AS badge_id, b.code, b.title, b.target_band, b.workflow_status,
                   u.name AS reviewer_name, u.band AS reviewer_band, u.email AS reviewer_email
            FROM badge_reviewer_assignments a
            JOIN badges b ON a.badge_id = b.id
            JOIN users u ON a.reviewer_id = u.id
            ORDER BY a.assigned_at DESC;
        """)
        return [dict(row) for row in cur.fetchall()]
