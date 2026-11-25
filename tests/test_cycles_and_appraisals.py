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
        self.assertIn("starapp-cycle-topbar", g_cycles_html)

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


if __name__ == "__main__":
    unittest.main()
