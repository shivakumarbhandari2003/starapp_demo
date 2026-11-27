# Logics — how the important mechanisms work (and why)

Each entry: **what / how / why / where**. Use it to avoid re-inventing (or accidentally undoing) the optimisations from Stage 1 and 2.
Short "previous → new → reason" history: [WORK_DONE_AND_STATUS.md](WORK_DONE_AND_STATUS.md) (the long Stage 1/2 log was deleted from the working tree; recover it with `git show d7706a9:STARAPP_STAGE1_LOGIC_OPTIMIZATION_LOG.md`).

## A. Data layer & caching

| # | Mechanism | How it works | Why | Where |
|:-:|:---|:---|:---|:---|
| A1 | **DB fingerprint** | `PRAGMA data_version` + `conn.total_changes`. Any commit by any connection changes it. | Cheap, exact "did the DB change?" check, safe even with several processes reading. | `starapp/storage.py` |
| A2 | **Memoisation** | `_memoized(key, builder, extra, scope)`; entries valid while the fingerprint (scope `all`) or learning fingerprint (scope `learning`) is unchanged. `mark_dirty(learning=False)` marks feed-only writes so heavy caches survive notification/activity churn. | Dashboards/leaderboards were recomputed on every click (20–68 s at 3k users). | `storage.py`, used by `cycles.py`, `analytics.py`, `get_all_*` |
| A3 | **Secondary indexes** | `_ensure_ix(name, key_fn)` builds `dict[key] → list`, `_ix_commit` updates incrementally on every `save_*`. | Replaces `for x in all_items: if x.cosmonaut_id == …` (O(N) per call, O(N²) per page). | `storage.py` |
| A4 | **Lazy submission payloads** | `ProjectSubmission` keeps `pdf_payload`/`payload`/`code_payload` unloaded (`payload_is_lazy`) until `_hydrate()`; snapshots use `export_to_dict(include_blobs=False)`. | Base64 PDFs made the cache hundreds of MB. | `models.py`, `database.py` |
| A5 | **Feed rowid watermark** | `_sync_feed_tables` loads only rows with `rowid > last_seen` for `activity_events`/`notifications`. | No full reload for append-only tables. | `storage.py` |
| A6 | **Idempotent load** | `load_from_json` skips when `_loaded_data_version` equals the current version. | Removed the double reload on startup/new session (3.6 s → 1.8 s). | `storage.py` |
| A7 | **UPSERT, not REPLACE** | `INSERT … ON CONFLICT(id) DO UPDATE` in `save_user`, `save_cycle`, etc. | `INSERT OR REPLACE` deletes+reinserts → `ON DELETE CASCADE` wiped enrollments/roles/timelines (reproduced: 76 → 38 enrollments). | `storage.py`, `database.py` |
| A8 | **Safe writes** | `_write_failed` + `StorageWriteError` + `resync_from_database()` | In-memory state must never diverge from disk after a failed write. | `storage.py` |
| A9 | **30 performance indexes** | `PERFORMANCE_INDEXES` + `ensure_performance_indexes` run at start (idempotent) and `PRAGMA optimize`. | Covering the join/filter columns used by the grouped queries. | `database.py` |
| A10 | **Grouped export** | `export_to_dict` loads each child table once and groups in Python (no per-row queries). | Removed N+1 on startup/resync. | `database.py` |

## B. Appraisal & analytics

* **Cycle performance** (`cycles.py`): O(N) — every table is grouped once per cycle (by cadet / reviewer) instead of rescanned per person. Public
  `compute_cycle_candidate_performance` memoises the whole cohort per cycle and serves single-user requests from that cached cohort (`users_override`).
  Rows are returned as **copies** (callers may mutate).
* **Analytics** (`analytics.py`): cohort profiles memoised; dashboards use real data only — hard-coded demo names/dates/counts were removed
  (badge catalogue, trends, popover facts, `last_active`, `upcoming_deadline`, `band`/`track`).
* **Cohort definition** (`storage.get_all_cosmonauts`): users with cosmonaut role; guardians/admins excluded.
* **Leaderboard**: top-10 plus the viewer's own row.

## C. Rendering & UI engine

| Mechanism | Detail |
|:---|:---|
| **Regions** | `render()` produces `{sidebarHtml, topbarHtml, mainHtml, modalHtml…}`; `bridge.js::updateRegions` patches each if changed. Only **one render per action**. |
| **`_sidebarSignature()`** | Signature of the sidebar HTML with `class="nav-link active"` removed. Replace the `<aside>` only when the *structure* changes; otherwise `_updateSidebarInPlace` moves the highlight. (Root cause of the old flicker: active class made the HTML differ on every navigation → full `outerHTML` replacement.) |
| **`iconize_html(html)`** | Replaces emoji / glyphs (✓ ⚠ ★ ⚑ 🏆 📅 …) with inline SVGs from `get_icon`. Operates on **text nodes only**, quote-aware tag matching (so `=>` inside `onclick="…"` is safe), skips `<option> <textarea> <title> <script> <style>`. Applied to main content and modals in `app.py`. |
| **`humanize_internal_ids(text)`** | Replaces `m_b1_1`-style user ids with names and `badge_…` ids with badge codes; unknown ids are left untouched. |
| **Pagination** | `starapp/pagination.py`: `page_slice(items, key)` returns the page; `render_pager` draws it; `bind_page_state` binds page numbers to the request via a contextvar; action `set_list_page`. Used for cycles table, activity feeds (25/50 per page), dashboard roster/leaderboard. Mapping list capped (`MAPPING_LIST_DISPLAY_CAP = 60`). |
| **Bounded widgets** | Selector lists and the velocity chart are capped so page size doesn't grow with the cohort (Guardian dashboard 34 MB → 227 KB at 3k users). |
| **`cosmonaut_terms(html)`** | Final pass on sidebar / main / modal / page title / flash of every non-Guardian view: `cadet(s)` → `cosmonaut(s)` keeping case. Tokenised like `iconize_html` (text nodes + 4 text attributes only; skips `<script>/<style>`), so identifiers such as `rev_proj_cadet_ids` or `uncoupled_cadets` are never touched. Also rewrites stored activity/notification text. |
| **Rail cycle pill** | Short label (`C1`) in the 72 px rail; full code when expanded. |

