# Database (`data/starapp.db`)

SQLite 3 · WAL · `foreign_keys=ON` · `busy_timeout=5000`. **38 tables + 1 view (`employees`)** · integrity `ok` · 0 FK violations (checked read-only on 2026-11-28; the row counts below are the committed DB at git `HEAD` `ccc3156` — running the app/e2e scripts changes the working copy, restore with `git checkout data/starapp.db`). **All stored timestamps are UTC; the UI shows IST.**
`schema_version` table tracks migrations (`backend/app/database/migrations.py`). The authoritative DDL lives in `starapp/database.py`
(creation + `PERFORMANCE_INDEXES`). A visual ER diagram is in `ER diagram/` and `Star Registry Schema.html`.

> No tables or columns were added/removed in Stage 1/2/3 or the 2026-11-27/28 Cosmonaut/Reviewer/Guardian workflow passes. The only physical change is **30 indexes** added in place on first start (idempotent). Later work only added **JSON keys** and new **decision values** (below).
> If you do change the schema: update DDL + migrations + seed + this file + the change log, and rebuild the offline bundle.

## 1. Tables by domain (rows in the committed DB)

### Identity & access
| Table | Purpose | Key columns / notes |
|:---|:---|:---|
| `users` (38) | every person (cadets, reviewers, guardians) | `id` (`m_b1_1`, `guardian_1`, `admin`), `email`/`username`, `band`, `track_code`, `primary_role`, `password` (**plaintext in seed**), `is_demo`, `status` |
| `employees` (view) | read model over users for the legacy API | |
| `system_roles` (4) | `guardian`, `badge_reviewer`, `project_reviewer`, `cosmonaut` | |
| `user_role_assignments` (98) | who holds which role | cascade from `users` |
| `permissions` (6), `role_permissions` (7) | coarse RBAC matrix | |
| `user_band_memberships` (38) | user ↔ band/track | |
| `employee_reporting` (35) | manager ↔ employee with bands | |
| `user_sessions` (0) | REST login sessions (cookie `starapp_session`) | `expires_at`, `last_active_at` (touched ≤ every 5 min) |
| `cosmonaut_profiles` (1) | batch name, assigned guardian, skills/certs JSON | |
| `bands` (7), `learning_tracks` (4) | taxonomy | B1…B6 + CEO; SD/AIE/SE/EXEC |

### Curriculum
| Table | Purpose | Notes |
|:---|:---|:---|
| `badges` (13) | the milestone | `workflow_status` (`pending_review/approved/returned`), `is_published`, `is_allocated`, `target_band`, `passing_percentage` (default 70), `learning_outcomes_json`, `learning_topics_json`, `prompt_json`, `assigned_reviewer_id`, `assigned_cosmonaut_ids_json`, `cycle_id` |
| `badge_powers`, `badge_capabilities`, `badge_skills` | taxonomy tags per badge (+ custom flags) | |
| `custom_capabilities`, `custom_skills` | guardian-added taxonomy | |
| `badge_prerequisites` (0) | roadmap locking | |
| `learning_materials` (2) | PDFs/YouTube per badge/topic | `url_or_data` |
| `badge_reviewer_assignments` (14) | badge → reviewer for approval | `status` pending/approved/returned/cancelled/expired; `review_due_at` = assigned + 48 h |
| `badge_review_events` (27) | audit trail of approvals | unique ids (`created_for_review`, `approved`, `returned`, `created_and_submitted`) |
| `badge_reviewer_qualifications` (29) | reviewer eligibility band range | |

