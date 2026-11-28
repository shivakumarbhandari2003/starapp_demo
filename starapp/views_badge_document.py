"""
STARAPP STRUCTURED BADGE DOCUMENT
One renderer for the full structured badge (location breadcrumb, outcomes, earn-the-badge strip, practice project,
learning topics, learning resources, related taxonomy) in its two states - read-only and editable.

Both portals use it, so the badge looks and edits identically everywhere:
  * Guardian  -> Create Badge workspace (the generated / saved badge, edited as an in-memory draft)
  * Reviewer  -> Review Requests -> badge review page (the REAL badge, edited in place)

The edit inputs keep stable ids (`edit-badge-title-input`, `edit-badge-desc-input`, `edit-badge-outcomes-input`,
`edit-topic-title-N`, `edit-topic-desc-N`, `edit-practice-prompt-input`, `edit-resources-prompt-input`) so the same
bridge helpers can collect them. Everything portal-specific (buttons, the status strip, the footer label) is passed in.
"""

from typing import Any, Dict, List, Optional

from starapp.views_common import escape, get_icon

CHEVRON_UP_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" '
    'stroke-linecap="round" stroke-linejoin="round" style="transition:transform 0.2s ease;"><polyline points="18 15 12 9 6 15"/></svg>'
)
CRUMB_SEP_SVG = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--frost-navy)" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><polyline points="9 18 15 12 9 6"/></svg>'
)


