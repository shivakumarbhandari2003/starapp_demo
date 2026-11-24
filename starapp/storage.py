"""
STARAPP CENTRALIZED STORAGE & DATA-ACCESS LAYER
Acts as the authoritative bridge between SQLite and both Guardian and Cosmonaut portals.
SQLite is the primary structured database; exports/imports binary snapshots to IndexedDB.
"""

import json
import datetime
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from starapp.models import (
    User, CosmonautProfile, Badge, BadgeTimeline, ProjectSubmission,
    AssessmentMarksheet, LearningMaterial, DeadlineExtension,
    Announcement, ActivityEvent, Notification, ReviewerProjectPrompt, current_iso_timestamp
)
from starapp.seed_data import get_initial_seed_data
from starapp.database import db, DatabaseManager, SCHEMA_VERSION
try:
    from starapp.repositories import (
        UserRepository, BadgeRepository, TimelineRepository, AssessmentRepository,
        MappingRepository, MaterialRepository, ExtensionRepository, AnnouncementRepository
    )
except ImportError:
    UserRepository = BadgeRepository = TimelineRepository = AssessmentRepository = None
    MappingRepository = MaterialRepository = ExtensionRepository = AnnouncementRepository = None

class DataStore:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or db
        # Modular SQLite repositories (resilient initialization)
        self.user_repo = UserRepository(self.db) if UserRepository else None
        self.badge_repo = BadgeRepository(self.db) if BadgeRepository else None
        self.timeline_repo = TimelineRepository(self.db) if TimelineRepository else None
        self.assessment_repo = AssessmentRepository(self.db) if AssessmentRepository else None
        self.mapping_repo = MappingRepository(self.db) if MappingRepository else None
        self.material_repo = MaterialRepository(self.db) if MaterialRepository else None
        self.extension_repo = ExtensionRepository(self.db) if ExtensionRepository else None
        self.announcement_repo = AnnouncementRepository(self.db) if AnnouncementRepository else None

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
        self.band_mappings: List[Dict[str, Any]] = []
        self.mapping_requests: List[Dict[str, Any]] = []
        self.reviewer_projects: Dict[str, Any] = {}
        self.is_loaded = False
        self.version: int = 1
        self.dirty: bool = False
        self._cached_json: Optional[str] = None

        # Auto-load existing authoritative SQLite state if available
        try:
            if self.db and self.db.conn:
                row = self.db.conn.execute("SELECT COUNT(*) FROM users").fetchone()
                if row and row[0] > 0:
                    exported = self.db.export_to_dict()
                    if exported.get("users"):
                        self.load_from_dict(exported)
        except Exception:
            pass

    def mark_dirty(self):
        """Flags store as modified to trigger targeted SQLite export and persistence."""
        self.version += 1
        self.dirty = True
        self._cached_json = None

    def load_from_dict(self, data: Dict[str, Any]):
        """Loads domain objects into in-memory lookup cache from structured dictionary."""
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
        self.band_mappings = data.get("band_mappings", [])
        self.mapping_requests = data.get("mapping_requests", [])
        rpp_raw = data.get("reviewer_projects") or data.get("reviewer_project_prompts") or []
        if isinstance(rpp_raw, list):
            self.reviewer_projects = {p["id"]: ReviewerProjectPrompt.from_dict(p) for p in rpp_raw if isinstance(p, dict) and "id" in p}
        elif isinstance(rpp_raw, dict):
            self.reviewer_projects = {k: ReviewerProjectPrompt.from_dict(v) for k, v in rpp_raw.items()}
        else:
            self.reviewer_projects = {}
        self.is_loaded = True
        self.version += 1
        self.dirty = False
        self._cached_json = None

    def to_dict(self) -> Dict[str, Any]:
        """Returns structured dictionary representation from SQLite authoritative state."""
        return self.db.export_to_dict()

    def to_json(self) -> str:
        if not self.dirty and self._cached_json is not None:
            return self._cached_json
        self._cached_json = json.dumps(self.to_dict(), indent=2)
        return self._cached_json

    def export_sqlite_base64(self) -> str:
        """Exports the SQLite database file as a base64 encoded string for IndexedDB."""
        return self.db.export_base64()

    def load_from_json(self, json_str: Optional[str], sqlite_b64: Optional[str] = None):
        """
        Authoritative initialization:
        1. If SQLite binary base64 is present from IndexedDB, restore SQLite directly.
        2. If JSON snapshot is present, migrate JSON records into SQLite.
        3. Otherwise, initialize SQLite with initial seed dataset.
        """
        # 1. Restore from SQLite binary snapshot if available
        if sqlite_b64 and sqlite_b64.strip():
            try:
                self.db.import_base64(sqlite_b64)
                data = self.db.export_to_dict()
                if data.get("users"):
                    self.load_from_dict(data)
                    return
            except Exception as e:
                print(f"[DataStore] Failed to restore from SQLite binary snapshot: {e}")

        # 2. Migrate from JSON snapshot if valid
        if json_str and json_str.strip():
            try:
                data = json.loads(json_str)
                # Migrate JSON into SQLite
                self.db.migrate_from_dict(data)
                exported = self.db.export_to_dict()
                self.load_from_dict(exported)
                return
            except Exception as e:
                print(f"[DataStore] Failed to migrate from JSON snapshot: {e}, resetting to seed.")

        # 3. Check if existing authoritative SQLite database already has records
        try:
            if self.db and self.db.conn:
                row = self.db.conn.execute("SELECT COUNT(*) FROM users").fetchone()
                if row and row[0] > 0:
                    exported = self.db.export_to_dict()
                    if exported.get("users"):
                        self.load_from_dict(exported)
                        return
        except Exception as e:
            print(f"[DataStore] Failed to load existing SQLite database: {e}")

        # 4. Fallback to clean seed only if SQLite database is completely empty
        self.reset_to_seed()

    def reset_to_seed(self):
        """Resets SQLite database and in-memory cache to the baseline 5-badge cohort dataset."""
        self.db.clear_all_tables()
        seed_data = get_initial_seed_data()
        self.db.migrate_from_dict(seed_data)
        exported = self.db.export_to_dict()
        self.load_from_dict(exported)
        self.mark_dirty()

    # --- Users & Profiles ---
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        if not user_id:
            return None
        # Check in-memory cache
        if user_id in self.users:
            return self.users[user_id]
        # Query SQLite directly (for demo users, etc.)
        row = self.db.conn.execute("SELECT * FROM users WHERE id = ? OR lower(username) = ?", (user_id, user_id.lower())).fetchone()
        if row:
            roles = [r[0] for r in self.db.conn.execute("SELECT role_id FROM user_role_assignments WHERE user_id = ?", (row["id"],)).fetchall()]
            band_row = self.db.conn.execute("SELECT band_code, track_code FROM user_band_memberships WHERE user_id = ?", (row["id"],)).fetchone()
            user_role = row["primary_role"] if "primary_role" in row.keys() else row["role"]
            user_band = row["band"] if "band" in row.keys() and row["band"] else (band_row["band_code"] if band_row else "")
            user_track = (band_row["track_code"] if band_row else "") or (row["learning_track"] if "learning_track" in row.keys() else "")
            user = User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                role=user_role,
                name=row["name"],
                avatar=row["avatar"] or row["name"][:2].upper(),
                roles=roles if roles else [user_role],
                band=user_band,
                learning_track=user_track
            )
            self.users[row["id"]] = user
            if user_id != row["id"]:
                self.users[user_id] = user
            return user
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        u_clean = username.lower().strip()
        for u in self.users.values():
            if u.username.lower() == u_clean or u.email.lower() == u_clean:
                return u
        # Query SQLite directly
        row = self.db.conn.execute(
            "SELECT * FROM users WHERE lower(username) = ? OR lower(email) = ?",
            (u_clean, u_clean)
        ).fetchone()
        if row:
            return self.get_user_by_id(row["id"])
        return None

    def get_all_cosmonauts(self) -> List[User]:
        # All members across B1 to B6 are cosmonauts/cadets
        return [
            u for u in self.users.values()
            if u.role in ("cosmonaut", "cadet") or "cosmonaut" in getattr(u, "roles", []) or "cadet" in getattr(u, "roles", []) or (u.id != "guardian_1" and getattr(u, "band", "") in ("B1", "B2", "B3", "B4", "B5", "B6"))
        ]

    def get_all_users(self) -> List[User]:
        return list(self.users.values())

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
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO users (id, username, email, name, primary_role, avatar, status, is_demo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'active', 0, ?)
                """,
                (user.id, user.username, user.email, user.name, user.role, user.avatar, current_iso_timestamp())
            )
            for r in getattr(user, "roles", [user.role]):
                self.db.conn.execute(
                    "INSERT OR IGNORE INTO user_role_assignments (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                    (user.id, r, current_iso_timestamp())
                )
        self.mark_dirty()

    def save_profile(self, profile: CosmonautProfile):
        self.profiles[profile.user_id] = profile
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO cosmonaut_profiles (user_id, batch_name, assigned_guardian_id, guardian_credentials, skills_json, certifications_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.user_id,
                    profile.batch_name,
                    profile.assigned_guardian_id,
                    profile.guardian_credentials,
                    json.dumps(profile.skills),
                    json.dumps(profile.certifications)
                )
            )
        self.mark_dirty()

    def update_cosmonaut_skills(self, user_id: str, skills: List[str]):
        profile = self.get_cosmonaut_profile(user_id)
        profile.skills = [s.strip() for s in skills if s.strip()]
        self.save_profile(profile)

    def update_cosmonaut_certifications(self, user_id: str, certifications: List[Dict[str, str]]):
        profile = self.get_cosmonaut_profile(user_id)
        profile.certifications = certifications
        self.save_profile(profile)

    # --- Badges ---
    def get_all_badges(self) -> List[Badge]:
        if self.db and self.db.conn:
            try:
                rows = self.db.conn.execute("SELECT * FROM badges").fetchall()
                for r in rows:
                    rd = dict(r)
                    b_id = rd.get("id")
                    if not b_id:
                        continue
                    if b_id in self.badges:
                        b = self.badges[b_id]
                        b.is_published = bool(rd.get("is_published", 1))
                        b.is_allocated = bool(rd.get("is_allocated", 1))
                        b.workflow_status = rd.get("workflow_status", "approved")
                        if rd.get("assigned_reviewer_id"):
                            b.assigned_reviewer_id = rd.get("assigned_reviewer_id")
                        if rd.get("assigned_cosmonaut_ids_json"):
                            try:
                                b.assigned_cosmonaut_ids = json.loads(rd["assigned_cosmonaut_ids_json"])
                            except Exception:
                                pass
                        if rd.get("default_timeline_json"):
                            try:
                                b.default_timeline = json.loads(rd["default_timeline_json"])
                            except Exception:
                                pass
                    else:
                        outcomes = []
                        if rd.get("learning_outcomes_json"):
                            try: outcomes = json.loads(rd["learning_outcomes_json"])
                            except Exception: pass
                        topics = []
                        if rd.get("learning_topics_json"):
                            try: topics = json.loads(rd["learning_topics_json"])
                            except Exception: pass
                        cids = []
                        if rd.get("assigned_cosmonaut_ids_json"):
                            try: cids = json.loads(rd["assigned_cosmonaut_ids_json"])
                            except Exception: pass
                        dt = {}
                        if rd.get("default_timeline_json"):
                            try: dt = json.loads(rd["default_timeline_json"])
                            except Exception: pass

                        self.badges[b_id] = Badge(
                            id=b_id,
                            code=rd.get("code", ""),
                            title=rd.get("title", ""),
                            category=rd.get("category", "Foundations"),
                            description=rd.get("description", ""),
                            learning_outcomes=outcomes,
                            learning_topics=topics,
                            prerequisites=[],
                            project_requirements=rd.get("project_requirements", ""),
                            is_published=bool(rd.get("is_published", 1)),
                            is_allocated=bool(rd.get("is_allocated", 1)),
                            target_band=rd.get("target_band", ""),
                            power=rd.get("power", ""),
                            capability=rd.get("capability", ""),
                            skill=rd.get("skill", ""),
                            prompt_json=rd.get("prompt_json", "{}"),
                            workflow_status=rd.get("workflow_status", "approved"),
                            creator_id=rd.get("creator_id", ""),
                            assigned_reviewer_id=rd.get("assigned_reviewer_id", ""),
                            assigned_cosmonaut_ids=cids,
                            default_timeline=dt,
                            created_at=rd.get("created_at", ""),
                            updated_at=rd.get("updated_at", "")
                        )
            except Exception:
                pass
        return list(self.badges.values())

    def get_badge(self, badge_id: str) -> Optional[Badge]:
        if not badge_id:
            return None
        if badge_id in self.badges:
            return self.badges[badge_id]
        if self.db and self.db.conn:
            try:
                row = self.db.conn.execute("SELECT * FROM badges WHERE id = ? OR code = ?", (badge_id, badge_id)).fetchone()
                if row:
                    rd = dict(row)
                    b_id = rd["id"]
                    outcomes = []
                    if rd.get("learning_outcomes_json"):
                        try: outcomes = json.loads(rd["learning_outcomes_json"])
                        except Exception: pass
                    topics = []
                    if rd.get("learning_topics_json"):
                        try: topics = json.loads(rd["learning_topics_json"])
                        except Exception: pass
                    cids = []
                    if rd.get("assigned_cosmonaut_ids_json"):
                        try: cids = json.loads(rd["assigned_cosmonaut_ids_json"])
                        except Exception: pass
                    dt = {}
                    if rd.get("default_timeline_json"):
                        try: dt = json.loads(rd["default_timeline_json"])
                        except Exception: pass

                    b_obj = Badge(
                        id=b_id,
                        code=rd.get("code", ""),
                        title=rd.get("title", ""),
                        category=rd.get("category", "Foundations"),
                        description=rd.get("description", ""),
                        learning_outcomes=outcomes,
                        learning_topics=topics,
                        prerequisites=[],
                        project_requirements=rd.get("project_requirements", ""),
                        is_published=bool(rd.get("is_published", 1)),
                        is_allocated=bool(rd.get("is_allocated", 1)),
                        target_band=rd.get("target_band", ""),
                        power=rd.get("power", ""),
                        capability=rd.get("capability", ""),
                        skill=rd.get("skill", ""),
                        prompt_json=rd.get("prompt_json", "{}"),
                        workflow_status=rd.get("workflow_status", "approved"),
                        creator_id=rd.get("creator_id", ""),
                        assigned_reviewer_id=rd.get("assigned_reviewer_id", ""),
                        assigned_cosmonaut_ids=cids,
                        default_timeline=dt,
                        created_at=rd.get("created_at", ""),
                        updated_at=rd.get("updated_at", "")
                    )
                    self.badges[b_id] = b_obj
                    return b_obj
            except Exception:
                pass
        return None

    def save_badge(self, badge: Badge):
        self.badges[badge.id] = badge
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO badges (
                    id, code, title, category, description,
                    learning_outcomes_json, learning_topics_json, project_requirements,
                    is_published, is_allocated, target_band, power, capability, skill,
                    prompt_json, workflow_status, creator_id, assigned_reviewer_id,
                    assigned_cosmonaut_ids_json, default_timeline_json, created_at, updated_at,
                    passing_percentage, published_at, published_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    badge.id,
                    badge.code,
                    badge.title,
                    badge.category,
                    badge.description,
                    json.dumps(badge.learning_outcomes),
                    json.dumps(badge.learning_topics),
                    badge.project_requirements,
                    1 if badge.is_published else 0,
                    1 if getattr(badge, "is_allocated", True) else 0,
                    getattr(badge, "target_band", None) or None,
                    getattr(badge, "power", None) or None,
                    getattr(badge, "capability", None) or None,
                    getattr(badge, "skill", None) or None,
                    getattr(badge, "prompt_json", None) or None,
                    getattr(badge, "workflow_status", "approved"),
                    getattr(badge, "creator_id", None) or "guardian_1",
                    getattr(badge, "assigned_reviewer_id", None) or None,
                    json.dumps(badge.assigned_cosmonaut_ids),
                    json.dumps(badge.default_timeline),
                    getattr(badge, "created_at", current_iso_timestamp()),
                    current_iso_timestamp(),
                    getattr(badge, "passing_percentage", 70.0),
                    getattr(badge, "published_at", ""),
                    getattr(badge, "published_by", "")
                )
            )
            # Update prerequisites
            self.db.conn.execute("DELETE FROM badge_prerequisites WHERE badge_id = ?", (badge.id,))
            for prereq in badge.prerequisites:
                self.db.conn.execute("INSERT OR IGNORE INTO badge_prerequisites (badge_id, prerequisite_badge_id) VALUES (?, ?)", (badge.id, prereq))

            # Update normalized power, capability, skill associations
            if getattr(badge, "power", None):
                self.db.conn.execute("INSERT OR REPLACE INTO badge_powers (badge_id, power_name) VALUES (?, ?)", (badge.id, badge.power))
            if getattr(badge, "capability", None):
                self.db.conn.execute("INSERT OR REPLACE INTO badge_capabilities (badge_id, capability_name, is_custom) VALUES (?, ?, 0)", (badge.id, badge.capability))
            if getattr(badge, "skill", None):
                self.db.conn.execute("INSERT OR REPLACE INTO badge_skills (badge_id, skill_name, is_custom) VALUES (?, ?, 0)", (badge.id, badge.skill))
        self.mark_dirty()

    def get_badges_for_cosmonaut(self, cosmo_id: str) -> List[Badge]:
        target_ids = {cosmo_id}

        # 1. Collect badge IDs from in-memory timelines
        mapped_badge_ids = set()
        for t in self.timelines.values():
            if getattr(t, "cosmonaut_id", "") in target_ids:
                mapped_badge_ids.add(t.badge_id)

        # 2. Collect badge IDs from SQLite badge_timelines table
        if self.db and getattr(self.db, "conn", None):
            try:
                placeholders = ",".join(["?"] * len(target_ids))
                rows = self.db.conn.execute(
                    f"SELECT badge_id FROM badge_timelines WHERE cosmonaut_id IN ({placeholders})",
                    list(target_ids)
                ).fetchall()
                for r in rows:
                    mapped_badge_ids.add(r[0])
            except Exception:
                pass

        # 3. Collect badge IDs from band_mappings
        try:
            mappings = self.get_band_mappings()
            for m in mappings:
                m_cosmonauts = m.get("cosmonauts", [])
                if any(cid in m_cosmonauts for cid in target_ids):
                    b_ref = m.get("badge", "")
                    for b in self.badges.values():
                        if b.title == b_ref or b.code == b_ref or b.id == b_ref:
                            mapped_badge_ids.add(b.id)
        except Exception:
            pass

        # 4. Filter badges: direct assignment or mapped
        result = []
        for b in self.badges.values():
            is_assigned = any(cid in getattr(b, "assigned_cosmonaut_ids", []) for cid in target_ids)
            is_mapped = b.id in mapped_badge_ids
            if (is_assigned and (b.is_published or getattr(b, "is_allocated", False))) or is_mapped or (b.is_published and is_assigned):
                if b not in result:
                    result.append(b)
        return result

    # --- Timelines ---
    def get_timeline(self, badge_id: str, cosmo_id: str) -> Optional[BadgeTimeline]:
        key = f"{badge_id}_{cosmo_id}"
        return self.timelines.get(key)

    def save_timeline(self, timeline: BadgeTimeline):
        key = f"{timeline.badge_id}_{timeline.cosmonaut_id}"
        self.timelines[key] = timeline
        try:
            with self.db.conn:
                self.db.conn.execute(
                    """
                    INSERT OR REPLACE INTO badge_timelines (
                        badge_id, cosmonaut_id, assignment_date, publication_date,
                        learning_start_date, learning_end_date, project_start_date, project_end_date,
                        submission_deadline, review_date, expected_award_date, actual_award_date, status,
                        reviewer_id, review_window_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timeline.badge_id,
                        timeline.cosmonaut_id,
                        timeline.assignment_date,
                        timeline.publication_date,
                        timeline.learning_start_date,
                        timeline.learning_end_date,
                        timeline.project_start_date,
                        timeline.project_end_date,
                        timeline.submission_deadline,
                        timeline.review_date,
                        timeline.expected_award_date,
                        timeline.actual_award_date,
                        timeline.status,
                        getattr(timeline, "reviewer_id", ""),
                        getattr(timeline, "review_window_json", "[]")
                    )
                )
        except Exception:
            pass
        self.mark_dirty()

    # --- Submissions ---
    def get_all_submissions(self) -> List[ProjectSubmission]:
        return sorted(self.submissions.values(), key=lambda s: s.submitted_at, reverse=True)

    def get_submission(self, sub_id: str) -> Optional[ProjectSubmission]:
        if sub_id in self.submissions:
            return self.submissions[sub_id]
        if self.db and self.db.conn:
            try:
                row = self.db.conn.execute("SELECT * FROM project_submissions WHERE id = ?", (sub_id,)).fetchone()
                if row:
                    sub = ProjectSubmission.from_dict(dict(row))
                    self.submissions[sub_id] = sub
                    return sub
            except Exception:
                pass
        return None

    def get_submissions_for_cosmonaut(self, cosmo_id: str, badge_id: Optional[str] = None) -> List[ProjectSubmission]:
        subs = [s for s in self.submissions.values() if s.cosmonaut_id == cosmo_id]
        if badge_id:
            subs = [s for s in subs if s.badge_id == badge_id]
        return sorted(subs, key=lambda s: (s.badge_id, s.attempt_number))

    def save_submission(self, sub: ProjectSubmission):
        self.submissions[sub.id] = sub
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO project_submissions (
                    id, badge_id, cosmonaut_id, attempt_number, submission_type,
                    payload, file_name, submitted_at, status, pdf_name, pdf_payload,
                    code_name, code_payload, github_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sub.id,
                    sub.badge_id,
                    sub.cosmonaut_id,
                    sub.attempt_number,
                    sub.submission_type,
                    sub.payload,
                    sub.file_name,
                    sub.submitted_at,
                    sub.status,
                    getattr(sub, "pdf_name", ""),
                    getattr(sub, "pdf_payload", ""),
                    getattr(sub, "code_name", ""),
                    getattr(sub, "code_payload", ""),
                    getattr(sub, "github_url", "")
                )
            )
        self.mark_dirty()

    # --- Assessments ---
    def get_all_assessments(self) -> List[AssessmentMarksheet]:
        return sorted(self.assessments.values(), key=lambda a: a.reviewed_at, reverse=True)

    def get_assessment(self, asm_id: str) -> Optional[AssessmentMarksheet]:
        return self.assessments.get(asm_id)

    def get_assessment_for_submission(self, sub_id: str) -> Optional[AssessmentMarksheet]:
        # Return Guardian final assessment if present, otherwise latest assessment
        sub_asms = [a for a in self.assessments.values() if a.submission_id == sub_id]
        if not sub_asms:
            return None
        guardian_asm = next((a for a in sub_asms if getattr(a, "assessor_role", "guardian") == "guardian"), None)
        return guardian_asm or sub_asms[-1]

    def get_all_assessments_for_submission(self, sub_id: str) -> List[AssessmentMarksheet]:
        return [a for a in self.assessments.values() if a.submission_id == sub_id]

    def get_reviewer_assessment_for_submission(self, sub_id: str) -> Optional[AssessmentMarksheet]:
        for a in self.assessments.values():
            if a.submission_id == sub_id and getattr(a, "assessor_role", "") == "reviewer":
                return a
        return None

    def get_guardian_assessment_for_submission(self, sub_id: str) -> Optional[AssessmentMarksheet]:
        for a in self.assessments.values():
            if a.submission_id == sub_id and getattr(a, "assessor_role", "guardian") == "guardian":
                return a
        return None

    def get_assessments_for_cosmonaut(self, cosmo_id: str, badge_id: Optional[str] = None) -> List[AssessmentMarksheet]:
        asms = [a for a in self.assessments.values() if a.cosmonaut_id == cosmo_id]
        if badge_id:
            asms = [a for a in asms if a.badge_id == badge_id]
        return sorted(asms, key=lambda a: (a.badge_id, a.attempt_number))

    def save_assessment(self, asm: AssessmentMarksheet):
        self.assessments[asm.id] = asm
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO assessment_marksheets (
                    id, submission_id, attempt_number, badge_id, cosmonaut_id,
                    reviewer_id, reviewer_name, reviewed_at, decision,
                    business_understanding, architecture_report, technical_knowledge,
                    presentation, qa, total_marks, percentage,
                    strength_areas, improvement_areas, overall_feedback,
                    assessor_role, remarks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asm.id,
                    asm.submission_id,
                    asm.attempt_number,
                    asm.badge_id,
                    asm.cosmonaut_id,
                    asm.reviewer_id,
                    asm.reviewer_name,
                    asm.reviewed_at,
                    asm.decision,
                    asm.business_understanding,
                    asm.architecture_report,
                    asm.technical_knowledge,
                    asm.presentation,
                    asm.qa,
                    asm.total_marks,
                    asm.percentage,
                    asm.strength_areas,
                    asm.improvement_areas,
                    asm.overall_feedback,
                    getattr(asm, "assessor_role", "guardian"),
                    getattr(asm, "remarks", "")
                )
            )
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
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO learning_materials (
                    id, badge_id, topic, title, description, material_type, url_or_data, upload_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mat.id,
                    mat.badge_id,
                    mat.topic,
                    mat.title,
                    mat.description,
                    mat.material_type,
                    mat.url_or_data,
                    mat.upload_date
                )
            )
        self.mark_dirty()

    def delete_material(self, mat_id: str):
        if mat_id in self.materials:
            del self.materials[mat_id]
        with self.db.conn:
            self.db.conn.execute("DELETE FROM learning_materials WHERE id = ?", (mat_id,))
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
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO deadline_extensions (
                    id, badge_id, cosmonaut_id, current_deadline, proposed_deadline,
                    reason, status, guardian_response, requested_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ext.id,
                    ext.badge_id,
                    ext.cosmonaut_id,
                    ext.current_deadline,
                    ext.proposed_deadline,
                    ext.reason,
                    ext.status,
                    ext.guardian_response,
                    ext.requested_at,
                    ext.decided_at
                )
            )
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
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO announcements (
                    id, title, message, author_id, author_name, target_type, badge_id, published_at, expiry_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ann.id,
                    ann.title,
                    ann.message,
                    ann.author_id,
                    ann.author_name,
                    ann.target_type,
                    ann.badge_id,
                    ann.published_at,
                    ann.expiry_date
                )
            )
            for recip in ann.target_cosmonaut_ids:
                self.db.conn.execute("INSERT OR IGNORE INTO announcement_recipients (announcement_id, cosmonaut_id) VALUES (?, ?)", (ann.id, recip))
            for reader in ann.read_by_cosmonaut_ids:
                self.db.conn.execute("INSERT OR IGNORE INTO announcement_read_receipts (announcement_id, cosmonaut_id, read_at) VALUES (?, ?, ?)", (ann.id, reader, current_iso_timestamp()))
        self.mark_dirty()

    def mark_announcement_read(self, ann_id: str, cosmo_id: str):
        if ann_id in self.announcements:
            ann = self.announcements[ann_id]
            if cosmo_id not in ann.read_by_cosmonaut_ids:
                ann.read_by_cosmonaut_ids.append(cosmo_id)
                with self.db.conn:
                    self.db.conn.execute("INSERT OR IGNORE INTO announcement_read_receipts (announcement_id, cosmonaut_id, read_at) VALUES (?, ?, ?)", (ann_id, cosmo_id, current_iso_timestamp()))
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
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO activity_events (
                    id, timestamp, event_type, actor_id, actor_name, cosmonaut_id, badge_id, summary, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event.id, event.timestamp, event.event_type, event.actor_id, event.actor_name, event.cosmonaut_id, event.badge_id, event.summary, event.details)
            )
        self.mark_dirty()

    # --- Notifications ---
    def get_notifications(self, user_id: str) -> List[Notification]:
        notifs = [n for n in self.notifications if n.recipient_id == user_id]
        return sorted(notifs, key=lambda n: n.created_at, reverse=True)

    def add_notification(self, recipient_id: str, title: str, message: str, link_section: str = "", event_type: str = "", related_badge_id: str = ""):
        notif_id = f"notif_{len(self.notifications) + 1}_{int(datetime.datetime.now().timestamp() * 1000)}"
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
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO notifications (
                    id, recipient_id, title, message, link_section, created_at, is_read, event_type, related_badge_id
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (notif.id, notif.recipient_id, notif.title, notif.message, notif.link_section, notif.created_at, event_type, related_badge_id)
            )
        self.mark_dirty()

    def mark_notification_read(self, notif_id: str):
        for n in self.notifications:
            if n.id == notif_id:
                n.is_read = True
                with self.db.conn:
                    self.db.conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
                self.mark_dirty()
                break

    def mark_all_notifications_read(self, user_id: str):
        for n in self.notifications:
            if n.recipient_id == user_id:
                n.is_read = True
        with self.db.conn:
            self.db.conn.execute("UPDATE notifications SET is_read = 1 WHERE recipient_id = ?", (user_id,))
        self.mark_dirty()

    # --- Band Mappings & Requests ---
    def get_band_mappings(self) -> List[Dict[str, Any]]:
        if not hasattr(self, "band_mappings") or self.band_mappings is None:
            self.band_mappings = []
        return self.band_mappings

    def save_band_mapping(self, mapping: Dict[str, Any]):
        if not hasattr(self, "band_mappings") or self.band_mappings is None:
            self.band_mappings = []
        m_id = mapping.get("id")
        replaced = False
        for idx, m in enumerate(self.band_mappings):
            if m.get("id") == m_id:
                self.band_mappings[idx] = mapping
                replaced = True
                break
        if not replaced:
            self.band_mappings.insert(0, mapping)
        b_id = mapping.get("badge_id", "")
        if not b_id and mapping.get("badge"):
            b_val = mapping.get("badge")
            for b in self.get_all_badges():
                if b.title == b_val or b.code == b_val or b.id == b_val:
                    b_id = b.id
                    mapping["badge_id"] = b.id
                    break
        with self.db.conn:
            self.db.conn.execute(
                "INSERT OR REPLACE INTO band_mappings (id, band, badge_id, data_json) VALUES (?, ?, ?, ?)",
                (m_id, mapping.get("band", "B1"), b_id, json.dumps(mapping))
            )
        self.mark_dirty()

    def delete_band_mapping(self, mapping_id: str):
        if hasattr(self, "band_mappings") and self.band_mappings:
            self.band_mappings = [m for m in self.band_mappings if m.get("id") != mapping_id]
        with self.db.conn:
            self.db.conn.execute("DELETE FROM band_mappings WHERE id = ?", (mapping_id,))
        self.mark_dirty()

    def get_mapping_requests(self) -> List[Dict[str, Any]]:
        if not hasattr(self, "mapping_requests") or self.mapping_requests is None:
            self.mapping_requests = []
        return self.mapping_requests

    def add_mapping_request(self, req: Dict[str, Any]):
        if not hasattr(self, "mapping_requests") or self.mapping_requests is None:
            self.mapping_requests = []
        req_id = req.get("id")
        replaced = False
        for idx, r in enumerate(self.mapping_requests):
            if r.get("id") == req_id:
                self.mapping_requests[idx] = req
                replaced = True
                break
        if not replaced:
            self.mapping_requests.append(req)
        with self.db.conn:
            self.db.conn.execute(
                "INSERT OR REPLACE INTO mapping_requests (id, band, reviewer_id, status, data_json) VALUES (?, ?, ?, ?, ?)",
                (req_id, req.get("band", ""), req.get("reviewer_id", ""), req.get("status", "pending"), json.dumps(req))
            )
        self.mark_dirty()

    def update_mapping_request_status(self, req_id: str, status: str):
        if not hasattr(self, "mapping_requests") or not self.mapping_requests:
            return
        for r in self.mapping_requests:
            legacy_id = f"req_{r.get('band')}_{r.get('reviewer_id')}"
            if r.get("id") == req_id or legacy_id == req_id or r.get("id", "").startswith(req_id):
                r["status"] = status
                actual_id = r.get("id")
                with self.db.conn:
                    self.db.conn.execute("UPDATE mapping_requests SET status = ?, data_json = ? WHERE id = ?", (status, json.dumps(r), actual_id))
                self.mark_dirty()
                break

    def delete_mapping_request(self, req_id: str):
        if hasattr(self, "mapping_requests") and self.mapping_requests:
            to_delete = []
            for r in self.mapping_requests:
                legacy_id = f"req_{r.get('band')}_{r.get('reviewer_id')}"
                if r.get("id") == req_id or legacy_id == req_id or r.get("id", "").startswith(req_id):
                    to_delete.append(r.get("id"))
            self.mapping_requests = [r for r in self.mapping_requests if r.get("id") not in to_delete]
            with self.db.conn:
                for del_id in to_delete:
                    self.db.conn.execute("DELETE FROM mapping_requests WHERE id = ?", (del_id,))
            self.mark_dirty()

    def clear_mapping_requests(self, band: Optional[str] = None):
        if not hasattr(self, "mapping_requests"):
            self.mapping_requests = []
            return
        if band:
            self.mapping_requests = [r for r in self.mapping_requests if r.get("band") != band]
            with self.db.conn:
                self.db.conn.execute("DELETE FROM mapping_requests WHERE band = ?", (band,))
        else:
            self.mapping_requests = []
            with self.db.conn:
                self.db.conn.execute("DELETE FROM mapping_requests")
        self.mark_dirty()

    # --- Reviewer Project Prompts & Mapping Uncoupling ---
    def save_reviewer_project_prompt(self, prompt: Any):
        if hasattr(prompt, "to_dict"):
            p_dict = prompt.to_dict()
            p_id = prompt.id
            obj = prompt
        elif isinstance(prompt, dict):
            p_dict = prompt
            p_id = prompt.get("id") or f"proj_{prompt.get('badge_id')}_{prompt.get('reviewer_id')}"
            obj = ReviewerProjectPrompt.from_dict(prompt)
        else:
            return

        if not hasattr(self, "reviewer_projects") or not isinstance(self.reviewer_projects, dict):
            self.reviewer_projects = {}
        self.reviewer_projects[p_id] = obj

        try:
            with self.db.conn:
                self.db.conn.execute("""
                    INSERT OR REPLACE INTO reviewer_project_prompts (
                        id, badge_id, reviewer_id, cosmonaut_ids_json, title, description,
                        deliverables_json, requirements_text, outcomes_json, status, created_at, sent_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p_id,
                    p_dict.get("badge_id"),
                    p_dict.get("reviewer_id"),
                    json.dumps(p_dict.get("cosmonaut_ids", [])),
                    p_dict.get("title", ""),
                    p_dict.get("description", ""),
                    json.dumps(p_dict.get("deliverables", {})),
                    json.dumps(p_dict.get("requirements", [])),
                    json.dumps(p_dict.get("outcomes", [])),
                    p_dict.get("status", "draft"),
                    p_dict.get("created_at") or current_iso_timestamp(),
                    p_dict.get("sent_at")
                ))
        except Exception:
            pass
        self.mark_dirty()

    def get_reviewer_project_prompts(self, badge_id: Optional[str] = None, reviewer_id: Optional[str] = None) -> List[Any]:
        results = []
        try:
            if self.db and self.db.conn:
                query = "SELECT * FROM reviewer_project_prompts WHERE 1=1"
                params = []
                if badge_id:
                    query += " AND badge_id = ?"
                    params.append(badge_id)
                if reviewer_id:
                    query += " AND reviewer_id = ?"
                    params.append(reviewer_id)
                query += " ORDER BY created_at DESC"
                rows = self.db.conn.execute(query, tuple(params)).fetchall()
                for r in rows:
                    d = dict(r)
                    results.append(ReviewerProjectPrompt.from_dict(d))
        except Exception:
            pass

        if not results and hasattr(self, "reviewer_projects") and self.reviewer_projects:
            for p in self.reviewer_projects.values():
                if badge_id and getattr(p, "badge_id", "") != badge_id:
                    continue
                if reviewer_id and getattr(p, "reviewer_id", "") != reviewer_id:
                    continue
                results.append(p)
        return results

    def get_project_prompt_for_cadet(self, badge_id: str, cosmonaut_id: str) -> Optional[Any]:
        # First verify the cadet is actually allocated/mapped to this badge
        tl = self.get_timeline(badge_id, cosmonaut_id)
        is_allocated = (tl is not None)
        assigned_rev_id = getattr(tl, "reviewer_id", "") if tl else ""
        if not is_allocated:
            b_obj = self.get_badge(badge_id)
            if b_obj and cosmonaut_id in getattr(b_obj, "assigned_cosmonaut_ids", []):
                is_allocated = True
                assigned_rev_id = getattr(b_obj, "assigned_reviewer_id", "")
            else:
                for m in self.get_band_mappings():
                    m_b = m.get("badge_id") or m.get("badge")
                    if (m_b == badge_id or (b_obj and m_b in (b_obj.title, b_obj.code, b_obj.id))) and cosmonaut_id in m.get("cosmonauts", []):
                        is_allocated = True
                        if m.get("reviewers"):
                            assigned_rev_id = m["reviewers"][0]
                        break

        if not is_allocated:
            return None

        prompts = self.get_reviewer_project_prompts(badge_id=badge_id)
        # 1. First priority: Prompt specifically addressed to this cadet (must be released/sent)
        for p in prompts:
            if getattr(p, "status", "") in ("draft",):
                continue
            c_ids = getattr(p, "cosmonaut_ids", [])
            if cosmonaut_id in c_ids:
                return p
        # 2. Second priority: General prompt with no restricted cosmonaut_ids, ONLY if created by cadet's assigned reviewer or guardian
        for p in prompts:
            if getattr(p, "status", "") in ("draft",):
                continue
            c_ids = getattr(p, "cosmonaut_ids", [])
            if not c_ids:
                p_rev = getattr(p, "reviewer_id", "")
                if not assigned_rev_id or p_rev == assigned_rev_id or p_rev.startswith("guardian"):
                    return p
        # Do not leak prompts addressed to other cadets
        return None

    def uncouple_cadet_badge_mapping(self, badge_id: str, cosmonaut_id: str):
        """
        Uncouples the active reviewer-cadet mapping for a specific badge once the badge is officially earned.
        Transitions the cadet's mapping status to 'completed' / 'earned'.
        """
        mappings = self.get_band_mappings()
        for m in mappings:
            m_badge = m.get("badge_id") or m.get("badge")
            b_obj = self.get_badge(badge_id)
            match = (m_badge == badge_id) or (b_obj and m_badge in (b_obj.title, b_obj.code, b_obj.id))
            if match and cosmonaut_id in m.get("cosmonauts", []):
                comp = m.setdefault("completed_cosmonauts", [])
                if cosmonaut_id not in comp:
                    comp.append(cosmonaut_id)
                uncoupled = m.setdefault("uncoupled_cadets", [])
                if cosmonaut_id not in uncoupled:
                    uncoupled.append(cosmonaut_id)
                active_remaining = [c for c in m.get("cosmonauts", []) if c not in comp]
                if not active_remaining:
                    m["status"] = "completed"
                self.save_band_mapping(m)
                break

    # ==========================================================================
    # CUSTOM CAPABILITIES & SKILLS
    # ==========================================================================

    def get_custom_capabilities(self) -> List[str]:
        return self.db.get_custom_capabilities()

    def get_members_by_band(self, band: str) -> List[Dict[str, Any]]:
        return self.db.get_members_by_band(band)

    def add_custom_capability(self, name: str, user_id: str = "guardian_1", created_by: Optional[str] = None) -> Tuple[bool, str]:
        u_id = created_by or user_id
        ok, res = self.db.add_custom_capability(name, u_id)
        if ok:
            self.mark_dirty()
        return ok, res

    def get_custom_skills(self, capability_name: Optional[str] = None) -> List[str]:
        return self.db.get_custom_skills(capability_name)

    def add_custom_skill(self, name: str, capability_name: str = "", user_id: str = "guardian_1", created_by: Optional[str] = None) -> Tuple[bool, str]:
        u_id = created_by or user_id
        ok, res = self.db.add_custom_skill(name, capability_name=capability_name, user_id=u_id)
        if ok:
            self.mark_dirty()
        return ok, res

    # ==========================================================================
    # REVIEWER ELIGIBILITY & BADGE AUTHORIZATION
    # ==========================================================================

    def get_eligible_badge_reviewers(self, target_band: str) -> List[Dict[str, Any]]:
        return self.db.get_eligible_badge_reviewers(target_band)

    def verify_reviewer_eligibility(self, reviewer_id: str, target_band: str) -> Tuple[bool, str]:
        return self.db.verify_reviewer_eligibility(reviewer_id, target_band)

    def get_pending_badge_approvals(self, reviewer_id: Optional[str] = None, target_band: Optional[str] = None) -> List[Badge]:
        pending = [b for b in self.badges.values() if getattr(b, "workflow_status", "approved") == "pending_review"]
        if reviewer_id:
            pending = [b for b in pending if getattr(b, "assigned_reviewer_id", "") == reviewer_id]
        if target_band:
            pending = [b for b in pending if getattr(b, "target_band", "") == target_band]
        return pending

    def create_badge_for_review(self, *args, **kwargs) -> Tuple[bool, str, Optional[str]]:
        if args and isinstance(args[0], dict):
            badge_data = dict(args[0])
            creator_id = args[1] if len(args) > 1 else kwargs.get("creator_id", "guardian_1")
            creator_name = args[2] if len(args) > 2 else kwargs.get("creator_name", "Arjun Mehta")
        else:
            badge_data = dict(kwargs)
            creator_id = kwargs.get("creator_id", "guardian_1")
            creator = self.get_user_by_id(creator_id)
            creator_name = creator.name if creator else "Arjun Mehta"

        ok, msg, b_id = self.db.create_badge_for_review(badge_data, creator_id, creator_name)
        if ok and b_id:
            # Sync in-memory badge dictionary
            self.badges[b_id] = Badge(
                id=b_id,
                code=badge_data["code"],
                title=badge_data["title"],
                category=badge_data.get("category", "Architecture"),
                description=badge_data.get("description", ""),
                learning_outcomes=badge_data.get("learning_outcomes", []),
                learning_topics=badge_data.get("learning_topics", []),
                prerequisites=badge_data.get("prerequisites", []),
                project_requirements=badge_data.get("project_requirements", ""),
                is_published=False,
                is_allocated=False,
                target_band=badge_data.get("target_band", ""),
                power=badge_data.get("power", ""),
                capability=badge_data.get("capability", ""),
                skill=badge_data.get("skill", ""),
                prompt_json=badge_data.get("prompt_json", "{}"),
                workflow_status="pending_review",
                creator_id=creator_id,
                assigned_reviewer_id=badge_data.get("assigned_reviewer_id") or badge_data.get("reviewer_id", "")
            )
            # Reload notifications & activities
            self.notifications = [Notification.from_dict(n) for n in self.db.export_to_dict()["notifications"]]
            self.activities = [ActivityEvent.from_dict(act) for act in self.db.export_to_dict()["activities"]]
            self.mark_dirty()
        return ok, msg, b_id

    def update_badge_by_reviewer(self, badge_id: str, *args, **kwargs) -> Tuple[bool, str]:
        # Handle both (badge_id, updated_data, reviewer_id, reviewer_name) and (badge_id, reviewer_id, updates)
        if args and isinstance(args[0], dict):
            updated_data = args[0]
            reviewer_id = args[1] if len(args) > 1 else kwargs.get("reviewer_id", "")
            reviewer_name = args[2] if len(args) > 2 else kwargs.get("reviewer_name", "")
        elif args and isinstance(args[0], str):
            reviewer_id = args[0]
            updated_data = args[1] if len(args) > 1 else kwargs.get("updated_data", {})
            reviewer_name = args[2] if len(args) > 2 else kwargs.get("reviewer_name", "")
        else:
            reviewer_id = kwargs.get("reviewer_id", "")
            updated_data = kwargs.get("updated_data", {})
            reviewer_name = kwargs.get("reviewer_name", "")

        if not reviewer_name:
            u = self.get_user_by_id(reviewer_id)
            reviewer_name = u.name if u else "Reviewer"

        ok, msg = self.db.update_badge_by_reviewer(badge_id, updated_data, reviewer_id, reviewer_name)
        if ok:
            b = self.get_badge(badge_id)
            if b:
                if "title" in updated_data: b.title = updated_data["title"]
                if "category" in updated_data: b.category = updated_data["category"]
                if "description" in updated_data: b.description = updated_data["description"]
                if "learning_outcomes" in updated_data: b.learning_outcomes = updated_data["learning_outcomes"]
                if "learning_topics" in updated_data: b.learning_topics = updated_data["learning_topics"]
                if "project_requirements" in updated_data: b.project_requirements = updated_data["project_requirements"]
                if "power" in updated_data: b.power = updated_data["power"]
                if "capability" in updated_data: b.capability = updated_data["capability"]
                if "skill" in updated_data: b.skill = updated_data["skill"]
                if "prompt_json" in updated_data: b.prompt_json = updated_data["prompt_json"]
            self.mark_dirty()
        return ok, msg

    def approve_badge(self, badge_id: str, reviewer_id: str, reviewer_name: str = "", notes: str = "") -> Tuple[bool, str]:
        if not reviewer_name:
            u = self.get_user_by_id(reviewer_id)
            reviewer_name = u.name if u else "Reviewer"
        ok, msg = self.db.approve_badge(badge_id, reviewer_id, reviewer_name, notes)
        if ok:
            b = self.get_badge(badge_id)
            if b:
                b.workflow_status = "approved"
            self.notifications = [Notification.from_dict(n) for n in self.db.export_to_dict()["notifications"]]
            self.activities = [ActivityEvent.from_dict(act) for act in self.db.export_to_dict()["activities"]]
            self.mark_dirty()
        return ok, msg

    def return_badge(self, badge_id: str, reviewer_id: str, reviewer_name: str = "", notes: str = "") -> Tuple[bool, str]:
        if not reviewer_name:
            u = self.get_user_by_id(reviewer_id)
            reviewer_name = u.name if u else "Reviewer"
        ok, msg = self.db.return_badge(badge_id, reviewer_id, reviewer_name, notes)
        if ok:
            b = self.get_badge(badge_id)
            if b:
                b.workflow_status = "returned"
            self.notifications = [Notification.from_dict(n) for n in self.db.export_to_dict()["notifications"]]
            self.activities = [ActivityEvent.from_dict(act) for act in self.db.export_to_dict()["activities"]]
            self.mark_dirty()
        return ok, msg

    def assign_and_request_badge_review(self, badge_id: str, reviewer_id: str, creator_id: str = "guardian_1") -> Tuple[bool, str]:
        ok, msg = self.db.assign_and_request_badge_review(badge_id, reviewer_id, creator_id)
        if ok:
            b = self.get_badge(badge_id)
            if b:
                b.workflow_status = "pending_review"
                b.assigned_reviewer_id = reviewer_id
            self.notifications = [Notification.from_dict(n) for n in self.db.export_to_dict()["notifications"]]
            self.activities = [ActivityEvent.from_dict(act) for act in self.db.export_to_dict()["activities"]]
            self.mark_dirty()
        return ok, msg

    def get_badge_review_requests_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        return self.db.get_badge_review_requests_for_user(user_id)

    def get_badge_review_history(self, badge_id: Optional[str] = None, reviewer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.db.get_badge_review_history(badge_id=badge_id, reviewer_id=reviewer_id)

    def get_submitted_badges_for_approval(self, status_filter: str = "all") -> List[Dict[str, Any]]:
        return self.db.get_submitted_badges_for_approval(status_filter)

    def get_badge_review_detail(self, badge_id: str) -> Optional[Dict[str, Any]]:
        return self.db.get_badge_review_detail(badge_id)

    def save_generated_badge(self, badge_dict: Dict[str, Any], creator_id: str = "guardian_1") -> Tuple[bool, str, Optional[Badge]]:
        title = badge_dict.get("title", "Generated Badge").strip()
        band = badge_dict.get("target_band", "B1")
        power = badge_dict.get("power", "Tech")
        cap = badge_dict.get("capability", "Data & Machine")
        skill = badge_dict.get("skill", "Hardware").strip()
        desc = badge_dict.get("description", "")
        outcomes = badge_dict.get("outcomes", [])
        topics = [t["title"] if isinstance(t, dict) else str(t) for t in badge_dict.get("learning_topics", [])]
        code = badge_dict.get("code") or f"{band}-{skill[:3].upper()}-01"

        clean_skill = re.sub(r'[^a-zA-Z0-9]+', '_', skill.strip().lower()).strip('_')
        canonical_id = f"badge_{band.lower()}_{clean_skill}"
        provided_id = badge_dict.get("id")

        # Find existing badge in this band matching skill or ID
        existing_badge = None
        for existing in self.badges.values():
            if getattr(existing, "target_band", "") == band:
                if (provided_id and existing.id == provided_id) or \
                   (getattr(existing, "skill", "").strip().lower() == skill.lower()) or \
                   (existing.id == canonical_id):
                    existing_badge = existing
                    break

        if existing_badge:
            is_custom_provided = bool(provided_id and provided_id != canonical_id and not provided_id.startswith(f"badge_{band.lower()}_"))
            is_custom_existing = bool(existing_badge.id != canonical_id and not existing_badge.id.startswith(f"badge_{band.lower()}_"))
            if is_custom_provided and is_custom_existing and provided_id != existing_badge.id:
                # Explicit conflict between two distinct custom IDs (e.g. test_dup_badge_1 vs test_dup_badge_2)
                return False, f"A badge for skill '{skill}' already exists for Band {band} ('{existing_badge.title}'). Duplicate badges are not allowed in the same band.", None
            # Re-use existing badge ID to update it
            b_id = existing_badge.id
        else:
            b_id = provided_id or canonical_id

        # Deduplication check across OTHER badges in the same band
        for existing in self.badges.values():
            if getattr(existing, "target_band", "") == band and existing.id != b_id:
                if existing.title.strip().lower() == title.lower() and getattr(existing, "skill", "").strip().lower() != skill.lower():
                    return False, f"A badge with title '{title}' already exists for Band {band}. Duplicate badges are not allowed.", None
                if getattr(existing, "skill", "").strip().lower() == skill.lower():
                    return False, f"A badge for skill '{skill}' already exists for Band {band} ('{existing.title}'). Duplicate badges are not allowed in the same band.", None

        practice_prompt = ""
        if isinstance(badge_dict.get("practice_project"), dict):
            practice_prompt = badge_dict["practice_project"].get("prompt", "")
        if not practice_prompt:
            practice_prompt = badge_dict.get("practice_prompt", "") or badge_dict.get("project_requirements", "")

        assigned_cosmonaut_ids = getattr(existing_badge, "assigned_cosmonaut_ids", []) if existing_badge else []
        default_timeline = getattr(existing_badge, "default_timeline", {}) if existing_badge else {}
        assigned_reviewer_id = getattr(existing_badge, "assigned_reviewer_id", "") if existing_badge else ""
        is_published = getattr(existing_badge, "is_published", False) if existing_badge else False
        is_allocated = getattr(existing_badge, "is_allocated", False) if existing_badge else False
        workflow_status = getattr(existing_badge, "workflow_status", None) if existing_badge else None
        if not workflow_status or workflow_status == "approved":
            workflow_status = badge_dict.get("workflow_status", "ready_for_review")

        badge = Badge(
            id=b_id,
            code=code,
            title=title,
            category=f"{cap} / {skill}",
            description=desc,
            learning_outcomes=outcomes,
            learning_topics=topics,
            prerequisites=[],
            project_requirements=practice_prompt,
            is_published=is_published,
            is_allocated=is_allocated,
            target_band=band,
            power=power,
            capability=cap,
            skill=skill,
            prompt_json=json.dumps(badge_dict, indent=2),
            workflow_status=workflow_status,
            creator_id=creator_id,
            assigned_reviewer_id=assigned_reviewer_id,
            assigned_cosmonaut_ids=assigned_cosmonaut_ids,
            default_timeline=default_timeline
        )
        self.save_badge(badge)
        self.add_activity(
            event_type="badge_saved",
            actor_id=creator_id,
            actor_name="Guardian",
            cosmonaut_id="",
            badge_id=b_id,
            summary=f"Saved badge '{title}' -> {skill} -> {cap} -> {power} -> Band {band}."
        )
        self.mark_dirty()
        return True, "Badge saved successfully!", badge

    def get_saved_badges(self, band: Optional[str] = None) -> List[Dict[str, Any]]:
        # Sync from SQLite to ensure latest badges across all processes/tabs
        try:
            if self.db and self.db.conn:
                rows = self.db.conn.execute("SELECT * FROM badges").fetchall()
                for r in rows:
                    if r["id"] not in self.badges or not getattr(self.badges[r["id"]], "target_band", None):
                        self.badges[r["id"]] = Badge(
                            id=r["id"],
                            code=r["code"] or "",
                            title=r["title"] or "",
                            category=r["category"] or "",
                            description=r["description"] or "",
                            learning_outcomes=json.loads(r["learning_outcomes_json"] or "[]"),
                            learning_topics=json.loads(r["learning_topics_json"] or "[]"),
                            project_requirements=r["project_requirements"] or "",
                            is_published=bool(r["is_published"]),
                            is_allocated=bool(r["is_allocated"]),
                            target_band=r["target_band"],
                            power=r["power"],
                            capability=r["capability"],
                            skill=r["skill"],
                            prompt_json=r["prompt_json"],
                            workflow_status=r["workflow_status"] or "ready_for_review",
                            creator_id=r["creator_id"] or "guardian_1",
                            assigned_reviewer_id=r["assigned_reviewer_id"]
                        )
        except Exception:
            pass

        results = []
        for b in self.badges.values():
            b_band = getattr(b, "target_band", None) or ""
            if not getattr(b, "is_allocated", True) or b_band:
                if band and b_band != band:
                    continue
                # Parse structured prompt if available
                badge_json = {}
                if b.prompt_json:
                    try:
                        badge_json = json.loads(b.prompt_json)
                    except Exception:
                        pass
                loc = badge_json.get("location") or f"{b.title} -> {getattr(b, 'skill', 'General')} -> {getattr(b, 'capability', 'Core')} -> {getattr(b, 'power', 'Tech')} -> Band {b_band or 'B1'}"
                rev_user = self.get_user_by_id(getattr(b, "assigned_reviewer_id", "")) if getattr(b, "assigned_reviewer_id", None) else None
                # Check assignment decision notes from DB if available
                dec_notes = ""
                try:
                    if self.db and self.db.conn:
                        ra_row = self.db.conn.execute("SELECT decision_notes FROM badge_reviewer_assignments WHERE badge_id = ? ORDER BY assigned_at DESC LIMIT 1", (b.id,)).fetchone()
                        if ra_row and ra_row["decision_notes"]:
                            dec_notes = ra_row["decision_notes"]
                except Exception:
                    pass
                results.append({
                    "id": b.id,
                    "code": b.code,
                    "title": b.title,
                    "target_band": b_band or "B1",
                    "power": getattr(b, "power", "Tech"),
                    "capability": getattr(b, "capability", "Data & Machine"),
                    "skill": getattr(b, "skill", "Hardware"),
                    "description": b.description,
                    "location": loc,
                    "created_at": getattr(b, "created_at", ""),
                    "workflow_status": getattr(b, "workflow_status", "ready_for_review"),
                    "assigned_reviewer_id": getattr(b, "assigned_reviewer_id", None),
                    "assigned_reviewer_name": rev_user.name if rev_user else None,
                    "assigned_reviewer_band": getattr(rev_user, "band", "") if rev_user else None,
                    "decision_notes": dec_notes,
                    "badge_data": badge_json,
                    "is_published": getattr(b, "is_published", False),
                    "passing_percentage": getattr(b, "passing_percentage", 70.0),
                    "published_at": getattr(b, "published_at", ""),
                    "published_by": getattr(b, "published_by", "")
                })
        return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)

# Global store instance
store = DataStore()
