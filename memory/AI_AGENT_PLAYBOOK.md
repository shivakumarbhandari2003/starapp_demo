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
* **Asset cache-bust:** any change under `css/` or `js/` ⇒ bump `?v=N` in `index.html` + `sw.js` (and the tests/`Report.md` that assert it). The server caches versioned assets for 24 h.
* **Type scale:** font sizes are rem tokens (`--type-page-title 1.75`, `--type-section-title 1.25`, `--type-subtitle 1`, `--type-body .875`, `--type-small .8125`, `--type-caption .75`); no `px` font sizes; headings inside `.app-main` are pinned to the scale.
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

### Performance work
Measure first (3k-user synthetic DB, time `ctrl.render()` per view), then prefer: grouped lookups → secondary index → memoise → paginate. Re-run the suite; record before/after numbers.

### UI polish
Match Guardian styling; check contrast (≥ 4.5:1), min font 10 px, no overflow at 420 px, no layout shift on navigation, DOM churn low. Keep `_sidebarSignature`.
Use the type tokens, container queries (`container-type: inline-size`) for components that live in resizable panels/modals, and whole-pixel geometry for connectors/lines (fractional heights blur and misalign).
Verify visually: render the controller on a temp DB, build static HTML with the css files, screenshot with headless Chrome (device scale 1 **and** 2); for pixel questions scan the PNG.
Then run `python scripts/e2e_guardian_logic.py` and `python scripts/e2e_guardian_browser.py`.

## 4. Pre-commit checklist

- [ ] `python tests/run_tests.py` → OK (note the count)
- [ ] `python scripts/pack_py.py` if `starapp/` changed
- [ ] `?v=` bumped if `css/` or `js/` changed
- [ ] `python scripts/e2e_guardian_logic.py` and `python scripts/e2e_guardian_browser.py` → 0 failed (after UI/workflow changes)
- [ ] `git status data/` empty (unless intentional)
- [ ] `memory/` docs + change log updated
- [ ] no secrets, no scratch files, no `__pycache__`
- [ ] commit message: what + why (end with the attribution line your tool requires)

## 5. Collaboration (two people, two machines)

* One owner per area at a time; pull before starting, push small commits.
* **`data/starapp.db` is binary** — merging two modified copies is impossible. Rule of thumb: only one person commits DB changes; others `git checkout -- data/starapp.db` before committing code.
* Generated reports (audits, investigations) are gitignored — keep durable knowledge here in `memory/`, not in ad-hoc report files.
* If you discover that a statement in `memory/` is wrong, fix it in the same commit as your change.

## 6. Fast facts for answering questions

* Pass mark: badge `passing_percentage` (default 70 % = 35/50). Rubric: 5 × 10.
* Reviewer must be in a strictly higher band; B6 badges have no peer reviewers (Guardian oversees).
* Flow: create → approve → map → **reviewer accepts within 24 h (else the request expires and counts as declined; Guardian can resend)** → allot (Edit Badge: cosmonauts + reviewer + dates) → publish → brief → submit → reviewer grades → guardian finalises → badge earned / retake.
* Cycle score: cosmo (marks 70 % + completion 30 %) and reviewer execution blended 80/20; tiers 90/80/70/1; promotion at ≥ 85 with ≥ 1 badge.
* 264 tests + 135 end-to-end checks; `data/starapp.db` = 38 tables + 1 view; 38 users (36 cadets, 2 guardians).
* `g_cosmonauts` is a legacy view id with no renderer and no sidebar link (empty page if routed to) - not a regression; ignore or remove.
