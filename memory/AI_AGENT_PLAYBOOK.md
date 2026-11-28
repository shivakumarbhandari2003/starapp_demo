# AI Agent Playbook — how to get things done in this repo

> You are an AI coding assistant on a fresh machine with no chat history. This file replaces that history. Read it fully, then
> read the file(s) it points to for your task. Prefer acting over asking: the defaults below are the owner's established preferences.

## 0. Owner preferences (standing instructions — keep following them)

1. **Implement everything requested, leave nothing out**; efficient, optimised, fully functional.
2. **Keep the UI identical** unless a UI task is requested; when polishing UI, match the **Guardian portal** standard: clean, professional, readable, SVG icons, minimal text.
3. **Log every meaningful change**: stage/area · previous logic · new logic · reason → append to `memory/WORK_DONE_AND_STATUS.md §6`.
4. The platform must work for **thousands of users** — no unbounded lists, no per-request cohort recomputation, no N+1 queries.
5. Surface *causes*, not symptoms; report test failures honestly (with output); never claim "done" without running the suite.
6. Don't commit/push unless asked. Don't touch `data/starapp.db` unless the task is about the DB.
7. **Owner working style — UI-only passes stay small.** For a purely visual request: make the change, bump `?v=` (+ SW cache + the two test asserts) if `css/` or `js/` changed, verify it visually once (headless Chrome screenshot or the running app), and stop. Run the full suite (and the e2e scripts) only when business logic, server rules or data are touched, or when a test asserts the text/markup you changed. Do not do docs/bundle/E2E cycles for a colour or spacing tweak unless asked. Timestamps shown to users are always IST.

## 1. Orientation in 5 minutes

1. `memory/README.md` (map + gotchas) → `PROJECT_CONTEXT.md` → the file matching your task (see README table).
2. `grep` for the action name (`grep -n 'action == "xyz"' starapp/app.py`) — nearly every behaviour is a controller action.
3. Find the renderer in `starapp/views_guardian.py` / `views_cosmonaut.py` (`def render_…`) and the model/store method in `storage.py`.

## 2. Hard rules (never violate)

* Tests only through `python tests/run_tests.py` (isolated DB). Never run unittest/pytest directly on the real DB.
* No `INSERT OR REPLACE` on cascade parents; use `ON CONFLICT DO UPDATE`.
* Server enforces every rule; a hidden button is not security. New org-wide action ⇒ `_GUARDIAN_ONLY_ACTIONS`.
* Reviewer_Band > Badge_Band; 50-mark rubric; pass = badge `passing_percentage` (default 70); attempts append, never overwrite; finalised attempts are immutable.
* Never leak or commit secrets (`.env`, API keys). `GEMINI_API_KEY` stays server-side.
* Don't hand-edit `js/starapp_bundle.js`; rebuild via `scripts/pack_py.py`.
* **Asset cache-bust:** any change under `css/` or `js/` ⇒ bump `?v=N` in `index.html` + `sw.js` (plus the SW cache name and the asserts in `tests/test_backend_fullstack.py` + `tests/test_ui_remediation.py`; now `v=121` / `starapp-runtime-cache-v78`). The server caches versioned assets for 24 h.
* **Type scale:** font sizes are rem tokens (`--type-page-title 2` (was 1.75 until 2026-11-28), `--type-section-title 1.25`, `--type-subtitle 1`, `--type-body .875`, `--type-small .8125`, `--type-caption .75`); no `px` font sizes; `h1–h4` inside `.app-main` are pinned to the scale with `!important` (for a custom size use `<div role="heading" aria-level="N">`, not a real `h*`).
* **IST everywhere users look:** all user-visible times are IST (UTC+5:30), storage stays UTC. Use `views_common.format_ist` / `ist_plain` / `to_ist` / `format_utc_stamp`; never print UTC or the word "UTC".
* **Reviewer recommends, Guardian decides:** reviewer marksheet decision is `recommend_approve | recommend_resubmit | recommend_reject` (legacy `reviewer_assessed`), never `approve`; reviewer marks lock after one submission per attempt; the Guardian's decision is locked until the Guardian revokes it (`revoke_guardian_decision`, Guardian-only). Earned = decision `approve`/`approved` — a Resubmit/Reject sheet never means earned.
* **One marksheet:** the cosmonaut marksheet shows ONE sheet (latest evaluation) with marks only — no tabs, no outcome pill, no summary; status lives elsewhere (gold badge, Guardian pills).
* **Smooth UI:** no `linear-gradient` on big glass surfaces (use a flat tint such as `rgba(245,250,255,0.86)`), `backdrop-filter` only on chrome (sidebar, top bar, modal veil, popovers), bounded animations, passive listeners, no `scroll` listeners; countdowns must be excluded from HTML comparison (`stable_html_signature`).
* **Edit Badge** may change only the assigned cosmonauts (+ which reviewer each belongs to) and the timeline; the Timeline & Mapping modal is read-only; never rebuild a whole `Badge` from a form payload (that reset band/taxonomy/state and force-published it).
* Positioning inside a `<button>` is browser-dependent: attach decorative pseudo-elements/connectors to a `<div>` wrapper, not to the button.
* Don't reintroduce emoji icons, raw ids in UI, fake/hard-coded analytics, unbounded tables, or sidebar rebuilds.
* The Bash tool on Windows collapses backslash escapes in heredocs and chokes on long quoted text: write helper scripts/text with the **Write** tool, then run them. Set `PYTHONUTF8=1` for Python on Windows consoles.

