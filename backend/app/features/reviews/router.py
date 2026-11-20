"""
Reviews API Router (/api/v1/reviews).
"""
import sqlite3
from fastapi import APIRouter, Depends, status
from backend.app.core.dependencies import get_db, get_current_user, require_guardian, require_reviewer
from backend.app.features.reviews.schemas import DispatchReviewRequest, ReviewDecisionRequest
from backend.app.features.reviews.repository import ReviewsRepository
from backend.app.features.badges.repository import BadgesRepository
from backend.app.features.users.repository import UserRepository
from backend.app.features.reviews.service import ReviewsService

router = APIRouter(prefix="/reviews", tags=["Badge Reviews & Approval"])


@router.post("/request", status_code=status.HTTP_201_CREATED)
async def dispatch_review_request(
    req: DispatchReviewRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    repo = ReviewsRepository(conn)
    badge_repo = BadgesRepository(conn)
    user_repo = UserRepository(conn)
    service = ReviewsService(repo, badge_repo, user_repo)
    assign_id = service.dispatch_review_request(req.badge_id, req.reviewer_id, req.notes)
    return {
        "success": True,
        "assignment_id": assign_id,
        "message": "Review request dispatched successfully to reviewer."
    }


@router.get("/inbox")
async def get_reviewer_inbox(
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user)
):
    repo = ReviewsRepository(conn)
    badge_repo = BadgesRepository(conn)
    user_repo = UserRepository(conn)
    service = ReviewsService(repo, badge_repo, user_repo)
    inbox = service.get_reviewer_inbox(user["id"])
    return {"success": True, "count": len(inbox), "requests": inbox}


@router.get("/guardian-overview")
async def get_guardian_overview(
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    repo = ReviewsRepository(conn)
    badge_repo = BadgesRepository(conn)
    user_repo = UserRepository(conn)
    service = ReviewsService(repo, badge_repo, user_repo)
    requests = service.get_guardian_overview()
    return {"success": True, "count": len(requests), "requests": requests}


@router.post("/{badge_id}/decision")
async def submit_review_decision(
    badge_id: str,
    req: ReviewDecisionRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user)
):
    repo = ReviewsRepository(conn)
    badge_repo = BadgesRepository(conn)
    user_repo = UserRepository(conn)
    service = ReviewsService(repo, badge_repo, user_repo)
    service.submit_decision(badge_id, user["id"], req.dict(exclude_unset=True))
    return {
        "success": True,
        "decision": req.decision,
        "message": f"Review {req.decision} recorded and saved permanently."
    }
