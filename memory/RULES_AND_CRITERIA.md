# Rules & Criteria (business + technical invariants)

> These are **non-negotiable**. Each rule lists *where it is enforced* so you can change it in one place and update its test.
> "UI hides it" is never enforcement: the server (controller / DB layer) must reject the violating call.

## 1. Bands & reviewer eligibility

| Rule | Detail | Enforced in |
|:---|:---|:---|
| **Reviewer_Band > Badge_Band** (strict) | B1 badges ← B2…B6 · B2 ← B3…B6 · B3 ← B4…B6 · B4 ← B5,B6 · B5 ← B6 · **B6 badges: no peer review** (only Guardians/Executive oversee). Never peer review inside the same band. | `backend/app/core/permissions.py::verify_reviewer_eligibility`, `starapp/database.py` (`verify_reviewer_eligibility`, `authorize_badge_decision`), `send_mapping_requests` in `starapp/app.py` |
| Cadets are mapped only to badges of **their own band** | active users of the badge band only | `send_mapping_requests` |
| Review window (calendar): weekends can't be selected; Manual mode keeps ≥ 1 day and ≤ 45 days; 3/5/7 modes = that many consecutive working days from the clicked day | `select_mapping_review_anchor`, `get_consecutive_review_days` |
| A badge may be mapped only when `workflow_status == "approved"` | else `ActionDenied` | `send_mapping_requests` |
| Nobody reviews a badge they authored | | `authorize_badge_decision` |
| Band order | `B1 < B2 < … < B6` (`BAND_HIERARCHY`; CEO is outside the peer-review ladder) | `permissions.py`, `mapping_data.BAND_CODES` |

## 2. Badge approval (who may approve / return)

`authorize_badge_decision(badge_row, reviewer_id)` — returns an error string, else `None`:
1. badge must be `pending_review`;
2. **guardians always may** (also B6 badges);
3. otherwise the user needs the `badge_reviewer` role, must not be the creator, must be the assigned reviewer (`assigned_reviewer_id`) or hold a `pending` row in `badge_reviewer_assignments`, and must satisfy Reviewer_Band > Badge_Band.
Each decision writes a `badge_review_events` row with a **unique** id (no overwritten audit trail).

