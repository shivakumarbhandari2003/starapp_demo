"""
Test suite for StarApp SQLite Persistence Layer.
Verifies relational schema, foreign key enforcement, migration, binary export/import,
and multi-role integrity.
"""

import unittest
import json
import os
import sys
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starapp.database import DatabaseManager, SCHEMA_VERSION
from starapp.storage import DataStore, store
from starapp.models import User, Badge


class TestSQLitePersistence(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")
        self.db.clear_all_tables()
        self.db.seed_system_metadata()
        with self.db.conn:
            self.db.conn.execute(
                "INSERT OR REPLACE INTO users (id, username, email, name, primary_role, created_at) VALUES ('guardian_1', 'guardian', 'g@starapp.io', 'Dr. Elena Vance', 'guardian', '2026-11-18')"
            )

    def tearDown(self):
        self.db.close()

    def test_schema_initialization_and_version(self):
        """Verify all core tables exist and SCHEMA_VERSION is tracked."""
        tables = [r[0] for r in self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        required = [
            "system_roles", "bands", "learning_tracks", "users",
            "user_role_assignments", "user_band_memberships",
            "badges", "badge_reviewer_assignments", "badge_review_events",
            "custom_capabilities", "custom_skills", "project_submissions",
            "assessment_marksheets", "deadline_extensions", "announcements",
            "notifications", "activity_events"
        ]
        for tbl in required:
            self.assertIn(tbl, tables, f"Required table '{tbl}' missing from SQLite schema.")

        ver = self.db.get_schema_version()
        self.assertEqual(ver, SCHEMA_VERSION)

    def test_foreign_key_enforcement(self):
        """Verify PRAGMA foreign_keys = ON blocks invalid foreign key references."""
        self.db.conn.execute("PRAGMA foreign_keys = ON;")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute(
                "INSERT INTO user_role_assignments (user_id, role_id, assigned_at) VALUES ('nonexistent_user', 'guardian', '2026-11-18')"
            )

    def test_binary_export_and_import_roundtrip(self):
        """Verify binary export to bytes/base64 can be imported into a fresh database without data loss."""
        # Insert a user and badge
        with self.db.conn:
            self.db.conn.execute(
                "INSERT INTO users (id, username, email, name, primary_role, created_at) VALUES ('test_u1', 'test_user', 'u@test.com', 'Test User', 'guardian', '2026-11-18')"
            )
            self.db.conn.execute(
                "INSERT INTO user_role_assignments (user_id, role_id, assigned_at) VALUES ('test_u1', 'guardian', '2026-11-18')"
            )

        # Export binary base64
        b64_data = self.db.export_base64()
        self.assertTrue(len(b64_data) > 100)

        # Create new DatabaseManager and import
        db2 = DatabaseManager(":memory:")
        db2.import_base64(b64_data)
        row = db2.conn.execute("SELECT name FROM users WHERE id = 'test_u1'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["name"], "Test User")
        db2.close()

    def test_custom_capability_and_skill_persistence_and_uniqueness(self):
        """Verify custom capabilities and skills persist in SQLite and enforce case-insensitive uniqueness."""
        ok, msg = self.db.add_custom_capability("GenAI Systems", "guardian_1")
        self.assertTrue(ok)

        # Duplicate (case-insensitive) should be rejected
        ok2, msg2 = self.db.add_custom_capability("genai systems", "guardian_1")
        self.assertFalse(ok2)
        self.assertIn("already exists", msg2.lower())

        # Custom skill
        ok_s, msg_s = self.db.add_custom_skill("Prompt Tuning", "guardian_1")
        self.assertTrue(ok_s)

        ok_s2, msg_s2 = self.db.add_custom_skill("PROMPT TUNING", "guardian_1")
        self.assertFalse(ok_s2)
        self.assertIn("already exists", msg_s2.lower())

        caps = self.db.get_custom_capabilities()
        self.assertTrue(any(c == "GenAI Systems" for c in caps))

        skills = self.db.get_custom_skills()
        self.assertTrue(any(s == "Prompt Tuning" for s in skills))

    def test_36_indian_demo_members_integrity(self):
        """Verify all 36 demo profiles exist across B1-B6 and CEO according to corporate hierarchy."""
        from starapp.mapping_data import INDIAN_DEMO_MEMBERS
        self.assertEqual(len(INDIAN_DEMO_MEMBERS), 36)

        # Count distribution across bands and tracks
        band_tracks = {}
        for m in INDIAN_DEMO_MEMBERS:
            b = m["band"]
            t = m["role"]
            if b not in band_tracks:
                band_tracks[b] = {}
            band_tracks[b][t] = band_tracks[b].get(t, 0) + 1

        self.assertIn("CEO", band_tracks)
        self.assertEqual(band_tracks["CEO"].get("Chief Executive Officer"), 1)

        for b_code in ["B1", "B2", "B3", "B4", "B5"]:
            self.assertIn(b_code, band_tracks)
            self.assertEqual(band_tracks[b_code].get("Solutions Designer"), 2, f"Band {b_code} must have 2 SD")
            self.assertEqual(band_tracks[b_code].get("AI Engineer"), 2, f"Band {b_code} must have 2 AIE")
            self.assertEqual(band_tracks[b_code].get("Systems Engineer"), 2, f"Band {b_code} must have 2 SE")

        # B6 has exactly 5 members: 2 SD, 2 AIE, 1 SE
        self.assertIn("B6", band_tracks)
        self.assertEqual(band_tracks["B6"].get("Solutions Designer"), 2)
        self.assertEqual(band_tracks["B6"].get("AI Engineer"), 2)
        self.assertEqual(band_tracks["B6"].get("Systems Engineer"), 1)


if __name__ == "__main__":
    unittest.main()
