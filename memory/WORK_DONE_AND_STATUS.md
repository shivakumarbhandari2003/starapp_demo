# Work Done, Current Status & Backlog

**State as of 2026-11-27 (215 tests passing):** Stage 1 (logic / performance / security) and Stage 2 (Cosmonaut + Reviewer UI brought to the Guardian standard) are
**implemented, tested (215 tests) and logged**. Changes are in the working tree; whether they are committed depends on the owner — check `git log` / `git status`.

## 1. Timeline

| When | What |
|:---|:---|
| Before 2026-11 | Base product: Guardian portal, Cosmonaut portal, FastAPI modular backend, SQLite, 6-month cycles & appraisals, mapping/allotment/review flows (commits "Guardian UI done", "Calendar and badge hierarchy updated", "Single and updated db"). |
| 2026-11-26 | **Analysis**: Report.md + whole codebase reviewed; badge lifecycle flowchart produced. |
| 2026-11-26 | **Stage 1**: every role's workflow audited for correctness / efficiency / scale; code fixed; log written. |
| 2026-11-26 | **Stage 2**: Cosmonaut + Reviewer UI polished to Guardian standard; flicker root cause fixed. |
| 2026-11-26 | Repo hygiene: generated audit reports ignored in `.gitignore` (kept on disk); this `memory/` folder created. |

## 2. Stage 1 — what changed (summary; details in the log)

| Area | Problem found | Fix |
|:---|:---|:---|
| Test safety | tests re-seeded the real `data/starapp.db` (twice) | `tests/run_tests.py` copies the DB to a temp dir, sets `STARAPP_DB_PATH`/`DATABASE_URL` before imports (`STARAPP_TEST_USE_REAL_DB=1` opts out) |
| Data integrity | `save_cycle`/`save_user` used `INSERT OR REPLACE` → cascade deletes (76→38 enrollments) | UPSERT; `StorageWriteError` + resync |
| DB / store | N+1 export, O(N) scans, no indexes, blobs in memory, double reload | grouped export, 30 indexes, secondary indexes, lazy payloads, fingerprint memoisation, idempotent load |
| Appraisal | O(N²) cohort maths per click | O(N) grouped lookups + memoised cohort |
| Analytics | **fabricated numbers** ("Kaelen Frost", "6 Cadets × 5 Badges", fake trends/dates) | computed from real data |
| Page volume | unbounded tables (6.8 MB cycles page, 34 MB dashboard) | pagination, caps, bounded selectors/charts |
| Server | blocking event loop, unbounded sessions, always-on hot reload | threadpool + lock, LRU sessions, one render/action, GZip, restricted CORS, `HOT_RELOAD` gate |
| Auth/RBAC | a session id containing `guard` logged in as admin; client could claim any `user_id`; any user could request `guardian` role; `require_roles` never denied; cycles API unauthenticated | signed expiring snapshots, strict session ids, role validation, fixed `require_roles`, demo-only fallbacks, guardian-only cycles mutations |
| Workflow rules | cadet could run Guardian actions/open Guardian pages; anyone could answer another reviewer's invitation; submit for non-allotted badges with fabricated deliverables; re-grade final attempts; any reviewer approve any badge; default 9.0 scores; extensions for any badge | `_GUARDIAN_ONLY_ACTIONS`, actor checks, eligibility/deliverable/attempt rules, immutability, `authorize_badge_decision`, no default scores, extension rules |

## 3. Stage 2 — UI (summary)

Method: every page of both portals rendered in headless Chrome at 1440/1024/420 px (87 combinations) and measured (overflow, contrast, CLS, DOM churn, emoji, ids, console errors).
Result: **0 emoji, 0 internal ids, 0 console errors, 0 page overflow, 0 fonts < 10 px, 0 contrast failures**.

* Emoji → SVG icons (`iconize_html`); internal ids → names/badge codes (`humanize_internal_ids`); WCAG-AA colours; verbose sub-titles removed;
  Review Schedule restructured (compact cadet row, shared buttons); rail cycle pill short label; paginated activity feeds; admin no longer counted as a cadet;
  **sidebar flicker fixed** (`_sidebarSignature`).

## 4. Verification status

* `python tests/run_tests.py` → **215 tests OK** (~22 s), never touches `data/starapp.db`.
* Load test (3,038 users, 60 concurrent, 420 requests): **0 errors, 66–74 req/s, p50 ≈ 0.6 s, ~180 MB**.
* Browser audit: clean (see Stage 2).
* `/api/health`: `healthy`, 38 tables, 0 FK violations.

## 5. Known limits & backlog (priority order)

