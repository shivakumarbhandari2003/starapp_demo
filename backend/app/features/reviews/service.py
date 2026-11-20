"""
Reviews service layer.
Enforces the authoritative higher-band reviewer eligibility rule.
"""
from typing import List, Dict, Any
from backend.app.core.permissions import verify_reviewer_eligibility
from backend.app.core.exceptions import ForbiddenException, NotFoundException, ConflictException
from backend.app.features.reviews.repository import ReviewsRepository
from backend.app.features.badges.repository import BadgesRepository
from backend.app.features.users.repository import UserRepository


class ReviewsService:
    def __init__(self, repo: ReviewsRepository, badge_repo: BadgesRepository, user_repo: UserRepository):
        self.repo = repo
        self.badge_repo = badge_repo
        self.user_repo = user_repo

    def dispatch_review_request(self, badge_id: str, reviewer_id: str, notes: str = "") -> str:
        badge = self.badge_repo.get_by_id(badge_id)
        if not badge:
            raise NotFoundException(f"Badge '{badge_id}' not found.")

        reviewer = self.user_repo.get_by_id(reviewer_id)
        if not reviewer:
            raise NotFoundException(f"Reviewer '{reviewer_id}' not found.")

        # Enforce server-side rule: Reviewer_Band > Badge_Band
        reviewer_band = reviewer.get("band", "B1")
        badge_band = badge.get("target_band", "B1")
        if not verify_reviewer_eligibility(reviewer_band, badge_band):
            raise ForbiddenException(
                f"Reviewer eligibility violation: Reviewer {reviewer['name']} is in band {reviewer_band}, "
                f"which is not higher than badge band {badge_band}. (Rule: Reviewer_Band > Badge_Band)"
            )

        # Use canonical primary key IDs for foreign key integrity
        return self.repo.create_assignment(badge["id"], reviewer["id"], notes)

    def get_reviewer_inbox(self, reviewer_id: str) -> List[Dict[str, Any]]:
        return self.repo.get_reviewer_inbox(reviewer_id)

    def submit_decision(self, badge_id: str, reviewer_id: str, req_data: Dict[str, Any]) -> bool:
        decision = req_data.get("decision", "approved")
        notes = req_data.get("notes", "")

        # If reviewer made edits, save them directly to the badge
        updates = {}
        if req_data.get("updated_title"):
            updates["title"] = req_data["updated_title"]
        if req_data.get("updated_description"):
            updates["description"] = req_data["updated_description"]
        if req_data.get("updated_outcomes"):
            updates["learning_outcomes"] = req_data["updated_outcomes"]
        if req_data.get("updated_topics"):
            updates["learning_topics"] = req_data["updated_topics"]
            
        if updates:
            self.badge_repo.update_badge(badge_id, updates)

        return self.repo.record_decision(badge_id, reviewer_id, decision, notes)

    def get_guardian_overview(self) -> List[Dict[str, Any]]:
        return self.repo.get_review_requests_for_guardian()
