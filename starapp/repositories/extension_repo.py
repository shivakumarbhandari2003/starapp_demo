"""
STARAPP DEADLINE EXTENSION REPOSITORY
Encapsulates all SQLite queries for Submission Extensions and Guardian Decisions.
"""

from typing import List, Optional
from starapp.repositories.base import BaseRepository
from starapp.models import DeadlineExtension

class ExtensionRepository(BaseRepository):
    def get_all(self) -> List[DeadlineExtension]:
        rows = self.fetchall("SELECT * FROM deadline_extensions ORDER BY requested_at DESC")
        return [DeadlineExtension.from_dict(r) for r in rows]

    def get_by_id(self, ext_id: str) -> Optional[DeadlineExtension]:
        row = self.fetchone("SELECT * FROM deadline_extensions WHERE id = ?", (ext_id,))
        if not row:
            return None
        return DeadlineExtension.from_dict(row)

    def get_by_cosmonaut(self, cosmonaut_id: str) -> List[DeadlineExtension]:
        rows = self.fetchall("SELECT * FROM deadline_extensions WHERE cosmonaut_id = ? ORDER BY requested_at DESC", (cosmonaut_id,))
        return [DeadlineExtension.from_dict(r) for r in rows]

    def get_by_badge(self, badge_id: str) -> List[DeadlineExtension]:
        rows = self.fetchall("SELECT * FROM deadline_extensions WHERE badge_id = ? ORDER BY requested_at DESC", (badge_id,))
        return [DeadlineExtension.from_dict(r) for r in rows]

    def save(self, ext: DeadlineExtension):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO deadline_extensions (
                    id, badge_id, cosmonaut_id, current_deadline, proposed_deadline,
                    reason, status, guardian_response, requested_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ext.id,
                    ext.badge_id,
                    ext.cosmonaut_id,
                    ext.current_deadline,
                    ext.proposed_deadline,
                    ext.reason,
                    ext.status,
                    ext.guardian_response,
                    ext.requested_at,
                    ext.decided_at
                )
            )
