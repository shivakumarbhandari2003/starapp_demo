"""
STARAPP CORE APPLICATION CONTROLLER & ROUTER
Orchestrates role-based navigation, state mutation, event dispatch, and UI rendering.
Works seamlessly in browser Pyodide runtime and in local Python test suites.
"""

import json
import time
from typing import Optional, Dict, Any, Tuple
from starapp.models import (
    User, Badge, BadgeTimeline, ProjectSubmission, AssessmentMarksheet,
    LearningMaterial, DeadlineExtension, Announcement, ReviewerProjectPrompt, current_iso_timestamp
)
from starapp.storage import store
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
    get_icon,
    render_topbar, render_liquid_card, render_metal_button, escape,
    render_status_pill, render_standard_marksheet, render_9point_timeline
)
from starapp.views_guardian import (
    render_guardian_sidebar, render_guardian_dashboard,
    render_guardian_badge_allotment, render_guardian_mapping, render_guardian_review_queue,
    render_guardian_review_detail,
    render_assessment_modal_content, render_guardian_materials,
    render_guardian_activity_feed, render_guardian_extensions,
    render_guardian_announcements,
    render_guardian_create_badge, render_guardian_badge_approval_queue,
    render_badge_creation_preview_modal, render_badge_review_inspect_modal,
    render_badge_reviewer_edit_modal, render_badge_approval_confirm_modal,
    render_badge_return_confirm_modal
)
from starapp.mapping_data import (
    get_higher_bands, filter_members_by_band_and_roles, filter_reviewers_by_band_and_roles,
    get_consecutive_review_days, parse_iso_date
)
from starapp.views_cosmonaut import (
    render_cosmonaut_sidebar, render_cosmonaut_dashboard,
    render_cosmonaut_profile, render_gamified_roadmap,
    render_badge_detail_modal_content, render_cosmonaut_submission_workspace,
    render_cosmonaut_badge_detail_page, render_cosmonaut_allocated_project_modal,
    render_cosmonaut_submission_modal,
    render_cosmonaut_badge_preview_modal,
    render_cosmonaut_results, render_cosmonaut_materials,
    render_cosmonaut_extensions, render_cosmonaut_announcements,
    render_cosmonaut_activity_stream, render_cosmonaut_review_requests,
    render_reviewer_assessment_queue, render_reviewer_assessment_detail,
    render_reviewer_badge_schedule,
    render_reviewer_badge_timeline_modal,
    render_reviewer_project_creator_modal
)

# Pyodide browser bridge detection
try:
    import js
    IS_BROWSER = hasattr(js, "document")
except ImportError:
    js = None
    IS_BROWSER = False

