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
    humanize_internal_ids, is_reviewer_band, render_sidebar_actions_footer,
    get_icon,
    escape, render_liquid_card, render_metal_button, render_liquid_button,
    render_status_pill, render_standard_marksheet, render_9point_timeline,
    render_learning_materials_view, render_back_button, render_taxonomy_hierarchy_tree,
    render_request_timer, render_badge_review_timer, render_project_window_timer, format_utc_stamp, format_short_date, format_ist, ist_plain,
    REVIEWER_RECOMMENDATIONS, reviewer_recommendation_key, render_recommendation_chip
)
from starapp.roadmap import generate_roadmap_graph
from starapp.views_badge_document import (
    render_badge_document, render_badge_edit_controls, render_badge_edit_footer_bar, split_badge_document
)
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

    # Order: Badges (home) -> Assessment Marksheet -> Deadline Extension -> reviewer tools (Band 2+) -> Profile.
    # Cycle switching is done from the cycle pill at the top of the sidebar (opens the Choose Cycle page).
    nav_items = []

    # Eligible reviewers (bands B2 through B6 or badge_reviewer role) receive Badge Reviews, Review Requests & Cadet Assessments
    # Reviewers must sit in a HIGHER band than the badges they review, so only Band 2 and above can ever review.
    is_eligible = is_reviewer_band(getattr(current_user, "band", ""))
    if is_eligible:
        try:
            pending_project_requests = len(store.get_pending_project_requests(current_user.id))
        except Exception:
            pending_project_requests = 0
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
                "badge": pending_project_requests + pending_asms_count      # projects to send + deliverables waiting for marks
            },
            {
                "id": "c_requests",
                "label": "Review Requests",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>',
                "badge": pending_requests_count
            }
        ])

    # Exact requested Cosmonaut sidebar items (Learning Roadmap & Study Materials omitted from sidebar; views/routes kept in code)
    nav_items.extend([
        {"id": "c_submission", "label": "Badges", "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>', "badge": 0},
        {"id": "c_results", "label": "Assessment Marksheet", "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>', "badge": 0},
        {"id": "c_extensions", "label": "Deadline Extension", "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', "badge": 0},
    ])

    _by_id = {i["id"]: i for i in nav_items}
    _order = ["c_submission", "c_results", "c_extensions"]
    if is_eligible:
        _order += ["c_badge_reviews", "c_requests"]
    # Profile is compulsory for everyone: it is the "View Profile" link pinned to the bottom of the sidebar.
    nav_items = [_by_id[i] for i in _order if i in _by_id]

    links_html = []
    for item in nav_items:
        is_active = (
            (item["id"] == active_view)
            or (item["id"] == "c_badge_reviews" and active_view == "c_assessment_detail")
            or (item["id"] == "c_requests" and active_view == "c_badge_review")
            or (item["id"] == "c_submission" and active_view in ("c_badge_detail", "c_project"))
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

    _track = getattr(current_user, "learning_track", "") or ""
    footer_html = render_sidebar_actions_footer(
        current_user, "nav_cosmonaut", "c_profile", active_view,
        f"Band {getattr(current_user, 'band', 'B1')}" + (f" • {_track}" if _track else "")
    )
    band_lbl = escape(getattr(current_user, "band", "") or "")
    cyc_name = escape(getattr(selected_cycle, "name", "") or "")
    # Header: just the band number (same chip as the Guardian sidebar). It also opens the cycle picker, which replaces the
    # old "C1 / C1-2026 ACTIVE" pill, so switching cycle is still possible.
    header_html = (
        '<div class="sidebar-header">'
        f'<a class="sidebar-band-chip is-link" role="button" title="Band {band_lbl}{(" · " + cyc_name) if cyc_name else ""} — click to choose a cycle" '
        "onclick=\"window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_choose_cycle')\">" + band_lbl + "</a>"
        '<button type="button" class="sidebar-collapse-btn" style="display:none;" onclick="window.StarAppBridge.toggleSidebar()" aria-hidden="true"></button>'
        "</div>"
    ) if band_lbl else '<div class="sidebar-header is-empty"></div>'

    return f"""
    <aside id="starapp-shell-sidebar" class="app-sidebar" data-portal-role="cosmonaut" data-user-id="{escape(current_user.id)}">
        {header_html}

        <ul class="sidebar-nav">
            {"".join(links_html)}
        </ul>

        {footer_html}
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
        rank_medal = '<span style="background:#FEF3C7; color:#B45309; border:1px solid #FCD34D; font-weight:800; padding:4px 10px; border-radius:999px; font-size:0.71875rem; display:inline-flex; align-items:center; gap:4px;">&#129351; Rank #1 &bull; Batch Top Standing</span>'
    elif rank == 2:
        rank_medal = '<span style="background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; font-weight:800; padding:4px 10px; border-radius:999px; font-size:0.71875rem; display:inline-flex; align-items:center; gap:4px;">&#129352; Rank #2 &bull; High Honors</span>'
    elif rank == 3:
        rank_medal = '<span style="background:#FFEDD5; color:#C2410C; border:1px solid #FDBA74; font-weight:800; padding:4px 10px; border-radius:999px; font-size:0.71875rem; display:inline-flex; align-items:center; gap:4px;">&#129353; Rank #3 &bull; Honors</span>'
    else:
        rank_medal = f'<span style="background:rgba(23,52,92,0.08); color:var(--deep-frozen-midnight); border:1px solid var(--icy-steel); font-weight:800; padding:4px 10px; border-radius:999px; font-size:0.71875rem; display:inline-flex; align-items:center; gap:4px;">Rank #{rank} of {total_cohort}</span>'

    # Risk Status Pill
    if r_status == "On Track":
        r_pill = '<span style="font-size:0.71875rem; font-weight:800; color:#047857; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); padding:4px 12px; border-radius:999px; display:inline-flex; align-items:center; gap:5px;">&#10003; On Track</span>'
    elif r_status == "Monitor":
        r_pill = '<span style="font-size:0.71875rem; font-weight:800; color:#1D4ED8; background:rgba(59,130,246,0.12); border:1px solid rgba(59,130,246,0.3); padding:4px 12px; border-radius:999px; display:inline-flex; align-items:center; gap:5px;">&#9203; Monitor</span>'
    elif r_status == "Needs Attention":
        r_pill = '<span style="font-size:0.71875rem; font-weight:800; color:#B45309; background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); padding:4px 12px; border-radius:999px; display:inline-flex; align-items:center; gap:5px;">&#9888; Needs Attention</span>'
    else:
        r_pill = '<span style="font-size:0.71875rem; font-weight:800; color:#B91C1C; background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.3); padding:4px 12px; border-radius:999px; display:inline-flex; align-items:center; gap:5px;">&#10005; At Risk</span>'

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
        next_action_pill = '<span class="status-pill status-pending" style="font-size:0.6875rem; font-weight:800; padding:4px 10px;">&#9203; Under Guardian Review</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:0.75rem; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Track Submission Status &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:0.75rem; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_materials')">Browse Study Materials &rarr;</button>"""
    elif latest_sub and latest_sub.status == "resubmission_requested":
        next_action_title = f"Resubmission Required: {active_b.code if active_b else 'Milestone'}"
        next_action_desc = f"Evaluator requested a revised Attempt #{latest_sub.attempt_number + 1} deliverable. Address the architectural feedback and resubmit your implementation package."
        next_action_pill = '<span class="status-pill status-rejected" style="font-size:0.6875rem; font-weight:800; padding:4px 10px;">&#9888; Resubmission Requested</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:0.75rem; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Submit Revised Deliverable &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:0.75rem; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')">View Evaluator Feedback &rarr;</button>"""
    elif active_b:
        next_action_title = f"Active Sprint: Complete {active_b.code} Deliverables"
        next_action_desc = f"You are currently fulfilling <strong>{escape(active_b.title)}</strong>. Prepare your PDF system architecture charter and executable code package for upload."
        next_action_pill = '<span class="status-pill status-active" style="font-size:0.6875rem; font-weight:800; padding:4px 10px;">&#9654; Sprint In Progress</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:0.75rem; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Submit Project Deliverable &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:0.75rem; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_materials')">Review Study Materials &rarr;</button>"""
    else:
        next_action_title = "Curriculum Roadmap Completed"
        next_action_desc = "All assigned enterprise milestones have been certified. Review your official marksheet transcript."
        next_action_pill = '<span class="status-pill status-approved" style="font-size:0.6875rem; font-weight:800; padding:4px 10px;">&#10003; Certified</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:0.75rem; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')">View Marksheets &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:0.75rem; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_roadmap')">Explore Career Pathways &rarr;</button>"""

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
            r_badge = '<span style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:#FEF3C7; color:#B45309; font-weight:800; font-size:0.75rem; border:1px solid #FCD34D;">1</span>'
        elif idx == 2:
            r_badge = '<span style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:#F1F5F9; color:#475569; font-weight:800; font-size:0.75rem; border:1px solid #CBD5E1;">2</span>'
        elif idx == 3:
            r_badge = '<span style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:#FFEDD5; color:#C2410C; font-weight:800; font-size:0.75rem; border:1px solid #FDBA74;">3</span>'
        else:
            r_badge = f'<span style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:rgba(23,52,92,0.06); color:var(--frost-navy); font-weight:700; font-size:0.71875rem;">{idx}</span>'

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
            you_tag = '<span style="font-size:0.625rem; font-weight:800; background:#047857; color:#FFFFFF; padding:2px 7px; border-radius:999px; margin-left:6px; letter-spacing:0.5px;">YOU</span>'
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
                    <div class="user-avatar" style="width:32px; height:32px; font-size:0.6875rem; font-weight:800; border:1px solid var(--icy-steel);">{escape(c.get("avatar", "CO"))}</div>
                    <div>
                        <div style="display:flex; align-items:center;">
                            <strong style="font-size:0.8125rem; color:var(--frost-navy);">{escape(c.get("name", "Cadet"))}</strong>
                            {you_tag}
                        </div>
                        <div style="font-size:0.6875rem; color:var(--frost-navy-50);">{escape(c.get("band", "") or "")}{" &bull; " if c.get("band") else ""}{escape(c.get("track", "") or c.get("role", "") or "Cadet")}</div>
                    </div>
                </div>
            </td>
            <td style="padding:10px 14px; text-align:center; vertical-align:middle;">
                <span style="font-weight:800; color:var(--deep-frozen-midnight);">{c_comp}</span> <span style="font-size:0.6875rem; opacity:0.6;">/ {c.get("total_assigned", 0)} Badge{'s' if c.get('total_assigned', 0) != 1 else ''}</span>
                <div style="width:50px; height:4px; border-radius:2px; background:rgba(157,183,213,0.3); margin:3px auto 0 auto; overflow:hidden;">
                    <div style="width:{c_prog_pct}%; height:100%; background:#10B981;"></div>
                </div>
            </td>
            <td style="padding:10px 14px; vertical-align:middle;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                    <span style="font-size:0.78125rem; font-weight:800; color:var(--deep-frozen-midnight);">{c_marks:.1f} <span style="font-size:0.65625rem; opacity:0.6;">/ 50</span></span>
                    <span style="font-size:0.6875rem; font-weight:700; color:{tier_color};">{c_pct:.1f}%</span>
                </div>
                <div style="height:5px; border-radius:3px; background:rgba(157,183,213,0.25); overflow:hidden;">
                    <div style="height:100%; width:{c_pct}%; background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
                </div>
            </td>
            <td style="padding:10px 14px; text-align:center; vertical-align:middle;">
                <span style="font-size:0.6875rem; font-weight:700; color:{tier_color}; background:rgba(23,52,92,0.06); padding:3px 9px; border-radius:999px;">
                    {tier_label}
                </span>
            </td>
            <td style="padding:10px 14px; text-align:right; vertical-align:middle; white-space:nowrap;">
                <span style="font-size:0.6875rem; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.05); padding:3px 8px; border-radius:4px;">
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
                <div style="font-size:0.75rem; color:var(--frost-navy-50);">Ranked by average assessment score and certified milestones.</div>
            </div>
            <span style="font-size:0.6875rem; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
                {total_cohort} Enrolled Cadets &bull; Your Rank: #{rank}
            </span>
        </div>

        <div style="overflow-x:auto;">
            <table style="width:100%; border-collapse:collapse; text-align:left;">
                <thead>
                    <tr style="border-bottom:1.5px solid var(--icy-steel); background:rgba(234,244,255,0.45); font-size:0.65625rem; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">
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
            status_pill = '<span style="font-size:0.65625rem; font-weight:800; color:#047857; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); padding:2px 8px; border-radius:999px;">&#10003; Certified</span>'
        else:
            score = 0.0
            pct = 0.0
            att = 0
            rev_dt = "Pending"
            status_pill = '<span style="font-size:0.65625rem; font-weight:800; color:var(--frost-navy-50); background:rgba(23,52,92,0.06); padding:2px 8px; border-radius:999px;">In Progress</span>'

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
        <div style="font-weight:800; font-size:0.75rem; color:#FFFFFF; margin-bottom:4px;">{escape(bcode)}: {escape(b["title"])}</div>
        <div style="font-size:0.6875rem; color:var(--pure-ice); margin-bottom:6px;">{escape(b["pillar"])}</div>
        <div style="padding-top:5px; border-top:1px solid rgba(157,183,213,0.25); font-size:0.71875rem; color:#FFFFFF;">
            Rubric Score: <strong style="color:#047857;">{score:.1f} / 50.0</strong> ({pct:.1f}%)
        </div>
        <div style="font-size:0.6875rem; color:var(--pure-ice); margin-top:2px;">Attempt #{att if att > 0 else '—'} &bull; {"Certified Assessment" if att > 0 else "Pending Deliverable"}</div>
        <div style="font-size:0.65625rem; color:var(--pure-ice); margin-top:3px; font-style:italic;">Evaluated: {escape(rev_dt)}</div>
        """

        bargraph_cols.append(f"""
        <div class="has-glass-tooltip velocity-bar-col {pop_align}" style="display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; position:relative; cursor:pointer;">
            <!-- Top Score Label -->
            <div style="font-size:0.75rem; font-weight:800; color:{label_color}; margin-bottom:6px; font-family:var(--font-family-mono);">{score_label}</div>

            <!-- Vertical Bar Fill -->
            <div style="width:100%; max-width:68px; height:{height_pct}%; {bar_style} border-radius:6px 6px 0 0; transition:height 0.2s ease, opacity 0.2s ease;"></div>

            <!-- Popover Tooltip -->
            <div class="glass-tooltip-popover {pop_align}" style="min-width:215px;">
                {popover_body}
            </div>

            <!-- Column Legend / Subtext -->
            <div style="margin-top:10px; text-align:center; width:100%;">
                <div style="font-family:var(--font-family-mono); font-size:0.75rem; font-weight:800; color:var(--deep-frozen-midnight);">{escape(bcode)}</div>
                <div style="font-size:0.6875rem; color:var(--frost-navy-75); margin:2px 0 6px 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{escape(b['title'])}">{escape(b['title'])}</div>
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
                <div style="font-size:0.78125rem; color:var(--frost-navy-50);">Your verified 50-mark standard assessment rubric scores across curriculum roadmap badges.</div>
            </div>
            <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap; font-size:0.71875rem;">
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
                <span style="position:absolute; right:0; top:-20px; font-size:0.65625rem; font-weight:800; color:#047857; background:rgba(255,255,255,0.95); padding:2px 8px; border-radius:4px; border:1px solid rgba(16,185,129,0.3); box-shadow:0 1px 3px rgba(0,0,0,0.05);">
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
                    <span style="font-family:var(--font-family-mono); font-size:0.6875rem; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">{escape(b_code)}</span>
                    <strong style="font-size:0.84375rem; color:var(--frost-navy);">{escape(b_title)}</strong>
                    <span style="font-size:0.71875rem; color:var(--frost-navy-50);">(Attempt #{att})</span>
                </div>
                <div style="font-size:0.75rem; color:var(--frost-navy-75);">
                    Score: <strong style="color:var(--deep-frozen-midnight);">{tot:.1f} / 50.0</strong> ({pct:.1f}%) &bull; Certified on {escape(dt)}
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
                <span class="status-pill status-approved" style="font-size:0.65625rem;">&#10003; Certified</span>
                <button type="button" class="btn-metal btn-sm" style="font-size:0.71875rem; font-weight:700; padding:6px 14px; display:inline-flex; align-items:center; gap:5px;" onclick="window.StarAppBridge.dispatchAction('view_marksheet', '{escape(asm_id)}')">
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
                    <div style="font-size:0.65625rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px;">{escape(sk_cat)}</div>
                    <strong style="font-size:0.84375rem; color:var(--frost-navy); display:block; margin-top:2px;">{escape(sk_name)}</strong>
                </div>
                <span style="font-family:var(--font-family-mono); font-size:0.65625rem; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">{escape(sk_badge)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; font-size:0.71875rem; gap:8px; flex-wrap:wrap;">
                <span style="font-weight:800; color:{sk_col}; background:rgba(37,99,235,0.08); padding:2px 8px; border-radius:4px;">{escape(sk_prof)}</span>
                <span style="font-weight:800; font-size:0.71875rem; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.07); padding:2px 8px; border-radius:4px; border:1px solid var(--icy-steel);">
                    &#9733; Rating: <strong style="color:#047857; font-size:0.75rem;">{sk_rating:.1f}</strong> / 10.0
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
                <span style="font-family:var(--font-family-mono); font-size:0.6875rem; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.07); padding:3px 8px; border-radius:4px;">{escape(cred_id)}</span>
                <span style="font-size:0.65625rem; font-weight:800; color:#047857; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); padding:3px 8px; border-radius:999px;">&#10003; {escape(honors)}</span>
            </div>
            <div style="font-size:0.875rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">
                <span style="font-family:var(--font-family-mono); color:var(--deep-frozen-midnight); font-weight:800;">{escape(c_code)}:</span> {escape(c_title)}
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; padding-top:8px; border-top:1px solid var(--icy-steel-30); font-size:0.71875rem; color:var(--frost-navy-75);">
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
    <li style="margin-bottom:10px; display:flex; align-items:flex-start; gap:8px; font-size:0.78125rem; color:var(--frost-navy); line-height:1.5;">
        <span style="color:#047857; font-weight:800; font-size:0.8125rem; line-height:1.4;">&#10003;</span>
        <span>{escape(s)}</span>
    </li>
    """ for s in strengths_data])

    imp_items = "".join([f"""
    <li style="margin-bottom:10px; display:flex; align-items:flex-start; gap:8px; font-size:0.78125rem; color:var(--frost-navy); line-height:1.5;">
        <span style="color:#B45309; font-weight:800; font-size:0.8125rem; line-height:1.4;">&#9678;</span>
        <span>{escape(im)}</span>
    </li>
    """ for im in improvements_data])

    diagnostics_html = f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(320px, 100%), 1fr)); gap:18px; margin-bottom:18px;">
        <!-- Column 1: Strengths -->
        <div style="background:rgba(16,185,129,0.03); border:1px solid rgba(16,185,129,0.22); border-left:4px solid #10B981; border-radius:var(--radius-sm); padding:16px 18px;">
            <div style="font-size:0.8125rem; font-weight:800; color:#065F46; margin-bottom:12px; display:flex; align-items:center; gap:8px;">
                <span style="background:#047857; color:#fff; width:22px; height:22px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:0.75rem;">&#10003;</span>
                Demonstrated Engineering Strengths
            </div>
            <ul style="list-style:none; padding:0; margin:0;">
                {str_items}
            </ul>
        </div>

        <!-- Column 2: Improvement Areas -->
        <div style="background:rgba(245,158,11,0.03); border:1px solid rgba(245,158,11,0.22); border-left:4px solid #F59E0B; border-radius:var(--radius-sm); padding:16px 18px;">
            <div style="font-size:0.8125rem; font-weight:800; color:#92400E; margin-bottom:12px; display:flex; align-items:center; gap:8px;">
                <span style="background:#F59E0B; color:#451A03; width:22px; height:22px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:0.75rem;">&#9678;</span>
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
            <div style="width:26px; height:26px; border-radius:50%; background:var(--deep-frozen-midnight); color:#fff; display:flex; align-items:center; justify-content:center; font-size:0.6875rem; font-weight:800;">GM</div>
            <div style="font-size:0.78125rem; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px;">
                Faculty Mentoring Guidance &bull; Mentorship Committee
            </div>
        </div>
        <div style="font-size:0.8125rem; color:var(--frost-navy); line-height:1.55; margin-left:36px;">
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
                    <div style="font-size:0.71875rem; font-weight:800; color:#B45309; text-transform:uppercase; letter-spacing:0.5px;">Institutional Peer Review Assignment</div>
                    <div style="font-size:0.84375rem; color:var(--frost-navy); font-weight:700; margin-top:2px;">
                        You have <strong>{pending_review_cnt} badge review request(s)</strong> awaiting your inspection and authorization.
                    </div>
                </div>
                <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_requests')" style="font-weight:700; font-size:0.75rem; padding:6px 16px;">
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
        <div class="liquid-glass-card" style="padding:22px 28px; margin-bottom:24px; border-radius:var(--radius-lg); border:1.5px solid var(--icy-steel); background:rgba(244, 250, 255, 0.91); box-shadow:0 6px 20px rgba(7,22,41,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div class="user-avatar" style="width:52px; height:52px; font-size:1.125rem; font-weight:800; border:2px solid var(--icy-steel);">{escape(current_user.avatar)}</div>
                    <div>
                        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                            <h2 style="font-size:1.45rem; font-weight:800; color:var(--frost-navy); margin:0;">Welcome back, {escape(current_user.name)}</h2>
                            <span style="font-size:0.6875rem; font-weight:800; background:#047857; color:#FFFFFF; padding:3px 9px; border-radius:var(--radius-xs);">FLIGHT OFFICER</span>
                        </div>
                        <div style="font-size:0.78125rem; color:var(--frost-navy-75); margin-top:3px;">
                            Band <strong>{escape(getattr(current_user, "band", "") or "B1")}</strong> &bull; <strong>{escape(getattr(current_user, "learning_track", "") or "Cosmonaut")}</strong>{(" &bull; Batch: <strong>" + escape(profile.batch_name) + "</strong>") if getattr(profile, "batch_name", "") else ""}{(" &bull; Mentor: <strong>" + escape(_mentor_name) + "</strong>") if _mentor_name else ""}
                        </div>
                    </div>
                </div>

                <div style="display:flex; flex-direction:column; align-items:flex-end; gap:8px;">
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                        {rank_medal}
                        <span style="font-size:0.75rem; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:5px 12px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel);">
                            Standing: <strong>{escape(tier)}</strong>
                        </span>
                        {r_pill}
                    </div>
                    <div style="font-size:0.6875rem; color:var(--frost-navy-50);">
                        Last Active: <strong style="color:var(--frost-navy);">{escape(last_act)}</strong> &bull; {escape(last_act_desc)}
                    </div>
                </div>
            </div>
        </div>

        <!-- SECTION B: Executive Performance KPIs Grid -->
        <div class="kpi-grid guardian-kpi-row" style="margin-bottom:24px;">
            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        Certified Milestones
                    </span>
                    {render_cosmo_metric_info_popover('individual_badges', astraea_rec, 'individual')}
                </div>
                <div class="kpi-value" style="font-size:1.75rem; font-weight:800; line-height:1.1; margin:2px 0 6px 0; color:var(--frost-navy);">{comp_count} / {total_assigned}</div>
                <div style="height:5px; border-radius:3px; background:rgba(157,183,213,0.3); overflow:hidden; margin:4px 0;">
                    <div style="height:100%; width:{progress_pct}%; background:#10B981;"></div>
                </div>
                <div class="kpi-subtext" style="color:#047857; font-weight:700; font-size:0.6875rem;">▲ {progress_pct}% Roadmap Certified</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        Average Score
                    </span>
                    {render_cosmo_metric_info_popover('individual_score', astraea_rec, 'individual')}
                </div>
                <div class="kpi-value" style="font-size:1.75rem; font-weight:800; line-height:1.1; margin:2px 0 6px 0; color:var(--frost-navy);">{avg_marks:.1f} <span style="font-size:0.78125rem; opacity:0.65; font-weight:600;">/ 50.0</span></div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700; font-size:0.6875rem;">{avg_pct:.1f}% Average Across Milestones</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        Leaderboard Rank
                    </span>
                    <div class="kpi-icon-bubble" style="width:24px; height:24px; display:flex; align-items:center; justify-content:center; border-radius:var(--radius-xs);">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    </div>
                </div>
                <div class="kpi-value" style="font-size:1.75rem; font-weight:800; line-height:1.1; margin:2px 0 6px 0; color:#047857;">#{rank} <span style="font-size:0.78125rem; opacity:0.65; color:var(--frost-navy);">/ {total_cohort}</span></div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700; font-size:0.6875rem;">Top {round((rank/max(1, total_cohort))*100)}% of Cohort</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        First-Attempt Pass Rate
                    </span>
                    {render_cosmo_metric_info_popover('individual_first_attempt', astraea_rec, 'individual', 'right')}
                </div>
                <div class="kpi-value" style="font-size:1.75rem; font-weight:800; line-height:1.1; margin:2px 0 6px 0; color:var(--frost-navy);">{first_pass_rate}%</div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700; font-size:0.6875rem;">{astraea_rec.get("first_attempt_passes", 0)} Cleared on Attempt #1</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:16px 18px; border-radius:var(--radius-md); display:flex; flex-direction:column; justify-content:space-between; min-width:0;">
                <div class="kpi-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.4px;">
                        Active Milestone
                    </span>
                    {render_cosmo_metric_info_popover('individual_active_milestone', astraea_rec, 'individual', 'right')}
                </div>
                <div class="kpi-value" style="font-size:1.35rem; font-weight:800; color:var(--deep-frozen-midnight); line-height:1.2; margin:2px 0 6px 0;">{escape(active_b.code if active_b else "Completed")}</div>
                <div class="kpi-subtext" style="color:var(--frost-navy-50); font-size:0.6875rem; font-weight:600;">{escape(astraea_rec.get("deadline_status", "On Schedule"))}</div>
            </div>
        </div>

        <!-- SECTION C: Personalized Next Action Card -->
        <div class="liquid-glass-card" style="padding:22px 28px; margin-bottom:24px; border-radius:var(--radius-lg); border:1.5px solid var(--icy-steel); background:rgba(244, 250, 255, 0.94); box-shadow:0 6px 20px rgba(7,22,41,0.06);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 9px; border-radius:var(--radius-xs);">YOUR NEXT ACTION</span>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0;">{next_action_title}</h3>
                </div>
                {next_action_pill}
            </div>

            <p style="font-size:0.84375rem; color:var(--frost-navy); line-height:1.55; margin:0 0 16px 0;">
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
                    <div style="font-size:0.78125rem; color:var(--frost-navy-50);">Audited submission evaluations across the 5 rubric criteria. Click 'View Review Marksheet' to inspect your full evaluation rubric.</div>
                </div>
                <span style="font-size:0.75rem; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
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
                    <div style="font-size:0.78125rem; color:var(--frost-navy-50);">Evaluated engineering capabilities demonstrated through accredited milestone submissions, with ratings scored out of 10.0.</div>
                </div>
                <span style="font-size:0.75rem; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
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
                    <div style="font-size:0.78125rem; color:var(--frost-navy-50);">Standard-issue micro-credentials awarded upon successful 50-mark rubric evaluation.</div>
                </div>
                <span style="font-size:0.75rem; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
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
                    <div style="font-size:0.78125rem; color:var(--frost-navy-50);">Guardian observational analysis, demonstrated competencies, and targeted improvement roadmaps.</div>
                </div>
                <span style="font-size:0.75rem; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
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

