"""
STARAPP COMPREHENSIVE AUTOMATED TEST SUITE (SINGLE GUARDIAN + SINGLE COSMONAUT)
Executes unit, workflow, and regression tests for StarApp domain logic.
"""

import unittest
import json
import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starapp.models import (
    User, CosmonautProfile, Badge, BadgeTimeline, ProjectSubmission,
    AssessmentMarksheet, LearningMaterial, DeadlineExtension, Announcement
)
from starapp.storage import store
from starapp.assessment import (
    validate_rubric_scores, calculate_assessment_totals,
    calculate_batch_aggregate_analytics, calculate_batch_leaderboard,
    calculate_cosmonaut_score_summary
)
from starapp.roadmap import compute_milestone_state, generate_roadmap_graph
from starapp.validation import (
    validate_badge_input, validate_submission_input,
    validate_extension_request, validate_announcement_input
)
from starapp.app import controller

class TestModelsAndSerialization(unittest.TestCase):
    def test_user_serialization(self):
        user = User("u1", "cadet1", "cadet1@starapp.dev", "cosmonaut", "Cadet One")
        d = user.to_dict()
        self.assertEqual(d["id"], "u1")
        self.assertEqual(d["role"], "cosmonaut")
        u2 = User.from_dict(d)
        self.assertEqual(u2.name, "Cadet One")

    def test_assessment_rubric_calculation(self):
        asm = AssessmentMarksheet(
            id="asm_test",
            submission_id="sub_test",
            attempt_number=1,
            badge_id="badge_gov_101",
            cosmonaut_id="cosmo_1",
            reviewer_id="guardian_1",
            reviewer_name="Dr. Elena Vance",
            reviewed_at="2026-11-07T12:00:00Z",
            decision="approve",
            business_understanding=9.5,
            architecture_report=9.0,
            technical_knowledge=9.5,
            presentation=9.0,
            qa=9.0,
            strength_areas="High clarity",
            improvement_areas="None",
            overall_feedback="Excellent work"
        )
        self.assertEqual(asm.total_marks, 46.0)
        self.assertEqual(asm.percentage, 92.0)
        d = asm.to_dict()
        self.assertEqual(d["total_marks"], 46.0)
        asm2 = AssessmentMarksheet.from_dict(d)
        self.assertEqual(asm2.percentage, 92.0)


class TestAssessmentAndAnalytics(unittest.TestCase):
    def test_rubric_validation_boundaries(self):
        valid, err = validate_rubric_scores(10.0, 9.5, 8.0, 7.5, 10.0)
        self.assertTrue(valid)
        self.assertIsNone(err)

        valid, err = validate_rubric_scores(10.5, 9.0, 8.0, 7.0, 6.0)
        self.assertFalse(valid)
        self.assertIn("must be between 0.0 and 10.0", err)

        valid, err = validate_rubric_scores(-1.0, 9.0, 8.0, 7.0, 6.0)
        self.assertFalse(valid)
        self.assertIn("must be between 0.0 and 10.0", err)

    def test_batch_leaderboard_ranking(self):
        store.reset_to_seed()
        cosmonauts = store.get_all_cosmonauts()
        assessments = store.get_all_assessments()

        leaderboard = calculate_batch_leaderboard(cosmonauts, assessments)
        self.assertEqual(len(leaderboard), 1)
        # Astraea Nova has 3 completed badges (48, 47, 49 = avg 48.0), should be rank #1
        self.assertEqual(leaderboard[0]["cosmonaut_id"], "cosmo_1")
        self.assertEqual(leaderboard[0]["rank"], 1)
        self.assertEqual(leaderboard[0]["average_marks"], 48.0)


