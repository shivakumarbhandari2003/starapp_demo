"""
Evaluations service layer.
"""
from typing import List, Dict, Any, Optional
from backend.app.core.exceptions import NotFoundException, StarAppException, ForbiddenException
from backend.app.core.permissions import validate_50_mark_rubric, verify_reviewer_eligibility
from backend.app.features.evaluations.repository import EvaluationsRepository


class EvaluationsService:
    def __init__(self, repo: EvaluationsRepository):
        self.repo = repo

    def submit_evaluation(self, req_data: Dict[str, Any], reviewer: Dict[str, Any]) -> str:
        submission = self.repo.get_submission_by_id(req_data["submission_id"])
        if not submission:
            raise NotFoundException(f"Submission '{req_data['submission_id']}' not found.")

        # Determine reviewer details from DB if missing in reviewer dict
        cur = self.repo.conn.cursor()
        cur.execute("SELECT role, band FROM users WHERE id = ?;", (reviewer["id"],))
        u_row = cur.fetchone()
        u_role = reviewer.get("role") or (u_row["role"] if u_row else "reviewer")
        u_band = reviewer.get("band") or (u_row["band"] if u_row else "B2")

        is_guardian = (u_role in ("guardian", "admin") or "guardian" in reviewer.get("roles", []))
        if not is_guardian:
            # 1. Higher-band reviewer eligibility check
            badge = self.repo.get_badge_by_id(submission["badge_id"])
            if badge:
                badge_band = badge.get("target_band", "B1")
                if not verify_reviewer_eligibility(u_band, badge_band):
                    raise ForbiddenException(
                        f"Reviewer band ({u_band}) must be strictly higher than badge band ({badge_band})."
                    )

            # 2. Assignment verification: if assignments exist for this submission, verify reviewer is assigned
            if self.repo.has_assignments_for_submission(submission):
                if not self.repo.is_reviewer_assigned_to_submission(reviewer["id"], submission):
                    raise ForbiddenException(
                        f"Reviewer '{reviewer.get('name', reviewer['id'])}' is not authorized or assigned to evaluate this submission."
                    )

        # Prepare evaluation payload
        eval_payload = dict(req_data)
        eval_payload["attempt_number"] = submission["attempt_number"]
        eval_payload["badge_id"] = submission["badge_id"]
        eval_payload["cosmonaut_id"] = submission["cosmonaut_id"]
        eval_payload["reviewer_id"] = reviewer["id"]
        eval_payload["reviewer_name"] = reviewer.get("name", "Institutional Reviewer")

        return self.repo.record_evaluation(eval_payload)

    def get_marksheets(self, cosmonaut_id: str, badge_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.get_marksheets_for_cosmonaut(cosmonaut_id, badge_id)

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        return self.repo.get_leaderboard()
