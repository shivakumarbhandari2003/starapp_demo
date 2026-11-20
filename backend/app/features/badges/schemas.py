"""
Badge schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class CreateBadgeRequest(BaseModel):
    code: str
    title: str
    category: str
    description: str
    target_band: str
    power: Optional[str] = "Tech"
    capability: Optional[str] = "Data & Machine"
    skill: Optional[str] = "Hardware"
    learning_outcomes: List[str] = []
    learning_topics: List[Dict[str, Any]] = []
    project_requirements: Optional[str] = ""
    prompt_json: Optional[str] = ""
    assigned_reviewer_id: Optional[str] = None


class UpdateBadgeRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    learning_outcomes: Optional[List[str]] = None
    learning_topics: Optional[List[Dict[str, Any]]] = None
    project_requirements: Optional[str] = None
    workflow_status: Optional[str] = None
    is_published: Optional[bool] = None
