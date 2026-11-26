# StarApp — Stage 1: Logic, Performance, Security & Data-Integrity Remediation Log

> **Goal of this stage:** make every step of every role (Guardian → Reviewer → Cosmonaut) correct, efficient and safe for
> **thousands of users**, while keeping the UI exactly as it is.
> **How to read this file:** every entry has four parts — **Stage / area**, **Previous logic**, **New logic**, **Reason**.
> Files are linked so the change can be reviewed in place.

---

## 0. How the work was measured (so the numbers below can be reproduced)

A synthetic copy of the database was generated with **3,038 users, 36 badges, 9,000 timelines, 8,100 submissions
(with ~40 KB payloads), 8,100 marksheets, 24,000 notifications and 18,000 activity events** (never the real database).
Every page was rendered for a Guardian and for a Cosmonaut, then a **real `uvicorn` server** was hit by 60 concurrent
cadets. Scripts used: profile of every view, load test through HTTP, and 183 automated tests.

| Measurement at ~3,000 users | Before | After |
|:---|---:|---:|
| Server start (cold) / memory | 3.6 s *(extra reload in `initialize`)* / **515 MB** | **1.8 s total** / **94 MB** |
| New browser tab / login (`initialize`) | full database reload every time (~1–3 s) | **~15 ms** (no reload) |
| Guardian **Cycles** page | **22 s**, 6.8 MB HTML | **~20 ms**, 65 KB |
| Guardian **Dashboard** | **19.6 s**, **34 MB** HTML | **~300 ms**, 227 KB |
| Guardian **Activity** stream | 107 ms, 9.6 MB | 12 ms, 35 KB |
| Guardian **Mapping** | 91 ms, 2.1 MB | 41 ms, 173 KB |
| Cosmonaut **Dashboard** | **68 s**, 9.8 MB | **~200 ms**, 92 KB |
| Average Cosmonaut page | 48 ms | **8.7 ms** |
| Live throughput, 60 concurrent users | 18 req/s (p50 3.3 s) | **66–74 req/s (p50 ≈ 0.6 s)**, 0 errors |
| Server memory after load | – | 183 MB |
| Test suite | 89 documented / 149 real tests, ~32 s | **190 tests, ~18 s**, all pass |

---

## STAGE A — Data safety of the test suite

### A1. Tests destroyed the real database
- **Previous logic:** `tests/run_tests.py` imported the app against `data/starapp.db`. Many suites call `store.reset_to_seed()`
  → `clear_all_tables()`, so **every test run wiped and re-seeded the real database** (it showed up as `M data/starapp.db`).
- **New logic:** [tests/run_tests.py](tests/run_tests.py) copies the database to a temp folder and sets `STARAPP_DB_PATH` /
  `DATABASE_URL` before any StarApp module is imported; the temp copy is deleted afterwards. `STARAPP_TEST_USE_REAL_DB=1` restores
  the old behaviour deliberately.
- **Reason:** running tests must never be able to lose production data. Verified: the real file's checksum is identical before and after a run.

### A2. Two tests opened a hard-coded path
- **Previous logic:** `sqlite3.connect("data/starapp.db")` in [test_save_badge_verification.py](tests/test_save_badge_verification.py)
  and [test_final_e2e_workflow_verification.py](tests/test_final_e2e_workflow_verification.py).
- **New logic:** they use `store.db.db_path` (the database the app is really using).
- **Reason:** otherwise they only passed because they looked at the file other tests had polluted.

---

## STAGE B — Database layer (`starapp/database.py`, `starapp/storage.py`, `starapp/models.py`)

### B1. `INSERT OR REPLACE` silently deleted child rows (real data-loss bug)
- **Previous logic:** [`save_cycle`](starapp/storage.py) and [`save_user`](starapp/storage.py) used `INSERT OR REPLACE`. In SQLite this
  *deletes the old row first*, which fires `ON DELETE CASCADE`. Reproduced on a copy: calling `save_cycle` cut a cycle's enrollments
  from **76 → 38**; `save_user` removed the user's role assignments and **badge timelines** and reset track / manager columns.
  `save_cycle` runs when appraisals are calculated and when a cycle is activated or finalised.
- **New logic:** proper `INSERT … ON CONFLICT(id) DO UPDATE` upserts that touch only the columns being saved.
- **Reason:** saving a cycle or a user must never delete other people's data. Regression tests: `TestNoCascadeDataLoss`.

