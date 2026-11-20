"""
Authentication service layer.
"""
import datetime
from typing import Dict, Any, Tuple
from backend.app.core.security import verify_password, generate_session_token
from backend.app.core.config import SESSION_EXPIRE_HOURS
from backend.app.core.exceptions import UnauthorizedException, NotFoundException
from backend.app.features.auth.repository import AuthRepository


class AuthService:
    def __init__(self, repo: AuthRepository):
        self.repo = repo

    def login(self, identifier: str, password: str, selected_role: str = None) -> Tuple[str, Dict[str, Any]]:
        user = self.repo.find_user_by_username_or_email(identifier)
        if not user:
            raise UnauthorizedException("Invalid username or password.")

        if not verify_password(password, user.get("password", "")):
            raise UnauthorizedException("Invalid username or password.")

        # Determine effective role
        role = selected_role or user.get("primary_role", "cosmonaut")
        token = generate_session_token()
        expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=SESSION_EXPIRE_HOURS)).isoformat()
        
        self.repo.create_session(token, user["id"], role, expires_at)
        user_copy = dict(user)
        user_copy.pop("password", None)
        user_copy["active_role"] = role
        return token, user_copy

    def logout(self, session_id: str):
        if session_id:
            self.repo.delete_session(session_id)

    def switch_role(self, session_id: str, new_role: str):
        valid_roles = ["guardian", "reviewer", "cosmonaut", "admin"]
        if new_role.lower() not in valid_roles:
            raise ValueError(f"Invalid role '{new_role}'. Valid roles: {valid_roles}")
        self.repo.update_session_role(session_id, new_role.lower())