def split_badge_document(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalises a structured badge dict (the shape stored in `badges.prompt_json` / the Guardian draft) into the plain
    fields the document renders. Tolerates the older flat keys (`practice_prompt`, `resources_prompt`).
    """
    data = data if isinstance(data, dict) else {}
    pp = data.get("practice_project")
    practice = pp.get("prompt", "") if isinstance(pp, dict) else (str(pp) if pp else "")
    practice = practice or data.get("practice_prompt", "") or ""
    lr = data.get("learning_resources")
    resources = lr.get("prompt", "") if isinstance(lr, dict) else (str(lr) if lr else "")
    resources = resources or data.get("resources_prompt", "") or ""
    outcomes = data.get("outcomes") or data.get("learning_outcomes") or []
    if isinstance(outcomes, str):
        outcomes = [o.strip() for o in outcomes.split("\n") if o.strip()]
    topics = data.get("learning_topics") or []
    return {
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "outcomes": [str(o) for o in outcomes],
        "practice_prompt": practice,
        "resources_prompt": resources,
        "topics": [t for t in topics if isinstance(t, dict)] if isinstance(topics, list) else [],
    }


def format_prompt_readable_html(prompt_text: str, elem_id: str) -> str:
    """Renders a multi-line LLM prompt as clean, high-contrast prose + bullet list."""
    raw = str(prompt_text or "").strip()
    if not raw:
        return f'<div id="{elem_id}" class="cb-prompt-surface"><p class="cb-prompt-lead">No prompt content provided.</p></div>'
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    blocks: List[str] = []
    bullet_items: List[str] = []

    def _bold_prefix(text: str) -> str:
        esc_text = escape(text)
        if ":" in esc_text:
            head, tail = esc_text.split(":", 1)
            if 1 <= len(head) <= 34 and not head.lower().startswith("http") and tail.strip():
                return f'<strong style="font-weight:800; color:var(--frost-navy);">{head}:</strong>{tail}'
        return esc_text

    def _flush_bullets():
        if bullet_items:
            lis = "".join(f"<li>{_bold_prefix(item)}</li>" for item in bullet_items)
            blocks.append(f'<ul class="cb-prompt-bullets">{lis}</ul>')
            bullet_items.clear()

    for line in lines:
        if line.startswith(("- ", "* ", "• ")):
            bullet_items.append(line[2:].strip())
        elif len(line) > 3 and line[0].isdigit() and line[1:3] in (". ", ") "):
            bullet_items.append(line)
        else:
            _flush_bullets()
            has_header = (":" in line and 1 <= len(line.split(":", 1)[0]) <= 34 and not line.lower().startswith("http"))
            fw = "700" if (len(blocks) == 0 or has_header) else "500"
            blocks.append(f'<p class="cb-prompt-lead" style="font-weight:{fw};">{_bold_prefix(line)}</p>')
    _flush_bullets()
    return f'<div id="{elem_id}" class="cb-prompt-surface">{"".join(blocks)}</div>'


def render_badge_edit_controls(is_editing: bool, edit_onclick: str, apply_onclick: str, cancel_onclick: str) -> str:
    """The Edit button (read-only) or the Apply Changes + Cancel pair (editing). The handlers are JS expressions."""
    if is_editing:
        return (
            f'<button type="button" class="btn-metal btn-sm" onclick="{apply_onclick}" '
            'style="font-size:0.8125rem; font-weight:800; padding:8px 16px; display:inline-flex; align-items:center; gap:6px;">'
            f'{get_icon("check", size=14)} Apply Changes</button>'
            f'<button type="button" class="btn-secondary btn-sm" onclick="{cancel_onclick}" '
            'style="font-size:0.8125rem; font-weight:700; padding:8px 14px;">Cancel</button>'
        )
    return (
        f'<button type="button" class="btn-secondary btn-sm" onclick="{edit_onclick}" '
        'style="font-size:0.8125rem; font-weight:700; padding:8px 14px; display:inline-flex; align-items:center; gap:6px;">'
        f'{get_icon("edit", size=14)} Edit</button>'
    )


def _outcomes_block(outcomes: List[str], is_editing: bool) -> str:
    if is_editing:
        return f"""
        <div class="cb-edit-card">
            <label for="edit-badge-outcomes-input" class="cb-edit-label">
                Learning Outcomes (one per line, starting with "Can...")
            </label>
            <textarea id="edit-badge-outcomes-input" class="form-input auto-grow-textarea" rows="4"
                style="font-size:0.90625rem; line-height:1.65; font-weight:500; color:var(--frost-navy); font-family:var(--font-family-base); width:100%; box-sizing:border-box; padding:12px 14px; border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel); background:var(--snow-white); resize:none; overflow:hidden;"
                placeholder="Can identify...&#10;Can analyze...&#10;Can design...&#10;Can implement...">{escape(chr(10).join(outcomes))}</textarea>
        </div>
        """
    check_svg = get_icon("check", size=14)
    items = "".join(
        f'''<div style="display:flex; align-items:flex-start; gap:12px; font-size:0.90625rem; color:var(--frost-navy); line-height:1.6; padding:12px 16px; background:rgba(255,255,255,0.88); border:1.5px solid rgba(5,150,105,0.28); border-radius:var(--radius-sm); margin-bottom:9px;">
            <span style="width:24px; height:24px; border-radius:50%; background:rgba(5,150,105,0.14); color:#047857; display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-top:1px;">{check_svg}</span>
            <span style="font-weight:600; flex:1; color:var(--frost-navy);">{escape(o)}</span>
        </div>'''
        for o in outcomes
    )
    return f'<div style="display:flex; flex-direction:column; gap:2px;">{items}</div>'


def _topics_block(topics: List[Dict[str, Any]], is_editing: bool, show_progress: bool) -> str:
    if is_editing:
        rows = []
        for idx, t in enumerate(topics):
            t_title = t.get("title", "")
            t_desc = t.get("description", "")
            t_comp = t.get("completed", False) or str(t.get("status", "")).lower() == "completed"
            t_status = t.get("status") or ("Completed" if t_comp else "In Progress")
            rows.append(f"""
            <div class="cb-edit-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; gap:8px;">
                    <span style="font-size:0.75rem; font-weight:800; background:rgba(6,182,212,0.14); color:#0E7490; padding:4px 12px; border-radius:12px; border:1px solid rgba(6,182,212,0.3);">Topic {idx+1}</span>
                    <span style="font-size:0.78125rem; font-weight:700; color:var(--frost-navy);">Curriculum Module</span>
                </div>
                <div style="margin-bottom:10px;">
                    <label for="edit-topic-title-{idx}" class="cb-edit-label">Topic Title</label>
                    <input type="text" id="edit-topic-title-{idx}" class="form-input"
                        data-completed="{'1' if t_comp else '0'}" data-status="{escape(t_status)}"
                        style="font-size:0.9375rem; font-weight:800; color:var(--frost-navy); width:100%; box-sizing:border-box; padding:10px 14px; border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel); background:var(--snow-white);"
                        placeholder="Topic Title" value="{escape(t_title)}">
                </div>
                <div>
                    <label for="edit-topic-desc-{idx}" class="cb-edit-label">Description &amp; Scope</label>
                    <textarea id="edit-topic-desc-{idx}" class="form-input auto-grow-textarea" rows="2"
                        style="font-size:0.875rem; line-height:1.6; font-weight:500; color:var(--frost-navy); width:100%; box-sizing:border-box; padding:10px 14px; border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel); background:var(--snow-white); resize:none; overflow:hidden;"
                        placeholder="Topic Description / Scope">{escape(t_desc)}</textarea>
                </div>
            </div>
            """)
        return f'<div id="topics-list-container" class="cb-edit-grid" style="width:100%; box-sizing:border-box;">{"".join(rows)}</div>'

    cards = []
    for idx, t in enumerate(topics):
        t_title = t.get("title", "")
        t_desc = t.get("description", "")
        is_comp = show_progress and (t.get("completed", False) or str(t.get("status", "")).lower() == "completed")
        border_color = "#059669" if is_comp else "rgba(8,145,178,0.34)"
        bg_style = ("background:linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(236,253,245,0.75) 100%);" if is_comp
                    else "background:rgba(244, 250, 255, 0.88);")
        progress_html = ""
        if show_progress:
            status_text = "Completed" if is_comp else "In Progress"
            status_bg = "rgba(16,185,129,0.16)" if is_comp else "rgba(157,183,213,0.25)"
            status_color = "#047857" if is_comp else "var(--frost-navy)"
            status_border = "rgba(16,185,129,0.36)" if is_comp else "var(--icy-steel)"
            btn_class = "is-completed" if is_comp else ""
            btn_bg = "#059669" if is_comp else "var(--snow-white)"
            btn_color = "white" if is_comp else "var(--frost-navy)"
            btn_border = "#047857" if is_comp else "var(--icy-steel)"
            btn_shadow = "0 2px 8px rgba(5,150,105,0.28)" if is_comp else "none"
            btn_content = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Completed'
                           if is_comp else "Mark Complete")
            status_tag = (
                f'<span id="topic-status-tag-{idx}" style="background:{status_bg}; color:{status_color}; padding:3px 11px; border-radius:12px; '
                f'font-size:0.75rem; font-weight:700; border:1px solid {status_border}; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease;">{status_text}</span>'
            )
            toggle_btn = f"""
                <div style="flex-shrink:0;">
                    <button type="button" id="topic-toggle-btn-{idx}" class="{btn_class}"
                        onclick="window.StarAppBridge.toggleTopicCompletion({idx})"
                        style="background:{btn_bg}; color:{btn_color}; border:1.5px solid {btn_border}; box-shadow:{btn_shadow}; font-size:0.8125rem; font-weight:800; padding:9px 18px; border-radius:20px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; transition:border-color 0.25s ease, background 0.25s ease, color 0.25s ease, box-shadow 0.25s ease;">
                        {btn_content}
                    </button>
                </div>"""
        else:
            status_tag = ""
            toggle_btn = ""
        cards.append(f"""
            <div id="topic-card-{idx}" class="topic-row-card" style="padding:18px 22px; border-radius:var(--radius-md); border:1.5px solid {border_color}; {bg_style} display:flex; justify-content:space-between; align-items:center; gap:20px; width:100%; box-sizing:border-box; transition:border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;">
                <div style="flex:1;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:7px; flex-wrap:wrap;">
                        <span style="font-size:0.75rem; font-weight:800; background:rgba(8,145,178,0.13); color:#0E7490; padding:3px 11px; border-radius:12px; border:1px solid rgba(8,145,178,0.28);">Topic {idx+1}</span>
                        {status_tag}
                        <span style="font-size:0.75rem; color:var(--frost-navy); font-weight:700;">Curriculum Module</span>
                    </div>
                    <div style="font-size:0.96875rem; font-weight:800; color:var(--frost-navy); margin-bottom:5px;">{escape(t_title)}</div>
                    <div style="font-size:0.875rem; font-weight:500; color:var(--frost-navy); line-height:1.55;">{escape(t_desc)}</div>
                </div>
                {toggle_btn}
            </div>
            """)
    return f'<div id="topics-list-container" style="display:flex; flex-direction:column; gap:12px; width:100%; box-sizing:border-box;">{"".join(cards)}</div>'


def _prompt_textarea(elem_id: str, label: str, value: str) -> str:
    return f'''
            <div class="cb-edit-card">
                <label for="{elem_id}" class="cb-edit-label">{label}</label>
                <textarea id="{elem_id}" class="form-input auto-grow-textarea" rows="6"
                    style="width:100%; box-sizing:border-box; min-height:140px; font-size:0.90625rem; font-weight:500; line-height:1.65; color:var(--frost-navy); font-family:var(--font-family-base); padding:12px 14px; border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel); background:var(--snow-white); resize:none; overflow:hidden;">{escape(value)}</textarea>
            </div>
            '''


def render_badge_document(
    *,
    title: str,
    description: str,
    outcomes: List[str],
    practice_prompt: str,
    resources_prompt: str,
    topics: List[Dict[str, Any]],
    skill: str,
    capability: str,
    power: str,
    band: str,
    is_editing: bool,
    header_actions_html: str,
    footer_bar_html: str = "",
    earn_strip_html: Optional[str] = None,
    show_topic_progress: bool = True,
    location_label: str = "Created Badge Location",
    show_description: bool = True,
    title_actions_html: str = "",
    is_gold: bool = False,
) -> str:
    """
    Renders the structured badge. `header_actions_html` holds the buttons on the hero card (Toggle All / Edit / Save ...),
    `footer_bar_html` the bar shown under the sections while editing, `earn_strip_html` the "Earn the Badge" strip
    (None = the standard "Pending Review" strip). `show_topic_progress` adds the Completed pill, progress bar and
    Mark Complete buttons (a Guardian drafting a badge); the reviewer reads the topics as pure curriculum.
    """
    total_topics = len(topics)
    done = sum(1 for t in topics if t.get("completed", False) or str(t.get("status", "")).lower() == "completed")
    progress_pct = int(round((done / total_topics) * 100)) if total_topics > 0 else 0

    if is_editing:
        header_body = f'''
            <div class="cb-edit-grid" style="margin-top:4px;">
                <div class="cb-edit-card">
                    <label for="edit-badge-title-input" class="cb-edit-label">Badge Title</label>
                    <input type="text" id="edit-badge-title-input" class="form-input"
                        style="font-size:1.35rem; font-weight:800; color:var(--frost-navy); width:100%; box-sizing:border-box; padding:10px 14px; border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel); background:var(--snow-white);"
                        value="{escape(title)}">
                </div>
                <div class="cb-edit-card">
                    <label for="edit-badge-desc-input" class="cb-edit-label">Scope &amp; Summary Description</label>
                    <textarea id="edit-badge-desc-input" class="form-input auto-grow-textarea" rows="3"
                        style="font-size:0.90625rem; line-height:1.6; font-weight:500; color:var(--frost-navy); width:100%; box-sizing:border-box; padding:10px 14px; border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel); background:var(--snow-white); resize:none; overflow:hidden;">{escape(description)}</textarea>
                </div>
            </div>
            '''
        practice_inner = _prompt_textarea("edit-practice-prompt-input", "Practice Project Prompt", practice_prompt)
        resources_inner = _prompt_textarea("edit-resources-prompt-input", "Learning Resources Prompt", resources_prompt)
    else:
        header_body = f'''
            <h2 style="font-size:1.55rem; font-weight:800; color:var(--frost-navy); margin:0 0 8px 0; line-height:1.25;">{escape(title)}</h2>
            {f'<p style="font-size:0.9375rem; font-weight:500; color:var(--frost-navy); line-height:1.6; margin:0;">{escape(description)}</p>' if show_description else ''}
            '''
        practice_inner = format_prompt_readable_html(practice_prompt, "practice-prompt-text")
        resources_inner = format_prompt_readable_html(resources_prompt, "resources-prompt-text")

    if earn_strip_html is None:
        earn_strip_html = """
            <div style="display:flex; align-items:flex-start; gap:12px;">
                <span class="cb-section-icon" style="background:rgba(37,99,235,0.12); color:#1D4ED8;">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
                </span>
                <div>
                    <div class="cb-section-title">Earn the Badge</div>
                    <div style="font-size:0.90625rem; font-weight:600; color:var(--frost-navy); margin-top:3px;">Great job submitting your project &mdash; your guardian is reviewing it now.</div>
                </div>
            </div>
            <div>
                <span style="background:rgba(245,158,11,0.16); color:#B45309; padding:5px 14px; border-radius:20px; font-size:0.78125rem; font-weight:800; border:1px solid rgba(217,119,6,0.34);">
                    Pending Review
                </span>
            </div>
            """

    if show_topic_progress:
        pill_on = progress_pct > 0
        progress_html = f"""
                        <span id="topics-summary-pill" style="background:{'rgba(16,185,129,0.16)' if pill_on else 'rgba(157,183,213,0.24)'}; color:{'#047857' if pill_on else 'var(--frost-navy)'}; padding:3px 12px; border-radius:12px; font-size:0.75rem; font-weight:700; border:1px solid {'rgba(16,185,129,0.34)' if pill_on else 'var(--icy-steel)'};">
                            {done}/{total_topics} Completed
                        </span>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <div style="width:130px; height:8px; border-radius:4px; background:rgba(157,183,213,0.35); overflow:hidden;">
                                <div id="topics-progress-bar" style="width:{progress_pct}%; height:100%; background:linear-gradient(90deg, #0891B2, #059669); border-radius:4px; transition:width 0.4s ease;"></div>
                            </div>
                            <span id="topics-progress-text" style="font-size:0.8125rem; font-weight:800; color:var(--frost-navy); min-width:38px;">{progress_pct}%</span>
                        </div>"""
    else:
        progress_html = f"""
                        <span style="background:rgba(157,183,213,0.24); color:var(--frost-navy); padding:3px 12px; border-radius:12px; font-size:0.75rem; font-weight:700; border:1px solid var(--icy-steel);">
                            {total_topics} Module{'' if total_topics == 1 else 's'}
                        </span>"""

    outcomes_html = _outcomes_block(outcomes, is_editing)
    topics_html = _topics_block(topics, is_editing, show_topic_progress)
    chev = CHEVRON_UP_SVG
    sep = CRUMB_SEP_SVG

    return f"""
        <div id="created-badge-display-area" style="margin-bottom:32px;">

            <!-- LOCATION & ACTION HERO CARD -->
            <div class="cb-result-hero">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:14px; padding-bottom:16px; margin-bottom:16px; border-bottom:1px solid var(--icy-steel-40);">
                    <div style="flex:1; min-width:260px;">
                        <div style="font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--frost-navy); margin-bottom:6px;">
                            {escape(location_label)}
                        </div>
                        <div style="display:flex; align-items:center; flex-wrap:wrap; gap:8px;">
                            <span style="color:var(--frost-navy); font-size:0.96875rem; font-weight:800;">{escape(title)}</span>
                            {sep}
                            <span style="background:rgba(8,145,178,0.12); color:#0E7490; padding:4px 12px; border-radius:14px; font-size:0.8125rem; font-weight:700; border:1px solid rgba(8,145,178,0.28);">{escape(skill)}</span>
                            {sep}
                            <span style="background:rgba(37,99,235,0.12); color:#1D4ED8; padding:4px 12px; border-radius:14px; font-size:0.8125rem; font-weight:700; border:1px solid rgba(37,99,235,0.28);">{escape(capability)}</span>
                            {sep}
                            <span style="background:rgba(124,58,237,0.12); color:#6D28D9; padding:4px 12px; border-radius:14px; font-size:0.8125rem; font-weight:700; border:1px solid rgba(124,58,237,0.28);">{escape(power)}</span>
                            {sep}
                            <span style="background:var(--deep-frozen-midnight); color:var(--snow-white); padding:4px 12px; border-radius:14px; font-size:0.8125rem; font-weight:800;">Band {escape(band)}</span>
                        </div>
                    </div>
                    <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap; flex-shrink:0;">
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.toggleAllBadgeSections()" style="font-size:0.8125rem; font-weight:700; padding:8px 14px;">
                            Toggle All
                        </button>
                        {header_actions_html}
                    </div>
                </div>

                <!-- BADGE TITLE & SCOPE -->
                <div style="display:flex; align-items:flex-start; gap:16px;">
                    <div class="{'gold-medal is-lg' if is_gold else ''}" title="{'Badge earned' if is_gold else ''}" style="{'' if is_gold else 'width:50px; height:50px; border-radius:14px; background:linear-gradient(135deg, var(--snow-white) 0%, var(--frost-mist) 100%); border:1.5px solid var(--icy-steel); color:var(--deep-frozen-midnight);'} display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>
                    </div>
                    <div style="flex:1; min-width:0;">
                        {header_body}
                    </div>
                    {f'<div class="cb-title-actions">{title_actions_html}</div>' if title_actions_html else ''}
                </div>
            </div>

            <!-- SECTION 1: OUTCOMES -->
            <div id="badge-section-outcomes" class="cb-section-card accent-emerald">
                <div class="cb-section-head" onclick="window.StarAppBridge.toggleBadgeSection('outcomes')">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span class="cb-section-icon" style="background:rgba(5,150,105,0.12); color:#047857;">
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
                        </span>
                        <span class="cb-section-title">Outcomes ({len(outcomes)})</span>
                    </div>
                    <span id="chevron-outcomes" style="color:var(--frost-navy); display:inline-flex; align-items:center;">{chev}</span>
                </div>
                <div id="content-outcomes" style="padding:0 22px 20px 22px; display:block;">
                    {outcomes_html}
                </div>
            </div>

            <!-- SECTION 2: EARN THE BADGE -->
            <div id="badge-section-earn" class="cb-section-card" style="border-left-color:#2563EB; padding:18px 22px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
                {earn_strip_html}
            </div>

            <!-- SECTION 3: PRACTICE PROJECT -->
            <div id="badge-section-practice" class="cb-section-card accent-amber">
                <div class="cb-section-head" onclick="window.StarAppBridge.toggleBadgeSection('practice')">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span class="cb-section-icon" style="background:rgba(217,119,6,0.12); color:#B45309;">
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m14 2-4 0"/><path d="M10 2v7.5L5 19a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3L14 9.5V2"/></svg>
                        </span>
                        <span class="cb-section-title">Practice Project</span>
                    </div>
                    <span id="chevron-practice" style="color:var(--frost-navy); display:inline-flex; align-items:center;">{chev}</span>
                </div>
                <div id="content-practice" style="padding:0 22px 22px 22px; display:block;">
                    <p style="font-size:0.875rem; font-weight:600; color:var(--frost-navy); margin:0 0 12px 0;">Want some hands-on practice? Use this structured prompt to generate a practice project.</p>
                    {practice_inner}
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; flex-wrap:wrap; gap:10px;">
                        <span style="font-size:0.8125rem; font-weight:600; color:var(--frost-navy);">This is a prompt which should be provided to an LLM (Gemini, Claude, ChatGPT) to generate a practice project for this badge.</span>
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('practice-prompt-text', this)" style="font-size:0.78125rem; font-weight:700; display:inline-flex; align-items:center; gap:6px; padding:7px 14px;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                            Copy Prompt
                        </button>
                    </div>
                </div>
            </div>

            <!-- SECTION 4: LEARNING TOPICS -->
            <div id="badge-section-topics" class="cb-section-card accent-cyan">
                <div class="cb-section-head" onclick="window.StarAppBridge.toggleBadgeSection('topics')">
                    <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                        <span class="cb-section-icon" style="background:rgba(8,145,178,0.12); color:#0E7490;">
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>
                        </span>
                        <span class="cb-section-title">Learning Topics</span>{progress_html}
                    </div>
                    <span id="chevron-topics" style="color:var(--frost-navy); display:inline-flex; align-items:center;">{chev}</span>
                </div>
                <div id="content-topics" style="padding:0 22px 22px 22px; display:block;">
                    {topics_html}
                </div>
            </div>

            <!-- SECTION 5: LEARNING RESOURCES -->
            <div id="badge-section-resources" class="cb-section-card" style="border-left-color:#2563EB;">
                <div class="cb-section-head" onclick="window.StarAppBridge.toggleBadgeSection('resources')">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span class="cb-section-icon" style="background:rgba(37,99,235,0.12); color:#1D4ED8;">
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                        </span>
                        <span class="cb-section-title">Learning Resources</span>
                    </div>
                    <span id="chevron-resources" style="color:var(--frost-navy); display:inline-flex; align-items:center;">{chev}</span>
                </div>
                <div id="content-resources" style="padding:0 22px 22px 22px; display:block;">
                    <p style="font-size:0.875rem; font-weight:600; color:var(--frost-navy); margin:0 0 12px 0;">Not sure where to start learning? Use this structured prompt to find curated resources tailored to this badge.</p>
                    {resources_inner}
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; flex-wrap:wrap; gap:10px;">
                        <span style="font-size:0.8125rem; font-weight:600; color:var(--frost-navy);">This is a prompt which should be provided to an LLM (Gemini, Claude, ChatGPT) to get relevant learning resources.</span>
                        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.copyTextFromElement('resources-prompt-text', this)" style="font-size:0.78125rem; font-weight:700; display:inline-flex; align-items:center; gap:6px; padding:7px 14px;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                            Copy Prompt
                        </button>
                    </div>
                </div>
            </div>

            <!-- SECTION 6: RELATED SKILLS, CAPABILITIES & POWERS -->
            <div id="badge-section-related" class="cb-section-card" style="border-left-color:#7C3AED; margin-bottom:24px;">
                <div class="cb-section-head" onclick="window.StarAppBridge.toggleBadgeSection('related')">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span class="cb-section-icon" style="background:rgba(124,58,237,0.12); color:#6D28D9;">
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
                        </span>
                        <span class="cb-section-title">Related Skills, Capabilities &amp; Powers</span>
                    </div>
                    <span id="chevron-related" style="color:var(--frost-navy); display:inline-flex; align-items:center;">{chev}</span>
                </div>
                <div id="content-related" style="padding:0 22px 22px 22px; display:block;">
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:20px;">
                        <div>
                            <div style="font-size:0.75rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.5px; margin-bottom:7px;">Skills</div>
                            <span style="background:rgba(8,145,178,0.12); color:#0E7490; padding:6px 15px; border-radius:20px; font-size:0.84375rem; font-weight:700; display:inline-block; border:1px solid rgba(8,145,178,0.28);">{escape(skill)}</span>
                        </div>
                        <div>
                            <div style="font-size:0.75rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.5px; margin-bottom:7px;">Capabilities</div>
                            <span style="background:rgba(37,99,235,0.12); color:#1D4ED8; padding:6px 15px; border-radius:20px; font-size:0.84375rem; font-weight:700; display:inline-block; border:1px solid rgba(37,99,235,0.28);">{escape(capability)}</span>
                        </div>
                        <div>
                            <div style="font-size:0.75rem; font-weight:800; text-transform:uppercase; color:var(--frost-navy); letter-spacing:0.5px; margin-bottom:7px;">Powers</div>
                            <span style="background:rgba(124,58,237,0.12); color:#6D28D9; padding:6px 15px; border-radius:20px; font-size:0.84375rem; font-weight:700; display:inline-block; border:1px solid rgba(124,58,237,0.28);">{escape(power)}</span>
                        </div>
                    </div>
                </div>
            </div>

            {footer_bar_html}
        </div>
        """


def render_badge_edit_footer_bar(label: str, apply_onclick: str, cancel_onclick: str) -> str:
    """The bar under the sections while editing: a label on the left, Cancel + Apply Changes on the right."""
    return f'''
            <div class="cb-selection-bar" style="margin-top:8px; margin-bottom:24px; justify-content:flex-end;">
                <span style="font-size:0.84375rem; font-weight:700; color:var(--frost-navy); margin-right:auto;">{escape(label)}</span>
                <button type="button" class="btn-secondary btn-sm" onclick="{cancel_onclick}" style="font-size:0.8125rem; font-weight:700; padding:8px 16px;">Cancel</button>
                <button type="button" class="btn-metal btn-sm" onclick="{apply_onclick}" style="font-size:0.8125rem; font-weight:800; padding:8px 18px; display:inline-flex; align-items:center; gap:6px;">{get_icon("check", size=14)} Apply Changes</button>
            </div>
            '''
