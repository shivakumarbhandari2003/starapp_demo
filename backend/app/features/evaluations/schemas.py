"""
Evaluations and marksheets schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class SubmitEvaluationRequest(BaseModel):
    submission_id: str
    decision: str  # 'approved' or 'resubmission_requested'
    business_understanding: float = Field(..., ge=0.0, le=10.0)
    architecture_report: float = Field(..., ge=0.0, le=10.0)
    technical_knowledge: float = Field(..., ge=0.0, le=10.0)
    presentation: float = Field(..., ge=0.0, le=10.0)
    qa: float = Field(..., ge=0.0, le=10.0)
    strength_areas: Optional[str] = ""
    improvement_areas: Optional[str] = ""
    overall_feedback: Optional[str] = ""