def _cosmonaut_profile_facts(current_user: User, profile: CosmonautProfile, summary, leaderboard, cycle_row) -> Dict[str, Any]:
    """Real, per-user facts for the profile page (nothing here is hard-coded demo text)."""
    from starapp.mapping_data import BANDS
    from starapp.storage import store
    role_labels = {"guardian": "Guardian", "badge_reviewer": "Badge Reviewer",
                   "project_reviewer": "Project Reviewer", "cosmonaut": "Cosmonaut"}
    roles = [r for r in (getattr(current_user, "roles", None) or [current_user.role]) if r]
    band = getattr(current_user, "band", "") or ""
    band_title = next((b["title"] for b in BANDS if b["code"] == band), "")
    summary = summary or {}
    rank, total = None, len(leaderboard or [])
    for i, entry in enumerate(leaderboard or [], start=1):
        if entry.get("cosmonaut_id") == current_user.id:
            rank = i
            break
    guardian = store.get_user_by_id(profile.assigned_guardian_id) if getattr(profile, "assigned_guardian_id", "") else None
    batch = getattr(profile, "batch_name", "") or ""
    if not batch or batch == "Orion-24":  # "Orion-24" is only the store's placeholder for profiles without a stored cohort
        batch = f"Band {band} Cohort" if band else "Cohort"
    current_badge = None
    try:
        for tl in store.get_timelines_for_cosmonaut(current_user.id):
            if getattr(tl, "status", "") in ("active", "reviewer_assessed", "retake_required"):
                current_badge = store.get_badge(tl.badge_id)
                if current_badge:
                    break
    except Exception:
        current_badge = None
    return {
        "band": band, "band_title": band_title, "track": getattr(current_user, "learning_track", "") or "",
        "roles_text": ", ".join(role_labels.get(r, r.replace("_", " ").title()) for r in roles),
        "status": (getattr(current_user, "status", "") or "active").title(),
        "manager_name": getattr(current_user, "reporting_manager_name", "") or "",
        "manager_band": getattr(current_user, "reporting_manager_band", "") or "",
        "guardian_name": guardian.name if guardian else "",
        "batch": batch,
        "earned": int(summary.get("approved_count", 0) or 0),
        "avg_pct": float(summary.get("average_percentage", 0.0) or 0.0),
        "avg_marks": float(summary.get("average_marks", 0.0) or 0.0),
        "rank": rank, "total": total,
        "tier": (cycle_row or {}).get("performance_tier") or "",
        "composite": float((cycle_row or {}).get("composite_score", 0.0) or 0.0),
        "current_badge": current_badge,
    }


def render_cosmonaut_profile(
    current_user: User,
    profile: CosmonautProfile,
    assigned_badges: Optional[List[Badge]] = None,
    summary: Optional[Dict[str, Any]] = None,
    leaderboard: Optional[List[Dict[str, Any]]] = None,
    cycle_row: Optional[Dict[str, Any]] = None,
    cycle_name: str = ""
) -> str:
    f = _cosmonaut_profile_facts(current_user, profile, summary, leaderboard, cycle_row)
    assigned_count = len(assigned_badges or [])

    def _tile(label: str, value: str, sub: str = "") -> str:
        sub_html = f'<div style="font-size:0.6875rem; color:var(--frost-navy-50); margin-top:1px;">{escape(sub)}</div>' if sub else ""
        return (
            '<div style="background:rgba(255,255,255,0.9); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">'
            f'<div style="font-size:0.6875rem; text-transform:uppercase; color:var(--frost-navy-50); font-weight:700; letter-spacing:0.5px;">{escape(label)}</div>'
            f'<div style="font-size:0.84375rem; font-weight:800; color:var(--deep-frozen-midnight); margin-top:2px;">{escape(value)}</div>'
            f'{sub_html}</div>'
        )

    mgr_value = f.get("manager_name") or "Not assigned"
    mgr_sub = f"Band {f['manager_band']}" if f.get("manager_band") else ""
    cb = f.get("current_badge")
    standing_value = f["tier"] or "Not assessed yet"
    standing_sub = (f"{f['composite']:.1f} / 100" + (f" • {cycle_name}" if cycle_name else "")) if f["tier"] else (cycle_name or "")
    rank_value = f"#{f['rank']} of {f['total']}" if f["rank"] else "Not ranked yet"
    tiles = "".join([
        _tile("Band", f"{f['band']} • {f['band_title']}" if f["band_title"] else (f["band"] or "-"), f["track"]),
        _tile("Roles", f["roles_text"] or "Cosmonaut"),
        _tile("Reporting Manager", mgr_value, mgr_sub),
        _tile("Guardian / Mentor", f["guardian_name"] or "Not assigned", "Academy Guardian" if f["guardian_name"] else ""),
        _tile("Training Cohort", f["batch"], f["track"]),
        _tile("Current Cycle Standing", standing_value, standing_sub),
        _tile("Badges Earned", f"{f['earned']} / {assigned_count}", "Allotted badges completed"),
        _tile("Average Score", f"{f['avg_marks']:.1f} / 50 ({f['avg_pct']:.1f}%)" if f["earned"] else "No scores yet", rank_value),
        _tile("Current Milestone", cb.code if cb else "None active", cb.title if cb else ""),
    ])

    # Skills Pill Badges
    skills_tags = []
    for s in profile.skills:
        skills_tags.append(f"""
        <div style="display:inline-flex; align-items:center; gap:8px; padding:6px 14px; background:linear-gradient(135deg, rgba(23, 52, 92, 0.92) 0%, rgba(7, 22, 41, 0.96) 100%); border:1px solid var(--icy-steel); border-radius:var(--radius-full); font-size:0.78125rem; font-weight:700; color:var(--snow-white); box-shadow:0 2px 6px rgba(7,22,41,0.12); transition:transform 150ms ease;">
            <span style="font-family:var(--font-family-mono);">{escape(s)}</span>
            <span style="cursor:pointer; font-weight:900; font-size:0.875rem; color:var(--icy-steel); line-height:1; padding-left:2px;" title="Remove skill" onclick="window.StarAppBridge.dispatchAction('remove_skill', '{escape(s)}')">&times;</span>
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
                <div style="width:40px; height:40px; border-radius:var(--radius-sm); background:rgba(23,52,92,0.08); display:flex; align-items:center; justify-content:center; color:var(--deep-frozen-midnight); font-size:1.25rem;">
                    {get_icon("file_text", 20)}
                </div>
                <div>
                    <div style="font-weight:800; color:var(--frost-navy); font-size:0.875rem;">{escape(c_name)}</div>
                    <div style="font-size:0.75rem; color:var(--frost-navy-50); margin-top:2px;">
                        Issuing Authority: <strong style="color:var(--deep-frozen-midnight);">{escape(c_issuer)}</strong> &bull; Year: <strong style="color:var(--deep-frozen-midnight);">{escape(c_year)}</strong>
                    </div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
                <span class="status-pill status-approved" style="font-size:0.6875rem; padding:3px 10px;">Verified</span>
                <button type="button" class="btn-secondary btn-sm" style="color:var(--frost-navy-50); padding:4px 10px;" onclick="window.StarAppBridge.dispatchAction('remove_certification', '{idx}')">Remove</button>
            </div>
        </div>
        """)

    return f"""
    <div style="max-width:1100px; margin:0 auto;">
        <!-- 1. Identity & Credentials Header Banner -->
        <div class="liquid-glass-card" style="padding:28px 32px; margin-bottom:24px; border:1.5px solid var(--icy-steel); background:rgba(244, 250, 255, 0.79);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:18px; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:20px;">
                    <div class="user-avatar" style="display:flex; align-items:center; justify-content:center; border-radius:50%; width:72px; height:72px; font-size:1.625rem; font-weight:800; background:linear-gradient(135deg, var(--deep-frozen-midnight) 0%, var(--frost-navy) 100%); color:var(--snow-white); border:2.5px solid var(--icy-steel); box-shadow:0 4px 16px rgba(7,22,41,0.18);">
                        {escape(current_user.avatar)}
                    </div>
                    <div>
                        <div style="display:flex; align-items:center; gap:10px;">
                            <h2 style="font-size:1.75rem; font-weight:800; color:var(--frost-navy); margin:0; letter-spacing:-0.4px;">{escape(current_user.name)}</h2>
                            <span class="status-pill status-approved" style="font-size:0.6875rem; padding:3px 10px;">{escape(f["status"])}</span>
                        </div>
                        <div style="font-size:0.8125rem; color:var(--deep-frozen-midnight); font-weight:700; margin-top:3px;">
                            {escape("Band " + f["band"] if f["band"] else "Cosmonaut")} &bull; ID: <span style="font-family:var(--font-family-mono);">{escape(current_user.id)}</span>
                        </div>
                        <div style="font-size:0.78125rem; color:var(--frost-navy-50); margin-top:2px;">
                            Email: <strong style="color:var(--frost-navy);">{escape(current_user.email)}</strong>
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

            <!-- Core profile facts -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(220px, 100%), 1fr)); gap:14px;">
                {tiles}
            </div>
        </div>

        <!-- 2. Technical Competencies & Skills Section -->
        <div class="liquid-glass-card" style="padding:26px 30px; margin-bottom:24px; border:1.5px solid var(--icy-steel); background:rgba(244, 250, 255, 0.73);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px;">
                <div>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0 0 3px 0;">Technical Competencies & Skills</h3>
                    <div style="font-size:0.78125rem; color:var(--frost-navy-50);">Validated domain proficiencies and framework competencies.</div>
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
                {"".join(skills_tags) if skills_tags else "<span style='font-size:0.8125rem; color:var(--frost-navy-50); font-style:italic;'>No skills registered yet. Click '+ Add Skill' to add your technical proficiencies.</span>"}
            </div>
        </div>

        <!-- 3. Industry Certifications Section -->
        <div class="liquid-glass-card" style="padding:26px 30px; margin-bottom:24px; border:1.5px solid var(--icy-steel); background:rgba(244, 250, 255, 0.73);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px;">
                <div>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0 0 3px 0;">Verified Industry Certifications</h3>
                    <div style="font-size:0.78125rem; color:var(--frost-navy-50);">Recognized accreditations and professional engineering credentials.</div>
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
            code_style = "color: #92400E; font-weight: 800; font-family: var(--font-family-mono); font-size: 0.71875rem;"
            title_style = "color: #78350F; font-weight: 800; font-size: 0.875rem; margin: 3px 0 2px;"
            desc_style = "color: #92400E; font-size: 0.6875rem; font-weight: 600;"
            status_html = '<span class="status-pill status-approved" style="font-size:0.65625rem; padding:2px 8px; border-radius:12px; font-weight:800; background:#F59E0B; color:#451A03; border:1px solid #D97706; box-shadow:0 2px 6px rgba(245,158,11,0.4); display:inline-flex; align-items:center; gap:3px;">★ Completed</span>'
        elif state == "active":
            card_style = (
                "background: linear-gradient(135deg, rgba(234, 244, 255, 0.96) 0%, rgba(255, 255, 255, 0.98) 100%); "
                "border: 2px solid var(--deep-frozen-midnight); "
                "box-shadow: 0 0 0 4px rgba(23, 52, 92, 0.18), 0 10px 24px rgba(7, 22, 41, 0.12); "
                "color: var(--frost-navy);"
            )
            code_style = "color: var(--deep-frozen-midnight); font-weight: 800; font-family: var(--font-family-mono); font-size: 0.71875rem;"
            title_style = "color: var(--frost-navy); font-weight: 700; font-size: 0.875rem; margin: 3px 0 2px;"
            desc_style = "color: var(--frost-navy-50); font-size: 0.6875rem;"
            if node.get("is_current_active"):
                status_html = '<span class="status-pill status-active" style="font-size:0.65625rem; padding:2px 8px;">Active • Current</span>'
            else:
                status_html = '<span class="status-pill status-active" style="font-size:0.65625rem; padding:2px 8px;">Available</span>'
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
            code_style = "color: var(--frost-navy-50); font-weight: 700; font-family: var(--font-family-mono); font-size: 0.71875rem;"
            title_style = "color: var(--frost-navy); font-weight: 700; font-size: 0.875rem; margin: 3px 0 2px; opacity: 0.85;"
            desc_style = "color: var(--frost-navy-50); font-size: 0.6875rem;"
            status_html = '<span class="status-pill status-locked" style="font-size:0.65625rem; padding:2px 8px;">Locked</span>'
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
            <p style="font-size:0.84375rem;color:var(--frost-navy-50);margin-bottom:14px;">{heading_desc}</p>
            <div class="liquid-glass-card" style="display:inline-flex;flex-direction:column;gap:8px;padding:12px 20px;border-radius:var(--radius-md);min-width:300px;max-width:560px;width:100%;">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:0.75rem;font-weight:700;color:var(--frost-navy);flex-wrap:wrap;">
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
                <span style="font-family:var(--font-family-mono); font-size:0.75rem; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:3px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-50);">{escape(display_code)}</span>
                <span style="font-size:0.9375rem; font-weight:800; color:var(--frost-navy);">{escape(display_title)}</span>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:0.71875rem; font-weight:600; color:var(--frost-navy-50);">Decided by Assigned Reviewer</span>
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


def project_brief_content(prompt: Any) -> str:
    """Body text of a project. Projects now consist of a heading and one block of content; older projects that
    carried separate outcomes / requirements lists are folded into that content so nothing is lost."""
    content = (getattr(prompt, "description", "") or getattr(prompt, "objective", "") or "").strip()
    extras = []
    outcomes = [str(o).strip() for o in (getattr(prompt, "outcomes", None) or []) if str(o).strip()]
    reqs = [str(r).strip() for r in (getattr(prompt, "requirements", None) or []) if str(r).strip()]
    if outcomes:
        extras.append("Expected outcomes:\n" + "\n".join(f"- {o}" for o in outcomes))
    if reqs:
        extras.append("Requirements:\n" + "\n".join(f"- {r}" for r in reqs))
    return "\n\n".join([c for c in [content] + extras if c])


_PJ_SECTION_STYLE = {
    # key: (icon, accent class / colour)
    "case_study": ("layers", "accent-emerald", ""),
    "challenge": ("target", "accent-amber", ""),
    "details": ("clipboard", "accent-cyan", ""),
    "deliverables": ("file_text", "", "#2563EB"),
    "evaluation": ("award", "", "#7C3AED"),
}


def _pj_deliverable_icon(label: str) -> str:
    low = label.lower()
    if "github" in low or "repository" in low:
        return get_icon("github", 20)
    if "code" in low or "source" in low:
        return get_icon("code", 20)
    return get_icon("file_text", 20)


def _pj_paragraphs(text: Any) -> str:
    return "".join(f'<p class="pj-text">{escape(p.strip())}</p>' for p in str(text or "").split("\n\n") if p.strip())


def _pj_bullets(items: Any) -> str:
    items = [str(i).strip() for i in (items or []) if str(i).strip()]
    return '<ul class="pj-list">' + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>" if items else ""


def _pj_deliv_card(label: str, text: str, idx: Optional[int] = None) -> str:
    """One deliverable as an icon card. `idx` adds ids so the Create Project form can update it live."""
    nid = f' id="rp-del-name-{idx}"' if idx is not None else ""
    tid = f' id="rp-del-text-{idx}"' if idx is not None else ""
    return (f'<div class="pj-deliv"><span class="pj-deliv-ico">{_pj_deliverable_icon(label)}</span>'
            f'<div><div class="pj-deliv-name"{nid}>{escape(label)}</div><div class="pj-deliv-text"{tid}>{escape(text)}</div></div></div>')


def _pj_split_deliverable(line: str) -> Any:
    label, _, rest = str(line).partition(":")
    return (label.strip(), rest.strip()) if rest else ("Deliverable", str(line).strip())


def render_project_brief(title: str, content: str) -> str:
    """
    A project as shown to BOTH the reviewer and the cosmonaut: a big bold heading, then its sections as glass cards in the same
    visual language as the badge (Case Study, Your Challenge, Project Details, Deliverables as cards, Evaluation). Free-text
    projects written without section headings render as one block, exactly as before.
    """
    from starapp.badge_generator import PROJECT_SECTIONS, parse_project_content
    heading = (f'<h2 style="font-size:1.75rem; font-weight:900; letter-spacing:-0.4px; line-height:1.2; color:var(--frost-navy); '
               f'margin:0 0 14px 0; word-break:break-word;">{escape(title)}</h2>')
    parsed = parse_project_content(content)
    if not parsed:
        return f"""
    <div class="project-brief">
        {heading}
        <div style="font-size:0.875rem; line-height:1.7; color:var(--frost-navy); white-space:pre-wrap; word-break:break-word;">{escape(content)}</div>
    </div>
    """
    cards = []
    for key, sec_title, kind in PROJECT_SECTIONS:
        if key not in parsed or not parsed[key]:
            continue
        icon, accent, color = _PJ_SECTION_STYLE[key]
        val = parsed[key]
        if key == "deliverables":
            body = f'<div class="pj-deliv-grid">{"".join(_pj_deliv_card(*_pj_split_deliverable(line)) for line in val)}</div>'
        elif kind == "list":
            body = _pj_bullets(val)
        else:
            body = _pj_paragraphs(val)
        style = f' style="border-left-color:{color};"' if color else ""
        cards.append(f"""
        <div class="cb-section-card {accent}"{style}>
            <div class="cb-section-head pj-head">
                <div style="display:flex; align-items:center; gap:12px;">
                    <span class="cb-section-icon">{get_icon(icon, 17)}</span>
                    <span class="cb-section-title">{escape(sec_title)}</span>
                </div>
            </div>
            <div class="pj-body">{body}</div>
        </div>""")
    return f"""
    <div class="project-brief is-structured">
        {heading}
        {"".join(cards)}
    </div>
    """


def _render_assigned_project_spec_inner(
    assigned_proj: Any,
    rev_name_str: str = "",
    rev_band_str: str = "",
    window_str: str = "",
    sub_deadline_str: str = "",
    is_earned: bool = False,
    existing_sub: Optional[ProjectSubmission] = None,
    compact: bool = False
) -> str:
    """The project the mapped reviewer sent: heading + content only (extra arguments kept for compatibility)."""
    return render_project_brief(getattr(assigned_proj, "title", "") or "Project", project_brief_content(assigned_proj))


def _project_cta(badge: Badge, current_user: Optional[User]) -> Dict[str, str]:
    """
    The cosmonaut's "Earn the Badge" project action. There is nothing to request: the mapped reviewer creates the project and
    sends it. Until then the button reads "Project Allocated" and is DISABLED (state "pending"); the moment it arrives it
    unlocks (state "received") and opens the project, where the Submit Deliverables button lives.
    """
    from starapp.storage import store
    out = {"state": "none", "buttons": "", "text": ""}
    if not (current_user and store and badge):
        return out
    uid = current_user.id
    if not store.get_timeline(badge.id, uid) and badge.id not in {b.id for b in store.get_badges_for_cosmonaut(uid)}:
        return out
    rev_id = store.get_mapped_reviewer_id(badge.id, uid)
    rev_user = store.get_user_by_id(rev_id) if rev_id else None
    rev = escape(rev_user.name) if rev_user else "your mapped reviewer"
    bid = escape(badge.id)
    if store.get_project_prompt_for_cadet(badge.id, uid):
        out["state"] = "received"
        out["text"] = f"Your project from <strong>{rev}</strong> has arrived. Open it to read the brief and submit your deliverables."
        out["buttons"] = (
            f"<button type=\"button\" class=\"pa-btn is-ready\" id=\"btn-project-allocated-{bid}\" "
            f"onclick=\"window.StarAppBridge.dispatchAction('open_allocated_project_page', '{bid}')\">"
            f"{get_icon('clipboard', 15)}<span>Project Allocated</span>{get_icon('arrow_right', 13)}</button>"
        )
    else:
        out["state"] = "pending"
        out["text"] = f"<strong>{rev}</strong> will create your project and send it here. The button unlocks the moment it arrives."
        out["buttons"] = (
            f"<button type=\"button\" class=\"pa-btn is-locked\" id=\"btn-project-allocated-{bid}\" disabled aria-disabled=\"true\" "
            f"title=\"Your reviewer has not sent the project yet\">"
            f"{get_icon('lock', 14)}<span>Project Allocated</span></button>"
        )
    return out


_EARN_ICO = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
             'stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
             '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>')


def _earn_inner(title: str, text_html: str, right_html: str) -> str:
    """Inside of the "Earn the Badge" strip: title + one sentence on the left, the project button / status pills on the right."""
    return f"""
                <div class="earn-main">
                    <span class="earn-ico">{_EARN_ICO}</span>
                    <div>
                        <div class="earn-title">{title}</div>
                        <div class="earn-text">{text_html}</div>
                    </div>
                </div>
                <div class="earn-actions">{right_html}</div>"""


def _earn_card(title: str, text_html: str, right_html: str) -> str:
    """The glass "Earn the Badge" strip as its own card (used where the badge is not rendered by `render_badge_document`)."""
    return f"""
            <div id="badge-section-earn" class="earn-card">{_earn_inner(title, text_html, right_html)}
            </div>
            """


def _project_submit_button(badge_id: str, latest_sub: Optional[ProjectSubmission], is_earned: bool) -> str:
    """The one place a cosmonaut submits deliverables: inside the allocated project (marksheet link once the badge is earned)."""
    bid = escape(badge_id)
    if is_earned:
        return (f"""<button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('open_badge_marksheet', '{bid}')" """
                f"""style="display:inline-flex; align-items:center; gap:6px; font-weight:800; background:linear-gradient(135deg, #F59E0B, #D97706); border-color:#D97706;">"""
                f"""{get_icon("award", 14)}<span>View Official Marksheet</span>{get_icon("arrow_right", 13)}</button>""")
    label = (f'{get_icon("edit", 14)}<span>Edit Deliverables</span>' if latest_sub
             else f'{get_icon("rocket", 14)}<span>Submit Deliverables</span>')
    return (f"""<button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('open_submission_modal', '{bid}')" """
            f"""style="display:inline-flex; align-items:center; gap:6px; font-weight:800; background:linear-gradient(135deg, #059669 0%, #047857 100%); border-color:#059669;">"""
            f"""{label}{get_icon("arrow_right", 13)}</button>""")


