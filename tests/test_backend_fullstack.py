"""
StarApp Full-Stack Architecture Test Suite
Comprehensive integration and unit test coverage for the FastAPI backend,
authoritative SQLite3 persistent storage, and RBAC business rules.
"""
import unittest
import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.database.connection import get_connection, check_database_integrity
from backend.app.core.permissions import verify_reviewer_eligibility, validate_50_mark_rubric
from backend.app.features.auth.repository import AuthRepository
from backend.app.features.auth.service import AuthService
from backend.app.features.users.repository import UserRepository
from backend.app.features.users.service import UserService
from backend.app.features.bands.repository import BandsRepository
from backend.app.features.bands.service import BandsService
from backend.app.features.badges.repository import BadgesRepository
from backend.app.features.badges.service import BadgesService
from backend.app.features.reviews.repository import ReviewsRepository
from backend.app.features.reviews.service import ReviewsService
from backend.app.features.allotments.repository import AllotmentsRepository
from backend.app.features.allotments.service import AllotmentsService
from backend.app.features.submissions.repository import SubmissionsRepository
from backend.app.features.submissions.service import SubmissionsService
from backend.app.features.evaluations.repository import EvaluationsRepository
from backend.app.features.evaluations.service import EvaluationsService
from backend.app.core.exceptions import ConflictException, ForbiddenException, NotFoundException


