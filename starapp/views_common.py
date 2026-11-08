# -*- coding: utf-8 -*-
"""
STARAPP SHARED VIEW COMPONENTS
Reusable UI templates for liquid-glass containers, marksheets, timelines, and navigation.
"""

import html
from typing import List, Dict, Any, Optional
from starapp.models import AssessmentMarksheet, BadgeTimeline, Badge, Notification, User


# ==============================================================================
# PROFESSIONAL VECTOR SVG ICON SYSTEM (Zero external font dependencies)
# ==============================================================================

ICON_SVGS = {
    "calendar": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
    "clock": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>',
    "book": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>',
    "code": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>',
    "terminal": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>',
    "award": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    "scale": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M9 11l3 3L22 4"></path><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>',
    "clipboard": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>',
    "rocket": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"></path><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"></path></svg>',
    "revoke": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>',
    "undo": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="9 14 4 9 9 4"></polyline><path d="M20 20v-7a4 4 0 0 0-4-4H4"></path></svg>',
    "lock": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>',
    "unlock": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>',
    "search": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
    "eye": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>',
    "edit": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>',
    "check": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="20 6 9 17 4 12"></polyline></svg>',
    "check_circle": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
    "plus": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
    "layers": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>',
    "globe": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
    "target": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>',
    "analytics": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
    "map": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon><line x1="8" y1="2" x2="8" y2="18"></line><line x1="16" y1="6" x2="16" y2="22"></line></svg>',
    "user": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
    "users": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
    "file_text": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>',
    "video": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>',
    "shield": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
    "bell": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>',
    "arrow_right": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>',
    "medal_1": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="#D4AF37" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="8" r="6" fill="#FFD700" fill-opacity="0.25"></circle><path d="M12 2l2.5 5 5.5.8-4 3.9.9 5.3-4.9-2.6-4.9 2.6.9-5.3-4-3.9 5.5-.8z" fill="#FFD700"></path><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    "medal_2": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="#8A9BA8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="8" r="6" fill="#C0C0C0" fill-opacity="0.25"></circle><path d="M12 2l2.5 5 5.5.8-4 3.9.9 5.3-4.9-2.6-4.9 2.6.9-5.3-4-3.9 5.5-.8z" fill="#C0C0C0"></path><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    "medal_3": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="#A97142" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="8" r="6" fill="#CD7F32" fill-opacity="0.25"></circle><path d="M12 2l2.5 5 5.5.8-4 3.9.9 5.3-4.9-2.6-4.9 2.6.9-5.3-4-3.9 5.5-.8z" fill="#CD7F32"></path><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    "flash": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>',
    "filter": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>',
    "external_link": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>',
    "alert_triangle": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    "github": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>',
    "download": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>',
    "copy": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'
}

def get_icon(name: str, size: int = 15, style: str = "") -> str:
    """Returns a clean professional vector SVG icon."""
    template = ICON_SVGS.get(name)
    if not template:
        template = ICON_SVGS.get("award")
    return template.format(s=size, st=style)


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

