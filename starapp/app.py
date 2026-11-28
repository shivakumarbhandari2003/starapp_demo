"""
STARAPP CORE APPLICATION CONTROLLER & ROUTER
Orchestrates role-based navigation, state mutation, event dispatch, and UI rendering.
Works seamlessly in browser Pyodide runtime and in local Python test suites.
"""

import datetime
import json
import time
import uuid
from typing import Optional, Dict, Any, Tuple, List
from starapp.models import (
    DEFAULT_CYCLE_ID, User, Badge, BadgeTimeline, ProjectSubmission, AssessmentMarksheet,
    LearningMaterial, DeadlineExtension, Announcement, ReviewerProjectPrompt,
    CycleEnrollment, CyclePerformanceAppraisal, current_iso_timestamp
)
from starapp.storage import store, StorageWriteError
from starapp.pagination import bind_page_state, reset_page_state
from starapp.cycles import (
    compute_cycle_candidate_performance, calculate_and_save_cycle_appraisals,
    finalize_and_close_cycle, create_new_six_month_cycle, activate_cycle
)
from starapp.assessment import (
    validate_rubric_scores, calculate_assessment_totals,
    calculate_batch_aggregate_analytics, calculate_batch_leaderboard,
    calculate_cosmonaut_score_summary
)
from starapp.roadmap import generate_roadmap_graph
from starapp.validation import (
    validate_badge_input, validate_submission_input,
    validate_extension_request, validate_announcement_input
)
from starapp.analytics import (
    get_guardian_cohort_profiles, calculate_guardian_cohort_analytics,
    get_cosmonaut_individual_dossier
)
from starapp.views_common import (
    ist_plain,
    normalize_decision, REVIEWER_RECOMMENDATIONS,
    get_icon, render_global_back_bar, hoist_page_title, TITLE_HOIST_VIEWS,
    render_cycle_context_bar, render_topbar, render_liquid_card, render_metal_button, escape,
    render_status_pill, render_standard_marksheet, render_9point_timeline, iconize_html, cosmonaut_terms,
    is_reviewer_band, COSMONAUT_REVIEWER_VIEWS
)
from starapp.views_guardian import (
    render_decision_revoke_confirm_modal,
    _bi_render_raw_prompt, _fmt_nice_date, render_badge_edit_assignees, _extract_badge_mapping_details,
    render_guardian_sidebar, render_guardian_dashboard,
    render_guardian_badge_allotment, render_guardian_mapping, render_guardian_mapping_badge_detail,
    render_mapping_calendar_modal,
    render_guardian_review_queue, render_guardian_review_detail,
    render_assessment_modal_content, render_guardian_materials,
    render_guardian_activity_feed, render_guardian_extensions,
    render_guardian_announcements, render_guardian_profile,
    render_guardian_create_badge, render_guardian_badge_approval_queue,
    render_badge_creation_preview_modal, render_badge_review_inspect_modal,
    render_badge_reviewer_edit_modal, render_badge_approval_confirm_modal, render_badge_activity_log_modal, render_badge_reviewer_manage_modal,
    render_badge_return_confirm_modal, render_badge_publish_confirm_modal, render_badge_revoke_confirm_modal,
    render_guardian_cycles_view, render_create_cycle_modal, render_cycle_candidate_detail_modal,
    render_badge_timeline_mapping_modal,
    render_guardian_pillar_placeholder
)
from starapp.mapping_data import (
    get_higher_bands, filter_members_by_band_and_roles, filter_reviewers_by_band_and_roles,
    get_consecutive_review_days, get_working_days_between, parse_iso_date
)
from starapp.views_cosmonaut import (
    render_cosmonaut_sidebar, render_cosmonaut_dashboard,
    render_cosmonaut_profile, render_gamified_roadmap,
    render_badge_detail_modal_content, render_cosmonaut_submission_workspace,
    render_cosmonaut_badge_detail_page, render_cosmonaut_project_page,
    render_cosmonaut_reviewer_modal, render_cosmonaut_timeline_modal,
    render_cosmonaut_submission_modal,
    render_cosmonaut_badge_preview_modal,
    render_cosmonaut_results, render_cosmonaut_materials,
    render_cosmonaut_extensions, render_cosmonaut_announcements,
    render_cosmonaut_activity_stream, render_cosmonaut_review_requests,
    render_reviewer_assessment_detail,
    render_reviewer_badge_schedule, render_reviewer_badge_review,
    render_reviewer_badge_timeline_modal,
    render_reviewer_project_creator_modal,
    render_cosmonaut_cycles_view,
    render_cosmonaut_choose_cycle_view
)

# Pyodide browser bridge detection
try:
    import js
    IS_BROWSER = hasattr(js, "document")
except ImportError:
    js = None
    IS_BROWSER = False

class ActionDenied(Exception):
    """Raised by an action handler when the signed-in user may not perform it (message is shown to them)."""


# Per-file upload ceiling (characters of the base64 data URL / source text). Keeps one submission from
# exhausting server memory or the database; roughly 9 MB of binary data.
MAX_UPLOAD_CHARS = 12_000_000


def _demo_mode_enabled() -> bool:
    """
    Passwordless demo conveniences (quick-login pills, username-only login) are allowed only while
    STARAPP_DEMO_MODE is on (default). In the browser/Pyodide runtime there is no environment, so the
    offline demo keeps working. Set STARAPP_DEMO_MODE=false for any deployment with real accounts.
    """
    try:
        import os as _os
        return _os.environ.get("STARAPP_DEMO_MODE", "true").strip().lower() in ("true", "1", "yes", "on")
    except Exception:
        return True


