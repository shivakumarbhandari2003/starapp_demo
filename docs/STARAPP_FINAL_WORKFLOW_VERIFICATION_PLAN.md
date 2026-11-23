# STARAPP — FINAL WORKFLOW VERIFICATION, DATABASE VALIDATION & GAP REMEDIATION PLAN

> **Document Version:** 1.0.0  
> **Target System:** StarApp Full-Stack Architecture (FastAPI + Vanilla JS Liquid Glass + Persistent SQLite3 WAL)  
> **Author:** Antigravity AI Engineering & Architecture Team  
> **Database:** `data/starapp.db` (Authoritative persistent SQLite3 with 34 tables)  
> **Verification Date:** 2026-11-22  

---

## 1. Executive Overview & Architectural Scope

This verification plan establishes the complete testing, inspection, validation, and gap remediation protocol for the end-to-end StarApp workflow:

```text
[GUARDIAN] Creates Badge Proposal (B1-B6)
       │
       ▼
[REVIEWER] Higher-Band Peer Review (Reviewer_Band > Badge_Band) ➔ Review/Edit/Approve
       │
       ▼
[GUARDIAN] Institutional Publication & Allocation (is_published=True, is_allocated=True)
       │
       ▼
[GUARDIAN] Competency Mapping (Band, Role, Badge, Cadets, Reviewer, 3-Day Window)
       │
       ├─────────────────────────────────┬─────────────────────────────────┐
       ▼                                 ▼                                 ▼
[REVIEWER] 3-Day Project Creation     [COSMONAUT] 3-Day Concept Study   [PERSISTENT DB]
- Opens Timeline                      - Studies Curriculum              - `band_mappings`
- Gemini AI Project Generator         - Reviews Objectives              - `badge_timelines`
- Releases to Mapped Cadets           - Prepares for Sprint             - `reviewer_project_prompts`
       │                                 │                                 │
       └────────────────┬────────────────┘                                 │
                        ▼                                                  │
[COSMONAUT] Deliverable Submission (Code, PDF, GitHub Repo)               │
                        │                                                  │
                        ▼                                                  │
[REVIEWER] Assessment Workspace (`c_assessments`) ➔ 50-Mark Rubric         │
                        │                                                  │
                        ▼                                                  │
[GUARDIAN] Final Assessment & Award Decision (Threshold ≥ 70% / 35 marks) │
                        │                                                  │
                        ▼                                                  │
[SYSTEM] Active Mapping Uncoupling (Cadet certified; mapping archived) ────┘
```

---

## 2. Requirement-by-Requirement Verification Checklist

### REQ-01: Persistent Database Storage Across All Entities
- **Expected Behavior:** Every lifecycle event, proposal, assignment, mapping, prompt, deliverable, score, and decision must be durably stored in SQLite3 (`data/starapp.db`). In-memory storage, `sessionStorage`, or `localStorage` must never be the single source of truth.
- **Current Implementation:** 34 SQLite tables with WAL mode and `PRAGMA foreign_keys = ON`. Storage managed through `starapp/storage.py`, `starapp/database.py`, and `backend/app/database/migrations.py`.
- **Relevant Frontend Files:** `js/bridge.js`, `js/api.js`.
- **Relevant Backend Files:** `starapp/storage.py`, `starapp/database.py`, `backend/app/database/connection.py`.
- **Relevant Database Tables:** `badges`, `band_mappings`, `badge_reviewer_assignments`, `badge_review_events`, `mapping_requests`, `badge_timelines`, `reviewer_project_prompts`, `project_submissions`, `assessment_marksheets`.
- **Existing Test Coverage:** `tests/test_sqlite_persistence.py`, `tests/test_backend_fullstack.py` (Test 1).
- **Verification Method:** Direct SQL query inspection, server restart test, foreign-key integrity check.
- **Identified Gap / Remediation Target:** Ensure `band_mappings.badge_id` column is always populated with the authoritative badge ID (not left empty when matching by title).

---

### REQ-02: Badge Review Requests & Role-Based Views
- **Expected Behavior:** Guardian creates badge proposal. System enforces `Reviewer_Band > Badge_Band`. Review request is stored in `badge_reviewer_assignments` and `badge_review_events`. Assigned Reviewer receives notification, inspects proposal, edits or adds remarks, and submits approval.
- **Current Implementation:** Handled in `starapp/app.py` (`preview_new_badge`, `create_badge`, `save_reviewed_badge`, `approve_submitted_badge`, `return_submitted_badge`), `starapp/views_guardian.py`, `starapp/views_cosmonaut.py`.
- **Relevant Frontend Files:** `starapp/views_guardian.py`, `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `backend/app/features/reviews/`, `starapp/app.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `badges`, `badge_reviewer_assignments`, `badge_review_events`, `notifications`.
- **Existing Test Coverage:** `tests/test_badge_creation_and_approval.py`, `tests/test_badge_review_workflow.py`.
- **Verification Method:** Multi-account session simulation: Guardian creates B1 badge -> Reviewer (B2) edits and approves -> Guardian checks status.

