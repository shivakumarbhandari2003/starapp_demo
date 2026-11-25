"""
STARAPP 6-MONTH PERFORMANCE CYCLES & DUAL-ROLE APPRAISAL ENGINE
Manages 6-month cycle creation, participant enrollment, dual-role candidate performance
(both as Cosmonaut and as Reviewer), hike/compensation calculations, and cycle closure.
"""

import json
import datetime
from typing import List, Dict, Any, Optional, Tuple
from starapp.models import (
    DEFAULT_CYCLE_ID,
    DEFAULT_HIKE_POLICY,
    PerformanceCycle,
    CycleEnrollment,
    CyclePerformanceAppraisal,
    Badge,
    User,
    add_six_months_iso,
    current_iso_timestamp,
)
from starapp.mapping_data import BAND_CODES, get_higher_bands


def _next_band(band_code: str) -> str:
    if band_code in BAND_CODES:
        idx = BAND_CODES.index(band_code)
        if idx + 1 < len(BAND_CODES):
            return BAND_CODES[idx + 1]
    return ""


def _resolve_tier_and_hike(score: float, policy: Optional[Dict[str, Any]] = None, has_activity: bool = True) -> Tuple[str, float]:
    """Maps a 0-100 composite performance score to a rating tier and recommended hike %."""
    if not has_activity:
        return "Not Assessed", 0.0
    p = policy if isinstance(policy, dict) else DEFAULT_HIKE_POLICY
    slabs = p.get("slabs") or DEFAULT_HIKE_POLICY["slabs"]
    sorted_slabs = sorted(slabs, key=lambda s: float(s.get("min_score", 0.0)), reverse=True)
    for slab in sorted_slabs:
        if score >= float(slab.get("min_score", 0.0)):
            return str(slab.get("tier", "Meets Expectations")), float(slab.get("recommended_hike_pct", 0.0))
    return "Needs Development", 0.0