class StarAppController:
    def __init__(self):
        self.current_user: Optional[User] = None
        self.current_view: str = "login"
        self.selected_guardian_cosmo_id: str = "all"
        self.guardian_review_filter: str = "all"
        self.assessment_power_filter: str = "all"
        self.assessment_capability_filter: str = "all"
        self.assessment_selected_badge_id: Optional[str] = None
        self.assessment_selected_cosmonaut_id: Optional[str] = None
        self.guardian_allotment_filter: str = "all"
        self.selected_review_sub_id: Optional[str] = None
        self.selected_viewer_tab: str = "pdf"
        self.cosmonaut_submission_badge_id: str = "badge_cur_102"
        self.cosmonaut_expanded_badge_id: Optional[str] = None
        self.reviewer_expanded_badge_id: Optional[str] = None
        self.cosmonaut_results_badge_id: str = "badge_gov_101"
        self.cosmonaut_results_picked: bool = False        # True once the cosmonaut chose a badge on the marksheet page (else: the newest evaluated badge)
        self.cosmonaut_results_asm_id: str = ""            # the evaluation tab shown on the marksheet page ("" = the newest)
        self.materials_badge_filter: str = "all"
        self.materials_type_filter: str = "all"
        self.active_modal: Optional[str] = None
        self.modal_payload: Dict[str, Any] = {}
        self.flash_message: Optional[str] = None
        self.last_flash_message: Optional[str] = None
        self.flash_type: str = "info"
        self.login_error: Optional[str] = None
        self.login_email_draft: str = ""
        self.render_generation: int = 0
        self._last_render_source: str = "init"
        self.view_history: list = []
        # Current page of every paginated list/table (key -> 1-based page). See starapp/pagination.py
        self.list_pages: Dict[str, int] = {}

        # Mapping workspace state
        self.mapping_selected_band: str = "B1"
        self.mapping_selected_roles: list = ["Solutions Designer", "AI Engineer", "Systems Engineer"]
        self.mapping_selected_badge: str = ""
        self.mapping_selected_badge_id: str = ""
        self.mapping_selected_cosmonauts: list = []
        self.mapping_selected_reviewer_bands: list = ["B2"]
        self.mapping_selected_reviewer_band: str = "B2"
        self.mapping_selected_reviewers: list = []
        self.mapping_cosmo_search: str = ""
        self.mapping_reviewer_search: str = ""
        self.mapping_badge_search: str = ""
        self.mapping_calendar_year: int = datetime.date.today().year
        self.mapping_calendar_month: int = datetime.date.today().month
        self.mapping_review_anchor: str = "2026-11-18"
        self.mapping_review_direction: str = "after"
        self.mapping_review_days_count: int = 3
        self.mapping_review_mode: str = "gap"
        self.mapping_range_start: str = ""
        self.mapping_review_dates: list = ["2026-11-18", "2026-11-19", "2026-11-20"]
        self.mapping_staged_previews: Dict[str, Any] = {}
        self.mapping_expanded_badge_key: str = ""
        self.mapping_detail_badge_key: str = ""
        self.mapping_last_sent_badge_by_band: Dict[str, Tuple[str, str, str]] = {}
        self.editing_mapping_id: Optional[str] = None
        self.mapping_show_final_stage: bool = False

        # Create Badge Workspace state
        self.create_badge_band: Optional[str] = None
        self.create_badge_power: str = "Tech"
        self.create_badge_capability: str = "Data & Machine"
        self.create_badge_skill: str = "Hardware"
        self.create_badge_outcome_sentence: str = "Identify CPU, memory, storage, and GPU components in a given system spec and describe their basic roles"
        self.created_badge_data: Optional[Dict[str, Any]] = None
        self.is_editing_badge: bool = False
        self.saved_badges: List[Dict[str, Any]] = []
        self.create_badge_reviewer_id: Optional[str] = None
        self.create_badge_prompt_json: str = json.dumps({
            "prompt": "Identify CPU, memory, storage, and GPU components in a given system specification and describe their basic roles.",
            "learning_objectives": [
                "Identify hardware components",
                "Understand their primary functions",
                "Explain how the components work together"
            ],
            "expected_outcomes": [
                "Component identification table",
                "Functional architecture diagram",
                "Tradeoff analysis summary"
            ],
            "evaluation_focus": [
                "Technical accuracy",
                "System integration reasoning",
                "Clarity and completeness"
            ]
        }, indent=2)
        self.create_badge_metadata: Dict[str, Any] = {
            "code": "B1-HDW-01",
            "title": "Foundational Hardware Architecture",
            "category": "Systems Engineering",
            "description": "Architectural overview of system hardware, processor components, bus architectures, memory hierarchy, and storage subsystems.",
            "learning_outcomes": "Component identification table, Functional architecture diagram, Tradeoff analysis summary",
            "learning_topics": "CPU Architecture, Memory Subsystems, Storage Systems, Accelerator Hardware",
            "project_requirements": "Design a complete specification document analyzing hardware bottlenecks in a high-throughput processing pipeline."
        }
        self.create_badge_json_error: Optional[str] = None
        self.create_badge_skill_search: str = ""

        # Badge Approval Queue state
        self.badge_approval_filter: str = "all"
        self.badge_approval_search: str = ""

        # Cosmonaut Review Requests Queue state
        self.cosmo_requests_tab: str = "all"
        self.cosmo_requests_search: str = ""
        # Reviewer badge-review page (Review Requests -> one badge): which real badge, and whether it is being edited
        self.reviewer_review_badge_id: str = ""
        self.reviewer_review_editing: bool = False

        # 6-Month Cycle & Performance Management state
        self.selected_cycle_id: Optional[str] = None
        self.cycle_band_filter: str = "all"
        self.cycle_role_filter: str = "all"

    # Landing page of the Cosmonaut portal (first sidebar item).
    COSMONAUT_HOME_VIEW = "c_submission"

    # Valid view ids per role to prevent arbitrary injection
    _GUARDIAN_VIEWS = {
        "g_learning", "g_earning", "g_contribution",
        "g_create_badge", "g_badge_approval",
        "g_dashboard", "g_roadmap", "g_cosmonauts", "g_allotment", "g_badge_allotment", "g_mapping", "g_mapping_badge_detail", "g_reviews", "g_review_detail",
        "g_materials", "g_extensions", "g_announcements", "g_activity", "g_cycles", "g_profile"
    }
    _COSMONAUT_VIEWS = {
        "c_choose_cycle", "c_dashboard", "c_roadmap", "c_submission", "c_badge_detail", "c_project", "c_results",
        "c_materials", "c_profile", "c_announcements", "c_extensions", "c_activity",
        "c_requests", "c_badge_review", "c_badge_reviews", "c_assessment_detail", "c_cycles"
    }

    def _allocated_project_denied(self, badge_id: str) -> str:
        """Why this user may not open this badge's project page ('' when they may): it must be a badge allotted to them whose project has been sent."""
        user = self.current_user
        badge = store.get_badge(badge_id) if badge_id else None
        if not (user and badge):
            return "Badge not found."
        if not (store.get_timeline(badge_id, user.id) or badge_id in {b.id for b in store.get_badges_for_cosmonaut(user.id)}):
            return "This badge is not allotted to you."
        if not store.get_project_prompt_for_cadet(badge_id, user.id):
            return "Your project has not been sent yet. It appears under \"Project Allocated\" as soon as your mapped reviewer sends it."
        return ""

    def _get_effective_cycle_id(self) -> str:
        """Resolves the controller's active or viewed cycle_id, falling back cleanly if absent."""
        cycles = store.get_all_cycles()
        cycle_ids = {c.id for c in cycles}
        if self.selected_cycle_id and self.selected_cycle_id in cycle_ids:
            return self.selected_cycle_id
        active_cid = store.get_active_cycle_id()
        self.selected_cycle_id = active_cid
        return active_cid

    def initialize(self, stored_json: Optional[str] = None, session_json: Optional[str] = None, sqlite_b64: Optional[str] = None):
        """Loads data from storage and restores previous user session including the exact page."""
        store.load_from_json(stored_json, sqlite_b64)

        # Restore session — including the exact page the user was on
        if session_json and session_json.strip():
            try:
                session_data = json.loads(session_json)
                user_id = session_data.get("user_id")
                saved_view = session_data.get("current_view", "")
                saved_cycle_id = session_data.get("selected_cycle_id")
                if saved_cycle_id and store.get_cycle(saved_cycle_id):
                    self.selected_cycle_id = saved_cycle_id
                if user_id:
                    user = store.get_user_by_id(user_id)
                    if user:
                        self.current_user = user
                        is_guardian_user = (user.role in ("guardian", "badge_reviewer") or user.has_role("guardian") or user.has_role("badge_reviewer"))
                        # Restore the exact page if it is valid for the user's role
                        if is_guardian_user and saved_view in self._GUARDIAN_VIEWS:
                            self.current_view = saved_view
                        elif saved_view in self._COSMONAUT_VIEWS:
                            self.current_view = saved_view
                        else:
                            self.current_view = "g_cycles" if is_guardian_user else self.COSMONAUT_HOME_VIEW
            except Exception as e:
                print(f"[Controller] Session restore error: {e}")

        self._get_effective_cycle_id()
        self.sync_storage(force_data=True)
        self._last_render_source = "initialize"
        self.render()

    def sync_storage(self, force_data: bool = False):
        """
        Persists current session state to sessionStorage.
        Only serializes and writes domain data to IndexedDB / localStorage when
        store.dirty is True or force_data is requested, avoiding expensive redundant writes.
        """
        session_data = json.dumps({
            "user_id": self.current_user.id if self.current_user else None,
            "current_view": self.current_view,
            "selected_cycle_id": self._get_effective_cycle_id()
        })
        if IS_BROWSER and hasattr(js, "window") and hasattr(js.window, "StarAppBridge"):
            js.window.StarAppBridge.setStore("session", session_data)
            if store.dirty or force_data:
                json_data = store.to_json()
                js.window.StarAppBridge.setStore("data", json_data)
                try:
                    sqlite_b64 = store.export_sqlite_base64()
                    js.window.StarAppBridge.setStore("sqlite_db", sqlite_b64)
                except Exception as e:
                    print(f"[Controller] SQLite export error: {e}")
                store.dirty = False

    def reload_data(self, stored_json: Optional[str] = None, expected_generation: Optional[int] = None, sqlite_b64: Optional[str] = None):
        """
        Real-time multi-window synchronization callback.
        Called when another browser window updates the shared data store.
        Reloads domain data from JSON while maintaining this window's user session.
        Aborts cleanly if a newer local navigation/render generation has occurred.
        """
        if expected_generation is not None and int(expected_generation) < self.render_generation:
            return
        if (stored_json and stored_json.strip()) or (sqlite_b64 and sqlite_b64.strip()):
            prev_active_cid = store.get_active_cycle_id()
            store.load_from_json(stored_json, sqlite_b64)
            new_active_cid = store.get_active_cycle_id()
            if self.current_user:
                updated_user = store.get_user_by_id(self.current_user.id)
                if updated_user:
                    self.current_user = updated_user
                u_roles = getattr(self.current_user, "roles", [self.current_user.role])
                is_guard = (self.current_user.id in ("guardian_1", "admin") or self.current_user.role in ("guardian", "admin") or "guardian" in u_roles)
                if not is_guard and new_active_cid and new_active_cid != prev_active_cid and self.current_view != "c_cycles":
                    self.selected_cycle_id = new_active_cid
            self._last_render_source = "cross_tab_reload"
            self.render()

    def set_flash(self, message: str, ftype: str = "info"):
        self.flash_message = message
        self.last_flash_message = message
        self.flash_type = ftype

    def _push_history(self):
        if not hasattr(self, "view_history"):
            self.view_history = []
        entry = {
            "view": self.current_view,
            "band": self.create_badge_band,
            "sub_id": self.selected_review_sub_id,
            "submission_badge_id": self.cosmonaut_submission_badge_id,
            "assessment_badge_id": getattr(self, "assessment_selected_badge_id", None),
            "assessment_cosmo_id": getattr(self, "assessment_selected_cosmonaut_id", None),
        }
        if (
            not self.view_history
            or self.view_history[-1]["view"] != self.current_view
            or self.view_history[-1].get("band") != self.create_badge_band
            or self.view_history[-1].get("assessment_badge_id") != entry["assessment_badge_id"]
            or self.view_history[-1].get("assessment_cosmo_id") != entry["assessment_cosmo_id"]
        ):
            self.view_history.append(entry)
        if len(self.view_history) > 30:
            self.view_history.pop(0)

    def _get_filtered_mapping_member_ids(self, store, mode: str) -> List[str]:
        """Return currently visible active member IDs in Card 3 (cosmonauts) or Card 4 (reviewers)."""
        effective_band = self.create_badge_band if getattr(self, "create_badge_band", None) else self.mapping_selected_band
        active_roles = list(getattr(self, "mapping_selected_roles", []) or [])
        target_cid = store.get_effective_read_cycle_id()
        cycle_enr_band: Dict[str, str] = {}
        if store and store.db and store.db.conn:
            try:
                enr_rows = store.db.conn.execute(
                    "SELECT user_id, band_code FROM cycle_enrollments WHERE cycle_id = ?",
                    (target_cid,)
                ).fetchall()
                cycle_enr_band = {r["user_id"]: r["band_code"] for r in enr_rows if r["band_code"]}
            except Exception:
                cycle_enr_band = {}

        if mode == "cosmonauts":
            search = (getattr(self, "mapping_cosmo_search", "") or "").strip().lower()
            target_bands = {effective_band}
        else:
            search = (getattr(self, "mapping_reviewer_search", "") or "").strip().lower()
            hb = get_higher_bands(effective_band)
            r_bands = getattr(self, "mapping_selected_reviewer_bands", [self.mapping_selected_reviewer_band])
            target_bands = set([b for b in r_bands if b in hb] or ([hb[0]] if hb else []))

        ids: List[str] = []
        if target_bands and store and store.db and store.db.conn:
            try:
                rows = store.db.conn.execute(
                    "SELECT id, name, role, band FROM users WHERE status = 'active' ORDER BY band, name"
                ).fetchall()
                for r in rows:
                    eff_band = cycle_enr_band.get(r["id"]) or r["band"]
                    if eff_band not in target_bands:
                        continue
                    r_role = r["role"] or ""
                    if active_roles and r_role not in active_roles:
                        continue
                    if search and search not in (r["name"] or "").lower() and search not in r_role.lower():
                        continue
                    ids.append(r["id"])
            except Exception:
                ids = []
        if not ids:
            if mode == "cosmonauts":
                ids = [m["id"] for m in filter_members_by_band_and_roles(effective_band, active_roles, search)]
            else:
                ids = [m["id"] for m in filter_reviewers_by_band_and_roles(list(target_bands), active_roles, search)]
        return ids

    def _collect_badge_mapping_inputs(
        self,
        store,
        effective_band: str,
        b_id: str,
        b_title: str,
        b_code: str,
        prefer_selected_cosmonauts: bool = False
    ) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
        """Collect accepted requests, cosmonaut IDs, and review dates independently for a badge."""
        requests = store.get_mapping_requests()

        def _is_badge_req(r: Dict[str, Any]) -> bool:
            if r.get("band") != effective_band:
                return False
            r_bid = r.get("badge_id", "")
            r_b = r.get("badge", "")
            if b_id and r_bid and r_bid == b_id:
                return True
            if r_b and (r_b in (b_title, b_code, b_id) or (b_title and b_title in r_b)):
                return True
            return False

        badge_reqs = [r for r in requests if _is_badge_req(r)]
        if not badge_reqs:
            badge_reqs = [r for r in requests if r.get("band") == effective_band and not r.get("badge_id")]

        accepted_reqs = [r for r in badge_reqs if r.get("status") == "accepted"]

        req_cosmo_ids: List[str] = []
        seen_c = set()
        for r in badge_reqs:
            if r.get("status") == "rejected":
                continue
            for cid in r.get("cosmonaut_ids") or []:
                if cid and cid not in seen_c:
                    seen_c.add(cid)
                    req_cosmo_ids.append(cid)

        sel_cosmo = list(getattr(self, "mapping_selected_cosmonauts", []) or [])
        if prefer_selected_cosmonauts and sel_cosmo:
            cosmo_ids = sel_cosmo
        else:
            cosmo_ids = req_cosmo_ids if req_cosmo_ids else sel_cosmo

        r_dates: List[str] = []
        for r in accepted_reqs + badge_reqs:
            if r.get("review_dates"):
                r_dates = list(r.get("review_dates"))
                break
        if not r_dates:
            r_dates = list(getattr(self, "mapping_review_dates", []) or [])

        return accepted_reqs, cosmo_ids, r_dates

    def _commit_badge_mapping(
        self,
        store,
        effective_band: str,
        b_id: str,
        b_title: str,
        b_code: str,
        accepted_reqs: List[Dict[str, Any]],
        cosmo_ids: List[str],
        review_dates: List[str],
        roles: Optional[List[str]] = None
    ) -> int:
        """Persist balanced reviewer-to-cosmonaut mappings across band_mappings, badge_timelines, and Badge."""
        import time
        curr_cid = store.get_effective_read_cycle_id()
        store.band_mappings = [
            m for m in store.band_mappings
            if not (
                (m.get("cycle_id") or DEFAULT_CYCLE_ID) == curr_cid
                and m.get("band") == effective_band
                and (
                    (b_id and m.get("badge_id") == b_id)
                    or m.get("badge") in (b_title, b_code, b_id)
                )
            )
        ]
        if store.db and store.db.conn:
            try:
                store.db.conn.execute(
                    "DELETE FROM band_mappings WHERE cycle_id = ? AND band = ? AND (badge_id = ? OR json_extract(data_json, '$.badge_id') = ? OR json_extract(data_json, '$.badge') = ?)",
                    (curr_cid, effective_band, b_id or "", b_id or "", b_title)
                )
            except Exception:
                pass

        num_guardians = len(accepted_reqs)
        guardian_buckets = {r["reviewer_id"]: [] for r in accepted_reqs}
        for idx, c_id in enumerate(cosmo_ids):
            target_g = accepted_reqs[idx % num_guardians]
            guardian_buckets[target_g["reviewer_id"]].append(c_id)

        r_dates = list(review_dates or [])
        roles_list = list(roles if roles is not None else getattr(self, "mapping_selected_roles", []))
        created_mappings = 0
        for req in accepted_reqs:
            g_id = req["reviewer_id"]
            assigned = guardian_buckets.get(g_id, [])
            if not assigned:
                continue
            mapping_record = {
                "id": f"map_{effective_band}_{b_id}_{g_id}_{int(time.time() * 1000)}_{created_mappings}",
                "band": effective_band,
                "badge": b_title,
                "badge_id": b_id or "",
                "badge_code": b_code or "",
                "roles": roles_list,
                "cosmonauts": assigned,
                "reviewer_band": req.get("reviewer_band", self.mapping_selected_reviewer_band),
                "reviewers": [g_id],
                "review_dates": r_dates,
                "review_duration_days": len(r_dates),
                "created_at": current_iso_timestamp(),
                "status": "active"
            }
            store.save_band_mapping(mapping_record)
            created_mappings += 1

        if b_id:
            start_d = r_dates[0] if r_dates else current_iso_timestamp()[:10]
            end_d = r_dates[-1] if r_dates else current_iso_timestamp()[:10]
            for idx, c_id in enumerate(cosmo_ids):
                target_g = accepted_reqs[idx % num_guardians]
                assigned_rev = target_g["reviewer_id"]
                tl_obj = BadgeTimeline(
                    badge_id=b_id,
                    cosmonaut_id=c_id,
                    assignment_date=current_iso_timestamp()[:10],
                    publication_date=current_iso_timestamp()[:10],
                    learning_start_date=start_d,
                    learning_end_date=end_d,
                    project_start_date=start_d,
                    project_end_date=end_d,
                    submission_deadline=end_d,
                    review_date=end_d,
                    expected_award_date=end_d,
                    status="active",
                    reviewer_id=assigned_rev,
                    review_window_json=json.dumps(r_dates)
                )
                store.save_timeline(tl_obj)
                store.add_activity(
                    event_type="cadet_mapped_to_badge",
                    actor_id=self.current_user.id if self.current_user else "guardian_1",
                    actor_name=self.current_user.name if self.current_user else "Guardian",
                    cosmonaut_id=c_id,
                    badge_id=b_id,
                    summary=f"Mapped {c_id} to '{b_title}' (Band {effective_band})",
                    details=f"Assigned Reviewer: {assigned_rev} &bull; Window: {', '.join(r_dates)}"
                )

            b_obj = store.get_badge(b_id)
            if b_obj:
                b_obj.is_allocated = True
                if not hasattr(b_obj, "is_published") or b_obj.is_published is None:
                    b_obj.is_published = False
                for c_id in cosmo_ids:
                    if c_id not in b_obj.assigned_cosmonaut_ids:
                        b_obj.assigned_cosmonaut_ids.append(c_id)
                if accepted_reqs:
                    b_obj.assigned_reviewer_id = accepted_reqs[0]["reviewer_id"]
                if not b_obj.default_timeline:
                    b_obj.default_timeline = {}
                b_obj.default_timeline.update({
                    "assignment_date": current_iso_timestamp()[:10],
                    "publication_date": current_iso_timestamp()[:10],
                    "learning_start_date": start_d,
                    "learning_end_date": end_d,
                    "project_start_date": start_d,
                    "project_end_date": end_d,
                    "submission_deadline": end_d,
                    "review_date": end_d,
                    "expected_award_date": end_d,
                    "review_dates": r_dates,
                    "review_duration_days": len(r_dates)
                })
                store.save_badge(b_obj)

                if store.db and store.db.conn:
                    try:
                        store.db.conn.execute("""
                            UPDATE badges SET
                                is_allocated = 1,
                                assigned_reviewer_id = ?,
                                assigned_cosmonaut_ids_json = ?,
                                default_timeline_json = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (
                            b_obj.assigned_reviewer_id,
                            json.dumps(b_obj.assigned_cosmonaut_ids),
                            json.dumps(b_obj.default_timeline),
                            current_iso_timestamp(),
                            b_obj.id
                        ))
                        store.db.conn.commit()
                    except Exception as e:
                        print(f"Error updating badge in SQLite: {e}")

            store.mark_dirty()

        preview_key = f"{effective_band}::{b_id or b_title}"
        if hasattr(self, "mapping_staged_previews") and preview_key in self.mapping_staged_previews:
            self.mapping_staged_previews.pop(preview_key, None)

        store.add_activity(
            event_type="badge_mapped",
            actor_id=self.current_user.id if self.current_user else "guardian_1",
            actor_name=self.current_user.name if self.current_user else "Guardian",
            cosmonaut_id="",
            badge_id=b_id or "",
            summary=f"Equally Mapped {len(cosmo_ids)} Cosmonauts across {len(accepted_reqs)} Accepted Reviewers for '{b_title}' ({effective_band})",
            details=f"Badge: {b_title} &bull; Review Dates: {', '.join(r_dates)} &bull; Saved to Badge & SQLite"
        )
        return created_mappings

    def resolve_mapping_badge(self, store, band: str = None, badge_ref_override: str = "", badge_id_override: str = "") -> Tuple[str, str, str]:
        """
        Returns (badge_id, badge_title, badge_code) for the currently selected or specified mapping badge
        scoped strictly to the given or active band.
        """
        target_band = band or (self.create_badge_band if getattr(self, "create_badge_band", None) else self.mapping_selected_band)
        target_cid = store.get_effective_read_cycle_id()
        b_id = badge_id_override or ("" if badge_ref_override else getattr(self, "mapping_selected_badge_id", ""))
        b_ref = badge_ref_override or ("" if badge_id_override else getattr(self, "mapping_selected_badge", ""))

        # 1. If b_ref is specified, prioritize matching b_ref
        if b_ref:
            if store.db and store.db.conn:
                try:
                    row = store.db.conn.execute(
                        "SELECT id, title, code, target_band FROM badges WHERE cycle_id = ? AND (title = ? OR code = ? OR id = ?) AND (target_band = ? OR ? = '')",
                        (target_cid, b_ref, b_ref, b_ref, target_band, target_band)
                    ).fetchone()
                    if row:
                        return row["id"], row["title"], row["code"]
                except Exception:
                    pass

            for b in store.get_all_badges(cycle_id=target_cid):
                if not target_band or getattr(b, "target_band", "") == target_band:
                    if b.title == b_ref or b.code == b_ref or b.id == b_ref:
                        return b.id, b.title, b.code

            return b_id or "", b_ref, b_ref

        # 2. If b_id is specified
        if b_id:
            if store.db and store.db.conn:
                try:
                    row = store.db.conn.execute(
                        "SELECT id, title, code, target_band FROM badges WHERE id = ? AND cycle_id = ? AND (target_band = ? OR ? = '')",
                        (b_id, target_cid, target_band, target_band)
                    ).fetchone()
                    if row:
                        return row["id"], row["title"], row["code"]
                except Exception:
                    pass

            for b in store.get_all_badges(cycle_id=target_cid):
                if not target_band or getattr(b, "target_band", "") == target_band:
                    if b.id == b_id:
                        return b.id, b.title, b.code

            return b_id, b_ref or "Badge", b_ref or "BDG"

        # 3. Fallback to first available approved badge in this band ONLY if neither b_ref nor b_id is provided
        if store.db and store.db.conn:
            try:
                row = store.db.conn.execute(
                    "SELECT id, title, code FROM badges WHERE target_band = ? AND cycle_id = ? AND workflow_status IN ('approved', 'ready_for_review') LIMIT 1",
                    (target_band, target_cid)
                ).fetchone()
                if row:
                    return row["id"], row["title"], row["code"]
            except Exception:
                pass

        return "", "Badge", "BDG"

    # ------------------------------------------------------------------------------------------
    # CENTRAL ACTION AUTHORISATION. The browser chooses the action name, so the server must decide whether
    # the signed-in user may run it. These actions change organisation-wide state (badges, mappings,
    # allotments, cycles, salaries, announcements, final marks) and are Guardian-only.
    # ------------------------------------------------------------------------------------------
    _GUARDIAN_ONLY_ACTIONS = frozenset({
        # the Guardian's final decision on a submission can be undone only by the Guardian
        "open_revoke_decision_confirm", "revoke_guardian_decision",
        # cycles & appraisals (salary / hike / promotion)
        "activate_cycle", "create_six_month_cycle", "calculate_cycle_appraisals",
        "update_cycle_appraisal", "finalize_and_close_cycle", "reset_demo_data",
        # badge authoring & publication
        "save_generated_badge", "create_badge", "save_badge_edits", "send_badge_review_request", "cancel_badge_reviewer", "manage_badge_reviewer",
        "add_custom_capability", "add_custom_skill", "save_badge_form",
        "publish_and_unlock_badge", "publish_badge", "unpublish_badge", "revoke_badge",
        # mapping & allotment
        "save_band_mapping", "delete_band_mapping", "edit_band_mapping", "send_mapping_requests",
        "save_allotment_timeline", "delete_mapping_request", "resend_mapping_request", "save_staged_mapping",
        "execute_cosmonaut_mapping", "clear_band_mappings", "reset_all_mapping_state", "reset_mapping_demo",
        # who is mapped to whom / the schedule: Guardian-only views
        "open_badge_mapping_modal", "open_badge_timeline_modal", "open_badge_timeline_mapping_modal",
        "confirm_publish_badge", "confirm_revoke_badge",
        # learning materials, extensions, announcements
        "save_bulk_materials", "save_material_form", "update_material", "delete_material",
        "submit_extension_decision", "broadcast_announcement",
        # final assessment / badge award
        "submit_guardian_final_assessment", "earn_badge", "award_badge",
    })

    def _reviewer_cadets_for_badge(self, reviewer_id: str, badge_id: str) -> set:
        """Cadets a reviewer is mapped to for one badge (timelines, band mappings, badge assignment)."""
        return store.get_reviewer_mapped_cosmonaut_ids(reviewer_id, badge_id)

    def _is_guardian_user(self) -> bool:
        u = self.current_user
        if not u:
            return False
        roles = set(getattr(u, "roles", None) or []) | {getattr(u, "role", "")}
        return bool(roles & {"guardian", "admin"}) or u.id in ("guardian_1", "admin")

    def _can_open_badge_review(self, badge) -> bool:
        """The reviewer a badge was sent to (it is in their Review Requests queue) - or a Guardian - may open its review page."""
        if not (self.current_user and badge):
            return False
        if self._is_guardian_user():
            return True
        if not is_reviewer_band(getattr(self.current_user, "band", "")):
            return False
        uid = self.current_user.id
        if getattr(badge, "assigned_reviewer_id", "") == uid:
            return True
        return any(r.get("id") == badge.id for r in store.get_badge_review_requests_for_user(uid))

    def _badge_review_edit_denied(self, badge) -> Optional[str]:
        """Why the signed-in user may not edit / decide this badge now (None = allowed): it must be awaiting review and
        the user must be its assigned reviewer (Reviewer_Band > Badge_Band, not the author) or a Guardian."""
        if not (self.current_user and badge):
            return "Badge not found."
        status = getattr(badge, "workflow_status", "")
        if status != "pending_review":
            return f"This badge is '{status or 'not submitted'}' and is no longer awaiting review, so it can't be edited."
        return store.badge_review_denied_reason(badge.id, self.current_user.id)

    _CYCLE_READONLY_SAFE_ACTIONS = {
        "login", "select_demo_account", "logout", "reset_demo_data", "go_back",
        "nav_guardian", "nav_cosmonaut", "nav_to_submit_badge",
        "select_cycle", "activate_cycle", "open_create_cycle_modal", "create_six_month_cycle",
        "calculate_cycle_appraisals", "update_cycle_appraisal", "finalize_and_close_cycle",
        "view_cycle_candidate_detail", "filter_cycle_performance",
        "select_create_badge_band", "close_modal", "toggle_notifications_modal",
        "open_badge_detail_modal", "view_marksheet", "view_material_preview",
        "filter_materials_badge", "filter_materials_type", "view_submission_artifact",
        "select_guardian_cosmo_filter", "filter_guardian_risk", "filter_guardian_reviews",
        "filter_assessment_power", "filter_assessment_capability",
        "open_assessment_badge", "close_assessment_badge",
        "open_assessment_cosmonaut", "close_assessment_cosmonaut",
        "filter_guardian_allotment", "filter_badge_approval",
        "search_badge_approval", "open_badge_for_review", "open_badge_activity_log", "open_cosmonaut_badge_page", "open_reviewer_badge_review",
        "toggle_cosmonaut_badge_card", "open_cosmonaut_badge_preview", "toggle_reviewer_badge_expand",
        "filter_cosmo_requests", "search_cosmo_requests", "change_submission_target_badge",
        "change_results_badge", "select_results_marksheet", "open_badge_marksheet", "open_submission_review_page", "change_viewer_tab",
        "open_reviewer_assessment_page",
        "open_reviewer_badge_timeline_modal", "open_badge_timeline_mapping_modal", "open_badge_mapping_modal", "open_badge_timeline_modal", "open_allocated_project_modal", "open_allocated_project_page",
        "open_cosmonaut_reviewer_modal", "open_cosmonaut_timeline_modal",
        "view_allocated_project", "recalc_rubric_total", "select_mapping_band",
        "select_mapping_badge", "select_mapping_review_anchor", "set_mapping_review_direction",
        "set_mapping_review_duration", "set_mapping_review_mode", "set_mapping_date_range",
        "jump_mapping_calendar_today", "open_mapping_calendar_modal",
        "toggle_mapping_badge_card", "open_mapping_badge_detail", "sync_mapping_requests", "sync_badge_reviews",
        "change_mapping_calendar_month", "cancel_edit_band_mapping", "reset_mapping_selection",
        "view_saved_badge", "search_skills", "preview_new_badge", "open_locked_milestone_notice",
        "mark_announcement_as_read", "set_list_page"
    }

    # ==========================================================================
    # ACTION & EVENT HANDLER
    # ==========================================================================

    def _expire_overdue_mapping_requests(self):
        """24-hour rule: a pending mapping request nobody answered in time is auto-declined (and both sides are told)."""
        try:
            expired = store.expire_overdue_mapping_requests()
        except Exception as exc:  # the sweep must never block the action the user actually asked for
            print(f"[Controller] mapping-request expiry sweep failed: {exc!r}")
            return
        for req in expired:
            try:
                self._notify_mapping_request_expired(req)
            except Exception as exc:  # a failed notice must never undo the expiry or block the user's action
                print(f"[Controller] could not notify about expired request {req.get('id')}: {exc!r}")

    def _notify_mapping_request_expired(self, req: Dict[str, Any]):
        title = req.get("badge", "Badge")
        band = req.get("band", "")
        rev_name = req.get("reviewer_name", "The reviewer")
        store.add_activity(
            event_type="mapping_request_expired",
            actor_id="guardian_1",          # activity_events.actor_id must reference a real user
            actor_name="System (auto-expiry)",
            cosmonaut_id="",
            badge_id=req.get("badge_id", ""),
            summary=f"Mapping Request Expired for '{title}' (Band {band})",
            details=f"{rev_name} did not respond within 24 hours, so the request was treated as declined ({req.get('id', '')}).",
        )
        store.add_notification(
            recipient_id=req.get("reviewer_id", ""),
            title=f"Review Request Expired: {title}",
            message=f"You did not respond to the '{title}' (Band {band}) review request within 24 hours, so it was closed. Ask the Guardian to resend it.",
            link_section="c_requests",
            event_type="mapping_request_expired",
            related_badge_id=req.get("badge_id", ""),
        )
        store.add_notification(
            recipient_id="guardian_1",
            title=f"Mapping Request Expired: {title}",
            message=f"{rev_name} did not respond to the '{title}' (Band {band}) request within 24 hours. It is now counted as not accepted - resend it from the badge's request history.",
            link_section="g_mapping",
            event_type="mapping_request_expired",
            related_badge_id=req.get("badge_id", ""),
        )

    def _expire_overdue_badge_reviews(self):
        """48-hour rule: a badge review nobody decided in time is closed (badge kept as it is, reviewer keeps a read-only view)."""
        try:
            store.expire_overdue_badge_reviews()
        except Exception as exc:  # the sweep must never block the action the user actually asked for
            print(f"[Controller] badge-review expiry sweep failed: {exc!r}")

    def handle_event(self, action: str, payload_json: str = "{}"):
        self._expire_overdue_mapping_requests()
        self._expire_overdue_badge_reviews()
        if action in self._GUARDIAN_ONLY_ACTIONS and not self._is_guardian_user():
            self.set_flash("You do not have permission to perform that action.", "error")
            print(f"[Controller] DENIED guardian-only action '{action}' for user "
                  f"{getattr(self.current_user, 'id', None)!r}")
            self._last_render_source = f"action:{action}"
            self.render()
            return
        eff_cid = self._get_effective_cycle_id()
        curr_cyc = store.get_cycle(eff_cid)
        if curr_cyc and getattr(curr_cyc, "status", "active") == "closed" and action not in self._CYCLE_READONLY_SAFE_ACTIONS:
            self.set_flash(
                f"Cycle '{curr_cyc.name}' is closed (Read-Only Archive). Switch to an active cycle or launch a new 6-month cycle to make changes.",
                "error"
            )
            with store.cycle_scope(eff_cid):
                self.sync_storage()
                self.render()
            return
        with store.cycle_scope(eff_cid):
            try:
                return self._handle_event_impl(action, payload_json)
            except ActionDenied as exc:
                self.set_flash(str(exc), "error")
            except StorageWriteError as exc:
                # The write was rolled back; discard any half-applied in-memory change and tell the user.
                try:
                    store.resync_from_database()
                except Exception:
                    pass
                self.set_flash("Your change could not be saved (database busy). Nothing was modified - please try again.", "error")
                print(f"[Controller] write failure during '{action}': {exc}")
            except Exception as exc:  # never leave the UI frozen on an unexpected handler error
                import traceback
                traceback.print_exc()
                self.set_flash("Something went wrong while processing that action. Please try again.", "error")
                print(f"[Controller] unexpected error during '{action}': {exc!r}")
            self._last_render_source = f"action:{action}"
            self.render()

    def _handle_event_impl(self, action: str, payload_json: str = "{}"):
        import time
        if isinstance(payload_json, str) and payload_json.startswith("{") and action != "update_badge_prompt":
            try:
                payload = json.loads(payload_json)
            except Exception:
                payload = payload_json
        else:
            payload = payload_json

        # --- Pagination (pure UI state, safe in every cycle) ---
        if action == "set_list_page":
            if isinstance(payload, dict):
                key = str(payload.get("key", ""))[:160]
                try:
                    page = max(1, int(payload.get("page", 1)))
                except (TypeError, ValueError):
                    page = 1
                if key:
                    self.list_pages[key] = page
                    if len(self.list_pages) > 200:  # bound the per-session state
                        self.list_pages.pop(next(iter(self.list_pages)))
            self._last_render_source = "action:set_list_page"
            self.render()
            return

        # --- Authentication Actions ---
        if action == "login":
            self.view_history = []
            self.reviewer_expanded_badge_id = None
            has_email_or_pwd = isinstance(payload, dict) and (
                "email" in payload or "password" in payload or bool(payload.get("require_password"))
            )
            if has_email_or_pwd:
                email_input = str(payload.get("email", "") or payload.get("username", "")).strip()
                pwd_input = payload.get("password", "")
                self.login_email_draft = email_input
                user, err_msg = store.authenticate_user(email_input, pwd_input, require_password=True)
            elif not _demo_mode_enabled():
                user, err_msg = None, "Password is required to sign in."
            else:
                ident = str(payload.get("username", "") if isinstance(payload, dict) else payload).strip().lower()
                user, err_msg = store.authenticate_user(ident, None, require_password=False)

            if user:
                self.login_error = None
                self.login_email_draft = ""
                self.current_user = user
                self.selected_cycle_id = store.get_active_cycle_id()
                user_roles = getattr(user, "roles", [user.role])
                is_guardian_user = (
                    user.id in ("guardian_1", "admin")
                    or user.role in ("guardian", "admin")
                    or "guardian" in user_roles
                    or "admin" in user_roles
                )
                if is_guardian_user:
                    self.current_view = "g_cycles"
                    self.create_badge_band = None
                else:
                    self.current_view = self.COSMONAUT_HOME_VIEW
                self.set_flash(f"Welcome back, {user.name}!", "success")
            else:
                self.current_user = None
                self.current_view = "login"
                self.login_error = err_msg or "Invalid email or password."
                self.set_flash(self.login_error, "error")

        elif action == "select_demo_account":
            self.view_history = []
            self.reviewer_expanded_badge_id = None
            user_id = payload.get("user_id") if isinstance(payload, dict) else payload
            user = store.get_user_by_id(user_id) if _demo_mode_enabled() else None
            if not user and not _demo_mode_enabled():
                self.login_error = "Quick login is disabled. Please sign in with your email and password."
                self.set_flash(self.login_error, "error")
            if user:
                self.login_error = None
                self.login_email_draft = ""
                self.current_user = user
                self.selected_cycle_id = store.get_active_cycle_id()
                user_roles = getattr(user, "roles", [user.role])
                is_guardian_user = (user.id in ("guardian_1", "admin") or user.role in ("guardian", "admin") or "guardian" in user_roles or "admin" in user_roles)
                if is_guardian_user:
                    self.current_view = "g_cycles"
                    self.create_badge_band = None
                else:
                    self.current_view = self.COSMONAUT_HOME_VIEW
                self.set_flash(f"Logged in as {user.name} ({', '.join(user_roles).replace('_', ' ').title()})", "success")

        # --- Create Badge & Reviewer Approval Workflow ---
        elif action == "select_create_badge_band":
            from starapp.badge_generator import BAND_DEFAULT_OUTCOME_SENTENCES
            self._push_history()
            band = payload if isinstance(payload, str) else (payload.get("band", "") if isinstance(payload, dict) else "")
            band = band.strip() if band else None
            self.create_badge_band = band
            self.current_view = "g_create_badge"
            if band:
                self.create_badge_metadata["code"] = f"{band}-HDW-01"
                self.create_badge_metadata["title"] = f"Band {band} Systems & Hardware Architecture"
                self.create_badge_outcome_sentence = BAND_DEFAULT_OUTCOME_SENTENCES.get(band, "Identify CPU, memory, storage, and GPU components in a given system spec and describe their basic roles")
                # Do NOT pre-fill badge data — user must click "Create Badge" to generate via Gemini
                self.created_badge_data = None
                self.is_editing_badge = False
                revs = store.get_eligible_badge_reviewers(band)
                if revs:
                    self.create_badge_reviewer_id = revs[0]["id"]
                else:
                    self.create_badge_reviewer_id = None
            else:
                self.created_badge_data = None
            self.create_badge_json_error = None

        elif action in ["update_badge_power", "change_badge_power"]:
            from starapp.badge_generator import generate_badge_data
            power = payload if isinstance(payload, str) else payload.get("power", "Tech")
            self.create_badge_power = power
            if self.create_badge_band and self.created_badge_data is not None:
                self.created_badge_data = generate_badge_data(
                    band=self.create_badge_band,
                    power=self.create_badge_power,
                    capability=self.create_badge_capability,
                    skill=self.create_badge_skill,
                    outcome_sentence=self.create_badge_outcome_sentence
                )

        elif action in ["update_badge_capability", "change_badge_capability"]:
            from starapp.badge_generator import CAPABILITY_SKILLS_MAP, generate_badge_data
            cap = payload if isinstance(payload, str) else payload.get("capability", "Data & Machine")
            self.create_badge_capability = cap
            valid_skills = CAPABILITY_SKILLS_MAP.get(cap, ["Hardware"])
            if self.create_badge_skill not in valid_skills:
                self.create_badge_skill = valid_skills[0]
            if self.create_badge_band and self.created_badge_data is not None:
                self.created_badge_data = generate_badge_data(
                    band=self.create_badge_band,
                    power=self.create_badge_power,
                    capability=self.create_badge_capability,
                    skill=self.create_badge_skill,
                    outcome_sentence=self.create_badge_outcome_sentence
                )

        elif action in ["update_badge_skill", "change_badge_skill"]:
            from starapp.badge_generator import generate_badge_data
            skill = payload if isinstance(payload, str) else payload.get("skill", "Hardware")
            self.create_badge_skill = skill
            if self.create_badge_band and self.created_badge_data is not None:
                self.created_badge_data = generate_badge_data(
                    band=self.create_badge_band,
                    power=self.create_badge_power,
                    capability=self.create_badge_capability,
                    skill=self.create_badge_skill,
                    outcome_sentence=self.create_badge_outcome_sentence
                )

        elif action == "change_badge_outcome_sentence":
            sent = payload if isinstance(payload, str) else payload.get("outcome_sentence", "")
            self.create_badge_outcome_sentence = sent

        elif action == "on_badge_generated":
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            if isinstance(payload, dict):
                b_data = payload.get("badge_data", payload)
                # Strictly prioritize active band already selected in workspace
                payload_band = payload.get("band")
                if self.create_badge_band:
                    current_band = self.create_badge_band
                elif payload_band:
                    self.create_badge_band = payload_band
                    current_band = payload_band
                else:
                    current_band = "B1"

                if isinstance(b_data, dict):
                    b_data["target_band"] = current_band
                    skill = b_data.get("skill") or self.create_badge_skill
                    cap = b_data.get("capability") or self.create_badge_capability
                    power = b_data.get("power") or self.create_badge_power
                    suffix = "Foundations" if current_band in ("B1", "B2") else ("Architecture" if current_band in ("B3", "B4") else "Mastery")
                    title = b_data.get("title") or f"{skill} {suffix}"
                    b_data["title"] = title
                    outcomes = b_data.get("outcomes") or []
                    topics = b_data.get("learning_topics") or []

                    # Align band in location and description
                    b_data["location"] = f"{title} -> {skill} -> {cap} -> {power} -> Band {current_band}"
                    desc = b_data.get("description", "")
                    if not desc or "Foundational badge" in desc or (desc.startswith("B1 badge") and current_band != "B1"):
                        b_data["description"] = f"{current_band} badge specializing in {skill} under the {cap} capability ({power} domain). {self.create_badge_outcome_sentence or ''}".strip()
                    elif desc.startswith("B1 badge") and current_band != "B1":
                        b_data["description"] = f"{current_band} badge" + desc[8:]

                    from starapp.badge_generator import build_practice_project_prompt, build_learning_resources_prompt
                    p_prompt = b_data.get("practice_prompt", "")
                    if not p_prompt or len(p_prompt.strip()) < 120 or "\n-" not in p_prompt:
                        p_prompt = build_practice_project_prompt(title, skill, cap, power, current_band, topics, outcomes)
                        b_data["practice_prompt"] = p_prompt
                        b_data["practice_project"] = {
                            "intro": "Want some hands-on practice? Use this prompt to generate a practice project.",
                            "prompt": p_prompt,
                            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
                        }

                    r_prompt = b_data.get("resources_prompt", "")
                    if not r_prompt or len(r_prompt.strip()) < 120 or "\n-" not in r_prompt:
                        r_prompt = build_learning_resources_prompt(title, skill, cap, power, current_band, topics, outcomes)
                        b_data["resources_prompt"] = r_prompt
                        b_data["learning_resources"] = {
                            "intro": "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
                            "prompt": r_prompt,
                            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
                        }

                self.created_badge_data = b_data
                if "power" in payload: self.create_badge_power = payload["power"]
                if "capability" in payload: self.create_badge_capability = payload["capability"]
                if "skill" in payload: self.create_badge_skill = payload["skill"]
                if "outcome_sentence" in payload: self.create_badge_outcome_sentence = payload["outcome_sentence"]
                self.set_flash("Badge created successfully with Gemini AI!", "success")

        elif action == "toggle_edit_badge":
            self.is_editing_badge = not self.is_editing_badge

        elif action == "toggle_topic_completion":
            topic_idx = None
            if isinstance(payload, int):
                topic_idx = payload
            elif isinstance(payload, str):
                try:
                    p_obj = json.loads(payload)
                    if isinstance(p_obj, dict):
                        topic_idx = p_obj.get("index")
                    elif isinstance(p_obj, int):
                        topic_idx = p_obj
                except Exception:
                    if payload.isdigit():
                        topic_idx = int(payload)
            elif isinstance(payload, dict):
                topic_idx = payload.get("index")

            if topic_idx is not None and self.created_badge_data and "learning_topics" in self.created_badge_data:
                topics = self.created_badge_data["learning_topics"]
                if 0 <= topic_idx < len(topics):
                    curr = topics[topic_idx]
                    curr_completed = curr.get("completed", False) or curr.get("status", "").lower() == "completed"
                    curr["completed"] = not curr_completed
                    curr["status"] = "Completed" if not curr_completed else "In Progress"

        elif action == "save_badge_edits":
            if isinstance(payload, str):
                try: payload = json.loads(payload)
                except Exception: payload = {}
            if isinstance(payload, dict) and self.created_badge_data:
                from starapp.badge_generator import apply_badge_edits
                apply_badge_edits(self.created_badge_data, payload)
                t = self.created_badge_data.get("title", "")
                self.created_badge_data["location"] = f"{t} -> {self.create_badge_skill} -> {self.create_badge_capability} -> {self.create_badge_power} -> Band {self.create_badge_band}"
                self.is_editing_badge = False
                self.set_flash("Badge edits applied successfully.", "info")

        elif action == "save_generated_badge":
            payload_data = None
            if isinstance(payload, str) and payload.strip():
                try:
                    payload_data = json.loads(payload)
                except Exception:
                    payload_data = None
            elif isinstance(payload, dict):
                payload_data = payload

            if isinstance(payload_data, dict):
                if payload_data.get("band"):
                    self.create_badge_band = payload_data["band"]
                if payload_data.get("power"):
                    self.create_badge_power = payload_data["power"]
                if payload_data.get("capability"):
                    self.create_badge_capability = payload_data["capability"]
                if payload_data.get("skill"):
                    self.create_badge_skill = payload_data["skill"]
                if payload_data.get("badge_data") and isinstance(payload_data["badge_data"], dict):
                    self.created_badge_data = payload_data["badge_data"]
                    if "power" in self.created_badge_data:
                        self.create_badge_power = self.created_badge_data["power"]
                    if "capability" in self.created_badge_data:
                        self.create_badge_capability = self.created_badge_data["capability"]
                    if "skill" in self.created_badge_data:
                        self.create_badge_skill = self.created_badge_data["skill"]

            active_band = self.create_badge_band or "B1"
            if not self.created_badge_data:
                from starapp.badge_generator import generate_badge_data
                self.created_badge_data = generate_badge_data(
                    band=active_band,
                    power=self.create_badge_power,
                    capability=self.create_badge_capability,
                    skill=self.create_badge_skill,
                    outcome_sentence=self.create_badge_outcome_sentence
                )

            # Apply any direct DOM edit fields passed in payload
            if isinstance(payload_data, dict) and self.created_badge_data and isinstance(self.created_badge_data, dict):
                if payload_data.get("title"):
                    self.created_badge_data["title"] = str(payload_data["title"]).strip()
                if "description" in payload_data:
                    self.created_badge_data["description"] = str(payload_data["description"]).strip()
                if "outcomes" in payload_data:
                    if isinstance(payload_data["outcomes"], list):
                        self.created_badge_data["outcomes"] = payload_data["outcomes"]
                    elif isinstance(payload_data["outcomes"], str):
                        self.created_badge_data["outcomes"] = [o.strip() for o in payload_data["outcomes"].split("\n") if o.strip()]
                if "practice_prompt" in payload_data:
                    p_val = payload_data["practice_prompt"]
                    self.created_badge_data["practice_prompt"] = p_val
                    if "practice_project" not in self.created_badge_data or not isinstance(self.created_badge_data["practice_project"], dict):
                        self.created_badge_data["practice_project"] = {
                            "intro": "Want some hands-on practice? Use this prompt to generate a practice project.",
                            "prompt": p_val,
                            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
                        }
                    else:
                        self.created_badge_data["practice_project"]["prompt"] = p_val
                if "resources_prompt" in payload_data:
                    r_val = payload_data["resources_prompt"]
                    self.created_badge_data["resources_prompt"] = r_val
                    if "learning_resources" not in self.created_badge_data or not isinstance(self.created_badge_data["learning_resources"], dict):
                        self.created_badge_data["learning_resources"] = {
                            "intro": "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
                            "prompt": r_val,
                            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
                        }
                    else:
                        self.created_badge_data["learning_resources"]["prompt"] = r_val
                if "topics" in payload_data and isinstance(payload_data["topics"], list):
                    self.created_badge_data["learning_topics"] = payload_data["topics"]

            if self.created_badge_data:
                self.created_badge_data["target_band"] = active_band
                if self.create_badge_power:
                    self.created_badge_data["power"] = self.created_badge_data.get("power") or self.create_badge_power
                if self.create_badge_capability:
                    self.created_badge_data["capability"] = self.created_badge_data.get("capability") or self.create_badge_capability
                if self.create_badge_skill:
                    self.created_badge_data["skill"] = self.created_badge_data.get("skill") or self.create_badge_skill

            saved_title = self.created_badge_data.get('title') if self.created_badge_data else "Badge"
            success, msg, b_obj = store.save_generated_badge(
                self.created_badge_data,
                creator_id=self.current_user.id if self.current_user else "guardian_1"
            )
            if success:
                saved_title = b_obj.title if b_obj else saved_title
                self.created_badge_data = None  # Hide badge preview, stays on band workspace!
                self.create_badge_band = active_band  # Strictly preserve active band workspace!
                self.is_editing_badge = False
                self.set_flash(f"Badge '{saved_title}' saved successfully! View it anytime under Saved Badges below.", "success")
            else:
                self.set_flash(msg, "error")

        elif action == "view_saved_badge":
            badge_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            b = store.get_badge(badge_id)
            if b:
                if b.prompt_json:
                    try:
                        self.created_badge_data = json.loads(b.prompt_json)
                    except Exception:
                        self.created_badge_data = None
                if not self.created_badge_data:
                    from starapp.badge_generator import generate_badge_data
                    self.created_badge_data = generate_badge_data(
                        band=getattr(b, "target_band", "B1"),
                        power=getattr(b, "power", "Tech"),
                        capability=getattr(b, "capability", "Data & Machine"),
                        skill=getattr(b, "skill", "Hardware"),
                        outcome_sentence=self.create_badge_outcome_sentence
                    )
                if self.created_badge_data and isinstance(self.created_badge_data, dict):
                    if not self.created_badge_data.get("practice_project"):
                        p_prompt = self.created_badge_data.get("practice_prompt") or getattr(b, "project_requirements", "")
                        if p_prompt:
                            self.created_badge_data["practice_project"] = {
                                "intro": "Want some hands-on practice? Use this prompt to generate a practice project.",
                                "prompt": p_prompt,
                                "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
                            }
                    if not self.created_badge_data.get("learning_resources") and self.created_badge_data.get("resources_prompt"):
                        self.created_badge_data["learning_resources"] = {
                            "intro": "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
                            "prompt": self.created_badge_data.get("resources_prompt"),
                            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
                        }
                self.create_badge_band = getattr(b, "target_band", "B1")
                self.create_badge_power = getattr(b, "power", "Tech")
                self.create_badge_capability = getattr(b, "capability", "Data & Machine")
                self.create_badge_skill = getattr(b, "skill", "Hardware")
                self.is_editing_badge = False
                self.set_flash(f"Loaded saved badge '{b.title}'", "info")

        elif action == "add_custom_capability":
            if isinstance(payload, str):
                try:
                    p_obj = json.loads(payload)
                    cap_name = p_obj.get("name", payload) if isinstance(p_obj, dict) else payload
                except Exception:
                    cap_name = payload
            elif isinstance(payload, dict):
                cap_name = payload.get("name", "")
            else:
                cap_name = ""
            cap_name = cap_name.strip()
            if not cap_name:
                self.set_flash("Capability name cannot be empty.", "warning")
            else:
                success, msg = store.add_custom_capability(cap_name, created_by=self.current_user.id if self.current_user else "guardian_1")
                if success:
                    self.create_badge_capability = cap_name
                    skills = store.get_custom_skills(cap_name)
                    self.create_badge_skill = skills[0] if skills else f"{cap_name} Core"
                    self.set_flash(f"Custom capability '{cap_name}' added and saved to database.", "success")
                else:
                    self.set_flash(msg, "warning")

        elif action == "update_badge_skill":
            skill = payload if isinstance(payload, str) else payload.get("skill", "Hardware")
            self.create_badge_skill = skill

        elif action == "add_custom_skill":
            target_cap = self.create_badge_capability or "Data & Machine"
            if isinstance(payload, str):
                try:
                    p_obj = json.loads(payload)
                    if isinstance(p_obj, dict):
                        skill_name = p_obj.get("name", payload)
                        target_cap = p_obj.get("capability") or target_cap
                    else:
                        skill_name = payload
                except Exception:
                    skill_name = payload
            elif isinstance(payload, dict):
                skill_name = payload.get("name", "")
                target_cap = payload.get("capability") or target_cap
            else:
                skill_name = ""

            skill_name = skill_name.strip()
            if not skill_name:
                self.set_flash("Skill name cannot be empty.", "warning")
            else:
                success, msg = store.add_custom_skill(skill_name, capability_name=target_cap, created_by=self.current_user.id if self.current_user else "guardian_1")
                if success:
                    self.create_badge_capability = target_cap
                    self.create_badge_skill = skill_name
                    self.set_flash(f"Custom skill '{skill_name}' added under '{target_cap}' and saved to database.", "success")
                else:
                    self.set_flash(msg, "warning")

        elif action == "search_skills":
            self.create_badge_skill_search = payload if isinstance(payload, str) else payload.get("query", "")

        elif action == "select_badge_reviewer":
            rev_id = payload if isinstance(payload, str) else payload.get("reviewer_id", "")
            if self.create_badge_band:
                eligible, err_msg = store.verify_reviewer_eligibility(rev_id, self.create_badge_band)
                if not eligible:
                    self.set_flash(err_msg, "error")
                else:
                    self.create_badge_reviewer_id = rev_id
            else:
                self.create_badge_reviewer_id = rev_id

        elif action == "update_badge_prompt":
            if isinstance(payload, dict):
                if "prompt_json" in payload:
                    p_text = payload["prompt_json"]
                else:
                    p_text = json.dumps(payload, indent=2)
            else:
                p_text = str(payload)
            self.create_badge_prompt_json = p_text
            try:
                json.loads(p_text)
                self.create_badge_json_error = None
            except Exception as e:
                self.create_badge_json_error = str(e)

        elif action == "format_badge_prompt":
            try:
                p_obj = json.loads(self.create_badge_prompt_json)
                self.create_badge_prompt_json = json.dumps(p_obj, indent=2)
                self.create_badge_json_error = None
                self.set_flash("Prompt JSON formatted successfully.", "info")
            except Exception as e:
                self.create_badge_json_error = f"Cannot format invalid JSON: {e}"
                self.set_flash(f"JSON Syntax Error: {e}", "error")

        elif action == "preview_new_badge":
            if isinstance(payload, dict):
                for k in ["code", "title", "category", "description", "learning_outcomes", "learning_topics", "project_requirements"]:
                    if k in payload and payload[k] is not None:
                        self.create_badge_metadata[k] = str(payload[k]).strip()
                if "prompt_json" in payload and payload["prompt_json"]:
                    self.create_badge_prompt_json = payload["prompt_json"]

            if not self.create_badge_band:
                self.set_flash("Please select a target band for the badge.", "error")
            elif self.create_badge_band == "B6":
                self.set_flash("B6 badges cannot be assigned via standard reviewer workflow (executive council review required).", "error")
            elif not self.create_badge_reviewer_id:
                self.set_flash("Please select an eligible higher-band reviewer.", "error")
            else:
                is_elig, elig_err = store.verify_reviewer_eligibility(self.create_badge_reviewer_id, self.create_badge_band)
                if not is_elig:
                    self.set_flash(f"Selected reviewer ineligible: {elig_err}", "error")
                else:
                    try:
                        parsed_prompt = json.loads(self.create_badge_prompt_json)
                        if not isinstance(parsed_prompt, dict) or "prompt" not in parsed_prompt:
                            self.set_flash("Structured JSON prompt must be an object containing a 'prompt' property.", "error")
                        else:
                            code = self.create_badge_metadata.get("code", "").strip()
                            title = self.create_badge_metadata.get("title", "").strip()
                            if not code or not title:
                                self.set_flash("Badge Code and Title are required.", "error")
                            else:
                                self.active_modal = "badge_creation_preview"
                                self.modal_payload = {
                                    "target_band": self.create_badge_band,
                                    "power": self.create_badge_power,
                                    "capability": self.create_badge_capability,
                                    "skill": self.create_badge_skill,
                                    "reviewer_id": self.create_badge_reviewer_id,
                                    "code": code,
                                    "title": title,
                                    "category": self.create_badge_metadata.get("category", "Systems Engineering"),
                                    "description": self.create_badge_metadata.get("description", ""),
                                    "learning_outcomes": self.create_badge_metadata.get("learning_outcomes", ""),
                                    "learning_topics": self.create_badge_metadata.get("learning_topics", ""),
                                    "project_requirements": self.create_badge_metadata.get("project_requirements", ""),
                                    "prompt_json": self.create_badge_prompt_json
                                }
                    except Exception as e:
                        self.create_badge_json_error = str(e)
                        self.set_flash(f"Invalid JSON Prompt: {e}", "error")

        elif action == "create_badge":
            user_roles = getattr(self.current_user, "roles", [self.current_user.role]) if self.current_user else []
            if not self.current_user or ("guardian" not in user_roles and self.current_user.role != "guardian"):
                self.set_flash("Only Guardian / Training Mentors can author new badges.", "error")
            else:
                draft = (
                    payload
                    if (isinstance(payload, dict) and (payload.get("code") or payload.get("title")))
                    else (self.modal_payload if self.modal_payload else self.create_badge_metadata)
                )
                code = draft.get("code", "").strip()
                title = draft.get("title", "").strip()
                band = draft.get("target_band", self.create_badge_band)
                power = draft.get("power", self.create_badge_power)
                cap = draft.get("capability", self.create_badge_capability)
                skill = draft.get("skill", self.create_badge_skill)
                reviewer_id = draft.get("reviewer_id", self.create_badge_reviewer_id)
                prompt_json = draft.get("prompt_json", self.create_badge_prompt_json)

                all_b = store.get_all_badges()
                existing_badge_id = draft.get("badge_id") or draft.get("id")
                if not existing_badge_id:
                    # Check if there is an existing pending_review badge with this code
                    matching_pending = [b for b in all_b if b.code.lower() == code.lower() and getattr(b, "workflow_status", "") == "pending_review"]
                    if matching_pending:
                        existing_badge_id = matching_pending[0].id
                    else:
                        # If a published badge already uses this code, add a clean numeric increment
                        published_matching = [b for b in all_b if b.code.lower() == code.lower() and getattr(b, "workflow_status", "") != "pending_review"]
                        if published_matching:
                            code = f"{code}-{len(published_matching) + 1}"
                        existing_badge_id = f"badge_{code.lower().replace('-', '_')}"

                badge_id = existing_badge_id
                raw_outcomes = draft.get("learning_outcomes", "")
                if isinstance(raw_outcomes, list):
                    outcomes = [str(o).strip() for o in raw_outcomes if str(o).strip()]
                else:
                    outcomes = [o.strip() for o in str(raw_outcomes).replace("\n", ",").split(",") if o.strip()]
                raw_topics = draft.get("learning_topics", "")
                if isinstance(raw_topics, list):
                    topics = [str(t).strip() for t in raw_topics if str(t).strip()]
                else:
                    topics = [t.strip() for t in str(raw_topics).replace("\n", ",").split(",") if t.strip()]

                success, msg, *_ = store.create_badge_for_review(
                    badge_id=badge_id,
                    code=code,
                    title=title,
                    category=draft.get("category", "Systems Engineering"),
                    description=draft.get("description", ""),
                    target_band=band,
                    power=power,
                    capability=cap,
                    skill=skill,
                    prompt_json=prompt_json,
                    creator_id=self.current_user.id,
                    reviewer_id=reviewer_id,
                    learning_outcomes=outcomes,
                    learning_topics=topics,
                    project_requirements=draft.get("project_requirements", "")
                )

                if success:
                    rev_user = store.get_user_by_id(reviewer_id)
                    rev_name = rev_user.name if rev_user else reviewer_id
                    self.set_flash(f"Badge '{code}: {title}' successfully created and submitted to {rev_name} for approval.", "success")
                    self.active_modal = None
                    self.modal_payload = {}
                    self.current_view = "g_badge_approval"
                else:
                    self.set_flash(f"Failed to create badge: {msg}", "error")

        elif action == "filter_badge_approval":
            self.badge_approval_filter = payload if isinstance(payload, str) else payload.get("filter", "all")

        elif action == "search_badge_approval":
            self.badge_approval_search = payload if isinstance(payload, str) else payload.get("query", "")

        elif action == "open_badge_for_review":
            b_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            if badge:
                self.active_modal = "badge_inspect"
                self.modal_payload = {"badge_id": b_id}
            else:
                self.set_flash("Badge not found.", "warning")

        elif action == "open_badge_activity_log":
            b_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            b_id = str(b_id).strip().replace('"', '')
            if store.get_badge(b_id):
                self.active_modal = "badge_activity_log"
                self.modal_payload = {"badge_id": b_id}
            else:
                self.set_flash("Badge not found.", "warning")

        elif action in ("open_cosmonaut_badge_page", "toggle_cosmonaut_badge_card", "open_cosmonaut_badge_preview"):
            b_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            b_id = str(b_id).strip().replace('"', '')
            if action == "toggle_cosmonaut_badge_card" and self.current_view == "c_badge_detail" and self.cosmonaut_submission_badge_id == b_id:
                self._push_history()
                self.cosmonaut_expanded_badge_id = None
                self.current_view = "c_submission"
            else:
                self._push_history()
                self.cosmonaut_expanded_badge_id = b_id
                self.cosmonaut_submission_badge_id = b_id
                self.current_view = "c_badge_detail"
            self.active_modal = None

        elif action == "toggle_reviewer_badge_expand":
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            b_id = str(b_id).strip().replace('"', '')
            if getattr(self, "reviewer_expanded_badge_id", None) == b_id:
                self.reviewer_expanded_badge_id = ""
            else:
                self.reviewer_expanded_badge_id = b_id

        elif action == "edit_submitted_badge":
            b_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            if not badge:
                self.set_flash("Badge not found.", "warning")
            else:
                user_roles = getattr(self.current_user, "roles", [self.current_user.role]) if self.current_user else []
                is_assigned = (getattr(badge, "assigned_reviewer_id", "") == (self.current_user.id if self.current_user else ""))
                is_guardian = "guardian" in user_roles
                if not (is_assigned or is_guardian):
                    self.set_flash("Unauthorized: Only the assigned Badge Reviewer or Guardian can edit this submission.", "error")
                else:
                    self.active_modal = "badge_reviewer_edit"
                    self.modal_payload = {"badge_id": b_id}

        elif action == "open_reviewer_badge_review":
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            b_id = str(b_id).strip().replace('"', '')
            badge = store.get_badge(b_id)
            if not badge:
                self.set_flash("Badge not found.", "warning")
            elif not self._can_open_badge_review(badge):
                raise ActionDenied("This badge was not sent to you for review.")
            else:
                self._push_history()
                self.reviewer_review_badge_id = b_id
                self.reviewer_review_editing = False
                self.current_view = "c_badge_review"
                self.active_modal = None

        elif action == "toggle_reviewer_badge_edit":
            badge = store.get_badge(self.reviewer_review_badge_id) if self.reviewer_review_badge_id else None
            denied = self._badge_review_edit_denied(badge) if badge else "Badge not found."
            if self.reviewer_review_editing:
                self.reviewer_review_editing = False        # cancelling an edit is always allowed
            elif denied:
                self.set_flash(denied, "error")
            else:
                self.reviewer_review_editing = True

        elif action == "save_reviewer_badge_edits":
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            badge = store.get_badge(self.reviewer_review_badge_id) if self.reviewer_review_badge_id else None
            denied = self._badge_review_edit_denied(badge) if badge else "Badge not found."
            if denied:
                self.set_flash(denied, "error")
            elif not isinstance(payload, dict):
                self.set_flash("Nothing to save.", "warning")
            else:
                from starapp.badge_generator import structured_badge_from_row, apply_badge_edits
                data = structured_badge_from_row(badge)
                apply_badge_edits(data, payload)
                new_title = str(data.get("title", "")).strip()
                band = getattr(badge, "target_band", "") or "B1"
                clash = next((o for o in store.get_all_badges(cycle_id=getattr(badge, "cycle_id", None))
                              if o.id != badge.id and getattr(o, "target_band", "") == band and o.title.strip().lower() == new_title.lower()), None)
                if not new_title or not data.get("outcomes"):
                    self.set_flash("A badge needs a title and at least one outcome.", "warning")
                elif clash:
                    self.set_flash(f"Band {band} already has a badge titled '{clash.title}'. Pick a different title.", "warning")
                else:
                    skill, cap, power = getattr(badge, "skill", ""), getattr(badge, "capability", ""), getattr(badge, "power", "")
                    data["location"] = f"{new_title} -> {skill} -> {cap} -> {power} -> Band {band}"
                    data["reviewed_by"] = self.current_user.name
                    data["reviewed_at"] = current_iso_timestamp()
                    updates = {
                        "title": new_title,
                        "description": data.get("description", ""),
                        "learning_outcomes": data["outcomes"],
                        "learning_topics": [t.get("title", "") for t in data.get("learning_topics", []) if isinstance(t, dict)],
                        "project_requirements": data.get("practice_prompt", ""),
                        "prompt_json": json.dumps(data, indent=2),
                    }
                    ok, msg = store.update_badge_by_reviewer(badge.id, self.current_user.id, updates)
                    if ok:
                        self.reviewer_review_editing = False
                        if badge.creator_id and badge.creator_id != self.current_user.id:
                            store.add_notification(
                                recipient_id=badge.creator_id,
                                title=f"Badge edited by reviewer: {new_title}",
                                message=f"{self.current_user.name} corrected '{new_title}' (Band {band}) during review. The saved badge now shows the reviewer's changes.",
                                link_section="g_create_badge", event_type="badge_edited", related_badge_id=badge.id,
                            )
                        self.set_flash(f"Changes saved to '{new_title}'. The Guardian sees the same updated badge; it is still awaiting your decision.", "success")
                    else:
                        self.set_flash(f"Failed to save changes: {msg}", "error")

        elif action == "save_reviewed_badge":
            b_id = payload.get("badge_id") if isinstance(payload, dict) else ""
            badge = store.get_badge(b_id)
            if not badge:
                self.set_flash("Badge not found.", "warning")
            else:
                user_roles = getattr(self.current_user, "roles", [self.current_user.role]) if self.current_user else []
                is_assigned = (getattr(badge, "assigned_reviewer_id", "") == (self.current_user.id if self.current_user else ""))
                is_guardian = "guardian" in user_roles
                if not (is_assigned or is_guardian):
                    self.set_flash("Unauthorized: Only the assigned Badge Reviewer or Guardian can save edits.", "error")
                else:
                    updates = {
                        "title": payload.get("title", badge.title),
                        "power": payload.get("power", getattr(badge, "power", "Tech")),
                        "capability": payload.get("capability", getattr(badge, "capability", "Data & Machine")),
                        "skill": payload.get("skill", getattr(badge, "skill", "Hardware")),
                        "description": payload.get("description", badge.description),
                        "learning_outcomes": payload.get("learning_outcomes", badge.learning_outcomes),
                        "learning_topics": payload.get("learning_topics", badge.learning_topics),
                        "project_requirements": payload.get("project_requirements", badge.project_requirements),
                        "prompt_json": payload.get("prompt_json", getattr(badge, "prompt_json", "{}"))
                    }
                    reviewer_id = self.current_user.id if self.current_user else "reviewer_1"
                    reviewer_name = self.current_user.name if self.current_user else "Reviewer"
                    success, msg = store.update_badge_by_reviewer(b_id, reviewer_id, updates)
                    if success:
                        notes_val = payload.get("notes", "")
                        if notes_val and store.db and store.db.conn:
                            try:
                                store.db.conn.execute("UPDATE badge_review_events SET notes = ? WHERE badge_id = ? AND actor_id = ? ORDER BY timestamp DESC LIMIT 1", (notes_val, b_id, reviewer_id))
                            except Exception:
                                pass
                        if payload.get("and_approve", False):
                            ok, app_msg = store.approve_badge(b_id, reviewer_id, reviewer_name, notes=notes_val)
                            if ok:
                                self.set_flash(f"Badge '{badge.code}: {updates['title']}' updated and authorized successfully!", "success")
                            else:
                                self.set_flash(f"Edits saved, but authorization failed: {app_msg}", "warning")
                        else:
                            self.set_flash(f"Changes to '{badge.code}' saved successfully. Badge remains pending authorization.", "success")
                        self.active_modal = None
                        self.modal_payload = {}
                    else:
                        self.set_flash(f"Failed to update badge: {msg}", "error")

        elif action == "confirm_approve_badge":
            b_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            if not badge:
                self.set_flash("Badge not found.", "warning")
            else:
                user_roles = getattr(self.current_user, "roles", [self.current_user.role]) if self.current_user else []
                if "badge_reviewer" not in user_roles:
                    self.set_flash("Unauthorized: Only authorized Badge Reviewers can authorize badges.", "error")
                else:
                    self.active_modal = "badge_approval_confirm"
                    self.modal_payload = {"badge_id": b_id}

        elif action == "approve_submitted_badge":
            b_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            if not badge:
                self.set_flash("Badge not found.", "warning")
            else:
                user_roles = getattr(self.current_user, "roles", [self.current_user.role]) if self.current_user else []
                if "badge_reviewer" not in user_roles:
                    self.set_flash("Unauthorized: Only users with the Badge Reviewer role can approve badges.", "error")
                else:
                    success, msg = store.approve_badge(b_id, self.current_user.id)
                    if success:
                        self.set_flash(f"Badge '{badge.code}: {badge.title}' has been successfully authorized and approved.", "success")
                        self.active_modal = None
                        self.modal_payload = {}
                    else:
                        self.set_flash(f"Approval failed: {msg}", "error")

        elif action == "send_badge_review_request":
            if isinstance(payload, str) and payload.strip():
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            b_id = payload.get("badge_id", "")
            r_id = payload.get("reviewer_id", "")
            if not b_id or not r_id:
                self.set_flash("Please select an eligible higher-band reviewer.", "warning")
            else:
                creator_id = self.current_user.id if self.current_user else "guardian_1"
                success, msg = store.assign_and_request_badge_review(b_id, r_id, creator_id)
                if success:
                    self.set_flash(msg, "success")
                    if self.active_modal in ("badge_reviewer_edit", "badge_reviewer_manage"):
                        self.active_modal = None
                        self.modal_payload = {}
                else:
                    self.set_flash(msg, "error")

        elif action == "manage_badge_reviewer":
            b_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            b_id = str(b_id).strip().replace('"', '')
            if store.get_badge(b_id):
                self.active_modal = "badge_reviewer_manage"
                self.modal_payload = {"badge_id": b_id}
            else:
                self.set_flash("Badge not found.", "warning")

        elif action == "cancel_badge_reviewer":
            b_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            b_id = str(b_id).strip().replace('"', '')
            if not store.get_badge(b_id):
                self.set_flash("Badge not found.", "warning")
            else:
                actor_id = self.current_user.id if self.current_user else "guardian_1"
                success, msg = store.cancel_badge_review_request(b_id, actor_id)
                self.set_flash(msg, "success" if success else "error")
                if success and self.active_modal in ("badge_reviewer_edit", "badge_reviewer_manage"):
                    self.active_modal = None
                    self.modal_payload = {}

        elif action == "confirm_return_badge":
            b_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            if not badge:
                self.set_flash("Badge not found.", "warning")
            else:
                self.active_modal = "badge_reviewer_return"
                self.modal_payload = {"badge_id": b_id}

        elif action == "return_submitted_badge":
            if isinstance(payload, str) and payload.strip():
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {"badge_id": payload}
            b_id = payload.get("badge_id", "")
            notes = payload.get("notes", "")
            badge = store.get_badge(b_id)
            if not badge:
                self.set_flash("Badge not found.", "warning")
            else:
                rev_id = self.current_user.id if self.current_user else "guardian_1"
                rev_name = self.current_user.name if self.current_user else "Reviewer"
                success, msg = store.return_badge(b_id, rev_id, rev_name, notes)
                if success:
                    self.set_flash(f"Badge '{badge.code}' returned with revision feedback.", "info")
                    self.active_modal = None
                    self.modal_payload = {}
                else:
                    self.set_flash(msg, "error")

        elif action == "filter_cosmo_requests":
            self.cosmo_requests_tab = payload if isinstance(payload, str) else payload.get("tab", "all")

        elif action == "search_cosmo_requests":
            self.cosmo_requests_search = payload if isinstance(payload, str) else payload.get("query", "")

        elif action == "logout":
            self.current_user = None
            self.current_view = "login"
            self.active_modal = None
            self.login_error = None
            self.login_email_draft = ""
            self.view_history = []
            self.set_flash("You have been signed out.", "info")

        elif action == "reset_demo_data":
            store.reset_to_seed()
            self.selected_cycle_id = store.get_active_cycle_id()
            self.active_modal = None
            self.view_history = []
            self.set_flash("StarApp demo data has been restored to factory default.", "success")

        # --- 6-Month Cycle & Performance Management Actions ---
        elif action == "select_cycle":
            c_id = payload if isinstance(payload, str) else payload.get("cycle_id", "")
            c_id = str(c_id).strip().replace('"', '')
            cyc = store.get_cycle(c_id)
            if cyc:
                self.selected_cycle_id = cyc.id
                self.cosmonaut_expanded_badge_id = None
                self.cosmonaut_submission_badge_id = None
                self.cosmonaut_results_badge_id = None
                self.reviewer_expanded_badge_id = None
                self.selected_review_sub_id = None
                self.assessment_selected_badge_id = None
                self.assessment_selected_cosmonaut_id = None
                self.selected_guardian_cosmo_id = "all"
                self.created_badge_data = None
                self.mapping_selected_badge = ""
                self.mapping_selected_badge_id = ""
                self.editing_mapping_id = None
                self.active_modal = None
                st_note = "Previous Cycle Archive (Filtered View)" if cyc.status == "closed" else "Active Cycle"
                self.set_flash(f"Global Filter set to {cyc.name} ({cyc.start_date} → {cyc.end_date}) — {st_note}.", "info")
                self.sync_storage()
                self._last_render_source = f"action:{action}"
                with store.cycle_scope(cyc.id):
                    self.render()
                return
            else:
                self.set_flash("Selected performance cycle not found.", "error")

        elif action == "activate_cycle":
            c_id = payload if isinstance(payload, str) else payload.get("cycle_id", "")
            c_id = str(c_id).strip().replace('"', '')
            creator_id = self.current_user.id if self.current_user else "guardian_1"
            ok, msg, act_cyc = activate_cycle(c_id, store, actor_id=creator_id)
            if ok and act_cyc:
                self.selected_cycle_id = act_cyc.id
                self.created_badge_data = None
                self.mapping_selected_badge = ""
                self.mapping_selected_badge_id = ""
                self.editing_mapping_id = None
                self.active_modal = None
                self.set_flash(msg, "success")
                self.sync_storage(force_data=True)
                self._last_render_source = f"action:{action}"
                with store.cycle_scope(act_cyc.id):
                    self.render()
                return
            else:
                self.set_flash(msg, "error")

        elif action == "open_create_cycle_modal":
            self.active_modal = "create_cycle_modal"
            self.modal_payload = {}

        elif action == "create_six_month_cycle":
            p_dict = payload if isinstance(payload, dict) else {}
            creator_id = self.current_user.id if self.current_user else "guardian_1"
            ok, msg, new_cyc = create_new_six_month_cycle(
                store=store,
                name=p_dict.get("name", ""),
                start_date=p_dict.get("start_date", ""),
                end_date=p_dict.get("end_date", ""),
                code=p_dict.get("code", ""),
                created_by=creator_id,
                clone_badges_from_cycle_id=p_dict.get("clone_badges_from_cycle_id", ""),
                auto_close_previous=bool(p_dict.get("auto_close_previous", False)),
                notes=p_dict.get("notes", ""),
                set_as_active=bool(p_dict.get("set_as_active", True))
            )
            if ok and new_cyc:
                self.selected_cycle_id = new_cyc.id
                self.created_badge_data = None
                self.create_badge_band = None
                self.mapping_selected_badge = ""
                self.mapping_selected_badge_id = ""
                self.editing_mapping_id = None
                self.active_modal = None
                self.current_view = "g_cycles"
                self.set_flash(msg, "success")
                self.sync_storage(force_data=True)
                self._last_render_source = f"action:{action}"
                with store.cycle_scope(new_cyc.id):
                    self.render()
                return
            else:
                self.set_flash(msg, "error")

        elif action == "calculate_cycle_appraisals":
            p_dict = payload if isinstance(payload, dict) else {}
            c_id = p_dict.get("cycle_id") or self._get_effective_cycle_id()
            actor_id = self.current_user.id if self.current_user else "guardian_1"
            saved = calculate_and_save_cycle_appraisals(c_id, store, actor_id=actor_id)
            self.set_flash(f"Calculated cycle performance (Cosmonaut + Reviewer) for {len(saved)} members.", "success")

        elif action == "update_cycle_appraisal":
            p_dict = payload if isinstance(payload, dict) else {}
            c_id = p_dict.get("cycle_id") or self._get_effective_cycle_id()
            u_id = p_dict.get("user_id", "")
            cyc = store.get_cycle(c_id)
            if cyc and cyc.status == "closed":
                self.set_flash("Cannot edit appraisals on a finalized/closed cycle.", "error")
            elif u_id:
                calculate_and_save_cycle_appraisals(c_id, store, actor_id=self.current_user.id if self.current_user else "guardian_1", preserve_manual_overrides=True)
                app_obj = store.get_cycle_appraisal(c_id, u_id)
                if app_obj:
                    base_sal = float(p_dict.get("base_salary", app_obj.base_salary) or 0.0)
                    hike_pct = float(p_dict.get("approved_hike_pct", app_obj.approved_hike_pct) or 0.0)
                    bonus_amt = float(p_dict.get("bonus_amount", app_obj.bonus_amount) or 0.0)
                    promo_band = str(p_dict.get("recommended_promotion_band", "") or "")
                    remarks = str(p_dict.get("guardian_remarks", "") or "")
                    hike_amt = round(base_sal * (hike_pct / 100.0), 2) if base_sal > 0 else 0.0
                    new_sal = round(base_sal + hike_amt, 2) if base_sal > 0 else 0.0

                    app_obj.base_salary = base_sal
                    app_obj.approved_hike_pct = hike_pct
                    app_obj.hike_amount = hike_amt
                    app_obj.new_salary = new_sal
                    app_obj.bonus_amount = bonus_amt
                    app_obj.recommended_promotion_band = promo_band
                    app_obj.guardian_remarks = remarks
                    app_obj.status = "adjusted"
                    store.save_cycle_appraisal(app_obj)

                    # Also update base salary inside cycle_enrollments
                    enr = next((e for e in store.get_cycle_enrollments(c_id) if e.user_id == u_id), None)
                    if enr:
                        enr.base_salary = base_sal
                        store.save_cycle_enrollment(enr)

                    self.active_modal = None
                    self.set_flash(f"Saved cycle appraisal adjustment (+{hike_pct:.1f}% hike).", "success")

        elif action == "finalize_and_close_cycle":
            p_dict = payload if isinstance(payload, dict) else {}
            c_id = p_dict.get("cycle_id") or self._get_effective_cycle_id()
            actor_id = self.current_user.id if self.current_user else "guardian_1"
            ok, msg = finalize_and_close_cycle(c_id, store, actor_id=actor_id)
            self.set_flash(msg, "success" if ok else "error")

        elif action == "filter_cycle_performance":
            p_dict = payload if isinstance(payload, dict) else {}
            if "band_filter" in p_dict:
                self.cycle_band_filter = p_dict["band_filter"] or "all"
            if "role_filter" in p_dict:
                self.cycle_role_filter = p_dict["role_filter"] or "all"

        elif action == "view_cycle_candidate_detail":
            p_dict = payload if isinstance(payload, dict) else {}
            self.active_modal = "cycle_candidate_detail_modal"
            self.modal_payload = {
                "cycle_id": p_dict.get("cycle_id") or self._get_effective_cycle_id(),
                "user_id": p_dict.get("user_id", "")
            }

        # --- Navigation Actions ---
        elif action == "go_back":
            if self.active_modal:
                self.active_modal = None
                self.modal_payload = {}
            elif self.current_view == "g_create_badge" and self.create_badge_band:
                self.create_badge_band = None
            elif self.current_view == "g_reviews" and getattr(self, "assessment_selected_cosmonaut_id", None):
                self.assessment_selected_cosmonaut_id = None
            elif self.current_view == "g_reviews" and getattr(self, "assessment_selected_badge_id", None):
                self.assessment_selected_badge_id = None
            elif hasattr(self, "view_history") and self.view_history:
                prev_entry = self.view_history.pop()
                while (
                    self.view_history
                    and prev_entry.get("view") == self.current_view
                    and prev_entry.get("band") == self.create_badge_band
                    and prev_entry.get("assessment_badge_id") == getattr(self, "assessment_selected_badge_id", None)
                    and prev_entry.get("assessment_cosmo_id") == getattr(self, "assessment_selected_cosmonaut_id", None)
                ):
                    prev_entry = self.view_history.pop()

                prev_view = prev_entry.get("view", "")
                if prev_view:
                    self.current_view = prev_view
                    self.create_badge_band = prev_entry.get("band")
                    if "assessment_badge_id" in prev_entry:
                        self.assessment_selected_badge_id = prev_entry.get("assessment_badge_id")
                    if "assessment_cosmo_id" in prev_entry:
                        self.assessment_selected_cosmonaut_id = prev_entry.get("assessment_cosmo_id")
                elif self.current_view == "g_create_badge":
                    self.create_badge_band = None
                else:
                    is_guard = (self.current_user and (self.current_user.id == "guardian_1" or self.current_user.role == "guardian" or self.current_user.has_role("guardian")))
                    self.current_view = "g_cycles" if is_guard else self.COSMONAUT_HOME_VIEW
            else:
                if self.current_view == "g_create_badge" and self.create_badge_band:
                    self.create_badge_band = None
                else:
                    is_guard = (self.current_user and (self.current_user.id == "guardian_1" or self.current_user.role == "guardian" or self.current_user.has_role("guardian")))
                    if is_guard and self.current_view != "g_cycles":
                        self.current_view = "g_cycles"
                        self.create_badge_band = None
                    elif not is_guard and self.current_view != self.COSMONAUT_HOME_VIEW:
                        self.current_view = self.COSMONAUT_HOME_VIEW

        elif action == "nav_guardian":
            view_id = payload if isinstance(payload, str) else payload.get("view_id")
            view_id = str(view_id or "").strip().strip('"')
            if not self._is_guardian_user() or view_id not in self._GUARDIAN_VIEWS:
                raise ActionDenied("That page is not available for your account.")
            self._push_history()
            self.current_view = view_id
            self.active_modal = None
            if view_id == "g_learning":
                self.create_badge_band = None
            elif view_id == "g_reviews":
                self.assessment_selected_badge_id = None
                self.assessment_selected_cosmonaut_id = None
            elif view_id == "g_mapping" and getattr(self, "create_badge_band", None):
                self.mapping_selected_band = self.create_badge_band

        elif action == "nav_cosmonaut":
            view_id = payload if isinstance(payload, str) else payload.get("view_id")
            view_id = str(view_id or "").strip().strip('"')
            if view_id == "c_assessments":
                view_id = "c_badge_reviews"  # the Cosmonaut Assessments queue is gone: assessing happens from the Badge Review schedule
            if view_id not in self._COSMONAUT_VIEWS:
                raise ActionDenied("That page does not exist.")
            if view_id == "c_cycles":
                view_id = "c_choose_cycle"  # past cycles & appraisals live on the Choose Cycle page
            if view_id in COSMONAUT_REVIEWER_VIEWS and not is_reviewer_band(getattr(self.current_user, "band", "")):
                raise ActionDenied("Reviewer tools are available from Band 2 upwards.")
            self._push_history()
            self.current_view = view_id
            if view_id == "c_submission":
                self.cosmonaut_expanded_badge_id = None
            if view_id == "c_results":
                self.cosmonaut_results_picked = False
                self.cosmonaut_results_asm_id = ""
            self.active_modal = None

        elif action == "nav_to_submit_badge":
            self._push_history()
            badge_id = payload if isinstance(payload, str) else payload.get("badge_id")
            badge_id = str(badge_id).strip().replace('"', '') if badge_id else self.cosmonaut_submission_badge_id
            self.cosmonaut_submission_badge_id = badge_id
            self.cosmonaut_expanded_badge_id = badge_id
            self.current_view = "c_badge_detail"
            self.active_modal = None

        # --- Modal Controls ---
        elif action == "close_modal":
            self.active_modal = None
            self.modal_payload = {}

        elif action == "toggle_notifications_modal":
            if self.active_modal == "notifications":
                self.active_modal = None
            else:
                self.active_modal = "notifications"

        elif action == "open_badge_detail_modal":
            badge_id = payload.get("badge_id") if isinstance(payload, dict) else payload
            self.active_modal = "badge_detail"
            self.modal_payload = {"badge_id": badge_id}

        elif action == "view_marksheet":
            marksheet_id = payload.get("marksheet_id") if isinstance(payload, dict) else payload
            self.active_modal = "marksheet_modal"
            self.modal_payload = {"marksheet_id": marksheet_id}

        elif action == "view_material_preview":
            material_id = payload.get("material_id") if isinstance(payload, dict) else payload
            self.active_modal = "material_preview"
            self.modal_payload = {"material_id": material_id}

        elif action == "filter_materials_badge":
            badge_id = payload if isinstance(payload, str) else (payload.get("badge_id") if isinstance(payload, dict) else "all")
            self.materials_badge_filter = badge_id or "all"

        elif action == "filter_materials_type":
            type_val = payload if isinstance(payload, str) else (payload.get("type") if isinstance(payload, dict) else "all")
            self.materials_type_filter = type_val or "all"

        elif action == "view_submission_artifact":
            submission_id = payload.get("submission_id") if isinstance(payload, dict) else payload
            self.active_modal = "submission_artifact"
            self.modal_payload = {"submission_id": submission_id}

        # --- Guardian Specific Actions ---
        elif action == "select_guardian_cosmo_filter":
            cosmo_id = payload if isinstance(payload, str) else payload.get("cosmo_id")
            self.selected_guardian_cosmo_id = cosmo_id

        elif action == "filter_guardian_risk":
            risk = payload if isinstance(payload, str) else payload.get("filter", "all")
            self.guardian_risk_filter = risk

        elif action == "filter_guardian_reviews":
            status = payload if isinstance(payload, str) else payload.get("status")
            self.guardian_review_filter = status

        elif action == "filter_assessment_power":
            p_val = payload if isinstance(payload, str) else (payload.get("power", "all") if isinstance(payload, dict) else "all")
            self.assessment_power_filter = p_val or "all"
            self.assessment_selected_badge_id = None
            self.assessment_selected_cosmonaut_id = None

        elif action == "filter_assessment_capability":
            c_val = payload if isinstance(payload, str) else (payload.get("capability", "all") if isinstance(payload, dict) else "all")
            self.assessment_capability_filter = c_val or "all"
            self.assessment_selected_badge_id = None
            self.assessment_selected_cosmonaut_id = None

        elif action == "open_assessment_badge":
            bid = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            if bid:
                self._push_history()
                self.assessment_selected_badge_id = bid
                self.assessment_selected_cosmonaut_id = None

        elif action == "close_assessment_badge":
            self.assessment_selected_badge_id = None
            self.assessment_selected_cosmonaut_id = None

        elif action == "open_assessment_cosmonaut":
            if isinstance(payload, dict):
                bid = payload.get("badge_id") or getattr(self, "assessment_selected_badge_id", None)
                cid = payload.get("cosmonaut_id", "")
            else:
                bid = getattr(self, "assessment_selected_badge_id", None)
                cid = str(payload or "")
            if bid and cid:
                self._push_history()
                self.assessment_selected_badge_id = bid
                self.assessment_selected_cosmonaut_id = cid

        elif action == "close_assessment_cosmonaut":
            self.assessment_selected_cosmonaut_id = None

        elif action == "open_review_modal":
            submission_id = payload.get("submission_id") if isinstance(payload, dict) else payload
            self.active_modal = "review_submission"
            self.modal_payload = {"submission_id": submission_id}

        elif action == "submit_evaluation_rubric":
            self.execute_submit_evaluation(payload)

        elif action == "filter_guardian_allotment":
            self.guardian_allotment_filter = payload if isinstance(payload, str) else payload.get("filter", "all")

        # --- Guardian Mapping Actions ---
        elif action == "select_mapping_band":
            band = payload if isinstance(payload, str) else (payload.get("band", "B1") if isinstance(payload, dict) else "B1")
            self.mapping_selected_band = band
            self.create_badge_band = band  # Synchronize workspace band
            hb = get_higher_bands(band)
            self.mapping_selected_reviewer_bands = [b for b in getattr(self, "mapping_selected_reviewer_bands", []) if b in hb]
            if not self.mapping_selected_reviewer_bands and hb:
                self.mapping_selected_reviewer_bands = [hb[0]]
            self.mapping_selected_reviewer_band = self.mapping_selected_reviewer_bands[0] if self.mapping_selected_reviewer_bands else (hb[0] if hb else "")
            self.mapping_selected_cosmonauts = []
            self.mapping_selected_reviewers = []
            self.mapping_show_final_stage = False
            self.mapping_expanded_badge_key = ""
            self.mapping_selected_badge_id = ""
            b_id, b_title, b_code = self.resolve_mapping_badge(store, band)
            self.mapping_selected_badge = b_title if b_id else ""
            self.mapping_selected_badge_id = b_id

        elif action == "toggle_mapping_role":
            role = payload if isinstance(payload, str) else (payload.get("role") if isinstance(payload, dict) else "")
            if role:
                if role in self.mapping_selected_roles:
                    self.mapping_selected_roles.remove(role)
                else:
                    self.mapping_selected_roles.append(role)

        elif action == "select_all_mapping_roles":
            from starapp.mapping_data import ROLES
            self.mapping_selected_roles = list(ROLES)

        elif action == "clear_mapping_roles":
            self.mapping_selected_roles = []

        elif action == "select_mapping_badge":
            badge_name = payload if isinstance(payload, str) else (payload.get("badge", "") if isinstance(payload, dict) else "")
            badge_id_param = payload.get("badge_id", "") if isinstance(payload, dict) else ""
            if badge_name or badge_id_param:
                self.mapping_selected_badge_id = badge_id_param
                self.mapping_selected_badge = badge_name
                b_id, b_title, b_code = self.resolve_mapping_badge(store)
                if b_id:
                    self.mapping_selected_badge_id = b_id
                    self.mapping_selected_badge = b_title

        elif action == "toggle_mapping_cosmonaut":
            cid = payload if isinstance(payload, str) else (payload.get("member_id") if isinstance(payload, dict) else "")
            if cid:
                if cid in self.mapping_selected_cosmonauts:
                    self.mapping_selected_cosmonauts.remove(cid)
                else:
                    self.mapping_selected_cosmonauts.append(cid)

        elif action == "select_all_mapping_cosmonauts":
            self.mapping_selected_cosmonauts = self._get_filtered_mapping_member_ids(store, "cosmonauts")

        elif action == "clear_mapping_cosmonauts":
            self.mapping_selected_cosmonauts = []

        elif action in ("select_mapping_reviewer_band", "toggle_mapping_reviewer_band"):
            r_band = payload.strip().replace('"', '') if isinstance(payload, str) else (payload.get("band", "") if isinstance(payload, dict) else "")
            if r_band:
                hb = get_higher_bands(self.mapping_selected_band)
                if not hasattr(self, "mapping_selected_reviewer_bands") or not self.mapping_selected_reviewer_bands:
                    self.mapping_selected_reviewer_bands = [hb[0]] if hb else []

                if r_band == "ALL":
                    if len(self.mapping_selected_reviewer_bands) == len(hb):
                        self.mapping_selected_reviewer_bands = [hb[0]] if hb else []
                    else:
                        self.mapping_selected_reviewer_bands = list(hb)
                elif action == "toggle_mapping_reviewer_band":
                    if r_band in self.mapping_selected_reviewer_bands:
                        if len(self.mapping_selected_reviewer_bands) > 1:
                            self.mapping_selected_reviewer_bands.remove(r_band)
                    else:
                        self.mapping_selected_reviewer_bands.append(r_band)
                    self.mapping_selected_reviewer_band = r_band if r_band in hb else self.mapping_selected_reviewer_bands[0]
                else: # select_mapping_reviewer_band
                    self.mapping_selected_reviewer_band = r_band
                    if r_band not in self.mapping_selected_reviewer_bands:
                        self.mapping_selected_reviewer_bands.append(r_band)

        elif action == "toggle_mapping_reviewer":
            rid = payload if isinstance(payload, str) else (payload.get("member_id") if isinstance(payload, dict) else "")
            if rid:
                if rid in self.mapping_selected_reviewers:
                    self.mapping_selected_reviewers.remove(rid)
                else:
                    self.mapping_selected_reviewers.append(rid)

        elif action == "select_all_mapping_reviewers":
            self.mapping_selected_reviewers = self._get_filtered_mapping_member_ids(store, "reviewers")

        elif action == "clear_mapping_reviewers":
            self.mapping_selected_reviewers = []

        elif action in ("toggle_mapping_final_stage", "show_mapping_final_stage"):
            self.mapping_show_final_stage = not getattr(self, "mapping_show_final_stage", False)

        elif action in ("open_mapping_badge_detail", "toggle_mapping_badge_card"):
            p_dict = payload if isinstance(payload, dict) else {}
            if isinstance(payload, str) and payload.strip().startswith("{"):
                try:
                    p_dict = json.loads(payload)
                except Exception:
                    p_dict = {}
            key = p_dict.get("badge_key") or p_dict.get("badge_id") or p_dict.get("badge") or (payload if isinstance(payload, str) and not p_dict else "")
            if key:
                if p_dict.get("band"):
                    self.mapping_selected_band = p_dict["band"]
                    self.create_badge_band = p_dict["band"]
                self._push_history()
                self.mapping_detail_badge_key = key
                self.mapping_expanded_badge_key = key
                self.current_view = "g_mapping_badge_detail"

        elif action == "reset_mapping_selection":
            self.editing_mapping_id = None
            self.mapping_selected_band = "B1"
            from starapp.mapping_data import ROLES
            self.mapping_selected_roles = list(ROLES)
            self.mapping_selected_badge = ""
            self.mapping_selected_badge_id = ""
            self.mapping_selected_cosmonauts = []
            self.mapping_selected_reviewer_bands = ["B2"]
            self.mapping_selected_reviewer_band = "B2"
            self.mapping_selected_reviewers = []
            self.mapping_cosmo_search = ""
            self.mapping_reviewer_search = ""
            self.mapping_badge_search = ""
            self.mapping_calendar_year = datetime.date.today().year
            self.mapping_calendar_month = datetime.date.today().month
            self.mapping_review_anchor = "2026-11-18"
            self.mapping_review_direction = "after"
            self.mapping_review_days_count = 3
            self.mapping_review_mode = "gap"
            self.mapping_range_start = ""
            self.mapping_expanded_badge_key = ""
            self.mapping_review_dates = ["2026-11-18", "2026-11-19", "2026-11-20"]
            self.set_flash("Mapping configuration reset to baseline.", "info")

        elif action == "select_mapping_review_anchor":
            date_iso = payload if isinstance(payload, str) else (payload.get("date") if isinstance(payload, dict) else "")
            if date_iso:
                p_clicked = parse_iso_date(date_iso)
                self.mapping_calendar_year = p_clicked.year
                self.mapping_calendar_month = p_clicked.month
                if getattr(self, "mapping_review_mode", "gap") == "manual":
                    # Manual: each click switches that working day on or off (weekends can't be picked; at least one day stays)
                    cur = list(getattr(self, "mapping_review_dates", []) or [])
                    if p_clicked.weekday() < 5:
                        if date_iso in cur:
                            if len(cur) > 1:
                                cur.remove(date_iso)
                        elif len(cur) < 45:
                            cur.append(date_iso)
                        cur = sorted(set(cur))
                        self.mapping_review_dates = cur
                        self.mapping_review_anchor = cur[0]
                        self.mapping_review_days_count = len(cur)
                elif getattr(self, "mapping_review_mode", "gap") == "range":
                    if not getattr(self, "mapping_range_start", ""):
                        self.mapping_range_start = date_iso
                        self.mapping_review_anchor = date_iso
                        self.mapping_review_dates = [date_iso]
                    else:
                        dates = get_working_days_between(self.mapping_range_start, date_iso, max_days=45)
                        self.mapping_review_dates = dates
                        self.mapping_review_days_count = len(dates)
                        self.mapping_review_anchor = dates[0] if dates else date_iso
                        self.mapping_range_start = ""
                else:
                    days_n = max(1, min(30, int(getattr(self, "mapping_review_days_count", 3) or 3)))
                    self.mapping_review_anchor = date_iso
                    self.mapping_review_dates = get_consecutive_review_days(date_iso, self.mapping_review_direction, days_n)

        elif action == "set_mapping_date_range":
            data = payload if isinstance(payload, dict) else {}
            start_iso = str(data.get("start") or "").strip()[:10]
            end_iso = str(data.get("end") or "").strip()[:10]
            if start_iso and end_iso:
                dates = get_working_days_between(start_iso, end_iso, max_days=45)
                if dates:
                    self.mapping_review_mode = "range"
                    self.mapping_range_start = ""
                    self.mapping_review_dates = dates
                    self.mapping_review_days_count = len(dates)
                    self.mapping_review_anchor = dates[0]
                    p_start = parse_iso_date(dates[0])
                    self.mapping_calendar_year = p_start.year
                    self.mapping_calendar_month = p_start.month
            elif start_iso:
                days_n = max(1, min(30, int(getattr(self, "mapping_review_days_count", 3) or 3)))
                self.mapping_review_anchor = start_iso
                self.mapping_review_dates = get_consecutive_review_days(start_iso, "after", days_n)
                p_start = parse_iso_date(start_iso)
                self.mapping_calendar_year = p_start.year
                self.mapping_calendar_month = p_start.month

        elif action == "open_mapping_calendar_modal":
            self.active_modal = "mapping_calendar_modal"
            self.modal_payload = {}

        elif action == "jump_mapping_calendar_today":
            today_dt = datetime.date.today()
            self.mapping_calendar_year = today_dt.year
            self.mapping_calendar_month = today_dt.month
            days_n = max(1, min(30, int(getattr(self, "mapping_review_days_count", 3) or 3)))
            dates = get_consecutive_review_days(today_dt.isoformat(), "after", days_n)
            self.mapping_review_mode = "gap"
            self.mapping_review_direction = "after"
            self.mapping_range_start = ""
            self.mapping_review_anchor = dates[0] if dates else today_dt.isoformat()
            self.mapping_review_dates = dates

        elif action == "set_mapping_review_direction":
            direction = payload if isinstance(payload, str) else (payload.get("direction", "after") if isinstance(payload, dict) else "after")
            self.mapping_review_direction = direction if direction in ("before", "after") else "after"
            self.mapping_review_mode = "gap"
            self.mapping_range_start = ""
            days_n = max(1, min(30, int(getattr(self, "mapping_review_days_count", 3) or 3)))
            self.mapping_review_dates = get_consecutive_review_days(self.mapping_review_anchor, self.mapping_review_direction, days_n)

        elif action == "set_mapping_review_duration":
            raw_days = payload.get("days", 3) if isinstance(payload, dict) else payload
            try:
                days_n = max(1, min(30, int(str(raw_days).strip())))
            except Exception:
                days_n = 3
            self.mapping_review_days_count = days_n
            self.mapping_review_mode = "gap"
            self.mapping_range_start = ""
            self.mapping_review_dates = get_consecutive_review_days(self.mapping_review_anchor, self.mapping_review_direction, days_n)

        elif action == "set_mapping_review_mode":
            mode = payload if isinstance(payload, str) else (payload.get("mode", "gap") if isinstance(payload, dict) else "gap")
            self.mapping_review_mode = mode if mode in ("range", "manual") else "gap"
            self.mapping_range_start = ""
            if self.mapping_review_mode == "gap":
                days_n = max(1, min(30, int(getattr(self, "mapping_review_days_count", 3) or 3)))
                self.mapping_review_dates = get_consecutive_review_days(self.mapping_review_anchor, self.mapping_review_direction, days_n)

        elif action == "change_mapping_calendar_month":
            if isinstance(payload, dict):
                self.mapping_calendar_year = max(2020, min(2040, int(payload.get("year", self.mapping_calendar_year))))
                self.mapping_calendar_month = max(1, min(12, int(payload.get("month", self.mapping_calendar_month))))
            elif isinstance(payload, str) and payload.strip():
                try:
                    p = json.loads(payload)
                    self.mapping_calendar_year = max(2020, min(2040, int(p.get("year", self.mapping_calendar_year))))
                    self.mapping_calendar_month = max(1, min(12, int(p.get("month", self.mapping_calendar_month))))
                except Exception:
                    pass

        elif action == "edit_band_mapping":
            m_id = payload if isinstance(payload, str) else (payload.get("mapping_id") if isinstance(payload, dict) else "")
            target_map = None
            for m in store.get_band_mappings():
                if m.get("id") == m_id:
                    target_map = m
                    break
            if target_map:
                self.editing_mapping_id = target_map["id"]
                self.mapping_selected_band = target_map.get("band", "B1")
                self.mapping_selected_roles = list(target_map.get("roles", []))
                self.mapping_selected_badge = target_map.get("badge", "")
                self.mapping_selected_cosmonauts = list(target_map.get("cosmonauts", []))
                self.mapping_selected_reviewer_band = target_map.get("reviewer_band", "B2")
                self.mapping_selected_reviewers = list(target_map.get("reviewers", []))
                dates = target_map.get("review_dates", [])
                if dates:
                    self.mapping_review_dates = list(dates)
                    self.mapping_review_anchor = dates[0]
                    p = parse_iso_date(dates[0])
                    self.mapping_calendar_year = p.year
                    self.mapping_calendar_month = p.month
                if self.current_view == "g_mapping_badge_detail":
                    self._push_history()
                    self.current_view = "g_mapping"
                self.set_flash(f"Editing mapping '{self.mapping_selected_badge}' (Band {self.mapping_selected_band}). Adjust selections and click 'Update Badge Mapping'.", "info")

        elif action == "cancel_edit_band_mapping":
            self.editing_mapping_id = None
            self.set_flash("Exited mapping editing mode.", "info")

        elif action == "save_band_mapping":
            import time
            if getattr(self, "editing_mapping_id", None):
                map_id = self.editing_mapping_id
                action_word = "Updated"
            else:
                map_id = f"map_{int(time.time() * 1000)}"
                action_word = "Created"

            # Locate badge in SQLite within active cycle and update badge_timelines & publishing status
            curr_cid = store.get_effective_read_cycle_id()
            matched_badge_id = None
            matched_badge_title = self.mapping_selected_badge
            if store.db and store.db.conn:
                try:
                    b_row = store.db.conn.execute(
                        "SELECT id, title FROM badges WHERE cycle_id = ? AND (title = ? OR code = ? OR id = ?) AND target_band = ?",
                        (curr_cid, self.mapping_selected_badge, self.mapping_selected_badge, self.mapping_selected_badge, self.mapping_selected_band)
                    ).fetchone()
                    if b_row:
                        matched_badge_id = b_row["id"]
                        matched_badge_title = b_row["title"]
                    elif not self.mapping_selected_badge:
                        fallback_row = store.db.conn.execute(
                            "SELECT id, title FROM badges WHERE cycle_id = ? AND target_band = ? AND workflow_status IN ('approved', 'ready_for_review') LIMIT 1",
                            (curr_cid, self.mapping_selected_band)
                        ).fetchone()
                        if fallback_row:
                            matched_badge_id = fallback_row["id"]
                            matched_badge_title = fallback_row["title"]
                            self.mapping_selected_badge = matched_badge_title
                except Exception:
                    pass
            if not matched_badge_id:
                for b in store.get_all_badges(cycle_id=curr_cid):
                    if getattr(b, "target_band", "") == self.mapping_selected_band:
                        if (b.title == self.mapping_selected_badge or b.code == self.mapping_selected_badge or b.id == self.mapping_selected_badge):
                            matched_badge_id = b.id
                            matched_badge_title = b.title
                            break
                        elif not self.mapping_selected_badge and getattr(b, "workflow_status", "") in ("approved", "ready_for_review"):
                            matched_badge_id = b.id
                            matched_badge_title = b.title
                            self.mapping_selected_badge = matched_badge_title

            mapping_record = {
                "id": map_id,
                "band": self.mapping_selected_band,
                "badge": matched_badge_title,
                "badge_id": matched_badge_id or "",
                "roles": list(self.mapping_selected_roles),
                "cosmonauts": list(self.mapping_selected_cosmonauts),
                "reviewer_band": self.mapping_selected_reviewer_band,
                "reviewers": list(self.mapping_selected_reviewers),
                "review_dates": list(self.mapping_review_dates),
                "created_at": current_iso_timestamp(),
                "status": "active"
            }
            store.save_band_mapping(mapping_record)
            self.editing_mapping_id = None

            if matched_badge_id:
                r_dates = list(self.mapping_review_dates)
                start_d = r_dates[0] if r_dates else current_iso_timestamp()[:10]
                end_d = r_dates[-1] if r_dates else current_iso_timestamp()[:10]
                sel_revs = list(self.mapping_selected_reviewers)
                for idx, c_id in enumerate(self.mapping_selected_cosmonauts):
                    assigned_rev = sel_revs[idx % len(sel_revs)] if sel_revs else ""
                    tl_obj = BadgeTimeline(
                        badge_id=matched_badge_id,
                        cosmonaut_id=c_id,
                        assignment_date=current_iso_timestamp()[:10],
                        publication_date=current_iso_timestamp()[:10],
                        learning_start_date=start_d,
                        learning_end_date=end_d,
                        project_start_date=start_d,
                        project_end_date=end_d,
                        submission_deadline=end_d,
                        review_date=end_d,
                        expected_award_date=end_d,
                        status="active",
                        reviewer_id=assigned_rev,
                        review_window_json=json.dumps(r_dates)
                    )
                    store.save_timeline(tl_obj)
                    store.add_activity(
                        event_type="cadet_mapped_to_badge",
                        actor_id=self.current_user.id if self.current_user else "guardian_1",
                        actor_name=self.current_user.name if self.current_user else "Guardian",
                        cosmonaut_id=c_id,
                        badge_id=matched_badge_id,
                        summary=f"Mapped {c_id} to '{matched_badge_title}' (Band {self.mapping_selected_band})",
                        details=f"Assigned Reviewer: {assigned_rev or 'Executive Council'} &bull; Window: {', '.join(r_dates)}"
                    )

                b_obj = store.get_badge(matched_badge_id)
                if b_obj:
                    b_obj.is_allocated = True
                    # Keep unpublished until Guardian explicitly publishes in Badge Allotment
                    if not hasattr(b_obj, "is_published") or b_obj.is_published is None:
                        b_obj.is_published = False
                    for c_id in self.mapping_selected_cosmonauts:
                        if c_id not in b_obj.assigned_cosmonaut_ids:
                            b_obj.assigned_cosmonaut_ids.append(c_id)
                    if self.mapping_selected_reviewers:
                        b_obj.assigned_reviewer_id = self.mapping_selected_reviewers[0]
                    if not b_obj.default_timeline:
                        b_obj.default_timeline = {}
                    b_obj.default_timeline.update({
                        "assignment_date": current_iso_timestamp()[:10],
                        "publication_date": current_iso_timestamp()[:10],
                        "learning_start_date": start_d,
                        "learning_end_date": end_d,
                        "project_start_date": start_d,
                        "project_end_date": end_d,
                        "submission_deadline": end_d,
                        "review_date": end_d,
                        "expected_award_date": end_d,
                        "review_dates": list(self.mapping_review_dates)
                    })
                    store.save_badge(b_obj)

                    if store.db and store.db.conn:
                        try:
                            store.db.conn.execute("""
                                UPDATE badges SET
                                    is_allocated = 1,
                                    is_published = ?,
                                    assigned_reviewer_id = ?,
                                    assigned_cosmonaut_ids_json = ?,
                                    default_timeline_json = ?,
                                    updated_at = ?
                                WHERE id = ?
                            """, (
                                1 if b_obj.is_published else 0,
                                b_obj.assigned_reviewer_id,
                                json.dumps(b_obj.assigned_cosmonaut_ids),
                                json.dumps(b_obj.default_timeline),
                                current_iso_timestamp(),
                                b_obj.id
                            ))
                            store.db.conn.commit()
                        except Exception:
                            pass

                store.mark_dirty()

            saved_badge_title = matched_badge_title
            saved_cosmo_count = len(self.mapping_selected_cosmonauts)
            saved_rev_count = len(self.mapping_selected_reviewers)
            saved_rev_dates = list(self.mapping_review_dates)

            # Reset mapping page selections after saving
            self.mapping_selected_cosmonauts = []
            self.mapping_selected_reviewers = []
            self.mapping_show_final_stage = False
            self.editing_mapping_id = None

            store.add_activity(
                event_type="badge_mapped",
                actor_id=self.current_user.id if self.current_user else "guardian_1",
                actor_name=self.current_user.name if self.current_user else "Guardian",
                cosmonaut_id="",
                badge_id=matched_badge_id or "",
                summary=f"{action_word} Badge '{saved_badge_title}' for Band {self.mapping_selected_band}",
                details=f"Roles: {', '.join(self.mapping_selected_roles)} &bull; {saved_cosmo_count} Cosmonaut(s) &bull; Reviewers: {saved_rev_count} ({self.mapping_selected_reviewer_band}) &bull; Review Dates: {', '.join(saved_rev_dates)} &bull; Ready for publishing"
            )
            self.set_flash(f"Successfully {action_word.lower()} '{saved_badge_title}' mapping! Saved directly into badge with {saved_cosmo_count} cosmonaut(s), reviewer(s), and review dates. Mapping page reset & ready for timeline publishing in Badge Allotment.", "success")

        elif action == "delete_band_mapping":
            m_id = payload if isinstance(payload, str) else (payload.get("mapping_id") if isinstance(payload, dict) else "")
            if m_id:
                store.delete_band_mapping(m_id)
                self.set_flash("Band badge mapping deleted successfully.", "info")

        elif action == "send_mapping_requests":
            effective_band = self.create_badge_band if getattr(self, "create_badge_band", None) else self.mapping_selected_band
            if not getattr(self, "mapping_selected_badge", "") and not getattr(self, "mapping_selected_badge_id", ""):
                self.set_flash("Please select a badge before sending requests.", "warning")
            else:
                b_id, b_title, b_code = self.resolve_mapping_badge(store, effective_band)
                if not b_id and not b_title:
                    self.set_flash("Please select a valid badge before sending requests.", "warning")
                elif not self.mapping_selected_cosmonauts:
                    self.set_flash("Please select at least 1 cosmonaut before sending requests.", "warning")
                elif not self.mapping_selected_reviewers:
                    self.set_flash("Please select at least 1 reviewer before sending requests.", "warning")
                else:
                    # SERVER-SIDE RULE ENFORCEMENT (the UI only offers valid choices, the server must not trust it):
                    #   * the badge must be approved,
                    #   * every reviewer must be an active badge reviewer whose band is HIGHER than the badge band,
                    #   * every cosmonaut must be an active user of the badge band.
                    badge_obj = store.get_badge(b_id) if b_id else None
                    if badge_obj and getattr(badge_obj, "workflow_status", "approved") != "approved":
                        raise ActionDenied(f"'{badge_obj.title}' is not approved yet, so it cannot be mapped.")
                    bad_reviewers = []
                    valid_reviewer_ids = []
                    for r_id in self.mapping_selected_reviewers:
                        ok_rev, why_rev = store.verify_reviewer_eligibility(r_id, effective_band)
                        if ok_rev:
                            valid_reviewer_ids.append(r_id)
                        else:
                            bad_reviewers.append(r_id)
                    if not valid_reviewer_ids:
                        raise ActionDenied("None of the selected reviewers is eligible: a reviewer must hold a higher band than Band "
                                           f"{effective_band}.")
                    valid_cosmo_ids = [
                        cid for cid in self.mapping_selected_cosmonauts
                        if (lambda u: bool(u) and (getattr(u, "band", "") or effective_band) == effective_band)(store.get_user_by_id(cid))
                    ]
                    if not valid_cosmo_ids:
                        raise ActionDenied(f"None of the selected cosmonauts belongs to Band {effective_band}.")
                    created_count = 0
                    sent_dates = list(getattr(self, "mapping_review_dates", []) or [])
                    sent_cosmo_ids = valid_cosmo_ids
                    for r_id in valid_reviewer_ids:
                        u = store.get_user_by_id(r_id)
                        req_id = f"req_{effective_band}_{b_id or b_code}_{r_id}"
                        new_req = {
                            "id": req_id,
                            "band": effective_band,
                            "badge_id": b_id or "",
                            "badge_code": b_code or "",
                            "badge": b_title,
                            "reviewer_id": r_id,
                            "reviewer_name": u.name if u else r_id,
                            "reviewer_role": u.role if u else "Reviewer",
                            "reviewer_band": getattr(u, "band", self.mapping_selected_reviewer_band),
                            "reviewer_avatar": getattr(u, "avatar", (u.name[:2].upper() if u else "REV")),
                            "cosmonaut_ids": list(sent_cosmo_ids),
                            "review_dates": list(sent_dates),
                            "review_duration_days": len(sent_dates),
                            "status": "pending",
                            "sent_at": current_iso_timestamp()
                        }
                        store.add_mapping_request(new_req)
                        store.add_notification(
                            r_id,
                            f"Review Request: {b_title} (Band {effective_band})",
                            f"The Guardian has asked you to mentor and evaluate {len(sent_cosmo_ids)} cosmonaut(s) for "
                            f"'{b_title}' (Band {effective_band}). Open Review Requests to accept or decline.",
                            link_section="c_requests",
                            event_type="mapping_request",
                            related_badge_id=b_id or ""
                        )
                        created_count += 1
                    preview_key = f"{effective_band}::{b_id or b_title}"
                    if hasattr(self, "mapping_staged_previews") and preview_key in self.mapping_staged_previews:
                        self.mapping_staged_previews.pop(preview_key, None)
                    # Refresh all upper selections so Guardian can configure other badges/bands cleanly
                    from starapp.mapping_data import ROLES
                    if not hasattr(self, "mapping_last_sent_badge_by_band"):
                        self.mapping_last_sent_badge_by_band = {}
                    self.mapping_last_sent_badge_by_band[effective_band] = (b_id or "", b_title or "", b_code or "")
                    self.mapping_selected_roles = list(ROLES)
                    self.mapping_selected_badge = ""
                    self.mapping_selected_badge_id = ""
                    self.mapping_selected_cosmonauts = []
                    self.mapping_selected_reviewers = []
                    self.mapping_badge_search = ""
                    self.mapping_cosmo_search = ""
                    self.mapping_reviewer_search = ""
                    self.mapping_expanded_badge_key = ""
                    self.mapping_show_final_stage = True
                    self.set_flash(f"Sent review request for '{b_title}' ({effective_band}) to {created_count} reviewer(s). Click the '{b_title}' card below to inspect requests and map candidates.", "success")

        elif action == "save_allotment_timeline":
            data = payload if isinstance(payload, dict) else {}
            if isinstance(payload, str):
                try:
                    data = json.loads(payload)
                except Exception:
                    data = {}
            badge_id = data.get("badge_id", "")
            # Normalize legacy short field names & canonical field names uniformly
            normalized = {
                "learning_start_date": data.get("learning_start_date") or data.get("learning_start") or None,
                "learning_end_date": data.get("learning_end_date") or data.get("learning_end") or None,
                "project_start_date": data.get("project_start_date") or data.get("project_start") or None,
                "project_end_date": data.get("project_end_date") or data.get("project_end") or None,
                "submission_deadline": data.get("submission_deadline") or data.get("deadline") or None,
                "review_date": data.get("review_date") or None,
                "expected_award_date": data.get("expected_award_date") or data.get("award_date") or None,
            }
            if badge_id:
                curr_cid = store.get_effective_read_cycle_id()
                b_obj = store.get_badge(badge_id)
                if b_obj:
                    if not b_obj.default_timeline:
                        b_obj.default_timeline = {}
                    for k, val in normalized.items():
                        if val:
                            b_obj.default_timeline[k] = val
                    store.save_badge(b_obj)

                if store.db and store.db.conn:
                    try:
                        store.db.conn.execute("""
                            UPDATE badge_timelines SET
                                learning_start_date = COALESCE(?, learning_start_date),
                                learning_end_date = COALESCE(?, learning_end_date),
                                project_start_date = COALESCE(?, project_start_date),
                                project_end_date = COALESCE(?, project_end_date),
                                submission_deadline = COALESCE(?, submission_deadline),
                                review_date = COALESCE(?, review_date),
                                expected_award_date = COALESCE(?, expected_award_date)
                            WHERE badge_id = ? AND cycle_id = ?
                        """, (
                            normalized["learning_start_date"],
                            normalized["learning_end_date"],
                            normalized["project_start_date"],
                            normalized["project_end_date"],
                            normalized["submission_deadline"],
                            normalized["review_date"],
                            normalized["expected_award_date"],
                            badge_id,
                            curr_cid
                        ))
                        store.db.conn.commit()
                    except Exception:
                        pass
                for tl in store.get_timelines_dict().values():
                    if tl.badge_id == badge_id:
                        for k, val in normalized.items():
                            if val:
                                setattr(tl, k, val)
                        store.save_timeline(tl)
                store.add_activity(
                    event_type="timeline_configured",
                    actor_id=self.current_user.id if self.current_user else "guardian_1",
                    actor_name=self.current_user.name if self.current_user else "Guardian",
                    cosmonaut_id="",
                    badge_id=badge_id,
                    summary=f"Configured Milestone Timeline Schedule for {b_obj.code if b_obj else badge_id}",
                    details=f"Deadline: {normalized['submission_deadline'] or 'unchanged'} | Review: {normalized['review_date'] or 'unchanged'}"
                )
                store.mark_dirty()
                self.set_flash("Timeline schedule configured and saved successfully!", "success")
            else:
                self.set_flash("Badge ID missing for timeline save.", "warning")

        elif action in ("accept_mapping_request", "reject_mapping_request", "delete_mapping_request"):
            req_id = payload.strip().replace('"', '') if isinstance(payload, str) else (payload.get("request_id") if isinstance(payload, dict) else "")
            if req_id:
                curr_cid = store.get_effective_read_cycle_id()
                reqs = store.get_mapping_requests(cycle_id=curr_cid)
                matched_req = next(
                    (
                        r for r in reqs
                        if r.get("id") == req_id
                        or f"req_{r.get('band')}_{r.get('reviewer_id')}" == req_id
                        or r.get("id", "").startswith(req_id)
                    ),
                    None
                )
                # AUTHORISATION: only the invited reviewer may accept / decline an invitation and only a
                # Guardian may withdraw one. Any signed-in user could previously act on any request id.
                if not self.current_user:
                    raise ActionDenied("Please sign in to respond to a mapping request.")
                _roles = set(getattr(self.current_user, "roles", None) or [self.current_user.role])
                _is_guardian_actor = bool(_roles & {"guardian", "admin"}) or self.current_user.id in ("guardian_1", "admin")
                if not matched_req:
                    raise ActionDenied("That mapping request no longer exists.")
                if action == "delete_mapping_request" and not _is_guardian_actor:
                    raise ActionDenied("Only a Guardian can withdraw a mapping request.")
                if action in ("accept_mapping_request", "reject_mapping_request") and not (
                    _is_guardian_actor or matched_req.get("reviewer_id") == self.current_user.id
                ):
                    raise ActionDenied("This mapping request was addressed to a different reviewer.")
                req_id = matched_req.get("id", req_id)  # resolve to the exact id (no ambiguous prefix updates)
                actor_id = self.current_user.id
                actor_name = self.current_user.name
                b_ref = matched_req.get("badge_id", "") if matched_req else ""
                b_label = matched_req.get("badge", req_id) if matched_req else req_id
                band_lbl = matched_req.get("band", "") if matched_req else ""

                if action == "accept_mapping_request" and matched_req.get("expired"):
                    raise ActionDenied("This review request expired after 24 hours without a response. Ask the Guardian to resend it.")
                if action == "accept_mapping_request":
                    store.update_mapping_request_status(req_id, "accepted")
                    store.add_activity(
                        event_type="mapping_request_accepted",
                        actor_id=actor_id,
                        actor_name=actor_name,
                        cosmonaut_id="",
                        badge_id=b_ref,
                        summary=f"Accepted Mapping Request for '{b_label}' (Band {band_lbl})",
                        details=f"{actor_name} accepted reviewer allocation invitation ({req_id})."
                    )
                    store.add_notification(
                        recipient_id="guardian_1",
                        title=f"Mapping Accepted: {b_label}",
                        message=f"{actor_name} accepted reviewer mapping request for '{b_label}' (Band {band_lbl}).",
                        link_section="g_mapping",
                        event_type="mapping_accepted",
                        related_badge_id=b_ref
                    )
                    self.set_flash("Review request accepted. Reviewer confirmed for milestone mapping.", "success")
                elif action == "reject_mapping_request":
                    store.update_mapping_request_status(req_id, "rejected")
                    store.add_activity(
                        event_type="mapping_request_rejected",
                        actor_id=actor_id,
                        actor_name=actor_name,
                        cosmonaut_id="",
                        badge_id=b_ref,
                        summary=f"Rejected Mapping Request for '{b_label}' (Band {band_lbl})",
                        details=f"{actor_name} declined reviewer allocation invitation ({req_id})."
                    )
                    store.add_notification(
                        recipient_id="guardian_1",
                        title=f"Mapping Declined: {b_label}",
                        message=f"{actor_name} declined reviewer mapping request for '{b_label}' (Band {band_lbl}).",
                        link_section="g_mapping",
                        event_type="mapping_rejected",
                        related_badge_id=b_ref
                    )
                    self.set_flash("Review request declined / rejected.", "info")
                else:
                    store.delete_mapping_request(req_id)
                    store.add_activity(
                        event_type="mapping_request_deleted",
                        actor_id=actor_id,
                        actor_name=actor_name,
                        cosmonaut_id="",
                        badge_id=b_ref,
                        summary=f"Deleted Mapping Request ({req_id})",
                        details=f"Removed mapping invitation for '{b_label}'."
                    )
                    self.set_flash("Review request removed.", "info")

        elif action == "resend_mapping_request":
            req_id = payload.strip().replace('"', '') if isinstance(payload, str) else (payload.get("request_id") if isinstance(payload, dict) else "")
            fresh = store.resend_mapping_request(req_id) if req_id else None
            if not fresh:
                raise ActionDenied("That mapping request no longer exists.")
            store.add_activity(
                event_type="mapping_request_resent",
                actor_id=self.current_user.id,
                actor_name=self.current_user.name,
                cosmonaut_id="",
                badge_id=fresh.get("badge_id", ""),
                summary=f"Re-sent Mapping Request for '{fresh.get('badge', '')}' (Band {fresh.get('band', '')})",
                details=f"New 24-hour window opened for {fresh.get('reviewer_name', '')} ({req_id}).",
            )
            store.add_notification(
                fresh.get("reviewer_id", ""),
                f"Review Request: {fresh.get('badge', '')} (Band {fresh.get('band', '')})",
                "The Guardian re-sent this review request. Open Review Requests and respond within 24 hours.",
                link_section="c_requests",
                event_type="mapping_request",
                related_badge_id=fresh.get("badge_id", ""),
            )
            self.set_flash(f"Request re-sent to {fresh.get('reviewer_name', 'the reviewer')}. They have 24 hours to respond.", "success")

        elif action == "sync_badge_reviews":
            pass  # a review countdown reached zero in the browser: the sweep at the top of handle_event already closed it

        elif action == "sync_mapping_requests":
            pass  # a countdown reached zero in the browser: the sweep at the top of handle_event already applied it

        elif action == "preview_cosmonaut_mapping":
            p_dict = payload if isinstance(payload, dict) else {}
            if isinstance(payload, str) and payload.strip():
                try:
                    p_dict = json.loads(payload)
                except Exception:
                    p_dict = {}
            effective_band = p_dict.get("band") or (self.create_badge_band if getattr(self, "create_badge_band", None) else self.mapping_selected_band)
            b_id, b_title, b_code = self.resolve_mapping_badge(
                store,
                effective_band,
                badge_ref_override=p_dict.get("badge", ""),
                badge_id_override=p_dict.get("badge_id", "")
            )
            accepted_reqs, cosmo_ids, r_dates = self._collect_badge_mapping_inputs(
                store, effective_band, b_id, b_title, b_code, prefer_selected_cosmonauts=False
            )
            if not accepted_reqs:
                self.set_flash(f"No accepted reviewers available for '{b_title}'. Ensure reviewers accept requests first.", "warning")
            elif not cosmo_ids:
                self.set_flash(f"No cosmonauts associated with '{b_title}'. Select cosmonauts and send requests first.", "warning")
            else:
                num_guardians = len(accepted_reqs)
                guardian_buckets = {r["reviewer_id"]: [] for r in accepted_reqs}
                for idx, c_id in enumerate(cosmo_ids):
                    guardian_buckets[accepted_reqs[idx % num_guardians]["reviewer_id"]].append(c_id)
                preview_key = f"{effective_band}::{b_id or b_title}"
                if not hasattr(self, "mapping_staged_previews"):
                    self.mapping_staged_previews = {}
                self.mapping_staged_previews[preview_key] = {
                    "band": effective_band,
                    "badge_id": b_id or "",
                    "badge": b_title,
                    "badge_code": b_code or "",
                    "review_dates": r_dates,
                    "roles": list(self.mapping_selected_roles),
                    "cosmonauts": cosmo_ids,
                    "assignments": [
                        {
                            "reviewer_id": req["reviewer_id"],
                            "reviewer_name": req.get("reviewer_name", req["reviewer_id"]),
                            "reviewer_band": req.get("reviewer_band", self.mapping_selected_reviewer_band),
                            "cosmonauts": guardian_buckets.get(req["reviewer_id"], [])
                        }
                        for req in accepted_reqs
                        if guardian_buckets.get(req["reviewer_id"], [])
                    ]
                }
                self.mapping_expanded_badge_key = b_id or b_title
                self.mapping_detail_badge_key = b_id or b_title
                self.set_flash(f"Mapped {len(cosmo_ids)} cosmonaut(s) across {num_guardians} accepted reviewer(s) for '{b_title}'. Review the pairings and click Save Mapping to finalize.", "info")

        elif action == "save_staged_mapping":
            p_dict = payload if isinstance(payload, dict) else {}
            if isinstance(payload, str) and payload.strip():
                try:
                    p_dict = json.loads(payload)
                except Exception:
                    p_dict = {}
            effective_band = p_dict.get("band") or (self.create_badge_band if getattr(self, "create_badge_band", None) else self.mapping_selected_band)
            b_id, b_title, b_code = self.resolve_mapping_badge(
                store,
                effective_band,
                badge_ref_override=p_dict.get("badge", ""),
                badge_id_override=p_dict.get("badge_id", "")
            )
            accepted_reqs, cosmo_ids, r_dates = self._collect_badge_mapping_inputs(
                store, effective_band, b_id, b_title, b_code, prefer_selected_cosmonauts=False
            )
            if not accepted_reqs:
                self.set_flash(f"No accepted reviewers available for '{b_title}'.", "warning")
            elif not cosmo_ids:
                self.set_flash(f"No cosmonauts available for '{b_title}'.", "warning")
            else:
                self._commit_badge_mapping(store, effective_band, b_id, b_title, b_code, accepted_reqs, cosmo_ids, r_dates)
                self.mapping_selected_badge = ""
                self.mapping_selected_badge_id = ""
                self.mapping_selected_cosmonauts = []
                self.mapping_selected_reviewers = []
                self.mapping_expanded_badge_key = b_id or b_title
                self.editing_mapping_id = None
                self.set_flash(f"Successfully saved mapping for '{b_title}' (Band {effective_band}) across {len(accepted_reqs)} accepted reviewer(s).", "success")

        elif action == "execute_cosmonaut_mapping":
            p_dict = payload if isinstance(payload, dict) else {}
            if isinstance(payload, str) and payload.strip():
                try:
                    p_dict = json.loads(payload)
                except Exception:
                    p_dict = {}
            effective_band = p_dict.get("band") or (self.create_badge_band if getattr(self, "create_badge_band", None) else self.mapping_selected_band)
            ref_ov = p_dict.get("badge", "")
            id_ov = p_dict.get("badge_id", "")
            if not ref_ov and not id_ov and not getattr(self, "mapping_selected_badge", "") and not getattr(self, "mapping_selected_badge_id", ""):
                last_info = getattr(self, "mapping_last_sent_badge_by_band", {}).get(effective_band)
                if last_info:
                    id_ov, ref_ov = last_info[0], last_info[1]
            b_id, b_title, b_code = self.resolve_mapping_badge(
                store,
                effective_band,
                badge_ref_override=ref_ov,
                badge_id_override=id_ov
            )
            prefer_sel = not p_dict.get("badge_id") and not p_dict.get("badge")
            accepted_reqs, cosmo_ids, r_dates = self._collect_badge_mapping_inputs(
                store, effective_band, b_id, b_title, b_code, prefer_selected_cosmonauts=prefer_sel
            )
            if not accepted_reqs:
                self.set_flash(f"No accepted reviewers available for '{b_title}'. Please ensure reviewers accept requests for this badge first.", "warning")
            elif not cosmo_ids:
                self.set_flash("No cosmonauts selected for mapping. Please select cosmonauts above.", "warning")
            else:
                self._commit_badge_mapping(store, effective_band, b_id, b_title, b_code, accepted_reqs, cosmo_ids, r_dates)
                self.mapping_selected_badge = ""
                self.mapping_selected_badge_id = ""
                self.mapping_selected_cosmonauts = []
                self.mapping_selected_reviewers = []
                self.mapping_expanded_badge_key = b_id or b_title
                self.mapping_show_final_stage = False
                self.editing_mapping_id = None
                self.set_flash(f"Successfully saved '{b_title}' mapping! Badge updated with mapped reviewers, cosmonauts, and review schedule.", "success")

        elif action == "clear_band_mappings":
            p_dict = payload if isinstance(payload, dict) else {}
            if isinstance(payload, str) and payload.strip().startswith("{"):
                try:
                    p_dict = json.loads(payload)
                except Exception:
                    p_dict = {}
            band = p_dict.get("band") or (payload.strip().replace('"', '') if isinstance(payload, str) and not p_dict else self.mapping_selected_band)
            badge_id_ref = p_dict.get("badge_id") if p_dict else None
            badge_ref = p_dict.get("badge") if p_dict else None
            curr_cid = store.get_effective_read_cycle_id()
            if badge_ref or badge_id_ref:
                store.band_mappings = [
                    m for m in store.band_mappings
                    if not (
                        (m.get("cycle_id") or DEFAULT_CYCLE_ID) == curr_cid
                        and m.get("band") == band
                        and ((badge_id_ref and m.get("badge_id") == badge_id_ref) or (badge_ref and m.get("badge") == badge_ref))
                    )
                ]
                if store.db and store.db.conn:
                    try:
                        store.db.conn.execute(
                            "DELETE FROM band_mappings WHERE cycle_id = ? AND band = ? AND (badge_id = ? OR json_extract(data_json, '$.badge_id') = ? OR json_extract(data_json, '$.badge') = ?)",
                            (curr_cid, band, badge_id_ref or "", badge_id_ref or "", badge_ref or "")
                        )
                        store.db.conn.commit()
                    except Exception:
                        pass
                self.set_flash(f"Active mappings for '{badge_ref or badge_id_ref}' (Band {band}) cleared.", "info")
            else:
                store.band_mappings = [
                    m for m in store.band_mappings
                    if not ((m.get("cycle_id") or DEFAULT_CYCLE_ID) == curr_cid and m.get("band") == band)
                ]
                if store.db and store.db.conn:
                    try:
                        store.db.conn.execute("DELETE FROM band_mappings WHERE cycle_id = ? AND band = ?", (curr_cid, band))
                        store.db.conn.commit()
                    except Exception:
                        pass
                self.set_flash(f"Active mappings for Band {band} cleared.", "info")
            store.mark_dirty()

        elif action in ("reset_all_mapping_state", "reset_mapping_demo"):
            curr_cid = store.get_effective_read_cycle_id()
            store.band_mappings = [m for m in store.band_mappings if (m.get("cycle_id") or DEFAULT_CYCLE_ID) != curr_cid]
            store.mapping_requests = [r for r in store.mapping_requests if (r.get("cycle_id") or DEFAULT_CYCLE_ID) != curr_cid]
            if store.db and store.db.conn:
                try:
                    store.db.conn.execute("DELETE FROM band_mappings WHERE cycle_id = ?", (curr_cid,))
                    store.db.conn.execute("DELETE FROM mapping_requests WHERE cycle_id = ?", (curr_cid,))
                    store.db.conn.commit()
                except Exception:
                    pass
            store.mark_dirty()
            self.mapping_selected_band = "B1"
            from starapp.mapping_data import ROLES
            self.mapping_selected_roles = list(ROLES)
            self.mapping_selected_badge = ""
            self.mapping_selected_badge_id = ""
            self.mapping_selected_cosmonauts = []
            hb = get_higher_bands("B1")
            self.mapping_selected_reviewer_bands = ["B2"]
            self.mapping_selected_reviewer_band = "B2"
            self.mapping_selected_reviewers = []
            self.mapping_cosmo_search = ""
            self.mapping_reviewer_search = ""
            self.mapping_badge_search = ""
            self.mapping_calendar_year = datetime.date.today().year
            self.mapping_calendar_month = datetime.date.today().month
            self.mapping_review_anchor = "2026-11-18"
            self.mapping_review_direction = "after"
            self.mapping_review_days_count = 3
            self.mapping_review_mode = "gap"
            self.mapping_range_start = ""
            self.mapping_review_dates = ["2026-11-18", "2026-11-19", "2026-11-20"]
            self.mapping_staged_previews = {}
            self.mapping_expanded_badge_key = ""
            self.mapping_detail_badge_key = ""
            self.mapping_last_sent_badge_by_band = {}
            self.editing_mapping_id = None
            self.mapping_show_final_stage = False
            self.set_flash("Mapping workspace and demo state reset successfully. Ready for a clean demonstration run.", "info")

        elif action == "open_locked_milestone_notice":
            idx = payload if isinstance(payload, (str, int)) else payload.get("index", "5")
            self.active_modal = "locked_milestone_notice"
            self.modal_payload = {"index": idx}

        elif action == "publish_and_unlock_badge":
            badge_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            badge = store.get_badge(badge_id)
            if badge:
                badge.is_allocated = True
                badge.is_published = True
                all_cosmo_ids = [c.id for c in store.get_all_cosmonauts()]
                badge.assigned_cosmonaut_ids = all_cosmo_ids
                store.save_badge(badge)

                dt = badge.default_timeline or {}
                for cid in all_cosmo_ids:
                    tl = store.get_timeline(badge.id, cid)
                    if not tl:
                        new_tl = BadgeTimeline(
                            badge_id=badge.id,
                            cosmonaut_id=cid,
                            assignment_date=dt.get("assignment_date", "2026-11-10"),
                            publication_date=dt.get("publication_date", "2026-11-10"),
                            learning_start_date=dt.get("learning_start_date", "2026-11-11"),
                            learning_end_date=dt.get("learning_end_date", "2026-11-20"),
                            project_start_date=dt.get("project_start_date", "2026-11-21"),
                            project_end_date=dt.get("project_end_date", "2026-12-01"),
                            submission_deadline=dt.get("submission_deadline", "2026-12-03"),
                            review_date=dt.get("review_date", "2026-12-06"),
                            expected_award_date=dt.get("expected_award_date", "2026-12-08"),
                            status="active"
                        )
                        store.save_timeline(new_tl)
                    else:
                        tl.status = "active"
                        store.save_timeline(tl)

                    store.add_notification(
                        recipient_id=cid,
                        title=f"Milestone Unlocked: {badge.code}",
                        message=f"{self.current_user.name if self.current_user else 'Arjun Mehta'} published and unlocked {badge.code}: {badge.title}! Curriculum and project requirements are now live.",
                        link_section="c_roadmap"
                    )

                if self.active_modal == "badge_detail":
                    self.active_modal = None
                    self.modal_payload = {}

                store.add_activity(
                    event_type="badge_published",
                    actor_id=self.current_user.id,
                    actor_name=self.current_user.name,
                    cosmonaut_id="",
                    badge_id=badge.id,
                    summary=f"Published & Unlocked Milestone {badge.code}: {badge.title}",
                    details="Milestone unlocked on both Guardian and Cosmonaut 25-level roadmaps."
                )
                self.set_flash(f"Published and unlocked {badge.code}: {badge.title} across Guardian & Cosmonaut roadmaps!", "success")

        elif action == "open_revoke_decision_confirm":
            sub_id = payload if isinstance(payload, str) else (payload.get("submission_id", "") if isinstance(payload, dict) else "")
            sub_id = str(sub_id).strip().replace('"', '')
            if store.get_submission(sub_id) and store.get_guardian_assessment_for_submission(sub_id):
                self.active_modal = "decision_revoke_confirm"
                self.modal_payload = {"submission_id": sub_id}
            else:
                self.set_flash("There is no final decision to revoke on this submission.", "warning")

        elif action == "revoke_guardian_decision":
            sub_id = payload if isinstance(payload, str) else (payload.get("submission_id", "") if isinstance(payload, dict) else "")
            self.execute_revoke_guardian_decision(str(sub_id).strip().replace('"', ''))

        elif action in ("confirm_publish_badge", "confirm_revoke_badge"):
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            b_id = str(b_id).strip().replace('"', '')
            if store.get_badge(b_id):
                self.active_modal = "badge_publish_confirm" if action == "confirm_publish_badge" else "badge_revoke_confirm"
                self.modal_payload = {"badge_id": b_id}
            else:
                self.set_flash("Badge not found.", "warning")

        elif action == "revoke_badge":
            self.active_modal = None            # the confirmation dialog closes whatever the outcome
            self.modal_payload = {}
            badge_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            badge = store.get_badge(badge_id)
            if badge:
                badge.is_allocated = False
                badge.is_published = False
                all_cosmo_ids = [c.id for c in store.get_all_cosmonauts()]
                for cid in all_cosmo_ids:
                    tl = store.get_timeline(badge.id, cid)
                    if tl:
                        tl.status = "locked"
                        store.save_timeline(tl)
                store.save_badge(badge)

                store.add_activity(
                    event_type="badge_revoked",
                    actor_id=self.current_user.id,
                    actor_name=self.current_user.name,
                    cosmonaut_id="",
                    badge_id=badge.id,
                    summary=f"Revoked Badge {badge.code}: {badge.title}",
                    details="Milestone revoked by Guardian; removed from active Cosmonaut roadmap and returned to catalog."
                )
                self.set_flash(f"Revoked {badge.code}: {badge.title}. It has been removed from the Cosmonaut roadmap and returned to catalog.", "info")

        elif action == "publish_badge":
            self.active_modal = None            # the confirmation dialog closes whatever the outcome
            self.modal_payload = {}
            badge_id = payload.get("badge_id") if isinstance(payload, dict) else payload
            if isinstance(badge_id, str):
                badge_id = badge_id.strip().replace('"', '')
            badge = store.get_badge(badge_id)
            if not badge and store.db and store.db.conn:
                try:
                    curr_cid = store.get_effective_read_cycle_id()
                    row = store.db.conn.execute("SELECT * FROM badges WHERE (id = ? OR code = ?) AND cycle_id = ?", (badge_id, badge_id, curr_cid)).fetchone()
                    if row:
                        badge = store.get_badge(row["id"])
                except Exception:
                    pass
            if badge:
                badge.is_published = True
                badge.is_allocated = True
                badge.published_at = current_iso_timestamp()
                badge.published_by = self.current_user.id if self.current_user else "guardian_1"
                store.save_badge(badge)

                # Look up authoritative mappings for reviewers and mapped cadets
                b_band = getattr(badge, "target_band", "B1") or "B1"
                matched_mappings = [
                    m for m in store.get_band_mappings()
                    if (m.get("badge_id") == badge.id or m.get("badge") in (badge.title, badge.code, badge.id) or badge.title in m.get("badge", ""))
                    and m.get("band") == b_band
                ]

                all_mapped_cids = set(getattr(badge, "assigned_cosmonaut_ids", []) or [])
                notified_reviewers = set()
                dt = badge.default_timeline or {}

                # If badge has assigned_reviewer_id directly
                if getattr(badge, "assigned_reviewer_id", "") and not matched_mappings:
                    direct_rev_id = badge.assigned_reviewer_id
                    if direct_rev_id not in notified_reviewers:
                        notified_reviewers.add(direct_rev_id)
                        store.add_notification(
                            recipient_id=direct_rev_id,
                            title=f"📋 Milestone Allotted: {badge.code}",
                            message=f"Milestone '{badge.title}' has been published and assigned to your review queue ({len(all_mapped_cids)} cadet(s)). You have 72 hours to create the project and send it to all your mapped cosmonauts.",
                            event_type="milestone",
                            link_section="c_badge_reviews"
                        )
                    for cid in all_mapped_cids:
                        start_d = dt.get("learning_start_date", "2026-11-21")
                        end_d = dt.get("review_date", "2026-12-15")
                        tl = store.get_timeline(badge.id, cid)
                        if not tl:
                            new_tl = BadgeTimeline(
                                badge_id=badge.id,
                                cosmonaut_id=cid,
                                reviewer_id=direct_rev_id,
                                assignment_date=dt.get("assignment_date", current_iso_timestamp()[:10]),
                                publication_date=current_iso_timestamp()[:10],
                                learning_start_date=start_d,
                                learning_end_date=end_d,
                                project_start_date=start_d,
                                project_end_date=end_d,
                                submission_deadline=end_d,
                                review_date=end_d,
                                expected_award_date=end_d,
                                status="active"
                            )
                            store.save_timeline(new_tl)
                        else:
                            tl.status = "active"
                            tl.reviewer_id = direct_rev_id
                            store.save_timeline(tl)

                for mp in matched_mappings:
                    rev_list = mp.get("reviewers", [])
                    rev_id = rev_list[0] if rev_list else ""
                    r_dates = mp.get("review_dates", [])
                    c_ids = mp.get("cosmonauts", [])
                    start_d = r_dates[0] if r_dates else dt.get("learning_start_date", "2026-11-10")
                    end_d = r_dates[-1] if r_dates else dt.get("review_date", "2026-11-20")

                    if rev_id and rev_id not in notified_reviewers:
                        notified_reviewers.add(rev_id)
                        store.add_notification(
                            recipient_id=rev_id,
                            title=f"📋 Milestone Allotted: {badge.code}",
                            message=f"Milestone '{badge.title}' has been published and assigned to your review queue ({len(c_ids)} cadet(s)). You have 72 hours to create the project and send it to all your mapped cosmonauts.",
                            event_type="milestone",
                            link_section="c_badge_reviews"
                        )

                    for cid in c_ids:
                        all_mapped_cids.add(cid)
                        tl = store.get_timeline(badge.id, cid)
                        if not tl:
                            new_tl = BadgeTimeline(
                                badge_id=badge.id,
                                cosmonaut_id=cid,
                                reviewer_id=rev_id,
                                assignment_date=dt.get("assignment_date", current_iso_timestamp()[:10]),
                                publication_date=current_iso_timestamp()[:10],
                                learning_start_date=start_d,
                                learning_end_date=end_d,
                                project_start_date=start_d,
                                project_end_date=end_d,
                                submission_deadline=end_d,
                                review_date=end_d,
                                expected_award_date=end_d,
                                status="active",
                                review_window_json=json.dumps(r_dates) if r_dates else "[]"
                            )
                            store.save_timeline(new_tl)
                        else:
                            tl.status = "active"
                            if rev_id:
                                tl.reviewer_id = rev_id
                            if r_dates:
                                tl.review_date = end_d
                                tl.submission_deadline = end_d
                                tl.review_window_json = json.dumps(r_dates)
                            store.save_timeline(tl)

                # Ensure assigned_cosmonaut_ids includes all mapped cids
                for cid in all_mapped_cids:
                    if cid not in badge.assigned_cosmonaut_ids:
                        badge.assigned_cosmonaut_ids.append(cid)
                    store.add_notification(
                        recipient_id=cid,
                        title=f"🚀 Milestone Unlocked: {badge.code}",
                        message=f"Milestone '{badge.title}' has been published to your active roadmap. Explore the curriculum & prepare for your sprint.",
                        event_type="milestone",
                        link_section="c_submission"
                    )

                # If no mapped cadets exist yet, fallback to cohort
                if not all_mapped_cids:
                    for c in store.get_all_cosmonauts():
                        if getattr(c, "band", "") == b_band:
                            tl = store.get_timeline(badge.id, c.id)
                            if not tl:
                                new_tl = BadgeTimeline(
                                    badge_id=badge.id,
                                    cosmonaut_id=c.id,
                                    assignment_date=dt.get("assignment_date", "2026-11-10"),
                                    publication_date=dt.get("publication_date", "2026-11-10"),
                                    learning_start_date=dt.get("learning_start_date", "2026-11-11"),
                                    learning_end_date=dt.get("learning_end_date", "2026-11-20"),
                                    project_start_date=dt.get("project_start_date", "2026-11-21"),
                                    project_end_date=dt.get("project_end_date", "2026-12-01"),
                                    submission_deadline=dt.get("submission_deadline", "2026-12-03"),
                                    review_date=dt.get("review_date", "2026-12-06"),
                                    expected_award_date=dt.get("expected_award_date", "2026-12-08"),
                                    status="active"
                                )
                                store.save_timeline(new_tl)
                            if c.id not in badge.assigned_cosmonaut_ids:
                                badge.assigned_cosmonaut_ids.append(c.id)
                            store.add_notification(
                                recipient_id=c.id,
                                title=f"🚀 Milestone Unlocked: {badge.code}",
                                message=f"Milestone '{badge.title}' has been published to your active roadmap. Explore the curriculum & prepare for your sprint.",
                                event_type="milestone",
                                link_section="c_submission"
                            )

                store.save_badge(badge)
                for cid in all_mapped_cids:
                    store.add_activity(
                        event_type="milestone_published_for_cadet",
                        actor_id=self.current_user.id if self.current_user else "guardian_1",
                        actor_name=self.current_user.name if self.current_user else "Guardian",
                        cosmonaut_id=cid,
                        badge_id=badge.id,
                        summary=f"Published Milestone {badge.code} ({badge.title}) to {cid}",
                        details=f"Band {b_band} milestone unlocked for mapped cadet."
                    )
                store.add_activity("badge_published", self.current_user.id if self.current_user else "guardian_1", self.current_user.name if self.current_user else "Guardian", "", badge.id, f"Published {badge.code}: {badge.title} — ready for mapping & curriculum")
                self.set_flash(f"Published {badge.code}: {badge.title}! It is now active on Reviewer and Cosmonaut roadmaps.", "success")

        elif action == "unpublish_badge":
            badge_id = payload.get("badge_id") if isinstance(payload, dict) else payload
            badge = store.get_badge(badge_id)
            if badge:
                badge.is_published = False
                store.save_badge(badge)
                store.add_activity("badge_unpublished", self.current_user.id, self.current_user.name, "", badge.id, f"Unpublished {badge.code}: {badge.title}")
                self.set_flash(f"Unpublished {badge.code} from active roadmaps.", "info")

        elif action == "open_create_badge_modal":
            self.active_modal = "create_badge"

        elif action == "open_edit_badge_modal":
            badge_id = payload.get("badge_id") if isinstance(payload, dict) else payload
            self.active_modal = "edit_badge"
            self.modal_payload = {"badge_id": badge_id}

        elif action == "save_badge_form":
            self.execute_save_badge(payload)

        elif action == "open_add_material_modal":
            self.active_modal = "add_material"

        elif action in ("save_bulk_materials", "save_material_form"):
            self.execute_save_bulk_materials(payload)

        elif action == "open_edit_material_modal":
            mat_id = payload.get("material_id") if isinstance(payload, dict) else payload
            self.active_modal = "edit_material"
            self.modal_payload = {"material_id": mat_id}

        elif action == "update_material":
            self.execute_update_material(payload)

        elif action == "delete_material":
            mat_id = payload.get("material_id") if isinstance(payload, dict) else payload
            store.delete_material(mat_id)
            self.set_flash("Learning material deleted successfully.", "info")

        elif action == "open_extension_decision_modal":
            self.active_modal = "decide_extension"
            if isinstance(payload, str) and payload.strip():
                try:
                    payload = json.loads(payload)
                except Exception:
                    pass
            self.modal_payload = payload

        elif action == "submit_extension_decision":
            self.execute_extension_decision(payload)

        elif action == "open_create_announcement_modal":
            self.active_modal = "create_announcement"

        elif action == "broadcast_announcement":
            self.execute_broadcast_announcement(payload)

        # --- Cosmonaut Specific Actions ---
        elif action == "add_skill":
            skill = payload if isinstance(payload, str) else payload.get("skill")
            if skill and self.current_user:
                profile = store.get_cosmonaut_profile(self.current_user.id)
                if skill not in profile.skills:
                    profile.skills.append(skill)
                    store.save_profile(profile)
                    self.set_flash(f"Added skill '{skill}' to profile.", "success")

        elif action == "remove_skill":
            skill = payload if isinstance(payload, str) else payload.get("skill")
            if skill and self.current_user:
                profile = store.get_cosmonaut_profile(self.current_user.id)
                if skill in profile.skills:
                    profile.skills.remove(skill)
                    store.save_profile(profile)
                    self.set_flash(f"Removed skill '{skill}'.", "info")

        elif action == "add_certification":
            if isinstance(payload, dict) and self.current_user:
                profile = store.get_cosmonaut_profile(self.current_user.id)
                profile.certifications.append(payload)
                store.save_profile(profile)
                self.set_flash(f"Added certification '{payload.get('name')}' to profile.", "success")

        elif action == "remove_certification":
            idx = int(payload if isinstance(payload, (int, str)) else payload.get("index", 0))
            if self.current_user:
                profile = store.get_cosmonaut_profile(self.current_user.id)
                if 0 <= idx < len(profile.certifications):
                    del profile.certifications[idx]
                    store.save_profile(profile)
                    self.set_flash("Removed certification.", "info")

        elif action == "change_submission_target_badge":
            badge_id = payload if isinstance(payload, str) else payload.get("badge_id")
            self.cosmonaut_submission_badge_id = badge_id

        elif action == "change_results_badge":
            badge_id = payload if isinstance(payload, str) else payload.get("badge_id")
            self.cosmonaut_results_badge_id = badge_id
            self.cosmonaut_results_picked = True
            self.cosmonaut_results_asm_id = ""

        elif action == "select_results_marksheet":
            # an evaluation tab on the marksheet page (attempt / reviewer / Guardian); only the cosmonaut's own marksheets can be shown
            asm_id = payload if isinstance(payload, str) else (payload.get("marksheet_id", "") if isinstance(payload, dict) else "")
            asm = store.get_assessment(str(asm_id).strip().replace('"', ''))
            if asm and self.current_user and asm.cosmonaut_id == self.current_user.id:
                self.cosmonaut_results_badge_id = asm.badge_id
                self.cosmonaut_results_picked = True
                self.cosmonaut_results_asm_id = asm.id

        elif action == "open_badge_marksheet":
            # "Official marksheet" / "View marks" from a badge or project page: the marksheet page on THAT badge
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            b_id = str(b_id).strip().replace('"', '')
            if b_id and store.get_badge(b_id):
                self._push_history()
                self.cosmonaut_results_badge_id = b_id
                self.cosmonaut_results_picked = True
                self.cosmonaut_results_asm_id = ""
                self.current_view = "c_results"
                self.active_modal = None

        elif action == "toggle_submission_method_fields":
            method = payload if isinstance(payload, str) else payload.get("method")
            if IS_BROWSER:
                gh_field = js.document.getElementById("field-github-container")
                file_field = js.document.getElementById("field-file-container")
                label = js.document.getElementById("file-input-label")
                file_inp = js.document.getElementById("submission-file-input")
                if gh_field and file_field and label and file_inp:
                    if method == "github":
                        gh_field.style.display = "block"
                        file_field.style.display = "none"
                    elif method == "code":
                        gh_field.style.display = "none"
                        file_field.style.display = "block"
                        label.innerText = "Select Code / Script File (.py, .sql, .js, .json)"
                        file_inp.accept = ".py,.sql,.js,.json,.txt"
                    else:  # pdf
                        gh_field.style.display = "none"
                        file_field.style.display = "block"
                        label.innerText = "Select PDF Document (.pdf)"
                        file_inp.accept = ".pdf"
            return  # Do not re-render full DOM on simple DOM field toggle

        elif action == "open_submission_review_page":
            is_guardian = (getattr(self.current_user, "role", "") == "guardian" or "guardian" in getattr(self.current_user, "roles", []))
            if not is_guardian:
                self.set_flash("Unauthorized: Only Guardians can access the Guardian review detail portal.", "error")
                return
            self._push_history()
            sub_id = payload if isinstance(payload, str) else payload.get("submission_id", "")
            self.selected_review_sub_id = sub_id
            self.selected_viewer_tab = "pdf"
            self.current_view = "g_review_detail"

        elif action == "change_viewer_tab":
            tab = payload if isinstance(payload, str) else payload.get("tab", "pdf")
            if tab == "odf":
                tab = "pdf"
            self.selected_viewer_tab = tab

        elif action in ("submit_evaluation_marksheet", "submit_evaluation_rubric", "submit_guardian_final_assessment", "earn_badge", "award_badge"):
            self.execute_submit_evaluation(payload, default_role="guardian")
            self.current_view = "g_reviews"

        elif action == "submit_reviewer_assessment":
            self.execute_submit_evaluation(payload, default_role="reviewer")
            self.current_view = "c_badge_reviews"

        elif action == "open_reviewer_assessment_page":
            self._push_history()
            if not self.current_user:
                self.set_flash("Authentication required.", "error")
                return
            sub_id = payload if isinstance(payload, str) else (payload.get("submission_id", "") if isinstance(payload, dict) else "")
            sub = store.get_submission(sub_id) if sub_id else None
            if sub:
                is_guardian = (getattr(self.current_user, "role", "") == "guardian" or "guardian" in getattr(self.current_user, "roles", []))
                tl = store.get_timeline(sub.badge_id, sub.cosmonaut_id)
                is_assigned = (tl and getattr(tl, "reviewer_id", "") == self.current_user.id)
                if not is_assigned:
                    badge = store.get_badge(sub.badge_id)
                    if badge and getattr(badge, "assigned_reviewer_id", "") == self.current_user.id and sub.cosmonaut_id in getattr(badge, "assigned_cosmonaut_ids", []):
                        is_assigned = True
                if not is_assigned:
                    for m in store.get_band_mappings():
                        if self.current_user.id in m.get("reviewers", []) and sub.cosmonaut_id in m.get("cosmonauts", []):
                            m_b = m.get("badge_id") or m.get("badge")
                            badge = store.get_badge(sub.badge_id)
                            if (m_b == sub.badge_id) or (badge and m_b in (badge.title, badge.code, badge.id)):
                                is_assigned = True
                                break
                if not (is_assigned or is_guardian):
                    self.set_flash("Unauthorized: You are not assigned to evaluate this submission.", "error")
                    self.current_view = "c_badge_reviews"
                    return
            self.selected_reviewer_sub_id = sub_id
            self.reviewer_selected_submission_id = sub_id
            self.selected_viewer_tab = "pdf"
            self.current_view = "c_assessment_detail"

        elif action == "open_submission_modal":
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            b_id = str(b_id).strip().replace('"', '') or getattr(self, "cosmonaut_submission_badge_id", "")
            self.cosmonaut_submission_badge_id = b_id
            if (self.current_user and b_id and not self._is_guardian_user()
                    and not store.get_project_prompt_for_cadet(b_id, self.current_user.id)):
                # Deliverables are only collected for a project the mapped reviewer has sent.
                self.set_flash("Your project has not been sent yet. It will appear under \"Project Allocated\" as soon as your mapped reviewer sends it.", "info")
            else:
                self.active_modal = "submission_portal_modal"
                self.modal_payload = {"badge_id": b_id}

        elif action in ("open_allocated_project_page", "open_allocated_project_modal", "view_allocated_project"):
            # "Project Allocated" opens the whole project as its own page (open_allocated_project_modal / view_allocated_project are
            # the old popup's names, kept so saved sessions and old buttons still land on the page).
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            b_id = str(b_id).strip().replace('"', '') or getattr(self, "cosmonaut_submission_badge_id", "")
            denied = self._allocated_project_denied(b_id)
            if denied:
                self.set_flash(denied, "info")
            else:
                self._push_history()
                self.cosmonaut_submission_badge_id = b_id
                self.current_view = "c_project"
                self.active_modal = None

        elif action == "open_reviewer_badge_timeline_modal":
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            self.active_modal = "reviewer_timeline_modal"
            self.modal_payload = {"badge_id": b_id}

        elif action in ("open_badge_timeline_mapping_modal", "open_badge_mapping_modal", "open_badge_timeline_modal"):
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            self.active_modal = {
                "open_badge_mapping_modal": "badge_mapping_view",
                "open_badge_timeline_modal": "badge_timeline_view",
            }.get(action, "badge_timeline_mapping")
            self.modal_payload = {"badge_id": b_id}

        elif action in ("open_cosmonaut_reviewer_modal", "open_cosmonaut_timeline_modal"):
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            b_id = str(b_id).strip().replace('"', '')
            uid = self.current_user.id if self.current_user else ""
            if not (store.get_badge(b_id) and uid and (store.get_timeline(b_id, uid) or b_id in {b.id for b in store.get_badges_for_cosmonaut(uid)})):
                raise ActionDenied("This badge is not allotted to you.")
            self.active_modal = "cosmonaut_reviewer_view" if action == "open_cosmonaut_reviewer_modal" else "cosmonaut_timeline_view"
            self.modal_payload = {"badge_id": b_id}

        elif action == "open_create_reviewer_project_modal":
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            self.active_modal = "reviewer_project_creator"
            self.modal_payload = {"badge_id": b_id}

        elif action == "request_project":
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            self.execute_request_project(str(b_id).strip().replace('"', ''))

        elif action in ("send_reviewer_project", "save_reviewer_project_prompt"):
            if isinstance(payload, str) and payload.strip():
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            if not isinstance(payload, dict):
                payload = {}
            badge_id = payload.get("badge_id", "")
            title = payload.get("title", "")
            objective = payload.get("content") or payload.get("objective") or payload.get("scenario") or payload.get("description") or ""
            tech_reqs = payload.get("technical_requirements") or payload.get("requirements") or []
            eval_crit = payload.get("evaluation_criteria") or payload.get("rubric_guidelines") or []
            sub_deadline = payload.get("submission_deadline", "")
            deliverables = payload.get("deliverables", {})
            cosmonaut_ids = payload.get("cosmonaut_ids", [])
            status = payload.get("status") or "released"

            raw_outcomes = payload.get("outcomes") or []
            if isinstance(raw_outcomes, str):
                outcomes = [x.strip() for x in raw_outcomes.split("\n") if x.strip()]
            elif isinstance(raw_outcomes, list):
                outcomes = [str(x).strip() for x in raw_outcomes if str(x).strip()]
            else:
                outcomes = []

            if not self.current_user:
                raise ActionDenied("Please sign in to create a project brief.")
            # AUTHORISATION: only a reviewer mapped to this badge (or a Guardian) may author / release its project
            # brief, and only to cadets they are responsible for. Previously any user could release a brief for
            # any badge to any cadets.
            if badge_id and not self._is_guardian_user():
                mapped_cadets = self._reviewer_cadets_for_badge(self.current_user.id, badge_id)
                if not mapped_cadets:
                    raise ActionDenied("You are not the mapped reviewer for this badge, so you cannot release its project.")
                if cosmonaut_ids:
                    cosmonaut_ids = [c for c in cosmonaut_ids if c in mapped_cadets]
                    if not cosmonaut_ids:
                        raise ActionDenied("None of the selected cadets is mapped to you for this badge.")
            rev_id = self.current_user.id
            rev_user = store.get_user_by_id(rev_id) if store else None
            rev_name = (self.current_user.name if self.current_user else None) or (rev_user.name if rev_user else None) or "Authorized Reviewer"

            # Auto-resolve mapped cadets if not explicitly passed
            if not cosmonaut_ids and badge_id:
                b_obj = store.get_badge(badge_id)
                for m in store.get_band_mappings():
                    rev_list = m.get("reviewers", [])
                    if rev_id in rev_list:
                        m_b = m.get("badge_id") or m.get("badge")
                        if m_b == badge_id or (b_obj and m_b in (b_obj.title, b_obj.code, b_obj.id)):
                            cosmo_list = m.get("cosmonauts", [])
                            for idx, cid in enumerate(cosmo_list):
                                if len(rev_list) > 1:
                                    if rev_list[idx % len(rev_list)] != rev_id:
                                        continue
                                if cid not in cosmonaut_ids:
                                    cosmonaut_ids.append(cid)
                for tl in store.get_timelines_dict().values():
                    if getattr(tl, "reviewer_id", "") == rev_id and getattr(tl, "badge_id", "") == badge_id:
                        cid = getattr(tl, "cosmonaut_id", "")
                        if cid and cid not in cosmonaut_ids:
                            cosmonaut_ids.append(cid)
                if b_obj and getattr(b_obj, "assigned_reviewer_id", "") == rev_id:
                    for cid in getattr(b_obj, "assigned_cosmonaut_ids", []):
                        if cid not in cosmonaut_ids:
                            cosmonaut_ids.append(cid)
                if not cosmonaut_ids:
                    for m in store.get_band_mappings():
                        m_b = m.get("badge_id") or m.get("badge")
                        if m_b == badge_id or (b_obj and m_b in (b_obj.title, b_obj.code, b_obj.id)):
                            for cid in m.get("cosmonauts", []):
                                if cid not in cosmonaut_ids:
                                    cosmonaut_ids.append(cid)

            title = str(title or "").strip()
            objective = str(objective or "").strip()
            if status != "draft":
                if not title:
                    raise ActionDenied("Give the project a heading before sending it.")
                if not objective:
                    raise ActionDenied("Write the project content before sending it.")
            if len(title) > 200 or len(objective) > 20000:
                raise ActionDenied("The project heading (200 characters) or content (20,000 characters) is too long.")
            if status != "draft" and not cosmonaut_ids:
                raise ActionDenied("Select at least one mapped cosmonaut to send the project to.")
            # Every send is its own record (history is kept; a later project never silently rewrites an earlier one).
            prompt_id = f"proj_{badge_id}_{rev_id}" if status == "draft" else f"proj_{badge_id}_{rev_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
            prompt = ReviewerProjectPrompt(
                id=prompt_id,
                badge_id=badge_id,
                reviewer_id=rev_id,
                reviewer_name=rev_name,
                title=title,
                objective=objective,
                description=objective,
                technical_requirements=tech_reqs,
                evaluation_criteria=eval_crit,
                submission_deadline=sub_deadline,
                deliverables=deliverables,
                cosmonaut_ids=cosmonaut_ids,
                outcomes=outcomes,
                status=status,
                created_at=current_iso_timestamp(),
                sent_at=current_iso_timestamp() if status != "draft" else None
            )
            store.save_reviewer_project_prompt(prompt)

            badge = store.get_badge(badge_id)
            b_title = badge.title if badge else "Assigned Milestone"
            if status != "draft":
                for cid in cosmonaut_ids:   # their open requests are answered by this project
                    req = store.get_project_request(badge_id, cid)
                    if req:
                        req.status = "fulfilled"
                        store.save_reviewer_project_prompt(req)

            if status == "draft":
                store.add_activity(
                    event_type="reviewer_project_draft_saved",
                    actor_id=rev_id,
                    actor_name=rev_name,
                    cosmonaut_id=cosmonaut_ids[0] if cosmonaut_ids else "",
                    badge_id=badge_id,
                    summary=f"Saved Project Draft: '{title}' by {rev_name}",
                    details=f"Draft saved for {b_title} ({len(cosmonaut_ids)} mapped cadets)."
                )
                self.set_flash(f"Project draft for '{title}' saved successfully.", "success")
            else:
                for cid in cosmonaut_ids:
                    store.add_notification(
                        recipient_id=cid,
                        title=f"Project received: {title}",
                        message=f"{rev_name} sent you the project '{title}' for '{b_title}'. Open the badge and choose Submit Project Deliverables.",
                        event_type="milestone",
                        link_section="c_submission"
                    )
                    store.add_activity(
                        event_type="reviewer_project_assigned",
                        actor_id=rev_id,
                        actor_name=rev_name,
                        cosmonaut_id=cid,
                        badge_id=badge_id,
                        summary=f"Project Assigned: '{title}' by {rev_name}",
                        details=f"{rev_name} released project '{title}' to mapped cadet {cid} for {b_title}."
                    )
                if not cosmonaut_ids:
                    store.add_activity(
                        event_type="reviewer_project_assigned",
                        actor_id=rev_id,
                        actor_name=rev_name,
                        cosmonaut_id="",
                        badge_id=badge_id,
                        summary=f"Project Released: '{title}' by {rev_name}",
                        details=f"{rev_name} released project '{title}' for {b_title}."
                    )
                self.set_flash(f"Project '{title}' sent to {len(cosmonaut_ids)} mapped cosmonaut{'s' if len(cosmonaut_ids) != 1 else ''}.", "success")

            self.active_modal = None
            self.modal_payload = {}

        elif action in ("submit_project_deliverable", "submit_project_deliverables"):
            self.execute_submit_project(payload)

        elif action == "submit_deadline_extension_request":
            self.execute_submit_extension_request(payload)

        elif action == "mark_announcement_as_read":
            ann_id = payload.get("announcement_id") if isinstance(payload, dict) else payload
            if self.current_user:
                store.mark_announcement_read(ann_id, self.current_user.id)
                self.set_flash("Marked announcement as read.", "info")

        elif action == "recalc_rubric_total":
            if IS_BROWSER:
                try:
                    bu = float(js.document.getElementById("rubric-bu").value or 0)
                    ar = float(js.document.getElementById("rubric-ar").value or 0)
                    tk = float(js.document.getElementById("rubric-tk").value or 0)
                    pr = float(js.document.getElementById("rubric-pr").value or 0)
                    qa = float(js.document.getElementById("rubric-qa").value or 0)
                    tot, pct = calculate_assessment_totals(bu, ar, tk, pr, qa)
                    disp = js.document.getElementById("rubric-total-display")
                    if disp:
                        disp.innerText = f"{tot:.1f} / 50.0 ({pct:.1f}%)"
                except Exception:
                    pass
            return

        self.sync_storage()
        self._last_render_source = f"action:{action}"
        self.render()

    # ==========================================================================
    # WORKFLOW EXECUTION HELPERS
    # ==========================================================================

    def execute_submit_evaluation(self, payload: Any = None, default_role: str = "guardian"):
        if not self.current_user:
            return

        payload_dict = {}
        sub_id = ""

        if isinstance(payload, dict):
            payload_dict = payload
            sub_id = payload.get("submission_id") or payload.get("sub_id") or ""
        elif isinstance(payload, str) and payload.strip():
            if payload.strip().startswith("{"):
                try:
                    payload_dict = json.loads(payload)
                    if isinstance(payload_dict, dict):
                        sub_id = payload_dict.get("submission_id") or payload_dict.get("sub_id") or ""
                except Exception:
                    payload_dict = {}
            else:
                sub_id = payload.strip()

        sub_id = sub_id or getattr(self, "selected_review_sub_id", "") or getattr(self, "selected_reviewer_sub_id", "")
        sub = store.get_submission(sub_id)
        if not sub and hasattr(self, "selected_review_sub_id") and self.selected_review_sub_id:
            sub = store.get_submission(self.selected_review_sub_id)
        if not sub and hasattr(self, "selected_reviewer_sub_id") and self.selected_reviewer_sub_id:
            sub = store.get_submission(self.selected_reviewer_sub_id)

        if not sub:
            self.set_flash("Submission record not found.", "error")
            return

        assessor_role = payload_dict.get("assessor_role") or default_role
        user_roles = getattr(self.current_user, "roles", [self.current_user.role])
        if "guardian" not in user_roles and assessor_role == "guardian":
            assessor_role = "reviewer"

        # A finalised attempt is immutable. Marksheet ids are deterministic (asm_<role>_<submission>_<attempt>)
        # and saved with INSERT OR REPLACE, so a second grading used to silently overwrite the final result
        # (for example turning an earned badge back into a retake).
        if sub.status in ("approved", "retake_required", "resubmission_requested"):
            self.set_flash("This attempt has already received a final decision and can no longer be re-graded.", "info")
            return

        try:
            bu = float(payload_dict.get("bu", 0)) if "bu" in payload_dict else None
            ar = float(payload_dict.get("ar", 0)) if "ar" in payload_dict else None
            tk = float(payload_dict.get("tk", 0)) if "tk" in payload_dict else None
            pr = float(payload_dict.get("pr", 0)) if "pr" in payload_dict else None
            qa = float(payload_dict.get("qa", 0)) if "qa" in payload_dict else None
            strengths = payload_dict.get("strengths", "")
            improvements = payload_dict.get("improvements", "")
            feedback = payload_dict.get("feedback", "")
            decision = payload_dict.get("decision", "")

            if IS_BROWSER and hasattr(js, "document"):
                if bu is None:
                    bu_el = js.document.getElementById("rubric-bu")
                    bu = float(bu_el.value) if bu_el and bu_el.value else None
                if ar is None:
                    ar_el = js.document.getElementById("rubric-ar")
                    ar = float(ar_el.value) if ar_el and ar_el.value else None
                if tk is None:
                    tk_el = js.document.getElementById("rubric-tk")
                    tk = float(tk_el.value) if tk_el and tk_el.value else None
                if pr is None:
                    pr_el = js.document.getElementById("rubric-pr")
                    pr = float(pr_el.value) if pr_el and pr_el.value else None
                if qa is None:
                    qa_el = js.document.getElementById("rubric-qa")
                    qa = float(qa_el.value) if qa_el and qa_el.value else None
                if not strengths:
                    str_el = js.document.getElementById("rubric-strengths")
                    strengths = str(str_el.value).strip() if str_el and str_el.value else ""
                if not improvements:
                    imp_el = js.document.getElementById("rubric-improvements")
                    improvements = str(imp_el.value).strip() if imp_el and imp_el.value else ""
                if not feedback:
                    fb_el = js.document.getElementById("rubric-feedback")
                    feedback = str(fb_el.value).strip() if fb_el and fb_el.value else ""
                if not decision:
                    dec_el = js.document.getElementById("rubric-decision")
                    decision = str(dec_el.value).strip() if dec_el and dec_el.value else ""

            rev_asm = store.get_reviewer_assessment_for_submission(sub.id)
            if assessor_role == "guardian" and rev_asm:
                default_bu = rev_asm.business_understanding
                default_ar = rev_asm.architecture_report
                default_tk = rev_asm.technical_knowledge
                default_pr = rev_asm.presentation
                default_qa = rev_asm.qa
                default_strengths = rev_asm.strength_areas or "Robust architecture patterns and clean code implementation."
                default_improvements = rev_asm.improvement_areas or "Maintain consistent logging and extend test coverage."
                default_feedback = rev_asm.overall_feedback or "Approved milestone deliverables."
            else:
                default_bu = 9.0
                default_ar = 9.0
                default_tk = 9.0
                default_pr = 9.0
                default_qa = 9.0
                default_strengths = "Robust architecture patterns and clean code implementation."
                default_improvements = "Maintain consistent logging and extend test coverage."
                default_feedback = "Approved milestone deliverables."

            if assessor_role == "reviewer" and not feedback:
                feedback = " ".join(t for t in (strengths, improvements) if t).strip()      # the reviewer panel has no separate remarks box
            bu = default_bu if bu is None else bu
            ar = default_ar if ar is None else ar
            tk = default_tk if tk is None else tk
            pr = default_pr if pr is None else pr
            qa = default_qa if qa is None else qa
            strengths = strengths or default_strengths
            improvements = improvements or default_improvements
            feedback = feedback or default_feedback

            valid, err = validate_rubric_scores(bu, ar, tk, pr, qa)
            if not valid:
                self.set_flash(f"Scoring error: {err}", "error")
                return

            badge = store.get_badge(sub.badge_id)
            b_name = badge.code if badge else sub.badge_id
            cosmo = store.get_user_by_id(sub.cosmonaut_id)
            cosmo_name = cosmo.name if cosmo else sub.cosmonaut_id
            badge_thresh = getattr(badge, "passing_percentage", 70.0) if badge else 70.0

            total_m = bu + ar + tk + pr + qa
            pct = (total_m / 50.0) * 100.0

            if assessor_role == "reviewer":
                # Strict authorization: Verify this reviewer is assigned to this submission
                tl = store.get_timeline(sub.badge_id, sub.cosmonaut_id)
                is_authorized_reviewer = (tl and getattr(tl, "reviewer_id", "") == self.current_user.id)
                if not is_authorized_reviewer:
                    for m in store.get_band_mappings():
                        if self.current_user.id in m.get("reviewers", []) and sub.cosmonaut_id in m.get("cosmonauts", []):
                            m_badge = m.get("badge_id") or m.get("badge")
                            if (m_badge == sub.badge_id) or (badge and m_badge in (badge.title, badge.code, badge.id)):
                                is_authorized_reviewer = True
                                break
                if not is_authorized_reviewer:
                    # same rule as the project / submission routing: the reviewer mapped to this cosmonaut for this badge (incl. the badge's own reviewer)
                    is_authorized_reviewer = store.get_mapped_reviewer_id(sub.badge_id, sub.cosmonaut_id) == self.current_user.id
                is_guardian = "guardian" in user_roles
                if not (is_authorized_reviewer or is_guardian):
                    self.set_flash("Unauthorized: You are not assigned to evaluate this cadet's milestone project.", "error")
                    return

                # Marks are final per attempt: once submitted they cannot be redone - a new assessment opens only for a new attempt
                if store.get_reviewer_assessment_for_submission(sub.id) or sub.status in ("reviewer_assessed", "approved", "retake_required", "resubmission_requested"):
                    self.set_flash("Marks for this attempt are already submitted and locked. A new assessment opens only if the cosmonaut makes a new attempt.", "info")
                    return

                # The reviewer RECOMMENDS (Give Badge / Re-attempt / Reject); the Guardian checks it and gives the final decision.
                rec = normalize_decision(decision)
                if rec == "approve" and pct < badge_thresh:
                    self.set_flash(f"Score {pct:.1f}% is below the {badge_thresh:.0f}% pass mark, so the badge cannot be recommended. Choose Re-attempt or Reject.", "error")
                    return
                rec_label = REVIEWER_RECOMMENDATIONS[rec]["label"] if rec else ""

                asm_id = f"asm_rev_{sub.id}_{sub.attempt_number}"
                decision = {"approve": "recommend_approve", "resubmission_requested": "recommend_resubmit", "reject": "recommend_reject"}.get(rec, "reviewer_assessed")
                marksheet = AssessmentMarksheet(
                    id=asm_id,
                    submission_id=sub.id,
                    attempt_number=sub.attempt_number,
                    badge_id=sub.badge_id,
                    cosmonaut_id=sub.cosmonaut_id,
                    reviewer_id=self.current_user.id,
                    reviewer_name=self.current_user.name,
                    reviewed_at=current_iso_timestamp(),
                    decision=decision,
                    business_understanding=bu,
                    architecture_report=ar,
                    technical_knowledge=tk,
                    presentation=pr,
                    qa=qa,
                    strength_areas=strengths,
                    improvement_areas=improvements,
                    overall_feedback=feedback,
                    assessor_role="reviewer",
                    remarks=feedback
                )
                store.save_assessment(marksheet)

                sub.status = "reviewer_assessed"
                store.save_submission(sub)

                tl = store.get_timeline(sub.badge_id, sub.cosmonaut_id)
                if tl:
                    tl.status = "reviewer_assessed"
                    store.save_timeline(tl)

                store.add_activity(
                    event_type="reviewer_assessment_completed",
                    actor_id=self.current_user.id,
                    actor_name=self.current_user.name,
                    cosmonaut_id=sub.cosmonaut_id,
                    badge_id=sub.badge_id,
                    summary=f"Reviewer Assessment: {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%) for {cosmo_name}",
                    details=f"{self.current_user.name} graded Attempt #{sub.attempt_number}" + (f" and recommends: {rec_label}" if rec_label else "") + ". Awaiting Guardian final decision."
                )

                self.cosmonaut_results_badge_id = sub.badge_id

                store.add_notification(
                    recipient_id=sub.cosmonaut_id,
                    title=f"Assessment Graded: {b_name}",
                    message=f"{self.current_user.name} has evaluated your deliverables for {b_name} with score {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%). Check your Assessment Marksheet for details.",
                    link_section="c_results"
                )

                store.add_notification(
                    recipient_id="guardian_1",
                    title=f"Reviewer Assessed: {cosmo_name}",
                    message=f"{self.current_user.name} completed reviewer evaluation for {cosmo_name} on {b_name} ({marksheet.total_marks:.1f}/50)" + (f" and recommends: {rec_label}" if rec_label else "") + ". Awaiting your final decision.",
                    link_section="g_reviews"
                )

                self.set_flash(f"Reviewer assessment for {cosmo_name} saved successfully ({marksheet.total_marks:.1f}/50). Awaiting Guardian final decision" + (f" (you recommended: {rec_label})." if rec_label else "."), "success")

            else:  # guardian
                asm_id = f"asm_g_{sub.id}_{sub.attempt_number}"
                # The Guardian's choice (Earn Badge / Resubmit / Reject) decides; with no choice the pass mark decides, as before.
                g_choice = normalize_decision(decision) or ("approve" if pct >= badge_thresh else "resubmission_requested")
                if g_choice == "approve" and pct < badge_thresh:
                    self.set_flash(f"Score {pct:.1f}% is below the {badge_thresh:.0f}% pass mark, so the badge cannot be awarded. Choose Resubmit or Reject.", "error")
                    return
                is_pass = g_choice == "approve"
                if is_pass:
                    decision = "approve"
                    sub.status = "approved"
                else:
                    decision = "rejected" if g_choice == "reject" else "resubmission_requested"
                    sub.status = "retake_required"          # a rejected attempt is closed too: the cosmonaut can start a new attempt

                marksheet = AssessmentMarksheet(
                    id=asm_id,
                    submission_id=sub.id,
                    attempt_number=sub.attempt_number,
                    badge_id=sub.badge_id,
                    cosmonaut_id=sub.cosmonaut_id,
                    reviewer_id=self.current_user.id,
                    reviewer_name=self.current_user.name,
                    reviewed_at=current_iso_timestamp(),
                    decision=decision,
                    business_understanding=bu,
                    architecture_report=ar,
                    technical_knowledge=tk,
                    presentation=pr,
                    qa=qa,
                    strength_areas=strengths,
                    improvement_areas=improvements,
                    overall_feedback=feedback,
                    assessor_role="guardian",
                    remarks=feedback
                )
                store.save_assessment(marksheet)
                store.save_submission(sub)

                tl = store.get_timeline(sub.badge_id, sub.cosmonaut_id)
                if tl:
                    if is_pass:
                        tl.status = "completed"
                        tl.actual_award_date = current_iso_timestamp()[:10]
                    else:
                        tl.status = "retake_required"
                    store.save_timeline(tl)

                # Pre-select this badge in Cosmonaut results view
                self.cosmonaut_results_badge_id = sub.badge_id

                if is_pass:
                    # Uncouple mapping: move cadet to completed/certified list
                    store.uncouple_cadet_badge_mapping(sub.badge_id, sub.cosmonaut_id)

                    store.add_activity(
                        event_type="badge_awarded",
                        actor_id=self.current_user.id,
                        actor_name=self.current_user.name,
                        cosmonaut_id=sub.cosmonaut_id,
                        badge_id=sub.badge_id,
                        summary=f"Milestone Badge Awarded: {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%) to {cosmo_name}",
                        details=f"Evaluated Attempt #{sub.attempt_number}. Score meets passing threshold of {badge_thresh:.1f}%."
                    )
                    store.add_notification(
                        recipient_id=sub.cosmonaut_id,
                        title=f"🏆 Badge Earned: {b_name}",
                        message=f"Congratulations! You were awarded {b_name} with a final score of {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%).",
                        link_section="c_submission"
                    )
                    self.set_flash(f"🏆 Badge Earned! Final assessment published! {cosmo_name} achieved {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}% >= {badge_thresh}% threshold). Badge awarded! (Gold certification)", "success")
                else:
                    store.add_activity(
                        event_type="retake_required",
                        actor_id=self.current_user.id,
                        actor_name=self.current_user.name,
                        cosmonaut_id=sub.cosmonaut_id,
                        badge_id=sub.badge_id,
                        summary=(f"Attempt Rejected: {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%) for {cosmo_name}" if g_choice == "reject"
                                 else f"Retake Required: {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%) for {cosmo_name}"),
                        details=(f"Evaluated Attempt #{sub.attempt_number}. The Guardian rejected this attempt; the cosmonaut can start a new one." if g_choice == "reject"
                                 else f"Evaluated Attempt #{sub.attempt_number}. A new attempt was requested (score {marksheet.percentage:.1f}% vs {badge_thresh:.1f}% pass mark).")
                    )
                    store.add_notification(
                        recipient_id=sub.cosmonaut_id,
                        title=(f"Attempt Rejected: {b_name}" if g_choice == "reject" else f"Retake Required: {b_name}"),
                        message=f"Score for Attempt #{sub.attempt_number} was {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}% vs {badge_thresh}% passing threshold). Please review feedback and resubmit Attempt #{sub.attempt_number + 1}.",
                        link_section="c_submission"
                    )
                    self.set_flash(f"Final assessment published. Score {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%) is below {badge_thresh}% threshold. Retake required for {cosmo_name}.", "warning")

            self.active_modal = None
        except Exception as e:
            self.set_flash(f"Assessment error: {e}", "error")

    def execute_revoke_guardian_decision(self, sub_id: str):
        """
        The Guardian undoes their final decision (badge earned / re-attempt / rejected) on a submission. The submission goes back to
        "ready for sign-off" with the reviewer's marks and recommendation untouched, and the Guardian can decide again. Only the
        CURRENT attempt can be revoked (once the cosmonaut has started a newer attempt the old decision is history).
        """
        self.active_modal = None
        self.modal_payload = {}
        sub = store.get_submission(sub_id) if sub_id else None
        g_asm = store.get_guardian_assessment_for_submission(sub_id) if sub else None
        if not (sub and g_asm and sub.status in ("approved", "retake_required", "resubmission_requested")):
            self.set_flash("There is no final decision to revoke on this submission.", "warning")
            return
        newest = (store.get_submissions_for_cosmonaut(sub.cosmonaut_id, sub.badge_id) or [sub])[-1]
        if newest.id != sub.id:
            self.set_flash("The cosmonaut has already started a newer attempt, so this earlier decision cannot be revoked.", "warning")
            return
        badge = store.get_badge(sub.badge_id)
        b_name = badge.code if badge else sub.badge_id
        cosmo = store.get_user_by_id(sub.cosmonaut_id)
        cosmo_name = cosmo.name if cosmo else sub.cosmonaut_id
        was = {"approve": "badge earned", "approved": "badge earned", "rejected": "rejected"}.get((g_asm.decision or "").lower(), "re-attempt requested")
        had_badge = sub.status == "approved"
        store.delete_assessment(g_asm.id)
        rev_asm = store.get_reviewer_assessment_for_submission(sub.id)
        sub.status = "reviewer_assessed" if rev_asm else "pending"
        store.save_submission(sub)
        tl = store.get_timeline(sub.badge_id, sub.cosmonaut_id)
        if tl:
            tl.status = "reviewer_assessed" if rev_asm else "awaiting_review"
            if had_badge:
                tl.actual_award_date = ""
            store.save_timeline(tl)
        if had_badge:
            store.recouple_cadet_badge_mapping(sub.badge_id, sub.cosmonaut_id)
        store.add_activity(
            event_type="guardian_decision_revoked", actor_id=self.current_user.id, actor_name=self.current_user.name,
            cosmonaut_id=sub.cosmonaut_id, badge_id=sub.badge_id,
            summary=f"Guardian decision revoked ({was}) for {cosmo_name}",
            details=f"{self.current_user.name} revoked the final decision on Attempt #{sub.attempt_number} (was: {was}, {g_asm.total_marks:.1f}/50). It is back with the Guardian for a new decision.")
        store.add_notification(
            recipient_id=sub.cosmonaut_id, title=f"Decision under review: {b_name}",
            message=f"The Guardian revoked the earlier decision on your Attempt #{sub.attempt_number} ({was}). It is being reconsidered; you will be notified of the new decision.",
            link_section="c_results")
        rev_id = store.get_mapped_reviewer_id(sub.badge_id, sub.cosmonaut_id)
        if rev_id:
            store.add_notification(
                recipient_id=rev_id, title=f"Guardian revoked a decision: {cosmo_name}",
                message=f"The Guardian revoked the final decision on {cosmo_name}'s Attempt #{sub.attempt_number} for {b_name}. Your marks and recommendation are unchanged.",
                link_section="c_badge_reviews")
        self.set_flash(f"Decision revoked for {cosmo_name} ({b_name}, Attempt #{sub.attempt_number}). You can decide again.", "success")

    def execute_request_project(self, badge_id: str):
        """A cosmonaut asks the reviewer they are mapped to for the project of an allotted badge."""
        user = self.current_user
        if not user:
            return
        badge = store.get_badge(badge_id) if badge_id else None
        if not badge:
            raise ActionDenied("Badge not found.")
        my_tl = store.get_timeline(badge_id, user.id)
        if not my_tl and badge_id not in {b.id for b in store.get_badges_for_cosmonaut(user.id)}:
            raise ActionDenied("This badge is not allotted to you, so you cannot request its project.")
        if (my_tl and getattr(my_tl, "status", "") == "completed") or any(
                s.status == "approved" for s in store.get_submissions_for_cosmonaut(user.id, badge_id)):
            self.set_flash(f"{badge.code} has already been earned.", "info")
            return
        if store.get_project_prompt_for_cadet(badge_id, user.id):
            self.set_flash("Your project has already been sent. Use Submit Project Deliverables.", "info")
            return
        if store.get_project_request(badge_id, user.id):
            self.set_flash("You have already requested this project. Your reviewer has been notified.", "info")
            return
        reviewer_id = store.get_mapped_reviewer_id(badge_id, user.id)
        reviewer = store.get_user_by_id(reviewer_id) if reviewer_id else None
        if not reviewer:
            self.set_flash("No reviewer is mapped to you for this badge yet. Please ask your Guardian.", "error")
            return
        now = current_iso_timestamp()
        store.save_reviewer_project_prompt(ReviewerProjectPrompt(
            id=f"projreq_{badge_id}_{user.id}",
            badge_id=badge_id,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer.name,
            cosmonaut_ids=[user.id],
            title="",
            description="",
            status="requested",
            created_at=now,
            sent_at=None,
        ))
        store.add_notification(
            recipient_id=reviewer_id,
            title=f"Project requested: {badge.code}",
            message=f"{user.name} asked you for the project of '{badge.title}'. Open Badge Reviews to create and send it.",
            event_type="project_request",
            related_badge_id=badge_id,
            link_section="c_badge_reviews",
        )
        store.add_activity(
            event_type="project_requested",
            actor_id=user.id,
            actor_name=user.name,
            cosmonaut_id=user.id,
            badge_id=badge_id,
            summary=f"Project requested for {badge.code} from {reviewer.name}",
            details=f"{user.name} requested the project for {badge.title} from mapped reviewer {reviewer.name}.",
        )
        self.set_flash(f"Project requested from {reviewer.name}. You will be notified when it arrives.", "success")

    def execute_submit_project(self, payload_dict: Any = None):
        if not self.current_user:
            return
        try:
            # Parse payload_dict if passed as JSON string
            if isinstance(payload_dict, str) and payload_dict.strip():
                try:
                    payload_dict = json.loads(payload_dict)
                except Exception:
                    payload_dict = {}
            if not isinstance(payload_dict, dict):
                payload_dict = {}

            # Read badge_id
            badge_id = payload_dict.get("badge_id")
            if not badge_id and IS_BROWSER:
                badge_el = js.document.getElementById("submission-badge-id")
                badge_id = str(badge_el.value) if badge_el else None
            badge_id = badge_id or self.cosmonaut_submission_badge_id

            badge = store.get_badge(badge_id)
            if not badge:
                self.set_flash("Invalid badge selection.", "error")
                return

            # Check prerequisites
            approved_asms = store.get_assessments_for_cosmonaut(self.current_user.id)
            approved_ids = {a.badge_id for a in approved_asms if a.decision == "approve"}
            for p in badge.prerequisites:
                if p not in approved_ids:
                    self.set_flash(f"Cannot submit: Prerequisite milestone '{p}' is not yet completed and approved.", "error")
                    return

            # ELIGIBILITY: a cadet may only submit against a badge that is mapped/assigned to them and
            # published (or one they already hold a timeline for). Previously ANY badge id was accepted.
            my_tl = store.get_timeline(badge_id, self.current_user.id)
            my_badge_ids = {b.id for b in store.get_badges_for_cosmonaut(self.current_user.id)}
            if not my_tl and badge_id not in my_badge_ids:
                self.set_flash("This milestone is not allotted to you, so deliverables cannot be submitted for it.", "error")
                return

            # The deliverables answer the project the mapped reviewer sent; without it there is nothing to submit.
            if not store.get_project_prompt_for_cadet(badge_id, self.current_user.id):
                self.set_flash("Your project has not been sent yet. Your mapped reviewer will send it; it then appears under \"Project Allocated\".", "error")
                return

            # Determine single submission / edit vs new submission
            existing_subs = store.get_submissions_for_cosmonaut(self.current_user.id, badge_id)
            latest_sub = existing_subs[-1] if existing_subs else None
            if latest_sub and latest_sub.status == "approved":
                self.set_flash(f"{badge.code} has already been earned. No further attempts are needed.", "info")
                return
            if latest_sub and latest_sub.status == "reviewer_assessed":
                self.set_flash("Your latest attempt has been graded by the reviewer and is awaiting the Guardian's final decision. "
                               "You can submit a new attempt only if a retake is requested.", "info")
                return
            # Only treat as edit if latest attempt is still pending or draft
            is_edit = bool(latest_sub and latest_sub.status in ("pending", "draft"))
            if is_edit and latest_sub:
                attempt_num = latest_sub.attempt_number
            elif latest_sub:
                attempt_num = latest_sub.attempt_number + 1
            else:
                attempt_num = 1

            # Extract fields from payload_dict or browser DOM
            pdf_name = payload_dict.get("pdf_name", "")
            pdf_payload = payload_dict.get("pdf_payload", "")
            code_name = payload_dict.get("code_name", "")
            code_payload = payload_dict.get("code_payload", "")
            gh_url = str(payload_dict.get("github_url", "")).strip()

            if IS_BROWSER:
                pdf_inp = js.document.getElementById("submission-pdf-file")
                code_inp = js.document.getElementById("submission-code-file")
                gh_inp = js.document.getElementById("submission-github-url")
                if not pdf_name and pdf_inp and hasattr(pdf_inp, "files") and pdf_inp.files and pdf_inp.files.length > 0:
                    pdf_name = pdf_inp.files[0].name
                if not code_name and code_inp and hasattr(code_inp, "files") and code_inp.files and code_inp.files.length > 0:
                    code_name = code_inp.files[0].name
                if not gh_url and gh_inp and gh_inp.value:
                    gh_url = str(gh_inp.value).strip()

            # DELIVERABLES: anything the cadet did not provide is inherited from their previous attempt.
            # Placeholder files / a fake GitHub URL are generated ONLY in demo mode -- in a real deployment
            # an empty submission used to be silently padded with dummy content that reviewers then graded.
            ref_sub = latest_sub
            if ref_sub:
                pdf_name = pdf_name or getattr(ref_sub, "pdf_name", "")
                pdf_payload = pdf_payload or getattr(ref_sub, "pdf_payload", "")
                code_name = code_name or getattr(ref_sub, "code_name", "")
                code_payload = code_payload or getattr(ref_sub, "code_payload", "")
                gh_url = gh_url or getattr(ref_sub, "github_url", "")

            demo_fill = _demo_mode_enabled()
            if not demo_fill:
                missing = [label for label, val in (
                    ("PDF architecture report", pdf_payload and pdf_name),
                    ("source-code file", code_payload and code_name),
                    ("GitHub repository URL", gh_url),
                ) if not val]
                if missing:
                    self.set_flash("Please provide all deliverables before submitting. Missing: " + ", ".join(missing) + ".", "error")
                    return

            if gh_url and not (gh_url.lower().startswith("https://") or gh_url.lower().startswith("http://")):
                self.set_flash("The GitHub repository must be a valid http(s) URL (for example https://github.com/org/repo).", "error")
                return
            if pdf_name and not pdf_name.lower().endswith(".pdf"):
                self.set_flash("The architecture report must be a PDF file.", "error")
                return
            if len(pdf_payload) > MAX_UPLOAD_CHARS or len(code_payload) > MAX_UPLOAD_CHARS:
                self.set_flash("A deliverable is too large (limit about 9 MB per file). Please upload a smaller file.", "error")
                return

            if not pdf_name:
                pdf_name = f"{self.current_user.name.split()[0]}_{badge.code}_Architecture_Report.pdf"
            if not pdf_payload:
                pdf_payload = "data/Chemistry%20Syllabus.pdf"

            if not code_name:
                code_name = f"{badge.code.lower().replace('-', '_')}_implementation.py"
            if not code_payload:
                code_payload = f'''"""
StarApp Academy: {badge.code} {badge.title} Implementation
Cosmonaut: {self.current_user.name} ({self.current_user.id})
Milestone Deliverable - Attempt #{attempt_num}
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("{badge.code}")

def execute_pipeline():
    logger.info("Initializing enterprise pipeline for {badge.title}...")
    status = "SUCCESS"
    logger.info("Pipeline executed with status: %s", status)
    return status

if __name__ == "__main__":
    execute_pipeline()
'''

            if not gh_url:
                gh_url = f"https://github.com/starapp-cosmonauts/{badge.code.lower().replace('-', '_')}-deliverable"

            if is_edit and latest_sub:
                sub = latest_sub
                sub.file_name = pdf_name
                sub.payload = pdf_payload
                sub.pdf_name = pdf_name
                sub.pdf_payload = pdf_payload
                sub.code_name = code_name
                sub.code_payload = code_payload
                sub.github_url = gh_url
                sub.submitted_at = current_iso_timestamp()
                sub.status = "pending"
                store.save_submission(sub)
                action_word = "Updated"
            else:
                sub_id = f"sub_{self.current_user.id}_{badge_id}_{attempt_num}"
                sub = ProjectSubmission(
                    id=sub_id,
                    badge_id=badge_id,
                    cosmonaut_id=self.current_user.id,
                    attempt_number=attempt_num,
                    submission_type="multi",
                    payload=pdf_payload,
                    file_name=pdf_name,
                    submitted_at=current_iso_timestamp(),
                    status="pending",
                    pdf_name=pdf_name,
                    pdf_payload=pdf_payload,
                    code_name=code_name,
                    code_payload=code_payload,
                    github_url=gh_url
                )
                store.save_submission(sub)
                action_word = "Submitted"

            # Update timeline status
            tl = store.get_timeline(badge_id, self.current_user.id)
            if tl:
                tl.status = "awaiting_review"
                store.save_timeline(tl)

            # Late-submission awareness (the deadline is recorded, never silently ignored)
            late_note = ""
            try:
                dl = datetime.date.fromisoformat(str(getattr(tl, "submission_deadline", "") or "")[:10]) if tl else None
                if dl and datetime.date.today() > dl:
                    late_note = f" Submitted {(datetime.date.today() - dl).days} day(s) after the {dl.isoformat()} deadline."
            except ValueError:
                late_note = ""

            # Log activity
            store.add_activity(
                event_type="project_submitted",
                actor_id=self.current_user.id,
                actor_name=self.current_user.name,
                cosmonaut_id=self.current_user.id,
                badge_id=badge_id,
                summary=f"Project Deliverable Submitted (Attempt #{attempt_num})",
                details=f"{self.current_user.name} submitted {badge.code}: {badge.title} with PDF, Code, and GitHub repository.{late_note}"
            )

            # Route deliverable strictly to assigned reviewer (not guardian)
            assigned_rev_id = store.get_mapped_reviewer_id(badge_id, self.current_user.id)

            if assigned_rev_id:
                store.add_notification(
                    recipient_id=assigned_rev_id,
                    title=f"Project submitted: {self.current_user.name}",
                    message=f"{self.current_user.name} submitted Attempt #{attempt_num} for {badge.code}: {badge.title}. Open Badge Reviews and use Assessment to see the deliverables and allocate marks.{late_note}",
                    link_section="c_badge_reviews"
                )

            self.active_modal = None
            self.modal_payload = {}
            self.set_flash(f"Deliverables for {badge.code} {action_word.lower()} successfully! PDF, Source Code, and GitHub repository are ready for formal assessment.", "success")
        except Exception as e:
            print("EXCEPTION in execute_submit_project:", e)
            self.set_flash(f"Submission failed: {e}", "error")

    def execute_submit_extension_request(self, payload: Dict[str, Any]):
        try:
            if isinstance(payload, str) and payload.strip():
                try:
                    payload = json.loads(payload)
                except Exception:
                    pass
            if not isinstance(payload, dict):
                payload = {}

            badge_id = payload.get("badge_id")
            prop_date = payload.get("proposed_deadline")
            reason = payload.get("reason")

            tl = store.get_timeline(badge_id, self.current_user.id)
            if not tl:
                # Previously a made-up default deadline was used, so extensions could be requested for ANY badge.
                self.set_flash("You can only request an extension for a milestone that is allotted to you.", "error")
                return
            if getattr(tl, "status", "") == "completed":
                self.set_flash("This milestone is already completed; no extension is needed.", "info")
                return
            if any(e.badge_id == badge_id and e.status == "pending" for e in store.get_extensions_for_cosmonaut(self.current_user.id)):
                self.set_flash("You already have a pending extension request for this milestone.", "info")
                return
            curr_date = tl.submission_deadline

            valid, err = validate_extension_request(curr_date, prop_date, reason)
            if not valid:
                self.set_flash(f"Request error: {err}", "error")
                return

            ext_id = f"ext_{self.current_user.id}_{badge_id}_{int(time.time() * 1000)}"
            ext = DeadlineExtension(
                id=ext_id,
                badge_id=badge_id,
                cosmonaut_id=self.current_user.id,
                current_deadline=curr_date,
                proposed_deadline=prop_date,
                reason=reason,
                status="pending"
            )
            store.save_extension(ext)

            badge = store.get_badge(badge_id)
            b_name = badge.code if badge else badge_id

            store.add_activity(
                event_type="extension_requested",
                actor_id=self.current_user.id,
                actor_name=self.current_user.name,
                cosmonaut_id=self.current_user.id,
                badge_id=badge_id,
                summary=f"Deadline Extension Requested for {b_name}",
                details=f"Proposed deadline: {prop_date}. Reason: {reason}"
            )

            store.add_notification(
                recipient_id="guardian_1",
                title="Deadline Extension Request",
                message=f"{self.current_user.name} requested an extension for {b_name} to {prop_date}.",
                link_section="g_extensions"
            )

            self.set_flash("Extension request submitted to Guardian.", "success")
        except Exception as e:
            self.set_flash(f"Failed to submit extension request: {e}", "error")

    def execute_extension_decision(self, payload: Dict[str, Any]):
        if isinstance(payload, str) and payload.strip():
            try:
                payload = json.loads(payload)
            except Exception:
                pass
        if not isinstance(payload, dict):
            payload = {}

        ext_id = payload.get("extension_id")
        decision = payload.get("decision")  # "approved" or "rejected"
        response_note = payload.get("response_note", "")

        ext = store.get_extension(ext_id)
        if ext:
            ext.status = decision
            ext.guardian_response = response_note
            ext.decided_at = current_iso_timestamp()
            store.save_extension(ext)

            # If approved, update badge timeline application-wide
            if decision == "approved":
                tl = store.get_timeline(ext.badge_id, ext.cosmonaut_id)
                if tl:
                    tl.submission_deadline = ext.proposed_deadline
                    store.save_timeline(tl)

            badge = store.get_badge(ext.badge_id)
            b_name = badge.code if badge else ext.badge_id

            store.add_activity(
                event_type=f"extension_{decision}",
                actor_id=self.current_user.id,
                actor_name=self.current_user.name,
                cosmonaut_id=ext.cosmonaut_id,
                badge_id=ext.badge_id,
                summary=f"Deadline Extension {decision.title()} for {b_name}",
                details=f"New deadline: {ext.proposed_deadline if decision == 'approved' else ext.current_deadline}. Note: {response_note}"
            )

            guardian_name = self.current_user.name if self.current_user else "Arjun Mehta"
            store.add_notification(
                recipient_id=ext.cosmonaut_id,
                title=f"Extension Request {decision.title()}",
                message=f"{guardian_name} {decision} your deadline extension request for {b_name}. Note: {response_note}",
                link_section="c_extensions"
            )

            self.active_modal = None
            self.set_flash(f"Extension request marked as {decision}.", "success")

    def execute_broadcast_announcement(self, payload: Dict[str, Any]):
        title = payload.get("title", "").strip()
        message = payload.get("message", "").strip()
        target_type = payload.get("target_type", "all")
        target_ids = payload.get("target_ids", [])
        badge_id = payload.get("badge_id", "")

        valid, err = validate_announcement_input(title, message, target_type, target_ids)
        if not valid:
            self.set_flash(f"Announcement error: {err}", "error")
            return

        ann_id = f"ann_{len(store.get_all_announcements()) + 1}"
        ann = Announcement(
            id=ann_id,
            title=title,
            message=message,
            author_id=self.current_user.id,
            author_name=self.current_user.name,
            target_type=target_type,
            target_cosmonaut_ids=target_ids if target_type == "selected" else [c.id for c in store.get_all_cosmonauts()],
            badge_id=badge_id
        )
        store.save_announcement(ann)

        # Notify recipients
        recipients = target_ids if target_type == "selected" else [c.id for c in store.get_all_cosmonauts()]
        for cid in recipients:
            store.add_notification(
                recipient_id=cid,
                title="New Academy Announcement",
                message=f"{title}: {message[:60]}...",
                link_section="c_announcements"
            )

        store.add_activity(
            event_type="announcement_published",
            actor_id=self.current_user.id,
            actor_name=self.current_user.name,
            cosmonaut_id="",
            badge_id=badge_id,
            summary=f"Announcement Broadcasted: '{title}'",
            details=f"Target: {'All 6 Cosmonauts' if target_type == 'all' else len(target_ids)}"
        )

        self.active_modal = None
        self.set_flash("Announcement broadcasted successfully.", "success")

    def _save_badge_allotment_edit(self, badge: Badge, payload: Dict[str, Any]):
        """
        The Edit option of an EXISTING badge: only (a) which cosmonauts are on the badge and WHICH REVIEWER each one is
        mapped to, and (b) the milestone timeline can change. Everything else on the badge (code, title, description,
        project brief, band, taxonomy, workflow state, publication, reviewer, pass mark) is preserved - values for those in
        the payload are ignored, so the read-only UI is not the only thing protecting them.

        Reviewer rules (server-enforced): a reviewer can only be one who is ALREADY mapped to this badge; a cosmonaut being
        newly added must match the badge's band; each cosmonaut has at most one reviewer. Reassignments are written to the
        band mappings, each cosmonaut's timeline (reviewer + review window), and the reviewer's accepted request, so the
        reviewer's own portal, the Mapping page and the Timeline view all agree.
        """
        import datetime as _dt

        all_users = {c.id: c for c in store.get_all_cosmonauts()}
        wanted: List[str] = []
        for cid in payload.get("assigned_cosmonaut_ids") or []:
            if cid in all_users and cid not in wanted:
                wanted.append(cid)
        if not wanted:
            self.set_flash("Assign at least one cosmonaut to this badge.", "warning")
            return

        old_ids = list(getattr(badge, "assigned_cosmonaut_ids", []) or [])
        removed = [cid for cid in old_ids if cid not in wanted]
        added = [cid for cid in wanted if cid not in old_ids]

        # new people must match the badge's criteria (its band)
        b_band = getattr(badge, "target_band", "") or ""
        mismatch = [cid for cid in added if b_band and getattr(all_users[cid], "band", "") != b_band]
        if mismatch:
            names = ", ".join(all_users[cid].name for cid in mismatch)
            self.set_flash(f"{names} {'is' if len(mismatch) == 1 else 'are'} not in Band {b_band}, so can't be added to {badge.code}.", "error")
            return

        # a cosmonaut who already started this badge cannot be taken off it
        blocked = [cid for cid in removed if store.get_submissions_for_cosmonaut(cid, badge_id=badge.id)]
        if blocked:
            names = ", ".join((store.get_user_by_id(cid).name if store.get_user_by_id(cid) else cid) for cid in blocked)
            self.set_flash(f"Cannot remove {names}: they already have work submitted for {badge.code}.", "error")
            return

        # ---- reviewers: who is mapped to this badge now, and who should each cosmonaut belong to
        cosmo_lookup = dict(getattr(store, "users", None) or {})
        cosmo_lookup.update(all_users)
        matched = _extract_badge_mapping_details(badge, cosmo_lookup, store.get_band_mappings())[4]
        mapping_owner: Dict[int, str] = {}
        current_owner: Dict[str, str] = {}
        for idx, m in enumerate(matched):
            revs = m.get("reviewers") or []
            if not revs:
                continue
            mapping_owner[idx] = revs[0]
            for cid in m.get("cosmonauts") or []:
                current_owner.setdefault(cid, revs[0])
        present_reviewers = set(mapping_owner.values())

        requested = payload.get("reviewer_assignments")
        assign: Dict[str, str] = {}
        for cid in wanted:
            rid = (requested.get(cid) if isinstance(requested, dict) and cid in requested else current_owner.get(cid, "")) or ""
            if rid and rid not in present_reviewers:
                self.set_flash("A cosmonaut can only be assigned to a reviewer who is already mapped to this badge.", "error")
                return
            assign[cid] = rid

        # ---- timeline dates
        old_tl = dict(badge.default_timeline or {})
        fields = ("assignment_date", "learning_start_date", "learning_end_date", "project_start_date",
                  "project_end_date", "submission_deadline", "review_date", "expected_award_date")
        new_vals = {k: (payload.get(k) or old_tl.get(k) or "") for k in fields}
        for k, v in new_vals.items():
            if not v:
                continue
            try:
                _dt.date.fromisoformat(str(v)[:10])
            except ValueError:
                self.set_flash(f"'{v}' is not a valid date.", "error")
                return
        for a_key, b_key, label in (("learning_start_date", "learning_end_date", "Learning"),
                                    ("project_start_date", "project_end_date", "Project")):
            if new_vals[a_key] and new_vals[b_key] and str(new_vals[b_key])[:10] < str(new_vals[a_key])[:10]:
                self.set_flash(f"{label} time cannot end before it starts.", "error")
                return

        # ---- everything validated: write
        merged_tl = {**old_tl, **{k: v for k, v in new_vals.items() if v}}
        merged_tl["publication_date"] = merged_tl.get("publication_date") or merged_tl.get("assignment_date", "")
        badge.default_timeline = merged_tl
        badge.assigned_cosmonaut_ids = wanted
        store.save_badge(badge)

        # band mappings: each mapping keeps exactly the cosmonauts now assigned to its reviewer (existing order first)
        placed: set = set()
        window_of: Dict[str, List[str]] = {}
        for idx, m in enumerate(matched):
            owner = mapping_owner.get(idx)
            if not owner:
                continue
            existing = [c for c in (m.get("cosmonauts") or []) if c in wanted]
            candidates = existing + [c for c in wanted if c not in existing]
            new_list = [c for c in candidates if assign.get(c) == owner and c not in placed]
            placed.update(new_list)
            window_of.setdefault(owner, list(m.get("review_dates") or []))
            if new_list != (m.get("cosmonauts") or []):
                m["cosmonauts"] = new_list
                store.save_band_mapping(m)

        live = bool(getattr(badge, "is_published", False))
        for cid in wanted:
            rid = assign[cid]
            window_json = json.dumps(window_of.get(rid, [])) if rid else "[]"
            tl = store.get_timeline(badge.id, cid)
            if not tl:
                tl = BadgeTimeline(
                    badge_id=badge.id, cosmonaut_id=cid, reviewer_id=rid,
                    assignment_date=merged_tl.get("assignment_date", ""), publication_date=merged_tl.get("publication_date", ""),
                    learning_start_date=merged_tl.get("learning_start_date", ""), learning_end_date=merged_tl.get("learning_end_date", ""),
                    project_start_date=merged_tl.get("project_start_date", ""), project_end_date=merged_tl.get("project_end_date", ""),
                    submission_deadline=merged_tl.get("submission_deadline", ""), review_date=merged_tl.get("review_date", ""),
                    expected_award_date=merged_tl.get("expected_award_date", ""),
                    status="active" if live else "locked", review_window_json=window_json,
                )
            else:
                tl.assignment_date = merged_tl.get("assignment_date", tl.assignment_date)
                tl.learning_start_date = merged_tl.get("learning_start_date", tl.learning_start_date)
                tl.learning_end_date = merged_tl.get("learning_end_date", tl.learning_end_date)
                tl.project_start_date = merged_tl.get("project_start_date", tl.project_start_date)
                tl.project_end_date = merged_tl.get("project_end_date", tl.project_end_date)
                tl.submission_deadline = merged_tl.get("submission_deadline", tl.submission_deadline)
                tl.review_date = merged_tl.get("review_date", tl.review_date)
                tl.expected_award_date = merged_tl.get("expected_award_date", tl.expected_award_date)
                tl.reviewer_id = rid
                tl.review_window_json = window_json
            store.save_timeline(tl)

        for cid in removed:      # (the band mappings above already dropped them - only wanted cosmonauts are kept)
            store.delete_timeline(badge.id, cid)

        # the reviewer's accepted / pending request lists the cadets they will review
        for req in store.get_mapping_requests():
            ref_match = req.get("badge_id") == badge.id or req.get("badge") in (badge.title, badge.code)
            if ref_match and req.get("status") in ("accepted", "pending") and req.get("reviewer_id") in present_reviewers:
                mine = [c for c in wanted if assign.get(c) == req["reviewer_id"]]
                if mine != (req.get("cosmonaut_ids") or []):
                    req["cosmonaut_ids"] = mine
                    store.add_mapping_request(req)

        # tell a reviewer when somebody is newly handed to them
        moved_in = [(cid, rid) for cid, rid in assign.items() if rid and rid != current_owner.get(cid, "")]
        for cid, rid in moved_in:
            store.add_notification(
                recipient_id=rid,
                title=f"Cadet added to your review group: {badge.code}",
                message=f"{all_users[cid].name} was assigned to you for '{badge.title}' (Band {b_band}).",
                link_section="c_requests", event_type="mapping_request", related_badge_id=badge.id,
            )

        store.add_activity(
            event_type="badge_updated",
            actor_id=self.current_user.id,
            actor_name=self.current_user.name,
            cosmonaut_id="",
            badge_id=badge.id,
            summary=f"Allotment & timeline updated for {badge.code}: {badge.title}",
            details=f"{len(wanted)} cosmonauts (+{len(added)} added, -{len(removed)} removed, {len(moved_in)} assigned to a reviewer).",
        )
        self.active_modal = None
        self.set_flash(
            f"{badge.code} updated: {len(wanted)} cosmonauts (+{len(added)}, -{len(removed)}), "
            f"{len(moved_in)} assigned to a reviewer, timeline saved.", "success")

    def execute_save_badge(self, payload: Dict[str, Any]):
        badge_id = payload.get("badge_id", "")
        existing_for_edit = store.get_badge(badge_id) if badge_id else None
        if existing_for_edit:
            self._save_badge_allotment_edit(existing_for_edit, payload)
            return
        code = payload.get("code", "").strip()
        title = payload.get("title", "").strip()
        desc = payload.get("description", "").strip()
        reqs = payload.get("project_requirements", "").strip()
        prereqs = payload.get("prerequisites", [])
        assigned_ids = payload.get("assigned_cosmonaut_ids", [])

        # Timeline milestones decided by Guardian
        alloc_date = payload.get("assignment_date") or current_iso_timestamp()[:10]
        learn_start = payload.get("learning_start_date") or alloc_date
        learn_end = payload.get("learning_end_date") or "2026-12-01"
        proj_start = payload.get("project_start_date") or "2026-12-02"
        proj_end = payload.get("project_end_date") or "2026-12-14"
        sub_deadline = payload.get("submission_deadline") or "2026-12-15"
        review_date = payload.get("review_date") or "2026-12-18"
        award_date = payload.get("expected_award_date") or "2026-12-20"

        valid, err = validate_badge_input({"title": title, "code": code})
        if not valid:
            self.set_flash(f"Badge validation error: {err}", "error")
            return

        write_cid = store.get_active_cycle_id()
        is_new = not badge_id
        if is_new:
            badge_id = f"badge_{code.lower().replace('-', '_')}"
            existing_other = store.get_badge(badge_id)
            if existing_other and (getattr(existing_other, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) != write_cid:
                badge_id = f"{write_cid}__{badge_id}"

        existing_badge = None if is_new else store.get_badge(badge_id)
        badge_cycle_id = getattr(existing_badge, "cycle_id", "") if existing_badge else write_cid
        default_alloc = False if is_new else getattr(existing_badge, "is_allocated", True)

        all_cosmo_ids = [c.id for c in store.get_all_cosmonauts()]
        # Cohort requirement: When Guardian creates/updates a milestone, update for ALL Cosmonauts unless specific assignees provided
        if not assigned_ids:
            assigned_ids = all_cosmo_ids

        default_tl = {
            "assignment_date": alloc_date,
            "publication_date": alloc_date,
            "learning_start_date": learn_start,
            "learning_end_date": learn_end,
            "project_start_date": proj_start,
            "project_end_date": proj_end,
            "submission_deadline": sub_deadline,
            "review_date": review_date,
            "expected_award_date": award_date
        }

        badge = Badge(
            id=badge_id,
            code=code,
            title=title,
            category=payload.get("category", "Foundations"),
            description=desc,
            learning_outcomes=payload.get("learning_outcomes", ["Master core milestone concepts"]),
            learning_topics=payload.get("learning_topics", ["Foundations", "Architecture"]),
            prerequisites=prereqs,
            project_requirements=reqs,
            is_published=True,
            assigned_cosmonaut_ids=assigned_ids,
            default_timeline=default_tl,
            is_allocated=payload.get("is_allocated", default_alloc),
            cycle_id=badge_cycle_id
        )
        store.save_badge(badge)

        # Ensure timelines exist and reflect Guardian's decisions for all assigned Cosmonauts
        for cid in assigned_ids:
            tl = store.get_timeline(badge.id, cid)
            if not tl:
                new_tl = BadgeTimeline(
                    badge_id=badge.id,
                    cosmonaut_id=cid,
                    assignment_date=alloc_date,
                    publication_date=alloc_date,
                    learning_start_date=learn_start,
                    learning_end_date=learn_end,
                    project_start_date=proj_start,
                    project_end_date=proj_end,
                    submission_deadline=sub_deadline,
                    review_date=review_date,
                    expected_award_date=award_date,
                    status="locked" if is_new else "active"
                )
                store.save_timeline(new_tl)
            else:
                tl.assignment_date = alloc_date
                tl.learning_start_date = learn_start
                tl.learning_end_date = learn_end
                tl.project_start_date = proj_start
                tl.project_end_date = proj_end
                tl.submission_deadline = sub_deadline
                tl.review_date = review_date
                tl.expected_award_date = award_date
                store.save_timeline(tl)

            if is_new:
                creator_name = self.current_user.name if self.current_user else "Arjun Mehta"
                store.add_notification(
                    recipient_id=cid,
                    title=f"New Milestone Available: {code}",
                    message=f"{creator_name} created new milestone {code}: {title}. The previous locked milestone is now unlocked!",
                    link_section="c_roadmap"
                )

        store.add_activity(
            event_type="badge_created" if is_new else "badge_updated",
            actor_id=self.current_user.id,
            actor_name=self.current_user.name,
            cosmonaut_id="",
            badge_id=badge.id,
            summary=f"Badge {badge.code}: {badge.title} {'Created' if is_new else 'Updated'}",
            details=f"Assigned to {len(assigned_ids)} Cosmonauts."
        )

        self.active_modal = None
        self.set_flash(f"Badge {badge.code} saved successfully.", "success")

    def execute_save_material(self, payload: Dict[str, Any]):
        badge_id = payload.get("badge_id", "")
        title = payload.get("title", "").strip()
        desc = payload.get("description", "").strip()
        mat_type = payload.get("material_type", "doc")
        url_or_data = payload.get("url_or_data", "").strip()
        topic = payload.get("topic", "General")

        if not title or not url_or_data:
            self.set_flash("Title and Resource URL/Data are required.", "error")
            return

        mat_id = f"mat_{len(store.get_materials()) + 1}"
        mat = LearningMaterial(
            id=mat_id,
            badge_id=badge_id,
            topic=topic,
            title=title,
            description=desc,
            material_type=mat_type,
            url_or_data=url_or_data,
            upload_date=current_iso_timestamp()
        )
        store.save_material(mat)

        badge = store.get_badge(badge_id)
        b_name = badge.code if badge else badge_id

        store.add_activity(
            event_type="material_published",
            actor_id=self.current_user.id if self.current_user else "guardian_1",
            actor_name=self.current_user.name if self.current_user else "Guardian",
            cosmonaut_id="",
            badge_id=badge_id,
            summary=f"Learning Material Published for {b_name}",
            details=f"Title: {title} ({mat_type.upper()})"
        )

        self.active_modal = None
        self.set_flash(f"Resource '{title}' published for {b_name}.", "success")

    def execute_save_bulk_materials(self, payload: Any):
        if isinstance(payload, str) and payload.strip():
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}

        # Fallback to single save if legacy fields are passed
        if ("url_or_data" in payload or "title" in payload) and "pdfs" not in payload and "youtube_links" not in payload:
            return self.execute_save_material(payload)

        badge_id = payload.get("badge_id", "")
        topic = payload.get("topic", "General Module").strip() or "General Module"
        desc = payload.get("description", "").strip() or "Milestone learning resource"
        pdfs = payload.get("pdfs", [])
        youtube_links = payload.get("youtube_links", [])

        if not badge_id:
            all_b = store.get_all_badges()
            if all_b:
                badge_id = all_b[0].id

        badge = store.get_badge(badge_id)
        b_name = badge.code if badge else badge_id
        saved_count = 0
        import time

        # Process uploaded PDFs
        for idx, pdf in enumerate(pdfs):
            name = pdf.get("name", f"Document_{idx+1}")
            data_url = pdf.get("dataUrl", "")
            if not data_url:
                continue
            mat_id = f"mat_pdf_{int(time.time()*1000)}_{idx+1}"
            title = name.replace(".pdf", "").replace("_", " ").title()
            mat = LearningMaterial(
                id=mat_id,
                badge_id=badge_id,
                topic=topic,
                title=title,
                description=desc,
                material_type="pdf",
                url_or_data=data_url,
                upload_date=current_iso_timestamp()
            )
            store.save_material(mat)
            saved_count += 1

        # Process YouTube links
        for idx, yt in enumerate(youtube_links):
            url = yt.get("url", "").strip()
            title = yt.get("title", "").strip()
            if not url:
                continue
            if not title:
                title = f"{b_name}: Video Lecture {idx+1}"
            mat_id = f"mat_yt_{int(time.time()*1000)}_{idx+1}"
            mat = LearningMaterial(
                id=mat_id,
                badge_id=badge_id,
                topic=topic,
                title=title,
                description=desc,
                material_type="youtube",
                url_or_data=url,
                upload_date=current_iso_timestamp()
            )
            store.save_material(mat)
            saved_count += 1

        if saved_count > 0:
            store.add_activity(
                event_type="material_published",
                actor_id=self.current_user.id if self.current_user else "guardian_1",
                actor_name=self.current_user.name if self.current_user else "Guardian",
                cosmonaut_id="",
                badge_id=badge_id,
                summary=f"Published {saved_count} Learning Materials for {b_name}",
                details=f"Topic: {topic} &bull; {len(pdfs)} PDF(s), {len(youtube_links)} Video(s)"
            )
            self.set_flash(f"Successfully published {saved_count} learning resources for {b_name}.", "success")
        else:
            self.set_flash("Please provide at least one PDF file or YouTube link.", "error")

        self.active_modal = None

    def execute_update_material(self, payload: Any):
        if isinstance(payload, str) and payload.strip():
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}

        mat_id = payload.get("material_id", "")
        mat = store.get_material(mat_id)
        if not mat:
            self.set_flash("Material record not found.", "error")
            return

        mat.badge_id = payload.get("badge_id", mat.badge_id)
        mat.title = payload.get("title", mat.title).strip() or mat.title
        mat.topic = payload.get("topic", mat.topic).strip() or mat.topic
        mat.description = payload.get("description", mat.description).strip()
        mat.material_type = payload.get("material_type", mat.material_type)
        new_url = payload.get("url_or_data", "").strip()
        if new_url:
            mat.url_or_data = new_url

        store.save_material(mat)
        self.active_modal = None
        self.set_flash(f"Updated learning material '{mat.title}'.", "success")

    # ==========================================================================
    # MODAL DIALOG RENDERER
    # ==========================================================================

    def render_active_modal(self) -> str:
        if not self.active_modal:
            return ""

        title = "StarApp Dialog"
        body = ""

        if self.active_modal == "notifications":
            title = "Notifications & Alerts"
            notifs = store.get_notifications(self.current_user.id) if self.current_user else []
            items = []
            for n in notifs:
                items.append(f"""
                <div style="padding:12px; border-radius:var(--radius-sm); background:rgba(234,244,255,0.7); margin-bottom:8px; border-left:4px solid var(--deep-frozen-midnight);">
                    <div style="font-weight:700; color:var(--frost-navy); font-size:0.8125rem;">{escape(n.title)}</div>
                    <div style="font-size:0.78125rem; color:var(--frost-navy); margin-top:2px;">{escape(n.message)}</div>
                    <div style="font-size:0.6875rem; color:var(--frost-navy-50); margin-top:4px;">{escape(ist_plain(n.created_at))}</div>
                </div>
                """)
            body = "".join(items) if items else "<p style='padding:20px; text-align:center; color:var(--frost-navy-50);'>No notifications.</p>"

        elif self.active_modal == "badge_detail":
            badge_id = self.modal_payload.get("badge_id")
            badge = store.get_badge(badge_id)
            if badge and self.current_user:
                title = f"{badge.code}: {badge.title} — Lifecycle Timeline"
                is_guardian = (self.current_user.role == "guardian")
                cosmo_id = (self.selected_guardian_cosmo_id if self.selected_guardian_cosmo_id != "all" else "cosmo_1") if is_guardian else self.current_user.id
                tl = store.get_timeline(badge.id, cosmo_id)
                mats = store.get_materials(badge.id)
                approved_ids = {a.badge_id for a in store.get_assessments_for_cosmonaut(cosmo_id) if a.decision == "approve"}
                is_unlocked_for_cosmo = getattr(badge, "is_allocated", False) and badge.is_published and cosmo_id in badge.assigned_cosmonaut_ids
                state = "completed" if badge.id in approved_ids else ("active" if is_unlocked_for_cosmo else "locked")
                if not is_guardian and state == "locked":
                    title = "Milestone locked"
                body = render_badge_detail_modal_content(badge, cosmo_id, tl, mats, state, is_guardian=is_guardian)

        elif self.active_modal == "marksheet_modal":
            asm_id = self.modal_payload.get("marksheet_id")
            marksheet = store.get_assessment(asm_id)
            if not marksheet and asm_id:
                # 1. Check actual cosmonaut benchmark assessments (Aarav Sharma)
                if asm_id in ("asm_c1_ing_2", "asm_c1_sql_201") or "cosmo_1" in asm_id:
                    is_sql = "sql" in asm_id.lower()
                    b_id = "badge_sql_201" if is_sql else "badge_ing_104"
                    marksheet = AssessmentMarksheet(
                        id=asm_id,
                        submission_id=f"sub_cosmo_1_{b_id}",
                        attempt_number=1 if is_sql else 2,
                        badge_id=b_id,
                        cosmonaut_id="cosmo_1",
                        reviewer_id="guardian_1",
                        reviewer_name="Arjun Mehta",
                        reviewed_at="2026-11-08",
                        decision="approve",
                        business_understanding=9.5,
                        architecture_report=9.5 if is_sql else 9.0,
                        technical_knowledge=9.5,
                        presentation=9.5,
                        qa=9.0,
                        strength_areas="High rubric excellence, distributed system architecture diagrams, and comprehensive automated test fixtures.",
                        improvement_areas="Explore partition rebalance cost modeling under unexpected consumer group crash scenarios.",
                        overall_feedback="Audited milestone evaluation passed with Honors Distinction."
                    )
                else:
                    # 2. Check demo cosmonauts for benchmark assessment marksheet preview
                    from starapp.dashboard_demo import get_dashboard_demo_cosmonauts
                    for demo in get_dashboard_demo_cosmonauts():
                        for a in demo.get("assessments", []):
                            candidate_id = a.get("id") or f"asm_{demo['id']}_{a.get('badge_code','').lower()}"
                            if candidate_id == asm_id:
                                b_id = a.get("badge_id", "")
                                marksheet = AssessmentMarksheet(
                                    id=asm_id,
                                    submission_id=f"sub_{demo['id']}_{a.get('badge_code','').lower()}",
                                    attempt_number=a.get("attempt_number", 1),
                                    badge_id=b_id,
                                    cosmonaut_id=demo["id"],
                                    reviewer_id="guardian_1",
                                    reviewer_name="Arjun Mehta",
                                    reviewed_at=a.get("reviewed_at", "2026-11-01"),
                                    decision=a.get("decision", "approve"),
                                    business_understanding=float(a.get("business_understanding", 9.0)),
                                    architecture_report=float(a.get("architecture_report", 9.0)),
                                    technical_knowledge=float(a.get("technical_knowledge", 9.0)),
                                    presentation=float(a.get("presentation", 9.0)),
                                    qa=float(a.get("qa", 9.0)),
                                    strength_areas="Strong technical implementation, reliable architectural diagrams and clean code modularity.",
                                    improvement_areas="Continue refining automated test edge-cases and distributed failure handling.",
                                    overall_feedback=f"Audited benchmark assessment for {demo['name']}."
                                )
                                break
                        if marksheet:
                            break

            if marksheet:
                b_code = marksheet.badge_id.replace("badge_", "").upper()
                title = f"Evaluated Marksheet — {b_code}"
                badge = store.get_badge(marksheet.badge_id)
                all_atts = [a for a in store.get_all_assessments() if a.badge_id == marksheet.badge_id and a.cosmonaut_id == marksheet.cosmonaut_id]
                if not all_atts:
                    all_atts = [marksheet]
                body = render_standard_marksheet(marksheet, badge, all_atts)

        elif self.active_modal == "material_preview":
            mat_id = self.modal_payload.get("material_id")
            mat = store.get_material(mat_id)
            if mat:
                badge = store.get_badge(mat.badge_id)
                badge_label = f"{badge.code}: {badge.title}" if badge else mat.badge_id
                title = f"{mat.title} ({badge_label})"
                if mat.material_type == "youtube":
                    # Convert watch/share URL to clean embed URL
                    embed_url = mat.url_or_data
                    if "watch?v=" in embed_url:
                        vid = embed_url.split("watch?v=")[1].split("&")[0]
                        embed_url = f"https://www.youtube.com/embed/{vid}?autoplay=1&rel=0"
                    elif "youtu.be/" in embed_url:
                        vid = embed_url.split("youtu.be/")[1].split("?")[0]
                        embed_url = f"https://www.youtube.com/embed/{vid}?autoplay=1&rel=0"
                    elif "/embed/" in embed_url:
                        if "?" not in embed_url:
                            embed_url = f"{embed_url}?autoplay=1&rel=0"

                    body = f"""
                    <div style="margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; background:rgba(23,52,92,0.06); padding:8px 14px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-50);">
                        <span style="font-size:0.75rem; font-weight:800; color:var(--deep-frozen-midnight);">{escape(badge_label)}</span>
                        <span style="font-size:0.71875rem; font-weight:700; color:var(--frost-navy-50);">Topic: {escape(mat.topic)}</span>
                    </div>
                    <div class="media-embed-container" style="box-shadow:0 8px 30px rgba(7,22,41,0.25); border-radius:var(--radius-md); overflow:hidden;">
                        <iframe src="{escape(embed_url)}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen style="border:0;"></iframe>
                    </div>
                    <div style="margin-top:14px; padding:12px 16px; background:#FFFFFF; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                        <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">Lecture Overview & Study Objectives:</div>
                        <p style="font-size:0.84375rem; line-height:1.55; color:var(--frost-navy); margin:0;">{escape(mat.description)}</p>
                    </div>
                    <div style="display:flex; justify-content:flex-end; margin-top:16px;">
                        <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Close Video Player</button>
                    </div>
                    """
                elif mat.material_type == "pdf":
                    raw_pdf_url = mat.url_or_data.replace(' ', '%20') if (mat.url_or_data and not mat.url_or_data.startswith('http') and not mat.url_or_data.startswith('data:')) else (mat.url_or_data or 'data/Chemistry%20Syllabus.pdf')
                    clean_pdf_url = f"{raw_pdf_url}#toolbar=1&navpanes=0&pagemode=none&view=FitH"
                    download_url = raw_pdf_url
                    body = f"""
                    <div style="margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; background:rgba(23,52,92,0.06); padding:10px 16px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-50); flex-wrap:wrap; gap:8px;">
                        <div>
                            <span style="font-size:0.78125rem; font-weight:800; color:var(--deep-frozen-midnight);">{escape(badge_label)}</span>
                            <span style="font-size:0.71875rem; font-weight:700; color:var(--frost-navy-50); margin-left:8px;">Topic: {escape(mat.topic)}</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <a href="{escape(raw_pdf_url)}" target="_blank" class="btn-secondary btn-sm" style="font-size:0.71875rem; font-weight:700; text-decoration:none; display:inline-flex; align-items:center; gap:5px; padding:4px 12px;">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                                Open in Full Tab
                            </a>
                            <a href="{escape(download_url)}" download="{escape(mat.title)}.pdf" class="btn-secondary btn-sm" style="font-size:0.71875rem; font-weight:700; text-decoration:none; display:inline-flex; align-items:center; gap:5px; padding:4px 12px;">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                Download PDF
                            </a>
                        </div>
                    </div>
                    <div style="background:#FFFFFF; border-radius:var(--radius-md); overflow:hidden; border:1.5px solid var(--icy-steel-50); box-shadow:0 8px 32px rgba(7,22,41,0.12); margin-bottom:12px;">
                        <object data="{escape(clean_pdf_url)}" type="application/pdf" style="width:100%; height:72vh; min-height:600px; border:none; display:block;">
                            <iframe class="pdf-preview-box" src="{escape(clean_pdf_url)}" style="width:100%; height:72vh; min-height:600px; border:none; display:block;" title="{escape(mat.title)}"></iframe>
                        </object>
                    </div>
                    <div style="padding:12px 16px; background:#FFFFFF; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                        <div style="flex:1; min-width:240px;">
                            <div style="font-size:0.6875rem; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:2px;">Document Syllabus & Engineering Context:</div>
                            <p style="font-size:0.8125rem; line-height:1.5; color:var(--frost-navy); margin:0;">{escape(mat.description)}</p>
                        </div>
                        <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Close Document Reader</button>
                    </div>
                    """
                else:
                    body = f"""
                    <pre style="background:var(--frost-navy); color:var(--snow-white); padding:16px; border-radius:var(--radius-md); max-height:400px; overflow:auto;"><code>{escape(mat.url_or_data)}</code></pre>
                    <p style="font-size:0.84375rem; margin-top:10px; color:var(--frost-navy);">{escape(mat.description)}</p>
                    <div style="display:flex; justify-content:flex-end; margin-top:16px;">
                        <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Close Viewer</button>
                    </div>
                    """

        elif self.active_modal == "review_submission":
            sub_id = self.modal_payload.get("submission_id")
            sub = store.get_submission(sub_id)
            if sub:
                badge = store.get_badge(sub.badge_id)
                cosmo = store.get_user_by_id(sub.cosmonaut_id)
                title = f"Project Assessment: {badge.code}"
                existing_asm = store.get_assessment_for_submission(sub.id)
                prev_asms = [a for a in store.get_assessments_for_cosmonaut(sub.cosmonaut_id, sub.badge_id) if a.attempt_number < sub.attempt_number]
                body = render_assessment_modal_content(sub, badge, cosmo, existing_asm, prev_asms)

        elif self.active_modal == "decide_extension":
            if isinstance(self.modal_payload, str) and self.modal_payload.strip():
                try:
                    self.modal_payload = json.loads(self.modal_payload)
                except Exception:
                    pass
            ext_id = self.modal_payload.get("extension_id") if isinstance(self.modal_payload, dict) else ""
            decision = self.modal_payload.get("decision", "approved") if isinstance(self.modal_payload, dict) else "approved"
            ext = store.get_extension(ext_id)
            badge = store.get_badge(ext.badge_id) if ext else None
            badge_label = f"{badge.code}: {badge.title}" if badge else (ext.badge_id if ext else "Milestone")
            cosmo = store.get_user_by_id(ext.cosmonaut_id) if ext else None
            cosmo_name = cosmo.name if cosmo else (ext.cosmonaut_id if ext else "Cosmonaut")
            title = f"{decision.title()} Extension: {badge.code if badge else 'Request'}"
            body = f"""
            <form onsubmit="event.preventDefault(); const n=document.getElementById('ext-decision-note').value; window.StarAppBridge.dispatchAction('submit_extension_decision', JSON.stringify({{extension_id:'{ext_id}', decision:'{decision}', response_note:n}}));">
                <div style="font-size:0.875rem; margin-bottom:14px; color:var(--frost-navy);">
                    Are you sure you want to <strong style="color:var(--deep-frozen-midnight);">{decision.upper()}</strong> the extension request from <strong>{escape(cosmo_name)}</strong> for <strong>{escape(badge_label)}</strong>?
                </div>
                <div style="background:rgba(234,244,255,0.7); padding:12px 16px; border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm); margin-bottom:16px; font-size:0.8125rem; line-height:1.5;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                        <span><strong>Original Cutoff:</strong> <span style="font-family:var(--font-family-mono);">{escape(ext.current_deadline if ext else 'N/A')}</span></span>
                        <span><strong>Proposed Cutoff:</strong> <span style="font-family:var(--font-family-mono); font-weight:800; color:var(--deep-frozen-midnight);">{escape(ext.proposed_deadline if ext else 'N/A')}</span></span>
                    </div>
                    <div><strong>Cosmonaut Rationale:</strong> {escape(ext.reason if ext else 'N/A')}</div>
                </div>
                <div class="form-group">
                    <label class="form-label" style="font-weight:700;">Mentor Feedback / Decision Note (Optional)</label>
                    <textarea id="ext-decision-note" class="form-textarea" style="min-height:85px; font-size:0.8125rem;" placeholder="Add guidance, expectations, or schedule details for the cosmonaut..."></textarea>
                </div>
                <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:18px;">
                    <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Cancel</button>
                    <button type="submit" class="btn-metal" style="font-weight:700;">Confirm {decision.title()} &rarr;</button>
                </div>
            </form>
            """

        elif self.active_modal == "create_announcement":
            title = "Broadcast Academy Announcement"
            cosmo_checks = []
            for c in store.get_all_cosmonauts():
                cosmo_checks.append(f"""
                <label style="display:flex; align-items:center; gap:6px; font-size:0.78125rem; margin-right:12px;">
                    <input type="checkbox" name="ann-target-cosmo" value="{c.id}">
                    <span>{escape(c.name)}</span>
                </label>
                """)

            badge_opts = ['<option value="">None (Academy-Wide)</option>']
            for b in store.get_all_badges():
                badge_opts.append(f'<option value="{b.id}">{escape(b.code)}: {escape(b.title)}</option>')

            body = f"""
            <form onsubmit="event.preventDefault(); const t=document.getElementById('ann-title').value; const m=document.getElementById('ann-msg').value; const tt=document.getElementById('ann-target-type').value; const b=document.getElementById('ann-badge').value; const boxes=document.querySelectorAll('input[name=ann-target-cosmo]:checked'); const sel=[]; boxes.forEach(x=>sel.push(x.value)); window.StarAppBridge.dispatchAction('broadcast_announcement', JSON.stringify({{title:t, message:m, target_type:tt, target_ids:sel, badge_id:b}}));">
                <div class="form-group">
                    <label class="form-label">Announcement Title</label>
                    <input type="text" id="ann-title" class="form-control" placeholder="e.g. Workshop Reschedule" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Message Body</label>
                    <textarea id="ann-msg" class="form-textarea" placeholder="Enter broadcast details..." required></textarea>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                    <div class="form-group">
                        <label class="form-label">Target Audience</label>
                        <select id="ann-target-type" class="form-select" onchange="const c=document.getElementById('ann-cosmo-select-box'); if(this.value=='selected'){{c.style.display='block';}}else{{c.style.display='none';}}">
                            <option value="all">All 6 Cosmonauts</option>
                            <option value="selected">Selected Cosmonauts Only</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Associated Milestone (Optional)</label>
                        <select id="ann-badge" class="form-select">
                            {"".join(badge_opts)}
                        </select>
                    </div>
                </div>

                <div id="ann-cosmo-select-box" style="display:none; margin-bottom:16px; background:rgba(234,244,255,0.4); padding:10px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                    <div style="font-size:0.75rem; font-weight:700; color:var(--deep-frozen-midnight); margin-bottom:6px;">Select Individual Recipients:</div>
                    <div style="display:flex; flex-wrap:wrap; gap:8px;">
                        {"".join(cosmo_checks)}
                    </div>
                </div>

                <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
                    <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Cancel</button>
                    <button type="submit" class="btn-metal">Broadcast Announcement</button>
                </div>
            </form>
            """

        elif self.active_modal == "locked_milestone_notice":
            idx = self.modal_payload.get("index", "5")
            lock_ic_16 = get_icon("lock", 16, "margin-right:6px;")
            lock_ic_32 = get_icon("lock", 32)
            title = f"{lock_ic_16} Milestone {idx} is Locked & Classified"
            body = f"""
            <div style="text-align:center; padding:10px 0;">
                <div style="display:inline-flex; align-items:center; justify-content:center; width:64px; height:64px; border-radius:50%; background:rgba(23,52,92,0.08); margin:0 auto 14px; color:var(--deep-frozen-midnight);">{lock_ic_32}</div>
                <h3 style="color:var(--frost-navy); font-weight:800; font-size:1.25rem; margin-bottom:8px;">Milestone {escape(str(idx))} Sealed</h3>
                <p style="font-size:0.84375rem; color:var(--frost-navy-75); line-height:1.6; max-width:440px; margin:0 auto 16px;">
                    This milestone curriculum and project parameters are managed by your Guardian, <strong>Arjun Mehta</strong>. Once your current sprint deliverables are reviewed and certified, Arjun Mehta will publish the timeline and unlock this milestone for your cohort.
                </p>
                <div style="background:rgba(234,244,255,0.6); padding:12px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); font-size:0.75rem; color:var(--frost-navy); margin-bottom:20px;">
                    <strong>Next Action:</strong> Complete and submit your active milestone (<strong>ING-104 Ingestion Foundations</strong>) to qualify for advancement.
                </div>
                <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Acknowledged</button>
            </div>
            """

        elif self.active_modal in ["create_badge", "edit_badge"]:
            is_edit = self.active_modal == "edit_badge"
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id) if is_edit else None

            title = "Allot & Set Milestone Timeline" if is_edit else "Create & Allot New Badge Milestone"
            code = badge.code if badge else ""
            b_title = badge.title if badge else ""
            desc = badge.description if badge else ""
            reqs = badge.project_requirements if badge else ""
            assigned = badge.assigned_cosmonaut_ids if badge else [c.id for c in store.get_all_cosmonauts()]

            dt = badge.default_timeline if badge else {}
            alloc_val = dt.get("assignment_date") or current_iso_timestamp()[:10]
            learn_start_val = dt.get("learning_start_date") or alloc_val
            learn_end_val = dt.get("learning_end_date") or "2026-12-01"
            proj_start_val = dt.get("project_start_date") or "2026-12-02"
            proj_end_val = dt.get("project_end_date") or "2026-12-14"
            sub_deadline_val = dt.get("submission_deadline") or "2026-12-15"
            review_date_val = dt.get("review_date") or "2026-12-18"
            award_date_val = dt.get("expected_award_date") or "2026-12-20"

            all_cosmonauts = store.get_all_cosmonauts()
            assign_html = render_badge_edit_assignees(badge, store, assigned)

            cal_ico = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'

            def _d(field_id: str, value: str, min_id: str = "", pair_id: str = "") -> str:
                # the real value lives in a hidden input (same id the submit handler reads, ISO format);
                # the visible control opens the glass calendar instead of the browser's native one
                extra = (f' data-gd-min="{min_id}"' if min_id else "") + (f' data-gd-pair="{pair_id}"' if pair_id else "")
                return (
                    f'<span class="gd-field"><input type="hidden" id="{field_id}" value="{escape(value)}">'
                    f'<button type="button" class="gd-btn" data-gd-input="{field_id}"{extra} onclick="window.StarAppBridge.openDatePicker(this)">'
                    f'<span class="gd-label">{escape(_fmt_nice_date(value))}</span>{cal_ico}</button></span>'
                )

            def _date_card(num: int, title_txt: str, inputs: str) -> str:
                return (
                    f'<div class="eb-date">'
                    f'<span class="eb-date-title"><b>{num}</b>{title_txt}</span>'
                    f'<span class="eb-date-inputs">{inputs}</span></div>'
                )

            dates_html = "".join([
                _date_card(1, "Allocated Date", _d("tl-alloc-date", alloc_val)),
                _date_card(2, "Learning Time", _d("tl-learn-start", learn_start_val, pair_id="tl-learn-end") + "<span>&rarr;</span>" + _d("tl-learn-end", learn_end_val, min_id="tl-learn-start")),
                _date_card(3, "Project Time", _d("tl-proj-start", proj_start_val, pair_id="tl-proj-end") + "<span>&rarr;</span>" + _d("tl-proj-end", proj_end_val, min_id="tl-proj-start")),
                _date_card(4, "Official Submission", _d("tl-sub-deadline", sub_deadline_val)),
                _date_card(5, "Review &amp; Defense", _d("tl-review-date", review_date_val)),
                _date_card(6, "Badge Earned (Target)", _d("tl-award-date", award_date_val)),
            ])

            if is_edit and badge:
                # Existing badge: no details card at all - only the cosmonauts and the timeline are edited here. The badge's own
                # content travels as hidden inputs (the server ignores it for an existing badge anyway).
                details_html = f"""
                    <div hidden>
                        <input type="hidden" id="badge-code" value="{escape(code)}">
                        <input type="hidden" id="badge-title" value="{escape(b_title)}">
                        <input type="hidden" id="badge-desc" value="{escape(desc)}">
                        <input type="hidden" id="badge-reqs" value="{escape(reqs)}">
                    </div>
                """
            else:
                details_html = f"""
                    <section class="eb-card eb-details">
                        <div class="eb-card-head"><h4 class="eb-card-title"><span class="eb-ico">{get_icon("award", 17)}</span>Badge Details</h4></div>
                        <div class="eb-row">
                            <div class="eb-field">
                                <label class="eb-label" for="badge-code">Badge Code</label>
                                <input type="text" id="badge-code" class="eb-input is-mono" value="{escape(code)}" placeholder="e.g. SQL-201" required>
                            </div>
                            <div class="eb-field">
                                <label class="eb-label" for="badge-title">Badge Title</label>
                                <input type="text" id="badge-title" class="eb-input is-strong" value="{escape(b_title)}" placeholder="e.g. Distributed Ingestion" required>
                            </div>
                        </div>
                        <div class="eb-field">
                            <label class="eb-label" for="badge-desc">Milestone Description</label>
                            <textarea id="badge-desc" class="eb-text" rows="3" required>{escape(desc)}</textarea>
                        </div>
                        <div class="eb-field eb-grow">
                            <label class="eb-label" for="badge-reqs">Project Deliverable Requirements</label>
                            <textarea id="badge-reqs" class="eb-text is-prompt" rows="9" required>{escape(reqs)}</textarea>
                        </div>
                    </section>
                """

            body = f"""
            <form class="eb-form" onsubmit="event.preventDefault(); const c=document.getElementById('badge-code').value; const t=document.getElementById('badge-title').value; const d=document.getElementById('badge-desc').value; const r=document.getElementById('badge-reqs').value; const al=document.getElementById('tl-alloc-date').value; const ls=document.getElementById('tl-learn-start').value; const le=document.getElementById('tl-learn-end').value; const ps=document.getElementById('tl-proj-start').value; const pe=document.getElementById('tl-proj-end').value; const sd=document.getElementById('tl-sub-deadline').value; const rd=document.getElementById('tl-review-date').value; const aw=document.getElementById('tl-award-date').value; const boxes=document.querySelectorAll('input[name=badge-assignee]:checked'); const sel=[]; boxes.forEach(x=>sel.push(x.value)); window.StarAppBridge.dispatchAction('save_badge_form', JSON.stringify({{badge_id:'{b_id}', code:c, title:t, description:d, project_requirements:r, assigned_cosmonaut_ids:sel, reviewer_assignments:window.StarAppBridge.collectReviewerAssignments(), assignment_date:al, learning_start_date:ls, learning_end_date:le, project_start_date:ps, project_end_date:pe, submission_deadline:sd, review_date:rd, expected_award_date:aw}}));">
                <div class="eb-grid{' is-edit' if (is_edit and badge) else ''}">
                    {details_html}

                    <section class="eb-card eb-assign">
                        <div class="eb-card-head">
                            <h4 class="eb-card-title"><span class="eb-ico">{get_icon("users", 17)}</span>Assigned Cosmonauts <span class="md-count"><span id="eb-count">{len(assigned)}</span>&nbsp;/&nbsp;{len(all_cosmonauts)}</span></h4>
                            <button type="button" class="eb-mini-btn is-danger" onclick="window.StarAppBridge.clearAssignees()">Remove all</button>
                        </div>
                        {assign_html}
                    </section>

                    <section class="eb-card eb-timeline">
                        <div class="eb-card-head">
                            <h4 class="eb-card-title"><span class="eb-ico">{get_icon("calendar", 17)}</span>Milestone Timeline</h4>
                            <span class="eb-sub">6 sequential gates</span>
                        </div>
                        <div class="eb-dates{' is-rows' if (is_edit and badge) else ''}">{dates_html}</div>
                    </section>
                </div>

                <div class="eb-footer">
                    <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Cancel</button>
                    <button type="submit" class="btn-metal">Save Allotment &amp; Timeline &rarr;</button>
                </div>
            </form>
            """

        elif self.active_modal == "add_material":
            title = "Upload Learning Materials (Multi-File & Video Links)"
            badge_opts = []
            for b in store.get_all_badges():
                badge_opts.append(f'<option value="{b.id}">{escape(b.code)}: {escape(b.title)}</option>')

            body = f"""
            <form onsubmit="event.preventDefault(); window.StarAppBridge.submitBulkMaterials();">
                <div class="form-group" style="margin-bottom:12px;">
                    <label class="form-label" style="font-size:0.75rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Target Milestone Badge *</label>
                    <select id="bulk-mat-badge" class="form-select" style="font-size:0.78125rem; font-weight:700;">
                        {"".join(badge_opts)}
                    </select>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                    <div class="form-group" style="margin:0;">
                        <label class="form-label" style="font-size:0.75rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Topic / Module Category *</label>
                        <input type="text" id="bulk-mat-topic" class="form-control" placeholder="e.g. Ingestion Foundations, Module 1" value="Module Specification" required>
                    </div>
                    <div class="form-group" style="margin:0;">
                        <label class="form-label" style="font-size:0.75rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Batch Description / Notes</label>
                        <input type="text" id="bulk-mat-desc" class="form-control" placeholder="e.g. Masterclass lectures and technical documentation.">
                    </div>
                </div>

                <!-- 1. PDF Uploads (Multiples Supported) -->
                <div style="margin-bottom:16px; padding:14px; background:rgba(234,244,255,0.6); border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel-50);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="font-size:0.78125rem; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px; display:flex; align-items:center; gap:6px;">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                            Upload PDF Documents (Multiple Files Supported)
                        </div>
                        <span style="font-size:0.6875rem; font-weight:700; color:var(--frost-navy-50);">Supports .pdf</span>
                    </div>

                    <div style="background:#FFFFFF; border:2px dashed var(--icy-steel); border-radius:var(--radius-xs); padding:16px; text-align:center; cursor:pointer;" onclick="document.getElementById('bulk-pdf-input').click()">
                        <input type="file" id="bulk-pdf-input" accept=".pdf,application/pdf" multiple style="display:none;" onchange="window.StarAppBridge.handleBulkPdfSelect(event)">
                        <div style="color:var(--deep-frozen-midnight); font-weight:800; font-size:0.8125rem; display:flex; align-items:center; justify-content:center; gap:8px;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                            Click to Select PDF Files (Multiple Files Supported)
                        </div>
                        <div style="font-size:0.71875rem; color:var(--frost-navy-50); margin-top:4px;">Upload course manuals, technical whitepapers, or syllabus handbooks</div>
                    </div>

                    <div id="bulk-pdf-list" style="margin-top:10px; display:flex; flex-direction:column; gap:6px;"></div>
                </div>

                <!-- 2. YouTube Video Links (Multiples Supported) -->
                <div style="margin-bottom:16px; padding:14px; background:rgba(234,244,255,0.6); border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel-50);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <div style="font-size:0.78125rem; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px; display:flex; align-items:center; gap:6px;">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                            YouTube Video Lectures (Multiple Links Supported)
                        </div>
                        <button type="button" class="btn-secondary btn-sm" style="font-weight:700; font-size:0.71875rem; padding:4px 10px; display:inline-flex; align-items:center; gap:4px;" onclick="window.StarAppBridge.addYouTubeRow()">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                            + Add Another YouTube Link
                        </button>
                    </div>

                    <div id="youtube-rows-container">
                        <div class="youtube-input-row" style="display:grid; grid-template-columns:1fr 1.5fr auto; gap:8px; align-items:center; margin-bottom:8px;">
                            <input type="text" class="yt-title-input form-control" placeholder="Video Title (e.g. Masterclass Lecture 1)">
                            <input type="url" class="yt-url-input form-control" placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/...">
                            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.clearOrRemoveYouTubeRow(this)" style="color:#d9534f; padding:4px 8px; font-weight:800;" title="Clear row">&times;</button>
                        </div>
                    </div>
                </div>

                <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:18px; padding-top:12px; border-top:1px solid var(--icy-steel-30);">
                    <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Cancel</button>
                    <button type="submit" class="btn-metal" style="font-weight:800;">Upload &amp; Publish All Materials &rarr;</button>
                </div>
            </form>
            """

        elif self.active_modal == "edit_material":
            mat_id = self.modal_payload.get("material_id") if self.modal_payload else ""
            mat = store.get_material(mat_id)
            if not mat:
                title = "Material Not Found"
                body = "<p style='padding:20px; text-align:center;'>Material not found.</p>"
            else:
                title = f"Edit Learning Material &mdash; {escape(mat.title)}"
                badge_opts = []
                for b in store.get_all_badges():
                    sel = " selected" if b.id == mat.badge_id else ""
                    badge_opts.append(f'<option value="{b.id}"{sel}>{escape(b.code)}: {escape(b.title)}</option>')

                body = f"""
                <form onsubmit="event.preventDefault(); window.StarAppBridge.submitEditMaterial('{escape(mat.id)}');">
                    <div class="form-group" style="margin-bottom:12px;">
                        <label class="form-label" style="font-size:0.75rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Target Milestone Badge *</label>
                        <select id="edit-mat-badge" class="form-select" style="font-size:0.78125rem; font-weight:700;">
                            {"".join(badge_opts)}
                        </select>
                    </div>

                    <div style="display:grid; grid-template-columns:2fr 1fr; gap:12px; margin-bottom:12px;">
                        <div class="form-group" style="margin:0;">
                            <label class="form-label" style="font-size:0.75rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Resource Title *</label>
                            <input type="text" id="edit-mat-title" class="form-control" value="{escape(mat.title)}" required>
                        </div>
                        <div class="form-group" style="margin:0;">
                            <label class="form-label" style="font-size:0.75rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Topic Category *</label>
                            <input type="text" id="edit-mat-topic" class="form-control" value="{escape(mat.topic)}" required>
                        </div>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 2fr; gap:12px; margin-bottom:12px;">
                        <div class="form-group" style="margin:0;">
                            <label class="form-label" style="font-size:0.75rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Format / Type</label>
                            <select id="edit-mat-type" class="form-select">
                                <option value="youtube"{" selected" if mat.material_type == "youtube" else ""}>Embedded YouTube Video</option>
                                <option value="pdf"{" selected" if mat.material_type == "pdf" else ""}>PDF Handbook Document</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin:0;">
                            <label class="form-label" style="font-size:0.75rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Resource URL or Embed Link</label>
                            <input type="text" id="edit-mat-url" class="form-control" value="{escape(mat.url_or_data)}" required>
                        </div>
                    </div>

                    <div class="form-group" style="margin-bottom:14px;">
                        <label class="form-label" style="font-size:0.75rem; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Description & Overview</label>
                        <textarea id="edit-mat-desc" class="form-textarea" rows="3">{escape(mat.description)}</textarea>
                    </div>

                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px; padding-top:12px; border-top:1px solid var(--icy-steel-30);">
                        <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Cancel</button>
                        <button type="submit" class="btn-metal" style="font-weight:800;">Save Changes &rarr;</button>
                    </div>
                </form>
                """

        elif self.active_modal == "badge_creation_preview":
            title = "Badge Creation Preview & Verification"
            rev = store.get_user_by_id(self.modal_payload.get("reviewer_id", ""))
            body = render_badge_creation_preview_modal(self.modal_payload, rev)

        elif self.active_modal == "badge_inspect":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Badge Inspection — {badge.code if badge else ''}"
            rev = store.get_user_by_id(getattr(badge, "assigned_reviewer_id", "")) if badge else None
            creator = store.get_user_by_id(getattr(badge, "creator_id", "")) if badge else None
            body = render_badge_review_inspect_modal(badge, rev, creator) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal == "badge_reviewer_edit":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Edit Badge Proposal — {badge.code if badge else ''}"
            custom_caps = store.get_custom_capabilities()
            custom_skills = store.get_custom_skills()
            elig_revs = store.get_eligible_badge_reviewers(getattr(badge, "target_band", "B1")) if badge else []
            body = render_badge_reviewer_edit_modal(badge, custom_caps, custom_skills, elig_revs) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal == "badge_reviewer_manage":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Manage Reviewer — {badge.code if badge else ''}"
            elig_revs = store.get_eligible_badge_reviewers(getattr(badge, "target_band", "B1")) if badge else []
            cur_rev = store.get_user_by_id(getattr(badge, "assigned_reviewer_id", "") or "") if badge else None
            body = render_badge_reviewer_manage_modal(badge, elig_revs, cur_rev) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal == "badge_activity_log":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Badge Activity Log — {badge.code if badge else ''}"
            events = store.get_badge_review_history(badge_id=b_id) if badge else []
            cur_rev = store.get_user_by_id(getattr(badge, "assigned_reviewer_id", "") or "") if badge else None
            body = render_badge_activity_log_modal(badge, events, cur_rev) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal == "badge_approval_confirm":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = "Confirm Institutional Authorization"
            body = render_badge_approval_confirm_modal(badge, self.current_user) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal in ("cosmonaut_reviewer_view", "cosmonaut_timeline_view"):
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            is_rev = self.active_modal == "cosmonaut_reviewer_view"
            title = "Your Reviewer" if is_rev else "Your Timeline"
            if not badge:
                body = "<p style='padding:20px; text-align:center;'>Badge not found.</p>"
            elif is_rev:
                body = render_cosmonaut_reviewer_modal(badge, self.current_user, store)
            else:
                body = render_cosmonaut_timeline_modal(badge, self.current_user, store)

        elif self.active_modal == "decision_revoke_confirm":
            sid = self.modal_payload.get("submission_id", "")
            sub_o = store.get_submission(sid)
            g_o = store.get_guardian_assessment_for_submission(sid) if sub_o else None
            title = "Revoke Decision"
            body = (render_decision_revoke_confirm_modal(sub_o, store.get_badge(sub_o.badge_id), store.get_user_by_id(sub_o.cosmonaut_id), g_o)
                    if (sub_o and g_o) else "<p style='padding:20px; text-align:center;'>There is no final decision to revoke.</p>")

        elif self.active_modal in ("badge_publish_confirm", "badge_revoke_confirm"):
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            is_pub = self.active_modal == "badge_publish_confirm"
            title = "Confirm Publication" if is_pub else "Confirm Revocation"
            if not badge:
                body = "<p style='padding:20px; text-align:center;'>Badge not found.</p>"
            elif is_pub:
                body = render_badge_publish_confirm_modal(badge, self.current_user, store)
            else:
                body = render_badge_revoke_confirm_modal(badge, self.current_user)

        elif self.active_modal == "badge_reviewer_return":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = "Return Badge Proposal for Revisions"
            body = render_badge_return_confirm_modal(badge, self.current_user) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal == "cosmonaut_badge_preview":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Badge Curriculum & Practice — {badge.code if badge else ''}"
            body = render_cosmonaut_badge_preview_modal(badge, self.current_user) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal == "reviewer_timeline_modal":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Milestone Timeline Schedule — {badge.code if badge else ''}"
            body = render_reviewer_badge_timeline_modal(badge, self.current_user, store) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal in ("badge_timeline_mapping", "badge_mapping_view", "badge_timeline_view"):
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            section, label = {
                "badge_mapping_view": ("mapping", "Mapping"),
                "badge_timeline_view": ("timeline", "Timeline"),
            }.get(self.active_modal, ("both", "Timeline & Mapping"))
            title = f"{label} — {badge.code if badge else ''}"
            body = render_badge_timeline_mapping_modal(badge, store, section) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal == "reviewer_project_creator":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Create Project — {badge.code if badge else ''}"
            body = render_reviewer_project_creator_modal(badge, self.current_user, store) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal == "submission_portal_modal":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Submit Project Deliverables — {badge.code if badge else ''}"
            if badge and self.current_user:
                existing_subs = store.get_submissions_for_cosmonaut(self.current_user.id, b_id)
                latest_sub = existing_subs[-1] if existing_subs else None
                body = render_cosmonaut_submission_modal(badge, self.current_user, store, existing_sub=latest_sub)
            else:
                body = "<div style='padding:24px; text-align:center; color:var(--frost-navy-50);'>Milestone badge not found.</div>"

        elif self.active_modal == "create_cycle_modal":
            title = "Create Performance Cycle"
            cycles_list = store.get_all_cycles()
            active_cyc = next((c for c in cycles_list if c.status in ("active", "evaluating")), None)
            body = render_create_cycle_modal(cycles_list, active_cyc)

        elif self.active_modal == "cycle_candidate_detail_modal":
            c_id = self.modal_payload.get("cycle_id") or self._get_effective_cycle_id()
            u_id = self.modal_payload.get("user_id", "")
            cyc = store.get_cycle(c_id)
            u_obj = store.get_user_by_id(u_id)
            if cyc and u_obj:
                rows = compute_cycle_candidate_performance(c_id, store, users_override=[u_obj])
                title = f"Cycle Performance & Appraisal — {u_obj.name}"
                body = render_cycle_candidate_detail_modal(rows[0], cyc, is_closed=(cyc.status == "closed")) if rows else "<p style='padding:20px;'>No data.</p>"
            else:
                title = "Cycle Candidate Details"
                body = "<p style='padding:20px; text-align:center;'>Candidate or cycle not found.</p>"

        elif self.active_modal == "mapping_calendar_modal":
            title = "Review Schedule Calendar"
            body = render_mapping_calendar_modal(
                review_dates=getattr(self, "mapping_review_dates", None),
                review_anchor=getattr(self, "mapping_review_anchor", "2026-11-18"),
                review_direction=getattr(self, "mapping_review_direction", "after"),
                review_days_count=getattr(self, "mapping_review_days_count", 3),
                review_mode=getattr(self, "mapping_review_mode", "gap"),
                range_start=getattr(self, "mapping_range_start", ""),
                calendar_year=getattr(self, "mapping_calendar_year", 2026),
                calendar_month=getattr(self, "mapping_calendar_month", 11),
            )

        modal_dialog_class = "liquid-glass-modal modal-dialog"
        if self.active_modal in ["material_preview", "badge_creation_preview", "badge_reviewer_edit", "badge_inspect", "cosmonaut_badge_preview", "reviewer_timeline_modal", "badge_timeline_mapping", "badge_mapping_view", "badge_timeline_view", "cosmonaut_reviewer_view", "cosmonaut_timeline_view", "reviewer_project_creator", "cycle_candidate_detail_modal", "create_badge", "edit_badge"]:
            modal_dialog_class += " modal-xl modal-lg"
        elif self.active_modal in ["marksheet_modal", "decision_revoke_confirm", "add_material", "edit_material", "badge_approval_confirm", "badge_publish_confirm", "badge_revoke_confirm", "badge_activity_log", "badge_reviewer_manage", "badge_reviewer_return", "create_cycle_modal"]:
            modal_dialog_class += " modal-lg"
        elif self.active_modal == "submission_portal_modal":
            modal_dialog_class += " modal-form"
        elif self.active_modal == "mapping_calendar_modal":
            modal_dialog_class += " modal-cal"

        return f"""
        <div class="modal-backdrop" onclick="if(event.target===this) window.StarAppBridge.dispatchAction('close_modal', '{{}}')">
            <div class="{modal_dialog_class}">
                <div class="modal-header">
                    <h3 class="modal-title">{escape(title)}</h3>
                    <button type="button" class="modal-close-btn" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">&times;</button>
                </div>
                <div class="modal-body">
                    {body}
                </div>
            </div>
        </div>
        """

    # ==========================================================================
    # LOGIN VIEW
    # ==========================================================================

    def render_login_view(self) -> str:
        quick_accounts = store.get_quick_login_accounts() if _demo_mode_enabled() else []
        quick_pills = []
        for acc in quick_accounts:
            acc_id = escape(acc["id"])
            acc_name = escape(acc["name"])
            role_tag = escape(acc["role_tag"])
            ceo_cls = " is-ceo" if acc.get("is_guardian") else ""
            quick_pills.append(
                f'<button type="button" class="lg-quick-pill{ceo_cls}" onclick="window.StarAppBridge.dispatchAction(\'select_demo_account\', \'{acc_id}\')">'
                f'<span>{acc_name}</span>'
                f'<span class="lg-quick-pill-band">{role_tag}</span>'
                f'</button>'
            )

        quick_pills_html = "".join(quick_pills)
        mail_icon = get_icon("mail", 16)
        lock_icon = get_icon("lock", 16)
        eye_icon = get_icon("eye", 16)
        arrow_icon = get_icon("arrow_right", 16)
        alert_icon = get_icon("alert_triangle", 16)
        flash_icon = get_icon("flash", 15, "margin-right:6px;")

        error_banner = ""
        if self.login_error:
            error_banner = f"""
            <div class="lg-login-error" id="login-error-banner" role="alert">
                {alert_icon}
                <span>{escape(self.login_error)}</span>
            </div>
            """

        email_val = escape(self.login_email_draft or "")

        return f"""
        <div class="lg-login-shell">
            <div class="lg-login-wrap">
                <div class="lg-login-brand">
                    <div class="brand-badge" style="width:52px; height:52px; margin:0 auto 12px;">
                        <svg viewBox="0 0 24 24" style="width:28px; height:28px; fill:var(--snow-white);"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    </div>
                    <h1 style="font-size:2.9rem; font-weight:900; color:var(--frost-navy); letter-spacing:1.2px; margin:0; line-height:1.1;">STARAPP</h1>
                </div>

                <div class="lg-login-card">
                    <div style="margin-bottom:20px;">
                        <h2 style="font-size:1.35rem; font-weight:800; color:var(--frost-navy); margin:0;">Sign In</h2>
                        <p style="font-size:0.84375rem; font-weight:600; color:var(--frost-navy); opacity:0.78; margin:4px 0 0 0;">Enter your StarApp email and password.</p>
                    </div>

                    {error_banner}

                    <form id="starapp-login-form" novalidate onsubmit="(function(e){{if(e)e.preventDefault();var em=document.getElementById('login-email');var pw=document.getElementById('login-password');window.StarAppBridge.dispatchAction('login',JSON.stringify({{email:em?em.value:'',password:pw?pw.value:'',require_password:true}}));return false;}})(event)">
                        <div class="lg-login-field">
                            <label class="lg-login-label" for="login-email">Email Address</label>
                            <div class="lg-login-input-wrap">
                                <span class="lg-login-input-icon">{mail_icon}</span>
                                <input id="login-email" name="email" type="email" autocomplete="email" class="lg-login-input" placeholder="name@starapp.io" value="{email_val}" required />
                            </div>
                        </div>

                        <div class="lg-login-field">
                            <label class="lg-login-label" for="login-password">Password</label>
                            <div class="lg-login-input-wrap">
                                <span class="lg-login-input-icon">{lock_icon}</span>
                                <input id="login-password" name="password" type="password" autocomplete="current-password" class="lg-login-input" placeholder="Enter your password" minlength="6" required />
                                <button type="button" class="lg-login-pwd-toggle" aria-label="Toggle password visibility" onclick="(function(){{var i=document.getElementById('login-password');if(i){{i.type=i.type==='password'?'text':'password';}}}})()">
                                    {eye_icon}
                                </button>
                            </div>
                        </div>

                        <button type="submit" id="login-submit-btn" class="btn-metal lg-login-submit">
                            <span>Sign In</span>
                            {arrow_icon}
                        </button>
                    </form>
                </div>

                <div class="lg-quick-login-box">
                    <div class="lg-quick-login-header">
                        <span style="display:inline-flex; align-items:center; font-size:0.84375rem; font-weight:800; color:var(--frost-navy);">
                            {flash_icon} Quick Login
                        </span>
                        <span style="font-size:0.75rem; font-weight:700; color:var(--frost-navy); opacity:0.75;">
                            6 Bands + CEO Guardian
                        </span>
                    </div>
                    <div class="lg-quick-pills-grid">
                        {quick_pills_html}
                    </div>
                </div>
            </div>
        </div>
        """

    # ==========================================================================
    # MAIN APPLICATION RENDERER
    # ==========================================================================

    def _dispatch_browser_render(self, regions_payload: Dict[str, Any], full_html: str):
        """Dispatches 3-region incremental update to JS bridge when running in Pyodide browser or backend API."""
        self.last_rendered_regions = regions_payload
        self.last_rendered_html = full_html
        if not (IS_BROWSER and hasattr(js, "document")):
            return
        if hasattr(js, "window") and hasattr(js.window, "StarAppBridge"):
            bridge = js.window.StarAppBridge
            if hasattr(bridge, "updateRegions"):
                try:
                    bridge.updateRegions(json.dumps(regions_payload))
                    return
                except Exception as exc:
                    print(f"[Controller] updateRegions fallback due to error: {exc}")
            if hasattr(bridge, "updateAppRoot"):
                try:
                    bridge.updateAppRoot(full_html)
                    return
                except Exception:
                    pass
        root = js.document.getElementById("app-root")
        if root:
            root.innerHTML = full_html

    def render(self) -> str:
        """Constructs the complete application view HTML and dispatches incremental region updates."""
        self.render_generation += 1
        render_source = getattr(self, "_last_render_source", "direct")
        self._last_render_source = "direct"

        if not self.current_user or self.current_view == "login":
            html_output = self.render_login_view()
            self._dispatch_browser_render(
                {
                    "mode": "login",
                    "generation": self.render_generation,
                    "isCrossTabReload": render_source == "cross_tab_reload",
                    "portalKey": "login",
                    "routeKey": "login",
                    "activeNavId": "",
                    "pageTitle": "StarApp — Sign In",
                    "sidebarBadges": {},
                    "sidebarHtml": "",
                    "pageContainerClass": "",
                    "flashHtml": "",
                    "mainContentHtml": html_output,
                    "activeModal": "",
                    "modalKey": "",
                    "modalTitle": "",
                    "modalHtml": "",
                },
                html_output,
            )
            return html_output

        # Defence in depth: whatever put the controller on a Guardian page (a stale session snapshot, a
        # crafted action, a role change), a non-guardian can never be RENDERED a g_* page.
        if self.current_view.startswith("g_") and not self._is_guardian_user():
            self.current_view = self.COSMONAUT_HOME_VIEW
            self.active_modal = None
        effective_cid = self._get_effective_cycle_id()
        page_token = bind_page_state(self.list_pages)
        try:
            with store.cycle_scope(effective_cid):
                return self._render_workspace_scoped(render_source, effective_cid)
        finally:
            reset_page_state(page_token)

    def _render_workspace_scoped(self, render_source: str, effective_cid: str) -> str:
        # "Past Cycle & Performance" is part of the Choose Cycle page now; old links / saved sessions still resolve.
        if self.current_view == "c_assessments":
            self.current_view = "c_badge_reviews"
        if self.current_view == "c_cycles":
            self.current_view = "c_choose_cycle"
        # Defence in depth: reviewer pages exist only from Band 2 up (a stale session / crafted view id gets Badges).
        if (self.current_view in COSMONAUT_REVIEWER_VIEWS and not self._is_guardian_user()
                and not is_reviewer_band(getattr(self.current_user, "band", ""))):
            self.current_view = self.COSMONAUT_HOME_VIEW
            self.active_modal = None
        # The reviewer's badge-review page needs a real badge that was sent to this user (stale session / crafted id -> the queue).
        if self.current_view == "c_badge_review":
            _rb = store.get_badge(self.reviewer_review_badge_id) if self.reviewer_review_badge_id else None
            if not (_rb and self._can_open_badge_review(_rb)):
                self.current_view = "c_requests"
        if self.current_view != "c_badge_review":
            self.reviewer_review_editing = False
        # The project page needs a badge allotted to this cosmonaut whose project has been sent (else back to the badge / the badge list).
        if self.current_view == "c_project" and self._allocated_project_denied(self.cosmonaut_submission_badge_id):
            self.current_view = "c_badge_detail" if store.get_badge(self.cosmonaut_submission_badge_id) else self.COSMONAUT_HOME_VIEW
            self.active_modal = None
        # Common data calculations (scoped to effective_cid)
        badges = store.get_all_badges()
        cosmonauts = store.get_all_cosmonauts()
        all_subs = store.get_all_submissions()
        all_asms = store.get_all_assessments()
        badges_map = {b.id: b for b in badges}
        cosmo_map = {c.id: c for c in cosmonauts}

        # Unread notifications
        user_notifs = store.get_notifications(self.current_user.id)
        unread_notifs = len([n for n in user_notifs if not n.is_read])

        sidebar_html = ""
        main_content_html = ""
        page_title = "StarApp Workspace"
        sidebar_badges: Dict[str, int] = {}
        active_nav_id = self.current_view
        route_key = self.current_view

        user_roles = getattr(self.current_user, "roles", [self.current_user.role])
        is_guardian_view = self.current_view.startswith("g_")
        selected_cycle_obj = store.get_cycle(effective_cid)

        if is_guardian_view:
            hide_sidebar = (
                self.current_view == "g_learning"
                or (self.current_view == "g_create_badge" and not self.create_badge_band)
            )
            pending_reviews = len([s for s in all_subs if s.status == "pending"])
            pending_exts = len([e for e in store.get_all_extensions() if e.status == "pending"])
            pending_badge_approvals = len(store.get_pending_badge_approvals(
                reviewer_id=self.current_user.id if "badge_reviewer" in user_roles and "guardian" not in user_roles else None,
                target_band=self.create_badge_band
            ))
            sidebar_badges = {"g_reviews": pending_reviews, "g_extensions": pending_exts, "g_badge_approval": pending_badge_approvals}
            if self.current_view == "g_review_detail":
                active_nav_id = "g_reviews"
            elif self.current_view == "g_mapping_badge_detail":
                active_nav_id = "g_mapping"
            elif self.current_view == "g_learning":
                active_nav_id = "g_create_badge"
            else:
                active_nav_id = self.current_view
            sidebar_html = render_guardian_sidebar(
                self.current_view,
                self.current_user,
                pending_reviews,
                pending_exts,
                pending_badge_approvals,
                active_band=self.create_badge_band,
                hidden=hide_sidebar,
                selected_cycle=selected_cycle_obj
            )

            if self.current_view in ("g_create_badge", "g_learning"):
                page_title = "Learning Bands & Badge Studio — StarApp" if self.current_view == "g_learning" else "Create Badge — StarApp"
                band_for_view = None if self.current_view == "g_learning" else self.create_badge_band
                custom_caps = store.get_custom_capabilities()
                custom_skills = store.get_custom_skills()
                elig_revs = store.get_eligible_badge_reviewers(band_for_view) if band_for_view else []
                saved_b = store.get_saved_badges(band_for_view)
                main_content_html = render_guardian_create_badge(
                    selected_band=band_for_view,
                    power=self.create_badge_power,
                    capability=self.create_badge_capability,
                    skill=self.create_badge_skill,
                    reviewer_id=self.create_badge_reviewer_id,
                    prompt_json=self.create_badge_prompt_json,
                    metadata=self.create_badge_metadata,
                    custom_capabilities=custom_caps,
                    custom_skills=custom_skills,
                    eligible_reviewers=elig_revs,
                    json_error=self.create_badge_json_error,
                    skill_search=self.create_badge_skill_search,
                    outcome_sentence=self.create_badge_outcome_sentence,
                    created_badge_data=self.created_badge_data,
                    is_editing_badge=self.is_editing_badge,
                    saved_badges=saved_b,
                    selected_cycle=selected_cycle_obj
                )

            elif self.current_view == "g_earning":
                page_title = "Earning — Global Cycle View — StarApp"
                main_content_html = render_guardian_pillar_placeholder("Earning", selected_cycle_obj)

            elif self.current_view == "g_contribution":
                page_title = "Contribution — Global Cycle View — StarApp"
                main_content_html = render_guardian_pillar_placeholder("Contribution", selected_cycle_obj)

            elif self.current_view == "g_badge_approval":
                page_title = "Reviewer Badge Approval — StarApp"
                all_badges = store.get_all_badges()
                # The queue is scoped to the band workspace the Guardian is in (sidebar band switcher); with no active
                # band it shows every band. There is deliberately no band dropdown on this page.
                band_filter = self.create_badge_band or "all"
                if band_filter and band_filter != "all":
                    all_badges = [b for b in all_badges if getattr(b, "target_band", "") == band_filter]
                main_content_html = render_guardian_badge_approval_queue(
                    badges=all_badges,
                    current_user=self.current_user,
                    status_filter=self.badge_approval_filter,
                    search_query=self.badge_approval_search,
                    selected_band=band_filter
                )

            elif self.current_view == "g_dashboard":
                page_title = "Training Batch Overview & Analytics"
                actual_cosmo = store.get_user_by_id("cosmo_1")
                assigned_badges = store.get_badges_for_cosmonaut("cosmo_1")
                u_asms = store.get_assessments_for_cosmonaut("cosmo_1")
                u_subs = store.get_submissions_for_cosmonaut("cosmo_1")
                u_exts = store.get_extensions_for_cosmonaut("cosmo_1")
                cohort_profiles = get_guardian_cohort_profiles(actual_cosmo, assigned_badges, u_asms, u_subs, u_exts)
                cohort_analytics = calculate_guardian_cohort_analytics(cohort_profiles, all_subs, all_asms)

                selected_cosmo_data = None
                if self.selected_guardian_cosmo_id != "all":
                    selected_cosmo_data = get_cosmonaut_individual_dossier(self.selected_guardian_cosmo_id, cohort_profiles)

                risk_filter = getattr(self, "guardian_risk_filter", "all")
                main_content_html = render_guardian_dashboard(
                    cohort_analytics=cohort_analytics,
                    cohort_profiles=cohort_profiles,
                    selected_cosmo_id=self.selected_guardian_cosmo_id,
                    selected_cosmo_data=selected_cosmo_data,
                    risk_filter=risk_filter
                )

            elif self.current_view == "g_roadmap":
                page_title = "Curriculum Milestone Roadmap"
                actual_cosmo = store.get_user_by_id("cosmo_1")
                cosmo_asms = store.get_assessments_for_cosmonaut("cosmo_1")
                cosmo_subs = store.get_submissions_for_cosmonaut("cosmo_1")
                nodes = generate_roadmap_graph(badges, "cosmo_1", cosmo_asms, cosmo_subs)
                main_content_html = render_gamified_roadmap(actual_cosmo, nodes, is_guardian=True)

            elif self.current_view == "g_allotment":
                page_title = "Badge Allotment & Timeline Management"
                scoped_badges = badges
                scoped_cosmonauts = cosmonauts
                if self.create_badge_band:
                    b_filtered = [b for b in badges if getattr(b, "target_band", "") == self.create_badge_band]
                    if b_filtered:
                        scoped_badges = b_filtered
                    c_filtered = [c for c in cosmonauts if getattr(c, "band", "") == self.create_badge_band]
                    if c_filtered:
                        scoped_cosmonauts = c_filtered
                main_content_html = render_guardian_badge_allotment(scoped_badges, scoped_cosmonauts, getattr(self, 'guardian_allotment_filter', 'all'),
                    all_band_mappings=store.get_band_mappings(),
                    all_timelines=store.get_timelines_dict()
                )

            elif self.current_view == "g_mapping":
                page_title = "Cosmonaut & Reviewer Competency Mapping"
                active_mapping_band = self.create_badge_band if self.create_badge_band else self.mapping_selected_band
                # Synchronize mapping_selected_badge with active band within current cycle
                app_badges = [b for b in store.get_saved_badges(active_mapping_band) if b.get("workflow_status") in ("approved", "ready_for_review")]
                if not app_badges and store.db and store.db.conn:
                    try:
                        curr_cid = store.get_effective_read_cycle_id()
                        rows = store.db.conn.execute("SELECT * FROM badges WHERE target_band = ? AND cycle_id = ? AND workflow_status IN ('approved', 'ready_for_review')", (active_mapping_band, curr_cid)).fetchall()
                        app_badges = [dict(r) for r in rows]
                    except Exception:
                        pass
                badge_titles = [b.get("title") for b in app_badges] + [b.get("code") for b in app_badges] + [b.get("id") for b in app_badges]
                if app_badges and self.mapping_selected_badge and not getattr(self, "mapping_selected_badge_id", ""):
                    for ab in app_badges:
                        if self.mapping_selected_badge in (ab.get("title"), ab.get("name"), ab.get("code"), ab.get("id")):
                            self.mapping_selected_badge_id = ab.get("id", "")
                            break

                main_content_html = render_guardian_mapping(
                    selected_band=active_mapping_band,
                    selected_roles=self.mapping_selected_roles,
                    selected_badge=self.mapping_selected_badge,
                    selected_cosmonauts=self.mapping_selected_cosmonauts,
                    selected_reviewer_band=self.mapping_selected_reviewer_band,
                    selected_reviewer_bands=getattr(self, "mapping_selected_reviewer_bands", [self.mapping_selected_reviewer_band]),
                    selected_reviewers=self.mapping_selected_reviewers,
                    review_dates=getattr(self, "mapping_review_dates", ["2026-11-18", "2026-11-19", "2026-11-20"]),
                    review_anchor=getattr(self, "mapping_review_anchor", "2026-11-18"),
                    review_direction=getattr(self, "mapping_review_direction", "after"),
                    review_days_count=getattr(self, "mapping_review_days_count", 3),
                    review_mode=getattr(self, "mapping_review_mode", "gap"),
                    range_start=getattr(self, "mapping_range_start", ""),
                    calendar_year=getattr(self, "mapping_calendar_year", 2026),
                    calendar_month=getattr(self, "mapping_calendar_month", 11),
                    editing_mapping_id=getattr(self, "editing_mapping_id", None),
                    cosmo_search=getattr(self, "mapping_cosmo_search", ""),
                    reviewer_search=getattr(self, "mapping_reviewer_search", ""),
                    badge_search=getattr(self, "mapping_badge_search", ""),
                    all_mappings=store.get_band_mappings(),
                    all_requests=store.get_mapping_requests(),
                    staged_previews=getattr(self, "mapping_staged_previews", {}),
                    expanded_badge_key=getattr(self, "mapping_expanded_badge_key", ""),
                    show_final_stage=getattr(self, "mapping_show_final_stage", False),
                    store=store
                )

            elif self.current_view == "g_mapping_badge_detail":
                active_mapping_band = self.create_badge_band if self.create_badge_band else self.mapping_selected_band
                detail_key = getattr(self, "mapping_detail_badge_key", "") or getattr(self, "mapping_expanded_badge_key", "")
                route_key = f"g_mapping_badge_detail:{active_mapping_band}:{detail_key}"
                page_title = "Badge Mapping & Requests Detail — StarApp"
                main_content_html = render_guardian_mapping_badge_detail(
                    selected_band=active_mapping_band,
                    badge_key=detail_key,
                    review_dates=getattr(self, "mapping_review_dates", ["2026-11-18", "2026-11-19", "2026-11-20"]),
                    all_mappings=store.get_band_mappings(),
                    all_requests=store.get_mapping_requests(),
                    staged_previews=getattr(self, "mapping_staged_previews", {}),
                    store=store
                )

            elif self.current_view == "g_reviews":
                page_title = "Assessment Dashboard"
                asms_by_sub = {a.submission_id: a for a in all_asms}
                scoped_subs = all_subs
                scoped_badges = list(badges)
                if self.create_badge_band:
                    b_subs = [s for s in all_subs if (cosmo_map.get(s.cosmonaut_id) and cosmo_map[s.cosmonaut_id].band == self.create_badge_band) or (badges_map.get(s.badge_id) and getattr(badges_map[s.badge_id], "target_band", "") == self.create_badge_band)]
                    if b_subs:
                        scoped_subs = b_subs
                    sub_badge_ids = {s.badge_id for s in scoped_subs}
                    scoped_badges = [b for b in badges if getattr(b, "target_band", "") == self.create_badge_band or b.id in sub_badge_ids]
                main_content_html = render_guardian_review_queue(
                    scoped_subs,
                    asms_by_sub,
                    badges_map,
                    cosmo_map,
                    self.guardian_review_filter,
                    badges_list=scoped_badges,
                    power_filter=getattr(self, "assessment_power_filter", "all"),
                    capability_filter=getattr(self, "assessment_capability_filter", "all"),
                    selected_badge_id=getattr(self, "assessment_selected_badge_id", None),
                    selected_cosmonaut_id=getattr(self, "assessment_selected_cosmonaut_id", None),
                    all_band_mappings=store.get_band_mappings(),
                )

            elif self.current_view == "g_review_detail":
                page_title = "Project Deliverable Technical Inspection & Assessment"
                is_guardian = (getattr(self.current_user, "role", "") == "guardian" or "guardian" in getattr(self.current_user, "roles", []))
                if not is_guardian:
                    main_content_html = "<div class='liquid-glass-card' style='padding:40px; text-align:center;'><h3 style='color:#DC2626;'>Unauthorized Access</h3><p style='color:var(--frost-navy-50); margin-top:8px;'>Only Guardians can access the Guardian review detail portal.</p></div>"
                else:
                    sub = store.get_submission(self.selected_review_sub_id) if getattr(self, "selected_review_sub_id", None) else None
                    if sub:
                        route_key = f"g_review_detail:{sub.id}"
                        badge = badges_map.get(sub.badge_id)
                        cosmo = cosmo_map.get(sub.cosmonaut_id)
                        existing_asm = store.get_assessment_for_submission(sub.id)
                        prev_asms = store.get_assessments_for_cosmonaut(sub.cosmonaut_id, sub.badge_id)
                        main_content_html = render_guardian_review_detail(
                            sub, badge, cosmo, existing_asm, prev_asms, getattr(self, "selected_viewer_tab", "pdf")
                        )
                    else:
                        main_content_html = "<div class='liquid-glass-card' style='padding:40px; text-align:center;'>Submission not found. <button onclick=\"window.StarAppBridge.dispatchAction('nav_guardian', 'g_reviews')\" class='btn-secondary'>Back to Reviews</button></div>"

            elif self.current_view == "g_materials":
                page_title = "Learning Resources & Materials Manager"
                scoped_materials = store.get_materials()
                scoped_badges = badges
                if self.create_badge_band:
                    band_b_ids = {b.id for b in badges if getattr(b, "target_band", "") == self.create_badge_band}
                    if band_b_ids:
                        scoped_badges = [b for b in badges if b.id in band_b_ids]
                        m_filtered = [m for m in scoped_materials if getattr(m, "badge_id", "") in band_b_ids]
                        if m_filtered:
                            scoped_materials = m_filtered
                main_content_html = render_guardian_materials(
                    materials=scoped_materials,
                    badges=scoped_badges,
                    badges_map=badges_map,
                    selected_badge_filter=self.materials_badge_filter,
                    selected_type_filter=self.materials_type_filter
                )

            elif self.current_view == "g_extensions":
                page_title = "Milestone Deadline Extensions"
                scoped_exts = store.get_all_extensions()
                if self.create_badge_band:
                    ext_filtered = [e for e in scoped_exts if (cosmo_map.get(e.cosmonaut_id) and cosmo_map[e.cosmonaut_id].band == self.create_badge_band) or (badges_map.get(e.badge_id) and getattr(badges_map[e.badge_id], "target_band", "") == self.create_badge_band)]
                    if ext_filtered:
                        scoped_exts = ext_filtered
                main_content_html = render_guardian_extensions(scoped_exts, cosmo_map, badges_map)

            elif self.current_view == "g_announcements":
                page_title = "Academy Announcement Broadcaster"
                main_content_html = render_guardian_announcements(store.get_all_announcements(), cosmonauts)

            elif self.current_view == "g_activity":
                page_title = "Academy Activity & Audit Stream"
                main_content_html = render_guardian_activity_feed(store.get_activities(), cosmonauts)

            elif self.current_view == "g_profile":
                page_title = "My Profile — StarApp"
                _uid = self.current_user.id
                main_content_html = render_guardian_profile(self.current_user, {
                    "cohort_size": len(cosmonauts),
                    "badges_authored": len([b for b in badges if getattr(b, "creator_id", "") == _uid]),
                    "badges_total": len(badges),
                    "badges_published": len([b for b in badges if getattr(b, "is_published", False)]),
                    "pending_approvals": pending_badge_approvals,
                    "pending_reviews": pending_reviews,
                    "pending_extensions": pending_exts,
                    "cycle_name": getattr(selected_cycle_obj, "name", "") or "",
                    "cycle_status": (getattr(selected_cycle_obj, "status", "") or "").title(),
                })

            elif self.current_view == "g_cycles":
                page_title = "6-Month Performance Cycles & Appraisals"
                all_cycles = store.get_all_cycles()
                sel_cyc = store.get_cycle(effective_cid)
                cand_rows = compute_cycle_candidate_performance(effective_cid, store)
                main_content_html = render_guardian_cycles_view(
                    cycles=all_cycles,
                    selected_cycle=sel_cyc,
                    candidate_rows=cand_rows,
                    band_filter=getattr(self, "cycle_band_filter", "all"),
                    role_filter=getattr(self, "cycle_role_filter", "all")
                )

        else:  # Cosmonaut Portal
            unread_anns = len([a for a in store.get_announcements_for_cosmonaut(self.current_user.id) if self.current_user.id not in a.read_by_cosmonaut_ids])
            cosmo_reqs = store.get_badge_review_requests_for_user(self.current_user.id)
            pending_cosmo_reqs_cnt = len([r for r in cosmo_reqs if r.get("workflow_status") == "pending_review" or r.get("assignment_status") == "pending"])
            if self.current_view in ("c_badge_detail", "c_project"):
                active_nav_id = "c_submission"
            elif self.current_view == "c_assessment_detail":
                active_nav_id = "c_badge_reviews"
            elif self.current_view == "c_badge_review":
                active_nav_id = "c_requests"
            else:
                active_nav_id = self.current_view
            sidebar_html = render_cosmonaut_sidebar(
                self.current_view,
                self.current_user,
                unread_anns,
                pending_cosmo_reqs_cnt,
                selected_cycle=selected_cycle_obj
            )

            assigned_badges = store.get_badges_for_cosmonaut(self.current_user.id)
            user_asms = store.get_assessments_for_cosmonaut(self.current_user.id)
            user_subs = store.get_submissions_for_cosmonaut(self.current_user.id)
            profile = store.get_cosmonaut_profile(self.current_user.id)
            summary = calculate_cosmonaut_score_summary(user_asms)
            leaderboard = calculate_batch_leaderboard(cosmonauts, all_asms)

            if self.current_view == "c_choose_cycle":
                page_title = "Choose Cycle — StarApp"
                all_cycles = store.get_all_cycles()
                choose_cycle_stats = {}
                for cyc in all_cycles:
                    with store.cycle_scope(cyc.id):
                        u_rows = compute_cycle_candidate_performance(cyc.id, store, users_override=[self.current_user])
                        if u_rows:
                            choose_cycle_stats[cyc.id] = u_rows[0]
                main_content_html = render_cosmonaut_choose_cycle_view(
                    current_user=self.current_user,
                    cycles=all_cycles,
                    selected_cycle=selected_cycle_obj,
                    cycle_stats=choose_cycle_stats
                )

            elif self.current_view == "c_dashboard":
                page_title = f"Cosmonaut Dossier — {self.current_user.name}"
                recent_anns = store.get_announcements_for_cosmonaut(self.current_user.id)[:3]
                u_exts = store.get_extensions_for_cosmonaut(self.current_user.id)
                cohort_profiles = get_guardian_cohort_profiles(self.current_user, assigned_badges, user_asms, user_subs, u_exts)
                main_content_html = render_cosmonaut_dashboard(
                    current_user=self.current_user,
                    profile=profile,
                    assigned_badges=assigned_badges,
                    assessments=user_asms,
                    submissions=user_subs,
                    extensions=u_exts,
                    recent_announcements=recent_anns,
                    cohort_profiles=cohort_profiles
                )

            elif self.current_view == "c_roadmap":
                page_title = "Interactive Gamified Learning Pathway"
                nodes = generate_roadmap_graph(badges, self.current_user.id, user_asms, user_subs)
                main_content_html = render_gamified_roadmap(self.current_user, nodes)

            elif self.current_view == "c_submission":
                page_title = "Badges & Technical Milestones"
                main_content_html = render_cosmonaut_submission_workspace(assigned_badges, self.cosmonaut_submission_badge_id, user_subs, current_user=self.current_user, store=store, expanded_badge_id=None)

            elif self.current_view == "c_badge_detail":
                target_badge = (
                    badges_map.get(self.cosmonaut_submission_badge_id)
                    or store.get_badge(self.cosmonaut_submission_badge_id)
                    or (assigned_badges[0] if assigned_badges else None)
                )
                if target_badge:
                    page_title = f"{target_badge.code}: {target_badge.title} — Milestone Details"
                    route_key = f"c_badge_detail:{target_badge.id}"
                else:
                    page_title = "Badge Details"
                main_content_html = render_cosmonaut_badge_detail_page(
                    badge=target_badge,
                    current_user=self.current_user,
                    store=store,
                    submissions=user_subs
                )

            elif self.current_view == "c_project":
                _pb = store.get_badge(self.cosmonaut_submission_badge_id)
                page_title = f"Project — {_pb.title}"
                route_key = f"c_project:{_pb.id}"
                main_content_html = render_cosmonaut_project_page(_pb, self.current_user, store)

            elif self.current_view == "c_results":
                page_title = "Official Evaluation Marksheets (50-Mark Rubric)"
                res_badge_id = self.cosmonaut_results_badge_id
                if user_asms and (not res_badge_id or not self.cosmonaut_results_picked):
                    # Unless a badge was chosen on this page, open on the badge with the most recent evaluation (so new marks are seen first)
                    latest_asm = sorted(user_asms, key=lambda a: a.reviewed_at)[-1]
                    res_badge_id = latest_asm.badge_id
                main_content_html = render_cosmonaut_results(
                    assessments=user_asms,
                    badges_map=badges_map,
                    selected_badge_id=res_badge_id,
                    available_badges=assigned_badges,
                    extensions=store.get_extensions_for_cosmonaut(self.current_user.id),
                    selected_asm_id=self.cosmonaut_results_asm_id,
                    submissions=user_subs,
                    project_ready_ids={b.id for b in assigned_badges if store.get_project_prompt_for_cadet(b.id, self.current_user.id)}
                )

            elif self.current_view == "c_materials":
                page_title = "Course Documents & Video Lectures"
                main_content_html = render_cosmonaut_materials(
                    materials=store.get_materials(),
                    badges=assigned_badges,
                    badges_map=badges_map,
                    selected_badge_filter=self.materials_badge_filter,
                    selected_type_filter=self.materials_type_filter
                )

            elif self.current_view == "c_profile":
                page_title = "Cosmonaut Profile & Competency Matrix"
                _cyc_rows = compute_cycle_candidate_performance(effective_cid, store, users_override=[self.current_user])
                main_content_html = render_cosmonaut_profile(
                    self.current_user, profile,
                    assigned_badges=assigned_badges, summary=summary, leaderboard=leaderboard,
                    cycle_row=(_cyc_rows[0] if _cyc_rows else None),
                    cycle_name=getattr(selected_cycle_obj, "name", "") or ""
                )

            elif self.current_view == "c_announcements":
                page_title = "Academy Announcement Center"
                main_content_html = render_cosmonaut_announcements(store.get_announcements_for_cosmonaut(self.current_user.id), self.current_user.id)

            elif self.current_view == "c_extensions":
                page_title = "Deadline Extension Requests"
                user_exts = store.get_extensions_for_cosmonaut(self.current_user.id)
                approved_asms = store.get_assessments_for_cosmonaut(self.current_user.id)
                completed_ids = {a.badge_id for a in approved_asms if a.decision == "approve"}
                main_content_html = render_cosmonaut_extensions(
                    assigned_badges=assigned_badges,
                    extensions=user_exts,
                    badges_map=badges_map,
                    completed_badge_ids=completed_ids
                )

            elif self.current_view == "c_activity":
                page_title = "Personal Training Activity Stream"
                user_acts = store.get_activities(self.current_user.id)
                main_content_html = render_cosmonaut_activity_stream(user_acts)

            elif self.current_view == "c_requests":
                page_title = "Badge Review Requests Queue"
                main_content_html = render_cosmonaut_review_requests(
                    requests=cosmo_reqs,
                    current_user=self.current_user,
                    active_tab=getattr(self, "cosmo_requests_tab", "all"),
                    search_query=getattr(self, "cosmo_requests_search", "")
                )

            elif self.current_view == "c_badge_review":
                page_title = "Badge Review"
                _rb = store.get_badge(self.reviewer_review_badge_id)
                main_content_html = render_reviewer_badge_review(
                    badge=_rb,
                    current_user=self.current_user,
                    request_row=next((r for r in cosmo_reqs if r.get("id") == _rb.id), {}),
                    can_edit=self._badge_review_edit_denied(_rb) is None,
                    is_editing=self.reviewer_review_editing and self._badge_review_edit_denied(_rb) is None,
                )

            elif self.current_view == "c_badge_reviews":
                page_title = "My Badge Review Schedule"
                main_content_html = render_reviewer_badge_schedule(
                    current_user=self.current_user,
                    store=store,
                    badges_map=badges_map,
                    cosmo_map=cosmo_map,
                    expanded_badge_id=getattr(self, "reviewer_expanded_badge_id", None)
                )

            elif self.current_view == "c_assessment_detail":
                page_title = "Cadet Deliverable Evaluation & Rubric Scoring"
                sub_id = getattr(self, "selected_reviewer_sub_id", "") or getattr(self, "reviewer_selected_submission_id", "")
                sub = store.get_submission(sub_id) if sub_id else None
                if sub:
                    is_guardian = (getattr(self.current_user, "role", "") == "guardian" or "guardian" in getattr(self.current_user, "roles", []))
                    tl = store.get_timeline(sub.badge_id, sub.cosmonaut_id)
                    is_assigned = (tl and getattr(tl, "reviewer_id", "") == self.current_user.id)
                    if not is_assigned:
                        badge = store.get_badge(sub.badge_id)
                        if badge and getattr(badge, "assigned_reviewer_id", "") == self.current_user.id and sub.cosmonaut_id in getattr(badge, "assigned_cosmonaut_ids", []):
                            is_assigned = True
                    if not is_assigned:
                        for m in store.get_band_mappings():
                            if self.current_user.id in m.get("reviewers", []) and sub.cosmonaut_id in m.get("cosmonauts", []):
                                m_b = m.get("badge_id") or m.get("badge")
                                badge = store.get_badge(sub.badge_id)
                                if (m_b == sub.badge_id) or (badge and m_b in (badge.title, badge.code, badge.id)):
                                    is_assigned = True
                                    break
                    if not (is_assigned or is_guardian):
                        main_content_html = "<div class='liquid-glass-card' style='padding:40px; text-align:center;'><h3 style='color:#DC2626;'>Unauthorized Access</h3><p style='color:var(--frost-navy-50); margin-top:8px;'>You are not authorized or assigned to evaluate this cadet deliverable.</p><button onclick=\"window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_badge_reviews')\" class='btn-secondary' style='margin-top:14px;'>Back to Badge Reviews</button></div>"
                    else:
                        cadet = cosmo_map.get(sub.cosmonaut_id) or store.get_user_by_id(sub.cosmonaut_id) or store.get_cosmonaut(sub.cosmonaut_id)
                        badge = badges_map.get(sub.badge_id) or store.get_badge(sub.badge_id)
                        existing_asms = store.get_assessments_for_cosmonaut(sub.cosmonaut_id)
                        sub_asms = [a for a in existing_asms if getattr(a, "submission_id", "") == sub.id and getattr(a, "assessor_role", "") == "reviewer"]
                        existing_asm = sub_asms[0] if sub_asms else None
                        main_content_html = render_reviewer_assessment_detail(
                            submission=sub,
                            badge=badge,
                            cosmonaut=cadet,
                            existing_reviewer_asm=existing_asm,
                            previous_assessments=[a for a in existing_asms if getattr(a, "submission_id", "") == sub.id and getattr(a, "assessor_role", "") != "reviewer"],
                            selected_tab=getattr(self, "selected_viewer_tab", "pdf")
                        )
                else:
                    main_content_html = "<div class='liquid-glass-card' style='padding:40px; text-align:center;'>Deliverable not found. <button onclick=\"window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_badge_reviews')\" class='btn-secondary'>Back to Badge Reviews</button></div>"

        modal_html = iconize_html(self.render_active_modal())
        main_content_html = iconize_html(main_content_html)
        if not is_guardian_view:
            # Cosmonaut portal terminology: the people we call "cadets" elsewhere are "Cosmonauts" here.
            sidebar_html = cosmonaut_terms(sidebar_html)
            main_content_html = cosmonaut_terms(main_content_html)
            modal_html = cosmonaut_terms(modal_html)
            page_title = cosmonaut_terms(page_title)

        flash_html = ""
        if self.flash_message:
            flash_border = "var(--deep-frozen-midnight)" if self.flash_type == "success" else "var(--frost-navy)"
            flash_html = f"""
            <div style="margin-bottom:16px; padding:12px 18px; border-radius:var(--radius-md); background:rgba(234,244,255,0.9); border:1px solid {flash_border}; border-left:5px solid {flash_border}; font-size:0.84375rem; font-weight:600; color:var(--frost-navy); display:flex; justify-content:space-between; align-items:center;">
                <span>{escape(cosmonaut_terms(self.flash_message) if not is_guardian_view else self.flash_message)}</span>
                <span style="cursor:pointer; font-size:1.125rem;" onclick="this.parentElement.remove();">&times;</span>
            </div>
            """
            self.flash_message = None  # Consume flash

        page_container_cls = "page-container page-review-detail" if self.current_view in ("g_review_detail", "c_assessment_detail") else "page-container"
        strip_title = ""
        if self.current_view in TITLE_HOIST_VIEWS:
            main_content_html, strip_title = hoist_page_title(main_content_html)
        topbar_html = render_global_back_bar(strip_title)

        full_html = f"""
        {sidebar_html}
        <div id="starapp-main-viewport" class="app-main">
            <div id="starapp-topbar-slot">{topbar_html}</div>
            <main id="starapp-page-slot" class="{page_container_cls}">
                <div id="starapp-flash-slot">{flash_html}</div>
                <div id="starapp-page-body">{main_content_html}</div>
            </main>
        </div>
        <div id="starapp-modal-root">{modal_html}</div>
        """

        modal_key = ""
        if self.active_modal:
            try:
                modal_key = f"{self.active_modal}:{json.dumps(self.modal_payload, sort_keys=True)}"
            except Exception:
                modal_key = str(self.active_modal)

        portal_key = f"{self.current_user.role}:{self.current_user.id}:{self.current_user.name}:{getattr(self.current_user, 'avatar', '')}"
        self._dispatch_browser_render(
            {
                "mode": "workspace",
                "generation": self.render_generation,
                "isCrossTabReload": render_source == "cross_tab_reload",
                "portalKey": portal_key,
                "routeKey": route_key,
                "activeNavId": active_nav_id,
                "pageTitle": page_title,
                "sidebarBadges": sidebar_badges,
                "sidebarHtml": sidebar_html,
                "topbarHtml": topbar_html,
                "pageContainerClass": page_container_cls,
                "flashHtml": flash_html,
                "mainContentHtml": main_content_html,
                "activeModal": self.active_modal or "",
                "modalKey": modal_key,
                "modalHtml": modal_html,
            },
            full_html,
        )

        return full_html

# Global controller instance
controller = StarAppController()

