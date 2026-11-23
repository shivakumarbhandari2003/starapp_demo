import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "starapp.db")
db_path = os.path.abspath(db_path)

tables_to_clear = [
    "assessment_marksheets",
    "project_submissions",
    "reviewer_project_prompts",
    "learning_materials",
    "deadline_extensions",
    "badge_timelines",
    "badge_prerequisites",
    "badge_reviewer_assignments",
    "badge_review_events",
    "badge_powers",
    "badge_capabilities",
    "badge_skills",
    "badges",
    "band_mappings",
    "mapping_requests",
    "custom_capabilities",
    "custom_skills",
    "notifications",
    "activity_events",
    "announcement_read_receipts",
    "announcement_recipients",
    "announcements",
    "user_sessions"
]

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = OFF;")

cleared_summary = {}
for tbl in tables_to_clear:
    try:
        cur.execute(f"DELETE FROM {tbl};")
        cleared_summary[tbl] = cur.rowcount
    except Exception as e:
        cleared_summary[tbl] = f"Error: {e}"

conn.commit()

# Vacuum database
cur.execute("VACUUM;")

# Foreign key and integrity checks
cur.execute("PRAGMA foreign_keys = ON;")
cur.execute("PRAGMA foreign_key_check;")
fk_violations = cur.fetchall()

cur.execute("PRAGMA integrity_check;")
integrity_result = cur.fetchall()

print("=== STARAPP DATA DELETION SUMMARY ===")
for t, count in cleared_summary.items():
    print(f"  - Cleared {t}: {count} rows")

print(f"\nForeign Key Violations: {len(fk_violations)}")
print(f"Integrity Check: {integrity_result}")

# Verify remaining preserved user tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%' ORDER BY name;")
all_tables = [r[0] for r in cur.fetchall()]

print("\n=== AUTHORITATIVE PRESERVED SQLITE TABLES ===")
for t in all_tables:
    cnt = conn.execute(f"SELECT COUNT(*) FROM {t};").fetchone()[0]
    print(f"  {t}: {cnt} rows")

conn.close()
