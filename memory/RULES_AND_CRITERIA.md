# Rules & Criteria (business + technical invariants)

> These are **non-negotiable**. Each rule lists *where it is enforced* so you can change it in one place and update its test.
> "UI hides it" is never enforcement: the server (controller / DB layer) must reject the violating call.

## 1. Bands & reviewer eligibility

| Rule | Detail | Enforced in |
|:---|:---|:---|
| **Reviewer_Band > Badge_Band** (strict) | B1 badges ← B2…B6 · B2 ← B3…B6 · B3 ← B4…B6 · B4 ← B5,B6 · B5 ← B6 · **B6 badges: no peer review** (only Guardians/Executive oversee). Never peer review inside the same band. | `backend/app/core/permissions.py::verify_reviewer_eligibility`, `starapp/database.py` (`verify_reviewer_eligibility`, `authorize_badge_decision`), `send_mapping_requests` in `starapp/app.py` |
| Cadets are mapped only to badges of **their own band** | active users of the badge band only | `send_mapping_requests` |
| A badge may be mapped only when `workflow_status == "approved"` | else `ActionDenied` | `send_mapping_requests` |
| Nobody reviews a badge they authored | | `authorize_badge_decision` |
| Band order | `B1 < B2 < … < B6` (`BAND_HIERARCHY`; CEO is outside the peer-review ladder) | `permissions.py`, `mapping_data.BAND_CODES` |

## 2. Badge approval (who may approve / return)

`authorize_badge_decision(badge_row, reviewer_id)` — returns an error string, else `None`:
1. badge must be `pending_review`;
2. **guardians always may** (also B6 badges);
3. otherwise the user needs the `badge_reviewer` role, must not be the creator, must be the assigned reviewer (`assigned_reviewer_id`) or hold a `pending` row in `badge_reviewer_assignments`, and must satisfy Reviewer_Band > Badge_Band.
Each decision writes a `badge_review_events` row with a **unique** id (no overwritten audit trail).

## 3. The 50-mark rubric (universal)

| Criterion (controller key) | Max |
|:---|:-:|
| Business Understanding (`bu`) | 10 |
| Architecture / Report (`ar`) | 10 |
| Technical Knowledge (`tk`) | 10 |
| Presentation (`pr`) | 10 |
| Question & Answering (`qa`) | 10 |
| **Total** | **50** |

* Each criterion `0.0 … 10.0` (`starapp/assessment.py::validate_rubric_scores`). Percentage = `total / 50 × 100`.
* **Pass threshold = the badge's `passing_percentage`** (default **70 %**, i.e. ≥ 35/50). Per-badge override is stored on `badges.passing_percentage`.
* No silent defaults: missing criteria are no longer filled with 9.0 for a reviewer; the Guardian's form defaults to the *reviewer's* marks.
* REST variant `validate_50_mark_rubric` (permissions.py) uses key `question_answering` and integer marks — naming differs from the controller (`qa`). Keep them aligned if you touch either.

## 4. Assessment workflow rules

1. **Two-step grading:** reviewer first (`decision = reviewer_assessed`) → Guardian final (`approve` | `resubmission_requested`).
2. Only the **mapped reviewer** (timeline `reviewer_id` or `band_mappings`) — or a guardian — may grade a cadet's submission.
3. **A finalised attempt is immutable.** Submission statuses `approved`, `retake_required`, `resubmission_requested` cannot be re-graded (marksheet ids are deterministic: `asm_rev_<sub>_<attempt>`, `asm_g_<sub>_<attempt>`).
4. Pass ⇒ submission `approved`, timeline `completed`, `actual_award_date` set, cadet "uncoupled" from the active mapping, activity `badge_awarded`, notification. Fail ⇒ `retake_required`.
5. A reviewer may not grade their own work (cadet ≠ reviewer is implied by mapping rules).

## 5. Submission rules (`execute_submit_project`)

* **Multi-attempt history is sacred:** never overwrite a graded attempt. New attempt = new row, `attempt_number = previous + 1`. Only a latest attempt that is still `pending`/`draft` is edited in place.
* A cadet may submit only if: all `prerequisites` of the badge are approved; the badge is allotted to them (timeline exists or badge in their list); the badge is not already earned; the latest attempt is not waiting for the Guardian's final decision.
* Deliverables: PDF architecture report (`.pdf`), a source-code file, and an `http(s)` GitHub URL. Anything missing is inherited from the previous attempt. **Only in demo mode** may placeholders be generated; in real mode a missing deliverable is an error.
* Upload cap `MAX_UPLOAD_CHARS = 12,000,000` characters (≈ 9 MB per file base64).

## 6. Performance-cycle / appraisal criteria (`starapp/cycles.py`, `models.py::DEFAULT_HIKE_POLICY`)

Per person (dual role), **per cycle**:

