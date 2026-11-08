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
        """Verify the 5 demo profiles are never in actual users, submissions, or login accounts."""
        # Only 2 actual accounts exist: guardian_1 and cosmo_1
        real_user_ids = set(store.users.keys())
        self.assertEqual(real_user_ids, {"guardian_1", "cosmo_1"})

        # Demo profiles are strictly isolated in dashboard_demo
        demos = get_dashboard_demo_cosmonauts()
        self.assertEqual(len(demos), 5)
        demo_ids = [d["id"] for d in demos]
        self.assertEqual(demo_ids, ["demo_orion", "demo_lyra", "demo_cassian", "demo_kaelen", "demo_seraphina"])

        for d_id in demo_ids:
            self.assertNotIn(d_id, store.users)
            self.assertIsNone(store.get_user_by_id(d_id))
            self.assertEqual(len(store.get_assessments_for_cosmonaut(d_id)), 0)
            self.assertEqual(len(store.get_submissions_for_cosmonaut(d_id)), 0)

        # Verify login view contains only the 2 actual demo accounts
        login_html = self.app.render_login_view()
        self.assertIn("Astraea Nova", login_html)
        self.assertIn("Dr. Elena Vance", login_html)
        for d in demos:
            self.assertNotIn(d["name"], login_html)

    def test_cosmonaut_dashboard_personalization_and_privacy(self):
        """Verify Astraea Nova sees only her actual data and zero demo or peer data."""
        self.app.handle_event("select_demo_account", "cosmo_1")
        self.assertEqual(self.app.current_user.id, "cosmo_1")
        self.assertEqual(self.app.current_view, "c_dashboard")

        html = self.app.render()

        # 1. Personal Header & Identity
        self.assertIn("Welcome back, Astraea Nova", html)
        self.assertIn("Batch: <strong>Orion-24</strong>", html)
        self.assertIn("Dr. Elena Vance", html)

        # 2. Actual KPIs
        self.assertIn("3 / 5", html)  # 3 completed out of 5 assigned
        self.assertIn("48.0", html)   # 48.0 / 50 score across approved badges
        self.assertIn("75.0%", html)  # 3 of 4 first attempt pass rate
        self.assertIn("ING-104", html) # Active milestone
        self.assertIn("Average Assessment Score", html)
        self.assertIn("Excellent Performance", html)

        # Personal Interactive Tooltips and Popovers
        self.assertIn("metric-info-trigger", html)
        self.assertIn("glass-tooltip-popover", html)
        self.assertIn("has-glass-tooltip", html)

        # 3. Personalized Next Action Card
        self.assertIn("YOUR NEXT ACTION", html)
        self.assertIn("Under Guardian Review", html)
        self.assertIn("Track Submission Status", html)

        # 4. Batch Leaderboard (Now accessible to Cosmonaut to view batch mates' scores)
        self.assertIn("Batch Orion-24 Academic Leaderboard", html)
        self.assertIn("Seraphina Vale", html)
        self.assertIn("Orion Blake", html)
        self.assertIn("Lyra Bennett", html)
        self.assertIn("Cassian Reed", html)
        self.assertIn("Kaelen Frost", html)
        self.assertIn("YOU", html)

        # 5. Milestone Performance Bar Graph & Full Sections
        self.assertIn("Milestone Performance & Rubric Marks Comparison", html)
        self.assertIn("GOV-101", html)
        self.assertIn("CUR-102", html)
        self.assertIn("DAT-103", html)
        self.assertIn("ING-104", html)
        self.assertIn("SQL-201", html)
        self.assertIn("Verified Skills & Competency Matrix", html)
        self.assertIn("ReactJS", html)
        self.assertIn("Rating:", html)

        # 6. Guardian Control Restrictions: No scope selector dropdown, no demo profile tag
        self.assertNotIn("Analytics Scope Selector", html)
        self.assertNotIn("DEMONSTRATION ANALYTICS PROFILE", html)

    def test_guardian_dashboard_aggregate_and_sections(self):
        """Verify Guardian dashboard renders all 8 required sections and cohort aggregate."""
        self.app.handle_event("select_demo_account", "guardian_1")
        self.assertEqual(self.app.current_user.id, "guardian_1")
        self.assertEqual(self.app.current_view, "g_dashboard")

        html = self.app.render()

        # Section A: Header & Scope Selector
        self.assertIn("Batch Orion-24 Command Center", html)
        self.assertIn("Analytics Scope Selector", html)
        self.assertIn("All Cosmonauts (Cohort Aggregate — 6 Profiles)", html)
        self.assertNotIn("1 Actual Cosmonaut", html)
        self.assertNotIn("Milestone certifications vs submissions over last 6 weeks", html)

        # Section B: 5 High-Value KPI Cards (Badge Completion Rate removed per instruction)
        self.assertIn("Enrolled Cadets", html)
        self.assertNotIn("Badge Completion Rate", html)
        self.assertIn("Average Score", html)
        self.assertIn("Pending Submissions", html)
        self.assertIn("Cadets For Attention", html)
        self.assertIn("First-Attempt Pass Rate", html)

        # Section C & Top Command Deck: Velocity, Action Center & Leaderboard (Above)
        self.assertIn("Weekly Curriculum Velocity & Pacing", html)
        self.assertIn("Guardian Action Command Center", html)
        self.assertIn("Batch Orion-24 Academic Leaderboard", html)
        self.assertIn("Evaluate Pending Deliverable", html)
        self.assertIn("Milestone Deadline Extensions", html)

        # Section D: Milestone Difficulty & Performance Comparison removed per instruction
        self.assertNotIn("5-Criterion Competency Diagnostic", html)
        self.assertNotIn("Milestone Status Pipeline", html)
        self.assertNotIn("Evaluation Score Distribution", html)
        self.assertNotIn("Milestone Difficulty & Performance Comparison", html)

        # Section E: Risk and Intervention Monitoring Table
        self.assertIn("Cadet Risk & Intervention Monitoring Matrix", html)
        self.assertIn("Astraea Nova", html)
        self.assertIn("Orion Blake", html)
        self.assertIn("Lyra Bennett", html)
        self.assertIn("Cassian Reed", html)
        self.assertIn("Kaelen Frost", html)
        self.assertIn("Seraphina Vale", html)
        self.assertIn("Inspect Dossier", html)

    def test_guardian_individual_scope_switching(self):
        """Verify Guardian can switch scope to inspect Astraea Nova (actual) or Orion Blake (demo)."""
        self.app.handle_event("select_demo_account", "guardian_1")

        # 1. Inspect Astraea Nova (Actual)
        self.app.handle_event("select_guardian_cosmo_filter", "cosmo_1")
        html_actual = self.app.render()
        self.assertIn("Astraea Nova", html_actual)
        self.assertIn("ACTUAL APPLICATION COSMONAUT", html_actual)
        self.assertIn("Back to Cohort Aggregate Analytics", html_actual)
        self.assertIn("Cohort Leaderboard Rank", html_actual)
        self.assertIn("Milestone Performance & Rubric Marks Comparison", html_actual)
        self.assertIn("Official Evaluated Marksheets", html_actual)
        self.assertIn("View Review Marksheet", html_actual)
        self.assertIn("Verified Skills & Competency Matrix", html_actual)
        self.assertIn("/ 10.0", html_actual)
        self.assertIn("Official Certifications & Verified Credentials", html_actual)
        self.assertIn("Pedagogical Diagnostics & Mentoring Pathway", html_actual)
        self.assertIn("Demonstrated Engineering Strengths", html_actual)
        self.assertIn("Targeted Improvement & Growth Areas", html_actual)
        self.assertIn("Guardian Mentoring Action Plan", html_actual)

        # 2. Inspect Orion Blake (Demo Profile)
        self.app.handle_event("select_guardian_cosmo_filter", "demo_orion")
        html_demo = self.app.render()
        self.assertIn("Orion Blake", html_demo)
        self.assertIn("DEMONSTRATION ANALYTICS PROFILE", html_demo)
        self.assertIn("Demonstration Record", html_demo)
        self.assertIn("Back to Cohort Aggregate Analytics", html_demo)
        self.assertIn("Cohort Leaderboard Rank", html_demo)
        self.assertIn("Milestone Performance & Rubric Marks Comparison", html_demo)
        self.assertIn("Official Evaluated Marksheets", html_demo)
        self.assertIn("View Review Marksheet", html_demo)
        self.assertIn("Verified Skills & Competency Matrix", html_demo)
        self.assertIn("/ 10.0", html_demo)
        self.assertIn("Official Certifications & Verified Credentials", html_demo)
        self.assertIn("Pedagogical Diagnostics & Mentoring Pathway", html_demo)
        self.assertIn("Demonstrated Engineering Strengths", html_demo)
        self.assertIn("Targeted Improvement & Growth Areas", html_demo)
        self.assertIn("Guardian Mentoring Action Plan", html_demo)

        # 3. Test other demo profiles have rich skills, certifications & diagnostics
        for demo_id in ["demo_lyra", "demo_cassian", "demo_kaelen", "demo_seraphina"]:
            self.app.handle_event("select_guardian_cosmo_filter", demo_id)
            demo_html = self.app.render()
            self.assertIn("Verified Skills & Competency Matrix", demo_html)
            self.assertIn("Official Certifications & Verified Credentials", demo_html)
            self.assertIn("Pedagogical Diagnostics & Mentoring Pathway", demo_html)
            self.assertIn("Guardian Mentoring Action Plan", demo_html)

        # 3. Return to Cohort Aggregate
        self.app.handle_event("select_guardian_cosmo_filter", "all")
        html_all = self.app.render()
        self.assertIn("Batch Orion-24 Academic Leaderboard", html_all)
        self.assertIn("Cadet Risk & Intervention Monitoring Matrix", html_all)

    def test_guardian_risk_filtering(self):
        """Verify Guardian can filter monitoring table by risk status."""
        self.app.handle_event("select_demo_account", "guardian_1")

        # Filter for Attention
        self.app.handle_event("filter_guardian_risk", "attention")
        html_att = self.app.render()
        # Kaelen Frost (Needs Attention) and Cassian Reed (Monitor) should be present
        self.assertIn("Kaelen Frost", html_att)
        self.assertIn("Cassian Reed", html_att)

        # Filter for On Track - table should not list Kaelen Frost in the monitoring table body
        self.app.handle_event("filter_guardian_risk", "track")
        html_trk = self.app.render()
        table_part = html_trk[html_trk.find("Cadet Risk & Intervention Monitoring Matrix"):]
        self.assertIn("Orion Blake", table_part)
        self.assertIn("Lyra Bennett", table_part)
        self.assertNotIn("Kaelen Frost", table_part)

if __name__ == "__main__":
    unittest.main()