**Changing the reviewer (Guardian only):** `manage_badge_reviewer` (opens the small Manage Reviewer modal from the queue's Edit button), `send_badge_review_request` (assign / reassign) and `cancel_badge_reviewer` (`DatabaseManager.cancel_badge_review_request`: `pending_review` → `ready_for_review`, `assigned_reviewer_id` NULL, event `reviewer_cancelled`). Both go through `_release_pending_reviewers`, which marks every other open `badge_reviewer_assignments` row `cancelled` and notifies that reviewer — `authorize_badge_decision` honours any `pending` row, so a stale one would let a removed reviewer keep approving. Only a badge awaiting review has a reviewer to cancel. (Known gap: the DB layer still lets a Guardian re-assign an already `approved` badge; the UI hides it.)

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

* **Project first:** *Request Project* -> reviewer sends **Heading + Content** -> *Submit Project Deliverables* (the modal shows the project, then PDF / code / GitHub). The submission is routed to the reviewer from `store.get_mapped_reviewer_id` (timeline -> band mapping -> badge assignment) and appears in their **Cosmonaut Assessments**.

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
| **Guardian-only actions** (40) — badge authoring/publish, mapping, allotment, materials, extension decisions, announcements, final assessment, cycles & salaries, reset | `StarAppController._GUARDIAN_ONLY_ACTIONS`, checked at the top of `handle_event` |
| Guardian views are only reachable by guardians; any user is limited to `_COSMONAUT_VIEWS` otherwise | `nav_*` handlers + render-time gate |
| A mapping request may be accepted/rejected/deleted only by the addressed reviewer or a guardian | `accept/reject/delete_mapping_request` |
| **Edit Badge: a cosmonaut can be given to any reviewer ALREADY mapped to the badge** (`reviewer_assignments` {cosmonaut: reviewer}); newly added cosmonauts must be in the badge's band; one reviewer per cosmonaut; the change is written to the band mapping, the cosmonaut's timeline (`reviewer_id` + `review_window_json`), the reviewer's accepted/pending request (`cosmonaut_ids`) and a notification - same save as below |
| **Edit Badge (allotment) may change ONLY the assigned cosmonauts and the milestone timeline** - code, title, description, project brief, band, taxonomy, workflow/publication state, reviewer and pass mark are preserved even if the payload carries other values; ≥1 cosmonaut required; dates must be valid ISO and learning/project end ≥ start; a cosmonaut who already submitted for the badge cannot be removed; removing one also deletes their timeline and strips them from the badge's band mappings | `StarAppController._save_badge_allotment_edit` (called by `execute_save_badge` for an existing badge), `store.delete_timeline` |
| **24-hour response window**: every mapping request gets `expires_at = sent_at + 24 h`; a still-`pending` request past it is auto-set to `rejected` + `expired=True` (both sides notified), a late accept is refused (even by a Guardian); only a Guardian can `resend_mapping_request` (fresh window). Legacy requests without `expires_at` never expire | `StarAppController._expire_overdue_mapping_requests` (runs at the top of every `handle_event`), `store.expire_overdue_mapping_requests`, `accept_mapping_request` guard |
| **Asset cache-bust**: the server caches `/css/*` and `/js/*?v=N` for 24 h, so after ANY change to `css/*` or `js/*` bump `?v=` in `index.html` + `sw.js` (and the `v=` / cache-name asserts in `tests/test_backend_fullstack.py`, `tests/test_ui_remediation.py`, `Report.md`) | `backend/app/main.py` cache middleware |
| **Type scale (rem)**: `--type-page-title 1.75rem` (h1/h2) · `--type-section-title 1.25rem` (h3) · `--type-subtitle 1rem` (h4) · `--type-body .875rem` · `--type-small .8125rem` · `--type-caption .75rem` (`css/design_tokens.css`); headings inside `.app-main` are pinned to them in `css/components.css`; all inline `font-size` is in rem (never px) | new UI should use the `--type-*` tokens |
| Only the mapped reviewer (or guardian) may send a project, only to their cosmonauts; heading and content are mandatory (heading <= 200, content <= 20,000 chars) | `send_reviewer_project` |
| A cosmonaut may request a project only for an allotted, not-yet-earned badge with a mapped reviewer (one open request); **deliverables can be submitted only for a project that was sent** (`open_submission_modal` and `execute_submit_project` both refuse otherwise) | `execute_request_project`, `execute_submit_project` |
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
7. Terminology: the Cosmonaut portal (any `c_*` view, incl. reviewer pages, modals, flash messages, page titles) says **"Cosmonaut", never "Cadet"**. It is enforced centrally by `views_common.cosmonaut_terms()` (text nodes + `placeholder/title/aria-label/alt` only; ids, classes, handlers, scripts untouched) applied in `_render_workspace_scoped`; Guardian pages keep their wording. New text may be written either way, but test `test_no_cadet_wording_on_any_cosmonaut_or_reviewer_page` must pass.
7a. **Cosmonaut sidebar order** (`views_cosmonaut.render_cosmonaut_sidebar`): Badges (`c_submission`, the landing page = `StarAppController.COSMONAUT_HOME_VIEW`) → Assessment Marksheet → Deadline Extension → *(Band 2+ only)* Badge Reviews → Review Requests (there is no separate Cosmonaut Assessments page: the reviewer assesses from the Badge Review schedule). **Profile is compulsory for every user in every portal and is not in the nav list: it is the standard `nav-link` "View Profile" pinned in the sidebar footer (`views_common.render_sidebar_profile_footer`, `data-nav-id` = `c_profile` / `g_profile`), highlighted with `active` while the profile page is open, above the user name + Sign Out.** Reviewer tools exist only for bands B2–B6 (`views_common.is_reviewer_band`, `COSMONAUT_REVIEWER_VIEWS`) because Reviewer_Band > Badge_Band; this is enforced in `nav_cosmonaut` (ActionDenied) **and** at render time (stale sessions fall back to Badges), not just by hiding the links. The Choose Cycle page has no sidebar item; it opens from the cycle pill at the top of the sidebar and the top-bar "Cycles & Appraisals" link.
7b. Filters: the Reviewer Badge Approval queue is scoped to the **active band workspace** (`create_badge_band`; none = every band). There is deliberately **no band dropdown** on that page. Status and search must work in both the queue and Review History.
7c. Don't regress flicker fixes: keep `_sidebarSignature()` ignoring the active class; keep one render per action; keep `full_html` omitted when `regions` exist.
8. After touching `starapp/*.py`: `python scripts/pack_py.py`.
9. Keep `data/starapp.db` untouched unless the task is a DB change; record schema changes in `memory/DATABASE.md` and the change log.

**UI rule - no browser dialogs for badge actions.** Publish and Revoke on the Badge Allotment card ask for confirmation in the app's own glass dialog (`confirm_publish_badge` / `confirm_revoke_badge` -> modal `badge_publish_confirm` / `badge_revoke_confirm`, Guardian-only on the server); the confirm button dispatches `publish_badge` / `revoke_badge`. Do not reintroduce `confirm()` in `js/bridge.js` or in rendered `onclick`s for these actions.
