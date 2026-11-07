# -*- coding: utf-8 -*-
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
            active_style = (
                "background:var(--deep-frozen-midnight); color:var(--snow-white); font-weight:700; border:1px solid var(--deep-frozen-midnight);"
                if is_active else
                "background:rgba(234,244,255,0.85); color:var(--frost-navy); border:1px solid var(--icy-steel-50);"
            )
            payload = f'{{"marksheet_id": "{att.id}"}}'
            tab_buttons.append(
                f'<button type="button" class="btn-secondary btn-sm" style="{active_style} padding:6px 14px; border-radius:var(--radius-xs);" '
                f'onclick="window.StarAppBridge.dispatchAction(\'view_marksheet\', \'{escape(payload)}\')">'
                f'Attempt #{att.attempt_number} &bull; {att.total_marks}/50.0 ({att.decision.replace("_", " ").title()})</button>'
            )
        attempts_tabs_html = f'''
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:20px; padding:12px 16px; background:rgba(234,244,255,0.45); border-radius:var(--radius-md); border:1px solid var(--icy-steel-30);">
            <span style="font-size:11.5px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.5px;">Attempt History:</span>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">{"".join(tab_buttons)}</div>
        </div>
        '''

    decision_pill = render_status_pill(marksheet.decision)

    criteria = [
        {
            "num": 1,
            "name": "Business Understanding",
            "scope": "Problem formulation, regulatory compliance boundaries (GDPR, HIPAA), and business value metrics.",
            "score": marksheet.business_understanding,
            "max": 10.0
        },
        {
            "num": 2,
            "name": "Architecture / Report",
            "scope": "Modularity, system design rigor, architectural diagrams, schemas, and written documentation.",
            "score": marksheet.architecture_report,
            "max": 10.0
        },
        {
            "num": 3,
            "name": "Technical Knowledge",
            "scope": "Code robustness, algorithm optimization, edge-case coverage, and execution efficiency.",
            "score": marksheet.technical_knowledge,
            "max": 10.0
        },
        {
            "num": 4,
            "name": "Presentation",
            "scope": "Narrative coherence, clarity of demonstration, structured delivery, and verification packaging.",
            "score": marksheet.presentation,
            "max": 10.0
        },
        {
            "num": 5,
            "name": "Question & Answering",
            "scope": "Defense of engineering trade-offs, conceptual agility, and domain comprehension under review.",
            "score": marksheet.qa,
            "max": 10.0
        }
    ]

    criteria_rows = []
    for c in criteria:
        pct = min(100, max(0, int((c["score"] / c["max"]) * 100)))
        criteria_rows.append(f"""
        <tr style="transition:background 150ms ease;">
            <td style="padding:14px 18px; border-bottom:1px solid var(--frost-mist);">
                <div style="font-weight:700; color:var(--frost-navy); font-size:13.5px; margin-bottom:2px;">
                    {c['num']}. {c['name']}
                </div>
                <div style="font-size:12px; color:var(--frost-navy-50); line-height:1.4;">
                    {c['scope']}
                </div>
            </td>
            <td style="padding:14px 18px; border-bottom:1px solid var(--frost-mist); width:180px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <div style="flex:1; height:7px; border-radius:999px; background:rgba(157,183,213,0.3); overflow:hidden;">
                        <div style="width:{pct}%; height:100%; border-radius:999px; background:linear-gradient(90deg, var(--deep-frozen-midnight) 0%, var(--icy-steel) 100%);"></div>
                    </div>
                    <span style="font-family:var(--font-family-mono); font-size:11px; font-weight:700; color:var(--deep-frozen-midnight);">{pct}%</span>
                </div>
            </td>
            <td style="padding:14px 18px; text-align:center; font-family:var(--font-family-mono); font-size:13px; color:var(--frost-navy-50); border-bottom:1px solid var(--frost-mist);">
                {c['max']:.1f}
            </td>
            <td style="padding:14px 18px; text-align:center; font-family:var(--font-family-mono); font-size:14px; font-weight:800; color:var(--deep-frozen-midnight); border-bottom:1px solid var(--frost-mist);">
                {c['score']:.1f}
            </td>
        </tr>
        """)

    return f"""
    <div class="marksheet-view" style="border:1.5px solid var(--icy-steel); border-radius:var(--radius-lg); overflow:hidden; background:var(--snow-white); box-shadow:0 12px 36px rgba(7, 22, 41, 0.08);">
        <!-- Executive Header -->
        <div class="marksheet-header" style="background:linear-gradient(135deg, #071629 0%, #17345C 100%); color:var(--snow-white); padding:24px 32px; display:flex; align-items:center; justify-content:space-between; border-bottom:2px solid var(--icy-steel-50);">
            <div>
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                    <span style="font-family:var(--font-family-mono); font-size:12px; font-weight:800; color:var(--snow-white); background:rgba(157,183,213,0.22); padding:3px 10px; border-radius:var(--radius-xs); border:1px solid rgba(157,183,213,0.35);">{escape(badge_code)}</span>
                    <span style="font-size:12px; font-weight:700; color:var(--icy-steel); letter-spacing:0.8px; text-transform:uppercase;">Official Evaluation Marksheet &bull; Attempt #{marksheet.attempt_number}</span>
                </div>
                <h2 style="font-size:1.6rem; font-weight:800; margin:0 0 6px 0; color:var(--snow-white); letter-spacing:-0.3px;">{escape(badge_title)}</h2>
                <div style="font-size:12.5px; color:rgba(234,244,255,0.8); display:flex; align-items:center; gap:8px;">
                    <span>Evaluated by: <strong>{escape(marksheet.reviewer_name)}</strong> (Guardian)</span>
                    <span>&bull;</span>
                    <span>Evaluation Date: <strong>{escape(marksheet.reviewed_at[:10])}</strong></span>
                </div>
            </div>
            <div class="marksheet-score-badge" style="text-align:right;">
                <div class="marksheet-score-num" style="font-size:2.2rem; font-weight:800; line-height:1; color:var(--snow-white); font-family:var(--font-family-mono);">
                    {marksheet.total_marks} <span style="font-size:1.1rem; color:var(--icy-steel); font-weight:600;">/ 50.0</span>
                </div>
                <div class="marksheet-percent" style="font-size:12.5px; color:var(--icy-steel); font-weight:700; margin-top:4px;">
                    {marksheet.percentage}% Standard Score
                </div>
                <div style="margin-top:8px;">{decision_pill}</div>
            </div>
        </div>

        <!-- Marksheet Body -->
        <div class="marksheet-body" style="padding:28px 32px;">
            {attempts_tabs_html}

            <!-- 5-Criterion Rubric Table -->
            <table class="marksheet-rubric-table" style="width:100%; border-collapse:collapse; margin-bottom:24px; border:1px solid var(--icy-steel-30); border-radius:var(--radius-md); overflow:hidden;">
                <thead>
                    <tr style="background:var(--frost-mist); text-align:left;">
                        <th style="padding:12px 18px; font-size:12px; font-weight:700; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.5px;">Assessment Criterion & Scope</th>
                        <th style="padding:12px 18px; font-size:12px; font-weight:700; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.5px;">Mastery Index</th>
                        <th style="padding:12px 18px; font-size:12px; font-weight:700; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.5px; text-align:center;">Max</th>
                        <th style="padding:12px 18px; font-size:12px; font-weight:700; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.5px; text-align:center;">Score</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(criteria_rows)}
                    <tr style="background:rgba(234,244,255,0.7); font-weight:800;">
                        <td colspan="2" style="padding:14px 18px; text-align:right; text-transform:uppercase; font-size:12.5px; letter-spacing:0.6px; color:var(--deep-frozen-midnight);">
                            Universal 5-Criterion Evaluation Total:
                        </td>
                        <td style="padding:14px 18px; text-align:center; font-family:var(--font-family-mono); font-size:13px; color:var(--frost-navy);">
                            50.0
                        </td>
                        <td style="padding:14px 18px; text-align:center; font-size:1.2rem; font-family:var(--font-family-mono); color:var(--deep-frozen-midnight); font-weight:900;">
                            {marksheet.total_marks:.1f}
                        </td>
                    </tr>
                </tbody>
            </table>

            <!-- Two-Column Structured Feedback -->
            <div class="marksheet-feedback-section" style="display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:22px;">
                <div class="feedback-card" style="padding:18px 20px; border-radius:var(--radius-md); background:linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(234,244,255,0.65) 100%); border:1px solid var(--icy-steel-50); box-shadow:0 2px 8px rgba(7,22,41,0.03);">
                    <div class="feedback-card-title" style="font-size:11.5px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.6px; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                        <span>&#10003;</span> Identified Strengths & Distinctions
                    </div>
                    <p style="font-size:13.5px; line-height:1.6; color:var(--frost-navy); margin:0;">
                        {escape(marksheet.strength_areas or "No specific strengths highlighted.")}
                    </p>
                </div>
                <div class="feedback-card" style="padding:18px 20px; border-radius:var(--radius-md); background:linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(234,244,255,0.65) 100%); border:1px solid var(--icy-steel-50); box-shadow:0 2px 8px rgba(7,22,41,0.03);">
                    <div class="feedback-card-title" style="font-size:11.5px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.6px; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                        <span>&#9873;</span> Areas for Technical Growth & Optimization
                    </div>
                    <p style="font-size:13.5px; line-height:1.6; color:var(--frost-navy); margin:0;">
                        {escape(marksheet.improvement_areas or "No critical weaknesses noted.")}
                    </p>
                </div>
            </div>

            <!-- Guardian Synthesis & Recommendation -->
            <div style="background:linear-gradient(135deg, rgba(234,244,255,0.7) 0%, rgba(255,255,255,0.95) 100%); border-left:4.5px solid var(--deep-frozen-midnight); padding:18px 22px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); border-left-width:4.5px; box-shadow:0 2px 8px rgba(7,22,41,0.03);">
                <div style="font-size:11.5px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); letter-spacing:0.6px; margin-bottom:6px;">
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
            <h4 style="font-size:1.1rem; font-weight:700; color:var(--frost-navy); margin:0;">{escape(badge_title)} &mdash; Lifecycle Timeline</h4>
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

