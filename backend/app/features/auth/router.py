"""
Authentication API Router (/api/v1/auth).
"""
import sqlite3
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Response, Cookie, status
from backend.app.core.config import SESSION_COOKIE_NAME, DEMO_MODE, COOKIE_SECURE
from backend.app.core.exceptions import ForbiddenException
from backend.app.core.dependencies import get_db, get_current_user
from backend.app.features.auth.schemas import LoginRequest, SwitchRoleRequest, LoginResponse
from backend.app.features.auth.repository import AuthRepository
from backend.app.features.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, response: Response, conn: sqlite3.Connection = Depends(get_db)):
    repo = AuthRepository(conn)
    service = AuthService(repo)
    token, user = service.login(req.username_or_email, req.password, req.selected_role)
    
    # Set HttpOnly Session Cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,  # set STARAPP_COOKIE_SECURE=true behind HTTPS
        max_age=86400,
    )
    return LoginResponse(success=True, token=token, user=user)


@router.post("/logout")
async def logout(
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
    starapp_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME)
):
    if starapp_session:
        repo = AuthRepository(conn)
        service = AuthService(repo)
        service.logout(starapp_session)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return {"success": True, "message": "Logged out successfully."}


@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_copy = dict(current_user)
    user_copy.pop("password", None)
    return {"success": True, "user": user_copy}


@router.post("/switch-role")
async def switch_role(
    req: SwitchRoleRequest,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    starapp_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME)
):
    if starapp_session:
        repo = AuthRepository(conn)
        service = AuthService(repo)
        service.switch_role(starapp_session, req.role, current_user.get("id"))
    return {"success": True, "active_role": req.role.lower()}


@router.get("/demo-users")
async def get_demo_users(conn: sqlite3.Connection = Depends(get_db)):
    if not DEMO_MODE:  # the full employee directory must not be public in a real deployment
        raise ForbiddenException("The demo user directory is disabled.")
    repo = AuthRepository(conn)
    users = repo.get_demo_users()
    return {"success": True, "users": users}