### B2. Thirty missing indexes
- **Previous logic:** only a handful of indexes; SQLite does not index foreign keys, so "timelines of cosmonaut X in cycle Y",
  "notifications of user Z", `lower(email)` at login, mapping lookups, etc. were full table scans.
- **New logic:** [`PERFORMANCE_INDEXES`](starapp/database.py) (30 composite / FK indexes) created idempotently on every start (existing
  databases are upgraded in place), followed by `PRAGMA optimize`.
- **Reason:** scans grow linearly with users; indexed lookups stay constant. `sqlite_stat1` (created by `optimize`) is excluded from the health-check table count.

### B3. `export_to_dict` ran thousands of queries
- **Previous logic:** one `SELECT` per user for roles, per badge for prerequisites, per announcement for recipients/receipts.
- **New logic:** one grouped query each ([`export_to_dict`](starapp/database.py)).
- **Reason:** query count was O(users); it is now constant.

### B4. Every submission's PDF / code was held in server memory
- **Previous logic:** `SELECT *` loaded the base64 PDF and code of **all** submissions into RAM at start-up and on every reload.
- **New logic:** `export_to_dict(include_blobs=False)` loads metadata only; [`ProjectSubmission`](starapp/models.py) fetches
  `payload / pdf_payload / code_payload` **lazily** (one row) the first time a viewer opens them. Saving a lazy submission updates
  metadata only and never rewrites the blobs. Browser/Pyodide snapshots still export blobs (`include_blobs=True`).
- **Reason:** memory and reload time are now independent of upload size (515 MB → 97 MB at 3,000 users).

### B5. Failed writes looked like successes
- **Previous logic:** 13 save methods did `except Exception as e: print("Error saving …")` and then `mark_dirty()` — a "database is
  locked" error made a grade/submission appear saved in memory and vanish after the next reload.
- **New logic:** [`_write_failed`](starapp/storage.py) rolls back, drops derived caches and raises `StorageWriteError`;
  [`handle_event`](starapp/app.py) catches it, re-syncs memory from SQLite and tells the user "nothing was modified – try again".
  Any other unexpected handler error is logged and shown as a friendly message instead of freezing the UI.
- **Reason:** memory and database must never disagree silently.

### B6. Badge approve / return exported the whole database twice
- **Previous logic:** `create_badge_for_review`, `approve_badge`, `return_badge`, `assign_and_request_badge_review` called
  `db.export_to_dict()` **twice** just to refresh notifications and activity.
- **New logic:** [`_sync_feed_tables`](starapp/storage.py) pulls only rows newer than a `rowid` watermark.
- **Reason:** a one-click approval cost seconds at scale; it is now milliseconds.

### B7. Every new tab reloaded the entire database
- **Previous logic:** `StarAppController.initialize()` → `store.load_from_json(None, None)` → full `export_to_dict` + rebuild of every
  cached object, for **every new session**, replacing the objects other sessions were holding.
- **New logic:** the process-wide store is reloaded only when another connection changed the file (`PRAGMA data_version`), see
  [`load_from_json`](starapp/storage.py).
- **Reason:** login storms no longer hammer the database; new session cost fell from seconds to ~15 ms.

---

## STAGE C — Data-access & caching layer (`starapp/storage.py`)

### C1. Per-user reads scanned every row
- **Previous logic:** `get_submissions_for_cosmonaut`, `get_assessments_for_cosmonaut`, `get_notifications`, `get_activities`,
  `get_extensions_for_cosmonaut`, `get_assessment_for_submission`… looped over *all* rows of *all* users.
- **New logic:** secondary indexes (by cosmonaut, submission, reviewer) built once, then maintained **incrementally** inside every
  `save_*` / `add_*` ([`_ensure_ix`](starapp/storage.py)); whole-collection replacement or direct add/remove is detected and rebuilds the index.
  New helpers: `get_timelines_for_cosmonaut`, `get_timelines_for_reviewer`, `get_reviewer_submissions`.
- **Reason:** O(1) per-user reads instead of O(all rows).

