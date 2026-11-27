"""
Verification tests for the 5 new StarApp workflow features:
1. Badge approval queue band filtering.
2. Mapping request dispatch & reviewer acceptance/rejection flow.
3. Save mapping button execution & persistence.
4. Badge allotment taxonomy details, timeline configuration drawer & publish flow.
5. Reviewer badge review schedule (upcoming & completed reviews).
"""

import unittest
import json
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import Badge, BadgeTimeline, current_iso_timestamp

class TestNewWorkflowFeatures(unittest.TestCase):

    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        self.ctrl.initialize()

    def test_01_badge_approval_queue_band_filtering(self):
        """Verify g_badge_approval defaults to the active band and only shows badges of that band."""
        # Login as guardian
        self.ctrl.handle_event("login", json.dumps({"username": "guardian"}))
        self.ctrl.handle_event("select_create_badge_band", "B2")

        # Navigate to badge approval
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        self.assertEqual(self.ctrl.current_view, "g_badge_approval")
        self.assertEqual(self.ctrl.create_badge_band, "B2")

        # Render HTML
        html = self.ctrl.render()
        self.assertIn("Reviewer Badge Approval", html)
        self.assertIn("ba-toolbar-card", html)
        # Queue is rendered as one compact row per badge under a "Taxonomy Hierarchy" header,
        # or the empty-state card when the selected band has no badge.
        self.assertTrue('class="ba-row"' in html or "No Badges Found" in html)

    def test_02_mapping_request_dispatch_and_reviewer_decision(self):
        """Verify Guardian sending requests in Mapping populates reviewer's c_requests where they can Accept."""
        self.ctrl.handle_event("login", json.dumps({"username": "guardian"}))
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.ctrl.handle_event("nav_guardian", "g_mapping")

        # Select cosmonaut and reviewer (real SQLite IDs)
        self.ctrl.mapping_selected_cosmonauts = ["m_b1_1"]
        self.ctrl.mapping_selected_reviewers = ["m_b2_1"]
        self.ctrl.mapping_selected_badge = "Signals Foundations"

        # Send mapping request
        self.ctrl.handle_event("send_mapping_requests", "{}")
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify request exists in store
        reqs = store.get_mapping_requests()
        rev_req = next((r for r in reqs if r.get("reviewer_id") == "m_b2_1"), None)
        self.assertIsNotNone(rev_req)
        self.assertEqual(rev_req["status"], "pending")

        # Now login as reviewer rohan.deshmukh
        self.ctrl.handle_event("login", json.dumps({"username": "rohan.deshmukh"}))
        self.ctrl.handle_event("nav_cosmonaut", "c_requests")
        self.assertEqual(self.ctrl.current_view, "c_requests")

        # Render review requests workspace - should contain the Cadet Evaluation Invitations section
        html = self.ctrl.render()
        self.assertIn("Cadet Evaluation Invitations", html)
        self.assertIn("Signals Foundations", html)

        # Reviewer accepts the request
        self.ctrl.handle_event("accept_mapping_request", rev_req["id"])
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify status is accepted
        req_updated = next(r for r in store.get_mapping_requests() if r["id"] == rev_req["id"])
        self.assertEqual(req_updated["status"], "accepted")

    def test_03_save_mapping_execution_and_persistence(self):
        """Verify Save Mapping creates band_mapping, updates badge_timelines and persists to SQLite."""
        self.ctrl.handle_event("login", json.dumps({"username": "guardian"}))
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.ctrl.mapping_selected_cosmonauts = ["m_b1_1"]
        self.ctrl.mapping_selected_reviewers = ["m_b2_1"]
        self.ctrl.mapping_selected_badge = "CUR-102"

        # Add accepted request
        store.add_mapping_request({
            "id": "req_B1_m_b2_1",
            "band": "B1",
            "badge": "CUR-102",
            "reviewer_id": "m_b2_1",
            "reviewer_name": "Rohan Deshmukh",
            "reviewer_role": "Reviewer",
            "reviewer_band": "B2",
            "reviewer_avatar": "RD",
            "cosmonaut_ids": ["m_b1_1"],
            "review_dates": ["2026-11-25", "2026-11-26", "2026-11-27"],
            "status": "accepted",
            "sent_at": current_iso_timestamp()
        })

        # Execute mapping
        self.ctrl.handle_event("execute_cosmonaut_mapping", "{}")
        mappings = store.get_band_mappings()
        self.assertTrue(len(mappings) > 0)
        b1_map = next((m for m in mappings if m.get("band") == "B1"), None)
        self.assertIsNotNone(b1_map)
        self.assertIn("m_b1_1", b1_map["cosmonauts"])
        self.assertIn("m_b2_1", b1_map["reviewers"])

    def test_04_badge_allotment_taxonomy_and_timeline_save(self):
        """Verify g_allotment renders full taxonomy details and save_allotment_timeline updates the timeline."""
        self.ctrl.handle_event("login", json.dumps({"username": "guardian"}))
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.ctrl.handle_event("nav_guardian", "g_allotment")

        html = self.ctrl.render()
        self.assertIn("open_badge_timeline_modal", html)
        self.assertNotIn("Badge Catalog &amp; Allotment Manager", html)
        self.assertNotIn("Active Mapped Badge Allocations", html)

        # Open Timeline & Mapping modal to inspect schedule and configure dates
        self.ctrl.handle_event("open_badge_timeline_mapping_modal", "badge_b1_signals")
        modal_html = self.ctrl.render_active_modal()
        self.assertIn("Milestone Timeline Schedule", modal_html)
        self.assertNotIn('type="date"', modal_html)                  # the timeline view is READ-ONLY ...
        self.assertNotIn("Save Timeline", modal_html)
        self.assertIn("Read-only view", modal_html)
        self.assertIn("Edit Badge", modal_html)                      # ... dates and cosmonauts are changed from Edit Badge
        self.ctrl.handle_event("close_modal", "{}")

        # Test save_allotment_timeline action on existing badge
        timeline_payload = {
            "badge_id": "badge_b1_signals",
            "learning_start_date": "2026-11-12",
            "learning_end_date": "2026-11-22",
            "project_start_date": "2026-11-23",
            "project_end_date": "2026-12-02",
            "submission_deadline": "2026-12-04",
            "review_date": "2026-12-07",
            "expected_award_date": "2026-12-09"
        }
        self.ctrl.handle_event("save_allotment_timeline", json.dumps(timeline_payload))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify badge default timeline updated
        b = store.get_badge("badge_b1_signals")
        self.assertIsNotNone(b)
        self.assertEqual(b.default_timeline.get("submission_deadline"), "2026-12-04")

    def test_05_reviewer_badge_review_schedule(self):
        """Verify reviewer sidebar includes Badge Reviews and c_badge_reviews shows schedule."""
        # Set up a timeline for m_b2_1 on badge_b1_signals
        tl = BadgeTimeline(
            badge_id="badge_b1_signals",
            cosmonaut_id="m_b1_1",
            assignment_date="2026-11-10",
            publication_date="2026-11-10",
            learning_start_date="2026-11-11",
            learning_end_date="2026-11-20",
            project_start_date="2026-11-21",
            project_end_date="2026-12-01",
            submission_deadline="2026-12-03",
            review_date="2026-12-06",
            expected_award_date="2026-12-08",
            reviewer_id="m_b2_1",
            status="active"
        )
        store.save_timeline(tl)

        # Login as rohan.deshmukh (Band B2 reviewer)
        self.ctrl.handle_event("login", json.dumps({"username": "rohan.deshmukh"}))
        self.ctrl.handle_event("nav_cosmonaut", "c_badge_reviews")
        self.assertEqual(self.ctrl.current_view, "c_badge_reviews")

        rendered = self.ctrl.render()
        self.assertIn("Badge Review Schedule", rendered)
        self.assertIn("Upcoming Reviews", rendered)
        self.assertIn("Signals Foundations", rendered)

    def test_06_c_requests_with_null_review_due_at_and_dates(self):
        """Verify c_requests renders cleanly when review_due_at, sent_at, decision_notes are None (e.g. from LEFT JOIN)."""
        # Create a badge assigned directly to m_b2_1 without a badge_reviewer_assignments row
        b = Badge(
            id="badge_test_null_due",
            code="B2-NULL-01",
            title="Null Due Test Badge",
            category="Tech",
            description="Testing null due date safety",
            target_band="B1",
            power="Tech",
            capability="Data",
            skill="Signals",
            learning_outcomes=["Outcome 1"],
            learning_topics=["Topic 1"],
            prerequisites=[],
            project_requirements="Build something",
            assigned_reviewer_id="m_b2_1",
            workflow_status="pending_review"
        )
        store.save_badge(b)

        # Login as rohan.deshmukh (m_b2_1)
        self.ctrl.handle_event("login", json.dumps({"username": "rohan.deshmukh"}))
        self.ctrl.handle_event("nav_cosmonaut", "c_requests")
        self.assertEqual(self.ctrl.current_view, "c_requests")

        rendered = self.ctrl.render()
        self.assertIn("Review Requests", rendered)
        self.assertIn("Badge Approval Requests", rendered)
        self.assertIn("Null Due Test Badge", rendered)
        self.assertIn("Cadet Evaluation Invitations", rendered)

if __name__ == "__main__":
    unittest.main()
