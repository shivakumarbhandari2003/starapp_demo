"""
Users and employees schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class UserSummary(BaseModel):
    id: str
    name: str
    email: str
    band: str
    role: str
    learning_track: str
    track_code: str
    reporting_manager_name: Optional[str] = None
    reporting_manager_band: Optional[str] = None
    primary_role: str
    avatar: Optional[str] = None


class EligibleReviewerResponse(BaseModel):
    badge_band: str
    eligible_reviewers: List[UserSummary]
