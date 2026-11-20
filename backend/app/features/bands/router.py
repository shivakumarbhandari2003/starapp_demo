"""
Bands API Router (/api/v1/bands).
"""
import sqlite3
from fastapi import APIRouter, Depends
from backend.app.core.dependencies import get_db, get_current_user, require_guardian
from backend.app.features.bands.schemas import AddCapabilityRequest, AddSkillRequest
from backend.app.features.bands.repository import BandsRepository
from backend.app.features.bands.service import BandsService

router = APIRouter(prefix="/bands", tags=["Bands & Taxonomy"])


@router.get("/")
async def list_bands(conn: sqlite3.Connection = Depends(get_db)):
    repo = BandsRepository(conn)
    service = BandsService(repo)
    bands = service.get_bands()
    return {"success": True, "bands": bands}


@router.get("/taxonomy")
async def get_taxonomy(conn: sqlite3.Connection = Depends(get_db)):
    repo = BandsRepository(conn)
    service = BandsService(repo)
    taxonomy = service.get_taxonomy()
    return {"success": True, "taxonomy": taxonomy}


@router.post("/capabilities")
async def add_capability(
    req: AddCapabilityRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    repo = BandsRepository(conn)
    service = BandsService(repo)
    success = service.add_capability(req.name, user["id"])
    return {"success": success, "name": req.name}


@router.post("/skills")
async def add_skill(
    req: AddSkillRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(require_guardian)
):
    repo = BandsRepository(conn)
    service = BandsService(repo)
    success = service.add_skill(req.name, req.capability_name, user["id"])
    return {"success": success, "name": req.name}