### C2. Cache invalidation by database fingerprint
- **Previous logic:** `get_all_badges`, `get_all_cycles`, `get_cycle_enrollments`, `get_cycle_appraisals` re-queried SQLite on **every call**
  (3,069 `SELECT * FROM badges` per render pass at scale) and `get_cycle_appraisal(cycle,user)` loaded + sorted every appraisal of the cycle for one user.
- **New logic:** [`_db_fingerprint`](starapp/storage.py) = `(PRAGMA data_version, conn.total_changes)` detects *any* write (this connection or
  another, e.g. REST). Reads are memoised against it; cycle tables reload only when another connection wrote; appraisal lookup is a dict.
- **Reason:** same freshness guarantee, a fraction of the queries.

### C3. "Learning-scope" memo (notification writes no longer flush heavy caches)
- **Previous logic:** (would have been) any write invalidates every cache — and notifications are written constantly.
- **New logic:** `mark_dirty(learning=False)` for notifications / activity / read receipts; expensive cohort caches use `scope="learning"`.
- **Reason:** cohort-level caches survive normal traffic.

### C4. `get_badges_for_cosmonaut` rebuilt everything per cadet
- **Previous logic:** per call: scan all timelines, run SQL, loop *every mapping × every badge*, `b not in result` (O(n²)).
- **New logic:** [`_cosmo_badge_map`](starapp/storage.py) builds `cosmonaut → badge ids` once per data change; each call is a set lookup. Visibility rule unchanged (published, or already certified).
- **Reason:** dashboards call it for every cadet (3,042 calls → 27 s).

### C5. Cycle-wide lists were re-filtered and re-sorted on every render
- **New logic:** `get_all_submissions / assessments / extensions / cosmonauts / badges` are memoised per cycle (learning scope), returned as copies.
- **Reason:** every page render of every user did this work; average cadet page 48 ms → 8.7 ms together with C6.

### C6. Sidebar scanned all submissions × all mappings
- **Previous logic:** [`render_cosmonaut_sidebar`](starapp/views_cosmonaut.py) filtered every submission of the cycle, calling `get_timeline`
  twice and `get_band_mappings()` **per submission** (24,000 calls per render). The reviewer assessments list had the same shape.
- **New logic:** `store.get_reviewer_submissions(reviewer_id)` touches only the reviewer's own cadets; mapping lookups are hoisted per badge.
- **Reason:** this ran on *every* page for every reviewer.

---

## STAGE D — Appraisal engine (`starapp/cycles.py`)

### D1. Quadratic appraisal calculation
- **Previous logic:** `compute_cycle_candidate_performance` re-scanned all submissions, assessments, timelines, mappings and badges for each
  candidate (O(users × rows) — **47 s** of CPU at 3,000 users) and recomputed "published badges" per user.
- **New logic:** every table is grouped by user once, then each candidate is a few dict lookups. Business rules (published-only assignment,
  70/30 cosmonaut score, 55/25/20 weights, tiers, hike slabs, promotion at ≥ 85) are untouched.
- **Reason:** O(users + rows). 22 s → ~20 ms.

### D2. Memoised cohort result; single-user rows served from it
- **New logic:** the full-cohort result is cached per cycle (learning scope); `users_override=[user]` (used on every cadet page for the cycle
  table) is answered from that cache instead of regrouping the cycle for one person.

---

## STAGE E — Analytics & dashboards (`starapp/analytics.py`)

### E1. Cohort profiles rebuilt per page view
- **New logic:** profiles of everyone else are built once per data change and shared by all viewers.

### E2. Invented ("demo") numbers presented as real analytics
- **Previous logic:** `build_cosmonaut_analytics_record` returned a fixed `last_active = "2026-11-08"`, `upcoming_deadline = "2026-12-02"`,
  `days_inactive = 0`, `batch = "Batch Orion-24"` for **every** cadet. The cohort analytics contained a hard-coded catalogue of five fictional
  badges ("GOV-101 … SQL-201"), fixed weekly trends, a fixed "6 weeks", and KPI popovers stating facts such as
  *"Kaelen Frost (Needs Attention…)"*, *"+18 % ahead of baseline (2.8 badges/week)"*, *"6 Cadets × 5 Badges"*.
- **New logic:** last-active and next deadline are derived from the cadet's real submissions / marksheets / timelines; the badge table, weekly
  trends, velocity (certifications ÷ real elapsed weeks), flagged-cadet names and denominators are all computed from real data.
