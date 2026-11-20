"""
FastAPI dependency injection utilities for database connections, authentication, and RBAC.
"""
import sqlite3
import datetime
from typing import Generator, Optional, Dict, Any, List
from fastapi import Request, Depends, Cookie, Header
from backend.app.core.config import SESSION_COOKIE_NAME
from backend.app.core.exceptions import UnauthorizedException, ForbiddenException
from backend.app.database.connection import get_connection


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Dependency yielding a thread-safe database connection."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


async def get_current_user(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    starapp_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Extracts and validates session token from Cookie or Authorization Header.
    Returns user details dict.
    """
    token = None
    if starapp_session:
        token = starapp_session
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        # Check if request has demo user query param for instant demo switching in development
        demo_user_id = request.query_params.get("demo_user_id")
        if demo_user_id:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?;", (demo_user_id,))
            user_row = cur.fetchone()
            if user_row:
                return dict(user_row)
        raise UnauthorizedException("Authentication required. Please log in.")

    cur = conn.cursor()
    # Check session
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        SELECT s.id AS session_id, s.role AS session_role, s.expires_at,
               u.*
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = ? AND s.expires_at > ?;
    """, (token, now_iso))
    row = cur.fetchone()
    if not row:
        raise UnauthorizedException("Invalid or expired session. Please log in again.")

    # Update last_active_at
    cur.execute("UPDATE user_sessions SET last_active_at = ? WHERE id = ?;", (now_iso, token))
    user_dict = dict(row)
    # Allow overriding role from session if session_role was explicitly selected
    if user_dict.get("session_role"):
        user_dict["active_role"] = user_dict["session_role"]
    else:
        user_dict["active_role"] = user_dict.get("primary_role", "cosmonaut")
    return user_dict


def require_roles(allowed_roles: List[str]):
    """Factory dependency requiring one of the specified roles."""
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("active_role", "").lower()
        allowed = [r.lower() for r in allowed_roles]
        if user_role not in allowed and "admin" not in allowed and user_role != "admin" and user_role != "guardian":
            raise ForbiddenException(f"Access denied for role '{user_role}'. Required roles: {allowed_roles}")
        return current_user
    return role_checker


require_guardian = require_roles(["guardian", "admin"])
require_reviewer = require_roles(["reviewer", "guardian", "admin"])
require_cosmonaut = require_roles(["cosmonaut", "guardian", "admin", "reviewer"])
