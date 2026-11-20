"""
Bands and taxonomy schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AddCapabilityRequest(BaseModel):
    name: str


class AddSkillRequest(BaseModel):
    name: str
    capability_name: Optional[str] = ""
