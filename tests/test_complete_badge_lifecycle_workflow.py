"""
STARAPP COMPLETE BADGE LIFECYCLE, REVIEWER–COSMONAUT MAPPING & ASSESSMENT WORKFLOW TEST
====================================================================================
Comprehensive integration test verifying the entire 9-stage lifecycle:
  1. Guardian creates B1 badge (draft / ready_for_review).
  2. Send badge to higher-band reviewer (Reviewer_Band > Badge_Band).
  3. Reviewer examines, edits, and approves badge (workflow_status='approved').
  4. Guardian publishes badge (is_published=True).
  5. Guardian maps badge to B1 cosmonauts and B2 reviewer (with 3-day review window); verified in SQLite.
  6. Cosmonaut submits Attempt #1 deliverables (PDF, Code, GitHub URL).
  7. Assigned reviewer evaluates deliverable (50-mark rubric with assessor_role='reviewer').
  8. Guardian conducts final assessment with score < 70% passing threshold, triggering retake_required.
  9. Cosmonaut submits Attempt #2 deliverables (Attempt #1 preserved); Reviewer & Guardian re-evaluate >= 70%,
     badge awarded and timeline marked completed.
"""

import unittest
import json
import sqlite3
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starapp.app import StarAppController
from project_helpers import give_project
from starapp.storage import store
from starapp.models import Badge, BadgeTimeline, ProjectSubmission, AssessmentMarksheet, current_iso_timestamp


