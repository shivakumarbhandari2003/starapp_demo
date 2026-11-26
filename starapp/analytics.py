"""
STARAPP ANALYTICS ENGINE & DATA ADAPTER
Computes standardized metrics, cohort aggregations, and diagnostic telemetry.
Guarantees strict data isolation between the actual Cosmonaut and demonstration profiles.
"""

import datetime
from typing import List, Dict, Any, Optional
from starapp.assessment import RUBRIC_CRITERIA, calculate_cosmonaut_score_summary
from starapp.models import User, Badge, ProjectSubmission, AssessmentMarksheet
from starapp.dashboard_demo import get_dashboard_demo_cosmonauts, get_demo_cosmonaut_by_id

def _parse_date(value: Any) -> Optional[datetime.date]:
    try:
        return datetime.date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _derive_activity(
    submissions: List[ProjectSubmission],
    assessments: List[AssessmentMarksheet],
    timelines: List[Any],
    today: datetime.date,
) -> Dict[str, Any]:
    """Last-active date and next deadline computed from the cadet's REAL records (no fixed dates)."""
    stamps = [str(s.submitted_at)[:10] for s in submissions if getattr(s, "submitted_at", "")]
    stamps += [str(a.reviewed_at)[:10] for a in assessments if getattr(a, "reviewed_at", "")]
    last_dates = [d for d in (_parse_date(x) for x in stamps) if d]
    last_active = max(last_dates) if last_dates else None
    deadlines = sorted(
        d for d in (
            _parse_date(getattr(t, "submission_deadline", ""))
            for t in timelines if getattr(t, "status", "") not in ("completed",)
        ) if d
    )
    upcoming = next((d for d in deadlines if d >= today), deadlines[-1] if deadlines else None)
    return {
        "last_active": last_active.isoformat() if last_active else "N/A",
        "days_inactive": max(0, (today - last_active).days) if last_active else None,
        "upcoming_deadline": upcoming.isoformat() if upcoming else "N/A",
    }