---

### REQ-03: Guardian Badge Publication & Segregation
- **Expected Behavior:** Reviewer approval transitions workflow status to `approved`. The badge remains unpublished until the Guardian explicitly clicks "Publish". Publishing sets `is_published=True`, `is_allocated=True`, records `published_at` and `published_by`.
- **Current Implementation:** `publish_badge` event in `starapp/app.py` (lines 1774–1840).
- **Relevant Frontend Files:** `starapp/views_guardian.py` (`render_guardian_badge_approval_queue`, `render_guardian_badge_allotment`).
- **Relevant Backend Files:** `backend/app/features/badges/router.py`, `starapp/app.py`.
- **Relevant Database Tables:** `badges`, `activity_events`, `notifications`.
- **Existing Test Coverage:** `tests/test_complete_badge_lifecycle_workflow.py` (Stage 4).
- **Verification Method:** Confirm unpublished badge is inaccessible to unmapped cosmonauts; verify publication timestamp and creator in SQLite.

---

### REQ-04: Badge Allotment & Per-Badge Dedicated Mapping
- **Expected Behavior:** Guardian "Badge Allotment" view must not display a global cross-band mapping dump. Every allocated badge card must render its own dedicated personnel mapping box containing the authorized higher-band Reviewer, review date window, and assigned cadet chips.
- **Current Implementation:** `render_guardian_badge_allotment` in `starapp/views_guardian.py` (lines 1480–1525). Dedicated mapping card embedded inside each badge item.
- **Relevant Frontend Files:** `starapp/views_guardian.py`.
- **Relevant Backend Files:** `starapp/app.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `badges`, `band_mappings`, `badge_timelines`.
- **Existing Test Coverage:** `tests/test_complete_badge_lifecycle_workflow.py` (test 2).
- **Verification Method:** Inspect HTML output of `render_guardian_badge_allotment` for badges in B1 and B2; confirm mapping cards are distinct and per-badge.

---

### REQ-05: Band-Specific Mapping & Data Scoping
- **Expected Behavior:** Mapping table at the bottom of Badge Allotment must filter mappings strictly by the bands and badges active in the current workspace. Mapping changes for Badge A must never affect Badge B.
- **Current Implementation:** `filtered_mappings` in `render_guardian_badge_allotment` (lines 1667–1679).
- **Relevant Frontend Files:** `starapp/views_guardian.py`.
- **Relevant Backend Files:** `starapp/storage.py`.
- **Relevant Database Tables:** `band_mappings`, `bands`.
- **Existing Test Coverage:** `tests/test_new_workflow_features.py`.
- **Verification Method:** Create 2 mappings for B1 badges and 1 mapping for B2 badge; filter allotment by B1; verify B2 does not appear.

---

### REQ-06: Published Badge Visibility (Role Isolation)
- **Expected Behavior:** A published badge must only appear to its assigned Reviewer in "Badge Reviews" (`c_schedule`) and to its mapped Cadets in "Badges" (`c_submission`) and "Roadmap" (`c_roadmap`). Unmapped cadets must see it as locked.
- **Current Implementation:** Handled in `starapp/views_cosmonaut.py` (`render_reviewer_badge_schedule`, `render_cosmonaut_submission_workspace`, `render_gamified_roadmap`).
- **Relevant Frontend Files:** `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `starapp/app.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `badges`, `band_mappings`, `badge_timelines`.
- **Existing Test Coverage:** `tests/test_cosmonaut_badges_view.py`.
- **Verification Method:** Query badge list for mapped Cadet vs unmapped Cadet; assert strictly mapped badges are active.

---

### REQ-07: Independent 3-Day Timelines for Reviewers and Cosmonauts
- **Expected Behavior:** Upon badge mapping, a 3-day review window is established. The Reviewer gets 3 days for project authoring/preparation, and the Cosmonaut gets 3 days for concept learning before sprint kickoff.
- **Current Implementation:** `badge_timelines` table with `review_window_json`, `learning_start_date`, `learning_end_date`, `project_start_date`, `project_end_date`. Modals `render_reviewer_badge_timeline_modal` and stepper `render_timeline_stepper`.
- **Relevant Frontend Files:** `starapp/views_guardian.py`, `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `starapp/app.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `badge_timelines`.
- **Existing Test Coverage:** `tests/test_complete_badge_lifecycle_workflow.py`.
- **Verification Method:** Verify timeline stepper rendering, persistence across server restart, and modal display.

---

### REQ-08: Reviewer AI Project Creation via Gemini & Deterministic Fallback Engine
- **Expected Behavior:** In "Badge Reviews", the Reviewer clicks "Create Project (AI)". The system invokes the Gemini API (`/integrations/gemini/generate-project`) or the deterministic fallback generator to produce a structured specification tailored to the badge.
- **Current Implementation:** `generate_reviewer_project_spec` in `starapp/badge_generator.py`, `backend/app/integrations/gemini/router.py`, `render_reviewer_project_creator_modal` in `starapp/views_cosmonaut.py`.
- **Relevant Frontend Files:** `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `backend/app/integrations/gemini/router.py`, `starapp/badge_generator.py`.
- **Relevant Database Tables:** `reviewer_project_prompts`.
- **Existing Test Coverage:** `tests/test_complete_badge_lifecycle_workflow.py`.
- **Verification Method:** Execute project generator; verify live API behavior (or report BLOCKED if sandbox network blocks outbound DNS); verify fallback produces complete structured JSON.

