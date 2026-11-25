"""
Test Badge Reviewer Request, Higher-Band Hierarchy, Cosmonaut Review Requests Queue,
Badge Editing by Reviewer, and Approval/Return Lifecycle.
"""
import unittest
import json
from starapp.app import StarAppController
from starapp.storage import store
from starapp.database import db

class TestBadgeReviewWorkflow(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        self.ctrl.initialize()

    def test_two_initial_b1_badges_seeded(self):
        """Verify the 2 initial B1 badges are persisted in SQLite and store."""
        b1_badges = [b for b in store.get_all_badges() if getattr(b, "target_band", "") == "B1"]
        self.assertGreaterEqual(len(b1_badges), 2, "Band B1 must have at least 2 seeded badges")
        titles = [b.title for b in b1_badges]
        self.assertIn("Intelligent Apps Foundations", titles)
        self.assertIn("Data Systems Architecture", titles)

    def test_higher_band_reviewer_filter_rule(self):
        """Verify higher band rule: B1 badges can only be reviewed by B2..B6 engineers."""
        # 1. B1 badge: eligible reviewers must only be from B2..B6
        b1_revs = store.get_eligible_badge_reviewers("B1")
        self.assertGreater(len(b1_revs), 0)
        b1_bands = {r["band"] for r in b1_revs}
        self.assertTrue(b1_bands.issubset({"B2", "B3", "B4", "B5", "B6"}))
        self.assertNotIn("B1", b1_bands)

        # 2. Attempting to assign a B1 user (e.g. m_b1_1 Aarav Sharma Cadet) to review a B1 badge must fail
        ok, msg = store.assign_and_request_badge_review("b1_int_01", "m_b1_1", "guardian_1")
        self.assertFalse(ok)
        self.assertIn("higher bands", msg.lower())

        # 3. Assigning a B2 user (Nisha Menon m_b2_4) to review a B1 badge must succeed
        ok, msg = store.assign_and_request_badge_review("b1_int_01", "m_b2_4", "guardian_1")
        self.assertTrue(ok)
        b = store.get_badge("b1_int_01")
        self.assertEqual(b.workflow_status, "pending_review")
        self.assertEqual(b.assigned_reviewer_id, "m_b2_4")

    def test_guardian_send_badge_review_request(self):
        """Verify Guardian can select a higher-band reviewer and send a review request."""
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.assertEqual(self.ctrl.current_view, "g_cycles")

        # Guardian dispatches review request for b1_dat_01 to Tanvi Shah (B3, m_b3_6)
        self.ctrl.handle_event("send_badge_review_request", {
            "badge_id": "b1_dat_01",
            "reviewer_id": "m_b3_6"
        })
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify badge updated in store
        badge = store.get_badge("b1_dat_01")
        self.assertEqual(badge.workflow_status, "pending_review")
        self.assertEqual(badge.assigned_reviewer_id, "m_b3_6")

        # Verify notification sent to Tanvi Shah
        tanvi_notifs = store.get_notifications("m_b3_6")
        self.assertTrue(any("review" in n.title.lower() or "review" in n.message.lower() for n in tanvi_notifs))

    def test_reviewer_portal_review_requests_display(self):
        """Verify reviewer sees Review Requests in sidebar, dashboard alert banner, and c_requests workspace."""
        # Guardian assigns b1_int_01 to Nisha Menon (B2, m_b2_4)
        store.assign_and_request_badge_review("b1_int_01", "m_b2_4", "guardian_1")

        # Log in as Nisha Menon -> opens Choose Cycle global filter with ordered sidebar
        self.ctrl.handle_event("select_demo_account", "m_b2_4")
        self.assertEqual(self.ctrl.current_user.id, "m_b2_4")
        self.assertEqual(self.ctrl.current_view, "c_choose_cycle")

        # Sidebar contains exact ordered items (Learning Roadmap & Study Materials omitted from sidebar)
        choose_html = self.ctrl.render()
        self.assertIn("Choose Cycle", choose_html)
        self.assertIn('data-nav-id="c_choose_cycle"', choose_html)
        self.assertIn('data-nav-id="c_badge_reviews"', choose_html)
        self.assertIn('data-nav-id="c_requests"', choose_html)
        self.assertIn('data-nav-id="c_assessments"', choose_html)
        self.assertNotIn('data-nav-id="c_roadmap"', choose_html)
        self.assertNotIn('data-nav-id="c_materials"', choose_html)

        # 1. Dashboard displays institutional review assignment alert when opened
        self.ctrl.handle_event("nav_cosmonaut", "c_dashboard")
        dash_html = self.ctrl.render()
        self.assertIn("Institutional Peer Review Assignment", dash_html)
        self.assertIn("Review Requests (1)", dash_html)

        # 3. Navigate to c_requests
        self.ctrl.handle_event("nav_cosmonaut", "c_requests")
        self.assertEqual(self.ctrl.current_view, "c_requests")
        reqs_html = self.ctrl.render()
        self.assertIn("Review Requests", reqs_html)
        self.assertIn("Intelligent Apps Foundations", reqs_html)
        self.assertIn("TARGET: BAND B1", reqs_html)
        self.assertIn("Inspect Badge", reqs_html)
        self.assertIn("Edit Badge", reqs_html)
        self.assertIn("Accept & Approve", reqs_html)
        self.assertIn("Return with Feedback", reqs_html)

    def test_reviewer_edit_badge_persists_permanently(self):
        """Verify reviewer can edit the badge proposal and edits are permanently saved in SQLite."""
        store.assign_and_request_badge_review("b1_int_01", "m_b2_4", "guardian_1")
        self.ctrl.handle_event("select_demo_account", "m_b2_4")

        # Reviewer submits edits
        new_prompt = json.dumps({
            "id": "b1_int_01",
            "title": "Intelligent Apps Architecture (Reviewed by B2)",
            "description": "Refined enterprise agent specifications with rigorous security sandboxing.",
            "outcomes": [
                "Can architect secure agent isolation environments",
                "Can validate API schemas with zero data leakage"
            ]
        })
        self.ctrl.handle_event("save_reviewed_badge", {
            "badge_id": "b1_int_01",
            "title": "Intelligent Apps Architecture (Reviewed by B2)",
            "description": "Refined enterprise agent specifications with rigorous security sandboxing.",
            "prompt_json": new_prompt
        })
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify badge permanently updated
        b = store.get_badge("b1_int_01")
        self.assertEqual(b.title, "Intelligent Apps Architecture (Reviewed by B2)")
        self.assertEqual(b.description, "Refined enterprise agent specifications with rigorous security sandboxing.")
        self.assertEqual(b.workflow_status, "pending_review")

        # Verify SQLite row also updated
        row = db.conn.execute("SELECT title, description FROM badges WHERE id = 'b1_int_01'").fetchone()
        self.assertEqual(row["title"], "Intelligent Apps Architecture (Reviewed by B2)")

    def test_reviewer_approve_badge(self):
        """Verify reviewer can authorize and approve badge, and Guardian view reflects approval."""
        store.assign_and_request_badge_review("b1_int_01", "m_b2_4", "guardian_1")
        self.ctrl.handle_event("select_demo_account", "m_b2_4")

        # Reviewer approves
        self.ctrl.handle_event("approve_submitted_badge", "b1_int_01")
        self.assertEqual(self.ctrl.flash_type, "success")
        b = store.get_badge("b1_int_01")
        self.assertEqual(b.workflow_status, "approved")

        # Guardian views approval queue
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        html = self.ctrl.render()
        self.assertIn("Approved", html)
        self.assertIn("Nisha Menon", html)

    def test_reviewer_return_badge_with_feedback(self):
        """Verify reviewer can return badge with feedback, and Guardian view reflects returned status and notes."""
        store.assign_and_request_badge_review("b1_int_01", "m_b2_4", "guardian_1")
        self.ctrl.handle_event("select_demo_account", "m_b2_4")

        # Reviewer returns badge with notes
        feedback = "Please include distributed caching in learning topics and expand the practice project rubric."
        self.ctrl.handle_event("return_submitted_badge", {
            "badge_id": "b1_int_01",
            "notes": feedback
        })
        self.assertEqual(self.ctrl.flash_type, "info")
        b = store.get_badge("b1_int_01")
        self.assertEqual(b.workflow_status, "returned")

        # Guardian view reflects returned status and feedback
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.ctrl.handle_event("select_create_badge_band", "B1")
        html_create = self.ctrl.render()
        self.assertIn("Returned for Changes", html_create)
        self.assertIn("Please include distributed caching", html_create)

    def test_direct_demo_login_order(self):
        """Verify one-click demo login lists Ananya Iyer - B1, Nisha Menon - B2, Tanvi Shah - B3 as the first three."""
        login_html = self.ctrl.render_login_view()
        self.assertIn("Ananya Iyer - B1", login_html)
        self.assertIn("Nisha Menon - B2", login_html)
        self.assertIn("Tanvi Shah - B3", login_html)
        self.assertIn("Arjun Mehta (CEO)", login_html)
        self.assertIn("Aarav Sharma - B1", login_html)

        # Verify exact order in the rendered HTML
        pos_ananya = login_html.find("Ananya Iyer - B1")
        pos_nisha = login_html.find("Nisha Menon - B2")
        pos_tanvi = login_html.find("Tanvi Shah - B3")
        self.assertTrue(pos_ananya < pos_nisha < pos_tanvi, "Demo accounts must be ordered Ananya, Nisha, Tanvi")

    def test_universal_back_button_and_history_navigation(self):
        """Verify universal Back button in topbar and non-destructive history navigation."""
        # 1. Login as Guardian -> Starts at g_create_badge (6 band cards)
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.ctrl.handle_event("nav_guardian", "g_create_badge")
        self.assertIsNone(self.ctrl.create_badge_band)
        html = self.ctrl.render()
        self.assertIn("dispatchAction('go_back'", html)

        # 2. Enter Band B1 -> Inside band workspace
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.assertEqual(self.ctrl.create_badge_band, "B1")
        html_b1 = self.ctrl.render()
        self.assertIn("Band B1 Workspace", html_b1)

        # 3. Click go_back -> Should return to 6 band cards view (band set to None)
        self.ctrl.handle_event("go_back")
        self.assertIsNone(self.ctrl.create_badge_band)
        self.assertEqual(self.ctrl.current_view, "g_create_badge")

        # 4. Navigate to g_badge_approval then go_back
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        self.assertEqual(self.ctrl.current_view, "g_badge_approval")
        self.ctrl.handle_event("go_back")
        self.assertEqual(self.ctrl.current_view, "g_create_badge")

        # 5. Cosmonaut navigation: c_choose_cycle -> c_submission -> go_back -> c_choose_cycle
        self.ctrl.handle_event("select_demo_account", "m_b1_2")
        self.assertEqual(self.ctrl.current_view, "c_choose_cycle")
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")
        self.assertEqual(self.ctrl.current_view, "c_submission")
        self.ctrl.handle_event("go_back")
        self.assertEqual(self.ctrl.current_view, "c_choose_cycle")

if __name__ == "__main__":
    unittest.main()
