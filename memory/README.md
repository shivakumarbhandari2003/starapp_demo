# StarApp — Project Memory (START HERE)

> **Audience:** any developer or AI assistant (Claude Code, Cursor, Copilot, ChatGPT, Gemini …) opening this repository on a new machine.
> **Purpose:** give you the *entire* project context — what it is, how it is built, the business rules, the logic, what was already done,
> what is left — without having to re-read 35,000 lines of code.
> **Last verified:** 2026-11-27 · branch `main` · **264 automated tests passing** + **135 end-to-end checks** (77 logic/DB + 58 real-browser, `scripts/e2e_guardian_*.py`) · DB integrity `ok`, 38 tables + 1 view.

## 0. 60-second summary

**StarApp** is an enterprise training & gamified badge-management platform.
A **Guardian** (admin / mentor) authors **badges** (curriculum milestones) per **band** (B1–B6), a higher-band **Reviewer** approves each badge,
the Guardian **maps** cadets + reviewers to the badge and **allots** a calendar timeline, the Reviewer writes a **project brief**, the
**Cosmonaut** (cadet) learns and **submits** deliverables (PDF report + code + GitHub URL), the Reviewer **grades** them on a **50-mark rubric**,
the Guardian gives the **final decision** (pass ≥ badge threshold, default 70 % → **badge earned**, else **retake**). Every 6 months a
**performance cycle** turns the results into an appraisal (score → tier → hike % / promotion).

Stack: **Python 3.12/3.13 · FastAPI · SQLite (WAL) · vanilla JS** with a **server-rendered-HTML** UI engine (`starapp/`) and an optional
offline **Pyodide** bundle. One authoritative database: `data/starapp.db`.

## 1. Reading order (pick what you need)

| # | File | Read it when… |
|:-:|:---|:---|
| 1 | [AI_AGENT_PLAYBOOK.md](AI_AGENT_PLAYBOOK.md) | **Always first.** How to work here, hard rules, "never do X", checklists for common changes |
| 2 | [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | You need the product, roles, users, seed data, glossary |
| 3 | [ARCHITECTURE.md](ARCHITECTURE.md) | You touch backend, controller, views, bridge.js, sessions or startup |
| 4 | [FLOWCHART.md](FLOWCHART.md) | You need the badge lifecycle, request/dispatch flow, cycle flow, state machines |
| 5 | [RULES_AND_CRITERIA.md](RULES_AND_CRITERIA.md) | You change anything business-related (bands, rubric, thresholds, authorisation, scoring) |
| 6 | [LOGICS.md](LOGICS.md) | You touch performance code: caching, indexes, lazy payloads, pagination, UI helpers, security internals |
| 7 | [DATABASE.md](DATABASE.md) | You touch SQL / tables / seed data |
| 8 | [WORK_DONE_AND_STATUS.md](WORK_DONE_AND_STATUS.md) | You want history, measured results, known limits and the backlog |
| 9 | [RUNBOOK.md](RUNBOOK.md) | Setting up a new machine, running, testing, env vars, troubleshooting |

Change-by-change detail (previous logic → new logic → reason) lives in [WORK_DONE_AND_STATUS.md §6](WORK_DONE_AND_STATUS.md#6-change-log-append-here).
The old long-form Stage-1 log, `AGENTS.md` and `docs/` were deleted from the repo; [`../README.md`](../README.md) and `Report.md` are older overviews —
**this `memory/` folder wins on any conflict**.

## 2. The six things that will bite you if you skip this file

1. **Run tests ONLY with `python tests/run_tests.py`.** Suites call `reset_to_seed()` which *wipes* the database they point at; the runner copies
   `data/starapp.db` to a temp dir first. Running `unittest`/`pytest` directly can destroy `data/starapp.db`.
2. **`data/starapp.db` is a tracked binary** and the single source of truth. Two people committing different versions = unresolvable conflict.
   Agree who owns DB changes; never commit it as a side effect of running the app/tests (check `git status data/` before every commit).
3. **Never `INSERT OR REPLACE`** into tables that have `ON DELETE CASCADE` children — it deletes the row first and cascades. Use
   `INSERT … ON CONFLICT(...) DO UPDATE`.
4. **The UI only hides things; the server must enforce.** Every org-wide action must be in `StarAppController._GUARDIAN_ONLY_ACTIONS`
   and every rule must be checked in Python, not just by omitting a button.
5. **After editing anything in `starapp/` run `python scripts/pack_py.py`** to rebuild `js/starapp_bundle.js` (offline/Pyodide copy),
   then run the tests.
6. **After editing anything in `css/` or `js/` bump the `?v=N` query string** in `index.html` and `sw.js` (plus the asserts in
   `tests/test_backend_fullstack.py`, `tests/test_ui_remediation.py` and `Report.md`). The server sends versioned assets with
   `Cache-Control: max-age=86400`, so without a bump browsers keep showing the old CSS/JS for up to a day (new markup then renders unstyled).
   Current value: **`v=57`**, service-worker cache `starapp-runtime-cache-v19`.

## 3. Maintaining this memory (everyone, human or AI)

* When you change behaviour, update the matching file here **in the same commit** and append an entry to
  [WORK_DONE_AND_STATUS.md §6 Change log](WORK_DONE_AND_STATUS.md#6-change-log-append-here) (date · area · previous logic · new logic · reason).
* Keep facts verifiable (file path, function, table). If you are unsure, say "unverified" — a wrong memory is worse than none.
* Do not store secrets, API keys or personal data in this folder.

## 4. Verification you can re-run (nothing here touches the real database)

| What | Command | Covers |
|:---|:---|:---|
| Unit / feature suite | `python tests/run_tests.py` | 264 tests on an isolated DB copy |
| Guardian logic + DB end-to-end | `python scripts/e2e_guardian_logic.py` | 77 checks: every Guardian page renders; approval filters/search; mapping → 24 h requests → accept / expire / resend; calendar (3/5/7/Manual); detail page; Map + save; allotment cards; read-only Timeline; Edit Badge (cosmonauts, reviewer groups, dates, tamper-proof); publish; submission → reviewer marks → Guardian final (retake + approve); Assessment Dashboard; every write re-read from the SQLite **file**; reload-from-DB; integrity + FK check |
| Real-browser end-to-end | `python scripts/e2e_guardian_browser.py` | 58 checks: live FastAPI server on a temp DB + headless Chrome, **real clicks** through the sidebar, mapping lists, calendar, detail page, allotment modals (glass date picker, add-cosmonaut dropdown, real form submit), assessment tree, marks sheet (decision buttons, no-scroll fit), 1100 px overflow sweep, and zero JS/console errors |
