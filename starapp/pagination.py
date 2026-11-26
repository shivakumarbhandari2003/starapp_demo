"""
STARAPP LIST PAGINATION
=======================
Server-side pagination for every long list/table in both portals.

Why: pages used to render EVERY row (e.g. one table row per employee). With a few thousand users a
single dashboard produced 10-35 MB of HTML and froze the browser. Lists are now sliced on the server
and a compact pager (First / Prev / Page x of y / Next / Last) is rendered under the table.

Usage inside a view:

    rows, pager_html = page_slice("g_cycles:cycle_1:all", items, per_page=25)
    ... render `rows` ...
    ... append `pager_html` under the table ...

The current page of every list lives in `StarAppController.list_pages` (changed through the
`set_list_page` action) and is bound to the render pass with `bind_page_state`.
"""

import contextvars
import html
from typing import Any, Dict, List, Sequence, Tuple

DEFAULT_PAGE_SIZE = 25

_PAGE_STATE: contextvars.ContextVar = contextvars.ContextVar("starapp_list_pages", default=None)


def bind_page_state(state: Dict[str, int]):
    """Binds the controller's page dictionary for the current render pass. Returns a reset token."""
    return _PAGE_STATE.set(state)


def reset_page_state(token) -> None:
    try:
        _PAGE_STATE.reset(token)
    except Exception:
        pass


def current_page(key: str) -> int:
    state = _PAGE_STATE.get()
    if not state:
        return 1
    try:
        return max(1, int(state.get(key, 1)))
    except (TypeError, ValueError):
        return 1


def paginate(items: Sequence[Any], page: int, per_page: int = DEFAULT_PAGE_SIZE) -> Tuple[List[Any], int, int, int]:
    """Returns (page_items, clamped_page, total_pages, total_items)."""
    total = len(items)
    per_page = max(1, int(per_page))
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(1, int(page)), total_pages)
    start = (page - 1) * per_page
    return list(items[start:start + per_page]), page, total_pages, total


def render_pager(key: str, page: int, total_pages: int, total: int, per_page: int) -> str:
    """Compact pager that reuses the existing `btn-secondary btn-sm` styling. Empty for a single page."""
    if total_pages <= 1:
        return ""
    first = (page - 1) * per_page + 1
    last = min(total, page * per_page)
    safe_key = html.escape(key, quote=True)

    def btn(label: str, target: int, disabled: bool, title: str) -> str:
        if disabled:
            return (f'<button type="button" class="btn-secondary btn-sm list-pager-btn" disabled '
                    f'aria-label="{title}" title="{title}">{label}</button>')
        payload = html.escape('{"key":"%s","page":%d}' % (key.replace('"', ''), target), quote=True)
        return (f'<button type="button" class="btn-secondary btn-sm list-pager-btn" aria-label="{title}" title="{title}" '
                f'onclick="window.StarAppBridge.dispatchAction(\'set_list_page\', \'{payload}\')">{label}</button>')

    return f"""
    <nav class="list-pager" aria-label="Pagination" data-pager-key="{safe_key}">
        <span class="list-pager-summary">Showing <strong>{first:,}&ndash;{last:,}</strong> of <strong>{total:,}</strong></span>
        <span class="list-pager-controls">
            {btn("&laquo;", 1, page <= 1, "First page")}
            {btn("&lsaquo; Prev", page - 1, page <= 1, "Previous page")}
            <span class="list-pager-page">Page {page} of {total_pages}</span>
            {btn("Next &rsaquo;", page + 1, page >= total_pages, "Next page")}
            {btn("&raquo;", total_pages, page >= total_pages, "Last page")}
        </span>
    </nav>
    """


def page_slice(key: str, items: Sequence[Any], per_page: int = DEFAULT_PAGE_SIZE) -> Tuple[List[Any], str]:
    """Convenience: returns (rows_for_current_page, pager_html) for the page stored under `key`."""
    rows, page, total_pages, total = paginate(items, current_page(key), per_page)
    return rows, render_pager(key, page, total_pages, total, per_page)
