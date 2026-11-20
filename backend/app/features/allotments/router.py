"""
Allotments API Router (/api/v1/allotments).
"""
import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, status
from backend.app.core.dependencies import get_db, get_current_user, require_guardian
from backend.app.features.allotments.schemas import AllotBadgeRequest, ExtensionRequestSchema, ExtensionDecisionSchema
from backend.app.features.allotments.repository import AllotmentsRepository
from backend.app.features.allotments.service import AllotmentsService

router = APIRouter(prefix="/allotments", tags=["Allotments & Roadmap"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def allot_badge(
    req: AllotBadgeRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    repo = AllotmentsRepository(conn)
    service = AllotmentsService(repo)
    count = service.allot_badge(req.badge_id, req.cosmonaut_ids, req.timeline)
    return {"success": True, "allotted_count": count, "message": f"Badge allotted to {count} cosmonauts."}


@router.get("/roadmap")
async def get_roadmap(
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user)
):
    repo = AllotmentsRepository(conn)
    service = AllotmentsService(repo)
    roadmap = service.get_cosmonaut_roadmap(user["id"])
    return {"success": True, "cosmonaut_id": user["id"], "badges": roadmap}


@router.get("/guardian-overview")
async def get_guardian_allotments(
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    repo = AllotmentsRepository(conn)
    service = AllotmentsService(repo)
    allotments = service.get_guardian_allotments()
    return {"success": True, "count": len(allotments), "allotments": allotments}


@router.post("/extensions/request", status_code=status.HTTP_201_CREATED)
async def request_extension(
    req: ExtensionRequestSchema,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user)
):
    repo = AllotmentsRepository(conn)
    service = AllotmentsService(repo)
    ext_id = service.request_extension(req.badge_id, user["id"], req.proposed_deadline, req.reason)
    return {"success": True, "extension_id": ext_id, "message": "Extension request submitted."}


@router.get("/extensions")
async def list_extensions(
    status: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    repo = AllotmentsRepository(conn)
    service = AllotmentsService(repo)
    extensions = service.list_extensions(status)
    return {"success": True, "count": len(extensions), "extensions": extensions}


@router.post("/extensions/{extension_id}/decision")
async def decide_extension(
    extension_id: str,
    req: ExtensionDecisionSchema,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    repo = AllotmentsRepository(conn)
    service = AllotmentsService(repo)
    success = service.decide_extension(extension_id, req.status, req.response_notes)
    return {"success": success, "decision": req.status}
