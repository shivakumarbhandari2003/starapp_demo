"""Re-saving an announcement must not wipe its recipients / read receipts (INSERT OR REPLACE would cascade-delete them)."""
import unittest

from starapp.models import Announcement
from starapp.storage import store


class TestAnnouncementResave(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()

    def tearDown(self):
        store.reset_to_seed()

    def test_resave_keeps_original_read_time(self):
        ann = Announcement(id="ann_resave_1", title="T", message="M", author_id="guardian_1", author_name="G", target_type="selected",
                           badge_id="", published_at="2026-11-28T09:00:00Z", expiry_date="", target_cosmonaut_ids=["m_b1_1"])
        store.save_announcement(ann)
        store.mark_announcement_read("ann_resave_1", "m_b1_1")
        before = store.db.conn.execute("SELECT read_at FROM announcement_read_receipts WHERE announcement_id='ann_resave_1'").fetchall()
        self.assertEqual(len(before), 1)
        ann.message = "M2"
        store.save_announcement(ann)                                           # an edit / re-save
        rows = store.db.conn.execute("SELECT read_at FROM announcement_read_receipts WHERE announcement_id='ann_resave_1'").fetchall()
        self.assertEqual([tuple(r) for r in rows], [tuple(r) for r in before])
        self.assertEqual(store.db.conn.execute("SELECT COUNT(*) FROM announcement_recipients WHERE announcement_id='ann_resave_1'").fetchone()[0], 1)
        self.assertEqual(store.db.conn.execute("SELECT message FROM announcements WHERE id='ann_resave_1'").fetchone()[0], "M2")


if __name__ == "__main__":
    unittest.main()
