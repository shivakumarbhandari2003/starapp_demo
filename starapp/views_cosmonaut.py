"""
STARAPP COSMONAUT PORTAL VIEWS
Implements the 10 personalized learning workspaces for learners.
"""

from typing import List, Dict, Any, Optional
from starapp.models import (
    User, CosmonautProfile, Badge, BadgeTimeline, ProjectSubmission,
    AssessmentMarksheet, LearningMaterial, DeadlineExtension,
    Announcement, ActivityEvent
)
from starapp.views_common import (
    get_icon,
    escape, render_liquid_card, render_metal_button, render_liquid_button,
    render_status_pill, render_standard_marksheet, render_9point_timeline,
    render_learning_materials_view
)
from starapp.roadmap import generate_roadmap_graph
from starapp.assessment import RUBRIC_CRITERIA
from starapp.analytics import build_astraea_analytics_record, get_kpi_popover

def render_cosmo_metric_info_popover(key: str, data: Dict[str, Any], scope: str = "individual", align: str = "") -> str:
    """Renders interactive info trigger (i) with calculation details for personal learner metrics."""
    info = get_kpi_popover(key, data, scope)
    if not info:
        return ""
    align_cls = f"pop-{align}" if align else ""
    return f"""
    <span class="has-glass-tooltip">
        <button type="button" class="metric-info-trigger" aria-label="Metric details for {escape(info.get('title', ''))}" tabindex="0">
            i
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
                    <span class="popover-data-val" style="color:#10B981;">{escape(info.get('value', ''))}</span>
                </div>
                <div class="popover-criteria-section">
                    <div><strong>Included:</strong> {escape(info.get('included', ''))}</div>
                    <div style="margin-top:3px;"><strong>Excluded:</strong> {escape(info.get('excluded', ''))}</div>
                    <div style="margin-top:4px; color:var(--pure-ice); font-style:italic;">{escape(info.get('insight', ''))}</div>
                </div>
            </div>
        </button>
    </span>
    """

# ==============================================================================
# COSMONAUT SIDEBAR
# ==============================================================================

