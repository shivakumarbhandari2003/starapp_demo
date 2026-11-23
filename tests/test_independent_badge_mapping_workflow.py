import unittest
import json
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import Badge, BadgeTimeline

class TestIndependentBadgeMappingWorkflow(unittest.TestCase):
    def setUp(self):
        self.ctrl = StarAppController()
        self.ctrl.handle_event("select_demo_account", "admin")

        # Create two approved B4 badges
        b4_1 = store.get_badge("badge_b4_gov_test")
        if not b4_1:
            b4_1 = Badge(
                id="badge_b4_gov_test",
                code="B4-GOV-TEST",
                title="Governance Architecture Test",
                category="Data & Machine",
                description="B4 governance architecture testing",
                target_band="B4",
                power="Tech",
                capability="Data & Machine",
                skill="Governance",
                workflow_status="approved",
                creator_id="guardian_1",
                assigned_reviewer_id="m_b5_1",
                is_published=False,
                is_allocated=False,
                learning_outcomes=["Outcome 1"],
                learning_topics=["Topic 1"],
                prerequisites=[],
                project_requirements="Deliver governance test project",
                default_timeline={
                    "assignment_date": "2026-11-10",
                    "learning_start_date": "2026-11-10",
                    "learning_end_date": "2026-11-20",
                    "project_start_date": "2026-11-21",
                    "project_end_date": "2026-12-01",
                    "submission_deadline": "2026-12-03",
                    "review_date": "2026-12-06",
                    "expected_award_date": "2026-12-08"
                }
            )
            store.save_badge(b4_1)

        b4_2 = store.get_badge("badge_b4_cloud_test")
        if not b4_2:
            b4_2 = Badge(
                id="badge_b4_cloud_test",
                code="B4-CLD-TEST",
                title="Cloud Reliability Test",
                category="Systems & Fabric",
                description="B4 cloud reliability testing",
                target_band="B4",
                power="Tech",
                capability="Systems & Fabric",
                skill="Reliability",
                workflow_status="approved",
                creator_id="guardian_1",
                assigned_reviewer_id="m_b5_2",
                is_published=False,
                is_allocated=False,
                learning_outcomes=["Outcome 2"],
                learning_topics=["Topic 2"],
                prerequisites=[],
                project_requirements="Deliver cloud test project",
                default_timeline={
                    "assignment_date": "2026-11-12",
                    "learning_start_date": "2026-11-12",
                    "learning_end_date": "2026-11-22",
                    "project_start_date": "2026-11-23",
                    "project_end_date": "2026-12-03",
                    "submission_deadline": "2026-12-05",
                    "review_date": "2026-12-08",
                    "expected_award_date": "2026-12-10"
                }
            )
            store.save_badge(b4_2)

    def tearDown(self):
        # Clean up test badges and requests
        test_bids = ["badge_b4_gov_test", "badge_b4_cloud_test"]
        for bid in test_bids:
            store.badges.pop(bid, None)
        if store.db and store.db.conn:
            try:
                store.db.conn.execute("DELETE FROM badges WHERE id IN ('badge_b4_gov_test', 'badge_b4_cloud_test')")
                store.db.conn.execute("DELETE FROM mapping_requests WHERE badge_id IN ('badge_b4_gov_test', 'badge_b4_cloud_test')")
                store.db.conn.execute("DELETE FROM band_mappings WHERE badge_id IN ('badge_b4_gov_test', 'badge_b4_cloud_test')")
                store.db.conn.execute("DELETE FROM badge_timelines WHERE badge_id IN ('badge_b4_gov_test', 'badge_b4_cloud_test')")
                store.db.conn.commit()
            except Exception:
                pass
        store.mapping_requests = [r for r in store.get_mapping_requests() if r.get("badge_id") not in test_bids]
        store.band_mappings = [m for m in store.get_band_mappings() if m.get("badge_id") not in test_bids]

    def test_independent_mapping_requests_and_badge_isolation(self):
        """Verify independent request dispatch, concurrent review states, and non-destructive mapping per badge."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B4")
        
        # 1. Select Badge 1 and dispatch review requests
        self.ctrl.handle_event("select_mapping_badge", "Governance Architecture Test")
        self.assertEqual(self.ctrl.mapping_selected_badge, "Governance Architecture Test")
        self.assertEqual(self.ctrl.mapping_selected_badge_id, "badge_b4_gov_test")

        self.ctrl.mapping_selected_cosmonauts = ["m_b4_1", "m_b4_2"]
        self.ctrl.mapping_selected_reviewers = ["m_b5_1", "m_b5_2"]
        self.ctrl.mapping_review_dates = ["2026-11-17", "2026-11-18", "2026-11-19"]

        self.ctrl.handle_event("send_mapping_requests", "{}")
        all_reqs = store.get_mapping_requests()
        gov_reqs = [r for r in all_reqs if r.get("badge_id") == "badge_b4_gov_test" or r.get("badge") == "Governance Architecture Test"]
        self.assertEqual(len(gov_reqs), 2)
        gov_req_1 = next(r for r in gov_reqs if r.get("reviewer_id") == "m_b5_1")
        gov_req_2 = next(r for r in gov_reqs if r.get("reviewer_id") == "m_b5_2")

        # 2. While Badge 1 requests are pending, select Badge 2 and dispatch independent requests
        self.ctrl.handle_event("select_mapping_badge", "Cloud Reliability Test")
        self.assertEqual(self.ctrl.mapping_selected_badge, "Cloud Reliability Test")
        self.assertEqual(self.ctrl.mapping_selected_badge_id, "badge_b4_cloud_test")

        self.ctrl.mapping_selected_cosmonauts = ["m_b4_3", "m_b4_4"]
        self.ctrl.mapping_selected_reviewers = ["m_b5_1"]
        self.ctrl.mapping_review_dates = ["2026-11-20", "2026-11-21", "2026-11-22"]

        self.ctrl.handle_event("send_mapping_requests", "{}")

        # Verify requests for both badges coexist independently!
        all_reqs = store.get_mapping_requests()
        gov_reqs = [r for r in all_reqs if r.get("badge_id") == "badge_b4_gov_test" or r.get("badge") == "Governance Architecture Test"]
        cld_reqs = [r for r in all_reqs if r.get("badge_id") == "badge_b4_cloud_test" or r.get("badge") == "Cloud Reliability Test"]
        self.assertEqual(len(gov_reqs), 2, "Badge 1 requests must NOT be overwritten when sending Badge 2 requests")
        self.assertEqual(len(cld_reqs), 1, "Badge 2 request must be created independently")

        cld_req_1 = cld_reqs[0]
        self.assertNotEqual(gov_req_1["id"], cld_req_1["id"])

        # 3. Reviewer accepts Badge 1 request
        self.ctrl.handle_event("accept_mapping_request", gov_req_1["id"])
        self.ctrl.handle_event("accept_mapping_request", gov_req_2["id"])

        # 4. Guardian selects Badge 1 and saves mapping
        self.ctrl.handle_event("select_mapping_badge", "Governance Architecture Test")
        self.ctrl.mapping_selected_cosmonauts = ["m_b4_1", "m_b4_2"]
        self.ctrl.mapping_review_dates = ["2026-11-17", "2026-11-18", "2026-11-19"]
        self.ctrl.handle_event("execute_cosmonaut_mapping", "{}")

        # Verify Badge 1 mapping was saved
        mappings = store.get_band_mappings()
        gov_mappings = [m for m in mappings if m.get("badge_id") == "badge_b4_gov_test" or m.get("badge") == "Governance Architecture Test"]
        self.assertTrue(len(gov_mappings) >= 1)

        # 5. Reviewer accepts Badge 2 request
        self.ctrl.handle_event("accept_mapping_request", cld_req_1["id"])

        # 6. Guardian selects Badge 2 and saves mapping
        self.ctrl.handle_event("select_mapping_badge", "Cloud Reliability Test")
        self.ctrl.mapping_selected_cosmonauts = ["m_b4_3", "m_b4_4"]
        self.ctrl.mapping_review_dates = ["2026-11-20", "2026-11-21", "2026-11-22"]
        self.ctrl.handle_event("execute_cosmonaut_mapping", "{}")

        # Verify BOTH Badge 1 and Badge 2 mappings exist concurrently in SQLite!
        mappings = store.get_band_mappings()
        gov_mappings = [m for m in mappings if m.get("badge_id") == "badge_b4_gov_test" or m.get("badge") == "Governance Architecture Test"]
        cld_mappings = [m for m in mappings if m.get("badge_id") == "badge_b4_cloud_test" or m.get("badge") == "Cloud Reliability Test"]
        
        self.assertTrue(len(gov_mappings) >= 1, "Badge 1 mapping must NOT be erased when Badge 2 mapping is saved")
        self.assertTrue(len(cld_mappings) >= 1, "Badge 2 mapping must be saved independently")

        # Verify timelines for both badges
        tl_gov_1 = store.get_timeline("badge_b4_gov_test", "m_b4_1")
        self.assertIsNotNone(tl_gov_1)
        self.assertIn(tl_gov_1.reviewer_id, ["m_b5_1", "m_b5_2"])

        tl_cld_1 = store.get_timeline("badge_b4_cloud_test", "m_b4_3")
        self.assertIsNotNone(tl_cld_1)
        self.assertEqual(tl_cld_1.reviewer_id, "m_b5_1")

        # 7. Check Badge Allotment view
        self.ctrl.handle_event("nav_guardian", "g_allotment")
        html_allot = self.ctrl.render()
        self.assertIn("Governance Architecture Test", html_allot)
        self.assertIn("Cloud Reliability Test", html_allot)

if __name__ == "__main__":
    unittest.main()
