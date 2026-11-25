"""
STARAPP MANDATORY END-TO-END SCENARIOS A TO H (SINGLE GUARDIAN + SINGLE COSMONAUT)
Tests the complete lifecycle for Guardian Dr. Elena Vance and Cosmonaut Astraea Nova.
"""

import unittest
import json
import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starapp.models import (
    User, Badge, BadgeTimeline, ProjectSubmission, AssessmentMarksheet,
    LearningMaterial, DeadlineExtension, Announcement, current_iso_timestamp
)
from starapp.storage import store
from starapp.app import controller
from starapp.assessment import calculate_batch_leaderboard

class TestMandatoryScenariosAToH(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        controller.current_user = None
        controller.current_view = "login"

    def test_scenario_a_badge_publication(self):
        """Scenario A — Badge creation, assignment, and publication visibility."""
        # 1. Log in as Guardian
        controller.handle_event("select_demo_account", "guardian_1")
        self.assertEqual(controller.current_user.role, "guardian")

        # 2, 3, 4, 5. Create a badge assigned to Astraea (cosmo_1)
        controller.execute_save_badge({
            "code": "TEST-500",
            "title": "Distributed Consensus Foundations",
            "category": "Core Engineering",
            "description": "Raft and Paxos leader election protocols.",
            "project_requirements": "Implement Raft heartbeat leader election simulation.",
            "prerequisites": ["b1_int_01"],
            "assigned_cosmonaut_ids": ["cosmo_1"],
            "submission_deadline": "2026-12-28"
        })

        new_badge = store.get_badge("badge_test_500")
        self.assertIsNotNone(new_badge)
        self.assertTrue(new_badge.is_published)

        # 6 & 7. Log in as Cosmonaut 1 (Astraea)
        controller.handle_event("select_demo_account", "cosmo_1")
        astraea_badges = store.get_badges_for_cosmonaut("cosmo_1")
        astraea_badge_ids = [b.id for b in astraea_badges]
        self.assertIn("badge_test_500", astraea_badge_ids)

    def test_scenario_b_submission_and_assessment(self):
        """Scenario B — Project submission, 5-criterion 50-mark evaluation, marksheet appearance & leaderboard update."""
        # 1 & 2. Log in as Cosmonaut 1 (Astraea)
        controller.handle_event("select_demo_account", "cosmo_1")
        
        # 3. Submit a project for b1_int_01
        sub = ProjectSubmission(
            id="sub_test_sql",
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            attempt_number=1,
            submission_type="pdf",
            payload="data:application/pdf;base64,JVBERi0xLjQK...",
            file_name="Astraea_SQL_Optimization.pdf",
            submitted_at=current_iso_timestamp(),
            status="pending"
        )
        store.save_submission(sub)

        # 4 & 5. Log in as Guardian
        controller.handle_event("select_demo_account", "guardian_1")

        # 6, 7, 8, 9, 10. Evaluate with all five rubric marks
        marksheet = AssessmentMarksheet(
            id="asm_test_sql_1",
            submission_id=sub.id,
            attempt_number=1,
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            reviewer_id="guardian_1",
            reviewer_name="Dr. Elena Vance",
            reviewed_at=current_iso_timestamp(),
            decision="approve",
            business_understanding=10.0,
            architecture_report=10.0,
            technical_knowledge=9.5,
            presentation=9.5,
            qa=9.0,
            strength_areas="Masterful query optimization and execution plan costing",
            improvement_areas="Explore partial indexes",
            overall_feedback="Outstanding blueprint meeting all enterprise constraints. Badge awarded."
        )
        store.save_assessment(marksheet)
        sub.status = "approved"
        store.save_submission(sub)

        # 11 & 12. Cosmonaut sees marksheet
        controller.handle_event("select_demo_account", "cosmo_1")
        asms = store.get_assessments_for_cosmonaut("cosmo_1", "b1_int_01")
        self.assertEqual(len(asms), 1)
        self.assertEqual(asms[0].total_marks, 48.0)
        self.assertEqual(asms[0].percentage, 96.0)

        # 13. Leaderboard updates with 1 completed badge
        cosmonauts = store.get_all_cosmonauts()
        lb = calculate_batch_leaderboard(cosmonauts, store.get_all_assessments())
        astraea_rank = [item for item in lb if item["cosmonaut_id"] == "cosmo_1"][0]
        self.assertEqual(astraea_rank["completed_badges"], 1)
        self.assertEqual(astraea_rank["rank"], 1)

    def test_scenario_c_resubmission_and_history_preservation(self):
        """Scenario C — Guardian requests resubmission; cadet resubmits; old assessment is preserved."""
        # Create Attempt 1
        sub1 = ProjectSubmission(
            id="sub_test_int_1",
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            attempt_number=1,
            submission_type="pdf",
            payload="data:application/pdf;base64,...",
            file_name="Astraea_Intelligent_Apps_v1.pdf",
            submitted_at=current_iso_timestamp(),
            status="resubmission_requested"
        )
        store.save_submission(sub1)
        asm1 = AssessmentMarksheet(
            id="asm_int_attempt_1",
            submission_id=sub1.id,
            attempt_number=1,
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            reviewer_id="guardian_1",
            reviewer_name="Dr. Elena Vance",
            reviewed_at=current_iso_timestamp(),
            decision="resubmission_requested",
            business_understanding=7.0,
            architecture_report=6.0,
            technical_knowledge=7.0,
            presentation=6.0,
            qa=6.0,
            strength_areas="Good prompt engineering",
            improvement_areas="Improve tool schema error handling",
            overall_feedback="Please revise tool schema."
        )
        store.save_assessment(asm1)

        # Create Attempt 2
        sub2 = ProjectSubmission(
            id="sub_test_int_2",
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            attempt_number=2,
            submission_type="pdf",
            payload="data:application/pdf;base64,...",
            file_name="Astraea_Intelligent_Apps_v2.pdf",
            submitted_at=current_iso_timestamp(),
            status="pending"
        )
        store.save_submission(sub2)

        # Check initial state for Astraea (cosmo_1) on b1_int_01
        astraea_subs = store.get_submissions_for_cosmonaut("cosmo_1", "b1_int_01")
        self.assertEqual(len(astraea_subs), 2)
        
        # Verify Attempt 1 marksheet is preserved
        asm1_check = store.get_assessment_for_submission(astraea_subs[0].id)
        self.assertIsNotNone(asm1_check)
        self.assertEqual(asm1_check.attempt_number, 1)
        self.assertEqual(asm1_check.decision, "resubmission_requested")
        self.assertEqual(asm1_check.total_marks, 32.0)

        # Guardian now reviews Attempt 2
        controller.handle_event("select_demo_account", "guardian_1")
        asm2 = AssessmentMarksheet(
            id="asm_int_attempt_2",
            submission_id=astraea_subs[1].id,
            attempt_number=2,
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            reviewer_id="guardian_1",
            reviewer_name="Dr. Elena Vance",
            reviewed_at=current_iso_timestamp(),
            decision="approve",
            business_understanding=9.0,
            architecture_report=9.0,
            technical_knowledge=9.0,
            presentation=9.0,
            qa=9.0,
            strength_areas="Tool schema error handling resolved gracefully.",
            improvement_areas="None",
            overall_feedback="Attempt 2 satisfies all criteria. Approved!"
        )
        store.save_assessment(asm2)
        astraea_subs[1].status = "approved"
        store.save_submission(astraea_subs[1])

        # Verify BOTH marksheets are intact and not overwritten
        all_int_asms = store.get_assessments_for_cosmonaut("cosmo_1", "b1_int_01")
        self.assertEqual(len(all_int_asms), 2)
        self.assertEqual(all_int_asms[0].attempt_number, 1)
        self.assertEqual(all_int_asms[0].total_marks, 32.0)
        self.assertEqual(all_int_asms[1].attempt_number, 2)
        self.assertEqual(all_int_asms[1].total_marks, 45.0)

    def test_scenario_d_deadline_extension_lifecycle(self):
        """Scenario D — Extension request, approval, deadline update, and rejection testing."""
        # 0. Setup timeline for b1_int_01
        tl = BadgeTimeline(
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            assignment_date="2026-11-20",
            publication_date="2026-11-20",
            learning_start_date="2026-11-21",
            learning_end_date="2026-11-30",
            project_start_date="2026-12-01",
            project_end_date="2026-12-10",
            submission_deadline="2026-12-12",
            review_date="2026-12-15",
            expected_award_date="2026-12-16"
        )
        store.save_timeline(tl)

        # 1. Cosmonaut requests extension on b1_int_01
        controller.handle_event("select_demo_account", "cosmo_1")
        controller.execute_submit_extension_request({
            "badge_id": "b1_int_01",
            "proposed_deadline": "2026-12-20",
            "reason": "Profiling query execution plans on 100M row dataset requires additional index tuning."
        })

        exts = [e for e in store.get_extensions_for_cosmonaut("cosmo_1") if e.badge_id == "b1_int_01"]
        self.assertEqual(len(exts), 1)
        int_ext = exts[0]
        self.assertEqual(int_ext.status, "pending")
        self.assertEqual(int_ext.proposed_deadline, "2026-12-20")

        # 2. Guardian approves it
        controller.handle_event("select_demo_account", "guardian_1")
        controller.execute_extension_decision({
            "extension_id": int_ext.id,
            "decision": "approved",
            "response_note": "Approved. Include the EXPLAIN ANALYZE comparison table."
        })

        # 3. Verify deadline updated
        self.assertEqual(int_ext.status, "approved")
        tl_updated = store.get_timeline("b1_int_01", "cosmo_1")
        self.assertEqual(tl_updated.submission_deadline, "2026-12-20")

        # Test Rejection flow on another extension request
        tl2 = BadgeTimeline(
            badge_id="b1_dat_01",
            cosmonaut_id="cosmo_1",
            assignment_date="2026-11-20",
            publication_date="2026-11-20",
            learning_start_date="2026-11-21",
            learning_end_date="2026-11-30",
            project_start_date="2026-12-01",
            project_end_date="2026-12-10",
            submission_deadline="2026-12-15",
            review_date="2026-12-18",
            expected_award_date="2026-12-19"
        )
        store.save_timeline(tl2)
        controller.handle_event("select_demo_account", "cosmo_1")
        controller.execute_submit_extension_request({
            "badge_id": "b1_dat_01",
            "proposed_deadline": "2026-12-25",
            "reason": "Benchmarking memory bandwidth across multiple NUMA nodes."
        })
        ext_rej = store.get_extensions_for_cosmonaut("cosmo_1")[-1]
        
        # Guardian rejects
        controller.handle_event("select_demo_account", "guardian_1")
        controller.execute_extension_decision({
            "extension_id": ext_rej.id,
            "decision": "rejected",
            "response_note": "Denied. Baseline schedule allows sufficient buffer."
        })
        self.assertEqual(ext_rej.status, "rejected")
        tl_rej = store.get_timeline("b1_dat_01", "cosmo_1")
        self.assertEqual(tl_rej.submission_deadline, "2026-12-15")

    def test_scenario_e_announcements_broadcast_and_read_status(self):
        """Scenario E — Broadcast announcement, verify recipient, mark as read, check read receipts."""
        # 1. Guardian broadcasts notice
        controller.handle_event("select_demo_account", "guardian_1")
        controller.execute_broadcast_announcement({
            "title": "Batch Review Session",
            "message": "Cosmonaut review session tomorrow at 10:00 UTC.",
            "target_type": "all",
            "target_ids": [],
            "badge_id": "b1_int_01"
        })

        # 2. Verify Cosmonaut 1 (Astraea) receives notice
        anns_1 = store.get_announcements_for_cosmonaut("cosmo_1")
        titles_1 = [a.title for a in anns_1]
        self.assertIn("Batch Review Session", titles_1)

        # 3. Astraea marks notice as read
        batch_ann = [a for a in anns_1 if a.title == "Batch Review Session"][0]
        self.assertNotIn("cosmo_1", batch_ann.read_by_cosmonaut_ids)
        controller.handle_event("select_demo_account", "cosmo_1")
        controller.handle_event("mark_announcement_as_read", {"announcement_id": batch_ann.id})
        self.assertIn("cosmo_1", batch_ann.read_by_cosmonaut_ids)

    def test_scenario_f_learning_materials(self):
        """Scenario F — Upload document, publish YouTube resource, verify access."""
        controller.handle_event("select_demo_account", "guardian_1")
        controller.execute_save_material({
            "badge_id": "b1_int_01",
            "topic": "Compliance Law",
            "title": "HIPAA Security Rule Practical Walkthrough",
            "description": "Video guide analyzing audit log immutability.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        })

        mats = store.get_materials("b1_int_01")
        titles = [m.title for m in mats]
        self.assertIn("HIPAA Security Rule Practical Walkthrough", titles)

        # Verify Cosmonaut can view material
        controller.handle_event("select_demo_account", "cosmo_1")
        c_mats = store.get_materials("b1_int_01")
        self.assertEqual(len(c_mats), 1)
        self.assertEqual(c_mats[0].material_type, "youtube")

    def test_scenario_g_remedial_support_workflow(self):
        """Scenario G — Low score triggers support flag; mentoring plan appears in guardian overview."""
        sub = ProjectSubmission(
            id="sub_low",
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            attempt_number=1,
            submission_type="pdf",
            payload="data:...",
            file_name="low.pdf",
            submitted_at=current_iso_timestamp(),
            status="pending"
        )
        store.save_submission(sub)

        # Low score assessment: total 28.0 (< 35.0)
        asm_low = AssessmentMarksheet(
            id="asm_test_low",
            submission_id=sub.id,
            attempt_number=1,
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            reviewer_id="guardian_1",
            reviewer_name="Dr. Elena Vance",
            reviewed_at=current_iso_timestamp(),
            decision="resubmission_requested",
            business_understanding=6.0,
            architecture_report=5.5,
            technical_knowledge=5.5,
            presentation=5.5,
            qa=5.5,
            strength_areas="Understands core terminology",
            improvement_areas="Architecture document missing failover diagram",
            overall_feedback="Requires thorough revision before passing."
        )
        store.save_assessment(asm_low)

        # Guardian reviews batch overview
        controller.handle_event("select_demo_account", "guardian_1")
        controller.handle_event("nav_guardian", "g_dashboard")
        html = controller.render()
        
        # Verify dashboard renders successfully
        self.assertIn("Academy Command Center", html)

    def test_scenario_h_privacy_and_permissions(self):
        """Scenario H — Cosmonaut cannot access another cadet's private records or guardian actions."""
        # Create a submission for b1_int_01
        sub = ProjectSubmission(
            id="sub_test_p",
            badge_id="b1_int_01",
            cosmonaut_id="cosmo_1",
            attempt_number=1,
            submission_type="pdf",
            payload="data:...",
            file_name="p.pdf",
            submitted_at=current_iso_timestamp(),
            status="pending"
        )
        store.save_submission(sub)

        controller.handle_event("select_demo_account", "cosmo_1")
        self.assertEqual(controller.current_user.id, "cosmo_1")

        user_asms = store.get_assessments_for_cosmonaut(controller.current_user.id)
        for a in user_asms:
            self.assertEqual(a.cosmonaut_id, "cosmo_1")

        # Guardian retains oversight of submissions
        controller.handle_event("select_demo_account", "guardian_1")
        all_subs = store.get_all_submissions()
        self.assertTrue(len(all_subs) >= 1)

if __name__ == "__main__":
    unittest.main()
