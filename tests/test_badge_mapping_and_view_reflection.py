import unittest
import json
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import User, Badge, BadgeTimeline

class TestBadgeMappingAndViewReflection(unittest.TestCase):
    def setUp(self):
        self.ctrl = StarAppController()
        # Log in as Guardian Admin
        self.ctrl.handle_event("select_demo_account", "admin")
        store.mapping_requests = [r for r in store.get_mapping_requests() if r.get("band") != "B4"]
        
        # Ensure B4 approved badge exists in store & SQLite
        b4 = store.get_badge("badge_b4_governance")
        if not b4:
            b4 = Badge(
                id="badge_b4_governance",
                code="B4-GOV-01",
                title="Governance Architecture",
                category="Data & Machine",
                description="B4 badge specializing in Governance",
                target_band="B4",
                power="Tech",
                capability="Data & Machine",
                skill="Governance",
                workflow_status="approved",
                creator_id="guardian_1",
                assigned_reviewer_id="m_b5_1",
                is_published=False,
                is_allocated=False,
                learning_outcomes=["Lead enterprise-scale system optimization"],
                learning_topics=["Governance Core Fundamentals"],
                prerequisites=[],
                project_requirements="Deliver enterprise governance architecture",
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
            store.save_badge(b4)

    def test_01_b4_mapping_badge_selection_and_milestone_not_aios(self):
        """Verify selecting Band B4 maps to Governance Architecture, not AIOS."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B4")
        self.assertEqual(self.ctrl.mapping_selected_band, "B4")
        self.assertEqual(self.ctrl.mapping_selected_badge, "Governance Architecture")

        html = self.ctrl.render()
        self.assertIn("Governance Architecture", html)
        self.assertIn("Band B4", html)

    def test_02_execute_cosmonaut_mapping_saves_badge_and_timelines(self):
        """Verify Save Mapping creates timelines for the specific badge with 3-day window."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B4")
        
        # Select cosmonauts and reviewers
        cosmo_ids = ["m_b4_1", "m_b4_2"]
        rev_ids = ["m_b5_1"]
        self.ctrl.mapping_selected_cosmonauts = list(cosmo_ids)
        self.ctrl.mapping_selected_reviewers = list(rev_ids)
        self.ctrl.mapping_review_dates = ["2026-11-17", "2026-11-18", "2026-11-19"]

        # Send request and accept
        self.ctrl.handle_event("send_mapping_requests", "{}")
        reqs = store.get_mapping_requests()
        b4_req = next((r for r in reqs if r.get("band") == "B4" and r.get("reviewer_id") == "m_b5_1"), None)
        self.assertIsNotNone(b4_req)
        self.assertEqual(b4_req["badge"], "Governance Architecture")
        
        # Accept request
        self.ctrl.handle_event("accept_mapping_request", b4_req["id"])

        # Execute Cosmonaut Mapping
        self.ctrl.handle_event("execute_cosmonaut_mapping", "{}")

        # Verify band mappings
        b4_mappings = [m for m in store.get_band_mappings() if m.get("band") == "B4"]
        self.assertTrue(len(b4_mappings) >= 1)
        m = b4_mappings[0]
        self.assertEqual(m["badge"], "Governance Architecture")
        self.assertEqual(m["badge_id"], "badge_b4_governance")
        self.assertIn("m_b4_1", m["cosmonauts"])
        self.assertIn("m_b4_2", m["cosmonauts"])

        # Verify Live Mapped Review Allocations HTML displays Governance Architecture (not AIOS)
        html = self.ctrl.render()
        self.assertIn("Live Mapped Review Allocations", html)
        self.assertIn("Governance Architecture", html)

        # Verify BadgeTimeline records created in store
        tl1 = store.get_timeline("badge_b4_governance", "m_b4_1")
        self.assertIsNotNone(tl1)
        self.assertEqual(tl1.reviewer_id, "m_b5_1")
        self.assertEqual(tl1.status, "active")

    def test_03_badge_allotment_displays_dedicated_mapping_info(self):
        """In Badge Allotment, Governance Architecture shows assigned cadets and reviewer."""
        self.ctrl.handle_event("nav_guardian", "g_allotment")
        html = self.ctrl.render()
        self.assertIn("Governance Architecture", html)
        self.assertIn("BAND B4", html)
        self.assertIn("Mapped Evaluation Personnel", html)

    def test_04_publish_badge_and_role_views_reflection(self):
        """Verify published badge appears in Cosmonaut roadmap and Reviewer schedule."""
        self.ctrl.handle_event("publish_badge", "badge_b4_governance")

        badge = store.get_badge("badge_b4_governance")
        self.assertTrue(badge.is_published)
        self.assertTrue(badge.is_allocated)

        # Log in as mapped Cosmonaut (m_b4_1)
        cosmo_ctrl = StarAppController()
        cosmo_ctrl.handle_event("select_demo_account", "m_b4_1")
        
        # 1. Check Cosmonaut Roadmap (route still intact even though hidden from sidebar)
        cosmo_ctrl.handle_event("nav_cosmonaut", "c_roadmap")
        roadmap_html = cosmo_ctrl.render()
        self.assertIn("Cosmonaut Learning Pathway", roadmap_html)
        self.assertIn("Governance Architecture", roadmap_html)

        # 2. Check Cosmonaut Badges / Submission view
        cosmo_ctrl.handle_event("nav_cosmonaut", "c_submission")
        sub_html = cosmo_ctrl.render()
        self.assertIn("Governance Architecture", sub_html)

        # 3. Log in as mapped Reviewer (m_b5_1)
        rev_ctrl = StarAppController()
        rev_ctrl.handle_event("select_demo_account", "m_b5_1")
        
        # Check Reviewer Badge Reviews schedule
        rev_ctrl.handle_event("nav_cosmonaut", "c_badge_reviews")
        sched_html = rev_ctrl.render()
        self.assertIn("Governance Architecture", sched_html)
        self.assertIn("Upcoming Review", sched_html)
        self.assertIn("Create Project", sched_html)

if __name__ == "__main__":
    unittest.main()
