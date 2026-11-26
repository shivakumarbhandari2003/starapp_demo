"""
Unit & Integration Test Suite:
1. Reviewer-Cosmonaut Role Isolation:
   - Reviewer mapped to 4 cadets sees ONLY their 4 mapped cadets, NOT all 7 cohort cadets.
2. Hierarchical Badge Reviews UI:
   - Level 1 Badge Name Card -> Level 2/3 Dedicated Cadet Card matching UI.
   - Expand/collapse toggle via toggle_reviewer_badge_expand.
3. Lifecycle state progression:
   - 3-Day Prep -> Project Given -> Submitted -> Evaluated (50-mark) -> Awarded.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starapp.storage import store
from starapp.app import StarAppController
from starapp.models import Badge, BadgeTimeline, ProjectSubmission, AssessmentMarksheet


class TestReviewerCosmonautIsolationAndSchedule(unittest.TestCase):
    def setUp(self):
        self.app = StarAppController()
        self.app.initialize()

        self.rev_a = store.users.get("m_b5_1")  # Anirudh Krishnan (Band 5)
        self.rev_b = store.users.get("m_b6_1")  # Kavita Raman (Band 6)
        self.guardian = store.users.get("guardian_1")

        # 4 cadets for Reviewer A
        self.cadets_a = ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4"]
        # 2 cadets for Reviewer B
        self.cadets_b = ["m_b1_5", "m_b1_6"]

        self.badge = Badge(
            id="badge_ai_os_arch_b4",
            code="B4-AI--01",
            title="AI-OS Architecture",
            target_band="B4",
            category="Data & Machine / AI-OS",
            description="Foundational architecture of AI operating systems.",
            learning_outcomes=["Identify CPU, memory, storage, and GPU components in a given system spec"],
            learning_topics=["Kernel Architecture", "GPU Scheduling"],
            prerequisites=[],
            project_requirements="Design multi-tenant kernel scheduler",
            power="Tech",
            capability="Data & Machine",
            skill="AI-OS",
            is_published=True,
            is_allocated=True
        )
        store.save_badge(self.badge)

        # Clear existing timelines/mappings/projects for this test badge
        cur = store.db.conn.cursor()
        cur.execute("DELETE FROM assessment_marksheets WHERE badge_id = ?", (self.badge.id,))
        cur.execute("DELETE FROM project_submissions WHERE badge_id = ?", (self.badge.id,))
        cur.execute("DELETE FROM reviewer_project_prompts WHERE badge_id = ?", (self.badge.id,))
        cur.execute("DELETE FROM badge_timelines WHERE badge_id = ?", (self.badge.id,))
        cur.execute("DELETE FROM band_mappings WHERE badge_id = ? OR id LIKE ?", (self.badge.id, f"%{self.badge.id}%"))
        store.db.conn.commit()

        store.timelines = {k: tl for k, tl in store.timelines.items() if getattr(tl, "badge_id", "") != self.badge.id}
        store.reviewer_projects = {k: p for k, p in store.reviewer_projects.items() if getattr(p, "badge_id", "") != self.badge.id}
        store.submissions = {k: s for k, s in store.submissions.items() if getattr(s, "badge_id", "") != self.badge.id}
        store.assessments = {k: a for k, a in store.assessments.items() if getattr(a, "badge_id", "") != self.badge.id}

        # Setup 2 band mappings: Mapping A (rev_a with 4 cadets), Mapping B (rev_b with 3 cadets)
        store.save_band_mapping({
            "id": f"map_{self.badge.id}_a",
            "band": "B4",
            "badge": self.badge.title,
            "badge_id": self.badge.id,
            "reviewers": [self.rev_a.id],
            "cosmonauts": self.cadets_a,
            "review_dates": ["2026-11-18", "2026-11-19", "2026-11-20"],
            "status": "active"
        })
        store.save_band_mapping({
            "id": f"map_{self.badge.id}_b",
            "band": "B4",
            "badge": self.badge.title,
            "badge_id": self.badge.id,
            "reviewers": [self.rev_b.id],
            "cosmonauts": self.cadets_b,
            "review_dates": ["2026-11-18", "2026-11-19", "2026-11-20"],
            "status": "active"
        })

    def test_reviewer_cosmonaut_isolation_and_count(self):
        # 1. Reviewer A logs in: must see strictly 4 cadets, none from cadets_b
        self.app.handle_event("select_demo_account", self.rev_a.id)
        self.app.handle_event("nav_cosmonaut", "c_badge_reviews")

        # By default for multiple cadets, starts with Level 1 badge card
        html_collapsed = self.app.render()
        self.assertIn("Badge Review Schedule", html_collapsed)
        self.assertIn("B4-AI--01", html_collapsed)
        self.assertIn("BAND B4", html_collapsed)
        self.assertIn("AI-OS Architecture", html_collapsed)
        self.assertIn("4 Mapped Cadets", html_collapsed)

        # 2. Toggle expand Level 1 card
        self.app.handle_event("toggle_reviewer_badge_expand", self.badge.id)
        html_expanded = self.app.render()

        # Check all 4 cadets of Reviewer A are present
        for cid in self.cadets_a:
            c_user = store.users.get(cid)
            self.assertIn(c_user.name, html_expanded, f"Cadet {c_user.name} must appear in Reviewer A schedule")

        # Check NONE of Reviewer B cadets are present in Reviewer A schedule
        for cid in self.cadets_b:
            c_user = store.users.get(cid)
            self.assertNotIn(c_user.name, html_expanded, f"Cadet {c_user.name} must NOT appear in Reviewer A schedule")

        # Dedicated cadet card: one compact row per cadet (the badge header is not repeated inside it)
        self.assertIn("3-Day Project Preparation", html_expanded)
        self.assertIn("Review Window:", html_expanded)
        self.assertIn("Submission Deadline:", html_expanded)
        self.assertNotIn("Reviewer creates project, Cadet learns concepts", html_expanded)  # removed boilerplate
        self.assertIn("View Timeline", html_expanded)
        self.assertIn("Create Project (AI)", html_expanded)
        self.assertIn("Cadet Assessments", html_expanded)

        # 3. Reviewer B logs in: must see strictly 3 cadets, none from cadets_a
        self.app.handle_event("select_demo_account", self.rev_b.id)
        self.app.handle_event("nav_cosmonaut", "c_badge_reviews")
        self.app.handle_event("toggle_reviewer_badge_expand", self.badge.id)
        html_b = self.app.render()

        self.assertIn("2 Mapped Cadets", html_b)
        for cid in self.cadets_b:
            c_user = store.users.get(cid)
            self.assertIn(c_user.name, html_b, f"Cadet {c_user.name} must appear in Reviewer B schedule")

        for cid in self.cadets_a:
            c_user = store.users.get(cid)
            self.assertNotIn(c_user.name, html_b, f"Cadet {c_user.name} must NOT appear in Reviewer B schedule")

    def test_lifecycle_progression_in_reviewer_schedule(self):
        # 1. Start: Reviewer A sees 3-Day Prep & Create Project (AI)
        self.app.handle_event("select_demo_account", self.rev_a.id)
        self.app.handle_event("nav_cosmonaut", "c_badge_reviews")
        self.app.handle_event("toggle_reviewer_badge_expand", self.badge.id)
        html1 = self.app.render()
        self.assertIn("3-Day Project Preparation", html1)
        self.assertIn("Create Project (AI)", html1)

        # 2. Reviewer A authors and releases project
        create_payload = {
            "badge_id": self.badge.id,
            "title": "Scalable AI Kernel Engine",
            "objective": "Build a multi-tenant kernel scheduler for AI inference workloads.",
            "submission_deadline": "2026-11-20",
            "status": "released",
            "cosmonaut_ids": self.cadets_a
        }
        self.app.handle_event("save_reviewer_project_prompt", create_payload)

        # In Reviewer A schedule, status becomes Project Given & button becomes Edit Project
        html2 = self.app.render()
        self.assertIn("Project Given", html2)
        self.assertIn("Edit Project", html2)

        # 3. First Cadet submits deliverables
        cadet_1 = self.cadets_a[0]
        self.app.handle_event("select_demo_account", cadet_1)
        self.app.handle_event("submit_project_deliverables", {
            "badge_id": self.badge.id,
            "github_url": "https://github.com/starapp/ai-os-kernel",
            "pdf_filename": "ai_kernel_spec.pdf",
            "code_filename": "scheduler.py",
            "source_code": "class KernelScheduler:\n    pass"
        })

        # 4. Reviewer A views schedule: Cadet 1 shows "Deliverables Submitted" and "Inspect Deliverables & Allocate Marks"
        self.app.handle_event("select_demo_account", self.rev_a.id)
        self.app.handle_event("nav_cosmonaut", "c_badge_reviews")
        self.app.handle_event("toggle_reviewer_badge_expand", self.badge.id)
        html3 = self.app.render()
        self.assertIn("Deliverables Submitted", html3)
        self.assertIn("Inspect Deliverables", html3)

        # 5. Reviewer evaluates deliverables
        submissions = store.get_submissions_for_cosmonaut(cadet_1, self.badge.id)
        sub = submissions[-1]
        eval_payload = {
            "submission_id": sub.id,
            "assessor_role": "reviewer",
            "bu": 9.5,
            "ar": 9.0,
            "tk": 9.5,
            "pr": 9.0,
            "qa": 9.0,
            "feedback": "Outstanding architecture design."
        }
        self.app.handle_event("submit_reviewer_assessment", eval_payload)

        # In Reviewer A schedule, status becomes Evaluated: 46.0/50 and button becomes View Marksheet
        self.app.handle_event("nav_cosmonaut", "c_badge_reviews")
        html4 = self.app.render()
        self.assertIn("Evaluated: 46.0/50", html4)
        self.assertIn("View Marksheet (46.0/50)", html4)


if __name__ == "__main__":
    unittest.main()
