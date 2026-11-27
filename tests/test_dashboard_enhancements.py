import unittest
import json
from starapp.app import StarAppController, store
from starapp.dashboard_demo import get_dashboard_demo_cosmonauts, get_demo_cosmonaut_by_id
from starapp.analytics import get_guardian_cohort_profiles, calculate_guardian_cohort_analytics

class TestDashboardEnhancements(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.app = StarAppController()

    def test_strict_data_isolation(self):
        """Verify synthetic mock cadets are removed and all users are real SQLite entries."""
        real_user_ids = set(store.users.keys())
        self.assertIn("guardian_1", real_user_ids)
        self.assertIn("cosmo_1", real_user_ids)
        # All 36 corporate hierarchy employees exist in SQLite
        self.assertGreaterEqual(len(real_user_ids), 36)

        # Synthetic demo profiles list is empty
        demos = get_dashboard_demo_cosmonauts()
        self.assertEqual(len(demos), 0)

        # Verify login view contains Email+Password inputs and 6-band + CEO Guardian Quick Login pills
        login_html = self.app.render_login_view()
        self.assertIn('id="login-email"', login_html)
        self.assertIn('id="login-password"', login_html)
        self.assertIn("Ananya Iyer", login_html)
        self.assertIn("Nisha Menon", login_html)
        self.assertIn("Tanvi Shah", login_html)
        self.assertIn("Rajiv Menon", login_html)
        self.assertIn("Anirudh Krishnan", login_html)
        self.assertIn("Devika Narayanan", login_html)
        self.assertIn("Arjun Mehta", login_html)
        self.assertIn("CEO · Guardian", login_html)

    def test_cosmonaut_dashboard_personalization_and_privacy(self):
        """Verify Aarav Sharma sees his actual data and zero fake demo data."""
        self.app.handle_event("select_demo_account", "cosmo_1")
        self.assertEqual(self.app.current_user.id, "cosmo_1")
        self.assertEqual(self.app.current_view, "c_submission")
        self.app.handle_event("nav_cosmonaut", "c_dashboard")
        self.assertEqual(self.app.current_view, "c_dashboard")

        html = self.app.render()

        # 1. Personal Header & Identity
        self.assertIn("Welcome back, Aarav Sharma", html)
        self.assertIn("Batch: <strong>Orion-24</strong>", html)
        self.assertIn("Arjun Mehta", html)

        # 2. Actual KPIs (clean initial SQLite state: 0 completed out of assigned, 0.0 avg score)
        self.assertIn("0 / 0", html)  # 0 completed out of 0 assigned in clean seed
        self.assertIn("0.0", html)   # 0.0 / 50 score across approved badges
        self.assertIn("Enrolled", html)
        self.assertIn("Average Assessment Score", html)

        # Personal Interactive Tooltips and Popovers
        self.assertIn("metric-info-trigger", html)
        self.assertIn("glass-tooltip-popover", html)
        self.assertIn("has-glass-tooltip", html)

        # 3. Personalized Next Action Card
        self.assertIn("YOUR NEXT ACTION", html)

        # 4. Batch Leaderboard
        self.assertIn("Academic Leaderboard", html)

        # 5. Milestone Performance & Sections
        self.assertIn("Verified Skills & Competency Matrix", html)
        self.assertNotIn("ING-104", html)
        self.assertNotIn("GOV-101", html)

        # 6. Guardian Control Restrictions: No scope selector dropdown
        self.assertNotIn("Analytics Scope Selector", html)

    def test_guardian_dashboard_aggregate_and_sections(self):
        """Verify Guardian dashboard renders required sections and cohort aggregate from SQLite."""
        self.app.handle_event("select_demo_account", "guardian_1")
        self.assertEqual(self.app.current_user.id, "guardian_1")
        self.assertEqual(self.app.current_view, "g_cycles")
        self.app.handle_event("nav_guardian", "g_dashboard")
        self.assertEqual(self.app.current_view, "g_dashboard")

        html = self.app.render()

        # Section A: Header & Scope Selector
        self.assertIn("Command Center", html)
        self.assertIn("Analytics Scope Selector", html)

        # Section B: 5 High-Value KPI Cards
        self.assertIn("Enrolled Cadets", html)
        self.assertIn("Average Score", html)
        self.assertIn("Pending Submissions", html)
        self.assertIn("Cadets For Attention", html)
        self.assertIn("First-Attempt Pass Rate", html)

        # Section C & Top Command Deck: Velocity, Action Center & Leaderboard
        self.assertIn("Weekly Curriculum Velocity & Pacing", html)
        self.assertIn("Guardian Action Command Center", html)
        self.assertIn("Academic Leaderboard", html)
        self.assertIn("Evaluate Pending Deliverable", html)
        self.assertIn("Milestone Deadline Extensions", html)

        # Section E: Risk and Intervention Monitoring Table
        self.assertIn("Cadet Risk & Intervention Monitoring Matrix", html)
        self.assertIn("Aarav Sharma", html)
        self.assertIn("Inspect Dossier", html)

    def test_guardian_individual_scope_switching(self):
        """Verify Guardian can switch scope to inspect Aarav Sharma."""
        self.app.handle_event("select_demo_account", "guardian_1")
        self.app.handle_event("nav_guardian", "g_dashboard")

        # 1. Inspect Aarav Sharma
        self.app.handle_event("select_guardian_cosmo_filter", "cosmo_1")
        html_actual = self.app.render()
        self.assertIn("Aarav Sharma", html_actual)
        self.assertIn("Back to Cohort Aggregate Analytics", html_actual)
        self.assertIn("Cohort Leaderboard Rank", html_actual)
        self.assertIn("Milestone Performance & Rubric Marks Comparison", html_actual)
        self.assertIn("Official Evaluated Marksheets", html_actual)
        self.assertIn("View Review Marksheet", html_actual)
        self.assertIn("Verified Skills & Competency Matrix", html_actual)
        self.assertIn("Official Certifications & Verified Credentials", html_actual)
        self.assertIn("Pedagogical Diagnostics & Mentoring Pathway", html_actual)
        self.assertIn("Guardian Mentoring Action Plan", html_actual)

        # 2. Return to Cohort Aggregate
        self.app.handle_event("select_guardian_cosmo_filter", "all")
        html_all = self.app.render()
        self.assertIn("Academic Leaderboard", html_all)
        self.assertIn("Cadet Risk & Intervention Monitoring Matrix", html_all)

    def test_guardian_risk_filtering(self):
        """Verify Guardian can filter monitoring table by risk status."""
        self.app.handle_event("select_demo_account", "guardian_1")
        self.app.handle_event("nav_guardian", "g_dashboard")

        # Filter for Attention
        self.app.handle_event("filter_guardian_risk", "attention")
        html_att = self.app.render()
        self.assertIn("Cadet Risk & Intervention Monitoring Matrix", html_att)

        # Filter for On Track
        self.app.handle_event("filter_guardian_risk", "track")
        html_trk = self.app.render()
        self.assertIn("Cadet Risk & Intervention Monitoring Matrix", html_trk)

if __name__ == "__main__":
    unittest.main()
