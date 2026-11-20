"""
Allotments and roadmap service layer.
"""
from typing import List, Dict, Any, Optional
from backend.app.core.exceptions import NotFoundException
from backend.app.features.allotments.repository import AllotmentsRepository


class AllotmentsService:
    def __init__(self, repo: AllotmentsRepository):
        self.repo = repo

    def allot_badge(self, badge_id: str, cosmonaut_ids: List[str], timeline: Dict[str, str] = None) -> int:
        return self.repo.allot_badge_to_cosmonauts(badge_id, cosmonaut_ids, timeline)

    def get_cosmonaut_roadmap(self, cosmonaut_id: str) -> List[Dict[str, Any]]:
        return self.repo.get_cosmonaut_roadmap(cosmonaut_id)

    def get_guardian_allotments(self) -> List[Dict[str, Any]]:
        return self.repo.get_allotments_for_guardian()

    def request_extension(self, badge_id: str, cosmonaut_id: str, proposed_deadline: str, reason: str) -> str:
        return self.repo.create_extension_request(badge_id, cosmonaut_id, proposed_deadline, reason)

    def list_extensions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.list_extensions(status)

    def decide_extension(self, extension_id: str, status: str, notes: str) -> bool:
        return self.repo.decide_extension(extension_id, status, notes)