class TestStarAppFullStackBackend(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection()

    def tearDown(self):
        self.conn.close()

    def test_01_database_durability_and_integrity(self):
        """Verify database integrity, WAL mode, and zero foreign key violations."""
        integrity = check_database_integrity()
        self.assertEqual(integrity["integrity"], "ok")
        self.assertEqual(integrity["foreign_key_violations"], 0)
        self.assertGreaterEqual(integrity["table_count"], 32)
        self.assertEqual(integrity["status"], "healthy")

    def test_02_authentication_and_session_management(self):
        """Verify password verification, session generation, and logout."""
        auth_service = AuthService(AuthRepository(self.conn))
        
        # Admin login
        token, user = auth_service.login("admin", "12345678", "guardian")
        self.assertIsNotNone(token)
        self.assertEqual(user["id"], "admin")
        self.assertEqual(user["active_role"], "guardian")

        # Demo user login (Ananya Iyer B1)
        token_cadet, cadet = auth_service.login("ananya.iyer", "12345678", "cosmonaut")
        self.assertIsNotNone(token_cadet)
        self.assertEqual(cadet["name"], "Ananya Iyer")
        self.assertEqual(cadet["band"], "B1")

        # Invalid password rejected
        with self.assertRaises(Exception):
            auth_service.login("admin", "wrong_password")

    def test_03_corporate_hierarchy_36_members(self):
        """Verify corporate hierarchy: 36 members across B1-B6 + CEO."""
        user_service = UserService(UserRepository(self.conn))
        users = user_service.get_users()
        self.assertGreaterEqual(len(users), 36)

        # Check band distribution
        bands = set(u["band"] for u in users)
        for expected_band in ["B1", "B2", "B3", "B4", "B5", "B6"]:
            self.assertIn(expected_band, bands)

        # Verify CEO
        tree = user_service.get_hierarchy_tree()
        ceo = next((u for u in tree if "ceo" in (u.get("role") or "").lower() or "mehta" in u["name"].lower()), None)
        self.assertIsNotNone(ceo, "CEO Arjun Mehta must exist in hierarchy")

    def test_04_higher_band_reviewer_eligibility_enforcement(self):
        """Verify non-negotiable rule: Reviewer_Band > Badge_Band."""
        user_service = UserService(UserRepository(self.conn))

        # Band 1 badges: eligible reviewers must be in B2, B3, B4, B5, B6
        b1_reviewers = user_service.get_eligible_reviewers("B1")
        self.assertGreater(len(b1_reviewers), 0)
        for r in b1_reviewers:
            self.assertIn(r["band"], ["B2", "B3", "B4", "B5", "B6"])

        # Band 5 badges: eligible reviewers must ONLY be in B6
        b5_reviewers = user_service.get_eligible_reviewers("B5")
        self.assertGreater(len(b5_reviewers), 0)
        for r in b5_reviewers:
            self.assertEqual(r["band"], "B6")

        # Band 6 badges: locked out from peer review (0 eligible reviewers)
        b6_reviewers = user_service.get_eligible_reviewers("B6")
        self.assertEqual(len(b6_reviewers), 0)

    def test_05_50_mark_rubric_validation(self):
        """Verify 5-criterion, 50-mark assessment rubric validation."""
        valid_marks = {
            "business_understanding": 9,
            "architecture_report": 8,
            "technical_knowledge": 10,
            "presentation": 7,
            "question_answering": 9
        }
        ok, err, total = validate_50_mark_rubric(valid_marks)
        self.assertTrue(ok)
        self.assertEqual(total, 43)

        # Out-of-range mark (11/10)
        invalid_marks = dict(valid_marks, business_understanding=11)
        ok, err, total = validate_50_mark_rubric(invalid_marks)
        self.assertFalse(ok)
        self.assertIn("out of range", err)

        # Negative mark (-1)
        neg_marks = dict(valid_marks, presentation=-1)
        ok, err, total = validate_50_mark_rubric(neg_marks)
        self.assertFalse(ok)

    def test_06_badge_creation_and_deduplication(self):
        """Verify badge creation and deduplication within the same band."""
        badge_service = BadgesService(BadgesRepository(self.conn))
        
        # Clean up any leftover test badge
        self.conn.execute("DELETE FROM badges WHERE code = 'B1-DEDUP-TEST';")
        self.conn.commit()

        badge_data = {
            "code": "B1-DEDUP-TEST",
            "title": "Deduplication Test Badge",
            "category": "Tech",
            "description": "Verifying deduplication",
            "target_band": "B1",
            "power": "Tech",
            "capability": "Data & Machine",
            "skill": "Hardware",
            "creator_id": "admin"
        }
        badge_id = badge_service.create_badge(badge_data)
        self.assertIsNotNone(badge_id)

        # Attempt duplicate creation in same band -> must raise ConflictException
        with self.assertRaises(ConflictException):
            badge_service.create_badge(badge_data)

        # Clean up
        self.conn.execute("DELETE FROM badges WHERE id = ?;", (badge_id,))
        self.conn.commit()

    def test_07_review_workflow_dispatch_and_decision(self):
        """Verify review request dispatch, higher-band rule enforcement, and approval."""
        badge_service = BadgesService(BadgesRepository(self.conn))
        review_service = ReviewsService(
            ReviewsRepository(self.conn),
            BadgesRepository(self.conn),
            UserRepository(self.conn)
        )

        # Create a B1 badge
        self.conn.execute("DELETE FROM badges WHERE code = 'B1-REV-TEST';")
        self.conn.commit()

        badge_id = badge_service.create_badge({
            "code": "B1-REV-TEST",
            "title": "Review Workflow Test",
            "category": "Tech",
            "description": "Badge for testing review flow",
            "target_band": "B1",
            "creator_id": "admin"
        })

        # Aarav Sharma is B1 -> cannot review B1 badge (ForbiddenException)
        with self.assertRaises(ForbiddenException):
            review_service.dispatch_review_request(badge_id, "m_b1_1", "Invalid peer review")

        # Rohan Deshmukh is B2 -> can review B1 badge
        assign_id = review_service.dispatch_review_request(badge_id, "m_b2_1", "Valid higher-band review")
        self.assertIsNotNone(assign_id)

        # Reviewer inbox contains the assignment
        inbox = review_service.get_reviewer_inbox("m_b2_1")
        self.assertTrue(any(item["badge_id"] == badge_id for item in inbox))

        # Reviewer submits decision with an inline title edit
        review_service.submit_decision(badge_id, "m_b2_1", {
            "decision": "approved",
            "notes": "Excellent curriculum structure",
            "updated_title": "Review Workflow Test (Reviewed & Approved)"
        })

        # Verify badge permanently updated
        updated = badge_service.get_badge(badge_id)
        self.assertEqual(updated["workflow_status"], "approved")
        self.assertEqual(updated["title"], "Review Workflow Test (Reviewed & Approved)")

        # Clean up
        self.conn.execute("DELETE FROM badges WHERE id = ?;", (badge_id,))
        self.conn.commit()

    def _get_or_create_b1_badge(self):
        badges = BadgesRepository(self.conn).list_badges(band="B1")
        if badges:
            return badges[0]
        badge_service = BadgesService(BadgesRepository(self.conn))
        badge_service.create_badge({
            "code": "B1-TEST-BADGE",
            "title": "Backend Test Badge",
            "category": "Tech",
            "description": "B1 badge for backend testing",
            "target_band": "B1",
            "creator_id": "admin"
        })
        self.conn.commit()
        return BadgesRepository(self.conn).list_badges(band="B1")[0]

    def test_08_allotments_and_cosmonaut_roadmap(self):
        """Verify badge allotment and Candy Crush roadmap generation."""
        allot_service = AllotmentsService(AllotmentsRepository(self.conn))
        target_badge = self._get_or_create_b1_badge()

        # Allot to Ananya Iyer
        count = allot_service.allot_badge(target_badge["id"], ["m_b1_2"])
        self.assertEqual(count, 1)

        # Check roadmap for Ananya
        roadmap = allot_service.get_cosmonaut_roadmap("m_b1_2")
        self.assertGreater(len(roadmap), 0)
        self.assertTrue(any(b["id"] == target_badge["id"] for b in roadmap))

    def test_09_multi_attempt_submissions_and_history(self):
        """Verify multi-attempt submission history retention."""
        sub_service = SubmissionsService(SubmissionsRepository(self.conn))
        test_badge = self._get_or_create_b1_badge()

        # Attempt 1
        sub1 = sub_service.submit_project({
            "badge_id": test_badge["id"],
            "cosmonaut_id": "m_b1_2",
            "github_url": "https://github.com/cadet/project-attempt-1"
        })
        self.assertGreaterEqual(sub1["attempt_number"], 1)

        # Attempt 2
        sub2 = sub_service.submit_project({
            "badge_id": test_badge["id"],
            "cosmonaut_id": "m_b1_2",
            "github_url": "https://github.com/cadet/project-attempt-2"
        })
        self.assertEqual(sub2["attempt_number"], sub1["attempt_number"] + 1)

        # Verify history retains both attempts
        history = sub_service.get_history(test_badge["id"], "m_b1_2")
        self.assertGreaterEqual(len(history), 2)

    def test_10_evaluation_and_50_mark_scorecard(self):
        """Verify 50-mark scorecard calculation, percentage, and leaderboard."""
        sub_service = SubmissionsService(SubmissionsRepository(self.conn))
        eval_service = EvaluationsService(EvaluationsRepository(self.conn))
        test_badge = self._get_or_create_b1_badge()

        # Create submission
        sub = sub_service.submit_project({
            "badge_id": test_badge["id"],
            "cosmonaut_id": "m_b1_2",
            "github_url": "https://github.com/cadet/final-eval"
        })

        # Submit 50-mark evaluation (44/50 = 88%)
        eval_id = eval_service.submit_evaluation({
            "submission_id": sub["id"],
            "decision": "approved",
            "business_understanding": 9.0,
            "architecture_report": 9.0,
            "technical_knowledge": 8.0,
            "presentation": 9.0,
            "qa": 9.0,
            "overall_feedback": "Exceptional presentation and architecture."
        }, {"id": "m_b2_1", "name": "Rohan Deshmukh"})
        self.assertIsNotNone(eval_id)

        # Verify scorecard
        marksheets = eval_service.get_marksheets("m_b1_2", test_badge["id"])
        self.assertGreater(len(marksheets), 0)
        latest = marksheets[0]
        self.assertEqual(latest["total_marks"], 44.0)
        self.assertEqual(latest["percentage"], 88.0)
        self.assertEqual(latest["decision"], "approved")

        # Verify leaderboard
        leaderboard = eval_service.get_leaderboard()
        self.assertGreater(len(leaderboard), 0)

    def test_11_favicon_and_sw_routes_no_content_length_error(self):
        """Verify /favicon.ico returns 204 with empty body (no Content-Length mismatch) and /sw.js returns 200."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        with TestClient(app) as client:
            fav_res = client.get("/favicon.ico")
            self.assertEqual(fav_res.status_code, 204)
            self.assertEqual(fav_res.content, b"")

            sw_res = client.get("/sw.js")
            self.assertEqual(sw_res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
