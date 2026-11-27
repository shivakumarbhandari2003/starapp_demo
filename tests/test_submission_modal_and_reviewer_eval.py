import unittest
import json
from starapp.app import StarAppController
from project_helpers import give_project
from starapp.storage import store

class TestSubmissionModalAndReviewerEvaluation(unittest.TestCase):
    def setUp(self):
        self.ctrl = StarAppController()
        self.ctrl.initialize()
        self.cadet_id = "m_b1_1"
        self.badge_id = "badge_b1_signals"
        self.reviewer_id = "m_b2_1"
        give_project(store, self.badge_id, self.cadet_id)   # the mapped reviewer has sent the project

    def _ensure_clean_state(self):
        cur = store.db.conn.cursor()
        cur.execute("DELETE FROM assessment_marksheets WHERE cosmonaut_id = ? AND badge_id = ?", (self.cadet_id, self.badge_id))
        cur.execute("DELETE FROM project_submissions WHERE cosmonaut_id = ? AND badge_id = ?", (self.cadet_id, self.badge_id))
        store.db.conn.commit()
        store.submissions = {k: v for k, v in store.submissions.items() if not (v.cosmonaut_id == self.cadet_id and v.badge_id == self.badge_id)}
        store.assessments = {k: v for k, v in store.assessments.items() if not (v.cosmonaut_id == self.cadet_id and v.badge_id == self.badge_id)}

    def test_01_submission_modal_opens_on_demand_and_not_on_page(self):
        """Verify submission portal only pops up as a modal and is not embedded on page body."""
        self.ctrl.handle_event("select_demo_account", self.cadet_id)
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")
        page_html = self.ctrl.render()

        # The submission form should NOT be on the page body
        self.assertNotIn('id="submission-pdf-file"', page_html)
        self.assertNotIn('id="submission-portal-section"', page_html)

        # Trigger open_submission_modal action
        self.ctrl.handle_event("open_submission_modal", self.badge_id)
        self.assertEqual(self.ctrl.active_modal, "submission_portal_modal")
        self.assertEqual(self.ctrl.modal_payload.get("badge_id"), self.badge_id)

        modal_html = self.ctrl.render()
        self.assertIn("Submit Project Deliverables", modal_html)
        self.assertNotIn("SmartFit: The Member Intelligence Challenge", modal_html)  # the project lives on its page, not in the dialog
        self.assertIn("submission-pdf-file", modal_html)
        self.assertIn("submission-code-file", modal_html)
        self.assertIn("submission-github-url", modal_html)

    def test_02_single_submission_and_edit_in_place(self):
        """Verify cosmonaut can submit only once, and subsequent submissions edit in place."""
        self._ensure_clean_state()
        self.ctrl.handle_event("select_demo_account", self.cadet_id)

        # 1. Initial submission
        payload_1 = {
            "badge_id": self.badge_id,
            "pdf_name": "Initial_Architecture_Report.pdf",
            "pdf_payload": "data/initial_report.pdf",
            "code_name": "signals_v1.py",
            "code_payload": "print('Version 1')",
            "github_url": "https://github.com/starapp/signals-v1"
        }
        self.ctrl.handle_event("submit_project_deliverable", json.dumps(payload_1))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify exactly 1 submission in DB and memory
        subs = store.get_submissions_for_cosmonaut(self.cadet_id, self.badge_id)
        self.assertEqual(len(subs), 1, "Must have exactly 1 submission")
        sub_id = subs[0].id
        self.assertEqual(subs[0].code_name, "signals_v1.py")
        self.assertEqual(subs[0].status, "pending")

        # 2. Resubmit / edit deliverables
        payload_2 = {
            "badge_id": self.badge_id,
            "pdf_name": "Updated_Architecture_Report.pdf",
            "pdf_payload": "data/updated_report.pdf",
            "code_name": "signals_v2_improved.py",
            "code_payload": "print('Version 2 Improved')",
            "github_url": "https://github.com/starapp/signals-v2"
        }
        self.ctrl.handle_event("submit_project_deliverable", json.dumps(payload_2))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify still exactly 1 submission in DB and memory (edited in place)
        subs_after = store.get_submissions_for_cosmonaut(self.cadet_id, self.badge_id)
        self.assertEqual(len(subs_after), 1, "Must STILL have exactly 1 submission after edit")
        self.assertEqual(subs_after[0].id, sub_id, "Submission ID must be preserved")
        self.assertEqual(subs_after[0].code_name, "signals_v2_improved.py")
        self.assertEqual(subs_after[0].status, "pending")

    def test_03_reviewer_queue_shows_single_card_and_inspect_opens_detail_page(self):
        """Verify reviewer queue deduplicates cards and clicking inspect deliverables loads 50-mark rubric."""
        self._ensure_clean_state()

        # Create 1 submission
        self.ctrl.handle_event("select_demo_account", self.cadet_id)
        self.ctrl.handle_event("submit_project_deliverable", json.dumps({
            "badge_id": self.badge_id,
            "pdf_name": "Architecture_Spec.pdf",
            "pdf_payload": "data/sample.pdf",
            "code_name": "impl.py",
            "code_payload": "print('ok')",
            "github_url": "https://github.com/starapp/signals"
        }))
        subs = store.get_submissions_for_cosmonaut(self.cadet_id, self.badge_id)
        self.assertEqual(len(subs), 1)
        sub = subs[0]

        # Ensure reviewer is assigned
        tl = store.get_timeline(self.badge_id, self.cadet_id)
        if tl:
            tl.reviewer_id = self.reviewer_id
            store.save_timeline(tl)
        badge = store.get_badge(self.badge_id)
        if badge:
            badge.assigned_reviewer_id = self.reviewer_id
            if self.cadet_id not in badge.assigned_cosmonaut_ids:
                badge.assigned_cosmonaut_ids.append(self.cadet_id)
            store.save_badge(badge)

        # Log in as reviewer: the Badge Review schedule has one enabled Assessment button for this submission
        self.ctrl.handle_event("select_demo_account", self.reviewer_id)
        self.ctrl.handle_event("nav_cosmonaut", "c_badge_reviews")
        schedule_html = self.ctrl.render()
        self.assertIn("rv-assess", schedule_html)
        self.assertEqual(schedule_html.count(f"open_reviewer_assessment_page', '{sub.id}'"), 1)

        # Click Assessment
        self.ctrl.handle_event("open_reviewer_assessment_page", sub.id)
        self.assertEqual(self.ctrl.current_view, "c_assessment_detail")

        # Render detail page: MUST NOT throw TypeError and MUST contain viewers and rubric
        detail_html = self.ctrl.render()
        self.assertIn("review-detail-workspace", detail_html)
        self.assertIn("reviewer-rubric-form", detail_html)
        self.assertIn("1. Business Understanding", detail_html)
        self.assertIn("2. Architecture Report", detail_html)
        self.assertIn("3. Technical Knowledge", detail_html)
        self.assertIn("4. Presentation", detail_html)
        self.assertIn("5. Q&amp;A Technical Defense", detail_html)
        self.assertIn("Sum of Rubric Marks:", detail_html)

    def test_04_reviewer_submits_50_mark_evaluation(self):
        """Verify reviewer can evaluate deliverables and save 50-mark marksheet."""
        self._ensure_clean_state()

        # Create submission
        self.ctrl.handle_event("select_demo_account", self.cadet_id)
        self.ctrl.handle_event("submit_project_deliverable", json.dumps({
            "badge_id": self.badge_id,
            "pdf_name": "Signals_Report.pdf",
            "pdf_payload": "data/sample.pdf",
            "code_name": "signals.py",
            "code_payload": "print('Signals active')",
            "github_url": "https://github.com/starapp/signals"
        }))
        subs = store.get_submissions_for_cosmonaut(self.cadet_id, self.badge_id)
        self.assertEqual(len(subs), 1)
        sub = subs[0]

        # Assign reviewer
        tl = store.get_timeline(self.badge_id, self.cadet_id)
        if tl:
            tl.reviewer_id = self.reviewer_id
            store.save_timeline(tl)
        else:
            from starapp.models import BadgeTimeline
            tl = BadgeTimeline(
                badge_id=self.badge_id,
                cosmonaut_id=self.cadet_id,
                reviewer_id=self.reviewer_id,
                assignment_date="2026-11-10",
                publication_date="2026-11-10",
                learning_start_date="2026-11-11",
                learning_end_date="2026-11-20",
                project_start_date="2026-11-21",
                project_end_date="2026-12-01",
                submission_deadline="2026-12-03",
                review_date="2026-12-05",
                expected_award_date="2026-12-06",
                status="active"
            )
            store.save_timeline(tl)
        badge = store.get_badge(self.badge_id)
        if badge:
            badge.assigned_reviewer_id = self.reviewer_id
            if self.cadet_id not in badge.assigned_cosmonaut_ids:
                badge.assigned_cosmonaut_ids.append(self.cadet_id)
            store.save_badge(badge)

        self.ctrl.handle_event("select_demo_account", self.reviewer_id)
        eval_payload = {
            "submission_id": sub.id,
            "bu": 9.0,
            "ar": 8.5,
            "tk": 9.0,
            "pr": 8.5,
            "qa": 9.0,
            "strengths": "Exceptional error handling and clean architecture.",
            "improvements": "Consider adding automated integration tests.",
            "feedback": "Outstanding implementation meeting all curriculum criteria.",
            "decision": "approve"
        }
        self.ctrl.handle_event("submit_reviewer_assessment", json.dumps(eval_payload))
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify evaluation stored in SQLite
        asms = store.get_assessments_for_cosmonaut(self.cadet_id)
        reviewer_asm = next((a for a in asms if a.submission_id == sub.id and a.assessor_role == "reviewer"), None)
        self.assertIsNotNone(reviewer_asm, "Reviewer assessment must be saved in database")
        self.assertEqual(reviewer_asm.total_marks, 44.0)
        self.assertEqual(reviewer_asm.decision, "recommend_approve")        # a recommendation: the Guardian gives the final decision
        self.assertEqual(store.get_submission(sub.id).status, "reviewer_assessed")

if __name__ == "__main__":
    unittest.main()
