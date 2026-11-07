"""
STARAPP GUARDIAN PORTAL VIEWS
Implements the 7 core workspaces for training managers and mentors.
"""

from typing import List, Dict, Any, Optional
from starapp.models import User, Badge, ProjectSubmission, AssessmentMarksheet, LearningMaterial, DeadlineExtension, Announcement, ActivityEvent
from starapp.views_common import (
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
        {"id": "g_extensions", "label": "Extension Requests", "icon": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', "badge": pending_extensions_count},
        {"id": "g_announcements", "label": "Announcements", "icon": '<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>', "badge": 0},
        {"id": "g_activity", "label": "Activity Feed", "icon": '<svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>', "badge": 0}
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
    # Cosmonaut selector dropdown options
    selector_options = ['<option value="all"' + (' selected' if selected_cosmo_id == 'all' else '') + '>All Cosmonauts (Batch Aggregate)</option>']
    for c in cosmonauts:
        sel = " selected" if c.id == selected_cosmo_id else ""
        selector_options.append(f'<option value="{c.id}"{sel}>{escape(c.name)} ({c.id})</option>')

    selector_bar = f"""
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:24px; background:rgba(255,255,255,0.7); padding:12px 20px; border-radius:var(--radius-md); border:1px solid var(--icy-steel-30);">
        <div style="display:flex; align-items:center; gap:12px;">
            <label style="font-size:13px; font-weight:700; color:var(--deep-frozen-midnight); text-transform:uppercase;">View Scope:</label>
            <select class="form-select" style="width:280px; padding:6px 12px; font-weight:600;" onchange="window.StarAppBridge.dispatchAction('select_guardian_cosmo_filter', this.value)">
                {"".join(selector_options)}
            </select>
        </div>
        <div style="font-size:12px; color:var(--frost-navy-50);">
            Showing data for: <strong>{"Batch Orion-24 (All Cosmonauts)" if selected_cosmo_id == "all" else "Individual Dossier"}</strong>
        </div>
    </div>
    """

    if selected_cosmo_id != "all" and selected_cosmo_data:
        # Render Individual Cosmonaut Dossier
        return selector_bar + render_individual_cosmo_dossier(selected_cosmo_data)

    # Otherwise render Batch Aggregate Analytics
    kpis = f"""
    <div class="kpi-grid">
        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Total Cosmonauts</span>
                <div class="kpi-icon-bubble">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                </div>
            </div>
            <div class="kpi-value">{batch_analytics["total_cosmonauts"]}</div>
            <div class="kpi-subtext">Active Batch Orion-24</div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Total Badges Assigned</span>
                <div class="kpi-icon-bubble">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                </div>
            </div>
            <div class="kpi-value">{batch_analytics["total_assigned_badges"]}</div>
            <div class="kpi-subtext">Published milestones across batch</div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Completed Badges</span>
                <div class="kpi-icon-bubble">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                </div>
            </div>
            <div class="kpi-value">{batch_analytics["completed_badges"]}</div>
            <div class="kpi-subtext">{batch_analytics["completion_rate"]}% Batch completion rate</div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Awaiting Review</span>
                <div class="kpi-icon-bubble">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>
            </div>
            <div class="kpi-value">{batch_analytics["pending_reviews"]}</div>
            <div class="kpi-subtext">Submissions requiring assessment</div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Batch Average Score</span>
                <div class="kpi-icon-bubble">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                </div>
            </div>
            <div class="kpi-value">{batch_analytics["batch_avg_score"]} <span style="font-size:14px; opacity:0.6;">/ 50</span></div>
            <div class="kpi-subtext">{batch_analytics["batch_avg_pct"]}% across approved projects</div>
        </div>
    </div>
    """

    # Criterion-wise batch performance bars
    crit_bars = []
    for c in RUBRIC_CRITERIA:
        avg_val = batch_analytics["criterion_averages"].get(c["key"], 0.0)
        pct = (avg_val / 10.0) * 100.0
        crit_bars.append(f"""
        <div style="margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; font-size:13px; font-weight:600; margin-bottom:4px;">
                <span>{c["title"]}</span>
                <span style="color:var(--deep-frozen-midnight);">{avg_val} / 10.0 ({pct:.1f}%)</span>
            </div>
            <div style="height:10px; border-radius:var(--radius-full); background:rgba(157,183,213,0.3); overflow:hidden;">
                <div style="height:100%; width:{pct}%; border-radius:var(--radius-full); background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
            </div>
        </div>
        """)

    crit_card = render_liquid_card(
        title="Batch Criterion-Wise Average Performance (Standard 50-Mark Rubric)",
        subtitle="Aggregated across all approved badge evaluations in Batch Orion-24",
        content="".join(crit_bars)
    )

    # Cosmonauts roster overview table
    roster_rows = []
    for c in cosmonauts:
        roster_rows.append(f"""
        <tr>
            <td style="font-weight:700;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <div class="user-avatar" style="width:28px; height:28px; font-size:11px;">{escape(c.avatar)}</div>
                    <span>{escape(c.name)}</span>
                </div>
            </td>
            <td style="font-family:var(--font-family-mono); font-size:12px;">{escape(c.email)}</td>
            <td>Batch Orion-24</td>
            <td>
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('select_guardian_cosmo_filter', '{c.id}')">
                    Open Full Dossier
                </button>
            </td>
        </tr>
        """)

    roster_table = f"""
    <div class="table-responsive">
        <table class="star-table">
            <thead>
                <tr>
                    <th>Cosmonaut</th>
                    <th>Email Address</th>
                    <th>Training Batch</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {"".join(roster_rows)}
            </tbody>
        </table>
    </div>
    """

    roster_card = render_liquid_card(
        title="Batch Orion-24 Cosmonaut Directory",
        subtitle="Select any Cosmonaut to inspect their private marksheet history, submissions, skills, and timelines",
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

def render_guardian_badge_allotment(badges: List[Badge], cosmonauts: List[User]) -> str:
    badge_cards = []
    for b in badges:
        cosmo_count = len(b.assigned_cosmonaut_ids)
        prereq_badges = ", ".join(b.prerequisites) if b.prerequisites else "None (Entry Milestone)"
        pub_pill = render_status_pill("active" if b.is_published else "locked")
        toggle_pub_action = "unpublish_badge" if b.is_published else "publish_badge"
        toggle_pub_text = "Unpublish" if b.is_published else "Publish to Roadmap"

        badge_cards.append(f"""
        <div class="liquid-glass-card" style="margin-bottom:16px;">
            <div class="card-content">
                <div style="display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:12px;">
                    <div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-family:var(--font-family-mono); font-size:12px; font-weight:700; color:var(--deep-frozen-midnight);">{escape(b.code)}</span>
                            {pub_pill}
                        </div>
                        <h3 style="font-size:1.2rem; font-weight:700; color:var(--frost-navy); margin-top:4px;">{escape(b.title)}</h3>
                        <p style="font-size:13px; color:var(--frost-navy-50); margin-top:4px; max-width:700px;">{escape(b.description)}</p>
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('open_badge_detail_modal', '{b.id}')">
                            Timeline Window
                        </button>
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('open_edit_badge_modal', '{b.id}')">
                            Allot & Set Timeline
                        </button>
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('{toggle_pub_action}', '{b.id}')">
                            {toggle_pub_text}
                        </button>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px; background:rgba(234,244,255,0.4); padding:10px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); font-size:12px; margin-top:8px;">
                    <div><strong>Prerequisites:</strong> {escape(prereq_badges)}</div>
                    <div><strong>Assigned To:</strong> {cosmo_count} of {len(cosmonauts)} Cosmonaut(s)</div>
                    <div><strong>Allocated:</strong> {escape(b.default_timeline.get("assignment_date", "TBD"))}</div>
                    <div><strong>Learning Time:</strong> {escape(b.default_timeline.get("learning_start_date", "TBD"))} → {escape(b.default_timeline.get("learning_end_date", "TBD"))}</div>
                    <div><strong>Project Time:</strong> {escape(b.default_timeline.get("project_start_date", "TBD"))} → {escape(b.default_timeline.get("project_end_date", "TBD"))}</div>
                    <div><strong>Submission Date:</strong> {escape(b.default_timeline.get("submission_deadline", "TBD"))}</div>
                    <div><strong>Review Date:</strong> {escape(b.default_timeline.get("review_date", "TBD"))}</div>
                    <div><strong>Badge Earned Date:</strong> {escape(b.default_timeline.get("expected_award_date", "TBD"))}</div>
                </div>
            </div>
        </div>
        """)

    create_btn = render_metal_button("Create New Badge", "open_create_badge_modal", "{}")

    return f"""
    <div>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px;">
            <div>
                <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Badge Catalog & Allotment Manager</h2>
                <p style="font-size:13px; color:var(--frost-navy-50);">Configure prerequisites, publish roadmaps, and schedule milestone deadlines.</p>
            </div>
            {create_btn}
        </div>

        <div>
            {"".join(badge_cards)}
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