---

### REQ-09: Reviewer Project Editing and 1:N Scoped Delivery to Mapped Cadets
- **Expected Behavior:** Reviewer inspects and edits the generated scenario, requirements, and deliverables checklist. Clicking "Send Project to Mapped Cadets" saves `ReviewerProjectPrompt` in SQLite and delivers notifications strictly to cadets mapped to that specific reviewer (1:N isolation).
- **Current Implementation:** `send_reviewer_project` action in `starapp/app.py` (lines 2043–2095), `store.save_reviewer_project_prompt` in `starapp/storage.py`.
- **Relevant Frontend Files:** `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `starapp/app.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `reviewer_project_prompts`, `notifications`.
- **Existing Test Coverage:** `tests/test_complete_badge_lifecycle_workflow.py`.
- **Verification Method:** Map Reviewer 1 to Cadet 1 & 2; Map Reviewer 2 to Cadet 3 & 4. Reviewer 1 sends project. Verify Cadet 1 & 2 receive prompt; verify Cadet 3 & 4 do NOT receive Reviewer 1's prompt.

---

### REQ-10: Cosmonaut Project Submission Portal (Code, PDF, GitHub Repo)
- **Expected Behavior:** In "Badges" (`c_submission`), cadet sees the official assigned project specification banner. Below it is the Submission Portal accepting 3 distinct deliverables: Source Code (`.py`, `.sql`, `.zip`), Architecture PDF Report (`.pdf`), and GitHub Repository URL.
- **Current Implementation:** `render_cosmonaut_submission_workspace` in `starapp/views_cosmonaut.py` (lines 1833–2030), `submit_project_deliverable` / `execute_submit_project` in `starapp/app.py`.
- **Relevant Frontend Files:** `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `starapp/app.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `project_submissions`, `badge_timelines`, `activity_events`, `notifications`.
- **Existing Test Coverage:** `tests/test_submission_and_attempt_preservation.py`.
- **Verification Method:** Submit deliverable; verify `code_name`, `code_payload`, `pdf_name`, `pdf_payload`, and `github_url` in SQLite.

---

