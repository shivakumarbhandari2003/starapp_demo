"""
STARAPP CENTRALIZED STORAGE & DATA-ACCESS LAYER
Acts as the authoritative bridge between SQLite and both Guardian and Cosmonaut portals.
SQLite is the primary structured database; exports/imports binary snapshots to IndexedDB.
"""

import json
import datetime
import time
import re
import hmac
import contextvars
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple
try:
    import bcrypt
except ImportError:
    bcrypt = None

_EMAIL_VALIDATION_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
from starapp.models import (
    DEFAULT_CYCLE_ID, DEFAULT_HIKE_POLICY,
    User, CosmonautProfile, Badge, BadgeTimeline, ProjectSubmission,
    AssessmentMarksheet, LearningMaterial, DeadlineExtension,
    Announcement, ActivityEvent, Notification, ReviewerProjectPrompt,
    PerformanceCycle, CycleEnrollment, CyclePerformanceAppraisal,
    current_iso_timestamp
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

class StorageWriteError(RuntimeError):
    """Raised when a database write fails; the in-memory cache has been invalidated."""


_ACTIVE_READ_CYCLE_CTX: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("starapp_read_cycle_id", default=None)

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

        self.cycles: Dict[str, PerformanceCycle] = {}
        self.cycle_enrollments: Dict[str, CycleEnrollment] = {}
        self.cycle_appraisals: Dict[str, CyclePerformanceAppraisal] = {}
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

        # --- Scale layer (see STARAPP_STAGE1_LOGIC_OPTIMIZATION_LOG.md) ---
        # Secondary in-memory indexes (cosmonaut / submission / reviewer lookups) so that
        # per-user reads are O(1) instead of scanning every row of every user.
        self._learning_version: int = 0
        self._ix: Optional[Dict[str, Any]] = None
        self._ix_stamp_val: Optional[tuple] = None
        # Fingerprint-gated memo caches (invalidated by ANY write on this or another connection).
        self._memo: Dict[str, Tuple[Any, Any]] = {}
        self._cycle_tables_dv: Optional[int] = None
        self._loaded_data_version: Optional[int] = None
        self._cycle_appraisal_ix: Dict[Tuple[str, str], CyclePerformanceAppraisal] = {}
        self._feed_rowids: Dict[str, int] = {"notifications": 0, "activity_events": 0}

        # Auto-load existing authoritative SQLite state if available
        try:
            if self.db and self.db.conn:
                row = self.db.conn.execute("SELECT COUNT(*) FROM users").fetchone()
                if row and row[0] > 0:
                    exported = self.db.export_to_dict(include_blobs=False)
                    if exported.get("users"):
                        self.load_from_dict(exported)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Scale layer: fingerprints, memoisation and secondary indexes
    # ------------------------------------------------------------------
    def _write_failed(self, what: str, exc: Exception):
        """
        A failed database write must NEVER look like a success. Previously every save method printed the
        error and carried on, leaving memory and SQLite silently out of sync (e.g. a "database is locked"
        made a grade or submission vanish after the next reload). Roll back, drop derived caches and raise.
        """
        import logging
        logging.getLogger("starapp.storage").error("Write failed (%s): %s", what, exc)
        try:
            self.db.conn.rollback()
        except Exception:
            pass
        self._invalidate_indexes()
        raise StorageWriteError(f"{what}: {exc}") from exc

    def resync_from_database(self):
        """Discards in-memory state and reloads it from SQLite (used after a failed write)."""
        self._loaded_data_version = None
        self.load_from_dict(self.db.export_to_dict(include_blobs=False))

    def _db_fingerprint(self) -> Tuple[Any, Any]:
        """
        Cheap fingerprint that changes on EVERY write to the database:
        `data_version` moves for writes made by other connections (REST routers, scripts) and
        `total_changes` moves for writes made on this connection.
        """
        try:
            conn = self.db.conn
            return (conn.execute("PRAGMA data_version").fetchone()[0], conn.total_changes)
        except Exception:
            return (None, None)

    def _memoized(self, key: str, builder, extra: Any = None, scope: str = "all"):
        """
        Returns builder() cached until the data it depends on changes.
          scope="all"      invalidated by ANY write on this or another connection;
          scope="learning" invalidated only by learning-data writes (see mark_dirty) or by another
                           connection changing the database (PRAGMA data_version).
        """
        if scope == "learning":
            stamp = (self._learning_version, self._db_fingerprint()[0], extra)
        else:
            stamp = (self.version, self._db_fingerprint(), extra)
        hit = self._memo.get(key)
        if hit is not None and hit[0] == stamp:
            return hit[1]
        value = builder()
        self._memo[key] = (stamp, value)
        return value

    def _ix_stamp(self) -> tuple:
        # id() detects whole-collection replacement (tests / reset flows); len() detects direct add/remove.
        return (
            id(self.submissions), len(self.submissions),
            id(self.assessments), len(self.assessments),
            id(self.extensions), len(self.extensions),
            id(self.timelines), len(self.timelines),
            id(self.notifications), len(self.notifications),
            id(self.activities), len(self.activities),
        )

    def _ensure_ix(self) -> Dict[str, Any]:
        """Builds (or incrementally keeps) the per-cosmonaut / per-submission / per-reviewer indexes."""
        stamp = self._ix_stamp()
        if self._ix is not None and self._ix_stamp_val == stamp:
            return self._ix
        ix: Dict[str, Any] = {
            "subs_by_cosmo": {}, "asms_by_cosmo": {}, "asms_by_sub": {}, "exts_by_cosmo": {},
            "tl_by_cosmo": {}, "tl_by_reviewer": {}, "tl_reviewer_of": {},
            "notifs_by_user": {}, "acts_by_person": {},
        }
        for s in self.submissions.values():
            ix["subs_by_cosmo"].setdefault(s.cosmonaut_id, {})[s.id] = s
        for a in self.assessments.values():
            ix["asms_by_cosmo"].setdefault(a.cosmonaut_id, {})[a.id] = a
            ix["asms_by_sub"].setdefault(a.submission_id, {})[a.id] = a
        for e in self.extensions.values():
            ix["exts_by_cosmo"].setdefault(e.cosmonaut_id, {})[e.id] = e
        for k, t in self.timelines.items():
            ix["tl_by_cosmo"].setdefault(t.cosmonaut_id, {})[k] = t
            rid = getattr(t, "reviewer_id", "") or ""
            ix["tl_by_reviewer"].setdefault(rid, {})[k] = t
            ix["tl_reviewer_of"][k] = rid
        for n in self.notifications:
            ix["notifs_by_user"].setdefault(n.recipient_id, []).append(n)
        for act in self.activities:
            ix["acts_by_person"].setdefault(act.cosmonaut_id, []).append(act)
            if act.actor_id and act.actor_id != act.cosmonaut_id:
                ix["acts_by_person"].setdefault(act.actor_id, []).append(act)
        self._ix = ix
        self._ix_stamp_val = stamp
        return ix

    def _ix_commit(self):
        """Marks the index as consistent with the main collections after an incremental update."""
        self._ix_stamp_val = self._ix_stamp()

    def _invalidate_indexes(self):
        self._ix = None
        self._ix_stamp_val = None
        self._memo.clear()

    def _sync_feed_tables(self):
        """
        Pulls only NEW notification / activity rows (rowid watermark) written by db-level workflows
        (badge create/approve/return) instead of re-exporting the entire database twice per action.
        """
        conn = self.db.conn
        known_n = {n.id for n in self.notifications}
        known_a = {a.id for a in self.activities}
        try:
            rows = conn.execute(
                "SELECT rowid AS _rid, * FROM notifications WHERE rowid > ?", (self._feed_rowids["notifications"],)
            ).fetchall()
            for r in rows:
                d = dict(r)
                self._feed_rowids["notifications"] = max(self._feed_rowids["notifications"], d.pop("_rid"))
                if d["id"] not in known_n:
                    self.notifications.insert(0, Notification.from_dict(d))
            rows = conn.execute(
                "SELECT rowid AS _rid, * FROM activity_events WHERE rowid > ?", (self._feed_rowids["activity_events"],)
            ).fetchall()
            for r in rows:
                d = dict(r)
                self._feed_rowids["activity_events"] = max(self._feed_rowids["activity_events"], d.pop("_rid"))
                if d["id"] not in known_a:
                    self.activities.insert(0, ActivityEvent.from_dict(d))
        except Exception as e:
            print(f"[DataStore] feed sync error: {e}")
        self._invalidate_indexes()

    def _reset_feed_watermarks(self):
        try:
            for t in ("notifications", "activity_events"):
                row = self.db.conn.execute(f"SELECT COALESCE(MAX(rowid), 0) FROM {t}").fetchone()
                self._feed_rowids[t] = int(row[0] or 0)
        except Exception:
            pass

    @contextmanager
    def cycle_scope(self, cycle_id: Optional[str]):
        """Temporarily scopes read queries on the current request/thread to `cycle_id`."""
        token = _ACTIVE_READ_CYCLE_CTX.set(cycle_id)
        try:
            yield
        finally:
            _ACTIVE_READ_CYCLE_CTX.reset(token)

    def get_active_cycle_id(self) -> str:
        """Returns the current active/evaluating 6-month cycle id for new writes and default views."""
        if self.db and getattr(self.db, "conn", None):
            try:
                row = self.db.conn.execute(
                    "SELECT id FROM performance_cycles WHERE status IN ('active', 'evaluating') ORDER BY CASE WHEN status='active' THEN 0 ELSE 1 END, created_at DESC LIMIT 1"
                ).fetchone()
                if row and row[0]:
                    return row[0]
            except Exception:
                pass
        for c in sorted(self.cycles.values(), key=lambda x: getattr(x, "created_at", ""), reverse=True):
            if getattr(c, "status", "") in ("active", "evaluating"):
                return c.id
        if self.cycles:
            return sorted(self.cycles.values(), key=lambda x: getattr(x, "start_date", ""), reverse=True)[0].id
        return DEFAULT_CYCLE_ID

    def get_effective_read_cycle_id(self, cycle_id: Optional[str] = None) -> str:
        """Resolves target cycle_id for reads: explicit arg > context scope > active cycle."""
        if cycle_id:
            return cycle_id
        ctx_cid = _ACTIVE_READ_CYCLE_CTX.get(None)
        if ctx_cid:
            return ctx_cid
        return self.get_active_cycle_id()

    def mark_dirty(self, learning: bool = True):
        """
        Flags store as modified to trigger targeted SQLite export and persistence.

        `learning=False` is used for high-churn feed writes (notifications / activity / read receipts) that
        cannot change any badge, timeline, submission, assessment or appraisal figure, so expensive
        cohort-level caches are NOT thrown away every time somebody receives a notification.
        """
        self.version += 1
        if learning:
            self._learning_version += 1
        self.dirty = True
        self._cached_json = None

    def load_from_dict(self, data: Dict[str, Any]):
        """Loads domain objects into in-memory lookup cache from structured dictionary."""
        self.cycles = {c["id"]: PerformanceCycle.from_dict(c) for c in data.get("cycles", []) if isinstance(c, dict) and "id" in c}
        self.cycle_enrollments = {e["id"]: CycleEnrollment.from_dict(e) for e in data.get("cycle_enrollments", []) if isinstance(e, dict) and "id" in e}
        self.cycle_appraisals = {a["id"]: CyclePerformanceAppraisal.from_dict(a) for a in data.get("cycle_appraisals", []) if isinstance(a, dict) and "id" in a}
        self.users = {u["id"]: User.from_dict(u) for u in data.get("users", [])}
        self.profiles = {p["user_id"]: CosmonautProfile.from_dict(p) for p in data.get("profiles", [])}
        self.badges = {b["id"]: Badge.from_dict(b) for b in data.get("badges", [])}
        
        self.timelines = {}
        for t in data.get("timelines", []):
            tl = BadgeTimeline.from_dict(t)
            self.timelines[f"{tl.badge_id}_{tl.cosmonaut_id}"] = tl

        self.submissions = {s["id"]: ProjectSubmission.from_dict(s) for s in data.get("submissions", [])}
        for _sub in self.submissions.values():
            _sub._loader = self._load_submission_blobs
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
        self._cycle_tables_dv = None
        self._cycle_appraisal_ix = {}
        self._invalidate_indexes()
        self._reset_feed_watermarks()
        try:
            self._loaded_data_version = self.db.conn.execute("PRAGMA data_version").fetchone()[0]
        except Exception:
            self._loaded_data_version = None

    def _load_submission_blobs(self, sub_id: str) -> Dict[str, str]:
        """Fetches the heavy payload columns of ONE submission on demand."""
        row = self.db.conn.execute(
            "SELECT payload, pdf_payload, code_payload FROM project_submissions WHERE id = ?", (sub_id,)
        ).fetchone()
        if not row:
            return {}
        return {"payload": row[0] or "", "pdf_payload": row[1] or "", "code_payload": row[2] or ""}

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
                data = self.db.export_to_dict(include_blobs=False)
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
                exported = self.db.export_to_dict(include_blobs=False)
                self.load_from_dict(exported)
                return
            except Exception as e:
                print(f"[DataStore] Failed to migrate from JSON snapshot: {e}, resetting to seed.")

        # 3. Check if existing authoritative SQLite database already has records
        # PERFORMANCE: every new browser tab / login calls initialize() -> load_from_json(None, None).
        # The store is a process-wide singleton that already mirrors the database, so reloading the
        # ENTIRE database (and replacing every cached object) per tab is wasted work and also detaches
        # objects other sessions are holding. Reload only when another connection changed the database.
        if self.is_loaded and self.users and not (json_str and json_str.strip()) and not (sqlite_b64 and sqlite_b64.strip()):
            try:
                if self._loaded_data_version == self.db.conn.execute("PRAGMA data_version").fetchone()[0]:
                    return
            except Exception:
                pass
        try:
            if self.db and self.db.conn:
                row = self.db.conn.execute("SELECT COUNT(*) FROM users").fetchone()
                if row and row[0] > 0:
                    exported = self.db.export_to_dict(include_blobs=False)
                    if exported.get("users"):
                        self.load_from_dict(exported)
                        return
        except Exception as e:
            print(f"[DataStore] Failed to load existing SQLite database: {e}")
            if self.is_loaded and self.users:
                return

        # 4. Fallback to clean seed only if SQLite database is completely empty
        self.reset_to_seed()

    def reset_to_seed(self):
        """Resets SQLite database and in-memory cache to the baseline 5-badge cohort dataset."""
        self.db.clear_all_tables()
        seed_data = get_initial_seed_data()
        self.db.migrate_from_dict(seed_data)
        exported = self.db.export_to_dict(include_blobs=False)
        self.load_from_dict(exported)
        if self.get_cycle("cycle_0") and not self.get_cycle_appraisals("cycle_0"):
            from starapp.cycles import calculate_and_save_cycle_appraisals
            with self.cycle_scope("cycle_0"):
                apps = calculate_and_save_cycle_appraisals("cycle_0", self, actor_id="guardian_1", preserve_manual_overrides=True)
                for app_obj in apps:
                    app_obj.status = "finalized"
                    app_obj.finalized_by = "guardian_1"
                    app_obj.finalized_at = "2026-06-30T18:00:00Z"
                    self.save_cycle_appraisal(app_obj)
            self.load_from_dict(self.db.export_to_dict(include_blobs=False))
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
                learning_track=user_track,
                password=row["password"] if "password" in row.keys() and row["password"] else "123456789"
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
        # Query SQLite directly (supporting optional .b1-.b6 band suffix alias e.g. name.b3@starapp.io)
        row = self.db.conn.execute(
            "SELECT * FROM users WHERE lower(username) = ? OR lower(email) = ?",
            (u_clean, u_clean)
        ).fetchone()
        if not row:
            alias_match = re.match(r"^([a-z0-9._-]+)\.b[1-6]@([a-z0-9.-]+\.[a-z]{2,})$", u_clean)
            if alias_match:
                canonical_email = f"{alias_match.group(1)}@{alias_match.group(2)}"
                row = self.db.conn.execute(
                    "SELECT * FROM users WHERE lower(email) = ? OR lower(username) = ?",
                    (canonical_email, alias_match.group(1))
                ).fetchone()
        if row:
            return self.get_user_by_id(row["id"])
        return None

    @staticmethod
    def _verify_password_secret(plain_password: str, stored_password: str) -> bool:
        """Verifies plaintext or bcrypt-hashed user passwords stored in SQLite."""
        if not stored_password:
            return False
        if stored_password.startswith(("$2b$", "$2a$", "$2y$")):
            if bcrypt is None:
                return False
            try:
                return bool(bcrypt.checkpw(plain_password.encode("utf-8"), stored_password.encode("utf-8")))
            except Exception:
                return False
        return hmac.compare_digest(plain_password.encode("utf-8"), stored_password.encode("utf-8"))

    def authenticate_user(
        self,
        email_or_username: str,
        password: Optional[str] = None,
        require_password: bool = True
    ) -> Tuple[Optional[User], str]:
        """Validates email & password criteria and verifies active SQLite user credentials."""
        ident = str(email_or_username or "").strip().lower()
        pwd = "" if password is None else str(password)

        if require_password:
            if not ident:
                return None, "Please enter your email address."
            if not _EMAIL_VALIDATION_RE.match(ident):
                return None, "Please enter a valid email address (for example, name@starapp.io)."
            if not pwd.strip():
                return None, "Please enter your password."
            if len(pwd) < 6:
                return None, "Password must be at least 6 characters long."

            row = self.db.conn.execute(
                "SELECT * FROM users WHERE lower(email) = ? OR lower(username) = ?",
                (ident, ident)
            ).fetchone()
            if not row:
                alias_match = re.match(r"^([a-z0-9._-]+)\.b[1-6]@([a-z0-9.-]+\.[a-z]{2,})$", ident)
                if alias_match:
                    canonical_email = f"{alias_match.group(1)}@{alias_match.group(2)}"
                    row = self.db.conn.execute(
                        "SELECT * FROM users WHERE lower(email) = ? OR lower(username) = ?",
                        (canonical_email, alias_match.group(1))
                    ).fetchone()
            if not row:
                return None, "Invalid email or password. Account not found."

            status_val = str(row["status"] if "status" in row.keys() and row["status"] else "active").strip().lower()
            if status_val != "active":
                return None, "This account is inactive. Please contact an Academy Guardian."

            stored_pwd = str(row["password"] if "password" in row.keys() and row["password"] is not None else "")
            if not self._verify_password_secret(pwd, stored_pwd):
                return None, "Invalid email or password. Please check your credentials."

            self.users.pop(row["id"], None)
            user = self.get_user_by_id(row["id"])
            if not user:
                return None, "Unable to load user profile from database."
            return user, ""

        # Programmatic username lookup path (used by internal automation/unit tests)
        if not ident:
            return None, "Please enter an email address or username."
        row = self.db.conn.execute(
            "SELECT id, status FROM users WHERE lower(username) = ? OR lower(email) = ?",
            (ident, ident)
        ).fetchone()
        if row:
            status_val = str(row["status"] if "status" in row.keys() and row["status"] else "active").strip().lower()
            if status_val != "active":
                return None, "This account is inactive."
        user = self.get_user_by_username(ident)
        if user:
            return user, ""
        return None, "Account not found."

    def get_quick_login_accounts(self) -> List[Dict[str, Any]]:
        """Returns 6 band representatives (B1-B6) plus the CEO Guardian from SQLite for Quick Login pills."""
        preferred_bands = [
            ("B1", "m_b1_2"),
            ("B2", "m_b2_4"),
            ("B3", "m_b3_6"),
            ("B4", "m_b4_1"),
            ("B5", "m_b5_1"),
            ("B6", "m_b6_1"),
        ]
        results: List[Dict[str, Any]] = []
        seen_ids = set()

        for band_code, pref_id in preferred_bands:
            row = self.db.conn.execute(
                """
                SELECT id, name, email, band, primary_role, role
                FROM users
                WHERE id = ? AND lower(coalesce(status, 'active')) = 'active'
                """,
                (pref_id,)
            ).fetchone()
            if not row:
                row = self.db.conn.execute(
                    """
                    SELECT id, name, email, band, primary_role, role
                    FROM users
                    WHERE band = ? AND lower(coalesce(status, 'active')) = 'active' AND id != 'guardian_1'
                    ORDER BY id
                    LIMIT 1
                    """,
                    (band_code,)
                ).fetchone()
            if row and row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                results.append({
                    "id": row["id"],
                    "name": row["name"],
                    "email": row["email"],
                    "band": row["band"] or band_code,
                    "role_tag": row["band"] or band_code,
                    "is_guardian": False,
                })

        guardian_row = self.db.conn.execute(
            """
            SELECT id, name, email, band, primary_role, role
            FROM users
            WHERE id = 'guardian_1' AND lower(coalesce(status, 'active')) = 'active'
            """
        ).fetchone()
        if not guardian_row:
            guardian_row = self.db.conn.execute(
                """
                SELECT id, name, email, band, primary_role, role
                FROM users
                WHERE lower(coalesce(primary_role, '')) = 'guardian'
                  AND lower(coalesce(status, 'active')) = 'active'
                ORDER BY id
                LIMIT 1
                """
            ).fetchone()
        if guardian_row and guardian_row["id"] not in seen_ids:
            seen_ids.add(guardian_row["id"])
            results.append({
                "id": guardian_row["id"],
                "name": guardian_row["name"],
                "email": guardian_row["email"],
                "band": guardian_row["band"] or "CEO",
                "role_tag": "CEO · Guardian",
                "is_guardian": True,
            })
        return results

    def get_all_cosmonauts(self) -> List[User]:
        # All members across B1 to B6 are cosmonauts/cadets
        def build():
            # Guardians / admins administer the Academy; they are not cadets and must not appear in the
            # cohort, leaderboard, "enrolled cadets" or appraisal counts (the admin account used to, as B6).
            def is_guardian(u):
                roles = set(getattr(u, "roles", []) or []) | {u.role}
                return bool(roles & {"guardian", "admin"}) and "cosmonaut" not in roles

            return [
                u for u in self.users.values()
                if not is_guardian(u) and (
                    u.role in ("cosmonaut", "cadet") or "cosmonaut" in getattr(u, "roles", []) or "cadet" in getattr(u, "roles", [])
                    or (u.id != "guardian_1" and getattr(u, "band", "") in ("B1", "B2", "B3", "B4", "B5", "B6"))
                )
            ]
        return list(self._memoized("all_cosmonauts", build, extra=len(self.users), scope="learning"))

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
                INSERT INTO users (id, username, email, name, band, password, primary_role, avatar, status, is_demo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username = excluded.username, email = excluded.email, name = excluded.name,
                    band = excluded.band, password = excluded.password,
                    primary_role = excluded.primary_role, avatar = excluded.avatar
                """,
                (
                    user.id,
                    user.username,
                    user.email,
                    user.name,
                    getattr(user, "band", "") or "B1",
                    getattr(user, "password", "123456789") or "123456789",
                    user.role,
                    user.avatar,
                    current_iso_timestamp()
                )
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

    def save_user_band_update(self, user_id: str, band_code: str):
        """Updates a user's active Band in SQLite & in-memory cache (e.g., upon end-of-cycle promotion)."""
        u = self.get_user_by_id(user_id)
        if u:
            u.band = band_code
            self.users[u.id] = u
        if self.db and getattr(self.db, "conn", None):
            try:
                with self.db.conn:
                    self.db.conn.execute("UPDATE users SET band = ? WHERE id = ?", (band_code, user_id))
                    self.db.conn.execute("UPDATE user_band_memberships SET band_code = ? WHERE user_id = ?", (band_code, user_id))
                self.db.conn.commit()
            except Exception as e:
                self._write_failed("updating user band", e)
        self.mark_dirty()

    # --- 6-Month Performance Cycles, Enrollments & Appraisals ---
    def _sync_cycle_tables(self):
        """
        Reloads cycles / enrollments / appraisals from SQLite ONLY when another connection changed the
        database (PRAGMA data_version). Writes made through this store already update the caches, so
        the previous behaviour of re-querying three tables on every single call is no longer needed.
        """
        conn = getattr(self.db, "conn", None)
        if conn is None:
            return
        try:
            dv = conn.execute("PRAGMA data_version").fetchone()[0]
        except Exception:
            return
        if self._cycle_tables_dv == dv:
            return
        try:
            cycles = {}
            for r in conn.execute("SELECT * FROM performance_cycles ORDER BY start_date DESC, created_at DESC").fetchall():
                d = dict(r)
                cycles[d["id"]] = PerformanceCycle.from_dict(d)
            enrollments = {}
            for r in conn.execute("SELECT * FROM cycle_enrollments").fetchall():
                e = CycleEnrollment.from_dict(dict(r))
                enrollments[e.id] = e
            appraisals = {}
            for r in conn.execute("SELECT * FROM cycle_performance_appraisals").fetchall():
                a = CyclePerformanceAppraisal.from_dict(dict(r))
                appraisals[a.id] = a
            self.cycles, self.cycle_enrollments, self.cycle_appraisals = cycles, enrollments, appraisals
            self._cycle_appraisal_ix = {(a.cycle_id, a.cosmonaut_id): a for a in appraisals.values()}
            self._cycle_tables_dv = dv
        except Exception:
            pass

    def get_all_cycles(self) -> List[PerformanceCycle]:
        self._sync_cycle_tables()
        return sorted(self.cycles.values(), key=lambda c: (getattr(c, "start_date", ""), getattr(c, "created_at", "")), reverse=True)

    def get_cycle(self, cycle_id: str) -> Optional[PerformanceCycle]:
        if not cycle_id:
            return None
        self._sync_cycle_tables()
        if cycle_id in self.cycles:
            return self.cycles[cycle_id]
        if self.db and getattr(self.db, "conn", None):
            try:
                row = self.db.conn.execute("SELECT * FROM performance_cycles WHERE id = ?", (cycle_id,)).fetchone()
                if row:
                    cyc = PerformanceCycle.from_dict(dict(row))
                    self.cycles[cyc.id] = cyc
                    return cyc
            except Exception:
                pass
        return None

    def save_cycle(self, cyc: PerformanceCycle):
        self.cycles[cyc.id] = cyc
        if self.db and getattr(self.db, "conn", None):
            try:
                with self.db.conn:
                    self.db.conn.execute(
                        """
                        INSERT INTO performance_cycles (
                            id, code, name, start_date, end_date, status, created_by,
                            created_at, closed_at, cloned_from_cycle_id, hike_policy_json, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            code = excluded.code, name = excluded.name, start_date = excluded.start_date,
                            end_date = excluded.end_date, status = excluded.status, created_by = excluded.created_by,
                            closed_at = excluded.closed_at, cloned_from_cycle_id = excluded.cloned_from_cycle_id,
                            hike_policy_json = excluded.hike_policy_json, notes = excluded.notes
                        """,
                        (
                            cyc.id, cyc.code, cyc.name, cyc.start_date, cyc.end_date,
                            cyc.status, cyc.created_by, cyc.created_at, cyc.closed_at,
                            cyc.cloned_from_cycle_id, json.dumps(cyc.hike_policy or DEFAULT_HIKE_POLICY), cyc.notes
                        )
                    )
                self.db.conn.commit()
            except Exception as e:
                self._write_failed("saving performance cycle", e)
        self.mark_dirty()

    def get_cycle_enrollments(self, cycle_id: Optional[str] = None) -> List[CycleEnrollment]:
        cid = self.get_effective_read_cycle_id(cycle_id)
        self._sync_cycle_tables()
        grouped = self._memoized(
            "enrollments_by_cycle",
            lambda: self._group_by_cycle(self.cycle_enrollments.values()),
            extra=len(self.cycle_enrollments), scope="learning",
        )
        return list(grouped.get(cid, []))

    def save_cycle_enrollment(self, enr: CycleEnrollment):
        self.cycle_enrollments[enr.id] = enr
        if self.db and getattr(self.db, "conn", None):
            try:
                with self.db.conn:
                    self.db.conn.execute(
                        """
                        INSERT OR REPLACE INTO cycle_enrollments (
                            id, cycle_id, user_id, cycle_role, band_code, track_code,
                            base_salary, reporting_manager_id, status, enrolled_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            enr.id, enr.cycle_id, enr.user_id, enr.cycle_role, enr.band_code,
                            enr.track_code, float(enr.base_salary or 0.0), enr.reporting_manager_id,
                            enr.status, enr.enrolled_at
                        )
                    )
                self.db.conn.commit()
            except Exception as e:
                self._write_failed("saving cycle enrollment", e)
        self.mark_dirty()

    def get_cycle_appraisals(self, cycle_id: Optional[str] = None) -> List[CyclePerformanceAppraisal]:
        cid = self.get_effective_read_cycle_id(cycle_id)
        self._sync_cycle_tables()
        grouped = self._memoized(
            "appraisals_by_cycle",
            lambda: self._group_by_cycle(self.cycle_appraisals.values()),
            extra=len(self.cycle_appraisals), scope="learning",
        )
        return sorted(grouped.get(cid, []), key=lambda x: x.composite_score, reverse=True)

    @staticmethod
    def _group_by_cycle(items) -> Dict[str, List[Any]]:
        grouped: Dict[str, List[Any]] = {}
        for it in items:
            grouped.setdefault(it.cycle_id, []).append(it)
        return grouped

    def get_cycle_appraisal(self, cycle_id: str, user_id: str) -> Optional[CyclePerformanceAppraisal]:
        """O(1) lookup (previously loaded + sorted EVERY appraisal of the cycle for each single user)."""
        self._sync_cycle_tables()
        hit = self._cycle_appraisal_ix.get((cycle_id, user_id))
        if hit is not None and self.cycle_appraisals.get(hit.id) is hit:
            return hit
        for a in self.cycle_appraisals.values():
            if a.cycle_id == cycle_id and a.cosmonaut_id == user_id:
                self._cycle_appraisal_ix[(cycle_id, user_id)] = a
                return a
        return None

    def save_cycle_appraisal(self, app_obj: CyclePerformanceAppraisal):
        self.cycle_appraisals[app_obj.id] = app_obj
        self._cycle_appraisal_ix[(app_obj.cycle_id, app_obj.cosmonaut_id)] = app_obj
        if self.db and getattr(self.db, "conn", None):
            try:
                with self.db.conn:
                    self.db.conn.execute(
                        """
                        INSERT OR REPLACE INTO cycle_performance_appraisals (
                            id, cycle_id, cosmonaut_id, band_code,
                            badges_assigned, badges_submitted, badges_earned, first_attempt_passes, total_attempts,
                            avg_marks, avg_percentage, cosmo_score,
                            badge_reviews_assigned, badge_reviews_completed, projects_created, projects_released,
                            submissions_assigned_to_review, submissions_graded, reviewer_avg_marks_given, reviewer_score,
                            composite_score, performance_tier, base_salary, recommended_hike_pct, approved_hike_pct,
                            hike_amount, new_salary, bonus_amount, recommended_promotion_band, guardian_remarks,
                            status, calculated_at, finalized_by, finalized_at, details_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            app_obj.id, app_obj.cycle_id, app_obj.cosmonaut_id, app_obj.band_code,
                            app_obj.badges_assigned, app_obj.badges_submitted, app_obj.badges_earned,
                            app_obj.first_attempt_passes, app_obj.total_attempts,
                            app_obj.avg_marks, app_obj.avg_percentage, app_obj.cosmo_score,
                            app_obj.badge_reviews_assigned, app_obj.badge_reviews_completed,
                            app_obj.projects_created, app_obj.projects_released,
                            app_obj.submissions_assigned_to_review, app_obj.submissions_graded,
                            app_obj.reviewer_avg_marks_given, app_obj.reviewer_score,
                            app_obj.composite_score, app_obj.performance_tier,
                            app_obj.base_salary, app_obj.recommended_hike_pct, app_obj.approved_hike_pct,
                            app_obj.hike_amount, app_obj.new_salary, app_obj.bonus_amount,
                            app_obj.recommended_promotion_band, app_obj.guardian_remarks,
                            app_obj.status, app_obj.calculated_at, app_obj.finalized_by, app_obj.finalized_at,
                            json.dumps(app_obj.details or {})
                        )
                    )
                self.db.conn.commit()
            except Exception as e:
                self._write_failed("saving cycle appraisal", e)
        self.mark_dirty()

    # --- Badges ---
    def get_all_badges(self, cycle_id: Optional[str] = None) -> List[Badge]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        fp = self._db_fingerprint()
        if getattr(self, "_badge_sync_fp", None) != (fp, self.version):
            self._sync_badges_from_db()
            self._badge_sync_fp = (fp, self.version)
        grouped = self._memoized("badges_by_cycle", self._group_badges_by_cycle, extra=len(self.badges), scope="learning")
        return list(grouped.get(target_cid, []))

    def _group_badges_by_cycle(self) -> Dict[str, List[Badge]]:
        grouped: Dict[str, List[Badge]] = {}
        for b in self.badges.values():
            grouped.setdefault(getattr(b, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID, []).append(b)
        return grouped

    def _sync_badges_from_db(self):
        """Merges rows written by other connections / db-level workflows into the in-memory badge cache."""
        if self.db and self.db.conn:
            try:
                rows = self.db.conn.execute("SELECT * FROM badges").fetchall()
                for r in rows:
                    rd = dict(r)
                    b_id = rd.get("id")
                    if not b_id:
                        continue
                    b_cid = rd.get("cycle_id") or DEFAULT_CYCLE_ID
                    if b_id in self.badges:
                        b = self.badges[b_id]
                        b.cycle_id = b_cid
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
                            updated_at=rd.get("updated_at", ""),
                            cycle_id=b_cid
                        )
            except Exception:
                pass

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
        if not getattr(badge, "cycle_id", ""):
            badge.cycle_id = self.get_active_cycle_id()
        self.badges[badge.id] = badge
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT INTO badges (
                    id, code, title, category, description,
                    learning_outcomes_json, learning_topics_json, project_requirements,
                    is_published, is_allocated, target_band, power, capability, skill,
                    prompt_json, workflow_status, creator_id, assigned_reviewer_id,
                    assigned_cosmonaut_ids_json, default_timeline_json, created_at, updated_at,
                    passing_percentage, published_at, published_by, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    code = excluded.code,
                    title = excluded.title,
                    category = excluded.category,
                    description = excluded.description,
                    learning_outcomes_json = excluded.learning_outcomes_json,
                    learning_topics_json = excluded.learning_topics_json,
                    project_requirements = excluded.project_requirements,
                    is_published = excluded.is_published,
                    is_allocated = excluded.is_allocated,
                    target_band = excluded.target_band,
                    power = excluded.power,
                    capability = excluded.capability,
                    skill = excluded.skill,
                    prompt_json = excluded.prompt_json,
                    workflow_status = excluded.workflow_status,
                    creator_id = excluded.creator_id,
                    assigned_reviewer_id = excluded.assigned_reviewer_id,
                    assigned_cosmonaut_ids_json = excluded.assigned_cosmonaut_ids_json,
                    default_timeline_json = excluded.default_timeline_json,
                    updated_at = excluded.updated_at,
                    passing_percentage = excluded.passing_percentage,
                    published_at = excluded.published_at,
                    published_by = excluded.published_by,
                    cycle_id = excluded.cycle_id
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
                    getattr(badge, "published_by", ""),
                    badge.cycle_id
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
            if self.db and self.db.conn:
                self.db.conn.commit()
        self.mark_dirty()

    def _cosmo_badge_map(self, target_cid: str):
        """
        Per-cycle lookup tables built ONCE per data change:
          mapped   : cosmonaut_id -> badge ids reached through timelines / badge_timelines / band_mappings
          assigned : cosmonaut_id -> badge ids directly listed in Badge.assigned_cosmonaut_ids
        Previously every call re-scanned all timelines, ran a SQL query and looped every mapping x badge.
        """
        def build():
            cycle_badges = self.get_all_badges(cycle_id=target_cid)
            mapped: Dict[str, set] = {}
            for t in self.timelines.values():
                if (getattr(t, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid:
                    mapped.setdefault(t.cosmonaut_id, set()).add(t.badge_id)
            if self.db and getattr(self.db, "conn", None):
                try:
                    for r in self.db.conn.execute(
                        "SELECT cosmonaut_id, badge_id FROM badge_timelines WHERE cycle_id = ?", (target_cid,)
                    ).fetchall():
                        mapped.setdefault(r[0], set()).add(r[1])
                except Exception:
                    pass
            ref_to_ids: Dict[str, List[str]] = {}
            for b in cycle_badges:
                for ref in {b.title, b.code, b.id}:
                    ref_to_ids.setdefault(ref, []).append(b.id)
            try:
                for m in self.get_band_mappings(cycle_id=target_cid):
                    ids = ref_to_ids.get(m.get("badge", ""), [])
                    if ids:
                        for cid in m.get("cosmonauts", []):
                            mapped.setdefault(cid, set()).update(ids)
            except Exception:
                pass
            assigned: Dict[str, set] = {}
            for b in cycle_badges:
                for cid in getattr(b, "assigned_cosmonaut_ids", []):
                    assigned.setdefault(cid, set()).add(b.id)
            return mapped, assigned, cycle_badges

        return self._memoized(f"cosmo_badge_map:{target_cid}", build, extra=(len(self.timelines), len(self.band_mappings)), scope="learning")

    def get_badges_for_cosmonaut(self, cosmo_id: str, cycle_id: Optional[str] = None) -> List[Badge]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        mapped, assigned, cycle_badges = self._cosmo_badge_map(target_cid)
        ids_mapped = mapped.get(cosmo_id)
        ids_assigned = assigned.get(cosmo_id)
        if not ids_mapped and not ids_assigned:
            return []
        approved_hist_ids = {
            a.badge_id
            for a in self.get_assessments_for_cosmonaut(cosmo_id, cycle_id=target_cid)
            if getattr(a, "decision", "") == "approve"
        }
        ids_mapped = ids_mapped or set()
        ids_assigned = ids_assigned or set()
        # Only published badges (or ones already certified) are visible to the cosmonaut.
        return [
            b for b in cycle_badges
            if (getattr(b, "is_published", False) or b.id in approved_hist_ids)
            and (b.id in ids_assigned or b.id in ids_mapped)
        ]

    # --- Timelines ---
    def get_timelines_dict(self, cycle_id: Optional[str] = None) -> Dict[str, BadgeTimeline]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        return {
            k: t for k, t in self.timelines.items()
            if (getattr(t, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid
        }

    def get_timelines_for_cosmonaut(self, cosmo_id: str, cycle_id: Optional[str] = None) -> List[BadgeTimeline]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        return [
            t for t in self._ensure_ix()["tl_by_cosmo"].get(cosmo_id, {}).values()
            if (getattr(t, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid
        ]

    def get_timelines_for_reviewer(self, reviewer_id: str, cycle_id: Optional[str] = None) -> List[BadgeTimeline]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        return [
            t for t in self._ensure_ix()["tl_by_reviewer"].get(reviewer_id, {}).values()
            if (getattr(t, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid
        ]

    def get_reviewer_submissions(self, reviewer_id: str, cycle_id: Optional[str] = None) -> List[ProjectSubmission]:
        """
        Submissions of the cadets a reviewer is responsible for: (badge, cadet) pairs whose timeline names the
        reviewer, OR any cadet listed together with the reviewer in a band mapping. Touches only those
        cadets' own submissions (indexed) instead of scanning every submission of the cycle.
        """
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        pairs = {(t.badge_id, t.cosmonaut_id) for t in self.get_timelines_for_reviewer(reviewer_id, cycle_id=target_cid)}
        mapped_cadets = set()
        for m in self.get_band_mappings(cycle_id=target_cid):
            if reviewer_id in (m.get("reviewers") or []):
                mapped_cadets.update(m.get("cosmonauts") or [])
        cadets = mapped_cadets | {c for _, c in pairs}
        result: List[ProjectSubmission] = []
        for cadet in cadets:
            for sub in self.get_submissions_for_cosmonaut(cadet, cycle_id=target_cid):
                if cadet in mapped_cadets or (sub.badge_id, cadet) in pairs:
                    result.append(sub)
        return result

    def get_timeline(self, badge_id: str, cosmo_id: str) -> Optional[BadgeTimeline]:
        key = f"{badge_id}_{cosmo_id}"
        if key in self.timelines:
            return self.timelines[key]
        if self.db and self.db.conn:
            try:
                row = self.db.conn.execute("SELECT * FROM badge_timelines WHERE badge_id = ? AND cosmonaut_id = ?", (badge_id, cosmo_id)).fetchone()
                if row:
                    tl = BadgeTimeline.from_dict(dict(row))
                    self.timelines[key] = tl
                    return tl
            except Exception:
                pass
        return None

    def save_timeline(self, timeline: BadgeTimeline):
        if not getattr(timeline, "cycle_id", "") or timeline.cycle_id == DEFAULT_CYCLE_ID:
            b_obj = self.get_badge(timeline.badge_id)
            timeline.cycle_id = (getattr(b_obj, "cycle_id", "") if b_obj else "") or self.get_active_cycle_id()
        key = f"{timeline.badge_id}_{timeline.cosmonaut_id}"
        ix = self._ensure_ix()
        self.timelines[key] = timeline
        ix["tl_by_cosmo"].setdefault(timeline.cosmonaut_id, {})[key] = timeline
        old_rid = ix["tl_reviewer_of"].get(key)
        new_rid = getattr(timeline, "reviewer_id", "") or ""
        if old_rid is not None and old_rid != new_rid:
            ix["tl_by_reviewer"].get(old_rid, {}).pop(key, None)
        ix["tl_by_reviewer"].setdefault(new_rid, {})[key] = timeline
        ix["tl_reviewer_of"][key] = new_rid
        self._ix_commit()
        try:
            with self.db.conn:
                self.db.conn.execute(
                    """
                    INSERT OR REPLACE INTO badge_timelines (
                        badge_id, cosmonaut_id, assignment_date, publication_date,
                        learning_start_date, learning_end_date, project_start_date, project_end_date,
                        submission_deadline, review_date, expected_award_date, actual_award_date, status,
                        reviewer_id, review_window_json, cycle_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        getattr(timeline, "review_window_json", "[]"),
                        timeline.cycle_id
                    )
                )
            if self.db and self.db.conn:
                self.db.conn.commit()
        except Exception as e:
            self._write_failed("saving timeline", e)
        self.mark_dirty()

    # --- Submissions ---
    def get_all_submissions(self, cycle_id: Optional[str] = None) -> List[ProjectSubmission]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)

        def build():
            return sorted(
                [s for s in self.submissions.values() if (getattr(s, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid],
                key=lambda s: s.submitted_at,
                reverse=True
            )
        # Cached per cycle until learning data changes (every page render used to filter + sort ALL rows).
        return list(self._memoized(f"all_submissions:{target_cid}", build,
                                   extra=(id(self.submissions), len(self.submissions)), scope="learning"))

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

    def get_submissions_for_cosmonaut(self, cosmo_id: str, badge_id: Optional[str] = None, cycle_id: Optional[str] = None) -> List[ProjectSubmission]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        subs = [
            s for s in self._ensure_ix()["subs_by_cosmo"].get(cosmo_id, {}).values()
            if (getattr(s, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid
        ]
        if badge_id:
            subs = [s for s in subs if s.badge_id == badge_id]
        return sorted(subs, key=lambda s: (s.badge_id, s.attempt_number))

    def save_submission(self, sub: ProjectSubmission):
        if not getattr(sub, "cycle_id", "") or sub.cycle_id == DEFAULT_CYCLE_ID:
            b_obj = self.get_badge(sub.badge_id)
            sub.cycle_id = (getattr(b_obj, "cycle_id", "") if b_obj else "") or self.get_active_cycle_id()
        ix = self._ensure_ix()
        self.submissions[sub.id] = sub
        ix["subs_by_cosmo"].setdefault(sub.cosmonaut_id, {})[sub.id] = sub
        self._ix_commit()
        try:
            if sub.payload_is_lazy:
                # Payload was never loaded into memory -> update metadata only, never rewrite heavy blobs.
                with self.db.conn:
                    self.db.conn.execute(
                        """
                        UPDATE project_submissions SET badge_id = ?, cosmonaut_id = ?, attempt_number = ?,
                            submission_type = ?, file_name = ?, submitted_at = ?, status = ?, pdf_name = ?,
                            code_name = ?, github_url = ?, cycle_id = ? WHERE id = ?
                        """,
                        (sub.badge_id, sub.cosmonaut_id, sub.attempt_number, sub.submission_type, sub.file_name,
                         sub.submitted_at, sub.status, getattr(sub, "pdf_name", ""), getattr(sub, "code_name", ""),
                         getattr(sub, "github_url", ""), sub.cycle_id, sub.id)
                    )
                self.mark_dirty()
                return
            with self.db.conn:
                self.db.conn.execute(
                    """
                    INSERT INTO project_submissions (
                        id, badge_id, cosmonaut_id, attempt_number, submission_type,
                        payload, file_name, submitted_at, status, pdf_name, pdf_payload,
                        code_name, code_payload, github_url, cycle_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        badge_id = excluded.badge_id,
                        cosmonaut_id = excluded.cosmonaut_id,
                        attempt_number = excluded.attempt_number,
                        submission_type = excluded.submission_type,
                        payload = excluded.payload,
                        file_name = excluded.file_name,
                        submitted_at = excluded.submitted_at,
                        status = excluded.status,
                        pdf_name = excluded.pdf_name,
                        pdf_payload = excluded.pdf_payload,
                        code_name = excluded.code_name,
                        code_payload = excluded.code_payload,
                        github_url = excluded.github_url,
                        cycle_id = excluded.cycle_id
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
                        getattr(sub, "github_url", ""),
                        sub.cycle_id
                    )
                )
            if self.db and self.db.conn:
                self.db.conn.commit()
        except Exception as e:
            self._write_failed("saving submission", e)
        self.mark_dirty()

    # --- Assessments ---
    def get_all_assessments(self, cycle_id: Optional[str] = None) -> List[AssessmentMarksheet]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)

        def build():
            return sorted(
                [a for a in self.assessments.values() if (getattr(a, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid],
                key=lambda a: a.reviewed_at,
                reverse=True
            )
        return list(self._memoized(f"all_assessments:{target_cid}", build,
                                   extra=(id(self.assessments), len(self.assessments)), scope="learning"))

    def get_assessment(self, asm_id: str) -> Optional[AssessmentMarksheet]:
        return self.assessments.get(asm_id)

    def get_assessment_for_submission(self, sub_id: str) -> Optional[AssessmentMarksheet]:
        # Return Guardian final assessment if present, otherwise latest assessment
        sub_asms = list(self._ensure_ix()["asms_by_sub"].get(sub_id, {}).values())
        if not sub_asms:
            return None
        guardian_asm = next((a for a in sub_asms if getattr(a, "assessor_role", "guardian") == "guardian"), None)
        return guardian_asm or sub_asms[-1]

    def get_all_assessments_for_submission(self, sub_id: str) -> List[AssessmentMarksheet]:
        return list(self._ensure_ix()["asms_by_sub"].get(sub_id, {}).values())

    def get_reviewer_assessment_for_submission(self, sub_id: str) -> Optional[AssessmentMarksheet]:
        for a in self._ensure_ix()["asms_by_sub"].get(sub_id, {}).values():
            if getattr(a, "assessor_role", "") == "reviewer":
                return a
        return None

    def get_guardian_assessment_for_submission(self, sub_id: str) -> Optional[AssessmentMarksheet]:
        for a in self._ensure_ix()["asms_by_sub"].get(sub_id, {}).values():
            if getattr(a, "assessor_role", "guardian") == "guardian":
                return a
        return None

    def get_assessments_for_cosmonaut(self, cosmo_id: str, badge_id: Optional[str] = None, cycle_id: Optional[str] = None) -> List[AssessmentMarksheet]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        asms = [
            a for a in self._ensure_ix()["asms_by_cosmo"].get(cosmo_id, {}).values()
            if (getattr(a, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid
        ]
        if badge_id:
            asms = [a for a in asms if a.badge_id == badge_id]
        return sorted(asms, key=lambda a: (a.badge_id, a.attempt_number))

    def save_assessment(self, asm: AssessmentMarksheet):
        if not getattr(asm, "cycle_id", "") or asm.cycle_id == DEFAULT_CYCLE_ID:
            b_obj = self.get_badge(asm.badge_id)
            asm.cycle_id = (getattr(b_obj, "cycle_id", "") if b_obj else "") or self.get_active_cycle_id()
        ix = self._ensure_ix()
        self.assessments[asm.id] = asm
        ix["asms_by_cosmo"].setdefault(asm.cosmonaut_id, {})[asm.id] = asm
        ix["asms_by_sub"].setdefault(asm.submission_id, {})[asm.id] = asm
        self._ix_commit()
        try:
            with self.db.conn:
                self.db.conn.execute(
                    """
                    INSERT OR REPLACE INTO assessment_marksheets (
                        id, submission_id, attempt_number, badge_id, cosmonaut_id,
                        reviewer_id, reviewer_name, reviewed_at, decision,
                        business_understanding, architecture_report, technical_knowledge,
                        presentation, qa, total_marks, percentage,
                        strength_areas, improvement_areas, overall_feedback,
                        assessor_role, remarks, cycle_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        getattr(asm, "remarks", ""),
                        asm.cycle_id
                    )
                )
            if self.db and self.db.conn:
                self.db.conn.commit()
        except Exception as e:
            self._write_failed("saving assessment", e)
        self.mark_dirty()

    # --- Materials ---
    def get_materials(self, badge_id: Optional[str] = None, cycle_id: Optional[str] = None) -> List[LearningMaterial]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        mats = [m for m in self.materials.values() if (getattr(m, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid]
        if badge_id:
            mats = [m for m in mats if m.badge_id == badge_id]
        return sorted(mats, key=lambda m: m.upload_date, reverse=True)

    def get_material(self, mat_id: str) -> Optional[LearningMaterial]:
        return self.materials.get(mat_id)

    def save_material(self, mat: LearningMaterial):
        if not getattr(mat, "cycle_id", "") or mat.cycle_id == DEFAULT_CYCLE_ID:
            b_obj = self.get_badge(mat.badge_id)
            mat.cycle_id = (getattr(b_obj, "cycle_id", "") if b_obj else "") or self.get_active_cycle_id()
        self.materials[mat.id] = mat
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO learning_materials (
                    id, badge_id, topic, title, description, material_type, url_or_data, upload_date, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mat.id,
                    mat.badge_id,
                    mat.topic,
                    mat.title,
                    mat.description,
                    mat.material_type,
                    mat.url_or_data,
                    mat.upload_date,
                    mat.cycle_id
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
    def get_all_extensions(self, cycle_id: Optional[str] = None) -> List[DeadlineExtension]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)

        def build():
            return sorted(
                [e for e in self.extensions.values() if (getattr(e, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid],
                key=lambda e: e.requested_at,
                reverse=True
            )
        return list(self._memoized(f"all_extensions:{target_cid}", build,
                                   extra=(id(self.extensions), len(self.extensions)), scope="learning"))

    def get_extensions_for_cosmonaut(self, cosmo_id: str, cycle_id: Optional[str] = None) -> List[DeadlineExtension]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        exts = [
            e for e in self._ensure_ix()["exts_by_cosmo"].get(cosmo_id, {}).values()
            if (getattr(e, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid
        ]
        return sorted(exts, key=lambda e: e.requested_at, reverse=True)

    def get_extension(self, ext_id: str) -> Optional[DeadlineExtension]:
        return self.extensions.get(ext_id)

    def save_extension(self, ext: DeadlineExtension):
        if not getattr(ext, "cycle_id", "") or ext.cycle_id == DEFAULT_CYCLE_ID:
            b_obj = self.get_badge(ext.badge_id)
            ext.cycle_id = (getattr(b_obj, "cycle_id", "") if b_obj else "") or self.get_active_cycle_id()
        ix = self._ensure_ix()
        self.extensions[ext.id] = ext
        ix["exts_by_cosmo"].setdefault(ext.cosmonaut_id, {})[ext.id] = ext
        self._ix_commit()
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO deadline_extensions (
                    id, badge_id, cosmonaut_id, current_deadline, proposed_deadline,
                    reason, status, guardian_response, requested_at, decided_at, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ext.decided_at,
                    ext.cycle_id
                )
            )
        self.mark_dirty()

    # --- Announcements ---
    def get_all_announcements(self, cycle_id: Optional[str] = None) -> List[Announcement]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        return sorted(
            [a for a in self.announcements.values() if (getattr(a, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid],
            key=lambda a: a.published_at,
            reverse=True
        )

    def get_announcements_for_cosmonaut(self, cosmo_id: str, cycle_id: Optional[str] = None) -> List[Announcement]:
        anns = []
        for a in self.get_all_announcements(cycle_id=cycle_id):
            if a.target_type == "all" or cosmo_id in a.target_cosmonaut_ids:
                anns.append(a)
        return anns

    def save_announcement(self, ann: Announcement):
        if not getattr(ann, "cycle_id", "") or ann.cycle_id == DEFAULT_CYCLE_ID:
            ann.cycle_id = self.get_active_cycle_id()
        self.announcements[ann.id] = ann
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO announcements (
                    id, title, message, author_id, author_name, target_type, badge_id, published_at, expiry_date, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ann.expiry_date,
                    ann.cycle_id
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
    def get_activities(self, cosmo_id: Optional[str] = None, cycle_id: Optional[str] = None) -> List[ActivityEvent]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        source = self._ensure_ix()["acts_by_person"].get(cosmo_id, []) if cosmo_id else self.activities
        acts = [a for a in source if (getattr(a, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid]
        return sorted(acts, key=lambda a: a.timestamp, reverse=True)

    def add_activity(
        self,
        event_type: str,
        actor_id: str,
        actor_name: str,
        cosmonaut_id: str,
        badge_id: str,
        summary: str,
        details: str = "",
        cycle_id: Optional[str] = None
    ):
        cid = cycle_id or (getattr(self.get_badge(badge_id), "cycle_id", "") if badge_id else "") or self.get_active_cycle_id()
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
            details=details,
            cycle_id=cid
        )
        ix = self._ensure_ix()
        self.activities.insert(0, event)
        ix["acts_by_person"].setdefault(event.cosmonaut_id, []).insert(0, event)
        if event.actor_id and event.actor_id != event.cosmonaut_id:
            ix["acts_by_person"].setdefault(event.actor_id, []).insert(0, event)
        self._ix_commit()
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO activity_events (
                    id, timestamp, event_type, actor_id, actor_name, cosmonaut_id, badge_id, summary, details, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event.id, event.timestamp, event.event_type, event.actor_id, event.actor_name, event.cosmonaut_id, event.badge_id, event.summary, event.details, cid)
            )
        self.mark_dirty(learning=False)

    # --- Notifications ---
    def get_notifications(self, user_id: str, cycle_id: Optional[str] = None) -> List[Notification]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        notifs = [
            n for n in self._ensure_ix()["notifs_by_user"].get(user_id, [])
            if (getattr(n, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) == target_cid
        ]
        return sorted(notifs, key=lambda n: n.created_at, reverse=True)

    def add_notification(self, recipient_id: str, title: str, message: str, link_section: str = "", event_type: str = "", related_badge_id: str = "", cycle_id: Optional[str] = None):
        cid = cycle_id or (getattr(self.get_badge(related_badge_id), "cycle_id", "") if related_badge_id else "") or self.get_active_cycle_id()
        notif_id = f"notif_{len(self.notifications) + 1}_{int(datetime.datetime.now().timestamp() * 1000)}"
        notif = Notification(
            id=notif_id,
            recipient_id=recipient_id,
            title=title,
            message=message,
            link_section=link_section,
            created_at=current_iso_timestamp(),
            is_read=False,
            cycle_id=cid
        )
        ix = self._ensure_ix()
        self.notifications.insert(0, notif)
        ix["notifs_by_user"].setdefault(notif.recipient_id, []).insert(0, notif)
        self._ix_commit()
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR REPLACE INTO notifications (
                    id, recipient_id, title, message, link_section, created_at, is_read, event_type, related_badge_id, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (notif.id, notif.recipient_id, notif.title, notif.message, notif.link_section, notif.created_at, event_type, related_badge_id, cid)
            )
        self.mark_dirty(learning=False)

    def mark_notification_read(self, notif_id: str):
        for n in self.notifications:
            if n.id == notif_id:
                n.is_read = True
                with self.db.conn:
                    self.db.conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
                self.mark_dirty(learning=False)
                break

    def mark_all_notifications_read(self, user_id: str):
        for n in self.notifications:
            if n.recipient_id == user_id:
                n.is_read = True
        with self.db.conn:
            self.db.conn.execute("UPDATE notifications SET is_read = 1 WHERE recipient_id = ?", (user_id,))
        self.mark_dirty(learning=False)

    # --- Band Mappings & Requests ---
    def get_band_mappings(self, cycle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        if not hasattr(self, "band_mappings") or self.band_mappings is None:
            self.band_mappings = []
        if not self.band_mappings and self.db and self.db.conn:
            try:
                rows = self.db.conn.execute("SELECT data_json, cycle_id FROM band_mappings").fetchall()
                loaded = []
                for r in rows:
                    try:
                        bm_d = json.loads(r[0])
                        if not bm_d.get("cycle_id"):
                            bm_d["cycle_id"] = r[1] if len(r) > 1 and r[1] else DEFAULT_CYCLE_ID
                        loaded.append(bm_d)
                    except Exception:
                        pass
                if loaded:
                    self.band_mappings = loaded
            except Exception:
                pass
        return [m for m in self.band_mappings if (m.get("cycle_id") or DEFAULT_CYCLE_ID) == target_cid]

    def save_band_mapping(self, mapping: Dict[str, Any]):
        if not hasattr(self, "band_mappings") or self.band_mappings is None:
            self.band_mappings = []
        m_id = mapping.get("id")
        b_id = mapping.get("badge_id", "")
        if not b_id and mapping.get("badge"):
            b_val = mapping.get("badge")
            for b in self.get_all_badges(cycle_id=mapping.get("cycle_id")):
                if b.title == b_val or b.code == b_val or b.id == b_val:
                    b_id = b.id
                    mapping["badge_id"] = b.id
                    break
        b_obj = self.get_badge(b_id) if b_id else None
        m_cid = mapping.get("cycle_id") or (getattr(b_obj, "cycle_id", "") if b_obj else "") or self.get_active_cycle_id()
        mapping["cycle_id"] = m_cid

        replaced = False
        for idx, m in enumerate(self.band_mappings):
            if m.get("id") == m_id:
                self.band_mappings[idx] = mapping
                replaced = True
                break
        if not replaced:
            self.band_mappings.insert(0, mapping)
        try:
            with self.db.conn:
                self.db.conn.execute(
                    "INSERT OR REPLACE INTO band_mappings (id, band, badge_id, data_json, cycle_id) VALUES (?, ?, ?, ?, ?)",
                    (m_id, mapping.get("band", "B1"), b_id, json.dumps(mapping), m_cid)
                )
            if self.db and self.db.conn:
                self.db.conn.commit()
        except Exception as e:
            self._write_failed("saving band_mapping", e)
        self.mark_dirty()

    def delete_band_mapping(self, mapping_id: str):
        if hasattr(self, "band_mappings") and self.band_mappings:
            self.band_mappings = [m for m in self.band_mappings if m.get("id") != mapping_id]
        try:
            with self.db.conn:
                self.db.conn.execute("DELETE FROM band_mappings WHERE id = ?", (mapping_id,))
            if self.db and self.db.conn:
                self.db.conn.commit()
        except Exception as e:
            self._write_failed("deleting band_mapping", e)
        self.mark_dirty()

    def get_mapping_requests(self, cycle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        if not hasattr(self, "mapping_requests") or self.mapping_requests is None:
            self.mapping_requests = []
        if not self.mapping_requests and self.db and self.db.conn:
            try:
                rows = self.db.conn.execute("SELECT data_json, cycle_id FROM mapping_requests").fetchall()
                loaded = []
                for r in rows:
                    try:
                        mr_d = json.loads(r[0])
                        if not mr_d.get("cycle_id"):
                            mr_d["cycle_id"] = r[1] if len(r) > 1 and r[1] else DEFAULT_CYCLE_ID
                        loaded.append(mr_d)
                    except Exception:
                        pass
                if loaded:
                    self.mapping_requests = loaded
            except Exception:
                pass
        return [r for r in self.mapping_requests if (r.get("cycle_id") or DEFAULT_CYCLE_ID) == target_cid]

    def add_mapping_request(self, req: Dict[str, Any]):
        if not hasattr(self, "mapping_requests") or self.mapping_requests is None:
            self.mapping_requests = []
        req_id = req.get("id")
        b_id = req.get("badge_id", "")
        b_obj = self.get_badge(b_id) if b_id else None
        r_cid = req.get("cycle_id") or (getattr(b_obj, "cycle_id", "") if b_obj else "") or self.get_active_cycle_id()
        req["cycle_id"] = r_cid
        replaced = False
        for idx, r in enumerate(self.mapping_requests):
            if r.get("id") == req_id:
                self.mapping_requests[idx] = req
                replaced = True
                break
        if not replaced:
            self.mapping_requests.append(req)
        try:
            with self.db.conn:
                self.db.conn.execute(
                    "INSERT OR REPLACE INTO mapping_requests (id, band, reviewer_id, status, data_json, cycle_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (req_id, req.get("band", ""), req.get("reviewer_id", ""), req.get("status", "pending"), json.dumps(req), r_cid)
                )
            if self.db and self.db.conn:
                self.db.conn.commit()
        except Exception as e:
            self._write_failed("adding mapping request", e)
        self.mark_dirty()

    def update_mapping_request_status(self, req_id: str, status: str, cycle_id: Optional[str] = None):
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        if not hasattr(self, "mapping_requests") or not self.mapping_requests:
            self.get_mapping_requests(cycle_id=target_cid)
        scoped_reqs = [r for r in self.mapping_requests if (r.get("cycle_id") or DEFAULT_CYCLE_ID) == target_cid]
        # Prefer exact ID match before legacy band+reviewer fallback within target_cid
        target_r = next((r for r in scoped_reqs if r.get("id") == req_id), None)
        if not target_r:
            target_r = next(
                (r for r in scoped_reqs if f"req_{r.get('band')}_{r.get('reviewer_id')}" == req_id or r.get("id", "").startswith(req_id)),
                None
            )
        if target_r:
            target_r["status"] = status
            actual_id = target_r.get("id")
            try:
                with self.db.conn:
                    self.db.conn.execute("UPDATE mapping_requests SET status = ?, data_json = ? WHERE id = ?", (status, json.dumps(target_r), actual_id))
                if self.db and self.db.conn:
                    self.db.conn.commit()
            except Exception as e:
                self._write_failed("updating mapping request status", e)
            self.mark_dirty()

    def delete_mapping_request(self, req_id: str, cycle_id: Optional[str] = None):
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        if not hasattr(self, "mapping_requests") or not self.mapping_requests:
            self.get_mapping_requests(cycle_id=target_cid)
        if hasattr(self, "mapping_requests") and self.mapping_requests:
            to_delete = []
            for r in self.mapping_requests:
                if (r.get("cycle_id") or DEFAULT_CYCLE_ID) != target_cid:
                    continue
                legacy_id = f"req_{r.get('band')}_{r.get('reviewer_id')}"
                if r.get("id") == req_id or legacy_id == req_id or r.get("id", "").startswith(req_id):
                    to_delete.append(r.get("id"))
            if to_delete:
                self.mapping_requests = [r for r in self.mapping_requests if r.get("id") not in to_delete]
                try:
                    with self.db.conn:
                        for del_id in to_delete:
                            self.db.conn.execute("DELETE FROM mapping_requests WHERE id = ?", (del_id,))
                    if self.db and self.db.conn:
                        self.db.conn.commit()
                except Exception as e:
                    self._write_failed("deleting mapping request", e)
                self.mark_dirty()

    def clear_mapping_requests(self, band: Optional[str] = None, cycle_id: Optional[str] = None):
        if not hasattr(self, "mapping_requests"):
            self.mapping_requests = []
            return
        target_cid = cycle_id or self.get_active_cycle_id()
        if band:
            self.mapping_requests = [
                r for r in self.mapping_requests
                if not (r.get("band") == band and (r.get("cycle_id") or DEFAULT_CYCLE_ID) == target_cid)
            ]
            try:
                with self.db.conn:
                    self.db.conn.execute("DELETE FROM mapping_requests WHERE band = ? AND cycle_id = ?", (band, target_cid))
                if self.db and self.db.conn:
                    self.db.conn.commit()
            except Exception:
                pass
        else:
            self.mapping_requests = [
                r for r in self.mapping_requests
                if (r.get("cycle_id") or DEFAULT_CYCLE_ID) != target_cid
            ]
            try:
                with self.db.conn:
                    self.db.conn.execute("DELETE FROM mapping_requests WHERE cycle_id = ?", (target_cid,))
                if self.db and self.db.conn:
                    self.db.conn.commit()
            except Exception:
                pass
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

        b_obj = self.get_badge(p_dict.get("badge_id", ""))
        p_cid = p_dict.get("cycle_id")
        if not p_cid or p_cid == DEFAULT_CYCLE_ID:
            p_cid = (getattr(b_obj, "cycle_id", "") if b_obj else "") or self.get_active_cycle_id()
        obj.cycle_id = p_cid
        p_dict["cycle_id"] = p_cid

        if not hasattr(self, "reviewer_projects") or not isinstance(self.reviewer_projects, dict):
            self.reviewer_projects = {}
        self.reviewer_projects[p_id] = obj

        try:
            with self.db.conn:
                self.db.conn.execute("""
                    INSERT OR REPLACE INTO reviewer_project_prompts (
                        id, badge_id, reviewer_id, cosmonaut_ids_json, title, description,
                        deliverables_json, requirements_text, outcomes_json, status, created_at, sent_at, cycle_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    p_dict.get("sent_at"),
                    p_cid
                ))
            if self.db and self.db.conn:
                self.db.conn.commit()
        except Exception as e:
            self._write_failed("saving reviewer_project_prompt", e)
        self.mark_dirty()

    def get_reviewer_project_prompts(self, badge_id: Optional[str] = None, reviewer_id: Optional[str] = None, cycle_id: Optional[str] = None) -> List[Any]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        results = []
        try:
            if self.db and self.db.conn:
                query = "SELECT * FROM reviewer_project_prompts WHERE cycle_id = ?"
                params = [target_cid]
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
                if (getattr(p, "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) != target_cid:
                    continue
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

        tl = self.get_timeline(badge_id, cosmonaut_id)
        if tl:
            tl.status = "completed"
            if not tl.actual_award_date:
                tl.actual_award_date = current_iso_timestamp()[:10]
            self.save_timeline(tl)

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

    def get_pending_badge_approvals(self, reviewer_id: Optional[str] = None, target_band: Optional[str] = None, cycle_id: Optional[str] = None) -> List[Badge]:
        pending = [b for b in self.get_all_badges(cycle_id=cycle_id) if getattr(b, "workflow_status", "approved") == "pending_review"]
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

        if not badge_data.get("cycle_id"):
            badge_data["cycle_id"] = self.get_active_cycle_id()

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
                assigned_reviewer_id=badge_data.get("assigned_reviewer_id") or badge_data.get("reviewer_id", ""),
                cycle_id=badge_data["cycle_id"]
            )
            # Reload notifications & activities
            self._sync_feed_tables()
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
            self._sync_feed_tables()
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
            self._sync_feed_tables()
            self.mark_dirty()
        return ok, msg

    def assign_and_request_badge_review(self, badge_id: str, reviewer_id: str, creator_id: str = "guardian_1") -> Tuple[bool, str]:
        ok, msg = self.db.assign_and_request_badge_review(badge_id, reviewer_id, creator_id)
        if ok:
            b = self.get_badge(badge_id)
            if b:
                b.workflow_status = "pending_review"
                b.assigned_reviewer_id = reviewer_id
            self._sync_feed_tables()
            self.mark_dirty()
        return ok, msg

    def get_badge_review_requests_for_user(self, user_id: str, cycle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.db.get_badge_review_requests_for_user(user_id, cycle_id=self.get_effective_read_cycle_id(cycle_id))

    def get_badge_review_history(self, badge_id: Optional[str] = None, reviewer_id: Optional[str] = None, cycle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.db.get_badge_review_history(badge_id=badge_id, reviewer_id=reviewer_id, cycle_id=self.get_effective_read_cycle_id(cycle_id))

    def get_submitted_badges_for_approval(self, status_filter: str = "all", cycle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.db.get_submitted_badges_for_approval(status_filter, cycle_id=self.get_effective_read_cycle_id(cycle_id))

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
        write_cycle_id = badge_dict.get("cycle_id") or self.get_active_cycle_id()

        clean_skill = re.sub(r'[^a-zA-Z0-9]+', '_', skill.strip().lower()).strip('_')
        canonical_id = f"badge_{band.lower()}_{clean_skill}"
        provided_id = badge_dict.get("id")

        # Find existing badge in this band AND current cycle matching skill or ID
        cycle_badges = self.get_all_badges(cycle_id=write_cycle_id)
        existing_badge = None
        for existing in cycle_badges:
            if getattr(existing, "target_band", "") == band:
                if (provided_id and existing.id == provided_id) or \
                   (getattr(existing, "skill", "").strip().lower() == skill.lower()) or \
                   (existing.id == canonical_id) or (existing.id == f"{write_cycle_id}__{canonical_id}"):
                    existing_badge = existing
                    break

        if existing_badge:
            is_custom_provided = bool(provided_id and provided_id != canonical_id and not provided_id.startswith(f"badge_{band.lower()}_"))
            is_custom_existing = bool(existing_badge.id != canonical_id and not existing_badge.id.startswith(f"badge_{band.lower()}_"))
            if is_custom_provided and is_custom_existing and provided_id != existing_badge.id:
                return False, f"A badge for skill '{skill}' already exists for Band {band} ('{existing_badge.title}'). Duplicate badges are not allowed in the same band.", None
            b_id = existing_badge.id
        else:
            candidate_id = provided_id or canonical_id
            # Avoid overwriting a badge with the same ID that belongs to a different cycle
            if candidate_id in self.badges and (getattr(self.badges[candidate_id], "cycle_id", DEFAULT_CYCLE_ID) or DEFAULT_CYCLE_ID) != write_cycle_id:
                candidate_id = f"{write_cycle_id}__{candidate_id}"
            b_id = candidate_id

        # Deduplication check across OTHER badges in the same band & same cycle
        for existing in cycle_badges:
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
            default_timeline=default_timeline,
            cycle_id=write_cycle_id
        )
        self.save_badge(badge)
        self.add_activity(
            event_type="badge_saved",
            actor_id=creator_id,
            actor_name="Guardian",
            cosmonaut_id="",
            badge_id=b_id,
            summary=f"Saved badge '{title}' -> {skill} -> {cap} -> {power} -> Band {band}.",
            cycle_id=write_cycle_id
        )
        self.mark_dirty()
        return True, "Badge saved successfully!", badge

    def get_saved_badges(self, band: Optional[str] = None, cycle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        target_cid = self.get_effective_read_cycle_id(cycle_id)
        # Sync from SQLite to ensure latest badges across all processes/tabs
        cycle_badges = self.get_all_badges(cycle_id=target_cid)

        results = []
        for b in cycle_badges:
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
                        ra_row = self.db.conn.execute(
                            "SELECT decision_notes FROM badge_reviewer_assignments WHERE badge_id = ? AND cycle_id = ? ORDER BY assigned_at DESC LIMIT 1",
                            (b.id, target_cid)
                        ).fetchone()
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