## D. Server runtime & sessions (`backend/app/main.py`)

* `_run_dispatch` executes in a **threadpool under `_dispatch_lock`**, so the event loop stays free (static files, health, REST) while actions are serialised against the shared store.
* **Session registry**: `OrderedDict` LRU capped at `STARAPP_MAX_SESSIONS`; evicted sessions restore from the browser-held **signed snapshot** (`_sign_session_state`/`_verify_session_state`: HMAC-SHA256 with `SECRET_KEY`, includes expiry).
* GZip for responses ≥ 1 KB; restricted CORS; `HOT_RELOAD` (module reload per request) only in dev; `/js/starapp_bundle.js` only in demo mode.
* Health endpoint counts tables excluding `sqlite_%`.

## E. Workflow-logic details worth remembering

* **Project requests reuse `reviewer_project_prompts`** (no schema change): status `requested` / `fulfilled` rows are hidden from every project list (`get_reviewer_project_prompts(include_requests=False)`, `get_project_prompt_for_cadet`); `get_project_request`, `get_pending_project_requests(reviewer_id)` and `get_mapped_reviewer_id` are the accessors. One shared renderer `render_project_brief(title, content)` shows a project (big bold heading + pre-wrapped content) to both reviewer and cosmonaut; `_project_cta` decides Request Project / Project Requested / Submit Project Deliverables.

* **Allotment uncoupling:** after a pass, `store.uncouple_cadet_badge_mapping(badge, cadet)` removes the cadet from the active band mapping so the schedule shows them under *completed*, not *upcoming*.
* **Reviewer's cadets for a badge** (`_reviewer_cadets_for_badge`): union of timelines (`reviewer_id`), `band_mappings` containing the reviewer, and `badge.assigned_reviewer_id`. With several reviewers on a mapping, cadets are distributed round-robin (`rev_list[idx % len]`).
* **Roadmap state** (`roadmap.compute_milestone_state`): `completed` if approved; `active` if all prerequisites approved (or none); else `locked`. 25-milestone canonical order in `roadmap.CANONICAL_ORDER`.
* **Extensions:** approval rewrites `badge_timelines.submission_deadline` for that cadet+badge; everything is logged to `activity_events` + `notifications`.
* **Activity/notifications:** every workflow step calls `store.add_activity(...)` and `store.add_notification(...)`; feeds are cycle-scoped (`cycle_id`).
* **Closed cycle = read-only:** `handle_event` blocks state-changing actions unless in `_CYCLE_READONLY_SAFE_ACTIONS`.

## F. Measured results (so regressions can be detected)

Synthetic DB with **3,038 users** (scratch tooling, not in repo), real server, Playwright/Chrome:

| Measure | Before | After |
|:---|---:|---:|
| Cold start / memory | 3.6 s / 515 MB | 1.8 s / 94 MB |
| New session | seconds | ~15 ms |
| `g_cycles` | 22 s (6.8 MB) | ~20 ms (65 KB) |
| `g_dashboard` | 19.6 s (34 MB) | ~300 ms (227 KB) |
| `c_dashboard` | 68 s (9.8 MB) | ~200 ms (92 KB) |
| Avg cadet page | 48 ms | 8.7 ms |
| Throughput (60 concurrent users) | 18 req/s | 66–74 req/s, p50 ≈ 0.6 s, 0 errors |
| Test suite | 149 tests ≈ 32 s | 215 tests ≈ 22 s |

Reproduce the idea (scratch scripts were not committed): build a DB by cloning users/enrollments to ~3,000, start `uvicorn` against it via
`DATABASE_URL`/`STARAPP_DB_PATH`, time each view with `StarAppController().handle_event("select_demo_account", uid)` + `ctrl.current_view = …; ctrl.render()`.

## G. Known sharp edges (read before refactoring)

* Controller is large (6,000 lines, one `if/elif` action chain). Prefer adding small helper methods; keep action names stable (JS and tests reference them).
* `starapp/` is imported by the server **and** shipped to the browser (Pyodide). Avoid server-only imports in `starapp/` modules that the bundle needs.
* Tests call `store.reset_to_seed()`; that is why the runner isolates the DB. Don't write tests that assume the real DB's current contents.
* REST service layer ≠ controller rules (smaller duplicate). When a rule changes, change the controller and check the REST service.