### REQ-11: File Storage Persistence & Integrity Across Application Restarts
- **Expected Behavior:** Submitted deliverable metadata and payloads must persist in SQLite. Restarting the backend server must not lose files, corrupted data, or reset attempt numbers.
- **Current Implementation:** Stored in `project_submissions` table in `data/starapp.db`.
- **Relevant Frontend Files:** `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `starapp/storage.py`, `backend/app/database/connection.py`.
- **Relevant Database Tables:** `project_submissions`.
- **Existing Test Coverage:** `tests/test_backend_fullstack.py` (Test 9).
- **Verification Method:** Submit file, simulate backend restart by creating a new `DataStore` connection, retrieve file and assert exact match.

---

### REQ-12: Reviewer Assessment Sidebar & Worklist (`c_assessments`)
- **Expected Behavior:** Reviewer sidebar "Assessments" tab (`c_assessments`) displays submissions awaiting review. Clicking into a submission opens `c_assessment_detail` featuring the 3-deliverable viewer (PDF iframe, Code view, GitHub link).
- **Current Implementation:** `render_reviewer_assessment_queue` and `render_reviewer_assessment_detail` in `starapp/views_cosmonaut.py`.
- **Relevant Frontend Files:** `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `starapp/app.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `project_submissions`, `assessment_marksheets`.
- **Existing Test Coverage:** `tests/test_complete_badge_lifecycle_workflow.py`.
- **Verification Method:** Verify submission appears in reviewer queue; verify viewer tabs render code, PDF, and GitHub repository link.

---

### REQ-13: 50-Mark Rubric Scoring, Feedback, and Remarks Validation
- **Expected Behavior:** Reviewer scores 5 criteria (0–10 marks each: Business Understanding, Architecture Report, Technical Knowledge, Presentation, Q&A; Total: 0–50 marks). Scores are validated; out-of-range marks rejected. Marksheet is saved with `assessor_role="reviewer"`.
- **Current Implementation:** `execute_submit_evaluation` in `starapp/app.py`, `validate_rubric_scores` in `starapp/assessment.py`.
- **Relevant Frontend Files:** `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `starapp/app.py`, `starapp/assessment.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `assessment_marksheets`.
- **Existing Test Coverage:** `tests/test_assessment_and_analytics.py`.
- **Verification Method:** Submit valid score (e.g. 42/50); submit invalid score (e.g. 15/10) and verify error rejection.

---

### REQ-14: Marksheet Synchronization Across Cosmonaut and Guardian
- **Expected Behavior:** Reviewer-submitted marksheet is immediately viewable in Cosmonaut's "Assessment Marksheet" (`c_results`) and in Guardian's review queue (`g_reviews`).
- **Current Implementation:** `render_cosmonaut_results` in `starapp/views_cosmonaut.py`, `render_guardian_review_queue` and `render_guardian_review_detail` in `starapp/views_guardian.py`.
- **Relevant Frontend Files:** `starapp/views_cosmonaut.py`, `starapp/views_guardian.py`.
- **Relevant Backend Files:** `starapp/app.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `assessment_marksheets`, `project_submissions`.
- **Existing Test Coverage:** `tests/test_complete_badge_lifecycle_workflow.py`.
- **Verification Method:** Inspect HTML outputs in `c_results` and `g_reviews` for the evaluated cadet; verify identical marks and remarks.

---

### REQ-15: Guardian Final Award Decision & Passing Threshold Enforcement
- **Expected Behavior:** Guardian conducts final evaluation. If total score $\ge 35/50$ (70%), badge is awarded (`decision="approve"`, `status="completed"`, `actual_award_date` recorded). If $< 35/50$, status becomes `retake_required` and attempt history is preserved.
- **Current Implementation:** `execute_submit_evaluation` (guardian branch) in `starapp/app.py` (lines 2280–2350).
- **Relevant Frontend Files:** `starapp/views_guardian.py`.
- **Relevant Backend Files:** `starapp/app.py`, `starapp/storage.py`.
- **Relevant Database Tables:** `assessment_marksheets`, `project_submissions`, `badge_timelines`.
- **Existing Test Coverage:** `tests/test_complete_badge_lifecycle_workflow.py` (Stages 8 & 9).
- **Verification Method:** Test both branches: score 30/50 (retake) and score 42.5/50 (award).

---

### REQ-16: Reviewer-Cosmonaut Mapping Closure / Uncoupling
- **Expected Behavior:** When the badge is officially awarded, the active mapping between that Reviewer and that Cosmonaut for that specific badge is uncoupled (`uncoupled_cadets`, `completed_cosmonauts`). The cadet moves to "Completed & Certified Reviews" and cannot receive duplicate submissions for that badge. Other cadets and other badges remain active.
- **Current Implementation:** `uncouple_cadet_badge_mapping` in `starapp/storage.py` (lines 922–944), called inside `execute_submit_evaluation` in `starapp/app.py`.
- **Relevant Frontend Files:** `starapp/views_cosmonaut.py`.
- **Relevant Backend Files:** `starapp/storage.py`, `starapp/app.py`.
- **Relevant Database Tables:** `band_mappings`, `badge_timelines`.
- **Existing Test Coverage:** `tests/test_complete_badge_lifecycle_workflow.py` (Stage 9 & test 2).
- **Verification Method:** Award Badge A to Cadet 1; verify Cadet 1 is uncoupled for Badge A; verify Cadet 2 remains active for Badge A; verify Cadet 1 remains active for Badge B.

---

