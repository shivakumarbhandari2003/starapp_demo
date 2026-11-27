"""
Tests for Guardian Badge Allotment:
1. Headings renamed to 'Published' and 'Not Published Yet' (tabs & section headers)
2. Published badges display mapped cosmonauts and reviewers, with Revoke button
3. Not Published Yet badges display mapped cosmonauts and reviewers, with Publish to Roadmap button
4. Publishing a badge reflects on mapped cosmonauts' roadmap and reviewers' 'Badge reviews' section
5. Revoking a badge returns it to Not Published Yet, removes it from active roadmap and reviewer schedule
"""

import unittest
import json
from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import Badge, BadgeTimeline

class TestAllotmentPublishRevokeFlow(unittest.TestCase):
    def setUp(self):
        self.ctrl = StarAppController()
        # Initialize with clean store
        self.ctrl.handle_event("select_demo_account", "guardian_1")

    def test_01_allotment_view_headings_and_display(self):
        """Verify headings are Published and Not Published Yet, and cards show mapped personnel."""
        self.ctrl.handle_event("nav_guardian", "g_allotment")
        self.assertEqual(self.ctrl.current_view, "g_allotment")

        html = self.ctrl.render()

        # Check Tab Headings
        self.assertIn("Published (", html)
        self.assertIn("Not Published Yet (", html)
        self.assertNotIn("Allocated Badges (", html)
        self.assertNotIn("Not Allocated Yet (", html)

        # Check Section Headings
        self.assertIn("Published (", html)
        self.assertIn("Active on Roadmap", html)
        self.assertIn("Not Published Yet (", html)
        self.assertIn("In Catalog", html)

        # Check Published Badge (Signals Foundations)
        self.assertIn("Signals Foundations", html)
        self.assertIn("Revoke", html)
        self.assertIn("open_badge_mapping_modal", html)  # the mapped reviewer / cosmonauts are one click away (Mapping button)
        self.ctrl.handle_event("open_badge_mapping_modal", "badge_b1_signals")
        self.assertIn("Rohan Deshmukh", self.ctrl.render_active_modal())  # Mapped reviewer
        self.ctrl.handle_event("close_modal", "{}")

        # Check Not Published Yet Badges
        self.assertIn("Intelligent Apps Foundations", html)
        self.assertIn("Data Systems Architecture", html)
        self.assertIn("Publish to Roadmap", html)
        self.assertIn("open_badge_timeline_modal", html)

    def test_02_published_badge_visible_on_cosmonaut_roadmap_and_reviewer_schedule(self):
        """Verify published badge is visible to mapped cosmonaut and reviewer."""
        # Check Cosmonaut Roadmap for mapped cadet m_b1_1
        cosmo_ctrl = StarAppController()
        cosmo_ctrl.handle_event("login", json.dumps({"username": "aarav.sharma"}))
        cosmo_ctrl.handle_event("nav_cosmonaut", "c_roadmap")
        cosmo_html = cosmo_ctrl.render()

        # Signals Foundations is published and should be active / visible
        self.assertIn("Signals Foundations", cosmo_html)
        self.assertIn("B1-SIG-01", cosmo_html)

        # Check Reviewer Badge Reviews schedule for mapped reviewer m_b2_1 (Rohan Deshmukh)
        rev_ctrl = StarAppController()
        rev_ctrl.handle_event("login", json.dumps({"username": "rohan.deshmukh"}))
        rev_ctrl.handle_event("nav_cosmonaut", "c_badge_reviews")
        rev_html = rev_ctrl.render()

        self.assertIn("Badge Review Schedule", rev_html)
        self.assertIn("Upcoming Reviews", rev_html)
        self.assertIn("Signals Foundations", rev_html)

    def test_03_publish_unpublished_badge_propagates_to_roadmap_and_reviewer(self):
        """Publishing b1_int_01 makes it appear in Published, unlocks on roadmap, and shows in reviewer schedule."""
        # 1. Publish b1_int_01
        self.ctrl.handle_event("publish_badge", "b1_int_01")
        b = store.get_badge("b1_int_01")
        self.assertTrue(b.is_published)
        self.assertTrue(b.is_allocated)

        # 2. Check Guardian Allotment view
        self.ctrl.handle_event("nav_guardian", "g_allotment")
        html = self.ctrl.render()
        self.assertIn("Published (", html)
        # b1_int_01 now has the Revoke option
        self.assertIn("Revoke", html)

        # 3. Check Cosmonaut Roadmap
        cosmo_ctrl = StarAppController()
        cosmo_ctrl.handle_event("login", json.dumps({"username": "aarav.sharma"}))
        cosmo_ctrl.handle_event("nav_cosmonaut", "c_roadmap")
        cosmo_html = cosmo_ctrl.render()
        self.assertIn("Intelligent Apps Foundations", cosmo_html)

        # 4. Check Reviewer Schedule (Rohan Deshmukh)
        rev_ctrl = StarAppController()
        rev_ctrl.handle_event("login", json.dumps({"username": "rohan.deshmukh"}))
        rev_ctrl.handle_event("nav_cosmonaut", "c_badge_reviews")
        rev_html = rev_ctrl.render()
        self.assertIn("Intelligent Apps Foundations", rev_html)

    def test_04_revoke_badge_flow(self):
        """Revoking a badge moves it to Not Published Yet and removes from active roadmap and reviewer schedule."""
        # 1. Revoke badge_b1_signals
        self.ctrl.handle_event("revoke_badge", "badge_b1_signals")
        b = store.get_badge("badge_b1_signals")
        self.assertFalse(b.is_published)
        self.assertFalse(b.is_allocated)

        # 2. Check Guardian Allotment: it should now be in Not Published Yet
        self.ctrl.handle_event("nav_guardian", "g_allotment")
        html = self.ctrl.render()
        self.assertIn("Not Published Yet", html)
        self.assertIn("Publish to Roadmap", html)

        # 3. Check Reviewer schedule: badge_b1_signals should NOT be in active upcoming reviews
        rev_ctrl = StarAppController()
        rev_ctrl.handle_event("login", json.dumps({"username": "rohan.deshmukh"}))
        rev_ctrl.handle_event("nav_cosmonaut", "c_badge_reviews")
        rev_html = rev_ctrl.render()
        self.assertNotIn("Signals Foundations", rev_html)

    @classmethod
    def tearDownClass(cls):
        store.reset_to_seed()

if __name__ == "__main__":
    unittest.main()
