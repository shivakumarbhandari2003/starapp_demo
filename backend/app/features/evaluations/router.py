"""
Evaluations API Router (/api/v1/evaluations).
"""
import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, status
from backend.app.core.dependencies import get_db, get_current_user, require_reviewer
from backend.app.features.evaluations.schemas import SubmitEvaluationRequest
from backend.app.features.evaluations.repository import EvaluationsRepository
from backend.app.features.evaluations.service import EvaluationsService

router = APIRouter(prefix="/evaluations", tags=["Evaluations & Marksheets"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_evaluation(
    req: SubmitEvaluationRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_reviewer)
):
    repo = EvaluationsRepository(conn)
    service = EvaluationsService(repo)
    eval_id = service.submit_evaluation(req.dict(), user)
    return {
        "success": True,
        "evaluation_id": eval_id,
        "message": f"Evaluation submitted successfully with decision: {req.decision}."
    }


@router.get("/marksheets")
async def get_marksheets(
    badge_id: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user)
):
    repo = EvaluationsRepository(conn)
    service = EvaluationsService(repo)
    marksheets = service.get_marksheets(user["id"], badge_id)
    return {"success": True, "count": len(marksheets), "marksheets": marksheets}


@router.get("/leaderboard")
async def get_leaderboard(conn: sqlite3.Connection = Depends(get_db)):
    repo = EvaluationsRepository(conn)
    service = EvaluationsService(repo)
    leaderboard = service.get_leaderboard()
    return {"success": True, "count": len(leaderboard), "leaderboard": leaderboard}
