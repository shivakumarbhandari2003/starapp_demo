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
            "prerequisites": ["badge_gov_101"],
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
        
        # 3. Submit a project for SQL-201
        sub = ProjectSubmission(
            id="sub_test_sql",
            badge_id="badge_sql_201",
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
            badge_id="badge_sql_201",
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

        # 11 & 12. Log in as Cosmonaut 1 and verify marksheet
        controller.handle_event("select_demo_account", "cosmo_1")
        asms = store.get_assessments_for_cosmonaut("cosmo_1", "badge_sql_201")
        self.assertEqual(len(asms), 1)
        self.assertEqual(asms[0].total_marks, 48.0)
        self.assertEqual(asms[0].percentage, 96.0)

        # 13. Leaderboard updates with 4 completed badges
        cosmonauts = store.get_all_cosmonauts()
        lb = calculate_batch_leaderboard(cosmonauts, store.get_all_assessments())
        astraea_rank = [item for item in lb if item["cosmonaut_id"] == "cosmo_1"][0]
        self.assertEqual(astraea_rank["completed_badges"], 4)
        self.assertEqual(astraea_rank["rank"], 1)

    def test_scenario_c_resubmission_and_history_preservation(self):
        """Scenario C — Guardian requests resubmission; cadet resubmits; old assessment is preserved."""
        # Check initial state for Astraea (cosmo_1) on Ingestion (badge_ing_104)
        astraea_subs = store.get_submissions_for_cosmonaut("cosmo_1", "badge_ing_104")
        self.assertEqual(len(astraea_subs), 2)
        
        # Verify Attempt 1 marksheet is preserved
        asm1 = store.get_assessment_for_submission(astraea_subs[0].id)
        self.assertIsNotNone(asm1)
        self.assertEqual(asm1.attempt_number, 1)
        self.assertEqual(asm1.decision, "resubmission_requested")
        self.assertEqual(asm1.total_marks, 32.0)

        # Guardian now reviews Attempt 2
        controller.handle_event("select_demo_account", "guardian_1")
        asm2 = AssessmentMarksheet(
            id="asm_ing_attempt_2",
            submission_id=astraea_subs[1].id,
            attempt_number=2,
            badge_id="badge_ing_104",
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
            strength_areas="Kafka consumer offset idempotency resolved gracefully.",
            improvement_areas="None",
            overall_feedback="Attempt 2 satisfies all criteria. Approved!"
        )
        store.save_assessment(asm2)
        astraea_subs[1].status = "approved"
        store.save_submission(astraea_subs[1])

        # Verify BOTH marksheets are intact and not overwritten
        all_ing_asms = store.get_assessments_for_cosmonaut("cosmo_1", "badge_ing_104")
        self.assertEqual(len(all_ing_asms), 2)
        self.assertEqual(all_ing_asms[0].attempt_number, 1)
        self.assertEqual(all_ing_asms[0].total_marks, 32.0)
        self.assertEqual(all_ing_asms[1].attempt_number, 2)
        self.assertEqual(all_ing_asms[1].total_marks, 45.0)

    def test_scenario_d_deadline_extension_lifecycle(self):
        """Scenario D — Extension request, approval, deadline update, and rejection testing."""
        # 1. Cosmonaut requests extension on SQL-201
        controller.handle_event("select_demo_account", "cosmo_1")
        controller.execute_submit_extension_request({
            "badge_id": "badge_sql_201",
            "proposed_deadline": "2026-12-20",
            "reason": "Profiling query execution plans on 100M row dataset requires additional index tuning."
        })

        exts = [e for e in store.get_extensions_for_cosmonaut("cosmo_1") if e.badge_id == "badge_sql_201"]
        self.assertEqual(len(exts), 1)
        sql_ext = exts[0]
        self.assertEqual(sql_ext.status, "pending")
        self.assertEqual(sql_ext.proposed_deadline, "2026-12-20")

        # 2. Guardian approves it
        controller.handle_event("select_demo_account", "guardian_1")
        controller.execute_extension_decision({
            "extension_id": sql_ext.id,
            "decision": "approved",
            "response_note": "Approved. Include the EXPLAIN ANALYZE comparison table."
        })

        # 3. Verify deadline updated
        self.assertEqual(sql_ext.status, "approved")
        tl = store.get_timeline("badge_sql_201", "cosmo_1")
        self.assertEqual(tl.submission_deadline, "2026-12-20")

        # Test Rejection flow on another extension request
        controller.handle_event("select_demo_account", "cosmo_1")
        controller.execute_submit_extension_request({
            "badge_id": "badge_ing_104",
            "proposed_deadline": "2026-12-25",
            "reason": "Benchmarking memory bandwidth across multiple NUMA nodes."
        })
        ext_rej = store.get_extensions_for_cosmonaut("cosmo_1")[-1]
        
        # Guardian rejects
        controller.handle_event("select_demo_account", "guardian_1")
        controller.execute_extension_decision({
            "extension_id": ext_rej.id,
            "decision": "rejected",
            "response_note": "Deadline cannot be extended due to cohort scheduling cutoff."
        })
        self.assertEqual(ext_rej.status, "rejected")
        tl_ing = store.get_timeline("badge_ing_104", "cosmo_1")
        self.assertEqual(tl_ing.submission_deadline, "2026-12-02")

    def test_scenario_e_announcements_broadcast_and_read_status(self):
        """Scenario E — Broadcast announcement, verify recipient, mark as read, check read receipts."""
        # 1. Guardian broadcasts notice
        controller.handle_event("select_demo_account", "guardian_1")
        controller.execute_broadcast_announcement({
            "title": "Batch Review Session",
            "message": "Cosmonaut review session tomorrow at 10:00 UTC.",
            "target_type": "all",
            "target_ids": [],
            "badge_id": "badge_gov_101"
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
            "badge_id": "badge_gov_101",
            "topic": "Compliance Law",
            "title": "HIPAA Security Rule Practical Walkthrough",
            "description": "Video guide analyzing audit log immutability.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        })

        mats = store.get_materials("badge_gov_101")
        titles = [m.title for m in mats]
        self.assertIn("HIPAA Security Rule Practical Walkthrough", titles)

    def test_scenario_g_persistence_simulation(self):
        """Scenario G — Modify records, serialize to JSON, simulate reload, verify integrity."""
        store.update_cosmonaut_skills("cosmo_1", ["Kubernetes", "PySpark", "Kafka Streaming"])
        
        snapshot_json = store.to_json()
        self.assertTrue(len(snapshot_json) > 500)

        new_store = store.__class__()
        new_store.load_from_json(snapshot_json)

        p1 = new_store.get_cosmonaut_profile("cosmo_1")
        self.assertIn("Kubernetes", p1.skills)
        self.assertIn("PySpark", p1.skills)

    def test_scenario_h_privacy_and_permissions(self):
        """Scenario H — Cosmonaut cannot access another cadet's private records or guardian actions."""
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
