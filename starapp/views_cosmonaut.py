"""
STARAPP COSMONAUT PORTAL VIEWS
Implements the 10 personalized learning workspaces for learners.
"""

import json
from typing import List, Dict, Any, Optional
from starapp.pagination import page_slice
from starapp.models import (
    User, CosmonautProfile, Badge, BadgeTimeline, ProjectSubmission,
    AssessmentMarksheet, LearningMaterial, DeadlineExtension,
    Announcement, ActivityEvent
)
from starapp.views_common import (
    humanize_internal_ids,
    get_icon,
    escape, render_liquid_card, render_metal_button, render_liquid_button,
    render_status_pill, render_standard_marksheet, render_9point_timeline,
    render_learning_materials_view, render_back_button, render_taxonomy_hierarchy_tree
)
from starapp.roadmap import generate_roadmap_graph
from starapp.assessment import RUBRIC_CRITERIA
from starapp.analytics import build_astraea_analytics_record, get_guardian_cohort_profiles, get_kpi_popover

def render_cosmo_metric_info_popover(key: str, data: Dict[str, Any], scope: str = "individual", align: str = "") -> str:
    """Renders interactive info trigger (i) with calculation details for personal learner metrics."""
    info = get_kpi_popover(key, data, scope)
    if not info:
        return ""
    align_cls = f"pop-{align}" if align else ""
    return f"""
    <span class="has-glass-tooltip">
        <button type="button" class="metric-info-trigger" aria-label="Metric details for {escape(info.get('title', ''))}" tabindex="0">i</button>
        <div class="glass-tooltip-popover {align_cls}">
            <div class="popover-header">
                <span class="popover-title">{escape(info.get('title', ''))}</span>
                <span class="popover-scope-badge">{escape(info.get('scope', 'Personal'))}</span>
            </div>
            <div class="popover-formula-box">{escape(info.get('formula', ''))}</div>
            <div class="popover-data-row">
                <span class="popover-data-label">Numerator:</span>
                <span class="popover-data-val">{escape(info.get('numerator', ''))}</span>
            </div>
            <div class="popover-data-row">
                <span class="popover-data-label">Denominator:</span>
                <span class="popover-data-val">{escape(info.get('denominator', ''))}</span>
            </div>
            <div class="popover-data-row" style="border-top:1px solid rgba(157,183,213,0.25); padding-top:4px; margin-top:4px;">
                <span class="popover-data-label" style="color:var(--pure-ice);">Current Value:</span>
                <span class="popover-data-val" style="color:#047857;">{escape(info.get('value', ''))}</span>
            </div>
            <div class="popover-criteria-section">
                <div><strong>Included:</strong> {escape(info.get('included', ''))}</div>
                <div style="margin-top:3px;"><strong>Excluded:</strong> {escape(info.get('excluded', ''))}</div>
                <div style="margin-top:4px; color:var(--pure-ice); font-style:italic;">{escape(info.get('insight', ''))}</div>
            </div>
        </div>
    </span>
    """

# ==============================================================================
# COSMONAUT SIDEBAR
# ==============================================================================

def render_cosmonaut_sidebar(
    active_view: str,
    current_user: User,
    unread_announcements_count: int,
    pending_requests_count: int = 0,
    selected_cycle: Optional[Any] = None
) -> str:
    from starapp.storage import store
    from starapp.views_common import render_sidebar_cycle_pill

    # If pending_requests_count was not passed, compute it dynamically
    if pending_requests_count == 0 and hasattr(store, "get_badge_review_requests_for_user"):
        try:
            reqs = store.get_badge_review_requests_for_user(current_user.id)
            pending_requests_count = len([r for r in reqs if r.get("workflow_status") == "pending_review" or r.get("assignment_status") == "pending"])
            if hasattr(store, "get_mapping_requests"):
                pending_requests_count += len([m for m in store.get_mapping_requests() if m.get("reviewer_id") == current_user.id and m.get("status") == "pending"])
        except Exception:
            pending_requests_count = 0

    if selected_cycle is None and hasattr(store, "get_cycle"):
        try:
            selected_cycle = store.get_cycle(store.get_active_cycle_id())
        except Exception:
            selected_cycle = None

    nav_items = [
        {
            "id": "c_choose_cycle",
            "label": "Choose Cycle",
            "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="M8 14h.01M12 14h.01M16 14h.01"/></svg>',
            "badge": 0
        }
    ]

    # Eligible reviewers (bands B2 through B6 or badge_reviewer role) receive Badge Reviews, Review Requests & Cadet Assessments
    u_band = getattr(current_user, "band", "")
    is_eligible = (u_band in ("B2", "B3", "B4", "B5", "B6")) or current_user.has_role("badge_reviewer") or (pending_requests_count > 0)
    if is_eligible:
        pending_asms_count = 0
        try:
            # Indexed lookup of this reviewer's cadets (was: every submission x get_timeline x get_band_mappings)
            cadet_subs = store.get_reviewer_submissions(current_user.id)
            pending_asms_count = len([s for s in cadet_subs if s.status in ("pending", "submitted")])
        except Exception:
            pending_asms_count = 0

        nav_items.extend([
            {
                "id": "c_badge_reviews",
                "label": "Badge Reviews",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>',
                "badge": 0
            },
            {
                "id": "c_requests",
                "label": "Review Requests",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>',
                "badge": pending_requests_count
            },
            {
                "id": "c_assessments",
                "label": "Cadet Assessments",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/><path d="m9 14 2 2 4-4"/></svg>',
                "badge": pending_asms_count
            }
        ])

    # Exact requested Cosmonaut sidebar items (Learning Roadmap & Study Materials omitted from sidebar; views/routes kept in code)
    nav_items.extend([
        {"id": "c_submission", "label": "Badges", "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>', "badge": 0},
        {"id": "c_results", "label": "Assessment Marksheet", "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>', "badge": 0},
        {"id": "c_profile", "label": "Profile", "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>', "badge": 0},
        {"id": "c_extensions", "label": "Deadline Extension", "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', "badge": 0},
        {"id": "c_cycles", "label": "Past Cycle & Performance", "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>', "badge": 0}
    ])

    links_html = []
    for item in nav_items:
        is_active = (
            (item["id"] == active_view)
            or (item["id"] == "c_assessments" and active_view == "c_assessment_detail")
            or (item["id"] == "c_submission" and active_view == "c_badge_detail")
        )
        cls = "nav-link active" if is_active else "nav-link"
        badge_html = f'<span class="nav-badge" data-badge-for="{item["id"]}">{item["badge"]}</span>' if item["badge"] > 0 else ""
        links_html.append(f"""
        <li class="nav-item">
            <a class="{cls}" data-nav-id="{item["id"]}" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', '{item["id"]}')">
                {item["icon"]}
                <span>{item["label"]}</span>
                {badge_html}
            </a>
        </li>
        """)

    cycle_pill_html = render_sidebar_cycle_pill(selected_cycle, "nav_cosmonaut", "c_choose_cycle")

    return f"""
    <aside id="starapp-shell-sidebar" class="app-sidebar" data-portal-role="cosmonaut" data-user-id="{escape(current_user.id)}">
        <div class="sidebar-header">
            <div class="brand-text-wrap">
                <div class="brand-title"><span class="brand-initial">S</span><span class="brand-rest">TARAPP</span></div>
                <div class="brand-subtitle">COSMONAUT PORTAL</div>
            </div>
            <button type="button" class="sidebar-collapse-btn" style="display:none;" onclick="window.StarAppBridge.toggleSidebar()" aria-hidden="true"></button>
        </div>

        <div class="role-badge-pill">
            <span class="role-badge-label">Learner</span>
            <span class="role-badge-val">Band {escape(getattr(current_user, 'band', 'B1'))}</span>
        </div>

        {cycle_pill_html}

        <ul class="sidebar-nav">
            {"".join(links_html)}
        </ul>

        <div class="sidebar-footer">
            <div class="lg-sidebar-profile">
                <div class="lg-sidebar-profile-meta" style="cursor:pointer;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_profile')">
                    <div class="user-name">{escape(current_user.name)}</div>
                    <div class="user-role-text">Cosmonaut Profile</div>
                </div>
                <button type="button" class="lg-sidebar-signout-btn" onclick="window.StarAppBridge.dispatchAction('logout', '{{}}')" title="Sign Out">
                    Sign Out
                </button>
            </div>
        </div>
    </aside>
    """

# ==============================================================================
# 6.1 COSMONAUT DASHBOARD
# ==============================================================================

def render_cosmonaut_dashboard(
    current_user: User,
    profile: CosmonautProfile,
    assigned_badges: List[Badge],
    assessments: List[AssessmentMarksheet],
    leaderboard: Optional[List[Dict[str, Any]]] = None,
    score_summary: Optional[Dict[str, Any]] = None,
    upcoming_deadlines: Optional[List[Dict[str, str]]] = None,
    recent_announcements: Optional[List[Announcement]] = None,
    submissions: Optional[List[ProjectSubmission]] = None,
    extensions: Optional[List[Any]] = None,
    cohort_profiles: Optional[List[Dict[str, Any]]] = None
) -> str:
    from starapp.storage import store

    # 1. Executive Telemetry Calculations from actual records
    cadet_subs = submissions if submissions is not None else store.get_submissions_for_cosmonaut(current_user.id)
    cadet_exts = extensions if extensions is not None else store.get_extensions_for_cosmonaut(current_user.id)
    cadet_anns = recent_announcements if recent_announcements is not None else store.get_announcements_for_cosmonaut(current_user.id)[:3]

    # Standardized analytics profile for Aarav Sharma
    astraea_rec = build_astraea_analytics_record(current_user, assigned_badges, assessments, cadet_subs, cadet_exts)

    # Resolve cohort profiles for cohort-wide comparative metrics & leaderboard
    if cohort_profiles is None:
        cohort_profiles = get_guardian_cohort_profiles(current_user, assigned_badges, assessments, cadet_subs, cadet_exts)

    from starapp.storage import store as _store_ref
    _mentor_user = _store_ref.get_user_by_id(getattr(profile, "assigned_guardian_id", "") or "")
    _mentor_name = _mentor_user.name if _mentor_user else ""

    comp_count = astraea_rec.get("completed_count", 0)
    total_assigned = astraea_rec.get("total_assigned", 5)
    progress_pct = round((comp_count / max(1, total_assigned)) * 100.0, 1)

    avg_marks = astraea_rec.get("average_marks", 0.0)
    avg_pct = astraea_rec.get("average_percentage", 0.0)
    first_pass_rate = round((astraea_rec.get("first_attempt_passes", 0) / max(1, astraea_rec.get("first_attempt_eligible", 1))) * 100.0, 1)
    tier = astraea_rec.get("standing_tier", "Excellent Performance")
    asms = astraea_rec.get("assessments", [])
    r_status = astraea_rec.get("risk_status", "On Track")
    last_act = astraea_rec.get("last_active", "N/A")
    last_act_desc = astraea_rec.get("last_activity_summary", "")

    # Cohort Leaderboard ranking calculation
    sorted_cohort = sorted(cohort_profiles, key=lambda x: (x.get("average_marks", 0.0), x.get("completed_count", 0)), reverse=True)
    rank = 1
    total_cohort = len(sorted_cohort) if sorted_cohort else 6
    for idx, cp in enumerate(sorted_cohort, start=1):
        if cp.get("id") == current_user.id:
            rank = idx
            break

    if rank == 1:
        rank_medal = '<span style="background:#FEF3C7; color:#B45309; border:1px solid #FCD34D; font-weight:800; padding:4px 10px; border-radius:999px; font-size:11.5px; display:inline-flex; align-items:center; gap:4px;">&#129351; Rank #1 &bull; Batch Top Standing</span>'
    elif rank == 2:
        rank_medal = '<span style="background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; font-weight:800; padding:4px 10px; border-radius:999px; font-size:11.5px; display:inline-flex; align-items:center; gap:4px;">&#129352; Rank #2 &bull; High Honors</span>'
    elif rank == 3:
        rank_medal = '<span style="background:#FFEDD5; color:#C2410C; border:1px solid #FDBA74; font-weight:800; padding:4px 10px; border-radius:999px; font-size:11.5px; display:inline-flex; align-items:center; gap:4px;">&#129353; Rank #3 &bull; Honors</span>'
    else:
        rank_medal = f'<span style="background:rgba(23,52,92,0.08); color:var(--deep-frozen-midnight); border:1px solid var(--icy-steel); font-weight:800; padding:4px 10px; border-radius:999px; font-size:11.5px; display:inline-flex; align-items:center; gap:4px;">Rank #{rank} of {total_cohort}</span>'

    # Risk Status Pill
    if r_status == "On Track":
        r_pill = '<span style="font-size:11.5px; font-weight:800; color:#047857; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); padding:4px 12px; border-radius:999px; display:inline-flex; align-items:center; gap:5px;">&#10003; On Track</span>'
    elif r_status == "Monitor":
        r_pill = '<span style="font-size:11.5px; font-weight:800; color:#1D4ED8; background:rgba(59,130,246,0.12); border:1px solid rgba(59,130,246,0.3); padding:4px 12px; border-radius:999px; display:inline-flex; align-items:center; gap:5px;">&#9203; Monitor</span>'
    elif r_status == "Needs Attention":
        r_pill = '<span style="font-size:11.5px; font-weight:800; color:#B45309; background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); padding:4px 12px; border-radius:999px; display:inline-flex; align-items:center; gap:5px;">&#9888; Needs Attention</span>'
    else:
        r_pill = '<span style="font-size:11.5px; font-weight:800; color:#B91C1C; background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.3); padding:4px 12px; border-radius:999px; display:inline-flex; align-items:center; gap:5px;">&#10005; At Risk</span>'

    # Active milestone identification
    approved_badge_ids = {a.badge_id for a in assessments if a.decision == "approve"}
    active_badges = [b for b in assigned_badges if b.id not in approved_badge_ids]
    active_b = active_badges[0] if active_badges else None

    # Next step recommendation logic
    pending_sub = next((s for s in cadet_subs if s.badge_id == (active_b.id if active_b else "") and s.status == "pending"), None)
    latest_sub = next((s for s in sorted(cadet_subs, key=lambda x: x.attempt_number, reverse=True) if s.badge_id == (active_b.id if active_b else "")), None)

    if pending_sub:
        next_action_title = f"{active_b.code if active_b else 'Milestone'} Deliverable (Attempt #{pending_sub.attempt_number}) In Evaluation"
        next_action_desc = f"Your latest project package for <strong>{escape(active_b.title if active_b else '')}</strong> is currently undergoing technical review. While awaiting marksheet publication, begin reviewing study materials for subsequent milestones."
        next_action_pill = '<span class="status-pill status-pending" style="font-size:11px; font-weight:800; padding:4px 10px;">&#9203; Under Guardian Review</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:12px; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Track Submission Status &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:12px; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_materials')">Browse Study Materials &rarr;</button>"""
    elif latest_sub and latest_sub.status == "resubmission_requested":
        next_action_title = f"Resubmission Required: {active_b.code if active_b else 'Milestone'}"
        next_action_desc = f"Evaluator requested a revised Attempt #{latest_sub.attempt_number + 1} deliverable. Address the architectural feedback and resubmit your implementation package."
        next_action_pill = '<span class="status-pill status-rejected" style="font-size:11px; font-weight:800; padding:4px 10px;">&#9888; Resubmission Requested</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:12px; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Submit Revised Deliverable &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:12px; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')">View Evaluator Feedback &rarr;</button>"""
    elif active_b:
        next_action_title = f"Active Sprint: Complete {active_b.code} Deliverables"
        next_action_desc = f"You are currently fulfilling <strong>{escape(active_b.title)}</strong>. Prepare your PDF system architecture charter and executable code package for upload."
        next_action_pill = '<span class="status-pill status-active" style="font-size:11px; font-weight:800; padding:4px 10px;">&#9654; Sprint In Progress</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:12px; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Submit Project Deliverable &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:12px; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_materials')">Review Study Materials &rarr;</button>"""
    else:
        next_action_title = "Curriculum Roadmap Completed"
        next_action_desc = "All assigned enterprise milestones have been certified. Review your official marksheet transcript."
        next_action_pill = '<span class="status-pill status-approved" style="font-size:11px; font-weight:800; padding:4px 10px;">&#10003; Certified</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:12px; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')">View Marksheets &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:12px; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_roadmap')">Explore Career Pathways &rarr;</button>"""

    # --------------------------------------------------------------------------
    # SECTION D: Cohort Academic Leaderboard
    # --------------------------------------------------------------------------
    leaderboard_rows = []
    # Show the top 10 plus the signed-in cadet's own row (with true rank) instead of every employee.
    _top_n = 10
    _leaderboard_view = [(i, cp) for i, cp in enumerate(sorted_cohort, start=1) if i <= _top_n]
    if rank > _top_n:
        _leaderboard_view.append((rank, sorted_cohort[rank - 1]))
    for idx, c in _leaderboard_view:
        if idx == 1:
            r_badge = '<span style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:#FEF3C7; color:#B45309; font-weight:800; font-size:12px; border:1px solid #FCD34D;">1</span>'
        elif idx == 2:
            r_badge = '<span style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:#F1F5F9; color:#475569; font-weight:800; font-size:12px; border:1px solid #CBD5E1;">2</span>'
        elif idx == 3:
            r_badge = '<span style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:#FFEDD5; color:#C2410C; font-weight:800; font-size:12px; border:1px solid #FDBA74;">3</span>'
        else:
            r_badge = f'<span style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:rgba(23,52,92,0.06); color:var(--frost-navy); font-weight:700; font-size:11.5px;">{idx}</span>'

        c_marks = c.get("average_marks", 0.0)
        c_pct = c.get("average_percentage", 0.0)
        c_comp = c.get("completed_count", 0)
        c_total_assigned = max(1, c.get("total_assigned", 0) or 0)
        c_prog_pct = min(100, round((c_comp / c_total_assigned) * 100)) if c.get("total_assigned", 0) else 0
        tier_label = c.get("standing_tier", "Strong Performance")
        tier_color = "#059669" if c_marks >= 45.0 else ("#2563EB" if c_marks >= 40.0 else "#D97706")

        is_current_cadet = (c.get("id") == current_user.id)
        if is_current_cadet:
            row_style = "background:linear-gradient(90deg, rgba(16,185,129,0.12) 0%, rgba(234,244,255,0.6) 100%); border-left:4px solid #10B981; border-bottom:1px solid rgba(16,185,129,0.3);"
            you_tag = '<span style="font-size:10px; font-weight:800; background:#047857; color:#FFFFFF; padding:2px 7px; border-radius:999px; margin-left:6px; letter-spacing:0.5px;">YOU</span>'
        else:
            row_style = "border-bottom:1px solid var(--icy-steel-30); transition:background 0.15s ease;"
            you_tag = ""

        leaderboard_rows.append(f"""
        <tr style="{row_style}">
            <td style="padding:10px 14px; text-align:center; vertical-align:middle; width:50px;">
                {r_badge}
            </td>
            <td style="padding:10px 14px; vertical-align:middle;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <div class="user-avatar" style="width:32px; height:32px; font-size:11px; font-weight:800; border:1px solid var(--icy-steel);">{escape(c.get("avatar", "CO"))}</div>
                    <div>
                        <div style="display:flex; align-items:center;">
                            <strong style="font-size:13px; color:var(--frost-navy);">{escape(c.get("name", "Cadet"))}</strong>
                            {you_tag}
                        </div>
                        <div style="font-size:11px; color:var(--frost-navy-50);">{escape(c.get("band", "") or "")}{" &bull; " if c.get("band") else ""}{escape(c.get("track", "") or c.get("role", "") or "Cadet")}</div>
                    </div>
                </div>
            </td>
            <td style="padding:10px 14px; text-align:center; vertical-align:middle;">
                <span style="font-weight:800; color:var(--deep-frozen-midnight);">{c_comp}</span> <span style="font-size:11px; opacity:0.6;">/ {c.get("total_assigned", 0)} Badge{'s' if c.get('total_assigned', 0) != 1 else ''}</span>
                <div style="width:50px; height:4px; border-radius:2px; background:rgba(157,183,213,0.3); margin:3px auto 0 auto; overflow:hidden;">
                    <div style="width:{c_prog_pct}%; height:100%; background:#10B981;"></div>
                </div>
            </td>
            <td style="padding:10px 14px; vertical-align:middle;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                    <span style="font-size:12.5px; font-weight:800; color:var(--deep-frozen-midnight);">{c_marks:.1f} <span style="font-size:10.5px; opacity:0.6;">/ 50</span></span>
                    <span style="font-size:11px; font-weight:700; color:{tier_color};">{c_pct:.1f}%</span>
                </div>
                <div style="height:5px; border-radius:3px; background:rgba(157,183,213,0.25); overflow:hidden;">
                    <div style="height:100%; width:{c_pct}%; background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
                </div>
            </td>
            <td style="padding:10px 14px; text-align:center; vertical-align:middle;">
                <span style="font-size:11px; font-weight:700; color:{tier_color}; background:rgba(23,52,92,0.06); padding:3px 9px; border-radius:999px;">
                    {tier_label}
                </span>
            </td>
            <td style="padding:10px 14px; text-align:right; vertical-align:middle; white-space:nowrap;">
                <span style="font-size:11px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.05); padding:3px 8px; border-radius:4px;">
                    {escape(c.get("active_badge_code", "Active"))} Sprint
                </span>
            </td>
        </tr>
        """)

    leaderboard_deck = f"""
    <div class="liquid-glass-card" style="padding:22px 24px; margin-bottom:24px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:10px;">
            <div>
                <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Cohort Academic Leaderboard</h3>
                <div style="font-size:12px; color:var(--frost-navy-50);">Ranked by average assessment score and certified milestones.</div>
            </div>
            <span style="font-size:11px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
                {total_cohort} Enrolled Cadets &bull; Your Rank: #{rank}
            </span>
        </div>

        <div style="overflow-x:auto;">
            <table style="width:100%; border-collapse:collapse; text-align:left;">
                <thead>
                    <tr style="border-bottom:1.5px solid var(--icy-steel); background:rgba(234,244,255,0.45); font-size:10.5px; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">
                        <th style="padding:8px 14px; text-align:center;">Rank</th>
                        <th style="padding:8px 14px;">Cadet Profile</th>
                        <th style="padding:8px 14px; text-align:center;">Milestones</th>
                        <th style="padding:8px 14px; min-width:180px;">Score Performance</th>
                        <th style="padding:8px 14px; text-align:center;">Academic Standing</th>
                        <th style="padding:8px 14px; text-align:right;">Pacing Status</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(leaderboard_rows)}
                </tbody>
            </table>
        </div>
    </div>
    """

    # --------------------------------------------------------------------------
    # SECTION E: BAR GRAPH: MILESTONE DELIVERABLES & RUBRIC MARKS COMPARISON
    # --------------------------------------------------------------------------
    curriculum_badges = [
        {"code": b.code, "id": b.id, "title": b.title, "pillar": b.capability or b.category}
        for b in assigned_badges
    ]

    asms_by_code = {}
    for a in asms:
        code = a.get("badge_code") or a.get("badge_id", "").replace("badge_", "").upper()
        asms_by_code[code] = a

    bargraph_cols = []
    for idx, b in enumerate(curriculum_badges):
        bcode = b["code"]
        pop_align = "pop-align-left" if idx == 0 else ("pop-align-right" if idx == len(curriculum_badges) - 1 else "pop-align-center")

        if bcode in asms_by_code:
            a = asms_by_code[bcode]
            score = float(a.get("total_marks", 0.0))
            pct = float(a.get("percentage", 0.0))
            att = a.get("attempt_number", 1)
            rev_dt = a.get("reviewed_at", "2026-11-01")
            status_pill = '<span style="font-size:10.5px; font-weight:800; color:#047857; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); padding:2px 8px; border-radius:999px;">&#10003; Certified</span>'
        else:
            score = 0.0
            pct = 0.0
            att = 0
            rev_dt = "Pending"
            status_pill = '<span style="font-size:10.5px; font-weight:800; color:var(--frost-navy-50); background:rgba(23,52,92,0.06); padding:2px 8px; border-radius:999px;">In Progress</span>'

        height_pct = min(100.0, max(8.0, (score / 50.0) * 100.0))

        if score >= 45.0:
            bar_style = "background:linear-gradient(180deg, #10B981 0%, #059669 100%); box-shadow:0 4px 12px rgba(16,185,129,0.25);"
            label_color = "#059669"
        elif score > 0.0:
            bar_style = "background:linear-gradient(180deg, #3B82F6 0%, #1D4ED8 100%); box-shadow:0 4px 12px rgba(37,99,235,0.25);"
            label_color = "#2563EB"
        else:
            bar_style = "background:rgba(23,52,92,0.08); border:1px dashed var(--icy-steel);"
            label_color = "var(--frost-navy-50)"

        score_label = f"{score:.1f}" if score > 0.0 else "—"
        popover_body = f"""
        <div style="font-weight:800; font-size:12px; color:#FFFFFF; margin-bottom:4px;">{escape(bcode)}: {escape(b["title"])}</div>
        <div style="font-size:11px; color:var(--pure-ice); margin-bottom:6px;">{escape(b["pillar"])}</div>
        <div style="padding-top:5px; border-top:1px solid rgba(157,183,213,0.25); font-size:11.5px; color:#FFFFFF;">
            Rubric Score: <strong style="color:#047857;">{score:.1f} / 50.0</strong> ({pct:.1f}%)
        </div>
        <div style="font-size:11px; color:var(--pure-ice); margin-top:2px;">Attempt #{att if att > 0 else '—'} &bull; {"Certified Assessment" if att > 0 else "Pending Deliverable"}</div>
        <div style="font-size:10.5px; color:var(--pure-ice); margin-top:3px; font-style:italic;">Evaluated: {escape(rev_dt)}</div>
        """

        bargraph_cols.append(f"""
        <div class="has-glass-tooltip velocity-bar-col {pop_align}" style="display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; position:relative; cursor:pointer;">
            <!-- Top Score Label -->
            <div style="font-size:12px; font-weight:800; color:{label_color}; margin-bottom:6px; font-family:var(--font-family-mono);">{score_label}</div>

            <!-- Vertical Bar Fill -->
            <div style="width:100%; max-width:68px; height:{height_pct}%; {bar_style} border-radius:6px 6px 0 0; transition:height 0.2s ease, opacity 0.2s ease;"></div>

            <!-- Popover Tooltip -->
            <div class="glass-tooltip-popover {pop_align}" style="min-width:215px;">
                {popover_body}
            </div>

            <!-- Column Legend / Subtext -->
            <div style="margin-top:10px; text-align:center; width:100%;">
                <div style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:var(--deep-frozen-midnight);">{escape(bcode)}</div>
                <div style="font-size:11px; color:var(--frost-navy-75); margin:2px 0 6px 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{escape(b['title'])}">{escape(b['title'])}</div>
                {status_pill}
            </div>
        </div>
        """)

    if not bargraph_cols:
        bargraph_inner = """
        <div style="color:var(--frost-navy-50); font-style:italic; padding:36px 16px; text-align:center;">
            No assigned curriculum milestones available. Assigned badges and evaluated scores will appear here.
        </div>
        """
    else:
        bargraph_inner = f"""
        <div style="height:190px; display:grid; grid-template-columns:repeat({len(bargraph_cols)}, 1fr); gap:16px; align-items:flex-end; border-bottom:1px solid var(--icy-steel-30); padding-bottom:10px;">
            {''.join(bargraph_cols)}
        </div>
        """

    bargraph_deck = f"""
    <div class="liquid-glass-card" style="padding:24px; margin-bottom:24px; overflow:visible;">
        <div style="margin-bottom:18px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Milestone Performance & Rubric Marks Comparison</h3>
                <div style="font-size:12.5px; color:var(--frost-navy-50);">Your verified 50-mark standard assessment rubric scores across curriculum roadmap badges.</div>
            </div>
            <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap; font-size:11.5px;">
                <span style="display:inline-flex; align-items:center; gap:5px; color:var(--frost-navy); font-weight:700;">
                    <span style="width:10px; height:10px; border-radius:2px; background:#10B981;"></span> Honors Distinction (&ge; 45/50)
                </span>
                <span style="display:inline-flex; align-items:center; gap:5px; color:var(--frost-navy); font-weight:700;">
                    <span style="width:10px; height:10px; border-radius:2px; background:#3B82F6;"></span> Certified Milestone (&ge; 35/50)
                </span>
            </div>
        </div>

        <div style="background:rgba(234,244,255,0.35); border:1px solid var(--icy-steel-30); border-radius:var(--radius-md); padding:32px 24px 20px 24px; position:relative; overflow:visible;">
            {"<!-- Passing Threshold Guide Line (35.0 / 50.0 = 70% from baseline) -->" if bargraph_cols else ""}
            {f'''<div style="position:absolute; top:32%; left:24px; right:24px; height:1px; border-top:1.5px dashed rgba(16,185,129,0.6); z-index:1; pointer-events:none;">
                <span style="position:absolute; right:0; top:-20px; font-size:10.5px; font-weight:800; color:#047857; background:rgba(255,255,255,0.95); padding:2px 8px; border-radius:4px; border:1px solid rgba(16,185,129,0.3); box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                    Passing Threshold: 35.0 / 50.0 (70%)
                </span>
            </div>''' if bargraph_cols else ''}

            <!-- Milestone Performance Columns Container -->
            <div style="display:grid; grid-template-columns:repeat({max(1, len(bargraph_cols))}, minmax(0, 1fr)); gap:18px; min-height:160px; align-items:flex-end; position:relative; z-index:2;">
                {"".join(bargraph_cols) if bargraph_cols else '<div style="grid-column:1/-1; text-align:center; padding:32px 16px; color:var(--frost-navy-50); font-style:italic;">No milestone deliverables currently evaluated. Complete and submit a project milestone to see performance metrics.</div>'}
            </div>
        </div>
    </div>
    """

    # --------------------------------------------------------------------------
    # SECTION F: OFFICIAL EVALUATED MARKSHEETS
    # --------------------------------------------------------------------------
    marksheet_items = []
    for a in asms:
        b_code = a.get("badge_code", a.get("badge_id", ""))
        b_title = a.get("badge_title", "")
        att = a.get("attempt_number", 1)
        tot = a.get("total_marks", 0.0)
        pct = a.get("percentage", 0.0)
        dt = a.get("reviewed_at", "")
        asm_id = a.get("id") or f"asm_{current_user.id}_{b_code.lower()}"

        marksheet_items.append(f"""
        <div style="padding:14px 18px; margin-bottom:12px; background:rgba(255,255,255,0.92); border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; box-shadow:0 2px 6px rgba(7,22,41,0.03);">
            <div>
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:2px;">
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">{escape(b_code)}</span>
                    <strong style="font-size:13.5px; color:var(--frost-navy);">{escape(b_title)}</strong>
                    <span style="font-size:11.5px; color:var(--frost-navy-50);">(Attempt #{att})</span>
                </div>
                <div style="font-size:12px; color:var(--frost-navy-75);">
                    Score: <strong style="color:var(--deep-frozen-midnight);">{tot:.1f} / 50.0</strong> ({pct:.1f}%) &bull; Certified on {escape(dt)}
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
                <span class="status-pill status-approved" style="font-size:10.5px;">&#10003; Certified</span>
                <button type="button" class="btn-metal btn-sm" style="font-size:11.5px; font-weight:700; padding:6px 14px; display:inline-flex; align-items:center; gap:5px;" onclick="window.StarAppBridge.dispatchAction('view_marksheet', '{escape(asm_id)}')">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                    <span>View Review Marksheet &nearr;</span>
                </button>
            </div>
        </div>
        """)

    marksheets_html = "".join(marksheet_items) if marksheet_items else "<div style='padding:24px; text-align:center; color:var(--frost-navy-50); font-style:italic;'>No certified assessments recorded.</div>"

    # --------------------------------------------------------------------------
    # SECTION G: VERIFIED SKILLS INVENTORY (RATING OUT OF 10.0)
    # --------------------------------------------------------------------------
    skills_data = astraea_rec.get("skills", [])
    skill_cards = []
    for sk in skills_data:
        sk_name = sk.get("name", "Skill")
        sk_cat = sk.get("category", "General")
        sk_prof = sk.get("proficiency", "Proficient")
        sk_col = sk.get("level_color", "#2563EB")
        sk_pct = sk.get("pct", 85)
        sk_rating = float(sk.get("rating", round(sk_pct / 10.0, 1)))
        sk_badge = sk.get("badge", "GEN")

        skill_cards.append(f"""
        <div style="background:rgba(255,255,255,0.92); border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm); padding:14px 16px; box-shadow:0 2px 6px rgba(7,22,41,0.03);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:8px;">
                <div>
                    <div style="font-size:10.5px; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px;">{escape(sk_cat)}</div>
                    <strong style="font-size:13.5px; color:var(--frost-navy); display:block; margin-top:2px;">{escape(sk_name)}</strong>
                </div>
                <span style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">{escape(sk_badge)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; font-size:11.5px; gap:8px; flex-wrap:wrap;">
                <span style="font-weight:800; color:{sk_col}; background:rgba(37,99,235,0.08); padding:2px 8px; border-radius:4px;">{escape(sk_prof)}</span>
                <span style="font-weight:800; font-size:11.5px; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.07); padding:2px 8px; border-radius:4px; border:1px solid var(--icy-steel);">
                    &#9733; Rating: <strong style="color:#047857; font-size:12px;">{sk_rating:.1f}</strong> / 10.0
                </span>
            </div>
            <div style="width:100%; height:6px; background:rgba(157,183,213,0.25); border-radius:3px; overflow:hidden;">
                <div style="width:{sk_pct}%; height:100%; background:linear-gradient(90deg, #3B82F6, #10B981); border-radius:3px;"></div>
            </div>
        </div>
        """)

    skills_html = f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(300px, 100%), 1fr)); gap:14px;">
        {"".join(skill_cards)}
    </div>
    """ if skill_cards else "<div style='color:var(--frost-navy-50); font-style:italic;'>No skill competencies mapped yet.</div>"

    # --------------------------------------------------------------------------
    # SECTION H: OFFICIAL CERTIFICATIONS & VERIFIED CREDENTIALS
    # --------------------------------------------------------------------------
    certs_data = astraea_rec.get("certifications", [])
    cert_cards = []
    for ct in certs_data:
        c_code = ct.get("code", "")
        c_title = ct.get("title", "")
        cred_id = ct.get("credential_id", "")
        issued = ct.get("issued_at", "")
        score_str = ct.get("score", "")
        honors = ct.get("honors", "Certified")

        cert_cards.append(f"""
        <div style="background:rgba(255,255,255,0.92); border:1px solid var(--icy-steel-30); border-left:4px solid #10B981; border-radius:var(--radius-sm); padding:16px; box-shadow:0 2px 6px rgba(7,22,41,0.03);">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:10px;">
                <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.07); padding:3px 8px; border-radius:4px;">{escape(cred_id)}</span>
                <span style="font-size:10.5px; font-weight:800; color:#047857; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); padding:3px 8px; border-radius:999px;">&#10003; {escape(honors)}</span>
            </div>
            <div style="font-size:14px; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">
                <span style="font-family:var(--font-family-mono); color:var(--deep-frozen-midnight); font-weight:800;">{escape(c_code)}:</span> {escape(c_title)}
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; padding-top:8px; border-top:1px solid var(--icy-steel-30); font-size:11.5px; color:var(--frost-navy-75);">
                <span>Score: <strong style="color:var(--deep-frozen-midnight);">{escape(score_str)}</strong></span>
                <span>Issued: <strong>{escape(issued)}</strong></span>
            </div>
        </div>
        """)

    certs_html = f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(280px, 100%), 1fr)); gap:14px;">
        {"".join(cert_cards)}
    </div>
    """ if cert_cards else "<div style='color:var(--frost-navy-50); font-style:italic;'>No milestone certifications issued yet.</div>"

    # --------------------------------------------------------------------------
    # SECTION I: PEDAGOGICAL DIAGNOSTICS & MENTORING PATHWAY
    # --------------------------------------------------------------------------
    strengths_data = astraea_rec.get("strengths", [])
    improvements_data = astraea_rec.get("improvements", [])
    mentoring_plan = astraea_rec.get("mentoring_plan", "Maintain current pacing and deliverable quality.")

    str_items = "".join([f"""
    <li style="margin-bottom:10px; display:flex; align-items:flex-start; gap:8px; font-size:12.5px; color:var(--frost-navy); line-height:1.5;">
        <span style="color:#047857; font-weight:800; font-size:13px; line-height:1.4;">&#10003;</span>
        <span>{escape(s)}</span>
    </li>
    """ for s in strengths_data])

    imp_items = "".join([f"""
    <li style="margin-bottom:10px; display:flex; align-items:flex-start; gap:8px; font-size:12.5px; color:var(--frost-navy); line-height:1.5;">
        <span style="color:#B45309; font-weight:800; font-size:13px; line-height:1.4;">&#9678;</span>
        <span>{escape(im)}</span>
    </li>
    """ for im in improvements_data])

    diagnostics_html = f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(320px, 100%), 1fr)); gap:18px; margin-bottom:18px;">
        <!-- Column 1: Strengths -->
        <div style="background:rgba(16,185,129,0.03); border:1px solid rgba(16,185,129,0.22); border-left:4px solid #10B981; border-radius:var(--radius-sm); padding:16px 18px;">
            <div style="font-size:13px; font-weight:800; color:#065F46; margin-bottom:12px; display:flex; align-items:center; gap:8px;">
                <span style="background:#047857; color:#fff; width:22px; height:22px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:12px;">&#10003;</span>
                Demonstrated Engineering Strengths
            </div>
            <ul style="list-style:none; padding:0; margin:0;">
                {str_items}
            </ul>
        </div>

        <!-- Column 2: Improvement Areas -->
        <div style="background:rgba(245,158,11,0.03); border:1px solid rgba(245,158,11,0.22); border-left:4px solid #F59E0B; border-radius:var(--radius-sm); padding:16px 18px;">
            <div style="font-size:13px; font-weight:800; color:#92400E; margin-bottom:12px; display:flex; align-items:center; gap:8px;">
                <span style="background:#F59E0B; color:#451A03; width:22px; height:22px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:12px;">&#9678;</span>
                Targeted Improvement & Growth Areas
            </div>
            <ul style="list-style:none; padding:0; margin:0;">
                {imp_items}
            </ul>
        </div>
    </div>

    <!-- Mentoring Action Plan -->
    <div style="background:linear-gradient(135deg, rgba(23,52,92,0.05) 0%, rgba(37,99,235,0.08) 100%); border:1px solid rgba(37,99,235,0.22); border-left:4px solid var(--frost-navy); border-radius:var(--radius-sm); padding:16px 20px;">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <div style="width:26px; height:26px; border-radius:50%; background:var(--deep-frozen-midnight); color:#fff; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:800;">GM</div>
            <div style="font-size:12.5px; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px;">
                Faculty Mentoring Guidance &bull; Mentorship Committee
            </div>
        </div>
        <div style="font-size:13px; color:var(--frost-navy); line-height:1.55; margin-left:36px;">
            {escape(mentoring_plan)}
        </div>
    </div>
    """

    # Review request alert banner for higher-band reviewers
    review_alert_banner = ""
    try:
        user_reqs = store.get_badge_review_requests_for_user(current_user.id)
        pending_review_cnt = len([r for r in user_reqs if r.get("workflow_status") == "pending_review" or r.get("assignment_status") == "pending"])
        if pending_review_cnt > 0:
            review_alert_banner = f"""
            <div class="liquid-glass-card" style="padding:16px 20px; border-left:4px solid #F59E0B; margin-bottom:20px; background:linear-gradient(135deg, rgba(254,243,199,0.95) 0%, rgba(255,255,255,0.98) 100%); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; border-radius:var(--radius-md); box-shadow:0 4px 14px rgba(245,158,11,0.12);">
                <div>
                    <div style="font-size:11.5px; font-weight:800; color:#B45309; text-transform:uppercase; letter-spacing:0.5px;">Institutional Peer Review Assignment</div>
                    <div style="font-size:13.5px; color:var(--frost-navy); font-weight:700; margin-top:2px;">
                        You have <strong>{pending_review_cnt} badge review request(s)</strong> awaiting your inspection and authorization.
                    </div>
                </div>
                <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_requests')" style="font-weight:700; font-size:12px; padding:6px 16px;">
                    Review Requests ({pending_review_cnt}) &rarr;
                </button>
            </div>
            """
    except Exception:
        pass

    return f"""
    <div>
        {review_alert_banner}
        <!-- SECTION A: Personal Welcome / Dossier Header -->
        <div class="liquid-glass-card" style="padding:22px 28px; margin-bottom:24px; border-radius:var(--radius-lg); border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(234,244,255,0.85) 100%); box-shadow:0 6px 20px rgba(7,22,41,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div class="user-avatar" style="width:52px; height:52px; font-size:18px; font-weight:800; border:2px solid var(--icy-steel);">{escape(current_user.avatar)}</div>
                    <div>
                        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                            <h2 style="font-size:1.45rem; font-weight:800; color:var(--frost-navy); margin:0;">Welcome back, {escape(current_user.name)}</h2>
                            <span style="font-size:11px; font-weight:800; background:#047857; color:#FFFFFF; padding:3px 9px; border-radius:var(--radius-xs);">FLIGHT OFFICER</span>
                        </div>
                        <div style="font-size:12.5px; color:var(--frost-navy-75); margin-top:3px;">
                            Band <strong>{escape(getattr(current_user, "band", "") or "B1")}</strong> &bull; <strong>{escape(getattr(current_user, "learning_track", "") or "Cosmonaut")}</strong>{(" &bull; Batch: <strong>" + escape(profile.batch_name) + "</strong>") if getattr(profile, "batch_name", "") else ""}{(" &bull; Mentor: <strong>" + escape(_mentor_name) + "</strong>") if _mentor_name else ""}
                        </div>
                    </div>
                </div>

                <div style="display:flex; flex-direction:column; align-items:flex-end; gap:8px;">
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                        {rank_medal}
                        <span style="font-size:12px; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:5px 12px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel);">
                            Standing: <strong>{escape(tier)}</strong>
                        </span>
                        {r_pill}
                    </div>
                    <div style="font-size:11px; color:var(--frost-navy-50);">
                        Last Active: <strong style="color:var(--frost-navy);">{escape(last_act)}</strong> &bull; {escape(last_act_desc)}
                    </div>
                </div>
            </div>
        </div>

        <!-- SECTION B: Executive Performance KPIs Grid -->
        <div class="kpi-grid guardian-kpi-row" style="margin-bottom:24px;">
            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        Certified Milestones
                    </span>
                    {render_cosmo_metric_info_popover('individual_badges', astraea_rec, 'individual')}
                </div>
                <div class="kpi-value" style="font-size:1.75rem; font-weight:800; line-height:1.1; margin:2px 0 6px 0; color:var(--frost-navy);">{comp_count} / {total_assigned}</div>
                <div style="height:5px; border-radius:3px; background:rgba(157,183,213,0.3); overflow:hidden; margin:4px 0;">
                    <div style="height:100%; width:{progress_pct}%; background:#10B981;"></div>
                </div>
                <div class="kpi-subtext" style="color:#047857; font-weight:700; font-size:11px;">▲ {progress_pct}% Roadmap Certified</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        Average Score
                    </span>
                    {render_cosmo_metric_info_popover('individual_score', astraea_rec, 'individual')}
                </div>
                <div class="kpi-value" style="font-size:1.75rem; font-weight:800; line-height:1.1; margin:2px 0 6px 0; color:var(--frost-navy);">{avg_marks:.1f} <span style="font-size:12.5px; opacity:0.65; font-weight:600;">/ 50.0</span></div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700; font-size:11px;">{avg_pct:.1f}% Average Across Milestones</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        Leaderboard Rank
                    </span>
                    <div class="kpi-icon-bubble" style="width:24px; height:24px; display:flex; align-items:center; justify-content:center; border-radius:var(--radius-xs);">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    </div>
                </div>
                <div class="kpi-value" style="font-size:1.75rem; font-weight:800; line-height:1.1; margin:2px 0 6px 0; color:#047857;">#{rank} <span style="font-size:12.5px; opacity:0.65; color:var(--frost-navy);">/ {total_cohort}</span></div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700; font-size:11px;">Top {round((rank/max(1, total_cohort))*100)}% of Cohort</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        First-Attempt Pass Rate
                    </span>
                    {render_cosmo_metric_info_popover('individual_first_attempt', astraea_rec, 'individual', 'right')}
                </div>
                <div class="kpi-value" style="font-size:1.75rem; font-weight:800; line-height:1.1; margin:2px 0 6px 0; color:var(--frost-navy);">{first_pass_rate}%</div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700; font-size:11px;">{astraea_rec.get("first_attempt_passes", 0)} Cleared on Attempt #1</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        Active Milestone
                    </span>
                    {render_cosmo_metric_info_popover('individual_active_milestone', astraea_rec, 'individual', 'right')}
                </div>
                <div class="kpi-value" style="font-size:1.35rem; font-weight:800; color:var(--deep-frozen-midnight); line-height:1.2; margin:2px 0 6px 0;">{escape(active_b.code if active_b else "Completed")}</div>
                <div class="kpi-subtext" style="color:var(--frost-navy-50); font-size:11px; font-weight:600;">{escape(astraea_rec.get("deadline_status", "On Schedule"))}</div>
            </div>
        </div>

        <!-- SECTION C: Personalized Next Action Card -->
        <div class="liquid-glass-card" style="padding:22px 28px; margin-bottom:24px; border-radius:var(--radius-lg); border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(234,244,255,0.9) 100%); box-shadow:0 6px 20px rgba(7,22,41,0.06);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:11px; font-weight:800; text-transform:uppercase; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 9px; border-radius:var(--radius-xs);">YOUR NEXT ACTION</span>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0;">{next_action_title}</h3>
                </div>
                {next_action_pill}
            </div>

            <p style="font-size:13.5px; color:var(--frost-navy); line-height:1.55; margin:0 0 16px 0;">
                {next_action_desc}
            </p>

            <div style="display:flex; gap:10px; flex-wrap:wrap;">
                {primary_btn}
                {secondary_btn}
            </div>
        </div>

        <!-- SECTION D: Cohort Academic Leaderboard -->
        {leaderboard_deck}

        <!-- SECTION E: Milestone Performance & Rubric Marks Bar Graph -->
        {bargraph_deck}

        <!-- SECTION F: Official Evaluated Marksheets -->
        <div class="liquid-glass-card" style="padding:24px; margin-bottom:24px;">
            <div style="margin-bottom:18px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Official Evaluated Marksheets (Standard 50-Mark Rubric)</h3>
                    <div style="font-size:12.5px; color:var(--frost-navy-50);">Audited submission evaluations across the 5 rubric criteria. Click 'View Review Marksheet' to inspect your full evaluation rubric.</div>
                </div>
                <span style="font-size:12px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
                    {len(asms)} Evaluated Milestone{"s" if len(asms) != 1 else ""}
                </span>
            </div>

            <div>
                {marksheets_html}
            </div>
        </div>

        <!-- SECTION G: Verified Skills & Technical Competencies -->
        <div class="liquid-glass-card" style="padding:24px; margin-bottom:24px;">
            <div style="margin-bottom:18px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Verified Skills & Competency Matrix</h3>
                    <div style="font-size:12.5px; color:var(--frost-navy-50);">Evaluated engineering capabilities demonstrated through accredited milestone submissions, with ratings scored out of 10.0.</div>
                </div>
                <span style="font-size:12px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
                    {len(skills_data)} Verified Skill{"s" if len(skills_data) != 1 else ""}
                </span>
            </div>
            {skills_html}
        </div>

        <!-- SECTION H: Official Milestone Certifications & Credentials -->
        <div class="liquid-glass-card" style="padding:24px; margin-bottom:24px;">
            <div style="margin-bottom:18px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Official Certifications & Verified Credentials</h3>
                    <div style="font-size:12.5px; color:var(--frost-navy-50);">Standard-issue micro-credentials awarded upon successful 50-mark rubric evaluation.</div>
                </div>
                <span style="font-size:12px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
                    {len(certs_data)} Verified Credential{"s" if len(certs_data) != 1 else ""}
                </span>
            </div>
            {certs_html}
        </div>

        <!-- SECTION I: Pedagogical Diagnostics & Mentoring Pathway -->
        <div class="liquid-glass-card" style="padding:24px; margin-bottom:24px;">
            <div style="margin-bottom:18px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Pedagogical Diagnostics & Mentoring Pathway</h3>
                    <div style="font-size:12.5px; color:var(--frost-navy-50);">Guardian observational analysis, demonstrated competencies, and targeted improvement roadmaps.</div>
                </div>
                <span style="font-size:12px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
                    Pedagogical Diagnostic
                </span>
            </div>
            {diagnostics_html}
        </div>
    </div>
    """


# ==============================================================================
# 6.2 COSMONAUT PROFILE (Interactive Skill & Certification Management)
# ==============================================================================

def render_cosmonaut_profile(current_user: User, profile: CosmonautProfile) -> str:
    # Bio default text if not present on profile
    bio_text = getattr(profile, "bio", "") or (
        "Data systems apprentice specializing in stream processing architectures, "
        "fault-tolerant ETL pipelines, and regulatory data governance matrices under Guardian mentorship."
    )
    guardian_name = "Academy Guardian"
    guardian_title = profile.guardian_credentials or "Lead Enterprise Architect & Mentor"

    # Skills Pill Badges
    skills_tags = []
    for s in profile.skills:
        skills_tags.append(f"""
        <div style="display:inline-flex; align-items:center; gap:8px; padding:6px 14px; background:linear-gradient(135deg, rgba(23, 52, 92, 0.92) 0%, rgba(7, 22, 41, 0.96) 100%); border:1px solid var(--icy-steel); border-radius:var(--radius-full); font-size:12.5px; font-weight:700; color:var(--snow-white); box-shadow:0 2px 6px rgba(7,22,41,0.12); transition:transform 150ms ease;">
            <span style="font-family:var(--font-family-mono);">{escape(s)}</span>
            <span style="cursor:pointer; font-weight:900; font-size:14px; color:var(--icy-steel); line-height:1; padding-left:2px;" title="Remove skill" onclick="window.StarAppBridge.dispatchAction('remove_skill', '{escape(s)}')">&times;</span>
        </div>
        """)

    # Certifications Cards
    certs_items = []
    for idx, c in enumerate(profile.certifications):
        c_name = c.get("name", "")
        c_issuer = c.get("issuer", "")
        c_year = c.get("year", "")
        certs_items.append(f"""
        <div style="display:flex; align-items:center; justify-content:space-between; padding:14px 18px; background:rgba(255, 255, 255, 0.85); border-radius:var(--radius-md); border:1px solid var(--icy-steel-50); box-shadow:0 2px 8px rgba(7,22,41,0.03); margin-bottom:10px;">
            <div style="display:flex; align-items:center; gap:14px;">
                <div style="width:40px; height:40px; border-radius:var(--radius-sm); background:rgba(23,52,92,0.08); display:flex; align-items:center; justify-content:center; color:var(--deep-frozen-midnight); font-size:20px;">
                    {get_icon("file_text", 20)}
                </div>
                <div>
                    <div style="font-weight:800; color:var(--frost-navy); font-size:14px;">{escape(c_name)}</div>
                    <div style="font-size:12px; color:var(--frost-navy-50); margin-top:2px;">
                        Issuing Authority: <strong style="color:var(--deep-frozen-midnight);">{escape(c_issuer)}</strong> &bull; Year: <strong style="color:var(--deep-frozen-midnight);">{escape(c_year)}</strong>
                    </div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
                <span class="status-pill status-approved" style="font-size:11px; padding:3px 10px;">Verified</span>
                <button type="button" class="btn-secondary btn-sm" style="color:var(--frost-navy-50); padding:4px 10px;" onclick="window.StarAppBridge.dispatchAction('remove_certification', '{idx}')">Remove</button>
            </div>
        </div>
        """)

    return f"""
    <div style="max-width:1100px; margin:0 auto;">
        <div style="display:flex; align-items:center; margin-bottom:16px;">
            {render_back_button()}
        </div>
        <!-- 1. Executive Bio & Credentials Header Banner -->
        <div class="liquid-glass-card" style="padding:28px 32px; margin-bottom:24px; border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.92) 0%, rgba(234,244,255,0.65) 100%);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:18px; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:20px;">
                    <div class="user-avatar" style="width:72px; height:72px; font-size:26px; font-weight:800; background:linear-gradient(135deg, var(--deep-frozen-midnight) 0%, var(--frost-navy) 100%); color:var(--snow-white); border:2.5px solid var(--icy-steel); box-shadow:0 4px 16px rgba(7,22,41,0.18);">
                        {escape(current_user.avatar)}
                    </div>
                    <div>
                        <div style="display:flex; align-items:center; gap:10px;">
                            <h2 style="font-size:1.75rem; font-weight:800; color:var(--frost-navy); margin:0; letter-spacing:-0.4px;">{escape(current_user.name)}</h2>
                            <span class="status-pill status-approved" style="font-size:11px; padding:3px 10px;">Active Cosmonaut</span>
                        </div>
                        <div style="font-size:13px; color:var(--deep-frozen-midnight); font-weight:700; margin-top:3px;">
                            Cadre Orion-24 &bull; Trainee Identifier: <span style="font-family:var(--font-family-mono);">{escape(current_user.id)}</span>
                        </div>
                        <div style="font-size:12.5px; color:var(--frost-navy-50); margin-top:2px;">
                            Official Email: <strong style="color:var(--frost-navy);">{escape(current_user.email)}</strong>
                        </div>
                    </div>
                </div>

                <!-- Sign Out Button in Profile Header -->
                <div>
                    <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('logout', '{{}}')" style="display:inline-flex; align-items:center; gap:8px; font-weight:700; color:var(--deep-frozen-midnight); border:1.5px solid var(--icy-steel); padding:8px 18px; border-radius:var(--radius-md); box-shadow:0 2px 8px rgba(7,22,41,0.04);">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                        <span>Sign Out of Session</span>
                    </button>
                </div>
            </div>

            <!-- Professional Bio Narrative -->
            <div style="background:rgba(234,244,255,0.45); padding:16px 20px; border-radius:var(--radius-md); border:1px solid var(--icy-steel-30); margin-bottom:20px;">
                <div style="font-size:11.5px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.6px; margin-bottom:5px;">
                    Professional Summary & Academy Dossier
                </div>
                <p style="font-size:13.5px; color:var(--frost-navy); line-height:1.6; margin:0;">
                    {escape(bio_text)}
                </p>
            </div>

            <!-- Core Credentials Metadata Grid -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(220px, 100%), 1fr)); gap:14px;">
                <div style="background:rgba(255,255,255,0.9); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--frost-navy-50); font-weight:700; letter-spacing:0.5px;">Reporting Manager / Guardian</div>
                    <div style="font-size:13.5px; font-weight:800; color:var(--deep-frozen-midnight); margin-top:2px;">{escape(guardian_name)}</div>
                    <div style="font-size:11px; color:var(--frost-navy-50); margin-top:1px;">{escape(guardian_title)}</div>
                </div>

                <div style="background:rgba(255,255,255,0.9); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--frost-navy-50); font-weight:700; letter-spacing:0.5px;">Training Cohort</div>
                    <div style="font-size:13.5px; font-weight:800; color:var(--deep-frozen-midnight); margin-top:2px;">{escape(profile.batch_name or f"Band {getattr(current_user, 'band', 'B1')} Cohort")}</div>
                    <div style="font-size:11px; color:var(--frost-navy-50); margin-top:1px;">Enterprise Cadets</div>
                </div>

                <div style="background:rgba(255,255,255,0.9); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--frost-navy-50); font-weight:700; letter-spacing:0.5px;">Academy Standing</div>
                    <div style="font-size:13.5px; font-weight:800; color:var(--deep-frozen-midnight); margin-top:2px;">Tier-1 Certified</div>
                    <div style="font-size:11px; color:var(--frost-navy-50); margin-top:1px;">Good Standing &bull; Compliant</div>
                </div>

                <div style="background:rgba(255,255,255,0.9); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--frost-navy-50); font-weight:700; letter-spacing:0.5px;">Current Milestone</div>
                    <div style="font-size:13.5px; font-weight:800; color:var(--deep-frozen-midnight); margin-top:2px;">ING-104</div>
                    <div style="font-size:11px; color:var(--frost-navy-50); margin-top:1px;">Ingestion Foundations</div>
                </div>
            </div>
        </div>

        <!-- 2. Technical Competencies & Skills Section -->
        <div class="liquid-glass-card" style="padding:26px 30px; margin-bottom:24px; border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(234,244,255,0.55) 100%);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px;">
                <div>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0 0 3px 0;">Technical Competencies & Skills</h3>
                    <div style="font-size:12.5px; color:var(--frost-navy-50);">Validated domain proficiencies and framework competencies.</div>
                </div>
                <button type="button" class="btn-metal btn-sm" onclick="const box=document.getElementById('add-skill-form-box'); box.style.display=(box.style.display==='none'?'block':'none'); if(box.style.display==='block'){{document.getElementById('new-skill-input').focus();}}">
                    + Add Skill
                </button>
            </div>

            <!-- Hidden Add Skill Form (Revealed on Click) -->
            <div id="add-skill-form-box" style="display:none; margin-bottom:20px; padding:18px 20px; border-radius:var(--radius-md); background:rgba(255,255,255,0.95); border:1.5px solid var(--deep-frozen-midnight); box-shadow:0 4px 16px rgba(23,52,92,0.1);">
                <form onsubmit="event.preventDefault(); const inp=document.getElementById('new-skill-input'); if(inp.value.trim()){{ window.StarAppBridge.dispatchAction('add_skill', inp.value.trim()); inp.value=''; document.getElementById('add-skill-form-box').style.display='none'; }}" style="display:flex; gap:10px; align-items:center;">
                    <div style="flex:1;">
                        <input type="text" id="new-skill-input" class="liquid-glass-control" placeholder="Enter skill or framework (e.g. Apache Spark, Kafka, Distributed SQL, dbt)" style="background:#FFFFFF;" required>
                    </div>
                    <button type="submit" class="btn-metal" style="height:44px; padding:0 20px;">Save Skill</button>
                    <button type="button" class="btn-secondary" style="height:44px; padding:0 16px;" onclick="document.getElementById('add-skill-form-box').style.display='none';">Cancel</button>
                </form>
            </div>

            <!-- Skills Tag Cloud -->
            <div style="display:flex; flex-wrap:wrap; gap:10px;">
                {"".join(skills_tags) if skills_tags else "<span style='font-size:13px; color:var(--frost-navy-50); font-style:italic;'>No skills registered yet. Click '+ Add Skill' to add your technical proficiencies.</span>"}
            </div>
        </div>

        <!-- 3. Industry Certifications Section -->
        <div class="liquid-glass-card" style="padding:26px 30px; margin-bottom:24px; border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(234,244,255,0.55) 100%);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px;">
                <div>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0 0 3px 0;">Verified Industry Certifications</h3>
                    <div style="font-size:12.5px; color:var(--frost-navy-50);">Recognized accreditations and professional engineering credentials.</div>
                </div>
                <button type="button" class="btn-metal btn-sm" onclick="const box=document.getElementById('add-cert-form-box'); box.style.display=(box.style.display==='none'?'block':'none'); if(box.style.display==='block'){{document.getElementById('cert-name-input').focus();}}">
                    + Add Certificate
                </button>
            </div>

            <!-- Hidden Add Certificate Form (Revealed on Click) -->
            <div id="add-cert-form-box" style="display:none; margin-bottom:20px; padding:20px 22px; border-radius:var(--radius-md); background:rgba(255,255,255,0.95); border:1.5px solid var(--deep-frozen-midnight); box-shadow:0 4px 16px rgba(23,52,92,0.1);">
                <form onsubmit="event.preventDefault(); const n=document.getElementById('cert-name-input'); const i=document.getElementById('cert-issuer-input'); const y=document.getElementById('cert-year-input'); if(n.value.trim()){{ window.StarAppBridge.dispatchAction('add_certification', JSON.stringify({{name:n.value.trim(), issuer:i.value.trim(), year:y.value.trim()}})); n.value=''; i.value=''; y.value=''; document.getElementById('add-cert-form-box').style.display='none'; }}" style="display:grid; grid-template-columns:2fr 2fr 1fr auto auto; gap:12px; align-items:center;">
                    <div>
                        <input type="text" id="cert-name-input" class="liquid-glass-control" placeholder="Certification Name (e.g. AWS Data Engineer Associate)" style="background:#FFFFFF;" required>
                    </div>
                    <div>
                        <input type="text" id="cert-issuer-input" class="liquid-glass-control" placeholder="Issuing Body (e.g. Amazon Web Services, Databricks)" style="background:#FFFFFF;" required>
                    </div>
                    <div>
                        <input type="text" id="cert-year-input" class="liquid-glass-control" placeholder="Year (e.g. 2026)" style="background:#FFFFFF;" required>
                    </div>
                    <button type="submit" class="btn-metal" style="height:44px; padding:0 20px;">Save Certificate</button>
                    <button type="button" class="btn-secondary" style="height:44px; padding:0 16px;" onclick="document.getElementById('add-cert-form-box').style.display='none';">Cancel</button>
                </form>
            </div>

            <!-- Certifications List -->
            <div>
                {"".join(certs_items) if certs_items else "<div style='padding:24px; text-align:center; color:var(--frost-navy-50); font-style:italic;'>No external certifications recorded yet. Click '+ Add Certificate' to register your credentials.</div>"}
            </div>
        </div>
    </div>
    """

# ==============================================================================
# 6.3 BADGES — CANDY CRUSH-INSPIRED GAMIFIED LEARNING ROADMAP
# ==============================================================================

def render_gamified_roadmap(
    current_user: User,
    roadmap_nodes: List[Dict[str, Any]],
    is_guardian: bool = False
) -> str:
    """
    Renders the Candy Crush-inspired learning roadmap using standalone liquid-glass containers.
    No separate circle stones or checkmark symbols.
    Containers act as the milestone nodes with distinct status styling:
      - Completed: Dark Frost Navy / Deep Frozen Midnight
      - Active: Crisp Snow White / Frost Mist with pulsing active accent
      - Locked: Muted frosted glass with dashed border
    Connecting lines attach directly to container edges with a smooth organic S-curve.
    Order: Left -> Center -> Right -> Middle -> Left.
    """
    if not roadmap_nodes:
        return "<p style='padding:40px; text-align:center; color:var(--frost-navy-50);'>No roadmap milestones available.</p>"

    CW = 1000          # SVG viewBox width (responsive 100% width)
    CARD_W = 270       # Container width
    CARD_H = 96        # Container height
    half_w = CARD_W // 2
    half_h = CARD_H // 2
    total_height = len(roadmap_nodes) * 175 + 100

    # Build smooth organic cubic bezier curves directly between containers
    # From bottom center of container i to top center of container i+1
    full_paths = []
    completed_paths = []

    for i in range(len(roadmap_nodes) - 1):
        n1 = roadmap_nodes[i]
        n2 = roadmap_nodes[i + 1]
        x1 = n1["cx"]
        y1 = n1["cy"] + half_h
        x2 = n2["cx"]
        y2 = n2["cy"] - half_h
        mid_y = (y1 + y2) // 2

        # Pure smooth cubic bezier curve without any sharp corners or elbows
        seg = "M {} {} C {} {}, {} {}, {} {}".format(x1, y1, x1, mid_y, x2, mid_y, x2, y2)
        full_paths.append(seg)
        if n1["state"] == "completed":
            completed_paths.append(seg)

    full_curve_d = " ".join(full_paths)
    completed_curve_d = " ".join(completed_paths)

    completed_svg = ""
    if completed_curve_d:
        completed_svg = (
            '<path d="{}" fill="none" stroke="#F59E0B" '
            'stroke-width="7" stroke-linecap="round" opacity="0.95"/>'.format(completed_curve_d)
        )

    # Render standalone milestone containers
    milestone_els = []
    for idx, node in enumerate(roadmap_nodes):
        state = node["state"]
        cx, cy = node["cx"], node["cy"]
        badge_id = node["badge_id"]
        code = escape(node["code"])
        title = escape(node["title"])
        category = escape(node.get("category", "Foundations"))
        card_left = cx - half_w
        card_top = cy - half_h

        # Distinct color scheme per milestone state
        if state == "completed":
            card_style = (
                "background: linear-gradient(135deg, rgba(254, 243, 199, 0.98) 0%, rgba(251, 191, 36, 0.35) 50%, rgba(254, 240, 138, 0.95) 100%); "
                "border: 2px solid #F59E0B; "
                "box-shadow: 0 0 20px rgba(245, 158, 11, 0.45), 0 8px 24px rgba(180, 83, 9, 0.2); "
                "color: #78350F;"
            )
            code_style = "color: #92400E; font-weight: 800; font-family: var(--font-family-mono); font-size: 11.5px;"
            title_style = "color: #78350F; font-weight: 800; font-size: 14px; margin: 3px 0 2px;"
            desc_style = "color: #92400E; font-size: 11px; font-weight: 600;"
            status_html = '<span class="status-pill status-approved" style="font-size:10.5px; padding:2px 8px; border-radius:12px; font-weight:800; background:#F59E0B; color:#451A03; border:1px solid #D97706; box-shadow:0 2px 6px rgba(245,158,11,0.4); display:inline-flex; align-items:center; gap:3px;">★ Completed</span>'
        elif state == "active":
            card_style = (
                "background: linear-gradient(135deg, rgba(234, 244, 255, 0.96) 0%, rgba(255, 255, 255, 0.98) 100%); "
                "border: 2px solid var(--deep-frozen-midnight); "
                "box-shadow: 0 0 0 4px rgba(23, 52, 92, 0.18), 0 10px 24px rgba(7, 22, 41, 0.12); "
                "color: var(--frost-navy);"
            )
            code_style = "color: var(--deep-frozen-midnight); font-weight: 800; font-family: var(--font-family-mono); font-size: 11.5px;"
            title_style = "color: var(--frost-navy); font-weight: 700; font-size: 14px; margin: 3px 0 2px;"
            desc_style = "color: var(--frost-navy-50); font-size: 11px;"
            if node.get("is_current_active"):
                status_html = '<span class="status-pill status-active" style="font-size:10.5px; padding:2px 8px;">Active • Current</span>'
            else:
                status_html = '<span class="status-pill status-active" style="font-size:10.5px; padding:2px 8px;">Available</span>'
        else:  # locked
            card_style = (
                "background: rgba(234, 244, 255, 0.45); "
                "border: 1.5px dashed var(--icy-steel-50); "
                "opacity: 0.9; "
                "color: var(--frost-navy-50);"
            )
            lock_ic_12 = get_icon("lock", 12, "margin-right:4px;")
            code = f"{lock_ic_12} LEVEL {idx + 1:02d}"
            title = "Milestone locked"
            category = "Unlocks on Guardian Publish"
            code_style = "color: var(--frost-navy-50); font-weight: 700; font-family: var(--font-family-mono); font-size: 11.5px;"
            title_style = "color: var(--frost-navy); font-weight: 700; font-size: 14px; margin: 3px 0 2px; opacity: 0.85;"
            desc_style = "color: var(--frost-navy-50); font-size: 11px;"
            status_html = '<span class="status-pill status-locked" style="font-size:10.5px; padding:2px 8px;">Locked</span>'
            onclick = f"window.StarAppBridge.dispatchAction('open_badge_detail_modal', '{badge_id}');"
        if state != "locked":
            onclick = f"window.StarAppBridge.dispatchAction('open_badge_detail_modal', '{badge_id}');"

        milestone_els.append(
            '\n        <div class="liquid-glass-card interactive milestone-container-node"'
            ' style="position:absolute;left:{cl}px;top:{ct}px;width:{cw}px;height:{ch}px;'
            'z-index:2;cursor:pointer;{card_style}padding:12px 16px;border-radius:var(--radius-md);"'
            ' onclick="{onclick}">'
            '\n            <div style="display:flex;align-items:center;justify-content:space-between;">'
            '\n                <span style="{code_style}">{code}</span>'
            '\n                {status_html}'
            '\n            </div>'
            '\n            <div style="{title_style}">{title}</div>'
            '\n            <div style="{desc_style}">{category} • Level {idx}</div>'
            '\n        </div>'.format(
                cl=card_left, ct=card_top, cw=CARD_W, ch=CARD_H,
                card_style=card_style, onclick=onclick,
                code_style=code_style, code=code,
                status_html=status_html,
                title_style=title_style, title=title,
                desc_style=desc_style, category=category, idx=idx + 1
            )
        )

    total_nodes = len(roadmap_nodes)
    completed_count = sum(1 for n in roadmap_nodes if n["state"] == "completed")
    active_count = sum(1 for n in roadmap_nodes if n["state"] == "active")
    unlocked_count = completed_count + active_count
    locked_count = total_nodes - unlocked_count
    unlock_pct = round((unlocked_count / max(1, total_nodes)) * 100)

    heading_title = "Curriculum Milestone Roadmap" if is_guardian else "Cosmonaut Learning Pathway"
    heading_desc = (
        "Track cohort progress across the 25-level Candy Crush curriculum. Publish badges one by one in Badge Allotment or click any locked level to unlock it."
        if is_guardian else
        "Progress level by level across the 25-milestone curriculum pathway. Each locked level unlocks as your Guardian publishes the next milestone."
    )

    back_html = f'<div style="display:flex; align-items:center; margin-bottom:16px;">{render_back_button()}</div>'

    roadmap_body = """
    <div>
        <div style="text-align:center;margin-bottom:28px;">
            <h2 style="font-size:1.6rem;font-weight:800;color:var(--frost-navy);">{heading_title}</h2>
            <p style="font-size:13.5px;color:var(--frost-navy-50);margin-bottom:14px;">{heading_desc}</p>
            <div class="liquid-glass-card" style="display:inline-flex;flex-direction:column;gap:8px;padding:12px 20px;border-radius:var(--radius-md);min-width:300px;max-width:560px;width:100%;">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:12px;font-weight:700;color:var(--frost-navy);flex-wrap:wrap;">
                    <span>Level Progress: <strong>{unlocked_count} / {total_nodes} Unlocked</strong> ({unlock_pct}%)</span>
                    <span style="color:var(--frost-navy-50);font-weight:600;">{completed_count} Cleared &bull; {active_count} Active &bull; {locked_count} Locked</span>
                </div>
                <div style="width:100%;height:7px;border-radius:999px;background:rgba(157,183,213,0.3);overflow:hidden;">
                    <div style="width:{unlock_pct}%;height:100%;border-radius:999px;background:linear-gradient(90deg, var(--deep-frozen-midnight), #3B6CA8);transition:width 0.35s ease;"></div>
                </div>
            </div>
        </div>
        <div style="width:100%;display:flex;justify-content:center;overflow-x:auto;">
            <div style="width:100%;max-width:{CW}px;position:relative;min-height:{th}px;">
                <!-- Smooth SVG Curved Connecting Lines Direct to Containers -->
                <svg viewBox="0 0 {CW} {th}" width="100%" height="{th}"
                     style="position:absolute;top:0;left:0;width:100%;height:{th}px;pointer-events:none;z-index:1;overflow:visible;">
                    <defs>
                        <linearGradient id="roadmap-track-grad" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#071629"/>
                            <stop offset="50%" stop-color="#17345C"/>
                            <stop offset="100%" stop-color="#9DB7D5"/>
                        </linearGradient>
                    </defs>
                    <!-- Frosted shadow / glow halo -->
                    <path d="{fcd}" fill="none" stroke="rgba(157,183,213,0.38)" stroke-width="14" stroke-linecap="round"/>
                    <!-- Completed milestone track -->
                    {cmpsvg}
                    <!-- Clean solid core track (no white dots, no dashed line) -->
                    <path d="{fcd}" fill="none" stroke="url(#roadmap-track-grad)" stroke-width="5.5" stroke-linecap="round"/>
                </svg>
                <!-- Standalone Milestone Containers Layer -->
                <div style="position:relative;z-index:2;width:100%;min-height:{th}px;">
                    {containers}
                </div>
            </div>
        </div>
    </div>
    """.format(
        heading_title=heading_title,
        heading_desc=heading_desc,
        unlocked_count=unlocked_count,
        total_nodes=total_nodes,
        unlock_pct=unlock_pct,
        completed_count=completed_count,
        active_count=active_count,
        locked_count=locked_count,
        CW=CW, th=total_height,
        fcd=full_curve_d,
        cmpsvg=completed_svg,
        containers="\n".join(milestone_els)
    )
    return f"<div>{back_html}{roadmap_body}</div>"

def render_badge_detail_modal_content(
    badge: Badge,
    cosmo_id: str,
    timeline: Optional[BadgeTimeline],
    materials: List[LearningMaterial],
    state: str,
    is_guardian: bool = False
) -> str:
    dt = badge.default_timeline or {}
    alloc_date = (timeline.assignment_date if timeline and timeline.assignment_date else dt.get("assignment_date")) or "2026-10-01"
    learn_start = (timeline.learning_start_date if timeline and timeline.learning_start_date else dt.get("learning_start_date")) or "2026-10-02"
    learn_end = (timeline.learning_end_date if timeline and timeline.learning_end_date else dt.get("learning_end_date")) or "2026-10-10"
    proj_start = (timeline.project_start_date if timeline and timeline.project_start_date else dt.get("project_start_date")) or "2026-10-11"
    proj_end = (timeline.project_end_date if timeline and timeline.project_end_date else dt.get("project_end_date")) or "2026-10-20"
    sub_deadline = (timeline.submission_deadline if timeline and timeline.submission_deadline else dt.get("submission_deadline")) or "2026-10-22"
    review_date = (timeline.review_date if timeline and timeline.review_date else dt.get("review_date")) or "2026-10-25"
    award_date = (timeline.actual_award_date or timeline.expected_award_date if timeline else dt.get("expected_award_date")) or "2026-10-26"

    today_str = "2026-11-07"

    steps = [
        {
            "num": 1,
            "title": "Badge & Project Allocated",
            "date": alloc_date,
            "pill": "completed" if state in ["completed", "active"] else "locked",
            "cls": "completed" if state in ["completed", "active"] else "locked"
        },
        {
            "num": 2,
            "title": "Learning Time",
            "date": f"{learn_start} → {learn_end}",
            "pill": "completed" if (state == "completed" or (state == "active" and today_str >= learn_end)) else ("active" if state == "active" else "locked"),
            "cls": "completed" if (state == "completed" or (state == "active" and today_str >= learn_end)) else ("active" if state == "active" else "locked")
        },
        {
            "num": 3,
            "title": "Project Time",
            "date": f"{proj_start} → {proj_end}",
            "pill": "completed" if state == "completed" else ("active" if state == "active" else "locked"),
            "cls": "completed" if state == "completed" else ("active" if state == "active" else "locked")
        },
        {
            "num": 4,
            "title": "Submission Date",
            "date": sub_deadline,
            "pill": "completed" if state == "completed" else ("active" if state == "active" else "locked"),
            "cls": "completed" if state == "completed" else ("active" if state == "active" else "locked")
        },
        {
            "num": 5,
            "title": "Review Date",
            "date": review_date,
            "pill": "completed" if state == "completed" else ("active" if state == "active" else "locked"),
            "cls": "completed" if state == "completed" else ("active" if state == "active" else "locked")
        },
        {
            "num": 6,
            "title": "Badge Earned Date",
            "date": award_date,
            "pill": "completed" if state == "completed" else ("active" if state == "active" else "locked"),
            "cls": "completed" if state == "completed" else ("active" if state == "active" else "locked")
        }
    ]

    steps_html = []
    fill_percent = 100 if state == "completed" else (50 if state == "active" else 0)

    for idx, s in enumerate(steps):
        delay = 0.08 + idx * 0.08
        steps_html.append(f"""
        <div class="timeline-node-row {s['cls']}" style="animation-delay: {delay:.2f}s;">
            <div class="node-anchor">
                <div class="node-orb">{s['num']}</div>
            </div>
            <div class="node-connector-strip">
                <div class="node-label-title">{escape(s['title'])}</div>
                <div class="node-meta-group">
                    <span class="node-timestamp-pill">{escape(s['date'])}</span>
                    {render_status_pill(s['pill'])}
                </div>
            </div>
        </div>
        """)

    # Contextual action buttons
    actions = []
    if is_guardian:
        if state == "locked":
            actions.append(f"""
            <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('publish_and_unlock_badge', '{badge.id}')">
                {get_icon("rocket", 13, "margin-right:4px;")} Publish & Unlock Milestone
            </button>
            """)
        actions.append(f"""
        <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_edit_badge_modal', '{badge.id}')">
            Decide / Edit Timelines
        </button>
        """)
    else:
        if state in ["active", "completed"]:
            actions.append(f"""
            <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_to_submit_badge', '{badge.id}')">
                Proceed to Project Submission →
            </button>
            """)

    actions.append("""
    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('close_modal', '{}')">Close Window</button>
    """)

    display_code = "LOCKED" if (not is_guardian and state == "locked") else badge.code
    display_title = "Milestone locked" if (not is_guardian and state == "locked") else badge.title

    return f"""
    <div style="padding: 2px 0 0 0;">
        <!-- Clean Subheader with Badge Code, Title and Status -->
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid var(--icy-steel-30);">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:3px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-50);">{escape(display_code)}</span>
                <span style="font-size:15px; font-weight:800; color:var(--frost-navy);">{escape(display_title)}</span>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:11.5px; font-weight:600; color:var(--frost-navy-50);">Decided by Assigned Reviewer</span>
                {render_status_pill(state)}
            </div>
        </div>

        <!-- High-Tech Animated Lifecycle Timeline Track (Zero Scrolling) -->
        <div class="animated-timeline-container">
            <div class="timeline-track-spine">
                <div class="timeline-track-bg"></div>
                <div class="timeline-track-fill" style="--fill-target: {fill_percent}%;"></div>
                <div class="timeline-track-beam"></div>
            </div>
            <div class="timeline-nodes-sequence">
                {"".join(steps_html)}
            </div>
        </div>

        <!-- Footer Actions -->
        <div style="display:flex; justify-content:flex-end; align-items:center; gap:10px; margin-top:14px; padding-top:10px; border-top:1px solid var(--icy-steel-30);">
            {"".join(actions)}
        </div>
    </div>
    """

# ==============================================================================
# 6.5 BADGES & PROJECT SUBMISSION WORKSPACE
# ==============================================================================

def _extract_deliverable_info(deliv_val: Any, default_name: str, default_desc: str) -> tuple:
    """Safely extracts (name, description) from deliverable dict or string entries."""
    if isinstance(deliv_val, dict):
        return (deliv_val.get("name") or default_name, deliv_val.get("description") or default_desc)
    if isinstance(deliv_val, str) and deliv_val.strip():
        return (deliv_val.strip(), default_desc)
    return (default_name, default_desc)


def _render_assigned_project_spec_inner(
    assigned_proj: Any,
    rev_name_str: str,
    rev_band_str: str = "",
    window_str: str = "",
    sub_deadline_str: str = "",
    is_earned: bool = False,
    existing_sub: Optional[ProjectSubmission] = None,
    compact: bool = False
) -> str:
    """Renders the shared structured specification body for a Reviewer-allocated milestone project."""
    deliv = getattr(assigned_proj, "deliverables", {}) or {}
    code_name, code_info = _extract_deliverable_info(deliv.get("code"), "script.py", "Modular Python script")
    pdf_name, pdf_info = _extract_deliverable_info(deliv.get("pdf"), "report.pdf", "Architecture document")
    gh_name, gh_info = _extract_deliverable_info(deliv.get("github"), "GitHub Repo", "GitHub repository")

    req_items = getattr(assigned_proj, "requirements", []) or []
    req_list = req_items if compact else req_items
    req_items_html = "".join([f'<li style="margin-bottom:4px;">{escape(str(r))}</li>' for r in req_list]) if req_list else '<li>Follow standard 50-mark rubric requirements.</li>'

    outcomes_items = getattr(assigned_proj, "outcomes", []) or []
    outcomes_html = ""
    if outcomes_items:
        outcomes_pills = "".join([
            f'<li style="margin-bottom:4px; display:flex; align-items:flex-start; gap:6px;"><span style="color:#047857; font-weight:800;">✓</span><span>{escape(str(o))}</span></li>'
            for o in outcomes_items
        ])
        outcomes_html = f"""
        <div style="margin-bottom:12px; background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.22); border-radius:var(--radius-xs); padding:10px 14px;">
            <div style="font-size:10.5px; font-weight:800; text-transform:uppercase; color:#047857; letter-spacing:0.5px; margin-bottom:5px;">Expected Project Outcomes:</div>
            <ul style="margin:0; padding:0; list-style:none; font-size:12px; color:var(--frost-navy); line-height:1.45;">
                {outcomes_pills}
            </ul>
        </div>
        """

    if is_earned:
        status_pill = f'<span class="status-pill status-approved" style="display:inline-flex; align-items:center; gap:4px; font-size:10.5px; font-weight:800; background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; border-color:#D97706;">{get_icon("award", 12)} Completed</span>'
    elif existing_sub:
        status_pill = f'<span class="status-pill status-approved" style="display:inline-flex; align-items:center; gap:4px; font-size:10.5px; font-weight:800;">{get_icon("check", 12)} Submitted</span>'
    else:
        status_pill = f'<span class="status-pill status-approved" style="display:inline-flex; align-items:center; gap:4px; font-size:10.5px; font-weight:800;">{get_icon("check", 12)} Ready for Submission</span>'

    rev_display = f"{rev_name_str} (Band {rev_band_str})" if rev_band_str else rev_name_str
    schedule_chips = ""
    if window_str or sub_deadline_str:
        schedule_chips = f"""
        <div style="display:flex; flex-wrap:wrap; gap:12px; margin-bottom:12px; padding:8px 12px; background:rgba(23,52,92,0.04); border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30); font-size:11.5px; color:var(--frost-navy-75);">
            {f'<span style="display:inline-flex; align-items:center; gap:5px;">{get_icon("calendar", 13)} <strong>Review Window:</strong> <span style="font-family:var(--font-family-mono); font-weight:700; color:var(--deep-frozen-midnight);">{escape(window_str)}</span></span>' if window_str else ''}
            {f'<span style="display:inline-flex; align-items:center; gap:5px;">{get_icon("clock", 13, "color:#DC2626;")} <strong>Submission Deadline:</strong> <span style="font-family:var(--font-family-mono); font-weight:700; color:#DC2626;">{escape(sub_deadline_str)}</span></span>' if sub_deadline_str else ''}
        </div>
        """

    return f"""
    <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1.5px solid var(--icy-steel-30); padding-bottom:8px; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                <span style="font-size:10.5px; font-weight:800; background:linear-gradient(135deg, #0284C7, #0369A1); color:#fff; padding:2px 8px; border-radius:3px;">ASSIGNED PROJECT SPECIFICATION</span>
                <span style="font-size:11.5px; font-weight:700; color:var(--deep-frozen-midnight);">Allocated by Reviewer: {escape(rev_display)}</span>
            </div>
            {status_pill}
        </div>
        <h4 style="font-size:1.18rem; font-weight:800; color:var(--frost-navy); margin:0 0 6px 0;">{escape(getattr(assigned_proj, 'title', 'Milestone Project'))}</h4>
        <p style="font-size:12.8px; color:var(--frost-navy-75); line-height:1.5; margin:0 0 12px 0;">{escape(getattr(assigned_proj, 'description', ''))}</p>
        {schedule_chips}
        {outcomes_html}
        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:5px;">Detailed Project Requirements:</div>
        <ul style="margin:0 0 14px 18px; padding:0; font-size:12px; color:var(--frost-navy-75); line-height:1.45;">
            {req_items_html}
        </ul>
        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Mandatory Deliverable Files (Mapped to 50-Mark Rubric):</div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
            <div style="background:#fff; border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:8px 10px;">
                <div style="display:flex; align-items:center; gap:5px; font-size:11.5px; font-weight:800; color:#047857;">{get_icon("code", 13)}<span>{escape(code_name)}</span></div>
                <div style="font-size:10.5px; color:var(--frost-navy-50); margin-top:3px;">{escape(code_info)}</div>
            </div>
            <div style="background:#fff; border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:8px 10px;">
                <div style="display:flex; align-items:center; gap:5px; font-size:11.5px; font-weight:800; color:#DC2626;">{get_icon("file_text", 13)}<span>{escape(pdf_name)}</span></div>
                <div style="font-size:10.5px; color:var(--frost-navy-50); margin-top:3px;">{escape(pdf_info)}</div>
            </div>
            <div style="background:#fff; border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:8px 10px;">
                <div style="display:flex; align-items:center; gap:5px; font-size:11.5px; font-weight:800; color:var(--deep-frozen-midnight);">{get_icon("github", 13)}<span>{escape(gh_name)}</span></div>
                <div style="font-size:10.5px; color:var(--frost-navy-50); margin-top:3px;">{escape(gh_info)}</div>
            </div>
        </div>
    </div>
    """


def _render_allocated_project_detail_section(
    badge: Badge,
    assigned_proj: Any,
    rev_name_str: str,
    rev_band_str: str = "",
    window_str: str = "",
    sub_deadline_str: str = "",
    is_earned: bool = False,
    existing_sub: Optional[ProjectSubmission] = None
) -> str:
    """Renders the inline Allocated Project card inside the dedicated Badge Detail Page."""
    spec_html = _render_assigned_project_spec_inner(
        assigned_proj=assigned_proj,
        rev_name_str=rev_name_str,
        rev_band_str=rev_band_str,
        window_str=window_str,
        sub_deadline_str=sub_deadline_str,
        is_earned=is_earned,
        existing_sub=existing_sub,
        compact=False
    )
    return f"""
    <!-- SECTION: ALLOCATED PROJECT SPECIFICATION (FROM MAPPED REVIEWER) -->
    <div id="badge-section-allocated-project" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #0284C7; overflow:hidden; background:linear-gradient(135deg, rgba(234,244,255,0.98) 0%, rgba(255,255,255,0.98) 100%);">
        <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('allocated-project')">
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                <span style="width:28px; height:28px; border-radius:6px; background:rgba(2,132,199,0.14); color:#0284C7; display:flex; align-items:center; justify-content:center;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 12h6"/><path d="M9 16h6"/><path d="M9 8h6"/></svg>
                </span>
                <span style="font-size:15px; font-weight:800; color:#0369A1;">Project Allocated ({escape(getattr(assigned_proj, 'title', 'Milestone Project'))})</span>
            </div>
            <span id="chevron-allocated-project" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
        </div>
        <div id="content-allocated-project" style="padding:0 20px 20px 20px; display:block;">
            {spec_html}
        </div>
    </div>
    """


def render_cosmonaut_badge_card_expanded_content(
    badge: Badge,
    current_user: Optional[User] = None,
    existing_sub: Optional[ProjectSubmission] = None,
    is_standalone_page: bool = False
) -> str:
    import json
    from starapp.badge_generator import (
        generate_badge_data, build_practice_project_prompt, build_learning_resources_prompt
    )

    badge_title = getattr(badge, "title", "Milestone Badge")
    badge_code = getattr(badge, "code", "")
    badge_desc = getattr(badge, "description", "")
    selected_band = getattr(badge, "target_band", "B1")
    active_power = getattr(badge, "power", "Tech") or "Tech"
    active_cap = getattr(badge, "capability", "Data & Machine") or "Data & Machine"
    active_skill = getattr(badge, "skill", "Curation") or "Curation"

    prompt_str = getattr(badge, "prompt_json", "{}")
    p_data = {}
    if prompt_str:
        try:
            p_data = json.loads(prompt_str) if isinstance(prompt_str, str) else prompt_str
            if not isinstance(p_data, dict):
                p_data = {}
        except Exception:
            p_data = {}

    # Extract outcomes
    outcomes = p_data.get("outcomes") or p_data.get("expected_outcomes") or getattr(badge, "learning_outcomes", [])
    if not outcomes:
        synth = generate_badge_data(selected_band, active_power, active_cap, active_skill, "")
        outcomes = synth.get("outcomes", [])

    # Extract practice prompt
    practice_prompt = ""
    if isinstance(p_data.get("practice_project"), dict):
        practice_prompt = p_data["practice_project"].get("prompt", "")
    if not practice_prompt:
        practice_prompt = p_data.get("practice_prompt", "")
    if not practice_prompt or len(practice_prompt.strip()) < 80:
        practice_prompt = getattr(badge, "project_requirements", "")
    if not practice_prompt or len(practice_prompt.strip()) < 80:
        practice_prompt = build_practice_project_prompt(
            badge_title, active_skill, active_cap, active_power, selected_band, [], outcomes
        )

    # Extract learning topics (expect 6)
    learning_topics = p_data.get("learning_topics", [])
    if not learning_topics or len(learning_topics) < 6:
        synth = generate_badge_data(selected_band, active_power, active_cap, active_skill, "")
        learning_topics = synth.get("learning_topics", [])

    total_topics = len(learning_topics) if learning_topics else 6
    completed_topics_count = sum(1 for t in learning_topics if t.get("completed", False) or t.get("status", "").lower() == "completed")
    progress_pct = int(round((completed_topics_count / total_topics) * 100)) if total_topics > 0 else 0

    # Extract learning resources prompt
    resources_prompt = ""
    if isinstance(p_data.get("learning_resources"), dict):
        resources_prompt = p_data["learning_resources"].get("prompt", "")
    if not resources_prompt:
        resources_prompt = p_data.get("resources_prompt", "")
    if not resources_prompt or len(resources_prompt.strip()) < 80:
        resources_prompt = build_learning_resources_prompt(
            badge_title, active_skill, active_cap, active_power, selected_band, learning_topics, outcomes
        )

    # Section 1: Outcomes HTML
    outcomes_list_items = "".join([
        f'''<div style="display:flex; align-items:flex-start; gap:12px; font-size:13px; color:var(--frost-navy); line-height:1.55; padding:10px 14px; background:rgba(234,244,255,0.45); border:1px solid rgba(16,185,129,0.25); border-radius:var(--radius-sm); margin-bottom:8px;">
            <span style="width:20px; height:20px; border-radius:50%; background:rgba(16,185,129,0.15); color:#047857; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; flex-shrink:0; margin-top:1px;">✓</span>
            <span style="font-weight:600; flex:1;">{escape(str(o))}</span>
        </div>'''
        for o in outcomes
    ])
    outcomes_html = f"""
    <div style="display:flex; flex-direction:column; gap:2px;">
        {outcomes_list_items}
    </div>
    """

    # Section 4: Topics HTML
    topics_card_items = []
    for idx, t in enumerate(learning_topics):
        t_title = t.get("title", "")
        t_desc = t.get("description", "")
        is_comp = t.get("completed", False) or t.get("status", "").lower() == "completed"

        border_color = "#10B981" if is_comp else "rgba(6,182,212,0.3)"
        bg_style = "background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(236,253,245,0.7) 100%);" if is_comp else "background:linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(234,244,255,0.85) 100%);"
        status_text = "Completed" if is_comp else "In Progress"
        status_bg = "rgba(16,185,129,0.15)" if is_comp else "rgba(157,183,213,0.18)"
        status_color = "#10B981" if is_comp else "var(--frost-navy-50)"
        status_border = "rgba(16,185,129,0.3)" if is_comp else "rgba(157,183,213,0.3)"

        btn_class = "is-completed" if is_comp else ""
        btn_bg = "#10B981" if is_comp else "rgba(255,255,255,0.9)"
        btn_color = "white" if is_comp else "var(--frost-navy-75)"
        btn_border = "#059669" if is_comp else "var(--icy-steel)"
        btn_shadow = "0 2px 8px rgba(16,185,129,0.3)" if is_comp else "none"
        btn_content = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Completed' if is_comp else "Mark Complete"

        topics_card_items.append(f"""
        <div id="topic-card-{idx}" class="topic-row-card" style="padding:16px 20px; border-radius:var(--radius-md); border:1.5px solid {border_color}; {bg_style} display:flex; justify-content:space-between; align-items:center; gap:20px; width:100%; box-sizing:border-box; transition:border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;">
            <div style="flex:1;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                    <span style="font-size:11px; font-weight:800; background:rgba(6,182,212,0.12); color:#0891B2; padding:3px 10px; border-radius:12px; border:1px solid rgba(6,182,212,0.25);">Topic {idx+1}</span>
                    <span id="topic-status-tag-{idx}" style="background:{status_bg}; color:{status_color}; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; border:1px solid {status_border}; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease;">{status_text}</span>
                    <span style="font-size:11px; color:var(--frost-navy-50); font-weight:600;">Curriculum Module</span>
                </div>
                <div style="font-size:14.5px; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">{escape(t_title)}</div>
                <div style="font-size:12.5px; color:var(--frost-navy-75); line-height:1.5;">{escape(t_desc)}</div>
            </div>
            <div style="flex-shrink:0;">
                <button type="button" id="topic-toggle-btn-{idx}" class="{btn_class}"
                    onclick="window.StarAppBridge.toggleTopicCompletion({idx})"
                    style="background:{btn_bg}; color:{btn_color}; border:1.5px solid {btn_border}; box-shadow:{btn_shadow}; font-size:12px; font-weight:800; padding:8px 16px; border-radius:20px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease, box-shadow 0.25s ease;">
                    {btn_content}
                </button>
            </div>
        </div>
        """)
    topics_html = f'<div id="topics-list-container" style="display:flex; flex-direction:column; gap:12px; width:100%; box-sizing:border-box;">{"".join(topics_card_items)}</div>'

    btn_label = "Edit Deliverables for this Badge" if existing_sub else "Submit Deliverables for this Badge"
    btn_icon = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' if existing_sub else '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>'

    from starapp.storage import store
    is_earned = False
    earned_asm = None
    rev_id_str = ""
    rev_name_str = "Assigned Reviewer"
    rev_band_str = ""
    window_str = ""
    sub_deadline_str = ""
    assigned_proj = None
    is_retake = bool(existing_sub and getattr(existing_sub, "status", "") in ("retake_required", "resubmission_requested"))
    next_attempt = (getattr(existing_sub, "attempt_number", 1) + 1) if existing_sub else 1

    if current_user and store:
        tl = store.get_timeline(badge.id, current_user.id)
        if tl and getattr(tl, "status", "") == "completed":
            is_earned = True
        if tl and getattr(tl, "reviewer_id", ""):
            rev_id_str = tl.reviewer_id
        if not rev_id_str:
            for m in store.get_band_mappings():
                m_b = m.get("badge_id") or m.get("badge")
                if current_user.id in m.get("cosmonauts", []) and m.get("reviewers") and m_b in (badge.id, badge.code, badge.title):
                    rev_id_str = m["reviewers"][0]
                    break
        if not rev_id_str:
            rev_id_str = getattr(badge, "assigned_reviewer_id", "") or ""
        if rev_id_str:
            r_u = store.get_user_by_id(rev_id_str)
            if r_u:
                rev_name_str = r_u.name
                rev_band_str = getattr(r_u, "band", "") or ""
        if tl and getattr(tl, "review_window_json", None):
            try:
                rw_list = json.loads(tl.review_window_json)
                if isinstance(rw_list, list) and rw_list:
                    window_str = " → ".join(rw_list)
            except Exception:
                window_str = ""
        if tl and getattr(tl, "submission_deadline", ""):
            sub_deadline_str = tl.submission_deadline
        elif getattr(badge, "default_timeline", None) and badge.default_timeline.get("submission_deadline"):
            sub_deadline_str = badge.default_timeline.get("submission_deadline", "")

        asms = store.get_assessments_for_cosmonaut(current_user.id, badge.id)
        rev_earned_asm = None
        grd_earned_asm = None
        for a in sorted(
            asms,
            key=lambda x: (
                getattr(x, "attempt_number", 1),
                1 if getattr(x, "assessor_role", "") == "guardian" else 0,
                getattr(x, "reviewed_at", ""),
            ),
        ):
            a_role = getattr(a, "assessor_role", "")
            if a_role == "reviewer":
                rev_earned_asm = a
            elif a_role == "guardian":
                grd_earned_asm = a
            if a.decision == "approve" or a_role == "guardian":
                is_earned = True
                earned_asm = a
        if not earned_asm and existing_sub:
            sub_asm = store.get_assessment_for_submission(existing_sub.id)
            if existing_sub.status == "approved" or (sub_asm and sub_asm.decision == "approve"):
                is_earned = True
                earned_asm = sub_asm

        awarded_on_str = (getattr(tl, "actual_award_date", "") if tl else "") or (
            getattr(earned_asm, "reviewed_at", "")[:10] if earned_asm and getattr(earned_asm, "reviewed_at", "") else ""
        )

        cand_proj = store.get_project_prompt_for_cadet(badge.id, current_user.id)
        if cand_proj and getattr(cand_proj, "status", "") in ("released", "sent"):
            assigned_proj = cand_proj

    has_allocated_project = assigned_proj is not None
    project_allocated_btn_html = ""
    if has_allocated_project:
        project_allocated_btn_html = f"""
        <button type="button" id="btn-project-allocated-{escape(badge.id)}" class="btn-secondary btn-sm"
            onclick="window.StarAppBridge.dispatchAction('open_allocated_project_modal', '{escape(badge.id)}')"
            style="font-weight:800; font-size:12px; padding:6px 14px; background:rgba(2,132,199,0.1); color:#0369A1; border:1.5px solid #0284C7; border-radius:var(--radius-sm); display:inline-flex; align-items:center; gap:5px;">
            <span>📋</span>
            <span>Project allocated</span>
        </button>
        """

    if is_earned:
        top_card_style = "border:2px solid #F59E0B; background:linear-gradient(135deg, rgba(255,255,255,0.99) 0%, rgba(254,243,199,0.92) 100%); box-shadow:0 12px 36px rgba(245,158,11,0.25);"
        top_icon_style = "background:linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%); border:2px solid #F59E0B; color:#B45309;"
        top_icon_svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>'
        meta_chip = '<span style="background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; border:1px solid #D97706; font-size:11px; font-weight:800; padding:3px 12px; border-radius:12px; display:inline-flex; align-items:center; gap:4px; box-shadow:0 2px 6px rgba(245,158,11,0.4);">🏆 Badge Earned • Completed</span>'

        tot_m = earned_asm.total_marks if earned_asm else 45.0
        pct_m = earned_asm.percentage if earned_asm else 90.0
        bu_m = earned_asm.business_understanding if earned_asm else 9.0
        ar_m = earned_asm.architecture_report if earned_asm else 9.0
        tk_m = earned_asm.technical_knowledge if earned_asm else 9.0
        pr_m = earned_asm.presentation if earned_asm else 9.0
        qa_m = earned_asm.qa if earned_asm else 9.0
        fb_txt = (earned_asm.overall_feedback or earned_asm.remarks) if earned_asm else "Exemplary architecture spec and implementation. Enterprise-grade pipeline approved."
        str_txt = earned_asm.strength_areas if earned_asm else "Robust technical architecture patterns and clean modular code."
        imp_txt = earned_asm.improvement_areas if earned_asm else "Maintain comprehensive test coverage for future releases."

        eval_chain_chips = []
        if awarded_on_str:
            eval_chain_chips.append(
                f'<span style="font-size:11.5px; font-weight:700; color:#78350F; background:rgba(255,255,255,0.85); border:1px solid rgba(245,158,11,0.45); padding:3px 10px; border-radius:999px;">📅 Awarded: <strong>{escape(awarded_on_str)}</strong></span>'
            )
        if rev_earned_asm:
            eval_chain_chips.append(
                f'<span style="font-size:11.5px; font-weight:700; color:#0369A1; background:rgba(224,242,254,0.9); border:1px solid rgba(2,132,199,0.3); padding:3px 10px; border-radius:999px;">Peer Reviewer ({escape(rev_earned_asm.reviewer_name)}): <strong>{rev_earned_asm.total_marks:.1f}/50 ({rev_earned_asm.percentage:.1f}%)</strong></span>'
            )
        if grd_earned_asm:
            eval_chain_chips.append(
                f'<span style="font-size:11.5px; font-weight:700; color:#047857; background:rgba(209,250,229,0.9); border:1px solid rgba(16,185,129,0.35); padding:3px 10px; border-radius:999px;">Guardian Final ({escape(grd_earned_asm.reviewer_name)}): <strong>{grd_earned_asm.total_marks:.1f}/50 ({grd_earned_asm.percentage:.1f}%)</strong></span>'
            )
        eval_chain_html = (
            f'<div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:12px;">{"".join(eval_chain_chips)}</div>'
            if eval_chain_chips else ""
        )

        sub_rec_html = ""
        if existing_sub:
            p_name = getattr(existing_sub, "pdf_name", "") or (existing_sub.file_name if getattr(existing_sub, "submission_type", "") == "pdf" else "") or "Report.pdf"
            c_name = getattr(existing_sub, "code_name", "") or (existing_sub.file_name if getattr(existing_sub, "submission_type", "") == "code" else "") or "solution.py"
            g_url = getattr(existing_sub, "github_url", "") or (existing_sub.payload if getattr(existing_sub, "submission_type", "") == "github" else "") or ""
            s_dt = (getattr(existing_sub, "submitted_at", "") or "")[:16].replace("T", " ")
            g_chip = (
                f'<span style="font-size:11.5px; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{get_icon("github", 12)} {escape(g_url.split("/")[-1] if "/" in g_url else g_url)}</span>'
                if g_url else ""
            )
            sub_rec_html = f"""
            <div style="background:rgba(255,255,255,0.92); border:1px solid rgba(245,158,11,0.35); border-radius:var(--radius-sm); padding:10px 14px; margin-bottom:12px;">
                <div style="font-size:10.5px; font-weight:800; color:#92400E; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">
                    Certified Submission Artifacts &bull; Attempt #{getattr(existing_sub, 'attempt_number', 1)} {f'({escape(s_dt)} UTC)' if s_dt else ''}
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                    <span style="font-size:11.5px; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{get_icon("file_text", 12)} {escape(p_name)}</span>
                    <span style="font-size:11.5px; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{get_icon("code", 12)} {escape(c_name)}</span>
                    {g_chip}
                </div>
            </div>
            """

        earn_section_html = f"""
        <!-- SECTION 2: BADGE EARNED & ALLOCATED MARKS (GOLD) -->
        <div id="badge-section-earn" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:2px solid #F59E0B; padding:20px 24px; background:linear-gradient(135deg, rgba(254,243,199,0.98) 0%, rgba(253,230,138,0.7) 100%); box-shadow:0 6px 20px rgba(245,158,11,0.25);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; margin-bottom:14px; border-bottom:1.5px solid rgba(245,158,11,0.3); padding-bottom:12px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <span style="width:36px; height:36px; border-radius:50%; background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:18px; box-shadow:0 2px 8px rgba(245,158,11,0.4);">
                        🏆
                    </span>
                    <div>
                        <div style="font-size:16px; font-weight:900; color:#78350F; letter-spacing:-0.2px;">Badge Earned &amp; Certified!</div>
                        <div style="font-size:12.5px; color:#92400E; margin-top:2px;">Congratulations! Your milestone project has been officially evaluated, approved, and certified.</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    {project_allocated_btn_html}
                    <span style="font-family:var(--font-family-mono); font-size:14.5px; font-weight:900; color:#78350F; background:#FFFFFF; border:2px solid #F59E0B; padding:6px 16px; border-radius:20px; box-shadow:0 2px 8px rgba(245,158,11,0.2);">
                        Allocated Marks: {tot_m:.1f} / 50.0 ({pct_m:.1f}%)
                    </span>
                </div>
            </div>

            {eval_chain_html}
            {sub_rec_html}

            <!-- Rubric Criteria Scores Grid -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:14px;">
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Business Underst.</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{bu_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Architecture</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{ar_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Technical Knowl.</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{tk_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Presentation</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{pr_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Q&amp;A Defense</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{qa_m:.1f} / 10</div>
                </div>
            </div>

            <!-- Evaluator Feedback Section -->
            <div style="background:#FFFFFF; border:1.5px solid rgba(245,158,11,0.35); border-radius:var(--radius-sm); padding:14px 16px;">
                <div style="font-size:11px; font-weight:800; color:#92400E; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">Evaluator Feedback &amp; Certification Remarks:</div>
                <div style="font-size:13px; color:#78350F; line-height:1.55; font-style:italic; margin-bottom:10px;">
                    "{escape(fb_txt)}"
                </div>
                {f'<div style=\"font-size:12px; color:#92400E; margin-bottom:4px;\"><strong>Key Strengths:</strong> {escape(str_txt)}</div>' if str_txt else ''}
                {f'<div style=\"font-size:12px; color:#92400E;\"><strong>Recommendations:</strong> {escape(imp_txt)}</div>' if imp_txt else ''}
            </div>
        </div>
        """
    else:
        top_card_style = "border:2px solid var(--deep-frozen-midnight); background:linear-gradient(135deg, rgba(255,255,255,0.99) 0%, rgba(234,244,255,0.92) 100%); box-shadow:0 12px 36px rgba(7,22,41,0.12);"
        top_icon_style = "background:linear-gradient(135deg, rgba(234,244,255,1) 0%, rgba(157,183,213,0.3) 100%); border:1.5px solid var(--icy-steel); color:var(--deep-frozen-midnight);"
        top_icon_svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>'
        if has_allocated_project:
            meta_chip = '<span style="background:rgba(2,132,199,0.12); color:#0284C7; border:1px solid rgba(2,132,199,0.3); font-size:11px; font-weight:800; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">🚀 Project Allocated</span>'
        else:
            meta_chip = '<span style="background:rgba(16,185,129,0.12); color:#047857; border:1px solid rgba(16,185,129,0.3); font-size:11px; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Allocated Project</span>'

        if existing_sub and getattr(existing_sub, "status", "") == "reviewer_assessed":
            earn_section_html = f"""
            <!-- SECTION 2: EARN THE BADGE (REVIEWER ASSESSED) -->
            <div id="badge-section-earn" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #06B6D4; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; background:rgba(255,255,255,0.98);">
                <div style="display:flex; align-items:flex-start; gap:12px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(6,182,212,0.12); color:#0891B2; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
                    </span>
                    <div>
                        <div style="font-size:15px; font-weight:800; color:#0891B2;">Reviewer Evaluation Complete</div>
                        <div style="font-size:13px; color:var(--frost-navy-75); margin-top:2px;">Your assigned reviewer has evaluated your deliverables. Awaiting Guardian final approval and badge award.</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    {project_allocated_btn_html}
                    <span style="background:rgba(6,182,212,0.15); color:#0891B2; padding:4px 14px; border-radius:20px; font-size:12px; font-weight:700; border:1px solid rgba(6,182,212,0.3);">
                        Awaiting Guardian Award
                    </span>
                </div>
            </div>
            """
        elif existing_sub and getattr(existing_sub, "status", "") in ("pending", "submitted"):
            earn_section_html = f"""
            <!-- SECTION 2: EARN THE BADGE (PENDING REVIEW) -->
            <div id="badge-section-earn" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #3B82F6; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; background:rgba(255,255,255,0.98);">
                <div style="display:flex; align-items:flex-start; gap:12px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(59,130,246,0.12); color:#1D4ED8; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
                    </span>
                    <div>
                        <div style="font-size:15px; font-weight:800; color:#1D4ED8;">Earn the Badge</div>
                        <div style="font-size:13px; color:var(--frost-navy-75); margin-top:2px;">Deliverables routed to assigned reviewer <strong>{escape(rev_name_str)}</strong> — evaluation in progress.</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    {project_allocated_btn_html}
                    <span style="background:rgba(245,158,11,0.15); color:#B45309; padding:4px 14px; border-radius:20px; font-size:12px; font-weight:700; border:1px solid rgba(245,158,11,0.3);">
                        Pending Reviewer Evaluation
                    </span>
                    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('open_submission_modal', '{badge.id}')" style="font-weight:700; font-size:12px;">
                        Edit Deliverables
                    </button>
                </div>
            </div>
            """
        else:
            earn_section_html = f"""
            <!-- SECTION 2: EARN THE BADGE (READY TO SUBMIT) -->
            <div id="badge-section-earn" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #3B82F6; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; background:rgba(255,255,255,0.98);">
                <div style="display:flex; align-items:flex-start; gap:12px; flex:1; min-width:260px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(59,130,246,0.12); color:#1D4ED8; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
                    </span>
                    <div>
                        <div style="font-size:15px; font-weight:800; color:#1D4ED8;">Earn the Badge</div>
                        <div style="font-size:13px; color:var(--frost-navy-75); margin-top:2px;">Submit your project deliverables (Source Code, PDF Report, and GitHub URL) to earn this badge.</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <span style="background:rgba(16,185,129,0.15); color:#047857; padding:4px 14px; border-radius:20px; font-size:12px; font-weight:700; border:1px solid rgba(16,185,129,0.3);">
                        Allocated Milestone
                    </span>
                    {project_allocated_btn_html}
                    <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_submission_modal', '{badge.id}')" style="font-weight:800; font-size:12.5px; padding:6px 18px;">
                        Submit Deliverables &rarr;
                    </button>
                </div>
            </div>
            """

    allocated_project_section_html = ""
    if has_allocated_project:
        allocated_project_section_html = _render_allocated_project_detail_section(
            badge=badge,
            assigned_proj=assigned_proj,
            rev_name_str=rev_name_str,
            rev_band_str=rev_band_str,
            window_str=window_str,
            sub_deadline_str=sub_deadline_str,
            is_earned=is_earned,
            existing_sub=existing_sub
        )

    retake_banner = ""
    if is_retake and existing_sub:
        latest_asm = store.get_assessment_for_submission(existing_sub.id) if store else None
        feedback_txt = latest_asm.overall_feedback if latest_asm else "Revisions required."
        score_txt = f"{latest_asm.total_marks:.1f}/50 ({latest_asm.percentage:.1f}%)" if latest_asm else "Score below threshold"
        retake_banner = f"""
        <div style="background:linear-gradient(135deg, rgba(254,242,242,0.95) 0%, rgba(254,226,226,0.9) 100%); border:1.5px solid #EF4444; border-radius:var(--radius-sm); padding:16px 20px; margin-bottom:20px; box-shadow:0 4px 14px rgba(239,68,68,0.12);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:8px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="background:#EF4444; color:#fff; font-size:10.5px; font-weight:800; padding:2px 8px; border-radius:10px;">RETAKE REQUIRED</span>
                    <span style="font-weight:800; font-size:13.5px; color:#991B1B;">Attempt #{existing_sub.attempt_number} Did Not Meet Passing Threshold</span>
                </div>
                <span style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:#DC2626;">Previous Score: {score_txt}</span>
            </div>
            <p style="font-size:12.5px; color:#7F1D1D; margin:0 0 8px 0; line-height:1.4;">
                <strong>Guardian Feedback:</strong> {escape(feedback_txt)}
            </p>
            <div style="font-size:11.5px; color:#B91C1C;">
                Please review the feedback above, improve your technical deliverable, and submit revised materials for <strong>Attempt #{next_attempt}</strong>. Your Attempt #{existing_sub.attempt_number} history is preserved in your permanent record.
            </div>
        </div>
        """

    mapping_info_banner = ""
    if rev_id_str or window_str or sub_deadline_str:
        rev_full = f"{rev_name_str} (Band {rev_band_str})" if rev_band_str else rev_name_str
        mapping_info_banner = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding:10px 14px; background:rgba(234,244,255,0.7); border:1px solid var(--icy-steel-40); border-radius:var(--radius-sm); margin-bottom:18px;">
            {f'<div style="font-size:12px; color:var(--frost-navy);"><strong>Assigned Peer Reviewer:</strong> <span style="font-weight:700; color:var(--deep-frozen-midnight);">{escape(rev_full)}</span></div>' if rev_id_str else ''}
            {f'<div style="font-size:12px; color:var(--frost-navy-75);"><strong>Review Window:</strong> <span style="font-family:var(--font-family-mono); font-weight:700;">{escape(window_str)}</span></div>' if window_str else ''}
            {f'<div style="font-size:12px; color:#DC2626;"><strong>Submission Deadline:</strong> <span style="font-family:var(--font-family-mono); font-weight:700;">{escape(sub_deadline_str)}</span></div>' if sub_deadline_str else ''}
        </div>
        """

    top_back_header_html = ""
    if is_standalone_page:
        top_back_header_html = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')" style="font-weight:700; display:inline-flex; align-items:center; gap:6px; padding:7px 14px;">
                <span>&larr;</span>
                <span>Back to Badges</span>
            </button>
            <span style="font-size:12px; font-weight:700; color:var(--frost-navy-50);">
                Badge Workspace &bull; Band {escape(selected_band)} &bull; {escape(badge_code)}
            </span>
        </div>
        """
        location_right_btn = f"""
        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')" style="font-size:12px; font-weight:700; display:inline-flex; align-items:center; gap:5px; background:rgba(23,52,92,0.08); border-color:var(--icy-steel);">
            <span>&larr;</span>
            <span>All Badges</span>
        </button>
        """
        footer_left_btn = f"""
        <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')" style="font-weight:700; display:inline-flex; align-items:center; gap:6px;">
            <span>&larr;</span>
            <span>Back to All Badges</span>
        </button>
        """
        wrapper_style = f"padding:28px 32px; border-radius:var(--radius-lg); {top_card_style} transition:all 0.25s ease;"
        wrapper_classes = "liquid-glass-card badge-detail-page-card"
    else:
        location_right_btn = f"""
        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('toggle_cosmonaut_badge_card', '{badge.id}')" style="font-size:12px; font-weight:700; display:inline-flex; align-items:center; gap:5px; background:rgba(23,52,92,0.08); border-color:var(--icy-steel);">
            <span>Collapse Badge</span>
            <span>▲</span>
        </button>
        """
        footer_left_btn = f"""
        <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('toggle_cosmonaut_badge_card', '{badge.id}')" style="font-weight:700; display:inline-flex; align-items:center; gap:6px;">
            <span>Collapse Badge Details</span>
            <span>▲</span>
        </button>
        """
        wrapper_style = f"grid-column: 1 / -1; padding:28px 32px; border-radius:var(--radius-lg); {top_card_style} transition:all 0.25s ease;"
        wrapper_classes = "liquid-glass-card badge-card-item expanded-badge-card"

    if is_earned:
        footer_right_btn = f"""
        <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')" style="font-weight:800; padding:9px 20px; display:inline-flex; align-items:center; gap:8px; background:linear-gradient(135deg, #F59E0B, #D97706); border-color:#D97706;">
            {get_icon("award", 14)}<span>View Official Marksheet</span>{get_icon("arrow_right", 13)}
        </button>
        """
    else:
        footer_right_btn = f"""
        <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('open_submission_modal', '{badge.id}')" style="font-weight:800; padding:9px 20px; display:inline-flex; align-items:center; gap:8px;">
            {btn_icon}
            <span>{btn_label}</span>
            {get_icon("arrow_right", 13)}
        </button>
        """

    return f"""
    <div>
        {top_back_header_html}
        <div class="{wrapper_classes}" id="badge-card-{badge.id}" data-badge-id="{badge.id}" style="{wrapper_style}">
            <!-- LOCATION BAR & ACTIONS -->
            <div style="padding:14px 20px; border-radius:var(--radius-md); background:linear-gradient(135deg, rgba(23,52,92,0.06) 0%, rgba(157,183,213,0.18) 100%); border:1.5px solid var(--deep-frozen-midnight); margin-bottom:22px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
                <div>
                    <span style="font-size:10.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--deep-frozen-midnight);">
                        Badge Location
                    </span>
                    <div style="font-size:14px; font-weight:800; color:var(--frost-navy); margin-top:5px; display:flex; align-items:center; flex-wrap:wrap; gap:8px;">
                        <span style="color:var(--deep-frozen-midnight); font-size:14.5px; font-weight:800;">{escape(badge_title)}</span>
                        <span style="color:var(--frost-navy-50); font-weight:800; font-size:13px;">&rarr;</span>
                        <span style="background:rgba(6,182,212,0.12); color:#0891B2; padding:3px 10px; border-radius:14px; font-size:12px; font-weight:700; border:1px solid rgba(6,182,212,0.25);">{escape(active_skill)}</span>
                        <span style="color:var(--frost-navy-50); font-weight:800; font-size:13px;">&rarr;</span>
                        <span style="background:rgba(59,130,246,0.12); color:#1D4ED8; padding:3px 10px; border-radius:14px; font-size:12px; font-weight:700; border:1px solid rgba(59,130,246,0.25);">{escape(active_cap)}</span>
                        <span style="color:var(--frost-navy-50); font-weight:800; font-size:13px;">&rarr;</span>
                        <span style="background:rgba(139,92,246,0.12); color:#7C3AED; padding:3px 10px; border-radius:14px; font-size:12px; font-weight:700; border:1px solid rgba(139,92,246,0.25);">{escape(active_power)}</span>
                        <span style="color:var(--frost-navy-50); font-weight:800; font-size:13px;">&rarr;</span>
                        <span style="background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 10px; border-radius:14px; font-size:12px; font-weight:800;">Band {selected_band}</span>
                    </div>
                </div>
                <div style="display:flex; gap:10px; align-items:center; flex-shrink:0;">
                    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.toggleAllBadgeSections()" style="font-size:12px; font-weight:700;">
                        Toggle All
                    </button>
                    {location_right_btn}
                </div>
            </div>

            <!-- BADGE HEADER (ICON + TITLE + DESCRIPTION) -->
            <div style="margin-bottom:18px; display:flex; align-items:flex-start; gap:16px;">
                <div style="width:48px; height:48px; border-radius:50%; {top_icon_style} display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                    {top_icon_svg}
                </div>
                <div style="flex:1;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap;">
                        <span style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 9px; border-radius:var(--radius-xs); letter-spacing:0.5px;">BAND {selected_band}</span>
                        {f'<span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--frost-mist); color:var(--deep-frozen-midnight); padding:3px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30);">{escape(badge_code)}</span>' if badge_code else ''}
                        {meta_chip}
                        <h2 style="font-size:1.45rem; font-weight:800; color:var(--frost-navy); margin:0 0 0 4px;">{escape(badge_title)}</h2>
                    </div>
                    <p style="font-size:13.5px; color:var(--frost-navy-75); line-height:1.5; margin:0;">{escape(badge_desc)}</p>
                </div>
            </div>

            {mapping_info_banner}
            {retake_banner}

            <!-- SECTION 1: OUTCOMES -->
            <div id="badge-section-outcomes" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #10B981; overflow:hidden; background:rgba(255,255,255,0.98);">
                <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('outcomes')">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="width:28px; height:28px; border-radius:6px; background:rgba(16,185,129,0.12); color:#047857; display:flex; align-items:center; justify-content:center;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
                        </span>
                        <span style="font-size:15px; font-weight:800; color:#047857;">Outcomes ({len(outcomes)})</span>
                    </div>
                    <span id="chevron-outcomes" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
                </div>
                <div id="content-outcomes" style="padding:0 20px 18px 20px; display:block;">
                    {outcomes_html}
                </div>
            </div>

            {earn_section_html}
            {allocated_project_section_html}

            <!-- SECTION 3: PRACTICE PROJECT -->
            <div id="badge-section-practice" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #F97316; overflow:hidden; background:rgba(255,255,255,0.98);">
                <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('practice')">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="width:28px; height:28px; border-radius:6px; background:rgba(249,115,22,0.12); color:#F97316; display:flex; align-items:center; justify-content:center;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m14 2-4 0"/><path d="M10 2v7.5L5 19a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3L14 9.5V2"/></svg>
                        </span>
                        <span style="font-size:15px; font-weight:800; color:#EA580C;">Practice Project</span>
                    </div>
                    <span id="chevron-practice" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
                </div>
                <div id="content-practice" style="padding:0 20px 20px 20px; display:block;">
                    <p style="font-size:13px; color:var(--frost-navy-75); margin:0 0 14px 0;">Want some hands-on practice? Use this prompt to generate a practice project.</p>
                    <div style="background:rgba(241,245,249,0.85); border:1px solid var(--icy-steel-40); border-radius:var(--radius-md); padding:16px; position:relative;">
                        <div id="practice-prompt-text" style="font-size:12.5px; color:var(--frost-navy); line-height:1.65; white-space:pre-wrap; font-family:var(--font-family-sans);">{escape(practice_prompt)}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid rgba(157,183,213,0.3); flex-wrap:wrap; gap:10px;">
                            <span style="font-size:11.5px; color:var(--frost-navy-50);">This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge.</span>
                            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('practice-prompt-text', this)" style="font-size:11.5px; font-weight:700; display:inline-flex; align-items:center; gap:6px;">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                                Copy
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- SECTION 4: LEARNING TOPICS -->
            <div id="badge-section-topics" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #06B6D4; overflow:hidden; background:rgba(255,255,255,0.98);">
                <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('topics')">
                    <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                        <span style="width:28px; height:28px; border-radius:6px; background:rgba(6,182,212,0.12); color:#0E7490; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>
                        </span>
                        <span style="font-size:15px; font-weight:800; color:#0891B2;">Learning Topics</span>
                        <span id="topics-summary-pill" style="background:{'rgba(16,185,129,0.15)' if progress_pct > 0 else 'rgba(157,183,213,0.18)'}; color:{'#10B981' if progress_pct > 0 else 'var(--frost-navy-50)'}; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:700; border:1px solid {'rgba(16,185,129,0.3)' if progress_pct > 0 else 'rgba(157,183,213,0.3)'};">
                            {completed_topics_count}/{total_topics} Completed
                        </span>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <div style="width:130px; height:8px; border-radius:4px; background:rgba(157,183,213,0.3); overflow:hidden;">
                                <div id="topics-progress-bar" style="width:{progress_pct}%; height:100%; background:linear-gradient(90deg, #06B6D4, #10B981); border-radius:4px; transition:width 0.4s ease;"></div>
                            </div>
                            <span id="topics-progress-text" style="font-size:12px; font-weight:800; color:#0891B2; min-width:36px;">{progress_pct}%</span>
                        </div>
                    </div>
                    <span id="chevron-topics" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
                </div>
                <div id="content-topics" style="padding:0 20px 20px 20px; display:block;">
                    {topics_html}
                </div>
            </div>

            <!-- SECTION 5: LEARNING RESOURCES -->
            <div id="badge-section-resources" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #3B82F6; overflow:hidden; background:rgba(255,255,255,0.98);">
                <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('resources')">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="width:28px; height:28px; border-radius:6px; background:rgba(59,130,246,0.12); color:#1D4ED8; display:flex; align-items:center; justify-content:center;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                        </span>
                        <span style="font-size:15px; font-weight:800; color:#1D4ED8;">Learning Resources</span>
                    </div>
                    <span id="chevron-resources" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
                </div>
                <div id="content-resources" style="padding:0 20px 20px 20px; display:block;">
                    <p style="font-size:13px; color:var(--frost-navy-75); margin:0 0 14px 0;">Not sure where to start learning? Use this prompt to find free resources tailored to this badge.</p>
                    <div style="background:rgba(241,245,249,0.85); border:1px solid var(--icy-steel-40); border-radius:var(--radius-md); padding:16px; position:relative;">
                        <div id="resources-prompt-text" style="font-size:12.5px; color:var(--frost-navy); line-height:1.65; white-space:pre-wrap; font-family:var(--font-family-sans);">{escape(resources_prompt)}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid rgba(157,183,213,0.3); flex-wrap:wrap; gap:10px;">
                            <span style="font-size:11.5px; color:var(--frost-navy-50);">This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources.</span>
                            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('resources-prompt-text', this)" style="font-size:11.5px; font-weight:700; display:inline-flex; align-items:center; gap:6px;">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                                Copy
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- SECTION 6: RELATED SKILLS, CAPABILITIES & POWERS -->
            <div id="badge-section-related" class="liquid-glass-card" style="margin-bottom:20px; border-radius:var(--radius-lg); border:1.5px solid #8B5CF6; overflow:hidden; background:rgba(255,255,255,0.98);">
                <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('related')">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="width:28px; height:28px; border-radius:6px; background:rgba(139,92,246,0.12); color:#8B5CF6; display:flex; align-items:center; justify-content:center;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
                        </span>
                        <span style="font-size:15px; font-weight:800; color:#7C3AED;">Related Skills, Capabilities &amp; Powers</span>
                    </div>
                    <span id="chevron-related" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
                </div>
                <div id="content-related" style="padding:0 20px 20px 20px; display:block;">
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:20px;">
                        <div>
                            <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Skills</div>
                            <span style="background:rgba(6,182,212,0.12); color:#0891B2; padding:5px 14px; border-radius:20px; font-size:12.5px; font-weight:700; display:inline-block; border:1px solid rgba(6,182,212,0.25);">{escape(active_skill)}</span>
                        </div>
                        <div>
                            <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Capabilities</div>
                            <span style="background:rgba(59,130,246,0.12); color:#1D4ED8; padding:5px 14px; border-radius:20px; font-size:12.5px; font-weight:700; display:inline-block; border:1px solid rgba(59,130,246,0.25);">{escape(active_cap)}</span>
                        </div>
                        <div>
                            <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Powers</div>
                            <span style="background:rgba(139,92,246,0.12); color:#7C3AED; padding:5px 14px; border-radius:20px; font-size:12.5px; font-weight:700; display:inline-block; border:1px solid rgba(139,92,246,0.25);">{escape(active_power)}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- BADGE DETAIL FOOTER ACTIONS -->
            <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; padding-top:16px; border-top:1.5px solid var(--icy-steel-30); margin-top:20px; flex-wrap:wrap;">
                {footer_left_btn}
                {footer_right_btn}
            </div>
        </div>
    </div>
    """


def render_cosmonaut_badge_detail_page(
    badge: Optional[Badge],
    current_user: Optional[User] = None,
    store: Any = None,
    submissions: Optional[List[ProjectSubmission]] = None
) -> str:
    """Renders the dedicated single-badge workspace page with complete curriculum details, allocated project view, and deliverable submission modal trigger."""
    if not badge:
        return """
        <div class="liquid-glass-card" style="padding:40px; text-align:center;">
            <h3 style="color:var(--frost-navy); margin:0 0 8px 0;">Badge Not Found</h3>
            <p style="font-size:13px; color:var(--frost-navy-50); margin:0 0 16px 0;">The selected milestone badge could not be loaded.</p>
            <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">&larr; Back to Badges</button>
        </div>
        """

    user_subs = submissions if submissions is not None else (
        store.get_submissions_for_cosmonaut(current_user.id, badge.id) if (store and current_user) else []
    )
    badge_subs = sorted([s for s in user_subs if s.badge_id == badge.id], key=lambda s: getattr(s, "attempt_number", 1))
    latest_sub = badge_subs[-1] if badge_subs else None
    return render_cosmonaut_badge_card_expanded_content(
        badge=badge,
        current_user=current_user,
        existing_sub=latest_sub,
        is_standalone_page=True
    )


def render_cosmonaut_allocated_project_modal(badge: Badge, current_user: User, store: Any) -> str:
    """Renders the dedicated popup modal showing the project allocated to this cosmonaut by their mapped reviewer."""
    badge_title = getattr(badge, "title", "Milestone Badge")
    badge_code = getattr(badge, "code", "")
    badge_band = getattr(badge, "target_band", "B1")

    selected_tl = store.get_timeline(badge.id, current_user.id) if (store and current_user) else None
    rev_id = getattr(selected_tl, "reviewer_id", "") if selected_tl else ""
    if not rev_id and store and current_user:
        for m in store.get_band_mappings():
            m_b = m.get("badge_id") or m.get("badge")
            if current_user.id in m.get("cosmonauts", []) and m.get("reviewers") and m_b in (badge.id, badge.code, badge.title):
                rev_id = m["reviewers"][0]
                break
    if not rev_id:
        rev_id = getattr(badge, "assigned_reviewer_id", "") or ""
    rev_user = store.get_user_by_id(rev_id) if (store and rev_id) else None
    rev_name = rev_user.name if rev_user else (rev_id or "Assigned Reviewer")
    rev_band = getattr(rev_user, "band", "") if rev_user else ""

    window_str = ""
    sub_deadline_str = ""
    if selected_tl and getattr(selected_tl, "review_window_json", None):
        try:
            rw_list = json.loads(selected_tl.review_window_json)
            if isinstance(rw_list, list) and rw_list:
                window_str = " → ".join(rw_list)
        except Exception:
            window_str = ""
    if selected_tl and getattr(selected_tl, "submission_deadline", ""):
        sub_deadline_str = selected_tl.submission_deadline
    elif getattr(badge, "default_timeline", None) and badge.default_timeline.get("submission_deadline"):
        sub_deadline_str = badge.default_timeline.get("submission_deadline", "")

    assigned_proj = store.get_project_prompt_for_cadet(badge.id, current_user.id) if (store and current_user) else None
    if not assigned_proj or getattr(assigned_proj, "status", "") not in ("released", "sent"):
        return f"""
        <div style="padding:24px; text-align:center;">
            <div style="font-size:28px; margin-bottom:10px;">⏳</div>
            <h4 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0 0 8px 0;">Project Not Allocated Yet</h4>
            <p style="font-size:13px; color:var(--frost-navy-75); margin:0 0 18px 0;">
                Your mapped reviewer <strong>{escape(rev_name)}</strong> has not released the milestone project specification yet.
            </p>
            <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Close</button>
        </div>
        """

    user_subs = store.get_submissions_for_cosmonaut(current_user.id, badge.id) if (store and current_user) else []
    latest_sub = user_subs[-1] if user_subs else None
    is_earned = bool(
        (selected_tl and getattr(selected_tl, "status", "") == "completed")
        or (latest_sub and getattr(latest_sub, "status", "") == "approved")
        or (store and current_user and any(a.decision == "approve" for a in store.get_assessments_for_cosmonaut(current_user.id, badge.id)))
    )

    spec_html = _render_assigned_project_spec_inner(
        assigned_proj=assigned_proj,
        rev_name_str=rev_name,
        rev_band_str=rev_band,
        window_str=window_str,
        sub_deadline_str=sub_deadline_str,
        is_earned=is_earned,
        existing_sub=latest_sub,
        compact=False
    )

    if is_earned:
        cta_btn = f"""<button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')" style="display:inline-flex; align-items:center; gap:6px; font-weight:800; background:linear-gradient(135deg, #F59E0B, #D97706); border-color:#D97706;">{get_icon("award", 14)}<span>View Official Marksheet</span>{get_icon("arrow_right", 13)}</button>"""
    else:
        cta_txt = (
            f'{get_icon("edit", 14)}<span>Edit Deliverables</span>{get_icon("arrow_right", 13)}'
            if latest_sub
            else f'{get_icon("rocket", 14)}<span>Submit Deliverables</span>{get_icon("arrow_right", 13)}'
        )
        cta_btn = f"""<button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('open_submission_modal', '{escape(badge.id)}')" style="display:inline-flex; align-items:center; gap:6px; font-weight:800; background:linear-gradient(135deg, #059669 0%, #047857 100%); border-color:#059669;">{cta_txt}</button>"""

    return f"""
    <div style="padding:6px 4px;">
        <div style="padding:10px 14px; background:rgba(23,52,92,0.04); border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">{escape(badge_code)}</span>
                <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:#0284C7; color:#fff; padding:2px 7px; border-radius:var(--radius-xs);">BAND {escape(badge_band)}</span>
                <span style="font-size:12.5px; font-weight:800; color:var(--frost-navy);">{escape(badge_title)}</span>
            </div>
            <span style="font-size:11.5px; color:var(--frost-navy-50);">
                Mapped Reviewer: <strong style="color:#047857;">{escape(rev_name)}</strong>
            </span>
        </div>

        <div style="background:rgba(234,244,255,0.55); border:1.5px solid var(--icy-steel-50); border-radius:var(--radius-sm); padding:16px 20px; margin-bottom:18px;">
            {spec_html}
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; padding-top:12px; border-top:1px solid var(--icy-steel-30); flex-wrap:wrap; gap:10px;">
            <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">
                Close
            </button>
            {cta_btn}
        </div>
    </div>
    """


def render_cosmonaut_submission_workspace(
    badges: List[Badge],
    selected_badge_id: str,
    submissions: List[ProjectSubmission],
    current_user: Optional[User] = None,
    store: Any = None,
    expanded_badge_id: Optional[str] = None
) -> str:
    # Support direct callers passing expanded_badge_id by delegating cleanly to the dedicated badge detail page
    if expanded_badge_id:
        target_b = next((b for b in badges if b.id == expanded_badge_id), None)
        if target_b:
            return render_cosmonaut_badge_detail_page(
                badge=target_b,
                current_user=current_user,
                store=store,
                submissions=submissions
            )

    # 1. Build Allocated Badges Cards Grid (3x3 layout — strictly compact cards, opening separate dedicated badge pages)
    if badges:
        badge_cards = []
        for b in badges:
            b_subs = sorted([s for s in submissions if s.badge_id == b.id], key=lambda s: getattr(s, "attempt_number", 1))
            cadet_sub = b_subs[-1] if b_subs else None
            b_code = escape(getattr(b, "code", ""))
            b_title = escape(getattr(b, "title", "Milestone Badge"))
            b_band = escape(getattr(b, "target_band", "B1"))
            b_power = escape(getattr(b, "power", "Tech") or "Tech")
            b_cap = escape(getattr(b, "capability", "Data & Machine") or "Data & Machine")
            b_skill = escape(getattr(b, "skill", "Curation") or "Curation")

            tl = store.get_timeline(b.id, current_user.id) if (store and current_user) else None
            is_earned = (tl and getattr(tl, "status", "") == "completed") or (cadet_sub and getattr(cadet_sub, "status", "") == "approved")
            earned_card_asm = None
            if store and current_user:
                asms = sorted(
                    store.get_assessments_for_cosmonaut(current_user.id, b.id),
                    key=lambda x: (
                        getattr(x, "attempt_number", 1),
                        1 if getattr(x, "assessor_role", "") == "guardian" else 0,
                        getattr(x, "reviewed_at", ""),
                    ),
                )
                for a in asms:
                    if a.decision == "approve" or getattr(a, "assessor_role", "") == "guardian":
                        is_earned = True
                        earned_card_asm = a

            assigned_proj = store.get_project_prompt_for_cadet(b.id, current_user.id) if (store and current_user) else None
            has_proj = bool(assigned_proj and getattr(assigned_proj, "status", "") in ("released", "sent"))

            earned_meta_html = ""
            if is_earned:
                sub_chip = f'<span style="background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; border:1px solid #D97706; font-size:11px; font-weight:800; padding:3px 12px; border-radius:12px; display:inline-flex; align-items:center; gap:4px; box-shadow:0 2px 6px rgba(245,158,11,0.4);">{get_icon("award", 12)} Badge Earned • Completed</span>'
                action_btn_txt = "View Feedback & Marks"
                btn_color_style = "background:linear-gradient(135deg, #F59E0B 0%, #D97706 100%); color:#451A03; border-color:#D97706;"
                card_border_style = "border:2px solid #F59E0B; background:linear-gradient(135deg, rgba(254,243,199,0.98) 0%, rgba(253,230,138,0.6) 50%, rgba(254,243,199,0.98) 100%); box-shadow:0 0 20px rgba(245,158,11,0.35), 0 8px 24px rgba(180,83,9,0.15);"
                sc_str = f"{earned_card_asm.total_marks:.1f}/50 ({earned_card_asm.percentage:.1f}%)" if earned_card_asm else "Certified"
                aw_str = (getattr(tl, "actual_award_date", "") if tl else "") or (earned_card_asm.reviewed_at[:10] if earned_card_asm and getattr(earned_card_asm, "reviewed_at", "") else "Awarded")
                att_str = f"Attempt #{getattr(cadet_sub, 'attempt_number', getattr(earned_card_asm, 'attempt_number', 1))}" if (cadet_sub or earned_card_asm) else ""
                earned_meta_html = f"""
                <div style="margin-top:10px; padding:7px 10px; border-radius:8px; background:rgba(255,255,255,0.85); border:1px solid rgba(245,158,11,0.4); display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px; font-size:11.5px; color:#78350F; font-weight:700;">
                    <span style="font-family:var(--font-family-mono); font-weight:800;">Score: {escape(sc_str)}</span>
                    <span>&bull; Awarded: {escape(aw_str)}</span>
                    {f'<span>&bull; {escape(att_str)}</span>' if att_str else ''}
                </div>
                """
            elif cadet_sub and getattr(cadet_sub, "status", "") == "reviewer_assessed":
                sub_chip = '<span style="background:rgba(6,182,212,0.12); color:#0891B2; border:1px solid rgba(6,182,212,0.3); font-size:11px; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">Awaiting Guardian Award</span>'
                action_btn_txt = "View Assessment Status"
                btn_color_style = "background:linear-gradient(135deg, #0891B2 0%, #0e7490 100%); color:#fff; border-color:#0891B2;"
                card_border_style = "border:1.5px solid var(--icy-steel-40); background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(234,244,255,0.9) 100%); box-shadow:0 6px 24px rgba(7,22,41,0.06);"
            elif cadet_sub and getattr(cadet_sub, "status", "") in ("retake_required", "resubmission_requested"):
                sub_chip = f'<span style="background:rgba(239,68,68,0.12); color:#DC2626; border:1px solid rgba(239,68,68,0.3); font-size:11px; font-weight:800; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">{get_icon("alert_triangle", 12)} Retake Required</span>'
                action_btn_txt = "Open Badge & Resubmit"
                btn_color_style = "background:linear-gradient(135deg, #DC2626 0%, #B91C1C 100%); color:#fff; border-color:#DC2626;"
                card_border_style = "border:1.5px solid rgba(239,68,68,0.45); background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(254,242,242,0.85) 100%); box-shadow:0 6px 24px rgba(239,68,68,0.08);"
            elif cadet_sub:
                sub_chip = f'<span style="background:rgba(16,185,129,0.12); color:#047857; border:1px solid rgba(16,185,129,0.3); font-size:11px; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">{get_icon("check", 12)} Submitted</span>'
                action_btn_txt = "View Badge & Submission"
                btn_color_style = "background:linear-gradient(135deg, #059669 0%, #047857 100%); color:#fff; border-color:#059669;"
                card_border_style = "border:1.5px solid var(--icy-steel-40); background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(234,244,255,0.9) 100%); box-shadow:0 6px 24px rgba(7,22,41,0.06);"
            elif has_proj:
                sub_chip = f'<span class="status-pill status-active" style="background:rgba(2,132,199,0.12); color:#0284C7; border:1px solid rgba(2,132,199,0.3); font-size:11px; font-weight:800; padding:3px 12px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">{get_icon("rocket", 12)} Project Allocated</span>'
                action_btn_txt = "View Badge & Project"
                btn_color_style = "background:linear-gradient(135deg, #0284C7 0%, #0369A1 100%); color:#fff; border-color:#0284C7;"
                card_border_style = "border:1.5px solid rgba(2,132,199,0.4); background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(234,244,255,0.92) 100%); box-shadow:0 6px 24px rgba(2,132,199,0.08);"
            else:
                sub_chip = '<span style="background:rgba(234,244,255,0.8); color:var(--deep-frozen-midnight); border:1px solid var(--icy-steel-40); font-size:11px; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">Allocated Project</span>'
                action_btn_txt = "Open Badge Details"
                btn_color_style = ""
                card_border_style = "border:1.5px solid var(--icy-steel-40); background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(234,244,255,0.9) 100%); box-shadow:0 6px 24px rgba(7,22,41,0.06);"

            open_page_onclick = f"window.StarAppBridge.dispatchAction('open_cosmonaut_badge_page', '{b.id}')"
            open_btn_onclick = f"event.stopPropagation(); window.StarAppBridge.dispatchAction('open_cosmonaut_badge_page', '{b.id}')"

            # Initial collapsed card: strictly BAND, code, Allocated Project, hierarchy, and title
            badge_cards.append(f"""
            <div class="liquid-glass-card badge-card-item collapsed-badge-card" id="badge-card-{b.id}" data-badge-id="{b.id}" onclick="{open_page_onclick}" role="button" tabindex="0" style="padding:22px; border-radius:var(--radius-lg); {card_border_style} display:flex; flex-direction:column; justify-content:space-between; transition:transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease; cursor:pointer;" onmouseover="this.style.transform='translateY(-2px)';" onmouseout="this.style.transform='none';">
                <div>
                    <!-- Meta Row -->
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 9px; border-radius:var(--radius-xs); letter-spacing:0.5px;">BAND {b_band}</span>
                            {f'<span style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:800; background:var(--frost-mist); color:var(--deep-frozen-midnight); padding:3px 9px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30);">{b_code}</span>' if b_code else ''}
                        </div>
                        {sub_chip}
                    </div>

                    <!-- Connected Collapsible Taxonomy Lineage -->
                    <div style="margin-bottom:10px;">
                        {render_taxonomy_hierarchy_tree(getattr(b, "power", "Tech") or "Tech", getattr(b, "capability", "Data & Machine") or "Data & Machine", getattr(b, "skill", "Curation") or "Curation", compact=True)}
                    </div>

                    <!-- Headline Title -->
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0; letter-spacing:-0.2px; line-height:1.35;">
                        {b_title}
                    </h3>
                    {earned_meta_html}
                </div>

                <!-- Navigation to Dedicated Badge Detail Page -->
                <div style="margin-top:20px; padding-top:12px; border-top:1px dashed var(--icy-steel-30); display:flex; justify-content:space-between; align-items:center; gap:8px;">
                    <button type="button" class="btn-metal btn-sm" onclick="{open_btn_onclick}" style="font-weight:800; font-size:11.5px; padding:5px 14px; display:inline-flex; align-items:center; gap:5px; {btn_color_style}">
                        <span>{action_btn_txt}</span>
                        <span>&rarr;</span>
                    </button>
                    <span style="font-size:11px; color:var(--frost-navy-50); font-weight:700; background:rgba(23,52,92,0.06); padding:4px 8px; border-radius:10px;">Open Page &rarr;</span>
                </div>
            </div>
            """)

        badges_grid_html = f"""
        <div class="badges-grid-3x3" style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:20px; margin-bottom:32px;">
            {"".join(badge_cards)}
        </div>
        """
    else:
        badges_grid_html = """
        <div class="liquid-glass-card" style="padding:32px 24px; text-align:center; border-radius:var(--radius-lg); border:1.5px dashed var(--icy-steel-30); background:linear-gradient(135deg, rgba(255,255,255,0.92) 0%, rgba(234,244,255,0.7) 100%); margin-bottom:32px;">
            <div style="width:48px; height:48px; border-radius:50%; background:rgba(6,182,212,0.12); color:#0891B2; display:flex; align-items:center; justify-content:center; margin:0 auto 12px auto;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>
                </svg>
            </div>
            <h3 style="font-size:16px; font-weight:800; color:var(--frost-navy); margin:0 0 6px 0;">No Badges Allocated Yet</h3>
            <p style="font-size:13px; color:var(--frost-navy-75); max-width:540px; margin:0 auto 16px auto; line-height:1.5;">
                Your Guardian has not yet allocated curriculum badges to your profile. Once mapped and published, your assigned badges with learning outcomes and deliverables will appear here.
            </p>
        </div>
        """

    return f"""
    <div>
        <div style="display:flex; align-items:center; margin-bottom:16px;">
            {render_back_button()}
        </div>

        <!-- PAGE HEADER -->
        <div style="margin-bottom:28px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <h2 style="font-size:1.6rem; font-weight:800; color:var(--frost-navy); margin:0 0 6px 0; letter-spacing:-0.3px;">Allocated Badges &amp; Milestone Projects</h2>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:12px; font-weight:700; color:var(--frost-navy-50);">Allocated Badges:</span>
                    <span style="font-size:12px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 12px; border-radius:12px;">{len(badges)}</span>
                </div>
            </div>
        </div>

        <!-- 1. BADGES CARDS GRID -->
        {badges_grid_html}
    </div>
    """


def render_cosmonaut_submission_modal(badge: Badge, current_user: User, store: Any, existing_sub: Optional[ProjectSubmission] = None) -> str:
    """
    Renders the dedicated Project Deliverable Submission Portal modal popup for a specific badge.
    Allows Cosmonauts to submit deliverables for formal evaluation, or edit their existing submission.
    """
    import json
    badge_title = getattr(badge, "title", "Milestone Badge")
    badge_code = getattr(badge, "code", "")
    badge_band = getattr(badge, "target_band", "B1")
    badge_power = getattr(badge, "power", "Tech") or "Tech"
    badge_cap = getattr(badge, "capability", "Data & Machine") or "Data & Machine"
    badge_skill = getattr(badge, "skill", "Curation") or "Curation"

    # Assigned Reviewer & Window
    selected_tl = store.get_timeline(badge.id, current_user.id) if (store and current_user) else None
    rev_id = getattr(selected_tl, "reviewer_id", "") if selected_tl else getattr(badge, "assigned_reviewer_id", "")
    rev_user = store.get_user_by_id(rev_id) if (store and rev_id) else None
    rev_name = rev_user.name if rev_user else (rev_id or "Authorized Reviewer")
    rev_band = getattr(rev_user, "band", "") if rev_user else ""
    r_window = []
    if selected_tl and getattr(selected_tl, "review_window_json", None):
        try:
            r_window = json.loads(selected_tl.review_window_json)
        except Exception:
            r_window = []
    elif getattr(badge, "default_timeline", None) and badge.default_timeline.get("review_date"):
        r_window = [badge.default_timeline.get("review_date")]
    window_str = " &rarr; ".join(r_window) if r_window else "3-Day Review Window"

    # Assigned Project Specification from Reviewer
    assigned_proj = store.get_project_prompt_for_cadet(badge.id, current_user.id) if (store and current_user) else None
    assigned_project_banner = ""
    if assigned_proj and getattr(assigned_proj, "status", "") in ("released", "sent"):
        spec_inner = _render_assigned_project_spec_inner(
            assigned_proj=assigned_proj,
            rev_name_str=rev_name,
            rev_band_str=rev_band,
            window_str=window_str,
            existing_sub=existing_sub,
            compact=True
        )
        assigned_project_banner = f"""
        <div style="background:rgba(234,244,255,0.7); border:1.5px solid var(--icy-steel-50); border-radius:var(--radius-sm); padding:14px 18px; margin-bottom:18px;">
            {spec_inner}
        </div>
        """

    # Existing submission notice
    existing_notice = ""
    if existing_sub:
        submitted_at_fmt = getattr(existing_sub, "submitted_at", "")[:16].replace("T", " ")
        existing_notice = f"""
        <div style="background:rgba(16,185,129,0.08); border:1.5px solid rgba(16,185,129,0.3); border-radius:var(--radius-sm); padding:12px 16px; margin-bottom:16px;">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="background:#047857; color:#fff; font-size:10.5px; font-weight:800; padding:2px 8px; border-radius:10px;">SUBMISSION ACTIVE</span>
                    <span style="font-size:12.5px; font-weight:700; color:#047857;">Submitted on {escape(submitted_at_fmt)}</span>
                </div>
                <span style="font-size:11.5px; font-weight:700; color:var(--frost-navy-50);">Status: {escape(getattr(existing_sub, 'status', 'pending').upper())}</span>
            </div>
            <div style="font-size:11.5px; color:#065F46; margin-top:4px;">
                You can edit your deliverables below. Updating will replace your active deliverable files for formal evaluation.
            </div>
        </div>
        """

    current_pdf_hint = f'<div style="font-size:11px; color:#047857; font-weight:700; margin-top:3px;">Current file: {escape(existing_sub.pdf_name)}</div>' if (existing_sub and getattr(existing_sub, 'pdf_name', '')) else ''
    current_code_hint = f'<div style="font-size:11px; color:#047857; font-weight:700; margin-top:3px;">Current file: {escape(existing_sub.code_name)}</div>' if (existing_sub and getattr(existing_sub, 'code_name', '')) else ''
    gh_val = getattr(existing_sub, "github_url", "") if existing_sub else ""

    submit_btn_txt = (
        f'{get_icon("check_circle", 14)} Update Deliverables {get_icon("arrow_right", 13)}'
        if existing_sub
        else f'{get_icon("rocket", 14)} Submit Deliverables for Assessment {get_icon("arrow_right", 13)}'
    )

    return f"""
    <div style="padding:4px 0;">
        <!-- Hierarchy & Context Bar -->
        <div style="padding:10px 14px; background:rgba(23,52,92,0.04); border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">{escape(badge_code)}</span>
                <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:#06B6D4; color:#fff; padding:2px 7px; border-radius:var(--radius-xs);">BAND {escape(badge_band)}</span>
                <span style="font-size:12.5px; font-weight:800; color:var(--frost-navy);">{escape(badge_title)}</span>
            </div>
            <div style="font-size:11.5px; color:var(--frost-navy-50);">
                <span>Assigned Reviewer: <strong style="color:#047857;">{escape(rev_name)}</strong></span>
            </div>
        </div>

        {existing_notice}
        {assigned_project_banner}

        <form id="project-submission-form" onsubmit="event.preventDefault(); window.StarAppBridge.submitCosmonautDeliverables();">
            <input type="hidden" id="submission-badge-id" value="{escape(badge.id)}">

            <!-- 1. PDF Document Deliverable Field -->
            <div class="liquid-form-group" style="margin-bottom:18px;">
                <label class="liquid-form-label" for="submission-pdf-file" style="font-size:12px; font-weight:800; color:var(--frost-navy); display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                    {get_icon("file_text", 14)}<span>PDF Document Deliverable</span>
                </label>
                <input type="file" id="submission-pdf-file" class="liquid-glass-file-input" accept=".pdf">
                {current_pdf_hint}
                <span class="liquid-form-hint" style="font-size:11px; color:var(--frost-navy-50); display:block; margin-top:2px;">Upload design charter, architecture report, or technical documentation (.pdf)</span>
            </div>

            <!-- 2. Code / Script File Deliverable Field -->
            <div class="liquid-form-group" style="margin-bottom:18px;">
                <label class="liquid-form-label" for="submission-code-file" style="font-size:12px; font-weight:800; color:var(--frost-navy); display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                    {get_icon("code", 14)}<span>Code / Script File Deliverable</span>
                </label>
                <input type="file" id="submission-code-file" class="liquid-glass-file-input" accept=".py,.sql,.zip,.js,.json,.tar.gz,.txt">
                {current_code_hint}
                <span class="liquid-form-hint" style="font-size:11px; color:var(--frost-navy-50); display:block; margin-top:2px;">Upload executable script, pipeline package, queries, or zip archive (.py, .sql, .zip)</span>
            </div>

            <!-- 3. GitHub Repository Link Field -->
            <div class="liquid-form-group" style="margin-bottom:22px;">
                <label class="liquid-form-label" for="submission-github-url" style="font-size:12px; font-weight:800; color:var(--frost-navy); display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                    {get_icon("github", 14)}<span>GitHub Repository Link</span>
                </label>
                <input type="url" id="submission-github-url" class="liquid-glass-control" value="{escape(gh_val)}" placeholder="https://github.com/username/project-repo" style="width:100%; font-size:12.5px;">
                <span class="liquid-form-hint" style="font-size:11px; color:var(--frost-navy-50); display:block; margin-top:2px;">Direct URL to version-controlled repository or pull request</span>
            </div>

            <!-- Actions Row -->
            <div style="display:flex; justify-content:space-between; align-items:center; padding-top:14px; border-top:1px solid var(--icy-steel-30); flex-wrap:wrap; gap:10px;">
                <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">
                    Cancel
                </button>
                <button type="submit" class="btn-metal" style="padding:9px 24px; font-weight:800; background:linear-gradient(135deg, #059669 0%, #047857 100%); color:#fff; border-color:#059669; font-size:13px;">
                    {submit_btn_txt}
                </button>
            </div>
        </form>
    </div>
    """


# ==============================================================================
# 6.5.1 COSMONAUT BADGE PREVIEW MODAL (MATCHING GUARDIAN CREATION VIEW)
# ==============================================================================

def render_cosmonaut_badge_preview_modal(badge: Badge, current_user: Optional[User] = None) -> str:
    import json
    from starapp.badge_generator import (
        generate_badge_data, build_practice_project_prompt, build_learning_resources_prompt
    )

    badge_title = getattr(badge, "title", "Milestone Badge")
    badge_code = getattr(badge, "code", "")
    badge_desc = getattr(badge, "description", "")
    selected_band = getattr(badge, "target_band", "B1")
    active_power = getattr(badge, "power", "Tech") or "Tech"
    active_cap = getattr(badge, "capability", "Data & Machine") or "Data & Machine"
    active_skill = getattr(badge, "skill", "Curation") or "Curation"

    prompt_str = getattr(badge, "prompt_json", "{}")
    p_data = {}
    if prompt_str:
        try:
            p_data = json.loads(prompt_str) if isinstance(prompt_str, str) else prompt_str
            if not isinstance(p_data, dict):
                p_data = {}
        except Exception:
            p_data = {}

    # Extract outcomes
    outcomes = p_data.get("outcomes") or p_data.get("expected_outcomes") or getattr(badge, "learning_outcomes", [])
    if not outcomes:
        synth = generate_badge_data(selected_band, active_power, active_cap, active_skill, "")
        outcomes = synth.get("outcomes", [])

    # Extract practice prompt
    practice_prompt = ""
    if isinstance(p_data.get("practice_project"), dict):
        practice_prompt = p_data["practice_project"].get("prompt", "")
    if not practice_prompt:
        practice_prompt = p_data.get("practice_prompt", "")
    if not practice_prompt or len(practice_prompt.strip()) < 80:
        practice_prompt = getattr(badge, "project_requirements", "")
    if not practice_prompt or len(practice_prompt.strip()) < 80:
        practice_prompt = build_practice_project_prompt(
            badge_title, active_skill, active_cap, active_power, selected_band, [], outcomes
        )

    # Extract learning topics (expect 6)
    learning_topics = p_data.get("learning_topics", [])
    if not learning_topics or len(learning_topics) < 6:
        synth = generate_badge_data(selected_band, active_power, active_cap, active_skill, "")
        learning_topics = synth.get("learning_topics", [])

    total_topics = len(learning_topics) if learning_topics else 6
    completed_topics_count = sum(1 for t in learning_topics if t.get("completed", False) or t.get("status", "").lower() == "completed")
    progress_pct = int(round((completed_topics_count / total_topics) * 100)) if total_topics > 0 else 0

    # Extract learning resources prompt
    resources_prompt = ""
    if isinstance(p_data.get("learning_resources"), dict):
        resources_prompt = p_data["learning_resources"].get("prompt", "")
    if not resources_prompt:
        resources_prompt = p_data.get("resources_prompt", "")
    if not resources_prompt or len(resources_prompt.strip()) < 80:
        resources_prompt = build_learning_resources_prompt(
            badge_title, active_skill, active_cap, active_power, selected_band, learning_topics, outcomes
        )

    # Section 1: Outcomes HTML
    outcomes_list_items = "".join([
        f'''<div style="display:flex; align-items:flex-start; gap:12px; font-size:13px; color:var(--frost-navy); line-height:1.55; padding:10px 14px; background:rgba(234,244,255,0.45); border:1px solid rgba(16,185,129,0.25); border-radius:var(--radius-sm); margin-bottom:8px;">
            <span style="width:20px; height:20px; border-radius:50%; background:rgba(16,185,129,0.15); color:#047857; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; flex-shrink:0; margin-top:1px;">✓</span>
            <span style="font-weight:600; flex:1;">{escape(str(o))}</span>
        </div>'''
        for o in outcomes
    ])
    outcomes_html = f"""
    <div style="display:flex; flex-direction:column; gap:2px;">
        {outcomes_list_items}
    </div>
    """

    # Section 4: Topics HTML
    topics_card_items = []
    for idx, t in enumerate(learning_topics):
        t_title = t.get("title", "")
        t_desc = t.get("description", "")
        is_comp = t.get("completed", False) or t.get("status", "").lower() == "completed"

        border_color = "#10B981" if is_comp else "rgba(6,182,212,0.3)"
        bg_style = "background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(236,253,245,0.7) 100%);" if is_comp else "background:linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(234,244,255,0.85) 100%);"
        status_text = "Completed" if is_comp else "In Progress"
        status_bg = "rgba(16,185,129,0.15)" if is_comp else "rgba(157,183,213,0.18)"
        status_color = "#10B981" if is_comp else "var(--frost-navy-50)"
        status_border = "rgba(16,185,129,0.3)" if is_comp else "rgba(157,183,213,0.3)"

        btn_class = "is-completed" if is_comp else ""
        btn_bg = "#10B981" if is_comp else "rgba(255,255,255,0.9)"
        btn_color = "white" if is_comp else "var(--frost-navy-75)"
        btn_border = "#059669" if is_comp else "var(--icy-steel)"
        btn_shadow = "0 2px 8px rgba(16,185,129,0.3)" if is_comp else "none"
        btn_content = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Completed' if is_comp else "Mark Complete"

        topics_card_items.append(f"""
        <div id="topic-card-{idx}" class="topic-row-card" style="padding:16px 20px; border-radius:var(--radius-md); border:1.5px solid {border_color}; {bg_style} display:flex; justify-content:space-between; align-items:center; gap:20px; width:100%; box-sizing:border-box; transition:border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;">
            <div style="flex:1;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                    <span style="font-size:11px; font-weight:800; background:rgba(6,182,212,0.12); color:#0891B2; padding:3px 10px; border-radius:12px; border:1px solid rgba(6,182,212,0.25);">Topic {idx+1}</span>
                    <span id="topic-status-tag-{idx}" style="background:{status_bg}; color:{status_color}; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; border:1px solid {status_border}; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease;">{status_text}</span>
                    <span style="font-size:11px; color:var(--frost-navy-50); font-weight:600;">Curriculum Module</span>
                </div>
                <div style="font-size:14.5px; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">{escape(t_title)}</div>
                <div style="font-size:12.5px; color:var(--frost-navy-75); line-height:1.5;">{escape(t_desc)}</div>
            </div>
            <div style="flex-shrink:0;">
                <button type="button" id="topic-toggle-btn-{idx}" class="{btn_class}"
                    onclick="window.StarAppBridge.toggleTopicCompletion({idx})"
                    style="background:{btn_bg}; color:{btn_color}; border:1.5px solid {btn_border}; box-shadow:{btn_shadow}; font-size:12px; font-weight:800; padding:8px 16px; border-radius:20px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease, box-shadow 0.25s ease;">
                    {btn_content}
                </button>
            </div>
        </div>
        """)
    topics_html = f'<div id="topics-list-container" style="display:flex; flex-direction:column; gap:12px; width:100%; box-sizing:border-box;">{"".join(topics_card_items)}</div>'

    from starapp.storage import store
    is_earned = False
    earned_asm = None
    rev_name_str = "Assigned Reviewer"
    existing_sub = None
    if current_user and store:
        subs = store.get_submissions_for_cosmonaut(current_user.id, badge.id)
        existing_sub = subs[-1] if subs else None
        tl = store.get_timeline(badge.id, current_user.id)
        if tl and getattr(tl, "status", "") == "completed":
            is_earned = True
        if tl and getattr(tl, "reviewer_id", ""):
            r_u = store.get_user_by_id(tl.reviewer_id)
            if r_u:
                rev_name_str = r_u.name
        asms = store.get_assessments_for_cosmonaut(current_user.id, badge.id)
        for a in reversed(asms):
            if a.decision == "approve" or getattr(a, "assessor_role", "") == "guardian":
                is_earned = True
                earned_asm = a
                break
        if not earned_asm and existing_sub:
            sub_asm = store.get_assessment_for_submission(existing_sub.id)
            if existing_sub.status == "approved" or (sub_asm and sub_asm.decision == "approve"):
                is_earned = True
                earned_asm = sub_asm

    if is_earned:
        modal_top_style = "border:2px solid #F59E0B; background:linear-gradient(135deg, rgba(255,255,255,0.99) 0%, rgba(254,243,199,0.92) 100%);"
        top_icon_style = "background:linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%); border:2px solid #F59E0B; color:#B45309;"
        top_icon_svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>'
        meta_chip = '<span style="background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; border:1px solid #D97706; font-size:11px; font-weight:800; padding:3px 12px; border-radius:12px; display:inline-flex; align-items:center; gap:4px; box-shadow:0 2px 6px rgba(245,158,11,0.4);">🏆 Badge Earned • Completed</span>'

        tot_m = earned_asm.total_marks if earned_asm else 45.0
        pct_m = earned_asm.percentage if earned_asm else 90.0
        bu_m = earned_asm.business_understanding if earned_asm else 9.0
        ar_m = earned_asm.architecture_report if earned_asm else 9.0
        tk_m = earned_asm.technical_knowledge if earned_asm else 9.0
        pr_m = earned_asm.presentation if earned_asm else 9.0
        qa_m = earned_asm.qa if earned_asm else 9.0
        fb_txt = (earned_asm.overall_feedback or earned_asm.remarks) if earned_asm else "Exemplary architecture spec and implementation. Enterprise-grade pipeline approved."
        str_txt = earned_asm.strength_areas if earned_asm else "Robust technical architecture patterns and clean modular code."
        imp_txt = earned_asm.improvement_areas if earned_asm else "Maintain comprehensive test coverage for future releases."

        earn_section_html = f"""
        <!-- SECTION 2: BADGE EARNED & ALLOCATED MARKS (GOLD) -->
        <div id="badge-section-earn" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:2px solid #F59E0B; padding:20px 24px; background:linear-gradient(135deg, rgba(254,243,199,0.98) 0%, rgba(253,230,138,0.7) 100%); box-shadow:0 6px 20px rgba(245,158,11,0.25);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; margin-bottom:14px; border-bottom:1.5px solid rgba(245,158,11,0.3); padding-bottom:12px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <span style="width:36px; height:36px; border-radius:50%; background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:18px; box-shadow:0 2px 8px rgba(245,158,11,0.4);">
                        🏆
                    </span>
                    <div>
                        <div style="font-size:16px; font-weight:900; color:#78350F; letter-spacing:-0.2px;">Badge Earned &amp; Certified!</div>
                        <div style="font-size:12.5px; color:#92400E; margin-top:2px;">Congratulations! Your milestone project has been officially evaluated, approved, and certified.</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-family:var(--font-family-mono); font-size:14.5px; font-weight:900; color:#78350F; background:#FFFFFF; border:2px solid #F59E0B; padding:6px 16px; border-radius:20px; box-shadow:0 2px 8px rgba(245,158,11,0.2);">
                        Allocated Marks: {tot_m:.1f} / 50.0 ({pct_m:.1f}%)
                    </span>
                </div>
            </div>

            <!-- Rubric Criteria Scores Grid -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:14px;">
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Business Underst.</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{bu_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Architecture</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{ar_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Technical Knowl.</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{tk_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Presentation</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{pr_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:10.5px; font-weight:700; color:#92400E; text-transform:uppercase;">Q&amp;A Defense</div>
                    <div style="font-size:14px; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{qa_m:.1f} / 10</div>
                </div>
            </div>

            <!-- Evaluator Feedback Section -->
            <div style="background:#FFFFFF; border:1.5px solid rgba(245,158,11,0.35); border-radius:var(--radius-sm); padding:14px 16px;">
                <div style="font-size:11px; font-weight:800; color:#92400E; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">Evaluator Feedback &amp; Certification Remarks:</div>
                <div style="font-size:13px; color:#78350F; line-height:1.55; font-style:italic; margin-bottom:10px;">
                    "{escape(fb_txt)}"
                </div>
                {f'<div style=\"font-size:12px; color:#92400E; margin-bottom:4px;\"><strong>Key Strengths:</strong> {escape(str_txt)}</div>' if str_txt else ''}
                {f'<div style=\"font-size:12px; color:#92400E;\"><strong>Recommendations:</strong> {escape(imp_txt)}</div>' if imp_txt else ''}
            </div>
        </div>
        """
    else:
        modal_top_style = "border:1.5px solid var(--deep-frozen-midnight);"
        top_icon_style = "background:linear-gradient(135deg, rgba(234,244,255,1) 0%, rgba(157,183,213,0.3) 100%); border:1.5px solid var(--icy-steel); color:var(--deep-frozen-midnight);"
        top_icon_svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>'
        meta_chip = '<span style="background:rgba(16,185,129,0.12); color:#047857; border:1px solid rgba(16,185,129,0.3); font-size:11px; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Allocated Project</span>'

        if existing_sub and getattr(existing_sub, "status", "") == "reviewer_assessed":
            earn_section_html = f"""
            <!-- SECTION 2: EARN THE BADGE (REVIEWER ASSESSED) -->
            <div id="badge-section-earn" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #06B6D4; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; background:rgba(255,255,255,0.98);">
                <div style="display:flex; align-items:flex-start; gap:12px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(6,182,212,0.12); color:#0891B2; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
                    </span>
                    <div>
                        <div style="font-size:15px; font-weight:800; color:#0891B2;">Reviewer Evaluation Complete</div>
                        <div style="font-size:13px; color:var(--frost-navy-75); margin-top:2px;">Your assigned reviewer has evaluated your deliverables. Awaiting Guardian final approval and badge award.</div>
                    </div>
                </div>
                <div>
                    <span style="background:rgba(6,182,212,0.15); color:#0891B2; padding:4px 14px; border-radius:20px; font-size:12px; font-weight:700; border:1px solid rgba(6,182,212,0.3);">
                        Awaiting Guardian Award
                    </span>
                </div>
            </div>
            """
        elif existing_sub and getattr(existing_sub, "status", "") in ("pending", "submitted"):
            earn_section_html = f"""
            <!-- SECTION 2: EARN THE BADGE (PENDING REVIEW) -->
            <div id="badge-section-earn" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #3B82F6; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; background:rgba(255,255,255,0.98);">
                <div style="display:flex; align-items:flex-start; gap:12px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(59,130,246,0.12); color:#1D4ED8; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
                    </span>
                    <div>
                        <div style="font-size:15px; font-weight:800; color:#1D4ED8;">Earn the Badge</div>
                        <div style="font-size:13px; color:var(--frost-navy-75); margin-top:2px;">Deliverables routed to assigned reviewer <strong>{escape(rev_name_str)}</strong> — evaluation in progress.</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="background:rgba(245,158,11,0.15); color:#B45309; padding:4px 14px; border-radius:20px; font-size:12px; font-weight:700; border:1px solid rgba(245,158,11,0.3);">
                        Pending Reviewer Evaluation
                    </span>
                </div>
            </div>
            """
        else:
            earn_section_html = f"""
            <!-- SECTION 2: EARN THE BADGE (READY TO SUBMIT) -->
            <div id="badge-section-earn" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #3B82F6; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; background:rgba(255,255,255,0.98);">
                <div style="display:flex; align-items:flex-start; gap:12px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(59,130,246,0.12); color:#1D4ED8; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
                    </span>
                    <div>
                        <div style="font-size:15px; font-weight:800; color:#1D4ED8;">Earn the Badge</div>
                        <div style="font-size:13px; color:var(--frost-navy-75); margin-top:2px;">Submit your project deliverables (Source Code, PDF Report, and GitHub URL) to earn this badge.</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="background:rgba(16,185,129,0.15); color:#047857; padding:4px 14px; border-radius:20px; font-size:12px; font-weight:700; border:1px solid rgba(16,185,129,0.3);">
                        Allocated Milestone
                    </span>
                    <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_submission_modal', '{badge.id}')" style="font-weight:800; font-size:12.5px; padding:6px 18px;">
                        Submit Deliverables &rarr;
                    </button>
                </div>
            </div>
            """

    return f"""
    <div style="padding:4px 0 10px 0;">
        <!-- LOCATION BAR -->
        <div style="padding:16px 20px; border-radius:var(--radius-md); background:linear-gradient(135deg, rgba(23,52,92,0.06) 0%, rgba(157,183,213,0.18) 100%); {modal_top_style} margin-bottom:22px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; transition:border-color 0.3s ease;">
            <div>
                <span style="font-size:10.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--deep-frozen-midnight);">
                    Badge Location
                </span>
                <div style="font-size:14px; font-weight:800; color:var(--frost-navy); margin-top:5px; display:flex; align-items:center; flex-wrap:wrap; gap:8px;">
                    <span style="color:var(--deep-frozen-midnight); font-size:14.5px; font-weight:800;">{escape(badge_title)}</span>
                    <span style="color:var(--frost-navy-50); font-weight:800; font-size:13px;">&rarr;</span>
                    <span style="background:rgba(6,182,212,0.12); color:#0891B2; padding:3px 10px; border-radius:14px; font-size:12px; font-weight:700; border:1px solid rgba(6,182,212,0.25);">{escape(active_skill)}</span>
                    <span style="color:var(--frost-navy-50); font-weight:800; font-size:13px;">&rarr;</span>
                    <span style="background:rgba(59,130,246,0.12); color:#1D4ED8; padding:3px 10px; border-radius:14px; font-size:12px; font-weight:700; border:1px solid rgba(59,130,246,0.25);">{escape(active_cap)}</span>
                    <span style="color:var(--frost-navy-50); font-weight:800; font-size:13px;">&rarr;</span>
                    <span style="background:rgba(139,92,246,0.12); color:#7C3AED; padding:3px 10px; border-radius:14px; font-size:12px; font-weight:700; border:1px solid rgba(139,92,246,0.25);">{escape(active_power)}</span>
                    <span style="color:var(--frost-navy-50); font-weight:800; font-size:13px;">&rarr;</span>
                    <span style="background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 10px; border-radius:14px; font-size:12px; font-weight:800;">Band {selected_band}</span>
                </div>
            </div>
            <div style="display:flex; gap:10px; align-items:center; flex-shrink:0;">
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.toggleAllBadgeSections()" style="font-size:12px; font-weight:700;">
                    Toggle All
                </button>
            </div>
        </div>

        <!-- BADGE HEADER (ICON + TITLE + DESCRIPTION) -->
        <div style="margin-bottom:22px; display:flex; align-items:flex-start; gap:16px;">
            <div style="width:48px; height:48px; border-radius:50%; {top_icon_style} display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                {top_icon_svg}
            </div>
            <div style="flex:1;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px; flex-wrap:wrap;">
                    {f'<span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--frost-mist); color:var(--deep-frozen-midnight); padding:3px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30);">{escape(badge_code)}</span>' if badge_code else ''}
                    {meta_chip}
                    <h2 style="font-size:1.45rem; font-weight:800; color:var(--frost-navy); margin:0;">{escape(badge_title)}</h2>
                </div>
                <p style="font-size:13.5px; color:var(--frost-navy-75); line-height:1.5; margin:0;">{escape(badge_desc)}</p>
            </div>
        </div>

        <!-- SECTION 1: OUTCOMES -->
        <div id="badge-section-outcomes" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #10B981; overflow:hidden; background:rgba(255,255,255,0.98);">
            <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('outcomes')">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(16,185,129,0.12); color:#047857; display:flex; align-items:center; justify-content:center;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
                    </span>
                    <span style="font-size:15px; font-weight:800; color:#047857;">Outcomes ({len(outcomes)})</span>
                </div>
                <span id="chevron-outcomes" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
            </div>
            <div id="content-outcomes" style="padding:0 20px 18px 20px; display:block;">
                {outcomes_html}
            </div>
        </div>

        {earn_section_html}

        <!-- SECTION 3: PRACTICE PROJECT -->
        <div id="badge-section-practice" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #F97316; overflow:hidden; background:rgba(255,255,255,0.98);">
            <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('practice')">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(249,115,22,0.12); color:#F97316; display:flex; align-items:center; justify-content:center;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m14 2-4 0"/><path d="M10 2v7.5L5 19a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3L14 9.5V2"/></svg>
                    </span>
                    <span style="font-size:15px; font-weight:800; color:#EA580C;">Practice Project</span>
                </div>
                <span id="chevron-practice" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
            </div>
            <div id="content-practice" style="padding:0 20px 20px 20px; display:block;">
                <p style="font-size:13px; color:var(--frost-navy-75); margin:0 0 14px 0;">Want some hands-on practice? Use this prompt to generate a practice project.</p>
                <div style="background:rgba(241,245,249,0.85); border:1px solid var(--icy-steel-40); border-radius:var(--radius-md); padding:16px; position:relative;">
                    <div id="practice-prompt-text" style="font-size:12.5px; color:var(--frost-navy); line-height:1.65; white-space:pre-wrap; font-family:var(--font-family-sans);">{escape(practice_prompt)}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid rgba(157,183,213,0.3); flex-wrap:wrap; gap:10px;">
                        <span style="font-size:11.5px; color:var(--frost-navy-50);">This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge.</span>
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('practice-prompt-text', this)" style="font-size:11.5px; font-weight:700; display:inline-flex; align-items:center; gap:6px;">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                            Copy
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- SECTION 4: LEARNING TOPICS -->
        <div id="badge-section-topics" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #06B6D4; overflow:hidden; background:rgba(255,255,255,0.98);">
            <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('topics')">
                <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(6,182,212,0.12); color:#0E7490; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>
                    </span>
                    <span style="font-size:15px; font-weight:800; color:#0891B2;">Learning Topics</span>
                    <span id="topics-summary-pill" style="background:{'rgba(16,185,129,0.15)' if progress_pct > 0 else 'rgba(157,183,213,0.18)'}; color:{'#10B981' if progress_pct > 0 else 'var(--frost-navy-50)'}; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:700; border:1px solid {'rgba(16,185,129,0.3)' if progress_pct > 0 else 'rgba(157,183,213,0.3)'};">
                        {completed_topics_count}/{total_topics} Completed
                    </span>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="width:130px; height:8px; border-radius:4px; background:rgba(157,183,213,0.3); overflow:hidden;">
                            <div id="topics-progress-bar" style="width:{progress_pct}%; height:100%; background:linear-gradient(90deg, #06B6D4, #10B981); border-radius:4px; transition:width 0.4s ease;"></div>
                        </div>
                        <span id="topics-progress-text" style="font-size:12px; font-weight:800; color:#0891B2; min-width:36px;">{progress_pct}%</span>
                    </div>
                </div>
                <span id="chevron-topics" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
            </div>
            <div id="content-topics" style="padding:0 20px 20px 20px; display:block;">
                {topics_html}
            </div>
        </div>

        <!-- SECTION 5: LEARNING RESOURCES -->
        <div id="badge-section-resources" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #3B82F6; overflow:hidden; background:rgba(255,255,255,0.98);">
            <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('resources')">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(59,130,246,0.12); color:#1D4ED8; display:flex; align-items:center; justify-content:center;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                    </span>
                    <span style="font-size:15px; font-weight:800; color:#1D4ED8;">Learning Resources</span>
                </div>
                <span id="chevron-resources" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
            </div>
            <div id="content-resources" style="padding:0 20px 20px 20px; display:block;">
                <p style="font-size:13px; color:var(--frost-navy-75); margin:0 0 14px 0;">Not sure where to start learning? Use this prompt to find free resources tailored to this badge.</p>
                <div style="background:rgba(241,245,249,0.85); border:1px solid var(--icy-steel-40); border-radius:var(--radius-md); padding:16px; position:relative;">
                    <div id="resources-prompt-text" style="font-size:12.5px; color:var(--frost-navy); line-height:1.65; white-space:pre-wrap; font-family:var(--font-family-sans);">{escape(resources_prompt)}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid rgba(157,183,213,0.3); flex-wrap:wrap; gap:10px;">
                        <span style="font-size:11.5px; color:var(--frost-navy-50);">This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources.</span>
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('resources-prompt-text', this)" style="font-size:11.5px; font-weight:700; display:inline-flex; align-items:center; gap:6px;">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                            Copy
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- SECTION 6: RELATED SKILLS, CAPABILITIES & POWERS -->
        <div id="badge-section-related" class="liquid-glass-card" style="margin-bottom:20px; border-radius:var(--radius-lg); border:1.5px solid #8B5CF6; overflow:hidden; background:rgba(255,255,255,0.98);">
            <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('related')">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(139,92,246,0.12); color:#8B5CF6; display:flex; align-items:center; justify-content:center;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
                    </span>
                    <span style="font-size:15px; font-weight:800; color:#7C3AED;">Related Skills, Capabilities &amp; Powers</span>
                </div>
                <span id="chevron-related" style="color:var(--frost-navy-50); font-weight:800; font-size:13px; transition:transform 0.2s ease;">▲</span>
            </div>
            <div id="content-related" style="padding:0 20px 20px 20px; display:block;">
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:20px;">
                    <div>
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Skills</div>
                        <span style="background:rgba(6,182,212,0.12); color:#0891B2; padding:5px 14px; border-radius:20px; font-size:12.5px; font-weight:700; display:inline-block; border:1px solid rgba(6,182,212,0.25);">{escape(active_skill)}</span>
                    </div>
                    <div>
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Capabilities</div>
                        <span style="background:rgba(59,130,246,0.12); color:#1D4ED8; padding:5px 14px; border-radius:20px; font-size:12.5px; font-weight:700; display:inline-block; border:1px solid rgba(59,130,246,0.25);">{escape(active_cap)}</span>
                    </div>
                    <div>
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Powers</div>
                        <span style="background:rgba(139,92,246,0.12); color:#7C3AED; padding:5px 14px; border-radius:20px; font-size:12.5px; font-weight:700; display:inline-block; border:1px solid rgba(139,92,246,0.25);">{escape(active_power)}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL FOOTER ACTIONS -->
        <div style="display:flex; justify-content:flex-end; align-items:center; gap:12px; padding-top:14px; border-top:1px solid var(--icy-steel-30); flex-wrap:wrap;">
            <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">
                Close
            </button>
            <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('open_submission_modal', '{badge.id}')" style="font-weight:800; padding:9px 20px; display:inline-flex; align-items:center; gap:8px;">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                Submit Deliverables for this Badge &rarr;
            </button>
        </div>
    </div>
    """

# ==============================================================================
# 6.6 ASSESSMENT RESULTS & MARKSHEETS
# ==============================================================================

def render_cosmonaut_results(
    assessments: List[AssessmentMarksheet],
    badges_map: Dict[str, Badge],
    selected_badge_id: Optional[str] = None,
    available_badges: Optional[List[Badge]] = None,
    extensions: Optional[List[DeadlineExtension]] = None
) -> str:
    # 1. Determine list of selectable badges (assigned/published badges + any assessed badges)
    badge_list = list(available_badges) if available_badges else []
    existing_ids = {b.id for b in badge_list}
    # Also include any badges for which this user has assessments
    for a in assessments:
        if a.badge_id not in existing_ids and a.badge_id in badges_map:
            badge_list.append(badges_map[a.badge_id])
            existing_ids.add(a.badge_id)
    if selected_badge_id and selected_badge_id not in existing_ids and selected_badge_id in badges_map:
        badge_list.append(badges_map[selected_badge_id])
        existing_ids.add(selected_badge_id)
    present_4_ids = ["badge_gov_101", "badge_cur_102", "badge_dat_103", "badge_ing_104"]
    for pid in present_4_ids:
        if pid not in existing_ids and pid in badges_map:
            badge_list.append(badges_map[pid])

    # Fallback ONLY when caller omitted available_badges (synthetic unit tests)
    if not badge_list and available_badges is None:
        badge_list = list(badges_map.values())

    # Sort badges to put the present badges in logical progression order
    def badge_order(b: Badge) -> int:
        if b.id in present_4_ids:
            return present_4_ids.index(b.id)
        return 100

    badge_list.sort(key=badge_order)

    if not badge_list and not assessments:
        return f"""
        <div>
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:24px;">
                {render_back_button()}
                <div>
                    <h2 style="font-size:1.55rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">Official Assessment Marksheets</h2>
                </div>
            </div>
            <div class="liquid-glass-card" style="padding:48px 32px; text-align:center; border:1.5px dashed var(--icy-steel); background:rgba(255,255,255,0.75);">
                <div style="display:inline-flex; align-items:center; justify-content:center; width:56px; height:56px; border-radius:50%; background:rgba(23,52,92,0.08); margin-bottom:14px;">
                    {get_icon("clipboard", 22)}
                </div>
                <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0 0 6px 0;">No Badges Allocated in This Cycle</h3>
                <p style="font-size:13.5px; color:var(--frost-navy-50); max-width:520px; margin:0 auto; line-height:1.5;">
                    You do not have any published milestone badges or evaluation marksheets in the active performance cycle yet.
                </p>
            </div>
        </div>
        """

    # Validate selected_badge_id
    if not selected_badge_id or (selected_badge_id not in [b.id for b in badge_list]):
        selected_badge_id = badge_list[0].id if badge_list else "badge_gov_101"

    # Build options for top-right dropdown
    badge_options = []
    for b in badge_list:
        sel = " selected" if b.id == selected_badge_id else ""
        badge_options.append(f'<option value="{b.id}"{sel}>{escape(b.code)}: {escape(b.title)}</option>')

    # Matching assessments for selected_badge_id (Guardian Official Final prioritized over Reviewer preliminary per attempt)
    matching_asms = sorted(
        [a for a in assessments if a.badge_id == selected_badge_id],
        key=lambda a: (
            getattr(a, "attempt_number", 1),
            1 if getattr(a, "assessor_role", "") == "guardian" else 0,
            getattr(a, "reviewed_at", ""),
        ),
    )
    current_badge = badges_map.get(selected_badge_id)
    badge_code = current_badge.code if current_badge else selected_badge_id
    badge_title = current_badge.title if current_badge else "Milestone Assessment"

    # Deadline extension reflection banner
    ext_banner = ""
    if extensions:
        badge_exts = [e for e in extensions if e.badge_id == selected_badge_id]
        if badge_exts:
            latest_ext = badge_exts[-1]
            if latest_ext.status == "approved":
                ext_banner = f"""
                <div style="margin-bottom:20px; padding:12px 18px; background:linear-gradient(135deg, rgba(16,185,129,0.09) 0%, rgba(234,244,255,0.7) 100%); border:1.5px solid #10B981; border-radius:var(--radius-sm); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="background:#047857; color:#FFFFFF; font-size:11px; font-weight:800; padding:3px 9px; border-radius:var(--radius-xs); text-transform:uppercase;">Deadline Extended</span>
                        <span style="font-size:13px; font-weight:700; color:var(--deep-frozen-midnight);">
                            Official Submission Deadline: <span style="font-family:var(--font-family-mono); font-weight:800;">{escape(latest_ext.proposed_deadline)}</span> (Approved by Guardian)
                        </span>
                    </div>
                    <div style="font-size:12px; color:var(--frost-navy-50); font-style:italic;">
                        {escape(latest_ext.guardian_response or "Schedule adjustment approved by mentor.")}
                    </div>
                </div>
                """
            elif latest_ext.status == "pending":
                ext_banner = f"""
                <div style="margin-bottom:20px; padding:12px 18px; background:rgba(245,158,11,0.08); border:1.5px solid #F59E0B; border-radius:var(--radius-sm); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="background:#F59E0B; color:#451A03; font-size:11px; font-weight:800; padding:3px 9px; border-radius:var(--radius-xs); text-transform:uppercase;">Extension Pending</span>
                        <span style="font-size:13px; font-weight:700; color:var(--deep-frozen-midnight);">
                            Requested Extension to <span style="font-family:var(--font-family-mono); font-weight:800;">{escape(latest_ext.proposed_deadline)}</span> &bull; Awaiting Guardian Review
                        </span>
                    </div>
                    <span style="font-size:12px; color:var(--frost-navy-50);">Current Cutoff: {escape(latest_ext.current_deadline)}</span>
                </div>
                """
            elif latest_ext.status == "rejected":
                ext_banner = f"""
                <div style="margin-bottom:20px; padding:12px 18px; background:rgba(239,68,68,0.06); border:1px solid #EF4444; border-radius:var(--radius-sm); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="background:#EF4444; color:#FFFFFF; font-size:11px; font-weight:800; padding:3px 9px; border-radius:var(--radius-xs); text-transform:uppercase;">Extension Rejected</span>
                        <span style="font-size:13px; font-weight:700; color:var(--frost-navy);">
                            Original Cutoff Maintained: <span style="font-family:var(--font-family-mono); font-weight:800;">{escape(latest_ext.current_deadline)}</span>
                        </span>
                    </div>
                    <div style="font-size:12px; color:var(--frost-navy-50); font-style:italic;">{escape(latest_ext.guardian_response or "Extension rejected by mentor.")}</div>
                </div>
                """

    # Top header with Title on the left and Badge Dropdown on the top right
    top_header_html = f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:24px; flex-wrap:wrap; gap:16px;">
        <div style="display:flex; align-items:center; gap:12px;">
            {render_back_button()}
            <div>
                <h2 style="font-size:1.55rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">Official Assessment Marksheets</h2>
            </div>
        </div>
        <div style="min-width:320px;">
            <label style="font-size:11.5px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; display:block; margin-bottom:6px;">Select Milestone Badge</label>
            <div class="liquid-select-wrapper">
                <select id="results-badge-select" class="liquid-glass-control liquid-glass-select" onchange="window.StarAppBridge.dispatchAction('change_results_badge', this.value)">
                    {"".join(badge_options)}
                </select>
            </div>
        </div>
    </div>
    """

    if matching_asms:
        selected_asm = matching_asms[-1]
        sheet_content = render_standard_marksheet(selected_asm, current_badge, matching_asms)
    else:
        sheet_content = f"""
        <div class="liquid-glass-card" style="padding:48px 32px; text-align:center; border:1.5px dashed var(--icy-steel); background:rgba(255,255,255,0.7);">
            <div style="display:inline-flex; align-items:center; justify-content:center; width:56px; height:56px; border-radius:50%; background:rgba(23,52,92,0.08); margin-bottom:16px;">
                <span style="font-size:24px;">{get_icon("clipboard", 20)}</span>
            </div>
            <h3 style="font-size:1.3rem; font-weight:800; color:var(--frost-navy); margin-bottom:6px;">Evaluation Pending for {escape(badge_code)}</h3>
            <p style="font-size:13.5px; color:var(--frost-navy-50); max-width:540px; margin:0 auto 20px auto; line-height:1.5;">
                <strong>{escape(badge_title)}</strong> has been allocated by your Guardian. Once you submit project deliverables, your Guardian will publish your marksheet across the 50-mark universal rubric.
            </p>
            <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('nav_to_submit_badge', '{selected_badge_id}')">
                Open Deliverable Submission Portal →
            </button>
        </div>
        """

    return f"""
    <div>
        {top_header_html}
        {ext_banner}
        {sheet_content}
    </div>
    """

# ==============================================================================
# 6.7 LEARNING MATERIALS (In-App PDF Viewer & Embedded YouTube Player)
# ==============================================================================

def render_cosmonaut_materials(
    materials: List[LearningMaterial],
    badges: List[Badge],
    badges_map: Dict[str, Badge],
    selected_badge_filter: str = "all",
    selected_type_filter: str = "all"
) -> str:
    return render_learning_materials_view(
        materials=materials,
        badges=badges,
        badges_map=badges_map,
        selected_badge_filter=selected_badge_filter,
        selected_type_filter=selected_type_filter,
        is_guardian=False
    )


# ==============================================================================
# 6.9 DEADLINE EXTENSION REQUESTS
# ==============================================================================

def render_cosmonaut_extensions(
    assigned_badges: List[Badge],
    extensions: List[DeadlineExtension],
    badges_map: Dict[str, Badge],
    completed_badge_ids: Optional[Any] = None
) -> str:
    completed_set = set(completed_badge_ids or [])
    # Filter to only current available, non-completed milestones
    available_badges = [b for b in assigned_badges if b.id not in completed_set]

    if available_badges:
        badge_opts = "".join([f'<option value="{b.id}">{escape(b.code)}: {escape(b.title)} (In-Progress)</option>' for b in available_badges])
    else:
        badge_opts = '<option disabled selected>All assigned badges are currently completed</option>'

    # Build clean, compact table rows / cards for submitted requests
    req_rows = []
    for ext in extensions:
        badge = badges_map.get(ext.badge_id)
        b_code = badge.code if badge else ext.badge_id
        b_title = badge.title if badge else "Milestone Deliverable"

        if ext.status == "approved":
            status_pill = '<span class="status-pill" style="font-size:11px; font-weight:800; padding:4px 10px; background:#047857; color:#FFFFFF; border-radius:var(--radius-xs); display:inline-flex; align-items:center; gap:4px;">&#10003; Approved</span>'
            action_btn = f"""
            <button type="button" class="btn-metal btn-sm" style="font-size:12px; padding:6px 14px; white-space:nowrap;" onclick="window.StarAppBridge.dispatchAction('nav_to_submit_badge', '{ext.badge_id}')">
                Submit Deliverable &rarr;
            </button>
            """
        elif ext.status == "rejected":
            status_pill = '<span class="status-pill" style="font-size:11px; font-weight:800; padding:4px 10px; background:#EF4444; color:#FFFFFF; border-radius:var(--radius-xs); display:inline-flex; align-items:center; gap:4px;">&#10005; Rejected</span>'
            action_btn = f"""
            <button type="button" class="btn-secondary btn-sm" style="font-size:12px; padding:6px 14px; white-space:nowrap;" onclick="window.StarAppBridge.dispatchAction('nav_to_submit_badge', '{ext.badge_id}')">
                Submit Deliverable
            </button>
            """
        else:
            status_pill = '<span class="status-pill" style="font-size:11px; font-weight:800; padding:4px 10px; background:#F59E0B; color:#451A03; border-radius:var(--radius-xs); display:inline-flex; align-items:center; gap:4px;">&#9203; Pending Review</span>'
            action_btn = '<span style="font-size:12px; color:var(--frost-navy-50); font-weight:600; font-style:italic;">Awaiting Mentor</span>'

        feedback_html = ""
        if ext.guardian_response:
            feedback_html = f"""
            <div style="margin-top:6px; font-size:12px; padding:6px 10px; background:rgba(23,52,92,0.05); border-left:3px solid var(--deep-frozen-midnight); border-radius:var(--radius-xs); color:var(--frost-navy);">
                <strong>Guardian Note:</strong> {escape(ext.guardian_response)}
            </div>
            """

        req_rows.append(f"""
        <tr style="border-bottom:1px solid var(--icy-steel-30); transition:background 0.15s ease;">
            <td style="padding:14px 16px; vertical-align:top;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">{escape(b_code)}</span>
                    <strong style="font-size:13.5px; color:var(--frost-navy);">{escape(b_title)}</strong>
                </div>
                <div style="font-size:12px; color:var(--frost-navy-75); line-height:1.4; max-width:420px;">
                    <span style="color:var(--frost-navy-50);">Reason:</span> {escape(ext.reason)}
                </div>
                {feedback_html}
            </td>
            <td style="padding:14px 16px; vertical-align:middle; font-family:var(--font-family-mono); font-size:12.5px; color:var(--frost-navy-75); white-space:nowrap;">
                {escape(ext.current_deadline)}
            </td>
            <td style="padding:14px 16px; vertical-align:middle; font-family:var(--font-family-mono); font-size:13px; font-weight:800; color:var(--deep-frozen-midnight); white-space:nowrap;">
                {escape(ext.proposed_deadline)}
            </td>
            <td style="padding:14px 16px; vertical-align:middle; text-align:center; white-space:nowrap;">
                {status_pill}
            </td>
            <td style="padding:14px 16px; vertical-align:middle; text-align:right; white-space:nowrap;">
                {action_btn}
            </td>
        </tr>
        """)

    table_body = "".join(req_rows) if req_rows else """
    <tr>
        <td colspan="5" style="padding:32px 16px; text-align:center; color:var(--frost-navy-50); font-style:italic;">
            No deadline extension requests submitted yet. Select an in-progress milestone above to request an adjustment.
        </td>
    </tr>
    """

    return f"""
    <div>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:24px; flex-wrap:wrap; gap:12px;">
            <div style="display:flex; align-items:center; gap:12px;">
                {render_back_button()}
                <div>
                    <h2 style="font-size:1.55rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">Milestone Deadline Extension Portal</h2>
                    <p style="font-size:13.5px; color:var(--frost-navy-50); margin:0;">Request scheduling adjustments for active milestones and track evaluations in real-time.</p>
                </div>
            </div>
        </div>

        <!-- Vertically Stacked Layout: Form on top, Submitted requests below -->
        <div style="display:flex; flex-direction:column; gap:24px;">
            <!-- 1. Request Deadline Extension Container (Top) -->
            <div class="liquid-submission-portal" style="padding:28px 32px;">
                <div style="margin-bottom:18px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px;">
                    <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">Request Deadline Extension</h3>
                    <div style="font-size:12.5px; color:var(--frost-navy-50);">Choose an in-progress milestone and specify a realistic engineering rationale for mentor review.</div>
                </div>

                <form id="deadline-extension-form" onsubmit="event.preventDefault(); const b=document.getElementById('ext-badge'); const d=document.getElementById('ext-date'); const r=document.getElementById('ext-reason'); window.StarAppBridge.dispatchAction('submit_deadline_extension_request', JSON.stringify({{badge_id:b.value, proposed_deadline:d.value, reason:r.value}}));">
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(280px, 100%), 1fr)); gap:18px; margin-bottom:18px;">
                        <!-- Milestone Selector -->
                        <div class="liquid-form-group">
                            <label class="liquid-form-label" for="ext-badge">Target Available Milestone (In-Progress)</label>
                            <div class="liquid-select-wrapper">
                                <select id="ext-badge" class="liquid-glass-control liquid-glass-select" required>
                                    {badge_opts}
                                </select>
                            </div>
                            <span class="liquid-form-hint">Only active non-completed milestones are eligible.</span>
                        </div>

                        <!-- Datepicker -->
                        <div class="liquid-form-group">
                            <label class="liquid-form-label" for="ext-date">Proposed New Submission Deadline</label>
                            <div class="liquid-date-wrapper">
                                <div class="liquid-date-icon-box">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                                        <line x1="16" y1="2" x2="16" y2="6"></line>
                                        <line x1="8" y1="2" x2="8" y2="6"></line>
                                        <line x1="3" y1="10" x2="21" y2="10"></line>
                                    </svg>
                                </div>
                                <input type="date" id="ext-date" class="liquid-glass-date" required>
                            </div>
                            <span class="liquid-form-hint">Choose a future cutoff date allowing buffer for completion.</span>
                        </div>
                    </div>

                    <!-- Reason Textarea -->
                    <div class="liquid-form-group" style="margin-bottom:20px;">
                        <label class="liquid-form-label" for="ext-reason">Technical Justification & Bottleneck Details</label>
                        <textarea id="ext-reason" class="liquid-glass-control auto-grow-textarea" style="min-height:90px; padding:12px 14px; resize:none; overflow:hidden; font-family:var(--font-family-base); line-height:1.5;" placeholder="Describe the unexpected complexity, data pipeline latency, or algorithmic research requiring additional engineering time..." required></textarea>
                        <span class="liquid-form-hint">Provide at least 10 characters detailing the engineering rationale for your Guardian.</span>
                    </div>

                    <!-- Submit Button -->
                    <div style="display:flex; justify-content:flex-end;">
                        <div class="btn-metal-wrapper">
                            <div class="btn-metal-inner"></div>
                            <button type="submit" class="btn-metal" style="height:44px; padding:0 24px; font-size:13.5px; font-weight:700;">
                                Submit Extension Request for Guardian Review &rarr;
                            </button>
                        </div>
                    </div>
                </form>
            </div>

            <!-- 2. Submitted Requests & Status Container (Shown Below Request Container) -->
            <div class="liquid-submission-portal" style="padding:28px 32px;">
                <div style="margin-bottom:18px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div>
                        <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">Submitted Requests & Actions</h3>
                        <div style="font-size:12.5px; color:var(--frost-navy-50);">Requested milestone extensions, live status, and necessary actions.</div>
                    </div>
                    <span style="font-size:12px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
                        {len(extensions)} Total Request{"s" if len(extensions) != 1 else ""}
                    </span>
                </div>

                <div style="overflow-x:auto;">
                    <table style="width:100%; border-collapse:collapse; text-align:left;">
                        <thead>
                            <tr style="border-bottom:1.5px solid var(--icy-steel); background:rgba(234,244,255,0.4);">
                                <th style="padding:10px 16px; font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">Milestone & Details</th>
                                <th style="padding:10px 16px; font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">Current Cutoff</th>
                                <th style="padding:10px 16px; font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">Proposed Cutoff</th>
                                <th style="padding:10px 16px; font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; text-align:center;">Status</th>
                                <th style="padding:10px 16px; font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; text-align:right;">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_body}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """

# ==============================================================================
# 6.10 ANNOUNCEMENT CENTER
# ==============================================================================

def render_cosmonaut_announcements(
    announcements: List[Announcement],
    current_cosmo_id: str
) -> str:
    cards = []
    for ann in announcements:
        is_unread = current_cosmo_id not in ann.read_by_cosmonaut_ids
        unread_cls = "unread" if is_unread else ""
        mark_read_btn = ""
        if is_unread:
            mark_read_btn = f"""
            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('mark_announcement_as_read', '{{\"announcement_id\": \"{ann.id}\"}}')">
                Mark as Read
            </button>
            """

        cards.append(f"""
        <div class="liquid-glass-card announcement-card {unread_cls}">
            <div class="card-content">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <h3 style="font-size:1.15rem; font-weight:700; color:var(--frost-navy);">{escape(ann.title)}</h3>
                    {mark_read_btn}
                </div>
                <div class="announcement-meta">
                    <span>From: <strong>{escape(ann.author_name)}</strong></span>
                    <span>•</span>
                    <span>Date: {escape(ann.published_at[:10])}</span>
                </div>
                <p style="font-size:13.5px; line-height:1.5; color:var(--frost-navy); margin-top:8px;">{escape(ann.message)}</p>
            </div>
        </div>
        """)

    return f"""
    <div>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
            <div style="display:flex; align-items:center; gap:12px;">
                {render_back_button()}
                <div>
                    <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy); margin:0;">Academy Announcement Center</h2>
                    <p style="font-size:13px; color:var(--frost-navy-50); margin:2px 0 0 0;">Notices and schedule updates broadcasted by Academy Leadership.</p>
                </div>
            </div>
        </div>

        <div>
            {"".join(cards) if cards else "<p style='padding:30px; text-align:center; color:var(--frost-navy-50);'>No active announcements.</p>"}
        </div>
    </div>
    """

# ==============================================================================
# 6.8 ACTIVITY STREAM
# ==============================================================================

def render_cosmonaut_activity_stream(activities: List[ActivityEvent]) -> str:
    from starapp.storage import store as _store_ref
    rows = []
    page_acts, activity_pager_html = page_slice("c_activity", activities, 25)
    for act in page_acts:
        _badge = _store_ref.get_badge(act.badge_id) if act.badge_id else None
        rows.append(f"""
        <tr>
            <td style="font-family:var(--font-family-mono); font-size:12px; white-space:nowrap;">{escape(act.timestamp[:19].replace('T', ' '))}</td>
            <td>{render_status_pill(act.event_type)}</td>
            <td>
                <div style="font-weight:700;">{escape(humanize_internal_ids(act.summary))}</div>
                <div style="font-size:12px; color:var(--frost-navy-50);">{escape(humanize_internal_ids(act.details))}</div>
            </td>
            <td>{escape(_badge.code if _badge else (act.badge_id or "Academy"))}</td>
        </tr>
        """)

    return f"""
    <div>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
            <div style="display:flex; align-items:center; gap:12px;">
                {render_back_button()}
                <div>
                    <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy); margin:0;">Personal Activity Feed</h2>
                </div>
            </div>
        </div>

        <div class="table-responsive">
            <table class="star-table">
                <thead>
                    <tr>
                        <th>Timestamp (UTC)</th>
                        <th>Event</th>
                        <th>Progress Milestone Summary</th>
                        <th>Badge</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows) if rows else '<tr><td colspan="4" style="text-align:center; padding:24px; color:var(--frost-navy-50);">No recorded activities yet.</td></tr>'}
                </tbody>
            </table>
            {activity_pager_html}
        </div>
    </div>
    """


# ==============================================================================
# 6.9 REVIEW REQUESTS QUEUE (COSMONAUT VIEW FOR HIGHER-BAND REVIEWERS)
# ==============================================================================

def render_cosmonaut_review_requests(
    requests: List[Dict[str, Any]],
    current_user: User,
    active_tab: str = "all",
    search_query: str = ""
) -> str:
    """
    Renders the Review Requests workspace in the Cosmonaut portal.
    Engineers in higher bands (B2 through B6) can inspect, edit, approve,
    or return/reject badges submitted for peer review.
    """
    from starapp.storage import store

    # Filtering
    filtered = requests
    if active_tab and active_tab != "all":
        filtered = [
            r for r in filtered
            if r.get("workflow_status") == active_tab or r.get("assignment_status") == active_tab
        ]

    if search_query and search_query.strip():
        q = search_query.strip().lower()
        filtered = [
            r for r in filtered
            if q in r.get("title", "").lower()
            or q in r.get("code", "").lower()
            or q in r.get("target_band", "").lower()
            or q in r.get("skill", "").lower()
            or q in r.get("capability", "").lower()
        ]

    # Counts
    all_cnt = len(requests)
    pending_cnt = len([r for r in requests if r.get("workflow_status") == "pending_review" or r.get("assignment_status") == "pending"])
    approved_cnt = len([r for r in requests if r.get("workflow_status") == "approved" or r.get("assignment_status") == "approved"])
    returned_cnt = len([r for r in requests if r.get("workflow_status") == "returned" or r.get("assignment_status") == "returned"])

    history_records = store.get_badge_review_history(reviewer_id=current_user.id) if hasattr(store, "get_badge_review_history") else []
    history_cnt = len(history_records)

    def tab_btn(tab_id: str, label: str, count: int) -> str:
        is_sel = (tab_id == active_tab)
        st = "background:var(--deep-frozen-midnight); color:var(--snow-white); font-weight:800;" if is_sel else "background:rgba(255,255,255,0.75); color:var(--frost-navy); font-weight:600;"
        return f"""
        <button type="button" class="btn-secondary btn-sm" style="{st} padding:7px 16px; border-radius:var(--radius-sm);"
                onclick="window.StarAppBridge.dispatchAction('filter_cosmo_requests', '{tab_id}')">
            {label} ({count})
        </button>
        """

    tabs_html = f"""
    <div style="display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap;">
        {tab_btn('all', 'All Requests', all_cnt)}
        {tab_btn('pending_review', 'Pending Review', pending_cnt)}
        {tab_btn('approved', 'Approved Badges', approved_cnt)}
        {tab_btn('returned', 'Returned', returned_cnt)}
        {tab_btn('history', 'Review History & Audit', history_cnt)}
    </div>
    """

    user_band = getattr(current_user, "band", "B2")
    user_track = getattr(current_user, "learning_track", "Engineer")

    # Render request cards or history view
    cards_html = []

    if active_tab == "history":
        history_rows = []
        for h in history_records:
            ev_type = h.get("event_type", "")
            if ev_type == "approved":
                ev_pill = '<span class="status-pill status-approved" style="font-size:11px; font-weight:700;">Authorized & Approved</span>'
            elif ev_type == "returned":
                ev_pill = '<span class="status-pill status-rejected" style="font-size:11px; font-weight:700;">Returned with Feedback</span>'
            elif ev_type == "edited":
                ev_pill = '<span class="status-pill status-warning" style="font-size:11px; font-weight:700;">Badge Edited</span>'
            else:
                ev_pill = '<span class="status-pill status-active" style="font-size:11px; font-weight:700;">Review Dispatched</span>'

            history_rows.append(f"""
            <tr style="border-bottom:1px solid var(--icy-steel-25);">
                <td style="padding:14px 16px;">
                    <div style="font-weight:700; color:var(--frost-navy); font-size:13px;">{escape(h.get('badge_title', ''))}</div>
                    <div style="font-family:var(--font-family-mono); font-size:11.5px; color:var(--deep-frozen-midnight);">{escape(h.get('badge_code', ''))}</div>
                </td>
                <td style="padding:14px 16px;">
                    <span style="font-family:var(--font-family-mono); font-weight:800; font-size:11px; background:var(--frost-mist); color:var(--deep-frozen-midnight); padding:3px 8px; border-radius:var(--radius-xs);">BAND {escape(h.get('target_band', 'B1'))}</span>
                </td>
                <td style="padding:14px 16px; font-size:11.5px; color:var(--frost-navy-75); max-width:240px; line-height:1.4;">
                    {escape(h.get('taxonomy_tree', ''))}
                </td>
                <td style="padding:14px 16px; text-align:center;">
                    {ev_pill}
                </td>
                <td style="padding:14px 16px; font-size:12px; font-weight:600; color:var(--frost-navy);">
                    {escape(h.get('formatted_timestamp', ''))}
                </td>
                <td style="padding:14px 16px; font-size:11.5px; color:var(--frost-navy-75); max-width:220px;">
                    {escape(h.get('notes') or 'Action recorded.')}
                </td>
                <td style="padding:14px 16px; text-align:right;">
                    <button type="button" class="btn-secondary btn-sm" style="font-size:11px; font-weight:700;"
                            onclick="window.StarAppBridge.dispatchAction('open_badge_for_review', '{h.get('badge_id', '')}')">
                        Inspect
                    </button>
                </td>
            </tr>
            """)

        cards_html.append(f"""
        <div class="liquid-glass-card" style="padding:0; overflow:hidden; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-40);">
            <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse:collapse; text-align:left;">
                    <thead>
                        <tr style="background:linear-gradient(135deg, rgba(23,52,92,0.06) 0%, rgba(157,183,213,0.12) 100%); border-bottom:1.5px solid var(--icy-steel-30); font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:var(--frost-navy-75);">
                            <th style="padding:12px 16px;">Badge Title & Code</th>
                            <th style="padding:12px 16px;">Band</th>
                            <th style="padding:12px 16px;">Taxonomy Hierarchy Tree</th>
                            <th style="padding:12px 16px; text-align:center;">Decision Event</th>
                            <th style="padding:12px 16px;">Timestamp</th>
                            <th style="padding:12px 16px;">Feedback / Notes</th>
                            <th style="padding:12px 16px; text-align:right;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(history_rows) if history_rows else '<tr><td colspan="7" style="padding:32px; text-align:center; color:var(--frost-navy-50);">No review actions recorded in your history yet.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
        """)
    else:
        for r in filtered:
            b_id = r.get("id", "")
            b_code = escape(r.get("code", ""))
            b_title = escape(r.get("title", ""))
            target_band = escape(r.get("target_band", "B1"))
            b_loc = escape(r.get("location", ""))
            b_desc = escape(r.get("description", ""))
            wf_status = r.get("workflow_status", "pending_review")
            assign_status = r.get("assignment_status", "pending")
            creator_name = escape(r.get("creator_name") or "Guardian")
            assigned_ts = r.get("assigned_at") or ""
            assigned_at = assigned_ts[:16].replace("T", " ") if assigned_ts else "2026-11-20"
            due_ts = r.get("review_due_at") or ""
            due_date = escape(due_ts[:10] if due_ts else "2026-11-27")
            dec_notes = escape(r.get("decision_notes") or "")

            if wf_status == "pending_review":
                status_pill = '<span class="status-pill status-warning" style="font-size:11px; font-weight:700;">Pending Review</span>'
            elif wf_status == "approved":
                status_pill = '<span class="status-pill status-approved" style="font-size:11px; font-weight:700;">Approved</span>'
            elif wf_status == "returned":
                status_pill = '<span class="status-pill status-rejected" style="font-size:11px; font-weight:700;">Returned for Changes</span>'
            else:
                status_pill = f'<span class="status-pill status-active" style="font-size:11px; font-weight:700;">{escape(wf_status.title())}</span>'

            # Outcomes preview
            outcomes = r.get("learning_outcomes", [])
            outcomes_list = []
            for oc in outcomes[:3]:
                outcomes_list.append(f'<li style="margin-bottom:4px; font-size:12px; color:var(--frost-navy);">{escape(str(oc))}</li>')
            outcomes_html = f'<ul style="margin:6px 0 0 16px; padding:0; list-style-type:disc;">{"".join(outcomes_list)}</ul>' if outcomes_list else '<span style="font-size:12px; color:var(--frost-navy-50);">No outcomes specified.</span>'

            # Topics pills
            topics = r.get("learning_topics", [])
            topic_pills = []
            for t in topics[:6]:
                t_title = t.get("title") if isinstance(t, dict) else str(t)
                topic_pills.append(f'<span style="font-size:11px; background:rgba(23,52,92,0.06); color:var(--frost-navy); padding:2px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30); font-weight:600;">{escape(t_title)}</span>')
            topics_html = f'<div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:6px;">{"".join(topic_pills)}</div>' if topic_pills else ""

            # Practice Project requirements preview
            reqs = r.get("project_requirements", "")
            reqs_html = f"""
            <div style="margin-top:10px; padding:8px 12px; background:rgba(255,255,255,0.7); border-left:3px solid var(--deep-frozen-midnight); border-radius:var(--radius-xs); font-size:12px; color:var(--frost-navy-75);">
                <strong style="color:var(--frost-navy);">Practice Project Specification:</strong> {escape(reqs[:180])}{"..." if len(reqs) > 180 else ""}
            </div>
            """ if reqs else ""

            # Decision notes preview if present
            notes_box = ""
            if dec_notes:
                notes_box = f"""
                <div style="margin-top:10px; padding:8px 12px; background:rgba(239,68,68,0.06); border-left:3px solid #EF4444; border-radius:var(--radius-xs); font-size:12px; color:var(--frost-navy);">
                    <strong style="color:#DC2626;">Reviewer Feedback Notes:</strong> {dec_notes}
                </div>
                """

            # Action Buttons
            inspect_btn = f"""
            <button type="button" class="btn-secondary btn-sm" style="font-size:11.5px; font-weight:700;"
                    onclick="window.StarAppBridge.dispatchAction('open_badge_for_review', '{b_id}')">
                Inspect Badge
            </button>
            """

            edit_btn = f"""
            <button type="button" class="btn-secondary btn-sm" style="font-size:11.5px; font-weight:700;"
                    onclick="window.StarAppBridge.dispatchAction('edit_submitted_badge', '{b_id}')">
                Edit Badge
            </button>
            """

            approve_btn = ""
            return_btn = ""
            if wf_status == "pending_review":
                approve_btn = f"""
                <button type="button" class="btn-metal btn-sm" style="font-size:11.5px; font-weight:800; background:linear-gradient(135deg, #10B981 0%, #059669 100%); border-color:#059669; color:#fff;"
                        onclick="window.StarAppBridge.dispatchAction('confirm_approve_badge', '{b_id}')">
                    Accept & Approve &rarr;
                </button>
                """
                return_btn = f"""
                <button type="button" class="btn-secondary btn-sm" style="font-size:11.5px; font-weight:700; color:#DC2626; border-color:rgba(239,68,68,0.4);"
                        onclick="window.StarAppBridge.dispatchAction('confirm_return_badge', '{b_id}')">
                    Return with Feedback
                </button>
                """
            elif wf_status == "returned":
                approve_btn = f"""
                <button type="button" class="btn-metal btn-sm" style="font-size:11.5px; font-weight:800;"
                        onclick="window.StarAppBridge.dispatchAction('confirm_approve_badge', '{b_id}')">
                    Re-evaluate & Approve &rarr;
                </button>
                """

            cards_html.append(f"""
            <div class="liquid-glass-card" style="padding:20px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-40); margin-bottom:16px; background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(240,247,255,0.9) 100%); box-shadow:0 4px 14px rgba(7,22,41,0.04);">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; margin-bottom:12px;">
                    <div>
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px; flex-wrap:wrap;">
                            <span style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 8px; border-radius:var(--radius-xs);">{b_code}</span>
                            <span style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:800; background:var(--frost-mist); color:var(--deep-frozen-midnight); padding:3px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30);">TARGET: BAND {target_band}</span>
                            {status_pill}
                        </div>
                        <h3 style="font-size:15.5px; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">{b_title}</h3>
                        <div style="font-size:12px; color:var(--frost-navy-75); font-weight:600;">{b_loc}</div>
                    </div>

                    <div style="text-align:right; font-size:11.5px; color:var(--frost-navy-50);">
                        <div>Assigned by: <strong style="color:var(--frost-navy);">{creator_name}</strong></div>
                        <div>Assigned: <strong>{assigned_at}</strong> &bull; Due: <strong style="color:#B45309;">{due_date}</strong></div>
                    </div>
                </div>

                <p style="font-size:12.5px; color:var(--frost-navy-75); margin:0 0 10px 0; line-height:1.5;">{b_desc}</p>

                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(280px, 100%), 1fr)); gap:14px; margin-bottom:14px;">
                    <div style="background:rgba(255,255,255,0.6); padding:10px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                        <div style="font-size:11px; font-weight:800; color:var(--frost-navy-50); text-transform:uppercase; letter-spacing:0.5px;">Key Learning Outcomes</div>
                        {outcomes_html}
                    </div>

                    <div style="background:rgba(255,255,255,0.6); padding:10px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                        <div style="font-size:11px; font-weight:800; color:var(--frost-navy-50); text-transform:uppercase; letter-spacing:0.5px;">Curriculum Topics</div>
                        {topics_html}
                    </div>
                </div>

                {reqs_html}
                {notes_box}

                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-top:16px; padding-top:14px; border-top:1px solid var(--icy-steel-25);">
                    <div style="font-size:11.5px; color:var(--frost-navy-50);">
                        Institutional Reviewer: <strong style="color:var(--deep-frozen-midnight);">{escape(current_user.name)} (Band {user_band})</strong>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                        {inspect_btn}
                        {edit_btn}
                        {return_btn}
                        {approve_btn}
                    </div>
                </div>
            </div>
            """)

    empty_html = f"""
    <div class="liquid-glass-card" style="padding:48px 24px; text-align:center; border-radius:var(--radius-md); border:1.5px dashed var(--icy-steel-40);">
        <div style="width:48px; height:48px; margin:0 auto 12px; border-radius:50%; background:rgba(23,52,92,0.06); display:flex; align-items:center; justify-content:center; color:var(--deep-frozen-midnight);">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        </div>
        <h3 style="font-size:16px; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">No Review Requests in this Queue</h3>
        <p style="font-size:13px; color:var(--frost-navy-50); margin:0; max-width:440px; margin:0 auto;">
            When Guardians author badges for lower bands and request your oversight, they will appear here for review and authorization.
        </p>
    </div>
    """

    # === REVIEWER ASSIGNMENT / MAPPING REQUESTS SECTION ===
    mapping_reqs = []
    try:
        all_m_reqs = store.get_mapping_requests() if hasattr(store, "get_mapping_requests") else []
        mapping_reqs = [r for r in all_m_reqs if r.get("reviewer_id") == current_user.id]
    except Exception:
        mapping_reqs = []

    m_req_cards = []
    for req in mapping_reqs:
        r_id = req.get("id", "")
        r_status = req.get("status", "pending")
        badge_name = req.get("badge", "Badge")
        band = req.get("band", "B1")
        cosmo_ids = req.get("cosmonaut_ids", [])
        cosmo_count = len(cosmo_ids)
        cosmo_names = []
        for cid in cosmo_ids:
            u = store.get_user_by_id(cid)
            cosmo_names.append(u.name if u else cid)
        cosmo_names_str = ", ".join(cosmo_names[:4]) + (f" +{len(cosmo_names)-4} more" if len(cosmo_names) > 4 else "")
        dates = req.get("review_dates") or []
        if len(dates) > 3:
            dates_str = f"{dates[0]} → {dates[-1]} ({len(dates)} Working Days)"
        else:
            dates_str = " → ".join(dates) if dates else "Schedule Pending"
        sent_ts = req.get("sent_at") or ""
        sent_at = sent_ts[:10] if sent_ts else ""

        if r_status == "accepted":
            status_badge = f'<span class="status-pill status-approved" style="display:inline-flex; align-items:center; gap:4px; font-size:11px; font-weight:800; background:rgba(5,150,105,0.12); color:#047857; border:1px solid rgba(5,150,105,0.3);">{get_icon("check", 12)} Request Accepted</span>'
            action_btns = f'<button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction(\'reject_mapping_request\', \'{r_id}\')" style="display:inline-flex; align-items:center; gap:4px; font-size:11px; color:#DC2626; border-color:rgba(220,38,38,0.3); font-weight:700;">{get_icon("x", 12)} Decline / Revoke</button>'
            card_border = "border:1.5px solid #059669; background:rgba(5,150,105,0.03);"
        elif r_status == "rejected":
            status_badge = f'<span class="status-pill status-rejected" style="display:inline-flex; align-items:center; gap:4px; font-size:11px; font-weight:800; background:rgba(239,68,68,0.12); color:#DC2626; border:1px solid rgba(239,68,68,0.3);">{get_icon("x", 12)} Request Declined</span>'
            action_btns = f'<button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction(\'accept_mapping_request\', \'{r_id}\')" style="display:inline-flex; align-items:center; gap:4px; font-size:11px; font-weight:700;">{get_icon("check", 12)} Accept Request</button>'
            card_border = "border:1px solid rgba(239,68,68,0.25); background:rgba(239,68,68,0.02);"
        else:
            status_badge = f'<span class="status-pill status-pending" style="display:inline-flex; align-items:center; gap:4px; font-size:11px; font-weight:800; background:rgba(245,158,11,0.12); color:#B45309; border:1px solid rgba(245,158,11,0.3);">{get_icon("clock", 12)} Awaiting Your Decision</span>'
            action_btns = f'''<button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('accept_mapping_request', '{r_id}')" style="display:inline-flex; align-items:center; gap:4px; font-size:11.5px; padding:6px 14px; background:#059669; border-color:#059669; color:#fff; font-weight:800;">{get_icon("check", 12)} Accept & Confirm</button>
            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('reject_mapping_request', '{r_id}')" style="display:inline-flex; align-items:center; gap:4px; font-size:11.5px; padding:6px 12px; color:#DC2626; border-color:rgba(220,38,38,0.3); font-weight:700;">{get_icon("x", 12)} Decline</button>'''
            card_border = "border:1.5px solid var(--icy-steel-50); background:rgba(255,255,255,0.95);"

        m_req_cards.append(f"""
        <div class="liquid-glass-card" style="padding:16px 20px; {card_border} display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; margin-bottom:12px;">
            <div style="display:flex; flex-direction:column; gap:6px;">
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    <span style="font-size:14.5px; font-weight:800; color:var(--frost-navy);">{escape(badge_name)}</span>
                    <span style="font-family:var(--font-family-mono); font-size:10px; font-weight:900; background:var(--deep-frozen-midnight); color:#fff; padding:2px 7px; border-radius:3px;">BAND {escape(band)}</span>
                    {status_badge}
                </div>
                <div style="font-size:12px; color:var(--frost-navy-75);">
                    <span style="display:inline-flex; align-items:center; gap:5px;">{get_icon("users", 13)} <strong>{cosmo_count}</strong> Assigned Cosmonaut(s): <span style="color:var(--deep-frozen-midnight); font-weight:600;">{escape(cosmo_names_str)}</span></span>
                </div>
                <div style="font-size:11.5px; color:var(--frost-navy-50); display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                    <span style="display:inline-flex; align-items:center; gap:5px;">{get_icon("calendar", 13)} Review Window: <strong style="color:#047857;">{escape(dates_str)}</strong></span>
                    {f'<span>&bull; Sent: {escape(sent_at)}</span>' if sent_at else ''}
                </div>
            </div>
            <div style="display:flex; gap:8px; align-items:center; flex-shrink:0;">
                {action_btns}
            </div>
        </div>
        """)

    mapping_section_html = f"""
    <div class="liquid-glass-card" style="padding:22px; margin-top:32px; border:1.5px solid var(--icy-steel-50);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid var(--icy-steel-30); flex-wrap:wrap; gap:10px;">
            <div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0;">
                        Cadet Evaluation Invitations
                    </h3>
                </div>
            </div>
            <span class="status-pill status-active" style="font-weight:700; font-size:11px;">
                {len(mapping_reqs)} Review Assignment(s)
            </span>
        </div>
        <div>
            {''.join(m_req_cards) if m_req_cards else "<div style='text-align:center; padding:32px 20px; color:var(--frost-navy-50); font-size:13px; background:rgba(255,255,255,0.6); border:1px dashed var(--icy-steel-50); border-radius:var(--radius-sm);'>No pending reviewer mapping requests. When a Guardian selects you in the Mapping Matrix, assignments will appear here.</div>"}
        </div>
    </div>
    """

    return f"""
    <div>
        <!-- Heading -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:16px;">
            <div>
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 8px; border-radius:var(--radius-xs);">BAND {user_band}</span>
                    <span style="font-size:11px; font-weight:700; color:var(--frost-navy-50);">{user_track}</span>
                </div>
                <h1 style="font-size:1.85rem; font-weight:800; color:var(--frost-navy); letter-spacing:-0.5px; margin:0 0 4px 0;">Review Requests</h1>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
                {render_back_button()}
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_dashboard')" style="font-weight:700;">
                    &larr; Dashboard
                </button>
            </div>
        </div>

        <!-- Section 1: Badge Approval Requests -->
        <div class="liquid-glass-card" style="padding:22px; margin-bottom:24px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid var(--icy-steel-30); flex-wrap:wrap; gap:10px;">
                <div>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0;">
                        Badge Approval Requests
                    </h3>
                </div>
            </div>

            <!-- Filter tabs & Search -->
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; margin-bottom:16px;">
                {tabs_html}
                <div style="min-width:240px; max-width:320px; width:100%;">
                    <input type="text" class="form-input" placeholder="Search request, code, band..." value="{escape(search_query)}" style="font-size:12px; padding:7px 12px;"
                           oninput="window.StarAppBridge.dispatchAction('search_cosmo_requests', this.value)">
                </div>
            </div>

            <!-- Request Cards List -->
            <div>
                {"".join(cards_html) if cards_html else empty_html}
            </div>
        </div>

        <!-- Section 2: Cadet Evaluation Invitations -->
        {mapping_section_html}
    </div>
    """


# ==============================================================================
# 6.12B REVIEWER BADGE REVIEW SCHEDULE WORKSPACE
# ==============================================================================

def _format_review_window_label(tl_obj: Any, r_dates: Optional[List[str]] = None) -> str:
    """Formats a multi-day review window list or BadgeTimeline review_window_json cleanly."""
    dates = list(r_dates or [])
    if not dates and tl_obj and getattr(tl_obj, "review_window_json", None):
        try:
            parsed = json.loads(tl_obj.review_window_json)
            if isinstance(parsed, list):
                dates = [str(d) for d in parsed if d]
        except Exception:
            dates = []
    if dates:
        if len(dates) > 3:
            return f"{dates[0]} \u2192 {dates[-1]} ({len(dates)} Days)"
        return " \u2192 ".join(dates)
    if tl_obj and getattr(tl_obj, "review_date", ""):
        return str(tl_obj.review_date)
    return "Schedule Pending"


def _render_review_deliverables_tray(sub: ProjectSubmission) -> str:
    """Renders compact submitted deliverable artifact pills for Upcoming & Completed review cards."""
    pdf_name = getattr(sub, "pdf_name", "") or (sub.file_name if getattr(sub, "submission_type", "") == "pdf" else "") or "Report.pdf"
    code_name = getattr(sub, "code_name", "") or (sub.file_name if getattr(sub, "submission_type", "") == "code" else "") or "solution.py"
    github_url = getattr(sub, "github_url", "") or (sub.payload if getattr(sub, "submission_type", "") == "github" else "") or ""
    repo_lbl = github_url.split("/")[-1] if "/" in github_url else (github_url or "GitHub Repo")
    sub_dt = (getattr(sub, "submitted_at", "") or "")[:16].replace("T", " ")

    pdf_ic = get_icon("file_text", 12, "margin-right:4px; color:#D32F2F;")
    code_ic = get_icon("code", 12, "margin-right:4px; color:var(--deep-frozen-midnight);")
    gh_ic = get_icon("github", 12, "margin-right:4px; color:var(--frost-navy);")

    gh_pill = (
        f'<span style="display:inline-flex; align-items:center; font-size:11px; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{gh_ic}{escape(repo_lbl)}</span>'
        if github_url else ""
    )
    return f"""
    <div style="background:rgba(241,245,249,0.75); border:1px solid var(--icy-steel-30); border-radius:8px; padding:8px 12px; margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:5px;">
            <span style="font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:0.45px; color:var(--frost-navy-50);">Submitted Deliverables &bull; Attempt #{getattr(sub, 'attempt_number', 1)}</span>
            {f'<span style="font-size:10.5px; font-family:var(--font-family-mono); color:var(--frost-navy-50);">{escape(sub_dt)} UTC</span>' if sub_dt else ''}
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
            <span style="display:inline-flex; align-items:center; font-size:11px; font-weight:700; color:var(--frost-navy); background:#FFFFFF; border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{pdf_ic}{escape(pdf_name)}</span>
            <span style="display:inline-flex; align-items:center; font-size:11px; font-weight:700; color:var(--frost-navy); background:#FFFFFF; border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{code_ic}{escape(code_name)}</span>
            {gh_pill}
        </div>
    </div>
    """


def _collect_cadet_review_context(
    store: Any,
    b_id: str,
    c_actual_id: str,
    b_prompt: List[Any],
    tl_obj: Any = None,
) -> Dict[str, Any]:
    """Gathers submissions, reviewer/guardian evaluations, project prompt, and completion status for a cadet badge pair."""
    assigned_proj = store.get_project_prompt_for_cadet(b_id, c_actual_id) if (store and b_id) else None
    if not assigned_proj and store and b_id and b_prompt:
        for p in b_prompt:
            if c_actual_id in getattr(p, "cosmonaut_ids", []):
                assigned_proj = p
                break
        if not assigned_proj:
            assigned_proj = b_prompt[0]

    c_subs: List[ProjectSubmission] = []
    if store and b_id and c_actual_id:
        c_subs = list(store.get_submissions_for_cosmonaut(c_actual_id, b_id) or [])
        if not c_subs:
            c_subs = [
                s for s in store.get_all_submissions()
                if s.cosmonaut_id == c_actual_id and s.badge_id == b_id
            ]
        c_subs.sort(key=lambda s: getattr(s, "attempt_number", 1))
    latest_sub = c_subs[-1] if c_subs else None

    rev_asm = None
    g_asm = None
    all_pair_asms: List[AssessmentMarksheet] = []
    if store and b_id and c_actual_id:
        all_pair_asms = sorted(
            store.get_assessments_for_cosmonaut(c_actual_id, b_id) or [],
            key=lambda a: (getattr(a, "attempt_number", 1), getattr(a, "reviewed_at", "")),
        )
        if latest_sub:
            rev_asm = store.get_reviewer_assessment_for_submission(latest_sub.id)
            if hasattr(store, "get_guardian_assessment_for_submission"):
                g_asm = store.get_guardian_assessment_for_submission(latest_sub.id)
        for a in all_pair_asms:
            role = getattr(a, "assessor_role", "")
            if role == "reviewer" and (not latest_sub or a.submission_id == latest_sub.id or not rev_asm):
                rev_asm = a
            elif role == "guardian" and (not latest_sub or a.submission_id == latest_sub.id or not g_asm):
                g_asm = a
            elif not role and not g_asm and a.decision == "approve":
                g_asm = a

    if tl_obj is None and store and b_id and c_actual_id:
        tl_obj = store.get_timeline(b_id, c_actual_id)

    is_completed = bool(
        (tl_obj and (getattr(tl_obj, "status", "") in ("completed", "awarded") or getattr(tl_obj, "actual_award_date", "")))
        or (latest_sub and getattr(latest_sub, "status", "") == "approved")
        or (g_asm and getattr(g_asm, "decision", "") == "approve")
    )
    award_date = (
        (getattr(tl_obj, "actual_award_date", "") if tl_obj else "")
        or (g_asm.reviewed_at[:10] if g_asm and getattr(g_asm, "reviewed_at", "") else "")
        or (getattr(tl_obj, "expected_award_date", "") if tl_obj else "")
    )
    return {
        "assigned_proj": assigned_proj,
        "subs": c_subs,
        "latest_sub": latest_sub,
        "rev_asm": rev_asm,
        "g_asm": g_asm,
        "all_asms": all_pair_asms,
        "tl": tl_obj,
        "is_completed": is_completed,
        "award_date": award_date,
    }


def render_reviewer_badge_schedule(
    current_user: User,
    store: Any,
    badges_map: Optional[Dict[str, Badge]] = None,
    cosmo_map: Optional[Dict[str, User]] = None,
    expanded_badge_id: Optional[str] = None
) -> str:
    """
    Renders the Reviewer Badge Review Schedule Workspace.
    Displays upcoming and completed badge review assignments for higher-band reviewers.
    """
    if store is None:
        from starapp.storage import store as global_store
        store = global_store
    badges_map = badges_map or {b.id: b for b in store.get_all_badges()}
    cosmo_map = cosmo_map or store.users
    target_cid = store.get_effective_read_cycle_id()

    user_band = getattr(current_user, "band", "B2")

    upcoming_entries = []
    completed_entries = []

    # Step 1: Collect timelines from memory and SQLite strictly within active read cycle
    scoped_tl_dict = store.get_timelines_dict(cycle_id=target_cid) if hasattr(store, "get_timelines_dict") else {}
    all_timelines = list(scoped_tl_dict.values())
    if store.db and store.db.conn:
        try:
            t_rows = store.db.conn.execute(
                "SELECT * FROM badge_timelines WHERE reviewer_id = ? AND cycle_id = ? ORDER BY review_date",
                (current_user.id, target_cid)
            ).fetchall()
            for r in t_rows:
                rd = dict(r)
                if not any(t.badge_id == rd.get("badge_id") and t.cosmonaut_id == rd.get("cosmonaut_id") for t in all_timelines):
                    from starapp.models import BadgeTimeline
                    all_timelines.append(BadgeTimeline.from_dict(rd))
        except Exception:
            pass

    # Collect pairs assigned to other reviewers to avoid leaking across reviewers
    other_reviewer_pairs = set()
    try:
        for tl in all_timelines:
            rev_id = getattr(tl, "reviewer_id", "")
            if rev_id and rev_id != current_user.id:
                other_reviewer_pairs.add((tl.badge_id, tl.cosmonaut_id))
        if store.db and store.db.conn:
            rows = store.db.conn.execute(
                "SELECT badge_id, cosmonaut_id, reviewer_id FROM badge_timelines WHERE cycle_id = ? AND reviewer_id != '' AND reviewer_id != ?",
                (target_cid, current_user.id)
            ).fetchall()
            for r in rows:
                other_reviewer_pairs.add((r["badge_id"], r["cosmonaut_id"]))
    except Exception:
        pass

    seen_pairs = set()

    # 1. Timelines strictly where reviewer_id == current_user.id
    for tl in all_timelines:
        if getattr(tl, "reviewer_id", "") == current_user.id:
            pair = (tl.badge_id, tl.cosmonaut_id)
            if pair in seen_pairs:
                continue
            b = badges_map.get(tl.badge_id) or store.get_badge(tl.badge_id)
            if b and not getattr(b, "is_published", False) and b.code not in ("GOV-101", "CUR-102", "DAT-103"):
                continue
            if getattr(tl, "status", "") == "locked":
                continue
            seen_pairs.add(pair)
            c = cosmo_map.get(tl.cosmonaut_id) or store.get_user_by_id(tl.cosmonaut_id)
            ctx = _collect_cadet_review_context(store, tl.badge_id, tl.cosmonaut_id, [], tl_obj=tl)
            item = {
                "badge": b,
                "cosmonaut": c,
                "badge_id": tl.badge_id,
                "cosmonaut_id": tl.cosmonaut_id,
                "timeline": tl,
                "status": "completed" if ctx["is_completed"] else getattr(tl, "status", "active"),
                "review_date": _format_review_window_label(tl),
                "deadline": getattr(tl, "submission_deadline", "TBD") or "TBD",
                "award_date": ctx["award_date"],
            }
            if ctx["is_completed"]:
                completed_entries.append(item)
            else:
                upcoming_entries.append(item)

    # 2. Band mappings strictly for current_user (matching Guardian contiguous chunking / explicit reviewer_assignments)
    try:
        mappings = store.get_band_mappings()
        for m in mappings:
            rev_list = list(m.get("reviewers", []) or [])
            if current_user.id not in rev_list:
                continue
            b_name = m.get("badge", "")
            b_obj = None
            for b in badges_map.values():
                if b.title == b_name or b.code == b_name or b.id == b_name or (m.get("badge_id") and b.id == m.get("badge_id")):
                    b_obj = b
                    break
            if b_obj and not getattr(b_obj, "is_published", False) and b_obj.code not in ("GOV-101", "CUR-102", "DAT-103"):
                continue
            b_id_resolved = b_obj.id if b_obj else (m.get("badge_id") or b_name)
            r_dates = list(m.get("review_dates", []) or [])
            r_dates_str = _format_review_window_label(None, r_dates)

            rev_assigns = m.get("reviewer_assignments") or {}
            cosmo_list = list(m.get("cosmonauts", []) or [])
            if isinstance(rev_assigns, dict) and current_user.id in rev_assigns:
                target_cadets = list(rev_assigns.get(current_user.id) or [])
            elif len(rev_list) > 1 and cosmo_list:
                n_rev = len(rev_list)
                chunk, rem = divmod(len(cosmo_list), n_rev)
                c_idx = 0
                target_cadets = []
                for ri, r_id in enumerate(rev_list):
                    take = chunk + (1 if ri < rem else 0)
                    slice_ids = cosmo_list[c_idx:c_idx + take]
                    c_idx += take
                    if r_id == current_user.id:
                        target_cadets = slice_ids
                        break
            else:
                target_cadets = cosmo_list

            for cid in target_cadets:
                pair = (b_id_resolved, cid)
                if pair in other_reviewer_pairs or pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                c_obj = cosmo_map.get(cid) or store.get_user_by_id(cid)
                tl_pair = store.get_timeline(b_id_resolved, cid) if store else None
                ctx = _collect_cadet_review_context(store, b_id_resolved, cid, [], tl_obj=tl_pair)
                is_uncoupled = (cid in m.get("completed_cosmonauts", []) or cid in m.get("uncoupled_cadets", []))
                is_comp = is_uncoupled or ctx["is_completed"]
                r_win_final = _format_review_window_label(tl_pair, r_dates) if (tl_pair or r_dates) else "Schedule Pending"
                dl_final = (getattr(tl_pair, "submission_deadline", "") if tl_pair else "") or (r_dates[-1] if r_dates else "TBD")
                m_item = {
                    "badge": b_obj,
                    "cosmonaut": c_obj,
                    "badge_id": b_id_resolved,
                    "cosmonaut_id": cid,
                    "badge_title": b_name,
                    "timeline": tl_pair,
                    "status": "completed" if is_comp else "active",
                    "review_date": r_win_final,
                    "deadline": dl_final,
                    "award_date": ctx["award_date"],
                }
                if is_comp:
                    completed_entries.append(m_item)
                else:
                    upcoming_entries.append(m_item)
    except Exception:
        pass

    # 3. Direct badge assignment ONLY if NO band mappings exist for this badge
    try:
        all_mappings = store.get_band_mappings()
        mapped_badge_ids = set()
        for m in all_mappings:
            if m.get("badge_id"):
                mapped_badge_ids.add(m.get("badge_id"))
            if m.get("badge"):
                mapped_badge_ids.add(m.get("badge"))

        for b in badges_map.values():
            if getattr(b, "assigned_reviewer_id", "") == current_user.id:
                if b.id in mapped_badge_ids or b.title in mapped_badge_ids or b.code in mapped_badge_ids:
                    continue
                if not getattr(b, "is_published", False) and b.code not in ("GOV-101", "CUR-102", "DAT-103"):
                    continue
                dt = getattr(b, "default_timeline", {}) or {}
                r_dates = dt.get("review_dates", [])
                for cid in getattr(b, "assigned_cosmonaut_ids", []):
                    pair = (b.id, cid)
                    if pair in other_reviewer_pairs or pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    c_obj = cosmo_map.get(cid) or store.get_user_by_id(cid)
                    tl_obj = store.get_timeline(b.id, cid) if store else None
                    ctx = _collect_cadet_review_context(store, b.id, cid, [], tl_obj=tl_obj)
                    is_b_comp = ctx["is_completed"] or (cid in getattr(b, "completed_cosmonaut_ids", []))
                    b_item = {
                        "badge": b,
                        "cosmonaut": c_obj,
                        "badge_id": b.id,
                        "cosmonaut_id": cid,
                        "badge_title": b.title,
                        "timeline": tl_obj,
                        "status": "completed" if is_b_comp else "active",
                        "review_date": _format_review_window_label(tl_obj, r_dates),
                        "deadline": (getattr(tl_obj, "submission_deadline", "") if tl_obj else "") or dt.get("submission_deadline", "") or (r_dates[-1] if r_dates else "TBD"),
                        "award_date": ctx["award_date"],
                    }
                    if is_b_comp:
                        completed_entries.append(b_item)
                    else:
                        upcoming_entries.append(b_item)
    except Exception:
        pass

    # 4. Assessment records fallback for current_user within active read cycle (catches any graded cadet missing from timelines/mappings)
    try:
        for a in store.get_all_assessments(cycle_id=target_cid):
            if getattr(a, "reviewer_id", "") != current_user.id or getattr(a, "assessor_role", "reviewer") == "guardian":
                continue
            pair = (a.badge_id, a.cosmonaut_id)
            if pair in seen_pairs or pair in other_reviewer_pairs:
                continue
            b_obj = badges_map.get(a.badge_id) or store.get_badge(a.badge_id)
            if not b_obj or (not getattr(b_obj, "is_published", False) and b_obj.code not in ("GOV-101", "CUR-102", "DAT-103")):
                continue
            seen_pairs.add(pair)
            c_obj = cosmo_map.get(a.cosmonaut_id) or store.get_user_by_id(a.cosmonaut_id)
            tl_obj = store.get_timeline(a.badge_id, a.cosmonaut_id)
            ctx = _collect_cadet_review_context(store, a.badge_id, a.cosmonaut_id, [], tl_obj=tl_obj)
            f_item = {
                "badge": b_obj,
                "cosmonaut": c_obj,
                "badge_id": b_obj.id,
                "cosmonaut_id": a.cosmonaut_id,
                "badge_title": b_obj.title,
                "timeline": tl_obj,
                "status": "completed" if ctx["is_completed"] else "active",
                "review_date": _format_review_window_label(tl_obj),
                "deadline": getattr(tl_obj, "submission_deadline", "TBD") if tl_obj else "TBD",
                "award_date": ctx["award_date"],
            }
            if ctx["is_completed"]:
                completed_entries.append(f_item)
            else:
                upcoming_entries.append(f_item)
    except Exception:
        pass

    # Group upcoming entries by Badge
    badge_groups = {}
    for item in upcoming_entries:
        b = item.get("badge")
        b_id = b.id if b else item.get("badge_id", "")
        if b_id not in badge_groups:
            badge_groups[b_id] = {
                "badge": b,
                "badge_id": b_id,
                "badge_title": b.title if b else item.get("badge_title", "Curriculum Badge"),
                "badge_code": b.code if b else "",
                "badge_band": getattr(b, "target_band", "B1") if b else "",
                "badge_cat": getattr(b, "category", "") or getattr(b, "skill", ""),
                "review_date": item.get("review_date", "Schedule Pending"),
                "deadline": item.get("deadline", "TBD"),
                "cadets": []
            }
        badge_groups[b_id]["cadets"].append(item)

    upcoming_cards_html = []
    for b_id, bg in badge_groups.items():
        cadets_list = bg["cadets"]
        num_cadets = len(cadets_list)

        # Show all upcoming cadet cards on initial load so zero data is hidden; still allow explicit focus/collapse toggling
        if expanded_badge_id == b_id:
            is_expanded = True
        elif expanded_badge_id == "":
            is_expanded = False
        elif expanded_badge_id is None:
            is_expanded = True
        else:
            is_expanded = False

        b_prompt = store.get_reviewer_project_prompts(badge_id=b_id, reviewer_id=current_user.id) if store else []
        badge_prompt_status = getattr(b_prompt[0], "status", "none") if b_prompt else "none"

        if badge_prompt_status in ("released", "sent"):
            badge_proj_pill = '<span class="status-pill status-approved" style="font-size:11px; font-weight:800; background:rgba(5,150,105,0.12); color:#047857; border:1px solid rgba(5,150,105,0.3);">✓ Project Released</span>'
            badge_btn_text = "✏️ Edit Project"
        elif badge_prompt_status == "draft":
            badge_proj_pill = '<span class="status-pill status-warning" style="font-size:11px; font-weight:800; background:rgba(245,158,11,0.12); color:#B45309; border:1px solid rgba(245,158,11,0.3);">📝 Draft Project Saved</span>'
            badge_btn_text = "📝 Continue Project Draft"
        else:
            badge_proj_pill = '<span class="status-pill status-warning" style="font-size:11px; font-weight:800; background:rgba(245,158,11,0.12); color:#B45309; border:1px solid rgba(245,158,11,0.3);">⏳ 3-Day Project Preparation</span>'
            badge_btn_text = "✨ Create Project (AI)"

        chevron = "▲" if is_expanded else "▼"

        cadet_cards_html = []
        roster_summary_chips = []
        for item in cadets_list:
            c = item.get("cosmonaut")
            c_actual_id = c.id if c else item.get("cosmonaut_id", "")
            c_name = c.name if c else c_actual_id
            c_band = getattr(c, "band", "B1") if c else "B1"
            c_track = getattr(c, "learning_track", getattr(c, "role", "Cosmonaut")) if c else "Cosmonaut"
            c_avatar = getattr(c, "avatar", (c_name[:2].upper() if c_name else "CO"))
            r_date = item.get("review_date", "TBD")
            deadline = item.get("deadline", "TBD")

            ctx = _collect_cadet_review_context(store, b_id, c_actual_id, b_prompt, tl_obj=item.get("timeline"))
            assigned_proj = ctx["assigned_proj"]
            sub = ctx["latest_sub"]
            rev_asm = ctx["rev_asm"]
            g_asm = ctx["g_asm"]

            if sub and getattr(sub, "status", "") in ("retake_required", "resubmission_requested"):
                card_status_pill = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:700; background:#FEE2E2; border:1px solid #FCA5A5; color:#991B1B; padding:2px 10px; border-radius:999px;"><span>&bull;</span> Retake Required (Awaiting Cadet)</span>'
                short_status = "Retake Required"
                card_action_btn = f"""
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('open_reviewer_assessment_page', '{escape(sub.id)}')" style="display:inline-flex; align-items:center; gap:6px;">
                    Inspect Submission &amp; History &rarr;
                </button>
                """
            elif rev_asm:
                card_status_pill = f'<span style="display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:700; background:#EEF2FF; border:1px solid #C7D2FE; color:#4338CA; padding:2px 10px; border-radius:999px;"><span style="font-size:13px; line-height:1;">&bull;</span> ✓ Evaluated: {rev_asm.total_marks:.1f}/50 ({rev_asm.percentage:.1f}%)</span>'
                short_status = f"Evaluated {rev_asm.total_marks:.1f}/50"
                card_action_btn = f"""
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('open_reviewer_assessment_page', '{escape(sub.id if sub else rev_asm.submission_id)}')" style="display:inline-flex; align-items:center; gap:6px;">
                    📊 View Marksheet ({rev_asm.total_marks:.1f}/50) &rarr;
                </button>
                """
            elif sub:
                card_status_pill = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:700; background:#D1FAE5; border:1px solid #A7F3D0; color:#065F46; padding:2px 10px; border-radius:999px;"><span style="font-size:13px; line-height:1;">&bull;</span> 📥 Deliverables Submitted</span>'
                short_status = f"Attempt #{getattr(sub, 'attempt_number', 1)} Submitted"
                card_action_btn = f"""
                <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_reviewer_assessment_page', '{escape(sub.id)}')" style="display:inline-flex; align-items:center; gap:6px;">
                    📝 Inspect Deliverables & Allocate Marks &rarr;
                </button>
                """
            elif assigned_proj and getattr(assigned_proj, "status", "") in ("released", "sent"):
                card_status_pill = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:700; background:#E0F2FE; border:1px solid #BAE6FD; color:#0284C7; padding:2px 10px; border-radius:999px;"><span style="font-size:13px; line-height:1;">&bull;</span> 🚀 Project Given</span>'
                short_status = "Project Given"
                card_action_btn = f"""
                <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_create_reviewer_project_modal', '{escape(b_id)}')" style="display:inline-flex; align-items:center; gap:6px;">
                    ✏️ Edit Project
                </button>
                """
            elif assigned_proj and getattr(assigned_proj, "status", "") == "draft":
                card_status_pill = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:700; background:#FEF3C7; border:1px solid #FDE68A; color:#B45309; padding:2px 10px; border-radius:999px;"><span style="font-size:13px; line-height:1;">&bull;</span> 📝 Draft Project Saved</span>'
                short_status = "Draft Saved"
                card_action_btn = f"""
                <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_create_reviewer_project_modal', '{escape(b_id)}')" style="display:inline-flex; align-items:center; gap:6px;">
                    📝 Continue Project Draft
                </button>
                """
            else:
                card_status_pill = '<span style="display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:700; background:#FEF3C7; border:1px solid #FDE68A; color:#B45309; padding:2px 10px; border-radius:999px;"><span style="font-size:13px; line-height:1;">&bull;</span> ⏳ 3-Day Project Preparation</span>'
                short_status = "3-Day Prep"
                card_action_btn = f"""
                <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_create_reviewer_project_modal', '{escape(b_id)}')" style="display:inline-flex; align-items:center; gap:6px;">
                    ✨ Create Project (AI)
                </button>
                """

            roster_summary_chips.append(
                f'<span style="font-size:11px; font-weight:700; color:var(--frost-navy); background:rgba(255,255,255,0.85); border:1px solid var(--icy-steel-40); padding:2px 8px; border-radius:999px;">{escape(c_name)} &bull; <span style="color:#0284C7;">{escape(short_status)}</span></span>'
            )

            proj_banner_html = ""
            if assigned_proj and getattr(assigned_proj, "title", ""):
                proj_st_lbl = "Released Brief" if getattr(assigned_proj, "status", "") in ("released", "sent") else "Draft Brief"
                proj_banner_html = f"""
                <div style="font-size:12px; color:#0369A1; background:rgba(224,242,254,0.6); border:1px solid rgba(2,132,199,0.25); border-radius:7px; padding:6px 10px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px;">
                    <span><strong>Assigned Project ({escape(proj_st_lbl)}):</strong> {escape(assigned_proj.title)}</span>
                </div>
                """

            sub_tray_html = _render_review_deliverables_tray(sub) if sub else ""

            eval_note_html = ""
            if rev_asm or g_asm:
                bits = []
                if rev_asm:
                    fb_prev = (getattr(rev_asm, "overall_feedback", "") or getattr(rev_asm, "remarks", "") or "").strip()
                    bits.append(f'<strong>Your Evaluation:</strong> {rev_asm.total_marks:.1f}/50 ({rev_asm.percentage:.1f}%){f" — {escape(fb_prev)}" if fb_prev else ""}')
                if g_asm:
                    g_fb = (getattr(g_asm, "overall_feedback", "") or getattr(g_asm, "remarks", "") or "").strip()
                    bits.append(f'<strong>Guardian Review ({escape(g_asm.decision.replace("_", " ").title())}):</strong> {g_asm.total_marks:.1f}/50{f" — {escape(g_fb)}" if g_fb else ""}')
                eval_note_html = f'<div style="font-size:11.5px; color:#1E293B; background:rgba(238,242,255,0.75); border:1px solid #C7D2FE; border-radius:7px; padding:7px 11px; margin-bottom:10px; line-height:1.45;">{"<br>".join(bits)}</div>'

            cadet_cards_html.append(f"""
            <div class="liquid-glass-card" style="padding:18px 22px; border:1.5px solid var(--icy-steel); background:#FFFFFF; border-radius:12px; box-shadow:0 4px 14px rgba(7,22,41,0.05); margin-bottom:12px;">
                <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; gap:10px; min-width:0;">
                        <div class="user-avatar" style="width:34px; height:34px; font-size:11.5px; font-weight:800; border:1px solid var(--icy-steel); flex-shrink:0;">{escape(c_avatar)}</div>
                        <div style="min-width:0;">
                            <div style="font-size:15px; font-weight:800; color:var(--frost-navy); line-height:1.25;">{escape(c_name)}</div>
                            <div style="font-size:12.5px; color:var(--frost-navy-75);">Band {escape(c_band)} &bull; {escape(c_track)}</div>
                        </div>
                    </div>
                    {card_status_pill}
                </div>
                <div style="display:flex; gap:22px; flex-wrap:wrap; font-size:12.5px; color:var(--frost-navy); margin-bottom:12px;">
                    <span>📅 Review Window: <strong style="color:#047857;">{escape(r_date)}</strong></span>
                    <span>⏰ Submission Deadline: <strong style="color:#B91C1C;">{escape(deadline)}</strong></span>
                </div>
                {proj_banner_html}
                {sub_tray_html}
                {eval_note_html}
                <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('open_reviewer_badge_timeline_modal', '{escape(b_id)}')" style="display:inline-flex; align-items:center; gap:6px;">
                        📅 View Timeline
                    </button>
                    {card_action_btn}
                    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_assessments')" style="display:inline-flex; align-items:center; gap:6px;">
                        Cadet Assessments &rarr;
                    </button>
                </div>
            </div>
            """)

        expanded_section_html = f"""
        <div style="padding:16px 20px; background:rgba(241,245,249,0.5); display:flex; flex-direction:column; gap:12px;">
            {"".join(cadet_cards_html)}
        </div>
        """ if is_expanded else ""

        upcoming_cards_html.append(f"""
        <div class="liquid-glass-card" style="padding:0; border:1.5px solid var(--deep-frozen-midnight); background:#FFFFFF; border-radius:12px; margin-bottom:18px; box-shadow:0 4px 18px rgba(23,52,92,0.08); overflow:hidden;">
            <!-- Level 1 Badge Name Card (Clickable Header) -->
            <div onclick="window.StarAppBridge.dispatchAction('toggle_reviewer_badge_expand', '{escape(b_id)}')"
                 style="padding:16px 22px; cursor:pointer; background:linear-gradient(135deg, rgba(234,244,255,0.98) 0%, rgba(255,255,255,0.98) 100%); border-bottom:{'1.5px solid var(--icy-steel-30)' if is_expanded else 'none'}; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div style="flex:1; min-width:240px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap;">
                        {f'<span style="font-family:var(--font-family-mono); font-size:11.5px; font-weight:900; background:#0F172A; color:#FFFFFF; padding:2px 8px; border-radius:3px; letter-spacing:0.5px;">{escape(bg["badge_code"])}</span>' if bg["badge_code"] else ''}
                        <span style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:800; background:#E2E8F0; color:#1E293B; padding:2px 7px; border-radius:3px;">BAND {escape(bg["badge_band"])}</span>
                        {f'<span style="font-size:12px; font-weight:600; color:#64748B;">{escape(bg["badge_cat"])}</span>' if bg["badge_cat"] else ''}
                        <span class="status-pill status-active" style="font-size:11px; font-weight:700;">Upcoming Review</span>
                        {badge_proj_pill}
                    </div>
                    <h3 style="font-size:1.3rem; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0; letter-spacing:-0.3px;">
                        {escape(bg["badge_title"])}
                    </h3>
                    <div style="font-size:12px; color:var(--frost-navy-50); margin-bottom:8px;">
                        📅 Review Window: <strong style="color:#047857;">{escape(bg["review_date"])}</strong> &bull; ⏰ Deadline: <strong style="color:#DC2626;">{escape(bg["deadline"])}</strong>
                    </div>
                    <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
                        {"".join(roster_summary_chips)}
                    </div>
                </div>

                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;" onclick="event.stopPropagation();">
                    <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_create_reviewer_project_modal', '{escape(b_id)}')" style="font-size:11.5px; padding:6px 14px; font-weight:800; background:linear-gradient(135deg, #0284C7, #0369A1); border-color:#0284C7; color:#fff;">
                        {badge_btn_text}
                    </button>
                    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('toggle_reviewer_badge_expand', '{escape(b_id)}')" style="font-size:11.5px; padding:6px 14px; font-weight:700; display:inline-flex; align-items:center; gap:6px; background:#FFFFFF; border:1.5px solid #CBD5E1; color:#1E293B;">
                        👥 {num_cadets} Mapped Cadet{'s' if num_cadets != 1 else ''} {chevron}
                    </button>
                </div>
            </div>

            <!-- Level 2/3 Dedicated Cadet Cards -->
            {expanded_section_html}
        </div>
        """)

    completed_cards_html = []
    for item in completed_entries:
        b = item.get("badge")
        c = item.get("cosmonaut")
        b_id_c = b.id if b else item.get("badge_id", "")
        b_title = b.title if b else item.get("badge_title", item.get("badge_id", "Milestone"))
        b_code = b.code if b else ""
        b_band = getattr(b, "target_band", "B1") if b else ""
        b_cat = (getattr(b, "category", "") or getattr(b, "skill", "")) if b else ""
        c_actual_id = c.id if c else item.get("cosmonaut_id", "")
        c_name = c.name if c else c_actual_id
        c_band = getattr(c, "band", "B1") if c else "B1"
        c_track = getattr(c, "learning_track", getattr(c, "role", "Cosmonaut")) if c else "Cosmonaut"
        c_email = getattr(c, "email", "") if c else ""
        c_avatar = getattr(c, "avatar", (c_name[:2].upper() if c_name else "CO"))

        b_prompt_c = store.get_reviewer_project_prompts(badge_id=b_id_c, reviewer_id=current_user.id) if (store and b_id_c) else []
        ctx_c = _collect_cadet_review_context(store, b_id_c, c_actual_id, b_prompt_c, tl_obj=item.get("timeline"))
        sub_c = ctx_c["latest_sub"]
        rev_asm_c = ctx_c["rev_asm"]
        g_asm_c = ctx_c["g_asm"]
        proj_c = ctx_c["assigned_proj"]
        award_date = item.get("award_date") or ctx_c["award_date"] or "Completed"
        r_win_c = item.get("review_date", "Schedule Recorded")

        score_pills = []
        if rev_asm_c:
            score_pills.append(
                f'<span style="font-size:11.5px; font-weight:800; color:#0369A1; background:rgba(224,242,254,0.9); border:1px solid rgba(2,132,199,0.3); padding:3px 10px; border-radius:999px;">Reviewer Score: <strong>{rev_asm_c.total_marks:.1f} / 50 ({rev_asm_c.percentage:.1f}%)</strong></span>'
            )
        if g_asm_c:
            score_pills.append(
                f'<span style="font-size:11.5px; font-weight:800; color:#047857; background:rgba(209,250,229,0.9); border:1px solid rgba(16,185,129,0.35); padding:3px 10px; border-radius:999px;">Guardian Final: <strong>{g_asm_c.total_marks:.1f} / 50 ({g_asm_c.percentage:.1f}%)</strong></span>'
            )
        if not score_pills:
            score_pills.append(
                '<span style="font-size:11.5px; font-weight:700; color:#047857; background:rgba(209,250,229,0.75); border:1px solid rgba(16,185,129,0.3); padding:3px 10px; border-radius:999px;">Certified Cohort Record</span>'
            )

        feedback_preview = ""
        best_asm = g_asm_c or rev_asm_c
        if best_asm:
            fb_str = (getattr(best_asm, "overall_feedback", "") or getattr(best_asm, "remarks", "") or "").strip()
            if fb_str:
                feedback_preview = f'<div style="font-size:12px; color:#334155; background:rgba(248,250,252,0.9); border-left:3px solid #10B981; padding:6px 10px; border-radius:4px; margin-bottom:10px;"><strong>Evaluation Remarks:</strong> {escape(fb_str)}</div>'

        proj_line_c = (
            f'<div style="font-size:12px; color:#0369A1; margin-bottom:8px;"><strong>Allocated Project:</strong> {escape(proj_c.title)}</div>'
            if proj_c and getattr(proj_c, "title", "") else ""
        )
        deliverables_tray_c = _render_review_deliverables_tray(sub_c) if sub_c else ""

        if sub_c:
            view_btn_html = f"""
            <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_reviewer_assessment_page', '{escape(sub_c.id)}')" style="font-size:11.5px; font-weight:800; padding:7px 14px;">
                📊 Inspect Deliverables &amp; Marksheet &rarr;
            </button>
            """
        else:
            view_btn_html = """
            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_assessments')" style="font-size:11.5px; font-weight:700;">
                View Assessment Record &rarr;
            </button>
            """

        completed_cards_html.append(f"""
        <div class="liquid-glass-card" style="padding:18px 22px; border:1.5px solid rgba(16,185,129,0.45); background:rgba(255,255,255,0.94); margin-bottom:12px; border-radius:12px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; margin-bottom:10px;">
                <div>
                    <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:6px;">
                        {f'<span style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:800; background:#0F172A; color:#FFFFFF; padding:2px 7px; border-radius:3px;">{escape(b_code)}</span>' if b_code else ''}
                        <span style="font-family:var(--font-family-mono); font-size:10px; font-weight:800; background:rgba(23,52,92,0.08); color:var(--deep-frozen-midnight); padding:2px 6px; border-radius:3px;">BAND {escape(b_band)}</span>
                        {f'<span style="font-size:11.5px; font-weight:600; color:#64748B;">{escape(b_cat)}</span>' if b_cat else ''}
                        <span class="status-pill status-approved" style="font-size:11px; font-weight:700;">✓ Completed &amp; Certified</span>
                    </div>
                    <div style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">{escape(b_title)}</div>
                    <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; font-size:12px; color:var(--frost-navy-75);">
                        <span style="width:22px; height:22px; border-radius:50%; background:#CBD5E1; color:#1E293B; display:inline-flex; align-items:center; justify-content:center; font-size:10px; font-weight:800;">{escape(c_avatar)}</span>
                        <span>Cadet: <strong>{escape(c_name)}</strong> (Band {escape(c_band)} &bull; {escape(c_track)}{f' &bull; {escape(c_email)}' if c_email else ''})</span>
                        <span style="color:#94A3B8;">&bull;</span>
                        <span>📅 Window: <strong>{escape(r_win_c)}</strong></span>
                        <span style="color:#94A3B8;">&bull;</span>
                        <span>🏆 Awarded: <strong style="color:#047857;">{escape(award_date)}</strong></span>
                    </div>
                </div>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('open_reviewer_badge_timeline_modal', '{escape(b_id_c)}')" style="font-size:11.5px; font-weight:700;">
                        📅 Timeline
                    </button>
                    {view_btn_html}
                </div>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:10px;">
                {"".join(score_pills)}
            </div>
            {proj_line_c}
            {deliverables_tray_c}
            {feedback_preview}
        </div>
        """)

    return f"""
    <div>
        <!-- Top Heading -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
            <div>
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 8px; border-radius:var(--radius-xs);">BAND {escape(user_band)}</span>
                    <span style="font-size:11px; font-weight:700; color:var(--frost-navy-50);">Project Reviewer</span>
                </div>
                <h1 style="font-size:1.85rem; font-weight:800; color:var(--frost-navy); letter-spacing:-0.5px; margin:0 0 4px 0;">Badge Review Schedule</h1>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_dashboard')" style="font-weight:700;">
                    &larr; Dashboard
                </button>
                <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_assessments')" style="font-weight:700;">
                    Assessment Queue &rarr;
                </button>
            </div>
        </div>

        <!-- Upcoming Badge Reviews Section -->
        <div class="liquid-glass-card" style="padding:22px; margin-bottom:28px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid var(--icy-steel-30); flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0;">
                        Upcoming Reviews ({len(upcoming_cards_html)})
                    </h3>
                </div>
            </div>
            <div>
                {"".join(upcoming_cards_html) if upcoming_cards_html else "<div style='text-align:center; padding:36px 20px; color:var(--frost-navy-50); font-size:13px; background:rgba(255,255,255,0.6); border:1px dashed var(--icy-steel-50); border-radius:var(--radius-sm);'>No upcoming badge reviews scheduled. When a Guardian allocates badges to cadets and designates you as reviewer, they will appear here.</div>"}
            </div>
        </div>

        <!-- Completed Reviews Section -->
        <div class="liquid-glass-card" style="padding:22px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid var(--icy-steel-30); flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0;">
                        Completed Reviews ({len(completed_cards_html)})
                    </h3>
                </div>
            </div>
            <div>
                {"".join(completed_cards_html) if completed_cards_html else "<div style='text-align:center; padding:30px 20px; color:var(--frost-navy-50); font-size:13px; background:rgba(255,255,255,0.6); border:1px dashed var(--icy-steel-50); border-radius:var(--radius-sm);'>No completed badge evaluations on record yet.</div>"}
            </div>
        </div>
    </div>
    """


# ==============================================================================
# 6.13 REVIEWER ASSESSMENT OF CADET DELIVERABLES WORKSPACE
# ==============================================================================

def render_reviewer_assessment_queue(
    submissions: List[ProjectSubmission],
    assessments_by_sub: Dict[str, AssessmentMarksheet],
    badges_map: Dict[str, Badge],
    cosmonauts_map: Dict[str, User],
    current_user: User,
    status_filter: str = "all"
) -> str:
    """
    Renders the Cadet Project Assessments queue for eligible higher-band reviewers.
    Allows reviewers to view mapped cadets, submitted deliverables, and submit their 50-mark review assessment.
    """
    from starapp.storage import store

    # Deduplicate submissions so only ONE submission per cadet per badge is shown
    deduped_subs = {}
    for s in submissions:
        key = (s.cosmonaut_id, s.badge_id)
        if key not in deduped_subs:
            deduped_subs[key] = s
        else:
            if getattr(s, "attempt_number", 1) >= getattr(deduped_subs[key], "attempt_number", 1):
                deduped_subs[key] = s

    unique_submissions = list(deduped_subs.values())

    # Find submissions of cadets assigned strictly to this reviewer
    assigned_subs = []
    is_guardian = (getattr(current_user, "role", "") == "guardian" or "guardian" in getattr(current_user, "roles", []))
    _all_band_mappings = store.get_band_mappings() if store else []
    _mappings_by_badge: Dict[str, List[Dict[str, Any]]] = {}  # computed once per badge, not once per submission
    for s in unique_submissions:
        b_obj = badges_map.get(s.badge_id) or (store.get_badge(s.badge_id) if store else None)
        if s.badge_id not in _mappings_by_badge:
            _mappings_by_badge[s.badge_id] = [
                m for m in _all_band_mappings
                if (m.get("badge_id") == s.badge_id or (b_obj and m.get("badge") in (b_obj.title, b_obj.code, b_obj.id)))
            ]
        badge_mappings = _mappings_by_badge[s.badge_id] if store else []

        is_assigned = False
        if is_guardian:
            is_assigned = True
        elif badge_mappings:
            for m in badge_mappings:
                if current_user.id in m.get("reviewers", []) and s.cosmonaut_id in m.get("cosmonauts", []):
                    is_assigned = True
                    break
        else:
            tl = store.get_timeline(s.badge_id, s.cosmonaut_id) if store else None
            if tl and getattr(tl, "reviewer_id", "") == current_user.id:
                is_assigned = True
            elif b_obj and getattr(b_obj, "assigned_reviewer_id", "") == current_user.id and s.cosmonaut_id in getattr(b_obj, "assigned_cosmonaut_ids", []):
                is_assigned = True

        if is_assigned:
            assigned_subs.append(s)

    filtered = assigned_subs
    if status_filter != "all":
        if status_filter == "pending":
            filtered = [s for s in assigned_subs if s.status in ("pending", "submitted")]
        elif status_filter == "reviewed":
            filtered = [s for s in assigned_subs if s.status == "reviewer_assessed"]
        elif status_filter == "approved":
            filtered = [s for s in assigned_subs if s.status == "approved"]
        elif status_filter == "retake":
            filtered = [s for s in assigned_subs if s.status in ("retake_required", "resubmission_requested")]

    pending_cnt = len([s for s in assigned_subs if s.status in ("pending", "submitted")])
    reviewed_cnt = len([s for s in assigned_subs if s.status == "reviewer_assessed"])
    approved_cnt = len([s for s in assigned_subs if s.status == "approved"])
    retake_cnt = len([s for s in assigned_subs if s.status in ("retake_required", "resubmission_requested")])

    filter_tabs = [
        ("all", "All Assigned", len(assigned_subs)),
        ("pending", "Awaiting Your Review", pending_cnt),
        ("reviewed", "Assessed by You", reviewed_cnt),
        ("approved", "Awarded by Guardian", approved_cnt),
        ("retake", "Retake Required", retake_cnt)
    ]
    filter_buttons = []
    for f_id, f_label, f_count in filter_tabs:
        is_active = f_id == status_filter
        st = "background:var(--deep-frozen-midnight); color:var(--snow-white); font-weight:700;" if is_active else "background:rgba(255,255,255,0.7); color:var(--frost-navy); font-weight:600;"
        filter_buttons.append(
            f'<button type="button" class="btn-secondary btn-sm" style="{st}" onclick="window.StarAppBridge.dispatchAction(\'filter_reviewer_assessments\', \'{f_id}\')">{f_label} ({f_count})</button>'
        )

    cards = []
    for sub in filtered:
        cosmo = cosmonauts_map.get(sub.cosmonaut_id)
        badge = badges_map.get(sub.badge_id)
        cosmo_name = cosmo.name if cosmo else sub.cosmonaut_id
        cosmo_avatar = getattr(cosmo, "avatar", "AN") or "AN"
        cosmo_band = getattr(cosmo, "band", "B1")
        badge_code = badge.code if badge else sub.badge_id
        badge_title = badge.title if badge else "Milestone Deliverable"
        badge_category = getattr(badge, "category", "Core Engineering")

        tl = store.get_timeline(sub.badge_id, sub.cosmonaut_id)
        r_window = []
        if tl and getattr(tl, "review_window_json", None):
            try:
                r_window = json.loads(tl.review_window_json)
            except Exception:
                r_window = []
        window_str = " &rarr; ".join(r_window) if r_window else "3-Day Window"

        rev_asm = store.get_reviewer_assessment_for_submission(sub.id)

        # File names / payloads
        pdf_name = getattr(sub, "pdf_name", "") or (sub.file_name if sub.submission_type == "pdf" else "") or "Deliverable.pdf"
        code_name = getattr(sub, "code_name", "") or (sub.file_name if sub.submission_type == "code" else "") or "script.py"
        github_url = getattr(sub, "github_url", "") or (sub.payload if sub.submission_type == "github" else "") or ""

        pdf_ic = get_icon("file_text", 13, "margin-right:4px; color:#D32F2F;")
        code_ic = get_icon("code", 13, "margin-right:4px; color:var(--deep-frozen-midnight);")
        gh_ic = get_icon("github", 13, "margin-right:4px; color:var(--frost-navy);")
        clock_ic = get_icon("clock", 12, "margin-right:4px; opacity:0.7;")
        arrow_ic = get_icon("arrow_right", 12, "margin-left:5px;")

        card_border = "border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(234,244,255,0.88) 100%);"
        if sub.status in ("pending", "submitted"):
            card_border = "border:2px solid #06B6D4; box-shadow:0 6px 20px rgba(6,182,212,0.15); background:linear-gradient(135deg, rgba(234,244,255,0.98) 0%, rgba(255,255,255,0.95) 100%);"

        submitted_date_str = escape(sub.submitted_at[:16].replace("T", " ")) + " UTC"

        # Assessment status badges
        if rev_asm:
            rev_badge = f'<span style="font-size:11.5px; font-weight:800; color:#047857; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); padding:3px 10px; border-radius:var(--radius-xs);">Your Score: {rev_asm.total_marks:.1f}/50 ({rev_asm.percentage:.1f}%)</span>'
        else:
            rev_badge = '<span style="font-size:11.5px; font-weight:800; color:#B45309; background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); padding:3px 10px; border-radius:var(--radius-xs);">Awaiting Your Evaluation</span>'

        cards.append(f"""
        <div class="liquid-glass-card interactive" style="{card_border} border-radius:var(--radius-md); padding:20px 24px; margin-bottom:16px; cursor:pointer;" onclick="window.StarAppBridge.dispatchAction('open_reviewer_assessment_page', '{sub.id}')">
            <!-- Top Row: Cadet & Status -->
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:10px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <div style="width:34px; height:34px; border-radius:50%; background:var(--deep-frozen-midnight); color:var(--snow-white); display:flex; align-items:center; justify-content:center; font-weight:800; font-size:12px; box-shadow:0 2px 6px rgba(7,22,41,0.25);">
                        {escape(cosmo_avatar)}
                    </div>
                    <div>
                        <div style="font-size:14.5px; font-weight:800; color:var(--frost-navy); line-height:1.2;">{escape(cosmo_name)} <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:700; color:#0E7490;">(Band {escape(cosmo_band)})</span></div>
                        <div style="font-size:11px; color:var(--frost-navy-50);">Engineering Cadet &bull; Assigned to You as Peer Reviewer</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:700; background:rgba(23,52,92,0.06); color:var(--frost-navy); padding:3px 8px; border-radius:var(--radius-xs);">Attempt #{sub.attempt_number}</span>
                    {render_status_pill(sub.status)}
                </div>
            </div>

            <!-- Middle Row: Badge Milestone & Date -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
                <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <span style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 8px; border-radius:var(--radius-xs);">{escape(badge_code)}</span>
                        <span style="font-size:11px; font-weight:700; background:rgba(23,52,92,0.08); color:var(--frost-navy); padding:2px 7px; border-radius:var(--radius-xs);">{escape(badge_category)}</span>
                    </div>
                    <div style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); line-height:1.3;">{escape(badge_title)}</div>
                </div>
                <div style="font-size:11.5px; color:var(--frost-navy-50); font-family:var(--font-family-mono); display:flex; align-items:center;">
                    {clock_ic} Submitted: {submitted_date_str}
                </div>
            </div>

            <!-- Window & Score Row -->
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px; padding:8px 12px; background:rgba(234,244,255,0.6); border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30);">
                <div style="font-size:11px; color:var(--frost-navy-75);">
                    <strong>Assigned Review Window:</strong> <span style="font-family:var(--font-family-mono);">{escape(window_str)}</span>
                </div>
                <div>
                    {rev_badge}
                </div>
            </div>

            <!-- Deliverables Files Tray -->
            <div style="background:rgba(255,255,255,0.7); border:1px solid var(--icy-steel-40); border-radius:var(--radius-sm); padding:10px 14px; margin-bottom:14px;">
                <div style="font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--frost-navy-50); margin-bottom:6px;">Submitted Deliverables:</div>
                <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                    <span style="display:inline-flex; align-items:center; font-size:11.5px; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-50); padding:4px 10px; border-radius:var(--radius-xs);">
                        {pdf_ic} {escape(pdf_name)}
                    </span>
                    <span style="display:inline-flex; align-items:center; font-size:11.5px; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-50); padding:4px 10px; border-radius:var(--radius-xs);">
                        {code_ic} {escape(code_name)}
                    </span>
                    <span style="display:inline-flex; align-items:center; font-size:11.5px; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-50); padding:4px 10px; border-radius:var(--radius-xs);">
                        {gh_ic} {escape(github_url.split('/')[-1] if '/' in github_url else 'GitHub Repo')}
                    </span>
                </div>
            </div>

            <!-- Footer Action Row -->
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <span style="font-size:11px; font-weight:600; color:var(--frost-navy-50);">Click to inspect PDF, Code &amp; evaluate against 5-criterion 50-mark rubric</span>
                <button type="button" class="btn-metal btn-sm" style="font-weight:700; font-size:12px; padding:6px 16px;" onclick="event.stopPropagation(); window.StarAppBridge.dispatchAction('open_reviewer_assessment_page', '{sub.id}')">
                    Inspect Deliverables &amp; Evaluate (50 Marks) {arrow_ic}
                </button>
            </div>
        </div>
        """)

    filter_tray = "".join(filter_buttons)
    cards_html = "".join(cards) if cards else f"""
    <div class="liquid-glass-card" style="padding:48px 24px; text-align:center; border-radius:var(--radius-md); border:1.5px dashed var(--icy-steel-40);">
        <div style="width:48px; height:48px; margin:0 auto 12px; border-radius:50%; background:rgba(6,182,212,0.1); display:flex; align-items:center; justify-content:center; color:#0891B2;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
        </div>
        <h3 style="font-size:16px; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">No Cadet Deliverables in this Queue</h3>
        <p style="font-size:13px; color:var(--frost-navy-50); margin:0; max-width:440px; margin:0 auto;">
            When cadets mapped to you submit project deliverables, they will appear here for your formal technical inspection and 50-mark rubric scoring.
        </p>
    </div>
    """

    return f"""
    <div>
        <!-- Heading -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:16px;">
            <div>
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 8px; border-radius:var(--radius-xs);">BAND {getattr(current_user, 'band', 'B2')}</span>
                    <span style="font-size:11px; font-weight:700; color:var(--frost-navy-50);">Authorized Peer Reviewer Workspace</span>
                </div>
                <h1 style="font-size:1.85rem; font-weight:800; color:var(--frost-navy); letter-spacing:-0.5px; margin:0 0 4px 0;">Cadet Project Assessments</h1>
                <p style="font-size:13.5px; color:var(--frost-navy-75); margin:0;">
                    Review incoming project deliverables submitted by mapped cadets. Grade the 5-criterion 50-mark rubric and submit your assessment.
                </p>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
                {render_back_button()}
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_dashboard')" style="font-weight:700;">
                    &larr; Dashboard
                </button>
            </div>
        </div>

        <!-- Filter tabs -->
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; margin-bottom:16px;">
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
                {filter_tray}
            </div>
        </div>

        <!-- Cards List -->
        <div>
            {cards_html}
        </div>
    </div>
    """


def render_reviewer_assessment_detail(
    submission: ProjectSubmission,
    badge: Badge,
    cosmonaut: User,
    existing_reviewer_asm: Optional[AssessmentMarksheet] = None,
    previous_assessments: Optional[List[AssessmentMarksheet]] = None,
    selected_tab: str = "pdf"
) -> str:
    """
    Dedicated in-website technical inspection & assessment workspace for Reviewers.
    Reviewer can toggle between PDF and Code viewer directly, and submit 50-mark rubric.
    """
    cosmo_name = cosmonaut.name if cosmonaut else submission.cosmonaut_id
    badge_code = badge.code if badge else submission.badge_id
    badge_title = badge.title if badge else "Milestone Deliverable"

    pdf_name = getattr(submission, "pdf_name", "") or (submission.file_name if submission.submission_type == "pdf" else "") or "Deliverable.pdf"
    pdf_payload = getattr(submission, "pdf_payload", "") or (submission.payload if submission.submission_type == "pdf" else "") or ""
    code_name = getattr(submission, "code_name", "") or (submission.file_name if submission.submission_type == "code" else "") or "script.py"
    code_payload = getattr(submission, "code_payload", "") or (submission.payload if submission.submission_type == "code" else "") or "# Source script"
    github_url = getattr(submission, "github_url", "") or ""

    base_pdf_url = pdf_payload.split("#")[0]
    clean_pdf_url = f"{base_pdf_url}#toolbar=1&navpanes=0&pagemode=none&view=FitH"

    download_ic = get_icon("download", 13, "margin-right:5px;")
    copy_ic = get_icon("copy", 13, "margin-right:5px;")
    expand_ic = get_icon("external_link", 13, "margin-right:5px;")

    init_bu = existing_reviewer_asm.business_understanding if existing_reviewer_asm else 9.0
    init_ar = existing_reviewer_asm.architecture_report if existing_reviewer_asm else 9.0
    init_tk = existing_reviewer_asm.technical_knowledge if existing_reviewer_asm else 9.0
    init_pr = existing_reviewer_asm.presentation if existing_reviewer_asm else 9.0
    init_qa = existing_reviewer_asm.qa if existing_reviewer_asm else 9.0
    init_total = init_bu + init_ar + init_tk + init_pr + init_qa
    init_pct = (init_total / 50.0) * 100.0

    init_strengths = existing_reviewer_asm.strength_areas if existing_reviewer_asm else "Robust technical architecture patterns and clean modular code."
    init_improvements = existing_reviewer_asm.improvement_areas if existing_reviewer_asm else "Ensure comprehensive unit testing across edge cases."
    init_feedback = existing_reviewer_asm.overall_feedback if existing_reviewer_asm else "Deliverables satisfy all criteria. Recommended for Guardian approval."

    # Viewer body
    if selected_tab == "pdf":
        viewer_body = f"""
        <div style="flex:1; min-height:0; width:100%; height:100%; overflow:hidden; position:relative; background:#FFFFFF;">
            <iframe id="pdf-document-frame" src="{clean_pdf_url}" style="width:100%; height:100%; border:none; display:block; background:#FFFFFF;" title="PDF Preview"></iframe>
        </div>
        """
        toolbar_extra = f"""
        <div style="display:flex; align-items:center; gap:8px;">
            <a href="{escape(pdf_payload)}" download="{escape(pdf_name)}" class="btn-secondary btn-sm" style="display:inline-flex; align-items:center; font-size:11.5px; text-decoration:none; padding:5px 12px;">
                {download_ic} Download PDF
            </a>
        </div>
        """
    elif selected_tab == "code":
        lines = code_payload.strip().split("\n")
        code_lines_html = []
        for l_num, line in enumerate(lines, 1):
            code_lines_html.append(
                f'<tr><td style="user-select:none; text-align:right; padding-right:14px; color:#5c7694; font-family:var(--font-family-mono); font-size:12px; width:40px; border-right:1px solid #17345C;">{l_num}</td>'
                f'<td style="white-space:pre-wrap; word-break:break-all; font-family:var(--font-family-mono); font-size:12.5px; color:#EAF4FF; padding-left:14px;">{escape(line)}</td></tr>'
            )
        code_table = "".join(code_lines_html)
        viewer_body = f"""
        <div id="deliverable-viewport-container" style="flex:1; min-height:0; width:100%; height:100%; background:#071629; overflow:auto; padding:14px 16px;">
            <table style="width:100%; border-collapse:collapse;">
                <tbody>
                    {code_table}
                </tbody>
            </table>
        </div>
        <pre id="raw-code-store" style="display:none;">{escape(code_payload)}</pre>
        """
        toolbar_extra = f"""
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:11.5px; font-family:var(--font-family-mono); color:var(--frost-navy-50);">{escape(code_name)}</span>
            <button type="button" class="btn-secondary btn-sm" style="display:inline-flex; align-items:center; font-size:11.5px; padding:5px 12px;" onclick="window.StarAppBridge.copySourceCode();">
                {copy_ic} Copy Code
            </button>
        </div>
        """
    else:  # github
        viewer_body = f"""
        <div style="flex:1; min-height:0; width:100%; height:100%; overflow:auto; padding:24px; background:#FFFFFF;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                <div style="width:40px; height:40px; border-radius:50%; background:var(--deep-frozen-midnight); color:var(--snow-white); display:flex; align-items:center; justify-content:center;">
                    {get_icon("github", 20)}
                </div>
                <div>
                    <div style="font-size:15px; font-weight:800; color:var(--frost-navy);">{escape(github_url.split('/')[-1] if '/' in github_url else 'GitHub Project Repository')}</div>
                    <div style="font-size:12px; color:var(--frost-navy-50);">Version Controlled Delivery Artifact</div>
                </div>
            </div>
            <div style="margin-bottom:16px;">
                <label style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--frost-navy-50);">Repository URL:</label>
                <div style="margin-top:4px; font-family:var(--font-family-mono); font-size:12px; background:rgba(23,52,92,0.06); padding:8px 12px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-50); word-break:break-all;">
                    {escape(github_url)}
                </div>
            </div>
            <a href="{escape(github_url)}" target="_blank" class="btn-metal" style="display:inline-flex; align-items:center; gap:6px; font-weight:700; font-size:12.5px; text-decoration:none; padding:8px 18px;">
                {expand_ic} Open Repository in New Tab
            </a>
        </div>
        """
        toolbar_extra = f"""
        <div>
            <a href="{escape(github_url)}" target="_blank" class="btn-secondary btn-sm" style="display:inline-flex; align-items:center; gap:5px; font-size:11.5px; text-decoration:none; padding:5px 12px;">
                {expand_ic} Open Repo
            </a>
        </div>
        """

    active_tab_icon = (
        get_icon("file_text", 14)
        if selected_tab in ("pdf", "odf")
        else (get_icon("code", 14) if selected_tab == "code" else get_icon("github", 14))
    )

    return f"""
    <div class="review-detail-workspace">
        <div class="review-workspace-grid">
            <!-- Column 1: PDF and Code Viewer -->
            <div class="review-left-column" style="background:#FFFFFF; border:1.5px solid var(--icy-steel); border-radius:var(--radius-md); box-shadow:0 4px 18px rgba(7,22,41,0.06); display:flex; flex-direction:column; height:100%; min-height:0; overflow:hidden;">
                <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 12px; background:rgba(234,244,255,0.7); border-bottom:1px solid var(--icy-steel-50); flex-shrink:0; height:42px; box-sizing:border-box;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <button type="button" class="btn-secondary btn-sm" style="font-weight:700; font-size:11.5px; padding:4px 10px; display:inline-flex; align-items:center; gap:4px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_assessments')">
                            {get_icon("chevron_left", 14)} Back to Cadet Assessments
                        </button>
                        <div class="asm-deliverable-toolbar-group">
                            <span class="asm-deliverable-icon-badge">{active_tab_icon}</span>
                            <div class="liquid-select-wrapper asm-deliverable-select-wrap">
                                <select id="deliverable-type-select" class="liquid-glass-control liquid-glass-select" onchange="window.StarAppBridge.dispatchAction('change_viewer_tab', this.value)">
                                    <option value="pdf"{" selected" if selected_tab in ("pdf", "odf") else ""}>View PDF Document (.pdf / .odf)</option>
                                    <option value="code"{" selected" if selected_tab == "code" else ""}>View Source Code (.py)</option>
                                    <option value="github"{" selected" if selected_tab == "github" else ""}>View GitHub Repo (Link)</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    {toolbar_extra}
                </div>
                {viewer_body}
            </div>

            <!-- Column 2: 50-Mark Rubric for Reviewer (Exact 100vh Zero-Scroll Fit) -->
            <div class="review-right-column" style="background:#FFFFFF; border:1.5px solid var(--deep-frozen-midnight); border-radius:var(--radius-md); box-shadow:0 4px 20px rgba(23,52,92,0.1); display:flex; flex-direction:column; height:100%; min-height:0; overflow:hidden;">
                <div style="padding:8px 14px; border-bottom:1.5px solid var(--icy-steel-30); background:linear-gradient(135deg, rgba(234,244,255,0.9) 0%, #FFFFFF 100%); display:flex; justify-content:space-between; align-items:center; flex-shrink:0; height:42px; box-sizing:border-box;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="font-size:11px; font-weight:800; background:#06B6D4; color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">REVIEWER RUBRIC</div>
                        <h3 style="font-size:1.05rem; font-weight:800; color:var(--frost-navy); margin:0;">Technical Assessment</h3>
                    </div>
                    <span id="rubric-total-display" style="display:none;"></span>
                </div>

                <form id="reviewer-rubric-form" style="flex:1; min-height:0; display:flex; flex-direction:column; overflow:hidden; margin:0;" onsubmit="event.preventDefault(); window.StarAppBridge.submitReviewerAssessment('{submission.id}');">
                    <div class="review-rubric-body-fit">
                        <!-- Cadet Details Bar -->
                        <div class="lg-rubric-meta-bar">
                            <span>{escape(cosmo_name)} &bull; {escape(badge_code)}</span>
                            <span style="font-family:var(--font-family-mono); font-weight:800;">Attempt #{submission.attempt_number}</span>
                        </div>

                        <!-- Structured 5 Criteria Matrix (Max 10 each) -->
                        <div class="lg-rubric-table-box">
                            <div class="lg-rubric-table-head">
                                <span>Criterion</span>
                                <span>Marks (Max 10)</span>
                            </div>
                            <div class="lg-rubric-row">
                                <span class="lg-rubric-crit-title">1. Business Understanding</span>
                                <span class="lg-rubric-score-box">
                                    <input type="number" id="rubric-bu" step="0.5" min="0" max="10" value="{init_bu}" class="lg-rubric-num-input" oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                            <div class="lg-rubric-row">
                                <span class="lg-rubric-crit-title">2. Architecture Report</span>
                                <span class="lg-rubric-score-box">
                                    <input type="number" id="rubric-ar" step="0.5" min="0" max="10" value="{init_ar}" class="lg-rubric-num-input" oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                            <div class="lg-rubric-row">
                                <span class="lg-rubric-crit-title">3. Technical Knowledge</span>
                                <span class="lg-rubric-score-box">
                                    <input type="number" id="rubric-tk" step="0.5" min="0" max="10" value="{init_tk}" class="lg-rubric-num-input" oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                            <div class="lg-rubric-row">
                                <span class="lg-rubric-crit-title">4. Presentation</span>
                                <span class="lg-rubric-score-box">
                                    <input type="number" id="rubric-pr" step="0.5" min="0" max="10" value="{init_pr}" class="lg-rubric-num-input" oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                            <div class="lg-rubric-row">
                                <span class="lg-rubric-crit-title">5. Q&amp;A Technical Defense</span>
                                <span class="lg-rubric-score-box">
                                    <input type="number" id="rubric-qa" step="0.5" min="0" max="10" value="{init_qa}" class="lg-rubric-num-input" oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                        </div>

                        <!-- Real-time Sum -->
                        <div class="lg-rubric-total-bar">
                            <span style="font-size:12px; font-weight:800; color:var(--frost-navy);">Sum of Rubric Marks:</span>
                            <span id="rubric-sum-display" style="font-size:14px; font-weight:900; color:var(--deep-frozen-midnight); font-family:var(--font-family-mono);">{init_total:.1f} / 50.0 ({init_pct:.1f}%)</span>
                        </div>

                        <!-- Qualitative Feedback -->
                        <div class="lg-rubric-fields-pair">
                            <div>
                                <label class="lg-rubric-field-label" for="rubric-strengths">Technical Strengths</label>
                                <textarea id="rubric-strengths" rows="2" class="lg-rubric-textarea">{escape(init_strengths)}</textarea>
                            </div>
                            <div>
                                <label class="lg-rubric-field-label" for="rubric-improvements">Improvements</label>
                                <textarea id="rubric-improvements" rows="2" class="lg-rubric-textarea">{escape(init_improvements)}</textarea>
                            </div>
                        </div>

                        <div>
                            <label class="lg-rubric-field-label" for="rubric-feedback">Reviewer Remarks &amp; Recommendations</label>
                            <textarea id="rubric-feedback" rows="2" class="lg-rubric-textarea">{escape(init_feedback)}</textarea>
                        </div>
                    </div>

                    <div style="padding:8px 14px; background:rgba(234,244,255,0.9); border-top:1px solid var(--icy-steel-30); flex-shrink:0;">
                        <button type="submit" class="btn-metal" style="width:100%; height:38px; font-size:13px; font-weight:800; letter-spacing:0.2px;">
                            Submit Reviewer Assessment &rarr;
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    """


# ==============================================================================
# 6.13 REVIEWER MODALS: TIMELINE & GEMINI AI PROJECT CREATOR
# ==============================================================================

def render_reviewer_badge_timeline_modal(badge: Optional[Badge], current_user: User, store: Any = None) -> str:
    if not badge:
        return "<p style='padding:24px; text-align:center;'>Badge information not found.</p>"
    dt = badge.default_timeline or {}
    tl = store.get_timeline(badge.id, "m_b1_1") if store else None
    if tl:
        dt = {
            "assignment_date": getattr(tl, "assignment_date", "2026-11-10"),
            "publication_date": getattr(tl, "publication_date", "2026-11-10"),
            "learning_start_date": getattr(tl, "learning_start_date", "2026-11-11"),
            "learning_end_date": getattr(tl, "learning_end_date", "2026-11-20"),
            "project_start_date": getattr(tl, "project_start_date", "2026-11-21"),
            "project_end_date": getattr(tl, "project_end_date", "2026-12-01"),
            "submission_deadline": getattr(tl, "submission_deadline", "2026-12-03"),
            "review_date": getattr(tl, "review_date", "2026-12-06"),
            "expected_award_date": getattr(tl, "expected_award_date", "2026-12-08")
        }
    alloc_date = dt.get("assignment_date", "2026-11-10")
    learn_start = dt.get("learning_start_date", "2026-11-11")
    learn_end = dt.get("learning_end_date", "2026-11-20")
    proj_start = dt.get("project_start_date", "2026-11-21")
    proj_end = dt.get("project_end_date", "2026-12-01")
    sub_deadline = dt.get("submission_deadline", "2026-12-03")
    review_date = dt.get("review_date", "2026-12-06")
    award_date = dt.get("expected_award_date", "2026-12-08")

    return f"""
    <div style="padding:10px 6px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; border-bottom:1.5px solid var(--icy-steel-30); padding-bottom:12px; flex-wrap:wrap; gap:10px;">
            <div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-family:var(--font-family-mono); font-size:11.5px; font-weight:800; background:var(--deep-frozen-midnight); color:#fff; padding:2px 8px; border-radius:3px;">{escape(badge.code)}</span>
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:rgba(23,52,92,0.08); color:var(--deep-frozen-midnight); padding:2px 6px; border-radius:3px;">BAND {escape(badge.target_band)}</span>
                    <span class="status-pill status-approved" style="font-size:11px; font-weight:700;">Milestone Timeline</span>
                </div>
                <h3 style="font-size:1.3rem; font-weight:800; color:var(--frost-navy); margin:6px 0 0 0;">{escape(badge.title)}</h3>
            </div>
            <span style="font-size:12px; font-weight:700; color:#047857; background:rgba(5,150,105,0.08); border:1px solid rgba(5,150,105,0.25); padding:4px 10px; border-radius:var(--radius-xs);">
                Reviewer: {escape(current_user.name)}
            </span>
        </div>

        <!-- 3-Day Allocation Window Notice -->
        <div style="background:linear-gradient(135deg, rgba(2,132,199,0.08) 0%, rgba(234,244,255,0.7) 100%); border:1.5px solid #0284C7; border-radius:var(--radius-sm); padding:14px 16px; margin-bottom:20px;">
            <div style="font-size:13px; font-weight:800; color:#0369A1; margin-bottom:4px; display:flex; align-items:center; gap:6px;">
                <span>⏱️ 3-Day Milestone Preparation Window Active</span>
            </div>
            <div style="font-size:12.5px; color:var(--frost-navy-75); line-height:1.5;">
                Both Reviewer and Cadets have an allocated 3-day window:
                <br>&bull; <strong>Cadets:</strong> Dedicated time for foundational self-study and learning concepts.
                <br>&bull; <strong>Reviewer ({escape(current_user.name)}):</strong> Dedicated window to author and dispatch the milestone project prompt via Gemini AI.
            </div>
        </div>

        <!-- Milestone Steppers Deck -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-bottom:20px;">
            <div style="background:#fff; border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm); padding:12px;">
                <div style="font-size:10px; font-weight:800; color:var(--frost-navy-50); text-transform:uppercase;">1. Allocation &amp; Publish</div>
                <div style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:var(--frost-navy); margin-top:4px;">{escape(alloc_date)}</div>
                <div style="font-size:11px; color:#047857; margin-top:2px;">Guardian Approved</div>
            </div>
            <div style="background:#fff; border:1.5px solid #0284C7; border-radius:var(--radius-sm); padding:12px;">
                <div style="font-size:10px; font-weight:800; color:#0284C7; text-transform:uppercase;">2. 3-Day Prep &amp; Learning</div>
                <div style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:#0369A1; margin-top:4px;">{escape(learn_start)} &rarr; {escape(learn_end)}</div>
                <div style="font-size:11px; color:#0284C7; margin-top:2px;">Project Draft &amp; Study</div>
            </div>
            <div style="background:#fff; border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm); padding:12px;">
                <div style="font-size:10px; font-weight:800; color:var(--frost-navy-50); text-transform:uppercase;">3. Project Sprint</div>
                <div style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:var(--frost-navy); margin-top:4px;">{escape(proj_start)} &rarr; {escape(proj_end)}</div>
                <div style="font-size:11px; color:var(--frost-navy-50); margin-top:2px;">Code &amp; PDF Implementation</div>
            </div>
            <div style="background:rgba(239,68,68,0.05); border:1.5px solid rgba(239,68,68,0.3); border-radius:var(--radius-sm); padding:12px;">
                <div style="font-size:10px; font-weight:800; color:#DC2626; text-transform:uppercase;">4. Submission Cutoff</div>
                <div style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:#DC2626; margin-top:4px;">{escape(sub_deadline)}</div>
                <div style="font-size:11px; color:#DC2626; margin-top:2px;">Strict Deliverables Due</div>
            </div>
            <div style="background:rgba(5,150,105,0.05); border:1.5px solid rgba(5,150,105,0.3); border-radius:var(--radius-sm); padding:12px;">
                <div style="font-size:10px; font-weight:800; color:#047857; text-transform:uppercase;">5. 3-Day Review Window</div>
                <div style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:#047857; margin-top:4px;">{escape(review_date)}</div>
                <div style="font-size:11px; color:#047857; margin-top:2px;">50-Mark Rubric Assessment</div>
            </div>
            <div style="background:#fff; border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm); padding:12px;">
                <div style="font-size:10px; font-weight:800; color:var(--frost-navy-50); text-transform:uppercase;">6. Certification Award</div>
                <div style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:var(--frost-navy); margin-top:4px;">{escape(award_date)}</div>
                <div style="font-size:11px; color:var(--frost-navy-50); margin-top:2px;">Guardian Final Publication</div>
            </div>
        </div>

        <div style="display:flex; justify-content:flex-end; gap:8px; border-top:1px solid var(--icy-steel-30); padding-top:14px;">
            <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">
                Close
            </button>
            <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('open_create_reviewer_project_modal', '{escape(badge.id)}')">
                ✨ Author Project Specification &rarr;
            </button>
        </div>
    </div>
    """


def render_reviewer_project_creator_modal(badge: Optional[Badge], current_user: User, store: Any = None, project_draft: Optional[Dict[str, Any]] = None) -> str:
    if not badge:
        return "<p style='padding:24px; text-align:center;'>Badge information not found.</p>"

    # Look up mapped cadets for this reviewer and badge
    mapped_cadets = []
    if store:
        mappings = store.get_band_mappings()
        for m in mappings:
            if current_user.id in m.get("reviewers", []):
                m_b = m.get("badge_id") or m.get("badge")
                if m_b in (badge.id, badge.code, badge.title):
                    for cid in m.get("cosmonauts", []):
                        u = store.get_user_by_id(cid)
                        if u and u not in mapped_cadets:
                            mapped_cadets.append(u)
        # Also include directly assigned cadets from timelines within current cycle
        scoped_timelines = store.get_timelines_dict() if hasattr(store, "get_timelines_dict") else store.timelines
        if scoped_timelines:
            for tl in scoped_timelines.values():
                if getattr(tl, "reviewer_id", "") == current_user.id and getattr(tl, "badge_id", "") == badge.id:
                    u = store.get_user_by_id(getattr(tl, "cosmonaut_id", ""))
                    if u and u not in mapped_cadets:
                        mapped_cadets.append(u)
        # Fallback: include directly assigned cadets from badge itself ONLY if no mapped cadets found
        if not mapped_cadets and getattr(badge, "assigned_reviewer_id", "") == current_user.id:
            for cid in getattr(badge, "assigned_cosmonaut_ids", []):
                u = store.get_user_by_id(cid)
                if u and u not in mapped_cadets:
                    mapped_cadets.append(u)

    cadet_chips = []
    cadet_ids = []
    for c in mapped_cadets:
        cadet_ids.append(c.id)
        c_av = getattr(c, "avatar", c.name[:2].upper())
        cadet_chips.append(f"""
        <span style="display:inline-flex; align-items:center; gap:5px; padding:3px 8px; background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-40); border-radius:var(--radius-xs); font-size:11.5px; font-weight:700; color:var(--frost-navy);">
            <span style="width:16px; height:16px; border-radius:50%; background:var(--deep-frozen-midnight); color:#fff; display:inline-flex; align-items:center; justify-content:center; font-size:10px; font-weight:800;">{escape(c_av)}</span>
            {escape(c.name)}
        </span>
        """)
    cadet_chips_html = "".join(cadet_chips) if cadet_chips else '<span style="font-size:12px; color:var(--frost-navy-50);">All Assigned Cohort Cadets</span>'

    from starapp.badge_generator import generate_reviewer_project_spec
    existing_proj = None
    if not project_draft and store:
        prompts = store.get_reviewer_project_prompts(badge_id=badge.id, reviewer_id=current_user.id)
        if prompts:
            existing_proj = prompts[0]

    if existing_proj:
        proj_title = getattr(existing_proj, "title", f"{badge.title} Project")
        scenario = getattr(existing_proj, "description", "")
        reqs = getattr(existing_proj, "requirements", [])
        outcomes_list = getattr(existing_proj, "outcomes", []) or getattr(badge, "outcomes", [])
        deliv = getattr(existing_proj, "deliverables", {}) or {}
    else:
        from starapp.badge_generator import generate_reviewer_project_spec
        spec = project_draft or generate_reviewer_project_spec(
            band=getattr(badge, "target_band", "B1"),
            power=getattr(badge, "power", "Tech"),
            capability=getattr(badge, "capability", "Data & Machine"),
            skill=getattr(badge, "skill", "Signals"),
            badge_title=badge.title,
            reviewer_name=current_user.name
        )
        proj_title = spec.get("title", f"{badge.title} Project")
        scenario = spec.get("scenario", "")
        reqs = spec.get("requirements", [])
        outcomes_list = getattr(badge, "outcomes", []) or spec.get("outcomes", [])
        deliv = spec.get("deliverables", {})

    reqs_text = "\n".join(reqs) if isinstance(reqs, list) else str(reqs)
    outcomes_text = "\n".join(outcomes_list) if isinstance(outcomes_list, list) else str(outcomes_list)

    code_desc = deliv.get("code", {}).get("description", "Source code implementation") if isinstance(deliv.get("code"), dict) else "Source code implementation"
    pdf_desc = deliv.get("pdf", {}).get("description", "Architecture document") if isinstance(deliv.get("pdf"), dict) else "Architecture document"
    gh_desc = deliv.get("github", {}).get("description", "GitHub repository") if isinstance(deliv.get("github"), dict) else "GitHub repository"

    is_already_released = existing_proj and getattr(existing_proj, "status", "") in ("released", "sent")
    status_pill_text = "✓ Project Active & Assigned" if is_already_released else ("📝 Draft Project" if existing_proj else "✓ AI Generated Draft")

    return f"""
    <div style="padding:10px 6px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; border-bottom:1.5px solid var(--icy-steel-30); padding-bottom:12px; flex-wrap:wrap; gap:10px;">
            <div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:linear-gradient(135deg, #0284C7, #0369A1); color:#fff; padding:2px 8px; border-radius:3px;">REVIEWER PROJECT CREATOR</span>
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:rgba(23,52,92,0.08); color:var(--deep-frozen-midnight); padding:2px 6px; border-radius:3px;">BAND {escape(badge.target_band)}</span>
                </div>
                <h3 style="font-size:1.35rem; font-weight:800; color:var(--frost-navy); margin:4px 0 0 0;">Create Milestone Project for Mapped Cadets</h3>
                <div style="font-size:12px; color:var(--frost-navy-50); margin-top:2px;">Reviewer-guided project specification with details, outcomes &amp; deliverables tailored to '{escape(badge.title)}'.</div>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span class="status-pill status-approved" style="font-size:11px; font-weight:800;">
                    {status_pill_text}
                </span>
            </div>
        </div>

        <!-- Recipient Mapped Cadets Box -->
        <div style="background:rgba(234,244,255,0.7); border:1px solid var(--icy-steel-40); border-radius:var(--radius-sm); padding:12px 16px; margin-bottom:16px;">
            <div style="font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--deep-frozen-midnight); margin-bottom:6px;">
                👥 Target Recipient Cadets (Mapped to You as Reviewer):
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:6px;">
                {cadet_chips_html}
            </div>
            <div style="font-size:11px; color:var(--frost-navy-50); margin-top:6px;">
                When submitted, this exact project with outcomes and deliverable targets will be dispatched to each of these mapped cadets' submission portals.
            </div>
        </div>

        <!-- Project Form -->
        <form id="reviewer-project-spec-form" onsubmit="event.preventDefault();">
            <div style="margin-bottom:14px;">
                <label style="font-size:11.5px; font-weight:800; color:var(--frost-navy); display:block; margin-bottom:4px;">Project Title</label>
                <input type="text" id="rev_proj_title" class="form-input" value="{escape(proj_title)}" style="font-size:13px; font-weight:700; width:100%;">
            </div>

            <div style="margin-bottom:14px;">
                <label style="font-size:11.5px; font-weight:800; color:var(--frost-navy); display:block; margin-bottom:4px;">Project Details &amp; Problem Scenario</label>
                <textarea id="rev_proj_scenario" rows="3" class="form-input" style="font-size:12.5px; line-height:1.45; width:100%;">{escape(scenario)}</textarea>
            </div>

            <div style="margin-bottom:14px;">
                <label style="font-size:11.5px; font-weight:800; color:var(--frost-navy); display:block; margin-bottom:4px;">Expected Project Outcomes (1 per line)</label>
                <textarea id="rev_proj_outcomes" rows="3" class="form-input" style="font-size:12px; line-height:1.45; width:100%; font-family:var(--font-family-mono);">{escape(outcomes_text)}</textarea>
            </div>

            <div style="margin-bottom:14px;">
                <label style="font-size:11.5px; font-weight:800; color:var(--frost-navy); display:block; margin-bottom:4px;">Detailed Project Requirements (1 per line)</label>
                <textarea id="rev_proj_reqs" rows="3" class="form-input" style="font-size:12px; line-height:1.45; width:100%; font-family:var(--font-family-mono);">{escape(reqs_text)}</textarea>
            </div>

            <div style="margin-bottom:16px;">
                <label style="font-size:11.5px; font-weight:800; color:var(--frost-navy); display:block; margin-bottom:6px;">Mandatory Deliverables Checklist (Mapped to 50-Mark Rubric)</label>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(200px, 100%), 1fr)); gap:10px;">
                    <div style="background:#fff; border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:10px;">
                        <div style="font-size:11px; font-weight:800; color:#047857; display:flex; align-items:center; gap:5px;">💻 1. Source Code File (.py)</div>
                        <input type="text" id="rev_proj_code_desc" class="form-input" value="{escape(code_desc)}" style="font-size:11px; margin-top:4px; padding:4px 6px;">
                    </div>
                    <div style="background:#fff; border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:10px;">
                        <div style="font-size:11px; font-weight:800; color:#DC2626; display:flex; align-items:center; gap:5px;">📄 2. Architecture PDF Report</div>
                        <input type="text" id="rev_proj_pdf_desc" class="form-input" value="{escape(pdf_desc)}" style="font-size:11px; margin-top:4px; padding:4px 6px;">
                    </div>
                    <div style="background:#fff; border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:10px;">
                        <div style="font-size:11px; font-weight:800; color:var(--deep-frozen-midnight); display:flex; align-items:center; gap:5px;">🔗 3. GitHub Repository URL</div>
                        <input type="text" id="rev_proj_gh_desc" class="form-input" value="{escape(gh_desc)}" style="font-size:11px; margin-top:4px; padding:4px 6px;">
                    </div>
                </div>
                <input type="hidden" id="rev_proj_cadet_ids" value="{escape(json.dumps(cadet_ids))}">
                <input type="hidden" id="rev_proj_code_name" value="{escape(deliv.get('code', {}).get('name', 'script.py') if isinstance(deliv.get('code'), dict) else 'script.py')}">
                <input type="hidden" id="rev_proj_pdf_name" value="{escape(deliv.get('pdf', {}).get('name', 'report.pdf') if isinstance(deliv.get('pdf'), dict) else 'report.pdf')}">
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--icy-steel-30); padding-top:14px; flex-wrap:wrap; gap:10px;">
                <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">
                    Cancel
                </button>
                <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                    <button type="button" class="btn-secondary" style="padding:9px 18px; font-weight:700; font-size:12.5px;"
                        onclick="(function(s){{var g=function(i){{var e=document.getElementById(i);return e?e.value:'';}};var o=g('rev_proj_outcomes').split(/\\r?\\n/).map(function(x){{return x.trim();}}).filter(Boolean);var r=g('rev_proj_reqs').split(/\\r?\\n/).map(function(x){{return x.trim();}}).filter(Boolean);var c=[];try{{c=JSON.parse(g('rev_proj_cadet_ids')||'[]');}}catch(e){{}}var p={{badge_id:'{escape(badge.id)}',reviewer_id:'{escape(current_user.id)}',title:g('rev_proj_title').trim()||'Milestone Implementation Project',objective:g('rev_proj_scenario').trim(),description:g('rev_proj_scenario').trim(),outcomes:o,requirements:r,technical_requirements:r,deliverables:{{code:{{name:g('rev_proj_code_name')||'script.py',description:g('rev_proj_code_desc').trim()}},pdf:{{name:g('rev_proj_pdf_name')||'report.pdf',description:g('rev_proj_pdf_desc').trim()}},github:{{name:'GitHub Repository',description:g('rev_proj_gh_desc').trim()}}}},cosmonaut_ids:c,status:s}};if(window.StarAppBridge&&typeof window.StarAppBridge.dispatchAction==='function'){{window.StarAppBridge.dispatchAction('send_reviewer_project',JSON.stringify(p));}}else if(window.starAppController&&typeof window.starAppController.handle_event==='function'){{window.starAppController.handle_event('send_reviewer_project',JSON.stringify(p));}}else{{var sid=(window.StarAppBridge&&typeof window.StarAppBridge.getWindowSessionId==='function')?window.StarAppBridge.getWindowSessionId():(sessionStorage.getItem('starapp_window_session_id')||'default');fetch('/api/v1/dispatch',{{method:'POST',headers:{{'Content-Type':'application/json','X-Session-Id':sid}},body:JSON.stringify({{action:'send_reviewer_project',payload:JSON.stringify(p),session_id:sid}})}}).then(function(res){{return res.json();}}).then(function(data){{if(data&&data.regions&&window.StarAppBridge){{window.StarAppBridge.updateRegions(JSON.stringify(data.regions));}}else if(data&&data.full_html&&window.StarAppBridge){{window.StarAppBridge.updateAppRoot(data.full_html);}}else{{window.location.reload();}}}});}}}})('draft');">
                        💾 Save Draft
                    </button>
                    <button type="button" class="btn-metal" style="padding:9px 24px; font-weight:800; background:linear-gradient(135deg, #059669 0%, #047857 100%); color:#fff; border-color:#059669; font-size:13px;"
                        onclick="(function(s){{var g=function(i){{var e=document.getElementById(i);return e?e.value:'';}};var o=g('rev_proj_outcomes').split(/\\r?\\n/).map(function(x){{return x.trim();}}).filter(Boolean);var r=g('rev_proj_reqs').split(/\\r?\\n/).map(function(x){{return x.trim();}}).filter(Boolean);var c=[];try{{c=JSON.parse(g('rev_proj_cadet_ids')||'[]');}}catch(e){{}}var p={{badge_id:'{escape(badge.id)}',reviewer_id:'{escape(current_user.id)}',title:g('rev_proj_title').trim()||'Milestone Implementation Project',objective:g('rev_proj_scenario').trim(),description:g('rev_proj_scenario').trim(),outcomes:o,requirements:r,technical_requirements:r,deliverables:{{code:{{name:g('rev_proj_code_name')||'script.py',description:g('rev_proj_code_desc').trim()}},pdf:{{name:g('rev_proj_pdf_name')||'report.pdf',description:g('rev_proj_pdf_desc').trim()}},github:{{name:'GitHub Repository',description:g('rev_proj_gh_desc').trim()}}}},cosmonaut_ids:c,status:s}};if(window.StarAppBridge&&typeof window.StarAppBridge.dispatchAction==='function'){{window.StarAppBridge.dispatchAction('send_reviewer_project',JSON.stringify(p));}}else if(window.starAppController&&typeof window.starAppController.handle_event==='function'){{window.starAppController.handle_event('send_reviewer_project',JSON.stringify(p));}}else{{var sid=(window.StarAppBridge&&typeof window.StarAppBridge.getWindowSessionId==='function')?window.StarAppBridge.getWindowSessionId():(sessionStorage.getItem('starapp_window_session_id')||'default');fetch('/api/v1/dispatch',{{method:'POST',headers:{{'Content-Type':'application/json','X-Session-Id':sid}},body:JSON.stringify({{action:'send_reviewer_project',payload:JSON.stringify(p),session_id:sid}})}}).then(function(res){{return res.json();}}).then(function(data){{if(data&&data.regions&&window.StarAppBridge){{window.StarAppBridge.updateRegions(JSON.stringify(data.regions));}}else if(data&&data.full_html&&window.StarAppBridge){{window.StarAppBridge.updateAppRoot(data.full_html);}}else{{window.location.reload();}}}});}}}})('released');">
                        🚀 Submit & Send Project to Mapped Cadets &rarr;
                    </button>
                </div>
            </div>
        </form>
    </div>
    """


def render_cosmonaut_cycles_view(
    current_user: User,
    cycles: List[Any],
    selected_cycle: Any,
    user_perf_per_cycle: List[Dict[str, Any]]
) -> str:
    """Renders Cosmonaut & Reviewer Performance Cycles History & Appraisals view."""
    cards = []
    for entry in user_perf_per_cycle:
        cyc = entry["cycle"]
        row = entry["row"]
        is_sel = (selected_cycle and cyc.id == selected_cycle.id)
        border_style = "border:2px solid var(--deep-frozen-midnight);" if is_sel else "border:1px solid var(--icy-steel-50);"
        st_lbl = (cyc.status or "active").upper()
        st_pill = (
            '<span style="background:rgba(16,185,129,0.14); color:#047857; padding:3px 9px; border-radius:999px; font-size:10.5px; font-weight:800;">ACTIVE CYCLE</span>'
            if cyc.status == "active" else
            f'<span style="background:rgba(100,116,139,0.14); color:#334155; padding:3px 9px; border-radius:999px; font-size:10.5px; font-weight:800;">{escape(st_lbl)}</span>'
        )
        sal_html = ""
        if row.get("base_salary", 0) > 0:
            sal_html = f'<div style="font-size:12px; color:#047857; margin-top:4px;">Compensation Update: {row["base_salary"]:,.0f} &rarr; <strong>{row["new_salary"]:,.0f}</strong> (+{row["approved_hike_pct"]:.1f}%)</div>'
        elif row.get("approved_hike_pct", 0) > 0:
            sal_html = f'<div style="font-size:12px; color:#047857; margin-top:4px;">Recommended Hike: <strong>+{row["approved_hike_pct"]:.1f}%</strong></div>'

        promo_html = f'<span style="background:rgba(79,70,229,0.12); color:#4F46E5; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:800;">Promotion Rec: Band {escape(row["recommended_promotion_band"])}</span>' if row.get("recommended_promotion_band") else ""

        cards.append(f"""
        <div class="liquid-glass-card" style="padding:18px 22px; margin-bottom:16px; {border_style}">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding-bottom:12px; border-bottom:1px solid var(--icy-steel-30); margin-bottom:14px;">
                <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; background:var(--deep-frozen-midnight); color:#fff; padding:2px 8px; border-radius:var(--radius-xs);">{escape(cyc.code)}</span>
                        <span style="font-size:12px; color:var(--frost-navy-50); font-weight:700;">{escape(cyc.start_date)} &rarr; {escape(cyc.end_date)}</span>
                        {st_pill}
                    </div>
                    <h3 style="margin:0; font-size:1.2rem; font-weight:800; color:var(--frost-navy);">{escape(cyc.name)}</h3>
                </div>
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <div style="text-align:right;">
                        <div style="font-family:var(--font-family-mono); font-size:1.35rem; font-weight:900; color:var(--deep-frozen-midnight);">{row["composite_score"]:.1f} / 100</div>
                        <div style="font-size:11.5px; font-weight:800; color:var(--frost-navy-50);">{escape(row["performance_tier"])}</div>
                    </div>
                    <button type="button" class="btn-secondary btn-sm" style="font-weight:800; padding:7px 14px;"
                            onclick="window.StarAppBridge.dispatchAction('select_cycle', '{escape(cyc.id)}')">
                        {"Currently Viewing" if is_sel else "Inspect Cycle Workspace →"}
                    </button>
                </div>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(260px, 100%), 1fr)); gap:14px;">
                <div style="padding:12px 14px; border-radius:var(--radius-sm); background:rgba(234,244,255,0.6); border:1px solid var(--icy-steel-30);">
                    <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:6px;">🎓 My Cosmonaut Performance</div>
                    <div style="font-size:12.5px; color:var(--frost-navy); line-height:1.6;">
                        <div>Badges Earned: <strong>{row["badges_earned"]} / {row["badges_assigned"]}</strong> ({row["cosmo_completion_pct"]}%)</div>
                        <div>Average Score: <strong>{row["avg_marks"]} / 50</strong> ({row["avg_percentage"]}%)</div>
                        <div>First-Attempt Passes: <strong>{row["first_attempt_passes"]}</strong> &bull; Cosmonaut Index: <strong>{row["cosmo_score"]}%</strong></div>
                    </div>
                </div>
                <div style="padding:12px 14px; border-radius:var(--radius-sm); background:rgba(240,253,250,0.75); border:1px solid rgba(13,148,136,0.28);">
                    <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:#0F766E; margin-bottom:6px;">⚖️ My Reviewer Performance</div>
                    <div style="font-size:12.5px; color:var(--frost-navy); line-height:1.6;">
                        <div>Badge Proposals Reviewed: <strong>{row["badge_reviews_completed"]} / {row["badge_reviews_assigned"]}</strong></div>
                        <div>Projects Released: <strong>{row["projects_released"]}</strong> &bull; Cadet Grades Submitted: <strong>{row["submissions_graded"]} / {row["submissions_assigned_to_review"]}</strong></div>
                        <div>Reviewer Index: <strong>{row["reviewer_score"]}%</strong></div>
                    </div>
                </div>
            </div>

            <div style="margin-top:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    {promo_html}
                    {sal_html}
                    {f'<div style="font-size:12px; color:var(--frost-navy-75); margin-top:4px;"><strong>Guardian Remarks:</strong> {escape(row["guardian_remarks"])}</div>' if row.get("guardian_remarks") else ""}
                </div>
                <span style="font-size:11px; font-weight:800; color:var(--frost-navy-50); text-transform:uppercase;">Appraisal Status: {escape(row["status"])}</span>
            </div>
        </div>
        """)

    return f"""
    <div>
        <div class="liquid-glass-card" style="padding:18px 22px; margin-bottom:20px; border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(234,244,255,0.85) 100%);">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">My 6-Month Performance Cycles &amp; Appraisals</h2>
            <p style="font-size:12.5px; color:var(--frost-navy-50); margin:0;">
                Review your historical and active 6-month cycles, including your dual-role performance as both Cosmonaut and Reviewer, finalized rating tiers, and hike recommendations.
            </p>
        </div>
        {"".join(cards) if cards else '<div class="liquid-glass-card" style="padding:36px; text-align:center; color:var(--frost-navy-50);">No cycles recorded yet.</div>'}
    </div>
    """


def _fmt_cosmo_cycle_window(start_iso: str, end_iso: str) -> str:
    """Formats ISO start/end dates into compact readable date ranges."""
    import datetime as _dt
    try:
        s = _dt.date.fromisoformat((start_iso or "")[:10])
        e = _dt.date.fromisoformat((end_iso or "")[:10])
        if s.year == e.year:
            return f"{s.strftime('%b %d')} \u2013 {e.strftime('%b %d, %Y')}"
        return f"{s.strftime('%b %d, %Y')} \u2013 {e.strftime('%b %d, %Y')}"
    except Exception:
        return f"{start_iso} \u2013 {end_iso}" if (start_iso or end_iso) else "Unscheduled"


def render_cosmonaut_choose_cycle_view(
    current_user: User,
    cycles: List[Any],
    selected_cycle: Any,
    cycle_stats: Optional[Dict[str, Dict[str, Any]]] = None
) -> str:
    """Renders compact, responsive Performance Cycle selector for Cosmonauts and Reviewers."""
    sel_id = getattr(selected_cycle, "id", "cycle_1") if selected_cycle else "cycle_1"
    sel_name = getattr(selected_cycle, "name", "Cycle 1") if selected_cycle else "Cycle 1"
    sel_window = _fmt_cosmo_cycle_window(
        getattr(selected_cycle, "start_date", "") if selected_cycle else "",
        getattr(selected_cycle, "end_date", "") if selected_cycle else "",
    )

    u_band = getattr(current_user, "band", "")
    is_reviewer = (u_band in ("B2", "B3", "B4", "B5", "B6")) or current_user.has_role("badge_reviewer")
    cal_svg = get_icon("calendar", 14)
    stats_map = cycle_stats or {}

    cycle_cards = []
    for cyc in cycles:
        is_sel = (cyc.id == sel_id)
        st_raw = (getattr(cyc, "status", "active") or "active").lower()
        st_label = "Active" if st_raw == "active" else ("Evaluating" if st_raw == "evaluating" else "Closed")
        st_pill_cls = "status-active" if st_raw == "active" else ("status-pending" if st_raw == "evaluating" else "status-locked")
        cyc_window = _fmt_cosmo_cycle_window(getattr(cyc, "start_date", ""), getattr(cyc, "end_date", ""))
        row = stats_map.get(cyc.id) or {}

        earned = int(row.get("badges_earned", 0) or 0)
        assigned = int(row.get("badges_assigned", 0) or 0)
        avg_marks = float(row.get("avg_marks", 0) or 0)
        comp_pct = max(0.0, min(100.0, float(row.get("cosmo_completion_pct", 0) or 0)))
        marks_str = f"{avg_marks:.1f} / 50" if avg_marks > 0 else "No scores"

        sub_graded = int(row.get("submissions_graded", 0) or 0)
        sub_assigned = int(row.get("submissions_assigned_to_review", 0) or 0)
        prop_done = int(row.get("badge_reviews_completed", 0) or 0)
        prop_assigned = int(row.get("badge_reviews_assigned", 0) or 0)
        comp_score = float(row.get("composite_score", 0) or 0)
        perf_tier = row.get("performance_tier") or ("In Progress" if st_raw == "active" else "Closed")

        rev_metric_box = ""
        if is_reviewer or (sub_assigned + prop_assigned) > 0:
            rev_metric_box = f"""
            <div class="cosmo-cycle-metric-box">
                <span class="cosmo-cycle-metric-k">Reviews</span>
                <span class="cosmo-cycle-metric-v">{sub_graded}/{sub_assigned} Graded</span>
                <span class="cosmo-cycle-metric-sub">{prop_done}/{prop_assigned} Proposals</span>
            </div>
            """

        card_cls = "liquid-glass-card interactive cosmo-cycle-card is-selected" if is_sel else "liquid-glass-card interactive cosmo-cycle-card"
        action_chip = (
            '<span class="cosmo-cycle-selected-pill">Selected</span>'
            if is_sel else
            '<span class="cosmo-cycle-switch-pill">Select Cycle &rarr;</span>'
        )

        cycle_cards.append(f"""
        <div class="{card_cls}" onclick="window.StarAppBridge.dispatchAction('select_cycle', '{escape(cyc.id)}')">
            <div class="cosmo-cycle-card-head">
                <div style="min-width:0;">
                    <div style="display:flex; align-items:center; gap:7px; flex-wrap:wrap; margin-bottom:5px;">
                        <span class="cosmo-cycle-code">{escape(cyc.code)}</span>
                        <span class="cosmo-cycle-date-chip">{cal_svg}<span>{escape(cyc_window)}</span></span>
                    </div>
                    <h3 class="cosmo-cycle-card-title">{escape(cyc.name)}</h3>
                </div>
                <span class="status-pill {st_pill_cls}" style="font-size:11px; flex-shrink:0;">{st_label}</span>
            </div>

            <div class="cosmo-cycle-metrics">
                <div class="cosmo-cycle-metric-box">
                    <span class="cosmo-cycle-metric-k">Badges</span>
                    <span class="cosmo-cycle-metric-v">{earned} / {assigned}</span>
                    <div class="cycle-meter-track" style="margin-top:4px;">
                        <div class="cycle-meter-fill emerald" style="width:{comp_pct:.0f}%;"></div>
                    </div>
                    <span class="cosmo-cycle-metric-sub">{marks_str}</span>
                </div>
                {rev_metric_box}
                <div class="cosmo-cycle-metric-box">
                    <span class="cosmo-cycle-metric-k">Standing</span>
                    <span class="cosmo-cycle-metric-v">{comp_score:.1f} / 100</span>
                    <span class="cosmo-cycle-metric-sub">{escape(perf_tier)}</span>
                </div>
            </div>

            <div class="cosmo-cycle-foot">
                <span style="font-size:11.5px; font-weight:700; color:var(--frost-navy-50);">{escape(st_label)} Cycle</span>
                {action_chip}
            </div>
        </div>
        """)

    rev_quick_btn = (
        """
        <button type="button" class="btn-secondary btn-sm" style="font-weight:700; padding:0 12px;"
                onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_badge_reviews')">
            Badge Reviews &rarr;
        </button>
        <button type="button" class="btn-secondary btn-sm" style="font-weight:700; padding:0 12px;"
                onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_requests')">
            Review Requests &rarr;
        </button>
        """
        if is_reviewer else ""
    )

    return f"""
    <div class="cosmo-cycle-container">
        <div class="liquid-glass-card cosmo-cycle-hero">
            <div class="cosmo-cycle-hero-left">
                <h2 class="cosmo-cycle-hero-title">Performance Cycles</h2>
                <span class="cycle-window-chip">{cal_svg}<span>{escape(sel_name)} &middot; {escape(sel_window)}</span></span>
            </div>
            <div class="cosmo-cycle-hero-actions">
                {rev_quick_btn}
                <button type="button" class="btn-secondary btn-sm" style="font-weight:700; padding:0 12px;"
                        onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_cycles')">
                    Past Performance &rarr;
                </button>
                <button type="button" class="btn-metal btn-sm" style="font-weight:800; padding:0 14px;"
                        onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">
                    Open Badges &rarr;
                </button>
            </div>
        </div>

        <div class="cosmo-cycle-grid">
            {"".join(cycle_cards) if cycle_cards else '<div class="liquid-glass-card" style="padding:28px; text-align:center;">No performance cycles available yet.</div>'}
        </div>
    </div>
    """



