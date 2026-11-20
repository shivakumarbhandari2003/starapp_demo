"""
Review schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class DispatchReviewRequest(BaseModel):
    badge_id: str
    reviewer_id: str
    notes: Optional[str] = ""


class ReviewDecisionRequest(BaseModel):
    decision: str  # 'approved' or 'returned'
    notes: Optional[str] = ""
    updated_title: Optional[str] = None
    updated_description: Optional[str] = None
    updated_outcomes: Optional[List[str]] = None
    updated_topics: Optional[List[Dict[str, Any]]] = None