def compute_cycle_candidate_performance(
    cycle_id: str,
    store: Any,
    users_override: Optional[List[User]] = None
) -> List[Dict[str, Any]]:
    """
    Computes complete performance telemetry inside `cycle_id` for every candidate across BOTH roles:
      1. Performance as Cosmonaut (assigned badges, earned badges, 50-mark avg & rubric breakdown, first-attempt rate)
      2. Performance as Reviewer (badge reviews completed, projects authored/released, submissions graded, avg marks awarded)
    Combines them into a cycle composite score, tier, and recommended hike %.
    """
    cycle = store.get_cycle(cycle_id)
    policy = cycle.hike_policy if cycle else DEFAULT_HIKE_POLICY
    enrollments = {e.user_id: e for e in store.get_cycle_enrollments(cycle_id)}
    existing_appraisals = {a.cosmonaut_id: a for a in store.get_cycle_appraisals(cycle_id)}

    candidates = users_override if users_override is not None else store.get_all_cosmonauts()
    # Keep deterministic band -> name order
    band_rank = {b: i for i, b in enumerate(BAND_CODES)}
    candidates = sorted(candidates, key=lambda u: (band_rank.get(getattr(u, "band", "B1"), 99), getattr(u, "name", "")))

    cycle_badges = store.get_all_badges(cycle_id=cycle_id)
    badges_map = {b.id: b for b in cycle_badges}
    cycle_timelines = store.get_timelines_dict(cycle_id=cycle_id)
    cycle_mappings = store.get_band_mappings(cycle_id=cycle_id)
    cycle_requests = store.get_mapping_requests(cycle_id=cycle_id)
    cycle_prompts = store.get_reviewer_project_prompts(cycle_id=cycle_id)
    cycle_subs = store.get_all_submissions(cycle_id=cycle_id)
    cycle_asms = store.get_all_assessments(cycle_id=cycle_id)
    cycle_exts = store.get_all_extensions(cycle_id=cycle_id)

    # Query badge_reviewer_assignments for this cycle
    rev_assignments_by_user: Dict[str, List[Dict[str, Any]]] = {}
    if store.db and getattr(store.db, "conn", None):
        try:
            rows = store.db.conn.execute(
                "SELECT * FROM badge_reviewer_assignments WHERE cycle_id = ?",
                (cycle_id,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                rev_assignments_by_user.setdefault(d.get("reviewer_id", ""), []).append(d)
        except Exception:
            pass

    results: List[Dict[str, Any]] = []

    for u in candidates:
        uid = u.id
        enr = enrollments.get(uid)
        band_code = (enr.band_code if enr else None) or getattr(u, "band", "B1") or "B1"
        base_salary = float(enr.base_salary) if enr else 0.0

        # ------------------------------------------------------------------
        # 1. AS COSMONAUT METRICS (within cycle_id)
        # ------------------------------------------------------------------
        assigned_badge_ids = set()
        for t in cycle_timelines.values():
            if t.cosmonaut_id == uid:
                assigned_badge_ids.add(t.badge_id)
        for m in cycle_mappings:
            if uid in m.get("cosmonauts", []):
                m_b = m.get("badge_id") or m.get("badge")
                matched_b = next((b for b in cycle_badges if b.id == m_b or b.code == m_b or b.title == m_b), None)
                if matched_b:
                    assigned_badge_ids.add(matched_b.id)
        for b in cycle_badges:
            if uid in getattr(b, "assigned_cosmonaut_ids", []) and (b.is_published or b.is_allocated):
                assigned_badge_ids.add(b.id)

        u_subs = [s for s in cycle_subs if s.cosmonaut_id == uid]
        u_asms = [a for a in cycle_asms if a.cosmonaut_id == uid]
        u_exts = [e for e in cycle_exts if e.cosmonaut_id == uid]

        for s in u_subs:
            assigned_badge_ids.add(s.badge_id)

        badges_assigned = len(assigned_badge_ids)
        badges_submitted = len({s.badge_id for s in u_subs})
        total_attempts = len(u_subs)

        # Prefer Guardian final evaluations per badge; fall back to reviewer assessment if pending Guardian
        guardian_approved_asms = [
            a for a in u_asms
            if a.decision in ("approve", "approved") and getattr(a, "assessor_role", "guardian") == "guardian"
        ]
        earned_badge_ids = {a.badge_id for a in guardian_approved_asms}
        for t in cycle_timelines.values():
            if t.cosmonaut_id == uid and getattr(t, "status", "") == "completed":
                earned_badge_ids.add(t.badge_id)

        badges_earned = len(earned_badge_ids)
        first_attempt_passes = sum(1 for a in guardian_approved_asms if getattr(a, "attempt_number", 1) == 1)

        # Average marks across final Guardian marksheets (or latest per badge if not yet earned)
        eval_pool = guardian_approved_asms
        if not eval_pool and u_asms:
            # Use latest per badge if any evaluations exist
            by_badge: Dict[str, Any] = {}
            for a in sorted(u_asms, key=lambda x: getattr(x, "reviewed_at", "")):
                by_badge[a.badge_id] = a
            eval_pool = list(by_badge.values())

        if eval_pool:
            avg_marks = round(sum(a.total_marks for a in eval_pool) / len(eval_pool), 2)
            avg_percentage = round(sum(a.percentage for a in eval_pool) / len(eval_pool), 1)
            rubric_avgs = {
                "business": round(sum(a.business_understanding for a in eval_pool) / len(eval_pool), 1),
                "architecture": round(sum(a.architecture_report for a in eval_pool) / len(eval_pool), 1),
                "technical": round(sum(a.technical_knowledge for a in eval_pool) / len(eval_pool), 1),
                "presentation": round(sum(a.presentation for a in eval_pool) / len(eval_pool), 1),
                "qa": round(sum(a.qa for a in eval_pool) / len(eval_pool), 1),
            }
        else:
            avg_marks = 0.0
            avg_percentage = 0.0
            rubric_avgs = {"business": 0.0, "architecture": 0.0, "technical": 0.0, "presentation": 0.0, "qa": 0.0}

        cosmo_completion_pct = round((badges_earned / max(1, badges_assigned)) * 100.0, 1) if badges_assigned > 0 else 0.0
        cosmo_has_activity = bool(badges_assigned > 0 or total_attempts > 0 or len(eval_pool) > 0)
        if cosmo_has_activity:
            # 70% assessment marks % + 30% badge completion %
            cosmo_score = round((avg_percentage * 0.70) + (cosmo_completion_pct * 0.30), 1)
        else:
            cosmo_score = 0.0

        # ------------------------------------------------------------------
        # 2. AS REVIEWER METRICS (within cycle_id)
        # ------------------------------------------------------------------
        u_badge_assigns = list(rev_assignments_by_user.get(uid, []))
        assigned_review_badge_ids = {a["badge_id"] for a in u_badge_assigns}
        for b in cycle_badges:
            if getattr(b, "assigned_reviewer_id", "") == uid and b.id not in assigned_review_badge_ids:
                assigned_review_badge_ids.add(b.id)
                u_badge_assigns.append({
                    "badge_id": b.id,
                    "status": "approved" if getattr(b, "workflow_status", "") == "approved" else (
                        "returned" if getattr(b, "workflow_status", "") == "returned" else "pending"
                    )
                })

        badge_reviews_assigned = len(u_badge_assigns)
        badge_reviews_completed = sum(1 for a in u_badge_assigns if a.get("status") in ("approved", "returned"))

        u_map_reqs = [r for r in cycle_requests if r.get("reviewer_id") == uid]
        mapping_invitations_total = len(u_map_reqs)
        mapping_invitations_accepted = sum(1 for r in u_map_reqs if r.get("status") == "accepted")

        # Cadets & badges mapped to this reviewer for cohort mentorship / project creation / grading
        reviewer_mapped_pairs = set()
        for t in cycle_timelines.values():
            if getattr(t, "reviewer_id", "") == uid:
                reviewer_mapped_pairs.add((t.badge_id, t.cosmonaut_id))
        for m in cycle_mappings:
            if uid in m.get("reviewers", []):
                m_b = m.get("badge_id") or m.get("badge")
                matched_b = next((b for b in cycle_badges if b.id == m_b or b.code == m_b or b.title == m_b), None)
                resolved_bid = matched_b.id if matched_b else m_b
                if resolved_bid:
                    for cid in m.get("cosmonauts", []):
                        reviewer_mapped_pairs.add((resolved_bid, cid))

        u_prompts = [p for p in cycle_prompts if getattr(p, "reviewer_id", "") == uid]
        projects_created = len(u_prompts)
        projects_released = sum(1 for p in u_prompts if getattr(p, "status", "") in ("released", "sent"))

        # Submissions assigned to this reviewer in cycle_id
        assigned_sub_ids = {
            s.id for s in cycle_subs
            if (s.badge_id, s.cosmonaut_id) in reviewer_mapped_pairs
        }
        # Reviewer marksheets submitted by uid in cycle_id
        u_reviewer_asms = [
            a for a in cycle_asms
            if a.reviewer_id == uid and getattr(a, "assessor_role", "") == "reviewer"
        ]
        for a in u_reviewer_asms:
            assigned_sub_ids.add(a.submission_id)

        submissions_assigned_to_review = len(assigned_sub_ids)
        submissions_graded = len({a.submission_id for a in u_reviewer_asms})
        reviewer_avg_marks_given = round(
            sum(a.total_marks for a in u_reviewer_asms) / len(u_reviewer_asms), 2
        ) if u_reviewer_asms else 0.0

        # Reviewer execution task denominator: badge reviews + distinct mapped badges expecting projects + submissions to grade
        mapped_badge_count_for_proj = len({pair[0] for pair in reviewer_mapped_pairs})
        expected_proj_tasks = max(mapped_badge_count_for_proj, projects_created)
        total_rev_tasks = badge_reviews_assigned + expected_proj_tasks + submissions_assigned_to_review
        completed_rev_tasks = (
            badge_reviews_completed
            + min(expected_proj_tasks, projects_released)
            + min(submissions_assigned_to_review, submissions_graded)
        )
        reviewer_has_activity = bool(total_rev_tasks > 0 or mapping_invitations_total > 0 or projects_created > 0 or submissions_graded > 0)

        if total_rev_tasks > 0:
            reviewer_score = round((completed_rev_tasks / total_rev_tasks) * 100.0, 1)
        elif mapping_invitations_total > 0:
            reviewer_score = round((mapping_invitations_accepted / mapping_invitations_total) * 100.0, 1)
        else:
            reviewer_score = 0.0

        # ------------------------------------------------------------------
        # 3. COMBINED SCORE, TIER & HIKE CALCULATION
        # ------------------------------------------------------------------
        if cosmo_has_activity and reviewer_has_activity:
            w = policy.get("weights") or DEFAULT_HIKE_POLICY["weights"]
            cw = float(w.get("cosmonaut_marks_weight", 0.55)) + float(w.get("cosmonaut_completion_weight", 0.25))
            rw = float(w.get("reviewer_execution_weight", 0.20))
            denom = max(0.01, cw + rw)
            composite_score = round(((cosmo_score * cw) + (reviewer_score * rw)) / denom, 1)
        elif cosmo_has_activity:
            composite_score = cosmo_score
        elif reviewer_has_activity:
            composite_score = reviewer_score
        else:
            composite_score = 0.0

        has_any_activity = cosmo_has_activity or reviewer_has_activity
        tier, rec_hike_pct = _resolve_tier_and_hike(composite_score, policy, has_activity=has_any_activity)

        saved_app = existing_appraisals.get(uid)
        if saved_app:
            eff_base_salary = float(saved_app.base_salary) if saved_app.base_salary else base_salary
            approved_hike_pct = float(saved_app.approved_hike_pct)
            bonus_amount = float(saved_app.bonus_amount)
            rec_promo = saved_app.recommended_promotion_band
            remarks = saved_app.guardian_remarks
            app_status = saved_app.status
            finalized_by = saved_app.finalized_by
            finalized_at = saved_app.finalized_at
        else:
            eff_base_salary = base_salary
            approved_hike_pct = rec_hike_pct
            bonus_amount = 0.0
            rec_promo = _next_band(band_code) if (composite_score >= 85.0 and badges_earned > 0) else ""
            remarks = ""
            app_status = "preview"
            finalized_by = ""
            finalized_at = ""

        hike_amount = round(eff_base_salary * (approved_hike_pct / 100.0), 2) if eff_base_salary > 0 else 0.0
        new_salary = round(eff_base_salary + hike_amount, 2) if eff_base_salary > 0 else 0.0

        results.append({
            "cycle_id": cycle_id,
            "user_id": uid,
            "name": u.name,
            "avatar": u.avatar,
            "email": u.email,
            "band_code": band_code,
            "learning_track": getattr(u, "learning_track", ""),
            "role": getattr(u, "role", "cosmonaut"),
            "roles": list(getattr(u, "roles", [])),
            # As Cosmonaut
            "cosmo_has_activity": cosmo_has_activity,
            "badges_assigned": badges_assigned,
            "badges_submitted": badges_submitted,
            "badges_earned": badges_earned,
            "first_attempt_passes": first_attempt_passes,
            "total_attempts": total_attempts,
            "extensions_count": len(u_exts),
            "avg_marks": avg_marks,
            "avg_percentage": avg_percentage,
            "cosmo_completion_pct": cosmo_completion_pct,
            "cosmo_score": cosmo_score,
            "rubric_avgs": rubric_avgs,
            # As Reviewer
            "reviewer_has_activity": reviewer_has_activity,
            "badge_reviews_assigned": badge_reviews_assigned,
            "badge_reviews_completed": badge_reviews_completed,
            "mapping_invitations_total": mapping_invitations_total,
            "mapping_invitations_accepted": mapping_invitations_accepted,
            "mapped_cohorts_count": len(reviewer_mapped_pairs),
            "projects_created": projects_created,
            "projects_released": projects_released,
            "submissions_assigned_to_review": submissions_assigned_to_review,
            "submissions_graded": submissions_graded,
            "reviewer_avg_marks_given": reviewer_avg_marks_given,
            "reviewer_score": reviewer_score,
            # Overall & Appraisal
            "composite_score": composite_score,
            "performance_tier": tier,
            "base_salary": eff_base_salary,
            "recommended_hike_pct": rec_hike_pct,
            "approved_hike_pct": approved_hike_pct,
            "hike_amount": hike_amount,
            "new_salary": new_salary,
            "bonus_amount": bonus_amount,
            "recommended_promotion_band": rec_promo,
            "guardian_remarks": remarks,
            "status": app_status,
            "finalized_by": finalized_by,
            "finalized_at": finalized_at,
        })

    return results


def calculate_and_save_cycle_appraisals(
    cycle_id: str,
    store: Any,
    actor_id: str = "guardian_1",
    preserve_manual_overrides: bool = True
) -> List[CyclePerformanceAppraisal]:
    """Calculates dual-role performance & appraisal rows for all cycle members and persists them in SQLite."""
    rows = compute_cycle_candidate_performance(cycle_id, store)
    now_iso = current_iso_timestamp()
    saved: List[CyclePerformanceAppraisal] = []

    for r in rows:
        uid = r["user_id"]
        app_id = f"app_{cycle_id}_{uid}"
        existing = store.get_cycle_appraisal(cycle_id, uid)
        if existing and preserve_manual_overrides:
            # Keep manually adjusted hike/salary/remarks if already edited by Guardian
            base_sal = existing.base_salary if existing.base_salary > 0 else r["base_salary"]
            appr_hike = existing.approved_hike_pct if existing.status in ("adjusted", "finalized") else r["recommended_hike_pct"]
            promo_band = existing.recommended_promotion_band if existing.status in ("adjusted", "finalized") else r["recommended_promotion_band"]
            remarks = existing.guardian_remarks
            bonus = existing.bonus_amount
            status = "adjusted" if existing.status == "adjusted" else ("finalized" if existing.status == "finalized" else "calculated")
        else:
            base_sal = r["base_salary"]
            appr_hike = r["recommended_hike_pct"]
            promo_band = r["recommended_promotion_band"]
            remarks = r["guardian_remarks"]
            bonus = r["bonus_amount"]
            status = "calculated"

        hike_amt = round(base_sal * (appr_hike / 100.0), 2) if base_sal > 0 else 0.0
        new_sal = round(base_sal + hike_amt, 2) if base_sal > 0 else 0.0

        app_obj = CyclePerformanceAppraisal(
            id=app_id,
            cycle_id=cycle_id,
            cosmonaut_id=uid,
            band_code=r["band_code"],
            badges_assigned=r["badges_assigned"],
            badges_submitted=r["badges_submitted"],
            badges_earned=r["badges_earned"],
            first_attempt_passes=r["first_attempt_passes"],
            total_attempts=r["total_attempts"],
            avg_marks=r["avg_marks"],
            avg_percentage=r["avg_percentage"],
            cosmo_score=r["cosmo_score"],
            badge_reviews_assigned=r["badge_reviews_assigned"],
            badge_reviews_completed=r["badge_reviews_completed"],
            projects_created=r["projects_created"],
            projects_released=r["projects_released"],
            submissions_assigned_to_review=r["submissions_assigned_to_review"],
            submissions_graded=r["submissions_graded"],
            reviewer_avg_marks_given=r["reviewer_avg_marks_given"],
            reviewer_score=r["reviewer_score"],
            composite_score=r["composite_score"],
            performance_tier=r["performance_tier"],
            base_salary=base_sal,
            recommended_hike_pct=r["recommended_hike_pct"],
            approved_hike_pct=appr_hike,
            hike_amount=hike_amt,
            new_salary=new_sal,
            bonus_amount=bonus,
            recommended_promotion_band=promo_band,
            guardian_remarks=remarks,
            status=status,
            calculated_at=now_iso,
            finalized_by=existing.finalized_by if existing else "",
            finalized_at=existing.finalized_at if existing else "",
            details={
                "cosmo_completion_pct": r["cosmo_completion_pct"],
                "rubric_avgs": r["rubric_avgs"],
                "mapping_invitations_total": r["mapping_invitations_total"],
                "mapping_invitations_accepted": r["mapping_invitations_accepted"],
                "mapped_cohorts_count": r["mapped_cohorts_count"],
                "extensions_count": r["extensions_count"],
                "cosmo_has_activity": r["cosmo_has_activity"],
                "reviewer_has_activity": r["reviewer_has_activity"],
            },
        )
        store.save_cycle_appraisal(app_obj)
        saved.append(app_obj)

    cyc = store.get_cycle(cycle_id)
    if cyc and cyc.status == "active":
        cyc.status = "evaluating"
        store.save_cycle(cyc)

    store.add_activity(
        event_type="cycle_appraisals_calculated",
        actor_id=actor_id,
        actor_name="Guardian",
        cosmonaut_id="",
        badge_id="",
        summary=f"Calculated cycle performance (Cosmonaut + Reviewer) for {len(saved)} members in cycle '{cyc.name if cyc else cycle_id}'.",
        cycle_id=cycle_id
    )
    return saved


def finalize_and_close_cycle(cycle_id: str, store: Any, actor_id: str = "guardian_1") -> Tuple[bool, str]:
    """Finalizes cycle performance appraisals & compensation, locks the cycle (closed), and notifies candidates."""
    cyc = store.get_cycle(cycle_id)
    if not cyc:
        return False, f"Cycle '{cycle_id}' not found."
    if cyc.status == "closed":
        return False, f"Cycle '{cyc.name}' is already finalized and closed."

    # Ensure calculations exist up to date
    appraisals = calculate_and_save_cycle_appraisals(cycle_id, store, actor_id=actor_id, preserve_manual_overrides=True)
    now_iso = current_iso_timestamp()

    for app_obj in appraisals:
        app_obj.status = "finalized"
        app_obj.finalized_by = actor_id
        app_obj.finalized_at = now_iso
        store.save_cycle_appraisal(app_obj)

        # Notify each active participant inside this cycle
        if app_obj.cosmo_score > 0 or app_obj.reviewer_score > 0:
            hike_note = f" Recommended Hike: +{app_obj.approved_hike_pct:.1f}%." if app_obj.approved_hike_pct > 0 else ""
            store.add_notification(
                recipient_id=app_obj.cosmonaut_id,
                title=f"Cycle Finalized: {cyc.name}",
                message=f"Your 6-month cycle performance appraisal is finalized (Overall Score: {app_obj.composite_score}/100, Tier: {app_obj.performance_tier}.{hike_note}). View it in Past Cycles & Appraisals.",
                link_section="c_cycles",
                event_type="cycle_finalized",
                related_badge_id="",
                cycle_id=cycle_id
            )

    cyc.status = "closed"
    cyc.closed_at = now_iso
    store.save_cycle(cyc)

    store.add_activity(
        event_type="cycle_closed",
        actor_id=actor_id,
        actor_name="Guardian",
        cosmonaut_id="",
        badge_id="",
        summary=f"Finalized and closed 6-month performance cycle '{cyc.name}' ({cyc.start_date} → {cyc.end_date}).",
        cycle_id=cycle_id
    )
    return True, f"Cycle '{cyc.name}' finalized & closed. You can now launch a new 6-month cycle."


def activate_cycle(cycle_id: str, store: Any, actor_id: str = "guardian_1") -> Tuple[bool, str, Optional[PerformanceCycle]]:
    """
    Sets `cycle_id` as the single Active 6-month cycle globally for all Cosmonauts & Reviewers.
    Any other currently active/evaluating cycle is cleanly closed/finalized first.
    """
    target = store.get_cycle(cycle_id)
    if not target:
        return False, f"Cycle '{cycle_id}' not found.", None

    existing = store.get_all_cycles()
    for oc in existing:
        if oc.id != target.id and getattr(oc, "status", "") in ("active", "evaluating"):
            ok_close, err_close = finalize_and_close_cycle(oc.id, store, actor_id=actor_id)
            if not ok_close:
                oc.status = "closed"
                oc.closed_at = current_iso_timestamp()
                store.save_cycle(oc)

    target.status = "active"
    target.closed_at = ""
    store.save_cycle(target)

    # Ensure all active users are enrolled in the activated cycle
    existing_enr_uids = {e.user_id for e in store.get_cycle_enrollments(target.id)}
    now_iso = current_iso_timestamp()
    for u in store.get_all_users():
        if u.id not in existing_enr_uids:
            enr = CycleEnrollment(
                id=f"enr_{target.id}_{u.id}",
                cycle_id=target.id,
                user_id=u.id,
                cycle_role=getattr(u, "role", "cosmonaut") or "cosmonaut",
                band_code=getattr(u, "band", "B1") or "B1",
                track_code=getattr(u, "track_code", "") or "SD",
                base_salary=0.0,
                reporting_manager_id=getattr(u, "reporting_manager_id", "") or "",
                status="active",
                enrolled_at=now_iso,
            )
            store.save_cycle_enrollment(enr)

    store.add_activity(
        event_type="cycle_activated",
        actor_id=actor_id,
        actor_name="Guardian",
        cosmonaut_id="",
        badge_id="",
        summary=f"Activated 6-month cycle '{target.name}' ({target.start_date} → {target.end_date}) for all Cosmonauts & Reviewers.",
        cycle_id=target.id,
    )
    return True, f"'{target.name}' is now the Active cycle for all Cosmonauts & Reviewers.", target


def create_new_six_month_cycle(
    store: Any,
    name: str,
    start_date: str,
    end_date: str = "",
    code: str = "",
    created_by: str = "guardian_1",
    clone_badges_from_cycle_id: str = "",
    auto_close_previous: bool = False,
    notes: str = "",
    hike_policy: Optional[Dict[str, Any]] = None,
    set_as_active: bool = True
) -> Tuple[bool, str, Optional[PerformanceCycle]]:
    """
    Creates a new 6-month cycle, enrolls the same cohort users (carrying over finalized
    new salaries & promoted bands if available), and keeps cycle data completely isolated.
    When `set_as_active=True`, it becomes the single active cycle for all Cosmonauts & Reviewers.
    """
    name = (name or "").strip()
    if not name:
        return False, "Please provide a cycle name (e.g., 'Cycle 2 (Jan–Jun 2027)').", None

    start_clean = (start_date or "").strip()[:10]
    if not start_clean:
        start_clean = datetime.date.today().isoformat()
    end_clean = (end_date or "").strip()[:10] or add_six_months_iso(start_clean, 6)
    if end_clean <= start_clean:
        return False, "Cycle End Date must be after Start Date.", None

    existing_cycles = store.get_all_cycles()
    open_cycles = [c for c in existing_cycles if c.status in ("active", "evaluating")]
    prev_cycle = open_cycles[0] if open_cycles else (existing_cycles[0] if existing_cycles else None)

    if set_as_active and open_cycles:
        if auto_close_previous:
            for oc in open_cycles:
                ok_close, err_close = finalize_and_close_cycle(oc.id, store, actor_id=created_by)
                if not ok_close:
                    return False, err_close, None
        else:
            return False, f"Active cycle '{open_cycles[0].name}' must be finalized/closed before creating a new cycle.", None

    idx_num = len(existing_cycles) + 1
    slug_base = f"cycle_{idx_num}_{int(datetime.datetime.now().timestamp())}"
    cycle_code = (code or "").strip() or f"C{idx_num}-{start_clean[:4]}"

    new_status = "active" if set_as_active else "closed"
    new_cycle = PerformanceCycle(
        id=slug_base,
        code=cycle_code,
        name=name,
        start_date=start_clean,
        end_date=end_clean,
        status=new_status,
        created_by=created_by,
        created_at=current_iso_timestamp(),
        closed_at="" if set_as_active else current_iso_timestamp(),
        cloned_from_cycle_id=clone_badges_from_cycle_id or "",
        hike_policy=hike_policy or (prev_cycle.hike_policy if prev_cycle else dict(DEFAULT_HIKE_POLICY)),
        notes=notes or ""
    )
    store.save_cycle(new_cycle)

    # Carry forward all the same people (same user IDs), updating band/salary if finalized in prior cycle
    prev_appraisals = {}
    prev_enrollments = {}
    if prev_cycle:
        prev_appraisals = {a.cosmonaut_id: a for a in store.get_cycle_appraisals(prev_cycle.id)}
        prev_enrollments = {e.user_id: e for e in store.get_cycle_enrollments(prev_cycle.id)}

    now_iso = current_iso_timestamp()
    enrolled_count = 0
    for u in store.get_all_users():
        prev_enr = prev_enrollments.get(u.id)
        prev_app = prev_appraisals.get(u.id)

        eff_band = getattr(u, "band", "B1") or "B1"
        eff_salary = prev_enr.base_salary if prev_enr else 0.0
        if prev_app:
            if prev_app.new_salary > 0:
                eff_salary = prev_app.new_salary
            elif prev_app.base_salary > 0:
                eff_salary = prev_app.base_salary
            if prev_app.recommended_promotion_band and prev_app.recommended_promotion_band in BAND_CODES:
                eff_band = prev_app.recommended_promotion_band
                # Also sync user's active band in SQLite users & membership if promoted
                u.band = eff_band
                store.save_user_band_update(u.id, eff_band)

        enr = CycleEnrollment(
            id=f"enr_{new_cycle.id}_{u.id}",
            cycle_id=new_cycle.id,
            user_id=u.id,
            cycle_role=getattr(u, "role", "cosmonaut") or "cosmonaut",
            band_code=eff_band,
            track_code=getattr(prev_enr, "track_code", "") or "SD",
            base_salary=eff_salary,
            reporting_manager_id=getattr(u, "reporting_manager_id", "") or "",
            status="active",
            enrolled_at=now_iso,
        )
        store.save_cycle_enrollment(enr)
        enrolled_count += 1

    # Optional: clone badge definitions cleanly as unpublished draft badges if requested
    cloned_count = 0
    if clone_badges_from_cycle_id:
        src_badges = store.get_all_badges(cycle_id=clone_badges_from_cycle_id)
        for src_b in src_badges:
            cloned_b = Badge(
                id=f"{new_cycle.id}__{src_b.id}",
                code=src_b.code,
                title=src_b.title,
                category=src_b.category,
                description=src_b.description,
                learning_outcomes=list(src_b.learning_outcomes),
                learning_topics=list(src_b.learning_topics),
                prerequisites=[],
                project_requirements=src_b.project_requirements,
                is_published=False,
                is_allocated=False,
                target_band=src_b.target_band,
                power=src_b.power,
                capability=src_b.capability,
                skill=src_b.skill,
                prompt_json=src_b.prompt_json,
                workflow_status="ready_for_review",
                creator_id=created_by,
                assigned_reviewer_id="",
                assigned_cosmonaut_ids=[],
                default_timeline={},
                passing_percentage=src_b.passing_percentage,
                cycle_id=new_cycle.id,
            )
            store.save_badge(cloned_b)
            cloned_count += 1

    store.add_activity(
        event_type="cycle_created",
        actor_id=created_by,
        actor_name="Guardian",
        cosmonaut_id="",
        badge_id="",
        summary=f"Launched new 6-month cycle '{new_cycle.name}' ({new_cycle.start_date} → {new_cycle.end_date}) with {enrolled_count} members.",
        details=f"Cloned badges: {cloned_count}" if cloned_count else "Fresh curriculum slate.",
        cycle_id=new_cycle.id
    )
    msg = f"6-Month Cycle '{new_cycle.name}' launched ({new_cycle.start_date} → {new_cycle.end_date}) with {enrolled_count} enrolled members"
    if cloned_count:
        msg += f" and {cloned_count} cloned badge drafts"
    return True, msg + ".", new_cycle
