"""
Submissions schemas.
"""
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any


class CreateSubmissionRequest(BaseModel):
    badge_id: str
    submission_type: Optional[str] = "github"
    github_url: Optional[str] = ""
    file_name: Optional[str] = ""
    payload: Optional[str] = ""
    pdf_name: Optional[str] = ""
    pdf_payload: Optional[str] = ""
    code_name: Optional[str] = ""
    code_payload: Optional[str] = ""
