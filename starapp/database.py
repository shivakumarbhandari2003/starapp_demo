"""
STARAPP SQLITE DATABASE ENGINE & SCHEMA ARCHITECTURE
Acts as the authoritative, persistent, structured database for StarApp.
Operates client-side via Python's built-in sqlite3 inside Pyodide WebAssembly,
and persists across browser reloads via IndexedDB binary file export/import.
"""

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    sqlite3 = None
    SQLITE_AVAILABLE = False
import os
import json
import base64
import datetime
from typing import Dict, Any, List, Optional, Tuple

SCHEMA_VERSION = 11

def current_iso_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def review_deadline_iso_timestamp(hours: int = 24) -> str:
    due = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours)
    return due.isoformat()

# ==============================================================================
# SQL DDL DEFINITIONS
# ==============================================================================

DDL_SCHEMA = """
PRAGMA foreign_keys = ON;

-- 1. System Roles
CREATE TABLE IF NOT EXISTS system_roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);

-- 2. Permissions
CREATE TABLE IF NOT EXISTS permissions (
    id TEXT PRIMARY KEY,
    description TEXT
);

-- 3. Role Permissions
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id TEXT NOT NULL REFERENCES system_roles(id) ON DELETE CASCADE,
    permission_id TEXT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- 4. Bands
CREATE TABLE IF NOT EXISTS bands (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    title TEXT NOT NULL,
    level TEXT NOT NULL,
    experience TEXT NOT NULL,
    description TEXT NOT NULL,
    order_idx INTEGER NOT NULL
);

-- 5. Learning Tracks
CREATE TABLE IF NOT EXISTS learning_tracks (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    color TEXT,
    icon TEXT
);

-- 6. Users / Employees
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    age INTEGER NOT NULL DEFAULT 30,
    role TEXT NOT NULL DEFAULT 'Solutions Designer',
    learning_track TEXT NOT NULL DEFAULT 'Solutions Designer',
    track_code TEXT NOT NULL DEFAULT 'SD',
    band TEXT NOT NULL DEFAULT 'B1',
    reporting_manager_id TEXT,
    reporting_manager_name TEXT,
    reporting_manager_band TEXT,
    password TEXT NOT NULL DEFAULT '12345678',
    primary_role TEXT NOT NULL DEFAULT 'cosmonaut',
    avatar TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_demo INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- View: employees (for enterprise employee queries)
CREATE VIEW IF NOT EXISTS employees AS
SELECT
    id,
    id AS employee_id,
    name AS employee_name,
    age,
    role,
    learning_track,
    track_code,
    band,
    reporting_manager_id,
    reporting_manager_name,
    reporting_manager_band,
    email,
    password,
    primary_role,
    avatar,
    status,
    created_at
FROM users;

-- Management & Reporting Hierarchy
CREATE TABLE IF NOT EXISTS employee_reporting (
    manager_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    employee_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    manager_band TEXT NOT NULL,
    employee_band TEXT NOT NULL,
    PRIMARY KEY (manager_id, employee_id)
);

-- 7. User Role Assignments (Many-to-Many: user can have multiple responsibilities)
CREATE TABLE IF NOT EXISTS user_role_assignments (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id TEXT NOT NULL REFERENCES system_roles(id) ON DELETE CASCADE,
    assigned_at TEXT NOT NULL,
    PRIMARY KEY (user_id, role_id)
);

-- 8. User Band Memberships
CREATE TABLE IF NOT EXISTS user_band_memberships (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    band_code TEXT NOT NULL REFERENCES bands(code),
    track_code TEXT NOT NULL REFERENCES learning_tracks(code),
    assigned_at TEXT NOT NULL
);

-- 9. Cosmonaut Profiles
CREATE TABLE IF NOT EXISTS cosmonaut_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    batch_name TEXT NOT NULL DEFAULT 'Orion-24',
    assigned_guardian_id TEXT REFERENCES users(id),
    guardian_credentials TEXT,
    skills_json TEXT NOT NULL DEFAULT '[]',
    certifications_json TEXT NOT NULL DEFAULT '[]'
);

-- 10. Badge Reviewer Qualifications
CREATE TABLE IF NOT EXISTS badge_reviewer_qualifications (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    min_band TEXT REFERENCES bands(code),
    max_band TEXT REFERENCES bands(code),
    is_active INTEGER NOT NULL DEFAULT 1
);

-- 11. Custom Capabilities & Skills (persisted and reusable across badge creation)
CREATE TABLE IF NOT EXISTS custom_capabilities (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_by TEXT REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    capability_name TEXT DEFAULT '',
    created_by TEXT REFERENCES users(id),
    created_at TEXT NOT NULL
);

-- 12. Badges (Enhanced with workflow status, target band, power, capability, skill, prompt)
CREATE TABLE IF NOT EXISTS badges (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    learning_outcomes_json TEXT NOT NULL DEFAULT '[]',
    learning_topics_json TEXT NOT NULL DEFAULT '[]',
    project_requirements TEXT NOT NULL DEFAULT '',
    is_published INTEGER NOT NULL DEFAULT 1,
    is_allocated INTEGER NOT NULL DEFAULT 1,
    target_band TEXT REFERENCES bands(code),
    power TEXT,
    capability TEXT,
    skill TEXT,
    prompt_json TEXT,
    workflow_status TEXT NOT NULL DEFAULT 'approved', -- 'pending_review', 'approved', 'returned'
    creator_id TEXT REFERENCES users(id),
    assigned_reviewer_id TEXT REFERENCES users(id),
    assigned_cosmonaut_ids_json TEXT NOT NULL DEFAULT '[]',
    default_timeline_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 13. Normalized Badge Powers, Capabilities, and Skills
CREATE TABLE IF NOT EXISTS badge_powers (
    badge_id TEXT PRIMARY KEY REFERENCES badges(id) ON DELETE CASCADE,
    power_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS badge_capabilities (
    badge_id TEXT PRIMARY KEY REFERENCES badges(id) ON DELETE CASCADE,
    capability_name TEXT NOT NULL,
    is_custom INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS badge_skills (
    badge_id TEXT PRIMARY KEY REFERENCES badges(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    is_custom INTEGER NOT NULL DEFAULT 0
);

-- 14. Badge Reviewer Assignments
CREATE TABLE IF NOT EXISTS badge_reviewer_assignments (
    id TEXT PRIMARY KEY,
    badge_id TEXT NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    reviewer_id TEXT NOT NULL REFERENCES users(id),
    assigned_at TEXT NOT NULL,
    review_due_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'returned'
    decision_notes TEXT DEFAULT '',
    decided_at TEXT
);

-- 15. Badge Review Events (Complete audit history for badge creation, edits, approvals)
CREATE TABLE IF NOT EXISTS badge_review_events (
    id TEXT PRIMARY KEY,
    badge_id TEXT NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    actor_id TEXT NOT NULL REFERENCES users(id),
    event_type TEXT NOT NULL, -- 'created_and_submitted', 'edited', 'approved', 'returned'
    previous_status TEXT,
    new_status TEXT,
    notes TEXT,
    timestamp TEXT NOT NULL
);

-- 16. Badge Prerequisites
CREATE TABLE IF NOT EXISTS badge_prerequisites (
    badge_id TEXT NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    prerequisite_badge_id TEXT NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    PRIMARY KEY (badge_id, prerequisite_badge_id)
);

-- 17. Badge Timelines
CREATE TABLE IF NOT EXISTS badge_timelines (
    badge_id TEXT NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    cosmonaut_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_date TEXT,
    publication_date TEXT,
    learning_start_date TEXT,
    learning_end_date TEXT,
    project_start_date TEXT,
    project_end_date TEXT,
    submission_deadline TEXT,
    review_date TEXT,
    expected_award_date TEXT,
    actual_award_date TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    PRIMARY KEY (badge_id, cosmonaut_id)
);

-- 18. Project Submissions
CREATE TABLE IF NOT EXISTS project_submissions (
    id TEXT PRIMARY KEY,
    badge_id TEXT NOT NULL REFERENCES badges(id),
    cosmonaut_id TEXT NOT NULL REFERENCES users(id),
    attempt_number INTEGER NOT NULL DEFAULT 1,
    submission_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    file_name TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    pdf_name TEXT DEFAULT '',
    pdf_payload TEXT DEFAULT '',
    code_name TEXT DEFAULT '',
    code_payload TEXT DEFAULT '',
    github_url TEXT DEFAULT ''
);

-- 19. Assessment Marksheets
CREATE TABLE IF NOT EXISTS assessment_marksheets (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL REFERENCES project_submissions(id),
    attempt_number INTEGER NOT NULL DEFAULT 1,
    badge_id TEXT NOT NULL REFERENCES badges(id),
    cosmonaut_id TEXT NOT NULL REFERENCES users(id),
    reviewer_id TEXT NOT NULL REFERENCES users(id),
    reviewer_name TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    decision TEXT NOT NULL,
    business_understanding REAL NOT NULL DEFAULT 0.0,
    architecture_report REAL NOT NULL DEFAULT 0.0,
    technical_knowledge REAL NOT NULL DEFAULT 0.0,
    presentation REAL NOT NULL DEFAULT 0.0,
    qa REAL NOT NULL DEFAULT 0.0,
    total_marks REAL NOT NULL DEFAULT 0.0,
    percentage REAL NOT NULL DEFAULT 0.0,
    strength_areas TEXT DEFAULT '',
    improvement_areas TEXT DEFAULT '',
    overall_feedback TEXT DEFAULT ''
);

-- 20. Learning Materials
CREATE TABLE IF NOT EXISTS learning_materials (
    id TEXT PRIMARY KEY,
    badge_id TEXT NOT NULL REFERENCES badges(id),
    topic TEXT NOT NULL DEFAULT 'General',
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    material_type TEXT NOT NULL,
    url_or_data TEXT NOT NULL,
    upload_date TEXT NOT NULL
);

-- 21. Deadline Extensions
CREATE TABLE IF NOT EXISTS deadline_extensions (
    id TEXT PRIMARY KEY,
    badge_id TEXT NOT NULL REFERENCES badges(id),
    cosmonaut_id TEXT NOT NULL REFERENCES users(id),
    current_deadline TEXT NOT NULL,
    proposed_deadline TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    guardian_response TEXT DEFAULT '',
    requested_at TEXT NOT NULL,
    decided_at TEXT DEFAULT ''
);

-- 22. Announcements & Recipients & Read Receipts
CREATE TABLE IF NOT EXISTS announcements (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    author_id TEXT NOT NULL REFERENCES users(id),
    author_name TEXT NOT NULL,
    target_type TEXT NOT NULL DEFAULT 'all',
    badge_id TEXT DEFAULT '',
    published_at TEXT NOT NULL,
    expiry_date TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS announcement_recipients (
    announcement_id TEXT NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
    cosmonaut_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (announcement_id, cosmonaut_id)
);

CREATE TABLE IF NOT EXISTS announcement_read_receipts (
    announcement_id TEXT NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
    cosmonaut_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    read_at TEXT NOT NULL,
    PRIMARY KEY (announcement_id, cosmonaut_id)
);

-- 23. Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    recipient_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    link_section TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    event_type TEXT DEFAULT '',
    related_badge_id TEXT
);

-- 24. Activity Events
CREATE TABLE IF NOT EXISTS activity_events (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL REFERENCES users(id),
    actor_name TEXT NOT NULL,
    cosmonaut_id TEXT,
    badge_id TEXT,
    summary TEXT NOT NULL,
    details TEXT DEFAULT ''
);

-- 25. Band Mappings & Review Requests
CREATE TABLE IF NOT EXISTS band_mappings (
    id TEXT PRIMARY KEY,
    band TEXT NOT NULL REFERENCES bands(code),
    badge_id TEXT,
    data_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mapping_requests (
    id TEXT PRIMARY KEY,
    band TEXT NOT NULL,
    reviewer_id TEXT NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'pending',
    data_json TEXT NOT NULL
);

-- 26. Reviewer Authored Project Prompts for Mapped Cadets
CREATE TABLE IF NOT EXISTS reviewer_project_prompts (
    id TEXT PRIMARY KEY,
    badge_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL REFERENCES users(id),
    cosmonaut_ids_json TEXT NOT NULL DEFAULT '[]',
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    deliverables_json TEXT NOT NULL DEFAULT '{}',
    requirements_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    sent_at TEXT
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_badges_target_band ON badges(target_band);
CREATE INDEX IF NOT EXISTS idx_badges_workflow_status ON badges(workflow_status);
CREATE INDEX IF NOT EXISTS idx_submissions_badge_cosmo ON project_submissions(badge_id, cosmonaut_id);
CREATE INDEX IF NOT EXISTS idx_assessments_sub_id ON assessment_marksheets(submission_id);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_id, is_read);
CREATE INDEX IF NOT EXISTS idx_activity_events_timestamp ON activity_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_badge_reviewer_assignments_reviewer ON badge_reviewer_assignments(reviewer_id, status);
CREATE INDEX IF NOT EXISTS idx_rev_proj_badge ON reviewer_project_prompts(badge_id);
CREATE INDEX IF NOT EXISTS idx_rev_proj_reviewer ON reviewer_project_prompts(reviewer_id);
"""

