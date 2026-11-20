"""
Submissions service layer.
"""
from typing import List, Dict, Any
from backend.app.features.submissions.repository import SubmissionsRepository


class SubmissionsService:
    def __init__(self, repo: SubmissionsRepository):
        self.repo = repo

    def submit_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.repo.create_submission(data)

    def get_history(self, badge_id: str, cosmonaut_id: str) -> List[Dict[str, Any]]:
        return self.repo.get_submission_history(badge_id, cosmonaut_id)

    def get_pending(self) -> List[Dict[str, Any]]:
        return self.repo.get_pending_submissions()
