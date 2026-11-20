"""
Users service layer.
"""
from typing import List, Dict, Any, Optional
from backend.app.core.permissions import BAND_HIERARCHY, verify_reviewer_eligibility
from backend.app.core.exceptions import NotFoundException
from backend.app.features.users.repository import UserRepository


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_users(self, band: Optional[str] = None, track: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.list_users(band, track)

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(f"User '{user_id}' not found.")
        return user

    def get_eligible_reviewers(self, badge_band: str) -> List[Dict[str, Any]]:
        band_val = BAND_HIERARCHY.get(badge_band.upper(), 0)
        return self.repo.get_eligible_reviewers(band_val)

    def get_hierarchy_tree(self) -> List[Dict[str, Any]]:
        return self.repo.get_hierarchy_tree()
