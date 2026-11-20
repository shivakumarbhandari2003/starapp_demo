"""
Audit and activity event router (/api/v1/audit).
"""
import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends
from backend.app.core.dependencies import get_db, require_guardian
from backend.app.database.connection import check_database_integrity

router = APIRouter(prefix="/audit", tags=["Audit & System Diagnostics"])


@router.get("/logs")
async def get_audit_logs(
    limit: int = 50,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    cur = conn.cursor()
    cur.execute("""
        SELECT e.*, b.code AS badge_code, b.title AS badge_title, u.name AS actor_name
        FROM badge_review_events e
        LEFT JOIN badges b ON e.badge_id = b.id
        LEFT JOIN users u ON e.actor_id = u.id
        ORDER BY e.timestamp DESC
        LIMIT ?;
    """, (limit,))
    logs = [dict(row) for row in cur.fetchall()]
    return {"success": True, "count": len(logs), "logs": logs}


@router.get("/health")
async def get_system_health(conn: sqlite3.Connection = Depends(get_db)):
    health_status = check_database_integrity()
    return {"success": True, "health": health_status}
