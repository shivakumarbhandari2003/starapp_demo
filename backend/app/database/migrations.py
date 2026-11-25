"""
Database migration management and schema initialization for StarApp persistent backend.
"""
import sqlite3
import datetime
import logging
from backend.app.database.connection import get_db_connection
from backend.app.core.security import hash_password

logger = logging.getLogger("starapp.migrations")


def apply_migrations():
    """Apply versioned schema migrations to the persistent SQLite database."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # 1. Create user_sessions table if not present
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_active_at TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);")

        # 1b. Create reviewer_project_prompts table if not present
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reviewer_project_prompts (
                id TEXT PRIMARY KEY,
                badge_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                cosmonaut_ids_json TEXT NOT NULL DEFAULT '[]',
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                deliverables_json TEXT NOT NULL DEFAULT '{}',
                requirements_text TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                sent_at TEXT,
                FOREIGN KEY(reviewer_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rev_proj_badge ON reviewer_project_prompts(badge_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rev_proj_reviewer ON reviewer_project_prompts(reviewer_id);")
        
        # 2. Check if admin user exists; if not, create default admin/guardian
        cur.execute("SELECT COUNT(*) FROM users WHERE username = 'admin' OR id = 'admin';")
        if cur.fetchone()[0] == 0:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT OR IGNORE INTO users (
                    id, username, email, name, role, learning_track, track_code, band,
                    password, primary_role, status, is_demo, created_at
                ) VALUES (
                    'admin', 'admin', 'admin@starapp.io', 'Guardian Admin', 'Administrator',
                    'Leadership', 'EXEC', 'B6', ?, 'guardian', 'active', 0, ?
                );
            """, (hash_password("12345678"), now_iso))

        # 3. Safe Column Migrations for Complete Assessment, Mapping & Cycle Workflow
        safe_columns = [
            ("assessment_marksheets", "assessor_role", "TEXT DEFAULT 'guardian'"),
            ("assessment_marksheets", "remarks", "TEXT DEFAULT ''"),
            ("badges", "passing_percentage", "REAL DEFAULT 70.0"),
            ("badges", "published_at", "TEXT DEFAULT ''"),
            ("badges", "published_by", "TEXT DEFAULT ''"),
            ("badge_timelines", "reviewer_id", "TEXT DEFAULT ''"),
            ("badge_timelines", "review_window_json", "TEXT DEFAULT '[]'"),
        ]
        for tbl, col, col_def in safe_columns:
            try:
                cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def};")
            except Exception:
                pass

        # 4. 6-Month Performance Cycles, Enrollments & Appraisals Schema
        cur.execute("""
            CREATE TABLE IF NOT EXISTS performance_cycles (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_by TEXT DEFAULT 'guardian_1',
                created_at TEXT NOT NULL,
                closed_at TEXT DEFAULT '',
                cloned_from_cycle_id TEXT DEFAULT '',
                hike_policy_json TEXT NOT NULL DEFAULT '{}',
                notes TEXT DEFAULT ''
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cycle_enrollments (
                id TEXT PRIMARY KEY,
                cycle_id TEXT NOT NULL REFERENCES performance_cycles(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                cycle_role TEXT NOT NULL DEFAULT 'cosmonaut',
                band_code TEXT NOT NULL DEFAULT 'B1',
                track_code TEXT NOT NULL DEFAULT 'SD',
                base_salary REAL NOT NULL DEFAULT 0.0,
                reporting_manager_id TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                enrolled_at TEXT NOT NULL,
                UNIQUE(cycle_id, user_id)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cycle_performance_appraisals (
                id TEXT PRIMARY KEY,
                cycle_id TEXT NOT NULL REFERENCES performance_cycles(id) ON DELETE CASCADE,
                cosmonaut_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                band_code TEXT NOT NULL DEFAULT 'B1',
                badges_assigned INTEGER NOT NULL DEFAULT 0,
                badges_submitted INTEGER NOT NULL DEFAULT 0,
                badges_earned INTEGER NOT NULL DEFAULT 0,
                first_attempt_passes INTEGER NOT NULL DEFAULT 0,
                total_attempts INTEGER NOT NULL DEFAULT 0,
                avg_marks REAL NOT NULL DEFAULT 0.0,
                avg_percentage REAL NOT NULL DEFAULT 0.0,
                cosmo_score REAL NOT NULL DEFAULT 0.0,
                badge_reviews_assigned INTEGER NOT NULL DEFAULT 0,
                badge_reviews_completed INTEGER NOT NULL DEFAULT 0,
                projects_created INTEGER NOT NULL DEFAULT 0,
                projects_released INTEGER NOT NULL DEFAULT 0,
                submissions_assigned_to_review INTEGER NOT NULL DEFAULT 0,
                submissions_graded INTEGER NOT NULL DEFAULT 0,
                reviewer_avg_marks_given REAL NOT NULL DEFAULT 0.0,
                reviewer_score REAL NOT NULL DEFAULT 0.0,
                composite_score REAL NOT NULL DEFAULT 0.0,
                performance_tier TEXT NOT NULL DEFAULT 'Not Assessed',
                base_salary REAL NOT NULL DEFAULT 0.0,
                recommended_hike_pct REAL NOT NULL DEFAULT 0.0,
                approved_hike_pct REAL NOT NULL DEFAULT 0.0,
                hike_amount REAL NOT NULL DEFAULT 0.0,
                new_salary REAL NOT NULL DEFAULT 0.0,
                bonus_amount REAL NOT NULL DEFAULT 0.0,
                recommended_promotion_band TEXT DEFAULT '',
                guardian_remarks TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'calculated',
                calculated_at TEXT NOT NULL,
                finalized_by TEXT DEFAULT '',
                finalized_at TEXT DEFAULT '',
                details_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(cycle_id, cosmonaut_id)
            );
        """)

        cycle_scoped_tables = [
            "badges", "badge_reviewer_assignments", "badge_review_events", "badge_timelines",
            "project_submissions", "assessment_marksheets", "learning_materials",
            "deadline_extensions", "announcements", "notifications", "activity_events",
            "band_mappings", "mapping_requests", "reviewer_project_prompts"
        ]
        for tbl in cycle_scoped_tables:
            try:
                cur.execute(f"ALTER TABLE {tbl} ADD COLUMN cycle_id TEXT NOT NULL DEFAULT 'cycle_1';")
            except Exception:
                pass
            try:
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{tbl}_cycle ON {tbl}(cycle_id);")
            except Exception:
                pass

        # Backfill initial 6-month cycle if empty so all previously saved data belongs to cycle_1
        cur.execute("SELECT COUNT(*) FROM performance_cycles;")
        if cur.fetchone()[0] == 0:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT OR IGNORE INTO performance_cycles (
                    id, code, name, start_date, end_date, status, created_by, created_at
                ) VALUES ('cycle_1', 'C1-2026', 'Cycle 1 (Jul–Dec 2026)', '2026-07-01', '2026-12-31', 'active', 'guardian_1', ?);
            """, (now_iso,))

        active_row = cur.execute("SELECT id FROM performance_cycles ORDER BY CASE WHEN status='active' THEN 0 ELSE 1 END, created_at ASC LIMIT 1").fetchone()
        default_cid = active_row[0] if active_row else "cycle_1"
        for tbl in cycle_scoped_tables:
            try:
                cur.execute(f"UPDATE {tbl} SET cycle_id = ? WHERE cycle_id IS NULL OR cycle_id = '';", (default_cid,))
            except Exception:
                pass

        # Enroll existing active users in default_cid if missing
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for u_row in cur.execute("SELECT id, primary_role, band, track_code, reporting_manager_id FROM users WHERE status = 'active'").fetchall():
            cur.execute("""
                INSERT OR IGNORE INTO cycle_enrollments (
                    id, cycle_id, user_id, cycle_role, band_code, track_code, base_salary, reporting_manager_id, status, enrolled_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, 'active', ?);
            """, (f"enr_{default_cid}_{u_row[0]}", default_cid, u_row[0], u_row[1] or "cosmonaut", u_row[2] or "B1", u_row[3] or "SD", u_row[4] or "", now_iso))

        logger.info("Database migrations applied successfully.")


if __name__ == "__main__":
    apply_migrations()
    print("Migrations applied.")
