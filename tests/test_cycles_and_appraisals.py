"""
End-to-End Tests for 6-Month Performance Cycles & Dual-Role Appraisals:
- All cycle-scoped operational data (badges, mappings, projects, submissions, marksheets, notifications)
  lives inside its active cycle_id and backfills legacy data cleanly into cycle_1.
- Dual-role performance tracking per candidate (both As Cosmonaut AND As Reviewer).
- End-of-cycle score, tier, optional compensation/hike override, and finalization/closure.
- Closed-cycle read-only lock & Topbar cycle switching between Active and Closed archives.
- Starting a new 6-month cycle retains the same cohort users (carrying over promotions & new salary)
  while isolating badges, mappings, projects, submissions, and marks inside Cycle 2.
- Cosmonaut/Reviewer Past Cycles & Appraisals UI view (`c_cycles`) & FastAPI `/api/v1/cycles` endpoints.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from starapp.app import StarAppController
from starapp.models import add_six_months_iso
from starapp.storage import store
from starapp.cycles import compute_cycle_candidate_performance


class TestSixMonthCyclesAndAppraisals(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        self.ctrl.initialize()

    def test_01_schema_backfill_and_six_month_date_helper(self):
        """Verify 6-month inclusive end_date helper and initial cycle_1 backfill + enrollments."""
        self.assertEqual(add_six_months_iso("2026-07-01", 6), "2026-12-31")
        self.assertEqual(add_six_months_iso("2026-01-01", 6), "2026-06-30")
        self.assertEqual(add_six_months_iso("2026-11-25", 6), "2027-05-24")

        cycles = store.get_all_cycles()
        self.assertGreaterEqual(len(cycles), 1)
        c1 = store.get_cycle("cycle_1")
        self.assertIsNotNone(c1)
        self.assertEqual(c1.status, "active")

        enrollments = store.get_cycle_enrollments("cycle_1")
        self.assertGreaterEqual(len(enrollments), 36)

        # Every seeded badge belongs to cycle_1
        badges = store.get_all_badges(cycle_id="cycle_1")
        self.assertGreater(len(badges), 0)
        for b in badges:
            self.assertEqual(b.cycle_id, "cycle_1")

    def test_02_full_cycle_lifecycle_dual_role_metrics_close_and_rollover(self):
        """
        Run a full workflow inside Cycle 1, calculate performance for BOTH Cosmonaut (m_b1_1)
        and Reviewer (m_b2_1), override & finalize Cycle 1, verify Read-Only lock,
        start Cycle 2 (6 months) with same users & isolated fresh data, and verify switcher.
        """
        # 1. Guardian creates & submits a B1 badge to Reviewer m_b2_1 inside Cycle 1
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.ctrl.handle_event("save_generated_badge", json.dumps({
            "band": "B1",
            "power": "Tech",
            "capability": "Data & Machine",
            "skill": "Hardware",
            "title": "Cycle 1 Hardware Architecture",
            "code": "B1-HDW-C1",
            "description": "Foundational hardware systems milestone for Cycle 1"
        }))
        saved = [b for b in store.get_all_badges(cycle_id="cycle_1") if b.title == "Cycle 1 Hardware Architecture"]
        self.assertEqual(len(saved), 1)
        b_id = saved[0].id

        self.ctrl.handle_event("select_badge_reviewer", "m_b2_1")
        self.ctrl.handle_event("send_badge_review_request", b_id)

        # 2. Reviewer m_b2_1 accepts proposal & approves badge
        self.ctrl.handle_event("select_demo_account", "m_b2_1")
        self.ctrl.handle_event("approve_submitted_badge", json.dumps({"badge_id": b_id, "notes": "Approved for Cycle 1."}))

        # 3. Guardian maps m_b1_1 to m_b2_1 and publishes badge
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.ctrl.handle_event("select_mapping_band", "B1")
        self.ctrl.mapping_selected_badge = "Cycle 1 Hardware Architecture"
        self.ctrl.mapping_selected_badge_id = b_id
        self.ctrl.mapping_selected_cosmonauts = ["m_b1_1"]
        self.ctrl.mapping_selected_reviewers = ["m_b2_1"]
        self.ctrl.mapping_review_dates = ["2026-11-18", "2026-11-19", "2026-11-20"]
        self.ctrl.handle_event("save_band_mapping", "{}")
        self.ctrl.handle_event("publish_badge", b_id)

        # 4. Reviewer m_b2_1 creates & releases project for m_b1_1
        self.ctrl.handle_event("select_demo_account", "m_b2_1")
        self.ctrl.handle_event("send_reviewer_project", json.dumps({
            "badge_id": b_id,
            "reviewer_id": "m_b2_1",
            "title": "Hardware Pipeline Lab",
            "description": "Implement CPU/Memory bottleneck analyzer.",
            "outcomes": ["Pipeline telemetry script"],
            "requirements": ["Include PDF & Python code"],
            "deliverables": {"code": {"name": "hw.py"}, "pdf": {"name": "hw.pdf"}, "github": {"name": "Repo"}},
            "cosmonaut_ids": ["m_b1_1"],
            "status": "released"
        }))

        # 5. Cosmonaut m_b1_1 submits deliverables
        self.ctrl.handle_event("select_demo_account", "m_b1_1")
        self.ctrl.handle_event("submit_project_deliverables", json.dumps({
            "badge_id": b_id,
            "pdf_name": "aarav_hw.pdf",
            "pdf_payload": "data:application/pdf;base64,JVBERi0xLjQK",
            "code_name": "hw.py",
            "code_payload": "print('hw ok')",
            "github_url": "https://github.com/starapp/hw-c1"
        }))
        subs = store.get_submissions_for_cosmonaut("m_b1_1", b_id, cycle_id="cycle_1")
        self.assertEqual(len(subs), 1)
        sub_id = subs[0].id

        # 6. Reviewer m_b2_1 evaluates submission (44/50 -> 88%)
        self.ctrl.handle_event("select_demo_account", "m_b2_1")
        self.ctrl.handle_event("submit_reviewer_assessment", json.dumps({
            "submission_id": sub_id,
            "bu": 9, "ar": 9, "tk": 9, "pr": 8, "qa": 9,
            "decision": "approve",
            "feedback": "Solid execution in Cycle 1."
        }))

        # 7. Guardian earns badge with final 45/50 (90%)
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.ctrl.handle_event("submit_evaluation_marksheet", json.dumps({
            "submission_id": sub_id,
            "bu": 9, "ar": 9, "tk": 9, "pr": 9, "qa": 9,
            "decision": "approve",
            "feedback": "Earned in Cycle 1."
        }))

        # 8. Guardian opens Cycles & Performance and computes dual-role metrics
        self.ctrl.handle_event("nav_guardian", "g_cycles")
        self.ctrl.handle_event("calculate_cycle_appraisals", json.dumps({"cycle_id": "cycle_1"}))
        g_cycles_html = self.ctrl.render()
        self.assertIn("Candidate Cycle Performance", g_cycles_html)
        self.assertNotIn("starapp-sidebar-cycle-pill", g_cycles_html)
        self.assertNotIn("starapp-cycle-topbar", g_cycles_html)

        rows = {r["user_id"]: r for r in compute_cycle_candidate_performance("cycle_1", store)}
        r_cosmo = rows["m_b1_1"]
        self.assertGreaterEqual(r_cosmo["badges_earned"], 1)
        self.assertEqual(r_cosmo["avg_marks"], 45.0)
        self.assertEqual(r_cosmo["avg_percentage"], 90.0)
        self.assertTrue(r_cosmo["cosmo_has_activity"])

        r_rev = rows["m_b2_1"]
        self.assertTrue(r_rev["reviewer_has_activity"])
        self.assertGreaterEqual(r_rev["badge_reviews_completed"], 1)
        self.assertGreaterEqual(r_rev["projects_released"], 1)
        self.assertGreaterEqual(r_rev["submissions_graded"], 1)
        self.assertEqual(r_rev["reviewer_avg_marks_given"], 44.0)

        # 9. Guardian adjusts m_b1_1 appraisal & finalizes Cycle 1
        self.ctrl.handle_event("update_cycle_appraisal", json.dumps({
            "cycle_id": "cycle_1",
            "user_id": "m_b1_1",
            "base_salary": 100000.0,
            "approved_hike_pct": 20.0,
            "bonus_amount": 5000.0,
            "recommended_promotion_band": "B2",
            "guardian_remarks": "Promoted to B2 after Cycle 1 excellence."
        }))
        self.ctrl.handle_event("finalize_and_close_cycle", json.dumps({"cycle_id": "cycle_1"}))
        c1 = store.get_cycle("cycle_1")
        self.assertEqual(c1.status, "closed")

        # Read-only lock blocks mutations while viewing closed Cycle 1
        self.ctrl.handle_event("save_generated_badge", json.dumps({
            "band": "B1", "power": "Tech", "capability": "Data & Machine", "skill": "Signals",
            "title": "Blocked Closed Cycle Badge"
        }))
        self.assertEqual(self.ctrl.flash_type, "error")
        self.assertIn("closed", (self.ctrl.last_flash_message or "").lower())
        self.assertFalse(any(b.title == "Blocked Closed Cycle Badge" for b in store.get_all_badges(cycle_id="cycle_1")))

        # 10. Guardian creates Cycle 2 (next 6 months) keeping all people, carrying m_b1_1 promotion & salary, with clean curriculum
        self.ctrl.handle_event("create_six_month_cycle", json.dumps({
            "name": "Cycle 2 (Jan-Jun 2027)",
            "code": "C2-2027",
            "start_date": "2027-01-01",
            "notes": "Fresh 6-month cohort cycle"
        }))
        c2_id = self.ctrl.selected_cycle_id
        self.assertNotEqual(c2_id, "cycle_1")
        c2 = store.get_cycle(c2_id)
        self.assertEqual(c2.end_date, "2027-06-30")
        self.assertEqual(c2.status, "active")

        # Same people enrolled; m_b1_1 carried over with B2 promotion and 120000 new salary
        c2_enrs = {e.user_id: e for e in store.get_cycle_enrollments(c2_id)}
        self.assertGreaterEqual(len(c2_enrs), 36)
        self.assertEqual(c2_enrs["m_b1_1"].band_code, "B2")
        self.assertEqual(c2_enrs["m_b1_1"].base_salary, 120000.0)

        # Cycle 2 starts completely fresh with 0 badges/submissions/mappings
        self.assertEqual(len(store.get_all_badges(cycle_id=c2_id)), 0)
        self.assertEqual(len(store.get_all_submissions(cycle_id=c2_id)), 0)
        self.assertEqual(len(store.get_band_mappings(cycle_id=c2_id)), 0)

        # Creating a badge in Cycle 2 with SAME Band & Skill must succeed WITHOUT touching Cycle 1 badge!
        self.ctrl.handle_event("save_generated_badge", json.dumps({
            "band": "B1",
            "power": "Tech",
            "capability": "Data & Machine",
            "skill": "Hardware",
            "title": "Cycle 2 Hardware Fresh Badge",
            "code": "B1-HDW-C2"
        }))
        c2_badges = store.get_all_badges(cycle_id=c2_id)
        c1_badges = store.get_all_badges(cycle_id="cycle_1")
        self.assertEqual(len(c2_badges), 1)
        self.assertEqual(c2_badges[0].title, "Cycle 2 Hardware Fresh Badge")
        self.assertTrue(any(b.title == "Cycle 1 Hardware Architecture" for b in c1_badges))
        self.assertFalse(any(b.title == "Cycle 2 Hardware Fresh Badge" for b in c1_badges))

        # 11. Topbar cycle switching preserves Cycle 1 vs Cycle 2 view isolation
        self.ctrl.handle_event("select_cycle", "cycle_1")
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        c1_view_html = self.ctrl.render()
        self.assertIn("Cycle 1 Hardware Architecture", c1_view_html)
        self.assertNotIn("Cycle 2 Hardware Fresh Badge", c1_view_html)

        self.ctrl.handle_event("select_cycle", c2_id)
        c2_view_html = self.ctrl.render()
        self.assertIn("Cycle 2 Hardware Fresh Badge", c2_view_html)
        self.assertNotIn("Cycle 1 Hardware Architecture", c2_view_html)

        # 12. Cosmonaut Past Cycles & Appraisals view shows Cycle 1 & Cycle 2 performance
        self.ctrl.handle_event("select_demo_account", "m_b2_1")
        self.ctrl.handle_event("nav_cosmonaut", "c_cycles")
        cosmo_cycles_html = self.ctrl.render()
        self.assertIn("My 6-Month Performance Cycles", cosmo_cycles_html)
        self.assertIn("Cycle 1", cosmo_cycles_html)
        self.assertIn("Cycle 2 (Jan-Jun 2027)", cosmo_cycles_html)

    def test_03_fastapi_cycles_rest_api_endpoints(self):
        """Verify FastAPI /api/v1/cycles endpoints work cleanly over HTTP."""
        with TestClient(app) as client:
            # The cycles API is guardian-only: authenticate through the real login endpoint (cookie session).
            res_login = client.post("/api/v1/auth/login", json={"username_or_email": "admin", "password": "123456789", "selected_role": "guardian"})
            self.assertEqual(res_login.status_code, 200, res_login.text)
            res_list = client.get("/api/v1/cycles/")
            self.assertEqual(res_list.status_code, 200)
            body = res_list.json()
            self.assertEqual(body["active_cycle_id"], "cycle_1")

            res_perf = client.get("/api/v1/cycles/cycle_1/performance")
            self.assertEqual(res_perf.status_code, 200)
            self.assertGreaterEqual(len(res_perf.json()["candidates"]), 30)

            res_calc = client.post("/api/v1/cycles/cycle_1/calculate")
            self.assertEqual(res_calc.status_code, 200)
            self.assertTrue(res_calc.json()["success"])

    def test_04_global_cycle_filter_and_restructured_sidebars(self):
        """Verify Global Cycle Filter across Guardian 4-pillar shell and ordered Cosmonaut/Reviewer sidebars."""
        import json as _json
        self.ctrl.handle_event("login", _json.dumps({"username": "guardian"}))
        self.assertEqual(self.ctrl.current_view, "g_cycles")
        p_html = self.ctrl.render()
        self.assertNotIn("starapp-cycle-topbar", p_html)
        self.assertNotIn("starapp-sidebar-cycle-pill", p_html)
        self.assertLess(p_html.find('data-nav-id="g_cycles"'), p_html.find('data-nav-id="g_learning"'))
        self.assertLess(p_html.find('data-nav-id="g_learning"'), p_html.find('data-nav-id="g_earning"'))
        self.assertLess(p_html.find('data-nav-id="g_earning"'), p_html.find('data-nav-id="g_contribution"'))

        # Create Cycle 2 and apply globally across Learning, Earning, Contribution
        self.ctrl.handle_event("create_six_month_cycle", _json.dumps({
            "name": "Cycle 2 Global Filter",
            "code": "C2-GF",
            "start_date": "2027-01-01",
            "auto_close_previous": True,
            "notes": "Test cycle"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")
        self.ctrl.handle_event("nav_guardian", "g_earning")
        self.assertIn("Cycle 2 Global Filter", self.ctrl.render())
        self.ctrl.handle_event("nav_guardian", "g_contribution")
        self.assertIn("Cycle 2 Global Filter", self.ctrl.render())
        self.ctrl.handle_event("nav_guardian", "g_learning")
        lrn_html = self.ctrl.render()
        self.assertIn("Cycle 2 Global Filter", lrn_html)
        self.assertIn("Band B1", lrn_html)

        # Reviewer-eligible Cosmonaut sidebar order
        self.ctrl.handle_event("select_demo_account", "m_b2_1")
        self.assertEqual(self.ctrl.current_view, "c_choose_cycle")
        c_html = self.ctrl.render()
        self.assertNotIn("starapp-cycle-topbar", c_html)
        ids = [
            "c_choose_cycle", "c_badge_reviews", "c_requests", "c_assessments",
            "c_submission", "c_results", "c_profile", "c_extensions", "c_cycles"
        ]
        positions = [c_html.find(f'data-nav-id="{nid}"') for nid in ids]
        self.assertTrue(all(p > 0 for p in positions), f"Missing cosmonaut nav ids: {positions}")
        self.assertEqual(positions, sorted(positions), "Cosmonaut/Reviewer sidebar order mismatch")
        self.assertNotIn('data-nav-id="c_roadmap"', c_html)
        self.assertNotIn('data-nav-id="c_materials"', c_html)

        # Band B1 learner (non-reviewer) omits reviewer tabs while keeping exact remaining order
        self.ctrl.handle_event("select_demo_account", "cosmo_1")
        b1_html = self.ctrl.render()
        self.assertNotIn('data-nav-id="c_badge_reviews"', b1_html)
        self.assertNotIn('data-nav-id="c_requests"', b1_html)
        self.assertNotIn('data-nav-id="c_assessments"', b1_html)
        b1_ids = ["c_choose_cycle", "c_submission", "c_results", "c_profile", "c_extensions", "c_cycles"]
        b1_pos = [b1_html.find(f'data-nav-id="{nid}"') for nid in b1_ids]
        self.assertEqual(b1_pos, sorted(b1_pos))

    def test_05_previous_cycle_synthetic_data_and_calendar_activation(self):
        """Verify seeded cycle_0 previous cycle filtering across all Learning views and calendar cycle activation for Cosmonauts & Reviewers."""
        import json as _json
        self.ctrl.handle_event("login", _json.dumps({"username": "guardian"}))
        self.assertEqual(store.get_active_cycle_id(), "cycle_1")

        # 1. Choose Cycle displays both cycle_1 (Active) and cycle_0 (Previous Cycle archive) + modal creator trigger
        cyc_html = self.ctrl.render()
        self.assertIn("Previous Cycle (Jan–Jun 2026)", cyc_html)
        self.assertIn("open_create_cycle_modal", cyc_html)
        self.assertIn("Set Active", cyc_html)
        self.assertNotIn("inline-calendar-cycle-creator", cyc_html)
        self.assertNotIn("Viewing Previous / Closed Cycle Archive", cyc_html)
        self.assertNotIn("Review dual-role contributions across the 6-month cycle", cyc_html)
        self.assertNotIn("Top Performer", cyc_html)
        self.assertNotIn("Attention Queue", cyc_html)
        self.assertNotIn("Appraisal &amp; Hike", cyc_html)
        self.assertNotIn("Switch Cycle Filter", cyc_html)
        self.ctrl.handle_event("open_create_cycle_modal", "{}")
        modal_html = self.ctrl.render()
        self.assertIn("lg-cycle-calendar-mount", modal_html)
        self.assertIn("create_six_month_cycle", modal_html)
        self.ctrl.handle_event("close_modal", "{}")

        # 2. Guardian clicks on cycle_0 -> entire Learning workspace filters to Previous Cycle data
        self.ctrl.handle_event("select_cycle", "cycle_0")
        self.assertEqual(self.ctrl.selected_cycle_id, "cycle_0")
        self.assertEqual(store.get_active_cycle_id(), "cycle_1")

        self.ctrl.handle_event("nav_guardian", "g_learning")
        lrn_c0 = self.ctrl.render()
        self.assertIn("Previous Cycle (Jan–Jun 2026)", lrn_c0)
        self.assertIn("Band B1", lrn_c0)

        self.ctrl.handle_event("select_create_badge_band", "B1")
        cb_c0 = self.ctrl.render()
        self.assertIn("Python &amp; Backend API Foundations", cb_c0)
        self.assertIn("Relational SQL &amp; Schema Design", cb_c0)

        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        self.assertIn("Python &amp; Backend API Foundations", self.ctrl.render())
        self.ctrl.handle_event("select_create_badge_band", "")      # no active band -> the queue lists every band
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        ba_c0 = self.ctrl.render()
        self.assertIn("Zero-Trust Service Mesh Proposal", ba_c0)

        self.ctrl.handle_event("nav_guardian", "g_mapping")
        mp_c0 = self.ctrl.render()
        self.assertIn("Python &amp; Backend API Foundations", mp_c0)

        self.ctrl.handle_event("nav_guardian", "g_allotment")
        al_c0 = self.ctrl.render()
        self.assertIn("Python &amp; Backend API Foundations", al_c0)      # cards are identified by badge name (the code chip was removed)
        self.assertIn("Zero-Trust Service Mesh Proposal", al_c0)

        self.ctrl.handle_event("nav_guardian", "g_reviews")
        rv_c0 = self.ctrl.render()
        self.assertIn("C0-B1-PY-01", rv_c0)

        self.ctrl.handle_event("nav_guardian", "g_extensions")
        ex_c0 = self.ctrl.render()
        self.assertIn("2026-02-23", ex_c0)

        # Switching back to cycle_1 cleanly removes cycle_0 items
        self.ctrl.handle_event("select_cycle", "cycle_1")
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        ba_c1 = self.ctrl.render()
        self.assertNotIn("Zero-Trust Service Mesh Proposal", ba_c1)

        # 3. Guardian creates & activates a cycle using calendar dates -> becomes Active for all Cosmonauts & Reviewers
        self.ctrl.handle_event("create_six_month_cycle", _json.dumps({
            "name": "H1 2027 Calendar Cycle",
            "code": "C2-2027",
            "start_date": "2027-01-01",
            "end_date": "2027-06-30",
            "auto_close_previous": True,
            "set_as_active": True,
            "notes": "Calendar selected cycle"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")
        new_active = store.get_active_cycle_id()
        self.assertEqual(self.ctrl.selected_cycle_id, new_active)
        self.assertEqual(store.get_cycle(new_active).name, "H1 2027 Calendar Cycle")

        # All Cosmonauts and Reviewers logging in automatically land in the Guardian-activated cycle
        cosmo_ctrl = StarAppController()
        cosmo_ctrl.handle_event("login", _json.dumps({"username": "aarav.sharma"}))
        self.assertEqual(cosmo_ctrl.selected_cycle_id, new_active)
        rev_ctrl = StarAppController()
        rev_ctrl.handle_event("select_demo_account", "m_b2_1")
        self.assertEqual(rev_ctrl.selected_cycle_id, new_active)

        # Guardian can also explicitly activate an existing cycle cleanly
        self.ctrl.handle_event("activate_cycle", _json.dumps({"cycle_id": "cycle_1"}))
        self.assertEqual(store.get_active_cycle_id(), "cycle_1")
        rev_ctrl.handle_event("login", _json.dumps({"username": "rohan.deshmukh"}))
        self.assertEqual(rev_ctrl.selected_cycle_id, "cycle_1")

    def test_06_all_bands_b1_to_b6_and_all_stages_persisted_in_db(self):
        """Verify SQLite persistence across all Bands B1–B6 and every workflow stage at band & person level."""
        import json as _json

        # A. Verify seeded Previous Cycle (cycle_0) spans all 6 bands B1–B6 and all stage tables
        conn = store.db.conn
        c0_bands = {r[0] for r in conn.execute("SELECT DISTINCT target_band FROM badges WHERE cycle_id='cycle_0'").fetchall()}
        self.assertEqual(c0_bands, {"B1", "B2", "B3", "B4", "B5", "B6"})

        c0_event_types = {r[0] for r in conn.execute("SELECT DISTINCT event_type FROM activity_events WHERE cycle_id='cycle_0'").fetchall()}
        for expected_evt in (
            "badge_created", "badge_approved", "badge_mapped", "cadet_mapped_to_badge",
            "badge_published", "reviewer_project_assigned", "project_submitted",
            "reviewer_assessment_completed", "badge_awarded", "retake_required",
            "extension_requested", "extension_approved", "extension_rejected", "cycle_closed"
        ):
            self.assertIn(expected_evt, c0_event_types, f"Missing cycle_0 audit log type: {expected_evt}")

        # B. Execute live E2E workflow in cycle_1 for Bands B1..B5 (with peer higher-band reviewers) + B6 (Executive Council)
        band_matrix = [
            # (band, cosmo_id, reviewer_id)
            ("B1", "m_b1_1", "m_b2_2"),
            ("B2", "m_b2_1", "m_b3_1"),
            ("B3", "m_b3_1", "m_b4_1"),
            ("B4", "m_b4_1", "m_b5_1"),
            ("B5", "m_b5_1", "m_b6_1"),
        ]
        for band, cosmo_id, rev_id in band_matrix:
            self.ctrl.handle_event("login", _json.dumps({"username": "guardian"}))
            code = f"{band}-AUDIT-99"
            title = f"Band {band} Audit Capstone"
            self.ctrl.handle_event("create_badge", _json.dumps({
                "code": code,
                "title": title,
                "target_band": band,
                "power": "Tech",
                "capability": "Systems & Cloud",
                "skill": f"AuditSkill{band}",
                "reviewer_id": rev_id,
                "learning_outcomes": "Design system,Validate rubric",
                "learning_topics": "Design,Testing",
                "project_requirements": "Submit code + PDF + GitHub",
            }))
            b_obj = next(b for b in store.get_all_badges(cycle_id="cycle_1") if b.code == code)

            # Higher-band reviewer approves badge
            rev_ctrl = StarAppController()
            rev_ctrl.handle_event("select_demo_account", rev_id)
            rev_ctrl.handle_event("approve_submitted_badge", b_obj.id)
            self.assertEqual(store.get_badge(b_obj.id).workflow_status, "approved")

            # Guardian sends mapping request -> reviewer accepts (verifying log + notification saved!) -> execute mapping
            self.ctrl.handle_event("nav_guardian", "g_mapping")
            self.ctrl.handle_event("select_mapping_band", band)
            self.ctrl.handle_event("select_mapping_badge", _json.dumps({"badge_id": b_obj.id, "badge": title}))
            self.ctrl.mapping_selected_cosmonauts = [cosmo_id]
            self.ctrl.mapping_selected_reviewers = [rev_id]
            self.ctrl.handle_event("send_mapping_requests", "{}")
            req_id = f"req_{band}_{b_obj.id}_{rev_id}"
            rev_ctrl.handle_event("accept_mapping_request", req_id)
            self.ctrl.handle_event("execute_cosmonaut_mapping", "{}")

            # Publish & configure timeline
            self.ctrl.handle_event("publish_badge", b_obj.id)
            self.ctrl.handle_event("save_allotment_timeline", _json.dumps({
                "badge_id": b_obj.id, "submission_deadline": "2026-12-18", "review_date": "2026-12-20"
            }))

            # Reviewer creates draft then releases project prompt to mapped cadet
            rev_ctrl.handle_event("send_reviewer_project", _json.dumps({
                "badge_id": b_obj.id, "title": f"{band} Spec", "description": "Deliver system", "status": "draft"
            }))
            rev_ctrl.handle_event("send_reviewer_project", _json.dumps({
                "badge_id": b_obj.id, "title": f"{band} Spec", "description": "Deliver system", "status": "released"
            }))

            # Cosmonaut submits deliverables + requests extension -> Guardian approves extension
            c_ctrl = StarAppController()
            c_ctrl.handle_event("select_demo_account", cosmo_id)
            c_ctrl.handle_event("submit_project_deliverables", _json.dumps({
                "badge_id": b_obj.id,
                "code_name": f"{band.lower()}.py", "code_payload": "def main(): return 1",
                "pdf_name": f"{band.lower()}.pdf", "pdf_payload": "Architecture report",
                "github_url": f"https://github.com/starapp/{band.lower()}-audit"
            }))
            c_ctrl.handle_event("submit_deadline_extension_request", _json.dumps({
                "badge_id": b_obj.id, "proposed_deadline": "2026-12-22", "reason": "Benchmark suite expansion"
            }))
            ext_id = store.get_extensions_for_cosmonaut(cosmo_id)[0].id
            self.ctrl.handle_event("submit_extension_decision", _json.dumps({
                "extension_id": ext_id, "decision": "approved", "response_note": "Approved for Band benchmark"
            }))

            # Reviewer & Guardian 50-mark evaluations -> Gold completion
            sub = store.get_submissions_for_cosmonaut(cosmo_id, b_obj.id, cycle_id="cycle_1")[-1]
            rev_ctrl.handle_event("submit_reviewer_assessment", _json.dumps({
                "submission_id": sub.id, "bu": 9, "ar": 9, "tk": 9, "pr": 9, "qa": 9, "overall_feedback": f"{band} reviewer pass"
            }))
            self.ctrl.handle_event("submit_evaluation_rubric", _json.dumps({
                "submission_id": sub.id, "bu": 9, "ar": 9, "tk": 9, "pr": 9, "qa": 9,
                "decision": "approve", "overall_feedback": f"{band} guardian pass"
            }))

            # Direct SQLite assertions per Band and per Person
            self.assertEqual(conn.execute("SELECT target_band FROM badges WHERE id=?", (b_obj.id,)).fetchone()[0], band)
            self.assertEqual(conn.execute("SELECT status, reviewer_id FROM badge_timelines WHERE badge_id=? AND cosmonaut_id=?", (b_obj.id, cosmo_id)).fetchone()[:], ("completed", rev_id))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM assessment_marksheets WHERE badge_id=? AND cosmonaut_id=?", (b_obj.id, cosmo_id)).fetchone()[0], 2)
            self.assertGreaterEqual(conn.execute("SELECT COUNT(*) FROM activity_events WHERE badge_id=? AND cosmonaut_id=?", (b_obj.id, cosmo_id)).fetchone()[0], 5)
            self.assertGreaterEqual(conn.execute("SELECT COUNT(*) FROM notifications WHERE recipient_id=?", (cosmo_id,)).fetchone()[0], 4)

        # C. Band B6 (Executive Council): peer review forbidden, direct Executive Council workflow persists cleanly
        bad_ok, _ = store.verify_reviewer_eligibility("m_b6_2", "B6")
        self.assertFalse(bad_ok, "Rule 1 must forbid B6 peer reviewers")
        self.ctrl.handle_event("login", _json.dumps({"username": "guardian"}))
        self.ctrl.handle_event("save_generated_badge", _json.dumps({
            "band": "B6", "power": "Business", "capability": "Strategy & Scale", "skill": "ExecutiveAuditB6",
            "title": "Band B6 Executive Milestone"
        }))
        b6 = next(b for b in store.get_all_badges(cycle_id="cycle_1") if getattr(b, "target_band", "") == "B6")
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B6")
        self.ctrl.handle_event("select_mapping_badge", _json.dumps({"badge_id": b6.id, "badge": b6.title}))
        self.ctrl.mapping_selected_cosmonauts = ["m_b6_1"]
        self.ctrl.mapping_selected_reviewers = []
        self.ctrl.handle_event("save_band_mapping", "{}")
        self.ctrl.handle_event("publish_badge", b6.id)
        b6_c = StarAppController()
        b6_c.handle_event("select_demo_account", "m_b6_1")
        b6_c.handle_event("submit_project_deliverables", _json.dumps({
            "badge_id": b6.id, "code_name": "b6.py", "code_payload": "pass",
            "pdf_name": "b6.pdf", "pdf_payload": "Strategy", "github_url": "https://github.com/starapp/b6"
        }))
        b6_sub = store.get_submissions_for_cosmonaut("m_b6_1", b6.id, cycle_id="cycle_1")[-1]
        self.ctrl.handle_event("submit_evaluation_rubric", _json.dumps({
            "submission_id": b6_sub.id, "bu": 9.5, "ar": 9.5, "tk": 9.5, "pr": 9.5, "qa": 9.5,
            "decision": "approve", "overall_feedback": "Executive Council approved"
        }))
        self.assertEqual(conn.execute("SELECT status FROM badge_timelines WHERE badge_id=? AND cosmonaut_id='m_b6_1'", (b6.id,)).fetchone()[0], "completed")

        # Verify mapping_request_accepted & timeline_configured & draft activity logs were persisted in SQLite
        c1_evts = {r[0] for r in conn.execute("SELECT DISTINCT event_type FROM activity_events WHERE cycle_id='cycle_1'").fetchall()}
        for required_log in ("mapping_request_accepted", "timeline_configured", "reviewer_project_draft_saved", "cadet_mapped_to_badge", "milestone_published_for_cadet", "badge_awarded"):
            self.assertIn(required_log, c1_evts, f"Missing live DB audit log: {required_log}")


if __name__ == "__main__":
    unittest.main()
