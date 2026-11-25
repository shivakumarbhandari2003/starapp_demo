"""
API v1 Cycles & Dual-Role Appraisal Router.
Provides REST endpoints to list/create 6-month cycles, compute Cosmonaut+Reviewer
performance appraisals, adjust hike/promotion fields, and finalize/close cycles.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from starapp.storage import store
from starapp.cycles import (
    compute_cycle_candidate_performance,
    calculate_and_save_cycle_appraisals,
    finalize_and_close_cycle,
    create_new_six_month_cycle,
    activate_cycle,
)

router = APIRouter(prefix="/cycles", tags=["Performance Cycles"])


class CreateCycleRequest(BaseModel):
    name: str
    start_date: str
    end_date: Optional[str] = ""
    code: Optional[str] = ""
    created_by: Optional[str] = "guardian_1"
    clone_badges_from_cycle_id: Optional[str] = ""
    auto_close_previous: bool = False
    set_as_active: bool = True
    notes: Optional[str] = ""


class AppraisalUpdateRequest(BaseModel):
    base_salary: Optional[float] = None
    approved_hike_pct: Optional[float] = None
    bonus_amount: Optional[float] = None
    recommended_promotion_band: Optional[str] = ""
    guardian_remarks: Optional[str] = ""


@router.get("/")
async def list_cycles():
    cycles = [c.to_dict() for c in store.get_all_cycles()]
    return {
        "active_cycle_id": store.get_active_cycle_id(),
        "cycles": cycles,
    }


@router.post("/")
async def create_cycle(req: CreateCycleRequest):
    ok, msg, new_cyc = create_new_six_month_cycle(
        store=store,
        name=req.name,
        start_date=req.start_date,
        end_date=req.end_date or "",
        code=req.code or "",
        created_by=req.created_by or "guardian_1",
        clone_badges_from_cycle_id=req.clone_badges_from_cycle_id or "",
        auto_close_previous=req.auto_close_previous,
        notes=req.notes or "",
        set_as_active=req.set_as_active,
    )
    if not ok or not new_cyc:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "cycle": new_cyc.to_dict()}


@router.post("/{cycle_id}/activate")
async def activate_target_cycle(cycle_id: str, actor_id: str = "guardian_1"):
    ok, msg, cyc = activate_cycle(cycle_id, store, actor_id=actor_id)
    if not ok or not cyc:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "cycle": cyc.to_dict()}


@router.get("/{cycle_id}/performance")
async def get_cycle_performance(cycle_id: str):
    cyc = store.get_cycle(cycle_id)
    if not cyc:
        raise HTTPException(status_code=404, detail="Cycle not found")
    with store.cycle_scope(cycle_id):
        rows = compute_cycle_candidate_performance(cycle_id, store)
    return {"cycle": cyc.to_dict(), "candidates": rows}


@router.post("/{cycle_id}/calculate")
async def calculate_cycle_performance(cycle_id: str, actor_id: str = "guardian_1"):
    cyc = store.get_cycle(cycle_id)
    if not cyc:
        raise HTTPException(status_code=404, detail="Cycle not found")
    with store.cycle_scope(cycle_id):
        saved = calculate_and_save_cycle_appraisals(cycle_id, store, actor_id=actor_id)
    return {"success": True, "count": len(saved), "appraisals": [a.to_dict() for a in saved]}


@router.put("/{cycle_id}/appraisals/{user_id}")
async def update_candidate_appraisal(cycle_id: str, user_id: str, req: AppraisalUpdateRequest):
    cyc = store.get_cycle(cycle_id)
    if not cyc:
        raise HTTPException(status_code=404, detail="Cycle not found")
    if cyc.status == "closed":
        raise HTTPException(status_code=400, detail="Closed cycle is read-only")
    with store.cycle_scope(cycle_id):
        calculate_and_save_cycle_appraisals(cycle_id, store, preserve_manual_overrides=True)
        app_obj = store.get_cycle_appraisal(cycle_id, user_id)
        if not app_obj:
            raise HTTPException(status_code=404, detail="Candidate appraisal not found")
        base_sal = float(req.base_salary if req.base_salary is not None else app_obj.base_salary)
        hike_pct = float(req.approved_hike_pct if req.approved_hike_pct is not None else app_obj.approved_hike_pct)
        bonus_amt = float(req.bonus_amount if req.bonus_amount is not None else app_obj.bonus_amount)
        hike_amt = round(base_sal * (hike_pct / 100.0), 2) if base_sal > 0 else 0.0
        new_sal = round(base_sal + hike_amt, 2) if base_sal > 0 else 0.0
        app_obj.base_salary = base_sal
        app_obj.approved_hike_pct = hike_pct
        app_obj.hike_amount = hike_amt
        app_obj.new_salary = new_sal
        app_obj.bonus_amount = bonus_amt
        if req.recommended_promotion_band is not None:
            app_obj.recommended_promotion_band = req.recommended_promotion_band
        if req.guardian_remarks is not None:
            app_obj.guardian_remarks = req.guardian_remarks
        app_obj.status = "adjusted"
        store.save_cycle_appraisal(app_obj)
    return {"success": True, "appraisal": app_obj.to_dict()}


@router.post("/{cycle_id}/finalize")
async def finalize_cycle(cycle_id: str, actor_id: str = "guardian_1"):
    with store.cycle_scope(cycle_id):
        ok, msg = finalize_and_close_cycle(cycle_id, store, actor_id=actor_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}
