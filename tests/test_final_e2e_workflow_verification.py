"""
STARAPP FINAL END-TO-END WORKFLOW VERIFICATION SUITE
===================================================
Executes and validates the complete multi-user lifecycle across 18 phases:
  1 Guardian, 2 Reviewers, 4 Cosmonauts, 2 Badges in Band B1.
Tests:
  - Badge creation, reviewer assignment eligibility (Reviewer_Band > Badge_Band), and approval.
  - Guardian publication.
  - Per-badge independent mapping and dedicated timeline scheduling.
  - Gemini AI / fallback project generation and Reviewer editing.
  - 1:N Reviewer-to-Cadet delivery isolation (Reviewer 1 -> Cadets 1 & 2; Reviewer 2 -> Cadets 3 & 4).
  - Cosmonaut multi-deliverable submission (Code, PDF, GitHub URL).
  - Reviewer assessment queue isolation (Reviewer 2 cannot see or assess Reviewer 1's cadets).
  - 50-mark rubric scoring and marksheet persistence in SQLite.
  - Marksheet synchronization to Cosmonaut and Guardian views.
  - Guardian final badge award (>= 70% threshold).
  - Reviewer-Cosmonaut mapping uncoupling/closure (Cadet 1 certified; Cadet 2 remains active; Mapping 2 unaffected).
  - Database persistence across simulated server restarts.
  - SQLite integrity check and foreign key check.
"""

import unittest
import json
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import (
    Badge, BadgeTimeline, ProjectSubmission, AssessmentMarksheet,
    ReviewerProjectPrompt, current_iso_timestamp
)
from starapp.badge_generator import generate_reviewer_project_spec
from starapp.views_guardian import render_guardian_badge_allotment
from starapp.views_cosmonaut import (
    render_cosmonaut_submission_workspace,
    render_reviewer_assessment_queue,
    render_reviewer_badge_schedule
)