## 3. Recipes

### Add a new controller action
1. Implement in `StarAppController.handle_event` (`elif action == "name":`) or an `execute_*` helper. Validate the actor and the rules → `raise ActionDenied("…")` or `self.set_flash(msg, "error")`.
2. If org-wide/privileged → add to `_GUARDIAN_ONLY_ACTIONS`. If it only changes UI state and must work in a closed cycle → `_CYCLE_READONLY_SAFE_ACTIONS`.
3. Persist through `store.save_*`; log with `store.add_activity(...)` and `store.add_notification(...)`.
4. Wire the button: `onclick="StarAppBridge.dispatchAction('name', payload)"` (or in `bridge.js` for form payloads).
5. Add a test (`tests/test_scale_and_security_regressions.py` or a feature test); run the suite; rebuild the bundle; log it.

### Add a page/view
1. Add the id to `_GUARDIAN_VIEWS` or `_COSMONAUT_VIEWS`; add nav entry and the render branch in `render()`.
2. Renderer in the matching `views_*.py`; reuse components in `views_common.py` (cards, pills, `get_icon`, pager).
3. Paginate any list; show names/codes; use shared button classes; verify at 1440/1024/420 px.
4. Extend `test_no_emoji_or_internal_ids_on_any_rendered_page` coverage if needed.

### Add a table/column
DDL + migration in `starapp/database.py` / `backend/app/database/migrations.py`; model in `models.py`; `export_to_dict` + load in `storage.py`;
UPSERT writer; index in `PERFORMANCE_INDEXES` if filtered on; seed data; `memory/DATABASE.md`; tests; bundle.

### Change a business rule (e.g. pass %, hike slabs, rubric)
Edit the single enforcement point listed in `RULES_AND_CRITERIA.md`, update the rule table there, adjust tests, add a change-log entry.

### After a workflow change (assessment / mapping / earning / revoke)
1. `python tests/run_tests.py` (432 OK).
2. `python scripts/e2e_full_lifecycle.py` → 57 checks, 0 failed (drives cycle → badge → map → project → marks → Guardian decisions incl. a re-attempt loop and a revoke → both earn → mapping `completed`; also checks persistence, integrity, timing).
3. `python scripts/e2e_guardian_logic.py` (113) and, for UI, `python scripts/e2e_guardian_browser.py` (114, needs Chrome).
4. `git checkout data/starapp.db`, then `python scripts/pack_py.py` if `starapp/` changed, then `git status data/` is empty.
5. Log the change in `WORK_DONE_AND_STATUS.md §6` and update the affected memory file(s).

### Performance work
Measure first (3k-user synthetic DB, time `ctrl.render()` per view), then prefer: grouped lookups → secondary index → memoise → paginate. Re-run the suite; record before/after numbers.

### UI polish
Match Guardian styling; check contrast (≥ 4.5:1), min font 10 px, no overflow at 420 px, no layout shift on navigation, DOM churn low. Keep `_sidebarSignature`.
Use the type tokens, container queries (`container-type: inline-size`) for components that live in resizable panels/modals, and whole-pixel geometry for connectors/lines (fractional heights blur and misalign).
Verify visually: render the controller on a temp DB, build static HTML with the css files, screenshot with headless Chrome (device scale 1 **and** 2); for pixel questions scan the PNG.
Then run `python scripts/e2e_guardian_logic.py` and `python scripts/e2e_guardian_browser.py` (skip for a tiny UI-only tweak, see §0.7).

