"""
STARAPP GUARDIAN PORTAL VIEWS
Implements the 7 core workspaces for training managers and mentors.
"""

from typing import List, Dict, Any, Optional
from starapp.models import User, Badge, ProjectSubmission, AssessmentMarksheet, LearningMaterial, DeadlineExtension, Announcement, ActivityEvent
from starapp.views_common import (
    get_icon,
    escape, render_liquid_card, render_metal_button, render_liquid_button,
    render_status_pill, render_standard_marksheet, render_9point_timeline
)
from starapp.assessment import RUBRIC_CRITERIA

# ==============================================================================
# GUARDIAN SIDEBAR
# ==============================================================================

def render_guardian_sidebar(active_view: str, current_user: User, pending_reviews_count: int, pending_extensions_count: int) -> str:
    nav_items = [
        {"id": "g_dashboard", "label": "Batch Dashboard", "icon": '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>', "badge": 0},
        {"id": "g_allotment", "label": "Badge Allotment", "icon": '<svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>', "badge": 0},
        {"id": "g_reviews", "label": "Project Reviews", "icon": '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>', "badge": pending_reviews_count},
        {"id": "g_materials", "label": "Learning Materials", "icon": '<svg viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>', "badge": 0},
        {"id": "g_extensions", "label": "Extension Requests", "icon": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', "badge": pending_extensions_count}
    ]

    links_html = []
    for item in nav_items:
        is_active = item["id"] == active_view
        cls = "nav-link active" if is_active else "nav-link"
        badge_html = f'<span class="nav-badge">{item["badge"]}</span>' if item["badge"] > 0 else ""
        links_html.append(f"""
        <li class="nav-item">
            <a class="{cls}" onclick="window.StarAppBridge.dispatchAction('nav_guardian', '{item["id"]}')">
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
                <div class="brand-subtitle">GUARDIAN PORTAL</div>
            </div>
        </div>

        <div class="role-badge-pill">
            <span class="role-badge-label">Role</span>
            <span class="role-badge-val">Training Mentor</span>
        </div>

        <ul class="sidebar-nav">
            {"".join(links_html)}
            <li class="nav-item" style="margin-top:12px; padding-top:10px; border-top:1px solid var(--icy-steel-30);">
                <a class="nav-link" onclick="window.open('index.html?role=cosmonaut', '_blank');" style="color:var(--deep-frozen-midnight); font-weight:700;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    <span>Cosmonaut Window ↗</span>
                </a>
            </li>
        </ul>

        <div class="sidebar-footer">
            <div class="user-mini-card" style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <div class="user-avatar">{escape(current_user.avatar)}</div>
                    <div class="user-details">
                        <div class="user-name">{escape(current_user.name)}</div>
                        <div class="user-role-text">Batch Orion-24 Lead</div>
                    </div>
                </div>
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('logout', '{{}}')" title="Sign Out" style="padding:4px 8px; font-size:11px; font-weight:700;">Sign Out</button>
            </div>
        </div>
    </aside>
    """

# ==============================================================================
# 7.1 GUARDIAN DASHBOARD (Batch aggregate vs. Individual Cosmonaut Selector)
# ==============================================================================

def render_guardian_dashboard(
    batch_analytics: Dict[str, Any],
    cosmonauts: List[User],
    selected_cosmo_id: str,
    selected_cosmo_data: Optional[Dict[str, Any]] = None
) -> str:
    from starapp.storage import store
    from starapp.assessment import calculate_cosmonaut_score_summary

    # Cosmonaut selector dropdown options
    selector_options = ['<option value="all"' + (' selected' if selected_cosmo_id == 'all' else '') + '>All Cosmonauts (Batch Aggregate Analytics)</option>']
    for c in cosmonauts:
        sel = " selected" if c.id == selected_cosmo_id else ""
        selector_options.append(f'<option value="{c.id}"{sel}>{escape(c.name)} ({c.id})</option>')

    selector_bar = f"""
    <div class="liquid-glass-card" style="display:flex; align-items:center; justify-content:space-between; margin-bottom:24px; background:linear-gradient(135deg, rgba(255,255,255,0.92) 0%, rgba(234,244,255,0.75) 100%); padding:14px 22px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-50); box-shadow:0 4px 16px rgba(7,22,41,0.04); flex-wrap:wrap; gap:12px;">
        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
            <label style="font-size:12.5px; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px;">Analytics Scope:</label>
            <div class="liquid-select-wrapper" style="min-width:280px; width:auto;">
                <select class="liquid-glass-control liquid-glass-select" style="font-weight:700;" onchange="window.StarAppBridge.dispatchAction('select_guardian_cosmo_filter', this.value)">
                    {"".join(selector_options)}
                </select>
            </div>
        </div>
        <div style="font-size:12px; color:var(--frost-navy-50);">
            Scope: <strong>{"Batch Orion-24 Telemetry (All Cosmonauts)" if selected_cosmo_id == "all" else "Individual Cadet Dossier"}</strong>
        </div>
    </div>
    """

    if selected_cosmo_id != "all" and selected_cosmo_data:
        # Render Individual Cosmonaut Dossier
        return selector_bar + render_individual_cosmo_dossier(selected_cosmo_data)

    # 1. High-Level Executive Batch KPIs
    batch_avg_score = batch_analytics.get("batch_avg_score", 0.0)
    batch_avg_pct = batch_analytics.get("batch_avg_pct", 0.0)
    completion_rate = batch_analytics.get("completion_rate", 0.0)
    total_assigned = batch_analytics.get("total_assigned_badges", 0)
    completed_badges = batch_analytics.get("completed_badges", 0)
    pending_reviews = batch_analytics.get("pending_reviews", 0)

    kpis = f"""
    <div class="kpi-grid">
        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Enrolled Cadets</span>
                <div class="kpi-icon-bubble">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                </div>
            </div>
            <div class="kpi-value">{batch_analytics["total_cosmonauts"]}</div>
            <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700;">Active Cohort: Batch Orion-24</div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Batch Completion Velocity</span>
                <div class="kpi-icon-bubble">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                </div>
            </div>
            <div class="kpi-value">{completed_badges} / {total_assigned}</div>
            <div style="height:6px; border-radius:var(--radius-full); background:rgba(157,183,213,0.3); overflow:hidden; margin:8px 0 6px 0;">
                <div style="height:100%; width:{completion_rate}%; background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
            </div>
            <div class="kpi-subtext" style="color:#2E7D32; font-weight:700;">▲ {completion_rate}% Aggregate milestone completion rate</div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Pending Submissions</span>
                <div class="kpi-icon-bubble">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>
            </div>
            <div class="kpi-value">{pending_reviews}</div>
            <div class="kpi-subtext" style="color:{"#C62828" if pending_reviews > 0 else "var(--frost-navy-50)"}; font-weight:700;">
                {"Requires Evaluation" if pending_reviews > 0 else "Review queue cleared"}
            </div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Batch Standard GPA</span>
                <div class="kpi-icon-bubble">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                </div>
            </div>
            <div class="kpi-value">{batch_avg_score:.1f} <span style="font-size:14px; opacity:0.65; font-weight:600;">/ 50.0</span></div>
            <div class="kpi-subtext" style="color:var(--deep-frozen-midnight); font-weight:700;">{batch_avg_pct:.1f}% Batch Average &bull; Tier 1 Quality</div>
        </div>
    </div>
    """

    # 2. Criterion-wise batch performance bars & diagnostic insights
    crit_bars = []
    crit_avgs = batch_analytics.get("criterion_averages", {})
    sorted_crits = sorted(RUBRIC_CRITERIA, key=lambda c: crit_avgs.get(c["key"], 0.0), reverse=True)

    for c in RUBRIC_CRITERIA:
        avg_val = crit_avgs.get(c["key"], 0.0)
        pct = (avg_val / 10.0) * 100.0
        crit_bars.append(f"""
        <div style="margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <div>
                    <span style="font-size:13px; font-weight:700; color:var(--frost-navy);">{escape(c["title"])}</span>
                    <span style="font-size:11px; color:var(--frost-navy-50); margin-left:6px;">({escape(c["desc"])})</span>
                </div>
                <span style="font-size:13px; font-weight:800; color:var(--deep-frozen-midnight);">{avg_val:.1f} / 10.0 ({pct:.1f}%)</span>
            </div>
            <div style="height:10px; border-radius:var(--radius-full); background:rgba(157,183,213,0.3); overflow:hidden;">
                <div style="height:100%; width:{pct}%; border-radius:var(--radius-full); background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
            </div>
        </div>
        """)

    top_crit = sorted_crits[0] if sorted_crits else None
    low_crit = sorted_crits[-1] if sorted_crits else None

    batch_diagnostic_html = f"""
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; padding-top:14px; border-top:1.5px solid var(--icy-steel-30);">
        <div style="background:rgba(23,52,92,0.05); padding:10px 14px; border-radius:var(--radius-sm); border-left:3px solid var(--deep-frozen-midnight);">
            <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:2px;">{get_icon("award", 13, "margin-right:5px;")} Cohort Core Competency</div>
            <div style="font-size:12.5px; font-weight:700; color:var(--frost-navy);">{escape(top_crit["title"] if top_crit else "Business Understanding")} ({crit_avgs.get(top_crit["key"], 0.0):.1f}/10)</div>
            <p style="font-size:11.5px; color:var(--frost-navy-75); margin:2px 0 0 0;">Batch demonstrates exemplary domain grounding and compliance alignment across evaluations.</p>
        </div>
        <div style="background:rgba(157,183,213,0.14); padding:10px 14px; border-radius:var(--radius-sm); border-left:3px solid var(--icy-steel);">
            <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy); margin-bottom:2px;">{get_icon("target", 13, "margin-right:5px;")} Pedagogical Focus Area</div>
            <div style="font-size:12.5px; font-weight:700; color:var(--frost-navy);">{escape(low_crit["title"] if low_crit else "Testing & Resilience")} ({crit_avgs.get(low_crit["key"], 0.0):.1f}/10)</div>
            <p style="font-size:11.5px; color:var(--frost-navy-75); margin:2px 0 0 0;">Recommend scheduling technical QA office hours to reinforce automated regression coverage.</p>
        </div>
    </div>
    """

    crit_card = render_liquid_card(
        title="Batch Criterion-Wise Competency Diagnostic (Standard 50-Mark Rubric)",
        subtitle="Aggregated across all approved badge evaluations in Batch Orion-24",
        content="".join(crit_bars) + batch_diagnostic_html
    )

    # 3. Enhanced Cosmonauts Roster with Detailed Analytics
    roster_rows = []
    for c in cosmonauts:
        c_asms = store.get_assessments_for_cosmonaut(c.id)
        c_summary = calculate_cosmonaut_score_summary(c_asms)
        c_completed = c_summary.get("approved_count", 0)
        c_avg = c_summary.get("average_marks", 0.0)
        c_pct = c_summary.get("average_percentage", 0.0)

        # Performance Tier Pill
        if c_avg >= 45.0:
            tier_pill = '<span class="status-pill status-approved" style="font-size:10.5px;">Honors Tier</span>'
        elif c_avg >= 35.0:
            tier_pill = '<span class="status-pill status-active" style="font-size:10.5px;">Production Ready</span>'
        elif c_completed > 0:
            tier_pill = '<span class="status-pill status-pending" style="font-size:10.5px;">Needs Improvement</span>'
        else:
            tier_pill = '<span class="status-pill" style="opacity:0.6; font-size:10.5px;">Sprint Initiated</span>'

        roster_rows.append(f"""
        <tr>
            <td style="font-weight:700;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <div class="user-avatar" style="width:30px; height:30px; font-size:11px; font-weight:800;">{escape(c.avatar)}</div>
                    <div>
                        <div style="color:var(--frost-navy);">{escape(c.name)}</div>
                        <div style="font-size:11px; font-family:var(--font-family-mono); color:var(--frost-navy-50);">{escape(c.id)}</div>
                    </div>
                </div>
            </td>
            <td style="font-size:12px; font-family:var(--font-family-mono);">{escape(c.email)}</td>
            <td style="text-align:center;">
                <span style="font-weight:800; color:var(--deep-frozen-midnight);">{c_completed}</span> / 5 Badges
            </td>
            <td style="text-align:center;">
                <span style="font-weight:800; color:var(--deep-frozen-midnight);">{c_avg:.1f}</span> <span style="font-size:11px; opacity:0.6;">/ 50</span> ({c_pct:.1f}%)
            </td>
            <td style="text-align:center;">{tier_pill}</td>
            <td style="text-align:right;">
                <button type="button" class="btn-metal btn-sm" style="padding:4px 12px; font-size:11.5px;" onclick="window.StarAppBridge.dispatchAction('select_guardian_cosmo_filter', '{c.id}')">
                    Inspect Dossier →
                </button>
            </td>
        </tr>
        """)

    roster_table = f"""
    <div class="table-responsive">
        <table class="star-table">
            <thead>
                <tr>
                    <th style="width:28%;">Cosmonaut Cadet</th>
                    <th style="width:22%;">Contact Email</th>
                    <th style="width:14%; text-align:center;">Milestones</th>
                    <th style="width:16%; text-align:center;">Average GPA</th>
                    <th style="width:10%; text-align:center;">Standing</th>
                    <th style="width:10%; text-align:right;">Actions</th>
                </tr>
            </thead>
            <tbody>
                {"".join(roster_rows)}
            </tbody>
        </table>
    </div>
    """

    roster_card = render_liquid_card(
        title="Batch Orion-24 Cadet Roster & Performance Matrix",
        subtitle="Live telemetry across all enrolled cadets. Select any Cosmonaut to inspect their private marksheet dossier, submissions, and timeline.",
        content=roster_table
    )

    return f"""
    <div>
        {selector_bar}
        {kpis}
        <div style="display:grid; grid-template-columns:1fr; gap:24px; margin-bottom:24px;">
            {crit_card}
            {roster_card}
        </div>
    </div>
    """

def render_individual_cosmo_dossier(data: Dict[str, Any]) -> str:
    cosmo = data["cosmonaut"]
    profile = data["profile"]
    summary = data["score_summary"]
    asms = data["assessments"]
    subs = data["submissions"]

    skills_pills = "".join([f'<span class="status-pill status-active" style="margin:2px;">{escape(s)}</span>' for s in profile.skills]) or '<span style="font-size:12px; opacity:0.6;">No skills entered.</span>'
    certs_html = "".join([f'<li style="font-size:13px; margin-bottom:4px;"><strong>{escape(c.get("name",""))}</strong> — {escape(c.get("issuer",""))} ({escape(c.get("year",""))})</li>' for c in profile.certifications]) or '<span style="font-size:12px; opacity:0.6;">No certifications entered.</span>'

    # Marksheets list
    marksheet_items = []
    for a in asms:
        marksheet_items.append(f"""
        <div style="margin-bottom:12px; padding:12px; border-radius:var(--radius-sm); background:rgba(255,255,255,0.7); border:1px solid var(--icy-steel-30); display:flex; align-items:center; justify-content:space-between;">
            <div>
                <div style="font-weight:700; color:var(--deep-frozen-midnight);">{escape(a.badge_id)} — Attempt #{a.attempt_number}</div>
                <div style="font-size:12px; color:var(--frost-navy-50);">Score: <strong>{a.total_marks}/50</strong> ({a.percentage}%) on {escape(a.reviewed_at[:10])}</div>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                {render_status_pill(a.decision)}
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('view_marksheet', '{{\"marksheet_id\": \"{a.id}\"}}')">Inspect Marksheet</button>
            </div>
        </div>
        """)

    marksheets_html = "".join(marksheet_items) if marksheet_items else "<p style='font-size:13px; opacity:0.6;'>No evaluated marksheets for this Cosmonaut.</p>"

    return f"""
    <div>
        <div class="kpi-grid">
            <div class="liquid-glass-card kpi-card">
                <div class="kpi-header"><span class="kpi-title">Completed Badges</span></div>
                <div class="kpi-value">{summary["approved_count"]}</div>
                <div class="kpi-subtext">Approved credentials</div>
            </div>
            <div class="liquid-glass-card kpi-card">
                <div class="kpi-header"><span class="kpi-title">Average Assessment</span></div>
                <div class="kpi-value">{summary["average_marks"]} <span style="font-size:14px; opacity:0.6;">/ 50</span></div>
                <div class="kpi-subtext">{summary["average_percentage"]}% Standard score</div>
            </div>
            <div class="liquid-glass-card kpi-card">
                <div class="kpi-header"><span class="kpi-title">Highest Score</span></div>
                <div class="kpi-value">{summary["best_marks"]} <span style="font-size:14px; opacity:0.6;">/ 50</span></div>
                <div class="kpi-subtext">Personal best evaluation</div>
            </div>
            <div class="liquid-glass-card kpi-card">
                <div class="kpi-header"><span class="kpi-title">Total Submissions</span></div>
                <div class="kpi-value">{len(subs)}</div>
                <div class="kpi-subtext">Total deliverable uploads</div>
            </div>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px;">
            {render_liquid_card(
                title=f"Cosmonaut Profile — {cosmo.name}",
                subtitle=f"Batch: {profile.batch_name} | Assigned Mentor: {profile.assigned_guardian_id}",
                content=f'''
                <div style="margin-bottom:12px;">
                    <strong style="font-size:12px; text-transform:uppercase; color:var(--deep-frozen-midnight);">Skills:</strong>
                    <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:6px;">{skills_pills}</div>
                </div>
                <div>
                    <strong style="font-size:12px; text-transform:uppercase; color:var(--deep-frozen-midnight);">Certifications:</strong>
                    <ul style="margin-top:6px; padding-left:18px;">{certs_html}</ul>
                </div>
                '''
            )}

            {render_liquid_card(
                title="Historical Assessment Marksheets",
                subtitle="All reviewed submission attempts using the 50-mark rubric",
                content=marksheets_html
            )}
        </div>
    </div>
    """

# ==============================================================================
# 7.2 BADGE ALLOTMENT & TIMELINE MANAGEMENT
# ==============================================================================

def render_guardian_badge_allotment(
    badges: List[Badge],
    cosmonauts: List[User],
    filter_tab: str = "all"
) -> str:
    """
    Renders Guardian Badge Catalog & Allotment Manager in a clean 2-in-a-row card layout.
    Displays clear visual timeline steppers for all badges, and supports badge publication and revocation.
    """
    allocated = []
    unallocated = []

    for b in badges:
        is_alloc = getattr(b, "is_allocated", True)
        if is_alloc:
            allocated.append(b)
        else:
            unallocated.append(b)

    completed_codes = {"GOV-101", "CUR-102", "DAT-103"}

    def render_timeline_stepper(dt: dict, is_allocated: bool) -> str:
        alloc_date = dt.get("assignment_date", "TBD")
        learn_dates = f"{dt.get('learning_start_date', 'TBD')} → {dt.get('learning_end_date', 'TBD')}"
        proj_dates = f"{dt.get('project_start_date', 'TBD')} → {dt.get('project_end_date', 'TBD')}"
        sub_deadline = dt.get("submission_deadline", "TBD")
        review_date = dt.get("review_date", "TBD")
        award_date = dt.get("expected_award_date", "TBD")

        box_border = "border:1px solid var(--icy-steel-50); background:rgba(234,244,255,0.4);" if is_allocated else "border:1px dashed var(--icy-steel); background:rgba(234,244,255,0.25);"

        return f"""
        <div style="{box_border} border-radius:var(--radius-sm); padding:10px 12px; margin:14px 0 16px 0;">
            <div style="font-size:10.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--deep-frozen-midnight); margin-bottom:8px; display:flex; align-items:center; justify-content:space-between;">
                <span>{get_icon("calendar", 13, "margin-right:5px;")} Milestone Timeline Schedule</span>
                <span style="font-size:10px; font-weight:600; color:var(--frost-navy-50);">{"Active Sequence" if is_allocated else "Target Schedule"}</span>
            </div>

            <!-- 2 Rows of 3 Connected Timeline Milestones -->
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; margin-bottom:8px;">
                <div style="background:rgba(255,255,255,0.85); border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:6px 8px;">
                    <div style="font-size:10px; color:var(--frost-navy-50); font-weight:700; display:flex; align-items:center; gap:4px;">
                        <span>{get_icon("clipboard", 12)}</span> ALLOCATED
                    </div>
                    <div style="font-family:var(--font-family-mono); font-size:11.5px; font-weight:700; color:var(--frost-navy); margin-top:2px;">
                        {escape(alloc_date)}
                    </div>
                </div>

                <div style="background:rgba(255,255,255,0.85); border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:6px 8px;">
                    <div style="font-size:10px; color:var(--frost-navy-50); font-weight:700; display:flex; align-items:center; gap:4px;">
                        <span>{get_icon("book", 12)}</span> LEARNING
                    </div>
                    <div style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:700; color:var(--frost-navy); margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                        {escape(learn_dates)}
                    </div>
                </div>

                <div style="background:rgba(255,255,255,0.85); border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:6px 8px;">
                    <div style="font-size:10px; color:var(--frost-navy-50); font-weight:700; display:flex; align-items:center; gap:4px;">
                        <span>{get_icon("code", 12)}</span> SPRINT
                    </div>
                    <div style="font-family:var(--font-family-mono); font-size:10.5px; font-weight:700; color:var(--frost-navy); margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                        {escape(proj_dates)}
                    </div>
                </div>
            </div>

            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px;">
                <div style="background:rgba(211,47,47,0.06); border:1.5px solid rgba(211,47,47,0.3); border-radius:var(--radius-xs); padding:6px 8px;">
                    <div style="font-size:10px; color:#D32F2F; font-weight:800; display:flex; align-items:center; gap:4px;">
                        <span>{get_icon("clock", 12, "color:#D32F2F;")}</span> DEADLINE
                    </div>
                    <div style="font-family:var(--font-family-mono); font-size:11.5px; font-weight:800; color:#D32F2F; margin-top:2px;">
                        {escape(sub_deadline)}
                    </div>
                </div>

                <div style="background:rgba(255,255,255,0.85); border:1px solid var(--icy-steel-30); border-radius:var(--radius-xs); padding:6px 8px;">
                    <div style="font-size:10px; color:var(--frost-navy-50); font-weight:700; display:flex; align-items:center; gap:4px;">
                        <span>{get_icon("scale", 12)}</span> REVIEW
                    </div>
                    <div style="font-family:var(--font-family-mono); font-size:11.5px; font-weight:700; color:var(--frost-navy); margin-top:2px;">
                        {escape(review_date)}
                    </div>
                </div>

                <div style="background:rgba(46,125,50,0.06); border:1.5px solid rgba(46,125,50,0.3); border-radius:var(--radius-xs); padding:6px 8px;">
                    <div style="font-size:10px; color:#2E7D32; font-weight:800; display:flex; align-items:center; gap:4px;">
                        <span>{get_icon("award", 12, "color:#2E7D32;")}</span> AWARD
                    </div>
                    <div style="font-family:var(--font-family-mono); font-size:11.5px; font-weight:800; color:#2E7D32; margin-top:2px;">
                        {escape(award_date)}
                    </div>
                </div>
            </div>
        </div>
        """

    # Build Allocated Badges Cards (Clean, 2 in a row)
    allocated_cards = []
    for b in allocated:
        dt = b.default_timeline or {}
        is_completed = b.code in completed_codes or b.id in ["badge_gov_101", "badge_cur_102", "badge_dat_103"]

        check_ic_11 = get_icon("check", 11, "margin-right:4px;")
        flash_ic_11 = get_icon("flash", 11, "margin-right:4px;")
        revoke_ic_13 = get_icon("revoke", 13, "margin-right:4px;")

        if is_completed:
            status_pill = f'<span class="status-pill status-approved" style="font-weight:700; font-size:11px; padding:3px 9px;">{check_ic_11} Certified</span>'
            card_border = "border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(234,244,255,0.88) 100%);"
            revoke_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-weight:700; color:#D32F2F; border-color:rgba(211,47,47,0.35); background:rgba(211,47,47,0.04); font-size:11px;" onclick="if(confirm('Revoke milestone {escape(b.code)} from Cosmonaut roadmap?')) window.StarAppBridge.dispatchAction('revoke_badge', '{b.id}')">{revoke_ic_13} Revoke</button>"""
        else:
            status_pill = f'<span class="status-pill status-active" style="font-weight:700; font-size:11px; padding:3px 9px; background:var(--deep-frozen-midnight); color:var(--snow-white);">{flash_ic_11} In Progress</span>'
            card_border = "border:2px solid var(--deep-frozen-midnight); box-shadow:0 0 0 3px rgba(23,52,92,0.1); background:linear-gradient(135deg, rgba(234,244,255,0.96) 0%, rgba(255,255,255,0.98) 100%);"
            revoke_btn = f"""<button type="button" class="btn-secondary btn-sm" style="font-weight:700; color:#D32F2F; border-color:rgba(211,47,47,0.35); background:rgba(211,47,47,0.04); font-size:11px;" onclick="if(confirm('Revoke milestone {escape(b.code)} from Cosmonaut roadmap?')) window.StarAppBridge.dispatchAction('revoke_badge', '{b.id}')">{revoke_ic_13} Revoke</button>"""

        timeline_html = render_timeline_stepper(dt, is_allocated=True)

        allocated_cards.append(f"""
        <div class="liquid-glass-card" style="{card_border} border-radius:var(--radius-md); padding:18px 20px; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <!-- Header: Code, Title, Category, Status -->
                <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:8px;">
                    <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                        <span style="font-family:var(--font-family-mono); font-size:12.5px; font-weight:800; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 8px; border-radius:var(--radius-xs);">{escape(b.code)}</span>
                        <span style="font-size:11px; font-weight:700; background:rgba(23,52,92,0.08); color:var(--frost-navy); padding:2px 7px; border-radius:var(--radius-xs);">{escape(b.category)}</span>
                    </div>
                    {status_pill}
                </div>
                <h4 style="font-size:1.18rem; font-weight:800; color:var(--frost-navy); margin:4px 0 0 0; line-height:1.3;">{escape(b.title)}</h4>

                <!-- Visual Timeline Stepper -->
                {timeline_html}
            </div>

            <!-- Clean Action Buttons Row -->
            <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; padding-top:10px; border-top:1px solid var(--icy-steel-30); flex-wrap:wrap;">
                <div style="display:flex; gap:6px;">
                    <button type="button" class="btn-metal btn-sm" style="font-weight:700; font-size:11.5px; display:flex; align-items:center; gap:5px;" onclick="window.StarAppBridge.dispatchAction('open_edit_badge_modal', '{b.id}')">
                        {get_icon("calendar", 13, "margin-right:4px;")} Update Timeline
                    </button>
                    <button type="button" class="btn-secondary btn-sm" style="font-weight:600; font-size:11.5px;" onclick="window.StarAppBridge.dispatchAction('open_badge_detail_modal', '{b.id}')">
                        {get_icon("eye", 13, "margin-right:4px;")} View Timeline
                    </button>
                </div>
                {revoke_btn}
            </div>
        </div>
        """)

    # Build Not Allocated Yet Cards (Clean, 2 in a row)
    unallocated_cards = []
    for b in unallocated:
        dt = b.default_timeline or {}
        timeline_html = render_timeline_stepper(dt, is_allocated=False)

        unallocated_cards.append(f"""
        <div class="liquid-glass-card" style="border:1.5px dashed var(--icy-steel); background:rgba(234,244,255,0.45); border-radius:var(--radius-md); padding:18px 20px; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <!-- Header: Code, Title, Category, Status -->
                <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:8px;">
                    <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                        <span style="font-family:var(--font-family-mono); font-size:12.5px; font-weight:800; background:rgba(23,52,92,0.15); color:var(--frost-navy); padding:2px 8px; border-radius:var(--radius-xs);">{escape(b.code)}</span>
                        <span style="font-size:11px; font-weight:700; background:rgba(23,52,92,0.06); color:var(--frost-navy); padding:2px 7px; border-radius:var(--radius-xs);">{escape(b.category)}</span>
                    </div>
                    <span class="status-pill status-locked" style="font-weight:700; font-size:11px; padding:3px 9px;">{get_icon("lock", 11, "margin-right:4px;")} Not Allocated</span>
                </div>
                <h4 style="font-size:1.18rem; font-weight:800; color:var(--frost-navy); margin:4px 0 0 0; line-height:1.3;">{escape(b.title)}</h4>

                <!-- Visual Timeline Stepper -->
                {timeline_html}
            </div>

            <!-- Clean Action Buttons Row -->
            <div style="display:flex; align-items:center; justify-content:flex-end; gap:8px; padding-top:10px; border-top:1px solid var(--icy-steel-30); flex-wrap:wrap;">
                <button type="button" class="btn-secondary btn-sm" style="font-weight:700; font-size:11.5px;" onclick="window.StarAppBridge.dispatchAction('open_edit_badge_modal', '{b.id}')">
                    {get_icon("calendar", 13, "margin-right:4px;")} Set Timeline
                </button>
                <button type="button" class="btn-metal btn-sm" style="font-weight:800; font-size:11.5px; display:flex; align-items:center; gap:5px;" onclick="window.StarAppBridge.dispatchAction('publish_and_unlock_badge', '{b.id}')">
                    {get_icon("rocket", 13, "margin-right:4px;")} Publish to Cosmonaut
                </button>
            </div>
        </div>
        """)

    create_btn = render_metal_button(f'{get_icon("plus", 13, "margin-right:4px;")} Create New Milestone', "open_create_badge_modal", "{}")

    # Segmented Tab Filtering
    st_all = "background:var(--deep-frozen-midnight); color:var(--snow-white); font-weight:800;" if filter_tab == "all" else "background:rgba(255,255,255,0.75); color:var(--frost-navy); font-weight:600;"
    st_alloc = "background:var(--deep-frozen-midnight); color:var(--snow-white); font-weight:800;" if filter_tab == "allocated" else "background:rgba(255,255,255,0.75); color:var(--frost-navy); font-weight:600;"
    st_unalloc = "background:var(--deep-frozen-midnight); color:var(--snow-white); font-weight:800;" if filter_tab == "unallocated" else "background:rgba(255,255,255,0.75); color:var(--frost-navy); font-weight:600;"

    tabs_html = f"""
    <div style="display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap;">
        <button type="button" class="btn-secondary btn-sm" style="{st_all} padding:6px 14px; border-radius:var(--radius-sm);" onclick="window.StarAppBridge.dispatchAction('filter_guardian_allotment', 'all')">
            {get_icon("globe", 13, "margin-right:5px;")} All Milestones ({len(badges)})
        </button>
        <button type="button" class="btn-secondary btn-sm" style="{st_alloc} padding:6px 14px; border-radius:var(--radius-sm);" onclick="window.StarAppBridge.dispatchAction('filter_guardian_allotment', 'allocated')">
            {get_icon("target", 13, "margin-right:5px;")} Allocated Badges ({len(allocated)})
        </button>
        <button type="button" class="btn-secondary btn-sm" style="{st_unalloc} padding:6px 14px; border-radius:var(--radius-sm);" onclick="window.StarAppBridge.dispatchAction('filter_guardian_allotment', 'unallocated')">
            {get_icon("lock", 11, "margin-right:4px;")} Not Allocated Yet ({len(unallocated)})
        </button>
    </div>
    """

    # Sections in 2-in-a-row responsive grid
    sections = []
    if filter_tab in ["all", "allocated"]:
        sections.append(f"""
        <div style="margin-bottom:30px;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; border-bottom:1.5px solid var(--icy-steel-30); padding-bottom:8px;">
                <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0; display:flex; align-items:center; gap:8px;">
                    <span>{get_icon("clipboard", 16, "margin-right:6px;")}</span> Allocated Badges ({len(allocated)})
                </h3>
                <span class="status-pill status-approved" style="font-weight:700;">{len(allocated)} Active on Roadmap</span>
            </div>
            <!-- 2 Badges in a Row Responsive Grid -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(440px, 1fr)); gap:18px;">
                {"".join(allocated_cards)}
            </div>
        </div>
        """)

    if filter_tab in ["all", "unallocated"]:
        sections.append(f"""
        <div style="margin-bottom:30px;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; border-bottom:1.5px solid var(--icy-steel-30); padding-bottom:8px;">
                <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0; display:flex; align-items:center; gap:8px;">
                    <span>{get_icon("lock", 16, "margin-right:6px;")}</span> Not Allocated Yet ({len(unallocated)})
                </h3>
                <span class="status-pill status-locked" style="font-weight:700;">{len(unallocated)} In Catalog</span>
            </div>
            <!-- 2 Badges in a Row Responsive Grid -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(440px, 1fr)); gap:18px;">
                {"".join(unallocated_cards)}
            </div>
        </div>
        """)

    return f"""
    <div>
        <!-- Metric Counters Top Row -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:14px; margin-bottom:20px;">
            <div class="liquid-glass-card" style="padding:14px 18px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel);">
                <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--frost-navy-50);">Total Catalog Milestones</div>
                <div style="font-size:1.6rem; font-weight:900; color:var(--deep-frozen-midnight);">{len(badges)} Badges</div>
                <div style="font-size:11px; color:var(--frost-navy-75); margin-top:2px;">Curriculum progression roadmap</div>
            </div>
            <div class="liquid-glass-card" style="padding:14px 18px; border-radius:var(--radius-sm); border:1.5px solid var(--deep-frozen-midnight); background:rgba(234,244,255,0.6);">
                <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight);">Allocated Badges</div>
                <div style="font-size:1.6rem; font-weight:900; color:var(--deep-frozen-midnight);">{len(allocated)} Badges</div>
                <div style="font-size:11px; color:#2E7D32; font-weight:700; margin-top:2px;">Active on cohort roadmap</div>
            </div>
            <div class="liquid-glass-card" style="padding:14px 18px; border-radius:var(--radius-sm); border:1px dashed var(--icy-steel);">
                <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--frost-navy-50);">Not Allocated Yet</div>
                <div style="font-size:1.6rem; font-weight:900; color:var(--frost-navy);">{len(unallocated)} Badges</div>
                <div style="font-size:11px; color:var(--frost-navy-50); margin-top:2px;">Ready to schedule & publish</div>
            </div>
        </div>

        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
            <div>
                <h2 style="font-size:1.45rem; font-weight:800; color:var(--frost-navy); margin:0;">Badge Catalog & Allotment Manager</h2>
                <p style="font-size:13px; color:var(--frost-navy-50); margin:3px 0 0 0;">Schedule milestone timelines, update deadlines, and publish or revoke badge roadmaps.</p>
            </div>
            {create_btn}
        </div>

        {tabs_html}

        <div>
            {"".join(sections)}
        </div>
    </div>
    """

# ==============================================================================
# 7.3 PROJECT REVIEW & ASSESSMENT MANAGEMENT (Universal 50-Mark Rubric)
# ==============================================================================

def render_guardian_review_queue(
    submissions: List[ProjectSubmission],
    assessments_by_sub: Dict[str, AssessmentMarksheet],
    badges_map: Dict[str, Badge],
    cosmonauts_map: Dict[str, User],
    status_filter: str = "all"
) -> str:
    # Filter submissions
    filtered = submissions
    if status_filter != "all":
        filtered = [s for s in submissions if s.status == status_filter]

    filter_buttons = []
    for f_id, f_label in [("all", "All Submissions"), ("pending", "Pending Review"), ("approved", "Approved"), ("resubmission_requested", "Resubmission Requested")]:
        is_active = f_id == status_filter
        st = "background:var(--deep-frozen-midnight); color:var(--snow-white);" if is_active else "background:rgba(255,255,255,0.7); color:var(--frost-navy);"
        filter_buttons.append(
            f'<button type="button" class="btn-secondary btn-sm" style="{st}" onclick="window.StarAppBridge.dispatchAction(\'filter_guardian_reviews\', \'{f_id}\')">{f_label}</button>'
        )

    rows = []
    for sub in filtered:
        cosmo = cosmonauts_map.get(sub.cosmonaut_id)
        badge = badges_map.get(sub.badge_id)
        cosmo_name = cosmo.name if cosmo else sub.cosmonaut_id
        badge_name = f"{badge.code}: {badge.title}" if badge else sub.badge_id
        pill = render_status_pill(sub.status)

        action_btn = f"""
        <button type="button" class="btn-secondary btn-sm" style="font-weight:700;" onclick="window.StarAppBridge.dispatchAction('open_review_modal', '{{\"submission_id\": \"{sub.id}\"}}')">
            Evaluate (50-Mark Rubric)
        </button>
        """

        rows.append(f"""
        <tr>
            <td style="font-weight:700;">{escape(cosmo_name)}</td>
            <td>{escape(badge_name)}</td>
            <td style="text-align:center;">Attempt #{sub.attempt_number}</td>
            <td style="text-transform:uppercase; font-size:12px; font-weight:600;">{escape(sub.submission_type)}</td>
            <td style="font-family:var(--font-family-mono); font-size:12px;">{escape(sub.submitted_at[:16].replace('T', ' '))}</td>
            <td>{pill}</td>
            <td>{action_btn}</td>
        </tr>
        """)

    table_html = f"""
    <div class="table-responsive">
        <table class="star-table">
            <thead>
                <tr>
                    <th>Cosmonaut</th>
                    <th>Badge Deliverable</th>
                    <th style="text-align:center;">Attempt</th>
                    <th>Deliverable Type</th>
                    <th>Submitted At</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows) if rows else '<tr><td colspan="7" style="text-align:center; padding:32px; color:var(--frost-navy-50);">No project submissions match the selected filter.</td></tr>'}
            </tbody>
        </table>
    </div>
    """

    return f"""
    <div>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px;">
            <div>
                <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Project Deliverable Review Queue</h2>
                <p style="font-size:13px; color:var(--frost-navy-50);">Perform standardized 50-mark evaluations across the 5 mandatory rubric criteria.</p>
            </div>
            <div style="display:flex; gap:8px;">
                {"".join(filter_buttons)}
            </div>
        </div>

        {table_html}
    </div>
    """

def render_assessment_modal_content(
    submission: ProjectSubmission,
    badge: Badge,
    cosmonaut: User,
    existing_assessment: Optional[AssessmentMarksheet] = None,
    previous_assessments: Optional[List[AssessmentMarksheet]] = None
) -> str:
    """The interactive assessment modal with submission preview & 50-mark rubric form."""
    prev_asms_html = ""
    if previous_assessments:
        prev_items = []
        for pa in previous_assessments:
            prev_items.append(f"""
            <div style="padding:10px; background:rgba(234,244,255,0.6); border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); margin-bottom:8px; font-size:12.5px;">
                <strong>Attempt #{pa.attempt_number} Marksheet:</strong> {pa.total_marks}/50 ({pa.percentage}%) — {render_status_pill(pa.decision)}
                <div style="color:var(--frost-navy-50); margin-top:2px;">Feedback: {escape(pa.overall_feedback)}</div>
            </div>
            """)
        prev_asms_html = f"""
        <div style="margin-bottom:16px;">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:6px;">Previous Attempt Marksheets (Preserved in History):</div>
            {"".join(prev_items)}
        </div>
        """

    # Deliverable viewer preview
    preview_box = ""
    if submission.submission_type == "github":
        preview_box = f"""
        <div style="padding:14px; background:rgba(234,244,255,0.5); border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); margin-bottom:16px;">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">GitHub Repository Deliverable:</div>
            <a href="{escape(submission.payload)}" target="_blank" rel="noopener noreferrer" style="font-weight:700; color:var(--deep-frozen-midnight); word-break:break-all;">
                {escape(submission.payload)} ↗
            </a>
            <div style="font-size:11.5px; color:var(--frost-navy-50); margin-top:4px;">(External repository link opens in a secure browser tab for code inspection).</div>
        </div>
        """
    elif submission.submission_type == "code":
        preview_box = f"""
        <div style="margin-bottom:16px;">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">Submitted Code File: {escape(submission.file_name)}</div>
            <pre style="background:var(--frost-navy); color:var(--snow-white); padding:14px; border-radius:var(--radius-md); font-size:12px; overflow-x:auto; max-height:220px;"><code>{escape(submission.payload)}</code></pre>
        </div>
        """
    else:  # PDF
        preview_box = f"""
        <div style="margin-bottom:16px;">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">Submitted Document Deliverable: {escape(submission.file_name)}</div>
            <iframe src="{escape(submission.payload)}" style="width:100%; height:260px; border:1px solid var(--icy-steel-50); border-radius:var(--radius-sm); background:var(--snow-white);"></iframe>
        </div>
        """

    # Pre-fill scores if editing or reviewing
    bu = existing_assessment.business_understanding if existing_assessment else 8.0
    ar = existing_assessment.architecture_report if existing_assessment else 8.0
    tk = existing_assessment.technical_knowledge if existing_assessment else 8.0
    pr = existing_assessment.presentation if existing_assessment else 8.0
    qa = existing_assessment.qa if existing_assessment else 8.0
    strengths = existing_assessment.strength_areas if existing_assessment else ""
    improvements = existing_assessment.improvement_areas if existing_assessment else ""
    feedback = existing_assessment.overall_feedback if existing_assessment else ""

    return f"""
    <div>
        <div style="display:flex; justify-content:space-between; margin-bottom:16px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:10px;">
            <div>
                <h3 style="font-size:1.2rem; font-weight:800; color:var(--frost-navy); margin:0;">Evaluating: {escape(badge.code)} — {escape(badge.title)}</h3>
                <div style="font-size:12.5px; color:var(--frost-navy-50);">Cosmonaut: <strong>{escape(cosmonaut.name)}</strong> | Deliverable: <strong>Attempt #{submission.attempt_number}</strong></div>
            </div>
            <div>{render_status_pill(submission.status)}</div>
        </div>

        {prev_asms_html}
        {preview_box}

        <form id="evaluation-rubric-form" onsubmit="event.preventDefault(); window.StarAppBridge.dispatchAction('submit_evaluation_rubric', '{submission.id}');">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:8px;">
                Standard 50-Mark Rubric Scoring (0.0 to 10.0 each):
            </div>

            <div class="rubric-grid">
                <div class="rubric-item">
                    <label class="rubric-item-label">1. Business Understanding</label>
                    <span class="rubric-item-max">Max: 10.0</span>
                    <input type="number" id="rubric-bu" class="rubric-input" min="0" max="10" step="0.5" value="{bu}" required oninput="window.StarAppBridge.dispatchAction('recalc_rubric_total', '{{}}')">
                </div>

                <div class="rubric-item">
                    <label class="rubric-item-label">2. Architecture / Report</label>
                    <span class="rubric-item-max">Max: 10.0</span>
                    <input type="number" id="rubric-ar" class="rubric-input" min="0" max="10" step="0.5" value="{ar}" required oninput="window.StarAppBridge.dispatchAction('recalc_rubric_total', '{{}}')">
                </div>

                <div class="rubric-item">
                    <label class="rubric-item-label">3. Technical Knowledge</label>
                    <span class="rubric-item-max">Max: 10.0</span>
                    <input type="number" id="rubric-tk" class="rubric-input" min="0" max="10" step="0.5" value="{tk}" required oninput="window.StarAppBridge.dispatchAction('recalc_rubric_total', '{{}}')">
                </div>

                <div class="rubric-item">
                    <label class="rubric-item-label">4. Presentation</label>
                    <span class="rubric-item-max">Max: 10.0</span>
                    <input type="number" id="rubric-pr" class="rubric-input" min="0" max="10" step="0.5" value="{pr}" required oninput="window.StarAppBridge.dispatchAction('recalc_rubric_total', '{{}}')">
                </div>

                <div class="rubric-item">
                    <label class="rubric-item-label">5. Q & A Defense</label>
                    <span class="rubric-item-max">Max: 10.0</span>
                    <input type="number" id="rubric-qa" class="rubric-input" min="0" max="10" step="0.5" value="{qa}" required oninput="window.StarAppBridge.dispatchAction('recalc_rubric_total', '{{}}')">
                </div>
            </div>

            <div class="rubric-total-box">
                <div>
                    <div style="font-size:12px; text-transform:uppercase; letter-spacing:1px; opacity:0.8;">Automated Evaluation Total</div>
                    <div style="font-size:12px; opacity:0.7;">Universal standard across both portals</div>
                </div>
                <div class="rubric-total-val" id="rubric-total-display">
                    40.0 / 50.0 (80.0%)
                </div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px;">
                <div class="form-group">
                    <label class="form-label">Identified Strengths</label>
                    <textarea id="rubric-strengths" class="form-textarea" placeholder="Detail specific achievements, clean code patterns, or thorough analysis..." required>{escape(strengths)}</textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Areas for Improvement</label>
                    <textarea id="rubric-improvements" class="form-textarea" placeholder="Highlight technical deficiencies, edge cases, or documentation gaps..." required>{escape(improvements)}</textarea>
                </div>
            </div>

            <div class="form-group">
                <label class="form-label">Overall Guardian Feedback & Recommendation</label>
                <textarea id="rubric-feedback" class="form-textarea" placeholder="Comprehensive qualitative summary and action items..." required>{escape(feedback)}</textarea>
            </div>

            <div style="display:flex; align-items:center; justify-content:space-between; margin-top:20px; padding-top:16px; border-top:1px solid var(--icy-steel-30);">
                <div style="display:flex; align-items:center; gap:10px;">
                    <label class="form-label" style="margin:0;">Assessment Decision:</label>
                    <select id="rubric-decision" class="form-select" style="width:220px; font-weight:700;">
                        <option value="approve">Approve (Award Badge)</option>
                        <option value="resubmission_requested">Request Resubmission</option>
                        <option value="reject">Reject</option>
                    </select>
                </div>

                <div style="display:flex; gap:10px;">
                    <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Cancel</button>
                    <button type="submit" class="btn-metal">
                        Submit Final Assessment
                    </button>
                </div>
            </div>
        </form>
    </div>
    """

# ==============================================================================
# 7.4 LEARNING & MATERIAL MANAGEMENT
# ==============================================================================

def render_guardian_materials(materials: List[LearningMaterial], badges: List[Badge]) -> str:
    cards = []
    badges_map = {b.id: b for b in badges}

    for m in materials:
        badge = badges_map.get(m.badge_id)
        badge_label = f"{badge.code}: {badge.title}" if badge else m.badge_id
        type_pill = render_status_pill("active" if m.material_type == "youtube" else "completed")

        cards.append(f"""
        <div class="liquid-glass-card" style="margin-bottom:14px;">
            <div class="card-content" style="display:flex; align-items:flex-start; justify-content:space-between;">
                <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <span style="font-size:11px; font-weight:700; color:var(--deep-frozen-midnight);">{escape(badge_label)}</span>
                        {type_pill}
                        <span style="font-size:11px; color:var(--frost-navy-50);">Topic: {escape(m.topic)}</span>
                    </div>
                    <h3 style="font-size:1.1rem; font-weight:700; color:var(--frost-navy);">{escape(m.title)}</h3>
                    <p style="font-size:13px; color:var(--frost-navy-50); margin-top:2px;">{escape(m.description)}</p>
                    <div style="font-size:11.5px; font-family:var(--font-family-mono); color:var(--deep-frozen-midnight); margin-top:6px;">
                        URL: {escape(m.url_or_data[:60])}{"..." if len(m.url_or_data) > 60 else ""}
                    </div>
                </div>
                <div style="display:flex; gap:8px;">
                    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('view_material_preview', '{{\"material_id\": \"{m.id}\"}}')">Preview</button>
                    <button type="button" class="btn-secondary btn-sm" style="color:var(--frost-navy-50);" onclick="window.StarAppBridge.dispatchAction('delete_material', '{{\"material_id\": \"{m.id}\"}}')">Delete</button>
                </div>
            </div>
        </div>
        """)

    create_btn = render_metal_button("Upload / Add Material", "open_add_material_modal", "{}")

    return f"""
    <div>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px;">
            <div>
                <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Learning Resources & Materials Manager</h2>
                <p style="font-size:13px; color:var(--frost-navy-50);">Publish course handbooks, technical whitepapers, and embedded YouTube tutorials.</p>
            </div>
            {create_btn}
        </div>

        <div>
            {"".join(cards) if cards else "<p style='padding:30px; text-align:center; color:var(--frost-navy-50);'>No materials published yet.</p>"}
        </div>
    </div>
    """

# ==============================================================================
# 7.5 ACTIVITY HISTORY
# ==============================================================================

def render_guardian_activity_feed(activities: List[ActivityEvent], cosmonauts: List[User]) -> str:
    rows = []
    for act in activities:
        rows.append(f"""
        <tr>
            <td style="font-family:var(--font-family-mono); font-size:12px; white-space:nowrap;">{escape(act.timestamp[:19].replace('T', ' '))}</td>
            <td><strong style="color:var(--deep-frozen-midnight);">{escape(act.actor_name or act.actor_id)}</strong></td>
            <td>{render_status_pill(act.event_type)}</td>
            <td>
                <div style="font-weight:700;">{escape(act.summary)}</div>
                <div style="font-size:12px; color:var(--frost-navy-50);">{escape(act.details)}</div>
            </td>
            <td>{escape(act.badge_id or "General")}</td>
        </tr>
        """)

    table_html = f"""
    <div class="table-responsive">
        <table class="star-table">
            <thead>
                <tr>
                    <th>Timestamp (UTC)</th>
                    <th>Actor</th>
                    <th>Event Type</th>
                    <th>Audit Summary</th>
                    <th>Target Badge</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </div>
    """

    return f"""
    <div>
        <div style="margin-bottom:20px;">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Batch-Wide Activity & Audit Stream</h2>
            <p style="font-size:13px; color:var(--frost-navy-50);">Chronological audit trail of all badge assignments, submissions, evaluations, and extensions.</p>
        </div>

        {table_html}
    </div>
    """

# ==============================================================================
# 7.6 DEADLINE EXTENSION MANAGEMENT
# ==============================================================================

def render_guardian_extensions(extensions: List[DeadlineExtension], cosmonauts_map: Dict[str, User], badges_map: Dict[str, Badge]) -> str:
    items = []
    for ext in extensions:
        cosmo = cosmonauts_map.get(ext.cosmonaut_id)
        badge = badges_map.get(ext.badge_id)
        cosmo_name = cosmo.name if cosmo else ext.cosmonaut_id
        badge_name = badge.title if badge else ext.badge_id

        actions_html = ""
        if ext.status == "pending":
            actions_html = f"""
            <div style="display:flex; gap:8px; margin-top:12px;">
                <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('open_extension_decision_modal', '{{\"extension_id\": \"{ext.id}\", \"decision\": \"approved\"}}')">
                    Approve Extension
                </button>
                <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('open_extension_decision_modal', '{{\"extension_id\": \"{ext.id}\", \"decision\": \"rejected\"}}')">
                    Reject
                </button>
            </div>
            """
        else:
            actions_html = f"""
            <div style="margin-top:10px; font-size:12.5px; padding:8px 12px; background:rgba(23,52,92,0.06); border-radius:var(--radius-xs);">
                <strong>Decision Response:</strong> {escape(ext.guardian_response or "No response note provided.")}
            </div>
            """

        items.append(f"""
        <div class="liquid-glass-card" style="margin-bottom:14px;">
            <div class="card-content">
                <div style="display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:8px;">
                    <div>
                        <div style="font-size:11px; font-weight:700; color:var(--deep-frozen-midnight); text-transform:uppercase;">{escape(badge_name)}</div>
                        <h3 style="font-size:1.15rem; font-weight:700; color:var(--frost-navy); margin-top:2px;">Requested by {escape(cosmo_name)}</h3>
                    </div>
                    {render_status_pill(ext.status)}
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; background:rgba(234,244,255,0.5); padding:10px 14px; border-radius:var(--radius-sm); margin-bottom:10px; font-size:13px;">
                    <div><strong>Original Deadline:</strong> <span style="font-family:var(--font-family-mono);">{escape(ext.current_deadline)}</span></div>
                    <div><strong>Proposed New Deadline:</strong> <span style="font-family:var(--font-family-mono); font-weight:700; color:var(--deep-frozen-midnight);">{escape(ext.proposed_deadline)}</span></div>
                </div>

                <div style="font-size:13.5px; line-height:1.5; color:var(--frost-navy);">
                    <strong>Cosmonaut Justification:</strong> {escape(ext.reason)}
                </div>

                {actions_html}
            </div>
        </div>
        """)

    return f"""
    <div>
        <div style="margin-bottom:20px;">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Deadline Extension Management</h2>
            <p style="font-size:13px; color:var(--frost-navy-50);">Review extension requests. Approving an extension automatically updates the badge timeline application-wide.</p>
        </div>

        <div>
            {"".join(items) if items else "<p style='padding:30px; text-align:center; color:var(--frost-navy-50);'>No deadline extension requests.</p>"}
        </div>
    </div>
    """

# ==============================================================================
# 7.7 ANNOUNCEMENT MANAGEMENT
# ==============================================================================

def render_guardian_announcements(announcements: List[Announcement], cosmonauts: List[User]) -> str:
    cosmo_map = {c.id: c.name for c in cosmonauts}
    cards = []

    for ann in announcements:
        if ann.target_type == "all":
            recipients_str = "All Cosmonauts"
        else:
            names = [cosmo_map.get(cid, cid) for cid in ann.target_cosmonaut_ids]
            recipients_str = ", ".join(names)

        read_count = len(ann.read_by_cosmonaut_ids)
        total_target = len(cosmonauts) if ann.target_type == "all" else len(ann.target_cosmonaut_ids)

        cards.append(f"""
        <div class="liquid-glass-card" style="margin-bottom:14px;">
            <div class="card-content">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <h3 style="font-size:1.15rem; font-weight:700; color:var(--frost-navy);">{escape(ann.title)}</h3>
                    <div style="font-size:12px; font-weight:600; color:var(--deep-frozen-midnight);">
                        Read Receipts: {read_count} / {total_target}
                    </div>
                </div>
                <div class="announcement-meta">
                    <span>Published by <strong>{escape(ann.author_name)}</strong> on {escape(ann.published_at[:10])}</span>
                    <span>•</span>
                    <span>Target: <strong>{escape(recipients_str)}</strong></span>
                </div>
                <p style="font-size:13.5px; line-height:1.5; color:var(--frost-navy); margin-top:8px;">{escape(ann.message)}</p>
            </div>
        </div>
        """)

    create_btn = render_metal_button("Broadcast New Announcement", "open_create_announcement_modal", "{}")

    return f"""
    <div>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px;">
            <div>
                <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Academy Announcement Broadcaster</h2>
                <p style="font-size:13px; color:var(--frost-navy-50);">Publish targeted notices to the entire batch or selected Cosmonauts and inspect read receipts.</p>
            </div>
            {create_btn}
        </div>

        <div>
            {"".join(cards) if cards else "<p style='padding:30px; text-align:center; color:var(--frost-navy-50);'>No announcements broadcasted.</p>"}
        </div>
    </div>
    """