### Mapping, allotment, delivery
| Table | Purpose | Notes |
|:---|:---|:---|
| `band_mappings` (12) | Guardian's cadets+reviewers↔badge pairing | `data_json` holds `cosmonauts[]`, `reviewers[]` (first = owner), `badge_id`, `review_dates`; Edit Badge rewrites `cosmonauts[]` per reviewer. **Earning keys:** `completed_cosmonauts[]` and `uncoupled_cadets[]` (each earned cosmonaut is added by `store.uncouple_cadet_badge_mapping`, removed again by `recouple_cadet_badge_mapping` on a revoke) and **`status`** (`completed` only when EVERY cosmonaut in `cosmonauts[]` is in `completed_cosmonauts`; `active` again after a revoke) |
| `mapping_requests` (14) | invitation to reviewers (id `req_{band}_{badge_id}_{reviewer_id}`) | `status` pending/accepted/rejected; `data_json` keys added in Stage 3: **`expires_at`** (sent_at + 24 h), **`expired`** (true when the window ran out), **`responded_at`**; `cosmonaut_ids` is kept in sync by Edit Badge |
| `badge_timelines` (40) | per cadet+badge calendar | PK (`badge_id`,`cosmonaut_id`); `status` active/reviewer_assessed/completed/retake_required (a revoke sets it back to `reviewer_assessed` and clears `actual_award_date`); `reviewer_id`, `submission_deadline`, `actual_award_date`, `review_window_json`; Edit Badge creates/updates these (reviewer + window) and deletes the row of a removed cosmonaut (`store.delete_timeline`) |
| `reviewer_project_prompts` (9) | the project a reviewer sent (**Heading = `title`, Content = `description`**; `deliverables_json`/`outcomes_json`/`requirements_text` are legacy, folded into the content on display) AND the cosmonaut's project *request* | `cosmonaut_ids_json`, `status` = `requested` (id `projreq_<badge>_<cosmo>`) / `fulfilled` / `draft` / `sent` / `released` (id `proj_<badge>_<reviewer>_<ms>_<id>`, one record per send) |
| `project_submissions` (25) | attempts | `attempt_number`, `status` (`pending/draft → reviewer_assessed → approved | retake_required`; `resubmission_requested` also read as final), `pdf_payload`/`payload`/`code_payload` (**base64 blobs — lazy loaded**), `github_url` |
| `assessment_marksheets` (45) | graded attempts | 5 criteria columns, `total_marks`, `percentage`, `assessor_role` (`reviewer`/`guardian`), `decision`. **Decision values:** reviewer rows `recommend_approve` / `recommend_resubmit` / `recommend_reject` (the reviewer's recommendation; legacy rows hold `reviewer_assessed`, `approve`, `request_revision`); Guardian rows `approve` (badge earned; legacy `approved` also read) / `resubmission_requested` / `rejected`. Ids `asm_rev_<sub>_<attempt>` and `asm_g_<sub>_<attempt>`: one reviewer row per attempt (marks are locked once saved); **rows are deleted only by a Guardian revoke** (`store.delete_assessment`, latest attempt only) |
| `deadline_extensions` (3) | extension requests | `status` pending/approved/rejected |
| `announcements` (1), `announcement_recipients` (4), `announcement_read_receipts` (1) | broadcast + read state | **The only runtime table with `ON DELETE CASCADE` children** (the two child tables). `save_announcement` / the bulk save use `INSERT … ON CONFLICT(id) DO UPDATE` since 2026-11-28 (`INSERT OR REPLACE` used to delete the parent first and wipe recipients + read receipts) |

### Cycles & appraisal
| Table | Purpose | Notes |
|:---|:---|:---|
| `performance_cycles` (2) | 6-month cycles | `status`, `hike_policy_json`, `cloned_from_cycle_id` |
| `cycle_enrollments` (76) | who is in which cycle with which role/band/salary | |
| `cycle_performance_appraisals` (36) | persisted appraisal per cadet per cycle | scores, tier, hike %, promotion, `details_json`, `status` (`finalized`) |

### Feeds
| Table | Purpose |
|:---|:---|
| `activity_events` (227) | audit/activity feed (event_type, actor, cadet, badge, summary, cycle) |
| `notifications` (51) | per-user notifications (`is_read`, `link_section`) |

Most workflow tables carry **`cycle_id`**; views filter by the selected cycle.

## 2. Gotchas

1. **Cascades:** many children `ON DELETE CASCADE`. Parents with cascade children (verified with `PRAGMA foreign_key_list`): `users`, `performance_cycles` (enrollments, appraisals), `badges` (powers/capabilities/skills/prerequisites/review events/reviewer assignments/timelines), `announcements` (recipients, read receipts), `system_roles`, `permissions`. Never `INSERT OR REPLACE` these parents (use UPSERT). The other tables written at runtime with `OR REPLACE` (`cosmonaut_profiles`, `cycle_enrollments`, `cycle_performance_appraisals`, `badge_powers/capabilities/skills`, `badge_timelines`, `assessment_marksheets`, `learning_materials`, `deadline_extensions`, `activity_events`, `notifications`, `band_mappings`, `mapping_requests`, `reviewer_project_prompts`) have no child tables. `migrate_from_dict` (seed / legacy import) still uses `OR REPLACE` for parents but only runs on emptied tables.
2. **Blobs in SQLite:** submissions and materials store base64 in the DB. It is lazy-loaded in memory, but the file grows; moving to file/object storage is a backlog item.
3. **JSON columns** (`*_json`, `data_json`) are parsed in `models.py`/`storage.py`; keep them valid JSON.
4. **Passwords** in the seed are plaintext `123456789` — demo only. REST login uses `bcrypt` when hashes are present (`core/security.py`).
5. **Tests wipe the DB they point at** (`reset_to_seed()`); use `tests/run_tests.py` (temp copy).
6. `schema_version.installed_at` is written once (`INSERT OR IGNORE`); startup no longer re-stamps it, so launching the app/tests/packer leaves the tracked DB byte-identical.
7. `PRAGMA data_version` fingerprinting means *any* external writer (another tool, a script) is picked up automatically on the next read — but never edit the DB while tests/servers are mid-write.
8. Tracked binary: coordinate who commits `data/starapp.db` (see README §2). Backups/other files in `data/`: `Chemistry Syllabus.pdf`, `chemistry_syllabus.pdf` (placeholder PDF used by demo mode).

## 3. Useful queries

```sql
-- badge pipeline
SELECT workflow_status, COUNT(*) FROM badges GROUP BY 1;
-- who is stuck waiting for the guardian's final decision
SELECT cosmonaut_id, badge_id FROM project_submissions WHERE status='reviewer_assessed';
-- earned badges per cadet in a cycle
SELECT cosmonaut_id, COUNT(*) FROM badge_timelines WHERE status='completed' AND cycle_id='cycle_1' GROUP BY 1;
-- the reviewer's recommendation vs the Guardian's decision per attempt
SELECT submission_id, assessor_role, decision, total_marks FROM assessment_marksheets ORDER BY submission_id, assessor_role;
```
