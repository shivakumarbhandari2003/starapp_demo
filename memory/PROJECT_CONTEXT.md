# Project Context

## 1. What StarApp is

A training-and-recognition platform for an engineering organisation. People sit in **bands B1…B6** (plus an Executive/CEO band) and
in **learning tracks**. Growth is measured through **badges**: a badge is a curriculum milestone (learning outcomes, topics, a practice
project, a pass threshold). Cadets earn badges by submitting a real project that a *higher-band colleague* grades on a fixed
50-mark rubric. Badge results feed a **6-month performance cycle** that produces appraisal scores, tiers, hike % and promotion
recommendations.

## 2. Roles (people can hold several)

| Role id (`system_roles`) | UI name | What they do |
|:---|:---|:---|
| `guardian` | Guardian (admin, mentor, curriculum owner) | Creates badges (AI-assisted), maps cadets+reviewers, allots calendars, publishes/unpublishes, uploads learning materials, decides extensions, gives the **final** assessment, runs cycles & appraisals, broadcasts announcements. Sees every badge. |
| `badge_reviewer` | Badge Reviewer | Approves / returns a *proposed badge* of a lower band (Reviewer_Band > Badge_Band). Cannot review a badge they authored. |
| `project_reviewer` | Project Reviewer (shown as "Reviewer") | Accepts mapping invitations, writes & releases the **project brief** to mapped cadets, grades submissions on the rubric (the first assessment). |
| `cosmonaut` | Cosmonaut (cadet / learner) | Sees allotted badges & roadmap, studies materials, submits deliverables (multi-attempt), requests deadline extensions, sees marksheets/leaderboard/profile. |

Real counts in the committed DB (38 users): 36 cosmonauts, 30 badge reviewers, 30 project reviewers, 2 guardians (`guardian_1` Arjun Mehta – band CEO,
`admin` "Guardian Admin" – B6). A reviewer is *also* a cadet (dual role): the app is built around that. The `admin` account is **not** a cadet
(excluded from cohort counts by `get_all_cosmonauts()`).

Two portals, one codebase:
* **Guardian portal** — views `g_*` (the UI quality bar: icon rail, clean cards, SVG icons).
* **Cosmonaut portal** — views `c_*`, used by cadets *and* reviewers (reviewer pages: `c_requests`, `c_badge_review`, `c_badge_reviews`, `c_assessment_detail`; the old `c_assessments` queue was removed - ids from old links resolve to `c_badge_reviews`).

## 3. Bands, tracks, cycles (committed data)

| Band | Title | Experience | | Track code | Name |
|:-:|:---|:---|-|:-:|:---|
| B1 | Foundation Associate | 0–2 y | | `SD` | Solutions Designer |
| B2 | Specialist | 2–4 y | | `AIE` | AI Engineer |
| B3 | Senior Specialist | 4–7 y | | `SE` | Systems Engineer |
| B4 | Lead Engineer | 7–10 y | | `EXEC` | Executive Leadership |
| B5 | Principal Architect | 10–14 y | | | |
| B6 | Chief / Distinguished Fellow | 14+ y | | | |
| CEO | Executive Council | 20+ y | | | |

Users per band: B1 7, B2–B6 6 each, CEO 1 (38). Cycles: `cycle_0` "Previous Cycle (Jan–Jun 2026)" **closed**, `cycle_1` "Cycle 1 (Jul–Dec 2026)" **active**
(`DEFAULT_CYCLE_ID = "cycle_1"`). Both have 38 enrollments; 36 finalized appraisals exist.

Snapshot of seeded activity: 11 badges (9 approved, 1 pending_review, 1 returned; 8 published), 35 badge timelines (7 active, 28 completed),
24 submissions, 43 marksheets, 11 mapping requests, 8 reviewer project prompts, 3 deadline extensions.

## 4. Demo accounts / sign-in

* Username = email (e.g. `aarav.sharma@starapp.io`, cadet B1 `m_b1_1`; `rohan.deshmukh@starapp.io`, B2 `m_b2_1`; `arjun.mehta@starapp.io` guardian; `admin@starapp.io`).
* Seed passwords are **plaintext `123456789`** (known weakness, see backlog). The `?role=` shortcut and passwordless "quick-login" pills exist **only when `STARAPP_DEMO_MODE=true`**.
* User ids: cadets `m_b{band}_{n}` (e.g. `m_b3_4`), guardians `guardian_1`, `admin`.
* At login a user may select only a role they actually hold (`user_role_assignments`); anything else is rejected.

## 5. Glossary

