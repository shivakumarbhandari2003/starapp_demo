import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "starapp.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

tables_to_clear = [
    "badges",
    "badge_powers",
    "badge_capabilities",
    "band_mappings",
    "badge_timelines",
    "reviewer_project_prompts",
    "project_submissions",
    "assessment_marksheets",
    "deadline_extensions",
    "badge_reviewer_assignments",
    "badge_review_events",
    "badge_allotments",
    "badge_curriculum_plans",
    "mapping_requests"
]

print("Clearing tables in", db_path)
c.execute("PRAGMA foreign_keys = OFF;")
for table in tables_to_clear:
    try:
        c.execute(f"DELETE FROM {table};")
        print(f"Cleared {table}")
    except Exception as e:
        print(f"Error or not found {table}: {e}")

c.execute("PRAGMA foreign_keys = ON;")
conn.commit()
conn.close()
print("All badges and related data cleared successfully.")
