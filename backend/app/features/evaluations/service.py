"""
Evaluations service layer.
"""
from typing import List, Dict, Any, Optional
from backend.app.core.exceptions import NotFoundException, StarAppException
from backend.app.core.permissions import validate_50_mark_rubric
from backend.app.features.evaluations.repository import EvaluationsRepository


class EvaluationsService:
    def __init__(self, repo: EvaluationsRepository):
        self.repo = repo

    def submit_evaluation(self, req_data: Dict[str, Any], reviewer: Dict[str, Any]) -> str:
        submission = self.repo.get_submission_by_id(req_data["submission_id"])
        if not submission:
            raise NotFoundException(f"Submission '{req_data['submission_id']}' not found.")

        # Prepare evaluation payload
        eval_payload = dict(req_data)
        eval_payload["attempt_number"] = submission["attempt_number"]
        eval_payload["badge_id"] = submission["badge_id"]
        eval_payload["cosmonaut_id"] = submission["cosmonaut_id"]
        eval_payload["reviewer_id"] = reviewer["id"]
        eval_payload["reviewer_name"] = reviewer["name"]

        return self.repo.record_evaluation(eval_payload)

    def get_marksheets(self, cosmonaut_id: str, badge_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.get_marksheets_for_cosmonaut(cosmonaut_id, badge_id)

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        return self.repo.get_leaderboard()