# ==============================================================================
# DATABASE MANAGER
# ==============================================================================

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to Pyodide virtual fs or authoritative data/starapp.db
            if os.path.exists("/home/pyodide"):
                db_path = "/home/pyodide/starapp.db"
            elif os.path.exists(os.path.join(os.getcwd(), "data", "starapp.db")):
                db_path = os.environ.get("STARAPP_DB_PATH", os.path.join(os.getcwd(), "data", "starapp.db"))
            else:
                db_path = os.environ.get("STARAPP_DB_PATH", "data/starapp.db")
        self.db_path = db_path
        self._conn: Optional[Any] = None
        if SQLITE_AVAILABLE:
            self.connect()
        else:
            print("[StarApp Warning] sqlite3 module not available in Python runtime.")

    def connect(self):
        """Establishes SQLite connection with foreign keys enabled."""
        if not SQLITE_AVAILABLE:
            return
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
        parent_dir = os.path.dirname(self.db_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception:
                pass
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA busy_timeout = 5000;")
        self.create_tables()
        self._conn.execute("PRAGMA foreign_keys = ON;")

    def close(self):
        """Closes SQLite connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def get_schema_version(self) -> int:
        """Returns the current schema version from schema_version table."""
        if not SQLITE_AVAILABLE or self.conn is None:
            return SCHEMA_VERSION
        try:
            row = self.conn.execute("SELECT version FROM schema_version ORDER BY installed_at DESC LIMIT 1").fetchone()
            if row:
                return row["version"]
        except Exception:
            pass
        return SCHEMA_VERSION

    @property
    def conn(self) -> Any:
        if not SQLITE_AVAILABLE:
            return None
        if self._conn is None:
            self.connect()
        return self._conn

    def create_tables(self):
        """Executes idempotent schema creation."""
        if not SQLITE_AVAILABLE or self.conn is None:
            return
        self.conn.executescript(DDL_SCHEMA)
        try:
            self.conn.execute("ALTER TABLE custom_skills ADD COLUMN capability_name TEXT DEFAULT '';")
        except Exception:
            pass

        # Schema migration for users table if existing table lacks enterprise columns
        try:
            existing_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(users)").fetchall()}
            if existing_cols:
                needed_cols = [
                    ("age", "INTEGER NOT NULL DEFAULT 30"),
                    ("role", "TEXT NOT NULL DEFAULT 'Solutions Designer'"),
                    ("learning_track", "TEXT NOT NULL DEFAULT 'Solutions Designer'"),
                    ("track_code", "TEXT NOT NULL DEFAULT 'SD'"),
                    ("band", "TEXT NOT NULL DEFAULT 'B1'"),
                    ("reporting_manager_id", "TEXT"),
                    ("reporting_manager_name", "TEXT"),
                    ("reporting_manager_band", "TEXT"),
                    ("password", "TEXT NOT NULL DEFAULT '12345678'"),
                ]
                for col_name, col_def in needed_cols:
                    if col_name not in existing_cols:
                        self.conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def};")
        except Exception:
            pass

        # Safe Column Migrations for Complete Assessment & Mapping Workflow
        workflow_cols = [
            ("assessment_marksheets", "assessor_role", "TEXT DEFAULT 'guardian'"),
            ("assessment_marksheets", "remarks", "TEXT DEFAULT ''"),
            ("badges", "passing_percentage", "REAL DEFAULT 70.0"),
            ("badges", "published_at", "TEXT DEFAULT ''"),
            ("badges", "published_by", "TEXT DEFAULT ''"),
            ("badge_timelines", "reviewer_id", "TEXT DEFAULT ''"),
            ("badge_timelines", "review_window_json", "TEXT DEFAULT '[]'"),
        ]
        for tbl, col, col_def in workflow_cols:
            try:
                self.conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def};")
            except Exception:
                pass

        self.conn.commit()

    def clear_all_tables(self):
        """Clears all domain tables for a clean baseline reset."""
        if not SQLITE_AVAILABLE or self.conn is None:
            return
        with self.conn:
            self.conn.execute("PRAGMA foreign_keys = OFF;")
            tables = [
                "badge_review_events", "badge_reviewer_assignments", "badge_powers",
                "badge_capabilities", "badge_skills", "badge_prerequisites", "badge_timelines",
                "assessment_marksheets", "project_submissions", "deadline_extensions",
                "learning_materials", "announcement_read_receipts", "announcement_recipients",
                "announcements", "notifications", "activity_events", "band_mappings",
                "mapping_requests", "reviewer_project_prompts", "custom_capabilities", "custom_skills", "cosmonaut_profiles",
                "user_band_memberships", "badge_reviewer_qualifications", "user_role_assignments",
                "employee_reporting", "badges", "users"
            ]
            for t in tables:
                self.conn.execute(f"DELETE FROM {t};")
            self.conn.execute("PRAGMA foreign_keys = ON;")

    def seed_system_metadata(self):
        """Seeds system roles, permissions, bands, and learning tracks idempotently."""
        c = self.conn

        # 1. System Roles
        roles = [
            ("guardian", "Guardian", "Cohort evaluator, mentor, and curriculum creator"),
            ("badge_reviewer", "Badge Reviewer", "Authorized reviewer for proposed badges in lower bands"),
            ("project_reviewer", "Project Reviewer", "Evaluator for project deliverables and submissions"),
            ("cosmonaut", "Cosmonaut", "Engineering trainee, cadet, and badge earner")
        ]
        c.executemany("INSERT OR IGNORE INTO system_roles (id, name, description) VALUES (?, ?, ?)", roles)

        # 2. Permissions
        permissions = [
            ("create_badge", "Create new badges and author prompts"),
            ("approve_badge", "Inspect, edit, and approve badges submitted for review"),
            ("allot_badge", "Allot and publish badges to cohort roadmaps"),
            ("review_project", "Grade project deliverables using 50-mark rubric"),
            ("submit_project", "Upload deliverables for badge assessment"),
            ("request_extension", "Request deadline extensions")
        ]
        c.executemany("INSERT OR IGNORE INTO permissions (id, description) VALUES (?, ?)", permissions)

        # 3. Role Permissions
        rp = [
            ("guardian", "create_badge"),
            ("guardian", "allot_badge"),
            ("guardian", "review_project"),
            ("badge_reviewer", "approve_badge"),
            ("project_reviewer", "review_project"),
            ("cosmonaut", "submit_project"),
            ("cosmonaut", "request_extension")
        ]
        c.executemany("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)", rp)

        # 4. Bands B1 to B6 and Executive CEO
        from starapp.mapping_data import BANDS
        band_records = [
            (b["code"], b["name"], b["title"], b["level"], b["experience"], b["description"], idx)
            for idx, b in enumerate(BANDS)
        ]
        band_records.append(
            ("CEO", "Executive Council", "Chief Executive Officer", "Executive", "20+ years", "Executive leadership, corporate strategy, and organizational governance.", 6)
        )
        c.executemany(
            "INSERT OR REPLACE INTO bands (code, name, title, level, experience, description, order_idx) VALUES (?, ?, ?, ?, ?, ?, ?)",
            band_records
        )

        # 5. Learning Tracks (SD, AIE, SE, EXEC)
        tracks = [
            ("SD", "Solutions Designer", "System architecture, domain modeling & solution workflows", "#4F46E5", "layers"),
            ("AIE", "AI Engineer", "Machine learning pipelines, agent orchestration & LLM reasoning", "#059669", "cpu"),
            ("SE", "Systems Engineer", "Infrastructure, networking, distributed reliability & cloud fabric", "#0284C7", "terminal"),
            ("EXEC", "Executive Leadership", "Corporate strategy and organizational governance", "#7C3AED", "shield")
        ]
        c.executemany(
            "INSERT OR REPLACE INTO learning_tracks (code, name, description, color, icon) VALUES (?, ?, ?, ?, ?)",
            tracks
        )

        # 6. Seed 36 Corporate Demo Members
        from starapp.mapping_data import DUMMY_MEMBERS
        for m in DUMMY_MEMBERS:
            u_id = m["id"]
            u_name = m["name"]
            u_uname = m.get("username", m["name"].lower().replace(" ", "."))
            u_email = m["email"]
            u_avatar = m.get("avatar", u_name[:2].upper())
            roles_list = m.get("application_roles", ["cosmonaut"])
            primary_role = roles_list[0] if roles_list else "cosmonaut"
            u_age = m.get("age", 30)
            u_role = m.get("role", "Solutions Designer")
            u_track = m.get("learning_track", "Solutions Designer")
            u_track_code = m.get("track_code", "SD")
            u_band = m.get("band", "B1")
            u_mgr_id = m.get("reporting_manager_id")
            u_mgr_name = m.get("reporting_manager_name")
            u_mgr_band = m.get("reporting_manager_band")
            u_pwd = m.get("password", "12345678")

            c.execute(
                """
                INSERT OR REPLACE INTO users (
                    id, username, email, name, age, role, learning_track, track_code, band,
                    reporting_manager_id, reporting_manager_name, reporting_manager_band,
                    password, primary_role, avatar, status, is_demo, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?)
                """,
                (
                    u_id, u_uname, u_email, u_name, u_age, u_role, u_track, u_track_code, u_band,
                    u_mgr_id, u_mgr_name, u_mgr_band, u_pwd, primary_role, u_avatar, current_iso_timestamp()
                )
            )

            # Assign roles
            for r in roles_list:
                c.execute(
                    "INSERT OR IGNORE INTO user_role_assignments (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                    (u_id, r, current_iso_timestamp())
                )

            # Assign band membership
            c.execute(
                """
                INSERT OR REPLACE INTO user_band_memberships (user_id, band_code, track_code, assigned_at)
                VALUES (?, ?, ?, ?)
                """,
                (u_id, u_band, u_track_code, current_iso_timestamp())
            )

            # Direct reports hierarchy
            for rep_id in m.get("direct_reports", []):
                rep_m = next((x for x in DUMMY_MEMBERS if x["id"] == rep_id), None)
                rep_band = rep_m["band"] if rep_m else "B1"
                c.execute(
                    """
                    INSERT OR REPLACE INTO employee_reporting (manager_id, employee_id, manager_band, employee_band)
                    VALUES (?, ?, ?, ?)
                    """,
                    (u_id, rep_id, u_band, rep_band)
                )

            # Assign badge reviewer qualifications if applicable
            if "badge_reviewer" in roles_list:
                min_b = "B1"
                max_b = u_band if u_band != "CEO" else "B6"
                c.execute(
                    """
                    INSERT OR REPLACE INTO badge_reviewer_qualifications (user_id, min_band, max_band, is_active)
                    VALUES (?, ?, ?, 1)
                    """,
                    (u_id, min_b, max_b)
                )

        # Seed alias for cosmo_1 pointing to Aarav Sharma so existing test suites and session keys resolve
        c.execute(
            """
            INSERT OR REPLACE INTO users (
                id, username, email, name, age, role, learning_track, track_code, band,
                reporting_manager_id, reporting_manager_name, reporting_manager_band,
                password, primary_role, avatar, status, is_demo, created_at
            )
            VALUES ('cosmo_1', 'astraea', 'cosmo.aarav@starapp.io', 'Aarav Sharma', 26, 'Solutions Designer', 'Solutions Designer', 'SD', 'B1',
                    'm_b2_1', 'Rohan Deshmukh', 'B2', '12345678', 'cosmonaut', 'AS', 'active', 1, ?)
            """,
            (current_iso_timestamp(),)
        )
        c.execute("INSERT OR IGNORE INTO user_role_assignments (user_id, role_id, assigned_at) VALUES ('cosmo_1', 'cosmonaut', ?)", (current_iso_timestamp(),))
        c.execute("INSERT OR REPLACE INTO user_band_memberships (user_id, band_code, track_code, assigned_at) VALUES ('cosmo_1', 'B1', 'SD', ?)", (current_iso_timestamp(),))

        # Seed admin guardian account
        c.execute(
            """
            INSERT OR REPLACE INTO users (
                id, username, email, name, age, role, learning_track, track_code, band,
                password, primary_role, avatar, status, is_demo, created_at
            )
            VALUES ('admin', 'admin', 'admin@starapp.io', 'Guardian Admin', 40, 'Guardian Administrator', 'Curriculum Authority', 'EXEC', 'B6',
                    '12345678', 'guardian', 'GA', 'active', 1, ?)
            """,
            (current_iso_timestamp(),)
        )
        c.execute("INSERT OR IGNORE INTO user_role_assignments (user_id, role_id, assigned_at) VALUES ('admin', 'guardian', ?)", (current_iso_timestamp(),))
        c.execute("INSERT OR IGNORE INTO user_role_assignments (user_id, role_id, assigned_at) VALUES ('admin', 'badge_reviewer', ?)", (current_iso_timestamp(),))
        c.execute("INSERT OR REPLACE INTO user_band_memberships (user_id, band_code, track_code, assigned_at) VALUES ('admin', 'B6', 'EXEC', ?)", (current_iso_timestamp(),))

        # 7. Seed 2 Initial B1 Badges for Band B1 Card & Review Workflow
        b1_badges_seed = [
            (
                "b1_int_01",
                "B1-INT-01",
                "Intelligent Apps Foundations",
                "Intelligent Apps / Intelligent Apps",
                "Foundations of intelligent agents, LLM integrations, and modern full-stack reasoning workflows.",
                json.dumps([
                    "Understand agent architectures and prompt formatting",
                    "Connect LLM reasoning APIs to enterprise pipelines",
                    "Implement secure tool use and stateful conversations"
                ]),
                json.dumps(["Agent Architecture", "API Integration", "Tool Calling", "Context Windows", "Output Parsing", "Streaming APIs"]),
                "Build a production agent pipeline that queries live enterprise databases with structured validation.",
                0, 0, "B1", "Tech", "Intelligent Apps", "Intelligent Apps",
                json.dumps({
                    "id": "b1_int_01",
                    "code": "B1-INT-01",
                    "title": "Intelligent Apps Foundations",
                    "target_band": "B1",
                    "power": "Tech",
                    "capability": "Intelligent Apps",
                    "skill": "Intelligent Apps",
                    "description": "Foundations of intelligent agents, LLM integrations, and modern full-stack reasoning workflows.",
                    "location": "Intelligent Apps Foundations -> Intelligent Apps -> Intelligent Apps -> Tech -> Band B1",
                    "outcomes": [
                        "Can understand agent architectures and prompt formatting",
                        "Can connect LLM reasoning APIs to enterprise pipelines",
                        "Can implement secure tool use and stateful conversations"
                    ],
                    "learning_topics": [
                        {"index": 0, "title": "Agent Architecture", "description": "Core concepts of agents, planners, and memory buffers."},
                        {"index": 1, "title": "API Integration", "description": "Authenticating, rate-limiting, and error handling for reasoning APIs."},
                        {"index": 2, "title": "Tool Calling", "description": "Declaring schemas and invoking functions safely."},
                        {"index": 3, "title": "Context Windows", "description": "Managing prompt limits, token consumption, and KV cache."},
                        {"index": 4, "title": "Output Parsing", "description": "Structured output parsing and validation."},
                        {"index": 5, "title": "Streaming APIs", "description": "SSE and WebSocket chunk rendering."}
                    ],
                    "practice_project": {
                        "title": "Production Agent Pipeline",
                        "prompt": "Build a production agent pipeline that queries live enterprise databases with structured validation."
                    }
                }),
                "ready_for_review",
                "guardian_1",
                "m_b2_1",
                json.dumps(["cosmo_1", "m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5"]),
                json.dumps({}),
                current_iso_timestamp(),
                current_iso_timestamp()
            ),
            (
                "b1_dat_01",
                "B1-DAT-01",
                "Data Systems Architecture",
                "Data & Machine / Data Model",
                "Core concepts of high-scale data partitioning, cache topologies, and database durability.",
                json.dumps([
                    "Design normalized 3NF and dimensional schemas",
                    "Optimize distributed queries and indexing strategies",
                    "Implement failover policies and WAL logging"
                ]),
                json.dumps(["Schema Design", "Distributed Caching", "Failover Topologies", "WAL Logging", "ACID Guarantees", "Partitioning"]),
                "Design and evaluate a fault-tolerant relational cluster architecture with high-availability replication.",
                0, 0, "B1", "Tech", "Data & Machine", "Data Model",
                json.dumps({
                    "id": "b1_dat_01",
                    "code": "B1-DAT-01",
                    "title": "Data Systems Architecture",
                    "target_band": "B1",
                    "power": "Tech",
                    "capability": "Data & Machine",
                    "skill": "Data Model",
                    "description": "Core concepts of high-scale data partitioning, cache topologies, and database durability.",
                    "location": "Data Systems Architecture -> Data Model -> Data & Machine -> Tech -> Band B1",
                    "outcomes": [
                        "Can design normalized 3NF and dimensional schemas",
                        "Can optimize distributed queries and indexing strategies",
                        "Can implement failover policies and WAL logging"
                    ],
                    "learning_topics": [
                        {"index": 0, "title": "Schema Design", "description": "3NF normalization and dimensional models."},
                        {"index": 1, "title": "Distributed Caching", "description": "Redis and Memcached caching strategies."},
                        {"index": 2, "title": "Failover Topologies", "description": "Master-replica consensus and quorum."},
                        {"index": 3, "title": "WAL Logging", "description": "Write-ahead logging and point-in-time recovery."},
                        {"index": 4, "title": "ACID Guarantees", "description": "Transaction isolation levels and MVCC."},
                        {"index": 5, "title": "Partitioning", "description": "Horizontal sharding and range partitioning."}
                    ],
                    "practice_project": {
                        "title": "Fault-Tolerant Cluster Architecture",
                        "prompt": "Design and evaluate a fault-tolerant relational cluster architecture with high-availability replication."
                    }
                }),
                "ready_for_review",
                "guardian_1",
                "m_b2_1",
                json.dumps(["cosmo_1", "m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5"]),
                json.dumps({}),
                current_iso_timestamp(),
                current_iso_timestamp()
            )
        ]
        for b_item in b1_badges_seed:
            c.execute(
                """
                INSERT OR IGNORE INTO badges (
                    id, code, title, category, description,
                    learning_outcomes_json, learning_topics_json, project_requirements,
                    is_published, is_allocated, target_band, power, capability, skill,
                    prompt_json, workflow_status, creator_id, assigned_reviewer_id,
                    assigned_cosmonaut_ids_json, default_timeline_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                b_item
            )
            b_id = b_item[0]
            c.execute("INSERT OR REPLACE INTO badge_powers (badge_id, power_name) VALUES (?, ?)", (b_id, b_item[11]))
            c.execute("INSERT OR REPLACE INTO badge_capabilities (badge_id, capability_name, is_custom) VALUES (?, ?, 0)", (b_id, b_item[12]))
            c.execute("INSERT OR REPLACE INTO badge_skills (badge_id, skill_name, is_custom) VALUES (?, ?, 0)", (b_id, b_item[13]))

        self.conn.commit()

    # ==========================================================================
    # FILE PERSISTENCE & BINARY EXPORT / IMPORT
    # ==========================================================================

    def export_bytes(self) -> bytes:
        """Flushes transactions and reads raw SQLite database binary bytes."""
        if not SQLITE_AVAILABLE or self.conn is None:
            return b""
        self.conn.commit()
        if os.path.exists(self.db_path):
            with open(self.db_path, "rb") as f:
                return f.read()
        elif self.db_path == ":memory:":
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_name = tmp.name
            try:
                dest = sqlite3.connect(tmp_name)
                self.conn.backup(dest)
                dest.close()
                with open(tmp_name, "rb") as f:
                    data = f.read()
                return data
            finally:
                if os.path.exists(tmp_name):
                    try:
                        os.remove(tmp_name)
                    except Exception:
                        pass
        return b""

    def export_base64(self) -> str:
        """Returns base64 encoded string of SQLite database file for IndexedDB storage."""
        data = self.export_bytes()
        return base64.b64encode(data).decode("ascii")

    def import_bytes(self, data: bytes):
        """Restores SQLite database from raw binary bytes."""
        if not SQLITE_AVAILABLE or not data:
            return
        if self.db_path == ":memory:":
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(data)
                tmp_name = tmp.name
            try:
                src = sqlite3.connect(tmp_name)
                if self._conn is not None:
                    self._conn.close()
                    self._conn = None
                self.connect()
                src.backup(self.conn)
                src.close()
            finally:
                if os.path.exists(tmp_name):
                    try:
                        os.remove(tmp_name)
                    except Exception:
                        pass
            return
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        with open(self.db_path, "wb") as f:
            f.write(data)
        self.connect()

    def import_base64(self, b64_str: str):
        """Restores SQLite database from base64 string (retrieved from IndexedDB)."""
        if not b64_str or not b64_str.strip():
            return
        raw = base64.b64decode(b64_str.strip())
        self.import_bytes(raw)

    # ==========================================================================
    # DATA MIGRATION & DICTIONARY EXPORT
    # ==========================================================================

    def migrate_from_dict(self, data: Dict[str, Any]):
        """
        Idempotently migrates full StarApp domain dataset into SQLite.
        Preserves all users, profiles, badges, timelines, submissions,
        assessments, materials, extensions, announcements, activities, and mappings.
        """
        if not SQLITE_AVAILABLE or self.conn is None:
            return
        self.create_tables()
        self.seed_system_metadata()

        c = self.conn
        with c:
            # 1. Users
            for u in data.get("users", []):
                u_id = u["id"]
                u_uname = u.get("username", "")
                u_email = u["email"]
                u_role = u.get("role", "cosmonaut")
                u_name = u["name"]
                u_avatar = u.get("avatar", "")
                if u_id == "guardian_1":
                    u_name = "Arjun Mehta"
                    u_role_title = "Chief Executive Officer"
                    u_track = "Executive Leadership"
                    u_track_code = "EXEC"
                    u_band = "CEO"
                    u_email = "arjun.mehta@starapp.io"
                    u_age = 55
                    u_avatar = "AM"
                    u_pwd = "12345678"
                    u_role = "guardian"
                    u_mgr_id = None
                    u_mgr_name = None
                    u_mgr_band = None
                else:
                    u_age = u.get("age", 30)
                    u_role_title = u.get("role_title", u.get("role", "Solutions Designer"))
                    u_track = u.get("learning_track", "Solutions Designer")
                    u_track_code = u.get("track_code", "SD")
                    u_band = u.get("band", "B1")
                    u_mgr_id = u.get("reporting_manager_id")
                    u_mgr_name = u.get("reporting_manager_name")
                    u_mgr_band = u.get("reporting_manager_band")
                    u_pwd = u.get("password", "12345678")

                c.execute(
                    """
                    INSERT INTO users (
                        id, username, email, name, age, role, learning_track, track_code, band,
                        reporting_manager_id, reporting_manager_name, reporting_manager_band,
                        password, primary_role, avatar, status, is_demo, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        username=excluded.username,
                        email=excluded.email,
                        name=excluded.name,
                        age=excluded.age,
                        role=excluded.role,
                        learning_track=excluded.learning_track,
                        track_code=excluded.track_code,
                        band=excluded.band,
                        reporting_manager_id=excluded.reporting_manager_id,
                        reporting_manager_name=excluded.reporting_manager_name,
                        reporting_manager_band=excluded.reporting_manager_band,
                        password=excluded.password,
                        primary_role=excluded.primary_role,
                        avatar=excluded.avatar,
                        status=excluded.status
                    """,
                    (
                        u_id, u_uname, u_email, u_name, u_age, u_role_title, u_track, u_track_code, u_band,
                        u_mgr_id, u_mgr_name, u_mgr_band, u_pwd, u_role, u_avatar, current_iso_timestamp()
                    )
                )
                c.execute(
                    "INSERT OR IGNORE INTO user_role_assignments (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                    (u_id, u_role, current_iso_timestamp())
                )
                if u_role == "guardian":
                    c.execute(
                        "INSERT OR IGNORE INTO user_role_assignments (user_id, role_id, assigned_at) VALUES (?, 'project_reviewer', ?)",
                        (u_id, current_iso_timestamp())
                    )

            # 2. Cosmonaut Profiles
            for p in data.get("profiles", []):
                c.execute(
                    """
                    INSERT OR REPLACE INTO cosmonaut_profiles (user_id, batch_name, assigned_guardian_id, guardian_credentials, skills_json, certifications_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        p["user_id"],
                        p.get("batch_name", "Orion-24"),
                        p.get("assigned_guardian_id", "guardian_1"),
                        p.get("guardian_credentials", ""),
                        json.dumps(p.get("skills", [])),
                        json.dumps(p.get("certifications", []))
                    )
                )

            # 3. Badges
            for b in data.get("badges", []):
                b_id = b["id"]
                c.execute(
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
                        b_id,
                        b.get("code", ""),
                        b["title"],
                        b.get("category", "Foundations"),
                        b.get("description", ""),
                        json.dumps(b.get("learning_outcomes", [])),
                        json.dumps(b.get("learning_topics", [])),
                        b.get("project_requirements", ""),
                        1 if b.get("is_published", True) else 0,
                        1 if b.get("is_allocated", True) else 0,
                        b.get("target_band") or None,
                        b.get("power") or None,
                        b.get("capability") or None,
                        b.get("skill") or None,
                        b.get("prompt_json") or None,
                        b.get("workflow_status", "approved"),
                        b.get("creator_id") or "guardian_1",
                        b.get("assigned_reviewer_id") or None,
                        json.dumps(b.get("assigned_cosmonaut_ids", [])),
                        json.dumps(b.get("default_timeline", {})),
                        b.get("created_at", current_iso_timestamp()),
                        b.get("updated_at", current_iso_timestamp()),
                        float(b.get("passing_percentage", 70.0)),
                        b.get("published_at", ""),
                        b.get("published_by", "")
                    )
                )

                # Normalized badge power, capability, skill
                if b.get("power"):
                    c.execute("INSERT OR REPLACE INTO badge_powers (badge_id, power_name) VALUES (?, ?)", (b_id, b["power"]))
                if b.get("capability"):
                    c.execute("INSERT OR REPLACE INTO badge_capabilities (badge_id, capability_name, is_custom) VALUES (?, ?, 0)", (b_id, b["capability"]))
                if b.get("skill"):
                    c.execute("INSERT OR REPLACE INTO badge_skills (badge_id, skill_name, is_custom) VALUES (?, ?, 0)", (b_id, b["skill"]))

                # Prerequisites
                for prereq in b.get("prerequisites", []):
                    c.execute(
                        "INSERT OR IGNORE INTO badge_prerequisites (badge_id, prerequisite_badge_id) VALUES (?, ?)",
                        (b_id, prereq)
                    )

            # 4. Timelines
            for t in data.get("timelines", []):
                c.execute(
                    """
                    INSERT OR REPLACE INTO badge_timelines (
                        badge_id, cosmonaut_id, assignment_date, publication_date,
                        learning_start_date, learning_end_date, project_start_date, project_end_date,
                        submission_deadline, review_date, expected_award_date, actual_award_date, status,
                        reviewer_id, review_window_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        t["badge_id"],
                        t["cosmonaut_id"],
                        t.get("assignment_date", ""),
                        t.get("publication_date", ""),
                        t.get("learning_start_date", ""),
                        t.get("learning_end_date", ""),
                        t.get("project_start_date", ""),
                        t.get("project_end_date", ""),
                        t.get("submission_deadline", ""),
                        t.get("review_date", ""),
                        t.get("expected_award_date", ""),
                        t.get("actual_award_date", ""),
                        t.get("status", "active"),
                        t.get("reviewer_id", ""),
                        t.get("review_window_json", "[]")
                    )
                )

            # 5. Submissions
            for s in data.get("submissions", []):
                c.execute(
                    """
                    INSERT OR REPLACE INTO project_submissions (
                        id, badge_id, cosmonaut_id, attempt_number, submission_type,
                        payload, file_name, submitted_at, status, pdf_name, pdf_payload,
                        code_name, code_payload, github_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s["id"],
                        s["badge_id"],
                        s["cosmonaut_id"],
                        s.get("attempt_number", 1),
                        s.get("submission_type", "pdf"),
                        s.get("payload", ""),
                        s.get("file_name", ""),
                        s.get("submitted_at", current_iso_timestamp()),
                        s.get("status", "pending"),
                        s.get("pdf_name", ""),
                        s.get("pdf_payload", ""),
                        s.get("code_name", ""),
                        s.get("code_payload", ""),
                        s.get("github_url", "")
                    )
                )

            # 6. Assessments
            for a in data.get("assessments", []):
                c.execute(
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
                        a["id"],
                        a["submission_id"],
                        a.get("attempt_number", 1),
                        a["badge_id"],
                        a["cosmonaut_id"],
                        a.get("reviewer_id", "guardian_1"),
                        a.get("reviewer_name", "Arjun Mehta"),
                        a.get("reviewed_at", current_iso_timestamp()),
                        a.get("decision", "approve"),
                        float(a.get("business_understanding", 0.0)),
                        float(a.get("architecture_report", 0.0)),
                        float(a.get("technical_knowledge", 0.0)),
                        float(a.get("presentation", 0.0)),
                        float(a.get("qa", 0.0)),
                        float(a.get("total_marks", 0.0)),
                        float(a.get("percentage", 0.0)),
                        a.get("strength_areas", ""),
                        a.get("improvement_areas", ""),
                        a.get("overall_feedback", ""),
                        a.get("assessor_role", "guardian"),
                        a.get("remarks", "")
                    )
                )

            # 7. Materials
            for m in data.get("materials", []):
                c.execute(
                    """
                    INSERT OR REPLACE INTO learning_materials (
                        id, badge_id, topic, title, description, material_type, url_or_data, upload_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        m["id"],
                        m["badge_id"],
                        m.get("topic", "General"),
                        m["title"],
                        m.get("description", ""),
                        m.get("material_type", "doc"),
                        m.get("url_or_data", ""),
                        m.get("upload_date", current_iso_timestamp())
                    )
                )

            # 8. Extensions
            for e in data.get("extensions", []):
                c.execute(
                    """
                    INSERT OR REPLACE INTO deadline_extensions (
                        id, badge_id, cosmonaut_id, current_deadline, proposed_deadline,
                        reason, status, guardian_response, requested_at, decided_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        e["id"],
                        e["badge_id"],
                        e["cosmonaut_id"],
                        e.get("current_deadline", ""),
                        e.get("proposed_deadline", ""),
                        e.get("reason", ""),
                        e.get("status", "pending"),
                        e.get("guardian_response", ""),
                        e.get("requested_at", current_iso_timestamp()),
                        e.get("decided_at", "")
                    )
                )

            # 9. Announcements
            for ann in data.get("announcements", []):
                ann_id = ann["id"]
                c.execute(
                    """
                    INSERT OR REPLACE INTO announcements (
                        id, title, message, author_id, author_name, target_type, badge_id, published_at, expiry_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ann_id,
                        ann["title"],
                        ann["message"],
                        ann.get("author_id", "guardian_1"),
                        ann.get("author_name", "Arjun Mehta"),
                        ann.get("target_type", "all"),
                        ann.get("badge_id", ""),
                        ann.get("published_at", current_iso_timestamp()),
                        ann.get("expiry_date", "")
                    )
                )
                for recipient_id in ann.get("target_cosmonaut_ids", []):
                    c.execute(
                        "INSERT OR IGNORE INTO announcement_recipients (announcement_id, cosmonaut_id) VALUES (?, ?)",
                        (ann_id, recipient_id)
                    )
                for reader_id in ann.get("read_by_cosmonaut_ids", []):
                    c.execute(
                        "INSERT OR IGNORE INTO announcement_read_receipts (announcement_id, cosmonaut_id, read_at) VALUES (?, ?, ?)",
                        (ann_id, reader_id, current_iso_timestamp())
                    )

            # 10. Notifications
            for n in data.get("notifications", []):
                c.execute(
                    """
                    INSERT OR REPLACE INTO notifications (
                        id, recipient_id, title, message, link_section, created_at, is_read, event_type, related_badge_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        n["id"],
                        n["recipient_id"],
                        n["title"],
                        n["message"],
                        n.get("link_section", ""),
                        n.get("created_at", current_iso_timestamp()),
                        1 if n.get("is_read", False) else 0,
                        n.get("event_type", ""),
                        n.get("related_badge_id", "")
                    )
                )

            # 11. Activity Events
            for act in data.get("activities", []):
                c.execute(
                    """
                    INSERT OR REPLACE INTO activity_events (
                        id, timestamp, event_type, actor_id, actor_name, cosmonaut_id, badge_id, summary, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        act["id"],
                        act.get("timestamp", current_iso_timestamp()),
                        act.get("event_type", "general"),
                        act.get("actor_id", "guardian_1"),
                        act.get("actor_name", "Arjun Mehta"),
                        act.get("cosmonaut_id", ""),
                        act.get("badge_id", ""),
                        act.get("summary", ""),
                        act.get("details", "")
                    )
                )

            # 12. Band Mappings
            for bm in data.get("band_mappings", []):
                bm_id = bm.get("id") or f"map_{bm.get('band','B1')}_{bm.get('badge_id','')}"
                c.execute(
                    "INSERT OR REPLACE INTO band_mappings (id, band, badge_id, data_json) VALUES (?, ?, ?, ?)",
                    (bm_id, bm.get("band", "B1"), bm.get("badge_id", ""), json.dumps(bm))
                )

            # 13. Mapping Requests
            for mr in data.get("mapping_requests", []):
                mr_id = mr.get("id")
                if mr_id:
                    c.execute(
                        "INSERT OR REPLACE INTO mapping_requests (id, band, reviewer_id, status, data_json) VALUES (?, ?, ?, ?, ?)",
                        (mr_id, mr.get("band", ""), mr.get("reviewer_id", ""), mr.get("status", "pending"), json.dumps(mr))
                    )

            # 14. Reviewer Project Prompts
            rpp_list = data.get("reviewer_projects") or data.get("reviewer_project_prompts") or []
            for rp in rpp_list:
                rp_id = rp.get("id") or f"proj_{rp.get('badge_id')}_{rp.get('reviewer_id')}"
                c_ids_json = json.dumps(rp.get("cosmonaut_ids", [])) if isinstance(rp.get("cosmonaut_ids"), list) else (rp.get("cosmonaut_ids_json") or "[]")
                deliv_json = json.dumps(rp.get("deliverables", {})) if isinstance(rp.get("deliverables"), (dict, list)) else (rp.get("deliverables_json") or "{}")
                req_text = json.dumps(rp.get("requirements", [])) if isinstance(rp.get("requirements"), list) else (rp.get("requirements_text") or str(rp.get("requirements") or ""))
                c.execute(
                    """INSERT OR REPLACE INTO reviewer_project_prompts (
                        id, badge_id, reviewer_id, cosmonaut_ids_json, title, description,
                        deliverables_json, requirements_text, status, created_at, sent_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        rp_id,
                        rp.get("badge_id"),
                        rp.get("reviewer_id"),
                        c_ids_json,
                        rp.get("title", ""),
                        rp.get("description", ""),
                        deliv_json,
                        req_text,
                        rp.get("status", "sent"),
                        rp.get("created_at") or datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        rp.get("sent_at")
                    )
                )

    migrate_from_dict = migrate_from_dict

    def import_from_dict(self, data: Dict[str, Any]):
        return self.migrate_from_dict(data)

    def export_to_dict(self) -> Dict[str, Any]:
        """
        Extracts structured relational records from SQLite into a clean JSON-serializable dictionary.
        Enables 100% backward compatibility with DataStore and views.
        """
        if not SQLITE_AVAILABLE or self.conn is None:
            return {}
        c = self.conn

        # Users: all active users directly from SQLite
        users_rows = c.execute("SELECT * FROM users ORDER BY id").fetchall()
        users = []
        for r in users_rows:
            # Fetch assigned roles
            roles = [row[0] for row in c.execute("SELECT role_id FROM user_role_assignments WHERE user_id = ?", (r["id"],)).fetchall()]
            users.append({
                "id": r["id"],
                "username": r["username"],
                "email": r["email"],
                "role": r["primary_role"],
                "roles": roles,
                "name": r["name"],
                "avatar": r["avatar"]
            })

        # Profiles
        profiles_rows = c.execute("SELECT * FROM cosmonaut_profiles").fetchall()
        profiles = []
        for r in profiles_rows:
            profiles.append({
                "user_id": r["user_id"],
                "batch_name": r["batch_name"],
                "assigned_guardian_id": r["assigned_guardian_id"],
                "guardian_credentials": r["guardian_credentials"],
                "skills": json.loads(r["skills_json"]),
                "certifications": json.loads(r["certifications_json"])
            })

        # Badges & Prerequisites
        badges_rows = c.execute("SELECT * FROM badges ORDER BY id").fetchall()
        badges = []
        for r in badges_rows:
            prereqs = [row[0] for row in c.execute("SELECT prerequisite_badge_id FROM badge_prerequisites WHERE badge_id = ?", (r["id"],)).fetchall()]
            badges.append({
                "id": r["id"],
                "code": r["code"],
                "title": r["title"],
                "category": r["category"],
                "description": r["description"],
                "learning_outcomes": json.loads(r["learning_outcomes_json"]),
                "learning_topics": json.loads(r["learning_topics_json"]),
                "prerequisites": prereqs,
                "project_requirements": r["project_requirements"],
                "is_published": bool(r["is_published"]),
                "is_allocated": bool(r["is_allocated"]),
                "target_band": r["target_band"],
                "power": r["power"],
                "capability": r["capability"],
                "skill": r["skill"],
                "prompt_json": r["prompt_json"],
                "workflow_status": r["workflow_status"],
                "creator_id": r["creator_id"],
                "assigned_reviewer_id": r["assigned_reviewer_id"],
                "assigned_cosmonaut_ids": json.loads(r["assigned_cosmonaut_ids_json"]),
                "default_timeline": json.loads(r["default_timeline_json"]),
                "passing_percentage": float(r["passing_percentage"]) if "passing_percentage" in r.keys() and r["passing_percentage"] is not None else 70.0,
                "published_at": r["published_at"] if "published_at" in r.keys() and r["published_at"] else "",
                "published_by": r["published_by"] if "published_by" in r.keys() and r["published_by"] else ""
            })

        # Timelines
        timelines_rows = c.execute("SELECT * FROM badge_timelines").fetchall()
        timelines = [dict(r) for r in timelines_rows]

        # Submissions
        subs_rows = c.execute("SELECT * FROM project_submissions ORDER BY submitted_at DESC").fetchall()
        submissions = [dict(r) for r in subs_rows]

        # Assessments
        asms_rows = c.execute("SELECT * FROM assessment_marksheets ORDER BY reviewed_at DESC").fetchall()
        assessments = [dict(r) for r in asms_rows]

        # Materials
        mats_rows = c.execute("SELECT * FROM learning_materials ORDER BY upload_date DESC").fetchall()
        materials = [dict(r) for r in mats_rows]

        # Extensions
        exts_rows = c.execute("SELECT * FROM deadline_extensions ORDER BY requested_at DESC").fetchall()
        extensions = [dict(r) for r in exts_rows]

        # Announcements & Read receipts
        anns_rows = c.execute("SELECT * FROM announcements ORDER BY published_at DESC").fetchall()
        announcements = []
        for r in anns_rows:
            recips = [row[0] for row in c.execute("SELECT cosmonaut_id FROM announcement_recipients WHERE announcement_id = ?", (r["id"],)).fetchall()]
            reads = [row[0] for row in c.execute("SELECT cosmonaut_id FROM announcement_read_receipts WHERE announcement_id = ?", (r["id"],)).fetchall()]
            announcements.append({
                "id": r["id"],
                "title": r["title"],
                "message": r["message"],
                "author_id": r["author_id"],
                "author_name": r["author_name"],
                "target_type": r["target_type"],
                "target_cosmonaut_ids": recips,
                "badge_id": r["badge_id"],
                "published_at": r["published_at"],
                "expiry_date": r["expiry_date"],
                "read_by_cosmonaut_ids": reads
            })

        # Activities
        act_rows = c.execute("SELECT * FROM activity_events ORDER BY timestamp DESC").fetchall()
        activities = [dict(r) for r in act_rows]

        # Notifications
        notif_rows = c.execute("SELECT * FROM notifications ORDER BY created_at DESC").fetchall()
        notifications = []
        for r in notif_rows:
            d = dict(r)
            d["is_read"] = bool(d["is_read"])
            notifications.append(d)

        # Band Mappings
        bm_rows = c.execute("SELECT data_json FROM band_mappings").fetchall()
        band_mappings = [json.loads(r[0]) for r in bm_rows]

        # Mapping Requests
        mr_rows = c.execute("SELECT data_json FROM mapping_requests").fetchall()
        mapping_requests = [json.loads(r[0]) for r in mr_rows]

        # Reviewer Project Prompts
        reviewer_projects = []
        try:
            rpp_rows = c.execute("SELECT * FROM reviewer_project_prompts ORDER BY created_at DESC").fetchall()
            for r in rpp_rows:
                req_text = r["requirements_text"] or ""
                req_list = json.loads(req_text) if req_text.startswith("[") else [x.strip() for x in req_text.split("\n") if x.strip()]
                reviewer_projects.append({
                    "id": r["id"],
                    "badge_id": r["badge_id"],
                    "reviewer_id": r["reviewer_id"],
                    "cosmonaut_ids": json.loads(r["cosmonaut_ids_json"]) if r["cosmonaut_ids_json"] else [],
                    "title": r["title"],
                    "description": r["description"],
                    "deliverables": json.loads(r["deliverables_json"]) if r["deliverables_json"] else {},
                    "requirements": req_list,
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "sent_at": r["sent_at"]
                })
        except Exception:
            pass

        return {
            "schema_version": SCHEMA_VERSION,
            "users": users,
            "profiles": profiles,
            "badges": badges,
            "timelines": timelines,
            "submissions": submissions,
            "assessments": assessments,
            "materials": materials,
            "extensions": extensions,
            "announcements": announcements,
            "activities": activities,
            "notifications": notifications,
            "band_mappings": band_mappings,
            "mapping_requests": mapping_requests,
            "reviewer_projects": reviewer_projects,
            "reviewer_project_prompts": reviewer_projects
        }

    # ==========================================================================
    # BAND-SPECIFIC SCOPED MEMBERS & DATA QUERIES
    # ==========================================================================

    def get_members_by_band(self, band: str) -> List[Dict[str, Any]]:
        if SQLITE_AVAILABLE and self.conn is not None:
            try:
                rows = self.conn.execute(
                    """
                    SELECT id, username, email, name, age, role, learning_track, track_code, band,
                           reporting_manager_id, reporting_manager_name, reporting_manager_band,
                           password, primary_role, avatar, status
                    FROM users
                    WHERE band = ? AND id != 'cosmo_1'
                    ORDER BY id
                    """,
                    (band,)
                ).fetchall()
                if rows:
                    res = []
                    for r in rows:
                        d = dict(r)
                        d["application_roles"] = [d["primary_role"]]
                        res.append(d)
                    return res
            except Exception:
                pass
        from starapp.mapping_data import DUMMY_MEMBERS
        return [m for m in DUMMY_MEMBERS if m.get("band") == band]

    def get_direct_reports(self, manager_id: str) -> List[Dict[str, Any]]:
        """Retrieves direct reports managed by the given manager ID."""
        if SQLITE_AVAILABLE and self.conn is not None:
            try:
                rows = self.conn.execute(
                    """
                    SELECT id, username, email, name, age, role, learning_track, track_code, band,
                           reporting_manager_id, reporting_manager_name, reporting_manager_band,
                           password, primary_role, avatar, status
                    FROM users
                    WHERE reporting_manager_id = ? AND id != 'cosmo_1'
                    ORDER BY band, id
                    """,
                    (manager_id,)
                ).fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass
        from starapp.mapping_data import DUMMY_MEMBERS
        return [m for m in DUMMY_MEMBERS if m.get("reporting_manager_id") == manager_id]

    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Retrieves all 36 corporate employees with complete attributes and reporting links."""
        if SQLITE_AVAILABLE and self.conn is not None:
            try:
                rows = self.conn.execute(
                    """
                    SELECT id, username, email, name, age, role, learning_track, track_code, band,
                           reporting_manager_id, reporting_manager_name, reporting_manager_band,
                           password, primary_role, avatar, status
                    FROM users
                    WHERE id != 'cosmo_1'
                    ORDER BY CASE band
                        WHEN 'B1' THEN 1
                        WHEN 'B2' THEN 2
                        WHEN 'B3' THEN 3
                        WHEN 'B4' THEN 4
                        WHEN 'B5' THEN 5
                        WHEN 'B6' THEN 6
                        WHEN 'CEO' THEN 7
                        ELSE 8 END, id
                    """
                ).fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass
        from starapp.mapping_data import DUMMY_MEMBERS
        return list(DUMMY_MEMBERS)

    # ==========================================================================
    # CUSTOM CAPABILITIES & SKILLS QUERIES
    # ==========================================================================

    def get_custom_capabilities(self) -> List[str]:
        if not SQLITE_AVAILABLE or self.conn is None:
            return []
        rows = self.conn.execute("SELECT name FROM custom_capabilities ORDER BY name COLLATE NOCASE").fetchall()
        return [r[0] for r in rows]

    def add_custom_capability(self, name: str, user_id: str = "guardian_1") -> Tuple[bool, str]:
        name_clean = name.strip()
        if not name_clean:
            return False, "Capability name cannot be empty."
        if not SQLITE_AVAILABLE or self.conn is None:
            return True, name_clean
        existing = self.conn.execute("SELECT id FROM custom_capabilities WHERE lower(name) = lower(?)", (name_clean,)).fetchone()
        if existing:
            return False, f"Capability '{name_clean}' already exists."
        c_id = f"cap_custom_{int(datetime.datetime.now().timestamp() * 1000)}"
        self.conn.execute(
            "INSERT INTO custom_capabilities (id, name, created_by, created_at) VALUES (?, ?, ?, ?)",
            (c_id, name_clean, user_id, current_iso_timestamp())
        )
        self.conn.commit()
        return True, name_clean

    def get_custom_skills(self, capability_name: Optional[str] = None) -> List[str]:
        if not SQLITE_AVAILABLE or self.conn is None:
            return []
        if capability_name:
            cap_clean = capability_name.strip()
            rows = self.conn.execute(
                "SELECT name FROM custom_skills WHERE lower(capability_name) = lower(?) OR capability_name = '' ORDER BY name COLLATE NOCASE",
                (cap_clean,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT name FROM custom_skills ORDER BY name COLLATE NOCASE").fetchall()
        return [r[0] for r in rows]

    def add_custom_skill(self, name: str, user_id_or_cap: str = "guardian_1", capability_name: str = "", user_id: str = "guardian_1", created_by: Optional[str] = None) -> Tuple[bool, str]:
        name_clean = name.strip()
        if not name_clean:
            return False, "Skill name cannot be empty."

        target_cap = capability_name
        target_user = user_id
        if created_by:
            target_user = created_by

        if user_id_or_cap and user_id_or_cap != "guardian_1":
            if user_id_or_cap.startswith("guardian_") or user_id_or_cap.startswith("cosmonaut_") or user_id_or_cap.startswith("user_") or user_id_or_cap.startswith("m_"):
                target_user = user_id_or_cap
            else:
                if not target_cap:
                    target_cap = user_id_or_cap

        if not SQLITE_AVAILABLE or self.conn is None:
            return True, name_clean

        if target_cap:
            existing = self.conn.execute(
                "SELECT id FROM custom_skills WHERE lower(name) = lower(?) AND (lower(capability_name) = lower(?) OR capability_name = '')",
                (name_clean, target_cap)
            ).fetchone()
        else:
            existing = self.conn.execute(
                "SELECT id FROM custom_skills WHERE lower(name) = lower(?)",
                (name_clean,)
            ).fetchone()

        if existing:
            return False, f"Skill '{name_clean}' already exists."

        s_id = f"skill_custom_{int(datetime.datetime.now().timestamp() * 1000)}"
        self.conn.execute(
            "INSERT INTO custom_skills (id, name, capability_name, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (s_id, name_clean, target_cap, target_user, current_iso_timestamp())
        )
        self.conn.commit()
        return True, name_clean

    # ==========================================================================
    # REVIEWER ELIGIBILITY QUERIES
    # ==========================================================================

    def get_eligible_badge_reviewers(self, target_band: str) -> List[Dict[str, Any]]:
        """
        Retrieves active reviewers belonging to HIGHER bands than target_band
        who possess the 'badge_reviewer' role.
        B1 -> B2, B3, B4, B5, B6
        B2 -> B3, B4, B5, B6
        B3 -> B4, B5, B6
        B4 -> B5, B6
        B5 -> B6
        B6 -> [] (no higher band)
        """
        from starapp.mapping_data import get_higher_bands
        higher_bands = get_higher_bands(target_band)
        # If target_band is B6, higher_bands returns ['B6'] in mapping_data for peer review,
        # but for badge creation approval Part 5.2 explicitly requires:
        # B6 -> No eligible higher-band reviewer!
        if target_band == "B6":
            return []

        if not SQLITE_AVAILABLE or self.conn is None:
            from starapp.mapping_data import DUMMY_MEMBERS
            res = []
            for b in higher_bands:
                for m in DUMMY_MEMBERS.get(b, []):
                    if "badge_reviewer" in m.get("roles", []):
                        res.append({
                            "id": m["id"],
                            "name": m["name"],
                            "email": f"{m['id']}@starapp.io",
                            "avatar": "",
                            "username": m["id"],
                            "band": b,
                            "band_code": b,
                            "track_code": m.get("learning_track", "SE"),
                            "learning_track": m.get("learning_track", "Systems Engineer")
                        })
            return res

        placeholders = ",".join("?" for _ in higher_bands)
        query = f"""
        SELECT u.id, u.name, u.email, u.avatar, u.username, m.band_code, m.track_code, t.name AS track_name
        FROM users u
        JOIN user_role_assignments ra ON u.id = ra.user_id AND ra.role_id = 'badge_reviewer'
        JOIN user_band_memberships m ON u.id = m.user_id
        JOIN learning_tracks t ON m.track_code = t.code
        WHERE m.band_code IN ({placeholders}) AND u.status = 'active'
        ORDER BY m.band_code, u.name
        """
        rows = self.conn.execute(query, higher_bands).fetchall()
        res = []
        for r in rows:
            d = dict(r)
            d["band"] = d.get("band_code", "")
            d["learning_track"] = d.get("track_name", "")
            res.append(d)
        return res

    def verify_reviewer_eligibility(self, reviewer_id: str, target_band: str) -> Tuple[bool, str]:
        """Strict verification of reviewer eligibility for badge authorization."""
        if target_band == "B6":
            return False, "B6 is the highest band; no higher-band reviewer exists to authorize B6 badges."

        if not SQLITE_AVAILABLE or self.conn is None:
            return True, "Eligible"

        from starapp.mapping_data import get_higher_bands
        higher_bands = get_higher_bands(target_band)

        row = self.conn.execute(
            """
            SELECT u.id, u.name, m.band_code, ra.role_id
            FROM users u
            JOIN user_role_assignments ra ON u.id = ra.user_id AND ra.role_id = 'badge_reviewer'
            JOIN user_band_memberships m ON u.id = m.user_id
            WHERE u.id = ? AND u.status = 'active'
            """,
            (reviewer_id,)
        ).fetchone()

        if not row:
            return False, f"Selected reviewer ({reviewer_id}) is not an active user with Badge Reviewer responsibility."

        rev_band = row["band_code"]
        if rev_band not in higher_bands:
            return False, f"Reviewer is in band {rev_band}, which is not higher than target badge band {target_band}."

        return True, "Eligible"

    # ==========================================================================
    # BADGE CREATION & APPROVAL WORKFLOW
    # ==========================================================================

    def create_badge_for_review(
        self,
        badge_data: Dict[str, Any],
        creator_id: str = "guardian_1",
        creator_name: str = "Arjun Mehta"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Executes atomic creation of a badge in 'pending_review' status.
        Inserts normalized Power, Capability, Skill, structured Prompt,
        Reviewer assignment (with 24h deadline), ActivityEvent, and Notification.
        """
        target_band = badge_data.get("target_band", "")
        reviewer_id = badge_data.get("assigned_reviewer_id") or badge_data.get("reviewer_id", "")

        is_eligible, reason = self.verify_reviewer_eligibility(reviewer_id, target_band)
        if not is_eligible:
            return False, reason, None

        b_id = badge_data.get("id") or f"badge_{badge_data.get('code','').lower().replace('-','_')}_{int(datetime.datetime.now().timestamp())}"
        now_iso = current_iso_timestamp()
        due_iso = review_deadline_iso_timestamp(24)

        if not SQLITE_AVAILABLE or self.conn is None:
            return True, "Badge Created Successfully!", b_id

        try:
            with self.conn:
                # 1. Insert or Update Badge Record (workflow_status = 'pending_review', is_published = 0, is_allocated = 0)
                existing_b = self.conn.execute("SELECT id FROM badges WHERE id = ?", (b_id,)).fetchone()
                if existing_b:
                    self.conn.execute(
                        """
                        UPDATE badges SET
                            code = ?, title = ?, category = ?, description = ?,
                            learning_outcomes_json = ?, learning_topics_json = ?, project_requirements = ?,
                            target_band = ?, power = ?, capability = ?, skill = ?,
                            prompt_json = ?, workflow_status = 'pending_review', creator_id = ?, assigned_reviewer_id = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            badge_data["code"],
                            badge_data["title"],
                            badge_data.get("category", "Architecture"),
                            badge_data.get("description", ""),
                            json.dumps(badge_data.get("learning_outcomes", [])),
                            json.dumps(badge_data.get("learning_topics", [])),
                            badge_data.get("project_requirements", ""),
                            target_band,
                            badge_data.get("power", ""),
                            badge_data.get("capability", ""),
                            badge_data.get("skill", ""),
                            badge_data.get("prompt_json", "{}"),
                            creator_id,
                            reviewer_id,
                            now_iso,
                            b_id
                        )
                    )
                else:
                    self.conn.execute(
                        """
                        INSERT INTO badges (
                            id, code, title, category, description,
                            learning_outcomes_json, learning_topics_json, project_requirements,
                            is_published, is_allocated, target_band, power, capability, skill,
                            prompt_json, workflow_status, creator_id, assigned_reviewer_id,
                            assigned_cosmonaut_ids_json, default_timeline_json, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?, 'pending_review', ?, ?, '[]', '{}', ?, ?)
                        """,
                        (
                            b_id,
                            badge_data["code"],
                            badge_data["title"],
                            badge_data.get("category", "Architecture"),
                            badge_data.get("description", ""),
                            json.dumps(badge_data.get("learning_outcomes", [])),
                            json.dumps(badge_data.get("learning_topics", [])),
                            badge_data.get("project_requirements", ""),
                            target_band,
                            badge_data.get("power", ""),
                            badge_data.get("capability", ""),
                            badge_data.get("skill", ""),
                            badge_data.get("prompt_json", "{}"),
                            creator_id,
                            reviewer_id,
                            now_iso,
                            now_iso
                        )
                    )

                # 2. Normalized Associations
                if badge_data.get("power"):
                    self.conn.execute("INSERT OR REPLACE INTO badge_powers (badge_id, power_name) VALUES (?, ?)", (b_id, badge_data["power"]))
                if badge_data.get("capability"):
                    self.conn.execute("INSERT OR REPLACE INTO badge_capabilities (badge_id, capability_name, is_custom) VALUES (?, ?, ?)", (b_id, badge_data["capability"], 1 if badge_data.get("is_custom_capability") else 0))
                if badge_data.get("skill"):
                    self.conn.execute("INSERT OR REPLACE INTO badge_skills (badge_id, skill_name, is_custom) VALUES (?, ?, ?)", (b_id, badge_data["skill"], 1 if badge_data.get("is_custom_skill") else 0))

                # 3. Prerequisites
                for prereq in badge_data.get("prerequisites", []):
                    self.conn.execute("INSERT OR IGNORE INTO badge_prerequisites (badge_id, prerequisite_badge_id) VALUES (?, ?)", (b_id, prereq))

                # 4. Reviewer Assignment
                assign_id = f"assign_{b_id}_{int(datetime.datetime.now().timestamp())}"
                self.conn.execute(
                    """
                    INSERT INTO badge_reviewer_assignments (id, badge_id, reviewer_id, assigned_at, review_due_at, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                    """,
                    (assign_id, b_id, reviewer_id, now_iso, due_iso)
                )

                # 5. Review Event Log
                event_id = f"bre_{b_id}_created"
                self.conn.execute(
                    """
                    INSERT INTO badge_review_events (id, badge_id, actor_id, event_type, previous_status, new_status, notes, timestamp)
                    VALUES (?, ?, ?, 'created_and_submitted', NULL, 'pending_review', 'Badge created and submitted for authorization.', ?)
                    """,
                    (event_id, b_id, creator_id, now_iso)
                )

                # 6. Notification to Assigned Reviewer
                notif_id = f"notif_badge_rev_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO notifications (id, recipient_id, title, message, link_section, created_at, is_read, event_type, related_badge_id)
                    VALUES (?, ?, ?, ?, 'g_badge_approval', ?, 0, 'badge_review_assigned', ?)
                    """,
                    (
                        notif_id,
                        reviewer_id,
                        f"Badge Authorization Request: {badge_data['code']}",
                        f"Guardian {creator_name} has submitted a new badge '{badge_data['title']}' ({badge_data['code']}) for Band {target_band} requiring your review.",
                        now_iso,
                        b_id
                    )
                )

                # 7. Activity Event
                act_id = f"act_badge_created_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO activity_events (id, timestamp, event_type, actor_id, actor_name, cosmonaut_id, badge_id, summary, details)
                    VALUES (?, ?, 'badge_created', ?, ?, '', ?, ?, ?)
                    """,
                    (
                        act_id,
                        now_iso,
                        creator_id,
                        creator_name,
                        b_id,
                        f"Created badge {badge_data['code']} ({badge_data['title']}) and submitted for reviewer authorization.",
                        f"Assigned reviewer: {reviewer_id}. Target band: {target_band}."
                    )
                )

            return True, "Badge Created Successfully!", b_id
        except Exception as e:
            return False, f"Database transaction failed: {e}", None

    def update_badge_by_reviewer(
        self,
        badge_id: str,
        updated_data: Dict[str, Any],
        reviewer_id: str,
        reviewer_name: str
    ) -> Tuple[bool, str]:
        """
        Allows assigned Badge Reviewer to edit submitted badge metadata, power, capability,
        skill, or structured prompt. Preserves pending_review status without auto-approving.
        """
        now_iso = current_iso_timestamp()
        if not SQLITE_AVAILABLE or self.conn is None:
            return True, "Badge updated successfully. Status remains Pending Review."
        try:
            curr_row = self.conn.execute("SELECT * FROM badges WHERE id = ?", (badge_id,)).fetchone()
            if not curr_row:
                return False, f"Badge {badge_id} not found."

            new_title = updated_data.get("title") or curr_row["title"]
            new_cat = updated_data.get("category") or curr_row["category"]
            new_desc = updated_data.get("description") if "description" in updated_data else curr_row["description"]
            new_outcomes = json.dumps(updated_data["learning_outcomes"]) if "learning_outcomes" in updated_data else curr_row["learning_outcomes_json"]
            new_topics = json.dumps(updated_data["learning_topics"]) if "learning_topics" in updated_data else curr_row["learning_topics_json"]
            new_reqs = updated_data.get("project_requirements") if "project_requirements" in updated_data else curr_row["project_requirements"]
            new_power = updated_data.get("power") or curr_row["power"]
            new_cap = updated_data.get("capability") or curr_row["capability"]
            new_skill = updated_data.get("skill") or curr_row["skill"]
            new_prompt = updated_data.get("prompt_json") or curr_row["prompt_json"]

            # Synchronize outcomes and topics from prompt_json if provided
            if "prompt_json" in updated_data and updated_data["prompt_json"]:
                try:
                    pj = json.loads(updated_data["prompt_json"])
                    if "outcomes" in pj and "learning_outcomes" not in updated_data:
                        new_outcomes = json.dumps(pj["outcomes"])
                    elif "learning_outcomes" in pj and "learning_outcomes" not in updated_data:
                        new_outcomes = json.dumps(pj["learning_outcomes"])
                    if "learning_topics" in pj and "learning_topics" not in updated_data:
                        new_topics = json.dumps([t["title"] if isinstance(t, dict) else str(t) for t in pj["learning_topics"]])
                except Exception:
                    pass

            with self.conn:
                self.conn.execute(
                    """
                    UPDATE badges SET
                        title = ?,
                        category = ?,
                        description = ?,
                        learning_outcomes_json = ?,
                        learning_topics_json = ?,
                        project_requirements = ?,
                        power = ?,
                        capability = ?,
                        skill = ?,
                        prompt_json = ?,
                        updated_at = ?
                    WHERE id = ? AND workflow_status IN ('pending_review', 'ready_for_review', 'returned', 'approved')
                    """,
                    (
                        new_title,
                        new_cat,
                        new_desc,
                        new_outcomes,
                        new_topics,
                        new_reqs,
                        new_power,
                        new_cap,
                        new_skill,
                        new_prompt,
                        now_iso,
                        badge_id
                    )
                )

                # Normalized power, capability, skill updates
                if new_power:
                    self.conn.execute("INSERT OR REPLACE INTO badge_powers (badge_id, power_name) VALUES (?, ?)", (badge_id, new_power))
                if new_cap:
                    self.conn.execute("INSERT OR REPLACE INTO badge_capabilities (badge_id, capability_name, is_custom) VALUES (?, ?, 0)", (badge_id, new_cap))
                if new_skill:
                    self.conn.execute("INSERT OR REPLACE INTO badge_skills (badge_id, skill_name, is_custom) VALUES (?, ?, 0)", (badge_id, new_skill))

                # Audit event
                event_id = f"bre_{badge_id}_edit_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO badge_review_events (id, badge_id, actor_id, event_type, previous_status, new_status, notes, timestamp)
                    VALUES (?, ?, ?, 'edited', 'pending_review', 'pending_review', 'Badge details and structured prompt edited by reviewer.', ?)
                    """,
                    (event_id, badge_id, reviewer_id, now_iso)
                )

                # Activity event
                act_id = f"act_badge_edit_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO activity_events (id, timestamp, event_type, actor_id, actor_name, cosmonaut_id, badge_id, summary, details)
                    VALUES (?, ?, 'badge_edited', ?, ?, '', ?, ?, ?)
                    """,
                    (act_id, now_iso, reviewer_id, reviewer_name, badge_id, f"Reviewer {reviewer_name} edited badge {badge_id} specification.", "")
                )
            return True, "Badge updated successfully. Status remains Pending Review."
        except Exception as e:
            return False, f"Failed to update badge: {e}"

    def approve_badge(
        self,
        badge_id: str,
        reviewer_id: str,
        reviewer_name: str,
        notes: str = ""
    ) -> Tuple[bool, str]:
        """
        Executes formal badge authorization.
        Checks reviewer authority, updates workflow_status to 'approved',
        records decision timestamp, logs review event & activity, and notifies creator.
        Does NOT automatically allot or publish the badge to learners.
        """
        now_iso = current_iso_timestamp()

        if not SQLITE_AVAILABLE or self.conn is None:
            return True, f"Badge {badge_id} successfully approved!"

        # Authorization check: verify user has badge_reviewer role
        role_check = self.conn.execute(
            "SELECT 1 FROM user_role_assignments WHERE user_id = ? AND role_id = 'badge_reviewer'",
            (reviewer_id,)
        ).fetchone()
        if not role_check:
            return False, "Access Denied: Current user does not hold Badge Reviewer credentials."

        # Verify badge exists and is pending review
        badge_row = self.conn.execute("SELECT * FROM badges WHERE id = ?", (badge_id,)).fetchone()
        if not badge_row:
            return False, "Badge not found."

        if badge_row["workflow_status"] == "approved":
            return False, "Badge is already approved."

        creator_id = badge_row["creator_id"] or "guardian_1"
        badge_code = badge_row["code"]
        badge_title = badge_row["title"]

        try:
            with self.conn:
                # 1. Update Badge Status
                self.conn.execute(
                    """
                    UPDATE badges SET
                        workflow_status = 'approved',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now_iso, badge_id)
                )

                # 2. Update Reviewer Assignment Record
                self.conn.execute(
                    """
                    UPDATE badge_reviewer_assignments SET
                        status = 'approved',
                        decision_notes = ?,
                        decided_at = ?
                    WHERE badge_id = ? AND status = 'pending'
                    """,
                    (notes, now_iso, badge_id)
                )

                # 3. Audit Review Event
                event_id = f"bre_{badge_id}_approved"
                self.conn.execute(
                    """
                    INSERT INTO badge_review_events (id, badge_id, actor_id, event_type, previous_status, new_status, notes, timestamp)
                    VALUES (?, ?, ?, 'approved', 'pending_review', 'approved', ?, ?)
                    """,
                    (event_id, badge_id, reviewer_id, notes or "Badge authorized by reviewer.", now_iso)
                )

                # 4. Notify Originating Guardian
                notif_id = f"notif_approved_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO notifications (id, recipient_id, title, message, link_section, created_at, is_read, event_type, related_badge_id)
                    VALUES (?, ?, ?, ?, 'g_badge_approval', ?, 0, 'badge_approved', ?)
                    """,
                    (
                        notif_id,
                        creator_id,
                        f"Badge Approved: {badge_code}",
                        f"Reviewer {reviewer_name} has officially approved badge '{badge_title}' ({badge_code}). It is now available in your Allotment catalog.",
                        now_iso,
                        badge_id
                    )
                )

                # 5. Activity Event
                act_id = f"act_approved_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO activity_events (id, timestamp, event_type, actor_id, actor_name, cosmonaut_id, badge_id, summary, details)
                    VALUES (?, ?, 'badge_approved', ?, ?, '', ?, ?, ?)
                    """,
                    (
                        act_id,
                        now_iso,
                        reviewer_id,
                        reviewer_name,
                        badge_id,
                        f"Approved badge {badge_code} ({badge_title}).",
                        notes
                    )
                )

            return True, f"Badge {badge_code} successfully approved!"
        except Exception as e:
            return False, f"Approval transaction failed: {e}"

    def return_badge(
        self,
        badge_id: str,
        reviewer_id: str,
        reviewer_name: str,
        notes: str = ""
    ) -> Tuple[bool, str]:
        """
        Returns / Rejects a badge with revision feedback to the creator Guardian.
        Updates workflow_status to 'returned' and logs feedback and audit trails.
        """
        now_iso = current_iso_timestamp()
        if not SQLITE_AVAILABLE or self.conn is None:
            return True, f"Badge {badge_id} returned for revisions."

        try:
            badge_row = self.conn.execute("SELECT * FROM badges WHERE id = ?", (badge_id,)).fetchone()
            if not badge_row:
                return False, f"Badge {badge_id} not found."

            creator_id = badge_row["creator_id"] or "guardian_1"
            badge_code = badge_row["code"]
            badge_title = badge_row["title"]

            with self.conn:
                # 1. Update Badge status
                self.conn.execute(
                    """
                    UPDATE badges SET
                        workflow_status = 'returned',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now_iso, badge_id)
                )

                # 2. Update assignment record
                self.conn.execute(
                    """
                    UPDATE badge_reviewer_assignments SET
                        status = 'returned',
                        decision_notes = ?,
                        decided_at = ?
                    WHERE badge_id = ? AND status = 'pending'
                    """,
                    (notes or "Badge returned with revision feedback.", now_iso, badge_id)
                )

                # 3. Audit Review Event
                event_id = f"bre_{badge_id}_returned_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO badge_review_events (id, badge_id, actor_id, event_type, previous_status, new_status, notes, timestamp)
                    VALUES (?, ?, ?, 'returned', 'pending_review', 'returned', ?, ?)
                    """,
                    (event_id, badge_id, reviewer_id, notes or "Returned with feedback.", now_iso)
                )

                # 4. Notify Creator Guardian
                notif_id = f"notif_ret_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO notifications (id, recipient_id, title, message, link_section, created_at, is_read, event_type, related_badge_id)
                    VALUES (?, ?, ?, ?, 'g_badge_approval', ?, 0, 'badge_returned', ?)
                    """,
                    (
                        notif_id,
                        creator_id,
                        f"Badge Returned: {badge_code}",
                        f"Reviewer {reviewer_name} returned badge '{badge_title}' with feedback: {notes}",
                        now_iso,
                        badge_id
                    )
                )

                # 5. Activity Event
                act_id = f"act_ret_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO activity_events (id, timestamp, event_type, actor_id, actor_name, cosmonaut_id, badge_id, summary, details)
                    VALUES (?, ?, 'badge_returned', ?, ?, '', ?, ?, ?)
                    """,
                    (
                        act_id,
                        now_iso,
                        reviewer_id,
                        reviewer_name,
                        badge_id,
                        f"Reviewer {reviewer_name} returned badge {badge_code} ({badge_title}) for revisions.",
                        notes
                    )
                )

            return True, f"Badge {badge_code} returned with feedback."
        except Exception as e:
            return False, f"Failed to return badge: {e}"

    def assign_and_request_badge_review(
        self,
        badge_id: str,
        reviewer_id: str,
        creator_id: str = "guardian_1"
    ) -> Tuple[bool, str]:
        """
        Assigns an eligible higher-band reviewer to a badge and dispatches the review request.
        Strictly enforces higher-band hierarchy:
        Target Band B1 -> Reviewer must be B2..B6
        Target Band B2 -> Reviewer must be B3..B6
        Target Band B3 -> Reviewer must be B4..B6
        Target Band B4 -> Reviewer must be B5..B6
        Target Band B5 -> Reviewer must be B6
        Target Band B6 -> Locked (Executive Council)
        """
        now_iso = current_iso_timestamp()
        if not SQLITE_AVAILABLE or self.conn is None:
            return True, "Review request dispatched successfully."

        try:
            badge_row = self.conn.execute("SELECT * FROM badges WHERE id = ?", (badge_id,)).fetchone()
            if not badge_row:
                return False, f"Badge {badge_id} not found."

            target_band = badge_row["target_band"] or "B1"
            from starapp.mapping_data import get_higher_bands
            higher_bands = get_higher_bands(target_band)

            if target_band == "B6":
                return False, "Band B6 badges require Executive Council review. No higher-band reviewer is eligible."

            # Verify reviewer exists and is in a higher band
            rev_row = self.conn.execute(
                """
                SELECT u.id, u.name, u.email, m.band_code
                FROM users u
                JOIN user_band_memberships m ON u.id = m.user_id
                WHERE u.id = ? AND u.status = 'active'
                """,
                (reviewer_id,)
            ).fetchone()

            if not rev_row:
                return False, f"Selected reviewer {reviewer_id} not found or inactive."

            rev_band = rev_row["band_code"]
            if rev_band not in higher_bands:
                return False, f"Invalid Reviewer: A Band {target_band} badge can only be reviewed by engineers in higher bands ({', '.join(higher_bands)}). {rev_row['name']} is in Band {rev_band}."

            rev_name = rev_row["name"]
            badge_code = badge_row["code"]
            badge_title = badge_row["title"]

            due_date = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
            assign_id = f"bra_{badge_id}_{reviewer_id}_{int(datetime.datetime.now().timestamp())}"

            with self.conn:
                # 1. Update Badge status & assigned reviewer
                self.conn.execute(
                    """
                    UPDATE badges SET
                        workflow_status = 'pending_review',
                        assigned_reviewer_id = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (reviewer_id, now_iso, badge_id)
                )

                # 2. Insert or replace assignment record
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO badge_reviewer_assignments (
                        id, badge_id, reviewer_id, assigned_at, review_due_at, status, decision_notes, decided_at
                    ) VALUES (?, ?, ?, ?, ?, 'pending', '', NULL)
                    """,
                    (assign_id, badge_id, reviewer_id, now_iso, due_date)
                )

                # 3. Audit Review Event
                event_id = f"bre_{badge_id}_req_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO badge_review_events (id, badge_id, actor_id, event_type, previous_status, new_status, notes, timestamp)
                    VALUES (?, ?, ?, 'created_and_submitted', ?, 'pending_review', ?, ?)
                    """,
                    (event_id, badge_id, creator_id, badge_row["workflow_status"], f"Review requested from {rev_name} ({rev_band}).", now_iso)
                )

                # 4. Dispatch Notification to Reviewer
                notif_id = f"notif_req_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO notifications (id, recipient_id, title, message, link_section, created_at, is_read, event_type, related_badge_id)
                    VALUES (?, ?, ?, ?, 'c_requests', ?, 0, 'badge_review_requested', ?)
                    """,
                    (
                        notif_id,
                        reviewer_id,
                        f"Review Request: {badge_code}",
                        f"Guardian submitted badge '{badge_title}' ({badge_code}) for Band {target_band} for your review and authorization.",
                        now_iso,
                        badge_id
                    )
                )

                # 5. Activity Event
                act_id = f"act_req_{int(datetime.datetime.now().timestamp() * 1000)}"
                self.conn.execute(
                    """
                    INSERT INTO activity_events (id, timestamp, event_type, actor_id, actor_name, cosmonaut_id, badge_id, summary, details)
                    VALUES (?, ?, 'badge_review_requested', ?, 'Guardian', '', ?, ?, ?)
                    """,
                    (
                        act_id,
                        now_iso,
                        creator_id,
                        badge_id,
                        f"Dispatched review request for {badge_code} ({badge_title}) to {rev_name} ({rev_band}).",
                        f"Review due by {due_date}."
                    )
                )

            return True, f"Review request for badge '{badge_title}' sent to {rev_name} ({rev_band})!"
        except Exception as e:
            return False, f"Failed to dispatch review request: {e}"

    # ==========================================================================
    # WORKFLOW QUERY ACCESSORS
    # ==========================================================================

    def get_submitted_badges_for_approval(self, status_filter: str = "all") -> List[Dict[str, Any]]:
        """Retrieves badges in the authorization pipeline with creator and reviewer details."""
        if not SQLITE_AVAILABLE or self.conn is None:
            return []
        query = """
        SELECT
            b.id, b.code, b.title, b.category, b.description, b.target_band,
            b.power, b.capability, b.skill, b.prompt_json, b.workflow_status,
            b.created_at, b.updated_at,
            b.creator_id, u_c.name AS creator_name,
            b.assigned_reviewer_id, u_r.name AS reviewer_name,
            u_r.username AS reviewer_username,
            ra.review_due_at, ra.status AS assignment_status, ra.decision_notes
        FROM badges b
        LEFT JOIN users u_c ON b.creator_id = u_c.id
        LEFT JOIN users u_r ON b.assigned_reviewer_id = u_r.id
        LEFT JOIN badge_reviewer_assignments ra ON b.id = ra.badge_id
        WHERE b.workflow_status IN ('ready_for_review', 'pending_review', 'approved', 'returned')
        """
        params = []
        if status_filter != "all":
            query += " AND b.workflow_status = ?"
            params.append(status_filter)
        query += " ORDER BY b.created_at DESC"

        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_badge_review_detail(self, badge_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves complete details for badge review modal or inspection."""
        if not SQLITE_AVAILABLE or self.conn is None:
            return None
        query = """
        SELECT
            b.*,
            u_c.name AS creator_name, u_c.email AS creator_email,
            u_r.name AS reviewer_name, u_r.email AS reviewer_email,
            ra.assigned_at, ra.review_due_at, ra.status AS assignment_status, ra.decision_notes, ra.decided_at
        FROM badges b
        LEFT JOIN users u_c ON b.creator_id = u_c.id
        LEFT JOIN users u_r ON b.assigned_reviewer_id = u_r.id
        LEFT JOIN badge_reviewer_assignments ra ON b.id = ra.badge_id
        WHERE b.id = ?
        """
        row = self.conn.execute(query, (badge_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        # Parse JSON fields safely
        try:
            res["learning_outcomes"] = json.loads(res.get("learning_outcomes_json", "[]"))
        except Exception:
            res["learning_outcomes"] = []
        try:
            res["learning_topics"] = json.loads(res.get("learning_topics_json", "[]"))
        except Exception:
            res["learning_topics"] = []
        try:
            res["prompt"] = json.loads(res.get("prompt_json", "{}"))
        except Exception:
            res["prompt"] = {}
        return res

    def get_badge_review_requests_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all badge review requests where user_id is the assigned reviewer.
        Includes badge details, assignment metadata, decision notes, outcomes, and topics.
        """
        if not SQLITE_AVAILABLE or self.conn is None:
            return []
        query = """
        SELECT
            b.id, b.code, b.title, b.category, b.description, b.target_band,
            b.power, b.capability, b.skill, b.prompt_json, b.workflow_status,
            b.learning_outcomes_json, b.learning_topics_json, b.project_requirements,
            b.created_at, b.updated_at,
            b.creator_id, u_c.name AS creator_name, u_c.email AS creator_email,
            b.assigned_reviewer_id, u_r.name AS reviewer_name,
            ra.id AS assignment_id, ra.assigned_at, ra.review_due_at,
            ra.status AS assignment_status, ra.decision_notes, ra.decided_at
        FROM badges b
        LEFT JOIN users u_c ON b.creator_id = u_c.id
        LEFT JOIN users u_r ON b.assigned_reviewer_id = u_r.id
        LEFT JOIN badge_reviewer_assignments ra ON b.id = ra.badge_id
        WHERE b.assigned_reviewer_id = ? OR ra.reviewer_id = ?
        ORDER BY b.created_at DESC
        """
        rows = self.conn.execute(query, (user_id, user_id)).fetchall()
        results = []
        seen_ids = set()
        for r in rows:
            d = dict(r)
            if d["id"] in seen_ids:
                continue
            seen_ids.add(d["id"])
            try:
                d["learning_outcomes"] = json.loads(d.get("learning_outcomes_json") or "[]")
            except Exception:
                d["learning_outcomes"] = []
            try:
                d["learning_topics"] = json.loads(d.get("learning_topics_json") or "[]")
            except Exception:
                d["learning_topics"] = []
            prompt_obj = {}
            if d.get("prompt_json"):
                try:
                    prompt_obj = json.loads(d["prompt_json"])
                except Exception:
                    prompt_obj = {}
            d["prompt"] = prompt_obj
            d["location"] = prompt_obj.get("location") or f"{d['title']} -> {d.get('skill', 'General')} -> {d.get('capability', 'Core')} -> {d.get('power', 'Tech')} -> Band {d.get('target_band', 'B1')}"
            results.append(d)
        return results

    def get_badge_review_history(
        self,
        badge_id: Optional[str] = None,
        reviewer_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves complete audit trail of badge review events.
        Includes badge details, taxonomy tree, actor metadata, timestamps, and notes.
        """
        if not SQLITE_AVAILABLE or self.conn is None:
            return []
        
        conditions = []
        params = []
        if badge_id:
            conditions.append("e.badge_id = ?")
            params.append(badge_id)
        if reviewer_id:
            conditions.append("(e.actor_id = ? OR b.assigned_reviewer_id = ?)")
            params.extend([reviewer_id, reviewer_id])
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
        SELECT
            e.id, e.badge_id, e.actor_id, e.event_type, e.previous_status, e.new_status, e.notes, e.timestamp,
            b.code AS badge_code, b.title AS badge_title, b.target_band, b.power, b.capability, b.skill,
            u.name AS actor_name, m.band_code AS actor_band
        FROM badge_review_events e
        LEFT JOIN badges b ON e.badge_id = b.id
        LEFT JOIN users u ON e.actor_id = u.id
        LEFT JOIN user_band_memberships m ON u.id = m.user_id
        {where_clause}
        ORDER BY e.timestamp DESC
        """
        rows = self.conn.execute(query, tuple(params)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            b_title = d.get("badge_title") or "Milestone Badge"
            skill = d.get("skill") or "Engineering"
            cap = d.get("capability") or "Systems"
            power = d.get("power") or "Tech"
            band = d.get("target_band") or "B1"
            d["taxonomy_tree"] = f"{b_title} → {skill} → {cap} → {power} → Band {band}"
            ts = d.get("timestamp") or ""
            if "T" in ts:
                date_part, time_part = ts.split("T", 1)
                time_clean = time_part[:5]
                d["formatted_timestamp"] = f"{date_part} {time_clean}"
            else:
                d["formatted_timestamp"] = ts[:16]
            results.append(d)
        return results

# Global database manager instance
db = DatabaseManager()
