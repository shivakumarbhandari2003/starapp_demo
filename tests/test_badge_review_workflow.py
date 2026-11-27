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

        # Log in as Nisha Menon -> lands on Badges (first sidebar item) with the ordered sidebar
        self.ctrl.handle_event("select_demo_account", "m_b2_4")
        self.assertEqual(self.ctrl.current_user.id, "m_b2_4")
        self.assertEqual(self.ctrl.current_view, "c_submission")

        # Sidebar contains exact ordered items (Learning Roadmap & Study Materials omitted from sidebar)
        choose_html = self.ctrl.render()
        self.assertIn('data-nav-id="c_submission"', choose_html)
        self.assertNotIn('data-nav-id="c_choose_cycle"', choose_html)  # cycles are switched from the sidebar cycle pill
        self.assertIn('data-nav-id="c_badge_reviews"', choose_html)
        self.assertIn('data-nav-id="c_requests"', choose_html)
        self.assertNotIn('data-nav-id="c_assessments"', choose_html)   # no separate Cosmonaut Assessments page: assessing is in Badge Reviews
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
        # the request is a card; the badge is inspected / edited / approved / returned inside its review page
        self.assertIn("lg-saved-badge-card is-clickable", reqs_html)
        self.assertIn("Band B1", reqs_html)
        self.assertIn("Review Badge", reqs_html)
        self.assertIn("open_reviewer_badge_review", reqs_html)

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
        """Verify Liquid-Glass Email+Password login page and Quick Login pills for 6 bands + CEO Guardian."""
        login_html = self.ctrl.render_login_view()
        self.assertIn('id="login-email"', login_html)
        self.assertIn('id="login-password"', login_html)
        self.assertIn("Quick Login", login_html)
        self.assertIn("Ananya Iyer", login_html)
        self.assertIn("Nisha Menon", login_html)
        self.assertIn("Tanvi Shah", login_html)
        self.assertIn("Rajiv Menon", login_html)
        self.assertIn("Anirudh Krishnan", login_html)
        self.assertIn("Devika Narayanan", login_html)
        self.assertIn("Arjun Mehta", login_html)
        self.assertIn("CEO · Guardian", login_html)
        for b in ("B1", "B2", "B3", "B4", "B5", "B6"):
            self.assertIn(f">{b}<", login_html)
        self.assertNotIn("Multi-Window Live Sync Testing", login_html)
        self.assertNotIn("One-Click Demo Account Access:", login_html)

        # Verify exact B1 -> B6 -> CEO pill order in the rendered HTML
        pos_b1 = login_html.find("Ananya Iyer")
        pos_b2 = login_html.find("Nisha Menon")
        pos_b3 = login_html.find("Tanvi Shah")
        pos_b4 = login_html.find("Rajiv Menon")
        pos_b5 = login_html.find("Anirudh Krishnan")
        pos_b6 = login_html.find("Devika Narayanan")
        pos_ceo = login_html.find("Arjun Mehta")
        self.assertTrue(pos_b1 < pos_b2 < pos_b3 < pos_b4 < pos_b5 < pos_b6 < pos_ceo)

    def test_email_password_db_validation_and_quick_login(self):
        """Verify SQLite email/password validation rules and Quick Login pill authentication."""
        import starapp.storage as st

        # 1. Empty email rejected
        self.ctrl.handle_event("login", json.dumps({"email": "", "password": "123456789", "require_password": True}))
        self.assertIsNone(self.ctrl.current_user)
        self.assertIn("email address", (self.ctrl.login_error or "").lower())

        # 2. Invalid email syntax rejected
        self.ctrl.handle_event("login", json.dumps({"email": "bad-email", "password": "123456789", "require_password": True}))
        self.assertIsNone(self.ctrl.current_user)
        self.assertIn("valid email", (self.ctrl.login_error or "").lower())

        # 3. Short password (< 6 chars) rejected
        self.ctrl.handle_event("login", json.dumps({"email": "arjun.mehta@starapp.io", "password": "123", "require_password": True}))
        self.assertIsNone(self.ctrl.current_user)
        self.assertIn("at least 6 characters", (self.ctrl.login_error or "").lower())

        # 4. Wrong password rejected against SQLite
        self.ctrl.handle_event("login", json.dumps({"email": "arjun.mehta@starapp.io", "password": "wrongpassword", "require_password": True}))
        self.assertIsNone(self.ctrl.current_user)
        self.assertIn("invalid email or password", (self.ctrl.login_error or "").lower())
        err_html = self.ctrl.render_login_view()
        self.assertIn('id="login-error-banner"', err_html)
        self.assertIn('value="arjun.mehta@starapp.io"', err_html)

        # 5. Inactive user in SQLite rejected
        st.store.db.conn.execute("UPDATE users SET status = 'inactive' WHERE id = 'm_b2_4'")
        st.store.db.conn.commit()
        try:
            self.ctrl.handle_event("login", json.dumps({"email": "nisha.menon@starapp.io", "password": "123456789", "require_password": True}))
            self.assertIsNone(self.ctrl.current_user)
            self.assertIn("inactive", (self.ctrl.login_error or "").lower())
        finally:
            st.store.db.conn.execute("UPDATE users SET status = 'active' WHERE id = 'm_b2_4'")
            st.store.db.conn.commit()

        # 6. Valid CEO/Guardian email+password login against SQLite (shared password 123456789)
        self.ctrl.handle_event("login", json.dumps({"email": "arjun.mehta@starapp.io", "password": "123456789", "require_password": True}))
        self.assertIsNotNone(self.ctrl.current_user)
        self.assertEqual(self.ctrl.current_user.id, "guardian_1")
        self.assertEqual(self.ctrl.current_view, "g_cycles")
        self.assertIsNone(self.ctrl.login_error)

        # 7. Any-account shared password login across bands + optional .b1-.b6 email suffix alias
        for test_email, expected_id in (
            ("ananya.iyer@starapp.io", "m_b1_2"),
            ("aarav.sharma.b3@starapp.io", "m_b1_1"),
            ("vikram.rao@starapp.io", "m_b3_1"),
            ("devika.narayanan@starapp.io", "m_b6_1"),
        ):
            self.ctrl.handle_event("logout", "{}")
            self.assertIsNone(self.ctrl.current_user)
            self.ctrl.handle_event("login", json.dumps({"email": test_email, "password": "123456789", "require_password": True}))
            self.assertIsNotNone(self.ctrl.current_user, f"Failed shared password login for {test_email}")
            self.assertEqual(self.ctrl.current_user.id, expected_id)
            self.assertEqual(self.ctrl.current_view, "c_submission")

        # 8. Quick Login pill login (Band B6 & CEO Guardian)
        self.ctrl.handle_event("logout", "{}")
        self.ctrl.handle_event("select_demo_account", "m_b6_1")
        self.assertEqual(self.ctrl.current_user.id, "m_b6_1")
        self.assertEqual(self.ctrl.current_view, "c_submission")
        self.ctrl.handle_event("logout", "{}")
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.assertEqual(self.ctrl.current_user.id, "guardian_1")
        self.assertEqual(self.ctrl.current_view, "g_cycles")

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
        self.assertIn(">B1<", html_b1)
        self.assertIn("Configure Badge", html_b1)

        # 3. Click go_back -> Should return to 6 band cards view (band set to None)
        self.ctrl.handle_event("go_back")
        self.assertIsNone(self.ctrl.create_badge_band)
        self.assertEqual(self.ctrl.current_view, "g_create_badge")

        # 4. Navigate to g_badge_approval then go_back
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        self.assertEqual(self.ctrl.current_view, "g_badge_approval")
        self.ctrl.handle_event("go_back")
        self.assertEqual(self.ctrl.current_view, "g_create_badge")

        # 5. Cosmonaut navigation: c_submission (home) -> c_results -> go_back -> c_submission
        self.ctrl.handle_event("select_demo_account", "m_b1_2")
        self.assertEqual(self.ctrl.current_view, "c_submission")
        self.ctrl.handle_event("nav_cosmonaut", "c_results")
        self.assertEqual(self.ctrl.current_view, "c_results")
        self.assertNotIn("Guardian Window", self.ctrl.render())
        self.ctrl.handle_event("go_back")
        self.assertEqual(self.ctrl.current_view, "c_submission")

    def test_ui_polish_vertical_hierarchy_sidebar_mapping_allotment(self):
        """Verify enlarged STARAPP header, Liquid-Glass sidebar profile without icons, vertical taxonomy trees, Saved Badges, Mapping & Allotment cards."""
        login_html = self.ctrl.render_login_view()
        self.assertIn("STARAPP", login_html)
        self.assertNotIn("Autonomous Training", login_html)

        # Login as Guardian CEO & verify sidebar and views
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.ctrl.handle_event("nav_guardian", "g_learning")
        self.ctrl.handle_event("select_create_badge_band", "B1")
        create_html = self.ctrl.render()
        self.assertNotIn("Cosmonaut Window", create_html)
        self.assertNotIn("All Band Cards", create_html)
        self.assertNotIn("Workspace</span>", create_html)
        self.assertIn("dispatchAction('nav_guardian', 'g_learning')", create_html)
        self.assertIn("lg-sidebar-profile", create_html)
        self.assertIn("Arjun Mehta", create_html)
        self.assertIn("Academy Guardian", create_html)
        self.assertIn("signout-link", create_html)
        self.assertNotIn('class="user-avatar"', create_html)
        self.assertIn("lg-saved-badge-card", create_html)
        self.assertIn("lg-hier-tree", create_html)
        self.assertNotIn("(Band )", create_html)

        # Reviewer Badge Approval vertical taxonomy hierarchy
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        approval_html = self.ctrl.render()
        self.assertIn("lg-hier-tree", approval_html)
        self.assertIn("Power :", approval_html)
        self.assertIn("Capability :", approval_html)
        self.assertIn("Skill :", approval_html)

        # Mapping card section sizing
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        mapping_html = self.ctrl.render()
        self.assertIn("Badge Requests &amp; Mappings &bull; Band B1", mapping_html)

        # Allotment cards visualization
        self.ctrl.handle_event("nav_guardian", "g_allotment")
        allot_html = self.ctrl.render()
        self.assertIn("lg-allot-section-header", allot_html)
        self.assertIn("lg-allot-card", allot_html)
        self.assertIn("lg-allot-view-btn", allot_html)
        self.assertIn("lg-hier-tree", allot_html)

        # Clicking Portal Pillars returns from band workspace to 6 Band Cards view
        self.ctrl.handle_event("nav_guardian", "g_learning")
        self.assertEqual(self.ctrl.current_view, "g_learning")
        self.assertIsNone(self.ctrl.create_badge_band)
        bands_html = self.ctrl.render()
        self.assertIn("band-selection-hidden", bands_html)
        self.assertIn("Trainee", bands_html)
        self.assertIn("Principal", bands_html)

if __name__ == "__main__":
    unittest.main()