| Term | Meaning |
|:---|:---|
| Cosmonaut | cadet / learner |
| Guardian | admin + mentor + curriculum owner (also the "Executive Council") |
| Badge | a curriculum milestone with outcomes, topics, project requirements, pass %, target band |
| Band mapping | Guardian's pairing "cadets of band X + reviewers (higher band) ↔ badge" (`band_mappings`, `mapping_requests`) |
| Allotment / timeline | per-cadet-per-badge calendar (`badge_timelines`): learning window, project window, submission deadline, review date |
| Project request / project | a Cosmonaut taps **Request Project** on an allotted badge; the mapped Reviewer answers with a project = **Heading + Content** and sends it to their mapped Cosmonauts (`reviewer_project_prompts`); only then can the Cosmonaut submit deliverables |
| Marksheet | one graded attempt (`assessment_marksheets`): reviewer's first assessment, then Guardian's final |
| Attempt | one submission try; retakes create a new row with `attempt_number + 1` (history is never overwritten) |
| Cycle | 6-month performance period; appraisals are computed per cycle |
| Cosmo score / Reviewer score / Composite | the two halves of the dual-role appraisal and their blend (see RULES_AND_CRITERIA §6) |
| Region | a named chunk of server-rendered HTML (sidebar, topbar, main) that the browser patches in place |
| Dispatch | `POST /api/v1/dispatch` — the single endpoint through which the UI performs actions |
| Demo mode | `STARAPP_DEMO_MODE=true`: convenience shortcuts that must be OFF for real users |

## 6. Repository map (what lives where)

| Path | Responsibility |
|:---|:---|
| `serve.py` | local launcher (uvicorn on 127.0.0.1:8000) |
| `backend/app/main.py` | FastAPI app, dispatch endpoint, signed sessions, middleware, static mounts |
| `backend/app/core/` | `config.py` (env), `security.py`, `permissions.py` (band/rubric rules), `dependencies.py` (auth/RBAC), `exceptions.py` |
| `backend/app/database/` | `connection.py` (PRAGMAs, health), `migrations.py` |
| `backend/app/features/<name>/` | REST modules `router / service / repository / schemas`: auth, users, bands, badges, reviews, allotments, submissions, evaluations, audit, cycles |
| `backend/app/integrations/gemini/` | server-side Gemini proxy (badge content generation) |
| `starapp/app.py` | **`StarAppController`** — all UI actions, state, rendering orchestration (~6,000 lines) |
| `starapp/storage.py` | **`DataStore`** — in-memory cache + indexes over SQLite, memoisation |
| `starapp/database.py` | SQLite layer: DDL, `export_to_dict`, performance indexes, badge approval authorisation |
| `starapp/models.py` | dataclass-like models (`Badge`, `User`, `ProjectSubmission` lazy payloads …), `DEFAULT_HIKE_POLICY` |
| `starapp/cycles.py` | cycle creation/activation/closure + dual-role appraisal maths |
| `starapp/analytics.py` | cohort profiles, leaderboards, dashboard numbers (all computed from real data) |
| `starapp/assessment.py`, `roadmap.py` | rubric helpers; roadmap/prerequisite state (`completed / active / locked`) |
| `starapp/views_common.py`, `views_guardian.py`, `views_cosmonaut.py` | HTML renderers, icon system (`iconize_html`), id→name humaniser |
| `starapp/pagination.py` | server-side list pagination |
| `starapp/repositories/` | small per-aggregate repository helpers |
| `starapp/seed_data.py`, `mapping_data.py`, `previous_cycle_seed.py` | seed catalogues/users and the closed previous cycle |
| `js/bridge.js` | browser bridge: dispatch, region patching (`updateRegions`), sidebar signature, modals, 24 h countdown ticker, glass date picker, Edit-Badge assignee helpers, decision list |
| `js/api.js` | REST client `window.StarAppAPI` |
| `js/starapp_bundle.js` | **generated** offline Pyodide bundle (`scripts/pack_py.py`) — don't hand-edit |
| `css/` | design tokens (incl. the `--type-*` rem scale) + liquid-glass styles; versioned `?v=N` in `index.html`/`sw.js` |
| `tests/` | 411 tests; always via `tests/run_tests.py` |
| `scripts/` | `pack_py.py`, `seed_previous_cycle.py`, `clear_*.py`, `verify_e2e_workflow.py`, **`e2e_guardian_logic.py`**, **`e2e_guardian_browser.py`** (+ `_miniws.py`, a stdlib websocket client for Chrome DevTools) |
| `ER diagram/`, `Star Registry Schema.html` | standalone schema viewers |
| `data/starapp.db` | **the** database (tracked) |
