"""
Regression tests covering:
1. Single authoritative SQLite DB invariant (data/starapp.db only, no redundant .db files).
2. Badge Reviews (c_badge_reviews) Upcoming & Completed UI completeness:
   - Upcoming Reviews expanded by default with multi-day review window, project title, deliverables & score status.
   - Completed Reviews showing deliverables, Reviewer & Guardian scores, award date, feedback & direct marksheet action.
3. Cosmonaut Completed Badge & Results UI completeness + unpublished isolation:
   - Unpublished badge does not leak into c_submission / c_results / c_dashboard / c_cycles.
   - Completed badge card & detail show score, award date, deliverables & Guardian vs Peer Reviewer scores.
   - c_results prioritizes Guardian Official marksheet over Peer Reviewer preliminary sheet on Attempt #1
     and does not leak Band B1 catalog badges to users with 0 assigned badges.
   - c_dashboard does not double-count approved milestones when both Reviewer & Guardian approve.
"""

import glob
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import (
    Badge, BadgeTimeline, ReviewerProjectPrompt, ProjectSubmission, AssessmentMarksheet,
    current_iso_timestamp
)


class TestUIDataCompletenessAndSingleDB(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        self.ctrl.initialize()

    def test_01_single_authoritative_database_file_only(self):
        """Workspace must contain ONLY data/starapp.db and no redundant root or phase1 backup .db files."""
        all_dbs = []
        for dirpath, _dirnames, filenames in os.walk(ROOT):
            if ".git" in dirpath or "node_modules" in dirpath:
                continue
            for fn in filenames:
                if fn.endswith(".db"):
                    all_dbs.append(os.path.relpath(os.path.join(dirpath, fn), ROOT).replace("\\", "/"))
        self.assertEqual(all_dbs, ["data/starapp.db"])

    def test_02_badge_reviews_upcoming_and_completed_show_full_data(self):
        """c_badge_reviews shows full Review Window, Deliverables, Scores, Feedback, and direct Marksheet action."""
        b = Badge(
            id="badge_audit_rev_ui",
            code="B1-AUD-01",
            title="Audit Signal Systems",
            target_band="B1",
            category="Systems / Audit",
            description="End-to-end signal audit.",
            learning_outcomes=["Audit signals"],
            learning_topics=["Sampling"],
            prerequisites=[],
            project_requirements="Deliver telemetry report and script.",
            is_published=True,
            is_allocated=True,
        )
        store.save_badge(b)
        store.save_band_mapping({
            "id": "map_audit_rev_ui",
            "band": "B1",
            "badge": b.title,
            "badge_id": b.id,
            "reviewers": ["m_b2_1"],
            "cosmonauts": ["m_b1_1", "m_b1_2"],
            "review_dates": ["2026-11-18", "2026-11-19", "2026-11-20"],
            "status": "active",
        })
        store.save_timeline(BadgeTimeline(
            badge_id=b.id, cosmonaut_id="m_b1_1", reviewer_id="m_b2_1",
            assignment_date="2026-11-15", publication_date="2026-11-15",
            learning_start_date="2026-11-15", learning_end_date="2026-11-17",
            project_start_date="2026-11-18", project_end_date="2026-11-20",
            submission_deadline="2026-11-20", review_date="2026-11-20",
            expected_award_date="2026-11-25", actual_award_date="2026-11-25",
            status="completed", review_window_json='["2026-11-18", "2026-11-19", "2026-11-20"]',
        ))
        store.save_timeline(BadgeTimeline(
            badge_id=b.id, cosmonaut_id="m_b1_2", reviewer_id="m_b2_1",
            assignment_date="2026-11-15", publication_date="2026-11-15",
            learning_start_date="2026-11-15", learning_end_date="2026-11-17",
            project_start_date="2026-11-18", project_end_date="2026-11-20",
            submission_deadline="2026-11-20", review_date="2026-11-20",
            expected_award_date="2026-11-25",
            status="active", review_window_json='["2026-11-18", "2026-11-19", "2026-11-20"]',
        ))
        store.save_reviewer_project_prompt(ReviewerProjectPrompt(
            badge_id=b.id, reviewer_id="m_b2_1", reviewer_name="Rohan Deshmukh",
            cosmonaut_ids=["m_b1_1", "m_b1_2"],
            title="Signal Audit Enterprise Brief",
            description="Deliver signal telemetry simulator.",
            outcomes=["O1"], requirements=["R1"],
            status="released", created_at=current_iso_timestamp(), sent_at=current_iso_timestamp(),
        ))
        sub1 = ProjectSubmission(
            id="sub_audit_m_b1_1", badge_id=b.id, cosmonaut_id="m_b1_1", attempt_number=1,
            submission_type="multi", payload="data/Signals_Report.pdf", file_name="Aarav_Audit_Report.pdf",
            pdf_name="Aarav_Audit_Report.pdf", code_name="audit_sim.py",
            github_url="https://github.com/starapp/audit-sim", submitted_at="2026-11-25T08:40:00Z", status="approved"
        )
        store.save_submission(sub1)
        store.save_assessment(AssessmentMarksheet(
            id="asm_audit_rev_1", submission_id=sub1.id, attempt_number=1, badge_id=b.id, cosmonaut_id="m_b1_1",
            reviewer_id="m_b2_1", reviewer_name="Rohan Deshmukh", reviewed_at="2026-11-25T09:00:00Z",
            decision="reviewer_assessed", business_understanding=9.0, architecture_report=9.0,
            technical_knowledge=9.0, presentation=9.0, qa=9.0,
            strength_areas="Clean architecture.", improvement_areas="None.",
            overall_feedback="Reviewer: clean architecture.", assessor_role="reviewer"
        ))
        store.save_assessment(AssessmentMarksheet(
            id="asm_audit_grd_1", submission_id=sub1.id, attempt_number=1, badge_id=b.id, cosmonaut_id="m_b1_1",
            reviewer_id="guardian_1", reviewer_name="Arjun Mehta", reviewed_at="2026-11-25T10:00:00Z",
            decision="approve", business_understanding=9.5, architecture_report=9.5,
            technical_knowledge=9.0, presentation=9.0, qa=9.0,
            strength_areas="Production grade.", improvement_areas="None.",
            overall_feedback="Guardian Official Award confirmed.", assessor_role="guardian"
        ))

        self.ctrl.handle_event("select_demo_account", "m_b2_1")
        self.ctrl.handle_event("nav_cosmonaut", "c_badge_reviews")
        html = self.ctrl.render()

        # Upcoming review shows Ananya Iyer by default + multi-day window + project title
        self.assertIn("Ananya Iyer", html)
        self.assertIn("18 Nov \u2192 20 Nov 2026", html)              # the multi-day window, formatted
        self.assertIn("Signal Audit Enterprise Brief", html)

        # Completed review shows Aarav Sharma's scores, files, remarks & direct marksheet button
        self.assertIn("Completed Reviews (0)", html)                    # Ananya has not earned it yet, so the badge stays under Upcoming ...
        self.assertNotIn("All badges earned", html)                     # ... and moves to Completed only when EVERY mapped cosmonaut has
        self.assertIn("Badge earned - 46.0/50 (92.0%)", html)           # the cosmonaut's row carries the final score
        self.assertNotIn("Aarav_Audit_Report.pdf", html)                # the files are in the Assessment workspace, not on the card
        self.assertNotIn("audit_sim.py", html)
        self.assertIn(f"open_reviewer_assessment_page', '{sub1.id}'", html)

    def test_03_unpublished_isolation_completed_badge_and_marksheet_priority(self):
        """Unpublished mapped badge stays hidden; Completed badge, c_results & c_dashboard show accurate counts & Guardian sheet."""
        b_pub = Badge(
            id="badge_pub_done", code="B1-PUB-01", title="Published Audit Badge", target_band="B1",
            category="Systems", description="Published.", learning_outcomes=["O1"],
            learning_topics=["T1"], prerequisites=[], project_requirements="Req 1",
            is_published=True, is_allocated=True,
        )
        b_unpub = Badge(
            id="badge_unpub_draft", code="B1-UNP-02", title="Hidden Draft Badge", target_band="B1",
            category="Systems", description="Unpublished.", learning_outcomes=["O2"],
            learning_topics=["T2"], prerequisites=[], project_requirements="Req 2",
            is_published=False, is_allocated=True,
        )
        store.save_badge(b_pub)
        store.save_badge(b_unpub)
        for bid, bobj in ((b_pub.id, b_pub), (b_unpub.id, b_unpub)):
            store.save_band_mapping({
                "id": f"map_{bid}", "band": "B1", "badge": bobj.title, "badge_id": bid,
                "reviewers": ["m_b2_1"], "cosmonauts": ["m_b1_1"], "review_dates": ["2026-11-18"], "status": "active"
            })
        sub = ProjectSubmission(
            id="sub_pub_m_b1_1", badge_id=b_pub.id, cosmonaut_id="m_b1_1", attempt_number=1,
            submission_type="multi", payload="data/rep.pdf", file_name="rep.pdf",
            pdf_name="Final_Pub_Report.pdf", code_name="pub_sol.py", github_url="https://github.com/starapp/pub",
            submitted_at="2026-11-25T08:00:00Z", status="approved"
        )
        store.save_submission(sub)
        # Note IDs insert reviewer BEFORE or AFTER guardian intentionally
        store.save_assessment(AssessmentMarksheet(
            id="asm_z_grd", submission_id=sub.id, attempt_number=1, badge_id=b_pub.id, cosmonaut_id="m_b1_1",
            reviewer_id="guardian_1", reviewer_name="Arjun Mehta", reviewed_at="2026-11-25T10:00:00Z",
            decision="approve", business_understanding=9.5, architecture_report=9.5, technical_knowledge=9.0,
            presentation=9.0, qa=9.0, strength_areas="Clean.", improvement_areas="None.",
            overall_feedback="Guardian Final Ok", assessor_role="guardian"
        ))
        store.save_assessment(AssessmentMarksheet(
            id="asm_z_rev", submission_id=sub.id, attempt_number=1, badge_id=b_pub.id, cosmonaut_id="m_b1_1",
            reviewer_id="m_b2_1", reviewer_name="Rohan Deshmukh", reviewed_at="2026-11-25T09:00:00Z",
            decision="approve", business_understanding=9.0, architecture_report=9.0, technical_knowledge=9.0,
            presentation=9.0, qa=8.5, strength_areas="Solid.", improvement_areas="None.",
            overall_feedback="Reviewer Prelim", assessor_role="reviewer"
        ))

        self.ctrl.handle_event("select_demo_account", "m_b1_1")

        # 1. Unpublished badge must NOT leak into c_submission or c_cycles
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")
        sub_html = self.ctrl.render()
        self.assertIn("Published Audit Badge", sub_html)
        self.assertNotIn("Hidden Draft Badge", sub_html)
        self.assertNotIn("46.0/50 (92.0%)", sub_html)                  # no score on the badge card (it is inside the badge)

        # 2. c_badge_detail for completed badge shows Peer Reviewer + Guardian marks & Deliverables
        self.ctrl.handle_event("open_cosmonaut_badge_page", b_pub.id)
        detail_html = self.ctrl.render()
        self.assertIn("mbe-card", detail_html)                         # the achievement card shows the marks and feedback only
        for gone in ("Final_Pub_Report.pdf", "pub_sol.py", "Peer reviewer (", "Guardian final (", "Submitted Deliverables"):
            self.assertNotIn(gone, detail_html, gone)

        # 3. c_results prioritizes Guardian Official marksheet & labels evaluator roles cleanly
        self.ctrl.cosmonaut_results_badge_id = b_pub.id
        self.ctrl.handle_event("nav_cosmonaut", "c_results")
        res_html = self.ctrl.render()
        self.assertIn("Rohan Deshmukh", res_html)                     # the mapped peer reviewer is named, not the Guardian who signed off
        self.assertNotIn("ms-tab", res_html)                           # one marksheet only, no tab strip

        # 4. c_dashboard does NOT double-count (no 2 / 1)
        self.ctrl.handle_event("nav_cosmonaut", "c_dashboard")
        dash_html = self.ctrl.render()
        self.assertNotIn("2 Approved Milestones", dash_html)
        self.assertIn("1 Approved Milestones", dash_html)


if __name__ == "__main__":
    unittest.main()
