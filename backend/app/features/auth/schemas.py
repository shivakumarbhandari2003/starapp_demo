"""
Authentication schemas.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any


class LoginRequest(BaseModel):
    username_or_email: str
    password: str
    selected_role: Optional[str] = None


class SwitchRoleRequest(BaseModel):
    role: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    name: str
    age: int
    role: str
    learning_track: str
    track_code: str
    band: str
    reporting_manager_id: Optional[str] = None
    reporting_manager_name: Optional[str] = None
    reporting_manager_band: Optional[str] = None
    primary_role: str
    active_role: str
    avatar: Optional[str] = None
    status: str


class LoginResponse(BaseModel):
    success: bool
    token: str
    user: Dict[str, Any]
