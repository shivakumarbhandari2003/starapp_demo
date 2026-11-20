"""
Badges API Router (/api/v1/badges).
"""
import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, status
from backend.app.core.dependencies import get_db, get_current_user, require_guardian
from backend.app.features.badges.schemas import CreateBadgeRequest, UpdateBadgeRequest
from backend.app.features.badges.repository import BadgesRepository
from backend.app.features.badges.service import BadgesService

router = APIRouter(prefix="/badges", tags=["Badges"])


@router.get("/")
async def list_badges(
    band: Optional[str] = None,
    status: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db)
):
    repo = BadgesRepository(conn)
    service = BadgesService(repo)
    badges = service.get_badges(band, status)
    return {"success": True, "count": len(badges), "badges": badges}


@router.get("/{badge_id}")
async def get_badge(badge_id: str, conn: sqlite3.Connection = Depends(get_db)):
    repo = BadgesRepository(conn)
    service = BadgesService(repo)
    badge = service.get_badge(badge_id)
    return {"success": True, "badge": badge}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_badge(
    req: CreateBadgeRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    repo = BadgesRepository(conn)
    service = BadgesService(repo)
    badge_data = req.dict()
    badge_data["creator_id"] = user["id"]
    badge_id = service.create_badge(badge_data)
    return {"success": True, "badge_id": badge_id, "message": "Badge created successfully."}


@router.put("/{badge_id}")
async def update_badge(
    badge_id: str,
    req: UpdateBadgeRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user)
):
    repo = BadgesRepository(conn)
    service = BadgesService(repo)
    updated = service.update_badge(badge_id, req.dict(exclude_unset=True))
    return {"success": True, "badge": updated}
