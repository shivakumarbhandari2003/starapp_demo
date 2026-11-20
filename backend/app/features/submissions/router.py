"""
Submissions API Router (/api/v1/submissions).
"""
import sqlite3
from fastapi import APIRouter, Depends, status
from backend.app.core.dependencies import get_db, get_current_user, require_reviewer
from backend.app.features.submissions.schemas import CreateSubmissionRequest
from backend.app.features.submissions.repository import SubmissionsRepository
from backend.app.features.submissions.service import SubmissionsService

router = APIRouter(prefix="/submissions", tags=["Project Submissions"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_project(
    req: CreateSubmissionRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user)
):
    repo = SubmissionsRepository(conn)
    service = SubmissionsService(repo)
    data = req.dict()
    data["cosmonaut_id"] = user["id"]
    submission = service.submit_project(data)
    return {
        "success": True,
        "submission": submission,
        "message": f"Project submitted successfully (Attempt #{submission['attempt_number']})."
    }


@router.get("/history/{badge_id}")
async def get_submission_history(
    badge_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user)
):
    repo = SubmissionsRepository(conn)
    service = SubmissionsService(repo)
    history = service.get_history(badge_id, user["id"])
    return {"success": True, "count": len(history), "attempts": history}


@router.get("/pending")
async def get_pending_submissions(
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_reviewer)
):
    repo = SubmissionsRepository(conn)
    service = SubmissionsService(repo)
    pending = service.get_pending()
    return {"success": True, "count": len(pending), "submissions": pending}
