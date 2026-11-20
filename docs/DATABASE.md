# DATABASE ARCHITECTURE AND SCHEMA AUDIT

> **Authoritative Target Database:** Persistent SQLite3 database (`data/starapp.db`)  
> **Schema Version:** 1.0.0

---

## 1. Physical Database Location
- **Original Location:** In-memory SQLite within Pyodide WebAssembly VFS, backed up to `starapp.db` in repository root and browser IndexedDB.
- **Target Location:** `data/starapp.db` directly managed on local disk by Python backend with WAL mode and `PRAGMA foreign_keys = ON`.

---

## 2. Table Catalog (32 Tables + 1 View)

| # | Table Name | Primary Key | Foreign Keys | Purpose |
|:--|:---|:---|:---|:---|
| 1 | `schema_version` | `version` | None | Tracks database schema migration versions |
| 2 | `users` | `id` | None | User accounts, credentials, roles (guardian, cosmonaut, reviewer) |
| 3 | `bands` | `id` | None | Band definitions (B1 to B6) |
| 4 | `tracks` | `id` | None | Learning tracks (Solutions Designer, AI Engineer, Systems Engineer) |
| 5 | `employees` | `id` | `band_id`, `track_id`, `manager_id`, `user_id` | 36 Indian corporate employees + CEO hierarchy |
| 6 | `powers` | `id` | None | Top-level competency categories |
| 7 | `capabilities` | `id` | `power_id` | Intermediate competencies |
| 8 | `skills` | `id` | `capability_id` | Granular skills |
| 9 | `badges` | `id` | `band_id`, `track_id`, `skill_id` | Badges authored by band & track |
| 10 | `badge_criteria` | `id` | `badge_id` | 5 assessment rubric criteria per badge |
| 11 | `badge_prerequisites` | `badge_id`, `prerequisite_id` | `badge_id`, `prerequisite_id` | Prerequisite dependency graph |
| 12 | `badge_review_requests` | `id` | `badge_id`, `reviewer_id`, `requested_by` | Review workflow requests |
| 13 | `badge_allotments` | `id` | `badge_id`, `employee_id`, `allotted_by` | Badge assignment to cadets |
| 14 | `submissions` | `id` | `allotment_id` | Cadet submissions (URLs, attempts, notes) |
| 15 | `evaluations` | `id` | `submission_id`, `evaluator_id` | Overall evaluations and decision |
| 16 | `evaluation_marks` | `id` | `evaluation_id`, `criteria_id` | Per-criterion scores (10 marks each) |
| 17 | `extension_requests` | `id` | `allotment_id`, `requested_by` | Deadline extension lifecycle |
| 18 | `announcements` | `id` | `created_by` | System & broadcast announcements |
| 19 | `announcement_reads` | `announcement_id`, `employee_id` | `announcement_id`, `employee_id` | Read receipts |
| 20 | `materials` | `id` | `track_id`, `band_id` | Learning resources & documents |
| 21 | `mentor_messages` | `id` | `sender_id`, `receiver_id` | Cadet-mentor direct communication |
| 22 | `audit_logs` | `id` | `user_id` | Security and workflow change tracking |
| 23 | `sessions` | `id` | `user_id` | Backend session persistence |
| 24-32 | *Lookup & auxiliary tables* | `id` | Various | Badges tags, attachments, notifications |

---

## 3. Database Integrity Constraints

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
```

### Critical Foreign Key Integrity Rules:
1. `employees.manager_id REFERENCES employees(id)` (self-referential hierarchy).
2. `badge_review_requests.reviewer_id REFERENCES employees(id)`.
3. `badge_allotments.employee_id REFERENCES employees(id)`.
4. `evaluation_marks.evaluation_id REFERENCES evaluations(id) ON DELETE CASCADE`.
5. `submissions.allotment_id REFERENCES badge_allotments(id) ON DELETE CASCADE`.