class TestCompleteBadgeLifecycleWorkflow(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        self.ctrl.initialize()

    def test_complete_9_stage_workflow(self):
        # =========================================================================
        # STAGE 1: GUARDIAN CREATES BADGE
        # =========================================================================
        # 1. Login as Guardian
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.assertEqual(self.ctrl.current_user.role, "guardian")

        # 2. Select Band B1
        self.ctrl.handle_event("nav_guardian", "g_create_badge")
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.assertEqual(self.ctrl.create_badge_band, "B1")

        # 3. Guardian configures badge prompt and creates badge
        b1_prompt_json = json.dumps({
            "title": "Digital Signal Processing Foundations",
            "skill": "Signals",
            "capability": "Data & Machine",
            "power": "Tech",
            "target_band": "B1",
            "description": "Foundational digital signal processing, telemetry parsing, and time-series extraction.",
            "learning_outcomes": [
                "Can configure and evaluate modular telemetry streams.",
                "Can parse time-series metrics against operational latency thresholds."
            ],
            "practice_project": {
                "intro": "Hands-on practice project.",
                "prompt": "Construct a telemetry parser in Python.",
                "footnote": "Use for self-practice."
            },
            "practice_prompt": "Construct a telemetry parser in Python.",
            "learning_topics": [
                {"title": "1. Telemetry Fundamentals", "description": "Stream architectures.", "completed": False},
                {"title": "2. Signal Transformations", "description": "Fourier and filtering.", "completed": False}
            ],
            "learning_resources": {
                "intro": "Curated resources.",
                "prompt": "Read DSP open-source handbook.",
                "footnote": "DSP resources."
            },
            "resources_prompt": "Read DSP open-source handbook."
        })

        # =========================================================================
        # STAGE 2: SEND BADGE TO HIGHER-BAND REVIEWER (Reviewer_Band > Badge_Band)
        # =========================================================================
        # Check eligible reviewers for B1: all reviewers must have band > B1 (e.g. B2, B3, B4, B5, B6)
        eligible_revs = store.get_eligible_badge_reviewers("B1")
        self.assertTrue(len(eligible_revs) > 0)
        for r in eligible_revs:
            r_band_num = int(r["band"].replace("B", ""))
            self.assertGreater(r_band_num, 1, "Reviewer band must strictly be higher than badge target band (B1)")

        selected_reviewer = eligible_revs[0]
        reviewer_id = selected_reviewer["id"]  # E.g. m_b2_1 or similar
        self.ctrl.handle_event("select_badge_reviewer", reviewer_id)

        # Trigger preview and badge creation
        self.ctrl.handle_event("preview_new_badge", {
            "code": "B1-DSP-01",
            "title": "Digital Signal Processing Foundations",
            "prompt_json": b1_prompt_json
        })
        self.ctrl.handle_event("create_badge", "{}")

        # Verify badge exists in DB with pending_review workflow status
        all_b1_badges = [b for b in store.get_all_badges() if b.code.startswith("B1-DSP-01")]
        self.assertTrue(len(all_b1_badges) > 0, "Badge B1-DSP-01 must be saved in storage")
        badge = all_b1_badges[0]
        self.assertEqual(badge.workflow_status, "pending_review")
        self.assertEqual(badge.target_band, "B1")
        self.assertEqual(badge.assigned_reviewer_id, reviewer_id)
        self.assertFalse(badge.is_published, "New badge must remain unpublished")

        # =========================================================================
        # STAGE 3: REVIEWER EXAMINES, EDITS & APPROVES BADGE
        # =========================================================================
        # Reviewer logs in
        self.ctrl.handle_event("select_demo_account", reviewer_id)
        self.assertEqual(self.ctrl.current_user.id, reviewer_id)

        # Reviewer edits the badge specification
        updated_prompt = json.loads(b1_prompt_json)
        updated_prompt["description"] = "Industrial digital signal processing and robust telemetry extraction."
        self.ctrl.handle_event("save_reviewed_badge", {
            "badge_id": badge.id,
            "title": "Signals & Systems Foundations (Verified)",
            "prompt_json": json.dumps(updated_prompt)
        })

        # Badge remains pending_review until explicit approval
        badge_post_edit = store.get_badge(badge.id)
        self.assertEqual(badge_post_edit.workflow_status, "pending_review")
        self.assertIn("Verified", badge_post_edit.title)

        # Reviewer approves the badge proposal
        self.ctrl.handle_event("approve_submitted_badge", badge.id)
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify badge status in SQLite transitioned to 'approved'
        approved_badge = store.get_badge(badge.id)
        self.assertEqual(approved_badge.workflow_status, "approved")
        self.assertFalse(approved_badge.is_published, "Approved badge is not yet published")

        # =========================================================================
        # STAGE 4: RETURN APPROVED BADGE TO GUARDIAN & GUARDIAN PUBLISHES BADGE
        # =========================================================================
        # Guardian logs back in
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.assertEqual(self.ctrl.current_user.role, "guardian")

        # Guardian explicitly publishes badge
        self.ctrl.handle_event("publish_badge", badge.id)
        self.assertEqual(self.ctrl.flash_type, "success")

        published_badge = store.get_badge(badge.id)
        self.assertTrue(published_badge.is_published)
        self.assertEqual(published_badge.published_by, "guardian_1")
        self.assertTrue(len(published_badge.published_at) > 0)

        # =========================================================================
        # STAGE 5: GUARDIAN MAPS BADGE TO COSMONAUTS & REVIEWERS (3-DAY WINDOW)
        # =========================================================================
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B1")
        self.ctrl.handle_event("select_mapping_badge", published_badge.title)

        # Select Cosmonaut 1 (Astraea / cosmo_1) and Reviewer (reviewer_id)
        target_cosmonaut_id = "cosmo_1"
        self.ctrl.handle_event("toggle_mapping_cosmonaut", target_cosmonaut_id)
        self.ctrl.handle_event("toggle_mapping_reviewer", reviewer_id)

        # Set 3-day review window
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-25")
        self.ctrl.handle_event("set_mapping_review_direction", "after")
        expected_window = ["2026-11-25", "2026-11-26", "2026-11-27"]
        self.assertEqual(self.ctrl.mapping_review_dates, expected_window)

        # Send mapping request & accept
        self.ctrl.handle_event("send_mapping_requests", "{}")
        req_id = f"req_B1_{reviewer_id}"
        self.ctrl.handle_event("accept_mapping_request", req_id)

        # Execute mapping
        self.ctrl.handle_event("execute_cosmonaut_mapping", "{}")

        # Verify mapping record and timeline in SQLite
        tl = store.get_timeline(published_badge.id, target_cosmonaut_id)
        self.assertIsNotNone(tl, "BadgeTimeline must be generated for mapped cosmonaut")
        self.assertEqual(tl.reviewer_id, reviewer_id)
        self.assertEqual(tl.review_window, expected_window)
        self.assertEqual(tl.status, "active")

        # Verify Cosmonaut sees assigned badge
        cosmo_badges = store.get_badges_for_cosmonaut(target_cosmonaut_id)
        self.assertTrue(any(b.id == published_badge.id for b in cosmo_badges))

        # =========================================================================
        # STAGE 6: COSMONAUT SUBMITS ATTEMPT #1 DELIVERABLES
        # =========================================================================
        self.ctrl.handle_event("select_demo_account", target_cosmonaut_id)
        self.assertEqual(self.ctrl.current_user.id, target_cosmonaut_id)

        # The mapped reviewer has sent the project (request -> send is covered in test_scale_and_security_regressions)
        give_project(store, published_badge.id, target_cosmonaut_id)

        # Submit deliverable for Attempt #1
        self.ctrl.handle_event("submit_project_deliverable", json.dumps({
            "badge_id": published_badge.id,
            "pdf_name": "Astraea_Signals_Architecture_Report_v1.pdf",
            "pdf_payload": "data/sample_report.pdf",
            "code_name": "telemetry_processor_v1.py",
            "code_payload": "print('Telemetry processor v1 running')",
            "github_url": "https://github.com/starapp/signals-telemetry-v1"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify Attempt #1 submission in SQLite
        subs = store.get_submissions_for_cosmonaut(target_cosmonaut_id, published_badge.id)
        self.assertEqual(len(subs), 1)
        sub_att1 = subs[0]
        self.assertEqual(sub_att1.attempt_number, 1)
        self.assertEqual(sub_att1.status, "pending")
        self.assertEqual(sub_att1.pdf_name, "Astraea_Signals_Architecture_Report_v1.pdf")
        self.assertEqual(sub_att1.code_name, "telemetry_processor_v1.py")

        # Verify timeline is now awaiting review
        tl_att1 = store.get_timeline(published_badge.id, target_cosmonaut_id)
        self.assertEqual(tl_att1.status, "awaiting_review")

        # =========================================================================
        # STAGE 7: ASSIGNED REVIEWER EVALUATES DELIVERABLE (50-MARK RUBRIC)
        # =========================================================================
        self.ctrl.handle_event("select_demo_account", reviewer_id)
        self.assertEqual(self.ctrl.current_user.id, reviewer_id)

        # Reviewer evaluates deliverable with 5 criteria (30/50 = 60%, below 70%)
        rev_eval_payload = {
            "submission_id": sub_att1.id,
            "bu": 6.0,
            "ar": 6.0,
            "tk": 6.0,
            "pr": 6.0,
            "qa": 6.0,
            "strengths": "Good initial telemetry data parsing flow.",
            "improvements": "Missing error handling for corrupted time packets.",
            "feedback": "Needs architectural refinement on edge packet drops.",
            "decision": "changes_requested"
        }
        self.ctrl.handle_event("submit_reviewer_assessment", json.dumps(rev_eval_payload))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify submission status updated to 'reviewer_assessed'
        sub_rev_scored = store.get_submission(sub_att1.id)
        self.assertEqual(sub_rev_scored.status, "reviewer_assessed")

        # Verify Reviewer marksheet in SQLite
        rev_asms = [a for a in store.get_assessments_for_cosmonaut(target_cosmonaut_id) if a.submission_id == sub_att1.id and a.assessor_role == "reviewer"]
        self.assertEqual(len(rev_asms), 1)
        self.assertEqual(rev_asms[0].total_score, 30.0)
        self.assertEqual(rev_asms[0].assessor_role, "reviewer")

        # =========================================================================
        # STAGE 8: GUARDIAN FINAL ASSESSMENT (LOW SCORE -> RETAKE REQUIRED)
        # =========================================================================
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.assertEqual(self.ctrl.current_user.role, "guardian")

        # Guardian examines deliverables and Reviewer score, provides final assessment:
        # Total = 30.0 / 50.0 (60% < 70% passing threshold)
        guardian_eval_att1 = {
            "submission_id": sub_att1.id,
            "bu": 6.0,
            "ar": 6.0,
            "tk": 6.0,
            "pr": 6.0,
            "qa": 6.0,
            "strengths": "Solid signal logic structure.",
            "improvements": "Packet loss handling must be resolved.",
            "feedback": "Retake required to meet the 70% minimum threshold.",
            "decision": "changes_requested"
        }
        self.ctrl.handle_event("submit_guardian_final_assessment", json.dumps(guardian_eval_att1))
        self.assertEqual(self.ctrl.flash_type, "warning")
        self.assertIn("Retake required", self.ctrl.last_flash_message)

        # Verify submission and timeline transitioned to 'retake_required'
        sub_att1_final = store.get_submission(sub_att1.id)
        self.assertEqual(sub_att1_final.status, "retake_required")

        tl_att1_final = store.get_timeline(published_badge.id, target_cosmonaut_id)
        self.assertEqual(tl_att1_final.status, "retake_required")
        self.assertFalse(tl_att1_final.actual_award_date)

        # =========================================================================
        # STAGE 9: COSMONAUT SUBMITS ATTEMPT #2 & PASSES WITH >= 70% SCORE
        # =========================================================================
        # Cosmonaut logs in and sees retake required notification and status
        self.ctrl.handle_event("select_demo_account", target_cosmonaut_id)

        # Cosmonaut submits Attempt #2 deliverables
        self.ctrl.handle_event("submit_project_deliverable", json.dumps({
            "badge_id": published_badge.id,
            "pdf_name": "Astraea_Signals_Architecture_Report_v2_FINAL.pdf",
            "pdf_payload": "data/sample_report_v2.pdf",
            "code_name": "telemetry_processor_v2_robust.py",
            "code_payload": "print('Telemetry processor v2 with packet loss resilience running')",
            "github_url": "https://github.com/starapp/signals-telemetry-v2"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify multi-attempt history retention: Attempt #1 and Attempt #2 both exist in SQLite
        all_subs = store.get_submissions_for_cosmonaut(target_cosmonaut_id, published_badge.id)
        self.assertEqual(len(all_subs), 2, "Both Attempt #1 and Attempt #2 must be preserved")
        
        att1_stored = [s for s in all_subs if s.attempt_number == 1][0]
        att2_stored = [s for s in all_subs if s.attempt_number == 2][0]

        self.assertEqual(att1_stored.status, "retake_required")
        self.assertEqual(att2_stored.status, "pending")
        self.assertEqual(att2_stored.code_name, "telemetry_processor_v2_robust.py")

        # Reviewer logs in and evaluates Attempt #2 with high score (42/50 = 84%)
        self.ctrl.handle_event("select_demo_account", reviewer_id)
        rev_eval_att2 = {
            "submission_id": att2_stored.id,
            "bu": 8.5,
            "ar": 8.5,
            "tk": 8.5,
            "pr": 8.5,
            "qa": 8.0,
            "strengths": "Outstanding packet drop recovery implementation.",
            "improvements": "Minor logging verbosity.",
            "feedback": "Strongly recommended for approval.",
            "decision": "approve"
        }
        self.ctrl.handle_event("submit_reviewer_assessment", json.dumps(rev_eval_att2))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify Attempt #2 status is reviewer_assessed
        sub_att2_rev = store.get_submission(att2_stored.id)
        self.assertEqual(sub_att2_rev.status, "reviewer_assessed")

        # Guardian conducts final evaluation on Attempt #2 with 42.5/50 (85% >= 70%)
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        guardian_eval_att2 = {
            "submission_id": att2_stored.id,
            "bu": 8.5,
            "ar": 8.5,
            "tk": 8.5,
            "pr": 8.5,
            "qa": 8.5,
            "strengths": "Comprehensive architecture and resilient implementation.",
            "improvements": "None. Excellent work.",
            "feedback": "Exceeds all competencies. Badge awarded!",
            "decision": "approve"
        }
        self.ctrl.handle_event("submit_guardian_final_assessment", json.dumps(guardian_eval_att2))
        self.assertEqual(self.ctrl.flash_type, "success")
        self.assertIn("Badge awarded!", self.ctrl.last_flash_message)

        # Verify final state in SQLite:
        # 1. Attempt #2 submission status is 'approved'
        final_att2 = store.get_submission(att2_stored.id)
        self.assertEqual(final_att2.status, "approved")

        # 2. Attempt #1 remains unchanged as 'retake_required'
        final_att1 = store.get_submission(att1_stored.id)
        self.assertEqual(final_att1.status, "retake_required")

        # 3. BadgeTimeline is marked 'completed' and actual_award_date is set
        final_tl = store.get_timeline(published_badge.id, target_cosmonaut_id)
        self.assertEqual(final_tl.status, "completed")
        self.assertIsNotNone(final_tl.actual_award_date)
        self.assertTrue(len(final_tl.actual_award_date) > 0)

        # 4. Total assessment marksheets for Cosmonaut: 4 (Att #1 Rev, Att #1 Guard, Att #2 Rev, Att #2 Guard)
        all_cosmo_asms = store.get_assessments_for_cosmonaut(target_cosmonaut_id)
        badge_asms = [a for a in all_cosmo_asms if a.badge_id == published_badge.id]
        self.assertEqual(len(badge_asms), 4)

        # 5. Cosmonaut completed badges list includes this badge
        approved_asms = [a for a in all_cosmo_asms if a.decision == "approve" and a.assessor_role == "guardian"]
        completed_badge_ids = {a.badge_id for a in approved_asms}
        self.assertIn(published_badge.id, completed_badge_ids)

    def test_reviewer_ai_project_creation_and_mapping_uncoupling(self):
        """
        Verify:
          1. Dedicated mapping box and scoped table in Guardian Allotment view.
          2. Reviewer opens Timeline modal & AI Project Creator modal.
          3. Reviewer releases AI-generated project specification to mapped cadets.
          4. Cadets see assigned project banner in Badges submission view.
          5. Cadet submits deliverables (PDF, Code, GitHub URL).
          6. Reviewer evaluates deliverable (50-mark scorecard).
          7. Guardian final approval awards badge & uncouples active mapping to Completed/Certified.
        """
        from starapp.views_guardian import render_guardian_badge_allotment
        from starapp.views_cosmonaut import render_cosmonaut_submission_workspace
        from starapp.badge_generator import generate_reviewer_project_spec

        # 1. Login as Guardian & map badge
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        badge = store.get_badge("badge_b1_signals")  # Signals Foundations (B1)
        self.assertIsNotNone(badge)
        badge.is_published = True
        badge.is_allocated = True
        store.save_badge(badge)

        reviewer_id = "m_b2_1"
        target_cosmo_id = "cosmo_1"

        # Save band mapping in storage
        mapping_dict = {
            "id": "map_test_b1_signals",
            "band": "B1",
            "badge": badge.title,
            "cosmonauts": [target_cosmo_id],
            "reviewers": [reviewer_id],
            "review_dates": ["2026-11-25", "2026-11-26", "2026-11-27"],
            "reviewer_band": "B2",
            "guard_id": "guardian_1",
            "created_at": current_iso_timestamp(),
            "status": "active"
        }
        mapping_id = mapping_dict["id"]
        store.save_band_mapping(mapping_dict)
        self.assertIn(mapping_id, [m["id"] for m in store.get_band_mappings()])

        # 2. Verify Guardian Allotment view contains dedicated mapping card and scoped table
        allotment_html = render_guardian_badge_allotment(
            badges=[badge],
            cosmonauts=store.get_all_cosmonauts(),
            filter_tab="all",
            all_band_mappings=store.get_band_mappings(),
            all_timelines=store.timelines
        )
        self.assertIn("open_badge_mapping_modal", allotment_html)
        self.assertIn("open_badge_timeline_modal", allotment_html)

        # 3. Reviewer logs in & opens timeline modal and project creator modal
        self.ctrl.handle_event("select_demo_account", reviewer_id)
        self.assertEqual(self.ctrl.current_user.id, reviewer_id)

        # Open Reviewer Timeline Modal
        self.ctrl.handle_event("open_reviewer_badge_timeline_modal", badge.id)
        self.assertEqual(self.ctrl.active_modal, "reviewer_timeline_modal")
        modal_html = self.ctrl.render_active_modal()
        self.assertIn("Milestone Timeline Schedule", modal_html)
        self.ctrl.handle_event("close_modal", "{}")
        self.assertIsNone(self.ctrl.active_modal)

        # Open AI Project Creator Modal
        self.ctrl.handle_event("open_create_reviewer_project_modal", badge.id)
        self.assertEqual(self.ctrl.active_modal, "reviewer_project_creator")
        proj_modal_html = self.ctrl.render_active_modal()
        self.assertIn("Create Project", proj_modal_html)
        self.assertIn("Send Project to Mapped Cosmonauts", proj_modal_html)

        # Reviewer generates and releases project specification
        ai_spec = generate_reviewer_project_spec(
            band="B1",
            power="Tech",
            capability="Curation",
            skill="Data Management",
            badge_title=badge.title,
            reviewer_name=self.ctrl.current_user.name
        )
        self.ctrl.handle_event("send_reviewer_project", json.dumps({
            "badge_id": badge.id,
            "title": ai_spec["title"],
            "objective": ai_spec.get("objective", ai_spec.get("scenario", "")),
            "technical_requirements": ai_spec.get("technical_requirements", ai_spec.get("requirements", [])),
            "evaluation_criteria": ai_spec.get("evaluation_criteria", ai_spec.get("rubric_guidelines", [])),
            "submission_deadline": "2026-11-28",
            "deliverables": ai_spec["deliverables"],
            "cosmonaut_ids": [target_cosmo_id]
        }))
        self.assertEqual(self.ctrl.flash_type, "success")
        self.assertIsNone(self.ctrl.active_modal)

        # Verify prompt exists in SQLite
        saved_prompt = store.get_project_prompt_for_cadet(badge.id, target_cosmo_id)
        self.assertIsNotNone(saved_prompt, "Assigned project prompt must be stored in SQLite")
        self.assertEqual(saved_prompt.title, ai_spec["title"])

        # 4. Cosmonaut logs in and sees assigned project banner
        self.ctrl.handle_event("select_demo_account", target_cosmo_id)
        sub_workspace_html = render_cosmonaut_submission_workspace(
            badges=[badge],
            selected_badge_id=badge.id,
            submissions=[],
            current_user=self.ctrl.current_user,
            store=store,
            expanded_badge_id=badge.id
        )
        self.assertIn("Project Allocated", sub_workspace_html)

        # Cosmonaut submits deliverables
        self.ctrl.handle_event("submit_project_deliverable", json.dumps({
            "badge_id": badge.id,
            "pdf_name": "Curation_Capstone_Report.pdf",
            "pdf_payload": "data/sample_report.pdf",
            "code_name": "curation_pipeline.py",
            "code_payload": "print('Curation pipeline')",
            "github_url": "https://github.com/starapp/curation-capstone"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        subs = store.get_submissions_for_cosmonaut(target_cosmo_id, badge.id)
        self.assertTrue(len(subs) > 0)
        sub = subs[0]

        # 5. Reviewer evaluates submission
        self.ctrl.handle_event("select_demo_account", reviewer_id)
        self.ctrl.handle_event("submit_reviewer_assessment", json.dumps({
            "submission_id": sub.id,
            "bu": 9.0,
            "ar": 8.5,
            "tk": 9.0,
            "pr": 8.5,
            "qa": 8.0,
            "strengths": "Flawless metadata pipeline and robust validation.",
            "improvements": "None.",
            "feedback": "Ready for certification.",
            "decision": "approve"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        # 6. Guardian final approval & mapping uncoupling
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.ctrl.handle_event("submit_guardian_final_assessment", json.dumps({
            "submission_id": sub.id,
            "bu": 9.0,
            "ar": 9.0,
            "tk": 9.0,
            "pr": 8.5,
            "qa": 8.5,
            "strengths": "Exceptional end-to-end deliverable quality.",
            "improvements": "None.",
            "feedback": "Approved for official institutional award.",
            "decision": "approve"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        # 7. Verify mapping uncoupling
        mappings = store.get_band_mappings()
        matched = [m for m in mappings if m.get("id") == mapping_id or m.get("badge") == badge.title]
        self.assertTrue(len(matched) > 0)
        m = matched[0]
        self.assertIn(target_cosmo_id, m.get("uncoupled_cadets", []))
        self.assertIn(target_cosmo_id, m.get("completed_cosmonauts", []))

        # Check Reviewer assessment queue reflects uncoupled status
        ctrl_rev = StarAppController()
        ctrl_rev.initialize()
        ctrl_rev.handle_event("select_demo_account", reviewer_id)
        ctrl_rev.handle_event("nav_cosmonaut", "c_badge_reviews")
        schedule_html = ctrl_rev.render()
        self.assertIn("43.0 / 50", schedule_html)                       # the reviewer's score is on the Badge Review schedule
        self.assertIn("open_reviewer_assessment_page", schedule_html)


if __name__ == "__main__":
    unittest.main()