- **Reason:** a Guardian must be able to trust every figure on screen.

### E3. Hard-coded "5 badges per cadet"
- **Previous logic:** the roster, leaderboard and velocity chart divided by a constant `5`.
- **New logic:** they use each cadet's real `total_assigned` (the "Cadets for attention" sub-text is computed too instead of the fixed "1 Needs Attention • 1 Monitor").

---

## STAGE F — Page volume & rendering (same look, bounded size) 

### F1. Every list rendered every row
- **Previous logic:** one table row per employee on the dashboard, cycles table, leaderboard, activity stream; one `<option>` per employee in the
  selector; one bar-chart column + hover pop-over per cadet; the cadet's dashboard rendered the **entire company** as a leaderboard.
  At 3,000 users: 34 MB / 9.8 MB / 9.6 MB / 6.8 MB of HTML — the browser freezes long before the server finishes.
- **New logic:** [starapp/pagination.py](starapp/pagination.py) — server-side paging (25 rows; 50 for the audit stream; 10 for the leaderboard) with a
  compact First/Prev/Page x of y/Next/Last pager (`set_list_page` action, read-only-cycle safe, state bounded to 200 keys). The selector lists
  150 people + the current selection; the chart shows the 12 cadets who need attention most (totals still cover everyone); the cadet leaderboard
  shows the top 10 plus the viewer's own true rank; mapping cards render 60 people with a "+N more – refine your search" note (select-all still
  acts on the full filtered set on the server and selected people are always shown).
- **Reason:** payload size and browser work must not grow with the number of employees.

### F2. Two renders and a doubled payload per click
- **Previous logic:** `handle_event` rendered, then `/api/v1/dispatch` rendered **again**, and the JSON contained the page twice (`full_html` + `regions`).
- **New logic:** one render per action (`render_generation` check) and `full_html` is omitted when `regions` is present.
- **Reason:** halves CPU per click and roughly halves bytes on the wire (clients already prefer `regions`).

---

## STAGE G — Server runtime (`backend/app/main.py`, `config.py`)

| # | Previous | New | Reason |
|---|---|---|---|
| G1 | `async def dispatch` ran 100+ ms of CPU **on the event loop**, freezing health checks and static files | work runs in a worker thread under a lock (the in-memory store is shared, so actions are serialised, but the loop stays responsive) | one slow page can no longer stall everyone |
| G2 | `_session_controllers` dict grew forever (one controller per visitor) | LRU `OrderedDict`, `STARAPP_MAX_SESSIONS` (default 1500); evicted users are restored from the signed snapshot | bounded memory |
| G3 | no compression | `GZipMiddleware` | markup compresses ~10× |
| G4 | module hot-reload on every request, even in production | only when `STARAPP_HOT_RELOAD` (defaults to `DEBUG`) | dev convenience must not run in prod |
| G5 | CORS `*` with credentials (invalid + unsafe) | explicit origins (`STARAPP_CORS_ORIGINS`, localhost by default) | cross-site request protection |
| G6 | `/js/starapp_bundle.js` — **a base64 copy of the entire database, passwords included** — was downloadable by anyone | served only in `STARAPP_DEMO_MODE`; 404 otherwise | data-leak |
| G7 | session cookie never `Secure` | `STARAPP_COOKIE_SECURE` | HTTPS deployments |
| G8 | health check counted SQLite-internal tables | ignores `sqlite_%` | accurate after `PRAGMA optimize` |

---

## STAGE H — Authentication, sessions & RBAC (security)

