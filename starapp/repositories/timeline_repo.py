"""
STARAPP TIMELINE REPOSITORY
Encapsulates all SQLite queries for Badge Timelines, Milestones, and Roadmaps.
"""

from typing import List, Optional
from starapp.repositories.base import BaseRepository
from starapp.models import BadgeTimeline

class TimelineRepository(BaseRepository):
    def get_timeline(self, badge_id: str, cosmonaut_id: str) -> Optional[BadgeTimeline]:
        row = self.fetchone("SELECT * FROM badge_timelines WHERE badge_id = ? AND cosmonaut_id = ?", (badge_id, cosmonaut_id))
        if not row:
            return None
        return BadgeTimeline.from_dict(row)

    def get_timelines_by_cosmonaut(self, cosmonaut_id: str) -> List[BadgeTimeline]:
        rows = self.fetchall("SELECT * FROM badge_timelines WHERE cosmonaut_id = ?", (cosmonaut_id,))
        return [BadgeTimeline.from_dict(r) for r in rows]

    def get_timelines_by_badge(self, badge_id: str) -> List[BadgeTimeline]:
        rows = self.fetchall("SELECT * FROM badge_timelines WHERE badge_id = ?", (badge_id,))
        return [BadgeTimeline.from_dict(r) for r in rows]

    def get_all_timelines(self) -> List[BadgeTimeline]:
        rows = self.fetchall("SELECT * FROM badge_timelines")
        return [BadgeTimeline.from_dict(r) for r in rows]

    def save_timeline(self, tl: BadgeTimeline):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO badge_timelines (
                    badge_id, cosmonaut_id, assignment_date, publication_date,
                    learning_start_date, learning_end_date, project_start_date,
                    project_end_date, submission_deadline, review_date,
                    expected_award_date, actual_award_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tl.badge_id,
                    tl.cosmonaut_id,
                    tl.assignment_date,
                    tl.publication_date,
                    tl.learning_start_date,
                    tl.learning_end_date,
                    tl.project_start_date,
                    tl.project_end_date,
                    tl.submission_deadline,
                    tl.review_date,
                    tl.expected_award_date,
                    tl.actual_award_date,
                    tl.status
                )
            )
