import unittest, sys, os
sys.path.insert(0, os.path.abspath("."))
from starapp.app import store, StarAppController

class TestGuardianReviewFlow(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.app = StarAppController()
        self.app.initialize()

    def test_multi_deliverable_submission_and_guardian_review(self):
        # 1. Cosmonaut submits deliverable with badge name, pdf file, code file, and github link
        self.app.current_user = store.users.get("cosmo_1")
        sub_payload = {
            "badge_id": "badge_ing_104",
            "pdf_name": "Astraea_Kafka_Architecture_Spec.pdf",
            "pdf_payload": "data/Chemistry%20Syllabus.pdf",
            "code_name": "custom_kafka_idempotent_consumer.py",
            "code_payload": "def my_consumer():\n    print('Idempotent Kafka Consumer')\n",
            "github_url": "https://github.com/starapp-cosmonauts/custom-ingestion"
        }
        self.app.handle_event("submit_project_deliverable", sub_payload)
        subs = store.get_submissions_for_cosmonaut("cosmo_1", "badge_ing_104")
        latest_sub = subs[-1]
        self.assertEqual(latest_sub.pdf_name, "Astraea_Kafka_Architecture_Spec.pdf")
        self.assertEqual(latest_sub.code_name, "custom_kafka_idempotent_consumer.py")
        self.assertEqual(latest_sub.github_url, "https://github.com/starapp-cosmonauts/custom-ingestion")

        # 2. Guardian checks project reviews queue (rendered as modern containers)
        self.app.current_user = store.users.get("guardian_1")
        self.app.current_view = "g_reviews"
        html_queue = self.app.render()

        self.assertIn("Astraea Nova", html_queue)
        self.assertIn("ING-104", html_queue)
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
        self.assertIn("Sum of Rubric Marks:", html_detail)
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

        # Verify assessment was created
        asm = store.get_assessment_for_submission(latest_sub.id)
        self.assertIsNotNone(asm)
        self.assertEqual(asm.total_marks, 47.5)
        self.assertEqual(asm.decision, "approve")

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
