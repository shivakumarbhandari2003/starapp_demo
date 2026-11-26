import unittest, sys, os
sys.path.insert(0, os.path.abspath("."))
from starapp.app import store, StarAppController

class TestGuardianReviewFlow(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.app = StarAppController()
        self.app.initialize()

    def test_multi_deliverable_submission_and_guardian_review(self):
        # 0. The Guardian allots + publishes the milestone to the cadet (submissions are only accepted for
        #    badges that are assigned to the cadet and published).
        badge = store.get_badge("b1_int_01")
        badge.is_published = True
        if "cosmo_1" not in badge.assigned_cosmonaut_ids:
            badge.assigned_cosmonaut_ids.append("cosmo_1")
        store.save_badge(badge)

        # 1. Cosmonaut submits deliverable with badge name, pdf file, code file, and github link
        self.app.current_user = store.users.get("cosmo_1")
        sub_payload = {
            "badge_id": "b1_int_01",
            "pdf_name": "Astraea_Kafka_Architecture_Spec.pdf",
            "pdf_payload": "data/Chemistry%20Syllabus.pdf",
            "code_name": "custom_kafka_idempotent_consumer.py",
            "code_payload": "def my_consumer():\n    print('Idempotent Kafka Consumer')\n",
            "github_url": "https://github.com/starapp-cosmonauts/custom-ingestion"
        }
        self.app.handle_event("submit_project_deliverable", sub_payload)
        subs = store.get_submissions_for_cosmonaut("cosmo_1", "b1_int_01")
        latest_sub = subs[-1]
        self.assertEqual(latest_sub.pdf_name, "Astraea_Kafka_Architecture_Spec.pdf")
        self.assertEqual(latest_sub.code_name, "custom_kafka_idempotent_consumer.py")
        self.assertEqual(latest_sub.github_url, "https://github.com/starapp-cosmonauts/custom-ingestion")

        # 2. Guardian opens Assessment Dashboard -> Level 1 Badge Cards with Power & Capability filters
        self.app.current_user = store.users.get("guardian_1")
        self.app.current_view = "g_reviews"
        html_l1 = self.app.render()

        self.assertNotIn("Live tracking of cadet project submissions", html_l1)
        self.assertIn('id="asm-power-filter"', html_l1)
        self.assertIn('id="asm-capability-filter"', html_l1)
        self.assertIn("B1-INT-01", html_l1)
        self.assertIn("open_assessment_badge", html_l1)

        # Verify Power & Capability filters isolate badges cleanly
        self.app.handle_event("filter_assessment_power", "Domain")
        html_dom = self.app.render()
        self.assertNotIn("B1-INT-01", html_dom)
        self.app.handle_event("filter_assessment_power", "all")

        # Level 2: Open Badge Card -> Mapped Reviewers & Cosmonauts (Hierarchical Tree)
        self.app.handle_event("open_assessment_badge", "b1_int_01")
        html_l2 = self.app.render()
        self.assertIn("Mapped Reviewer", html_l2)
        self.assertIn("asm-tree-reviewer-branch", html_l2)
        self.assertIn("asm-tree-cosmo-list", html_l2)
        self.assertIn("asm-cosmo-chip-row", html_l2)
        self.assertIn("Aarav Sharma", html_l2)
        self.assertIn("open_assessment_cosmonaut", html_l2)

        # Level 3: Click Cosmonaut -> Deliverables & Results
        self.app.handle_event("open_assessment_cosmonaut", {"badge_id": "b1_int_01", "cosmonaut_id": "cosmo_1"})
        html_queue = self.app.render()
        self.assertIn("lg-attempt-card", html_queue)
        self.assertIn("Aarav Sharma", html_queue)
        self.assertIn("B1-INT-01", html_queue)
        self.assertIn("Uploaded Deliverables", html_queue)
        self.assertIn("Astraea_Kafka_Architecture_Spec.pdf", html_queue)
        self.assertIn("custom_kafka_idempotent_consumer.py", html_queue)
        self.assertIn("open_submission_review_page", html_queue)

        # 3. Guardian clicks container -> redirected to dedicated review page
        self.app.handle_event("open_submission_review_page", latest_sub.id)
        self.assertEqual(self.app.current_view, "g_review_detail")
        html_detail = self.app.render()

        self.assertIn("Back to Project Reviews", html_detail)
        self.assertIn("deliverable-type-select", html_detail)
        self.assertIn("asm-deliverable-select-wrap", html_detail)
        for emoji_char in ("📄", "💻", "🔗"):
            self.assertNotIn(emoji_char, html_detail)
        self.assertIn("Sum of Rubric Marks:", html_detail)
        self.assertIn("Max 10", html_detail)
        for removed_txt in (
            "Authorized Reviewer Score",
            "Domain scope &amp; formulation (Max: 10)",
            "PDF technical spec &amp; design (Max: 10)",
            "Source code execution &amp; depth (Max: 10)",
            "Code clean layout &amp; modularity (Max: 10)",
            "Edge cases &amp; justification (Max: 10)",
        ):
            self.assertNotIn(removed_txt, html_detail)
        self.assertIn("View PDF Document", html_detail)
        self.assertIn("View Source Code", html_detail)
        self.assertIn("View GitHub Repo", html_detail)
        self.assertIn("iframe", html_detail)

        # 4. Guardian toggles to Code Viewer
        self.app.handle_event("change_viewer_tab", "code")
        html_code = self.app.render()
        self.assertIn("custom_kafka_idempotent_consumer.py", html_code)
        self.assertIn("my_consumer", html_code)

        # 5. Guardian toggles to GitHub Viewer
        self.app.handle_event("change_viewer_tab", "github")
        html_gh = self.app.render()
        self.assertIn("custom-ingestion", html_gh)

        # 6. Guardian submits 50-mark evaluation marksheet on g_review_detail
        self.app.handle_event("open_submission_review_page", latest_sub.id)
        eval_payload = {
            "submission_id": latest_sub.id,
            "bu": 9.5,
            "ar": 9.5,
            "tk": 10.0,
            "pr": 9.0,
            "qa": 9.5,
            "strengths": "Flawless Kafka idempotency and high-throughput consumer.",
            "improvements": "Ready for production deployment.",
            "feedback": "Outstanding engineering achievement. Badge awarded.",
            "decision": "approve"
        }
        self.app.handle_event("submit_evaluation_marksheet", eval_payload)
        self.assertEqual(self.app.current_view, "g_reviews")

        # Verify submission updated to approved
        updated_sub = store.get_submission(latest_sub.id)
        self.assertEqual(updated_sub.status, "approved")

        # Verify assessment was created & Level 3 shows Title Case "Approved"
        asm = store.get_assessment_for_submission(latest_sub.id)
        self.assertIsNotNone(asm)
        self.assertEqual(asm.total_marks, 47.5)
        self.assertEqual(asm.decision, "approve")

        self.app.handle_event("open_assessment_cosmonaut", {"badge_id": "b1_int_01", "cosmonaut_id": "cosmo_1"})
        html_l3_post = self.app.render()
        self.assertIn("lg-eval-verdict\">Approved</span>", html_l3_post)

        # 7. Cosmonaut opens "Assessment Marksheet" section (c_results)
        self.app.current_user = store.users.get("cosmo_1")
        self.app.current_view = "c_results"
        html_results = self.app.render()

        self.assertIn("Official Assessment Marksheets", html_results)
        self.assertIn("47.5", html_results)
        self.assertIn("Flawless Kafka idempotency", html_results)
        self.assertIn("Outstanding engineering achievement", html_results)

if __name__ == "__main__":
    unittest.main()
