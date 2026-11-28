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

1. **The reviewer RECOMMENDS, the Guardian DECIDES.** The mapped reviewer saves the 50-mark rubric + a recommendation (Give Badge / Re-attempt / Reject → marksheet `decision` = `recommend_approve | recommend_resubmit | recommend_reject`; legacy `reviewer_assessed` = marks only). The submission becomes `reviewer_assessed`; nothing is awarded. The Guardian then decides: `approve` (badge earned) | `resubmission_requested` | `rejected`. Helpers: `views_common.REVIEWER_RECOMMENDATIONS`, `normalize_decision`, `reviewer_recommendation_key`, `render_recommendation_chip`. Enforced in `StarAppController.execute_submit_evaluation`.
2. Only the **mapped reviewer** (`store.get_mapped_reviewer_id`: timeline `reviewer_id` → `band_mappings` → badge's own reviewer) — or a guardian — may grade a cosmonaut's submission. The reviewer reaches the page from the **Assessment** button on the Badge Review schedule, which is disabled (`rv-assess is-locked`) until that cosmonaut has submitted.
3. **Reviewer marks are locked per attempt.** One reviewer marksheet per attempt (`asm_rev_<sub>_<attempt>`); a second submit for the same attempt is refused ("Marks … already submitted and locked") and the panel renders read-only. A new assessment exists only for a new attempt (new submission id).
4. **Give Badge cannot be recommended, and Earn Badge cannot be chosen, below the badge pass mark** (`passing_percentage`, default 70 %); the Guardian's choice drives the outcome (a passing score does not force a badge). With no choice, the pass mark decides.
5. **A finalised attempt is immutable.** Submission statuses `approved`, `retake_required`, `resubmission_requested` cannot be re-graded ("already received a final decision"); a second Guardian decision without revoking is refused.
6. Earn ⇒ submission `approved`, timeline `completed`, `actual_award_date` set, cosmonaut "uncoupled" from the mapping, activity `badge_awarded`, notification. Re-attempt / Reject ⇒ submission + timeline `retake_required`; the cosmonaut may submit a new attempt (`attempt_number + 1`; the loop restarts; old marksheets stay).
7. **Earned** = timeline `completed` / submission `approved` / a marksheet whose decision is exactly `approve`|`approved` (reviewer recommendations are `recommend_*`, Re-attempt / Reject sheets never mean earned — a past bug where any Guardian marksheet flagged the badge earned was fixed in `views_cosmonaut._cosmo_badge_state` and the Badges grid). Earned badges render gold (`.gold-medal`, `.gold-card`, `.mbe-card`).
8. **The saved Guardian decision is revocable only by the Guardian** (`open_revoke_decision_confirm` / `revoke_guardian_decision`, both in `_GUARDIAN_ONLY_ACTIONS`; `execute_revoke_guardian_decision`). Only the LATEST attempt can be revoked. Effect: Guardian marksheet deleted (`store.delete_assessment`), submission → `reviewer_assessed` (reviewer marks and recommendation untouched), timeline award date cleared, mapping re-coupled (`store.recouple_cadet_badge_mapping`), cosmonaut + reviewer notified, activity `guardian_decision_revoked`. This is the ONLY place an `assessment_marksheets` row is deleted.
9. **Mapping end rule:** each earned cosmonaut is uncoupled from the mapping (`store.uncouple_cadet_badge_mapping`: `completed_cosmonauts`, `uncoupled_cadets`, timeline `completed`, award date); `band_mappings.status` becomes `completed` **only when ALL mapped cosmonauts have earned**. The reviewer's Badge Review schedule groups Upcoming and Completed Reviews per badge; a badge moves to Completed only then ("All badges earned"); a revoke re-opens it.
10. A reviewer may not grade their own work (cadet ≠ reviewer is implied by mapping rules).
11. **The cosmonaut marksheet shows ONE sheet** — the latest evaluation (the Guardian's once decided, else the reviewer's) — **marks only** (no tabs, no outcome pill, no summary). Reviewer name = the real mapped peer reviewer (`views_common._ms_reviewer_name`), never the Guardian. Status is shown elsewhere (gold badge, Guardian pills).

## 5. Submission rules (`execute_submit_project`)

* **Project first:** the mapped reviewer sends **Heading + Content** (72 h window from publish) -> the cosmonaut opens the project **page** (`c_project`, guarded by `_allocated_project_denied`) -> *Submit Deliverables* (glass dialog: PDF / code / GitHub only). The submission is routed to the reviewer from `store.get_mapped_reviewer_id` (timeline -> band mapping -> badge assignment); their **Assessment** button on the Badge Review schedule unlocks (there is no Cosmonaut Assessments page any more).

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
| **Guardian-only actions** (47) — badge authoring/publish, mapping, allotment, materials, extension decisions, announcements, final assessment, **revoke of a final decision**, cycles & salaries, reset | `StarAppController._GUARDIAN_ONLY_ACTIONS`, checked at the top of `handle_event` |
| Guardian views are only reachable by guardians; any user is limited to `_COSMONAUT_VIEWS` otherwise | `nav_*` handlers + render-time gate |
| A mapping request may be accepted/rejected/deleted only by the addressed reviewer or a guardian | `accept/reject/delete_mapping_request` |
| **Edit Badge: a cosmonaut can be given to any reviewer ALREADY mapped to the badge** (`reviewer_assignments` {cosmonaut: reviewer}); newly added cosmonauts must be in the badge's band; one reviewer per cosmonaut; the change is written to the band mapping, the cosmonaut's timeline (`reviewer_id` + `review_window_json`), the reviewer's accepted/pending request (`cosmonaut_ids`) and a notification - same save as below |
| **Edit Badge (allotment) may change ONLY the assigned cosmonauts and the milestone timeline** - code, title, description, project brief, band, taxonomy, workflow/publication state, reviewer and pass mark are preserved even if the payload carries other values; ≥1 cosmonaut required; dates must be valid ISO and learning/project end ≥ start; a cosmonaut who already submitted for the badge cannot be removed; removing one also deletes their timeline and strips them from the badge's band mappings | `StarAppController._save_badge_allotment_edit` (called by `execute_save_badge` for an existing badge), `store.delete_timeline` |
| **24-hour response window**: every mapping request gets `expires_at = sent_at + 24 h`; a still-`pending` request past it is auto-set to `rejected` + `expired=True` (both sides notified), a late accept is refused (even by a Guardian); only a Guardian can `resend_mapping_request` (fresh window). Legacy requests without `expires_at` never expire | `StarAppController._expire_overdue_mapping_requests` (runs at the top of every `handle_event`), `store.expire_overdue_mapping_requests`, `accept_mapping_request` guard |
| **Asset cache-bust**: the server caches `/css/*` and `/js/*?v=N` for 24 h, so after ANY change to `css/*` or `js/*` bump `?v=` in `index.html` + `sw.js` (current: `v=121`, SW cache `starapp-runtime-cache-v78`) and the `v=` / cache-name asserts in `tests/test_backend_fullstack.py`, `tests/test_ui_remediation.py` (`Report.md` is an older overview and may still show old values) | `backend/app/main.py` cache middleware |
| **Type scale (rem)**: `--type-page-title 2rem` (h1/h2; was 1.75 until 2026-11-28) · `--type-section-title 1.25rem` (h3) · `--type-subtitle 1rem` (h4) · `--type-body .875rem` · `--type-small .8125rem` · `--type-caption .75rem` (`css/design_tokens.css`); `h1–h4` inside `.app-main` are pinned to them with `!important` in `css/components.css` (a custom size needs `<div role="heading" aria-level="N">`); all inline `font-size` is in rem (never px) | new UI should use the `--type-*` tokens |
| **Times shown to users are IST (UTC+5:30); storage stays UTC.** Never print a UTC string or the word "UTC" | `views_common.to_ist` / `format_ist` / `ist_plain` / `format_utc_stamp` (the last keeps its historical name but prints IST) |
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
2. SQL: parameterised queries only. UPSERT with `ON CONFLICT DO UPDATE` — never `INSERT OR REPLACE` on cascade parents (`users`, `performance_cycles`, `badges`, `announcements`, …). `announcements` is the only table written at runtime that has cascade children (`announcement_recipients`, `announcement_read_receipts`); `save_announcement` was converted to UPSERT on 2026-11-28 because `INSERT OR REPLACE` wiped the recipients and read receipts on every re-save. The other runtime `OR REPLACE` targets (`cosmonaut_profiles`, `cycle_enrollments`, `cycle_performance_appraisals`, `badge_powers/capabilities/skills`, `badge_timelines`, `assessment_marksheets`, `learning_materials`, `deadline_extensions`, `activity_events`, `notifications`, `band_mappings`, `mapping_requests`, `reviewer_project_prompts`) have no child tables (checked against the schema) — keep it that way or convert them first.
3. New org-wide action ⇒ add to `_GUARDIAN_ONLY_ACTIONS`. New read-only/UI-state action ⇒ add to `_CYCLE_READONLY_SAFE_ACTIONS` so it also works in a closed cycle.
4. New long list ⇒ paginate with `starapp/pagination.py` (`page_slice`/`render_pager`), never render unbounded rows.
5. New aggregate used on many pages ⇒ memoise with `store._memoized(key, builder, extra, scope)`; never recompute cohort-wide data per request.
6. UI: show names/badge codes, **not internal ids** (`humanize_internal_ids`); icons are SVG (no emoji glyphs in new code); text contrast ≥ WCAG AA; no font < 10 px; reuse `btn-metal` / `btn-secondary`; no sub-title boilerplate under headings.
7. Terminology: the Cosmonaut portal (any `c_*` view, incl. reviewer pages, modals, flash messages, page titles) says **"Cosmonaut", never "Cadet"**. It is enforced centrally by `views_common.cosmonaut_terms()` (text nodes + `placeholder/title/aria-label/alt` only; ids, classes, handlers, scripts untouched) applied in `_render_workspace_scoped`; Guardian pages keep their wording. New text may be written either way, but test `test_no_cadet_wording_on_any_cosmonaut_or_reviewer_page` must pass.
7b. **Never let a countdown cause a repaint.** Anything that ticks (`data-remaining`, `.rq-timer-text`) is excluded when HTML is compared (`views_common.stable_html_signature` on the server, `bridge.js::_stableHtml` in the browser). A new live element must either use that markup or be excluded the same way; a poll (`sync_*`) must never be treated as a user action (`dispatchAction`).
7c. **No gradients on big glass surfaces.** Cards / panels / headers that cover a large area use a FLAT translucent tint (e.g. `rgba(245, 250, 255, 0.86)`), never `linear-gradient(...)`: large translucent gradients were the dominant scroll cost (see LOGICS J). Small accents (buttons, medals, the gold card, avatars) may keep gradients. Guarded by `tests/test_performance_and_live_sync.py::TestScrollCost`.
7d. **Cosmonaut sidebar order** (`views_cosmonaut.render_cosmonaut_sidebar`): Badges (`c_submission`, the landing page = `StarAppController.COSMONAUT_HOME_VIEW`) → Assessment Marksheet → Deadline Extension → *(Band 2+ only)* Badge Reviews → Review Requests (there is no separate Cosmonaut Assessments page: the reviewer assesses from the Badge Review schedule). **Profile is compulsory for every user in every portal and is not in the nav list: it is the "View Profile" button in the sidebar footer (`views_common.render_sidebar_actions_footer`, the ONE footer for every portal: name card above View Profile | Sign Out; `data-nav-id` = `c_profile` / `g_profile`), highlighted with `active` while the profile page is open.** Reviewer tools exist only for bands B2–B6 (`views_common.is_reviewer_band`, `COSMONAUT_REVIEWER_VIEWS`) because Reviewer_Band > Badge_Band; this is enforced in `nav_cosmonaut` (ActionDenied) **and** at render time (stale sessions fall back to Badges), not just by hiding the links. The Choose Cycle page has no sidebar item; it opens from the cycle pill at the top of the sidebar and the top-bar "Cycles & Appraisals" link.
7e. Filters: the Reviewer Badge Approval queue is scoped to the **active band workspace** (`create_badge_band`; none = every band). There is deliberately **no band dropdown** on that page. Status and search must work in both the queue and Review History.
7f. Don't regress flicker fixes: keep `_sidebarSignature()` ignoring the active class; keep one render per action; keep `full_html` omitted when `regions` exist.
7g. **IST only** for anything a user reads (see §7 table); storage and comparisons stay UTC.
7h. **Panels that must fit without scrolling** (reviewer "Technical Assessment" and Guardian "Marks Allotment") are sized only through the `--rp-*` variables chosen by window-height tier in `css/components.css` (`.review-right-column`; reviewer tiers L ≥ 930, M 800–929, S 690–799, XS 600–689; the Guardian panel's tiers are shifted +120 px via `.review-right-column:has(#guardian-rubric-form)` and has one more step, XXS). Do not hard-code sizes in the views; notes boxes stay 34–58 px.
7i. **One marksheet renderer** (`views_common.render_standard_marksheet`) for the cosmonaut page and the modal; `.ms-*` classes; do not re-add tabs / outcome pill / summary / score ring.
8. After touching `starapp/*.py`: `git checkout data/starapp.db` then `python scripts/pack_py.py` (the bundle embeds the DB).
9. Keep `data/starapp.db` untouched unless the task is a DB change; record schema changes in `memory/DATABASE.md` and the change log.

**UI rule - no browser dialogs for badge actions.** Publish and Revoke on the Badge Allotment card ask for confirmation in the app's own glass dialog (`confirm_publish_badge` / `confirm_revoke_badge` -> modal `badge_publish_confirm` / `badge_revoke_confirm`, Guardian-only on the server); the confirm button dispatches `publish_badge` / `revoke_badge`. Do not reintroduce `confirm()` in `js/bridge.js` or in rendered `onclick`s for these actions.
