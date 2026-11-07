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
        {"id": "c_announcements", "label": "Announcements", "icon": '<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>', "badge": unread_announcements_count},
        {"id": "c_extensions", "label": "Deadline Extensions", "icon": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>', "badge": 0},
        {"id": "c_activity", "label": "Activity Stream", "icon": '<svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>', "badge": 0}
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
        </ul>

        <div class="sidebar-footer">
            <div class="user-mini-card">
                <div class="user-avatar">{escape(current_user.avatar)}</div>
                <div class="user-details">
                    <div class="user-name">{escape(current_user.name)}</div>
                    <div class="user-role-text">Cosmonaut ID: {escape(current_user.id)}</div>
                </div>
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
    total_assigned = len(assigned_badges)
    completed_count = score_summary["approved_count"]
    active_count = max(0, total_assigned - completed_count)
    progress_pct = round((completed_count / max(1, total_assigned)) * 100.0, 1)

    kpis = f"""
    <div class="kpi-grid">
        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header"><span class="kpi-title">Assigned Badges</span></div>
            <div class="kpi-value">{total_assigned}</div>
            <div class="kpi-subtext">Published learning milestones</div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header"><span class="kpi-title">Completed Badges</span></div>
            <div class="kpi-value">{completed_count}</div>
            <div class="kpi-subtext">{progress_pct}% Total roadmap progress</div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header"><span class="kpi-title">Active Badges</span></div>
            <div class="kpi-value">{active_count}</div>
            <div class="kpi-subtext">Currently in learning / build phase</div>
        </div>

        <div class="liquid-glass-card kpi-card">
            <div class="kpi-header"><span class="kpi-title">Standard Average</span></div>
            <div class="kpi-value">{score_summary["average_marks"]} <span style="font-size:14px; opacity:0.6;">/ 50</span></div>
            <div class="kpi-subtext">{score_summary["average_percentage"]}% Standard score</div>
        </div>
    </div>
    """

    # Performance bar chart across completed badges
    perf_bars = []
    approved_asms = [a for a in assessments if a.decision == "approve"]
    if approved_asms:
        for a in approved_asms:
            pct = a.percentage
            perf_bars.append(f"""
            <div style="margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; font-size:13px; font-weight:600; margin-bottom:4px;">
                    <span>{escape(a.badge_id)} (Attempt #{a.attempt_number})</span>
                    <span style="color:var(--deep-frozen-midnight);">{a.total_marks} / 50.0 ({pct:.1f}%)</span>
                </div>
                <div style="height:12px; border-radius:var(--radius-full); background:rgba(157,183,213,0.3); overflow:hidden;">
                    <div style="height:100%; width:{pct}%; border-radius:var(--radius-full); background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
                </div>
            </div>
            """)
    else:
        perf_bars.append("<p style='font-size:13px; opacity:0.6;'>Complete badge project assessments to display performance trends.</p>")

    chart_card = render_liquid_card(
        title="Assessment Performance (50-Mark Standard Rubric)",
        subtitle="Standardized scores achieved across evaluated badge deliverables",
        content="".join(perf_bars)
    )

    # Strengths and improvement areas based on Guardian evaluation
    all_strengths = [a.strength_areas for a in assessments if a.strength_areas]
    all_improvements = [a.improvement_areas for a in assessments if a.improvement_areas]

    insights_content = f"""
    <div style="margin-bottom:14px;">
        <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">Guardian Recognized Strengths:</div>
        <p style="font-size:13.5px; color:var(--frost-navy); line-height:1.5;">{escape(all_strengths[-1] if all_strengths else "No strengths recorded yet.")}</p>
    </div>
    <div>
        <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">Areas for Growth:</div>
        <p style="font-size:13.5px; color:var(--frost-navy); line-height:1.5;">{escape(all_improvements[-1] if all_improvements else "Continue following standard best practices.")}</p>
    </div>
    """

    insights_card = render_liquid_card(
        title="Mentor Evaluation Insights",
        subtitle="Feedback extracted directly from Dr. Elena Vance's marksheets",
        content=insights_content
    )

    # Batch Leaderboard (visible to all, ranking all 6, but NO access to private profiles)
    leaderboard_rows = []
    for item in leaderboard:
        is_me = item["cosmonaut_id"] == current_user.id
        row_style = "background:rgba(23,52,92,0.1); font-weight:700;" if is_me else ""
        you_badge = '<span class="status-pill status-approved" style="margin-left:6px; font-size:10px;">YOU</span>' if is_me else ""
        rank_medal = f'#{item["rank"]}'
        if item["rank"] == 1:
            rank_medal = "🥇 #1"
        elif item["rank"] == 2:
            rank_medal = "🥈 #2"
        elif item["rank"] == 3:
            rank_medal = "🥉 #3"

        leaderboard_rows.append(f"""
        <tr style="{row_style}">
            <td style="font-weight:700;">{rank_medal}</td>
            <td>
                <div style="display:flex; align-items:center; gap:8px;">
                    <div class="user-avatar" style="width:26px; height:26px; font-size:10px;">{escape(item["avatar"])}</div>
                    <span>{escape(item["cosmonaut_name"])}</span>
                    {you_badge}
                </div>
            </td>
            <td style="text-align:center;">{item["completed_badges"]}</td>
            <td style="text-align:center; font-weight:700; color:var(--deep-frozen-midnight);">{item["average_marks"]} / 50</td>
            <td style="text-align:center;">{item["average_percentage"]}%</td>
        </tr>
        """)

    leaderboard_card = render_liquid_card(
        title="Batch Orion-24 Official Leaderboard",
        subtitle="Ranked by average assessment score (/50) on approved badges. Updated in real-time.",
        content=f"""
        <div class="table-responsive">
            <table class="star-table">
                <thead>
                    <tr>
                        <th style="width:10%;">Rank</th>
                        <th style="width:40%;">Cosmonaut</th>
                        <th style="width:15%; text-align:center;">Badges Earned</th>
                        <th style="width:20%; text-align:center;">Average Score</th>
                        <th style="width:15%; text-align:center;">Standard %</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(leaderboard_rows)}
                </tbody>
            </table>
        </div>
        """
    )

    # Skills & Certifications summary
    skills_pills = "".join([f'<span class="status-pill status-active" style="margin:2px;">{escape(s)}</span>' for s in profile.skills]) or '<span style="font-size:12px; opacity:0.6;">Add skills in Profile.</span>'
    profile_widget = render_liquid_card(
        title="My Profile Skills & Certifications",
        subtitle="Live skills entered in your profile and reflected in batch queries",
        content=f"""
        <div style="margin-bottom:12px;">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:6px;">Current Skills:</div>
            <div style="display:flex; flex-wrap:wrap; gap:4px;">{skills_pills}</div>
        </div>
        <div style="display:flex; justify-content:flex-end;">
            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_profile')">Edit Skills in Profile →</button>
        </div>
        """
    )

    return f"""
    <div>
        {kpis}
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px;">
            {chart_card}
            {insights_card}
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
            {leaderboard_card}
            {profile_widget}
        </div>
    </div>
    """

# ==============================================================================
# 6.2 COSMONAUT PROFILE (Interactive Skill & Certification Management)
# ==============================================================================

def render_cosmonaut_profile(current_user: User, profile: CosmonautProfile) -> str:
    skills_tags = []
    for s in profile.skills:
        skills_tags.append(f"""
        <div style="display:inline-flex; align-items:center; gap:6px; padding:4px 10px; background:rgba(23,52,92,0.1); border:1px solid var(--icy-steel); border-radius:var(--radius-full); font-size:13px; font-weight:600; color:var(--deep-frozen-midnight);">
            <span>{escape(s)}</span>
            <span style="cursor:pointer; font-weight:800; font-size:14px; opacity:0.7;" onclick="window.StarAppBridge.dispatchAction('remove_skill', '{escape(s)}')">&times;</span>
        </div>
        """)

    certs_items = []
    for idx, c in enumerate(profile.certifications):
        certs_items.append(f"""
        <div style="display:flex; align-items:center; justify-content:space-between; padding:10px 14px; background:rgba(234,244,255,0.6); border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); margin-bottom:8px;">
            <div>
                <div style="font-weight:700; color:var(--frost-navy); font-size:13.5px;">{escape(c.get("name",""))}</div>
                <div style="font-size:12px; color:var(--frost-navy-50);">Issuer: {escape(c.get("issuer",""))} • Year: {escape(c.get("year",""))}</div>
            </div>
            <button type="button" class="btn-secondary btn-sm" style="color:var(--frost-navy-50);" onclick="window.StarAppBridge.dispatchAction('remove_certification', '{idx}')">Remove</button>
        </div>
        """)

    return f"""
    <div>
        <div style="margin-bottom:20px;">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Cosmonaut Profile & Credentials</h2>
            <p style="font-size:13px; color:var(--frost-navy-50);">Manage your personal information, specialized skills, and verified industry certifications.</p>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px;">
            {render_liquid_card(
                title="Cadet Identification & Mentorship",
                subtitle="Official academy placement details",
                content=f'''
                <div style="display:flex; align-items:center; gap:16px; margin-bottom:16px;">
                    <div class="user-avatar" style="width:64px; height:64px; font-size:24px;">{escape(current_user.avatar)}</div>
                    <div>
                        <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0;">{escape(current_user.name)}</h3>
                        <div style="font-size:13px; color:var(--deep-frozen-midnight); font-weight:600;">Cadet ID: {escape(current_user.id)}</div>
                        <div style="font-size:12px; color:var(--frost-navy-50);">{escape(current_user.email)}</div>
                    </div>
                </div>

                <div style="background:rgba(234,244,255,0.4); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); font-size:13px;">
                    <div><strong>Training Cohort:</strong> {escape(profile.batch_name)}</div>
                    <div style="margin-top:4px;"><strong>Assigned Guardian:</strong> Dr. Elena Vance</div>
                    <div style="margin-top:4px;"><strong>Mentor Credentials:</strong> {escape(profile.guardian_credentials)}</div>
                </div>
                '''
            )}

            {render_liquid_card(
                title="Skills & Technical Competencies",
                subtitle="Add competencies to display in your dossier and dashboard",
                content=f'''
                <form onsubmit="event.preventDefault(); const inp=document.getElementById('new-skill-input'); if(inp.value.trim()){{ window.StarAppBridge.dispatchAction('add_skill', inp.value.trim()); inp.value=''; }}" style="display:flex; gap:8px; margin-bottom:14px;">
                    <input type="text" id="new-skill-input" class="form-control" placeholder="e.g. Distributed SQL, Spark, Kafka" required>
                    <button type="submit" class="btn-metal">Add Skill</button>
                </form>

                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                    {"".join(skills_tags) if skills_tags else "<span style='font-size:13px; opacity:0.6;'>No skills recorded yet.</span>"}
                </div>
                '''
            )}
        </div>

        <div>
            {render_liquid_card(
                title="Industry Certifications",
                subtitle="Credential credentials automatically synchronized with Guardian reports",
                content=f'''
                <form onsubmit="event.preventDefault(); const n=document.getElementById('cert-name'); const i=document.getElementById('cert-issuer'); const y=document.getElementById('cert-year'); window.StarAppBridge.dispatchAction('add_certification', JSON.stringify({{name:n.value, issuer:i.value, year:y.value}})); n.value=''; i.value=''; y.value='';" style="display:grid; grid-template-columns:2fr 2fr 1fr auto; gap:10px; margin-bottom:16px;">
                    <input type="text" id="cert-name" class="form-control" placeholder="Certification Name" required>
                    <input type="text" id="cert-issuer" class="form-control" placeholder="Issuing Body" required>
                    <input type="text" id="cert-year" class="form-control" placeholder="Year" required>
                    <button type="submit" class="btn-metal">Add Credential</button>
                </form>

                <div>
                    {"".join(certs_items) if certs_items else "<p style='font-size:13px; opacity:0.6;'>No external certifications recorded yet.</p>"}
                </div>
                '''
            )}
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
                "opacity: 0.82; "
                "color: var(--frost-navy-50);"
            )
            code_style = "color: var(--frost-navy-50); font-weight: 700; font-family: var(--font-family-mono); font-size: 11.5px;"
            title_style = "color: var(--frost-navy); font-weight: 700; font-size: 14px; margin: 3px 0 2px; opacity: 0.75;"
            desc_style = "color: var(--frost-navy-50); font-size: 11px;"
            status_html = '<span class="status-pill status-locked" style="font-size:10.5px; padding:2px 8px;">Locked</span>'

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
            "date_label": "Allocated",
            "status": "Completed" if state in ["completed", "active"] else "Locked",
            "cls": "completed" if state in ["completed", "active"] else "locked",
            "desc": "Badge curriculum and hands-on project deliverable commissioned by Guardian Dr. Elena Vance."
        },
        {
            "num": 2,
            "title": "Learning Time",
            "date": f"{learn_start} to {learn_end}",
            "date_label": "Learning Window",
            "status": "Completed" if (state == "completed" or (state == "active" and today_str >= learn_end)) else ("Active" if state == "active" else "Locked"),
            "cls": "completed" if (state == "completed" or (state == "active" and today_str >= learn_end)) else ("active" if state == "active" else "locked"),
            "desc": "Study comprehensive documentation, architectural patterns, and embedded technical video lectures."
        },
        {
            "num": 3,
            "title": "Project Time",
            "date": f"{proj_start} to {proj_end}",
            "date_label": "Project Window",
            "status": "Completed" if state == "completed" else ("Active" if state == "active" else "Locked"),
            "cls": "completed" if state == "completed" else ("active" if state == "active" else "locked"),
            "desc": "Hands-on engineering: repository code construction, automated testing, and deliverable packaging."
        },
        {
            "num": 4,
            "title": "Submission Date",
            "date": sub_deadline,
            "date_label": "Deadline",
            "status": "Submitted" if state == "completed" else ("Due Soon" if state == "active" else "Locked"),
            "cls": "completed" if state == "completed" else ("active" if state == "active" else "locked"),
            "desc": "Hard deliverable intake cutoff. Project repository snapshot locked for formal review."
        },
        {
            "num": 5,
            "title": "Review Date",
            "date": review_date,
            "date_label": "Evaluation",
            "status": "Evaluated" if state == "completed" else ("Scheduled" if state == "active" else "Locked"),
            "cls": "completed" if state == "completed" else ("active" if state == "active" else "locked"),
            "desc": "Guardian evaluation on universal 5-criterion rubric (50 marks total)."
        },
        {
            "num": 6,
            "title": "Badge Earned Date",
            "date": award_date,
            "date_label": "Award Date",
            "status": "Earned & Issued" if state == "completed" else ("Target Date" if state == "active" else "Locked"),
            "cls": "completed" if state == "completed" else ("active" if state == "active" else "locked"),
            "desc": "Milestone credential officially awarded and permanently registered to Cosmonaut portfolio."
        }
    ]

    steps_html = []
    for s in steps:
        pill_status = "approved" if s["status"] in ["Completed", "Submitted", "Evaluated", "Earned & Issued"] else ("active" if "Active" in s["status"] or "Due" in s["status"] else "locked")
        steps_html.append(f"""
        <div class="timeline-step-card {s['cls']}">
            <div class="timeline-step-header">
                <div class="timeline-step-title">
                    <span style="display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; border-radius:var(--radius-full); background:var(--deep-frozen-midnight); color:var(--snow-white); font-size:11px; font-weight:800;">{s['num']}</span>
                    <span>{escape(s['title'])}</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="timeline-step-date"><strong>{s['date_label']}:</strong> {escape(s['date'])}</span>
                    {render_status_pill(pill_status)}
                </div>
            </div>
            <div class="timeline-step-desc">{escape(s['desc'])}</div>
        </div>
        """)

    materials_list = []
    for m in materials:
        materials_list.append(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 12px; background:rgba(234,244,255,0.6); border-radius:var(--radius-sm); margin-bottom:4px; font-size:12.5px;">
            <span><strong>{escape(m.title)}</strong> ({m.material_type.upper()})</span>
            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('view_material_preview', '{{\"material_id\": \"{m.id}\"}}')">Study Now</button>
        </div>
        """)

    # Contextual action buttons
    actions = []
    if is_guardian:
        actions.append(f"""
        <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('open_edit_badge_modal', '{{\"badge_id\": \"{badge.id}\"}}')">
            Decide / Edit Timelines
        </button>
        """)
    else:
        if state in ["active", "completed"]:
            actions.append(f"""
            <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('nav_to_submit_badge', '{badge.id}')">
                Proceed to Project Submission →
            </button>
            """)
        else:
            actions.append("""
            <div style="font-size:12.5px; color:var(--frost-navy-50); font-style:italic; align-self:center;">
                🔒 Milestone locked until prerequisite badges are successfully completed.
            </div>
            """)

    actions.append("""
    <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{}')">Close Window</button>
    """)

    return f"""
    <div>
        <!-- Window Header -->
        <div style="display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:12px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px;">
            <div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:12px; font-weight:800; font-family:var(--font-family-mono); color:var(--deep-frozen-midnight);">{escape(badge.code)}</span>
                    <span style="font-size:12px; color:var(--frost-navy-50);">• {escape(badge.category)}</span>
                </div>
                <h3 style="font-size:1.35rem; font-weight:800; color:var(--frost-navy); margin:4px 0 2px;">{escape(badge.title)}</h3>
                <p style="font-size:13px; color:var(--frost-navy-50); margin:0;">{escape(badge.description)}</p>
            </div>
            <div>{render_status_pill(state)}</div>
        </div>

        <!-- Project Deliverable Requirements Box -->
        <div style="background:rgba(234,244,255,0.45); padding:10px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); margin-bottom:14px; font-size:12.5px; line-height:1.4;">
            <strong style="color:var(--deep-frozen-midnight); text-transform:uppercase; font-size:11px;">Deliverable Requirements:</strong> {escape(badge.project_requirements)}
        </div>

        <!-- 6-Stage Professional Timeline Flow -->
        <div style="margin-bottom:14px;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                <h4 style="font-size:1.05rem; font-weight:700; color:var(--frost-navy); margin:0;">Milestone Lifecycle Timeline</h4>
                <span style="font-size:11px; font-weight:600; color:var(--deep-frozen-midnight);">Decided by Guardian Dr. Elena Vance</span>
            </div>
            <div class="badge-timeline-container">
                {"".join(steps_html)}
            </div>
        </div>

        <!-- Available Study Materials (if any) -->
        {"<div style='margin-bottom:14px;'><div style='font-size:11.5px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:6px;'>Learning Materials for this Milestone:</div>" + "".join(materials_list) + "</div>" if materials_list else ""}

        <!-- Modal Actions Footer -->
        <div style="display:flex; justify-content:flex-end; align-items:center; gap:10px; padding-top:12px; border-top:1px solid var(--icy-steel-30);">
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

    # History of previous attempts for selected badge
    matching_subs = [s for s in submissions if s.badge_id == selected_badge_id]
    attempt_rows = []
    for s in matching_subs:
        attempt_rows.append(f"""
        <tr>
            <td style="font-weight:700;">Attempt #{s.attempt_number}</td>
            <td style="text-transform:uppercase; font-size:12px;">{escape(s.submission_type)}</td>
            <td style="font-family:var(--font-family-mono); font-size:12px;">{escape(s.file_name or s.payload[:30])}</td>
            <td>{escape(s.submitted_at[:16].replace('T', ' '))}</td>
            <td>{render_status_pill(s.status)}</td>
            <td>
                <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('view_submission_artifact', '{{\"submission_id\": \"{s.id}\"}}')">Inspect</button>
            </td>
        </tr>
        """)

    history_table = f"""
    <div class="table-responsive">
        <table class="star-table">
            <thead>
                <tr>
                    <th>Attempt</th>
                    <th>Type</th>
                    <th>Deliverable Reference</th>
                    <th>Submitted At</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {"".join(attempt_rows) if attempt_rows else '<tr><td colspan="6" style="text-align:center; padding:24px; color:var(--frost-navy-50);">No previous attempts submitted for this badge.</td></tr>'}
            </tbody>
        </table>
    </div>
    """

    return f"""
    <div>
        <div style="margin-bottom:20px;">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Project Deliverable Submission Hub</h2>
            <p style="font-size:13px; color:var(--frost-navy-50);">Submit project deliverables for Guardian assessment across the standard 50-mark rubric.</p>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px;">
            {render_liquid_card(
                title="Deliverable Submission Portal",
                subtitle="Supports PDF upload, GitHub repository link, or Code file upload",
                content=f'''
                <form id="project-submission-form" onsubmit="event.preventDefault(); window.StarAppBridge.dispatchAction('submit_project_deliverable', '{{}}');">
                    <div class="form-group">
                        <label class="form-label">Target Badge Milestone</label>
                        <select id="submission-badge-id" class="form-select" onchange="window.StarAppBridge.dispatchAction('change_submission_target_badge', this.value)">
                            {"".join(badge_options)}
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Submission Method</label>
                        <select id="submission-type" class="form-select" onchange="window.StarAppBridge.dispatchAction('toggle_submission_method_fields', this.value)">
                            <option value="pdf">PDF Document Upload</option>
                            <option value="github">GitHub Repository Link</option>
                            <option value="code">Code / Script File Upload</option>
                        </select>
                    </div>

                    <div id="field-github-container" style="display:none;" class="form-group">
                        <label class="form-label">GitHub Repository URL</label>
                        <input type="url" id="submission-github-url" class="form-control" placeholder="https://github.com/username/project-repo">
                    </div>

                    <div id="field-file-container" class="form-group">
                        <label class="form-label" id="file-input-label">Select PDF File</label>
                        <input type="file" id="submission-file-input" class="form-control" accept=".pdf">
                    </div>

                    <div style="display:flex; justify-content:flex-end; margin-top:20px;">
                        <button type="submit" class="btn-metal">
                            Submit Deliverable for Guardian Review
                        </button>
                    </div>
                </form>
                '''
            )}

            {render_liquid_card(
                title="Submission & Assessment History",
                subtitle="All submitted attempts and evaluation statuses for this milestone",
                content=history_table
            )}
        </div>
    </div>
    """

# ==============================================================================
# 6.6 ASSESSMENT RESULTS & MARKSHEETS
# ==============================================================================

def render_cosmonaut_results(
    assessments: List[AssessmentMarksheet],
    badges_map: Dict[str, Badge],
    selected_marksheet_id: Optional[str] = None
) -> str:
    if not assessments:
        return """
        <div style="text-align:center; padding:60px 20px;">
            <h3 style="font-size:1.3rem; font-weight:800; color:var(--frost-navy);">No Evaluated Marksheets Available</h3>
            <p style="font-size:14px; color:var(--frost-navy-50); margin-top:6px;">Submit a project deliverable to receive your official 50-mark assessment marksheet from Dr. Elena Vance.</p>
        </div>
        """

    selected_asm = None
    if selected_marksheet_id:
        for a in assessments:
            if a.id == selected_marksheet_id:
                selected_asm = a
                break

    if not selected_asm:
        selected_asm = assessments[0]

    badge = badges_map.get(selected_asm.badge_id)
    same_badge_attempts = [a for a in assessments if a.badge_id == selected_asm.badge_id]

    # Sidebar list of all marksheets
    list_items = []
    for a in assessments:
        b = badges_map.get(a.badge_id)
        b_title = b.title if b else a.badge_id
        is_active = a.id == selected_asm.id
        cls = "background:var(--deep-frozen-midnight); color:var(--snow-white);" if is_active else "background:rgba(255,255,255,0.7); color:var(--frost-navy);"

        list_items.append(f"""
        <div style="padding:12px; border-radius:var(--radius-md); margin-bottom:8px; cursor:pointer; {cls} border:1px solid var(--icy-steel-30);" onclick="window.StarAppBridge.dispatchAction('view_marksheet', '{{\"marksheet_id\": \"{a.id}\"}}')">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:11px; font-weight:700; text-transform:uppercase;">{escape(b_title)}</span>
                <span style="font-weight:700;">{a.total_marks}/50</span>
            </div>
            <div style="font-size:12px; opacity:0.8; margin-top:2px;">Attempt #{a.attempt_number} • {escape(a.reviewed_at[:10])}</div>
        </div>
        """)

    return f"""
    <div>
        <div style="margin-bottom:20px;">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Official Assessment Marksheets</h2>
            <p style="font-size:13px; color:var(--frost-navy-50);">Complete breakdown of the standard 50-mark rubric evaluated by your Guardian.</p>
        </div>

        <div style="display:grid; grid-template-columns:300px 1fr; gap:20px;">
            <div>
                <h4 style="font-size:13px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:10px;">Evaluations:</h4>
                {"".join(list_items)}
            </div>

            <div>
                {render_standard_marksheet(selected_asm, badge, same_badge_attempts)}
            </div>
        </div>
    </div>
    """

# ==============================================================================
# 6.7 LEARNING MATERIALS (In-App PDF Viewer & Embedded YouTube Player)
# ==============================================================================

def render_cosmonaut_materials(
    materials: List[LearningMaterial],
    badges_map: Dict[str, Badge],
    selected_badge_filter: str = "all"
) -> str:
    filtered = materials
    if selected_badge_filter != "all":
        filtered = [m for m in materials if m.badge_id == selected_badge_filter]

    cards = []
    for m in filtered:
        badge = badges_map.get(m.badge_id)
        badge_name = badge.title if badge else m.badge_id
        type_pill = render_status_pill("active" if m.material_type == "youtube" else "completed")

        cards.append(f"""
        <div class="liquid-glass-card" style="margin-bottom:14px;">
            <div class="card-content" style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <span style="font-size:11px; font-weight:700; color:var(--deep-frozen-midnight);">{escape(badge_name)}</span>
                        {type_pill}
                        <span style="font-size:11px; color:var(--frost-navy-50);">Topic: {escape(m.topic)}</span>
                    </div>
                    <h3 style="font-size:1.15rem; font-weight:700; color:var(--frost-navy);">{escape(m.title)}</h3>
                    <p style="font-size:13px; color:var(--frost-navy-50); margin-top:2px;">{escape(m.description)}</p>
                </div>
                <div>
                    <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('view_material_preview', '{{\"material_id\": \"{m.id}\"}}')">
                        Open In-App
                    </button>
                </div>
            </div>
        </div>
        """)

    return f"""
    <div>
        <div style="margin-bottom:20px;">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Learning Resources & Study Hub</h2>
            <p style="font-size:13px; color:var(--frost-navy-50);">Access documentation and video lectures without leaving StarApp.</p>
        </div>

        <div>
            {"".join(cards) if cards else "<p style='padding:30px; text-align:center; color:var(--frost-navy-50);'>No materials published for this selection.</p>"}
        </div>
    </div>
    """

# ==============================================================================
# 6.9 DEADLINE EXTENSION REQUESTS
# ==============================================================================

def render_cosmonaut_extensions(
    assigned_badges: List[Badge],
    extensions: List[DeadlineExtension],
    badges_map: Dict[str, Badge]
) -> str:
    badge_opts = "".join([f'<option value="{b.id}">{escape(b.code)}: {escape(b.title)}</option>' for b in assigned_badges])

    req_items = []
    for ext in extensions:
        badge = badges_map.get(ext.badge_id)
        b_title = badge.title if badge else ext.badge_id
        pill = render_status_pill(ext.status)

        guardian_note = ""
        if ext.guardian_response:
            guardian_note = f"""
            <div style="margin-top:8px; font-size:12.5px; padding:8px 12px; background:rgba(23,52,92,0.06); border-radius:var(--radius-xs);">
                <strong>Guardian Note:</strong> {escape(ext.guardian_response)}
            </div>
            """

        req_items.append(f"""
        <div class="liquid-glass-card" style="margin-bottom:12px;">
            <div class="card-content">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <h3 style="font-size:1.1rem; font-weight:700; color:var(--frost-navy);">{escape(b_title)}</h3>
                    {pill}
                </div>
                <div style="font-size:12.5px; color:var(--frost-navy-50); margin-bottom:6px;">
                    Original: <span style="font-family:var(--font-family-mono);">{escape(ext.current_deadline)}</span> → Proposed: <span style="font-family:var(--font-family-mono); font-weight:700; color:var(--deep-frozen-midnight);">{escape(ext.proposed_deadline)}</span>
                </div>
                <div style="font-size:13px; color:var(--frost-navy);">{escape(ext.reason)}</div>
                {guardian_note}
            </div>
        </div>
        """)

    return f"""
    <div>
        <div style="margin-bottom:20px;">
            <h2 style="font-size:1.4rem; font-weight:800; color:var(--frost-navy);">Milestone Deadline Extension Requests</h2>
            <p style="font-size:13px; color:var(--frost-navy-50);">Request an adjustment to a submission deadline with an engineering justification.</p>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
            {render_liquid_card(
                title="Request Deadline Extension",
                subtitle="Approved requests automatically recalculate your badge timeline",
                content=f'''
                <form onsubmit="event.preventDefault(); const b=document.getElementById('ext-badge'); const d=document.getElementById('ext-date'); const r=document.getElementById('ext-reason'); window.StarAppBridge.dispatchAction('submit_deadline_extension_request', JSON.stringify({{badge_id:b.value, proposed_deadline:d.value, reason:r.value}}));">
                    <div class="form-group">
                        <label class="form-label">Milestone Badge</label>
                        <select id="ext-badge" class="form-select">
                            {badge_opts}
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Proposed New Deadline</label>
                        <input type="date" id="ext-date" class="form-control" required>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Engineering Justification</label>
                        <textarea id="ext-reason" class="form-textarea" placeholder="Detail the technical or operational bottleneck requiring extension..." required></textarea>
                    </div>

                    <div style="display:flex; justify-content:flex-end; margin-top:16px;">
                        <button type="submit" class="btn-metal">Submit Extension Request</button>
                    </div>
                </form>
                '''
            )}

            {render_liquid_card(
                title="My Request History",
                subtitle="Review past requests and mentor responses",
                content="".join(req_items) if req_items else "<p style='font-size:13px; opacity:0.6;'>No extension requests submitted.</p>"
            )}
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

