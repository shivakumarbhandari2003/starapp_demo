"""
FastAPI dependency injection utilities for database connections, authentication, and RBAC.
"""
import sqlite3
import datetime
from typing import Generator, Optional, Dict, Any, List
from fastapi import Request, Depends, Cookie, Header
from backend.app.core.config import SESSION_COOKIE_NAME, DEMO_MODE
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


def _attach_roles(cur: sqlite3.Cursor, user_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Adds every system role the user holds (guardian / badge_reviewer / project_reviewer / cosmonaut)."""
    try:
        cur.execute("SELECT role_id FROM user_role_assignments WHERE user_id = ?;", (user_dict.get("id"),))
        user_dict["roles"] = [r[0] for r in cur.fetchall()]
    except Exception:
        user_dict["roles"] = []
    return user_dict


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

    if not token and not DEMO_MODE:
        # Production: identity comes ONLY from a verified session token (cookie / Bearer).
        raise UnauthorizedException("Authentication required. Please log in.")

    if not token:
        # DEMO MODE ONLY: instant user switching via ?demo_user_id= / X-User-Id, or the active UI session.
        demo_user_id = request.query_params.get("demo_user_id") or request.headers.get("X-User-Id")
        if demo_user_id:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?;", (demo_user_id,))
            user_row = cur.fetchone()
            if user_row:
                user_dict = dict(user_row)
                user_dict["active_role"] = user_dict.get("primary_role", "cosmonaut")
                return _attach_roles(cur, user_dict)

        # Check active controller user in unified full-stack process
        try:
            from backend.app.main import get_session_controller
            sid = request.headers.get("X-Session-Id") or request.query_params.get("session_id") or "default"
            ctrl = get_session_controller(sid)
            active_u = getattr(ctrl, "current_user", None)
            if active_u and getattr(active_u, "id", None):
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE id = ?;", (active_u.id,))
                user_row = cur.fetchone()
                if user_row:
                    user_dict = dict(user_row)
                    user_dict["active_role"] = active_u.role or user_dict.get("primary_role", "cosmonaut")
                    return _attach_roles(cur, user_dict)
        except Exception:
            pass

        try:
            from starapp.app import controller
            if getattr(controller, "current_user", None) and controller.current_user.id:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE id = ?;", (controller.current_user.id,))
                user_row = cur.fetchone()
                if user_row:
                    user_dict = dict(user_row)
                    user_dict["active_role"] = controller.current_user.role or user_dict.get("primary_role", "cosmonaut")
                    return _attach_roles(cur, user_dict)
        except Exception:
            pass

        raise UnauthorizedException("Authentication required. Please log in.")

    cur = conn.cursor()
    # Check session
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        SELECT s.id AS session_id, s.role AS session_role, s.expires_at, s.last_active_at,
               u.*
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = ? AND s.expires_at > ?;
    """, (token, now_iso))
    row = cur.fetchone()
    if not row:
        raise UnauthorizedException("Invalid or expired session. Please log in again.")

    # Touch last_active_at at most once every 5 minutes and COMMIT IMMEDIATELY. Writing on every request
    # and keeping the transaction open until the response was sent held SQLite's single write lock, so
    # every store write made while handling the same request waited out the 5 s busy timeout.
    user_dict = dict(row)
    try:
        last_active = datetime.datetime.fromisoformat(str(row["last_active_at"]))
        stale = (datetime.datetime.now(datetime.timezone.utc) - last_active).total_seconds() > 300
    except Exception:
        stale = True
    if stale:
        cur.execute("UPDATE user_sessions SET last_active_at = ? WHERE id = ?;", (now_iso, token))
        conn.commit()
    # Allow overriding role from session if session_role was explicitly selected
    if user_dict.get("session_role"):
        user_dict["active_role"] = user_dict["session_role"]
    else:
        user_dict["active_role"] = user_dict.get("primary_role", "cosmonaut")
    return _attach_roles(cur, user_dict)


# Which concrete role names satisfy each logical requirement.
_ROLE_ALIASES = {
    "guardian": {"guardian", "admin"},
    "admin": {"guardian", "admin"},
    "reviewer": {"reviewer", "badge_reviewer", "project_reviewer"},
    "cosmonaut": {"cosmonaut", "cadet"},
}


def require_roles(allowed_roles: List[str]):
    """
    Factory dependency requiring at least one of the specified roles.

    BUG FIXED: the old condition `... and "admin" not in allowed and ...` was always False for the
    guardian / reviewer / cosmonaut guards (all of them list "admin"), so EVERY authenticated user
    passed EVERY role guard. A user is now authorised when the role of their session, or any system
    role assigned to them, satisfies the requirement. Guardians / admins may do everything.
    """
    needed = set()
    for r in allowed_roles:
        needed |= _ROLE_ALIASES.get(r.lower(), {r.lower()})

    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        held = {str(current_user.get("active_role", "")).lower()}
        held |= {str(r).lower() for r in current_user.get("roles", [])}
        if held & needed or held & {"guardian", "admin"}:
            return current_user
        raise ForbiddenException(
            f"Access denied for role '{current_user.get('active_role', '')}'. Required roles: {allowed_roles}"
        )
    return role_checker


async def get_current_user_optional(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    starapp_session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
    authorization: Optional[str] = Header(None),
) -> Optional[Dict[str, Any]]:
    """Optional user dependency that does not raise 401 when unauthenticated."""
    try:
        return await get_current_user(request, conn, starapp_session, authorization)
    except Exception:
        if not DEMO_MODE:
            return None  # production: unauthenticated callers stay anonymous (never silently a guardian)
        # DEMO MODE ONLY: fall back to guardian_1 for local development
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id IN ('guardian_1', 'admin') LIMIT 1;")
        row = cur.fetchone()
        if row:
            d = dict(row)
            d["active_role"] = d.get("primary_role", "guardian")
            return d
        return None


require_guardian = require_roles(["guardian", "admin"])
require_reviewer = require_roles(["reviewer", "guardian", "admin"])
require_cosmonaut = require_roles(["cosmonaut", "guardian", "admin", "reviewer"])
