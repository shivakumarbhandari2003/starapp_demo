"""
STARAPP ANNOUNCEMENT & NOTIFICATION REPOSITORY
Encapsulates all SQLite queries for Announcements, Broadcasts, and Activity Receipts.
"""

from typing import List, Optional
from starapp.repositories.base import BaseRepository
from starapp.models import Announcement, ActivityEvent, Notification, current_iso_timestamp

class AnnouncementRepository(BaseRepository):
    def get_all(self) -> List[Announcement]:
        rows = self.fetchall("SELECT * FROM announcements ORDER BY date DESC")
        return [Announcement.from_dict(r) for r in rows]

    def get_by_id(self, ann_id: str) -> Optional[Announcement]:
        row = self.fetchone("SELECT * FROM announcements WHERE id = ?", (ann_id,))
        if not row:
            return None
        return Announcement.from_dict(row)

    def save(self, ann: Announcement):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO announcements (
                    id, title, message, date, target_role, sender_id, sender_name, is_pinned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ann.id,
                    ann.title,
                    ann.message,
                    ann.date,
                    ann.target_role,
                    ann.sender_id,
                    ann.sender_name,
                    1 if getattr(ann, "is_pinned", False) else 0
                )
            )

    def mark_as_read(self, announcement_id: str, user_id: str):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO announcement_read_receipts (announcement_id, user_id, read_at)
                VALUES (?, ?, ?)
                """,
                (announcement_id, user_id, current_iso_timestamp())
            )

    def get_notifications_for_user(self, user_id: str) -> List[Notification]:
        rows = self.fetchall("SELECT * FROM notifications WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        return [Notification.from_dict(r) for r in rows]

    def add_notification(self, notif: Notification):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO notifications (
                    id, user_id, title, message, notif_type, timestamp, is_read, link_action
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notif.id,
                    notif.user_id,
                    notif.title,
                    notif.message,
                    notif.type,
                    notif.timestamp,
                    1 if notif.is_read else 0,
                    getattr(notif, "link_action", "")
                )
            )