| # | Previous logic | New logic | Reason |
|---|---|---|---|
| H1 | A client-chosen session id **containing `guard` or `cosmo`** auto-logged in as the **admin** / a cosmonaut | sessions start logged out; explicit `?role=` shortcuts exist only in demo mode | passwordless admin access |
| H2 | `boot` accepted `restore_session: {user_id:"admin"}` from the browser and made that user the session owner | snapshots are **HMAC-SHA256 signed + expire** (`SECRET_KEY`, `SESSION_EXPIRE_HOURS`); forged / tampered / expired ones are ignored | anyone could impersonate any user |
| H3 | missing session id silently used the shared `"default"` controller (every anonymous client shared one session) | `X-Session-Id` is required and validated | session mixing |
| H4 | `login` accepted `{"username":"x"}` with no password; `select_demo_account` logged in as anyone | both only in `STARAPP_DEMO_MODE`; quick-login pills hidden when off | passwordless login over the network |
| H5 | **`require_roles` never denied anyone** (`… and "admin" not in allowed and …` is always false for guardian / reviewer / cosmonaut guards) | roles are taken from the session **and** `user_role_assignments`; guardians may do everything | every user could call guardian endpoints |
| H6 | `POST /auth/login` trusted `selected_role` (a cosmonaut could ask for `guardian`); `switch-role` same | requested role must be one the user holds → 403 | privilege escalation |
| H7 | unauthenticated REST calls fell back to `X-User-Id`, `?demo_user_id=`, the UI session, or **guardian_1** | those fallbacks exist only in demo mode | impersonation by header |
| H8 | `/api/v1/cycles/*` had **no authentication**; `actor_id` / `created_by` came from the request | guardian-only mutations; actor = authenticated user | anonymous finalise / salary edits |
| H9 | plaintext password compare with `==`; `/auth/demo-users` public | `hmac.compare_digest`; directory disabled outside demo mode | timing + enumeration |
| H10 | `UPDATE user_sessions` on every request kept SQLite's single write lock for the whole request → store writes waited the 5 s busy timeout ("database is locked", 212 s test run) | touched at most every 5 min and **committed immediately** | lock contention |

---

## STAGE I — Business-rule enforcement (workflow correctness)

The UI only *offered* valid choices; the server did not verify them. Because the browser chooses the action name and its data, each rule is now enforced server-side.

