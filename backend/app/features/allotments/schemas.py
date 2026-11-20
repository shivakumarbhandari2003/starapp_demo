"""
Allotments and roadmap schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AllotBadgeRequest(BaseModel):
    badge_id: str
    cosmonaut_ids: List[str]
    timeline: Optional[Dict[str, str]] = None


class ExtensionRequestSchema(BaseModel):
    badge_id: str
    proposed_deadline: str
    reason: str


class ExtensionDecisionSchema(BaseModel):
    status: str  # 'approved' or 'rejected'
    response_notes: Optional[str] = ""
