"""
Unit & Integration Test Suite: Cosmonaut Submission -> Reviewer Evaluation -> Guardian "Earn Badge" -> Gold Reflection Flow
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starapp.storage import store
from project_helpers import give_project
from starapp.app import StarAppController
from starapp.models import ProjectSubmission, AssessmentMarksheet, BadgeTimeline


class TestSubmissionReviewEarnFlow(unittest.TestCase):
    def setUp(self):
        self.app = StarAppController()
        self.app.initialize()
        self.cosmonaut = store.users.get("m_b1_1")  # Aarav Sharma, Band 1
        self.reviewer = store.users.get("m_b2_1")   # Priya Patel, Band 2 Reviewer
        self.guardian = store.users.get("guardian_1") # Training Mentor Guardian
        self.badge = store.get_badge("badge_b1_signals")
        if not self.badge:
            if store.badges:
                self.badge = list(store.badges.values())[0]
            else:
                from starapp.models import Badge
                self.badge = Badge(
                    id="badge_b1_signals",
                    code="B1-SIG-01",
                    title="Signals Foundations",
                    target_band="B1",
                    category="Action / Signals",
                    is_published=True,
                    is_allocated=True
                )
                store.save_badge(self.badge)

        # Clean DB & in-memory state for this badge & cadet
        cur = store.db.conn.cursor()
        cur.execute("DELETE FROM assessment_marksheets WHERE cosmonaut_id = ? AND badge_id = ?", (self.cosmonaut.id, self.badge.id))
        cur.execute("DELETE FROM project_submissions WHERE cosmonaut_id = ? AND badge_id = ?", (self.cosmonaut.id, self.badge.id))
        cur.execute("DELETE FROM reviewer_project_prompts WHERE badge_id = ?", (self.badge.id,))
        cur.execute("DELETE FROM badge_timelines WHERE cosmonaut_id = ? AND badge_id = ?", (self.cosmonaut.id, self.badge.id))
        cur.execute("INSERT INTO badge_timelines (badge_id, cosmonaut_id, status, expected_award_date) VALUES (?, ?, 'in_progress', '2026-12-15')", (self.badge.id, self.cosmonaut.id))
        store.db.conn.commit()

        store.timelines = {k: tl for k, tl in store.timelines.items() if not (tl.badge_id == self.badge.id and tl.cosmonaut_id == self.cosmonaut.id)}
        store.timelines[f"{self.badge.id}_{self.cosmonaut.id}"] = BadgeTimeline(
            badge_id=self.badge.id,
            cosmonaut_id=self.cosmonaut.id,
            assignment_date="2026-11-20",
            publication_date="2026-11-20",
            learning_start_date="2026-11-21",
            learning_end_date="2026-11-25",
            project_start_date="2026-11-26",
            project_end_date="2026-12-05",
            submission_deadline="2026-12-08",
            review_date="2026-12-10",
            expected_award_date="2026-12-15",
            status="active",
            reviewer_id=self.reviewer.id
        )
        store.reviewer_projects = {k: p for k, p in store.reviewer_projects.items() if getattr(p, "badge_id", "") != self.badge.id}

        # Ensure mapping exists for badge_b1_signals
        store.save_band_mapping({
            "id": f"map_{self.badge.id}",
            "band": "B1",
            "badge_id": self.badge.id,
            "badge_name": self.badge.title,
            "reviewers": [self.reviewer.id],
            "cosmonauts": [self.cosmonaut.id],
            "active": True
        })

        store.submissions = {k: s for k, s in store.submissions.items() if not (s.badge_id == self.badge.id and s.cosmonaut_id == self.cosmonaut.id)}
        store.assessments = {k: a for k, a in store.assessments.items() if not (a.badge_id == self.badge.id and a.cosmonaut_id == self.cosmonaut.id)}

    def test_end_to_end_submission_reviewer_guardian_earn_badge_flow(self):
        # -------------------------------------------------------------
        # STEP 1: Cosmonaut Submits Deliverables
        # -------------------------------------------------------------
        self.app.handle_event("select_demo_account", self.cosmonaut.id)
        self.app.current_view = "c_submission"

        submit_payload = {
            "badge_id": self.badge.id,
            "github_url": "https://github.com/starapp/custom-kafka-pipeline",
            "pdf_filename": "kafka_stream_architecture.pdf",
            "code_filename": "kafka_idempotent_consumer.py",
            "source_code": "def process_event(event):\n    return {'status': 'processed', 'id': event['id']}"
        }

        # Clear notifications before submitting to verify routing
        store.notifications = []
        give_project(store, self.badge.id, self.cosmonaut.id, reviewer_id=self.reviewer.id)
        self.app.handle_event("open_submission_modal", self.badge.id)
        self.app.handle_event("submit_project_deliverables", submit_payload)

        # Verify submission created
        submissions = store.get_submissions_for_cosmonaut(self.cosmonaut.id)
        sub = next((s for s in submissions if s.badge_id == self.badge.id), None)
        self.assertIsNotNone(sub, "Project submission should be created in store")
        self.assertEqual(sub.status, "pending")

        # Verify notification routed ONLY to assigned reviewer, NOT to guardian
        reviewer_notifs = [n for n in store.notifications if n.recipient_id == self.reviewer.id]
        guardian_notifs = [n for n in store.notifications if n.recipient_id == self.guardian.id]

        self.assertTrue(len(reviewer_notifs) > 0, "Assigned reviewer must receive submission notification")
        self.assertEqual(len(guardian_notifs), 0, "Guardian must NOT receive unreviewed submission notification initially")

        # -------------------------------------------------------------
        # STEP 2: Reviewer Views Deliverables & Submits Evaluation
        # -------------------------------------------------------------
        self.app.current_user = self.reviewer
        self.app.current_view = "c_badge_reviews"
        html_rev_queue = self.app.render()
        self.assertIn("Aarav Sharma", html_rev_queue)
        self.assertIn(f"open_reviewer_assessment_page', '{sub.id}'", html_rev_queue)           # the Assessment button is enabled: they have submitted

        # Reviewer opens assessment detail page
        self.app.handle_event("open_reviewer_assessment_page", sub.id)
        self.assertEqual(self.app.current_view, "c_assessment_detail")
        html_rev_detail = self.app.render()

        # Check deliverable dropdown options (Code, PDF/ODF, GitHub)
        self.assertIn("deliverable-type-select", html_rev_detail)
        self.assertIn("View PDF Document", html_rev_detail)
        self.assertIn("View Source Code", html_rev_detail)
        self.assertIn("View GitHub Repo", html_rev_detail)

        # Toggle tabs including "odf" normalized to "pdf"
        self.app.handle_event("change_viewer_tab", "odf")
        self.assertEqual(self.app.selected_viewer_tab, "pdf")
        self.app.handle_event("change_viewer_tab", "code")
        self.assertEqual(self.app.selected_viewer_tab, "code")

        # Reviewer submits 50-mark rubric evaluation
        reviewer_eval_payload = {
            "submission_id": sub.id,
            "bu": 9.0,
            "ar": 8.5,
            "tk": 9.0,
            "pr": 8.5,
            "qa": 8.0,
            "decision": "approve",
            "strengths": "Great consumer group partition management and error handling.",
            "improvements": "Consider adding automated circuit breaker for downstream REST sync.",
            "feedback": "Exemplary code quality and clear architecture specification."
        }

        # Clear notifications before reviewer submits
        store.notifications = []
        self.app.handle_event("submit_evaluation_marksheet", reviewer_eval_payload)

        # Verify submission status is updated to reviewer_assessed
        updated_sub = store.get_submission(sub.id)
        self.assertEqual(updated_sub.status, "reviewer_assessed")

        # Verify Guardian is now notified that review is ready for sign-off
        guardian_signoff_notifs = [n for n in store.notifications if n.recipient_id == "guardian_1"]
        self.assertTrue(len(guardian_signoff_notifs) > 0, "Guardian must be notified once Reviewer assesses submission")

        # -------------------------------------------------------------
        # STEP 3: Guardian Views 3-Level Hierarchy, Opens Marksheet, Clicks "Earn the Badge"
        # -------------------------------------------------------------
        self.app.current_user = self.guardian
        self.app.current_view = "g_reviews"
        self.app.handle_event("open_assessment_badge", self.badge.id)
        self.app.handle_event("open_assessment_cosmonaut", {"badge_id": self.badge.id, "cosmonaut_id": self.cosmonaut.id})
        html_g_queue = self.app.render()

        # Should show in "Ready for Guardian Sign-off"
        self.assertIn("Ready for Guardian Sign-off", html_g_queue)
        self.assertIn("Review Marks &amp; Earn Badge", html_g_queue)

        # Guardian opens detail page
        self.app.handle_event("open_submission_review_page", sub.id)
        self.assertEqual(self.app.current_view, "g_review_detail")
        html_g_detail = self.app.render()
        self.assertNotIn("Authorized Reviewer Score", html_g_detail)
        self.assertIn("Max 10", html_g_detail)

        # Check deliverable dropdown options in Guardian view
        self.assertIn("deliverable-type-select", html_g_detail)
        self.assertIn("View PDF Document", html_g_detail)
        self.assertIn("View Source Code", html_g_detail)
        self.assertIn("View GitHub Repo", html_g_detail)

        # Verify "Earn the Badge" action button is present with gold accent
        self.assertIn("Earn the Badge", html_g_detail)

        # Guardian submits final assessment (can adjust marks and approves milestone)
        guardian_earn_payload = {
            "submission_id": sub.id,
            "bu": 9.0,
            "ar": 9.0,
            "tk": 9.0,
            "pr": 9.0,
            "qa": 9.0,
            "decision": "approve",
            "strengths": "Outstanding idempotency handling, modular design.",
            "improvements": "Keep documentation updated in future modules.",
            "feedback": "Flawless demonstration of data engineering principles. Badge certified!"
        }

        self.app.handle_event("earn_badge", guardian_earn_payload)

        # Verify flash message indicates Badge Earned & Awarded
        self.assertIn("Badge Earned!", self.app.last_flash_message)
        self.assertIn("Badge awarded!", self.app.last_flash_message)

        # Verify final submission state is approved
        final_sub = store.get_submission(sub.id)
        self.assertEqual(final_sub.status, "approved")

        # Verify timeline is completed
        tl = store.get_timeline(self.badge.id, self.cosmonaut.id)
        if tl:
            self.assertEqual(tl.status, "completed")
            self.assertTrue(bool(tl.actual_award_date))

        # Verify cadet mapping is concluded/uncoupled for this completed badge
        mapping = next((m for m in store.get_band_mappings() if m.get("badge_name") == self.badge.title), None)
        if mapping:
            self.assertIn(self.cosmonaut.id, mapping.get("completed_cosmonauts", []))

        # -------------------------------------------------------------
        # STEP 4: Cosmonaut View Displays GOLD Badge with Feedback & Marks
        # -------------------------------------------------------------
        self.app.current_user = self.cosmonaut
        self.app.current_view = "c_submission"
        html_cosmo_sub = self.app.render()

        # Collapsed badge card is gold styled and shows completed status
        self.assertIn("Badge Earned", html_cosmo_sub)
        self.assertIn("gold-card", html_cosmo_sub)
        self.assertIn("gold-medal", html_cosmo_sub)

        # Expand badge card to inspect 6 sections
        self.app.handle_event("toggle_cosmonaut_badge_card", self.badge.id)
        html_expanded = self.app.render()

        # Section 2 displays Badge Earned & Certified in Gold with marks & feedback
        self.assertIn("Badge earned &amp; certified", html_expanded)
        self.assertIn("Achievement unlocked", html_expanded)
        self.assertIn("45.0<small> / 50</small>", html_expanded)
        self.assertIn("90.0%", html_expanded)
        for gone in ("evaluated, approved and certified", "Peer reviewer (", "Guardian final (", "Submitted Deliverables", "Awarded "):
            self.assertNotIn(gone, html_expanded, gone)
        self.assertIn("Flawless demonstration of data engineering principles", html_expanded)
        self.assertIn("Outstanding idempotency handling", html_expanded)

        # Verify Cosmonaut Roadmap renders completed badge in GOLD
        self.app.current_view = "c_roadmap"
        html_roadmap = self.app.render()
        self.assertIn("Completed", html_roadmap)
        self.assertIn("#F59E0B", html_roadmap)

        # -------------------------------------------------------------
        # STEP 5: Reviewer Schedule Shows Completed Milestone (Mapping Ended)
        # -------------------------------------------------------------
        self.app.current_user = self.reviewer
        self.app.current_view = "c_badge_reviews"
        html_rev_sched = self.app.render()
        self.assertIn("Completed Reviews", html_rev_sched)
        self.assertIn("Aarav Sharma", html_rev_sched)

    def test_reviewer_project_creation_draft_and_submission_workflow(self):
        """
        Verify Reviewer Create Project (Draft vs Released), Cosmonaut reception of project with
        details/outcomes/deliverables, deliverable submission, reviewer 50-mark grading reflected
        in Cosmonaut marksheet, and Guardian Earn Badge gold award.
        """
        # STEP 1: the cosmonaut asks the mapped reviewer for the project
        self.app.handle_event("select_demo_account", self.cosmonaut.id)
        self.app.current_view = "c_submission"
        self.app.handle_event("toggle_cosmonaut_badge_card", self.badge.id)
        locked_html = self.app.render()
        self.assertIn("Project Allocated", locked_html)                  # nothing to request: the button is simply locked
        self.assertIn("pa-btn is-locked", locked_html)
        self.assertNotIn("Request Project", locked_html)
        self.assertNotIn("Submit Deliverables", locked_html)
        self.app.handle_event("request_project", self.badge.id)         # (the server still accepts an explicit request)

        # STEP 2: the reviewer sees the request, creates the project (heading + content) and sends it
        self.app.handle_event("select_demo_account", self.reviewer.id)
        self.app.current_view = "c_badge_reviews"
        rev_html = self.app.render()
        self.assertIn("Create Project", rev_html)

        self.app.handle_event("open_create_reviewer_project_modal", self.badge.id)
        self.assertEqual(self.app.active_modal, "reviewer_project_creator")
        modal_html = self.app.render_active_modal()
        for expected in ("Heading", "Content", "Send Project to Mapped Cosmonauts", "Requested"):
            self.assertIn(expected, modal_html)
        self.assertNotIn("Expected Project Outcomes", modal_html)
        self.assertNotIn("Mandatory Deliverables", modal_html)

        project = {
            "badge_id": self.badge.id,
            "reviewer_id": self.reviewer.id,
            "title": "High-Throughput Signal Streamer",
            "content": "Case Study\nA signal platform ingests telemetry from many sources.\n\nYour Challenge\nDesign the ingestion engine and explain your choices.",
            "cosmonaut_ids": [self.cosmonaut.id],
            "status": "released",
        }
        self.app.handle_event("send_reviewer_project", dict(project, title=""))      # a project needs a heading
        self.assertIsNone(store.get_project_prompt_for_cadet(self.badge.id, self.cosmonaut.id))
        self.app.handle_event("send_reviewer_project", dict(project, content=""))    # ... and content
        self.assertIsNone(store.get_project_prompt_for_cadet(self.badge.id, self.cosmonaut.id))
        self.app.handle_event("send_reviewer_project", project)
        self.assertIn("sent", self.app.last_flash_message.lower())

        # STEP 3: the cosmonaut receives it; Request Project is replaced by Submit Project Deliverables
        self.assertIsNone(store.get_project_request(self.badge.id, self.cosmonaut.id))   # the request is answered
        self.app.handle_event("select_demo_account", self.cosmonaut.id)
        notifs = store.get_notifications(self.cosmonaut.id)
        self.assertTrue(any("High-Throughput Signal Streamer" in n.title for n in notifs), "Cosmonaut must be notified")
        self.app.current_view = "c_submission"
        self.app.handle_event("toggle_cosmonaut_badge_card", self.badge.id)
        received_html = self.app.render()
        self.assertIn("pa-btn is-ready", received_html)                  # the locked button unlocked
        self.assertNotIn("pa-btn is-locked", received_html)
        self.assertNotIn("Request Project", received_html)

        # STEP 4: "Project Allocated" opens the project PAGE; Submit Deliverables opens the PDF / code / GitHub dialog
        self.app.handle_event("open_allocated_project_page", self.badge.id)
        self.assertEqual(self.app.current_view, "c_project")
        self.app.render()
        project_page_html = self.app.last_rendered_regions["mainContentHtml"]
        self.assertIn("High-Throughput Signal Streamer", project_page_html)
        self.assertIn("Design the ingestion engine", project_page_html)
        self.app.handle_event("open_submission_modal", self.badge.id)
        modal_submit_html = self.app.render_active_modal()
        for field in ("submission-pdf-file", "submission-code-file", "submission-github-url"):
            self.assertIn(field, modal_submit_html)
        submit_payload = {
            "badge_id": self.badge.id,
            "github_url": "https://github.com/starapp/streamer-pipeline",
            "pdf_filename": "streamer_arch.pdf",
            "code_filename": "streamer_pipeline.py",
            "source_code": "import asyncio\nasync def ingest():\n    return 'signals_streamed'"
        }
        self.app.handle_event("submit_project_deliverables", submit_payload)

        # Submission is in pending status
        submissions = store.get_submissions_for_cosmonaut(self.cosmonaut.id)
        sub = next((s for s in submissions if s.badge_id == self.badge.id), None)
        self.assertIsNotNone(sub)

        # STEP 4: Reviewer inspects deliverables and grades
        self.app.handle_event("select_demo_account", self.reviewer.id)
        self.app.handle_event("open_reviewer_assessment_page", sub.id)
        self.assertEqual(self.app.current_view, "c_assessment_detail")

        reviewer_eval = {
            "submission_id": sub.id,
            "bu": 9.5,
            "ar": 9.0,
            "tk": 9.5,
            "pr": 8.5,
            "qa": 8.5,
            "decision": "approve",
            "strengths": "Exceptional backpressure handling with asyncio queue.",
            "improvements": "Consider adding Grafana metrics dashboard.",
            "feedback": "Outstanding execution of streaming telemetry."
        }
        self.app.handle_event("submit_evaluation_marksheet", reviewer_eval)
        self.assertEqual(store.get_submission(sub.id).status, "reviewer_assessed")

        # STEP 5: Cosmonaut views results in assessment marksheet (c_results)
        self.app.handle_event("select_demo_account", self.cosmonaut.id)
        self.app.current_view = "c_results"
        cosmo_results_html = self.app.render()
        self.assertIn("Reviewer", cosmo_results_html)
        self.assertIn("45.0", cosmo_results_html)
        self.assertIn("Exceptional backpressure handling", cosmo_results_html)

        # STEP 6: Guardian reviews and awards badge ("Earn the Badge")
        self.app.handle_event("select_demo_account", self.guardian.id)
        self.app.current_view = "g_reviews"
        self.app.handle_event("open_submission_review_page", sub.id)
        guardian_earn = {
            "submission_id": sub.id,
            "bu": 9.5,
            "ar": 9.0,
            "tk": 9.5,
            "pr": 8.5,
            "qa": 8.5,
            "decision": "approve",
            "strengths": "Confirmed top-tier implementation.",
            "improvements": "Maintain high quality in future bands.",
            "feedback": "Officially certified. Earned!"
        }
        self.app.handle_event("earn_badge", guardian_earn)

        # Final check: Badge earned & gold reflection
        self.app.handle_event("select_demo_account", self.cosmonaut.id)
        self.app.current_view = "c_submission"
        final_cosmo_html = self.app.render()
        self.assertIn("Badge Earned", final_cosmo_html)
        self.assertIn("gold-card", final_cosmo_html)



if __name__ == "__main__":
    unittest.main()