| # | Workflow step | Previous logic | New logic |
|---|---|---|---|
| I1 | All Guardian actions | any signed-in user could dispatch `publish_badge`, `update_cycle_appraisal` (salary/hike), `finalize_and_close_cycle`, `broadcast_announcement`, … | central [`_GUARDIAN_ONLY_ACTIONS`](starapp/app.py) gate (37 actions) |
| I2 | Navigation | `nav_guardian` set **any** view for **any** user (a cadet could open the Guardian dashboard / salaries) | allow-lists + guardian check; render-time defence in depth |
| I3 | Mapping invitations | accept / reject / **delete** any request by id (prefix match!) as anyone | only the invited reviewer may answer; only a Guardian may withdraw; exact id |
| I4 | Send mapping invitations | reviewer band, badge approval and cadet band were **not** verified; notification text was the literal word "request" | `Reviewer_Band > Badge_Band` enforced, badge must be *approved*, cadets must belong to the band; real message |
| I5 | Cadet submission | any badge id accepted; missing PDF/code/GitHub replaced by **dummy file + fake GitHub URL** that reviewers then graded; new attempt allowed while awaiting Guardian or after the badge was earned | must be allotted + published; deliverables inherited from the previous attempt or required (placeholders only in demo mode); `.pdf`, `http(s)` URL, ~9 MB limit; blocked while `reviewer_assessed` / after `approved`; late submissions recorded in activity + reviewer notification |
| I6 | Grading | a finalised attempt could be graded again (deterministic marksheet id + `INSERT OR REPLACE` → an earned badge could flip to retake); offline browser mode defaulted blank scores to **9.0/10** | final decisions are immutable; blank scores are an error |
| I7 | Badge approve / return | only checked "has the badge_reviewer role" — any reviewer could approve **or return** *any* badge (other reviewers', higher band, already live); audit id `bre_<badge>_approved` could collide | [`authorize_badge_decision`](starapp/database.py): must be `pending_review`, assigned reviewer (or Guardian), `Reviewer_Band > Badge_Band`, not the author; unique audit ids |
| I8 | Reviewer project release | any user could author/release a project for any badge to any cadets | only the mapped reviewer / Guardian, only to their mapped cadets |
| I9 | Deadline extension | allowed for badges not allotted to the cadet (invented default deadline), unlimited duplicate pending requests, id from `len()+1` | requires an allotted, unfinished milestone; one pending request per milestone; unique id |

Regression coverage: [tests/test_scale_and_security_regressions.py](tests/test_scale_and_security_regressions.py) — 41 tests across
data-loss, indexes/memo, lazy payloads, pagination, signed sessions, session registry, demo mode, REST RBAC and every workflow rule above and the Stage 2 UI rules.

---

## New configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `STARAPP_DEMO_MODE` | `true` | passwordless quick-login pills, `?role=`, REST header fallbacks, offline bundle, demo placeholders. **Set `false` for real users.** |
| `STARAPP_MAX_SESSIONS` | `1500` | in-memory UI sessions before LRU eviction |
| `STARAPP_HOT_RELOAD` | = `DEBUG` | python hot-reload on request (dev only) |
| `STARAPP_CORS_ORIGINS` | localhost | comma-separated allowed origins |
| `STARAPP_COOKIE_SECURE` | `false` | `Secure` session cookie (HTTPS) |
| `SECRET_KEY` | dev key | **change it** — it signs session snapshots |

## Known limits / recommended next steps (not done in this stage)

1. **Uploads in the database:** PDFs/code are still stored base64 in SQLite (now lazy-loaded). For very large cohorts move them to files / object storage and keep a path column.
2. **One process:** actions are serialised on one in-memory store. For > ~1,000 *simultaneously active* users run behind a queue or move per-session state to a shared store; the `data_version` fingerprints already make multi-process reads safe.
3. **Passwords** in the seed data are plaintext `123456789`. Hash with bcrypt on first login (needs `bcrypt` in the offline runtime, so left as-is).
4. REST routers (`reviews`, `allotments`, `submissions`, `evaluations`) now have correct RBAC, but their service-layer rules are a smaller duplicate of the controller rules; long-term the controller should call the same services.
5. The offline Pyodide bundle (`js/starapp_bundle.js`) must be rebuilt with `python scripts/pack_py.py` after source changes.


---

# STAGE 2 — Cosmonaut & Reviewer portal brought up to the Guardian standard (UI)

> **Reference:** the Guardian portal (icon rail, clean cards, uniform tables/pills, SVG line icons). **Method:** every page of both
> portals was rendered in headless Chrome at **1440 / 1024 / 420 px** (87 page-width combinations) and measured: horizontal overflow, clipped text,
> console errors, emoji glyphs, internal ids shown to users, fonts < 10 px, text contrast, layout shift (CLS), DOM churn, replaying animations.
> Layout, colours, spacing and components were kept — only defects, noise and inconsistencies were changed.

| Audit result | Before | After |
|:---|---:|---:|
| Pages showing emoji / glyph "icons" (of 29 audited) | 7 | **0** |
| Pages showing internal ids (`m_b1_1`, `badge_b1_sig_01_1795596050`) | 3 | **0** |
| Console errors / page-level horizontal overflow | 0 / 0 | 0 / 0 |
| Text < 10 px | 14 spots (Guardian dashboard) | **0** |
| White-on-green / white-on-amber elements below WCAG AA (≈2.1–2.5 : 1) | 9 places in the views | **0** |
| Sidebar rebuilt on every navigation | yes | **no (patched in place)** |

### S2-1. Emoji used as icons
- **Previous logic:** hundreds of 🥇 🏆 📅 ⏰ ✏️ 🎓 ⚖️ 🚀 ⚡ 👥 ✨ 📥 ✓ ⚠ ★ ⚑ characters embedded in 6,000-line view files. They render in different fonts on every OS, in colour, next to the line icons.
- **New logic:** [`iconize_html`](starapp/views_common.py) swaps them for the existing SVG icon set (`get_icon`, plus new `star` and `flag`) in the finished markup
  of every page and modal. It only touches **text nodes** (quote-aware tag matching, so `=>` inside an `onclick` is safe; `<option>`, `<textarea>`, `<title>`, `<script>`, `<style>` are skipped).
- **Reason:** one consistent, professional icon language in both portals, and future views are covered automatically.

### S2-2. Internal ids shown to people
- **Previous logic:** the activity feeds and the dashboard header printed `Mapped m_b1_1 to …`, `Assigned Reviewer: m_b2_4`, `badge_b1_architecture`, `Completed badge_b1_sig_01_1795596050 evaluation`, `ID: m_b1_1`, and a hard-coded "Lead Mentor: Arjun Mehta".
- **New logic:** [`humanize_internal_ids`](starapp/views_common.py) renders people by name and badges by code; the "Target Badge" column shows the badge code; the dashboard header shows *Band · Track · Batch · Mentor* from the real profile; leaderboard rows show band + track instead of the id. Activity feeds are also paginated (25 / 50 per page).
- **Reason:** ids are meaningless to users and look unfinished.

### S2-3. Cadet cohort counted the administrators
- **Previous logic:** `get_all_cosmonauts()` returned every user in band B1–B6 except `guardian_1`, so the **`admin` account (B6) was counted as a cadet** in the leaderboard, "Enrolled Cadets" and appraisal counts.
- **New logic:** guardians / admins are excluded unless they also hold the cosmonaut role.
- **Reason:** correct headcounts and ranks.

### S2-4. Text colours that fail WCAG AA
- **Previous logic:** green / amber / red / blue / indigo / cyan *text* (2.1–3.8 : 1 on white) and white text on green or amber (2.1–2.5 : 1), e.g. the "FLIGHT OFFICER" and "YOU" tags, "Badge Earned" buttons.
- **New logic:** text uses the 700-weight shades of the same hues (≥ 4.5 : 1, mostly 5–7 : 1); white-on-amber becomes dark brown, white-on-green uses the darker green. Fonts below 10 px were raised to 10 px.
- **Reason:** readability for everyone; the palette itself is unchanged.

### S2-5. Verbose and duplicated content (Cosmonaut / Reviewer pages)
- **Previous logic:** explanatory sub-titles under almost every heading ("Select any allocated badge card to open its full milestone page with outcomes…", "Your upcoming (1 cadet assignment) and completed (1 certified review) commitments across assigned curriculum badges", "Higher-band peer review workspace. Inspect, edit…", "Institutional evaluation rubric scores and performance breakdown"); two redundant status chips ("Active Cohort Commitments", "Certified & Finalized"); the **Badge Review Schedule** repeated the entire badge header (code, band, category, title, "Upcoming Review", status) inside every cadet card plus a boiler-plate "3-Day Window: Reviewer creates project, Cadet learns concepts"; five different ad-hoc button colours (green / blue gradients).
- **New logic:** sub-titles removed or shortened; headings simplified ("Cadet Evaluation Invitations", "Badge Approval Requests"); each cadet card is now *avatar + name + band/track + status* then *review window / submission deadline*, then the project brief and actions; all buttons use the shared `btn-metal` / `btn-secondary` styles.
- **Reason:** the Guardian pages show data, not instructions; less text, more signal. (Tests that pinned the old wording were updated to the new design.)

### S2-6. Rail cycle pill clipped
- **Previous logic:** the 72 px rail showed `C1-202` (cut off).
- **New logic:** shows `C1`; the full code appears when the rail expands.

### S2-7. Flicker — sidebar rebuilt on every click (root cause)
- **Previous logic:** [`bridge.js`](js/bridge.js) patched the sidebar in place only when `sidebarHtml` was *identical* to the previous one. The server renders the active link (`class="nav-link active"`) into that HTML, so it was different after **every navigation** and the whole `<aside>` was replaced with `outerHTML` (hover/scroll/transition state lost, visible blink on the rail). Measured: sidebar node replaced on 4 of 5 navigations.
- **New logic:** `_sidebarSignature()` ignores the active class; the element is replaced only on a real structural change (different links, badge counts, user, cycle). The highlight moves via the existing `_updateSidebarInPlace`.
- **Reason:** removes the visible flicker; the sidebar node now persists across navigation (verified) and DOM mutations per click dropped by about 25–50 %. Layout shift measured ≈ 0 on every page change (the only 0.15 was the Guardian "Learning" page re-introducing its sidebar).

### S2-8. Misc
- Offline bundle `js/starapp_bundle.js` rebuilt (29 modules) so the Pyodide fallback matches the new code.
- `.env.example` documents the new settings; `tests/run_tests.py` is the only supported way to run the suite.

---

## Verification summary (final)
- **190 automated tests pass** (`python tests/run_tests.py`, ~18 s, never touches `data/starapp.db`).
- Real-server load test on a 3,038-user database: 60 concurrent users, 420 requests, **0 errors, 66–74 req/s, p50 ≈ 0.6 s, ~180 MB**.
- Headless-Chrome audit of 87 page × width combinations: **0 console errors, 0 emoji, 0 internal ids, 0 page-level horizontal overflow**.
- First start of the server on `data/starapp.db` adds the 30 indexes (and `PRAGMA optimize` statistics) in place; no data is changed.