```
cosmo_score    = avg_percentage × 0.70 + completion_pct × 0.30            (0–100)
reviewer_score = completed_review_tasks / total_review_tasks × 100         (fallback: accepted / total mapping invitations)
composite      = ((cosmo × cw) + (reviewer × rw)) / (cw + rw)   with cw = 0.55 + 0.25 = 0.80, rw = 0.20   (only when both roles had activity;
                 otherwise the score of the active role; 0 if none)
```

| composite ≥ | Tier | Recommended hike |
|:-:|:---|:-:|
| 90 | Outstanding | 18 % |
| 80 | Exceeds Expectations | 12 % |
| 70 | Meets Expectations | 8 % |
| 1 | Needs Development | 3 % |
| no activity | Not Assessed | 0 % |

* **Promotion recommendation:** composite ≥ 85 **and** at least one badge earned ⇒ next band (`_next_band`).
* The policy (weights + slabs) is stored per cycle in `performance_cycles.hike_policy_json`, so a cycle can change it; guardians can then adjust `approved_hike_pct`, bonus and remarks before finalising.
* Appraisal rows are persisted by `calculate_and_save_cycle_appraisals`; finalising closes the cycle and notifies each person.
* Cycles are 6 months (`add_six_months_iso`); exactly **one active cycle** at a time.
* Cohort = users with the cosmonaut role (admin/guardian accounts excluded unless they also hold cosmonaut).

## 7. Authorisation & security rules

| Rule | Where |
|:---|:---|
| **Guardian-only actions** (37) — badge authoring/publish, mapping, allotment, materials, extension decisions, announcements, final assessment, cycles & salaries, reset | `StarAppController._GUARDIAN_ONLY_ACTIONS`, checked at the top of `handle_event` |
| Guardian views are only reachable by guardians; any user is limited to `_COSMONAUT_VIEWS` otherwise | `nav_*` handlers + render-time gate |
| A mapping request may be accepted/rejected/deleted only by the addressed reviewer or a guardian | `accept/reject/delete_mapping_request` |
| Only the mapped reviewer (or guardian) may author/release a project brief, only to their cadets | `send_reviewer_project` |
| Extension request: only for an allotted, not-completed milestone, one pending per badge, ≥ 10-char reason, proposed date later than the current deadline | `execute_submit_extension_request`, `validation.py` |
| Login: the selected role must be a role the user holds | `auth/service.py`, controller login |
| REST: `require_roles` with aliases from `user_role_assignments`; cycles mutations guardian-only; actor from session | `dependencies.py`, `cycles/router.py` |
| Demo shortcuts (passwordless pills, `?role=`, header identity, offline bundle, placeholder deliverables) **only if `STARAPP_DEMO_MODE=true`** | `config.py`, `main.py`, `app.py::_demo_mode_enabled` |
| Session snapshots are HMAC-signed with `SECRET_KEY`, expire, and session ids must match a strict regex | `main.py` |
| Constant-time secret comparisons | `core/security.py` |
| Never put real API keys in git (`GEMINI_API_KEY` lives in `.env`, which is gitignored) | `.gitignore`, `.env.example` |

**Before real users:** `STARAPP_DEMO_MODE=false`, a new `SECRET_KEY`, `STARAPP_COOKIE_SECURE=true` behind HTTPS, `DEBUG=False`, restricted `STARAPP_CORS_ORIGINS`, hashed passwords (backlog).

## 8. Engineering rules (for code changes)

1. Tests: only `python tests/run_tests.py`. Add/adjust a test for every behaviour change (`tests/test_scale_and_security_regressions.py` is the home for scale/security/workflow-rule regressions).
2. SQL: parameterised queries only. UPSERT with `ON CONFLICT DO UPDATE` — never `INSERT OR REPLACE` on cascade parents (`users`, `performance_cycles`, `badges`, …).
3. New org-wide action ⇒ add to `_GUARDIAN_ONLY_ACTIONS`. New read-only/UI-state action ⇒ add to `_CYCLE_READONLY_SAFE_ACTIONS` so it also works in a closed cycle.
4. New long list ⇒ paginate with `starapp/pagination.py` (`page_slice`/`render_pager`), never render unbounded rows.
5. New aggregate used on many pages ⇒ memoise with `store._memoized(key, builder, extra, scope)`; never recompute cohort-wide data per request.
6. UI: show names/badge codes, **not internal ids** (`humanize_internal_ids`); icons are SVG (no emoji glyphs in new code); text contrast ≥ WCAG AA; no font < 10 px; reuse `btn-metal` / `btn-secondary`; no sub-title boilerplate under headings.
7. Don't regress flicker fixes: keep `_sidebarSignature()` ignoring the active class; keep one render per action; keep `full_html` omitted when `regions` exist.
8. After touching `starapp/*.py`: `python scripts/pack_py.py`.
9. Keep `data/starapp.db` untouched unless the task is a DB change; record schema changes in `memory/DATABASE.md` and the change log.
