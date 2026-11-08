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
    render_status_pill, render_standard_marksheet, render_9point_timeline
)
from starapp.roadmap import generate_roadmap_graph
from starapp.assessment import RUBRIC_CRITERIA

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
    leaderboard: List[Dict[str, Any]],
    score_summary: Dict[str, Any],
    upcoming_deadlines: List[Dict[str, str]],
    recent_announcements: List[Announcement]
) -> str:
    from starapp.storage import store

    # 1. Executive Telemetry Calculations
    total_assigned = len(assigned_badges)
    completed_count = score_summary.get("approved_count", 0)
    active_count = max(0, total_assigned - completed_count)
    progress_pct = round((completed_count / max(1, total_assigned)) * 100.0, 1)

    approved_asms = [a for a in assessments if a.decision == "approve"]
    first_attempt_passes = sum(1 for a in approved_asms if a.attempt_number == 1)
    pass_rate = round((first_attempt_passes / max(1, len(approved_asms))) * 100.0, 1) if approved_asms else 100.0

    avg_marks = score_summary.get("average_marks", 0.0)
    avg_pct = score_summary.get("average_percentage", 0.0)

    # Calculate cadet rank & percentile in cohort
    cadet_rank = 1
    total_cadets = len(leaderboard)
    for item in leaderboard:
        if item["cosmonaut_id"] == current_user.id:
            cadet_rank = item.get("rank", 1)
            break
    percentile_val = round(((total_cadets - cadet_rank + 1) / max(1, total_cadets)) * 100.0, 0)

    # 2. Rubric Dimension Breakdown (The 5 Standard Criteria)
    all_approved = [a for a in store.get_all_assessments() if a.decision == "approve"]
    rubric_telemetry = []
    cadet_scores_dict = {}

    for c in RUBRIC_CRITERIA:
        k = c["key"]
        title = c["title"]
        desc = c["desc"]
        # Cadet average for this criterion
        c_vals = [getattr(a, k, 0.0) for a in approved_asms]
        c_avg = round(sum(c_vals) / len(c_vals), 2) if c_vals else 0.0
        cadet_scores_dict[k] = c_avg

        # Cohort average for this criterion
        batch_vals = [getattr(a, k, 0.0) for a in all_approved]
        batch_avg = round(sum(batch_vals) / len(batch_vals), 2) if batch_vals else c_avg

        diff = round(c_avg - batch_avg, 2)
        pct_bar = min(100.0, (c_avg / 10.0) * 100.0)
        cohort_pct_bar = min(100.0, (batch_avg / 10.0) * 100.0)

        delta_badge = f'<span style="font-size:11px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:2px 8px; border-radius:var(--radius-xs);">{"+" if diff >= 0 else ""}{diff} vs Batch</span>'

        rubric_telemetry.append(f"""
        <div style="margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <div>
                    <span style="font-size:13px; font-weight:700; color:var(--frost-navy);">{escape(title)}</span>
                    <span style="font-size:11px; color:var(--frost-navy-50); margin-left:6px;">({escape(desc)})</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    {delta_badge}
                    <span style="font-size:13.5px; font-weight:800; color:var(--deep-frozen-midnight);">{c_avg:.1f} <span style="font-size:11px; font-weight:600; opacity:0.6;">/ 10</span></span>
                </div>
            </div>
            <div style="position:relative; height:10px; border-radius:var(--radius-full); background:rgba(157,183,213,0.25); overflow:hidden;">
                <!-- Cohort benchmark marker -->
                <div style="position:absolute; top:0; left:{cohort_pct_bar}%; width:2px; height:100%; background:var(--frost-navy-50); z-index:2;" title="Batch Cohort Benchmark ({batch_avg:.1f})"></div>
                <!-- Cadet Score Bar -->
                <div style="height:100%; width:{pct_bar}%; border-radius:var(--radius-full); background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
            </div>
        </div>
        """)

    # Identify Superpower & Growth Vector
    sorted_criteria = sorted(RUBRIC_CRITERIA, key=lambda x: cadet_scores_dict.get(x["key"], 0.0), reverse=True)
    superpower = sorted_criteria[0] if sorted_criteria else None
    growth_vector = sorted_criteria[-1] if sorted_criteria else None

    superpower_html = f"""
    <div style="display:flex; align-items:flex-start; gap:10px; background:rgba(23,52,92,0.05); padding:10px 14px; border-radius:var(--radius-sm); border-left:3px solid var(--deep-frozen-midnight); margin-bottom:10px;">
        <span style="display:inline-flex; align-items:center; color:var(--deep-frozen-midnight);">{get_icon("award", 18)}</span>
        <div>
            <div style="font-size:11.5px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">Primary Engineering Strength: {escape(superpower["title"] if superpower else "System Architecture")}</div>
            <p style="font-size:12px; color:var(--frost-navy); line-height:1.45; margin:2px 0 0 0;">Exemplary score of <strong>{cadet_scores_dict.get(superpower["key"], 0.0):.1f} / 10.0</strong> — demonstrably enterprise-ready problem formulation and technical depth.</p>
        </div>
    </div>
    """ if superpower else ""

    growth_html = f"""
    <div style="display:flex; align-items:flex-start; gap:10px; background:rgba(157,183,213,0.12); padding:10px 14px; border-radius:var(--radius-sm); border-left:3px solid var(--icy-steel);">
        <span style="display:inline-flex; align-items:center; color:var(--deep-frozen-midnight);">{get_icon("target", 18)}</span>
        <div>
            <div style="font-size:11.5px; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.5px;">Targeted Growth Vector: {escape(growth_vector["title"] if growth_vector else "Defensive Testing")}</div>
            <p style="font-size:12px; color:var(--frost-navy-75); line-height:1.45; margin:2px 0 0 0;">Score of <strong>{cadet_scores_dict.get(growth_vector["key"], 0.0):.1f} / 10.0</strong> — focus on runtime boundary conditions and defense of architectural trade-offs.</p>
        </div>
    </div>
    """ if growth_vector else ""

    # 3. Milestone Execution Pipeline Matrix
    pipeline_rows = []
    cadet_subs = store.get_submissions_for_cosmonaut(current_user.id)
    for idx, b in enumerate(assigned_badges):
        b_asm = next((a for a in approved_asms if a.badge_id == b.id), None)
        b_sub = next((s for s in cadet_subs if s.badge_id == b.id and s.status == "pending"), None)
        tl = store.get_timeline(b.id, current_user.id)

        if b_asm:
            code_str = escape(b.code)
            title_str = escape(b.title)
            cat_str = escape(b.category)
            status_badge = '<span class="status-pill status-approved">Certified</span>'
            score_text = f"<strong>{b_asm.total_marks:.1f}</strong> / 50 ({b_asm.percentage:.1f}%)"
            attempt_text = f"Attempt #{b_asm.attempt_number}"
            velocity_text = '<span style="color:#2E7D32; font-weight:700;">Ahead of Schedule</span>'
            action_btn = f"""<button type="button" class="btn-metal btn-sm" style="padding:3px 10px; font-size:11px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_results')">Marksheet →</button>"""
        elif b_sub:
            code_str = escape(b.code)
            title_str = escape(b.title)
            cat_str = escape(b.category)
            status_badge = '<span class="status-pill status-pending">In Review</span>'
            score_text = '<span style="opacity:0.6;">Under Guardian Review</span>'
            attempt_text = f"Attempt #{b_sub.attempt_number}"
            velocity_text = '<span style="color:var(--deep-frozen-midnight); font-weight:700;">Awaiting Feedback</span>'
            action_btn = f"""<button type="button" class="btn-secondary btn-sm" style="padding:3px 10px; font-size:11px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Track Status →</button>"""
        elif tl and getattr(tl, "status", "") in ["active", "in_progress"]:
            code_str = escape(b.code)
            title_str = escape(b.title)
            cat_str = escape(b.category)
            status_badge = '<span class="status-pill status-active">Active Sprint</span>'
            score_text = '<span style="opacity:0.6;">Sprint In Progress</span>'
            attempt_text = "Attempt #1 (Pending)"
            velocity_text = '<span style="color:var(--deep-frozen-midnight); font-weight:700;">Sprint Target</span>'
            action_btn = f"""<button type="button" class="btn-metal btn-sm" style="padding:3px 10px; font-size:11px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_submission')">Submit Project →</button>"""
        else:
            code_str = f'{get_icon("lock", 11, "margin-right:4px;")} LOCKED'
            title_str = f'{get_icon("lock", 13, "margin-right:5px;")} Milestone {idx+1} (Locked)'
            cat_str = "Classified"
            status_badge = '<span class="status-pill status-locked">Locked</span>'
            score_text = '<span style="opacity:0.6;">—</span>'
            attempt_text = "—"
            velocity_text = '<span style="opacity:0.6;">Awaiting Guardian</span>'
            action_btn = f"""<button type="button" class="btn-secondary btn-sm" style="padding:3px 10px; font-size:11px; opacity:0.7;" onclick="window.StarAppBridge.dispatchAction('open_locked_milestone_notice', '{idx+1}')">{get_icon("lock", 12, "margin-right:4px;")} Locked</button>"""

        pipeline_rows.append(f"""
        <tr>
            <td style="font-weight:700;">
                <span style="font-family:var(--font-family-mono); font-size:12px; background:var(--deep-frozen-midnight); color:var(--snow-white); padding:2px 7px; border-radius:var(--radius-xs); margin-right:6px;">{code_str}</span>
                <span>{title_str}</span>
            </td>
            <td><span style="font-size:11px; color:var(--frost-navy-50); background:rgba(23,52,92,0.06); padding:2px 7px; border-radius:var(--radius-xs); font-weight:600;">{cat_str}</span></td>
            <td>{status_badge}</td>
            <td style="text-align:center;">{score_text}</td>
            <td style="text-align:center; font-size:12px;">{attempt_text}</td>
            <td style="text-align:center; font-size:12px;">{velocity_text}</td>
            <td style="text-align:right;">{action_btn}</td>
        </tr>
        """)

    # 4. Batch Orion-24 Official Leaderboard
    leaderboard_rows = []
    for item in leaderboard:
        is_me = item["cosmonaut_id"] == current_user.id
        row_style = "background:rgba(23,52,92,0.08); font-weight:700;" if is_me else ""
        you_badge = '<span class="status-pill status-approved" style="margin-left:6px; font-size:9.5px; padding:1px 6px;">YOU</span>' if is_me else ""
        rank_medal = f'#{item["rank"]}'
        if item["rank"] == 1:
            rank_medal = f'{get_icon("medal_1", 18)} <span style="font-weight:800; color:#B8860B;">#1</span>'
        elif item["rank"] == 2:
            rank_medal = f'{get_icon("medal_2", 18)} <span style="font-weight:800; color:#708090;">#2</span>'
        elif item["rank"] == 3:
            rank_medal = f'{get_icon("medal_3", 18)} <span style="font-weight:800; color:#8B4513;">#3</span>'

        leaderboard_rows.append(f"""
        <tr style="{row_style}">
            <td style="font-weight:800; font-size:13px;">{rank_medal}</td>
            <td>
                <div style="display:flex; align-items:center; gap:8px;">
                    <div class="user-avatar" style="width:26px; height:26px; font-size:10px;">{escape(item["avatar"])}</div>
                    <span>{escape(item["cosmonaut_name"])}</span>
                    {you_badge}
                </div>
            </td>
            <td style="text-align:center; font-weight:700;">{item["completed_badges"]} / 5</td>
            <td style="text-align:center; font-weight:800; color:var(--deep-frozen-midnight);">{item["average_marks"]} / 50</td>
            <td style="text-align:center; font-weight:700;">{item["average_percentage"]}%</td>
        </tr>
        """)

    # 5. Prescriptive Action Plan & Guardian Intelligence
    all_strengths = [a.strength_areas for a in assessments if a.strength_areas]
    all_improvements = [a.improvement_areas for a in assessments if a.improvement_areas]

    # Skills widget pills
    skills_pills = "".join([f'<span class="status-pill status-active" style="margin:2px; font-size:11px;">{escape(s)}</span>' for s in profile.skills]) or '<span style="font-size:12px; opacity:0.6;">Add skills in Profile.</span>'

    return f"""
    <div>
        <!-- Executive Intelligence Header -->
        <div class="liquid-glass-card" style="padding:20px 24px; margin-bottom:24px; border-radius:var(--radius-lg); border:1.5px solid var(--icy-steel); background:linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(234,244,255,0.85) 100%); box-shadow:0 4px 18px rgba(7,22,41,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div class="user-avatar" style="width:50px; height:50px; font-size:18px; font-weight:800; border:2px solid var(--icy-steel);">{escape(current_user.avatar)}</div>
                    <div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <h2 style="font-size:1.45rem; font-weight:800; color:var(--frost-navy); margin:0;">{escape(current_user.name)}</h2>
                            <span class="status-pill status-approved" style="font-size:11px;">Flight Officer</span>
                            <span style="font-size:11.5px; font-family:var(--font-family-mono); color:var(--frost-navy-50);">ID: {escape(current_user.id)}</span>
                        </div>
                        <p style="font-size:12.5px; color:var(--frost-navy-75); margin:3px 0 0 0;">
                            Batch: <strong>{escape(profile.batch_name or "Orion-24")}</strong> &bull; Mentor: <strong>{escape(getattr(profile, "manager_name", "Dr. Elena Vance"))}</strong> &bull; Track: <strong>Enterprise Cloud & Systems Architecture</strong>
                        </p>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    <span style="font-size:12px; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:5px 12px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-50);">
                        Standing: <strong>Top {percentile_val:.0f}% (Rank #{cadet_rank})</strong>
                    </span>
                    <span style="font-size:12px; font-weight:800; color:var(--snow-white); background:var(--deep-frozen-midnight); padding:5px 12px; border-radius:var(--radius-sm); box-shadow:0 2px 6px rgba(7,22,41,0.2);">
                        GPA: <strong>{avg_marks:.1f} / 50 ({avg_pct:.1f}%)</strong>
                    </span>
                </div>
            </div>
        </div>

        <!-- 4-Card Analytics KPI Grid -->
        <div class="kpi-grid">
            <div class="liquid-glass-card kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Curriculum Velocity</span>
                    <div class="kpi-icon-bubble">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    </div>
                </div>
                <div class="kpi-value">{completed_count} / {total_assigned} <span style="font-size:14px; opacity:0.65; font-weight:600;">Milestones</span></div>
                <div style="height:6px; border-radius:var(--radius-full); background:rgba(157,183,213,0.3); overflow:hidden; margin:8px 0 6px 0;">
                    <div style="height:100%; width:{progress_pct}%; background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
                </div>
                <div class="kpi-subtext" style="color:#2E7D32; font-weight:700;">▲ {progress_pct}% Total Roadmap Completed</div>
            </div>

            <div class="liquid-glass-card kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Standard Academic Index</span>
                    <div class="kpi-icon-bubble">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    </div>
                </div>
                <div class="kpi-value">{avg_marks:.1f} <span style="font-size:14px; opacity:0.65; font-weight:600;">/ 50.0</span></div>
                <div class="kpi-subtext" style="font-weight:700; color:var(--deep-frozen-midnight);">{avg_pct:.1f}% Distinction Rate &bull; Tier 1</div>
            </div>

            <div class="liquid-glass-card kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">First-Attempt Pass Rate</span>
                    <div class="kpi-icon-bubble">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                    </div>
                </div>
                <div class="kpi-value">{pass_rate:.1f}%</div>
                <div class="kpi-subtext" style="color:var(--frost-navy); font-weight:600;">{first_attempt_passes} of {len(approved_asms)} passed on Attempt 1</div>
            </div>

            <div class="liquid-glass-card kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Validated Competencies</span>
                    <div class="kpi-icon-bubble">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    </div>
                </div>
                <div class="kpi-value">{len(profile.skills)} <span style="font-size:14px; opacity:0.65; font-weight:600;">Skills</span></div>
                <div class="kpi-subtext">Verified production engineering skills</div>
            </div>
        </div>

        <!-- Analytical Deep Dive: Rubric Dimension Radar & Prescriptive Insights -->
        <div style="display:grid; grid-template-columns:1.2fr 0.8fr; gap:22px; margin-bottom:26px;">
            <!-- Left: 5-Dimension Standard Rubric Competency Diagnostic -->
            <div class="liquid-glass-card" style="padding:22px 24px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-50); background:#FFFFFF; box-shadow:0 4px 16px rgba(7,22,41,0.05);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; padding-bottom:12px; border-bottom:1.5px solid var(--icy-steel-30);">
                    <div>
                        <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0;">5-Dimension Rubric Diagnostic</h3>
                        <p style="font-size:12px; color:var(--frost-navy-50); margin:2px 0 0 0;">Evaluated against Guardian Dr. Elena Vance's standardized 50-mark rubric</p>
                    </div>
                    <span style="font-size:11px; font-weight:700; color:var(--frost-navy-50); background:rgba(234,244,255,0.8); padding:3px 8px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30);">
                        | Benchmark Watermark
                    </span>
                </div>

                {"".join(rubric_telemetry)}

                <div style="margin-top:16px; padding-top:14px; border-top:1.5px solid var(--icy-steel-30);">
                    {superpower_html}
                    {growth_html}
                </div>
            </div>

            <!-- Right: Actionable Decision Support & Mentor Digest -->
            <div class="liquid-glass-card" style="padding:22px 24px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-50); background:#FFFFFF; box-shadow:0 4px 16px rgba(7,22,41,0.05); display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="margin-bottom:16px; padding-bottom:12px; border-bottom:1.5px solid var(--icy-steel-30);">
                        <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0;">Decision Support & Action Plan</h3>
                        <p style="font-size:12px; color:var(--frost-navy-50); margin:2px 0 0 0;">Prescriptive next-best steps based on telemetry</p>
                    </div>

                    <div style="margin-bottom:16px;">
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; margin-bottom:4px;">1. Immediate Sprint Priority</div>
                        <div style="background:rgba(234,244,255,0.7); padding:10px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-50); font-size:12.5px; color:var(--frost-navy); line-height:1.45;">
                            Focus on <strong>DAT-103: Data Architecture</strong> project submission. Completing this milestone will solidify your #1 standing in Batch Orion-24.
                        </div>
                    </div>

                    <div style="margin-bottom:16px;">
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; margin-bottom:4px;">2. Curriculum Study Recommendation</div>
                        <div style="background:rgba(234,244,255,0.7); padding:10px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-50); font-size:12.5px; color:var(--frost-navy); line-height:1.45;">
                            Watch <strong>Video 1 (Tactical Operations)</strong> and review Section 4 of <strong>Chemistry Syllabus (PDF)</strong> in the Study Materials workspace.
                        </div>
                    </div>

                    <div>
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; margin-bottom:4px;">3. Guardian Evaluation Takeaway</div>
                        <div style="background:rgba(23,52,92,0.06); padding:10px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-50); font-size:12px; color:var(--frost-navy); line-height:1.45; font-style:italic;">
                            "{escape(all_strengths[-1] if all_strengths else "Exemplary understanding of cloud architectures and compliance standards.")}"
                        </div>
                    </div>
                </div>

                <div style="margin-top:18px; padding-top:12px; border-top:1px solid var(--icy-steel-30); display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:11.5px; font-weight:700; color:var(--frost-navy-50);">Mentor: Dr. Elena Vance</span>
                    <button type="button" class="btn-metal btn-sm" style="padding:5px 14px; font-size:11.5px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_materials')">Open Study Hub →</button>
                </div>
            </div>
        </div>

        <!-- Curriculum Trajectory & Milestone Pipeline Matrix -->
        <div class="liquid-glass-card" style="padding:22px 24px; margin-bottom:26px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-50); background:#FFFFFF; box-shadow:0 4px 16px rgba(7,22,41,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; padding-bottom:12px; border-bottom:1.5px solid var(--icy-steel-30);">
                <div>
                    <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0;">Curriculum Milestone Execution Pipeline</h3>
                    <p style="font-size:12px; color:var(--frost-navy-50); margin:2px 0 0 0;">Comprehensive status of all 5 milestones across your cohort certification pathway</p>
                </div>
                <button type="button" class="btn-secondary btn-sm" style="padding:5px 14px; font-size:11.5px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_roadmap')">Interactive Roadmap View →</button>
            </div>

            <div class="table-responsive">
                <table class="star-table">
                    <thead>
                        <tr>
                            <th style="width:26%;">Milestone</th>
                            <th style="width:14%;">Domain</th>
                            <th style="width:14%;">Status</th>
                            <th style="width:16%; text-align:center;">Score Achieved</th>
                            <th style="width:10%; text-align:center;">Attempts</th>
                            <th style="width:12%; text-align:center;">Trajectory</th>
                            <th style="width:8%; text-align:right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(pipeline_rows)}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Dual Column: Orion-24 Official Leaderboard & Skills Deck -->
        <div style="display:grid; grid-template-columns:1.3fr 0.7fr; gap:22px;">
            <!-- Official Batch Leaderboard -->
            <div class="liquid-glass-card" style="padding:22px 24px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-50); background:#FFFFFF; box-shadow:0 4px 16px rgba(7,22,41,0.05);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; padding-bottom:12px; border-bottom:1.5px solid var(--icy-steel-30);">
                    <div>
                        <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0;">Batch Orion-24 Official Leaderboard</h3>
                        <p style="font-size:12px; color:var(--frost-navy-50); margin:2px 0 0 0;">Ranked by standardized 50-mark score average on approved deliverables</p>
                    </div>
                    <span class="status-pill status-approved" style="font-size:11px;">Live Sync</span>
                </div>

                <div class="table-responsive">
                    <table class="star-table">
                        <thead>
                            <tr>
                                <th style="width:12%;">Rank</th>
                                <th style="width:40%;">Cosmonaut</th>
                                <th style="width:18%; text-align:center;">Milestones</th>
                                <th style="width:18%; text-align:center;">Score (/50)</th>
                                <th style="width:12%; text-align:center;">Standard %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(leaderboard_rows)}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Profile Skills & Industry Certifications -->
            <div class="liquid-glass-card" style="padding:22px 24px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-50); background:#FFFFFF; box-shadow:0 4px 16px rgba(7,22,41,0.05); display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="margin-bottom:16px; padding-bottom:12px; border-bottom:1.5px solid var(--icy-steel-30);">
                        <h3 style="font-size:1.15rem; font-weight:800; color:var(--frost-navy); margin:0;">Validated Competency Cloud</h3>
                        <p style="font-size:12px; color:var(--frost-navy-50); margin:2px 0 0 0;">Industry credentials & certified skillsets</p>
                    </div>

                    <div style="margin-bottom:16px;">
                        <div style="font-size:11.5px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; margin-bottom:8px;">Active Technical Competencies:</div>
                        <div style="display:flex; flex-wrap:wrap; gap:6px;">
                            {skills_pills}
                        </div>
                    </div>

                    <div style="background:rgba(234,244,255,0.6); padding:12px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-50);">
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">Skill Endorsement Policy:</div>
                        <p style="font-size:11.5px; color:var(--frost-navy-75); line-height:1.45; margin:0;">Skills entered in your profile are validated upon each milestone certification and showcased to corporate sponsors.</p>
                    </div>
                </div>

                <div style="margin-top:16px; padding-top:12px; border-top:1px solid var(--icy-steel-30); display:flex; justify-content:flex-end;">
                    <button type="button" class="btn-secondary btn-sm" style="padding:5px 14px; font-size:11.5px;" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_profile')">Manage Skills in Profile →</button>
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
            code = f'{get_icon("lock", 12, "margin-right:4px;")} LOCKED'
            title = f'{get_icon("lock", 13, "margin-right:5px;")} Milestone {idx + 1} (Locked)'
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
                <form id="project-submission-form" onsubmit="event.preventDefault(); window.StarAppBridge.dispatchAction('submit_project_deliverable', '{{}}');">
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
    available_badges: Optional[List[Badge]] = None
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
    # 1. Determine badges to show
    if selected_badge_filter == "all":
        target_badges = badges
    else:
        target_badges = [b for b in badges if b.id == selected_badge_filter]
        if not target_badges and selected_badge_filter in badges_map:
            target_badges = [badges_map[selected_badge_filter]]

    # Compute overall counts in current scope
    scope_materials = [m for m in materials if any(b.id == m.badge_id for b in target_badges)]
    count_all = len(scope_materials)
    count_pdf = sum(1 for m in scope_materials if m.material_type == "pdf")
    count_yt = sum(1 for m in scope_materials if m.material_type == "youtube")

    # Options for Badge Dropdown
    badge_opts = []
    for b in badges:
        sel = " selected" if b.id == selected_badge_filter else ""
        badge_opts.append(f'<option value="{b.id}"{sel}>{escape(b.code)}: {escape(b.title)}</option>')

    # Type Filter Buttons Styling
    def get_btn_style(is_active: bool) -> str:
        if is_active:
            return "background:var(--deep-frozen-midnight); color:var(--snow-white); font-weight:800; border-radius:var(--radius-sm); padding:7px 16px; font-size:12.5px; border:none; cursor:pointer; box-shadow:0 2px 8px rgba(23,52,92,0.3); display:inline-flex; align-items:center; gap:6px;"
        return "background:transparent; color:var(--deep-frozen-midnight); font-weight:700; border-radius:var(--radius-sm); padding:7px 16px; font-size:12.5px; border:none; cursor:pointer; display:inline-flex; align-items:center; gap:6px; opacity:0.85;"

    btn_all_style = get_btn_style(selected_type_filter == "all")
    btn_pdf_style = get_btn_style(selected_type_filter == "pdf")
    btn_yt_style = get_btn_style(selected_type_filter == "youtube")

    # 2. Render Badge-by-Badge Sections
    badge_sections = []
    for b in target_badges:
        b_mats = [m for m in materials if m.badge_id == b.id]
        if selected_type_filter == "pdf":
            b_mats = [m for m in b_mats if m.material_type == "pdf"]
        elif selected_type_filter == "youtube":
            b_mats = [m for m in b_mats if m.material_type == "youtube"]

        # Only render badge container if it has materials matching current filter, or if specific badge is chosen
        if not b_mats and selected_badge_filter == "all":
            continue

        mat_cards = []
        for m in b_mats:
            if m.material_type == "pdf":
                type_badge = """
                <span style="background:rgba(23,52,92,0.08); color:var(--deep-frozen-midnight); padding:3px 8px; border-radius:var(--radius-xs); font-size:10.5px; font-weight:800; border:1px solid var(--icy-steel-50); display:inline-flex; align-items:center; gap:5px;">
                    <svg viewBox="0 0 24 24" style="width:12px; height:12px;" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                    PDF DOCUMENT
                </span>
                """
                read_indicator = '<span style="font-size:11px; font-weight:700; color:var(--deep-frozen-midnight); display:inline-flex; align-items:center; gap:4px;">&bull; In-Container PDF</span>'

                # Use official PDF from data folder
                pdf_src = "data/Chemistry%20Syllabus.pdf"
                if m.url_or_data and not m.url_or_data.startswith("http"):
                    pdf_src = m.url_or_data.replace(" ", "%20")

                # Fixed-size in-container PDF viewer (200px height, crisp, zero blur)
                media_viewer_html = f"""
                <div class="media-pdf-box">
                    <object data="{escape(pdf_src)}" type="application/pdf">
                        <iframe src="{escape(pdf_src)}" title="{escape(m.title)}"></iframe>
                    </object>
                </div>
                """
            else:
                type_badge = """
                <span style="background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 8px; border-radius:var(--radius-xs); font-size:10.5px; font-weight:800; border:1px solid var(--deep-frozen-midnight); display:inline-flex; align-items:center; gap:5px; box-shadow:0 1px 3px rgba(23,52,92,0.2);">
                    <svg viewBox="0 0 24 24" style="width:12px; height:12px;" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    YOUTUBE VIDEO
                </span>
                """
                read_indicator = '<span style="font-size:11px; font-weight:700; color:var(--deep-frozen-midnight); display:inline-flex; align-items:center; gap:4px;">&#9654; In-Container Player</span>'

                # Extract YouTube Video ID (defaults to Video 1 or Video 2)
                vid = "9ZGFF_bYenc"
                if "F0sqfPkCcyM" in m.url_or_data:
                    vid = "F0sqfPkCcyM"
                elif "9ZGFF_bYenc" in m.url_or_data:
                    vid = "9ZGFF_bYenc"
                elif "watch?v=" in m.url_or_data:
                    vid = m.url_or_data.split("watch?v=")[1].split("&")[0]
                elif "youtu.be/" in m.url_or_data:
                    vid = m.url_or_data.split("youtu.be/")[1].split("?")[0]
                elif "/embed/" in m.url_or_data:
                    vid = m.url_or_data.split("/embed/")[1].split("?")[0]

                embed_src = f"https://www.youtube.com/embed/{vid}"

                # Fixed-size in-container YouTube player (200px height, 16:9 contained, no clipping, zero blur)
                media_viewer_html = f"""
                <div class="media-video-box">
                    <iframe src="{embed_src}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen title="{escape(m.title)}"></iframe>
                </div>
                """

            mat_cards.append(f"""
            <div class="resource-media-card">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        {type_badge}
                        <span style="font-size:10.5px; font-weight:700; color:var(--frost-navy-50); text-transform:uppercase; letter-spacing:0.5px;">{escape(m.topic)}</span>
                    </div>
                    <h4 style="font-size:13.5px; font-weight:800; color:var(--frost-navy); margin:4px 0 2px 0; line-height:1.35; height:36px; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">{escape(m.title)}</h4>
                    <p style="font-size:11.5px; color:var(--frost-navy-75); line-height:1.4; margin:0 0 6px 0; height:32px; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">{escape(m.description)}</p>

                    <!-- In-Container Media Box (Fixed 200px height, crisp, zero blur) -->
                    {media_viewer_html}
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; padding-top:10px; border-top:1px solid var(--icy-steel-30); margin-top:4px;">
                    {read_indicator}
                    <button type="button" class="btn-metal btn-sm" style="padding:4px 10px; font-size:11.5px;" onclick="window.StarAppBridge.dispatchAction('view_material_preview', '{{"material_id": "{m.id}"}}')">
                        Theater View &rarr;
                    </button>
                </div>
            </div>
            """)

        mats_grid = f"""
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(310px, 1fr)); gap:18px; align-items:stretch;">
            {"".join(mat_cards)}
        </div>
        """ if mat_cards else """
        <div style="padding:20px; text-align:center; color:var(--frost-navy-50); font-style:italic; background:rgba(234,244,255,0.4); border-radius:var(--radius-sm); border:1px dashed var(--icy-steel-50);">
            No learning resources of the selected format found for this milestone.
        </div>
        """

        badge_sections.append(f"""
        <!-- Badge Section: {escape(b.code)} (Zero blur, crisp styling) -->
        <div class="badge-resource-section">
            <!-- Badge Header -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; padding-bottom:12px; border-bottom:1.5px solid var(--icy-steel-30); flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-family:var(--font-family-mono); font-size:12.5px; font-weight:800; color:var(--snow-white); background:var(--deep-frozen-midnight); padding:3px 10px; border-radius:var(--radius-xs); letter-spacing:0.5px;">{escape(b.code)}</span>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0;">{escape(b.title)}</h3>
                    <span style="font-size:11px; color:var(--frost-navy-50); background:rgba(23,52,92,0.06); padding:2px 7px; border-radius:var(--radius-xs); font-weight:600;">{escape(b.category)}</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:11.5px; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(234,244,255,0.9); padding:3px 10px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-50);">
                        {len(b_mats)} Available {"Resource" if len(b_mats) == 1 else "Resources"}
                    </span>
                </div>
            </div>

            <!-- Below: Its Documents and Video Lectures (Properly Sized & Structured) -->
            {mats_grid}
        </div>
        """)

    content_body = "".join(badge_sections) if badge_sections else """
    <div class="badge-resource-section" style="padding:48px 24px; text-align:center; color:var(--frost-navy-50);">
        <p style="font-size:15px; font-weight:700; color:var(--deep-frozen-midnight); margin-bottom:6px;">No learning resources matched your criteria.</p>
        <p style="font-size:13px; margin:0;">Try selecting "All Badges" or toggling the format filter to All.</p>
    </div>
    """

    return f"""
    <div>
        <!-- Page Title & Guidance -->
        <div style="margin-bottom:24px; text-align:center;">
            <h2 style="font-size:1.55rem; font-weight:800; color:var(--frost-navy); margin-bottom:6px;">Milestone Learning Resources & Study Hub</h2>
            <p style="font-size:13.5px; color:var(--frost-navy-50);">Comprehensive engineering documentation and video lectures &mdash; read documents and watch videos directly inside StarApp.</p>
        </div>

        <!-- Top Liquid Glass Filter Toolbar -->
        <div class="liquid-glass-card" style="padding:16px 22px; margin-bottom:26px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-50); background:linear-gradient(135deg, rgba(255,255,255,0.92) 0%, rgba(234,244,255,0.7) 100%); box-shadow:0 4px 18px rgba(7,22,41,0.04);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                <!-- Left: Badge Selection Dropdown -->
                <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                    <label for="materials-badge-select" style="font-size:12.5px; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px;">Filter by Badge:</label>
                    <div class="liquid-select-wrapper" style="min-width:280px; width:auto;">
                        <select id="materials-badge-select" class="liquid-glass-control liquid-glass-select" onchange="window.StarAppBridge.dispatchAction('filter_materials_badge', this.value);">
                            <option value="all"{' selected' if selected_badge_filter == 'all' else ''}>All Badges (Full Curriculum)</option>
                            {"".join(badge_opts)}
                        </select>
                    </div>
                </div>

                <!-- Right: Selecting button to choose PDF or YouTube videos -->
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:12px; font-weight:800; color:var(--frost-navy-50); text-transform:uppercase; letter-spacing:0.5px;">Format:</span>
                    <div style="display:inline-flex; background:rgba(234,244,255,0.85); padding:3.5px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel); -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px); box-shadow:inset 1px 1px 1px rgba(255,255,255,0.9);">
                        <button type="button" onclick="window.StarAppBridge.dispatchAction('filter_materials_type', 'all')" style="{btn_all_style}">
                            All ({count_all})
                        </button>
                        <button type="button" onclick="window.StarAppBridge.dispatchAction('filter_materials_type', 'pdf')" style="{btn_pdf_style}">
                            <svg viewBox="0 0 24 24" style="width:14px; height:14px;" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                            PDF Documents ({count_pdf})
                        </button>
                        <button type="button" onclick="window.StarAppBridge.dispatchAction('filter_materials_type', 'youtube')" style="{btn_yt_style}">
                            <svg viewBox="0 0 24 24" style="width:14px; height:14px;" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                            YouTube Videos ({count_yt})
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Sequential Badge Sections: Badge Name, Below its Documents, Next Badge... -->
        <div>
            {content_body}
        </div>
    </div>
    """


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

    req_items = []
    for ext in extensions:
        badge = badges_map.get(ext.badge_id)
        b_code = badge.code if badge else ext.badge_id
        b_title = badge.title if badge else "Milestone Deliverable"
        
        # High-contrast action/status badge and current action footer
        if ext.status == "approved":
            status_pill = '<span class="status-pill status-approved" style="font-size:12px; font-weight:800; padding:5px 14px; background:var(--deep-frozen-midnight); color:var(--snow-white); border:1.5px solid var(--icy-steel); display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 8px rgba(23,52,92,0.25);">&#10003; Accepted &bull; Approved</span>'
            current_action_html = f"""
            <div style="margin-top:14px; padding-top:12px; border-top:1px solid var(--icy-steel-30); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--snow-white); background:var(--deep-frozen-midnight); padding:3px 9px; border-radius:var(--radius-xs);">Current Action</span>
                    <span style="font-size:12.5px; color:var(--deep-frozen-midnight); font-weight:700;">Extension granted to {escape(ext.proposed_deadline)} &bull; Synchronized across roadmap</span>
                </div>
                <div style="display:flex; gap:8px;">
                    <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('open_badge_detail_modal', '{ext.badge_id}')">
                        View Updated Timeline &rarr;
                    </button>
                    <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_to_submit_badge', '{ext.badge_id}')">
                        Submit Deliverable
                    </button>
                </div>
            </div>
            """
        elif ext.status == "rejected":
            status_pill = '<span class="status-pill status-rejected" style="font-size:12px; font-weight:800; padding:5px 14px; background:rgba(7,22,41,0.08); color:var(--frost-navy); border:1.5px solid var(--frost-navy-50); display:inline-flex; align-items:center; gap:6px;">&#10005; Rejected</span>'
            current_action_html = f"""
            <div style="margin-top:14px; padding-top:12px; border-top:1px solid var(--icy-steel-30); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--frost-navy); background:rgba(7,22,41,0.10); padding:3px 9px; border-radius:var(--radius-xs);">Current Action</span>
                    <span style="font-size:12.5px; color:var(--frost-navy); font-weight:600;">Original cutoff ({escape(ext.current_deadline)}) in effect &bull; Immediate deliverable required</span>
                </div>
                <button type="button" class="btn-metal btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_to_submit_badge', '{ext.badge_id}')">
                    Proceed to Submission &rarr;
                </button>
            </div>
            """
        else:
            status_pill = '<span class="status-pill status-active" style="font-size:12px; font-weight:800; padding:5px 14px; background:rgba(234,244,255,0.95); color:var(--deep-frozen-midnight); border:1.5px solid var(--deep-frozen-midnight); display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 8px rgba(23,52,92,0.12);"><span style="width:7px; height:7px; border-radius:50%; background:var(--deep-frozen-midnight); display:inline-block;"></span> Awaiting Review &bull; Pending</span>'
            current_action_html = f"""
            <div style="margin-top:14px; padding-top:12px; border-top:1px solid var(--icy-steel-30); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); background:rgba(23,52,92,0.08); padding:3px 9px; border-radius:var(--radius-xs);">Current Action</span>
                    <span style="font-size:12.5px; color:var(--frost-navy-75); font-weight:600;">Awaiting Guardian review by Dr. Elena Vance</span>
                </div>
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('open_badge_detail_modal', '{ext.badge_id}')">
                    Inspect Milestone &rarr;
                </button>
            </div>
            """

        guardian_note = ""
        if ext.guardian_response:
            guardian_note = f"""
            <div style="margin-top:12px; font-size:13px; padding:12px 16px; background:linear-gradient(135deg, rgba(234,244,255,0.85) 0%, rgba(255,255,255,0.95) 100%); border-radius:var(--radius-sm); border-left:4px solid var(--deep-frozen-midnight); border:1px solid var(--icy-steel-50); border-left-width:4px;">
                <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; margin-bottom:4px;">Guardian Review Feedback (Dr. Elena Vance):</div>
                <div style="color:var(--frost-navy); line-height:1.5;">{escape(ext.guardian_response)}</div>
            </div>
            """

        req_items.append(f"""
        <div class="liquid-glass-card" style="padding:22px 24px; margin-bottom:16px; background:linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(234,244,255,0.85) 100%); border:1.5px solid var(--icy-steel); border-radius:var(--radius-md); box-shadow:0 6px 20px rgba(7,22,41,0.06), inset 1px 1px 1px rgba(255,255,255,0.95);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:var(--snow-white); background:var(--deep-frozen-midnight); padding:4px 10px; border-radius:var(--radius-xs); border:1px solid var(--deep-frozen-midnight); letter-spacing:0.5px;">{escape(b_code)}</span>
                    <span style="font-size:15px; font-weight:800; color:var(--frost-navy);">{escape(b_title)}</span>
                </div>
                {status_pill}
            </div>

            <div style="display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:12px; margin-bottom:12px; padding:10px 16px; background:rgba(234,244,255,0.7); border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm);">
                <div>
                    <div style="font-size:10.5px; font-weight:700; text-transform:uppercase; color:var(--frost-navy-50); letter-spacing:0.5px; margin-bottom:2px;">Original Cutoff</div>
                    <div style="font-family:var(--font-family-mono); font-size:13px; font-weight:700; color:var(--frost-navy-75); text-decoration:line-through;">{escape(ext.current_deadline)}</div>
                </div>
                <div style="font-size:16px; font-weight:800; color:var(--deep-frozen-midnight); padding:0 4px;">&rarr;</div>
                <div>
                    <div style="font-size:10.5px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; margin-bottom:2px;">Requested Extension</div>
                    <div style="font-family:var(--font-family-mono); font-size:14px; font-weight:800; color:var(--deep-frozen-midnight);">{escape(ext.proposed_deadline)}</div>
                </div>
            </div>

            <div style="font-size:13px; color:var(--frost-navy); line-height:1.55; background:#FFFFFF; padding:12px 16px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-30); box-shadow:0 1px 4px rgba(7,22,41,0.02);">
                <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px; margin-bottom:4px;">Cosmonaut Technical Rationale:</div>
                {escape(ext.reason)}
            </div>

            {guardian_note}

            {current_action_html}
        </div>
        """)

    return f"""
    <div>
        <div style="margin-bottom:24px; text-align:center;">
            <h2 style="font-size:1.55rem; font-weight:800; color:var(--frost-navy); margin-bottom:6px;">Milestone Deadline Extension Portal</h2>
            <p style="font-size:13.5px; color:var(--frost-navy-50);">Request scheduling adjustments for active milestones and track Guardian evaluations in real-time.</p>
        </div>

        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(440px, 1fr)); gap:24px; align-items:start;">
            <!-- Container 1: Extension Request Form -->
            <div class="liquid-submission-portal" style="padding:28px 32px;">
                <div style="margin-bottom:20px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:14px;">
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">Request Deadline Extension</h3>
                    <div style="font-size:12.5px; color:var(--frost-navy-50);">Choose an in-progress milestone and specify a realistic engineering rationale.</div>
                </div>

                <form id="deadline-extension-form" onsubmit="event.preventDefault(); const b=document.getElementById('ext-badge'); const d=document.getElementById('ext-date'); const r=document.getElementById('ext-reason'); window.StarAppBridge.dispatchAction('submit_deadline_extension_request', JSON.stringify({{badge_id:b.value, proposed_deadline:d.value, reason:r.value}}));">
                    <!-- 1. Dropdown of current available non-completed badges -->
                    <div class="liquid-form-group" style="margin-bottom:20px;">
                        <label class="liquid-form-label" for="ext-badge">Target Available Milestone (In-Progress)</label>
                        <div class="liquid-select-wrapper">
                            <select id="ext-badge" class="liquid-glass-control liquid-glass-select" required>
                                {badge_opts}
                            </select>
                        </div>
                        <span class="liquid-form-hint">Only current non-completed milestones are eligible for extension requests.</span>
                    </div>

                    <!-- 2. Liquid Glass Calendar Datepicker -->
                    <div class="liquid-form-group" style="margin-bottom:20px;">
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
                        <span class="liquid-form-hint">Choose a future cutoff date allowing adequate buffer beyond the milestone deadline.</span>
                    </div>

                    <!-- 3. Reason Textarea -->
                    <div class="liquid-form-group" style="margin-bottom:24px;">
                        <label class="liquid-form-label" for="ext-reason">Technical Justification & Bottleneck Details</label>
                        <textarea id="ext-reason" class="liquid-glass-control" style="min-height:105px; padding:12px 16px; resize:vertical; font-family:var(--font-family-base); line-height:1.5;" placeholder="Describe the unexpected complexity, data pipeline latency, or algorithmic research requiring additional engineering time..." required></textarea>
                        <span class="liquid-form-hint">Provide at least 10 characters detailing the engineering rationale for your Guardian.</span>
                    </div>

                    <!-- 4. Submit Button -->
                    <div style="display:flex; justify-content:flex-end;">
                        <div class="btn-metal-wrapper" style="width:100%;">
                            <div class="btn-metal-inner"></div>
                            <button type="submit" class="btn-metal" style="width:100%; height:46px; font-size:14px; font-weight:700; letter-spacing:0.3px;">
                                Submit Extension Request for Guardian Review &rarr;
                            </button>
                        </div>
                    </div>
                </form>
            </div>

            <!-- Container 2: Submitted Requests & Status -->
            <div class="liquid-submission-portal" style="padding:28px 32px;">
                <div style="margin-bottom:20px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:14px;">
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">Submitted Requests & Actions</h3>
                    <div style="font-size:12.5px; color:var(--frost-navy-50);">Audit trail of all requested milestone extensions and mentor decisions.</div>
                </div>

                <div>
                    {"".join(req_items) if req_items else "<div style='padding:36px 20px; text-align:center; color:var(--frost-navy-50); font-style:italic;'>No extension requests submitted yet. Select an available milestone on the left to request a schedule adjustment.</div>"}
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

