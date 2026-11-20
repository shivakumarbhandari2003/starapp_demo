"""
Badges service layer.
"""
from typing import Optional, List, Dict, Any
from backend.app.core.exceptions import ConflictException, NotFoundException, StarAppException
from backend.app.features.badges.repository import BadgesRepository


class BadgesService:
    def __init__(self, repo: BadgesRepository):
        self.repo = repo

    def get_badges(self, band: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.list_badges(band, status)

    def get_badge(self, badge_id: str) -> Dict[str, Any]:
        badge = self.repo.get_by_id(badge_id)
        if not badge:
            raise NotFoundException(f"Badge '{badge_id}' not found.")
        return badge

    def create_badge(self, data: Dict[str, Any]) -> str:
        # Enforce deduplication in same band
        if self.repo.check_duplicate(data["code"], data["title"], data["target_band"]):
            raise ConflictException(f"A badge with code '{data['code']}' or title '{data['title']}' already exists in band '{data['target_band']}'.")
        return self.repo.create_badge(data)

    def update_badge(self, badge_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        badge = self.repo.get_by_id(badge_id)
        if not badge:
            raise NotFoundException(f"Badge '{badge_id}' not found.")
        self.repo.update_badge(badge_id, updates)
        return self.repo.get_by_id(badge_id)
