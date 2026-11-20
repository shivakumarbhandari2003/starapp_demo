"""
Users API Router (/api/v1/users).
"""
import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends
from backend.app.core.dependencies import get_db, get_current_user
from backend.app.features.users.repository import UserRepository
from backend.app.features.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users & Corporate Hierarchy"])


@router.get("/")
async def list_users(
    band: Optional[str] = None,
    track: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db)
):
    repo = UserRepository(conn)
    service = UserService(repo)
    users = service.get_users(band, track)
    return {"success": True, "count": len(users), "users": users}


@router.get("/eligible-reviewers/{badge_band}")
async def get_eligible_reviewers(
    badge_band: str,
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Returns only reviewers satisfying Reviewer_Band > Badge_Band rule.
    """
    repo = UserRepository(conn)
    service = UserService(repo)
    reviewers = service.get_eligible_reviewers(badge_band)
    return {
        "success": True,
        "badge_band": badge_band.upper(),
        "count": len(reviewers),
        "reviewers": reviewers,
    }


@router.get("/hierarchy/tree")
async def get_hierarchy_tree(conn: sqlite3.Connection = Depends(get_db)):
    repo = UserRepository(conn)
    service = UserService(repo)
    tree = service.get_hierarchy_tree()
    return {"success": True, "tree": tree}


@router.get("/{user_id}")
async def get_user_profile(user_id: str, conn: sqlite3.Connection = Depends(get_db)):
    repo = UserRepository(conn)
    service = UserService(repo)
    user = service.get_user_profile(user_id)
    return {"success": True, "user": user}
