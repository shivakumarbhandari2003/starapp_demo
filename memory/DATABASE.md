# Database (`data/starapp.db`)

SQLite 3 · WAL · `foreign_keys=ON` · `busy_timeout=5000`. **38 tables + 1 view (`employees`)** · integrity `ok` · 0 FK violations.
`schema_version` table tracks migrations (`backend/app/database/migrations.py`). The authoritative DDL lives in `starapp/database.py`
(creation + `PERFORMANCE_INDEXES`). A visual ER diagram is in `ER diagram/` and `Star Registry Schema.html`.

> No tables or columns were added/removed in Stage 1/2/3. The only physical change is **30 indexes** added in place on first start (idempotent). Stage 3 only added **JSON keys** (below).
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
| `badges` (11) | the milestone | `workflow_status` (`pending_review/approved/returned`), `is_published`, `is_allocated`, `target_band`, `passing_percentage` (default 70), `learning_outcomes_json`, `learning_topics_json`, `prompt_json`, `assigned_reviewer_id`, `assigned_cosmonaut_ids_json`, `cycle_id` |
| `badge_powers`, `badge_capabilities`, `badge_skills` | taxonomy tags per badge (+ custom flags) | |
| `custom_capabilities`, `custom_skills` | guardian-added taxonomy | |
| `badge_prerequisites` (0) | roadmap locking | |
| `learning_materials` (2) | PDFs/YouTube per badge/topic | `url_or_data` |
| `badge_reviewer_assignments` (11) | badge → reviewer for approval | `status` pending/approved/returned |
| `badge_review_events` (21) | audit trail of approvals | unique ids (`created_for_review`, `approved`, `returned`, `created_and_submitted`) |
| `badge_reviewer_qualifications` (29) | reviewer eligibility band range | |

### Mapping, allotment, delivery
| Table | Purpose | Notes |
|:---|:---|:---|
| `band_mappings` (10) | Guardian's cadets+reviewers↔badge pairing | `data_json` holds `cosmonauts[]`, `reviewers[]` (first = owner), `badge_id`, `review_dates`; Edit Badge rewrites `cosmonauts[]` per reviewer |
| `mapping_requests` (11) | invitation to reviewers | `status` pending/accepted/rejected; `data_json` keys added in Stage 3: **`expires_at`** (sent_at + 24 h), **`expired`** (true when the window ran out), **`responded_at`**; `cosmonaut_ids` is kept in sync by Edit Badge |
| `badge_timelines` (35) | per cadet+badge calendar | PK (`badge_id`,`cosmonaut_id`); `status` active/reviewer_assessed/completed/retake_required; `reviewer_id`, `submission_deadline`, `actual_award_date`, `review_window_json`; Edit Badge creates/updates these (reviewer + window) and deletes the row of a removed cosmonaut (`store.delete_timeline`) |
| `reviewer_project_prompts` (8+) | the project a reviewer sent (**Heading = `title`, Content = `description`**; `deliverables_json`/`outcomes_json`/`requirements_text` are legacy, folded into the content on display) AND the cosmonaut's project *request* | `cosmonaut_ids_json`, `status` = `requested` (id `projreq_<badge>_<cosmo>`) / `fulfilled` / `draft` / `sent` / `released` (id `proj_<badge>_<reviewer>_<ms>_<id>`, one record per send) |
| `project_submissions` (24) | attempts | `attempt_number`, `status`, `pdf_payload`/`payload`/`code_payload` (**base64 blobs — lazy loaded**), `github_url` |
| `assessment_marksheets` (43) | graded attempts | 5 criteria columns, `total_marks`, `percentage`, `assessor_role`, `decision` |
| `deadline_extensions` (3) | extension requests | `status` pending/approved/rejected |
| `announcements` (1), `announcement_recipients` (4), `announcement_read_receipts` (1) | broadcast + read state | |

### Cycles & appraisal
| Table | Purpose | Notes |
|:---|:---|:---|
| `performance_cycles` (2) | 6-month cycles | `status`, `hike_policy_json`, `cloned_from_cycle_id` |
| `cycle_enrollments` (76) | who is in which cycle with which role/band/salary | |
| `cycle_performance_appraisals` (36) | persisted appraisal per cadet per cycle | scores, tier, hike %, promotion, `details_json`, `status` (`finalized`) |

### Feeds
| Table | Purpose |
|:---|:---|
| `activity_events` (198) | audit/activity feed (event_type, actor, cadet, badge, summary, cycle) |
| `notifications` (26) | per-user notifications (`is_read`, `link_section`) |

Most workflow tables carry **`cycle_id`**; views filter by the selected cycle.

## 2. Gotchas

1. **Cascades:** many children `ON DELETE CASCADE` from `users`/`performance_cycles`. Never `INSERT OR REPLACE` parents (use UPSERT).
2. **Blobs in SQLite:** submissions and materials store base64 in the DB. It is lazy-loaded in memory, but the file grows; moving to file/object storage is a backlog item.
3. **JSON columns** (`*_json`, `data_json`) are parsed in `models.py`/`storage.py`; keep them valid JSON.
4. **Passwords** in the seed are plaintext `123456789` — demo only. REST login uses `bcrypt` when hashes are present (`core/security.py`).
5. **Tests wipe the DB they point at** (`reset_to_seed()`); use `tests/run_tests.py` (temp copy).
6. `schema_version.installed_at` is written once (`INSERT OR IGNORE`); startup no longer re-stamps it, so launching the app/tests/packer leaves the tracked DB byte-identical.
7. `PRAGMA data_version` fingerprinting means *any* external writer (another tool, a script) is picked up automatically on the next read — but never edit the DB while tests/servers are mid-write.
7. Tracked binary: coordinate who commits `data/starapp.db` (see README §2). Backups/other files in `data/`: `Chemistry Syllabus.pdf`, `chemistry_syllabus.pdf` (placeholder PDF used by demo mode).

## 3. Useful queries

```sql
-- badge pipeline
SELECT workflow_status, COUNT(*) FROM badges GROUP BY 1;
-- who is stuck waiting for the guardian's final decision
SELECT cosmonaut_id, badge_id FROM project_submissions WHERE status='reviewer_assessed';
-- earned badges per cadet in a cycle
SELECT cosmonaut_id, COUNT(*) FROM badge_timelines WHERE status='completed' AND cycle_id='cycle_1' GROUP BY 1;
```