### REQ-17: Role-Based Data Isolation & Permission Boundaries
- **Expected Behavior:** Backend RBAC prevents privilege escalation: Cadets cannot view other cadets' dossiers or alter scores; Reviewers cannot evaluate unmapped cadets or award badges; Guardians cannot publish unapproved badges.
- **Current Implementation:** RBAC permissions in `backend/app/core/permissions.py`, checks in `starapp/app.py`.
- **Relevant Frontend Files:** `starapp/views_common.py`.
- **Relevant Backend Files:** `backend/app/core/permissions.py`, `starapp/app.py`.
- **Relevant Database Tables:** `permissions`, `role_permissions`, `user_role_assignments`.
- **Existing Test Coverage:** `tests/test_scenarios_a_to_h.py` (Scenario H).
- **Verification Method:** Attempt illegal state mutations and unauthorized API requests; verify rejection with HTTP 403 / error flash.

---

### REQ-18: Full End-to-End Workflow Verification Across Multi-User Sessions
- **Expected Behavior:** Execute complete workflow with 1 Guardian (`guardian_1`), 2 Reviewers (`m_b2_1`, `m_b3_2`), 4 Cosmonauts (`cosmo_1`, `m_b1_1`, `m_b1_3`, `m_b1_4`), 2 badges in Band B1 (`badge_b1_signals`, `b1_dat_01`), verifying all 9 stages in sequence.
- **Current Implementation:** Validated via automated test suite and live session dispatcher.
- **Relevant Files:** `tests/test_complete_badge_lifecycle_workflow.py`.
- **Verification Method:** Author dedicated multi-user end-to-end integration test suite and execute with full assertion logging.

---

## 3. Database Relationship & Integrity Audit Matrix

| Entity / Table | Primary Key | Foreign Keys | Status Fields | Timestamps | Persistence Mechanism | Retrievable on Restart |
|:---|:---|:---|:---|:---|:---|:---:|
| `users` | `id` | None | `is_active` | `created_at` | SQLite `users` table | YES |
| `badges` | `id` | `target_band`, `creator_id`, `assigned_reviewer_id` | `workflow_status`, `is_published`, `is_allocated` | `created_at`, `updated_at`, `published_at` | SQLite `badges` table | YES |
| `badge_reviewer_assignments` | `id` | `badge_id`, `reviewer_id` | `status` | `assigned_at`, `review_due_at`, `decided_at` | SQLite table | YES |
| `badge_review_events` | `id` | `badge_id`, `actor_id` | `previous_status`, `new_status` | `timestamp` | SQLite table | YES |
| `band_mappings` | `id` | `band` | `status` | `created_at` | SQLite `band_mappings` (JSON + columns) | YES |
| `badge_timelines` | `(badge_id, cosmonaut_id)` | `badge_id`, `cosmonaut_id` | `status` | `assignment_date`, `publication_date`, `actual_award_date` | SQLite composite PK | YES |
| `reviewer_project_prompts` | `id` | `reviewer_id` | `status` | `created_at`, `sent_at` | SQLite table | YES |
| `project_submissions` | `id` | `badge_id`, `cosmonaut_id` | `status` | `submitted_at` | SQLite table | YES |
| `assessment_marksheets` | `id` | `submission_id`, `badge_id`, `cosmonaut_id`, `reviewer_id` | `decision`, `assessor_role` | `reviewed_at` | SQLite table | YES |
| `notifications` | `id` | `user_id` | `is_read` | `created_at` | SQLite table | YES |

---

## 4. Execution Protocol & Verification Milestones

1. **Phase 1 Complete:** Deliver this comprehensive verification plan (`docs/STARAPP_FINAL_WORKFLOW_VERIFICATION_PLAN.md`).
2. **Phase 2 & 13 Database Audit:** Run integrity checks, verify foreign keys, inspect SQLite data persistence across simulated restarts.
3. **Phase 4 & 5 Per-Badge Mapping Hardening:** Ensure `band_mappings.badge_id` column is always populated on save; verify per-badge display isolation.
4. **Phase 7 Gemini API Audit:** Verify live API vs deterministic fallback; accurately document sandbox DNS constraint.
5. **Phase 8-11 Deliverable & Uncoupling Audit:** Verify triple deliverable storage (PDF, Code, GitHub URL), 50-mark scorecard calculation, and uncoupling of earned mappings.
6. **Phase 14-16 Multi-User Verification & Regression Execution:** Run 1 Guardian, 2 Reviewers, 4 Cosmonauts, 2 Badges across B1 and B2; execute all 123+ automated tests.
7. **Phase 17 & 18 Deliverables:** Author `docs/STARAPP_FINAL_END_TO_END_VERIFICATION_REPORT.md` and complete the Final Acceptance Matrix with concrete evidence.
