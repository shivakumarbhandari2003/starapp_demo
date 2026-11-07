"""
STARAPP SHARED VIEW COMPONENTS
Reusable UI templates for liquid-glass containers, marksheets, timelines, and navigation.
"""

import html
from typing import List, Dict, Any, Optional
from starapp.models import AssessmentMarksheet, BadgeTimeline, Badge, Notification, User

def escape(text: Any) -> str:
    return html.escape(str(text or ""))

def render_liquid_card(
    content: str,
    title: str = "",
    subtitle: str = "",
    actions_html: str = "",
    dark: bool = False,
    extra_class: str = "",
    card_id: str = ""
) -> str:
    """Standard reusable Liquid-Glass container matching code.txt specification."""
    dark_class = "dark" if dark else ""
    id_attr = f'id="{escape(card_id)}"' if card_id else ""
    header_html = ""
    if title or actions_html:
        header_html = f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px;">
            <div>
                {f'<h3 style="font-size:1.1rem; font-weight:700; color:inherit; margin:0;">{escape(title)}</h3>' if title else ''}
                {f'<p style="font-size:0.8rem; color:inherit; opacity:0.75; margin-top:2px;">{escape(subtitle)}</p>' if subtitle else ''}
            </div>
            {f'<div>{actions_html}</div>' if actions_html else ''}
        </div>
        """
    return f"""
    <div class="liquid-glass-card {dark_class} {escape(extra_class)}" {id_attr}>
        <div class="card-content">
            {header_html}
            {content}
        </div>
    </div>
    """

def render_liquid_button(
    text: str,
    action: str,
    payload_json: str = "{}",
    extra_class: str = "",
    icon_svg: str = ""
) -> str:
    """Button implementing the liquid styling from code.txt."""
    onclick_attr = f"window.StarAppBridge.dispatchAction('{escape(action)}', '{escape(payload_json)}')"
    return f"""
    <button type="button" class="btn-liquid {escape(extra_class)}" onclick="{onclick_attr}">
        {icon_svg}
        <span>{escape(text)}</span>
    </button>
    """

def render_metal_button(
    text: str,
    action: str,
    payload_json: str = "{}",
    variant: str = "primary",
    icon_svg: str = ""
) -> str:
    """3D tactile button matching MetalButton from code.txt."""
    onclick_attr = f"window.StarAppBridge.dispatchAction('{escape(action)}', '{escape(payload_json)}')"
    return f"""
    <div class="btn-metal-wrapper">
        <div class="btn-metal-inner"></div>
        <button type="button" class="btn-metal" onclick="{onclick_attr}">
            {icon_svg}
            <span>{escape(text)}</span>
        </button>
    </div>
    """

def render_status_pill(status: str) -> str:
    status_lower = (status or "").lower().replace(" ", "_")
    cls_map = {
        "approved": "status-approved",
        "completed": "status-completed",
        "active": "status-active",
        "pending": "status-pending",
        "awaiting_review": "status-awaiting-review",
        "resubmission_requested": "status-resubmit",
        "rejected": "status-rejected",
        "locked": "status-locked"
    }
    css_class = cls_map.get(status_lower, "status-pending")
    label = status.replace("_", " ").title()
    return f'<span class="status-pill {css_class}">{escape(label)}</span>'

def render_standard_marksheet(
    marksheet: AssessmentMarksheet,
    badge: Optional[Badge] = None,
    all_attempts: Optional[List[AssessmentMarksheet]] = None
) -> str:
    """Renders the standard 50-mark marksheet layout with the 5 criteria breakdown."""
    badge_title = badge.title if badge else "Project Assessment"
    badge_code = badge.code if badge else "STAR-RUBRIC"

    # Multi-attempt tab navigation if multiple attempts exist
    attempts_tabs_html = ""
    if all_attempts and len(all_attempts) > 1:
        tab_buttons = []
        for att in all_attempts:
            is_active = att.id == marksheet.id
            active_style = "background:var(--deep-frozen-midnight); color:var(--snow-white);" if is_active else "background:rgba(234,244,255,0.7); color:var(--frost-navy);"
            payload = f'{{"marksheet_id": "{att.id}"}}'
            tab_buttons.append(
                f'<button type="button" class="btn-secondary btn-sm" style="{active_style}" onclick="window.StarAppBridge.dispatchAction(\'view_marksheet\', \'{escape(payload)}\')">Attempt {att.attempt_number} ({att.total_marks}/50)</button>'
            )
        attempts_tabs_html = f'<div style="display:flex; gap:8px; margin-bottom:16px;">{"".join(tab_buttons)}</div>'

    decision_pill = render_status_pill(marksheet.decision)

    return f"""
    <div class="marksheet-view">
        <div class="marksheet-header">
            <div>
                <div style="font-size:12px; font-weight:700; color:var(--icy-steel); letter-spacing:1px; text-transform:uppercase;">
                    Standard Evaluation Rubric — Attempt #{marksheet.attempt_number}
                </div>
                <h2 style="font-size:1.4rem; font-weight:800; margin-top:2px; color:var(--snow-white);">{escape(badge_code)}: {escape(badge_title)}</h2>
                <div style="font-size:12px; color:var(--icy-steel); margin-top:4px;">
                    Evaluated by <strong>{escape(marksheet.reviewer_name)}</strong> on {escape(marksheet.reviewed_at[:10])}
                </div>
            </div>
            <div class="marksheet-score-badge">
                <div class="marksheet-score-num">{marksheet.total_marks} <span style="font-size:1rem; opacity:0.7;">/ 50</span></div>
                <div class="marksheet-percent">{marksheet.percentage}% Standard Score</div>
                <div style="margin-top:6px;">{decision_pill}</div>
            </div>
        </div>

        <div class="marksheet-body">
            {attempts_tabs_html}

            <table class="marksheet-rubric-table">
                <thead>
                    <tr>
                        <th style="width:45%;">Assessment Criterion</th>
                        <th style="width:35%;">Evaluation Scope</th>
                        <th style="width:10%; text-align:center;">Max</th>
                        <th style="width:10%; text-align:center;">Score</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>1. Business Understanding</strong></td>
                        <td style="font-size:12px; color:var(--frost-navy-50);">Problem formulation, compliance boundaries, and business impact</td>
                        <td style="text-align:center;">10.0</td>
                        <td style="text-align:center; font-weight:700; color:var(--deep-frozen-midnight);">{marksheet.business_understanding}</td>
                    </tr>
                    <tr>
                        <td><strong>2. Architecture / Report</strong></td>
                        <td style="font-size:12px; color:var(--frost-navy-50);">Modularity, system design rigor, diagrams, and written documentation</td>
                        <td style="text-align:center;">10.0</td>
                        <td style="text-align:center; font-weight:700; color:var(--deep-frozen-midnight);">{marksheet.architecture_report}</td>
                    </tr>
                    <tr>
                        <td><strong>3. Technical Knowledge</strong></td>
                        <td style="font-size:12px; color:var(--frost-navy-50);">Code robustness, algorithm optimization, edge-case handling</td>
                        <td style="text-align:center;">10.0</td>
                        <td style="text-align:center; font-weight:700; color:var(--deep-frozen-midnight);">{marksheet.technical_knowledge}</td>
                    </tr>
                    <tr>
                        <td><strong>4. Presentation</strong></td>
                        <td style="font-size:12px; color:var(--frost-navy-50);">Narrative coherence, clarity of demonstration, structured delivery</td>
                        <td style="text-align:center;">10.0</td>
                        <td style="text-align:center; font-weight:700; color:var(--deep-frozen-midnight);">{marksheet.presentation}</td>
                    </tr>
                    <tr>
                        <td><strong>5. Question & Answering</strong></td>
                        <td style="font-size:12px; color:var(--frost-navy-50);">Defense of engineering trade-offs and domain comprehension</td>
                        <td style="text-align:center;">10.0</td>
                        <td style="text-align:center; font-weight:700; color:var(--deep-frozen-midnight);">{marksheet.qa}</td>
                    </tr>
                    <tr style="background:var(--frost-mist); font-weight:800;">
                        <td colspan="2" style="text-align:right; text-transform:uppercase; letter-spacing:0.5px;">Universal Assessment Total:</td>
                        <td style="text-align:center;">50.0</td>
                        <td style="text-align:center; font-size:1.15rem; color:var(--deep-frozen-midnight);">{marksheet.total_marks}</td>
                    </tr>
                </tbody>
            </table>

            <div class="marksheet-feedback-section">
                <div class="feedback-card">
                    <div class="feedback-card-title">Identified Strengths</div>
                    <p style="font-size:13.5px; line-height:1.5; color:var(--frost-navy);">{escape(marksheet.strength_areas or "No specific strengths highlighted.")}</p>
                </div>
                <div class="feedback-card">
                    <div class="feedback-card-title">Areas for Improvement</div>
                    <p style="font-size:13.5px; line-height:1.5; color:var(--frost-navy);">{escape(marksheet.improvement_areas or "No critical weaknesses noted.")}</p>
                </div>
            </div>

            <div style="background:rgba(23,52,92,0.04); border-left:4px solid var(--deep-frozen-midnight); padding:16px; border-radius:var(--radius-sm);">
                <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">
                    Guardian Synthesis & Recommendation
                </div>
                <p style="font-size:14px; color:var(--frost-navy); line-height:1.6; margin:0;">
                    {escape(marksheet.overall_feedback or "No feedback recorded.")}
                </p>
            </div>
        </div>
    </div>
    """

def render_9point_timeline(timeline: BadgeTimeline, badge: Optional[Badge] = None) -> str:
    """Renders the comprehensive 9-point milestone timeline for a badge."""
    badge_title = badge.title if badge else "Training Milestone"
    nodes = [
        {"num": 1, "label": "Badge Assignment", "date": timeline.assignment_date, "desc": "Assigned to Cosmonaut dossier"},
        {"num": 2, "label": "Roadmap Publication", "date": timeline.publication_date, "desc": "Published on learning roadmap"},
        {"num": 3, "label": "Learning Phase Commences", "date": timeline.learning_start_date, "desc": "Study materials & theory modules"},
        {"num": 4, "label": "Learning Phase Concludes", "date": timeline.learning_end_date, "desc": "Curriculum completion cutoff"},
        {"num": 5, "label": "Project Implementation Begins", "date": timeline.project_start_date, "desc": "Hands-on build & engineering phase"},
        {"num": 6, "label": "Project Implementation Ends", "date": timeline.project_end_date, "desc": "Final test runs & artifact preparation"},
        {"num": 7, "label": "Official Submission Deadline", "date": timeline.submission_deadline, "desc": "Hard deadline for deliverable intake"},
        {"num": 8, "label": "Guardian Review & Q&A Defense", "date": timeline.review_date, "desc": "Standard 50-mark marksheet evaluation"},
        {"num": 9, "label": "Badge Award Date", "date": timeline.actual_award_date or timeline.expected_award_date, "desc": "Credential credentialing on blockchain/ledger"}
    ]

    items_html = []
    for node in nodes:
        is_past = bool(node["date"] and node["date"] <= "2026-11-07")  # Current system demo date
        node_cls = "completed" if is_past else "active"
        items_html.append(f"""
        <div class="timeline-node {node_cls}">
            <div>
                <div class="timeline-label">{node["num"]}. {escape(node["label"])}</div>
                <div style="font-size:11.5px; color:var(--frost-navy-50);">{escape(node["desc"])}</div>
            </div>
            <div class="timeline-date">{escape(node["date"] or "TBD")}</div>
        </div>
        """)

    return f"""
    <div>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
            <h4 style="font-size:1.1rem; font-weight:700; color:var(--frost-navy); margin:0;">{escape(badge_title)} — Lifecycle Timeline</h4>
            {render_status_pill(timeline.status)}
        </div>
        <div class="timeline-flow">
            {"".join(items_html)}
        </div>
    </div>
    """

def render_topbar(
    current_user: User,
    page_title: str,
    unread_notifs_count: int = 0
) -> str:
    """Renders the consistent top bar with role indicator, notification bell, demo reset, and logout."""
    bell_badge = f'<span class="notif-badge">{unread_notifs_count}</span>' if unread_notifs_count > 0 else ""
    return f"""
    <header class="app-topbar">
        <div class="topbar-left">
            <h1 class="topbar-page-title">{escape(page_title)}</h1>
        </div>
        <div class="topbar-right">
            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('reset_demo_data', '{{}}')" title="Restore initial clean dataset">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px;"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
                Demo Reset
            </button>

            <button type="button" class="notif-btn" onclick="window.StarAppBridge.dispatchAction('toggle_notifications_modal', '{{}}')" title="View Notifications">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                {bell_badge}
            </button>

            <div style="display:flex; align-items:center; gap:10px; padding-left:8px; border-left:1px solid var(--icy-steel-30);">
                <div class="user-avatar" style="width:34px; height:34px; font-size:12px;">{escape(current_user.avatar)}</div>
                <div style="line-height:1.2;">
                    <div style="font-size:13px; font-weight:700; color:var(--frost-navy);">{escape(current_user.name)}</div>
                    <div style="font-size:11px; text-transform:uppercase; color:var(--deep-frozen-midnight); font-weight:600;">{escape(current_user.role)}</div>
                </div>
            </div>

            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('logout', '{{}}')" title="Switch User or Logout">
                Sign Out
            </button>
        </div>
    </header>
    """