## 4. Pre-commit checklist

- [ ] `python tests/run_tests.py` → OK (note the count; 432 on 2026-11-28)
- [ ] `git checkout data/starapp.db` (running the app / e2e scripts dirties the tracked binary), **then** `python scripts/pack_py.py` if `starapp/` changed (the bundle embeds the DB, so build it from the clean one)
- [ ] `?v=` bumped in `index.html` + `sw.js` (+ SW cache name, + asserts in `tests/test_backend_fullstack.py` and `tests/test_ui_remediation.py`) if `css/` or `js/` changed — now `v=121` / `starapp-runtime-cache-v78`
- [ ] `python scripts/e2e_full_lifecycle.py`, `python scripts/e2e_guardian_logic.py` and `python scripts/e2e_guardian_browser.py` → 0 failed (after workflow/UI changes)
- [ ] `git status data/` empty (unless intentional)
- [ ] `memory/` docs + change log updated
- [ ] no secrets, no scratch files, no `__pycache__`
- [ ] commit message: what + why (end with the attribution line your tool requires)

## 5. Collaboration (two people, two machines)

* One owner per area at a time; pull before starting, push small commits.
* **`data/starapp.db` is binary** — merging two modified copies is impossible. Rule of thumb: only one person commits DB changes; others `git checkout -- data/starapp.db` before committing code.
* Generated reports (audits, investigations) are gitignored — keep durable knowledge here in `memory/`, not in ad-hoc report files.
* If you discover that a statement in `memory/` is wrong, fix it in the same commit as your change.

## 5b. Pitfalls learned the hard way (2026-11-27/28)

* `.app-main h1–h4` font sizes are pinned by the type scale (`!important`); a custom size needs `<div role="heading" aria-level="N">`.
* Heredocs in the Bash tool mangle backslashes: patch files with a **script file** (Write tool) instead of an inline heredoc.
* CSS `background` shorthand mixing a gradient and a `url()` needs comma-separated layers (see `.mapping-*-item.selected::after`).
* Browsers cache stylesheets/scripts for 24 h: bump `?v=` **and** hard-refresh (Ctrl+F5) when checking visually.
* `views_guardian.render_guardian_review_detail` contains a code-sample line that starts with `def`; when slicing the function by text, end the slice at `\ndef render_assessment_modal_content(`.
* Before every commit: `git checkout data/starapp.db` → `python scripts/pack_py.py` → `git status data/` clean (the tracked DB is modified by simply running the app).
* A cycle can be created only when the active one is closed, unless `auto_close_previous=True` (`starapp/cycles.py::create_new_six_month_cycle`).
* Mapping request ids are `req_{band}_{badge_id}_{reviewer_id}`; project request ids `projreq_<badge>_<cosmo>`; marksheet ids `asm_rev_<sub>_<attempt>` / `asm_g_<sub>_<attempt>`.
* `Report.md` and the root `README.md` are older overviews (old `?v=` / test counts); fix `memory/` first, they are not authoritative.

## 6. Fast facts for answering questions

* Pass mark: badge `passing_percentage` (default 70 % = 35/50). Rubric: 5 × 10.
* Reviewer must be in a strictly higher band; B6 badges have no peer reviewers (Guardian oversees).
* Flow: create → approve → map → **reviewer accepts within 24 h (else the request expires and counts as declined; Guardian can resend)** → allot (Edit Badge: cosmonauts + reviewer + dates) → publish (72 h for the reviewer to send the project) → project page → submit deliverables → reviewer assesses from the *Assessment* button on Badge Review (unlocks after the submission) and recommends (Give Badge / Re-attempt / Reject; marks lock per attempt) → Guardian decides → badge earned (gold) / re-attempt / reject (the loop restarts with a new attempt); the decision is locked and revocable only by the Guardian; the mapping becomes `completed` only when all mapped cosmonauts have earned.
* Cycle score: cosmo (marks 70 % + completion 30 %) and reviewer execution blended 80/20; tiers 90/80/70/1; promotion at ≥ 85 with ≥ 1 badge.
* 432 tests + 284 end-to-end checks (113 logic + 114 browser + 57 lifecycle); `data/starapp.db` = 38 tables + 1 view; 38 users (36 cadets, 2 guardians).
* `g_cosmonauts` is a legacy view id with no renderer and no sidebar link (empty page if routed to) - not a regression; ignore or remove.
