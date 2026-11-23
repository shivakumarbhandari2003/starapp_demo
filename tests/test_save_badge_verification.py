import unittest
import json
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starapp.storage import store
from starapp.app import StarAppController
from starapp.models import Badge


class TestSaveBadgeVerification(unittest.TestCase):
    def setUp(self):
        self.ctrl = StarAppController()
        self.ctrl.initialize()
        user = store.get_user_by_id("admin") or store.get_user_by_id("guardian_1")
        self.ctrl.current_user = user
        self.ctrl.current_view = "g_create_badge"

    def test_guardian_save_badge_flow(self):
        # 1. Select Band B2
        self.ctrl.handle_event("select_create_badge_band", "B2")
        self.assertEqual(self.ctrl.create_badge_band, "B2")

        # 2. Simulate generated badge payload from Gemini
        badge_payload = {
            "band": "B2",
            "badge_data": {
                "title": "Curation Systems",
                "skill": "Curation",
                "capability": "Data and Machine",
                "power": "Tech",
                "target_band": "B2",
                "description": "Advanced curation pipeline engineering.",
                "outcomes": ["Can configure curation filters.", "Can maintain data lakehouse."],
                "learning_topics": [{"title": "Curation 101", "description": "Basics", "status": "In Progress", "completed": False}],
                "practice_prompt": "Build a hands-on curation pipeline.",
                "resources_prompt": "Read the official curation documentation."
            }
        }

        # 3. Save the badge
        self.ctrl.handle_event("save_generated_badge", json.dumps(badge_payload))
        self.assertEqual(self.ctrl.flash_type, "success")
        self.assertIn("saved successfully", self.ctrl.last_flash_message)

        # 4. Verify saved badge is in store.get_saved_badges("B2")
        saved_b2 = store.get_saved_badges("B2")
        self.assertTrue(any(b["skill"] == "Curation" for b in saved_b2))
        saved_curation = next(b for b in saved_b2 if b["skill"] == "Curation")
        self.assertEqual(saved_curation["title"], "Curation Systems")
        self.assertEqual(saved_curation["target_band"], "B2")

        # 5. Verify it is persisted in SQLite
        conn = sqlite3.connect("data/starapp.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM badges WHERE id = ?", (saved_curation["id"],)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Curation Systems")
        self.assertEqual(row["target_band"], "B2")
        conn.close()

        # 6. Save again (e.g. user updates or clicks Save Badge a second time)
        update_payload = {
            "band": "B2",
            "title": "Curation Systems Pro",
            "description": "Updated description"
        }
        self.ctrl.handle_event("save_generated_badge", json.dumps(update_payload))
        self.assertEqual(self.ctrl.flash_type, "success")
        self.assertIn("saved successfully", self.ctrl.last_flash_message)

        # Verify update reflected in DB
        conn = sqlite3.connect("data/starapp.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM badges WHERE id = ?", (saved_curation["id"],)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Curation Systems Pro")
        self.assertEqual(row["description"], "Updated description")
        conn.close()

        # 7. Render view and verify Saved Badges section shows the badge
        html = self.ctrl.render()
        self.assertIn("Curation Systems Pro", html)
        self.assertIn("BAND B2", html)
        self.assertIn("Saved Badges for Band B2", html)


if __name__ == "__main__":
    unittest.main()
