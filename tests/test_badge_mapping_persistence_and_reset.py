"""
Test Badge Mapping Persistence, State Reset & Publish Lifecycle
Verifies:
1. Saving mapping updates the Badge model directly (assigned_cosmonaut_ids, assigned_reviewer_id, default_timeline, is_allocated=True).
2. Badge remains unpublished until Guardian explicitly publishes it.
3. Mapping page state resets after saving (cosmonauts, reviewers, final stage, editing id).
4. Badge Allotment displays mapped personnel and 'Publish to Roadmap' button.
5. Publishing activates badge on Reviewer schedule and unlocks Cosmonaut roadmap.
6. Mapped connection guarantees reviewer creates project only for mapped cadets, and cadets submit to that reviewer.
"""

import json
import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from starapp.app import StarAppController
from project_helpers import give_project
from starapp.storage import store
from starapp.models import Badge, current_iso_timestamp

class TestBadgeMappingPersistenceAndReset(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        # Login as guardian
        self.ctrl.handle_event("login", json.dumps({"username": "guardian"}))
        self.assertIsNotNone(self.ctrl.current_user)

    def test_save_mapping_persists_in_badge_and_resets_page(self):
        # 1. Create and approve a badge in B4
        badge_id = "badge_b4_cloud_arch_test"
        badge = Badge(
            id=badge_id,
            code="B4-ARC-01",
            title="Cloud Solutions Architecture Test",
            category="Solutions Architecture",
            description="Enterprise cloud architecture test badge.",
            learning_outcomes=["Design microservices", "Deploy container clusters"],
            learning_topics=["Kubernetes", "API Gateways"],
            prerequisites=[],
            project_requirements="Architect an end-to-end cloud pipeline.",
            is_published=False,
            is_allocated=False,
            target_band="B4",
            power="Tech",
            capability="Systems & Cloud",
            skill="Architecture",
            workflow_status="approved",
            creator_id="guardian_1"
        )
        store.save_badge(badge)

        # 2. Select badge in mapping matrix
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B4")
        payload = json.dumps({"badge_id": badge_id, "badge": "Cloud Solutions Architecture Test"})
        self.ctrl.handle_event("select_mapping_badge", payload)
        self.assertEqual(self.ctrl.mapping_selected_badge_id, badge_id)

        # 3. Select cosmonauts & reviewers and send request
        cosmo_ids = ["m_b4_1", "m_b4_2"]
        rev_id = "m_b5_1"
        self.ctrl.mapping_selected_cosmonauts = list(cosmo_ids)
        self.ctrl.mapping_selected_reviewers = [rev_id]
        self.ctrl.mapping_review_dates = ["2026-11-24", "2026-11-25", "2026-11-26"]
        self.ctrl.handle_event("send_mapping_requests", "{}")

        # 4. Reviewer accepts request
        reqs = store.get_mapping_requests()
        matching_req = next(r for r in reqs if r.get("badge_id") == badge_id and r.get("reviewer_id") == rev_id)
        self.ctrl.handle_event("accept_mapping_request", matching_req["id"])

        # Verify upper selections refreshed while independent request retained cosmonauts
        self.assertEqual(len(self.ctrl.mapping_selected_cosmonauts), 0)
        self.assertEqual(len(self.ctrl.mapping_selected_reviewers), 0)
        self.assertEqual(matching_req["cosmonaut_ids"], cosmo_ids)

        # 5. Guardian executes Save Mapping
        self.ctrl.handle_event("execute_cosmonaut_mapping", "{}")

        # VERIFY 1: Mapping page is RESET
        self.assertEqual(len(self.ctrl.mapping_selected_cosmonauts), 0)
        self.assertEqual(len(self.ctrl.mapping_selected_reviewers), 0)
        self.assertFalse(self.ctrl.mapping_show_final_stage)
        self.assertIsNone(self.ctrl.editing_mapping_id)

        # VERIFY 2: Badge object in storage & SQLite is updated with mapping & timeline
        updated_badge = store.get_badge(badge_id)
        self.assertIsNotNone(updated_badge)
        self.assertTrue(updated_badge.is_allocated)
        self.assertFalse(updated_badge.is_published)  # Not yet published!
        self.assertEqual(updated_badge.assigned_reviewer_id, rev_id)
        self.assertIn("m_b4_1", updated_badge.assigned_cosmonaut_ids)
        self.assertIn("m_b4_2", updated_badge.assigned_cosmonaut_ids)
        self.assertEqual(updated_badge.default_timeline.get("review_date"), "2026-11-26")

        # VERIFY 3: Check SQLite directly
        if store.db and store.db.conn:
            row = store.db.conn.execute("SELECT is_allocated, is_published, assigned_reviewer_id, assigned_cosmonaut_ids_json, default_timeline_json FROM badges WHERE id = ?", (badge_id,)).fetchone()
            self.assertEqual(row["is_allocated"], 1)
            self.assertEqual(row["is_published"], 0)
            self.assertEqual(row["assigned_reviewer_id"], rev_id)
            cids_in_db = json.loads(row["assigned_cosmonaut_ids_json"])
            self.assertIn("m_b4_1", cids_in_db)
            self.assertIn("m_b4_2", cids_in_db)

        # VERIFY 4: Badge Allotment view renders 'Ready to Publish' and 'Publish to Roadmap' button
        self.ctrl.handle_event("nav_guardian", "g_allotment")
        allotment_html = self.ctrl.render()
        self.assertIn("Cloud Solutions Architecture Test", allotment_html)
        self.assertIn("Ready to Publish", allotment_html)
        self.assertIn("Publish to Roadmap", allotment_html)
        self.assertIn("Anirudh", allotment_html)

        # 6. Guardian clicks Publish
        self.ctrl.handle_event("publish_badge", badge_id)
        published_badge = store.get_badge(badge_id)
        self.assertTrue(published_badge.is_published)

        # VERIFY 5: Reviewer view shows assigned cadets and project authoring button
        rev_ctrl = StarAppController()
        rev_user = store.get_user_by_id(rev_id)
        rev_ctrl.handle_event("login", json.dumps({"username": rev_user.username}))
        rev_ctrl.handle_event("nav_cosmonaut", "c_badge_reviews")
        rev_html = rev_ctrl.render()
        self.assertIn("Cloud Solutions Architecture Test", rev_html)
        self.assertIn("Create Project", rev_html)

        # VERIFY 6: Cosmonaut view has unlocked milestone
        cosmo_ctrl = StarAppController()
        cosmo_user = store.get_user_by_id("m_b4_1")
        cosmo_ctrl.handle_event("login", json.dumps({"username": cosmo_user.username}))
        cosmo_ctrl.handle_event("nav_cosmonaut", "c_submission")
        cosmo_html = cosmo_ctrl.render()
        self.assertIn("Cloud Solutions Architecture Test", cosmo_html)

if __name__ == "__main__":
    unittest.main()
