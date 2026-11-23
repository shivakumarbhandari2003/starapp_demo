"""
Targeted regression tests for the 6 verified outstanding issues:
1. Fix reviewer queue access so reviewers can see only projects assigned to them.
2. Enforce authorization for direct assessment access, including backend/API requests—not only UI navigation.
3. Isolate project-prompt retrieval so users can access only prompts they are authorized to view.
4. Ensure every badge mapping is correctly linked to its badge_id and cannot appear under another badge.
5. Fix export/import handling for reviewer_project_prompts, preserving the correct reviewer, cosmonaut, project, and prompt relationships.
6. Verify score consistency between reviewer preliminary score and Guardian final assessment.
"""

import unittest
import json
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import Badge, BadgeTimeline, ReviewerProjectPrompt
from backend.app.features.submissions.repository import SubmissionsRepository
from backend.app.features.submissions.service import SubmissionsService
from backend.app.features.evaluations.repository import EvaluationsRepository
from backend.app.features.evaluations.service import EvaluationsService
from backend.app.core.exceptions import ForbiddenException
from starapp.database import DatabaseManager


class TestOutstandingIssuesRegression(unittest.TestCase):

    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        self.ctrl.initialize()
        self.conn = store.db.conn

    def _make_timeline(self, badge_id, cosmonaut_id, reviewer_id):
        return BadgeTimeline(
            badge_id=badge_id,
            cosmonaut_id=cosmonaut_id,
            reviewer_id=reviewer_id,
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

    def test_01_reviewer_queue_access_isolation(self):
        """1. Reviewers must only see projects assigned to them in both backend API and queue."""
        sub_repo = SubmissionsRepository(self.conn)
        sub_service = SubmissionsService(sub_repo)

        # Create 2 submissions for Badge 1
        b = store.get_badge("badge_b1_signals")
        sub1 = sub_service.submit_project({
            "badge_id": b.id,
            "cosmonaut_id": "m_b1_1",
            "github_url": "https://github.com/cadet1/signals"
        })
        sub2 = sub_service.submit_project({
            "badge_id": b.id,
            "cosmonaut_id": "m_b1_2",
            "github_url": "https://github.com/cadet2/signals"
        })

        # Assign sub1 to Reviewer 1 (m_b2_1) and sub2 to Reviewer 2 (m_b2_2) in badge_timelines
        store.save_timeline(self._make_timeline(b.id, "m_b1_1", "m_b2_1"))
        store.save_timeline(self._make_timeline(b.id, "m_b1_2", "m_b2_2"))

        # Backend service check with reviewer_id
        pending_rev1 = sub_service.get_pending(reviewer_id="m_b2_1")
        pending_rev2 = sub_service.get_pending(reviewer_id="m_b2_2")

        rev1_sub_ids = [s["id"] for s in pending_rev1]
        rev2_sub_ids = [s["id"] for s in pending_rev2]

        self.assertIn(sub1["id"], rev1_sub_ids, "Reviewer 1 must see sub1")
        self.assertNotIn(sub2["id"], rev1_sub_ids, "Reviewer 1 must NOT see sub2")

        self.assertIn(sub2["id"], rev2_sub_ids, "Reviewer 2 must see sub2")
        self.assertNotIn(sub1["id"], rev2_sub_ids, "Reviewer 2 must NOT see sub1")

        # Guardian (reviewer_id=None) sees both
        pending_guardian = sub_service.get_pending(reviewer_id=None)
        all_ids = [s["id"] for s in pending_guardian]
        self.assertIn(sub1["id"], all_ids)
        self.assertIn(sub2["id"], all_ids)

    def test_02_direct_assessment_authorization_backend_and_ui(self):
        """2. Enforce authorization for direct assessment access on backend API and UI navigation."""
        eval_repo = EvaluationsRepository(self.conn)
        eval_service = EvaluationsService(eval_repo)
        sub_service = SubmissionsService(SubmissionsRepository(self.conn))

        b = store.get_badge("badge_b1_signals")
        sub = sub_service.submit_project({
            "badge_id": b.id,
            "cosmonaut_id": "m_b1_1",
            "github_url": "https://github.com/cadet1/auth-test"
        })

        # Explicitly assign to Reviewer 1 (m_b2_1)
        store.save_timeline(self._make_timeline(b.id, "m_b1_1", "m_b2_1"))

        # A) Backend API: Unauthorized Reviewer (m_b2_2) attempts evaluation -> must raise ForbiddenException
        eval_payload = {
            "submission_id": sub["id"],
            "decision": "approved",
            "business_understanding": 9.0,
            "architecture_report": 9.0,
            "technical_knowledge": 9.0,
            "presentation": 9.0,
            "qa": 9.0,
            "overall_feedback": "Unauthorized grading"
        }
        with self.assertRaises(ForbiddenException):
            eval_service.submit_evaluation(eval_payload, {"id": "m_b2_2", "name": "Unauthorized Reviewer"})

        # Lower-band user (Band B1 peer) attempts evaluation -> must raise ForbiddenException
        with self.assertRaises(ForbiddenException):
            eval_service.submit_evaluation(eval_payload, {"id": "m_b1_3", "name": "Peer Cadet", "band": "B1"})

        # Authorized Reviewer 1 (m_b2_1) succeeds
        eval_id = eval_service.submit_evaluation(eval_payload, {"id": "m_b2_1", "name": "Rohan Deshmukh"})
        self.assertIsNotNone(eval_id)

        # B) UI / Controller Navigation: Unauthorized reviewer attempts to open assessment page
        self.ctrl.handle_event("select_demo_account", "m_b2_2")
        self.ctrl.handle_event("open_reviewer_assessment_page", sub["id"])
        self.assertEqual(self.ctrl.flash_type, "error", "Unauthorized access must trigger error flash")
        self.assertNotEqual(self.ctrl.current_view, "c_assessment_detail", "Unauthorized reviewer cannot enter detail view")

        # Non-guardian attempts to open Guardian review detail portal
        self.ctrl.handle_event("open_submission_review_page", sub["id"])
        self.assertEqual(self.ctrl.flash_type, "error", "Non-guardian cannot open g_review_detail")

    def test_03_project_prompt_retrieval_isolation(self):
        """3. Isolate project-prompt retrieval so users can access only prompts they are authorized to view."""
        b1 = store.get_badge("badge_b1_signals")

        # Save a scoped prompt for Cadet 1 on Badge 1
        prompt1 = ReviewerProjectPrompt(
            id="prompt_test_cadet1",
            badge_id=b1.id,
            reviewer_id="m_b2_1",
            cosmonaut_ids=["m_b1_1"],
            title="Cadet 1 Signals Specification",
            description="Specific pipeline requirements for Cadet 1",
            status="sent"
        )
        store.save_reviewer_project_prompt(prompt1)

        # Map Cadet 1 to Badge 1 timeline
        store.save_timeline(self._make_timeline(b1.id, "m_b1_1", "m_b2_1"))

        # 1. Cadet 1 can view prompt1
        cadet1_prompt = store.get_project_prompt_for_cadet(b1.id, "m_b1_1")
        self.assertIsNotNone(cadet1_prompt)
        self.assertEqual(cadet1_prompt.id, "prompt_test_cadet1")

        # 2. Cadet 2 is mapped to Badge 1, but prompt1 is specifically restricted to Cadet 1 -> Cadet 2 must NOT receive it
        store.save_timeline(self._make_timeline(b1.id, "m_b1_2", "m_b2_1"))
        cadet2_prompt = store.get_project_prompt_for_cadet(b1.id, "m_b1_2")
        self.assertIsNone(cadet2_prompt, "Cadet 2 must not see prompt specifically assigned to Cadet 1")

        # 3. Cadet 3 is not mapped to Badge 1 at all -> must return None
        cadet3_prompt = store.get_project_prompt_for_cadet(b1.id, "m_b1_3")
        self.assertIsNone(cadet3_prompt, "Unmapped cadet must receive None")

    def test_04_badge_mapping_strictly_linked_to_badge_id(self):
        """4. Ensure every badge mapping is correctly linked to its badge_id and cannot appear under another badge."""
        b1 = store.get_badge("badge_b1_signals")
        b2 = store.get_badge("b1_dat_01")

        # Create mapping specifically for Badge 1
        mapping1 = {
            "id": "map_test_b1",
            "band": "B1",
            "badge": b1.title,
            "badge_id": b1.id,
            "cosmonauts": ["m_b1_1", "m_b1_2"],
            "reviewers": ["m_b2_1"],
            "review_dates": ["2026-11-25", "2026-11-26", "2026-11-27"],
            "status": "active"
        }
        store.save_band_mapping(mapping1)

        # In SQLite, band_mappings row must have badge_id populated
        row = self.conn.execute("SELECT badge_id FROM band_mappings WHERE id = 'map_test_b1'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], b1.id, "SQLite table band_mappings must store correct badge_id")

        # In Guardian allotment view helper, mapping must match Badge 1 and NOT Badge 2
        from starapp.views_guardian import render_guardian_badge_allotment
        cosmonauts = list(store.users.values())

        # Render allotment with only Badge 2
        html_b2 = render_guardian_badge_allotment(
            badges=[b2],
            cosmonauts=cosmonauts,
            all_band_mappings=[mapping1],
            all_timelines=store.timelines
        )
        # Mapping 1 (Signals) must not appear in the table for Badge 2
        self.assertNotIn("Signals Foundations", html_b2, "Signals mapping must NOT appear under Badge 2 (CUR-102)")

    def test_05_export_import_reviewer_project_prompts_roundtrip(self):
        """5. Fix export/import handling for reviewer_project_prompts, preserving relationships."""
        b = store.get_badge("badge_b1_signals")

        prompt = ReviewerProjectPrompt(
            id="proj_roundtrip_test",
            badge_id=b.id,
            reviewer_id="m_b2_1",
            cosmonaut_ids=["m_b1_1", "m_b1_2"],
            title="Roundtrip Preservation Test",
            description="Testing export and import preservation across SQLite",
            deliverables={"code": {"name": "test.py"}, "pdf": {"name": "test.pdf"}},
            requirements=["Req 1", "Req 2"],
            status="sent",
            created_at="2026-11-22T10:00:00Z",
            sent_at="2026-11-22T10:05:00Z"
        )
        store.save_reviewer_project_prompt(prompt)

        # 1. Export database to dict
        exported = store.db.export_to_dict()
        self.assertIn("reviewer_projects", exported)
        exported_prompts = exported["reviewer_projects"]
        target_p = next((p for p in exported_prompts if p["id"] == "proj_roundtrip_test"), None)
        self.assertIsNotNone(target_p, "Exported dictionary must contain saved project prompt")
        self.assertEqual(target_p["reviewer_id"], "m_b2_1")
        self.assertEqual(target_p["cosmonaut_ids"], ["m_b1_1", "m_b1_2"])

        # 2. Import into an in-memory fresh SQLite database
        fresh_db = DatabaseManager(":memory:")
        fresh_db.import_from_dict(exported)

        # 3. Verify record in fresh database
        imported_row = fresh_db.conn.execute(
            "SELECT * FROM reviewer_project_prompts WHERE id = 'proj_roundtrip_test'"
        ).fetchone()
        self.assertIsNotNone(imported_row, "Imported database must contain the prompt record")
        self.assertEqual(imported_row["reviewer_id"], "m_b2_1")
        self.assertEqual(imported_row["badge_id"], b.id)
        imported_c_ids = json.loads(imported_row["cosmonaut_ids_json"])
        self.assertEqual(imported_c_ids, ["m_b1_1", "m_b1_2"])
        fresh_db.close()

    def test_06_score_mismatch_investigation_and_consistency(self):
        """6. Reviewer score 44/50 defaults consistently in Guardian assessment unless intentionally adjusted."""
        sub_service = SubmissionsService(SubmissionsRepository(self.conn))
        b = store.get_badge("badge_b1_signals")

        # Create submission
        sub_dict = sub_service.submit_project({
            "badge_id": b.id,
            "cosmonaut_id": "m_b1_1",
            "github_url": "https://github.com/cadet1/score-test"
        })
        sub = store.get_submission(sub_dict["id"])

        # Map to Reviewer 1
        store.save_timeline(self._make_timeline(b.id, "m_b1_1", "m_b2_1"))

        # Reviewer 1 submits evaluation with total 44/50 (9.0, 9.0, 9.0, 8.5, 8.5)
        self.ctrl.handle_event("select_demo_account", "m_b2_1")
        self.ctrl.handle_event("submit_reviewer_assessment", json.dumps({
            "submission_id": sub.id,
            "bu": 9.0,
            "ar": 9.0,
            "tk": 9.0,
            "pr": 8.5,
            "qa": 8.5,
            "strengths": "Clean code.",
            "improvements": "None.",
            "feedback": "Passed.",
            "decision": "approve"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Check reviewer marksheet in store
        rev_asm = store.get_reviewer_assessment_for_submission(sub.id)
        self.assertIsNotNone(rev_asm)
        self.assertEqual(rev_asm.total_marks, 44.0)

        # Guardian opens review detail view: default form fields must inherit the 44.0 marks
        from starapp.views_guardian import render_guardian_review_detail
        detail_html = render_guardian_review_detail(
            sub, b, store.get_user_by_id("m_b1_1")
        )
        self.assertIn("44.0 / 50.0", detail_html, "Guardian view must clearly show reviewer score 44.0/50.0")

        # Case A: Guardian confirms without overriding scores -> must inherit exactly 44.0
        self.ctrl.handle_event("select_demo_account", "guardian_1")
        self.ctrl.handle_event("submit_guardian_final_assessment", json.dumps({
            "submission_id": sub.id,
            "decision": "approve"
        }))
        self.assertEqual(self.ctrl.flash_type, "success")

        g_asm = store.get_guardian_assessment_for_submission(sub.id)
        self.assertIsNotNone(g_asm)
        self.assertEqual(g_asm.total_marks, 44.0, "Guardian confirmation must maintain the reviewer's 44.0 marks")


if __name__ == "__main__":
    unittest.main()