def _render_allocated_project_detail_section(
    badge: Badge,
    assigned_proj: Any,
    rev_name_str: str,
    rev_band_str: str = "",
    window_str: str = "",
    sub_deadline_str: str = "",
    is_earned: bool = False,
    existing_sub: Optional[ProjectSubmission] = None,
    action_html: str = ""
) -> str:
    """Renders the inline Allocated Project card inside the dedicated Badge Detail Page (the submit button lives inside it)."""
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
    <div id="badge-section-allocated-project" class="earn-card is-project">
        <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('allocated-project')">
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                <span style="width:28px; height:28px; border-radius:6px; background:rgba(2,132,199,0.14); color:#0284C7; display:flex; align-items:center; justify-content:center;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 12h6"/><path d="M9 16h6"/><path d="M9 8h6"/></svg>
                </span>
                <span style="font-size:0.9375rem; font-weight:800; color:#0369A1;">Your Project</span>
            </div>
            <span id="chevron-allocated-project" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
        </div>
        <div id="content-allocated-project" style="padding:0 20px 20px 20px; display:block;">
            {spec_html}
            {f'<div class="earn-submit-row">{action_html}</div>' if action_html else ''}
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
        f'''<div style="display:flex; align-items:flex-start; gap:12px; font-size:0.8125rem; color:var(--frost-navy); line-height:1.55; padding:10px 14px; background:rgba(234,244,255,0.45); border:1px solid rgba(16,185,129,0.25); border-radius:var(--radius-sm); margin-bottom:8px;">
            <span style="width:20px; height:20px; border-radius:50%; background:rgba(16,185,129,0.15); color:#047857; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:800; flex-shrink:0; margin-top:1px;">✓</span>
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
        bg_style = "background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(236,253,245,0.7) 100%);" if is_comp else "background:rgba(244, 250, 255, 0.90);"
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
                    <span style="font-size:0.6875rem; font-weight:800; background:rgba(6,182,212,0.12); color:#0891B2; padding:3px 10px; border-radius:12px; border:1px solid rgba(6,182,212,0.25);">Topic {idx+1}</span>
                    <span id="topic-status-tag-{idx}" style="background:{status_bg}; color:{status_color}; padding:3px 10px; border-radius:12px; font-size:0.6875rem; font-weight:700; border:1px solid {status_border}; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease;">{status_text}</span>
                    <span style="font-size:0.6875rem; color:var(--frost-navy-50); font-weight:600;">Curriculum Module</span>
                </div>
                <div style="font-size:0.90625rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">{escape(t_title)}</div>
                <div style="font-size:0.78125rem; color:var(--frost-navy-75); line-height:1.5;">{escape(t_desc)}</div>
            </div>
            <div style="flex-shrink:0;">
                <button type="button" id="topic-toggle-btn-{idx}" class="{btn_class}"
                    onclick="window.StarAppBridge.toggleTopicCompletion({idx})"
                    style="background:{btn_bg}; color:{btn_color}; border:1.5px solid {btn_border}; box-shadow:{btn_shadow}; font-size:0.75rem; font-weight:800; padding:8px 16px; border-radius:20px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease, box-shadow 0.25s ease;">
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
            if a.decision in ("approve", "approved"):
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
    _cta = _project_cta(badge, current_user)
    project_allocated_btn_html = _cta["buttons"]      # locked "Project Allocated" until the reviewer sends it, then it opens the project

    if is_earned:
        top_card_style = "border:2px solid #F59E0B; background:linear-gradient(135deg, rgba(255,255,255,0.99) 0%, rgba(254,243,199,0.92) 100%); box-shadow:0 12px 36px rgba(245,158,11,0.25);"
        top_icon_style = "background:linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%); border:2px solid #F59E0B; color:#B45309;"
        top_icon_svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>'
        meta_chip = '<span style="background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; border:1px solid #D97706; font-size:0.6875rem; font-weight:800; padding:3px 12px; border-radius:12px; display:inline-flex; align-items:center; gap:4px; box-shadow:0 2px 6px rgba(245,158,11,0.4);">🏆 Badge Earned • Completed</span>'

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
                f'<span style="font-size:0.71875rem; font-weight:700; color:#78350F; background:rgba(255,255,255,0.85); border:1px solid rgba(245,158,11,0.45); padding:3px 10px; border-radius:999px;">📅 Awarded: <strong>{escape(awarded_on_str)}</strong></span>'
            )
        if rev_earned_asm:
            eval_chain_chips.append(
                f'<span style="font-size:0.71875rem; font-weight:700; color:#0369A1; background:rgba(224,242,254,0.9); border:1px solid rgba(2,132,199,0.3); padding:3px 10px; border-radius:999px;">Peer Reviewer ({escape(rev_earned_asm.reviewer_name)}): <strong>{rev_earned_asm.total_marks:.1f}/50 ({rev_earned_asm.percentage:.1f}%)</strong></span>'
            )
        if grd_earned_asm:
            eval_chain_chips.append(
                f'<span style="font-size:0.71875rem; font-weight:700; color:#047857; background:rgba(209,250,229,0.9); border:1px solid rgba(16,185,129,0.35); padding:3px 10px; border-radius:999px;">Guardian Final ({escape(grd_earned_asm.reviewer_name)}): <strong>{grd_earned_asm.total_marks:.1f}/50 ({grd_earned_asm.percentage:.1f}%)</strong></span>'
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
            s_dt = format_ist(getattr(existing_sub, "submitted_at", "") or "")
            g_chip = (
                f'<span style="font-size:0.71875rem; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{get_icon("github", 12)} {escape(g_url.split("/")[-1] if "/" in g_url else g_url)}</span>'
                if g_url else ""
            )
            sub_rec_html = f"""
            <div style="background:rgba(255,255,255,0.92); border:1px solid rgba(245,158,11,0.35); border-radius:var(--radius-sm); padding:10px 14px; margin-bottom:12px;">
                <div style="font-size:0.65625rem; font-weight:800; color:#92400E; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">
                    Certified Submission Artifacts &bull; Attempt #{getattr(existing_sub, 'attempt_number', 1)} {f'({escape(s_dt)})' if s_dt else ''}
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                    <span style="font-size:0.71875rem; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{get_icon("file_text", 12)} {escape(p_name)}</span>
                    <span style="font-size:0.71875rem; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{get_icon("code", 12)} {escape(c_name)}</span>
                    {g_chip}
                </div>
            </div>
            """

        earn_section_html = f"""
        <!-- SECTION 2: BADGE EARNED & ALLOCATED MARKS (GOLD) -->
        <div id="badge-section-earn" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:2px solid #F59E0B; padding:20px 24px; background:linear-gradient(135deg, rgba(254,243,199,0.98) 0%, rgba(253,230,138,0.7) 100%); box-shadow:0 6px 20px rgba(245,158,11,0.25);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; margin-bottom:14px; border-bottom:1.5px solid rgba(245,158,11,0.3); padding-bottom:12px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <span style="width:36px; height:36px; border-radius:50%; background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:1.125rem; box-shadow:0 2px 8px rgba(245,158,11,0.4);">
                        🏆
                    </span>
                    <div>
                        <div style="font-size:1rem; font-weight:900; color:#78350F; letter-spacing:-0.2px;">Badge Earned &amp; Certified!</div>
                        <div style="font-size:0.78125rem; color:#92400E; margin-top:2px;">Congratulations! Your milestone project has been officially evaluated, approved, and certified.</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    {project_allocated_btn_html}
                    <span style="font-family:var(--font-family-mono); font-size:0.90625rem; font-weight:900; color:#78350F; background:#FFFFFF; border:2px solid #F59E0B; padding:6px 16px; border-radius:20px; box-shadow:0 2px 8px rgba(245,158,11,0.2);">
                        Allocated Marks: {tot_m:.1f} / 50.0 ({pct_m:.1f}%)
                    </span>
                </div>
            </div>

            {eval_chain_html}
            {sub_rec_html}

            <!-- Rubric Criteria Scores Grid -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:14px;">
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Business Underst.</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{bu_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Architecture</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{ar_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Technical Knowl.</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{tk_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Presentation</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{pr_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Q&amp;A Defense</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{qa_m:.1f} / 10</div>
                </div>
            </div>

            <!-- Evaluator Feedback Section -->
            <div style="background:#FFFFFF; border:1.5px solid rgba(245,158,11,0.35); border-radius:var(--radius-sm); padding:14px 16px;">
                <div style="font-size:0.6875rem; font-weight:800; color:#92400E; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">Evaluator Feedback &amp; Certification Remarks:</div>
                <div style="font-size:0.8125rem; color:#78350F; line-height:1.55; font-style:italic; margin-bottom:10px;">
                    "{escape(fb_txt)}"
                </div>
                {f'<div style=\"font-size:0.75rem; color:#92400E; margin-bottom:4px;\"><strong>Key Strengths:</strong> {escape(str_txt)}</div>' if str_txt else ''}
                {f'<div style=\"font-size:0.75rem; color:#92400E;\"><strong>Recommendations:</strong> {escape(imp_txt)}</div>' if imp_txt else ''}
            </div>
        </div>
        """
    else:
        top_card_style = "border:2px solid var(--deep-frozen-midnight); background:rgba(244, 250, 255, 0.96); box-shadow:0 12px 36px rgba(7,22,41,0.12);"
        top_icon_style = "background:linear-gradient(135deg, rgba(234,244,255,1) 0%, rgba(157,183,213,0.3) 100%); border:1.5px solid var(--icy-steel); color:var(--deep-frozen-midnight);"
        top_icon_svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>'
        if has_allocated_project:
            meta_chip = '<span style="background:rgba(2,132,199,0.12); color:#0284C7; border:1px solid rgba(2,132,199,0.3); font-size:0.6875rem; font-weight:800; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">🚀 Project Allocated</span>'
        else:
            meta_chip = '<span style="background:rgba(16,185,129,0.12); color:#047857; border:1px solid rgba(16,185,129,0.3); font-size:0.6875rem; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Allocated Badge</span>'

        if existing_sub and getattr(existing_sub, "status", "") == "reviewer_assessed":
            earn_section_html = _earn_card(
                "Reviewer Evaluation Complete",
                "Your assigned reviewer has evaluated your deliverables. Awaiting Guardian final approval and badge award.",
                project_allocated_btn_html + '<span class="earn-pill is-cyan">Awaiting Guardian Award</span>',
            )
        elif existing_sub and getattr(existing_sub, "status", "") in ("pending", "submitted"):
            earn_section_html = _earn_card(
                "Earn the Badge",
                f"Deliverables routed to assigned reviewer <strong>{escape(rev_name_str)}</strong> &mdash; evaluation in progress.",
                project_allocated_btn_html + '<span class="earn-pill is-amber">Pending Reviewer Evaluation</span>',
            )
        else:
            earn_section_html = _earn_card("Earn the Badge", _cta["text"], _cta["buttons"])

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
            existing_sub=existing_sub,
            action_html=_project_submit_button(badge.id, existing_sub, is_earned)
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
                    <span style="background:#EF4444; color:#fff; font-size:0.65625rem; font-weight:800; padding:2px 8px; border-radius:10px;">RETAKE REQUIRED</span>
                    <span style="font-weight:800; font-size:0.84375rem; color:#991B1B;">Attempt #{existing_sub.attempt_number} Did Not Meet Passing Threshold</span>
                </div>
                <span style="font-family:var(--font-family-mono); font-size:0.75rem; font-weight:800; color:#DC2626;">Previous Score: {score_txt}</span>
            </div>
            <p style="font-size:0.78125rem; color:#7F1D1D; margin:0 0 8px 0; line-height:1.4;">
                <strong>Guardian Feedback:</strong> {escape(feedback_txt)}
            </p>
            <div style="font-size:0.71875rem; color:#B91C1C;">
                Please review the feedback above, improve your technical deliverable, and submit revised materials for <strong>Attempt #{next_attempt}</strong>. Your Attempt #{existing_sub.attempt_number} history is preserved in your permanent record.
            </div>
        </div>
        """

    mapping_info_banner = ""
    if rev_id_str or window_str or sub_deadline_str:
        rev_full = f"{rev_name_str} (Band {rev_band_str})" if rev_band_str else rev_name_str
        mapping_info_banner = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding:10px 14px; background:rgba(234,244,255,0.7); border:1px solid var(--icy-steel-40); border-radius:var(--radius-sm); margin-bottom:18px;">
            {f'<div style="font-size:0.75rem; color:var(--frost-navy);"><strong>Assigned Peer Reviewer:</strong> <span style="font-weight:700; color:var(--deep-frozen-midnight);">{escape(rev_full)}</span></div>' if rev_id_str else ''}
            {f'<div style="font-size:0.75rem; color:var(--frost-navy-75);"><strong>Review Window:</strong> <span style="font-family:var(--font-family-mono); font-weight:700;">{escape(window_str)}</span></div>' if window_str else ''}
            {f'<div style="font-size:0.75rem; color:#DC2626;"><strong>Submission Deadline:</strong> <span style="font-family:var(--font-family-mono); font-weight:700;">{escape(sub_deadline_str)}</span></div>' if sub_deadline_str else ''}
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
            <span style="font-size:0.75rem; font-weight:700; color:var(--frost-navy-50);">
                Badge Workspace &bull; Band {escape(selected_band)} &bull; {escape(badge_code)}
            </span>
        </div>
        """
        location_right_btn = f"""
        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')" style="font-size:0.75rem; font-weight:700; display:inline-flex; align-items:center; gap:5px; background:rgba(23,52,92,0.08); border-color:var(--icy-steel);">
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
        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('toggle_cosmonaut_badge_card', '{badge.id}')" style="font-size:0.75rem; font-weight:700; display:inline-flex; align-items:center; gap:5px; background:rgba(23,52,92,0.08); border-color:var(--icy-steel);">
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
        footer_right_btn = ""      # the project button is in the Earn the Badge strip; Submit Deliverables is inside the project

    return f"""
    <div>
        {top_back_header_html}
        <div class="{wrapper_classes}" id="badge-card-{badge.id}" data-badge-id="{badge.id}" style="{wrapper_style}">
            <!-- LOCATION BAR & ACTIONS -->
            <div style="padding:14px 20px; border-radius:var(--radius-md); background:linear-gradient(135deg, rgba(23,52,92,0.06) 0%, rgba(157,183,213,0.18) 100%); border:1.5px solid var(--deep-frozen-midnight); margin-bottom:22px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
                <div>
                    <span style="font-size:0.65625rem; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--deep-frozen-midnight);">
                        Badge Location
                    </span>
                    <div style="font-size:0.875rem; font-weight:800; color:var(--frost-navy); margin-top:5px; display:flex; align-items:center; flex-wrap:wrap; gap:8px;">
                        <span style="color:var(--deep-frozen-midnight); font-size:0.90625rem; font-weight:800;">{escape(badge_title)}</span>
                        <span style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem;">&rarr;</span>
                        <span style="background:rgba(6,182,212,0.12); color:#0891B2; padding:3px 10px; border-radius:14px; font-size:0.75rem; font-weight:700; border:1px solid rgba(6,182,212,0.25);">{escape(active_skill)}</span>
                        <span style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem;">&rarr;</span>
                        <span style="background:rgba(59,130,246,0.12); color:#1D4ED8; padding:3px 10px; border-radius:14px; font-size:0.75rem; font-weight:700; border:1px solid rgba(59,130,246,0.25);">{escape(active_cap)}</span>
                        <span style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem;">&rarr;</span>
                        <span style="background:rgba(139,92,246,0.12); color:#7C3AED; padding:3px 10px; border-radius:14px; font-size:0.75rem; font-weight:700; border:1px solid rgba(139,92,246,0.25);">{escape(active_power)}</span>
                        <span style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem;">&rarr;</span>
                        <span style="background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 10px; border-radius:14px; font-size:0.75rem; font-weight:800;">Band {selected_band}</span>
                    </div>
                </div>
                <div style="display:flex; gap:10px; align-items:center; flex-shrink:0;">
                    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.toggleAllBadgeSections()" style="font-size:0.75rem; font-weight:700;">
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
                        <span style="font-family:var(--font-family-mono); font-size:0.65625rem; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 9px; border-radius:var(--radius-xs); letter-spacing:0.5px;">BAND {selected_band}</span>
                        {f'<span style="font-family:var(--font-family-mono); font-size:0.6875rem; font-weight:800; background:var(--frost-mist); color:var(--deep-frozen-midnight); padding:3px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30);">{escape(badge_code)}</span>' if badge_code else ''}
                        {meta_chip}
                        <h2 style="font-size:1.45rem; font-weight:800; color:var(--frost-navy); margin:0 0 0 4px;">{escape(badge_title)}</h2>
                    </div>
                    <p style="font-size:0.84375rem; color:var(--frost-navy-75); line-height:1.5; margin:0;">{escape(badge_desc)}</p>
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
                        <span style="font-size:0.9375rem; font-weight:800; color:#047857;">Outcomes ({len(outcomes)})</span>
                    </div>
                    <span id="chevron-outcomes" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
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
                        <span style="font-size:0.9375rem; font-weight:800; color:#EA580C;">Practice Project</span>
                    </div>
                    <span id="chevron-practice" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
                </div>
                <div id="content-practice" style="padding:0 20px 20px 20px; display:block;">
                    <p style="font-size:0.8125rem; color:var(--frost-navy-75); margin:0 0 14px 0;">Want some hands-on practice? Use this prompt to generate a practice project.</p>
                    <div style="background:rgba(241,245,249,0.85); border:1px solid var(--icy-steel-40); border-radius:var(--radius-md); padding:16px; position:relative;">
                        <div id="practice-prompt-text" style="font-size:0.78125rem; color:var(--frost-navy); line-height:1.65; white-space:pre-wrap; font-family:var(--font-family-sans);">{escape(practice_prompt)}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid rgba(157,183,213,0.3); flex-wrap:wrap; gap:10px;">
                            <span style="font-size:0.71875rem; color:var(--frost-navy-50);">This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge.</span>
                            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('practice-prompt-text', this)" style="font-size:0.71875rem; font-weight:700; display:inline-flex; align-items:center; gap:6px;">
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
                        <span style="font-size:0.9375rem; font-weight:800; color:#0891B2;">Learning Topics</span>
                        <span id="topics-summary-pill" style="background:{'rgba(16,185,129,0.15)' if progress_pct > 0 else 'rgba(157,183,213,0.18)'}; color:{'#10B981' if progress_pct > 0 else 'var(--frost-navy-50)'}; padding:2px 10px; border-radius:12px; font-size:0.6875rem; font-weight:700; border:1px solid {'rgba(16,185,129,0.3)' if progress_pct > 0 else 'rgba(157,183,213,0.3)'};">
                            {completed_topics_count}/{total_topics} Completed
                        </span>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <div style="width:130px; height:8px; border-radius:4px; background:rgba(157,183,213,0.3); overflow:hidden;">
                                <div id="topics-progress-bar" style="width:{progress_pct}%; height:100%; background:linear-gradient(90deg, #06B6D4, #10B981); border-radius:4px; transition:width 0.4s ease;"></div>
                            </div>
                            <span id="topics-progress-text" style="font-size:0.75rem; font-weight:800; color:#0891B2; min-width:36px;">{progress_pct}%</span>
                        </div>
                    </div>
                    <span id="chevron-topics" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
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
                        <span style="font-size:0.9375rem; font-weight:800; color:#1D4ED8;">Learning Resources</span>
                    </div>
                    <span id="chevron-resources" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
                </div>
                <div id="content-resources" style="padding:0 20px 20px 20px; display:block;">
                    <p style="font-size:0.8125rem; color:var(--frost-navy-75); margin:0 0 14px 0;">Not sure where to start learning? Use this prompt to find free resources tailored to this badge.</p>
                    <div style="background:rgba(241,245,249,0.85); border:1px solid var(--icy-steel-40); border-radius:var(--radius-md); padding:16px; position:relative;">
                        <div id="resources-prompt-text" style="font-size:0.78125rem; color:var(--frost-navy); line-height:1.65; white-space:pre-wrap; font-family:var(--font-family-sans);">{escape(resources_prompt)}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid rgba(157,183,213,0.3); flex-wrap:wrap; gap:10px;">
                            <span style="font-size:0.71875rem; color:var(--frost-navy-50);">This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources.</span>
                            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('resources-prompt-text', this)" style="font-size:0.71875rem; font-weight:700; display:inline-flex; align-items:center; gap:6px;">
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
                        <span style="font-size:0.9375rem; font-weight:800; color:#7C3AED;">Related Skills, Capabilities &amp; Powers</span>
                    </div>
                    <span id="chevron-related" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
                </div>
                <div id="content-related" style="padding:0 20px 20px 20px; display:block;">
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:20px;">
                        <div>
                            <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Skills</div>
                            <span style="background:rgba(6,182,212,0.12); color:#0891B2; padding:5px 14px; border-radius:20px; font-size:0.78125rem; font-weight:700; display:inline-block; border:1px solid rgba(6,182,212,0.25);">{escape(active_skill)}</span>
                        </div>
                        <div>
                            <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Capabilities</div>
                            <span style="background:rgba(59,130,246,0.12); color:#1D4ED8; padding:5px 14px; border-radius:20px; font-size:0.78125rem; font-weight:700; display:inline-block; border:1px solid rgba(59,130,246,0.25);">{escape(active_cap)}</span>
                        </div>
                        <div>
                            <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Powers</div>
                            <span style="background:rgba(139,92,246,0.12); color:#7C3AED; padding:5px 14px; border-radius:20px; font-size:0.78125rem; font-weight:700; display:inline-block; border:1px solid rgba(139,92,246,0.25);">{escape(active_power)}</span>
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


def _cosmo_badge_state(badge: Badge, current_user: Optional[User], existing_sub: Optional[ProjectSubmission]) -> Dict[str, Any]:
    """Where this cosmonaut stands on one badge: earned (and the marksheet behind it), retake, mapped reviewer, project received."""
    from starapp.storage import store
    st: Dict[str, Any] = {
        "is_earned": False, "earned_asm": None, "rev_asm": None, "grd_asm": None, "awarded_on": "",
        "is_retake": bool(existing_sub and getattr(existing_sub, "status", "") in ("retake_required", "resubmission_requested")),
        "next_attempt": (getattr(existing_sub, "attempt_number", 1) + 1) if existing_sub else 1,
        "rev_name": "your mapped reviewer", "tl": None,
    }
    if not (current_user and store):
        return st
    tl = store.get_timeline(badge.id, current_user.id)
    st["tl"] = tl
    if tl and getattr(tl, "status", "") == "completed":
        st["is_earned"] = True
    rev_id = store.get_mapped_reviewer_id(badge.id, current_user.id)
    r_u = store.get_user_by_id(rev_id) if rev_id else None
    if r_u:
        st["rev_name"] = r_u.name
    for a in sorted(store.get_assessments_for_cosmonaut(current_user.id, badge.id),
                    key=lambda x: (getattr(x, "attempt_number", 1), 1 if getattr(x, "assessor_role", "") == "guardian" else 0, getattr(x, "reviewed_at", ""))):
        role = getattr(a, "assessor_role", "")
        if role == "reviewer":
            st["rev_asm"] = a
        elif role == "guardian":
            st["grd_asm"] = a
        if a.decision in ("approve", "approved"):
            st["is_earned"] = True
            st["earned_asm"] = a
    if not st["earned_asm"] and existing_sub:
        sub_asm = store.get_assessment_for_submission(existing_sub.id)
        if existing_sub.status == "approved" or (sub_asm and sub_asm.decision == "approve"):
            st["is_earned"] = True
            st["earned_asm"] = sub_asm
    ea = st["earned_asm"]
    st["awarded_on"] = (getattr(tl, "actual_award_date", "") if tl else "") or (
        getattr(ea, "reviewed_at", "")[:10] if ea and getattr(ea, "reviewed_at", "") else "")
    return st


def _render_badge_earned_card(st: Dict[str, Any], project_btn: str, existing_sub: Optional[ProjectSubmission] = None) -> str:
    """The achievement card on the badge page: gold seal, final score and the five rubric scores with the evaluator's feedback."""
    ea = st["earned_asm"]
    tot = ea.total_marks if ea else 0.0
    pct = ea.percentage if ea else 0.0
    scores = [("Business understanding", getattr(ea, "business_understanding", 0.0)), ("Architecture", getattr(ea, "architecture_report", 0.0)),
              ("Technical knowledge", getattr(ea, "technical_knowledge", 0.0)), ("Presentation", getattr(ea, "presentation", 0.0)),
              ("Q&A defense", getattr(ea, "qa", 0.0))] if ea else []
    tiles = "".join(
        f'<div class="mbe-score"><div class="mbe-score-lbl">{escape(n)}</div><div class="mbe-score-val">{v:.1f}<small> / 10</small></div>'
        f'<div class="mbe-meter"><span style="width:{max(0, min(100, int(round(v * 10))))}%;"></span></div></div>' for n, v in scores)
    fb = ((getattr(ea, "overall_feedback", "") or getattr(ea, "remarks", "")) if ea else "").strip()
    strengths = (getattr(ea, "strength_areas", "") if ea else "") or ""
    improve = (getattr(ea, "improvement_areas", "") if ea else "") or ""
    fb_html = ""
    if fb or strengths or improve:
        fb_html = '<div class="mbe-feedback">' + (f'<div class="mbe-fb-lbl">Evaluator feedback</div><p>{escape(fb)}</p>' if fb else "") + \
                  (f'<p><b>Key strengths:</b> {escape(strengths)}</p>' if strengths else "") + \
                  (f'<p><b>Recommendations:</b> {escape(improve)}</p>' if improve else "") + "</div>"
    return f"""
    <div id="badge-section-earned" class="mbe-card">
        <div class="mbe-head">
            <span class="gold-medal is-xl">{get_icon("award", 34)}</span>
            <div class="mbe-title-wrap">
                <div class="mbe-eyebrow">Achievement unlocked</div>
                <div class="mbe-title">Badge earned &amp; certified</div>
            </div>
            <div class="mbe-marks">
                <span class="mbe-marks-lbl">Final score</span>
                <span class="mbe-marks-val">{tot:.1f}<small> / 50</small></span>
                <span class="mbe-marks-pct">{pct:.1f}%</span>
            </div>
        </div>
        {f'<div class="mbe-scores">{tiles}</div>' if tiles else ''}
        {fb_html}
    </div>"""


def render_cosmonaut_badge_page(badge: Badge, current_user: Optional[User], existing_sub: Optional[ProjectSubmission] = None) -> str:
    """
    The cosmonaut's single-badge page, built from the SAME structured badge document the Guardian and the reviewer use
    (outcomes, practice project, topics, resources, related) in the glass style. The badge name carries two buttons on its right:
    Reviewer (their mapped reviewer) and Timeline (their schedule); both open live modals. The project itself is never shown on
    this page: "Project Allocated" (locked until the reviewer sends it) opens it, and Submit Deliverables lives inside it.
    """
    from starapp.badge_generator import structured_badge_from_row
    data = structured_badge_from_row(badge)
    doc = split_badge_document(data)
    st = _cosmo_badge_state(badge, current_user, existing_sub)
    cta = _project_cta(badge, current_user)
    bid = escape(badge.id)

    if st["is_earned"]:
        earn_inner = _earn_inner(
            "Badge earned", "Congratulations - you have earned this badge.",
            cta["buttons"] + f'<button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction(\'open_badge_marksheet\', \'{bid}\')">{get_icon("award", 14)}<span>Official marksheet</span></button>')
    elif existing_sub and getattr(existing_sub, "status", "") == "reviewer_assessed":
        earn_inner = _earn_inner("Reviewer evaluation complete", "Your assigned reviewer has evaluated your deliverables. Awaiting Guardian final approval and badge award.",
                                 cta["buttons"] + f'<button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction(\'open_badge_marksheet\', \'{bid}\')">{get_icon("award", 14)}<span>View marks</span></button><span class="earn-pill is-cyan">Awaiting Guardian award</span>')
    elif existing_sub and getattr(existing_sub, "status", "") in ("pending", "submitted"):
        earn_inner = _earn_inner("Earn the Badge", f"Deliverables routed to your reviewer <strong>{escape(st['rev_name'])}</strong> &mdash; evaluation in progress.",
                                 cta["buttons"] + '<span class="earn-pill is-amber">Pending reviewer evaluation</span>')
    else:
        earn_inner = _earn_inner("Earn the Badge", cta["text"] or "This badge is not allotted to you yet.", cta["buttons"])

    title_actions = (
        f'<button type="button" class="btn-secondary btn-sm cbp-btn" onclick="window.StarAppBridge.dispatchAction(\'open_cosmonaut_reviewer_modal\', \'{bid}\')">'
        f'{get_icon("shield", 14)}<span>Reviewer</span></button>'
        f'<button type="button" class="btn-secondary btn-sm cbp-btn" onclick="window.StarAppBridge.dispatchAction(\'open_cosmonaut_timeline_modal\', \'{bid}\')">'
        f'{get_icon("calendar", 14)}<span>Timeline</span></button>'
    )

    retake = ""
    if st["is_retake"] and existing_sub:
        from starapp.storage import store
        asm = store.get_assessment_for_submission(existing_sub.id) if store else None
        score = f"{asm.total_marks:.1f}/50 ({asm.percentage:.1f}%)" if asm else "below the threshold"
        fb = escape(asm.overall_feedback) if asm and asm.overall_feedback else "Revisions required."
        retake = f"""
        <div class="cbp-banner">
            <div class="cbp-banner-top"><span class="cbp-banner-tag">Retake required</span><b>Attempt #{existing_sub.attempt_number} did not meet the passing threshold</b><span class="cbp-banner-score">Previous score {score}</span></div>
            <p><b>Guardian feedback:</b> {fb}</p>
            <p>Improve your deliverables and submit Attempt #{st["next_attempt"]}. Your earlier attempt stays in your record.</p>
        </div>"""

    earned = _render_badge_earned_card(st, "", existing_sub) if st["is_earned"] else ""
    document = render_badge_document(
        title=doc["title"], description=doc["description"], outcomes=doc["outcomes"],
        practice_prompt=doc["practice_prompt"], resources_prompt=doc["resources_prompt"], topics=doc["topics"],
        skill=getattr(badge, "skill", ""), capability=getattr(badge, "capability", ""), power=getattr(badge, "power", ""),
        band=getattr(badge, "target_band", "B1"), is_editing=False, header_actions_html="",
        earn_strip_html=earn_inner, show_topic_progress=True,
        location_label="Badge Location", show_description=False, title_actions_html=title_actions, is_gold=bool(st["is_earned"]),
    )
    return f"""
    <div class="cbp-page" data-live-sync="badge" id="badge-card-{bid}" data-badge-id="{bid}">
        {retake}
        {earned}
        {document}
    </div>
    """


def render_cosmonaut_badge_detail_page(
    badge: Optional[Badge],
    current_user: Optional[User] = None,
    store: Any = None,
    submissions: Optional[List[ProjectSubmission]] = None
) -> str:
    """Renders the dedicated single-badge page (see `render_cosmonaut_badge_page`)."""
    if not badge:
        return """
        <div class="liquid-glass-card" style="padding:40px; text-align:center;">
            <h3 style="color:var(--frost-navy); margin:0 0 8px 0;">Badge Not Found</h3>
            <p style="font-size:0.8125rem; color:var(--frost-navy); margin:0;">The selected milestone badge could not be loaded.</p>
        </div>
        """
    user_subs = submissions if submissions is not None else (
        store.get_submissions_for_cosmonaut(current_user.id, badge.id) if (store and current_user) else []
    )
    badge_subs = sorted([s for s in user_subs if s.badge_id == badge.id], key=lambda s: getattr(s, "attempt_number", 1))
    return render_cosmonaut_badge_page(badge, current_user, badge_subs[-1] if badge_subs else None)


def _sub_files_html(sub: Optional[ProjectSubmission]) -> str:
    """The three deliverables of one submission as glass file chips (PDF report, source code, GitHub repository)."""
    if not sub:
        return ""
    pdf_name = getattr(sub, "pdf_name", "") or (sub.file_name if getattr(sub, "submission_type", "") == "pdf" else "")
    code_name = getattr(sub, "code_name", "") or (sub.file_name if getattr(sub, "submission_type", "") == "code" else "")
    gh = getattr(sub, "github_url", "") or (sub.payload if getattr(sub, "submission_type", "") == "github" else "") or ""
    chips = []
    for icon, label, val in (("file_text", "PDF report", pdf_name), ("code", "Source code", code_name), ("github", "GitHub repository", gh)):
        if val:
            shown = val.rstrip("/").split("/")[-1] if label == "GitHub repository" and "/" in val else val
            chips.append(f'<div class="pjp-file"><span class="pjp-file-ico">{get_icon(icon, 16)}</span>'
                         f'<div class="pjp-file-txt"><div class="pjp-file-lbl">{label}</div><div class="pjp-file-name">{escape(shown)}</div></div></div>')
    return f'<div class="pjp-files">{"".join(chips)}</div>' if chips else ""


def render_cosmonaut_project_page(badge: Badge, current_user: User, store: Any) -> str:
    """
    The allocated project as its OWN PAGE (opened from "Project Allocated"): who sent it and the schedule, the whole project, and the
    cosmonaut's submission status with the Submit / Edit Deliverables action. When the mapped reviewer has graded it, the marks show here too.
    """
    bid = escape(badge.id)
    proj = store.get_project_prompt_for_cadet(badge.id, current_user.id) if (store and current_user) else None
    if not (proj and getattr(proj, "status", "") in ("released", "sent")):
        return f"""
        <div class="pjp-page" data-live-sync="project">
            <div class="pjp-empty">{get_icon("lock", 28)}<div class="pjp-empty-title" role="heading" aria-level="2">Project not sent yet</div>
            <p>Your mapped reviewer has not sent the project for <b>{escape(badge.title)}</b>. This page updates by itself the moment it arrives.</p></div>
        </div>"""

    tl = store.get_timeline(badge.id, current_user.id)
    rev_id = store.get_mapped_reviewer_id(badge.id, current_user.id)
    rev = store.get_user_by_id(rev_id) if rev_id else None
    dt, review_days = _timeline_inputs(badge, tl)
    subs = sorted(store.get_submissions_for_cosmonaut(current_user.id, badge.id) or [], key=lambda s: getattr(s, "attempt_number", 1))
    latest = subs[-1] if subs else None
    st = _cosmo_badge_state(badge, current_user, latest)

    first = format_short_date(review_days[0]) if review_days else format_short_date(dt.get("review_date"))
    last = format_short_date(review_days[-1]) if review_days else ""
    window = f"{escape(first)} &rarr; {escape(last)}" if (first and last and first != last) else escape(first or "Schedule pending")
    rev_line = (f'{escape(rev.name)} <span class="pjp-fact-sub">Band {escape(getattr(rev, "band", "") or "")}</span>' if rev else "Your mapped reviewer")
    facts = f"""
        <div class="tlv-facts pjp-facts">
            <div class="tlv-fact"><div class="tlv-fact-lbl">Sent by</div><div class="tlv-fact-val">{rev_line}</div></div>
            <div class="tlv-fact"><div class="tlv-fact-lbl">Submission deadline</div><div class="tlv-fact-val rv-red">{escape(format_short_date(dt.get("submission_deadline")) or "Not set")}</div></div>
            <div class="tlv-fact"><div class="tlv-fact-lbl">Review window</div><div class="tlv-fact-val">{window}</div></div>
        </div>"""

    # --- where the cosmonaut stands -> status pill, the primary action, and the submission card -------------------------------------------
    status = getattr(latest, "status", "") if latest else ""
    if st["is_earned"]:
        pill = f'<span class="rv-pill is-green">{get_icon("award", 12)}<span>Badge earned</span></span>'
        action = (f'<button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction(\'open_badge_marksheet\', \'{bid}\')">'
                  f'{get_icon("award", 15)}<span>Open marksheet</span></button>')
    elif status == "reviewer_assessed":
        pill = f'<span class="rv-pill is-blue">{get_icon("clock", 12)}<span>Evaluated &middot; awaiting Guardian</span></span>'
        action = (f'<button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction(\'open_badge_marksheet\', \'{bid}\')">'
                  f'{get_icon("award", 15)}<span>Open marksheet</span></button>')
    elif status in ("pending", "submitted"):
        pill = f'<span class="rv-pill is-amber">{get_icon("clock", 12)}<span>Submitted &middot; with your reviewer</span></span>'
        action = (f'<button type="button" class="btn-metal pjp-primary" onclick="window.StarAppBridge.dispatchAction(\'open_submission_modal\', \'{bid}\')">'
                  f'{get_icon("edit", 15)}<span>Edit Deliverables</span></button>')
    else:
        pill = f'<span class="rv-pill is-amber">{get_icon("clock", 12)}<span>{"Retake needed" if st["is_retake"] else "Not submitted yet"}</span></span>'
        action = (f'<button type="button" class="btn-metal pjp-primary" onclick="window.StarAppBridge.dispatchAction(\'open_submission_modal\', \'{bid}\')">'
                  f'{get_icon("rocket", 15)}<span>Submit Deliverables</span></button>')

    ea = st["rev_asm"] or st["earned_asm"]
    marks = ""
    if ea and (status == "reviewer_assessed" or st["is_earned"] or getattr(ea, "assessor_role", "") == "guardian"):
        marks = (f'<div class="pjp-marks"><span class="pjp-marks-lbl">{"Final marks" if st["is_earned"] else "Reviewer marks"}</span>'
                 f'<span class="pjp-marks-val">{ea.total_marks:.1f} / 50 ({ea.percentage:.1f}%)</span></div>')

    if latest:
        sub_when = format_ist(getattr(latest, "submitted_at", "") or "")
        sub_body = (f'<div class="pjp-sub-meta">Attempt #{latest.attempt_number}'
                    + (f' &middot; submitted {escape(sub_when)}' if sub_when else "") + f'</div>{_sub_files_html(latest)}')
    else:
        sub_body = ('<p class="pjp-sub-empty">You have not submitted anything yet. Use <b>Submit Deliverables</b> to upload your PDF report, '
                    'source code and GitHub link. They go straight to your mapped reviewer, who assesses them and awards your marks.</p>')

    return f"""
    <div class="pjp-page" data-live-sync="project" id="project-page-{bid}" data-badge-id="{bid}">
        <div class="pjp-bar">
            <div class="pjp-bar-id">
                <span class="pjp-code">{escape(getattr(badge, "code", ""))}</span>
                <span class="pjp-badge-title" role="heading" aria-level="2">{escape(badge.title)}</span>
                <span class="pjp-kind">Project</span>
            </div>
            <div class="pjp-bar-actions">{pill}{action}</div>
        </div>
        {facts}
        {render_project_brief(getattr(proj, "title", "") or "Project", project_brief_content(proj))}
        <div class="pjp-sub-card" id="project-submission-card">
            <div class="pjp-sub-head">
                <div class="pjp-sub-title"><span class="pjp-sub-ico">{get_icon("send", 17)}</span><span>Your submission</span></div>
                {marks}
            </div>
            {sub_body}
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
                    if a.decision in ("approve", "approved"):
                        is_earned = True
                        earned_card_asm = a

            assigned_proj = store.get_project_prompt_for_cadet(b.id, current_user.id) if (store and current_user) else None
            has_proj = bool(assigned_proj and getattr(assigned_proj, "status", "") in ("released", "sent"))

            earned_meta_html = ""
            gold_cls = ""
            if is_earned:
                gold_cls = " gold-card"
                sub_chip = f'<span class="gold-chip">{get_icon("award", 12)}<span>Badge Earned</span></span>'
                action_btn_txt = "View Feedback &amp; Marks"
                btn_color_style = "background:linear-gradient(135deg, #b45309 0%, #92400e 100%); color:#ffffff; border-color:#92400e; text-shadow:none; letter-spacing:0.2px;"
                card_border_style = ""
                sc_str = f"{earned_card_asm.total_marks:.1f}/50 ({earned_card_asm.percentage:.1f}%)" if earned_card_asm else "Certified"
                aw_str = (getattr(tl, "actual_award_date", "") if tl else "") or (earned_card_asm.reviewed_at[:10] if earned_card_asm and getattr(earned_card_asm, "reviewed_at", "") else "Awarded")
                att_str = f"Attempt #{getattr(cadet_sub, 'attempt_number', getattr(earned_card_asm, 'attempt_number', 1))}" if (cadet_sub or earned_card_asm) else ""
                earned_meta_html = ""          # the score / award date live inside the badge, not on the card
            elif cadet_sub and getattr(cadet_sub, "status", "") == "reviewer_assessed":
                sub_chip = '<span style="background:rgba(6,182,212,0.12); color:#0891B2; border:1px solid rgba(6,182,212,0.3); font-size:0.6875rem; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">Awaiting Guardian Award</span>'
                action_btn_txt = "View Assessment Status"
                btn_color_style = "background:linear-gradient(135deg, #0891B2 0%, #0e7490 100%); color:#fff; border-color:#0891B2;"
                card_border_style = "border:1.5px solid var(--icy-steel-40); background:rgba(244, 250, 255, 0.94); box-shadow:0 6px 24px rgba(7,22,41,0.06);"
            elif cadet_sub and getattr(cadet_sub, "status", "") in ("retake_required", "resubmission_requested"):
                sub_chip = f'<span style="background:rgba(239,68,68,0.12); color:#DC2626; border:1px solid rgba(239,68,68,0.3); font-size:0.6875rem; font-weight:800; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">{get_icon("alert_triangle", 12)} Retake Required</span>'
                action_btn_txt = "Open Badge & Resubmit"
                btn_color_style = "background:linear-gradient(135deg, #DC2626 0%, #B91C1C 100%); color:#fff; border-color:#DC2626;"
                card_border_style = "border:1.5px solid rgba(239,68,68,0.45); background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(254,242,242,0.85) 100%); box-shadow:0 6px 24px rgba(239,68,68,0.08);"
            elif cadet_sub:
                sub_chip = f'<span style="background:rgba(16,185,129,0.12); color:#047857; border:1px solid rgba(16,185,129,0.3); font-size:0.6875rem; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">{get_icon("check", 12)} Submitted</span>'
                action_btn_txt = "View Badge & Submission"
                btn_color_style = "background:linear-gradient(135deg, #059669 0%, #047857 100%); color:#fff; border-color:#059669;"
                card_border_style = "border:1.5px solid var(--icy-steel-40); background:rgba(244, 250, 255, 0.94); box-shadow:0 6px 24px rgba(7,22,41,0.06);"
            elif has_proj:
                sub_chip = f'<span class="status-pill status-active" style="background:rgba(2,132,199,0.12); color:#0284C7; border:1px solid rgba(2,132,199,0.3); font-size:0.6875rem; font-weight:800; padding:3px 12px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">{get_icon("rocket", 12)} Project Allocated</span>'
                action_btn_txt = "View Badge & Project"
                btn_color_style = "background:linear-gradient(135deg, #0284C7 0%, #0369A1 100%); color:#fff; border-color:#0284C7;"
                card_border_style = "border:1.5px solid rgba(2,132,199,0.4); background:rgba(244, 250, 255, 0.95); box-shadow:0 6px 24px rgba(2,132,199,0.08);"
            else:
                sub_chip = '<span style="background:rgba(234,244,255,0.8); color:var(--deep-frozen-midnight); border:1px solid var(--icy-steel-40); font-size:0.6875rem; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">Allocated Project</span>'
                action_btn_txt = "Open Badge Details"
                btn_color_style = ""
                card_border_style = "border:1.5px solid var(--icy-steel-40); background:rgba(244, 250, 255, 0.94); box-shadow:0 6px 24px rgba(7,22,41,0.06);"

            open_page_onclick = f"window.StarAppBridge.dispatchAction('open_cosmonaut_badge_page', '{b.id}')"
            # Reviewer / Timeline on every card (an earned badge keeps them: its timeline shows when it was submitted, evaluated and earned)
            card_actions_html = (
                f'<div class="bc-actions">'
                f'<button type="button" class="btn-secondary btn-sm cbp-btn" onclick="event.stopPropagation(); window.StarAppBridge.dispatchAction(\'open_cosmonaut_reviewer_modal\', \'{b.id}\')">{get_icon("shield", 14)}<span>Reviewer</span></button>'
                f'<button type="button" class="btn-secondary btn-sm cbp-btn" onclick="event.stopPropagation(); window.StarAppBridge.dispatchAction(\'open_cosmonaut_timeline_modal\', \'{b.id}\')">{get_icon("calendar", 14)}<span>Timeline</span></button>'
                f'</div>'
            )
            open_btn_onclick = f"event.stopPropagation(); window.StarAppBridge.dispatchAction('open_cosmonaut_badge_page', '{b.id}')"

            # Initial collapsed card: strictly BAND, code, Allocated Project, hierarchy, and title
            badge_cards.append(f"""
            <div class="liquid-glass-card badge-card-item collapsed-badge-card{gold_cls}" id="badge-card-{b.id}" data-badge-id="{b.id}" onclick="{open_page_onclick}" role="button" tabindex="0" style="padding:22px; border-radius:var(--radius-lg); {card_border_style} display:flex; flex-direction:column; justify-content:space-between; transition:transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease; cursor:pointer;" onmouseover="this.style.transform='translateY(-2px)';" onmouseout="this.style.transform='none';">
                <div>
                    <!-- Badge name first (left), status chip on the top-right -->
                    <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px;">
                        <div style="display:flex; align-items:center; gap:12px; flex:1 1 0; min-width:0;">
                            {f'<span class="gold-medal" style="flex-shrink:0;" title="Badge earned">{get_icon("award", 22)}</span>' if is_earned else ''}
                            <div role="heading" aria-level="3" style="font-size:1.5rem; font-weight:800; color:var(--frost-navy); margin:0; letter-spacing:-0.3px; line-height:1.25; min-width:0;">
                                {b_title}
                            </div>
                        </div>
                        {f'<div style="flex-shrink:0; margin-top:2px;">{sub_chip}</div>' if is_earned else ''}
                    </div>
                    {earned_meta_html}
                    {card_actions_html}
                </div>

                <!-- Navigation to Dedicated Badge Detail Page -->
                <div style="margin-top:20px; padding-top:12px; border-top:1px dashed var(--icy-steel-30); display:flex; justify-content:space-between; align-items:center; gap:8px;">
                    <button type="button" class="btn-metal btn-sm" onclick="{open_btn_onclick}" style="font-weight:800; font-size:0.71875rem; padding:5px 14px; display:inline-flex; align-items:center; gap:5px; {btn_color_style}">
                        <span>{action_btn_txt}</span>
                        <span>&rarr;</span>
                    </button>
                    <span style="font-size:0.6875rem; color:var(--frost-navy-50); font-weight:700; background:rgba(23,52,92,0.06); padding:4px 8px; border-radius:10px;">Open Page &rarr;</span>
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
        <div class="liquid-glass-card" style="padding:32px 24px; text-align:center; border-radius:var(--radius-lg); border:1.5px dashed var(--icy-steel-30); background:rgba(244, 250, 255, 0.81); margin-bottom:32px;">
            <div style="width:48px; height:48px; border-radius:50%; background:rgba(6,182,212,0.12); color:#0891B2; display:flex; align-items:center; justify-content:center; margin:0 auto 12px auto;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>
                </svg>
            </div>
            <h3 style="font-size:1rem; font-weight:800; color:var(--frost-navy); margin:0 0 6px 0;">No Badges Allocated Yet</h3>
            <p style="font-size:0.8125rem; color:var(--frost-navy-75); max-width:540px; margin:0 auto 16px auto; line-height:1.5;">
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
            </div>
        </div>

        <!-- 1. BADGES CARDS GRID -->
        {badges_grid_html}
    </div>
    """


_UPLOAD_ICO = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
               'stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>')


def _sd_file_field(field_id: str, label: str, icon: str, accept: str, tone: str, current: str = "") -> str:
    """One file deliverable as a glass row: type icon tile, its name, the chosen file (or none) and a Browse button (StarAppBridge.showPickedFile)."""
    name_id = f"sd-name-{field_id}"
    shown = escape(current) if current else "No file chosen"
    cls = " is-set" if current else ""
    return f"""
        <label class="sd-row sd-drop{cls}" for="{field_id}" id="sd-drop-{field_id}">
            <span class="sd-ico is-{tone}">{get_icon(icon, 22)}</span>
            <span class="sd-row-txt"><b>{escape(label)}</b><span class="sd-file-name" id="{name_id}">{shown}</span></span>
            <span class="sd-drop-btn">{_UPLOAD_ICO}<span class="sd-drop-btn-lbl">{"Replace" if current else "Browse"}</span></span>
            <input type="file" id="{field_id}" class="sd-file" accept="{escape(accept)}"
                   onchange="window.StarAppBridge.showPickedFile(this, '{name_id}', 'sd-drop-{field_id}')">
        </label>"""


def render_cosmonaut_submission_modal(badge: Badge, current_user: User, store: Any, existing_sub: Optional[ProjectSubmission] = None) -> str:
    """
    The Submit / Edit Deliverables dialog (opened from the project page): a clean glass form for the three deliverables - PDF report,
    source code and GitHub link. Submitting routes them to the cosmonaut's mapped reviewer, who then sees and grades them.
    """
    proj = store.get_project_prompt_for_cadet(badge.id, current_user.id) if (store and current_user) else None
    if not (proj and getattr(proj, "status", "") in ("released", "sent")):
        cta = _project_cta(badge, current_user)
        return f"""
        <div class="sd-wrap">
            <div class="sd-empty">{get_icon("lock", 26)}<div class="sd-empty-title" role="heading" aria-level="3">Your project has not been sent yet</div>
            <p>{cta["text"] or "This badge is not allotted to you."}</p></div>
            <div class="sd-footer"><button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">Close</button></div>
        </div>"""

    rev_id = store.get_mapped_reviewer_id(badge.id, current_user.id)
    rev = store.get_user_by_id(rev_id) if rev_id else None
    rev_first = escape(rev.name.split()[0]) if rev else "your reviewer"
    notice = ""
    if existing_sub:
        when = format_ist(getattr(existing_sub, "submitted_at", "") or "")
        notice = (f'<div class="sd-notice">{get_icon("check_circle", 16)}<span>Attempt #{existing_sub.attempt_number} submitted'
                  + (f' on <b>{escape(when)}</b>' if when else "") + '. Saving replaces your current files.</span></div>')
    pdf_cur = getattr(existing_sub, "pdf_name", "") if existing_sub else ""
    code_cur = getattr(existing_sub, "code_name", "") if existing_sub else ""
    gh_val = getattr(existing_sub, "github_url", "") if existing_sub else ""
    submit_label = (f'{get_icon("check_circle", 15)}<span>Update deliverables</span>' if existing_sub
                    else f'{get_icon("send", 15)}<span>Submit to {rev_first}</span>')

    return f"""
    <div class="sd-wrap">
        <div class="sd-head">
            <span class="sd-head-ico">{get_icon("rocket", 22)}</span>
            <div class="sd-heading" role="heading" aria-level="3">{"Edit your deliverables" if existing_sub else "Submit your deliverables"}</div>
        </div>
        {notice}
        <form id="project-submission-form" onsubmit="event.preventDefault(); window.StarAppBridge.submitCosmonautDeliverables();">
            <input type="hidden" id="submission-badge-id" value="{escape(badge.id)}">
            {_sd_file_field("submission-pdf-file", "PDF report", "file_text", ".pdf", "red", pdf_cur)}
            {_sd_file_field("submission-code-file", "Source code", "code", ".py,.sql,.zip,.js,.json,.tar.gz,.txt", "violet", code_cur)}
            <label class="sd-row sd-link" for="submission-github-url">
                <span class="sd-ico is-dark">{get_icon("github", 22)}</span>
                <span class="sd-row-txt"><b>GitHub repository</b>
                    <input type="url" id="submission-github-url" class="sd-input" value="{escape(gh_val)}" placeholder="https://github.com/your-name/your-project" autocomplete="off"></span>
            </label>
            <div class="sd-footer">
                <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">Cancel</button>
                <button type="submit" class="btn-metal sd-submit">{submit_label}</button>
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
    _cta = _project_cta(badge, current_user)

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
        f'''<div style="display:flex; align-items:flex-start; gap:12px; font-size:0.8125rem; color:var(--frost-navy); line-height:1.55; padding:10px 14px; background:rgba(234,244,255,0.45); border:1px solid rgba(16,185,129,0.25); border-radius:var(--radius-sm); margin-bottom:8px;">
            <span style="width:20px; height:20px; border-radius:50%; background:rgba(16,185,129,0.15); color:#047857; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:800; flex-shrink:0; margin-top:1px;">✓</span>
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
        bg_style = "background:linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(236,253,245,0.7) 100%);" if is_comp else "background:rgba(244, 250, 255, 0.90);"
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
                    <span style="font-size:0.6875rem; font-weight:800; background:rgba(6,182,212,0.12); color:#0891B2; padding:3px 10px; border-radius:12px; border:1px solid rgba(6,182,212,0.25);">Topic {idx+1}</span>
                    <span id="topic-status-tag-{idx}" style="background:{status_bg}; color:{status_color}; padding:3px 10px; border-radius:12px; font-size:0.6875rem; font-weight:700; border:1px solid {status_border}; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease;">{status_text}</span>
                    <span style="font-size:0.6875rem; color:var(--frost-navy-50); font-weight:600;">Curriculum Module</span>
                </div>
                <div style="font-size:0.90625rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">{escape(t_title)}</div>
                <div style="font-size:0.78125rem; color:var(--frost-navy-75); line-height:1.5;">{escape(t_desc)}</div>
            </div>
            <div style="flex-shrink:0;">
                <button type="button" id="topic-toggle-btn-{idx}" class="{btn_class}"
                    onclick="window.StarAppBridge.toggleTopicCompletion({idx})"
                    style="background:{btn_bg}; color:{btn_color}; border:1.5px solid {btn_border}; box-shadow:{btn_shadow}; font-size:0.75rem; font-weight:800; padding:8px 16px; border-radius:20px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease, box-shadow 0.25s ease;">
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
            if a.decision in ("approve", "approved"):
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
        meta_chip = '<span style="background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; border:1px solid #D97706; font-size:0.6875rem; font-weight:800; padding:3px 12px; border-radius:12px; display:inline-flex; align-items:center; gap:4px; box-shadow:0 2px 6px rgba(245,158,11,0.4);">🏆 Badge Earned • Completed</span>'

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
                    <span style="width:36px; height:36px; border-radius:50%; background:linear-gradient(135deg, #F59E0B, #D97706); color:#451A03; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:1.125rem; box-shadow:0 2px 8px rgba(245,158,11,0.4);">
                        🏆
                    </span>
                    <div>
                        <div style="font-size:1rem; font-weight:900; color:#78350F; letter-spacing:-0.2px;">Badge Earned &amp; Certified!</div>
                        <div style="font-size:0.78125rem; color:#92400E; margin-top:2px;">Congratulations! Your milestone project has been officially evaluated, approved, and certified.</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-family:var(--font-family-mono); font-size:0.90625rem; font-weight:900; color:#78350F; background:#FFFFFF; border:2px solid #F59E0B; padding:6px 16px; border-radius:20px; box-shadow:0 2px 8px rgba(245,158,11,0.2);">
                        Allocated Marks: {tot_m:.1f} / 50.0 ({pct_m:.1f}%)
                    </span>
                </div>
            </div>

            <!-- Rubric Criteria Scores Grid -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:14px;">
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Business Underst.</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{bu_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Architecture</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{ar_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Technical Knowl.</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{tk_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Presentation</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{pr_m:.1f} / 10</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid rgba(245,158,11,0.4); border-radius:var(--radius-xs); padding:8px 10px; text-align:center;">
                    <div style="font-size:0.65625rem; font-weight:700; color:#92400E; text-transform:uppercase;">Q&amp;A Defense</div>
                    <div style="font-size:0.875rem; font-weight:900; color:#78350F; font-family:var(--font-family-mono); margin-top:2px;">{qa_m:.1f} / 10</div>
                </div>
            </div>

            <!-- Evaluator Feedback Section -->
            <div style="background:#FFFFFF; border:1.5px solid rgba(245,158,11,0.35); border-radius:var(--radius-sm); padding:14px 16px;">
                <div style="font-size:0.6875rem; font-weight:800; color:#92400E; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">Evaluator Feedback &amp; Certification Remarks:</div>
                <div style="font-size:0.8125rem; color:#78350F; line-height:1.55; font-style:italic; margin-bottom:10px;">
                    "{escape(fb_txt)}"
                </div>
                {f'<div style=\"font-size:0.75rem; color:#92400E; margin-bottom:4px;\"><strong>Key Strengths:</strong> {escape(str_txt)}</div>' if str_txt else ''}
                {f'<div style=\"font-size:0.75rem; color:#92400E;\"><strong>Recommendations:</strong> {escape(imp_txt)}</div>' if imp_txt else ''}
            </div>
        </div>
        """
    else:
        modal_top_style = "border:1.5px solid var(--deep-frozen-midnight);"
        top_icon_style = "background:linear-gradient(135deg, rgba(234,244,255,1) 0%, rgba(157,183,213,0.3) 100%); border:1.5px solid var(--icy-steel); color:var(--deep-frozen-midnight);"
        top_icon_svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>'
        meta_chip = '<span style="background:rgba(16,185,129,0.12); color:#047857; border:1px solid rgba(16,185,129,0.3); font-size:0.6875rem; font-weight:700; padding:3px 10px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Allocated Badge</span>'

        if existing_sub and getattr(existing_sub, "status", "") == "reviewer_assessed":
            earn_section_html = _earn_card(
                "Reviewer Evaluation Complete",
                "Your assigned reviewer has evaluated your deliverables. Awaiting Guardian final approval and badge award.",
                project_allocated_btn_html + '<span class="earn-pill is-cyan">Awaiting Guardian Award</span>',
            )
        elif existing_sub and getattr(existing_sub, "status", "") in ("pending", "submitted"):
            earn_section_html = _earn_card(
                "Earn the Badge",
                f"Deliverables routed to assigned reviewer <strong>{escape(rev_name_str)}</strong> &mdash; evaluation in progress.",
                project_allocated_btn_html + '<span class="earn-pill is-amber">Pending Reviewer Evaluation</span>',
            )
        else:
            earn_section_html = _earn_card("Earn the Badge", _cta["text"], _cta["buttons"])

    return f"""
    <div style="padding:4px 0 10px 0;">
        <!-- LOCATION BAR -->
        <div style="padding:16px 20px; border-radius:var(--radius-md); background:linear-gradient(135deg, rgba(23,52,92,0.06) 0%, rgba(157,183,213,0.18) 100%); {modal_top_style} margin-bottom:22px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; transition:border-color 0.3s ease;">
            <div>
                <span style="font-size:0.65625rem; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--deep-frozen-midnight);">
                    Badge Location
                </span>
                <div style="font-size:0.875rem; font-weight:800; color:var(--frost-navy); margin-top:5px; display:flex; align-items:center; flex-wrap:wrap; gap:8px;">
                    <span style="color:var(--deep-frozen-midnight); font-size:0.90625rem; font-weight:800;">{escape(badge_title)}</span>
                    <span style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem;">&rarr;</span>
                    <span style="background:rgba(6,182,212,0.12); color:#0891B2; padding:3px 10px; border-radius:14px; font-size:0.75rem; font-weight:700; border:1px solid rgba(6,182,212,0.25);">{escape(active_skill)}</span>
                    <span style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem;">&rarr;</span>
                    <span style="background:rgba(59,130,246,0.12); color:#1D4ED8; padding:3px 10px; border-radius:14px; font-size:0.75rem; font-weight:700; border:1px solid rgba(59,130,246,0.25);">{escape(active_cap)}</span>
                    <span style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem;">&rarr;</span>
                    <span style="background:rgba(139,92,246,0.12); color:#7C3AED; padding:3px 10px; border-radius:14px; font-size:0.75rem; font-weight:700; border:1px solid rgba(139,92,246,0.25);">{escape(active_power)}</span>
                    <span style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem;">&rarr;</span>
                    <span style="background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 10px; border-radius:14px; font-size:0.75rem; font-weight:800;">Band {selected_band}</span>
                </div>
            </div>
            <div style="display:flex; gap:10px; align-items:center; flex-shrink:0;">
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.toggleAllBadgeSections()" style="font-size:0.75rem; font-weight:700;">
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
                    {f'<span style="font-family:var(--font-family-mono); font-size:0.6875rem; font-weight:800; background:var(--frost-mist); color:var(--deep-frozen-midnight); padding:3px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30);">{escape(badge_code)}</span>' if badge_code else ''}
                    {meta_chip}
                    <h2 style="font-size:1.45rem; font-weight:800; color:var(--frost-navy); margin:0;">{escape(badge_title)}</h2>
                </div>
                <p style="font-size:0.84375rem; color:var(--frost-navy-75); line-height:1.5; margin:0;">{escape(badge_desc)}</p>
            </div>
        </div>

        <!-- SECTION 1: OUTCOMES -->
        <div id="badge-section-outcomes" class="liquid-glass-card" style="margin-bottom:18px; border-radius:var(--radius-lg); border:1.5px solid #10B981; overflow:hidden; background:rgba(255,255,255,0.98);">
            <div style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; user-select:none;" onclick="window.StarAppBridge.toggleBadgeSection('outcomes')">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:28px; height:28px; border-radius:6px; background:rgba(16,185,129,0.12); color:#047857; display:flex; align-items:center; justify-content:center;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
                    </span>
                    <span style="font-size:0.9375rem; font-weight:800; color:#047857;">Outcomes ({len(outcomes)})</span>
                </div>
                <span id="chevron-outcomes" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
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
                    <span style="font-size:0.9375rem; font-weight:800; color:#EA580C;">Practice Project</span>
                </div>
                <span id="chevron-practice" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
            </div>
            <div id="content-practice" style="padding:0 20px 20px 20px; display:block;">
                <p style="font-size:0.8125rem; color:var(--frost-navy-75); margin:0 0 14px 0;">Want some hands-on practice? Use this prompt to generate a practice project.</p>
                <div style="background:rgba(241,245,249,0.85); border:1px solid var(--icy-steel-40); border-radius:var(--radius-md); padding:16px; position:relative;">
                    <div id="practice-prompt-text" style="font-size:0.78125rem; color:var(--frost-navy); line-height:1.65; white-space:pre-wrap; font-family:var(--font-family-sans);">{escape(practice_prompt)}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid rgba(157,183,213,0.3); flex-wrap:wrap; gap:10px;">
                        <span style="font-size:0.71875rem; color:var(--frost-navy-50);">This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge.</span>
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('practice-prompt-text', this)" style="font-size:0.71875rem; font-weight:700; display:inline-flex; align-items:center; gap:6px;">
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
                    <span style="font-size:0.9375rem; font-weight:800; color:#0891B2;">Learning Topics</span>
                    <span id="topics-summary-pill" style="background:{'rgba(16,185,129,0.15)' if progress_pct > 0 else 'rgba(157,183,213,0.18)'}; color:{'#10B981' if progress_pct > 0 else 'var(--frost-navy-50)'}; padding:2px 10px; border-radius:12px; font-size:0.6875rem; font-weight:700; border:1px solid {'rgba(16,185,129,0.3)' if progress_pct > 0 else 'rgba(157,183,213,0.3)'};">
                        {completed_topics_count}/{total_topics} Completed
                    </span>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="width:130px; height:8px; border-radius:4px; background:rgba(157,183,213,0.3); overflow:hidden;">
                            <div id="topics-progress-bar" style="width:{progress_pct}%; height:100%; background:linear-gradient(90deg, #06B6D4, #10B981); border-radius:4px; transition:width 0.4s ease;"></div>
                        </div>
                        <span id="topics-progress-text" style="font-size:0.75rem; font-weight:800; color:#0891B2; min-width:36px;">{progress_pct}%</span>
                    </div>
                </div>
                <span id="chevron-topics" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
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
                    <span style="font-size:0.9375rem; font-weight:800; color:#1D4ED8;">Learning Resources</span>
                </div>
                <span id="chevron-resources" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
            </div>
            <div id="content-resources" style="padding:0 20px 20px 20px; display:block;">
                <p style="font-size:0.8125rem; color:var(--frost-navy-75); margin:0 0 14px 0;">Not sure where to start learning? Use this prompt to find free resources tailored to this badge.</p>
                <div style="background:rgba(241,245,249,0.85); border:1px solid var(--icy-steel-40); border-radius:var(--radius-md); padding:16px; position:relative;">
                    <div id="resources-prompt-text" style="font-size:0.78125rem; color:var(--frost-navy); line-height:1.65; white-space:pre-wrap; font-family:var(--font-family-sans);">{escape(resources_prompt)}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid rgba(157,183,213,0.3); flex-wrap:wrap; gap:10px;">
                        <span style="font-size:0.71875rem; color:var(--frost-navy-50);">This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources.</span>
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('resources-prompt-text', this)" style="font-size:0.71875rem; font-weight:700; display:inline-flex; align-items:center; gap:6px;">
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
                    <span style="font-size:0.9375rem; font-weight:800; color:#7C3AED;">Related Skills, Capabilities &amp; Powers</span>
                </div>
                <span id="chevron-related" style="color:var(--frost-navy-50); font-weight:800; font-size:0.8125rem; transition:transform 0.2s ease;">▲</span>
            </div>
            <div id="content-related" style="padding:0 20px 20px 20px; display:block;">
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:20px;">
                    <div>
                        <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Skills</div>
                        <span style="background:rgba(6,182,212,0.12); color:#0891B2; padding:5px 14px; border-radius:20px; font-size:0.78125rem; font-weight:700; display:inline-block; border:1px solid rgba(6,182,212,0.25);">{escape(active_skill)}</span>
                    </div>
                    <div>
                        <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Capabilities</div>
                        <span style="background:rgba(59,130,246,0.12); color:#1D4ED8; padding:5px 14px; border-radius:20px; font-size:0.78125rem; font-weight:700; display:inline-block; border:1px solid rgba(59,130,246,0.25);">{escape(active_cap)}</span>
                    </div>
                    <div>
                        <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:6px;">Powers</div>
                        <span style="background:rgba(139,92,246,0.12); color:#7C3AED; padding:5px 14px; border-radius:20px; font-size:0.78125rem; font-weight:700; display:inline-block; border:1px solid rgba(139,92,246,0.25);">{escape(active_power)}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL FOOTER ACTIONS -->
        <div style="display:flex; justify-content:flex-end; align-items:center; gap:12px; padding-top:14px; border-top:1px solid var(--icy-steel-30); flex-wrap:wrap;">
            <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">
                Close
            </button>
        </div>
    </div>
    """

# ==============================================================================
# 6.6 ASSESSMENT RESULTS & MARKSHEETS
# ==============================================================================

def _results_extension_banner(latest_ext: Any) -> str:
    """One glass line about the latest deadline-extension request for the selected badge."""
    if latest_ext.status == "approved":
        tone, tag = "green", "Deadline Extended"
        text = f'New submission deadline <b>{escape(latest_ext.proposed_deadline)}</b> (approved by the Guardian).'
        note = latest_ext.guardian_response or ""
    elif latest_ext.status == "pending":
        tone, tag = "amber", "Extension Pending"
        text = f'Requested <b>{escape(latest_ext.proposed_deadline)}</b> &middot; awaiting Guardian review. Current cutoff {escape(latest_ext.current_deadline)}.'
        note = ""
    else:
        tone, tag = "red", "Extension Rejected"
        text = f'Original cutoff stays at <b>{escape(latest_ext.current_deadline)}</b>.'
        note = latest_ext.guardian_response or ""
    return (f'<div class="ms-ext is-{tone}"><span class="ms-ext-tag">{tag}</span><span class="ms-ext-text">{text}</span>'
            + (f'<span class="ms-ext-note">{escape(note)}</span>' if note else "") + '</div>')


def render_cosmonaut_results(
    assessments: List[AssessmentMarksheet],
    badges_map: Dict[str, Badge],
    selected_badge_id: Optional[str] = None,
    available_badges: Optional[List[Badge]] = None,
    extensions: Optional[List[DeadlineExtension]] = None,
    selected_asm_id: Optional[str] = None,
    submissions: Optional[List[ProjectSubmission]] = None,
    project_ready_ids: Optional[Any] = None,
) -> str:
    """
    Assessment Marksheet page: pick a milestone badge, see its official 50-mark marksheet in glass. Every evaluation (the peer reviewer's
    marks as soon as they are submitted, then the Guardian's final) is a tab on the marksheet; without one the page says where the work stands.
    """
    # 1. selectable badges: allotted/published badges + any assessed badge
    badge_list = list(available_badges) if available_badges else []
    existing_ids = {b.id for b in badge_list}
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
    badge_list.sort(key=lambda b: present_4_ids.index(b.id) if b.id in present_4_ids else 100)

    if not badge_list and not assessments:
        return f"""
        <div class="ms-page">
            <h2 class="ms-page-title">Official Assessment Marksheets</h2>
            <div class="ms-empty">
                <span class="ms-empty-ico">{get_icon("clipboard", 26)}</span>
                <div class="ms-empty-title" role="heading" aria-level="3">No badges allotted in this cycle</div>
                <p>You do not have any published milestone badges or evaluation marksheets in the active performance cycle yet.</p>
            </div>
        </div>
        """

    if not selected_badge_id or (selected_badge_id not in [b.id for b in badge_list]):
        selected_badge_id = badge_list[0].id if badge_list else "badge_gov_101"

    badge_options = "".join(
        f'<option value="{escape(b.id)}"{" selected" if b.id == selected_badge_id else ""}>{escape(b.code)}: {escape(b.title)}</option>'
        for b in badge_list)

    # official Guardian final first within an attempt; the newest evaluation is shown by default (or the tab the cosmonaut picked)
    matching_asms = sorted(
        [a for a in assessments if a.badge_id == selected_badge_id],
        key=lambda a: (getattr(a, "attempt_number", 1), 1 if getattr(a, "assessor_role", "") == "guardian" else 0, getattr(a, "reviewed_at", "")),
    )
    current_badge = badges_map.get(selected_badge_id)
    badge_code = current_badge.code if current_badge else selected_badge_id
    badge_title = current_badge.title if current_badge else "Milestone Assessment"

    ext_banner = ""
    if extensions:
        badge_exts = [e for e in extensions if e.badge_id == selected_badge_id]
        if badge_exts:
            ext_banner = _results_extension_banner(badge_exts[-1])

    toolbar = f"""
    <div class="ms-toolbar">
        <div class="liquid-select-wrapper ms-select">
            <select id="results-badge-select" class="liquid-glass-control liquid-glass-select" onchange="window.StarAppBridge.dispatchAction('change_results_badge', this.value)">
                {badge_options}
            </select>
        </div>
    </div>"""

    if matching_asms:
        selected_asm = next((a for a in matching_asms if a.id == selected_asm_id), matching_asms[-1])
        sheet_content = render_standard_marksheet(selected_asm, current_badge, matching_asms, tab_action="select_results_marksheet")
    else:
        mine = sorted([s for s in (submissions or []) if s.badge_id == selected_badge_id], key=lambda s: getattr(s, "attempt_number", 1))
        sid = escape(selected_badge_id)
        if mine:
            title, text = "Submitted - waiting for evaluation", (
                f"Your deliverables for <b>{escape(badge_title)}</b> (attempt #{mine[-1].attempt_number}) are with your mapped reviewer. "
                "The marks appear here the moment they are submitted.")
            btn = (f'<button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction(\'open_allocated_project_page\', \'{sid}\')">'
                   f'{get_icon("clipboard", 15)}<span>View project &amp; submission</span></button>')
        elif project_ready_ids and selected_badge_id in project_ready_ids:
            title, text = "Evaluation pending", (
                f"Your project for <b>{escape(badge_title)}</b> has arrived. Submit your deliverables; your mapped reviewer will assess them "
                "and the marks appear here.")
            btn = (f'<button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction(\'open_allocated_project_page\', \'{sid}\')">'
                   f'{get_icon("rocket", 15)}<span>Open project</span></button>')
        else:
            title, text = "Evaluation pending", (
                f"<b>{escape(badge_title)}</b> has no marks yet. They appear here once you submit your deliverables and your mapped reviewer has assessed them.")
            btn = (f'<button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction(\'nav_to_submit_badge\', \'{sid}\')">'
                   f'{get_icon("arrow_right", 15)}<span>Open badge</span></button>')
        sheet_content = f"""
        <div class="ms-empty">
            <span class="ms-empty-ico">{get_icon("clipboard", 26)}</span>
            <div class="ms-empty-title" role="heading" aria-level="3">{title} &middot; {escape(badge_code)}</div>
            <p>{text}</p>
            {btn}
        </div>"""

    return f"""
    <div class="ms-page" data-live-sync="marksheet">
        <h2 class="ms-page-title">Official Assessment Marksheets</h2>
        {toolbar}
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
            status_pill = '<span class="status-pill" style="font-size:0.6875rem; font-weight:800; padding:4px 10px; background:#047857; color:#FFFFFF; border-radius:var(--radius-xs); display:inline-flex; align-items:center; gap:4px;">&#10003; Approved</span>'
            action_btn = f"""
            <button type="button" class="btn-metal btn-sm" style="font-size:0.75rem; padding:6px 14px; white-space:nowrap;" onclick="window.StarAppBridge.dispatchAction('nav_to_submit_badge', '{ext.badge_id}')">
                Submit Deliverable &rarr;
            </button>
            """
        elif ext.status == "rejected":
            status_pill = '<span class="status-pill" style="font-size:0.6875rem; font-weight:800; padding:4px 10px; background:#EF4444; color:#FFFFFF; border-radius:var(--radius-xs); display:inline-flex; align-items:center; gap:4px;">&#10005; Rejected</span>'
            action_btn = f"""
            <button type="button" class="btn-secondary btn-sm" style="font-size:0.75rem; padding:6px 14px; white-space:nowrap;" onclick="window.StarAppBridge.dispatchAction('nav_to_submit_badge', '{ext.badge_id}')">
                Submit Deliverable
            </button>
            """
        else:
            status_pill = '<span class="status-pill" style="font-size:0.6875rem; font-weight:800; padding:4px 10px; background:#F59E0B; color:#451A03; border-radius:var(--radius-xs); display:inline-flex; align-items:center; gap:4px;">&#9203; Pending Review</span>'
            action_btn = '<span style="font-size:0.75rem; color:var(--frost-navy-50); font-weight:600; font-style:italic;">Awaiting Mentor</span>'

        feedback_html = ""
        if ext.guardian_response:
            feedback_html = f"""
            <div style="margin-top:6px; font-size:0.75rem; padding:6px 10px; background:rgba(23,52,92,0.05); border-left:3px solid var(--deep-frozen-midnight); border-radius:var(--radius-xs); color:var(--frost-navy);">
                <strong>Guardian Note:</strong> {escape(ext.guardian_response)}
            </div>
            """

        req_rows.append(f"""
        <tr style="border-bottom:1px solid var(--icy-steel-30); transition:background 0.15s ease;">
            <td style="padding:14px 16px; vertical-align:top;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <span style="font-family:var(--font-family-mono); font-size:0.6875rem; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">{escape(b_code)}</span>
                    <strong style="font-size:0.84375rem; color:var(--frost-navy);">{escape(b_title)}</strong>
                </div>
                <div style="font-size:0.75rem; color:var(--frost-navy-75); line-height:1.4; max-width:420px;">
                    <span style="color:var(--frost-navy-50);">Reason:</span> {escape(ext.reason)}
                </div>
                {feedback_html}
            </td>
            <td style="padding:14px 16px; vertical-align:middle; font-family:var(--font-family-mono); font-size:0.78125rem; color:var(--frost-navy-75); white-space:nowrap;">
                {escape(ext.current_deadline)}
            </td>
            <td style="padding:14px 16px; vertical-align:middle; font-family:var(--font-family-mono); font-size:0.8125rem; font-weight:800; color:var(--deep-frozen-midnight); white-space:nowrap;">
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
                    <p style="font-size:0.84375rem; color:var(--frost-navy-50); margin:0;">Request scheduling adjustments for active milestones and track evaluations in real-time.</p>
                </div>
            </div>
        </div>

        <!-- Vertically Stacked Layout: Form on top, Submitted requests below -->
        <div style="display:flex; flex-direction:column; gap:24px;">
            <!-- 1. Request Deadline Extension Container (Top) -->
            <div class="liquid-submission-portal" style="padding:28px 32px;">
                <div style="margin-bottom:18px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px;">
                    <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">Request Deadline Extension</h3>
                    <div style="font-size:0.78125rem; color:var(--frost-navy-50);">Choose an in-progress milestone and specify a realistic engineering rationale for mentor review.</div>
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
                            <button type="submit" class="btn-metal" style="height:44px; padding:0 24px; font-size:0.84375rem; font-weight:700;">
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
                        <div style="font-size:0.78125rem; color:var(--frost-navy-50);">Requested milestone extensions, live status, and necessary actions.</div>
                    </div>
                    <span style="font-size:0.75rem; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.06); padding:4px 10px; border-radius:var(--radius-xs);">
                        {len(extensions)} Total Request{"s" if len(extensions) != 1 else ""}
                    </span>
                </div>

                <div style="overflow-x:auto;">
                    <table style="width:100%; border-collapse:collapse; text-align:left;">
                        <thead>
                            <tr style="border-bottom:1.5px solid var(--icy-steel); background:rgba(234,244,255,0.4);">
                                <th style="padding:10px 16px; font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">Milestone & Details</th>
                                <th style="padding:10px 16px; font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">Current Cutoff</th>
                                <th style="padding:10px 16px; font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">Proposed Cutoff</th>
                                <th style="padding:10px 16px; font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; text-align:center;">Status</th>
                                <th style="padding:10px 16px; font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; text-align:right;">Action</th>
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
                <p style="font-size:0.84375rem; line-height:1.5; color:var(--frost-navy); margin-top:8px;">{escape(ann.message)}</p>
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
                    <p style="font-size:0.8125rem; color:var(--frost-navy-50); margin:2px 0 0 0;">Notices and schedule updates broadcasted by Academy Leadership.</p>
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
            <td style="font-family:var(--font-family-mono); font-size:0.75rem; white-space:nowrap;">{escape(ist_plain(act.timestamp, True))}</td>
            <td>{render_status_pill(act.event_type)}</td>
            <td>
                <div style="font-weight:700;">{escape(humanize_internal_ids(act.summary))}</div>
                <div style="font-size:0.75rem; color:var(--frost-navy-50);">{escape(humanize_internal_ids(act.details))}</div>
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
                        <th>Timestamp (IST)</th>
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
    expired_cnt = len([r for r in requests if r.get("assignment_status") == "expired" and r.get("workflow_status") not in ("approved", "returned")])

    history_records = store.get_badge_review_history(reviewer_id=current_user.id) if hasattr(store, "get_badge_review_history") else []
    history_cnt = len(history_records)

    is_history = (active_tab == "history")
    status_options = [
        ("all", f"All Requests ({all_cnt})"),
        ("pending_review", f"Pending Review ({pending_cnt})"),
        ("approved", f"Approved Badges ({approved_cnt})"),
        ("returned", f"Returned ({returned_cnt})"),
        ("expired", f"Expired ({expired_cnt})"),
    ]
    status_opts = "".join(
        f'<option value="{val}"{" selected" if val == active_tab else ""}>{label}</option>' for val, label in status_options
    )
    if is_history:
        # while the history is open the dropdown reads "Review History & Audit"; picking a status leaves the history
        status_opts = f'<option value="history" selected hidden>Review History &amp; Audit ({history_cnt})</option>' + status_opts
    history_target = "all" if is_history else "history"

    tools_html = f"""
    <div class="rr-tools">
        <div class="liquid-select-wrapper rr-select-wrap">
            <select id="rr-status-filter-select" class="liquid-glass-control liquid-glass-select ba-toolbar-select"
                    aria-label="Filter requests by status"
                    onchange="window.StarAppBridge.dispatchAction('filter_cosmo_requests', this.value)">
                {status_opts}
            </select>
        </div>
        <button type="button" id="rr-history-toggle-btn" class="ba-history-btn{" is-active" if is_history else ""}"
                title="{'Back to the requests' if is_history else 'Every approve / return / edit / expiry you made'}"
                onclick="window.StarAppBridge.dispatchAction('filter_cosmo_requests', '{history_target}')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>Review History &amp; Audit ({history_cnt})</span>
        </button>
        <div class="ba-search-wrap rr-search-wrap">
            <span class="ba-search-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
            </span>
            <input type="text" id="rr-search-input" class="ba-search-input" aria-label="Search requests"
                   placeholder="Search badge, code, skill" value="{escape(search_query)}"
                   oninput="window.StarAppBridge.debouncedDispatch('search_cosmo_requests', this.value)">
        </div>
    </div>
    """

    user_band = getattr(current_user, "band", "B2")
    user_track = getattr(current_user, "learning_track", "Engineer")

    # Render request cards or history view
    cards_html = []

    if active_tab == "history":
        history_rows = []
        q = (search_query or "").strip().lower()
        shown_history = [
            h for h in history_records
            if not q or any(q in str(h.get(k, "") or "").lower() for k in ("badge_title", "badge_code", "target_band", "taxonomy_tree", "notes", "event_type"))
        ]
        for h in shown_history:
            ev_type = h.get("event_type", "")
            if ev_type == "approved":
                ev_pill = '<span class="status-pill status-approved" style="font-size:0.6875rem; font-weight:700;">Authorized & Approved</span>'
            elif ev_type == "returned":
                ev_pill = '<span class="status-pill status-rejected" style="font-size:0.6875rem; font-weight:700;">Returned with Feedback</span>'
            elif ev_type == "edited":
                ev_pill = '<span class="status-pill status-warning" style="font-size:0.6875rem; font-weight:700;">Badge Edited</span>'
            elif ev_type == "review_expired":
                ev_pill = '<span class="status-pill status-warning" style="font-size:0.6875rem; font-weight:700;">Review Window Ended</span>'
            elif ev_type == "reviewer_cancelled":
                ev_pill = '<span class="status-pill status-rejected" style="font-size:0.6875rem; font-weight:700;">Review Withdrawn</span>'
            else:
                ev_pill = '<span class="status-pill status-active" style="font-size:0.6875rem; font-weight:700;">Review Dispatched</span>'

            history_rows.append(f"""
            <tr style="border-bottom:1px solid var(--icy-steel-25);">
                <td style="padding:14px 16px;">
                    <div style="font-weight:700; color:var(--frost-navy); font-size:0.8125rem;">{escape(h.get('badge_title', ''))}</div>
                    <div style="font-family:var(--font-family-mono); font-size:0.71875rem; color:var(--deep-frozen-midnight);">{escape(h.get('badge_code', ''))}</div>
                </td>
                <td style="padding:14px 16px;">
                    <span style="font-family:var(--font-family-mono); font-weight:800; font-size:0.6875rem; background:var(--frost-mist); color:var(--deep-frozen-midnight); padding:3px 8px; border-radius:var(--radius-xs);">BAND {escape(h.get('target_band', 'B1'))}</span>
                </td>
                <td style="padding:14px 16px; font-size:0.71875rem; color:var(--frost-navy-75); max-width:240px; line-height:1.4;">
                    {escape(h.get('taxonomy_tree', ''))}
                </td>
                <td style="padding:14px 16px; text-align:center;">
                    {ev_pill}
                </td>
                <td style="padding:14px 16px; font-size:0.75rem; font-weight:600; color:var(--frost-navy);">
                    {escape(h.get('formatted_timestamp', ''))}
                </td>
                <td style="padding:14px 16px; font-size:0.71875rem; color:var(--frost-navy-75); max-width:220px;">
                    {escape(h.get('notes') or 'Action recorded.')}
                </td>
                <td style="padding:14px 16px; text-align:right;">
                    <button type="button" class="btn-secondary btn-sm" style="font-size:0.6875rem; font-weight:700;"
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
                        <tr style="background:linear-gradient(135deg, rgba(23,52,92,0.06) 0%, rgba(157,183,213,0.12) 100%); border-bottom:1.5px solid var(--icy-steel-30); font-size:0.6875rem; text-transform:uppercase; letter-spacing:0.5px; color:var(--frost-navy-75);">
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
                        {"".join(history_rows) if history_rows else '<tr><td colspan="7" style="padding:32px; text-align:center; color:var(--frost-navy-50);">' + ('No history matches your search.' if q else 'No review actions recorded in your history yet.') + '</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
        """)
    else:
        check_ic = get_icon("check", 12)
        for r in filtered:
            b_id = escape(r.get("id", ""))
            wf_status = r.get("workflow_status", "pending_review")
            a_status = r.get("assignment_status") or ""
            dec_notes = escape(r.get("decision_notes") or "")
            decided = format_utc_stamp(r.get("decided_at"))
            if wf_status == "approved" or a_status == "approved":
                kind = "approved"
            elif wf_status == "returned" or a_status == "returned":
                kind = "returned"
            elif a_status == "expired":
                kind = "expired"
            else:
                kind = "pending"

            if kind == "approved":
                state_html = f'<span class="lg-sb-state is-reviewed">{check_ic} Approved</span>'
                action_label, action_cls = "View Badge", "btn-secondary"
            elif kind == "returned":
                state_html = '<span class="lg-sb-state is-returned">Returned</span>'
                action_label, action_cls = "View Badge", "btn-secondary"
            elif kind == "expired":
                state_html = '<span class="lg-sb-state is-expired">Window ended</span>'
                action_label, action_cls = "View Badge", "btn-secondary"
            else:
                state_html = '<span class="lg-sb-state is-pending">Needs your review</span>'
                action_label, action_cls = "Review Badge", "btn-metal"

            # The line under the chips: the live countdown while it is open; the decision, like the history rows, once it is not.
            if kind == "pending":
                slot = render_badge_review_timer(r.get("review_due_at")) or '<span class="lg-sb-note">Review due ' + escape((r.get("review_due_at") or "")[:10]) + "</span>"
            else:
                label = {"approved": "Approved", "returned": "Returned with feedback", "expired": "Review window ended - badge kept as it is"}[kind]
                slot = f'<div class="lg-sb-decision is-{kind}"><strong>{label}</strong>{(" &middot; " + escape(decided)) if decided else ""}</div>'
            notes_html = (f'<div class="lg-sb-feedback{" is-ok" if kind == "approved" else ""}"><strong>{"Your notes" if kind == "approved" else "Your feedback"}:</strong> {dec_notes}</div>'
                          if dec_notes and kind in ("approved", "returned") else "")
            tree = render_taxonomy_hierarchy_tree(r.get("power"), r.get("capability"), r.get("skill"), compact=True)

            cards_html.append(f"""
            <div class="lg-saved-badge-card is-clickable" role="button" tabindex="0"
                 onclick="window.StarAppBridge.dispatchAction('open_reviewer_badge_review', '{b_id}')"
                 onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();this.click();}}">
                <div class="lg-sb-title is-request" role="heading" aria-level="4">{escape(r.get("title", ""))}</div>
                {state_html}
                <div class="lg-sb-meta">
                    {tree}
                    <span class="lg-sb-chip is-band">Band {escape(r.get("target_band", "B1"))}</span>
                </div>
                <div class="lg-sb-extra">
                    {slot}
                    {notes_html}
                </div>
                <div class="lg-sb-actions">
                    <button type="button" class="{action_cls} btn-sm">{action_label} &rarr;</button>
                </div>
            </div>
            """)
        if cards_html:
            cards_html = [f'<div class="lg-allot-grid">{"".join(cards_html)}</div>']

    empty_html = f"""
    <div class="liquid-glass-card" style="padding:48px 24px; text-align:center; border-radius:var(--radius-md); border:1.5px dashed var(--icy-steel-40);">
        <div style="width:48px; height:48px; margin:0 auto 12px; border-radius:50%; background:rgba(23,52,92,0.06); display:flex; align-items:center; justify-content:center; color:var(--deep-frozen-midnight);">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        </div>
        <h3 style="font-size:1rem; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">No Review Requests in this Queue</h3>
        <p style="font-size:0.8125rem; color:var(--frost-navy-50); margin:0; max-width:440px; margin:0 auto;">
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
        dates = req.get("review_dates") or []
        if len(dates) > 3:
            dates_str = f"{dates[0]} → {dates[-1]} ({len(dates)} Working Days)"
        else:
            dates_str = " → ".join(dates) if dates else "Schedule Pending"
        sent_ts = req.get("sent_at") or ""
        sent_at = sent_ts[:10] if sent_ts else ""

        if r_status == "accepted":
            status_badge = f'<span class="status-pill status-approved" style="display:inline-flex; align-items:center; gap:4px; font-size:0.6875rem; font-weight:800; background:rgba(5,150,105,0.12); color:#047857; border:1px solid rgba(5,150,105,0.3);">{get_icon("check", 12)} Request Accepted</span>'
            action_btns = f'<button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction(\'reject_mapping_request\', \'{r_id}\')" style="display:inline-flex; align-items:center; gap:4px; font-size:0.6875rem; color:#DC2626; border-color:rgba(220,38,38,0.3); font-weight:700;">{get_icon("x", 12)} Decline / Revoke</button>'
            card_cls = "is-accepted"
        elif r_status == "rejected" and req.get("expired"):
            status_badge = f'<span class="status-pill status-rejected" style="display:inline-flex; align-items:center; gap:4px; font-size:0.6875rem; font-weight:800; background:rgba(239,68,68,0.12); color:#DC2626; border:1px solid rgba(239,68,68,0.3);">{get_icon("clock", 12)} Request Expired</span>'
            action_btns = '<span class="rq-resp is-bad">No reply within 24 hours &mdash; ask the Guardian to resend this request.</span>'
            card_cls = "is-declined"
        elif r_status == "rejected":
            status_badge = f'<span class="status-pill status-rejected" style="display:inline-flex; align-items:center; gap:4px; font-size:0.6875rem; font-weight:800; background:rgba(239,68,68,0.12); color:#DC2626; border:1px solid rgba(239,68,68,0.3);">{get_icon("x", 12)} Request Declined</span>'
            action_btns = f'<button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction(\'accept_mapping_request\', \'{r_id}\')" style="display:inline-flex; align-items:center; gap:4px; font-size:0.6875rem; font-weight:700;">{get_icon("check", 12)} Accept Request</button>'
            card_cls = "is-declined"
        else:
            status_badge = ""        # the countdown alone says it is waiting for an answer
            action_btns = f'''<button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('accept_mapping_request', '{r_id}')" style="display:inline-flex; align-items:center; gap:4px; font-size:0.71875rem; padding:6px 14px; background:#059669; border-color:#059669; color:#fff; font-weight:800;">{get_icon("check", 12)} Accept & Confirm</button>
            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('reject_mapping_request', '{r_id}')" style="display:inline-flex; align-items:center; gap:4px; font-size:0.71875rem; padding:6px 12px; color:#DC2626; border-color:rgba(220,38,38,0.3); font-weight:700;">{get_icon("x", 12)} Decline</button>'''
            card_cls = "is-pending"

        # Cosmonauts are not the reviewer's business until they are really theirs: the request is accepted, the Guardian has
        # completed the mapping for this reviewer AND the badge is published. Until then no name (or count) is rendered at all.
        people_block = ""
        inv_badge = store.get_badge(req.get("badge_id", "")) if req.get("badge_id") else None
        if r_status == "accepted" and inv_badge is not None and getattr(inv_badge, "is_published", False):
            mapped_ids = sorted(store.get_reviewer_mapped_cosmonaut_ids(current_user.id, inv_badge.id))
            if mapped_ids:
                names = []
                for cid in mapped_ids:
                    u = store.get_user_by_id(cid)
                    names.append(u.name if u else cid)
                people = "".join(
                    f'<span class="inv-person"><span class="inv-av">{escape(n[:1].upper())}</span>{escape(n)}</span>' for n in names[:3]
                ) + (f'<span class="inv-person is-more">+{len(names) - 3} more</span>' if len(names) > 3 else "")
                people_block = f"""
                <div class="inv-block">
                    <div class="inv-lbl">{get_icon("users", 14)} Mapped Cosmonauts <span class="inv-count">{len(names)}</span></div>
                    <div class="inv-people">{people}</div>
                </div>"""
        win_start, win_end = format_short_date(dates[0]) if dates else "", format_short_date(dates[-1]) if dates else ""
        if win_start and win_end and win_start != win_end:
            window_html = f'<span class="inv-dates">{escape(win_start)} <span class="inv-arrow">&rarr;</span> {escape(win_end)}</span><span class="inv-pill">{len(dates)} working day{"" if len(dates) == 1 else "s"}</span>'
        elif win_start:
            window_html = f'<span class="inv-dates">{escape(win_start)}</span><span class="inv-pill">1 working day</span>'
        else:
            window_html = '<span class="inv-dates is-muted">Schedule pending</span>'

        m_req_cards.append(f"""
        <div class="inv-card {card_cls}">
            <div class="inv-head">
                <div class="inv-title-row">
                    <div class="inv-title" role="heading" aria-level="4">{escape(badge_name)}</div>
                    <span class="inv-band">BAND {escape(band)}</span>
                </div>
                <div class="inv-status-row">
                    {status_badge}
                    {render_request_timer(req, "Respond within")}
                </div>
            </div>
            <div class="inv-body">
                <div class="inv-block">
                    <div class="inv-lbl">{get_icon("calendar", 14)} Review window</div>
                    <div class="inv-window">{window_html}</div>
                </div>{people_block}
            </div>
            <div class="inv-actions">
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
            <span class="status-pill status-active" style="font-weight:700; font-size:0.6875rem;">
                {len(mapping_reqs)} Review Assignment(s)
            </span>
        </div>
        <div>
            {('<div class="lg-allot-grid">' + ''.join(m_req_cards) + '</div>') if m_req_cards else "<div style='text-align:center; padding:32px 20px; color:var(--frost-navy-50); font-size:0.8125rem; background:rgba(255,255,255,0.6); border:1px dashed var(--icy-steel-50); border-radius:var(--radius-sm);'>No pending reviewer mapping requests. When a Guardian selects you in the Mapping Matrix, assignments will appear here.</div>"}
        </div>
    </div>
    """

    return f"""
    <div>
        <!-- The page title is shown in the Back-button row (hoisted); no band chip / track / Back / Dashboard block here -->
        <h1 style="font-size:1.85rem; font-weight:800; color:var(--frost-navy); letter-spacing:-0.5px; margin:0 0 4px 0;">Review Requests</h1>

        <!-- Section 1: Badge Approval Requests -->
        <div class="liquid-glass-card" style="padding:22px; margin-bottom:24px;">
            <div class="rr-head">
                <h3 class="rr-head-title">Badge Approval Requests</h3>
                {tools_html}
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
# 6.12A REVIEWER BADGE REVIEW PAGE (Review Requests -> one badge)
# ==============================================================================

def render_reviewer_badge_review(
    badge: Badge,
    current_user: User,
    request_row: Optional[Dict[str, Any]] = None,
    is_editing: bool = False,
    can_edit: bool = False,
) -> str:
    """
    The page a reviewer lands on when they open a requested badge. It shows the REAL badge in exactly the structured
    format the Guardian authored it in (views_badge_document.render_badge_document) and lets the reviewer correct it
    (Edit -> Apply Changes writes straight to the badge, so the Guardian sees the same edits) and then approve it or
    return it with feedback. `can_edit` is the server's verdict (awaiting review + assigned reviewer); the page only
    reflects it - every action re-checks on the server.
    """
    from starapp.badge_generator import structured_badge_from_row

    request_row = request_row or {}
    data = structured_badge_from_row(badge)
    doc = split_badge_document(data)
    status = getattr(badge, "workflow_status", "") or "pending_review"
    band = getattr(badge, "target_band", "") or "B1"

    window_ended = (request_row.get("assignment_status") == "expired") and status not in ("approved", "returned")
    if status == "approved":
        pill = '<span class="status-pill status-approved">Approved</span>'
        strip_text = "You approved this badge. It is final - the Guardian can now allot it to Cosmonauts. You are viewing it read-only."
    elif status == "returned":
        pill = '<span class="status-pill status-rejected">Returned for Changes</span>'
        strip_text = "You returned this badge to the Guardian with feedback. You are viewing it read-only."
    elif window_ended:
        pill = '<span class="status-pill status-warning">Review Window Ended</span>'
        strip_text = "The 48-hour review window ended without a decision, so the badge was kept as it is (with any edits you had applied). You are viewing it read-only."
    else:
        pill = '<span class="status-pill status-warning">Pending Your Review</span>'
        strip_text = "Read the badge through for mistakes. Fix anything that is wrong with Edit, then approve it or return it with feedback."

    earn_strip = f"""
            <div style="display:flex; align-items:flex-start; gap:12px;">
                <span class="cb-section-icon" style="background:rgba(37,99,235,0.12); color:#1D4ED8;">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                </span>
                <div>
                    <div class="cb-section-title">Review This Badge</div>
                    <div style="font-size:0.90625rem; font-weight:600; color:var(--frost-navy); margin-top:3px;">{escape(strip_text)}</div>
                </div>
            </div>
            <div>{pill}</div>
    """

    apply_js = "window.StarAppBridge.saveReviewerBadgeEdits()"
    toggle_js = "window.StarAppBridge.dispatchAction('toggle_reviewer_badge_edit')"
    cancel_js = toggle_js
    header_actions = (
        render_badge_edit_controls(is_editing, toggle_js, apply_js, cancel_js)
        if (can_edit or is_editing) else ""
    )
    footer_bar = (
        render_badge_edit_footer_bar("Editing the badge \u2014 Apply Changes saves it for you and the Guardian", apply_js, cancel_js)
        if is_editing else ""
    )

    b_id = escape(badge.id)
    decision_bar = ""
    if can_edit and not is_editing and status == "pending_review":
        decision_bar = f"""
        <div class="cb-selection-bar rv-decision-bar" style="margin-bottom:24px; justify-content:flex-end;">
            <span style="font-size:0.84375rem; font-weight:700; color:var(--frost-navy); margin-right:auto;">Finished checking? Approve the badge, or send it back to the Guardian with feedback.</span>
            <button type="button" class="btn-secondary btn-sm" style="font-size:0.8125rem; font-weight:700; padding:8px 16px; color:#B91C1C; border-color:rgba(220,38,38,0.4);"
                    onclick="window.StarAppBridge.dispatchAction('confirm_return_badge', '{b_id}')">Return with Feedback</button>
            <button type="button" class="btn-metal btn-sm" style="font-size:0.8125rem; font-weight:800; padding:8px 18px; display:inline-flex; align-items:center; gap:6px; background:linear-gradient(135deg, #10B981 0%, #059669 100%); border-color:#059669; color:#fff;"
                    onclick="window.StarAppBridge.dispatchAction('confirm_approve_badge', '{b_id}')">{get_icon("check", 14)} Approve Badge</button>
        </div>
        """

    creator = escape(request_row.get("creator_name") or "the Guardian")
    assigned_ts = request_row.get("assigned_at") or ""
    due_ts = request_row.get("review_due_at") or ""
    meta_bits = [f"Sent by <strong>{creator}</strong>"]
    if assigned_ts:
        meta_bits.append(f"on <strong>{escape(format_short_date(assigned_ts))}</strong>")
    timer_html = render_badge_review_timer(due_ts) if (status == "pending_review" and not window_ended) else ""
    decided = format_utc_stamp(request_row.get("decided_at"))
    if decided and status in ("approved", "returned") or (decided and window_ended):
        meta_bits.append(f"&bull; {'closed' if window_ended else status} <strong>{escape(decided)}</strong>")
    read_only_chip = "" if (can_edit or is_editing) else '<span class="rv-readonly-chip">Read-only</span>'
    notes = request_row.get("decision_notes") or ""
    notes_html = (f'<div class="lg-sb-feedback" style="margin-top:10px;"><strong>Your feedback:</strong> {escape(notes)}</div>'
                  if notes and status == "returned" else "")

    document = render_badge_document(
        title=doc["title"], description=doc["description"], outcomes=doc["outcomes"],
        practice_prompt=doc["practice_prompt"], resources_prompt=doc["resources_prompt"], topics=doc["topics"],
        skill=getattr(badge, "skill", ""), capability=getattr(badge, "capability", ""), power=getattr(badge, "power", ""),
        band=band, is_editing=is_editing,
        header_actions_html=header_actions, footer_bar_html=footer_bar,
        earn_strip_html=earn_strip, show_topic_progress=False,
    )

    return f"""
    <div class="rv-badge-review" style="max-width:1280px; margin:0 auto;">
        <h1 style="font-size:1.85rem; font-weight:800; color:var(--frost-navy); letter-spacing:-0.5px; margin:0 0 4px 0;">Badge Review</h1>

        <div class="liquid-glass-card rv-review-meta" style="padding:14px 20px; margin-bottom:18px; display:flex; align-items:center; flex-wrap:wrap; gap:10px 14px;">
            <span style="font-family:var(--font-family-mono); font-size:0.75rem; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:4px 10px; border-radius:var(--radius-xs);">{escape(badge.code)}</span>
            <span style="font-family:var(--font-family-mono); font-size:0.75rem; font-weight:800; background:var(--frost-mist); color:var(--deep-frozen-midnight); padding:4px 10px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30);">BAND {escape(band)}</span>
            {pill}
            {read_only_chip}
            {timer_html}
            <span style="font-size:0.8125rem; font-weight:600; color:var(--frost-navy);">{" ".join(meta_bits)}</span>
            {notes_html}
        </div>

        {document}
        {decision_bar}
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


def _nice_window_label(label: Any) -> str:
    """'2026-11-18 -> 2026-11-19 -> 2026-11-20' / '2026-11-18 -> 2026-11-24 (5 Days)' -> '18 Nov -> 20 Nov 2026 - 3 days' (anything else as-is)."""
    import re as _re
    text = str(label or "")
    iso = _re.findall(r"\d{4}-\d{2}-\d{2}", text)
    if not iso:
        return text
    m = _re.search(r"\((\d+)\s*Days?\)", text)
    n = int(m.group(1)) if m else len(iso)
    if len(iso) == 1:
        return format_short_date(iso[0])
    same_year = iso[0][:4] == iso[-1][:4]
    first = format_short_date(iso[0])[:-5] if same_year else format_short_date(iso[0])
    return f"{first} → {format_short_date(iso[-1])} · {n} days"


def _render_review_deliverables_tray(sub: ProjectSubmission) -> str:
    """Renders compact submitted deliverable artifact pills for Upcoming & Completed review cards."""
    pdf_name = getattr(sub, "pdf_name", "") or (sub.file_name if getattr(sub, "submission_type", "") == "pdf" else "") or "Report.pdf"
    code_name = getattr(sub, "code_name", "") or (sub.file_name if getattr(sub, "submission_type", "") == "code" else "") or "solution.py"
    github_url = getattr(sub, "github_url", "") or (sub.payload if getattr(sub, "submission_type", "") == "github" else "") or ""
    repo_lbl = github_url.split("/")[-1] if "/" in github_url else (github_url or "GitHub Repo")
    sub_dt = format_ist(getattr(sub, "submitted_at", "") or "")

    pdf_ic = get_icon("file_text", 12, "margin-right:4px; color:#D32F2F;")
    code_ic = get_icon("code", 12, "margin-right:4px; color:var(--deep-frozen-midnight);")
    gh_ic = get_icon("github", 12, "margin-right:4px; color:var(--frost-navy);")

    gh_pill = (
        f'<span style="display:inline-flex; align-items:center; font-size:0.6875rem; font-weight:700; color:var(--frost-navy); background:rgba(234,244,255,0.9); border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{gh_ic}{escape(repo_lbl)}</span>'
        if github_url else ""
    )
    return f"""
    <div style="background:rgba(241,245,249,0.75); border:1px solid var(--icy-steel-30); border-radius:8px; padding:8px 12px; margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:5px;">
            <span style="font-size:0.625rem; font-weight:800; text-transform:uppercase; letter-spacing:0.45px; color:var(--frost-navy-50);">Submitted Deliverables &bull; Attempt #{getattr(sub, 'attempt_number', 1)}</span>
            {f'<span style="font-size:0.65625rem; font-family:var(--font-family-mono); color:var(--frost-navy-50);">{escape(sub_dt)}</span>' if sub_dt else ''}
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
            <span style="display:inline-flex; align-items:center; font-size:0.6875rem; font-weight:700; color:var(--frost-navy); background:#FFFFFF; border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{pdf_ic}{escape(pdf_name)}</span>
            <span style="display:inline-flex; align-items:center; font-size:0.6875rem; font-weight:700; color:var(--frost-navy); background:#FFFFFF; border:1px solid var(--icy-steel-40); padding:3px 9px; border-radius:6px;">{code_ic}{escape(code_name)}</span>
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
    for done_item in completed_entries:
        done_item["_done"] = True
    badge_groups = {}
    for item in upcoming_entries + completed_entries:
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

    # ---- Upcoming reviews: one glass card per badge, its mapped cosmonauts below it in the same connected-dot tree as the
    # Assessment Dashboard (asm-tree-cosmo-list / asm-tree-cosmo-branch / asm-elbow).
    def _pill(tone: str, text: str, ico: str = "") -> str:
        return f'<span class="rv-pill is-{tone}">{ico}<span>{text}</span></span>'

    upcoming_cards_html = []
    completed_cards_html = []
    for b_id, bg in badge_groups.items():
        cadets_list = bg["cadets"]
        num_cadets = len(cadets_list)
        badge_obj = bg.get("badge")

        if expanded_badge_id == b_id:
            is_expanded = True
        elif expanded_badge_id == "":
            is_expanded = False
        elif expanded_badge_id is None:
            is_expanded = True
        else:
            is_expanded = False

        b_prompt = store.get_reviewer_project_prompts(badge_id=b_id, reviewer_id=current_user.id) if store else []

        cadet_branches = []
        n_project_sent = 0
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
            proj_sent = bool(assigned_proj and getattr(assigned_proj, "status", "") in ("released", "sent"))
            if proj_sent:
                n_project_sent += 1

            # The ONE action on a cosmonaut row: Assessment. Disabled until the cosmonaut has submitted (a retake waits for the new attempt);
            # then it opens the workspace where the reviewer sees the deliverables and allocates the marks.
            can_assess = bool(sub and getattr(sub, "status", "") not in ("retake_required", "resubmission_requested"))
            earned_row = bool(item.get("_done") or (g_asm and g_asm.decision in ("approve", "approved")))
            if earned_row:
                final_asm = g_asm or rev_asm
                status_pill = _pill("green", "Badge earned" + (f" - {final_asm.total_marks:.1f}/50 ({final_asm.percentage:.1f}%)" if final_asm else ""), get_icon("award", 12))
            elif sub and getattr(sub, "status", "") in ("retake_required", "resubmission_requested"):
                status_pill = _pill("red", "Retake required - waiting for a new submission", get_icon("clock", 12))
            elif rev_asm:
                status_pill = _pill("indigo", f"Evaluated {rev_asm.total_marks:.1f}/50 ({rev_asm.percentage:.1f}%)", get_icon("check", 12))
            elif sub:
                status_pill = _pill("green", "Deliverables submitted - ready for marks", get_icon("check", 12))
            elif proj_sent:
                status_pill = _pill("blue", "Project sent - waiting for deliverables", get_icon("rocket", 12))
            elif assigned_proj and getattr(assigned_proj, "status", "") == "draft":
                status_pill = _pill("amber", "Draft saved", get_icon("edit", 12))
            else:
                status_pill = _pill("amber", "Project pending", get_icon("clock", 12))
            if can_assess:
                action_btn = (f'<button type="button" class="btn-metal btn-sm rv-act rv-assess" onclick="window.StarAppBridge.dispatchAction(\'open_reviewer_assessment_page\', \'{escape(sub.id)}\')">'
                              f'{get_icon("award" if rev_asm else "edit", 13)}<span>Assessment</span></button>')
            else:
                tip = "Available again once the cosmonaut submits the new attempt" if sub else "Available once the cosmonaut submits their deliverables"
                action_btn = (f'<button type="button" class="btn-secondary btn-sm rv-act rv-assess is-locked" disabled aria-disabled="true" title="{tip}">'
                              f'{get_icon("lock", 13)}<span>Assessment</span></button>')

            proj_line = (f'<div class="rv-sub-line"><span class="rv-sub-lbl">Project</span> {escape(assigned_proj.title)}</div>'
                         if assigned_proj and getattr(assigned_proj, "title", "") else "")
            eval_line = ""
            if (rev_asm or g_asm) and not earned_row:      # an earned row's pill already carries the final score
                bits = []
                if rev_asm:
                    bits.append(f"Your evaluation <b>{rev_asm.total_marks:.1f}/50</b> " + render_recommendation_chip(reviewer_recommendation_key(rev_asm), "Recommended"))
                if g_asm:
                    bits.append(f"Guardian ({escape(g_asm.decision.replace('_', ' ').title())}) <b>{g_asm.total_marks:.1f}/50</b>")
                eval_line = f'<div class="rv-sub-line">{" &middot; ".join(bits)}</div>'
            # the badge header already shows the shared schedule; a cosmonaut row only repeats it when theirs differs
            own_schedule = ""
            if r_date != bg["review_date"] or deadline != bg["deadline"]:
                own_schedule = (f'<div class="rv-sub-line"><span class="rv-sub-lbl">Window</span> {escape(_nice_window_label(r_date))}</div>'
                                f'<div class="rv-sub-line"><span class="rv-sub-lbl">Deadline</span> <b class="rv-red">{escape(format_short_date(deadline) or deadline)}</b></div>')

            cadet_branches.append(f"""
                <div class="asm-tree-cosmo-branch">
                    <span class="asm-elbow" aria-hidden="true"></span>
                    <div class="asm-cosmonaut-card is-static is-wide">
                        <div class="asm-cosmo-identity">
                            <span class="asm-cosmo-avatar rv-avatar">{escape(c_avatar)}</span>
                            <div style="min-width:0;">
                                <div class="asm-cosmo-name">{escape(c_name)}</div>
                                <div class="asm-cosmo-chip-row">
                                    <span class="asm-cosmo-chip is-band">Band {escape(c_band)}</span>
                                    <span class="asm-cosmo-chip">{escape(c_track)}</span>
                                </div>
                            </div>
                        </div>
                        <div class="asm-cosmo-progress">
                            <div>{status_pill}</div>
                            {proj_line}
                            {eval_line}
                            {own_schedule}
                        </div>
                        <div class="asm-cosmo-action">
                            <button type="button" class="btn-secondary btn-sm rv-act" onclick="window.StarAppBridge.dispatchAction('open_reviewer_badge_timeline_modal', '{escape(b_id)}')">
                                {get_icon("calendar", 13)}<span>Timeline</span>
                            </button>
                            {action_btn}
                        </div>
                    </div>
                </div>""")

        n_pending_projects = num_cadets - n_project_sent
        group_done = bool(cadets_list) and all(i.get("_done") for i in cadets_list)
        if n_pending_projects <= 0:
            create_label, create_ico = "Edit Project", get_icon("edit", 14)
        else:
            create_label, create_ico = "Create Project", get_icon("rocket", 14)

        # the 72-hour project window starts when the Guardian publishes the badge
        timer_html = ""
        if n_pending_projects > 0 and badge_obj is not None:
            timer_html = render_project_window_timer(getattr(badge_obj, "published_at", ""), large=True)
        if n_pending_projects <= 0 and num_cadets:
            timer_html = f'<span class="rv-sent">{get_icon("check", 14)}<span>All projects sent</span></span>'
        window_cell = f'<div class="rv-fact is-timer"><div class="rv-fact-lbl">Project window</div><div class="rv-fact-val">{timer_html}</div></div>' if timer_html else ""
        if group_done:
            window_cell = f'<div class="rv-fact"><div class="rv-fact-lbl">Status</div><div class="rv-fact-val"><span class="rv-sent">{get_icon("award", 14)}<span>All badges earned</span></span></div></div>'
        create_btn_html = "" if group_done else (
            f'<button type="button" class="btn-metal btn-sm rv-create" onclick="window.StarAppBridge.dispatchAction(\'open_create_reviewer_project_modal\', \'{escape(b_id)}\')">'
            f'{create_ico}<span>{create_label}</span></button>')

        tree_html = (
            f'<div class="rv-tree"><div class="asm-tree-cosmo-list">{"".join(cadet_branches)}</div></div>'
            if is_expanded else ""
        )
        chevron = get_icon("chevron_up" if is_expanded else "chevron_down", 14)

        (completed_cards_html if group_done else upcoming_cards_html).append(f"""
        <div class="rv-badge-card">
            <div class="rv-badge-head" onclick="window.StarAppBridge.dispatchAction('toggle_reviewer_badge_expand', '{escape(b_id)}')">
                <div class="rv-badge-id">
                    <div class="rv-badge-title" role="heading" aria-level="3">{escape(bg["badge_title"])}</div>
                </div>
                <div class="rv-badge-facts">
                    <div class="rv-fact"><div class="rv-fact-lbl">Review window</div><div class="rv-fact-val">{escape(_nice_window_label(bg["review_date"]))}</div></div>
                    <div class="rv-fact"><div class="rv-fact-lbl">Submission deadline</div><div class="rv-fact-val rv-red">{escape(format_short_date(bg["deadline"]) or bg["deadline"])}</div></div>
                    {window_cell}
                </div>
                <div class="rv-badge-actions" onclick="event.stopPropagation();">
                    {create_btn_html}
                    <button type="button" class="btn-secondary btn-sm rv-toggle" onclick="window.StarAppBridge.dispatchAction('toggle_reviewer_badge_expand', '{escape(b_id)}')">
                        {get_icon("users", 14)}<span>{num_cadets} mapped cosmonaut{'s' if num_cadets != 1 else ''}</span>{chevron}
                    </button>
                </div>
            </div>
            {tree_html}
        </div>
        """)

    return f"""
    <div>
        <!-- The page title is shown in the Back-button row (hoisted); no band chip, role label or shortcut buttons here -->
        <h1 style="font-size:1.85rem; font-weight:800; color:var(--frost-navy); letter-spacing:-0.5px; margin:0 0 4px 0;">Badge Review Schedule</h1>

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
                {"".join(upcoming_cards_html) if upcoming_cards_html else "<div style='text-align:center; padding:36px 20px; color:var(--frost-navy-50); font-size:0.8125rem; background:rgba(255,255,255,0.6); border:1px dashed var(--icy-steel-50); border-radius:var(--radius-sm);'>No upcoming badge reviews scheduled. When a Guardian allocates badges to cadets and designates you as reviewer, they will appear here.</div>"}
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
                {"".join(completed_cards_html) if completed_cards_html else "<div style='text-align:center; padding:30px 20px; color:var(--frost-navy-50); font-size:0.8125rem; background:rgba(255,255,255,0.6); border:1px dashed var(--icy-steel-50); border-radius:var(--radius-sm);'>No completed badge evaluations on record yet.</div>"}
            </div>
        </div>
    </div>
    """


# ==============================================================================
# 6.13 REVIEWER ASSESSMENT OF CADET DELIVERABLES WORKSPACE
# ==============================================================================

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

    # Marks are final per attempt: once submitted the whole panel is read-only (a new attempt opens a new assessment).
    locked = existing_reviewer_asm is not None
    thr = float(getattr(badge, "passing_percentage", 70.0) or 70.0) if badge else 70.0
    rec_key = reviewer_recommendation_key(existing_reviewer_asm) if locked else ""
    if not rec_key:
        rec_key = "approve" if init_pct >= thr else "resubmission_requested"
    dis = " disabled" if locked else ""
    ro = " readonly" if locked else ""
    dec_css = {"approve": "is-approve", "resubmission_requested": "is-resubmit", "reject": "is-reject"}
    dec_buttons = "".join(
        f'<button type="button" role="radio" class="lg-dec-opt {dec_css[k]}{" is-on" if k == rec_key else ""}" aria-checked="{"true" if k == rec_key else "false"}" '
        f'data-value="{k}" data-cta="Submit Assessment" data-desc="{escape(REVIEWER_RECOMMENDATIONS[k]["desc"])}"{dis} onclick="window.StarAppBridge.setReviewDecision(this)">'
        f'<span class="lg-dec-ico">{get_icon(REVIEWER_RECOMMENDATIONS[k]["icon"], 16)}</span><span class="lg-dec-title">{REVIEWER_RECOMMENDATIONS[k]["label"]}</span></button>'
        for k in ("approve", "resubmission_requested", "reject"))
    dec_options = "".join(f'<option value="{k}"{" selected" if k == rec_key else ""}>{REVIEWER_RECOMMENDATIONS[k]["label"]}</option>' for k in ("approve", "resubmission_requested", "reject"))
    decision_block = f"""
                        <div>
                            <span class="lg-rubric-field-label" id="rubric-decision-label">Your recommendation to the Guardian</span>
                            <select id="rubric-decision" hidden data-auto="{0 if locked else 1}" data-thr="{thr:g}" aria-labelledby="rubric-decision-label">{dec_options}</select>
                            <div class="lg-dec-list" role="radiogroup" aria-labelledby="rubric-decision-label">{dec_buttons}</div>
                        </div>"""
    if locked:
        footer_html = (f'<div class="lg-rubric-locked">{get_icon("lock", 14)}<span>Marks submitted and locked. The Guardian now checks your '
                       f'recommendation and gives the final decision. A new assessment opens only if the cosmonaut makes a new attempt.</span></div>')
    else:
        footer_html = ('<button type="submit" class="btn-metal" style="width:100%; height:38px; font-size:0.8125rem; font-weight:800; letter-spacing:0.2px;">'
                       '<span id="rubric-submit-label">Submit Assessment</span> &rarr;</button>')

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
            <a href="{escape(pdf_payload)}" download="{escape(pdf_name)}" class="btn-secondary btn-sm" style="display:inline-flex; align-items:center; font-size:0.71875rem; text-decoration:none; padding:5px 12px;">
                {download_ic} Download PDF
            </a>
        </div>
        """
    elif selected_tab == "code":
        lines = code_payload.strip().split("\n")
        code_lines_html = []
        for l_num, line in enumerate(lines, 1):
            code_lines_html.append(
                f'<tr><td style="user-select:none; text-align:right; padding-right:14px; color:#5c7694; font-family:var(--font-family-mono); font-size:0.75rem; width:40px; border-right:1px solid #17345C;">{l_num}</td>'
                f'<td style="white-space:pre-wrap; word-break:break-all; font-family:var(--font-family-mono); font-size:0.78125rem; color:#EAF4FF; padding-left:14px;">{escape(line)}</td></tr>'
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
            <span style="font-size:0.71875rem; font-family:var(--font-family-mono); color:var(--frost-navy-50);">{escape(code_name)}</span>
            <button type="button" class="btn-secondary btn-sm" style="display:inline-flex; align-items:center; font-size:0.71875rem; padding:5px 12px;" onclick="window.StarAppBridge.copySourceCode();">
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
                    <div style="font-size:0.9375rem; font-weight:800; color:var(--frost-navy);">{escape(github_url.split('/')[-1] if '/' in github_url else 'GitHub Project Repository')}</div>
                    <div style="font-size:0.75rem; color:var(--frost-navy-50);">Version Controlled Delivery Artifact</div>
                </div>
            </div>
            <div style="margin-bottom:16px;">
                <label style="font-size:0.6875rem; font-weight:700; text-transform:uppercase; color:var(--frost-navy-50);">Repository URL:</label>
                <div style="margin-top:4px; font-family:var(--font-family-mono); font-size:0.75rem; background:rgba(23,52,92,0.06); padding:8px 12px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-50); word-break:break-all;">
                    {escape(github_url)}
                </div>
            </div>
            <a href="{escape(github_url)}" target="_blank" class="btn-metal" style="display:inline-flex; align-items:center; gap:6px; font-weight:700; font-size:0.78125rem; text-decoration:none; padding:8px 18px;">
                {expand_ic} Open Repository in New Tab
            </a>
        </div>
        """
        toolbar_extra = f"""
        <div>
            <a href="{escape(github_url)}" target="_blank" class="btn-secondary btn-sm" style="display:inline-flex; align-items:center; gap:5px; font-size:0.71875rem; text-decoration:none; padding:5px 12px;">
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
                        <button type="button" class="btn-secondary btn-sm" style="font-weight:700; font-size:0.71875rem; padding:4px 10px; display:inline-flex; align-items:center; gap:4px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_badge_reviews')">
                            {get_icon("chevron_left", 14)} Back to Badge Reviews
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
                        <div style="font-size:0.6875rem; font-weight:800; background:#06B6D4; color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs);">REVIEWER RUBRIC</div>
                        <h3 style="font-size:1.05rem; font-weight:800; color:var(--frost-navy); margin:0;">Technical Assessment</h3>
                    </div>
                    <span id="rubric-total-display" style="display:none;"></span>
                </div>

                <form id="reviewer-rubric-form" style="flex:1; min-height:0; display:flex; flex-direction:column; overflow:hidden; margin:0;" onsubmit="event.preventDefault(); {'' if locked else "window.StarAppBridge.submitReviewerAssessment('" + submission.id + "');"}">
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
                                    <input type="number" id="rubric-bu" step="0.5" min="0" max="10" value="{init_bu}" class="lg-rubric-num-input"{ro} oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                            <div class="lg-rubric-row">
                                <span class="lg-rubric-crit-title">2. Architecture Report</span>
                                <span class="lg-rubric-score-box">
                                    <input type="number" id="rubric-ar" step="0.5" min="0" max="10" value="{init_ar}" class="lg-rubric-num-input"{ro} oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                            <div class="lg-rubric-row">
                                <span class="lg-rubric-crit-title">3. Technical Knowledge</span>
                                <span class="lg-rubric-score-box">
                                    <input type="number" id="rubric-tk" step="0.5" min="0" max="10" value="{init_tk}" class="lg-rubric-num-input"{ro} oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                            <div class="lg-rubric-row">
                                <span class="lg-rubric-crit-title">4. Presentation</span>
                                <span class="lg-rubric-score-box">
                                    <input type="number" id="rubric-pr" step="0.5" min="0" max="10" value="{init_pr}" class="lg-rubric-num-input"{ro} oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                            <div class="lg-rubric-row">
                                <span class="lg-rubric-crit-title">5. Q&amp;A Technical Defense</span>
                                <span class="lg-rubric-score-box">
                                    <input type="number" id="rubric-qa" step="0.5" min="0" max="10" value="{init_qa}" class="lg-rubric-num-input"{ro} oninput="window.StarAppBridge.recalcRubricTotal();">
                                    <span class="lg-rubric-max-tag">Max 10</span>
                                </span>
                            </div>
                        </div>

                        <!-- Real-time Sum -->
                        <div class="lg-rubric-total-bar">
                            <span style="font-size:0.75rem; font-weight:800; color:var(--frost-navy);">Sum of Rubric Marks:</span>
                            <span id="rubric-sum-display" style="font-size:0.875rem; font-weight:900; color:var(--deep-frozen-midnight); font-family:var(--font-family-mono);">{init_total:.1f} / 50.0 ({init_pct:.1f}%)</span>
                        </div>

                        <!-- Qualitative Feedback -->
                        <div class="lg-rubric-fields-pair">
                            <div>
                                <label class="lg-rubric-field-label" for="rubric-strengths">Technical Strengths</label>
                                <textarea id="rubric-strengths" rows="2" class="lg-rubric-textarea"{ro}>{escape(init_strengths)}</textarea>
                            </div>
                            <div>
                                <label class="lg-rubric-field-label" for="rubric-improvements">Improvements</label>
                                <textarea id="rubric-improvements" rows="2" class="lg-rubric-textarea"{ro}>{escape(init_improvements)}</textarea>
                            </div>
                        </div>
                    </div>

                    <div style="padding:10px 14px 12px; background:rgba(255,255,255,0.96); border-top:1px solid var(--icy-steel-30); flex-shrink:0;">
                        <div class="lg-decision-dock">{decision_block}</div>
                        {footer_html}
                    </div>
                </form>
            </div>
        </div>
    </div>
    """


# ==============================================================================
# 6.13 REVIEWER MODALS: TIMELINE & GEMINI AI PROJECT CREATOR
# ==============================================================================

def _render_milestone_steps(dt: Dict[str, Any], review_days: List[str], published_at: str, project_step: Dict[str, Any],
                            actuals: Optional[Dict[str, Any]] = None) -> str:
    """The vertical timeline of connected dots (`.tlv-*`) shared by the reviewer's and the cosmonaut's Timeline popups."""
    import datetime as _dt
    today = _dt.date.today()

    def _d(value: Any) -> Optional[_dt.date]:
        try:
            return _dt.date.fromisoformat(str(value)[:10])
        except Exception:
            return None

    def _fmt(value: Any) -> str:
        return format_short_date(value) or ""

    def _range(a: Any, b: Any) -> str:
        fa, fb = _fmt(a), _fmt(b)
        if fa and fb and fa != fb:
            return f'<span class="tlv-nw">{escape(fa)}</span> <span class="tlv-arrow">&rarr;</span> <span class="tlv-nw">{escape(fb)}</span>'
        return f'<span class="tlv-nw">{escape(fa or fb)}</span>' if (fa or fb) else '<span class="tlv-unset">Not set</span>'

    def _state(start: Any, end: Any = None) -> str:
        s_, e_ = _d(start), _d(end if end else start)
        if not s_ and not e_:
            return "next"
        s_ = s_ or e_
        e_ = e_ or s_
        if not end:                                    # a single-day event is either behind us or ahead of us
            return "done" if s_ <= today else "next"
        if e_ < today:
            return "done"
        if s_ <= today <= e_:
            return "now"
        return "next"

    state_label = {"done": "Done", "now": "In progress", "next": "Upcoming", "late": "Window ended"}
    steps: List[str] = []

    def _step(title: str, hint: str, when_html: str, state: str, note_html: str = "", tone: str = "") -> None:
        steps.append(f"""
            <li class="tlv-step is-{state} {tone}">
                <span class="tlv-dot" aria-hidden="true"></span>
                <div class="tlv-card">
                    <div class="tlv-card-top">
                        <div class="tlv-title">{escape(title)}</div>
                        <span class="tlv-state is-{state}">{state_label[state]}</span>
                    </div>
                    <div class="tlv-when">{when_html}</div>
                    <div class="tlv-hint">{escape(hint)}</div>
                    {note_html}
                </div>
            </li>""")

    pub_date = (published_at or "")[:10] or dt.get("publication_date") or dt.get("assignment_date")
    _step("Allocated & published", "The Guardian published the badge to its mapped cosmonauts.", _range(pub_date, None), _state(pub_date))
    _step(project_step["title"], project_step["hint"], project_step["when_html"], project_step["state"], project_step.get("note_html", ""))
    _step("Learning period", "Cosmonauts study the badge's topics.", _range(dt.get("learning_start_date"), dt.get("learning_end_date")),
          _state(dt.get("learning_start_date"), dt.get("learning_end_date")))
    _step("Project sprint", "Cosmonauts build the project and prepare their deliverables.", _range(dt.get("project_start_date"), dt.get("project_end_date")),
          _state(dt.get("project_start_date"), dt.get("project_end_date")))
    act = actuals or {}
    sub_notes = "".join(f'<span class="tlv-note is-ok">{n}</span>' for n in act.get("submitted", []))
    _step("Submission deadline" if not sub_notes else "Submission", "Deliverables (PDF, code, GitHub) are due." if not sub_notes else "Your deliverables were submitted.",
          _range(dt.get("submission_deadline"), None), "done" if sub_notes else _state(dt.get("submission_deadline")), sub_notes, tone="is-deadline")
    rv_first = review_days[0] if review_days else dt.get("review_date")
    rv_last = review_days[-1] if review_days else dt.get("review_date")
    rv_note = f'<span class="tlv-note">{len(review_days)} working days</span>' if len(review_days) > 1 else ""
    rev_notes = "".join(f'<span class="tlv-note is-ok">{n}</span>' for n in act.get("reviewed", []))
    _step("Review window", "The reviewer assesses the deliverables on the 50-mark rubric.", _range(rv_first, rv_last),
          "done" if rev_notes else _state(rv_first, rv_last), rev_notes or rv_note)
    if act.get("awarded"):
        _step("Badge earned", "The Guardian approved your project and awarded the badge.", f'<span class="tlv-nw">{escape(act["awarded"]["when"])}</span>', "done",
              f'<span class="tlv-note is-ok">{act["awarded"]["note"]}</span>')
    else:
        _step("Certification award", "The Guardian gives the final decision and awards the badge.", _range(dt.get("expected_award_date"), None), _state(dt.get("expected_award_date")),
              "".join(f'<span class="tlv-note">{n}</span>' for n in act.get("decided", [])))
    return f'<ol class="tlv-steps">{"".join(steps)}</ol>'


def _timeline_inputs(badge: Badge, tl: Any) -> Any:
    """(schedule dict, review-window days) from a timeline row, falling back to the badge's default timeline."""
    dt = dict(badge.default_timeline or {})
    if tl:
        for k in ("assignment_date", "publication_date", "learning_start_date", "learning_end_date", "project_start_date",
                  "project_end_date", "submission_deadline", "review_date", "expected_award_date"):
            v = getattr(tl, k, "")
            if v:
                dt[k] = v
    days: List[str] = []
    if tl and getattr(tl, "review_window_json", None):
        try:
            parsed = json.loads(tl.review_window_json)
            days = [str(d) for d in parsed if d] if isinstance(parsed, list) else []
        except Exception:
            days = []
    return dt, (days or list(dt.get("review_dates") or []))


def render_reviewer_badge_timeline_modal(badge: Optional[Badge], current_user: User, store: Any = None) -> str:
    """
    The reviewer's Timeline for one badge: who it is for (mapped cosmonauts, projects sent) and the milestone schedule as a vertical
    timeline of connected dots - the 72-hour window to send projects, the learning period, the project sprint, the submission
    deadline, the review window and the award. Each step says whether it is done, running now, or still ahead.
    """
    import datetime as _dt
    from starapp.storage import project_window_seconds_left
    if not badge:
        return "<p style='padding:24px; text-align:center;'>Badge information not found.</p>"

    mapped = _mapped_cosmonauts_for_reviewer_badge(store, current_user, badge)
    tl = store.get_timeline(badge.id, mapped[0].id) if (store and mapped) else None
    dt, review_days = _timeline_inputs(badge, tl)

    n_total = len(mapped)
    n_sent = sum(1 for c in mapped if store and store.get_project_prompt_for_cadet(badge.id, c.id))
    published_at = getattr(badge, "published_at", "") or ""
    left = project_window_seconds_left(published_at)
    pw_start = published_at[:10]
    pw_end = ""
    if published_at:
        try:
            pw_end = (_dt.datetime.fromisoformat(published_at.replace("Z", "+00:00")) + _dt.timedelta(hours=72)).date().isoformat()
        except Exception:
            pw_end = ""
    if n_total and n_sent >= n_total:
        pw_state, pw_note = "done", f'<span class="tlv-note is-ok">All {n_total} project{"" if n_total == 1 else "s"} sent</span>'
    elif left is None:
        pw_state, pw_note = "next", '<span class="tlv-note">Starts when the Guardian publishes the badge</span>'
    elif left == 0:
        pw_state, pw_note = "late", f'<span class="tlv-note is-bad">{n_total - n_sent} project{"" if n_total - n_sent == 1 else "s"} still to send</span>'
    else:
        pw_state, pw_note = "now", render_project_window_timer(published_at)
    when = (f'<span class="tlv-nw">{escape(format_short_date(pw_start))}</span> <span class="tlv-arrow">&rarr;</span> <span class="tlv-nw">{escape(format_short_date(pw_end))}</span>'
            if pw_start and pw_end else '<span class="tlv-unset">Starts at publish</span>')
    steps_html = _render_milestone_steps(dt, review_days, published_at, {
        "title": "Project window (72 hours)", "hint": "Create the project and send it to every mapped cosmonaut.",
        "when_html": when, "state": pw_state, "note_html": pw_note})

    chips = "".join(f'<span class="tlv-person">{escape(c.name)}</span>' for c in mapped[:6])
    if len(mapped) > 6:
        chips += f'<span class="tlv-person is-more">+{len(mapped) - 6} more</span>'
    if not mapped:
        chips = '<span class="tlv-unset">No cosmonauts are mapped to you for this badge yet.</span>'

    return f"""
    <div class="tlv-wrap">
        <div class="tlv-head">
            <div class="tlv-head-chips">
                <span class="tlv-code">{escape(badge.code)}</span>
                <span class="tlv-band">BAND {escape(getattr(badge, "target_band", "B1"))}</span>
                <span class="rv-pill is-green">Milestone timeline</span>
            </div>
            <div class="tlv-badge-title" role="heading" aria-level="3">{escape(badge.title)}</div>
        </div>

        <div class="tlv-facts">
            <div class="tlv-fact"><div class="tlv-fact-lbl">Reviewer</div><div class="tlv-fact-val">{escape(current_user.name)}</div></div>
            <div class="tlv-fact"><div class="tlv-fact-lbl">Mapped cosmonauts</div><div class="tlv-fact-val">{n_total}</div></div>
            <div class="tlv-fact"><div class="tlv-fact-lbl">Projects sent</div><div class="tlv-fact-val">{n_sent} / {n_total}</div></div>
        </div>
        <div class="tlv-people">{chips}</div>

        {steps_html}

        <div class="tlv-footer">
            <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">Close</button>
            <button type="button" class="btn-metal" style="display:inline-flex; align-items:center; gap:8px; font-weight:800;" onclick="window.StarAppBridge.dispatchAction('open_create_reviewer_project_modal', '{escape(badge.id)}')">
                {get_icon("rocket", 14)}<span>{"Edit Project" if (n_total and n_sent >= n_total) else "Create Project"}</span>
            </button>
        </div>
    </div>
    """


def render_cosmonaut_timeline_modal(badge: Optional[Badge], current_user: User, store: Any = None) -> str:
    """The cosmonaut's own schedule for one badge (live: it re-renders while open). Read from THEIR timeline."""
    import datetime as _dt
    from starapp.storage import project_window_seconds_left
    if not badge:
        return "<p style='padding:24px; text-align:center;'>Badge information not found.</p>"
    tl = store.get_timeline(badge.id, current_user.id) if store else None
    dt, review_days = _timeline_inputs(badge, tl)
    published_at = getattr(badge, "published_at", "") or ""
    received = bool(store and store.get_project_prompt_for_cadet(badge.id, current_user.id))
    rev_id = store.get_mapped_reviewer_id(badge.id, current_user.id) if store else ""
    rev = store.get_user_by_id(rev_id) if (store and rev_id) else None
    rev_name = rev.name if rev else "your reviewer"
    left = project_window_seconds_left(published_at)
    if received:
        state, note = "done", '<span class="tlv-note is-ok">Project received - open "Project Allocated" on the badge</span>'
    elif left is None:
        state, note = "next", '<span class="tlv-note">Your reviewer starts when the Guardian publishes the badge</span>'
    elif left == 0:
        state, note = "late", f'<span class="tlv-note is-bad">{escape(rev_name)} has not sent it yet</span>'
    else:
        state, note = "now", render_project_window_timer(published_at, suffix="until your project is sent")
    pw_end = ""
    if published_at:
        try:
            pw_end = (_dt.datetime.fromisoformat(published_at.replace("Z", "+00:00")) + _dt.timedelta(hours=72)).date().isoformat()
        except Exception:
            pw_end = ""
    when = (f'<span class="tlv-nw">Expected by {escape(format_short_date(pw_end))}</span>' if pw_end else '<span class="tlv-unset">After the badge is published</span>')
    # what really happened (IST): every submitted attempt, the reviewer's evaluation, the Guardian's decision, the award
    actuals: Dict[str, Any] = {"submitted": [], "reviewed": [], "decided": []}
    if store:
        for sub in sorted(store.get_submissions_for_cosmonaut(current_user.id, badge.id) or [], key=lambda x: getattr(x, "attempt_number", 1)):
            at = format_ist(getattr(sub, "submitted_at", "") or "")
            if at:
                actuals["submitted"].append(f"Attempt #{sub.attempt_number} submitted on <b>{escape(at)}</b>")
        for a in sorted(store.get_assessments_for_cosmonaut(current_user.id, badge.id) or [], key=lambda x: (getattr(x, "attempt_number", 1), getattr(x, "reviewed_at", ""))):
            at = format_ist(getattr(a, "reviewed_at", "") or "")
            if not at:
                continue
            if getattr(a, "assessor_role", "") == "reviewer":
                actuals["reviewed"].append(f"Attempt #{a.attempt_number} evaluated by {escape(a.reviewer_name)} on <b>{escape(at)}</b> &middot; {a.total_marks:.1f}/50")
            else:
                dec = (getattr(a, "decision", "") or "").lower()
                label = "badge awarded" if dec in ("approve", "approved") else ("rejected" if dec in ("rejected", "reject") else "re-attempt requested")
                if dec in ("approve", "approved"):
                    actuals["awarded"] = {"when": format_short_date(getattr(tl, "actual_award_date", "") or a.reviewed_at) or at,
                                          "note": f"Attempt #{a.attempt_number}: {label} on <b>{escape(at)}</b> &middot; final score {a.total_marks:.1f}/50 ({a.percentage:.1f}%)"}
                else:
                    actuals["decided"].append(f"Attempt #{a.attempt_number}: {label} on {escape(at)}")
    steps_html = _render_milestone_steps(dt, review_days, published_at, {
        "title": "Project from your reviewer", "hint": f"{rev_name} creates your project and sends it to you within 72 hours of publishing.",
        "when_html": when, "state": state, "note_html": note}, actuals)
    deadline = format_short_date(dt.get("submission_deadline")) or "Not set"
    return f"""
    <div class="tlv-wrap" data-live-sync="timeline">
        <div class="tlv-head">
            <div class="tlv-badge-title" role="heading" aria-level="3">{escape(badge.title)}</div>
            <div class="tlv-sub">Your milestone timeline &middot; updates live</div>
        </div>
        <div class="tlv-facts">
            <div class="tlv-fact"><div class="tlv-fact-lbl">Reviewer</div><div class="tlv-fact-val">{escape(rev.name if rev else "Not mapped yet")}</div></div>
            <div class="tlv-fact"><div class="tlv-fact-lbl">Project</div><div class="tlv-fact-val">{"Received" if received else "Pending"}</div></div>
            <div class="tlv-fact"><div class="tlv-fact-lbl">{"Badge earned" if actuals.get("awarded") else "Submission deadline"}</div><div class="tlv-fact-val{"" if actuals.get("awarded") else " rv-red"}">{escape(actuals["awarded"]["when"] if actuals.get("awarded") else deadline)}</div></div>
        </div>
        {steps_html}
        <div class="tlv-footer">
            <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">Close</button>
        </div>
    </div>
    """


def render_cosmonaut_reviewer_modal(badge: Optional[Badge], current_user: User, store: Any = None) -> str:
    """The reviewer the Guardian mapped to this cosmonaut for one badge: who, their schedule, and where the project stands (live)."""
    from starapp.storage import project_window_seconds_left
    if not badge:
        return "<p style='padding:24px; text-align:center;'>Badge information not found.</p>"
    tl = store.get_timeline(badge.id, current_user.id) if store else None
    rev_id = store.get_mapped_reviewer_id(badge.id, current_user.id) if store else ""
    rev = store.get_user_by_id(rev_id) if (store and rev_id) else None
    dt, review_days = _timeline_inputs(badge, tl)
    if not rev:
        return f"""
        <div class="rvm-wrap" data-live-sync="reviewer">
            <div class="rvm-empty">{get_icon("shield", 26)}<div class="rvm-empty-title">No reviewer mapped yet</div>
            <p>The Guardian has not mapped a reviewer to you for <b>{escape(badge.title)}</b> yet. This page updates by itself as soon as they do.</p></div>
            <div class="tlv-footer"><button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">Close</button></div>
        </div>"""
    received = bool(store.get_project_prompt_for_cadet(badge.id, current_user.id))
    left = project_window_seconds_left(getattr(badge, "published_at", "") or "")
    earned = bool(tl and getattr(tl, "status", "") == "completed") or any(
        a.decision in ("approve", "approved") for a in (store.get_assessments_for_cosmonaut(current_user.id, badge.id) or []))
    if earned:
        proj = '<span class="rv-pill is-green">' + get_icon("award", 12) + '<span>Badge earned</span></span>'
    elif received:
        proj = '<span class="rv-pill is-green">' + get_icon("check", 12) + '<span>Project sent - open "Project Allocated"</span></span>'
    elif left == 0:
        proj = '<span class="rv-pill is-red"><span>Project is overdue</span></span>'
    else:
        proj = '<span class="rv-pill is-amber">' + get_icon("clock", 12) + '<span>Project pending</span></span>' + (render_project_window_timer(getattr(badge, "published_at", "") or "", suffix="until it is sent") or "")
    first = format_short_date(review_days[0]) if review_days else format_short_date(dt.get("review_date"))
    last = format_short_date(review_days[-1]) if review_days else ""
    window = f'{escape(first)} &rarr; {escape(last)}' if (first and last and first != last) else escape(first or "Schedule pending")
    initials = "".join(w[0] for w in rev.name.split()[:2]).upper() or "R"
    return f"""
    <div class="rvm-wrap" data-live-sync="reviewer">
        <div class="tlv-head">
            <div class="tlv-badge-title" role="heading" aria-level="3">{escape(badge.title)}</div>
            <div class="tlv-sub">Your mapped reviewer &middot; updates live</div>
        </div>
        <div class="rvm-card">
            <span class="rvm-avatar">{escape(initials)}</span>
            <div class="rvm-who">
                <div class="rvm-name">{escape(rev.name)}</div>
                <div class="rvm-meta"><span class="asm-cosmo-chip is-band">Band {escape(getattr(rev, "band", "") or "")}</span><span class="asm-cosmo-chip">{escape(getattr(rev, "learning_track", "") or "Reviewer")}</span></div>
            </div>
            <span class="rv-pill is-green">Mapped to you</span>
        </div>
        <div class="tlv-facts">
            <div class="tlv-fact"><div class="tlv-fact-lbl">Review window</div><div class="tlv-fact-val">{window}</div></div>
            <div class="tlv-fact"><div class="tlv-fact-lbl">Submission deadline</div><div class="tlv-fact-val rv-red">{escape(format_short_date(dt.get("submission_deadline")) or "Not set")}</div></div>
            <div class="tlv-fact"><div class="tlv-fact-lbl">Your project</div><div class="tlv-fact-val rvm-proj">{proj}</div></div>
        </div>
        <p class="rvm-note">{escape(rev.name)} creates your project, sends it to you, and later assesses your deliverables.</p>
        <div class="tlv-footer">
            <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')" style="font-weight:700;">Close</button>
        </div>
    </div>
    """


def _mapped_cosmonauts_for_reviewer_badge(store: Any, reviewer: User, badge: Badge) -> List[User]:
    """Cosmonauts a reviewer is mapped to for one badge (band mappings, timelines, badge assignment)."""
    mapped: List[User] = []
    if not store:
        return mapped
    seen = set()

    def add(uid: str):
        u = store.get_user_by_id(uid)
        if u and u.id not in seen:
            seen.add(u.id)
            mapped.append(u)

    for m in store.get_band_mappings():
        if reviewer.id in m.get("reviewers", []):
            m_b = m.get("badge_id") or m.get("badge")
            if m_b in (badge.id, badge.code, badge.title):
                for cid in m.get("cosmonauts", []):
                    add(cid)
    for tl in store.get_timelines_for_reviewer(reviewer.id):
        if getattr(tl, "badge_id", "") == badge.id:
            add(getattr(tl, "cosmonaut_id", ""))
    if not mapped and getattr(badge, "assigned_reviewer_id", "") == reviewer.id:
        for cid in getattr(badge, "assigned_cosmonaut_ids", []):
            add(cid)
    return mapped


def render_reviewer_project_creator_modal(badge: Optional[Badge], current_user: User, store: Any = None, project_draft: Optional[Dict[str, Any]] = None) -> str:
    """
    The reviewer's Create Project form. A new project is PRE-FILLED with a synthetic sample built from the badge (heading, case
    study, challenge, project details, deliverables, evaluation) so the reviewer only edits and sends; an earlier project is shown
    in the same sections. Sent as heading + one structured content block to the mapped cosmonauts they pick.
    """
    import json as _json
    from starapp.badge_generator import generate_project_brief, parse_project_content
    if not badge:
        return "<p style='padding:24px; text-align:center;'>Badge information not found.</p>"

    mapped = _mapped_cosmonauts_for_reviewer_badge(store, current_user, badge)
    requested_ids = set()
    given_ids = set()
    latest = None
    if store:
        for r in store.get_pending_project_requests(current_user.id):
            if r.badge_id == badge.id:
                requested_ids.update(r.cosmonaut_ids)
        for p in store.get_reviewer_project_prompts(badge_id=badge.id, reviewer_id=current_user.id):
            if getattr(p, "status", "") in ("released", "sent"):
                given_ids.update(p.cosmonaut_ids)
                if latest is None:
                    latest = p          # newest first

    sample = generate_project_brief(badge)
    if latest:
        existing = parse_project_content(project_brief_content(latest))
        values = {"title": getattr(latest, "title", "") or sample["title"]}
        if existing:
            for k in ("case_study", "challenge", "details", "deliverables", "evaluation"):
                values[k] = existing.get(k, [] if k in ("details", "deliverables", "evaluation") else "")
        else:                                        # an older free-text project: keep it whole under Case Study
            values.update(case_study=project_brief_content(latest), challenge="", details=[], deliverables=[], evaluation=[])
        is_sample = False
    else:
        values = dict(sample)
        is_sample = True

    def _lines(v: Any) -> str:
        return "\n".join(v) if isinstance(v, list) else str(v or "")

    # the three deliverables are separate inputs (label + description); anything else the reviewer wrote is kept as a 4th line
    deliv_labels = ("PDF report", "Source code", "GitHub repository")
    deliv_values = ["", "", ""]
    extra_deliv = []
    for line in (values.get("deliverables") or []):
        placed = False
        for i, lab in enumerate(deliv_labels):
            if line.lower().startswith(lab.lower()) and not deliv_values[i]:
                deliv_values[i] = line
                placed = True
                break
        if not placed:
            extra_deliv.append(line)

    rows = []
    for c in mapped:
        if c.id in requested_ids:
            tag = '<span class="rp-tag is-amber">Requested</span>'
        elif c.id in given_ids:
            tag = '<span class="rp-tag is-green">Project sent</span>'
        else:
            tag = ""
        checked = (c.id in requested_ids) if requested_ids else (c.id not in given_ids)
        rows.append(f"""
        <label class="rp-person">
            <input type="checkbox" class="rev-proj-recipient" value="{escape(c.id)}"{" checked" if checked else ""}>
            <span class="rp-person-name">{escape(c.name)}</span>
            <span class="rp-person-meta">Band {escape(getattr(c, "band", "") or "")}</span>
            <span style="margin-left:auto;">{tag}</span>
        </label>
        """)
    recipients_html = "".join(rows) if rows else '<div class="rp-empty">No cosmonauts are mapped to you for this badge yet.</div>'
    send_disabled = "" if rows else " disabled"

    def _section(key: str, icon: str, title: str, hint: str, inner: str, view_html: str, accent: str = "", color: str = "") -> str:
        """A badge-style section card showing the content FORMATTED; the Edit button swaps in the input fields (and Done swaps back)."""
        style = f' style="border-left-color:{color};"' if color else ""
        return f"""
        <div class="cb-section-card {accent}"{style} data-pj-section="{key}">
            <div class="cb-section-head pj-head">
                <div style="display:flex; align-items:center; gap:12px;">
                    <span class="cb-section-icon">{get_icon(icon, 17)}</span>
                    <div><span class="cb-section-title">{title}</span><div class="rp-hint">{hint}</div></div>
                </div>
                <button type="button" class="btn-secondary btn-sm rp-edit-btn" data-pj-toggle="{key}" onclick="window.StarAppBridge.toggleProjectSection('{key}')">
                    {get_icon("edit", 13)}<span>Edit</span>
                </button>
            </div>
            <div class="pj-body">
                <div class="pj-view" id="rp-view-{key}">{view_html}</div>
                <div class="pj-edit" id="rp-edit-{key}" hidden>{inner}</div>
            </div>
        </div>"""

    def _ta(elem_id: str, value: str, rows_: int, placeholder: str) -> str:
        return (f'<textarea id="{elem_id}" class="form-input rp-ta" rows="{rows_}" maxlength="6000" placeholder="{escape(placeholder)}">{escape(value)}</textarea>')

    deliv_inner = "".join(
        f"""<div class="rp-deliv"><span class="pj-deliv-ico">{_pj_deliverable_icon(lab)}</span>
            <div style="flex:1; min-width:0;"><label class="rp-lbl" for="rev_proj_del_{i}">{escape(lab)}</label>
            <input type="text" id="rev_proj_del_{i}" class="form-input rp-in" maxlength="600" value="{escape(deliv_values[i])}" placeholder="{escape(lab)}: what the cosmonaut must hand in"></div></div>"""
        for i, lab in enumerate(deliv_labels)
    )
    if extra_deliv:
        deliv_inner += f'<div class="rp-deliv"><div style="flex:1;"><label class="rp-lbl" for="rev_proj_del_extra">Other deliverables (one per line)</label>{_ta("rev_proj_del_extra", chr(10).join(extra_deliv), 2, "")}</div></div>'

    deliv_view = '<div class="pj-deliv-grid">' + "".join(
        _pj_deliv_card(*(_pj_split_deliverable(deliv_values[i]) if deliv_values[i] else (lab, "")), idx=i) for i, lab in enumerate(deliv_labels)
    ) + "</div>" + f'<div id="rp-del-extra-view">{_pj_bullets(extra_deliv)}</div>'

    notice = (
        '<div class="rp-notice">' + get_icon("rocket", 15) +
        '<span><b>Sample project ready.</b> It was generated from this badge (its skill, band, outcomes and topics). Edit anything, then send it to your mapped cosmonauts.</span>'
        '<button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.resetReviewerProjectSample()">Reset to sample</button></div>'
        if is_sample else
        '<div class="rp-notice">' + get_icon("edit", 15) +
        '<span><b>Editing your earlier project.</b> Changes go to the cosmonauts you tick below.</span>'
        '<button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.resetReviewerProjectSample()">Load a fresh sample</button></div>'
    )
    sample_attr = escape(_json.dumps({
        "title": sample["title"], "case_study": sample["case_study"], "challenge": sample["challenge"],
        "details": "\n".join(sample["details"]), "evaluation": "\n".join(sample["evaluation"]),
        "deliverables": [next((d for d in sample["deliverables"] if d.lower().startswith(l.lower())), "") for l in deliv_labels],
    }))

    return f"""
    <div class="rp-wrap">
        <div class="rp-head">
            <span class="rv-code">{escape(badge.code)}</span>
            <span class="rp-badge-title">{escape(badge.title)}</span>
        </div>
        {notice}

        <form id="reviewer-project-spec-form" data-sample="{sample_attr}" onsubmit="event.preventDefault();">
            <div class="rp-title-box" data-pj-section="title">
                <div class="rp-title-top">
                    <label for="rev_proj_title" class="rp-lbl">Heading</label>
                    <button type="button" class="btn-secondary btn-sm rp-edit-btn" data-pj-toggle="title" onclick="window.StarAppBridge.toggleProjectSection('title')">
                        {get_icon("edit", 13)}<span>Edit</span>
                    </button>
                </div>
                <h2 class="rp-title-view" id="rp-view-title">{escape(values.get("title", "") or "Untitled project")}</h2>
                <div id="rp-edit-title" hidden>
                    <input type="text" id="rev_proj_title" class="form-input rp-title" maxlength="200" value="{escape(values.get("title", ""))}" placeholder="Project heading">
                </div>
            </div>

            <div class="rp-lead">Project Content</div>
            {_section("case_study", "layers", "Case Study", "The situation: who the client is and what is going wrong.", _ta("rev_proj_case", values.get("case_study", ""), 6, "Describe the client and the situation"), _pj_paragraphs(values.get("case_study", "")), "accent-emerald")}
            {_section("challenge", "target", "Your Challenge", "What the cosmonaut has to build or solve.", _ta("rev_proj_challenge", values.get("challenge", ""), 4, "State the challenge"), _pj_paragraphs(values.get("challenge", "")), "accent-amber")}
            {_section("details", "clipboard", "Project Details", "Scope, constraints and what to cover - one point per line.", _ta("rev_proj_details", _lines(values.get("details")), 7, "One requirement per line"), _pj_bullets(values.get("details")), "accent-cyan")}
            {_section("deliverables", "file_text", "Deliverables", "What has to be handed in.", deliv_inner, deliv_view, "", "#2563EB")}
            {_section("evaluation", "award", "Evaluation", "How the work is marked (the 50-mark rubric) - one point per line.", _ta("rev_proj_eval", _lines(values.get("evaluation")), 5, "One criterion per line"), _pj_bullets(values.get("evaluation")), "", "#7C3AED")}

            <div class="cb-section-card" style="border-left-color:#059669;">
                <div class="cb-section-head pj-head">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span class="cb-section-icon">{get_icon("users", 17)}</span>
                        <div><span class="cb-section-title">Send to mapped cosmonauts</span><div class="rp-hint">Everyone ticked receives this project.</div></div>
                    </div>
                </div>
                <div class="pj-body"><div class="rp-people">{recipients_html}</div></div>
            </div>

            <div class="rp-footer">
                <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Cancel</button>
                <button type="button" class="btn-metal rp-send"{send_disabled}
                        onclick="window.StarAppBridge.submitReviewerProject('{escape(badge.id)}', '{escape(current_user.id)}')">
                    {get_icon("rocket", 15)}<span>Send Project to Mapped Cosmonauts</span>{get_icon("arrow_right", 13)}
                </button>
            </div>
        </form>
    </div>
    """


def render_cosmonaut_appraisal_cards(
    selected_cycle: Any,
    user_perf_per_cycle: List[Dict[str, Any]]
) -> str:
    """Per-cycle appraisal cards (dual-role performance, tier, compensation) shown on the Choose Cycle page."""
    cards = []
    for entry in user_perf_per_cycle:
        cyc = entry["cycle"]
        row = entry["row"]
        is_sel = (selected_cycle and cyc.id == selected_cycle.id)
        border_style = "border:2px solid var(--deep-frozen-midnight);" if is_sel else "border:1px solid var(--icy-steel-50);"
        st_lbl = (cyc.status or "active").upper()
        st_pill = (
            '<span style="background:rgba(16,185,129,0.14); color:#047857; padding:3px 9px; border-radius:999px; font-size:0.65625rem; font-weight:800;">ACTIVE CYCLE</span>'
            if cyc.status == "active" else
            f'<span style="background:rgba(100,116,139,0.14); color:#334155; padding:3px 9px; border-radius:999px; font-size:0.65625rem; font-weight:800;">{escape(st_lbl)}</span>'
        )
        sal_html = ""
        if row.get("base_salary", 0) > 0:
            sal_html = f'<div style="font-size:0.75rem; color:#047857; margin-top:4px;">Compensation Update: {row["base_salary"]:,.0f} &rarr; <strong>{row["new_salary"]:,.0f}</strong> (+{row["approved_hike_pct"]:.1f}%)</div>'
        elif row.get("approved_hike_pct", 0) > 0:
            sal_html = f'<div style="font-size:0.75rem; color:#047857; margin-top:4px;">Recommended Hike: <strong>+{row["approved_hike_pct"]:.1f}%</strong></div>'

        promo_html = f'<span style="background:rgba(79,70,229,0.12); color:#4F46E5; padding:2px 8px; border-radius:4px; font-size:0.6875rem; font-weight:800;">Promotion Rec: Band {escape(row["recommended_promotion_band"])}</span>' if row.get("recommended_promotion_band") else ""

        cards.append(f"""
        <div class="liquid-glass-card" style="padding:18px 22px; margin-bottom:16px; {border_style}">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding-bottom:12px; border-bottom:1px solid var(--icy-steel-30); margin-bottom:14px;">
                <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <span style="font-family:var(--font-family-mono); font-size:0.6875rem; font-weight:800; background:var(--deep-frozen-midnight); color:#fff; padding:2px 8px; border-radius:var(--radius-xs);">{escape(cyc.code)}</span>
                        <span style="font-size:0.75rem; color:var(--frost-navy-50); font-weight:700;">{escape(cyc.start_date)} &rarr; {escape(cyc.end_date)}</span>
                        {st_pill}
                    </div>
                    <h3 style="margin:0; font-size:1.2rem; font-weight:800; color:var(--frost-navy);">{escape(cyc.name)}</h3>
                </div>
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <div style="text-align:right;">
                        <div style="font-family:var(--font-family-mono); font-size:1.35rem; font-weight:900; color:var(--deep-frozen-midnight);">{row["composite_score"]:.1f} / 100</div>
                        <div style="font-size:0.71875rem; font-weight:800; color:var(--frost-navy-50);">{escape(row["performance_tier"])}</div>
                    </div>
                </div>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(260px, 100%), 1fr)); gap:14px;">
                <div style="padding:12px 14px; border-radius:var(--radius-sm); background:rgba(234,244,255,0.6); border:1px solid var(--icy-steel-30);">
                    <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:6px;">🎓 My Cosmonaut Performance</div>
                    <div style="font-size:0.78125rem; color:var(--frost-navy); line-height:1.6;">
                        <div>Badges Earned: <strong>{row["badges_earned"]} / {row["badges_assigned"]}</strong> ({row["cosmo_completion_pct"]}%)</div>
                        <div>Average Score: <strong>{row["avg_marks"]} / 50</strong> ({row["avg_percentage"]}%)</div>
                        <div>First-Attempt Passes: <strong>{row["first_attempt_passes"]}</strong> &bull; Cosmonaut Index: <strong>{row["cosmo_score"]}%</strong></div>
                    </div>
                </div>
                <div style="padding:12px 14px; border-radius:var(--radius-sm); background:rgba(240,253,250,0.75); border:1px solid rgba(13,148,136,0.28);">
                    <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:#0F766E; margin-bottom:6px;">⚖️ My Reviewer Performance</div>
                    <div style="font-size:0.78125rem; color:var(--frost-navy); line-height:1.6;">
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
                    {f'<div style="font-size:0.75rem; color:var(--frost-navy-75); margin-top:4px;"><strong>Guardian Remarks:</strong> {escape(row["guardian_remarks"])}</div>' if row.get("guardian_remarks") else ""}
                </div>
                <span style="font-size:0.6875rem; font-weight:800; color:var(--frost-navy-50); text-transform:uppercase;">Appraisal Status: {escape(row["status"])}</span>
            </div>
        </div>
        """)

    return "".join(cards) if cards else '<div class="liquid-glass-card" style="padding:36px; text-align:center; color:var(--frost-navy-50);">No cycles recorded yet.</div>'


def render_cosmonaut_cycles_view(
    current_user: User,
    cycles: List[Any],
    selected_cycle: Any,
    user_perf_per_cycle: List[Dict[str, Any]]
) -> str:
    """Compatibility wrapper: the old 'Past Cycle & Performance' page is now part of Choose Cycle."""
    return f"""
    <div>
        <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy); margin:0 0 16px 0;">Performance &amp; Appraisals</h2>
        {render_cosmonaut_appraisal_cards(selected_cycle, user_perf_per_cycle)}
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
                <span class="status-pill {st_pill_cls}" style="font-size:0.6875rem; flex-shrink:0;">{st_label}</span>
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
                <span style="font-size:0.71875rem; font-weight:700; color:var(--frost-navy-50);">{escape(st_label)} Cycle</span>
                {action_chip}
            </div>
        </div>
        """)

    # Past cycles & appraisals now live on this page (the separate sidebar item was removed).
    appraisal_rows = [{"cycle": c, "row": stats_map[c.id]} for c in cycles if c.id in stats_map]
    appraisal_section = ""
    if appraisal_rows:
        appraisal_section = f"""
        <h3 style="display:flex; align-items:center; gap:8px; font-size:1.1rem; font-weight:800; color:var(--frost-navy); margin:26px 0 14px 0;">
            {get_icon("analytics", 18)}<span>Performance &amp; Appraisals</span>
        </h3>
        {render_cosmonaut_appraisal_cards(selected_cycle, appraisal_rows)}
        """

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
                <button type="button" class="btn-metal btn-sm" style="font-weight:800; padding:0 14px;"
                        onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">
                    Open Badges &rarr;
                </button>
            </div>
        </div>

        <div class="cosmo-cycle-grid">
            {"".join(cycle_cards) if cycle_cards else '<div class="liquid-glass-card" style="padding:28px; text-align:center;">No performance cycles available yet.</div>'}
        </div>
        {appraisal_section}
    </div>
    """