class TestRoadmapPrerequisites(unittest.TestCase):
    def test_prerequisite_unlocking_logic(self):
        b_cur = store.get_badge("badge_cur_102")  # Requires badge_gov_101
        self.assertIn("badge_gov_101", b_cur.prerequisites)

        # If GOV-101 is not approved, CUR-102 must be locked
        state_locked = compute_milestone_state(b_cur, "cosmo_test", set())
        self.assertEqual(state_locked, "locked")

        # If GOV-101 is approved, CUR-102 becomes active
        state_active = compute_milestone_state(b_cur, "cosmo_test", {"badge_gov_101"})
        self.assertEqual(state_active, "active")

        # If CUR-102 is also approved, CUR-102 becomes completed
        state_completed = compute_milestone_state(b_cur, "cosmo_test", {"badge_gov_101", "badge_cur_102"})
        self.assertEqual(state_completed, "completed")

    def test_5_badge_initial_and_dynamic_unlocking_chain(self):
        store.reset_to_seed()
        badges = store.get_all_badges()
        assessments = store.get_all_assessments()
        submissions = store.get_all_submissions()

        # Check for Cosmonaut Astraea:
        for cosmo in store.get_all_cosmonauts():
            graph = generate_roadmap_graph(badges, cosmo.id, assessments, submissions)
            # Exactly 5 badges initially
            self.assertEqual(len(graph), 5, f"Cosmonaut {cosmo.id} should have exactly 5 badges initially")
            # 3 completed
            self.assertEqual(graph[0]["state"], "completed")
            self.assertEqual(graph[1]["state"], "completed")
            self.assertEqual(graph[2]["state"], "completed")
            # 1 at present
            self.assertEqual(graph[3]["state"], "active")
            self.assertTrue(graph[3]["is_current_active"])
            # 1 locked
            self.assertEqual(graph[4]["state"], "locked")
            self.assertFalse(graph[4]["is_current_active"])

        # Guardian creates a new badge for cohort
        controller.current_user = store.get_user_by_id("guardian_1")
        controller.execute_save_badge({
            "code": "ADV-300",
            "title": "Autonomous Stream Processing",
            "description": "Stateful streaming and windowed joins.",
            "project_requirements": "Build real-time sliding window consumer.",
            "prerequisites": ["badge_sql_201"]
        })

        badges_updated = store.get_all_badges()
        for cosmo in store.get_all_cosmonauts():
            graph2 = generate_roadmap_graph(badges_updated, cosmo.id, assessments, submissions)
            self.assertEqual(len(graph2), 6, f"Cosmonaut {cosmo.id} should have 6 badges now")
            # 3 completed
            self.assertEqual(graph2[0]["state"], "completed")
            self.assertEqual(graph2[1]["state"], "completed")
            self.assertEqual(graph2[2]["state"], "completed")
            # 4th badge is still active
            self.assertEqual(graph2[3]["state"], "active")
            # 5th badge (SQL-201) is UNLOCKED (active) now!
            self.assertEqual(graph2[4]["state"], "active", "Previously locked badge must be unlocked")
            # 6th badge (ADV-300) is now locked!
            self.assertEqual(graph2[5]["state"], "locked", "Newly created badge must be locked")

    def test_badge_lifecycle_timeline_window_and_guardian_decision(self):
        """Verify Guardian decision of all 6 timeline milestones and rendering in Cosmonaut timeline window."""
        store.reset_to_seed()
        controller.handle_event("select_demo_account", "guardian_1")

        # Guardian sets/decides all 6 timeline milestones for a badge
        controller.execute_save_badge({
            "code": "TIME-601",
            "title": "Real-Time Pipeline Architectures",
            "category": "Data Engineering",
            "description": "Stream processing and stateful aggregations.",
            "project_requirements": "Implement tumbling window processor.",
            "assigned_cosmonaut_ids": ["cosmo_1"],
            "assignment_date": "2026-11-10",
            "learning_start_date": "2026-11-11",
            "learning_end_date": "2026-11-18",
            "project_start_date": "2026-11-19",
            "project_end_date": "2026-11-26",
            "submission_deadline": "2026-11-28",
            "review_date": "2026-12-01",
            "expected_award_date": "2026-12-05"
        })

        badge = store.get_badge("badge_time_601")
        self.assertIsNotNone(badge)
        self.assertEqual(badge.default_timeline["assignment_date"], "2026-11-10")
        self.assertEqual(badge.default_timeline["learning_start_date"], "2026-11-11")
        self.assertEqual(badge.default_timeline["learning_end_date"], "2026-11-18")
        self.assertEqual(badge.default_timeline["project_start_date"], "2026-11-19")
        self.assertEqual(badge.default_timeline["project_end_date"], "2026-11-26")
        self.assertEqual(badge.default_timeline["submission_deadline"], "2026-11-28")
        self.assertEqual(badge.default_timeline["review_date"], "2026-12-01")
        self.assertEqual(badge.default_timeline["expected_award_date"], "2026-12-05")

        # Verify Cosmonaut timeline record received Guardian's decisions
        tl = store.get_timeline(badge.id, "cosmo_1")
        self.assertIsNotNone(tl)
        self.assertEqual(tl.assignment_date, "2026-11-10")
        self.assertEqual(tl.learning_start_date, "2026-11-11")
        self.assertEqual(tl.learning_end_date, "2026-11-18")
        self.assertEqual(tl.project_start_date, "2026-11-19")
        self.assertEqual(tl.project_end_date, "2026-11-26")
        self.assertEqual(tl.submission_deadline, "2026-11-28")
        self.assertEqual(tl.review_date, "2026-12-01")
        self.assertEqual(tl.expected_award_date, "2026-12-05")

        # Verify Cosmonaut timeline window HTML content
        controller.handle_event("select_demo_account", "cosmo_1")
        controller.handle_event("open_badge_detail_modal", {"badge_id": badge.id})
        self.assertEqual(controller.active_modal, "badge_detail")
        html = controller.render()
        self.assertIn("Badge &amp; Project Allocated", html)
        self.assertIn("Learning Time", html)
        self.assertIn("Project Time", html)
        self.assertIn("Submission Date", html)
        self.assertIn("Review Date", html)
        self.assertIn("Badge Earned Date", html)
        self.assertIn("2026-11-10", html)
        self.assertIn("2026-11-28", html)
        self.assertIn("2026-12-01", html)
        self.assertIn("2026-12-05", html)