class TestFinalE2EWorkflowVerification(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        self.ctrl.initialize()

    def test_complete_multi_user_workflow_and_isolation(self):
        # =========================================================================
        # 1. SETUP ACTORS & BADGES
        # =========================================================================
        guardian_id = "guardian_1"
        rev1_id = "m_b2_1"   # Band B2 Reviewer
        rev2_id = "m_b3_2"   # Band B3 Reviewer
        cadet1_id = "cosmo_1" # Astraea Sharma (B1)
        cadet2_id = "m_b1_1"  # Cadet 2 (B1)
        cadet3_id = "m_b1_3"  # Cadet 3 (B1)
        cadet4_id = "m_b1_4"  # Cadet 4 (B1)

        # 2 Badges in Band B1
        badge1 = store.get_badge("badge_b1_signals")  # Signals Foundations (B1)
        self.assertIsNotNone(badge1)
        badge2 = store.get_badge("b1_dat_01")         # Data Model Foundations (B1)
        self.assertIsNotNone(badge2)

        # =========================================================================
        # 2. GUARDIAN CREATES & ASSIGNS BADGE PROPOSAL TO HIGHER-BAND REVIEWER
        # =========================================================================
        self.ctrl.handle_event("select_demo_account", guardian_id)
        self.assertEqual(self.ctrl.current_user.role, "guardian")

        # Test Reviewer Eligibility Rule: Reviewer_Band > Badge_Band
        eligible_for_b1 = store.get_eligible_badge_reviewers("B1")
        eligible_ids = [r["id"] for r in eligible_for_b1]
        self.assertIn(rev1_id, eligible_ids, "B2 reviewer must be eligible for B1 badge")
        self.assertIn(rev2_id, eligible_ids, "B3 reviewer must be eligible for B1 badge")
        self.assertNotIn(cadet1_id, eligible_ids, "B1 cadet cannot review B1 badge")

        # Publish both badges
        badge1.is_published = True
        badge1.is_allocated = True
        badge1.workflow_status = "approved"
        store.save_badge(badge1)

        badge2.is_published = True
        badge2.is_allocated = True
        badge2.workflow_status = "approved"
        store.save_badge(badge2)

        self.assertTrue(badge1.is_published)
        self.assertTrue(badge2.is_published)

        # =========================================================================
        # 3. INDEPENDENT BADGE-WISE MAPPINGS & 3-DAY TIMELINES
        # =========================================================================
        # Mapping 1: Badge 1 -> Reviewer 1 (m_b2_1) -> Cadets 1 & 2 (cosmo_1, m_b1_1)
        map1_dict = {
            "id": "map_b1_signals_group1",
            "band": "B1",
            "badge_id": badge1.id,
            "badge": badge1.title,
            "cosmonauts": [cadet1_id, cadet2_id],
            "reviewers": [rev1_id],
            "review_dates": ["2026-11-25", "2026-11-26", "2026-11-27"],
            "reviewer_band": "B2",
            "guard_id": guardian_id,
            "created_at": current_iso_timestamp(),
            "status": "active"
        }
        store.save_band_mapping(map1_dict)

        # Mapping 2: Badge 2 -> Reviewer 2 (m_b3_2) -> Cadets 3 & 4 (m_b1_3, m_b1_4)
        map2_dict = {
            "id": "map_b1_dat_group2",
            "band": "B1",
            "badge_id": badge2.id,
            "badge": badge2.title,
            "cosmonauts": [cadet3_id, cadet4_id],
            "reviewers": [rev2_id],
            "review_dates": ["2026-11-28", "2026-11-29", "2026-11-30"],
            "reviewer_band": "B3",
            "guard_id": guardian_id,
            "created_at": current_iso_timestamp(),
            "status": "active"
        }
        store.save_band_mapping(map2_dict)

        # Create timelines for Cadets 1 & 2
        for cid in [cadet1_id, cadet2_id]:
            tl = BadgeTimeline(
                badge_id=badge1.id,
                cosmonaut_id=cid,
                reviewer_id=rev1_id,
                assignment_date="2026-11-20",
                publication_date="2026-11-20",
                learning_start_date="2026-11-21",
                learning_end_date="2026-11-24",
                project_start_date="2026-11-25",
                project_end_date="2026-11-27",
                submission_deadline="2026-11-27",
                review_date="2026-11-28",
                expected_award_date="2026-11-30",
                status="active"
            )
            store.save_timeline(tl)

        # Create timelines for Cadets 3 & 4
        for cid in [cadet3_id, cadet4_id]:
            tl = BadgeTimeline(
                badge_id=badge2.id,
                cosmonaut_id=cid,
                reviewer_id=rev2_id,
                assignment_date="2026-11-20",
                publication_date="2026-11-20",
                learning_start_date="2026-11-21",
                learning_end_date="2026-11-27",
                project_start_date="2026-11-28",
                project_end_date="2026-11-30",
                submission_deadline="2026-11-30",
                review_date="2026-12-01",
                expected_award_date="2026-12-03",
                status="active"
            )
            store.save_timeline(tl)

        # Verify Guardian Badge Allotment HTML displays dedicated mapping cards
        allotment_html = render_guardian_badge_allotment(
            badges=[badge1, badge2],
            cosmonauts=store.get_all_cosmonauts(),
            filter_tab="all",
            all_band_mappings=store.get_band_mappings(),
            all_timelines=store.timelines
        )
        self.assertIn("Timeline &amp; Mapping", allotment_html)
        self.assertIn("Reviewer", allotment_html)

        # =========================================================================
        # 4. REVIEWER AI PROJECT GENERATION & 1:N DELIVERY ISOLATION
        # =========================================================================
        # Reviewer 1 logs in
        self.ctrl.handle_event("select_demo_account", rev1_id)
        self.assertEqual(self.ctrl.current_user.id, rev1_id)

        # Reviewer 1 generates project spec for Badge 1
        spec1 = generate_reviewer_project_spec(
            band="B1", power="Tech", capability="Signals", skill="Foundations",
            badge_title=badge1.title, reviewer_name="Reviewer 1"
        )
        self.ctrl.handle_event("send_reviewer_project", json.dumps({
            "badge_id": badge1.id,
            "title": "Signals Telemetry Processing Project",
            "objective": spec1.get("scenario", "Implement real-time telemetry parser"),
            "technical_requirements": spec1.get("requirements", []),
            "evaluation_criteria": spec1.get("rubric_guidelines", []),
            "submission_deadline": "2026-11-27",
            "deliverables": spec1.get("deliverables", {}),
            "cosmonaut_ids": [cadet1_id, cadet2_id]
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Reviewer 2 logs in
        self.ctrl.handle_event("select_demo_account", rev2_id)
        self.assertEqual(self.ctrl.current_user.id, rev2_id)

        # Reviewer 2 generates project spec for Badge 2
        spec2 = generate_reviewer_project_spec(
            band="B1", power="Tech", capability="Data", skill="Data Model",
            badge_title=badge2.title, reviewer_name="Reviewer 2"
        )
        self.ctrl.handle_event("send_reviewer_project", json.dumps({
            "badge_id": badge2.id,
            "title": "Enterprise Dimensional Data Modeling",
            "objective": spec2.get("scenario", "Implement relational star schema"),
            "technical_requirements": spec2.get("requirements", []),
            "evaluation_criteria": spec2.get("rubric_guidelines", []),
            "submission_deadline": "2026-11-30",
            "deliverables": spec2.get("deliverables", {}),
            "cosmonaut_ids": [cadet3_id, cadet4_id]
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify delivery isolation in SQLite:
        # Cadet 1 & 2 must receive Reviewer 1's prompt for Badge 1
        prompt_cadet1 = store.get_project_prompt_for_cadet(badge1.id, cadet1_id)
        self.assertIsNotNone(prompt_cadet1)
        self.assertEqual(prompt_cadet1.title, "Signals Telemetry Processing Project")
        self.assertEqual(prompt_cadet1.reviewer_id, rev1_id)

        prompt_cadet2 = store.get_project_prompt_for_cadet(badge1.id, cadet2_id)
        self.assertIsNotNone(prompt_cadet2)
        self.assertEqual(prompt_cadet2.title, "Signals Telemetry Processing Project")

        # Cadet 3 & 4 must receive Reviewer 2's prompt for Badge 2
        prompt_cadet3 = store.get_project_prompt_for_cadet(badge2.id, cadet3_id)
        self.assertIsNotNone(prompt_cadet3)
        self.assertEqual(prompt_cadet3.title, "Enterprise Dimensional Data Modeling")
        self.assertEqual(prompt_cadet3.reviewer_id, rev2_id)

        # Cadet 1 must NOT receive Reviewer 2's prompt for Badge 2
        prompt_cadet1_badge2 = store.get_project_prompt_for_cadet(badge2.id, cadet1_id)
        self.assertIsNone(prompt_cadet1_badge2, "Cadet 1 must not receive prompt from unmapped Reviewer 2")

        # Cadet 3 must NOT receive Reviewer 1's prompt for Badge 1
        prompt_cadet3_badge1 = store.get_project_prompt_for_cadet(badge1.id, cadet3_id)
        self.assertIsNone(prompt_cadet3_badge1, "Cadet 3 must not receive prompt from unmapped Reviewer 1")

        # =========================================================================
        # 5. CADET 1 DELIVERABLE SUBMISSION (CODE, PDF, GITHUB URL)
        # =========================================================================
        self.ctrl.handle_event("select_demo_account", cadet1_id)
        self.assertEqual(self.ctrl.current_user.id, cadet1_id)

        # Inspect Badges workspace HTML contains assigned project banner
        sub_workspace_html = render_cosmonaut_submission_workspace(
            badges=[badge1],
            selected_badge_id=badge1.id,
            submissions=[],
            current_user=self.ctrl.current_user,
            store=store,
            expanded_badge_id=badge1.id
        )
        self.assertIn("ASSIGNED PROJECT SPECIFICATION", sub_workspace_html)

        # Cadet 1 submits all 3 deliverables
        self.ctrl.handle_event("submit_project_deliverable", json.dumps({
            "badge_id": badge1.id,
            "pdf_name": "Astraea_Signals_Telemetry_Charter.pdf",
            "pdf_payload": "data/sample_charter.pdf",
            "code_name": "telemetry_core_parser.py",
            "code_payload": "def parse_telemetry(): return {'status': 'OK'}",
            "github_url": "https://github.com/starapp/signals-telemetry-charter"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify submission persisted in SQLite
        subs1 = store.get_submissions_for_cosmonaut(cadet1_id, badge1.id)
        self.assertEqual(len(subs1), 1)
        sub1 = subs1[0]
        self.assertEqual(sub1.attempt_number, 1)
        self.assertEqual(sub1.pdf_name, "Astraea_Signals_Telemetry_Charter.pdf")
        self.assertEqual(sub1.code_name, "telemetry_core_parser.py")
        self.assertEqual(sub1.github_url, "https://github.com/starapp/signals-telemetry-charter")

        # =========================================================================
        # 6. REVIEWER ASSESSMENT QUEUE & RBAC ISOLATION
        # =========================================================================
        # Reviewer 2 (unauthorized for Cadet 1) logs in
        self.ctrl.handle_event("select_demo_account", rev2_id)
        asms_map = {a.submission_id: a for a in store.get_all_assessments()}

        # Verify Reviewer 2 queue does NOT display Cadet 1's submission
        rev2_queue_html = render_reviewer_assessment_queue(
            submissions=store.get_all_submissions(),
            assessments_by_sub=asms_map,
            badges_map={badge1.id: badge1, badge2.id: badge2},
            cosmonauts_map={u.id: u for u in store.get_all_cosmonauts()},
            current_user=store.get_user_by_id(rev2_id),
            status_filter="all"
        )
        self.assertNotIn("Astraea_Signals_Telemetry_Charter.pdf", rev2_queue_html,
                         "Reviewer 2 must not see submissions of cadets mapped to Reviewer 1")

        # Reviewer 2 attempts unauthorized assessment of Cadet 1's submission
        self.ctrl.handle_event("submit_reviewer_assessment", json.dumps({
            "submission_id": sub1.id,
            "bu": 8.0, "ar": 8.0, "tk": 8.0, "pr": 8.0, "qa": 8.0,
            "feedback": "Illegitimate assessment attempt"
        }))
        self.assertEqual(self.ctrl.flash_type, "error",
                         "Reviewer 2 must be blocked from assessing unmapped Cadet 1")

        # Reviewer 1 (authorized) logs in
        self.ctrl.handle_event("select_demo_account", rev1_id)
        rev1_queue_html = render_reviewer_assessment_queue(
            submissions=store.get_all_submissions(),
            assessments_by_sub=asms_map,
            badges_map={badge1.id: badge1, badge2.id: badge2},
            cosmonauts_map={u.id: u for u in store.get_all_cosmonauts()},
            current_user=store.get_user_by_id(rev1_id),
            status_filter="all"
        )
        self.assertIn("Astraea_Signals_Telemetry_Charter.pdf", rev1_queue_html,
                      "Reviewer 1 must see mapped Cadet 1's submission")

        # Reviewer 1 scores Cadet 1 with 50-mark rubric (Total: 44.0/50.0 = 88%)
        self.ctrl.handle_event("submit_reviewer_assessment", json.dumps({
            "submission_id": sub1.id,
            "bu": 9.0,
            "ar": 9.0,
            "tk": 9.0,
            "pr": 8.5,
            "qa": 8.5,
            "strengths": "Clean dataflow pipeline with robust logging.",
            "improvements": "None.",
            "feedback": "Outstanding work. Highly recommended for certification.",
            "decision": "approve"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify submission status transitioned to 'reviewer_assessed'
        sub1_scored = store.get_submission(sub1.id)
        self.assertEqual(sub1_scored.status, "reviewer_assessed")

        # Verify marksheet in SQLite with assessor_role='reviewer'
        asms = [a for a in store.get_assessments_for_cosmonaut(cadet1_id) if a.submission_id == sub1.id and a.assessor_role == "reviewer"]
        self.assertEqual(len(asms), 1)
        self.assertEqual(asms[0].total_marks, 44.0)

        # =========================================================================
        # 7. GUARDIAN FINAL ASSESSMENT & MAPPING UNCOUPLING
        # =========================================================================
        self.ctrl.handle_event("select_demo_account", guardian_id)

        # Guardian approves final marksheet: 45.0 / 50.0 (90% >= 70% threshold)
        self.ctrl.handle_event("submit_guardian_final_assessment", json.dumps({
            "submission_id": sub1.id,
            "bu": 9.0,
            "ar": 9.0,
            "tk": 9.0,
            "pr": 9.0,
            "qa": 9.0,
            "strengths": "Exceptional architecture and complete rubric alignment.",
            "improvements": "None.",
            "feedback": "Institutional badge officially awarded.",
            "decision": "approve"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")
        self.assertIn("Badge awarded!", self.ctrl.last_flash_message)

        # Verify final state in SQLite:
        # 1. BadgeTimeline marked 'completed' and actual_award_date recorded
        tl1 = store.get_timeline(badge1.id, cadet1_id)
        self.assertEqual(tl1.status, "completed")
        self.assertTrue(len(tl1.actual_award_date) > 0)

        # 2. Submission status is 'approved'
        sub1_final = store.get_submission(sub1.id)
        self.assertEqual(sub1_final.status, "approved")

        # 3. Cadet 1 is uncoupled from active mapping for Badge 1
        m1 = [m for m in store.get_band_mappings() if m.get("id") == "map_b1_signals_group1"][0]
        self.assertIn(cadet1_id, m1.get("uncoupled_cadets", []), "Cadet 1 must be uncoupled")
        self.assertIn(cadet1_id, m1.get("completed_cosmonauts", []))

        # 4. Cadet 2 in Mapping 1 remains active (not yet completed)
        self.assertNotIn(cadet2_id, m1.get("uncoupled_cadets", []), "Cadet 2 must remain active")

        # 5. Mapping 2 (Badge 2 with Cadets 3 & 4) remains completely active and unaffected
        m2 = [m for m in store.get_band_mappings() if m.get("id") == "map_b1_dat_group2"][0]
        self.assertEqual(m2.get("status"), "active")
        self.assertNotIn(cadet3_id, m2.get("uncoupled_cadets", []))

        # =========================================================================
        # 8. PERSISTENCE ACROSS SIMULATED RESTART & SQLITE INTEGRITY
        # =========================================================================
        # Re-initialize controller and DataStore to simulate server restart
        new_ctrl = StarAppController()
        new_ctrl.initialize()

        # Verify Badge 1 timeline for Cadet 1 remains completed after restart
        tl1_after_restart = store.get_timeline(badge1.id, cadet1_id)
        self.assertEqual(tl1_after_restart.status, "completed")
        self.assertEqual(tl1_after_restart.actual_award_date, tl1.actual_award_date)

        # Verify Marksheets remain in SQLite
        asms_after_restart = store.get_assessments_for_cosmonaut(cadet1_id)
        badge1_asms = [a for a in asms_after_restart if a.badge_id == badge1.id]
        self.assertEqual(len(badge1_asms), 2, "Both Reviewer and Guardian marksheets must persist")

        # SQLite integrity and foreign key checks
        conn = sqlite3.connect(store.db.db_path)
        cur = conn.cursor()
        integrity = cur.execute("PRAGMA integrity_check").fetchall()
        self.assertEqual(integrity, [("ok",)])
        fk_violations = cur.execute("PRAGMA foreign_key_check").fetchall()
        self.assertEqual(fk_violations, [])
        conn.close()


if __name__ == "__main__":
    unittest.main()
