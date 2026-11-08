"""
STARAPP CORE APPLICATION CONTROLLER & ROUTER
Orchestrates role-based navigation, state mutation, event dispatch, and UI rendering.
Works seamlessly in browser Pyodide runtime and in local Python test suites.
"""

import json
from typing import Optional, Dict, Any
from starapp.models import (
    User, Badge, BadgeTimeline, ProjectSubmission, AssessmentMarksheet,
    LearningMaterial, DeadlineExtension, Announcement, current_iso_timestamp
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
    render_guardian_badge_allotment, render_guardian_review_queue,
    render_guardian_review_detail,
    render_assessment_modal_content, render_guardian_materials,
    render_guardian_activity_feed, render_guardian_extensions,
    render_guardian_announcements
)
from starapp.views_cosmonaut import (
    render_cosmonaut_sidebar, render_cosmonaut_dashboard,
    render_cosmonaut_profile, render_gamified_roadmap,
    render_badge_detail_modal_content, render_cosmonaut_submission_workspace,
    render_cosmonaut_results, render_cosmonaut_materials,
    render_cosmonaut_extensions, render_cosmonaut_announcements,
    render_cosmonaut_activity_stream
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
        self.cosmonaut_results_badge_id: str = "badge_gov_101"
        self.materials_badge_filter: str = "all"
        self.materials_type_filter: str = "all"
        self.active_modal: Optional[str] = None
        self.modal_payload: Dict[str, Any] = {}
        self.flash_message: Optional[str] = None
        self.flash_type: str = "info"

    # Valid view ids per role to prevent arbitrary injection
    _GUARDIAN_VIEWS = {
        "g_dashboard", "g_roadmap", "g_cosmonauts", "g_badge_allotment", "g_reviews", "g_review_detail",
        "g_materials", "g_extensions", "g_announcements", "g_activity"
    }
    _COSMONAUT_VIEWS = {
        "c_dashboard", "c_roadmap", "c_submission", "c_results",
        "c_materials", "c_profile", "c_announcements", "c_extensions", "c_activity"
    }

    def initialize(self, stored_json: Optional[str] = None, session_json: Optional[str] = None):
        """Loads data from storage and restores previous user session including the exact page."""
        store.load_from_json(stored_json)

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
                        # Restore the exact page if it is valid for the user's role
                        if user.role == "guardian" and saved_view in self._GUARDIAN_VIEWS:
                            self.current_view = saved_view
                        elif user.role == "cosmonaut" and saved_view in self._COSMONAUT_VIEWS:
                            self.current_view = saved_view
                        else:
                            self.current_view = "g_dashboard" if user.role == "guardian" else "c_dashboard"
            except Exception as e:
                print(f"[Controller] Session restore error: {e}")

        self.sync_storage()
        self.render()

    def sync_storage(self):
        """Persists current state snapshot to IndexedDB / localStorage via bridge."""
        json_data = store.to_json()
        session_data = json.dumps({
            "user_id": self.current_user.id if self.current_user else None,
            "current_view": self.current_view
        })
        if IS_BROWSER and hasattr(js, "window") and hasattr(js.window, "StarAppBridge"):
            js.window.StarAppBridge.setStore("data", json_data)
            js.window.StarAppBridge.setStore("session", session_data)

    def reload_data(self, stored_json: Optional[str] = None):
        """
        Real-time multi-window synchronization callback.
        Called when another browser window updates the shared data store.
        Reloads domain data from JSON while maintaining this window's user session.
        Re-renders immediately so changes appear live across windows.
        """
        if stored_json and stored_json.strip():
            store.load_from_json(stored_json)
            if self.current_user:
                updated_user = store.get_user_by_id(self.current_user.id)
                if updated_user:
                    self.current_user = updated_user
            self.render()

    def set_flash(self, message: str, ftype: str = "info"):
        self.flash_message = message
        self.flash_type = ftype

    # ==========================================================================
    # ACTION & EVENT HANDLER
    # ==========================================================================

    def handle_event(self, action: str, payload_json: str = "{}"):
        try:
            payload = json.loads(payload_json) if isinstance(payload_json, str) and payload_json.startswith("{") else payload_json
        except Exception:
            payload = {}

        # --- Authentication Actions ---
        if action == "login":
            username = str(payload.get("username", "")).strip().lower()
            user = store.get_user_by_username(username)
            if user:
                self.current_user = user
                self.current_view = "g_dashboard" if user.role == "guardian" else "c_dashboard"
                self.set_flash(f"Welcome back, {user.name}!", "success")
            else:
                self.set_flash("Invalid demo username. Please choose from the demo credentials below.", "error")

        elif action == "select_demo_account":
            user_id = payload.get("user_id") if isinstance(payload, dict) else payload
            user = store.get_user_by_id(user_id)
            if user:
                self.current_user = user
                self.current_view = "g_dashboard" if user.role == "guardian" else "c_dashboard"
                self.set_flash(f"Logged in as {user.name} ({user.role.title()})", "success")

        elif action == "logout":
            self.current_user = None
            self.current_view = "login"
            self.active_modal = None
            self.set_flash("You have been signed out.", "info")

        elif action == "reset_demo_data":
            store.reset_to_seed()
            self.active_modal = None
            self.set_flash("StarApp demo data has been restored to factory default.", "success")

        # --- Navigation Actions ---
        elif action == "nav_guardian":
            view_id = payload if isinstance(payload, str) else payload.get("view_id")
            self.current_view = view_id
            self.active_modal = None

        elif action == "nav_cosmonaut":
            view_id = payload if isinstance(payload, str) else payload.get("view_id")
            self.current_view = view_id
            self.active_modal = None

        elif action == "nav_to_submit_badge":
            badge_id = payload if isinstance(payload, str) else payload.get("badge_id")
            self.cosmonaut_submission_badge_id = badge_id
            self.current_view = "c_submission"
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
                        message=f"Dr. Elena Vance published and unlocked {badge.code}: {badge.title}! Curriculum and project requirements are now live.",
                        link_section="c_roadmap"
                    )

                # Assign next catalog milestone as new locked milestone
                all_b = store.get_all_badges()
                for nb in all_b:
                    if nb.id != badge.id and not getattr(nb, "is_allocated", True):
                        nb.is_published = True
                        nb.assigned_cosmonaut_ids = all_cosmo_ids
                        store.save_badge(nb)
                        break

                store.add_activity(
                    event_type="badge_published",
                    actor_id=self.current_user.id,
                    actor_name=self.current_user.name,
                    cosmonaut_id="",
                    badge_id=badge.id,
                    summary=f"Published & Unlocked Milestone {badge.code}: {badge.title}",
                    details="Milestone unlocked on Cosmonaut roadmap; subsequent catalog milestone queued as locked."
                )
                self.set_flash(f"Successfully published and unlocked {badge.code}: {badge.title} for Cosmonauts! Next milestone queued as locked.", "success")

        elif action == "revoke_badge":
            badge_id = payload if isinstance(payload, str) else payload.get("badge_id", "")
            badge = store.get_badge(badge_id)
            if badge:
                badge.is_allocated = False
                badge.is_published = False
                all_cosmo_ids = [c.id for c in store.get_all_cosmonauts()]
                badge.assigned_cosmonaut_ids = []
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
            badge = store.get_badge(badge_id)
            if badge:
                badge.is_published = True
                store.add_activity("badge_published", self.current_user.id, self.current_user.name, "", badge.id, f"Published {badge.code}: {badge.title} to learning roadmap")
                self.set_flash(f"Published {badge.code} to Cosmonaut learning roadmaps.", "success")

        elif action == "unpublish_badge":
            badge_id = payload.get("badge_id") if isinstance(payload, dict) else payload
            badge = store.get_badge(badge_id)
            if badge:
                badge.is_published = False
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
                    self.set_flash(f"Added skill '{skill}' to profile.", "success")

        elif action == "remove_skill":
            skill = payload if isinstance(payload, str) else payload.get("skill")
            if skill and self.current_user:
                profile = store.get_cosmonaut_profile(self.current_user.id)
                if skill in profile.skills:
                    profile.skills.remove(skill)
                    self.set_flash(f"Removed skill '{skill}'.", "info")

        elif action == "add_certification":
            if isinstance(payload, dict) and self.current_user:
                profile = store.get_cosmonaut_profile(self.current_user.id)
                profile.certifications.append(payload)
                self.set_flash(f"Added certification '{payload.get('name')}' to profile.", "success")

        elif action == "remove_certification":
            idx = int(payload if isinstance(payload, (int, str)) else payload.get("index", 0))
            if self.current_user:
                profile = store.get_cosmonaut_profile(self.current_user.id)
                if 0 <= idx < len(profile.certifications):
                    del profile.certifications[idx]
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
            sub_id = payload if isinstance(payload, str) else payload.get("submission_id", "")
            self.selected_review_sub_id = sub_id
            self.selected_viewer_tab = "pdf"
            self.current_view = "g_review_detail"

        elif action == "change_viewer_tab":
            tab = payload if isinstance(payload, str) else payload.get("tab", "pdf")
            self.selected_viewer_tab = tab

        elif action in ("submit_evaluation_marksheet", "submit_evaluation_rubric"):
            self.execute_submit_evaluation(payload)
            self.current_view = "g_reviews"

        elif action == "submit_project_deliverable":
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
        self.render()

    # ==========================================================================
    # WORKFLOW EXECUTION HELPERS
    # ==========================================================================

    def execute_submit_evaluation(self, payload: Any = None):
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

        sub_id = sub_id or getattr(self, "selected_review_sub_id", "")
        sub = store.get_submission(sub_id)
        if not sub and hasattr(self, "selected_review_sub_id") and self.selected_review_sub_id:
            sub = store.get_submission(self.selected_review_sub_id)

        if not sub:
            self.set_flash("Submission record not found.", "error")
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

            bu = 9.0 if bu is None else bu
            ar = 9.0 if ar is None else ar
            tk = 9.0 if tk is None else tk
            pr = 9.0 if pr is None else pr
            qa = 9.0 if qa is None else qa
            strengths = strengths or "Robust architecture patterns and clean code implementation."
            improvements = improvements or "Maintain consistent logging and extend test coverage."
            feedback = feedback or "Approved milestone deliverables."
            decision = decision or "approve"

            valid, err = validate_rubric_scores(bu, ar, tk, pr, qa)
            if not valid:
                self.set_flash(f"Scoring error: {err}", "error")
                return

            asm_id = f"asm_{sub.id}_{sub.attempt_number}"
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
                overall_feedback=feedback
            )
            store.save_assessment(marksheet)

            # Update submission status
            sub.status = "approved" if decision == "approve" else ("resubmission_requested" if decision == "resubmission_requested" else "rejected")
            store.save_submission(sub)

            # Update timeline if approved
            if decision == "approve":
                tl = store.get_timeline(sub.badge_id, sub.cosmonaut_id)
                if tl:
                    tl.status = "completed"
                    tl.actual_award_date = current_iso_timestamp()[:10]
                    store.save_timeline(tl)

            # Pre-select this badge in Cosmonaut results view
            self.cosmonaut_results_badge_id = sub.badge_id

            # Log activity
            badge = store.get_badge(sub.badge_id)
            b_name = badge.code if badge else sub.badge_id
            cosmo = store.get_user_by_id(sub.cosmonaut_id)
            cosmo_name = cosmo.name if cosmo else sub.cosmonaut_id

            store.add_activity(
                event_type="assessment_completed",
                actor_id=self.current_user.id,
                actor_name=self.current_user.name,
                cosmonaut_id=sub.cosmonaut_id,
                badge_id=sub.badge_id,
                summary=f"Assessment Marksheet Published: {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%) for {cosmo_name}",
                details=f"Evaluated Attempt #{sub.attempt_number} with decision: {decision.replace('_', ' ').title()}"
            )

            # Notify Cosmonaut
            store.add_notification(
                recipient_id=sub.cosmonaut_id,
                title=f"Assessment Completed: {b_name}",
                message=f"{self.current_user.name} completed evaluation for Attempt #{sub.attempt_number}. Score: {marksheet.total_marks:.1f}/50 ({marksheet.percentage:.1f}%). Decision: {decision.title()}.",
                link_section="c_results"
            )

            self.active_modal = None
            self.set_flash(f"Assessment marksheet for {cosmo_name} saved successfully. Marks: {marksheet.total_marks:.1f}/50.", "success")
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

            # Determine attempt number
            existing_subs = store.get_submissions_for_cosmonaut(self.current_user.id, badge_id)
            attempt_num = len(existing_subs) + 1

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

            # Update timeline status
            tl = store.get_timeline(badge_id, self.current_user.id)
            if tl:
                tl.status = "awaiting_review"
                store.save_timeline(tl)

            # Log activity & notify Guardian
            store.add_activity(
                event_type="project_submitted",
                actor_id=self.current_user.id,
                actor_name=self.current_user.name,
                cosmonaut_id=self.current_user.id,
                badge_id=badge_id,
                summary=f"Project Deliverable Submitted (Attempt #{attempt_num})",
                details=f"{self.current_user.name} submitted {badge.code}: {badge.title} with PDF, Code, and GitHub repository."
            )

            store.add_notification(
                recipient_id="guardian_1",
                title=f"New Deliverable: {self.current_user.name}",
                message=f"{self.current_user.name} submitted Attempt #{attempt_num} for {badge.code}: {badge.title} with all deliverables.",
                link_section="g_reviews"
            )

            self.set_flash(f"Deliverables for {badge.code} (Attempt #{attempt_num}) submitted successfully! PDF, Source Code, and GitHub repository are ready for Guardian assessment.", "success")
        except Exception as e:
            print("EXCEPTION in execute_submit_project:", e)
            self.set_flash(f"Submission failed: {e}", "error")

            self.set_flash(f"Deliverable for {badge.code} (Attempt #{attempt_num}) submitted successfully! Awaiting Guardian review.", "success")
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

            store.add_notification(
                recipient_id=ext.cosmonaut_id,
                title=f"Extension Request {decision.title()}",
                message=f"Dr. Elena Vance {decision} your deadline extension request for {b_name}. Note: {response_note}",
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
            is_allocated=True
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
                store.add_notification(
                    recipient_id=cid,
                    title=f"New Milestone Available: {code}",
                    message=f"Dr. Elena Vance created new milestone {code}: {title}. The previous locked milestone is now unlocked!",
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
                state = "completed" if badge.id in approved_ids else ("locked" if any(p not in approved_ids for p in badge.prerequisites) else "active")
                body = render_badge_detail_modal_content(badge, cosmo_id, tl, mats, state, is_guardian=is_guardian)

        elif self.active_modal == "marksheet_modal":
            asm_id = self.modal_payload.get("marksheet_id")
            marksheet = store.get_assessment(asm_id)
            if not marksheet and asm_id:
                # 1. Check actual cosmonaut benchmark assessments (Astraea Nova)
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
                        reviewer_name="Dr. Elena Vance",
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
                                    reviewer_name="Dr. Elena Vance",
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
                    body = f"""
                    <div style="margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; background:rgba(23,52,92,0.06); padding:8px 14px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel-50);">
                        <span style="font-size:12px; font-weight:800; color:var(--deep-frozen-midnight);">{escape(badge_label)}</span>
                        <span style="font-size:11.5px; font-weight:700; color:var(--frost-navy-50);">Topic: {escape(mat.topic)}</span>
                    </div>
                    <div style="background:#FFFFFF; border-radius:var(--radius-md); overflow:hidden; border:1.5px solid var(--icy-steel-50); box-shadow:0 6px 24px rgba(7,22,41,0.06); margin-bottom:12px;">
                        <object data="{escape(mat.url_or_data.replace(' ', '%20') if (mat.url_or_data and not mat.url_or_data.startswith('http')) else (mat.url_or_data or 'data/Chemistry%20Syllabus.pdf'))}" type="application/pdf" style="width:100%; height:580px; border:none; display:block;">
                            <iframe class="pdf-preview-box" src="{escape(mat.url_or_data.replace(' ', '%20') if (mat.url_or_data and not mat.url_or_data.startswith('http')) else (mat.url_or_data or 'data/Chemistry%20Syllabus.pdf'))}" style="width:100%; height:580px; border:none; display:block;" title="{escape(mat.title)}"></iframe>
                        </object>
                    </div>
                    <div style="padding:12px 16px; background:#FFFFFF; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                        <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:4px;">Document Syllabus & Engineering Context:</div>
                        <p style="font-size:13.5px; line-height:1.55; color:var(--frost-navy); margin:0;">{escape(mat.description)}</p>
                    </div>
                    <div style="display:flex; justify-content:flex-end; margin-top:16px;">
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
                    This milestone curriculum and project parameters are managed by your Guardian, <strong>Dr. Elena Vance</strong>. Once your current sprint deliverables are reviewed and certified, Dr. Vance will publish the timeline and unlock this milestone for your cohort.
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

            cosmo_checks = []
            for c in store.get_all_cosmonauts():
                chk = " checked" if c.id in assigned else ""
                cosmo_checks.append(f"""
                <label style="display:flex; align-items:center; gap:6px; font-size:12.5px; margin-right:12px;">
                    <input type="checkbox" name="badge-assignee" value="{c.id}"{chk}>
                    <span>{escape(c.name)}</span>
                </label>
                """)

            body = f"""
            <form onsubmit="event.preventDefault(); const c=document.getElementById('badge-code').value; const t=document.getElementById('badge-title').value; const d=document.getElementById('badge-desc').value; const r=document.getElementById('badge-reqs').value; const al=document.getElementById('tl-alloc-date').value; const ls=document.getElementById('tl-learn-start').value; const le=document.getElementById('tl-learn-end').value; const ps=document.getElementById('tl-proj-start').value; const pe=document.getElementById('tl-proj-end').value; const sd=document.getElementById('tl-sub-deadline').value; const rd=document.getElementById('tl-review-date').value; const aw=document.getElementById('tl-award-date').value; const boxes=document.querySelectorAll('input[name=badge-assignee]:checked'); const sel=[]; boxes.forEach(x=>sel.push(x.value)); window.StarAppBridge.dispatchAction('save_badge_form', JSON.stringify({{badge_id:'{b_id}', code:c, title:t, description:d, project_requirements:r, assigned_cosmonaut_ids:sel, assignment_date:al, learning_start_date:ls, learning_end_date:le, project_start_date:ps, project_end_date:pe, submission_deadline:sd, review_date:rd, expected_award_date:aw}}));">
                <div style="display:grid; grid-template-columns:1fr 2fr; gap:12px;">
                    <div class="form-group">
                        <label class="form-label">Badge Code</label>
                        <input type="text" id="badge-code" class="form-control" value="{escape(code)}" placeholder="e.g. SQL-201" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Badge Title</label>
                        <input type="text" id="badge-title" class="form-control" value="{escape(b_title)}" placeholder="e.g. Distributed Ingestion" required>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">Milestone Description</label>
                    <textarea id="badge-desc" class="form-textarea" rows="2" required>{escape(desc)}</textarea>
                </div>

                <div class="form-group">
                    <label class="form-label">Project Deliverable Requirements</label>
                    <textarea id="badge-reqs" class="form-textarea" rows="2" required>{escape(reqs)}</textarea>
                </div>

                <!-- Guardian Milestone Timeline Decisions -->
                <div style="background:rgba(234,244,255,0.45); padding:14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30); margin-bottom:16px;">
                    <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--deep-frozen-midnight); margin-bottom:10px;">
                        Guardian Timeline Decisions (Milestones for Roadmap):
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div class="form-group" style="margin-bottom:8px;">
                            <label class="form-label" style="font-size:11.5px;">1. Badge & Project Allocated Date</label>
                            <input type="date" id="tl-alloc-date" class="form-control" value="{escape(alloc_val)}" required>
                        </div>
                        <div class="form-group" style="margin-bottom:8px;">
                            <label class="form-label" style="font-size:11.5px;">4. Official Submission Date</label>
                            <input type="date" id="tl-sub-deadline" class="form-control" value="{escape(sub_deadline_val)}" required>
                        </div>
                        <div class="form-group" style="margin-bottom:8px;">
                            <label class="form-label" style="font-size:11.5px;">2. Learning Time (Start)</label>
                            <input type="date" id="tl-learn-start" class="form-control" value="{escape(learn_start_val)}" required>
                        </div>
                        <div class="form-group" style="margin-bottom:8px;">
                            <label class="form-label" style="font-size:11.5px;">2. Learning Time (End)</label>
                            <input type="date" id="tl-learn-end" class="form-control" value="{escape(learn_end_val)}" required>
                        </div>
                        <div class="form-group" style="margin-bottom:8px;">
                            <label class="form-label" style="font-size:11.5px;">3. Project Time (Start)</label>
                            <input type="date" id="tl-proj-start" class="form-control" value="{escape(proj_start_val)}" required>
                        </div>
                        <div class="form-group" style="margin-bottom:8px;">
                            <label class="form-label" style="font-size:11.5px;">3. Project Time (End)</label>
                            <input type="date" id="tl-proj-end" class="form-control" value="{escape(proj_end_val)}" required>
                        </div>
                        <div class="form-group" style="margin-bottom:8px;">
                            <label class="form-label" style="font-size:11.5px;">5. Review & Defense Date</label>
                            <input type="date" id="tl-review-date" class="form-control" value="{escape(review_date_val)}" required>
                        </div>
                        <div class="form-group" style="margin-bottom:8px;">
                            <label class="form-label" style="font-size:11.5px;">6. Badge Earned Date (Target)</label>
                            <input type="date" id="tl-award-date" class="form-control" value="{escape(award_date_val)}" required>
                        </div>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">Assign To Cosmonauts</label>
                    <div style="display:flex; flex-wrap:wrap; gap:8px; background:rgba(234,244,255,0.4); padding:10px 14px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-30);">
                        {"".join(cosmo_checks)}
                    </div>
                </div>

                <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
                    <button type="button" class="btn-secondary" onclick="window.StarAppBridge.dispatchAction('close_modal', '{{}}')">Cancel</button>
                    <button type="submit" class="btn-metal">Save Allotment & Timeline</button>
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

        modal_dialog_class = "liquid-glass-modal modal-dialog"
        if self.active_modal in ["material_preview", "marksheet_modal", "add_material", "edit_material"]:
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
            {"id": "guardian_1", "role": "Guardian", "name": "Dr. Elena Vance", "user": "guardian", "desc": "Training Mentor (Full curriculum management & rubric evaluations)"},
            {"id": "cosmo_1", "role": "Cosmonaut", "name": "Astraea Nova", "user": "astraea", "desc": "Cosmonaut Learner (3 Badges completed, Ingestion active)"}
        ]

        account_buttons = []
        for acc in demo_accounts:
            badge_cls = "status-approved" if acc["role"] == "Guardian" else "status-active"
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

    def render(self) -> str:
        """Constructs the complete application view HTML."""
        if not self.current_user or self.current_view == "login":
            html_output = self.render_login_view()
            if IS_BROWSER and hasattr(js, "document"):
                root = js.document.getElementById("app-root")
                if root:
                    root.innerHTML = html_output
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

        if self.current_user.role == "guardian":
            pending_reviews = len([s for s in all_subs if s.status == "pending"])
            pending_exts = len([e for e in store.get_all_extensions() if e.status == "pending"])
            sidebar_html = render_guardian_sidebar(self.current_view, self.current_user, pending_reviews, pending_exts)

            if self.current_view == "g_dashboard":
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
                main_content_html = render_gamified_roadmap(actual_cosmo, nodes)

            elif self.current_view == "g_allotment":
                page_title = "Badge Allotment & Timeline Management"
                main_content_html = render_guardian_badge_allotment(badges, cosmonauts, getattr(self, 'guardian_allotment_filter', 'all'))

            elif self.current_view == "g_reviews":
                page_title = "Project Deliverable Assessment Queue"
                asms_by_sub = {a.submission_id: a for a in all_asms}
                main_content_html = render_guardian_review_queue(all_subs, asms_by_sub, badges_map, cosmo_map, self.guardian_review_filter)

            elif self.current_view == "g_review_detail":
                page_title = "Project Deliverable Technical Inspection & Assessment"
                sub = store.get_submission(self.selected_review_sub_id) if getattr(self, "selected_review_sub_id", None) else None
                if not sub and all_subs:
                    sub = all_subs[0]
                if sub:
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
                main_content_html = render_guardian_materials(
                    materials=store.get_materials(),
                    badges=badges,
                    badges_map=badges_map,
                    selected_badge_filter=self.materials_badge_filter,
                    selected_type_filter=self.materials_type_filter
                )

            elif self.current_view == "g_extensions":
                page_title = "Milestone Deadline Extensions"
                main_content_html = render_guardian_extensions(store.get_all_extensions(), cosmo_map, badges_map)

            elif self.current_view == "g_announcements":
                page_title = "Academy Announcement Broadcaster"
                main_content_html = render_guardian_announcements(store.get_all_announcements(), cosmonauts)

            elif self.current_view == "g_activity":
                page_title = "Academy Activity & Audit Stream"
                main_content_html = render_guardian_activity_feed(store.get_activities(), cosmonauts)

        else:  # Cosmonaut Portal
            unread_anns = len([a for a in store.get_announcements_for_cosmonaut(self.current_user.id) if self.current_user.id not in a.read_by_cosmonaut_ids])
            sidebar_html = render_cosmonaut_sidebar(self.current_view, self.current_user, unread_anns)

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
                main_content_html = render_cosmonaut_dashboard(
                    current_user=self.current_user,
                    profile=profile,
                    assigned_badges=assigned_badges,
                    assessments=user_asms,
                    submissions=user_subs,
                    extensions=u_exts,
                    recent_announcements=recent_anns
                )

            elif self.current_view == "c_roadmap":
                page_title = "Interactive Gamified Learning Pathway"
                nodes = generate_roadmap_graph(badges, self.current_user.id, user_asms, user_subs)
                main_content_html = render_gamified_roadmap(self.current_user, nodes)

            elif self.current_view == "c_submission":
                page_title = "Project Deliverable Submission Portal"
                main_content_html = render_cosmonaut_submission_workspace(assigned_badges, self.cosmonaut_submission_badge_id, user_subs)

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

        page_container_cls = "page-container page-review-detail" if self.current_view == "g_review_detail" else "page-container"

        full_html = f"""
        {sidebar_html}
        <div class="app-main">
            <main class="{page_container_cls}">
                {flash_html}
                {main_content_html}
            </main>
        </div>
        {modal_html}
        """

        if IS_BROWSER and hasattr(js, "document"):
            root = js.document.getElementById("app-root")
            if root:
                root.innerHTML = full_html

        return full_html

# Global controller instance
controller = StarAppController()