class TestSubmissionAndAttemptPreservation(unittest.TestCase):
    def test_multi_attempt_history_retention(self):
        store.reset_to_seed()
        # Astraea Nova has 2 submissions on ING-104 in seed data
        astraea_subs = store.get_submissions_for_cosmonaut("cosmo_1", "badge_ing_104")
        self.assertEqual(len(astraea_subs), 2)
        self.assertEqual(astraea_subs[0].attempt_number, 1)
        self.assertEqual(astraea_subs[1].attempt_number, 2)
        # Attempt 1 has an assessment with decision resubmission_requested
        asm1 = store.get_assessment_for_submission(astraea_subs[0].id)
        self.assertIsNotNone(asm1)
        self.assertEqual(asm1.decision, "resubmission_requested")


class TestDeadlineExtensionWorkflow(unittest.TestCase):
    def test_extension_approval_updates_timeline(self):
        store.reset_to_seed()
        ext = store.get_extension("ext_1")
        self.assertEqual(ext.status, "pending")
        self.assertEqual(ext.proposed_deadline, "2026-12-10")

        # Guardian Elena Vance approves the extension
        controller.current_user = store.get_user_by_id("guardian_1")
        controller.execute_extension_decision({
            "extension_id": "ext_1",
            "decision": "approved",
            "response_note": "Extension granted. Please ensure Kafka latency benchmarks are included."
        })

        # Verify extension is approved
        ext_updated = store.get_extension("ext_1")
        self.assertEqual(ext_updated.status, "approved")
        self.assertEqual(ext_updated.guardian_response, "Extension granted. Please ensure Kafka latency benchmarks are included.")

        # Verify timeline for Astraea on badge_ing_104 is updated to 2026-12-10
        tl = store.get_timeline("badge_ing_104", "cosmo_1")
        self.assertIsNotNone(tl)
        self.assertEqual(tl.submission_deadline, "2026-12-10")


class TestAnnouncementsAndPrivacy(unittest.TestCase):
    def test_announcement_target_filtering(self):
        store.reset_to_seed()
        anns_astraea = store.get_announcements_for_cosmonaut("cosmo_1")
        ann_ids = [a.id for a in anns_astraea]
        self.assertIn("ann_1", ann_ids)
        self.assertIn("ann_2", ann_ids)

    def test_cosmonaut_cannot_access_other_private_dossier(self):
        controller.initialize()
        # Log in as cosmo_1
        controller.handle_event("select_demo_account", "cosmo_1")
        self.assertEqual(controller.current_user.id, "cosmo_1")
        self.assertEqual(controller.current_user.role, "cosmonaut")

        view_html = controller.render()
        self.assertIn("Astraea Nova", view_html)
        self.assertNotIn("Batch Orion-24 Lead", view_html)

if __name__ == "__main__":
    unittest.main()