| # | Item | Why / hint |
|:-:|:---|:---|
| 1 | **Hash seeded passwords** (plaintext `123456789`) | needs bcrypt in the offline runtime or hash-on-first-login |
| 2 | **Move uploads out of SQLite** (PDF/code base64) | keep a path column; object storage for big cohorts |
| 3 | **Multi-process scale-out** | actions are serialised on one in-memory store; needs shared session store/queue. `data_version` fingerprints already make multi-process *reads* safe |
| 4 | **Unify REST services with controller rules** | `reviews/allotments/submissions/evaluations` services are a smaller duplicate (and `qa` vs `question_answering` naming differs) |
| 5 | Split `starapp/app.py` (6k lines) and the views (6–7k lines each) into modules per feature | keep action names stable |
| 6 | Rebuild the offline bundle in CI (`scripts/pack_py.py`) | easy to forget |
| 7 | Remove leftovers if unused: `overall.txt`, `push_to_github.py`, `BASELINE_DATA_SNAPSHOT.json` | not referenced by the app (verify before deleting) |
| 8 | Real-deployment checklist | `STARAPP_DEMO_MODE=false`, new `SECRET_KEY`, HTTPS + `STARAPP_COOKIE_SECURE=true`, `DEBUG=False` |

## 6. Change log (append here)

Format: **date · area · previous logic · new logic · reason** (add a longer entry to the Stage log if the change is large).

| Date | Area | Previous logic | New logic | Reason |
|:---|:---|:---|:---|:---|
| 2026-11-26 | Stage 1 (A–I) & Stage 2 (S2-1…S2-8) | see section 2/3 and the full log | see log | scale to thousands of users, correctness, security, professional UI |
| 2026-11-26 | Repo hygiene | 15 generated audit/report `.md` tracked in git | ignored via `.gitignore` (files kept locally), untracked with `git rm --cached` | not needed to run the project |
| 2026-11-27 | Cosmonaut portal navigation | Sidebar had a separate "Past Cycle & Performance" page (`c_cycles`) plus a "Past Performance →" button | Item removed; the per-cycle appraisal cards (dual-role scores, tier, compensation, promotion, remarks) render under the cycle cards on **Choose Cycle**; `c_cycles` resolves to `c_choose_cycle`; topbar link renamed "Cycles & Appraisals"; finalisation notification points to Choose Cycle | one place for cycles and appraisals, less navigation |
| 2026-11-27 | Project request workflow | "Earn the Badge" showed `Allocated Milestone` + `Submit Deliverables`; the reviewer filled a long AI form (outcomes, requirements, deliverables); submissions needed no project (demo mode even invented one); `_collect_cadet_review_context` showed one cosmonaut's project on every card | Cosmonaut taps **Request Project** -> request to the mapped reviewer (notification, count on Badge Reviews) -> reviewer's **Create Project** = Heading + Content + recipient checklist -> **Send Project to Mapped Cosmonauts** -> button becomes **Submit Project Deliverables** (project shown first, then PDF/code/GitHub) -> reviewer's **Cosmonaut Assessments**; server refuses submission without a sent project; one record per send; reviewer card state per cosmonaut; reviewer queue/notification use `get_mapped_reviewer_id`; fixed literal `&rarr;` in the assessment queue; chip "Allocated Project" renamed "Allocated Badge" | the requested cosmonaut <-> reviewer project hand-off |
| 2026-11-27 | View Profile (all portals) | Cosmonaut: "Profile" nav item + clickable name card; Guardian: no profile page at all. Cosmonaut profile showed hard-coded text ("Cadre Orion-24", "Tier-1 Certified", "ING-104", a canned bio, placeholder guardian credentials) | "View Profile" `nav-link` pinned at the bottom of every sidebar (active on the profile page); new `g_profile` page (identity, role access, band, manager, cycle, live academy overview); cosmonaut profile now shows real band/roles/manager/guardian/cohort/cycle standing/badges earned/average/rank/current milestone; footer CSS (`.sidebar-footer` 164 px) updated | profile is compulsory for everyone and must show the person's real data |
| 2026-11-27 | Cosmonaut sidebar order & reviewer bands | Choose Cycle first and the landing page; reviewer items shown to any B2–B6 **or** badge_reviewer role **or** anyone with a pending request; label "Cadet Assessments" | Order Badges (home) → Marksheet → Deadline Extension → Badge Reviews → Review Requests → Cosmonaut Assessments (Band 2+ only) → Profile last; Choose Cycle reached from the cycle pill; band-only eligibility enforced in `nav_cosmonaut` + render | reviewers must be in a higher band than B1; consistent navigation |
| 2026-11-27 | Cosmonaut portal wording | mixed "Cadet" / "Cosmonaut" text, partly stored in the DB | `cosmonaut_terms()` normalises all Cosmonaut-portal output (see LOGICS C) | consistent terminology without touching ids/handlers |
| 2026-11-27 | DB hygiene | `INSERT OR REPLACE INTO schema_version` re-stamped `installed_at` on every start → tracked `data/starapp.db` always showed as modified | `INSERT OR IGNORE` | clean `git status` for both collaborators |
| 2026-11-26 | Documentation | scattered, partly outdated docs | `memory/` folder (this set) + root `CLAUDE.md` pointer | any AI/dev on a new machine gets full context |