def render_cosmonaut_sidebar(active_view: str, current_user: User, unread_announcements_count: int) -> str:
    nav_items = [
        {"id": "c_dashboard", "label": "My Dashboard", "icon": '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>', "badge": 0},
        {"id": "c_roadmap", "label": "Learning Roadmap", "icon": '<svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>', "badge": 0},
        {"id": "c_submission", "label": "Project Submission", "icon": '<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>', "badge": 0},
        {"id": "c_results", "label": "Assessment Marksheet", "icon": '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>', "badge": 0},
        {"id": "c_materials", "label": "Study Materials", "icon": '<svg viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>', "badge": 0},
        {"id": "c_profile", "label": "Cosmonaut Profile", "icon": '<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>', "badge": 0},
        {"id": "c_extensions", "label": "Deadline Extensions", "icon": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', "badge": 0}
    ]

    links_html = []
    for item in nav_items:
        is_active = item["id"] == active_view
        cls = "nav-link active" if is_active else "nav-link"
        badge_html = f'<span class="nav-badge">{item["badge"]}</span>' if item["badge"] > 0 else ""
        links_html.append(f"""
        <li class="nav-item">
            <a class="{cls}" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', '{item["id"]}')">
                {item["icon"]}
                <span>{item["label"]}</span>
                {badge_html}
            </a>
        </li>
        """)

    return f"""
    <aside class="app-sidebar">
        <div class="sidebar-header">
            <div class="brand-badge">
                <svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            </div>
            <div>
                <div class="brand-title">STARAPP</div>
                <div class="brand-subtitle">COSMONAUT PORTAL</div>
            </div>
        </div>

        <div class="role-badge-pill">
            <span class="role-badge-label">Learner</span>
            <span class="role-badge-val">Batch Orion-24</span>
        </div>

        <ul class="sidebar-nav">
            {"".join(links_html)}
            <li class="nav-item" style="margin-top:12px; padding-top:10px; border-top:1px solid var(--icy-steel-30);">
                <a class="nav-link" onclick="window.open('index.html?role=guardian', '_blank');" style="color:var(--deep-frozen-midnight); font-weight:700;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    <span>Guardian Window ↗</span>
                </a>
            </li>
        </ul>

        <div class="sidebar-footer">
            <div class="user-mini-card" style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; align-items:center; gap:8px; cursor:pointer;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_profile')">
                    <div class="user-avatar">{escape(current_user.avatar)}</div>
                    <div class="user-details">
                        <div class="user-name">{escape(current_user.name)}</div>
                        <div class="user-role-text">Cosmonaut Profile</div>
                    </div>
                </div>
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('logout', '{{}}')" title="Sign Out" style="padding:4px 8px; font-size:11px; font-weight:700;">Sign Out</button>
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
    extensions: Optional[List[Any]] = None
) -> str:
    from starapp.storage import store

    # 1. Executive Telemetry Calculations from actual records
    cadet_subs = submissions if submissions is not None else store.get_submissions_for_cosmonaut(current_user.id)
    cadet_exts = extensions if extensions is not None else store.get_extensions_for_cosmonaut(current_user.id)
    cadet_anns = recent_announcements if recent_announcements is not None else store.get_announcements_for_cosmonaut(current_user.id)[:3]

    astraea_rec = build_astraea_analytics_record(current_user, assigned_badges, assessments, cadet_subs, cadet_exts)

    approved_asms = [a for a in assessments if a.decision == "approve"]
    total_assigned = len(assigned_badges)
    completed_count = len(approved_asms)
    progress_pct = round((completed_count / max(1, total_assigned)) * 100.0, 1)

    # Calculate average score from actual approved assessments
    if approved_asms:
        avg_marks = round(sum(a.total_marks for a in approved_asms) / len(approved_asms), 2)
        avg_pct = round((avg_marks / 50.0) * 100.0, 1)
        best_score = max(a.total_marks for a in approved_asms)
        best_asm = next(a for a in approved_asms if a.total_marks == best_score)
        best_badge_code = best_asm.badge_id.replace("badge_", "").upper()
    else:
        avg_marks = 0.0
        avg_pct = 0.0
        best_score = 0.0
        best_badge_code = "N/A"

    # First attempt pass rate
    first_attempt_passes = sum(1 for a in approved_asms if a.attempt_number == 1)
    attempted_badge_ids = {s.badge_id for s in cadet_subs}
    eligible_count = max(1, len(attempted_badge_ids))
    pass_rate = round((first_attempt_passes / eligible_count) * 100.0, 1)

    # Active milestone identification
    completed_badge_ids = {a.badge_id for a in approved_asms}
    active_badges = [b for b in assigned_badges if b.id not in completed_badge_ids]
    active_b = active_badges[0] if active_badges else None

    # Next step recommendation logic
    pending_sub = next((s for s in cadet_subs if s.badge_id == (active_b.id if active_b else "") and s.status == "pending"), None)
    latest_sub = next((s for s in sorted(cadet_subs, key=lambda x: x.attempt_number, reverse=True) if s.badge_id == (active_b.id if active_b else "")), None)

    if pending_sub:
        next_action_title = f"{active_b.code if active_b else 'Milestone'} Deliverable (Attempt #{pending_sub.attempt_number}) In Evaluation"
        next_action_desc = f"Your latest project package for <strong>{escape(active_b.title if active_b else '')}</strong> is currently undergoing technical review by Dr. Elena Vance. While awaiting marksheet publication, begin reviewing study materials for subsequent milestones."
        next_action_pill = '<span class="status-pill status-pending" style="font-size:11px; font-weight:800; padding:4px 10px;">&#9203; Under Guardian Review</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:12px; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Track Submission Status &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:12px; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_materials')">Browse Study Materials &rarr;</button>"""
    elif latest_sub and latest_sub.status == "resubmission_requested":
        next_action_title = f"Resubmission Required: {active_b.code if active_b else 'Milestone'}"
        next_action_desc = f"Guardian requested a revised Attempt #{latest_sub.attempt_number + 1} deliverable. Address the architectural idempotency feedback and resubmit your implementation package."
        next_action_pill = '<span class="status-pill status-rejected" style="font-size:11px; font-weight:800; padding:4px 10px;">&#9888; Resubmission Requested</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:12px; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Submit Revised Deliverable &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:12px; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')">View Mentor Feedback &rarr;</button>"""
    elif active_b:
        next_action_title = f"Active Sprint: Complete {active_b.code} Deliverables"
        next_action_desc = f"You are currently fulfilling <strong>{escape(active_b.title)}</strong>. Prepare your PDF system architecture charter and executable code package for upload."
        next_action_pill = '<span class="status-pill status-active" style="font-size:11px; font-weight:800; padding:4px 10px;">&#9654; Sprint In Progress</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:12px; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Submit Project Deliverable &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:12px; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_materials')">Review Study Materials &rarr;</button>"""
    else:
        next_action_title = "Curriculum Roadmap Completed"
        next_action_desc = "All assigned enterprise milestones have been certified by Guardian mentorship. Review your official marksheet transcript."
        next_action_pill = '<span class="status-pill status-approved" style="font-size:11px; font-weight:800; padding:4px 10px;">&#10003; Certified</span>'
        primary_btn = f"""<button type="button" class="btn-metal btn-sm" style="font-size:12px; padding:6px 16px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')">View Marksheets &rarr;</button>"""
        secondary_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:12px; padding:6px 14px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_roadmap')">Explore Career Pathways &rarr;</button>"""

    # 2. Rubric Dimension Breakdown across approved assessments
    rubric_telemetry = []
    cadet_scores_dict = {}
    for c in RUBRIC_CRITERIA:
        k = c["key"]
        c_vals = [getattr(a, k, 0.0) for a in approved_asms]
        c_avg = round(sum(c_vals) / len(c_vals), 2) if c_vals else 0.0
        cadet_scores_dict[k] = c_avg
        pct_bar = min(100.0, (c_avg / 10.0) * 100.0)

        rubric_telemetry.append(f"""
        <div style="margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="font-size:12.5px; font-weight:700; color:var(--frost-navy);">{escape(c["title"])}</span>
                <span style="font-size:13px; font-weight:800; color:var(--deep-frozen-midnight);">{c_avg:.1f} <span style="font-size:11px; font-weight:600; opacity:0.6;">/ 10.0</span></span>
            </div>
            <div class="chart-node-interactive" style="height:10px; border-radius:var(--radius-full); background:rgba(157,183,213,0.25); overflow:visible; position:relative;" tabindex="0">
                <div style="height:100%; width:{pct_bar}%; border-radius:var(--radius-full); background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
                <div class="chart-data-tooltip">{escape(c["title"])}: {c_avg:.1f} / 10.0 ({pct_bar:.1f}%) &bull; Certified Rubric Average</div>
            </div>
        </div>
        """)

    # Primary strength & growth vector
    sorted_criteria = sorted(RUBRIC_CRITERIA, key=lambda x: cadet_scores_dict.get(x["key"], 0.0), reverse=True)
    superpower = sorted_criteria[0] if sorted_criteria else None
    growth_vector = sorted_criteria[-1] if sorted_criteria else None

    # 3. Score trend across certified badges
    trend_bars = []
    for a in sorted(approved_asms, key=lambda x: x.reviewed_at):
        b_code = a.badge_id.replace("badge_", "").upper()
        h = round((a.total_marks / 50.0) * 85)
        trend_bars.append(f"""
        <div class="chart-node-interactive" style="display:flex; flex-direction:column; align-items:center; flex:1; position:relative;" tabindex="0">
            <span style="font-size:11.5px; font-weight:800; color:var(--deep-frozen-midnight); margin-bottom:4px;">{a.total_marks:.1f}</span>
            <div style="width:100%; max-width:44px; height:{h}px; border-radius:var(--radius-xs); background:linear-gradient(180deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
            <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:800; color:var(--frost-navy); margin-top:6px;">{escape(b_code)}</span>
            <div class="chart-data-tooltip" style="bottom:calc(100% + 4px);">{escape(b_code)}: {a.total_marks:.1f} / 50.0 ({a.percentage:.1f}%) &bull; Attempt #{a.attempt_number}</div>
        </div>
        """)

    # 4. Roadmap progression pipeline rows
    pipeline_rows = []
    for idx, b in enumerate(assigned_badges):
        b_asm = next((a for a in approved_asms if a.badge_id == b.id), None)
        b_sub = next((s for s in cadet_subs if s.badge_id == b.id and s.status == "pending"), None)
        tl = store.get_timeline(b.id, current_user.id)

        if b_asm:
            st_pill = '<span class="status-pill status-approved" style="font-size:10.5px;">&#10003; Certified</span>'
            score_disp = f"<strong>{b_asm.total_marks:.1f}</strong> / 50 ({b_asm.percentage:.1f}%)"
            action = f"""<button type="button" class="btn-metal btn-sm" style="font-size:11px; padding:3px 10px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')">Marksheet &rarr;</button>"""
        elif b_sub:
            st_pill = '<span class="status-pill status-pending" style="font-size:10.5px;">&#9203; In Review</span>'
            score_disp = "<span style='opacity:0.6;'>Under Guardian Review</span>"
            action = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:11px; padding:3px 10px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Track Status &rarr;</button>"""
        elif tl and getattr(tl, "status", "") in ["active", "in_progress"]:
            st_pill = '<span class="status-pill status-active" style="font-size:10.5px;">Active Sprint</span>'
            score_disp = "<span style='opacity:0.6;'>In Progress</span>"
            action = f"""<button type="button" class="btn-metal btn-sm" style="font-size:11px; padding:3px 10px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Submit &rarr;</button>"""
        else:
            st_pill = '<span class="status-pill status-locked" style="font-size:10.5px;">Locked</span>'
            score_disp = "<span style='opacity:0.4;'>—</span>"
            action = f"""<button type="button" class="btn-secondary btn-sm" style="font-size:11px; padding:3px 10px; opacity:0.7;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_roadmap')">Roadmap</button>"""

        pipeline_rows.append(f"""
        <tr class="chart-node-interactive" style="border-bottom:1px solid var(--icy-steel-30); position:relative;" tabindex="0">
            <td style="padding:10px 12px; font-weight:700;">
                <span style="font-family:var(--font-family-mono); font-size:11px; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 6px; border-radius:var(--radius-xs); margin-right:6px;">{escape(b.code)}</span>
                <span style="font-size:13px; color:var(--frost-navy);">{escape(b.title)}</span>
            </td>
            <td style="padding:10px 12px; font-size:11.5px; color:var(--frost-navy-50);">{escape(getattr(b, 'category', 'Foundations'))}</td>
            <td style="padding:10px 12px; text-align:center;">{st_pill}</td>
            <td style="padding:10px 12px; text-align:center; font-size:12.5px;">{score_disp}</td>
            <td style="padding:10px 12px; text-align:right;">{action}</td>
        </tr>
        """)

    # 5. Announcements preview items
    ann_items = []
    for ann in cadet_anns[:2]:
        ann_items.append(f"""
        <div style="padding:10px 14px; background:rgba(234,244,255,0.6); border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm); margin-bottom:8px;">
            <div style="font-size:12.5px; font-weight:800; color:var(--frost-navy);">{escape(ann.title)}</div>
            <div style="font-size:11.5px; color:var(--frost-navy-75); margin-top:2px; line-height:1.4;">{escape(ann.message[:120])}...</div>
        </div>
        """)

    anns_html = "".join(ann_items) if ann_items else "<div style='font-size:12px; color:var(--frost-navy-50);'>No pending broadcast announcements.</div>"

    return f"""
    <div>
        <!-- SECTION A: Personal Welcome Header -->
        <div class="liquid-glass-card" style="padding:22px 28px; margin-bottom:24px; border-radius:var(--radius-lg); border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(234,244,255,0.85) 100%); box-shadow:0 6px 20px rgba(7,22,41,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div class="user-avatar" style="width:52px; height:52px; font-size:18px; font-weight:800; border:2px solid var(--icy-steel);">{escape(current_user.avatar)}</div>
                    <div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <h2 style="font-size:1.5rem; font-weight:800; color:var(--frost-navy); margin:0;">Welcome back, {escape(current_user.name)}</h2>
                            <span class="status-pill status-approved" style="font-size:11px; font-weight:800;">Flight Officer</span>
                        </div>
                        <div style="font-size:12.5px; color:var(--frost-navy-75); margin-top:3px;">
                            ID: <strong>{escape(current_user.id)}</strong> &bull; Batch: <strong>{escape(profile.batch_name or "Orion-24")}</strong> &bull; Mentor: <strong>Dr. Elena Vance</strong>
                        </div>
                    </div>
                </div>

                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <span style="font-size:12px; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:6px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel);">
                        Average Assessment Score: <strong>{avg_marks:.1f} / 50.0 ({avg_pct:.1f}%)</strong>
                    </span>
                    <span style="font-size:12px; font-weight:800; color:#FFFFFF; background:#10B981; padding:6px 14px; border-radius:var(--radius-sm);">
                        {escape(astraea_rec.get("standing_tier", "Excellent Performance"))}
                    </span>
                </div>
            </div>
        </div>

        <!-- SECTION B: Personal 6-KPI Overview -->
        <div class="kpi-grid" style="grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:16px; margin-bottom:24px;">
            <div class="liquid-glass-card kpi-card" style="padding:18px 20px;">
                <div class="kpi-header">
                    <span class="kpi-title" style="display:flex; align-items:center;">
                        Curriculum Progress
                        {render_cosmo_metric_info_popover('individual_badges', astraea_rec, 'individual')}
                    </span>
                </div>
                <div class="kpi-value" style="font-size:1.85rem;">{completed_count} / {total_assigned}</div>
                <div style="height:6px; border-radius:var(--radius-full); background:rgba(157,183,213,0.3); overflow:hidden; margin:6px 0;">
                    <div style="height:100%; width:{progress_pct}%; background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
                </div>
                <div class="kpi-subtext" style="color:#10B981; font-weight:700;">▲ {progress_pct}% Roadmap Certified</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:18px 20px;">
                <div class="kpi-header">
                    <span class="kpi-title" style="display:flex; align-items:center;">
                        Average Assessment Score
                        {render_cosmo_metric_info_popover('individual_score', astraea_rec, 'individual')}
                    </span>
                </div>
                <div class="kpi-value" style="font-size:1.85rem;">{avg_marks:.1f} <span style="font-size:13px; opacity:0.6; font-weight:600;">/ 50.0</span></div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700;">{avg_pct:.1f}% Average Across Cleared Milestones</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:18px 20px;">
                <div class="kpi-header">
                    <span class="kpi-title" style="display:flex; align-items:center;">
                        First-Attempt Pass Rate
                        {render_cosmo_metric_info_popover('individual_first_attempt', astraea_rec, 'individual')}
                    </span>
                </div>
                <div class="kpi-value" style="font-size:1.85rem;">{pass_rate}%</div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700;">{first_attempt_passes} of {eligible_count} Cleared on Attempt #1</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:18px 20px;">
                <div class="kpi-header">
                    <span class="kpi-title" style="display:flex; align-items:center;">
                        Current Active Badge
                        {render_cosmo_metric_info_popover('individual_active_milestone', astraea_rec, 'individual', 'right')}
                    </span>
                </div>
                <div class="kpi-value" style="font-size:1.45rem; color:var(--deep-frozen-midnight);">{escape(active_b.code if active_b else "Completed")}</div>
                <div class="kpi-subtext" style="color:var(--frost-navy-50);">{escape(active_b.title if active_b else "All Milestones Cleared")}</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:18px 20px;">
                <div class="kpi-header"><span class="kpi-title">Upcoming Milestone Cutoff</span></div>
                <div class="kpi-value" style="font-size:1.35rem; font-family:var(--font-family-mono); color:var(--frost-navy);">2026-12-02</div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700;">ING-104 Official Deadline</div>
            </div>

            <div class="liquid-glass-card kpi-card" style="padding:18px 20px;">
                <div class="kpi-header"><span class="kpi-title">Personal Best Evaluation</span></div>
                <div class="kpi-value" style="font-size:1.85rem; color:#10B981;">{best_score:.1f} <span style="font-size:13px; opacity:0.6; font-weight:600;">/ 50</span></div>
                <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700;">{best_badge_code} Distinction (98.0%)</div>
            </div>
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

        <!-- SECTION D & E: Personal Roadmap & Performance Analytics -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(420px, 1fr)); gap:20px; margin-bottom:24px;">
            <!-- Assessment Score Trend & Rubric Mastery -->
            <div class="liquid-glass-card" style="padding:22px 24px;">
                <div style="margin-bottom:16px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Rubric Competency Mastery</h3>
                        <div style="font-size:12px; color:var(--frost-navy-50);">Your certified marks across the 5 standard rubric dimensions.</div>
                    </div>
                    <span style="font-size:11px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:3px 8px; border-radius:var(--radius-xs);">
                        Standard 50-Mark Rubric
                    </span>
                </div>
                {"".join(rubric_telemetry)}

                <div style="margin-top:16px; padding-top:14px; border-top:1px solid var(--icy-steel-30);">
                    <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:8px;">Certified Milestone Scores (/50)</div>
                    <div style="display:flex; justify-content:space-around; align-items:flex-end; height:120px; padding-bottom:6px; border-bottom:1px solid var(--icy-steel-30);">
                        {"".join(trend_bars)}
                    </div>
                </div>
            </div>

            <!-- Learning Roadmap Trajectory -->
            <div class="liquid-glass-card" style="padding:22px 24px;">
                <div style="margin-bottom:16px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Curriculum Roadmap Status</h3>
                        <div style="font-size:12px; color:var(--frost-navy-50);">Sequential certification pathway for Batch Orion-24.</div>
                    </div>
                    <button type="button" class="btn-secondary btn-sm" style="font-size:11.5px; padding:3px 10px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_roadmap')">
                        Full Roadmap &rarr;
                    </button>
                </div>

                <div style="overflow-x:auto;">
                    <table style="width:100%; border-collapse:collapse; text-align:left;">
                        <thead>
                            <tr style="border-bottom:1.5px solid var(--icy-steel); font-size:11px; color:var(--deep-frozen-midnight); text-transform:uppercase;">
                                <th style="padding:8px 10px;">Milestone</th>
                                <th style="padding:8px 10px;">Domain</th>
                                <th style="padding:8px 10px; text-align:center;">Status</th>
                                <th style="padding:8px 10px; text-align:center;">Score</th>
                                <th style="padding:8px 10px; text-align:right;">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(pipeline_rows)}
                        </tbody>
                    </table>
                </div>

                <!-- SECTION F: Strengths & Growth Vector -->
                <div style="margin-top:16px; padding-top:14px; border-top:1px solid var(--icy-steel-30);">
                    <div style="background:rgba(23,52,92,0.05); padding:10px 14px; border-radius:var(--radius-sm); border-left:3px solid var(--deep-frozen-midnight); margin-bottom:10px;">
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:2px;">Primary Engineering Strength: Technical Knowledge</div>
                        <div style="font-size:12px; color:var(--frost-navy); line-height:1.45;">Exemplary score of <strong>10.0 / 10.0</strong> — robust atomic deduplication store prevents duplicate writes on Kafka consumer rebalances.</div>
                    </div>
                    <div style="background:rgba(157,183,213,0.15); padding:10px 14px; border-radius:var(--radius-sm); border-left:3px solid var(--icy-steel);">
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy); margin-bottom:2px;">Targeted Growth Vector: Architecture & Resilience</div>
                        <div style="font-size:12px; color:var(--frost-navy-75); line-height:1.45;">Focus on exponential backoff with jitter for Dead Letter Queue consumer failover.</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- SECTION G & H: Announcements & Recent Milestones -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)); gap:20px;">
            <div class="liquid-glass-card" style="padding:22px 24px;">
                <div style="margin-bottom:14px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:8px;">
                    <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Broadcast Announcements</h3>
                    <div style="font-size:12px; color:var(--frost-navy-50);">Official directives from Dr. Elena Vance and academy mentors.</div>
                </div>
                {anns_html}
            </div>

            <div class="liquid-glass-card" style="padding:22px 24px;">
                <div style="margin-bottom:14px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0 0 2px 0;">Milestone Deadline Status</h3>
                        <div style="font-size:12px; color:var(--frost-navy-50);">Submission schedules and evaluated extension requests.</div>
                    </div>
                    <button type="button" class="btn-secondary btn-sm" style="font-size:11px; padding:3px 10px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_extensions')">
                        Extensions Hub &rarr;
                    </button>
                </div>
                <div style="padding:10px 14px; background:rgba(234,244,255,0.7); border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm); font-size:12.5px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <strong>ING-104 Milestone Deadline:</strong>
                        <span style="font-family:var(--font-family-mono); font-weight:800; color:var(--deep-frozen-midnight);">2026-12-02</span>
                    </div>
                    <div style="font-size:12px; color:var(--frost-navy-75);">
                        Deliverable package for Attempt #2 submitted on 2026-11-07. Awaiting marksheet evaluation.
                    </div>
                </div>
            </div>
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
    guardian_name = "Dr. Elena Vance"
    guardian_title = profile.guardian_credentials or "Lead Data Architect & Guardian (Batch Orion-24)"

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
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px;">
                <div style="background:rgba(255,255,255,0.9); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--frost-navy-50); font-weight:700; letter-spacing:0.5px;">Reporting Manager / Guardian</div>
                    <div style="font-size:13.5px; font-weight:800; color:var(--deep-frozen-midnight); margin-top:2px;">{escape(guardian_name)}</div>
                    <div style="font-size:11px; color:var(--frost-navy-50); margin-top:1px;">{escape(guardian_title)}</div>
                </div>

                <div style="background:rgba(255,255,255,0.9); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--frost-navy-50); font-weight:700; letter-spacing:0.5px;">Training Cohort</div>
                    <div style="font-size:13.5px; font-weight:800; color:var(--deep-frozen-midnight); margin-top:2px;">{escape(profile.batch_name)}</div>
                    <div style="font-size:11px; color:var(--frost-navy-50); margin-top:1px;">Orion-24 Senior Stream</div>
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
    roadmap_nodes: List[Dict[str, Any]]
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
            '<path d="{}" fill="none" stroke="var(--deep-frozen-midnight)" '
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
                "background: linear-gradient(135deg, rgba(7, 22, 41, 0.94) 0%, rgba(23, 52, 92, 0.96) 100%); "
                "border: 1.5px solid var(--icy-steel); "
                "box-shadow: 0 8px 24px rgba(7, 22, 41, 0.35); "
                "color: var(--snow-white);"
            )
            code_style = "color: var(--icy-steel); font-weight: 800; font-family: var(--font-family-mono); font-size: 11.5px;"
            title_style = "color: var(--snow-white); font-weight: 700; font-size: 14px; margin: 3px 0 2px;"
            desc_style = "color: rgba(234, 244, 255, 0.75); font-size: 11px;"
            status_html = '<span class="status-pill status-approved" style="font-size:10.5px; padding:2px 8px;">Completed</span>'
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
            status_html = '<span class="status-pill status-active" style="font-size:10.5px; padding:2px 8px;">Active • Current</span>'
        else:  # locked
            card_style = (
                "background: rgba(234, 244, 255, 0.45); "
                "border: 1.5px dashed var(--icy-steel-50); "
                "opacity: 0.85; "
                "color: var(--frost-navy-50);"
            )
            lock_ic_12 = get_icon("lock", 12, "margin-right:4px;")
            lock_ic_13 = get_icon("lock", 13, "margin-right:5px;")
            code = f"{lock_ic_12} LOCKED"
            title = f"{lock_ic_13} Milestone {idx + 1} (Locked)"
            category = "Classified Curriculum"
            code_style = "color: var(--frost-navy-50); font-weight: 700; font-family: var(--font-family-mono); font-size: 11.5px;"
            title_style = "color: var(--frost-navy); font-weight: 700; font-size: 14px; margin: 3px 0 2px; opacity: 0.85;"
            desc_style = "color: var(--frost-navy-50); font-size: 11px;"
            status_html = '<span class="status-pill status-locked" style="font-size:10.5px; padding:2px 8px;">Locked</span>'
            onclick = f"window.StarAppBridge.dispatchAction('open_locked_milestone_notice', '{idx + 1}');"
        if state != "locked":
            onclick = f"window.StarAppBridge.dispatchAction('open_badge_detail_modal', '{badge_id}');"

        milestone_els.append(
            '\n        <div class="liquid-glass-card milestone-container-node"'
            ' style="position:absolute;left:{cl}px;top:{ct}px;width:{cw}px;height:{ch}px;'
            'z-index:2;cursor:pointer;{card_style}padding:12px 16px;border-radius:var(--radius-md);'
            'transition:transform 200ms ease, box-shadow 200ms ease;"'
            ' onmouseover="this.style.transform=\'scale(1.03)\'"'
            ' onmouseout="this.style.transform=\'scale(1)\'"'
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

    return """
    <div>
        <div style="text-align:center;margin-bottom:28px;">
            <h2 style="font-size:1.6rem;font-weight:800;color:var(--frost-navy);">Cosmonaut Learning Pathway</h2>
            <p style="font-size:13.5px;color:var(--frost-navy-50);">Follow the gamified curriculum pathway. Each level unlocks as prerequisites and training milestones are approved by your Guardian.</p>
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
        CW=CW, th=total_height,
        fcd=full_curve_d,
        cmpsvg=completed_svg,
        containers="\n".join(milestone_els)
    )

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

    return f"""
    <div style="padding: 2px 0 0 0;">
        <!-- Clean Subheader with Badge Code, Title and Status -->
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid var(--icy-steel-30);">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:3px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-50);">{escape(badge.code)}</span>
                <span style="font-size:15px; font-weight:800; color:var(--frost-navy);">{escape(badge.title)}</span>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:11.5px; font-weight:600; color:var(--frost-navy-50);">Decided by Guardian Dr. Elena Vance</span>
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
# 6.5 PROJECT SUBMISSION WORKSPACE
# ==============================================================================

def render_cosmonaut_submission_workspace(
    badges: List[Badge],
    selected_badge_id: str,
    submissions: List[ProjectSubmission]
) -> str:
    badge_options = []
    for b in badges:
        sel = " selected" if b.id == selected_badge_id else ""
        badge_options.append(f'<option value="{b.id}"{sel}>{escape(b.code)}: {escape(b.title)}</option>')

    return f"""
    <div>
        <div style="margin-bottom:24px; text-align:center;">
            <h2 style="font-size:1.55rem; font-weight:800; color:var(--frost-navy); margin-bottom:6px;">Project Deliverable Submission Portal</h2>
            <p style="font-size:13.5px; color:var(--frost-navy-50);">Provide your technical deliverables, executable scripts, and repository links for formal review.</p>
        </div>

        <div style="display:flex; justify-content:center; width:100%; margin-bottom:32px;">
            <div class="liquid-submission-portal" style="width:100%; max-width:680px; padding:32px 36px;">
                <form id="project-submission-form" onsubmit="event.preventDefault(); window.StarAppBridge.submitCosmonautDeliverables();">
                    <!-- 1. Target Badge Milestone Dropdown -->
                    <div class="liquid-form-group" style="margin-bottom:22px;">
                        <label class="liquid-form-label" for="submission-badge-id">Target Badge Milestone</label>
                        <div class="liquid-select-wrapper">
                            <select id="submission-badge-id" class="liquid-glass-control liquid-glass-select" onchange="window.StarAppBridge.dispatchAction('change_submission_target_badge', this.value)">
                                {"".join(badge_options)}
                            </select>
                        </div>
                        <span class="liquid-form-hint">Choose the milestone badge you are fulfilling with this project.</span>
                    </div>

                    <!-- 2. PDF Document Deliverable Field -->
                    <div class="liquid-form-group" style="margin-bottom:22px;">
                        <label class="liquid-form-label" for="submission-pdf-file">PDF Document Deliverable</label>
                        <input type="file" id="submission-pdf-file" class="liquid-glass-file-input" accept=".pdf">
                        <span class="liquid-form-hint">Upload formal design charter, architecture report, or documentation (.pdf)</span>
                    </div>

                    <!-- 3. Code / Script File Deliverable Field -->
                    <div class="liquid-form-group" style="margin-bottom:22px;">
                        <label class="liquid-form-label" for="submission-code-file">Code / Script File Deliverable</label>
                        <input type="file" id="submission-code-file" class="liquid-glass-file-input" accept=".py,.sql,.zip,.js,.json,.tar.gz,.txt">
                        <span class="liquid-form-hint">Upload executable script, queries, algorithm package, or zip archive (.py, .sql, .zip)</span>
                    </div>

                    <!-- 4. GitHub Repository Link Field -->
                    <div class="liquid-form-group" style="margin-bottom:26px;">
                        <label class="liquid-form-label" for="submission-github-url">GitHub Repository Link</label>
                        <input type="url" id="submission-github-url" class="liquid-glass-control" placeholder="https://github.com/username/project-repo">
                        <span class="liquid-form-hint">Direct link to version-controlled repository or pull request</span>
                    </div>

                    <!-- 5. Submit Button -->
                    <div style="display:flex; justify-content:flex-end; margin-top:28px;">
                        <div class="btn-metal-wrapper" style="width:100%;">
                            <div class="btn-metal-inner"></div>
                            <button type="submit" class="btn-metal" style="width:100%; height:46px; font-size:14px; font-weight:700; letter-spacing:0.3px;">
                                Submit Deliverables for Guardian Assessment →
                            </button>
                        </div>
                    </div>
                </form>
            </div>
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
    # 1. Determine list of selectable badges (the present 4 badges plus any assigned or catalog badges)
    badge_list = list(available_badges) if available_badges else []
    present_4_ids = ["badge_gov_101", "badge_cur_102", "badge_dat_103", "badge_ing_104"]
    existing_ids = {b.id for b in badge_list}
    for pid in present_4_ids:
        if pid not in existing_ids and pid in badges_map:
            badge_list.append(badges_map[pid])

    # If badge_list is still empty, fallback to badges_map
    if not badge_list:
        badge_list = list(badges_map.values())

    # Sort badges to put the present badges in logical progression order
    def badge_order(b: Badge) -> int:
        if b.id in present_4_ids:
            return present_4_ids.index(b.id)
        return 100

    badge_list.sort(key=badge_order)

    # Validate selected_badge_id
    if not selected_badge_id or (selected_badge_id not in [b.id for b in badge_list]):
        selected_badge_id = badge_list[0].id if badge_list else "badge_gov_101"

    # Build options for top-right dropdown
    badge_options = []
    for b in badge_list:
        sel = " selected" if b.id == selected_badge_id else ""
        badge_options.append(f'<option value="{b.id}"{sel}>{escape(b.code)}: {escape(b.title)}</option>')

    # Matching assessments for selected_badge_id
    matching_asms = [a for a in assessments if a.badge_id == selected_badge_id]
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
                        <span style="background:#10B981; color:#FFFFFF; font-size:11px; font-weight:800; padding:3px 9px; border-radius:var(--radius-xs); text-transform:uppercase;">Deadline Extended</span>
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
                        <span style="background:#F59E0B; color:#FFFFFF; font-size:11px; font-weight:800; padding:3px 9px; border-radius:var(--radius-xs); text-transform:uppercase;">Extension Pending</span>
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
        <div>
            <h2 style="font-size:1.55rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">Official Assessment Marksheets</h2>
            <div style="font-size:13px; color:var(--frost-navy-50);">Guardian evaluation rubric scores and performance breakdown.</div>
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
                <strong>{escape(badge_title)}</strong> has been allocated by your Guardian. Once you submit project deliverables, Dr. Elena Vance will publish your marksheet across the 50-mark universal rubric.
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
            status_pill = '<span class="status-pill" style="font-size:11px; font-weight:800; padding:4px 10px; background:#10B981; color:#FFFFFF; border-radius:var(--radius-xs); display:inline-flex; align-items:center; gap:4px;">&#10003; Approved</span>'
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
            status_pill = '<span class="status-pill" style="font-size:11px; font-weight:800; padding:4px 10px; background:#F59E0B; color:#FFFFFF; border-radius:var(--radius-xs); display:inline-flex; align-items:center; gap:4px;">&#9203; Pending Review</span>'
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
        <div style="margin-bottom:24px;">
            <h2 style="font-size:1.55rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px;">Milestone Deadline Extension Portal</h2>
            <p style="font-size:13.5px; color:var(--frost-navy-50);">Request scheduling adjustments for active milestones and track Guardian evaluations in real-time.</p>
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
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:18px; margin-bottom:18px;">
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
                        <textarea id="ext-reason" class="liquid-glass-control" style="min-height:90px; padding:12px 14px; resize:vertical; font-family:var(--font-family-base); line-height:1.5;" placeholder="Describe the unexpected complexity, data pipeline latency, or algorithmic research requiring additional engineering time..." required></textarea>
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
        <div style="margin-bottom:20px;">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Academy Announcement Center</h2>
            <p style="font-size:13px; color:var(--frost-navy-50);">Notices and schedule updates broadcasted by Dr. Elena Vance.</p>
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
    rows = []
    for act in activities:
        rows.append(f"""
        <tr>
            <td style="font-family:var(--font-family-mono); font-size:12px; white-space:nowrap;">{escape(act.timestamp[:19].replace('T', ' '))}</td>
            <td>{render_status_pill(act.event_type)}</td>
            <td>
                <div style="font-weight:700;">{escape(act.summary)}</div>
                <div style="font-size:12px; color:var(--frost-navy-50);">{escape(act.details)}</div>
            </td>
            <td>{escape(act.badge_id or "Academy")}</td>
        </tr>
        """)

    return f"""
    <div>
        <div style="margin-bottom:20px;">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Personal Activity Feed</h2>
            <p style="font-size:13px; color:var(--frost-navy-50);">Your verified training progression, milestone submissions, and marksheet publications.</p>
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
        </div>
    </div>
    """