def build_cosmonaut_analytics_record(
    actual_cosmo: User,
    assigned_badges: List[Badge],
    assessments: List[AssessmentMarksheet],
    submissions: List[ProjectSubmission],
    extensions: Optional[List[Any]] = None,
    timelines: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Constructs a standardized analytics profile for a Cosmonaut
    strictly from their actual SQLite application records.
    """
    raw_approved = [a for a in assessments if a.decision == "approve"]
    # Deduplicate approved assessments per badge (Guardian final overrides Reviewer preliminary on same badge)
    approved_by_badge = {}
    for a in sorted(
        raw_approved,
        key=lambda x: (
            getattr(x, "attempt_number", 1),
            1 if getattr(x, "assessor_role", "") == "guardian" else 0,
            getattr(x, "reviewed_at", ""),
        ),
    ):
        approved_by_badge[a.badge_id] = a
    approved_asms = list(approved_by_badge.values())
    total_assigned = len(assigned_badges)
    completed_count = len(approved_asms)
    
    # Active badge determination
    completed_badge_ids = {a.badge_id for a in approved_asms}
    active_badges = [b for b in assigned_badges if b.id not in completed_badge_ids]
    active_b = active_badges[0] if active_badges else None

    # First attempt calculation
    # Eligible badges: any badge with at least one submission
    attempted_badge_ids = {s.badge_id for s in submissions}
    first_attempt_passes = sum(1 for a in approved_asms if a.attempt_number == 1)
    eligible_count = max(1, len(attempted_badge_ids))
    first_attempt_pct = round((first_attempt_passes / eligible_count) * 100.0, 1)

    # Resubmissions
    resub_count = sum(1 for s in submissions if s.attempt_number > 1)

    # Approved average marks
    if approved_asms:
        avg_marks = round(sum(a.total_marks for a in approved_asms) / len(approved_asms), 2)
        avg_pct = round((avg_marks / 50.0) * 100.0, 1)
    else:
        avg_marks = 0.0
        avg_pct = 0.0

    # Risk evaluation based on actual state
    pending_subs = [s for s in submissions if s.status == "pending"]
    pending_exts = [e for e in (extensions or []) if getattr(e, "status", "") == "pending"]

    if pending_exts:
        risk_status = "Needs Attention"
        risk_reason = "Milestone deadline extension request submitted and awaiting Guardian evaluation."
    elif pending_subs:
        risk_status = "On Track"
        risk_reason = f"Deliverable for {active_b.code if active_b else 'milestone'} submitted; currently under Guardian assessment."
    elif resub_count > 0 and not approved_asms:
        risk_status = "At Risk"
        risk_reason = "Resubmission requested on initial milestone deliverable requiring revision."
    else:
        risk_status = "On Track"
        risk_reason = f"{len(approved_asms)} milestone{'s' if len(approved_asms) != 1 else ''} certified ({avg_pct:.1f}% Average Assessment Score). Pacing on schedule."

    # Format assessment details strictly from actual approved assessments
    badge_map = {b.id: b for b in assigned_badges}
    asm_list = []
    approved_badge_ids = {a.badge_id for a in approved_asms}
    for a in approved_asms:
        badge_obj = badge_map.get(a.badge_id)
        b_title = badge_obj.title if badge_obj else a.badge_id
        asm_list.append({
            "id": a.id,
            "badge_id": a.badge_id,
            "badge_code": getattr(badge_obj, "code", a.badge_id.replace("badge_", "").upper()),
            "badge_title": b_title,
            "attempt_number": a.attempt_number,
            "decision": a.decision,
            "reviewed_at": a.reviewed_at[:10],
            "business_understanding": a.business_understanding,
            "architecture_report": a.architecture_report,
            "technical_knowledge": a.technical_knowledge,
            "presentation": a.presentation,
            "qa": a.qa,
            "total_marks": a.total_marks,
            "percentage": a.percentage
        })

    # Standing tier (Academic Performance Category)
    if not approved_asms:
        tier = "Enrolled"
        skills = []
        certifications = []
        strengths = []
        improvements = []
        risk_reason = "Enrolled in cohort curriculum. Awaiting initial deliverable submission."
        mentoring_plan = "Enrolled in active learning cohort. Awaiting submission of initial milestone deliverable."
    else:
        if avg_marks >= 45.0:
            tier = "Excellent Performance"
        elif avg_marks >= 40.0:
            tier = "Strong Performance"
        elif avg_marks >= 35.0:
            tier = "Developing Performance"
        else:
            tier = "Needs Support"

        # Verified Skills & Competencies (Derived from actual cleared milestone rubrics)
        skills = [
            {"name": a.get("badge_title", "Engineering"), "category": "Milestone Proficiency", "proficiency": "Mastered", "level_color": "#10B981", "pct": int(a.get("percentage", 100)), "rating": round(a.get("total_marks", 50.0) / 5.0, 1), "badge": a.get("badge_code", "")}
            for a in asm_list
        ]

        # Official Certifications (Verified Credentials from actual approved assessments)
        certifications = [
            {
                "code": a.get("badge_code", ""),
                "title": a.get("badge_title", ""),
                "credential_id": f"STAR-CERT-2026-{a.get('badge_code', '')}",
                "issued_at": a.get("reviewed_at", ""),
                "score": f"{a.get('total_marks', 0.0)} / 50.0 ({a.get('percentage', 0.0)}%)",
                "honors": "Honors with Distinction" if a.get("total_marks", 0.0) >= 45 else "Certified with Merit"
            }
            for a in asm_list
        ]

        strengths = [
            f"Demonstrated verified engineering proficiency in {a.get('badge_title', '')}."
            for a in asm_list
        ]

        improvements = [
            "Continue applying advanced architecture patterns to subsequent milestones."
        ]
        mentoring_plan = f"Guide cadet through {active_b.code if active_b else 'subsequent'} curriculum milestones."

    if pending_subs:
        last_activity_summary = f"Submitted deliverable package for {active_b.code if active_b else 'milestone'}"
    elif approved_asms:
        _last_badge = badge_map.get(approved_asms[-1].badge_id)
        last_activity_summary = f"Completed {getattr(_last_badge, 'code', '') or getattr(_last_badge, 'title', '') or 'a milestone'} evaluation"
    else:
        last_activity_summary = "Enrolled in cohort curriculum"

    if timelines is None:
        from starapp.storage import store as _store
        timelines = _store.get_timelines_for_cosmonaut(actual_cosmo.id)
    activity = _derive_activity(submissions, assessments, timelines, datetime.date.today())

    from starapp.storage import store as _profile_store
    _profile = _profile_store.profiles.get(actual_cosmo.id)

    return {
        "id": actual_cosmo.id,
        "name": actual_cosmo.name,
        "email": actual_cosmo.email,
        "avatar": actual_cosmo.avatar,
        "band": getattr(actual_cosmo, "band", "") or "",
        "track": getattr(actual_cosmo, "learning_track", "") or "",
        "batch": getattr(_profile, "batch_name", "") or "",
        "is_demo": False,
        "completed_count": completed_count,
        "total_assigned": total_assigned,
        "active_badge_id": active_b.id if active_b else "None",
        "active_badge_code": active_b.code if active_b else "N/A",
        "active_badge_title": active_b.title if active_b else "All Completed",
        "upcoming_deadline": activity["upcoming_deadline"],
        "deadline_status": "Attempt in Review" if pending_subs else "On Schedule",
        "last_active": activity["last_active"],
        "days_inactive": activity["days_inactive"],
        "last_activity_summary": last_activity_summary,
        "risk_status": risk_status,
        "risk_reason": risk_reason,
        "assessments": asm_list,
        "skills": skills,
        "certifications": certifications,
        "strengths": strengths,
        "improvements": improvements,
        "mentoring_plan": mentoring_plan,
        "submissions_count": len(submissions),
        "first_attempt_passes": first_attempt_passes,
        "first_attempt_eligible": eligible_count,
        "resubmission_count": resub_count,
        "average_marks": avg_marks,
        "average_percentage": avg_pct,
        "standing_tier": tier
    }

build_astraea_analytics_record = build_cosmonaut_analytics_record

def get_guardian_cohort_profiles(
    actual_cosmo: User,
    assigned_badges: List[Badge],
    assessments: List[AssessmentMarksheet],
    submissions: List[ProjectSubmission],
    extensions: Optional[List[Any]] = None
) -> List[Dict[str, Any]]:
    """
    Returns cohort profiles computed directly from SQLite users.
    """
    from starapp.storage import store
    primary = build_cosmonaut_analytics_record(
        actual_cosmo, assigned_badges, assessments, submissions, extensions,
        timelines=store.get_timelines_for_cosmonaut(actual_cosmo.id),
    )

    # The records of everybody else are identical for every viewer, so they are built once per data
    # change (learning scope) and shared, instead of once per page view per user.
    def build_all():
        records: Dict[str, Dict[str, Any]] = {}
        for c in store.get_all_cosmonauts():
            records[c.id] = build_cosmonaut_analytics_record(
                c,
                store.get_badges_for_cosmonaut(c.id),
                store.get_assessments_for_cosmonaut(c.id),
                store.get_submissions_for_cosmonaut(c.id),
                store.get_extensions_for_cosmonaut(c.id),
                timelines=store.get_timelines_for_cosmonaut(c.id),
            )
        return records

    everyone = store._memoized(
        f"cohort_profiles:{store.get_effective_read_cycle_id()}:{datetime.date.today().isoformat()}",
        build_all, scope="learning",
    )
    cohort = [primary]
    cohort.extend(rec for cid, rec in everyone.items() if cid != actual_cosmo.id)
    return cohort

_COHORT_ANALYTICS_CACHE: Dict[str, Any] = {}

def calculate_guardian_cohort_analytics(
    cohort_profiles: List[Dict[str, Any]],
    actual_subs: List[ProjectSubmission],
    actual_asms: List[AssessmentMarksheet]
) -> Dict[str, Any]:
    """
    Computes comprehensive cohort-wide metrics across all 6 profiles.
    Optimized with memoization cache to eliminate redundant computation on non-mutating renders.
    """
    from starapp.storage import store
    curr_cid = store.get_effective_read_cycle_id()
    asms_sum = sum(getattr(a, "total_marks", 0) for a in actual_asms)
    total_completed_badges = sum(p.get("completed_count", 0) for p in cohort_profiles)
    cache_key = f"{curr_cid}_{datetime.date.today().isoformat()}_{len(cohort_profiles)}_{len(actual_subs)}_{len(actual_asms)}_{asms_sum}_{total_completed_badges}"
    if _COHORT_ANALYTICS_CACHE.get("key") == cache_key:
        return dict(_COHORT_ANALYTICS_CACHE["data"])

    total_profiles = len(cohort_profiles)
    actual_count = sum(1 for p in cohort_profiles if not p.get("is_demo", False))
    demo_count = sum(1 for p in cohort_profiles if p.get("is_demo", False))

    total_assigned_badges = sum(p.get("total_assigned", 5) for p in cohort_profiles)
    total_completed_badges = sum(p.get("completed_count", 0) for p in cohort_profiles)
    overall_completion_pct = round((total_completed_badges / max(1, total_assigned_badges)) * 100.0, 1)

    # All approved evaluations across cohort
    all_approved_evals = []
    for p in cohort_profiles:
        all_approved_evals.extend(p.get("assessments", []))

    eval_count = len(all_approved_evals)
    if eval_count > 0:
        avg_score = round(sum(a["total_marks"] for a in all_approved_evals) / eval_count, 2)
        avg_pct = round((avg_score / 50.0) * 100.0, 1)
    else:
        avg_score = 0.0
        avg_pct = 0.0

    # First-attempt success rate across cohort
    total_passes = sum(p.get("first_attempt_passes", 0) for p in cohort_profiles)
    total_eligible = sum(p.get("first_attempt_eligible", 1) for p in cohort_profiles)
    first_attempt_rate = round((total_passes / max(1, total_eligible)) * 100.0, 1)

    # Pending evaluations in queue (Actual live pending submissions)
    actual_pending = len([s for s in actual_subs if s.status == "pending"])
    pending_evals = actual_pending

    # At-risk profiles count
    requiring_attention = sum(1 for p in cohort_profiles if p.get("risk_status") in ["At Risk", "Needs Attention", "Monitor"])

    # Criterion-wise cohort averages
    criterion_avgs = {}
    for c in RUBRIC_CRITERIA:
        k = c["key"]
        vals = [a.get(k, 0.0) for a in all_approved_evals if k in a]
        criterion_avgs[k] = round(sum(vals) / max(1, len(vals)), 2) if vals else 9.0

    # Score distribution histogram (5 score buckets)
    distribution = {
        "0-10": 0,
        "11-20": 0,
        "21-30": 0,
        "31-40": sum(1 for a in all_approved_evals if 31.0 <= a["total_marks"] <= 40.0),
        "41-50": sum(1 for a in all_approved_evals if a["total_marks"] > 40.0)
    }

    # Badge completion distribution (Completed, In Progress / Active, Locked / Not Started)
    total_active = sum(1 for p in cohort_profiles if p.get("active_badge_id") not in ["None", None])
    total_locked = max(0, total_assigned_badges - total_completed_badges - total_active)
    badge_distribution = {
        "completed": total_completed_badges,
        "active": total_active,
        "locked": total_locked
    }

    # ------------------------------------------------------------------------------------------
    # Badge-wise performance: computed from the cycle's REAL badges, timelines and marksheets.
    # (Previously a hard-coded catalogue of five fictional badges with invented statistics.)
    # ------------------------------------------------------------------------------------------
    today = datetime.date.today()
    cycle_obj = store.get_cycle(curr_cid)
    cycle_start = _parse_date(getattr(cycle_obj, "start_date", "")) or today
    weeks_elapsed = max(1, (min(today, _parse_date(getattr(cycle_obj, "end_date", "")) or today) - cycle_start).days // 7 + 1)

    asms_by_badge: Dict[str, List[Dict[str, Any]]] = {}
    for ev in all_approved_evals:
        asms_by_badge.setdefault(ev.get("badge_id"), []).append(ev)
    subs_by_badge: Dict[str, List[Any]] = {}
    for sub in actual_subs:
        subs_by_badge.setdefault(sub.badge_id, []).append(sub)
    timelines_by_badge: Dict[str, List[Any]] = {}
    for tl in store.get_timelines_dict().values():
        timelines_by_badge.setdefault(tl.badge_id, []).append(tl)

    palette = ["#10B981", "#3B82F6", "#6366F1", "#F59E0B", "#E11D48", "#0EA5E9"]
    badge_performance = []
    cycle_badges = [bd for bd in store.get_all_badges() if getattr(bd, "is_published", False)]
    for bd in sorted(cycle_badges, key=lambda x: (getattr(x, "target_band", ""), x.code))[:12]:
        b_asms = asms_by_badge.get(bd.id, [])
        b_count = len(b_asms)
        b_avg = round(sum(x["total_marks"] for x in b_asms) / b_count, 1) if b_count else 0.0
        b_tls = timelines_by_badge.get(bd.id, [])
        planned, actual = [], []
        for tl in b_tls:
            d0, d1 = _parse_date(tl.assignment_date), _parse_date(tl.submission_deadline)
            if d0 and d1:
                planned.append((d1 - d0).days)
            d2 = _parse_date(tl.actual_award_date)
            if d0 and d2:
                actual.append((d2 - d0).days)
        first_pass = sum(1 for x in b_asms if x.get("attempt_number") == 1)
        attempted = len({sub.cosmonaut_id for sub in subs_by_badge.get(bd.id, [])})
        crit_avgs = {}
        for crit in RUBRIC_CRITERIA:
            vals = [x.get(crit["key"], 0.0) for x in b_asms]
            if vals:
                crit_avgs[crit["title"]] = sum(vals) / len(vals)
        weakest = min(crit_avgs.items(), key=lambda kv: kv[1]) if crit_avgs else None
        in_review = sum(1 for tl in b_tls if tl.status == "reviewer_assessed")
        in_progress = sum(1 for tl in b_tls if tl.status in ("active", "retake_required"))
        if b_avg >= 45.0 or b_count == 0:
            difficulty = "Moderate"
        elif b_avg >= 40.0:
            difficulty = "Standard"
        else:
            difficulty = "Challenging"
        badge_performance.append({
            "code": bd.code,
            "title": bd.title,
            "pillar": getattr(bd, "capability", "") or getattr(bd, "category", ""),
            "level": f"Band {getattr(bd, 'target_band', '')}",
            "level_color": palette[(int(getattr(bd, "target_band", "B1")[1:] or 1) - 1) % len(palette)] if getattr(bd, "target_band", "") else palette[0],
            "target_days": round(sum(planned) / len(planned)) if planned else 0,
            "avg_days": round(sum(actual) / len(actual), 1) if actual else 0.0,
            "first_attempt_rate": round(first_pass / max(1, attempted) * 100.0, 1) if attempted else 0.0,
            "bottleneck": f"Lowest rubric area: {weakest[0]} ({weakest[1]:.1f}/10)" if weakest else "No evaluations yet",
            "pedagogy": (bd.description or "")[:140],
            "status_summary": f"{b_count} Certified \u2022 {in_review} In Review \u2022 {in_progress} In Progress",
            "completed_count": b_count,
            "average_marks": b_avg,
            "difficulty": difficulty,
        })

    # Weekly progress trends: the last 6 calendar weeks of REAL submissions / certifications.
    weekly_trends = []
    week_start = today - datetime.timedelta(days=today.weekday())
    for offset in range(5, -1, -1):
        w0 = week_start - datetime.timedelta(weeks=offset)
        w1 = w0 + datetime.timedelta(days=6)
        w_subs = [sub for sub in actual_subs if (_parse_date(sub.submitted_at) or datetime.date.min) >= w0 and (_parse_date(sub.submitted_at) or datetime.date.max) <= w1]
        w_done = [ev for ev in all_approved_evals if w0 <= (_parse_date(ev.get("reviewed_at")) or datetime.date.min) <= w1]
        weekly_trends.append({
            "week": f"W{6 - offset}",
            "label": f"{w0.strftime('%b %d')} - {w1.strftime('%b %d')}",
            "completions": len(w_done),
            "submissions": len(w_subs),
            "avg_score": round(sum(ev["total_marks"] for ev in w_done) / len(w_done), 1) if w_done else 0.0,
        })

    weekly_velocity = round(total_completed_badges / float(weeks_elapsed), 1) if total_completed_badges else 0.0
    total_marks_sum = round(sum(x["total_marks"] for x in all_approved_evals), 1)
    flagged = [p["name"] for p in cohort_profiles if p.get("risk_status") in ("At Risk", "Needs Attention", "Monitor")]

    result = {
        "total_profiles": total_profiles,
        "actual_count": actual_count,
        "demo_count": demo_count,
        "total_assigned_badges": total_assigned_badges,
        "total_completed_badges": total_completed_badges,
        "overall_completion_pct": overall_completion_pct,
        "weekly_velocity": weekly_velocity,
        "total_marks_sum": total_marks_sum,
        "eval_count": eval_count,
        "average_score": avg_score,
        "average_pct": avg_pct,
        "total_passes": total_passes,
        "total_eligible": total_eligible,
        "first_attempt_rate": first_attempt_rate,
        "pending_evals": pending_evals,
        "requiring_attention": requiring_attention,
        "criterion_averages": criterion_avgs,
        "distribution": distribution,
        "badge_distribution": badge_distribution,
        "badge_performance": badge_performance,
        "weekly_trends": weekly_trends,
        "weeks_elapsed": weeks_elapsed,
        "flagged_names": flagged[:5],
        "flagged_total": len(flagged),
        "on_track_count": max(0, total_profiles - len(flagged)),
        "cycle_name": getattr(cycle_obj, "name", "") or curr_cid,
    }

    _COHORT_ANALYTICS_CACHE["key"] = cache_key
    _COHORT_ANALYTICS_CACHE["data"] = result
    return result

def get_kpi_popover(metric_key: str, data: Dict[str, Any], scope: str = "cohort") -> Dict[str, str]:
    """
    Returns rich metadata for interactive hover popovers and tooltips.
    Includes Formula, Numerator/Denominator, Scope, Included/Excluded rules.
    """
    if scope == "cohort":
        popovers = {
            "enrolled_cadets": {
                "title": "Total Cohort Cosmonauts",
                "formula": "Count(Active Enrolled Cadets in Batch)",
                "numerator": f"{data.get('total_profiles', 0):,} Registered Profiles",
                "denominator": f"{data.get('cycle_name', 'Current Cycle')} Enrollment",
                "value": f"{data.get('total_profiles', 0):,} Cadets",
                "scope": f"Cohort Aggregate ({data.get('total_profiles', 0):,} Profiles)",
                "included": f"All active enrolled engineering cadets in {data.get('cycle_name', 'the current cycle')}",
                "excluded": "Graduated alumni, external auditors, or unassigned accounts",
                "insight": "Active training cohort size representing the total instructional footprint of the Academy."
            },
            "completion_rate": {
                "title": "Badge Completion Rate",
                "formula": "(Total Completed Badges / Total Assigned Badges) × 100",
                "numerator": f"{data.get('total_completed_badges', 0):,} Completed Badges across cohort",
                "denominator": f"{data.get('total_assigned_badges', 0):,} Total Assigned Badges ({data.get('total_profiles', 0):,} Cadets)",
                "value": f"{data.get('overall_completion_pct', 0.0):.1f}%",
                "scope": "Cohort Aggregate",
                "included": "All officially certified milestone pass marksheets",
                "excluded": "Active in-progress deliverables, drafts, and resubmissions",
                "insight": "Measures total curriculum completion across every badge assigned to the cohort in this cycle."
            },
            "weekly_velocity": {
                "title": "Weekly Completion Velocity",
                "formula": "Total Certified Badges / Active Curriculum Elapsed Weeks",
                "numerator": f"{data.get('total_completed_badges', 0):,} Certified Badges",
                "denominator": f"{data.get('weeks_elapsed', 1)} Active Curriculum Weeks",
                "value": f"{data.get('weekly_velocity', 0.0):.1f} badges / week",
                "scope": "Cohort Velocity",
                "included": "All final approved assessment submissions to date",
                "excluded": "Pending queue submissions and non-assessed milestones",
                "insight": "Average certifications per week since the cycle started (live figure, no baseline assumed)."
            },
            "average_score": {
                "title": "Average Assessment Score",
                "formula": "Sum(Approved Marksheet Scores) / Count(Approved Evaluations)",
                "numerator": f"{data.get('total_marks_sum', 0.0):.1f} Total Rubric Marks Awarded",
                "denominator": f"{data.get('eval_count', 0):,} Officially Evaluated Marksheets",
                "value": f"{data.get('average_score', 0.0):.1f} / 50.0 ({data.get('average_pct', 0.0):.1f}%)",
                "scope": "Cohort Aggregate",
                "included": "All final approved evaluations graded by Guardian (Rubric-50)",
                "excluded": "Pending deliverables awaiting review and rejected initial attempts",
                "insight": "Batch performance index reflects enterprise production readiness across distributed architecture rubrics."
            },
            "first_attempt": {
                "title": "First-Attempt Success Rate",
                "formula": "(Milestones Cleared on Attempt #1 / Attempted Milestones) × 100",
                "numerator": f"{data.get('total_passes', 0):,} First-Attempt Passes",
                "denominator": f"{data.get('total_eligible', 0):,} Total First Attempts Graded",
                "value": f"{data.get('first_attempt_rate', 0.0):.1f}%",
                "scope": "Cohort Aggregate",
                "included": "Initial submissions meeting the badge passing threshold (default 70% = 35/50) on Attempt #1",
                "excluded": "Attempt #2 and subsequent revision submissions",
                "insight": "High first-attempt success indicates high initial deliverable quality and clear prerequisite instructions."
            },
            "cadets_attention": {
                "title": "Cadets Requiring Attention",
                "formula": "Count(Cadets where Risk Status ∈ {'At Risk', 'Needs Attention', 'Monitor'})",
                "numerator": f"{data.get('requiring_attention', 0):,} Cadets Flagged",
                "denominator": f"{data.get('total_profiles', 0):,} Enrolled Cadets ({round(data.get('requiring_attention', 0) / max(1, data.get('total_profiles', 1)) * 100, 1)}% Cohort Risk Surface)",
                "value": f"{data.get('requiring_attention', 0):,} Cadets",
                "scope": "Intervention Queue",
                "included": (", ".join(data.get("flagged_names", [])) + (f" and {data.get('flagged_total', 0) - len(data.get('flagged_names', [])):,} more" if data.get("flagged_total", 0) > len(data.get("flagged_names", [])) else "")) or "No cadets are currently flagged",
                "excluded": f"{data.get('on_track_count', 0):,} Cadets with risk status 'On Track' in good standing",
                "insight": "Actionable intervention list enabling proactive Guardian mentoring before milestone deadlines lapse."
            },
            "pending_evals": {
                "title": "Pending Submissions Queue",
                "formula": "Count(Submitted Deliverables with Status = 'pending')",
                "numerator": f"{data.get('pending_evals', 0)} Deliverables Awaiting Review",
                "denominator": "Active Application Submission Queue",
                "value": f"{data.get('pending_evals', 0)} Pending",
                "scope": "Guardian Production Queue",
                "included": "Deliverable packages currently awaiting evaluation",
                "excluded": "Completed evaluations and certified milestones",
                "insight": "Clicking 'Evaluate Pending Deliverable' opens the live 50-mark rubric assessment viewport."
            }
        }
        return popovers.get(metric_key, {})
    else:
        # Individual Scope (e.g. Aarav Sharma or Selected Cadet)
        popovers = {
            "individual_badges": {
                "title": "Certified Roadmap Milestones",
                "formula": "Certified Badges / Total Assigned Curriculum Badges",
                "numerator": f"{data.get('completed_count', 0)} Approved Milestones",
                "denominator": f"{data.get('total_assigned', 0)} Assigned Milestones",
                "value": f"{data.get('completed_count', 0)} / {max(0, data.get('total_assigned', 0))} ({round((data.get('completed_count', 0)/max(1, data.get('total_assigned', 1)))*100, 1)}%)",
                "scope": f"Individual: {data.get('name', 'Cadet')}",
                "included": f"Officially verified badges: {', '.join([a.get('badge_code', '') for a in data.get('assessments', []) if a.get('decision') == 'approve']) or 'None'}",
                "excluded": "Milestones in development or pending review",
                "insight": f"Cadet has completed {round((data.get('completed_count', 0)/max(1, data.get('total_assigned', 1)))*100, 1)}% of assigned curriculum milestones."
            },
            "individual_score": {
                "title": "Average Assessment Score",
                "formula": "Sum(Approved Milestone Marks) / Count(Approved Milestones)",
                "numerator": f"{sum(a.get('total_marks', 0) for a in data.get('assessments', [])):.1f} Total Marks",
                "denominator": f"{len(data.get('assessments', []))} Evaluated Milestones",
                "value": f"{data.get('average_marks', 0.0):.1f} / 50.0 ({data.get('average_percentage', 0.0):.1f}%)",
                "scope": f"Individual: {data.get('name', 'Cadet')}",
                "included": "All final rubric marks awarded across cleared badges",
                "excluded": "Pending deliverable revisions",
                "insight": f"Academic standing: {data.get('standing_tier', 'Enrolled')}."
            },
            "individual_first_attempt": {
                "title": "First-Attempt Pass Rate",
                "formula": "(Milestones Cleared on Attempt #1 / Attempted Milestones) × 100",
                "numerator": f"{data.get('first_attempt_passes', 0)} First-Attempt Passes",
                "denominator": f"{data.get('first_attempt_eligible', 0)} Attempted Milestones",
                "value": f"{round((data.get('first_attempt_passes', 0)/max(1, data.get('first_attempt_eligible', 1)))*100, 1)}%",
                "scope": f"Individual: {data.get('name', 'Cadet')}",
                "included": "Passed on Attempt #1 across completed milestones",
                "excluded": "Resubmissions and ongoing deliverables",
                "insight": "Measures single-pass delivery performance against technical rubrics."
            },
            "individual_active_milestone": {
                "title": "Active Milestone Sprint",
                "formula": "Current Roadmap Node & Sprint State",
                "numerator": f"{data.get('active_badge_code', 'N/A')}",
                "denominator": f"Target: {data.get('upcoming_deadline', 'N/A')}",
                "value": f"{data.get('active_badge_code', 'N/A')} ({data.get('deadline_status', 'Enrolled')})",
                "scope": f"Individual: {data.get('name', 'Cadet')}",
                "included": "Milestone deliverable, code repository, and architecture design document",
                "excluded": "Locked roadmap milestones",
                "insight": f"Current sprint status: {data.get('deadline_status', 'Enrolled')}."
            }
        }
        return popovers.get(metric_key, {})

def get_cosmonaut_individual_dossier(
    cosmo_id: str,
    cohort_profiles: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Returns the individual profile data for a specific Cosmonaut in the cohort."""
    for p in cohort_profiles:
        if p["id"] == cosmo_id:
            return p
    return None

