"""
STARAPP CENTRALIZED STORAGE & DATA-ACCESS LAYER
Acts as the single source of truth for both Guardian and Cosmonaut portals.
Synchronizes with browser IndexedDB and localStorage via bridge calls.
"""

import json
import datetime
from typing import List, Dict, Any, Optional
from starapp.models import (
    User, CosmonautProfile, Badge, BadgeTimeline, ProjectSubmission,
    AssessmentMarksheet, LearningMaterial, DeadlineExtension,
    Announcement, ActivityEvent, Notification, current_iso_timestamp
)
from starapp.seed_data import get_initial_seed_data

SCHEMA_VERSION = 9

class DataStore:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.profiles: Dict[str, CosmonautProfile] = {}
        self.badges: Dict[str, Badge] = {}
        # Key: (badge_id, cosmonaut_id)
        self.timelines: Dict[str, BadgeTimeline] = {}
        self.submissions: Dict[str, ProjectSubmission] = {}
        self.assessments: Dict[str, AssessmentMarksheet] = {}
        self.materials: Dict[str, LearningMaterial] = {}
        self.extensions: Dict[str, DeadlineExtension] = {}
        self.announcements: Dict[str, Announcement] = {}
        self.activities: List[ActivityEvent] = []
        self.notifications: List[Notification] = []
        self.is_loaded = False
        self.version: int = 1
        self.dirty: bool = False
        self._cached_json: Optional[str] = None

    def mark_dirty(self):
        """Flags store as modified to trigger targeted JSON serialization and persistence."""
        self.version += 1
        self.dirty = True
        self._cached_json = None

    def load_from_dict(self, data: Dict[str, Any]):
        self.users = {u["id"]: User.from_dict(u) for u in data.get("users", [])}
        self.profiles = {p["user_id"]: CosmonautProfile.from_dict(p) for p in data.get("profiles", [])}
        self.badges = {b["id"]: Badge.from_dict(b) for b in data.get("badges", [])}
        
        self.timelines = {}
        for t in data.get("timelines", []):
            tl = BadgeTimeline.from_dict(t)
            self.timelines[f"{tl.badge_id}_{tl.cosmonaut_id}"] = tl

        self.submissions = {s["id"]: ProjectSubmission.from_dict(s) for s in data.get("submissions", [])}
        self.assessments = {a["id"]: AssessmentMarksheet.from_dict(a) for a in data.get("assessments", [])}
        self.materials = {m["id"]: LearningMaterial.from_dict(m) for m in data.get("materials", [])}
        self.extensions = {e["id"]: DeadlineExtension.from_dict(e) for e in data.get("extensions", [])}
        self.announcements = {a["id"]: Announcement.from_dict(a) for a in data.get("announcements", [])}
        
        self.activities = [ActivityEvent.from_dict(act) for act in data.get("activities", [])]
        self.notifications = [Notification.from_dict(n) for n in data.get("notifications", [])]
        self.is_loaded = True
        self.version += 1
        self.dirty = False
        self._cached_json = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "users": [u.to_dict() for u in self.users.values()],
            "profiles": [p.to_dict() for p in self.profiles.values()],
            "badges": [b.to_dict() for b in self.badges.values()],
            "timelines": [t.to_dict() for t in self.timelines.values()],
            "submissions": [s.to_dict() for s in self.submissions.values()],
            "assessments": [a.to_dict() for a in self.assessments.values()],
            "materials": [m.to_dict() for m in self.materials.values()],
            "extensions": [e.to_dict() for e in self.extensions.values()],
            "announcements": [a.to_dict() for a in self.announcements.values()],
            "activities": [act.to_dict() for act in self.activities],
            "notifications": [n.to_dict() for n in self.notifications]
        }

    def to_json(self) -> str:
        if not self.dirty and self._cached_json is not None:
            return self._cached_json
        self._cached_json = json.dumps(self.to_dict(), indent=2)
        return self._cached_json

    def load_from_json(self, json_str: Optional[str]):
        if json_str and json_str.strip():
            try:
                data = json.loads(json_str)
                # Enforce schema version 2 (5-badge initial cohort state)
                if data.get("schema_version") == SCHEMA_VERSION:
                    self.load_from_dict(data)
                    return
                print("[DataStore] Stored data is prior schema version. Resetting to 5-badge cohort seed.")
            except Exception as e:
                print(f"[DataStore] Failed to load JSON data: {e}, falling back to seed.")
        
        self.reset_to_seed()

    def reset_to_seed(self):
        seed_data = get_initial_seed_data()
        self.load_from_dict(seed_data)

    # --- Users & Profiles ---
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        for u in self.users.values():
            if u.username.lower() == username.lower() or u.email.lower() == username.lower():
                return u
        return None

    def get_all_cosmonauts(self) -> List[User]:
        return [u for u in self.users.values() if u.role == "cosmonaut"]

    def get_cosmonaut_profile(self, user_id: str) -> CosmonautProfile:
        if user_id not in self.profiles:
            self.profiles[user_id] = CosmonautProfile(
                user_id=user_id,
                batch_name="Orion-24",
                assigned_guardian_id="guardian_1",
                guardian_credentials="Ph.D. Distributed Systems & AI, Lead Academy Mentor"
            )
        return self.profiles[user_id]

    def save_user(self, user: User):
        self.users[user.id] = user
        self.mark_dirty()

    def save_profile(self, profile: CosmonautProfile):
        self.profiles[profile.user_id] = profile
        self.mark_dirty()

    def update_cosmonaut_skills(self, user_id: str, skills: List[str]):
        profile = self.get_cosmonaut_profile(user_id)
        profile.skills = [s.strip() for s in skills if s.strip()]
        self.mark_dirty()

    def update_cosmonaut_certifications(self, user_id: str, certifications: List[Dict[str, str]]):
        profile = self.get_cosmonaut_profile(user_id)
        profile.certifications = certifications
        self.mark_dirty()

    # --- Badges ---
    def get_all_badges(self) -> List[Badge]:
        return list(self.badges.values())

    def get_badge(self, badge_id: str) -> Optional[Badge]:
        return self.badges.get(badge_id)

    def save_badge(self, badge: Badge):
        self.badges[badge.id] = badge
        self.mark_dirty()

    def get_badges_for_cosmonaut(self, cosmo_id: str) -> List[Badge]:
        return [b for b in self.badges.values() if b.is_published and cosmo_id in b.assigned_cosmonaut_ids]

    # --- Timelines ---
    def get_timeline(self, badge_id: str, cosmo_id: str) -> Optional[BadgeTimeline]:
        key = f"{badge_id}_{cosmo_id}"
        return self.timelines.get(key)

    def save_timeline(self, timeline: BadgeTimeline):
        key = f"{timeline.badge_id}_{timeline.cosmonaut_id}"
        self.timelines[key] = timeline
        self.mark_dirty()

    # --- Submissions ---
    def get_all_submissions(self) -> List[ProjectSubmission]:
        # Return sorted by submitted_at descending
        return sorted(self.submissions.values(), key=lambda s: s.submitted_at, reverse=True)

    def get_submission(self, sub_id: str) -> Optional[ProjectSubmission]:
        return self.submissions.get(sub_id)

    def get_submissions_for_cosmonaut(self, cosmo_id: str, badge_id: Optional[str] = None) -> List[ProjectSubmission]:
        subs = [s for s in self.submissions.values() if s.cosmonaut_id == cosmo_id]
        if badge_id:
            subs = [s for s in subs if s.badge_id == badge_id]
        return sorted(subs, key=lambda s: (s.badge_id, s.attempt_number))

    def save_submission(self, sub: ProjectSubmission):
        self.submissions[sub.id] = sub
        self.mark_dirty()

    # --- Assessments ---
    def get_all_assessments(self) -> List[AssessmentMarksheet]:
        return sorted(self.assessments.values(), key=lambda a: a.reviewed_at, reverse=True)

    def get_assessment(self, asm_id: str) -> Optional[AssessmentMarksheet]:
        return self.assessments.get(asm_id)

    def get_assessment_for_submission(self, sub_id: str) -> Optional[AssessmentMarksheet]:
        for a in self.assessments.values():
            if a.submission_id == sub_id:
                return a
        return None

    def get_assessments_for_cosmonaut(self, cosmo_id: str, badge_id: Optional[str] = None) -> List[AssessmentMarksheet]:
        asms = [a for a in self.assessments.values() if a.cosmonaut_id == cosmo_id]
        if badge_id:
            asms = [a for a in asms if a.badge_id == badge_id]
        return sorted(asms, key=lambda a: (a.badge_id, a.attempt_number))

    def save_assessment(self, asm: AssessmentMarksheet):
        self.assessments[asm.id] = asm
        self.mark_dirty()

    # --- Materials ---
    def get_materials(self, badge_id: Optional[str] = None) -> List[LearningMaterial]:
        mats = list(self.materials.values())
        if badge_id:
            mats = [m for m in mats if m.badge_id == badge_id]
        return sorted(mats, key=lambda m: m.upload_date, reverse=True)

    def get_material(self, mat_id: str) -> Optional[LearningMaterial]:
        return self.materials.get(mat_id)

    def save_material(self, mat: LearningMaterial):
        self.materials[mat.id] = mat
        self.mark_dirty()

    def delete_material(self, mat_id: str):
        if mat_id in self.materials:
            del self.materials[mat_id]
            self.mark_dirty()

    # --- Extensions ---
    def get_all_extensions(self) -> List[DeadlineExtension]:
        return sorted(self.extensions.values(), key=lambda e: e.requested_at, reverse=True)

    def get_extensions_for_cosmonaut(self, cosmo_id: str) -> List[DeadlineExtension]:
        return [e for e in self.get_all_extensions() if e.cosmonaut_id == cosmo_id]

    def get_extension(self, ext_id: str) -> Optional[DeadlineExtension]:
        return self.extensions.get(ext_id)

    def save_extension(self, ext: DeadlineExtension):
        self.extensions[ext.id] = ext
        self.mark_dirty()

    # --- Announcements ---
    def get_all_announcements(self) -> List[Announcement]:
        return sorted(self.announcements.values(), key=lambda a: a.published_at, reverse=True)

    def get_announcements_for_cosmonaut(self, cosmo_id: str) -> List[Announcement]:
        anns = []
        for a in self.get_all_announcements():
            if a.target_type == "all" or cosmo_id in a.target_cosmonaut_ids:
                anns.append(a)
        return anns

    def save_announcement(self, ann: Announcement):
        self.announcements[ann.id] = ann
        self.mark_dirty()

    def mark_announcement_read(self, ann_id: str, cosmo_id: str):
        if ann_id in self.announcements:
            ann = self.announcements[ann_id]
            if cosmo_id not in ann.read_by_cosmonaut_ids:
                ann.read_by_cosmonaut_ids.append(cosmo_id)
                self.mark_dirty()

    # --- Activities ---
    def get_activities(self, cosmo_id: Optional[str] = None) -> List[ActivityEvent]:
        acts = self.activities
        if cosmo_id:
            acts = [a for a in acts if a.cosmonaut_id == cosmo_id or (a.actor_id == cosmo_id)]
        return sorted(acts, key=lambda a: a.timestamp, reverse=True)

    def add_activity(
        self,
        event_type: str,
        actor_id: str,
        actor_name: str,
        cosmonaut_id: str,
        badge_id: str,
        summary: str,
        details: str = ""
    ):
        act_id = f"act_{len(self.activities) + 1}_{int(datetime.datetime.now().timestamp() * 1000)}"
        event = ActivityEvent(
            id=act_id,
            timestamp=current_iso_timestamp(),
            event_type=event_type,
            actor_id=actor_id,
            actor_name=actor_name,
            cosmonaut_id=cosmonaut_id,
            badge_id=badge_id,
            summary=summary,
            details=details
        )
        self.activities.insert(0, event)
        self.mark_dirty()

    # --- Notifications ---
    def get_notifications(self, user_id: str) -> List[Notification]:
        notifs = [n for n in self.notifications if n.recipient_id == user_id]
        return sorted(notifs, key=lambda n: n.created_at, reverse=True)

    def add_notification(self, recipient_id: str, title: str, message: str, link_section: str = ""):
        notif_id = f"notif_{len(self.notifications) + 1}"
        notif = Notification(
            id=notif_id,
            recipient_id=recipient_id,
            title=title,
            message=message,
            link_section=link_section,
            created_at=current_iso_timestamp(),
            is_read=False
        )
        self.notifications.insert(0, notif)
        self.mark_dirty()

    def mark_notification_read(self, notif_id: str):
        for n in self.notifications:
            if n.id == notif_id:
                n.is_read = True
                self.mark_dirty()
                break

    def mark_all_notifications_read(self, user_id: str):
        for n in self.notifications:
            if n.recipient_id == user_id:
                n.is_read = True
        self.mark_dirty()

# Global store instance
store = DataStore()