class StarAppController:
    def __init__(self):
        self.current_user: Optional[User] = None
        self.current_view: str = "login"
        self.selected_guardian_cosmo_id: str = "all"
        self.guardian_review_filter: str = "all"
        self.guardian_allotment_filter: str = "all"
        self.selected_review_sub_id: Optional[str] = None
        self.selected_viewer_tab: str = "pdf"
        self.cosmonaut_submission_badge_id: str = "badge_cur_102"
        self.cosmonaut_expanded_badge_id: Optional[str] = None
        self.reviewer_expanded_badge_id: Optional[str] = None
        self.cosmonaut_results_badge_id: str = "badge_gov_101"
        self.materials_badge_filter: str = "all"
        self.materials_type_filter: str = "all"
        self.active_modal: Optional[str] = None
        self.modal_payload: Dict[str, Any] = {}
        self.flash_message: Optional[str] = None
        self.last_flash_message: Optional[str] = None
        self.flash_type: str = "info"
        self.render_generation: int = 0
        self._last_render_source: str = "init"
        self.view_history: list = []

        # Mapping workspace state
        self.mapping_selected_band: str = "B1"
        self.mapping_selected_roles: list = ["Solutions Designer", "AI Engineer", "Systems Engineer"]
        self.mapping_selected_badge: str = ""
        self.mapping_selected_badge_id: str = ""
        self.mapping_selected_cosmonauts: list = ["m_b1_1", "m_b1_2"]
        self.mapping_selected_reviewer_bands: list = ["B2"]
        self.mapping_selected_reviewer_band: str = "B2"
        self.mapping_selected_reviewers: list = ["m_b2_1"]
        self.mapping_cosmo_search: str = ""
        self.mapping_reviewer_search: str = ""
        self.mapping_badge_search: str = ""
        self.mapping_calendar_year: int = 2026
        self.mapping_calendar_month: int = 11
        self.mapping_review_anchor: str = "2026-11-18"
        self.mapping_review_direction: str = "after"
        self.mapping_review_dates: list = ["2026-11-18", "2026-11-19", "2026-11-20"]
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

    # Valid view ids per role to prevent arbitrary injection
    _GUARDIAN_VIEWS = {
        "g_create_badge", "g_badge_approval",
        "g_dashboard", "g_roadmap", "g_cosmonauts", "g_allotment", "g_badge_allotment", "g_mapping", "g_reviews", "g_review_detail",
        "g_materials", "g_extensions", "g_announcements", "g_activity"
    }
    _COSMONAUT_VIEWS = {
        "c_dashboard", "c_roadmap", "c_submission", "c_badge_detail", "c_results",
        "c_materials", "c_profile", "c_announcements", "c_extensions", "c_activity",
        "c_requests", "c_badge_reviews"
    }

    def initialize(self, stored_json: Optional[str] = None, session_json: Optional[str] = None, sqlite_b64: Optional[str] = None):
        """Loads data from storage and restores previous user session including the exact page."""
        store.load_from_json(stored_json, sqlite_b64)

        # Restore session — including the exact page the user was on
        if session_json and session_json.strip():
            try:
                session_data = json.loads(session_json)
                user_id = session_data.get("user_id")
                saved_view = session_data.get("current_view", "")
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
                            self.current_view = "g_dashboard" if is_guardian_user else "c_dashboard"
            except Exception as e:
                print(f"[Controller] Session restore error: {e}")

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
            "current_view": self.current_view
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
            store.load_from_json(stored_json, sqlite_b64)
            if self.current_user:
                updated_user = store.get_user_by_id(self.current_user.id)
                if updated_user:
                    self.current_user = updated_user
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
            "submission_badge_id": self.cosmonaut_submission_badge_id
        }
        if not self.view_history or self.view_history[-1]["view"] != self.current_view or self.view_history[-1].get("band") != self.create_badge_band:
            self.view_history.append(entry)
        if len(self.view_history) > 30:
            self.view_history.pop(0)

    def resolve_mapping_badge(self, store, band: str = None) -> Tuple[str, str, str]:
        """
        Returns (badge_id, badge_title, badge_code) for the currently selected mapping badge
        scoped strictly to the given or active band.
        """
        target_band = band or (self.create_badge_band if getattr(self, "create_badge_band", None) else self.mapping_selected_band)
        b_id = getattr(self, "mapping_selected_badge_id", "")
        b_ref = getattr(self, "mapping_selected_badge", "")

        # 1. If b_ref is specified, prioritize matching b_ref
        if b_ref:
            if store.db and store.db.conn:
                try:
                    row = store.db.conn.execute(
                        "SELECT id, title, code, target_band FROM badges WHERE (title = ? OR code = ? OR id = ?) AND (target_band = ? OR ? = '')",
                        (b_ref, b_ref, b_ref, target_band, target_band)
                    ).fetchone()
                    if row:
                        return row["id"], row["title"], row["code"]
                except Exception:
                    pass

            for b in store.get_all_badges():
                if not target_band or getattr(b, "target_band", "") == target_band:
                    if b.title == b_ref or b.code == b_ref or b.id == b_ref:
                        return b.id, b.title, b.code

            return b_id or "", b_ref, b_ref

        # 2. If b_id is specified
        if b_id:
            if store.db and store.db.conn:
                try:
                    row = store.db.conn.execute(
                        "SELECT id, title, code, target_band FROM badges WHERE id = ? AND (target_band = ? OR ? = '')",
                        (b_id, target_band, target_band)
                    ).fetchone()
                    if row:
                        return row["id"], row["title"], row["code"]
                except Exception:
                    pass

            for b in store.get_all_badges():
                if not target_band or getattr(b, "target_band", "") == target_band:
                    if b.id == b_id:
                        return b.id, b.title, b.code

            return b_id, b_ref or "Badge", b_ref or "BDG"

        # 3. Fallback to first available approved badge in this band ONLY if neither b_ref nor b_id is provided
        if store.db and store.db.conn:
            try:
                row = store.db.conn.execute(
                    "SELECT id, title, code FROM badges WHERE target_band = ? AND workflow_status IN ('approved', 'ready_for_review') LIMIT 1",
                    (target_band,)
                ).fetchone()
                if row:
                    return row["id"], row["title"], row["code"]
            except Exception:
                pass

        return "", "Badge", "BDG"

    # ==========================================================================
    # ACTION & EVENT HANDLER
    # ==========================================================================

    def handle_event(self, action: str, payload_json: str = "{}"):
        import time
        if isinstance(payload_json, str) and payload_json.startswith("{") and action != "update_badge_prompt":
            try:
                payload = json.loads(payload_json)
            except Exception:
                payload = payload_json
        else:
            payload = payload_json

        # --- Authentication Actions ---
        if action == "login":
            self.view_history = []
            username = str(payload.get("username", "")).strip().lower()
            user = store.get_user_by_username(username)
            if user:
                self.current_user = user
                if user.role == "guardian" or user.has_role("guardian"):
                    self.current_view = "g_create_badge"
                    self.create_badge_band = None
                else:
                    self.current_view = "c_dashboard"
                self.set_flash(f"Welcome back, {user.name}!", "success")
            else:
                self.set_flash("Invalid demo username. Please choose from the demo credentials below.", "error")

        elif action == "select_demo_account":
            self.view_history = []
            self.reviewer_expanded_badge_id = None
            user_id = payload.get("user_id") if isinstance(payload, dict) else payload
            user = store.get_user_by_id(user_id)
            if user:
                self.current_user = user
                user_roles = getattr(user, "roles", [user.role])
                is_guardian_user = (user.id in ("guardian_1", "admin") or user.role in ("guardian", "admin") or "guardian" in user_roles or "admin" in user_roles)
                if is_guardian_user:
                    self.current_view = "g_dashboard"
                else:
                    self.current_view = "c_dashboard"
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
                if "title" in payload and payload["title"]:
                    self.created_badge_data["title"] = payload["title"].strip()
                if "description" in payload:
                    self.created_badge_data["description"] = payload["description"].strip()
                if "outcomes" in payload:
                    if isinstance(payload["outcomes"], list):
                        self.created_badge_data["outcomes"] = payload["outcomes"]
                    elif isinstance(payload["outcomes"], str):
                        self.created_badge_data["outcomes"] = [o.strip() for o in payload["outcomes"].split("\n") if o.strip()]
                if "practice_prompt" in payload:
                    if "practice_project" not in self.created_badge_data or not isinstance(self.created_badge_data["practice_project"], dict):
                        self.created_badge_data["practice_project"] = {
                            "intro": "Want some hands-on practice? Use this prompt to generate a practice project.",
                            "prompt": payload["practice_prompt"],
                            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
                        }
                    else:
                        self.created_badge_data["practice_project"]["prompt"] = payload["practice_prompt"]
                    self.created_badge_data["practice_prompt"] = payload["practice_prompt"]

                if "resources_prompt" in payload:
                    if "learning_resources" not in self.created_badge_data or not isinstance(self.created_badge_data["learning_resources"], dict):
                        self.created_badge_data["learning_resources"] = {
                            "intro": "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
                            "prompt": payload["resources_prompt"],
                            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
                        }
                    else:
                        self.created_badge_data["learning_resources"]["prompt"] = payload["resources_prompt"]
                    self.created_badge_data["resources_prompt"] = payload["resources_prompt"]
                if "topics" in payload and isinstance(payload["topics"], list):
                    self.created_badge_data["learning_topics"] = payload["topics"]
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
                draft = self.modal_payload if self.modal_payload else self.create_badge_metadata
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
                outcomes = [o.strip() for o in raw_outcomes.replace("\n", ",").split(",") if o.strip()]
                raw_topics = draft.get("learning_topics", "")
                topics = [t.strip() for t in raw_topics.replace("\n", ",").split(",") if t.strip()]

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

        elif action == "filter_badge_approval_band":
            band = payload if isinstance(payload, str) else payload.get("band", "all")
            self.badge_approval_band_filter = band

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
                else:
                    self.set_flash(msg, "error")

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
            self.view_history = []
            self.set_flash("You have been signed out.", "info")

        elif action == "reset_demo_data":
            store.reset_to_seed()
            self.active_modal = None
            self.view_history = []
            self.set_flash("StarApp demo data has been restored to factory default.", "success")

        # --- Navigation Actions ---
        elif action == "go_back":
            if self.active_modal:
                self.active_modal = None
                self.modal_payload = {}
            elif self.current_view == "g_create_badge" and self.create_badge_band:
                self.create_badge_band = None
            elif hasattr(self, "view_history") and self.view_history:
                prev_entry = self.view_history.pop()
                while self.view_history and prev_entry.get("view") == self.current_view and prev_entry.get("band") == self.create_badge_band:
                    prev_entry = self.view_history.pop()

                prev_view = prev_entry.get("view", "")
                if prev_view and prev_view != self.current_view:
                    self.current_view = prev_view
                    self.create_badge_band = prev_entry.get("band")
                elif self.current_view == "g_create_badge":
                    self.create_badge_band = None
                else:
                    is_guard = (self.current_user and (self.current_user.id == "guardian_1" or self.current_user.role == "guardian" or self.current_user.has_role("guardian")))
                    self.current_view = "g_dashboard" if is_guard else "c_dashboard"
            else:
                if self.current_view == "g_create_badge" and self.create_badge_band:
                    self.create_badge_band = None
                else:
                    is_guard = (self.current_user and (self.current_user.id == "guardian_1" or self.current_user.role == "guardian" or self.current_user.has_role("guardian")))
                    if is_guard and self.current_view != "g_dashboard":
                        self.current_view = "g_dashboard"
                    elif is_guard:
                        self.current_view = "g_create_badge"
                        self.create_badge_band = None
                    elif not is_guard and self.current_view != "c_dashboard":
                        self.current_view = "c_dashboard"

        elif action == "nav_guardian":
            self._push_history()
            view_id = payload if isinstance(payload, str) else payload.get("view_id")
            self.current_view = view_id
            self.active_modal = None
            if view_id == "g_badge_approval" and getattr(self, "create_badge_band", None):
                self.badge_approval_band_filter = self.create_badge_band
            elif view_id == "g_mapping" and getattr(self, "create_badge_band", None):
                self.mapping_selected_band = self.create_badge_band

        elif action == "nav_cosmonaut":
            self._push_history()
            view_id = payload if isinstance(payload, str) else payload.get("view_id")
            self.current_view = view_id
            if view_id == "c_submission":
                self.cosmonaut_expanded_badge_id = None
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
            members = filter_members_by_band_and_roles(self.mapping_selected_band, self.mapping_selected_roles, getattr(self, "mapping_cosmo_search", ""))
            self.mapping_selected_cosmonauts = [m["id"] for m in members]

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
            r_bands = getattr(self, "mapping_selected_reviewer_bands", [self.mapping_selected_reviewer_band])
            reviewers = filter_reviewers_by_band_and_roles(r_bands, self.mapping_selected_roles, getattr(self, "mapping_reviewer_search", ""))
            current_set = set(self.mapping_selected_reviewers)
            for r in reviewers:
                current_set.add(r["id"])
            self.mapping_selected_reviewers = list(current_set)

        elif action == "clear_mapping_reviewers":
            self.mapping_selected_reviewers = []

        elif action in ("toggle_mapping_final_stage", "show_mapping_final_stage"):
            self.mapping_show_final_stage = not getattr(self, "mapping_show_final_stage", False)

        elif action == "reset_mapping_selection":
            self.editing_mapping_id = None
            self.mapping_selected_band = "B1"
            from starapp.mapping_data import ROLES
            self.mapping_selected_roles = list(ROLES)
            self.mapping_selected_badge = ""
            self.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2"]
            self.mapping_selected_reviewer_band = "B2"
            self.mapping_selected_reviewers = ["m_b2_1"]
            self.mapping_cosmo_search = ""
            self.mapping_reviewer_search = ""
            self.mapping_badge_search = ""
            self.mapping_calendar_year = 2026
            self.mapping_calendar_month = 11
            self.mapping_review_anchor = "2026-11-18"
            self.mapping_review_direction = "after"
            self.mapping_review_dates = ["2026-11-18", "2026-11-19", "2026-11-20"]
            self.set_flash("Mapping configuration reset to default baseline.", "info")

        elif action == "select_mapping_review_anchor":
            date_iso = payload if isinstance(payload, str) else (payload.get("date") if isinstance(payload, dict) else "")
            if date_iso:
                self.mapping_review_anchor = date_iso
                self.mapping_review_dates = get_consecutive_review_days(date_iso, self.mapping_review_direction, 3)

        elif action == "set_mapping_review_direction":
            direction = payload if isinstance(payload, str) else (payload.get("direction", "after") if isinstance(payload, dict) else "after")
            self.mapping_review_direction = direction
            self.mapping_review_dates = get_consecutive_review_days(self.mapping_review_anchor, direction, 3)

        elif action == "change_mapping_calendar_month":
            if isinstance(payload, dict):
                self.mapping_calendar_year = int(payload.get("year", self.mapping_calendar_year))
                self.mapping_calendar_month = int(payload.get("month", self.mapping_calendar_month))
            elif isinstance(payload, str) and payload.strip():
                try:
                    p = json.loads(payload)
                    self.mapping_calendar_year = int(p.get("year", self.mapping_calendar_year))
                    self.mapping_calendar_month = int(p.get("month", self.mapping_calendar_month))
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

            # Locate badge in SQLite and update badge_timelines & publishing status
            matched_badge_id = None
            matched_badge_title = self.mapping_selected_badge
            if store.db and store.db.conn:
                try:
                    b_row = store.db.conn.execute(
                        "SELECT id, title FROM badges WHERE (title = ? OR code = ? OR id = ?) AND target_band = ?",
                        (self.mapping_selected_badge, self.mapping_selected_badge, self.mapping_selected_badge, self.mapping_selected_band)
                    ).fetchone()
                    if b_row:
                        matched_badge_id = b_row["id"]
                        matched_badge_title = b_row["title"]
                    elif not self.mapping_selected_badge:
                        fallback_row = store.db.conn.execute(
                            "SELECT id, title FROM badges WHERE target_band = ? AND workflow_status IN ('approved', 'ready_for_review') LIMIT 1",
                            (self.mapping_selected_band,)
                        ).fetchone()
                        if fallback_row:
                            matched_badge_id = fallback_row["id"]
                            matched_badge_title = fallback_row["title"]
                            self.mapping_selected_badge = matched_badge_title
                except Exception:
                    pass
            if not matched_badge_id:
                for b in store.badges.values():
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
            import time
            effective_band = self.create_badge_band if getattr(self, "create_badge_band", None) else self.mapping_selected_band
            b_id, b_title, b_code = self.resolve_mapping_badge(store, effective_band)
            if not b_id and not b_title:
                self.set_flash("Please select a valid badge before sending requests.", "warning")
            elif not self.mapping_selected_cosmonauts:
                self.set_flash("Please select at least 1 cosmonaut before sending requests.", "warning")
            elif not self.mapping_selected_reviewers:
                self.set_flash("Please select at least 1 reviewer before sending requests.", "warning")
            else:
                created_count = 0
                for r_id in self.mapping_selected_reviewers:
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
                        "cosmonaut_ids": list(self.mapping_selected_cosmonauts),
                        "review_dates": list(self.mapping_review_dates),
                        "status": "pending",
                        "sent_at": current_iso_timestamp()
                    }
                    store.add_mapping_request(new_req)
                    store.add_notification(
                        r_id,
                        f"Review Request: Guardian has requested your evaluation for {b_title} (Band {effective_band})",
                        "request",
                        link_section="c_requests"
                    )
                    created_count += 1
                self.mapping_show_final_stage = True
                self.set_flash(f"Sent review request for '{b_title}' to {created_count} reviewer(s). This mapping request is independent — you can also send requests for other badges while awaiting reviewer confirmation.", "success")

        elif action == "save_allotment_timeline":
            data = payload if isinstance(payload, dict) else {}
            if isinstance(payload, str):
                try:
                    data = json.loads(payload)
                except Exception:
                    data = {}
            badge_id = data.get("badge_id", "")
            if badge_id:
                b_obj = store.get_badge(badge_id)
                if b_obj:
                    if not b_obj.default_timeline:
                        b_obj.default_timeline = {}
                    for k in ["learning_start_date", "learning_end_date", "project_start_date", "project_end_date", "submission_deadline", "review_date", "expected_award_date"]:
                        if k in data and data[k]:
                            b_obj.default_timeline[k] = data[k]
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
                            WHERE badge_id = ?
                        """, (
                            data.get("learning_start_date") or None,
                            data.get("learning_end_date") or None,
                            data.get("project_start_date") or None,
                            data.get("project_end_date") or None,
                            data.get("submission_deadline") or None,
                            data.get("review_date") or None,
                            data.get("expected_award_date") or None,
                            badge_id
                        ))
                        store.db.conn.commit()
                    except Exception:
                        pass
                for tl in store.timelines.values():
                    if tl.badge_id == badge_id:
                        for k in ["learning_start_date", "learning_end_date", "project_start_date", "project_end_date", "submission_deadline", "review_date", "expected_award_date"]:
                            if k in data and data[k]:
                                setattr(tl, k, data[k])
                store.mark_dirty()
                self.set_flash("Timeline schedule configured and saved successfully!", "success")
            else:
                self.set_flash("Badge ID missing for timeline save.", "warning")

        elif action == "accept_mapping_request":
            req_id = payload.strip().replace('"', '') if isinstance(payload, str) else (payload.get("request_id") if isinstance(payload, dict) else "")
            if req_id:
                store.update_mapping_request_status(req_id, "accepted")
                self.set_flash("Review request accepted. Reviewer confirmed for milestone mapping.", "success")

        elif action == "reject_mapping_request":
            req_id = payload.strip().replace('"', '') if isinstance(payload, str) else (payload.get("request_id") if isinstance(payload, dict) else "")
            if req_id:
                store.update_mapping_request_status(req_id, "rejected")
                self.set_flash("Review request declined / rejected.", "info")

        elif action == "delete_mapping_request":
            req_id = payload.strip().replace('"', '') if isinstance(payload, str) else (payload.get("request_id") if isinstance(payload, dict) else "")
            if req_id:
                store.delete_mapping_request(req_id)
                self.set_flash("Review request removed.", "info")

        elif action == "execute_cosmonaut_mapping":
            import time
            effective_band = self.create_badge_band if getattr(self, "create_badge_band", None) else self.mapping_selected_band
            b_id, b_title, b_code = self.resolve_mapping_badge(store, effective_band)
            requests = store.get_mapping_requests()
            # Filter accepted requests specifically for THIS badge
            accepted_reqs = [
                r for r in requests
                if r.get("band") == effective_band
                and r.get("status") == "accepted"
                and (
                    (b_id and r.get("badge_id") == b_id)
                    or r.get("badge") in (b_title, b_code, b_id)
                    or (b_title and b_title in r.get("badge", ""))
                )
            ]
            if not accepted_reqs:
                # Fallback to any accepted request for this band only if no badge-specific match
                accepted_reqs = [r for r in requests if r.get("band") == effective_band and r.get("status") == "accepted"]

            if not accepted_reqs:
                self.set_flash(f"No accepted reviewers available for '{b_title}'. Please ensure reviewers accept requests for this badge first.", "warning")
            elif not self.mapping_selected_cosmonauts:
                self.set_flash("No cosmonauts selected for mapping. Please select cosmonauts above.", "warning")
            else:
                matched_badge_id = b_id
                matched_badge_title = b_title

                # 1. Remove ONLY previous mapping for this specific badge (do NOT delete other badges!)
                store.band_mappings = [
                    m for m in store.band_mappings
                    if not (
                        m.get("band") == effective_band
                        and (
                            (matched_badge_id and m.get("badge_id") == matched_badge_id)
                            or m.get("badge") in (matched_badge_title, b_code, matched_badge_id)
                        )
                    )
                ]
                if store.db and store.db.conn:
                    try:
                        store.db.conn.execute(
                            "DELETE FROM band_mappings WHERE band = ? AND (badge_id = ? OR json_extract(data_json, '$.badge_id') = ? OR json_extract(data_json, '$.badge') = ?)",
                            (effective_band, matched_badge_id or "", matched_badge_id or "", matched_badge_title)
                        )
                    except Exception:
                        pass

                # 2. Distribute selected cosmonauts equally among accepted guardians
                num_guardians = len(accepted_reqs)
                guardian_buckets = {r["reviewer_id"]: [] for r in accepted_reqs}
                
                for idx, c_id in enumerate(self.mapping_selected_cosmonauts):
                    target_g = accepted_reqs[idx % num_guardians]
                    guardian_buckets[target_g["reviewer_id"]].append(c_id)

                created_mappings = 0
                for req in accepted_reqs:
                    g_id = req["reviewer_id"]
                    assigned = guardian_buckets.get(g_id, [])
                    if not assigned:
                        continue
                    mapping_record = {
                        "id": f"map_{effective_band}_{matched_badge_id}_{g_id}_{int(time.time() * 1000)}_{created_mappings}",
                        "band": self.mapping_selected_band,
                        "badge": matched_badge_title,
                        "badge_id": matched_badge_id or "",
                        "badge_code": b_code or "",
                        "roles": list(self.mapping_selected_roles),
                        "cosmonauts": assigned,
                        "reviewer_band": req.get("reviewer_band", self.mapping_selected_reviewer_band),
                        "reviewers": [g_id],
                        "review_dates": list(self.mapping_review_dates),
                        "created_at": current_iso_timestamp(),
                        "status": "active"
                    }
                    store.save_band_mapping(mapping_record)
                    created_mappings += 1

                if matched_badge_id:
                    r_dates = list(self.mapping_review_dates)
                    start_d = r_dates[0] if r_dates else current_iso_timestamp()[:10]
                    end_d = r_dates[-1] if r_dates else current_iso_timestamp()[:10]
                    for idx, c_id in enumerate(self.mapping_selected_cosmonauts):
                        target_g = accepted_reqs[idx % num_guardians]
                        assigned_rev = target_g["reviewer_id"]
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

                    b_obj = store.get_badge(matched_badge_id)
                    if b_obj:
                        b_obj.is_allocated = True
                        if not hasattr(b_obj, "is_published") or b_obj.is_published is None:
                            b_obj.is_published = False
                        for c_id in self.mapping_selected_cosmonauts:
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
                            "review_dates": list(self.mapping_review_dates)
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

                mapped_badge_title = matched_badge_title
                mapped_cosmo_count = len(self.mapping_selected_cosmonauts)
                mapped_guardian_count = len(accepted_reqs)
                mapped_review_dates = list(self.mapping_review_dates)

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
                    summary=f"Equally Mapped {mapped_cosmo_count} Cosmonauts across {mapped_guardian_count} Accepted Reviewers for '{mapped_badge_title}' ({self.mapping_selected_band})",
                    details=f"Badge: {mapped_badge_title} &bull; Review Dates: {', '.join(mapped_review_dates)} &bull; Saved to Badge & SQLite"
                )
                self.set_flash(f"Successfully saved '{mapped_badge_title}' mapping! Badge updated with mapped reviewers, cosmonauts, and timeline schedule. Mapping page reset & ready for timeline publishing in Badge Allotment.", "success")

        elif action == "clear_band_mappings":
            band = payload.strip().replace('"', '') if isinstance(payload, str) else (payload.get("band", self.mapping_selected_band) if isinstance(payload, dict) else self.mapping_selected_band)
            badge_ref = payload.get("badge") if isinstance(payload, dict) else None
            if badge_ref:
                store.band_mappings = [m for m in store.band_mappings if not (m.get("band") == band and m.get("badge") == badge_ref)]
                if store.db and store.db.conn:
                    try:
                        store.db.conn.execute("DELETE FROM band_mappings WHERE band = ? AND (badge_id = ? OR json_extract(data_json, '$.badge') = ?)", (band, badge_ref, badge_ref))
                        store.db.conn.commit()
                    except Exception:
                        pass
                self.set_flash(f"Active mappings for '{badge_ref}' (Band {band}) cleared.", "info")
            else:
                store.band_mappings = [m for m in store.band_mappings if m.get("band") != band]
                if store.db and store.db.conn:
                    try:
                        store.db.conn.execute("DELETE FROM band_mappings WHERE band = ?", (band,))
                        store.db.conn.commit()
                    except Exception:
                        pass
                self.set_flash(f"Active mappings for Band {band} cleared.", "info")
            store.mark_dirty()

        elif action in ("reset_all_mapping_state", "reset_mapping_demo"):
            store.band_mappings = []
            store.mapping_requests = []
            if store.db and store.db.conn:
                try:
                    store.db.conn.execute("DELETE FROM band_mappings")
                    store.db.conn.execute("DELETE FROM mapping_requests")
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
            self.mapping_calendar_year = 2026
            self.mapping_calendar_month = 11
            self.mapping_review_anchor = "2026-11-18"
            self.mapping_review_dates = ["2026-11-18", "2026-11-19", "2026-11-20"]
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

        elif action == "revoke_badge":
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
            badge_id = payload.get("badge_id") if isinstance(payload, dict) else payload
            if isinstance(badge_id, str):
                badge_id = badge_id.strip().replace('"', '')
            badge = store.get_badge(badge_id)
            if not badge and store.db and store.db.conn:
                try:
                    row = store.db.conn.execute("SELECT * FROM badges WHERE id = ? OR code = ?", (badge_id, badge_id)).fetchone()
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
                            message=f"Milestone '{badge.title}' has been published and assigned to your review queue ({len(all_mapped_cids)} cadet(s)). 3-day project specification window is open.",
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
                            message=f"Milestone '{badge.title}' has been published and assigned to your review queue ({len(c_ids)} cadet(s)). 3-day project specification window is open.",
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

        elif action == "save_allotment_timeline":
            import json as _json
            data = payload if isinstance(payload, dict) else {}
            if isinstance(payload, str):
                try:
                    data = _json.loads(payload)
                except Exception:
                    data = {}
            badge_id = data.get("badge_id", "")
            if badge_id and store.db and store.db.conn:
                try:
                    store.db.conn.execute("""
                        UPDATE badge_timelines SET
                            learning_start_date = COALESCE(?, learning_start_date),
                            learning_end_date = COALESCE(?, learning_end_date),
                            project_start_date = COALESCE(?, project_start_date),
                            project_end_date = COALESCE(?, project_end_date),
                            submission_deadline = COALESCE(?, submission_deadline),
                            expected_award_date = COALESCE(?, expected_award_date)
                        WHERE badge_id = ?
                    """, (
                        data.get("learning_start") or None,
                        data.get("learning_end") or None,
                        data.get("project_start") or None,
                        data.get("project_end") or None,
                        data.get("deadline") or None,
                        data.get("award_date") or None,
                        badge_id
                    ))
                    store.db.conn.commit()
                    self.set_flash("Timeline saved successfully!", "success")
                except Exception as e:
                    self.set_flash(f"Error saving timeline: {e}", "error")
            else:
                self.set_flash("Badge ID missing or DB not available.", "warning")

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
            self.current_view = "c_assessments"

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
                    self.current_view = "c_assessments"
                    return
            self.selected_reviewer_sub_id = sub_id
            self.reviewer_selected_submission_id = sub_id
            self.selected_viewer_tab = "pdf"
            self.current_view = "c_assessment_detail"

        elif action == "open_submission_modal":
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            b_id = str(b_id).strip().replace('"', '') or getattr(self, "cosmonaut_submission_badge_id", "")
            self.cosmonaut_submission_badge_id = b_id
            self.active_modal = "submission_portal_modal"
            self.modal_payload = {"badge_id": b_id}

        elif action in ("open_allocated_project_modal", "view_allocated_project"):
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            b_id = str(b_id).strip().replace('"', '') or getattr(self, "cosmonaut_submission_badge_id", "")
            self.cosmonaut_submission_badge_id = b_id
            self.active_modal = "allocated_project_modal"
            self.modal_payload = {"badge_id": b_id}

        elif action == "filter_reviewer_assessments":
            self.reviewer_assessment_filter = payload if isinstance(payload, str) else "all"

        elif action == "open_reviewer_badge_timeline_modal":
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            self.active_modal = "reviewer_timeline_modal"
            self.modal_payload = {"badge_id": b_id}

        elif action == "open_create_reviewer_project_modal":
            b_id = payload if isinstance(payload, str) else (payload.get("badge_id", "") if isinstance(payload, dict) else "")
            self.active_modal = "reviewer_project_creator"
            self.modal_payload = {"badge_id": b_id}

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
            objective = payload.get("objective") or payload.get("scenario") or payload.get("description") or ""
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

            rev_id = (self.current_user.id if self.current_user else None) or payload.get("reviewer_id") or "reviewer_1"
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
                if hasattr(store, "timelines") and store.timelines:
                    for tl in store.timelines.values():
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

            prompt = ReviewerProjectPrompt(
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

            if status == "draft":
                self.set_flash(f"Project draft for '{title}' saved successfully.", "success")
            else:
                for cid in cosmonaut_ids:
                    store.add_notification(
                        recipient_id=cid,
                        title=f"🚀 New Project Assigned: {title}",
                        message=f"{rev_name} has assigned milestone project '{title}' for '{b_title}'. Review project details, outcomes & deliverables in your Badges portal.",
                        event_type="milestone",
                        link_section="c_submission"
                    )
                store.add_activity(
                    event_type="reviewer_project_assigned",
                    actor_id=rev_id,
                    actor_name=rev_name,
                    cosmonaut_id=cosmonaut_ids[0] if cosmonaut_ids else "",
                    badge_id=badge_id,
                    summary=f"Project Assigned: '{title}' by {rev_name}",
                    details=f"{rev_name} released project '{title}' to {len(cosmonaut_ids)} mapped cadets for {b_title}."
                )
                self.set_flash(f"Project '{title}' successfully submitted and assigned to {len(cosmonaut_ids)} mapped cadets!", "success")

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
                    bu = float(bu_el.value) if bu_el and bu_el.value else 9.0
                if ar is None:
                    ar_el = js.document.getElementById("rubric-ar")
                    ar = float(ar_el.value) if ar_el and ar_el.value else 9.0
                if tk is None:
                    tk_el = js.document.getElementById("rubric-tk")
                    tk = float(tk_el.value) if tk_el and tk_el.value else 9.0
                if pr is None:
                    pr_el = js.document.getElementById("rubric-pr")
                    pr = float(pr_el.value) if pr_el and pr_el.value else 9.0
                if qa is None:
                    qa_el = js.document.getElementById("rubric-qa")
                    qa = float(qa_el.value) if qa_el and qa_el.value else 9.0
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
                    decision = str(dec_el.value).strip() if dec_el and dec_el.value else "approve"

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
                is_guardian = "guardian" in user_roles
                if not (is_authorized_reviewer or is_guardian):
                    self.set_flash("Unauthorized: You are not assigned to evaluate this cadet's milestone project.", "error")
                    return

                asm_id = f"asm_rev_{sub.id}_{sub.attempt_number}"
                decision = "reviewer_assessed"
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
                    details=f"{self.current_user.name} graded Attempt #{sub.attempt_number}. Awaiting Guardian final marksheet."
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
                    message=f"{self.current_user.name} completed reviewer evaluation for {cosmo_name} on {b_name} ({marksheet.total_marks:.1f}/50). Awaiting final assessment.",
                    link_section="g_reviews"
                )

                self.set_flash(f"Reviewer assessment for {cosmo_name} saved successfully ({marksheet.total_marks:.1f}/50). Awaiting Guardian final assessment.", "success")

            else:  # guardian
                asm_id = f"asm_g_{sub.id}_{sub.attempt_number}"
                is_pass = pct >= badge_thresh
                if is_pass:
                    decision = "approve"
                    sub.status = "approved"
                else:
                    decision = "resubmission_requested"
                    sub.status = "retake_required"

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
                        summary=f"Retake Required: {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%) for {cosmo_name}",
                        details=f"Evaluated Attempt #{sub.attempt_number}. Score was below passing threshold of {badge_thresh:.1f}%. Resubmission requested."
                    )
                    store.add_notification(
                        recipient_id=sub.cosmonaut_id,
                        title=f"Retake Required: {b_name}",
                        message=f"Score for Attempt #{sub.attempt_number} was {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}% vs {badge_thresh}% passing threshold). Please review feedback and resubmit Attempt #{sub.attempt_number + 1}.",
                        link_section="c_submission"
                    )
                    self.set_flash(f"Final assessment published. Score {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%) is below {badge_thresh}% threshold. Retake required for {cosmo_name}.", "warning")

            self.active_modal = None
        except Exception as e:
            self.set_flash(f"Assessment error: {e}", "error")

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

            # Determine single submission / edit vs new submission
            existing_subs = store.get_submissions_for_cosmonaut(self.current_user.id, badge_id)
            latest_sub = existing_subs[-1] if existing_subs else None
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

            # Ensure high-quality defaults so all deliverables are present and readable in reviews
            ref_sub = latest_sub if is_edit else None
            if not pdf_name:
                pdf_name = ref_sub.pdf_name if ref_sub and getattr(ref_sub, "pdf_name", "") else f"{self.current_user.name.split()[0]}_{badge.code}_Architecture_Report.pdf"
            if not pdf_payload:
                pdf_payload = ref_sub.pdf_payload if ref_sub and getattr(ref_sub, "pdf_payload", "") else "data/Chemistry%20Syllabus.pdf"

            if not code_name:
                code_name = ref_sub.code_name if ref_sub and getattr(ref_sub, "code_name", "") else f"{badge.code.lower().replace('-', '_')}_implementation.py"
            if not code_payload:
                code_payload = ref_sub.code_payload if ref_sub and getattr(ref_sub, "code_payload", "") else f'''"""
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
                gh_url = ref_sub.github_url if ref_sub and getattr(ref_sub, "github_url", "") else f"https://github.com/starapp-cosmonauts/{badge.code.lower().replace('-', '_')}-deliverable"

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

            # Log activity
            store.add_activity(
                event_type="project_submitted",
                actor_id=self.current_user.id,
                actor_name=self.current_user.name,
                cosmonaut_id=self.current_user.id,
                badge_id=badge_id,
                summary=f"Project Deliverable Submitted (Attempt #{attempt_num})",
                details=f"{self.current_user.name} submitted {badge.code}: {badge.title} with PDF, Code, and GitHub repository."
            )

            # Route deliverable strictly to assigned reviewer (not guardian)
            assigned_rev_id = getattr(tl, "reviewer_id", "") if tl else ""
            if not assigned_rev_id:
                for mp in store.get_band_mappings():
                    if self.current_user.id in mp.get("cosmonauts", []) and mp.get("reviewers"):
                        assigned_rev_id = mp["reviewers"][0]
                        break

            if assigned_rev_id:
                store.add_notification(
                    recipient_id=assigned_rev_id,
                    title=f"Cadet Deliverable Assigned: {self.current_user.name}",
                    message=f"{self.current_user.name} submitted Attempt #{attempt_num} for {badge.code}: {badge.title}. 3-Day review window active.",
                    link_section="c_assessments"
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
            curr_date = tl.submission_deadline if tl else "2026-11-20"

            valid, err = validate_extension_request(curr_date, prop_date, reason)
            if not valid:
                self.set_flash(f"Request error: {err}", "error")
                return

            ext_id = f"ext_{self.current_user.id}_{badge_id}_{len(store.get_all_extensions()) + 1}"
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

    def execute_save_badge(self, payload: Dict[str, Any]):
        badge_id = payload.get("badge_id", "")
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

        is_new = not badge_id
        if is_new:
            badge_id = f"badge_{code.lower().replace('-', '_')}"

        existing_badge = None if is_new else store.get_badge(badge_id)
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
            is_allocated=payload.get("is_allocated", default_alloc)
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
                    <div style="font-weight:700; color:var(--frost-navy); font-size:13px;">{escape(n.title)}</div>
                    <div style="font-size:12.5px; color:var(--frost-navy); margin-top:2px;">{escape(n.message)}</div>
                    <div style="font-size:11px; color:var(--frost-navy-50); margin-top:4px;">{escape(n.created_at[:16].replace('T', ' '))}</div>
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
                        <span style="font-size:12px; font-weight:800; color:var(--deep-frozen-midnight);">{escape(badge_label)}</span>
                        <span style="font-size:11.5px; font-weight:700; color:var(--frost-navy-50);">Topic: {escape(mat.topic)}</span>
                    </div>
                    <div class="media-embed-container" style="box-shadow:0 8px 30px rgba(7,22,41,0.25); border-radius:var(--radius-md); overflow:hidden;">
                        <iframe src="{escape(embed_url)}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen style="border:0;"></iframe>
                    </div>
                    <div style="margin-top:14px; padding:12px 16px; background:#FFFFFF; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">Lecture Overview & Study Objectives:</div>
                        <p style="font-size:13.5px; line-height:1.55; color:var(--frost-navy); margin:0;">{escape(mat.description)}</p>
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
                            <span style="font-size:12.5px; font-weight:800; color:var(--deep-frozen-midnight);">{escape(badge_label)}</span>
                            <span style="font-size:11.5px; font-weight:700; color:var(--frost-navy-50); margin-left:8px;">Topic: {escape(mat.topic)}</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <a href="{escape(raw_pdf_url)}" target="_blank" class="btn-secondary btn-sm" style="font-size:11.5px; font-weight:700; text-decoration:none; display:inline-flex; align-items:center; gap:5px; padding:4px 12px;">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                                Open in Full Tab
                            </a>
                            <a href="{escape(download_url)}" download="{escape(mat.title)}.pdf" class="btn-secondary btn-sm" style="font-size:11.5px; font-weight:700; text-decoration:none; display:inline-flex; align-items:center; gap:5px; padding:4px 12px;">
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
                            <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:2px;">Document Syllabus & Engineering Context:</div>
                            <p style="font-size:13px; line-height:1.5; color:var(--frost-navy); margin:0;">{escape(mat.description)}</p>
                        </div>
                        <button type="button" class="btn-metal" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Close Document Reader</button>
                    </div>
                    """
                else:
                    body = f"""
                    <pre style="background:var(--frost-navy); color:var(--snow-white); padding:16px; border-radius:var(--radius-md); max-height:400px; overflow:auto;"><code>{escape(mat.url_or_data)}</code></pre>
                    <p style="font-size:13.5px; margin-top:10px; color:var(--frost-navy);">{escape(mat.description)}</p>
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
                <div style="font-size:14px; margin-bottom:14px; color:var(--frost-navy);">
                    Are you sure you want to <strong style="color:var(--deep-frozen-midnight);">{decision.upper()}</strong> the extension request from <strong>{escape(cosmo_name)}</strong> for <strong>{escape(badge_label)}</strong>?
                </div>
                <div style="background:rgba(234,244,255,0.7); padding:12px 16px; border:1px solid var(--icy-steel-30); border-radius:var(--radius-sm); margin-bottom:16px; font-size:13px; line-height:1.5;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                        <span><strong>Original Cutoff:</strong> <span style="font-family:var(--font-family-mono);">{escape(ext.current_deadline if ext else 'N/A')}</span></span>
                        <span><strong>Proposed Cutoff:</strong> <span style="font-family:var(--font-family-mono); font-weight:800; color:var(--deep-frozen-midnight);">{escape(ext.proposed_deadline if ext else 'N/A')}</span></span>
                    </div>
                    <div><strong>Cosmonaut Rationale:</strong> {escape(ext.reason if ext else 'N/A')}</div>
                </div>
                <div class="form-group">
                    <label class="form-label" style="font-weight:700;">Mentor Feedback / Decision Note (Optional)</label>
                    <textarea id="ext-decision-note" class="form-textarea" style="min-height:85px; font-size:13px;" placeholder="Add guidance, expectations, or schedule details for the cosmonaut..."></textarea>
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
                <label style="display:flex; align-items:center; gap:6px; font-size:12.5px; margin-right:12px;">
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
                    <div style="font-size:12px; font-weight:700; color:var(--deep-frozen-midnight); margin-bottom:6px;">Select Individual Recipients:</div>
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
                <p style="font-size:13.5px; color:var(--frost-navy-75); line-height:1.6; max-width:440px; margin:0 auto 16px;">
                    This milestone curriculum and project parameters are managed by your Guardian, <strong>Arjun Mehta</strong>. Once your current sprint deliverables are reviewed and certified, Arjun Mehta will publish the timeline and unlock this milestone for your cohort.
                </p>
                <div style="background:rgba(234,244,255,0.6); padding:12px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); font-size:12px; color:var(--frost-navy); margin-bottom:20px;">
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

            cosmo_cards = []
            all_cosmonauts = store.get_all_cosmonauts()
            for c in all_cosmonauts:
                chk = " checked" if c.id in assigned else ""
                c_band = getattr(c, "band", "B1")
                c_track = getattr(c, "learning_track", "General")
                initials = "".join([part[0] for part in c.name.split()[:2]]).upper() or "C"
                cosmo_cards.append(f"""
                <label class="liquid-glass-card cosmo-assignee-card" style="display:flex; align-items:center; justify-content:space-between; gap:10px; padding:9px 12px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-30); background:rgba(255,255,255,0.9); cursor:pointer; transition:all 0.15s ease;">
                    <div style="display:flex; align-items:center; gap:9px; min-width:0;">
                        <span style="width:28px; height:28px; border-radius:50%; background:linear-gradient(135deg, #17345C 0%, #3B82F6 100%); color:#fff; font-size:11px; font-weight:800; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                            {escape(initials)}
                        </span>
                        <div style="min-width:0;">
                            <div style="font-size:12px; font-weight:800; color:var(--frost-navy); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{escape(c.name)}</div>
                            <div style="display:flex; align-items:center; gap:4px; margin-top:1px;">
                                <span style="font-size:9.5px; font-weight:700; background:rgba(23,52,92,0.08); color:var(--deep-frozen-midnight); padding:1px 5px; border-radius:8px;">{escape(c_band)}</span>
                                <span style="font-size:9.5px; color:var(--frost-navy-50);">{escape(c_track)}</span>
                            </div>
                        </div>
                    </div>
                    <input type="checkbox" name="badge-assignee" value="{c.id}"{chk} style="width:16px; height:16px; accent-color:var(--deep-frozen-midnight); cursor:pointer; flex-shrink:0;">
                </label>
                """)

            body = f"""
            <form onsubmit="event.preventDefault(); const c=document.getElementById('badge-code').value; const t=document.getElementById('badge-title').value; const d=document.getElementById('badge-desc').value; const r=document.getElementById('badge-reqs').value; const al=document.getElementById('tl-alloc-date').value; const ls=document.getElementById('tl-learn-start').value; const le=document.getElementById('tl-learn-end').value; const ps=document.getElementById('tl-proj-start').value; const pe=document.getElementById('tl-proj-end').value; const sd=document.getElementById('tl-sub-deadline').value; const rd=document.getElementById('tl-review-date').value; const aw=document.getElementById('tl-award-date').value; const boxes=document.querySelectorAll('input[name=badge-assignee]:checked'); const sel=[]; boxes.forEach(x=>sel.push(x.value)); window.StarAppBridge.dispatchAction('save_badge_form', JSON.stringify({{badge_id:'{b_id}', code:c, title:t, description:d, project_requirements:r, assigned_cosmonaut_ids:sel, assignment_date:al, learning_start_date:ls, learning_end_date:le, project_start_date:ps, project_end_date:pe, submission_deadline:sd, review_date:rd, expected_award_date:aw}}));">
                <div style="display:grid; grid-template-columns:1fr 2fr; gap:12px;">
                    <div class="form-group">
                        <label class="form-label" style="font-size:12px; font-weight:700;">Badge Code</label>
                        <input type="text" id="badge-code" class="form-control" value="{escape(code)}" placeholder="e.g. SQL-201" required style="font-size:13px; font-weight:700;">
                    </div>
                    <div class="form-group">
                        <label class="form-label" style="font-size:12px; font-weight:700;">Badge Title</label>
                        <input type="text" id="badge-title" class="form-control" value="{escape(b_title)}" placeholder="e.g. Distributed Ingestion" required style="font-size:13px; font-weight:700;">
                    </div>
                </div>

                <div class="form-group" style="margin-top:10px;">
                    <label class="form-label" style="font-size:12px; font-weight:700;">Milestone Description</label>
                    <textarea id="badge-desc" class="form-textarea" rows="2" required style="font-size:12.5px; line-height:1.5;">{escape(desc)}</textarea>
                </div>

                <div class="form-group" style="margin-top:10px;">
                    <label class="form-label" style="font-size:12px; font-weight:700;">Project Deliverable Requirements</label>
                    <textarea id="badge-reqs" class="form-textarea" rows="2" required style="font-size:12.5px; line-height:1.5;">{escape(reqs)}</textarea>
                </div>

                <!-- Guardian Milestone Timeline Decisions -->
                <div style="background:rgba(234,244,255,0.45); padding:16px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-30); margin-top:14px; margin-bottom:14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <span style="font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--deep-frozen-midnight);">
                            Guardian Timeline Decisions (Milestones for Roadmap):
                        </span>
                        <span style="font-size:11px; font-weight:700; color:var(--frost-navy-50);">6 Sequential Gates</span>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label" style="font-size:11.5px; font-weight:700;">1. Badge &amp; Project Allocated Date</label>
                            <input type="date" id="tl-alloc-date" class="form-control" value="{escape(alloc_val)}" required style="font-size:12px;">
                        </div>
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label" style="font-size:11.5px; font-weight:700;">4. Official Submission Date</label>
                            <input type="date" id="tl-sub-deadline" class="form-control" value="{escape(sub_deadline_val)}" required style="font-size:12px;">
                        </div>
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label" style="font-size:11.5px; font-weight:700;">2. Learning Time (Start)</label>
                            <input type="date" id="tl-learn-start" class="form-control" value="{escape(learn_start_val)}" required style="font-size:12px;">
                        </div>
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label" style="font-size:11.5px; font-weight:700;">2. Learning Time (End)</label>
                            <input type="date" id="tl-learn-end" class="form-control" value="{escape(learn_end_val)}" required style="font-size:12px;">
                        </div>
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label" style="font-size:11.5px; font-weight:700;">3. Project Time (Start)</label>
                            <input type="date" id="tl-proj-start" class="form-control" value="{escape(proj_start_val)}" required style="font-size:12px;">
                        </div>
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label" style="font-size:11.5px; font-weight:700;">3. Project Time (End)</label>
                            <input type="date" id="tl-proj-end" class="form-control" value="{escape(proj_end_val)}" required style="font-size:12px;">
                        </div>
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label" style="font-size:11.5px; font-weight:700;">5. Review &amp; Defense Date</label>
                            <input type="date" id="tl-review-date" class="form-control" value="{escape(review_date_val)}" required style="font-size:12px;">
                        </div>
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label" style="font-size:11.5px; font-weight:700;">6. Badge Earned Date (Target)</label>
                            <input type="date" id="tl-award-date" class="form-control" value="{escape(award_date_val)}" required style="font-size:12px;">
                        </div>
                    </div>
                </div>

                <!-- Structured Assignee Section with Search/Actions -->
                <div class="form-group" style="margin-top:14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
                        <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin:0;">
                            Assign To Cosmonauts ({len(assigned)} / {len(all_cosmonauts)} Allocated)
                        </label>
                        <div style="display:flex; gap:6px;">
                            <button type="button" class="btn-secondary btn-sm" onclick="document.querySelectorAll('input[name=badge-assignee]').forEach(x => x.checked = true);" style="font-size:11px; padding:3px 9px;">Select All</button>
                            <button type="button" class="btn-secondary btn-sm" onclick="document.querySelectorAll('input[name=badge-assignee]').forEach(x => x.checked = false);" style="font-size:11px; padding:3px 9px;">Clear All</button>
                        </div>
                    </div>
                    <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(210px, 1fr)); gap:10px; max-height:220px; overflow-y:auto; padding:10px; background:rgba(234,244,255,0.4); border-radius:var(--radius-md); border:1px solid var(--icy-steel-30);">
                        {"".join(cosmo_cards)}
                    </div>
                </div>

                <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:20px; border-top:1px solid var(--icy-steel-30); padding-top:14px;">
                    <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Cancel</button>
                    <button type="submit" class="btn-metal" style="font-weight:800; padding:8px 22px;">Save Allotment &amp; Timeline &rarr;</button>
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
                    <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Target Milestone Badge *</label>
                    <select id="bulk-mat-badge" class="form-select" style="font-size:12.5px; font-weight:700;">
                        {"".join(badge_opts)}
                    </select>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                    <div class="form-group" style="margin:0;">
                        <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Topic / Module Category *</label>
                        <input type="text" id="bulk-mat-topic" class="form-control" placeholder="e.g. Ingestion Foundations, Module 1" value="Module Specification" required>
                    </div>
                    <div class="form-group" style="margin:0;">
                        <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Batch Description / Notes</label>
                        <input type="text" id="bulk-mat-desc" class="form-control" placeholder="e.g. Masterclass lectures and technical documentation.">
                    </div>
                </div>

                <!-- 1. PDF Uploads (Multiples Supported) -->
                <div style="margin-bottom:16px; padding:14px; background:rgba(234,244,255,0.6); border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel-50);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="font-size:12.5px; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px; display:flex; align-items:center; gap:6px;">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                            Upload PDF Documents (Multiple Files Supported)
                        </div>
                        <span style="font-size:11px; font-weight:700; color:var(--frost-navy-50);">Supports .pdf</span>
                    </div>

                    <div style="background:#FFFFFF; border:2px dashed var(--icy-steel); border-radius:var(--radius-xs); padding:16px; text-align:center; cursor:pointer;" onclick="document.getElementById('bulk-pdf-input').click()">
                        <input type="file" id="bulk-pdf-input" accept=".pdf,application/pdf" multiple style="display:none;" onchange="window.StarAppBridge.handleBulkPdfSelect(event)">
                        <div style="color:var(--deep-frozen-midnight); font-weight:800; font-size:13px; display:flex; align-items:center; justify-content:center; gap:8px;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                            Click to Select PDF Files (Multiple Files Supported)
                        </div>
                        <div style="font-size:11.5px; color:var(--frost-navy-50); margin-top:4px;">Upload course manuals, technical whitepapers, or syllabus handbooks</div>
                    </div>

                    <div id="bulk-pdf-list" style="margin-top:10px; display:flex; flex-direction:column; gap:6px;"></div>
                </div>

                <!-- 2. YouTube Video Links (Multiples Supported) -->
                <div style="margin-bottom:16px; padding:14px; background:rgba(234,244,255,0.6); border-radius:var(--radius-sm); border:1.5px solid var(--icy-steel-50);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <div style="font-size:12.5px; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px; display:flex; align-items:center; gap:6px;">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                            YouTube Video Lectures (Multiple Links Supported)
                        </div>
                        <button type="button" class="btn-secondary btn-sm" style="font-weight:700; font-size:11.5px; padding:4px 10px; display:inline-flex; align-items:center; gap:4px;" onclick="window.StarAppBridge.addYouTubeRow()">
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
                        <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Target Milestone Badge *</label>
                        <select id="edit-mat-badge" class="form-select" style="font-size:12.5px; font-weight:700;">
                            {"".join(badge_opts)}
                        </select>
                    </div>

                    <div style="display:grid; grid-template-columns:2fr 1fr; gap:12px; margin-bottom:12px;">
                        <div class="form-group" style="margin:0;">
                            <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Resource Title *</label>
                            <input type="text" id="edit-mat-title" class="form-control" value="{escape(mat.title)}" required>
                        </div>
                        <div class="form-group" style="margin:0;">
                            <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Topic Category *</label>
                            <input type="text" id="edit-mat-topic" class="form-control" value="{escape(mat.topic)}" required>
                        </div>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 2fr; gap:12px; margin-bottom:12px;">
                        <div class="form-group" style="margin:0;">
                            <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Format / Type</label>
                            <select id="edit-mat-type" class="form-select">
                                <option value="youtube"{" selected" if mat.material_type == "youtube" else ""}>Embedded YouTube Video</option>
                                <option value="pdf"{" selected" if mat.material_type == "pdf" else ""}>PDF Handbook Document</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin:0;">
                            <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Resource URL or Embed Link</label>
                            <input type="text" id="edit-mat-url" class="form-control" value="{escape(mat.url_or_data)}" required>
                        </div>
                    </div>

                    <div class="form-group" style="margin-bottom:14px;">
                        <label class="form-label" style="font-size:12px; font-weight:800; color:var(--frost-navy); margin-bottom:4px; display:block;">Description & Overview</label>
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

        elif self.active_modal == "badge_approval_confirm":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = "Confirm Institutional Authorization"
            body = render_badge_approval_confirm_modal(badge, self.current_user) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

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

        elif self.active_modal == "reviewer_project_creator":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"AI Project Creation Engine — {badge.code if badge else ''}"
            body = render_reviewer_project_creator_modal(badge, self.current_user, store) if badge else "<p style='padding:20px; text-align:center;'>Badge not found.</p>"

        elif self.active_modal == "allocated_project_modal":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Allocated Milestone Project — {badge.code if badge else ''}"
            if badge and self.current_user:
                body = render_cosmonaut_allocated_project_modal(badge, self.current_user, store)
            else:
                body = "<div style='padding:24px; text-align:center; color:var(--frost-navy-50);'>Milestone badge not found.</div>"

        elif self.active_modal == "submission_portal_modal":
            b_id = self.modal_payload.get("badge_id", "")
            badge = store.get_badge(b_id)
            title = f"Project Deliverable Submission Portal — {badge.code if badge else ''}"
            if badge and self.current_user:
                existing_subs = store.get_submissions_for_cosmonaut(self.current_user.id, b_id)
                latest_sub = existing_subs[-1] if existing_subs else None
                body = render_cosmonaut_submission_modal(badge, self.current_user, store, existing_sub=latest_sub)
            else:
                body = "<div style='padding:24px; text-align:center; color:var(--frost-navy-50);'>Milestone badge not found.</div>"

        modal_dialog_class = "liquid-glass-modal modal-dialog"
        if self.active_modal in ["material_preview", "badge_creation_preview", "badge_reviewer_edit", "badge_inspect", "cosmonaut_badge_preview", "reviewer_timeline_modal", "reviewer_project_creator", "submission_portal_modal", "allocated_project_modal"]:
            modal_dialog_class += " modal-xl modal-lg"
        elif self.active_modal in ["marksheet_modal", "add_material", "edit_material", "badge_approval_confirm", "badge_reviewer_return"]:
            modal_dialog_class += " modal-lg"

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
        demo_accounts = [
            {"id": "m_b1_2", "role": "Cosmonaut Cadet (B1)", "name": "Ananya Iyer - B1", "user": "ananya.iyer", "desc": "Solutions Designer • Band B1 Cadet (Learner Pilot)"},
            {"id": "m_b2_4", "role": "Specialist & Reviewer (B2)", "name": "Nisha Menon - B2", "user": "nisha.menon", "desc": "AI Engineer • Band B2 (Authorized Badge Reviewer for B1)"},
            {"id": "m_b3_6", "role": "Senior Specialist & Reviewer (B3)", "name": "Tanvi Shah - B3", "user": "tanvi.shah", "desc": "Systems Engineer • Band B3 (Authorized Badge Reviewer for B1 & B2)"},
            {"id": "m_b4_1", "role": "Lead Engineer & Reviewer (B4)", "name": "Rajiv Menon - B4", "user": "rajiv.menon", "desc": "Solutions Designer • Band B4 (Authorized Reviewer for B1 to B3)"},
            {"id": "m_b5_1", "role": "Principal Architect & Reviewer (B5)", "name": "Anirudh Krishnan - B5", "user": "anirudh.krishnan", "desc": "Solutions Designer • Band B5 (Authorized Reviewer for B1 to B4)"},
            {"id": "m_b6_1", "role": "Director & Reviewer (B6)", "name": "Devika Narayanan - B6", "user": "devika.narayanan", "desc": "Solutions Designer • Band B6 (Authorized Reviewer for B1 to B5)"},
            {"id": "guardian_1", "role": "Guardian / CEO", "name": "Arjun Mehta (CEO)", "user": "guardian", "desc": "Chief Executive Officer • Executive Leadership & Academy Guardian"},
            {"id": "admin", "role": "Administrator (B6)", "name": "Guardian Admin", "user": "admin", "desc": "System Administrator • Curriculum Architect & Authority"},
            {"id": "cosmo_1", "role": "Cosmonaut (B1)", "name": "Aarav Sharma - B1", "user": "astraea", "desc": "Solutions Designer • Band B1 Cadet (Active Learner)"}
        ]

        account_buttons = []
        for acc in demo_accounts:
            if "Guardian" in acc["role"]:
                badge_cls = "status-approved"
            elif "Reviewer" in acc["role"]:
                badge_cls = "status-warning"
            else:
                badge_cls = "status-active"
            acc_id = acc["id"]
            acc_name = escape(acc["name"])
            acc_role = escape(acc["role"])
            acc_desc = escape(acc["desc"])
            account_buttons.append(f"""
            <div class="liquid-glass-card interactive" style="padding:14px; margin-bottom:10px; cursor:pointer;" onclick="window.StarAppBridge.dispatchAction('select_demo_account', '{acc_id}')">
                <div style="display:flex; align-items:center; justify-content:space-between;">
                    <div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <strong style="color:var(--frost-navy); font-size:14px;">{acc_name}</strong>
                            <span class="status-pill {badge_cls}">{acc_role}</span>
                        </div>
                        <div style="font-size:12px; color:var(--frost-navy-50); margin-top:2px;">{acc_desc}</div>
                    </div>
                    <span style="font-weight:700; color:var(--deep-frozen-midnight); font-size:14px;">Sign In &rarr;</span>
                </div>
            </div>
            """)

        flash_icon = get_icon("flash", 14, "margin-right:6px;")
        joined_accounts = "".join(account_buttons)

        return f"""
        <div style="min-height:100vh; display:flex; align-items:center; justify-content:center; padding:24px; width:100%;">
            <div style="max-width:680px; width:100%;">
                <div style="text-align:center; margin-bottom:28px;">
                    <div class="brand-badge" style="width:48px; height:48px; margin:0 auto 12px;">
                        <svg viewBox="0 0 24 24" style="width:28px; height:28px; fill:var(--snow-white);"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    </div>
                    <h1 style="font-size:2rem; font-weight:800; color:var(--frost-navy); letter-spacing:-0.5px;">STARAPP</h1>
                    <p style="font-size:14px; color:var(--frost-navy-50); margin-top:4px;">Autonomous Training & Gamified Badge Management Platform</p>
                </div>

                <div class="liquid-glass-card" style="padding:24px; margin-bottom:20px;">
                    <h3 style="font-size:1.1rem; font-weight:700; color:var(--deep-frozen-midnight); margin-bottom:12px;">One-Click Demo Account Access:</h3>
                    {joined_accounts}
                </div>

                <!-- Multi-Window Live Sync Testing Station -->
                <div class="liquid-glass-card" style="padding:18px 22px; margin-bottom:24px; border-radius:var(--radius-md); border:1.5px solid var(--icy-steel-50); background:linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(234,244,255,0.85) 100%);">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                        <div>
                            <div style="font-size:12.5px; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px;">{flash_icon} Multi-Window Live Sync Testing</div>
                            <p style="font-size:12px; color:var(--frost-navy-75); margin:3px 0 0 0;">Open two windows side-by-side. Guardian actions in one window reflect live in the Cosmonaut window instantly.</p>
                        </div>
                        <div style="display:flex; gap:10px;">
                            <button type="button" class="btn-secondary btn-sm" style="font-weight:700;" onclick="window.open('index.html?role=cosmonaut', '_blank');">Launch Cosmonaut &nearr;</button>
                            <button type="button" class="btn-metal btn-sm" style="font-weight:700;" onclick="window.open('index.html?role=guardian', '_blank');">Launch Guardian &nearr;</button>
                        </div>
                    </div>
                </div>

                <div style="text-align:center; font-size:12px; color:var(--frost-navy-50);">
                    StarApp operates strictly browser-local using Pyodide and IndexedDB persistence.
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

        # Common data calculations
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

        if is_guardian_view:
            hide_sidebar = (self.current_view == "g_create_badge" and not self.create_badge_band)
            pending_reviews = len([s for s in all_subs if s.status == "pending"])
            pending_exts = len([e for e in store.get_all_extensions() if e.status == "pending"])
            pending_badge_approvals = len(store.get_pending_badge_approvals(
                reviewer_id=self.current_user.id if "badge_reviewer" in user_roles and "guardian" not in user_roles else None,
                target_band=self.create_badge_band
            ))
            sidebar_badges = {"g_reviews": pending_reviews, "g_extensions": pending_exts, "g_badge_approval": pending_badge_approvals}
            active_nav_id = "g_reviews" if self.current_view == "g_review_detail" else self.current_view
            sidebar_html = render_guardian_sidebar(
                self.current_view,
                self.current_user,
                pending_reviews,
                pending_exts,
                pending_badge_approvals,
                active_band=self.create_badge_band,
                hidden=hide_sidebar
            )

            if self.current_view == "g_create_badge":
                page_title = "Create Badge — StarApp"
                custom_caps = store.get_custom_capabilities()
                custom_skills = store.get_custom_skills()
                elig_revs = store.get_eligible_badge_reviewers(self.create_badge_band) if self.create_badge_band else []
                saved_b = store.get_saved_badges(self.create_badge_band)
                main_content_html = render_guardian_create_badge(
                    selected_band=self.create_badge_band,
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
                    saved_badges=saved_b
                )

            elif self.current_view == "g_badge_approval":
                page_title = "Reviewer Badge Approval — StarApp"
                all_badges = store.get_all_badges()
                # Use create_badge_band as the primary filter; fall back to badge_approval_band_filter
                active_band = self.create_badge_band if self.create_badge_band else getattr(self, "badge_approval_band_filter", "all")
                band_filter = active_band if active_band else "all"
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
                    all_timelines=store.timelines
                )

            elif self.current_view == "g_mapping":
                page_title = "Cosmonaut & Reviewer Competency Mapping"
                active_mapping_band = self.create_badge_band if self.create_badge_band else self.mapping_selected_band
                # Synchronize mapping_selected_badge with active band if invalid, AIOS, or empty
                app_badges = [b for b in store.get_saved_badges(active_mapping_band) if b.get("workflow_status") in ("approved", "ready_for_review")]
                if not app_badges and store.db and store.db.conn:
                    try:
                        rows = store.db.conn.execute("SELECT * FROM badges WHERE target_band = ? AND workflow_status IN ('approved', 'ready_for_review')", (active_mapping_band,)).fetchall()
                        app_badges = [dict(r) for r in rows]
                    except Exception:
                        pass
                badge_titles = [b.get("title") for b in app_badges] + [b.get("code") for b in app_badges] + [b.get("id") for b in app_badges]
                if app_badges:
                    if not self.mapping_selected_badge:
                        self.mapping_selected_badge = app_badges[0].get("title") or app_badges[0].get("name") or app_badges[0].get("code")
                        self.mapping_selected_badge_id = app_badges[0].get("id", "")
                    elif not getattr(self, "mapping_selected_badge_id", ""):
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
                    calendar_year=getattr(self, "mapping_calendar_year", 2026),
                    calendar_month=getattr(self, "mapping_calendar_month", 11),
                    editing_mapping_id=getattr(self, "editing_mapping_id", None),
                    cosmo_search=getattr(self, "mapping_cosmo_search", ""),
                    reviewer_search=getattr(self, "mapping_reviewer_search", ""),
                    badge_search=getattr(self, "mapping_badge_search", ""),
                    all_mappings=store.get_band_mappings(),
                    all_requests=store.get_mapping_requests(),
                    show_final_stage=getattr(self, "mapping_show_final_stage", False),
                    store=store
                )

            elif self.current_view == "g_reviews":
                page_title = "Project Deliverable Assessment Queue"
                asms_by_sub = {a.submission_id: a for a in all_asms}
                scoped_subs = all_subs
                if self.create_badge_band:
                    b_subs = [s for s in all_subs if (cosmo_map.get(s.cosmonaut_id) and cosmo_map[s.cosmonaut_id].band == self.create_badge_band) or (badges_map.get(s.badge_id) and getattr(badges_map[s.badge_id], "target_band", "") == self.create_badge_band)]
                    if b_subs:
                        scoped_subs = b_subs
                main_content_html = render_guardian_review_queue(scoped_subs, asms_by_sub, badges_map, cosmo_map, self.guardian_review_filter)

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

        else:  # Cosmonaut Portal
            unread_anns = len([a for a in store.get_announcements_for_cosmonaut(self.current_user.id) if self.current_user.id not in a.read_by_cosmonaut_ids])
            cosmo_reqs = store.get_badge_review_requests_for_user(self.current_user.id)
            pending_cosmo_reqs_cnt = len([r for r in cosmo_reqs if r.get("workflow_status") == "pending_review" or r.get("assignment_status") == "pending"])
            if self.current_view == "c_badge_detail":
                active_nav_id = "c_submission"
            elif self.current_view == "c_assessment_detail":
                active_nav_id = "c_assessments"
            else:
                active_nav_id = self.current_view
            sidebar_html = render_cosmonaut_sidebar(self.current_view, self.current_user, unread_anns, pending_cosmo_reqs_cnt)

            assigned_badges = store.get_badges_for_cosmonaut(self.current_user.id)
            user_asms = store.get_assessments_for_cosmonaut(self.current_user.id)
            user_subs = store.get_submissions_for_cosmonaut(self.current_user.id)
            profile = store.get_cosmonaut_profile(self.current_user.id)
            summary = calculate_cosmonaut_score_summary(user_asms)
            leaderboard = calculate_batch_leaderboard(cosmonauts, all_asms)

            if self.current_view == "c_dashboard":
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

            elif self.current_view == "c_results":
                page_title = "Official Evaluation Marksheets (50-Mark Rubric)"
                res_badge_id = self.cosmonaut_results_badge_id
                if not res_badge_id and user_asms:
                    # Automatically select the badge with the most recent marksheet evaluation
                    latest_asm = sorted(user_asms, key=lambda a: a.reviewed_at)[-1]
                    res_badge_id = latest_asm.badge_id
                main_content_html = render_cosmonaut_results(
                    assessments=user_asms,
                    badges_map=badges_map,
                    selected_badge_id=res_badge_id,
                    available_badges=assigned_badges,
                    extensions=store.get_extensions_for_cosmonaut(self.current_user.id)
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
                main_content_html = render_cosmonaut_profile(self.current_user, profile)

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

            elif self.current_view == "c_badge_reviews":
                page_title = "My Badge Review Schedule"
                main_content_html = render_reviewer_badge_schedule(
                    current_user=self.current_user,
                    store=store,
                    badges_map=badges_map,
                    cosmo_map=cosmo_map,
                    expanded_badge_id=getattr(self, "reviewer_expanded_badge_id", None)
                )

            elif self.current_view == "c_assessments":
                page_title = "Cadet Deliverables Assessment Queue"
                active_filter = getattr(self, "reviewer_assessments_filter", "all")
                all_subs = store.get_all_submissions()
                all_asms_dict = {a.submission_id: a for a in store.get_all_assessments()}
                main_content_html = render_reviewer_assessment_queue(
                    submissions=all_subs,
                    assessments_by_sub=all_asms_dict,
                    badges_map=badges_map,
                    cosmonauts_map=cosmo_map,
                    current_user=self.current_user,
                    status_filter=active_filter
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
                        main_content_html = "<div class='liquid-glass-card' style='padding:40px; text-align:center;'><h3 style='color:#DC2626;'>Unauthorized Access</h3><p style='color:var(--frost-navy-50); margin-top:8px;'>You are not authorized or assigned to evaluate this cadet deliverable.</p><button onclick=\"window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_assessments')\" class='btn-secondary' style='margin-top:14px;'>Back to Assessment Queue</button></div>"
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
                    main_content_html = "<div class='liquid-glass-card' style='padding:40px; text-align:center;'>Deliverable not found. <button onclick=\"window.StarAppBridge.dispatchAction('nav_cosmonaut', 'c_assessments')\" class='btn-secondary'>Back to Assessment Queue</button></div>"

        modal_html = self.render_active_modal()

        flash_html = ""
        if self.flash_message:
            flash_border = "var(--deep-frozen-midnight)" if self.flash_type == "success" else "var(--frost-navy)"
            flash_html = f"""
            <div style="margin-bottom:16px; padding:12px 18px; border-radius:var(--radius-md); background:rgba(234,244,255,0.9); border:1px solid {flash_border}; border-left:5px solid {flash_border}; font-size:13.5px; font-weight:600; color:var(--frost-navy); display:flex; justify-content:space-between; align-items:center;">
                <span>{escape(self.flash_message)}</span>
                <span style="cursor:pointer; font-size:18px;" onclick="this.parentElement.remove();">&times;</span>
            </div>
            """
            self.flash_message = None  # Consume flash

        page_container_cls = "page-container page-review-detail" if self.current_view in ("g_review_detail", "c_assessment_detail") else "page-container"

        full_html = f"""
        {sidebar_html}
        <div id="starapp-main-viewport" class="app-main">
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

