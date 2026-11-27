"""
Tests for Cosmonaut Badges View and Dedicated Badge Detail Page:
1. Sidebar option renamed to 'Badges' (and stays highlighted on c_badge_detail).
2. Initial allocated badge card in 3x3 grid showing strictly:
   - BAND B1
   - B1-SIG-01
   - Allocated Badge (or Project Allocated once the reviewer sends the project)
   - Tech › Data & Machine › Signals
   - Signals Foundations
   - And NOT 'Target Learning Outcomes', 'ASSIGNED PROJECT SPECIFICATION', or embedded Submission Portal.
3. Clicking a badge card opens a separate dedicated page ('c_badge_detail'), NOT inline in-card expansion
   and NOT a popup modal, displaying all badge curriculum sections cleanly with Back to Badges navigation.
4. When the mapped reviewer creates & releases a project for the badge:
   - The badge's 'Earn the Badge' section renders a 'Project allocated' button.
   - Clicking 'Project allocated' opens the allocated project viewer modal showing the reviewer's project details.
   - Clicking 'Submit Deliverables' opens the submission popup modal window, and submitting triggers the next review workflow.
5. Navigating back ('Back to Badges' / 'nav_cosmonaut' c_submission) returns cleanly to the compact cards grid.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import unittest
from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import ReviewerProjectPrompt, current_iso_timestamp


class TestCosmonautBadgesView(unittest.TestCase):
    def setUp(self):
        self.ctrl = StarAppController()
        self.ctrl.initialize()
        if not store.get_badge("badge_b1_signals"):
            store.load_from_json(None)
            self.ctrl = StarAppController()
            self.ctrl.initialize()

        # Ensure clean baseline for badge_b1_signals prompts/submissions for m_b1_1 during UI tests
        if store.db and store.db.conn:
            store.db.conn.execute("DELETE FROM reviewer_project_prompts WHERE badge_id = 'badge_b1_signals'")
            store.db.conn.execute("DELETE FROM assessment_marksheets WHERE cosmonaut_id = 'm_b1_1' AND badge_id = 'badge_b1_signals'")
            store.db.conn.execute("DELETE FROM project_submissions WHERE cosmonaut_id = 'm_b1_1' AND badge_id = 'badge_b1_signals'")
            store.db.conn.commit()
        store.reviewer_projects = {
            k: v for k, v in getattr(store, "reviewer_projects", {}).items()
            if getattr(v, "badge_id", "") != "badge_b1_signals"
        }
        store.submissions = {
            k: v for k, v in store.submissions.items()
            if not (v.cosmonaut_id == "m_b1_1" and v.badge_id == "badge_b1_signals")
        }
        store.assessments = {
            k: v for k, v in store.assessments.items()
            if not (v.cosmonaut_id == "m_b1_1" and v.badge_id == "badge_b1_signals")
        }

    def tearDown(self):
        if store.db and store.db.conn:
            store.db.conn.execute("DELETE FROM reviewer_project_prompts WHERE badge_id = 'badge_b1_signals'")
            store.db.conn.execute("DELETE FROM assessment_marksheets WHERE cosmonaut_id = 'm_b1_1' AND badge_id = 'badge_b1_signals'")
            store.db.conn.execute("DELETE FROM project_submissions WHERE cosmonaut_id = 'm_b1_1' AND badge_id = 'badge_b1_signals'")
            store.db.conn.commit()
        store.reviewer_projects = {
            k: v for k, v in getattr(store, "reviewer_projects", {}).items()
            if getattr(v, "badge_id", "") != "badge_b1_signals"
        }
        store.submissions = {
            k: v for k, v in store.submissions.items()
            if not (v.cosmonaut_id == "m_b1_1" and v.badge_id == "badge_b1_signals")
        }
        store.assessments = {
            k: v for k, v in store.assessments.items()
            if not (v.cosmonaut_id == "m_b1_1" and v.badge_id == "badge_b1_signals")
        }

    def test_sidebar_option_renamed_to_badges(self):
        """Verify sidebar option is renamed from 'Project Submission' to 'Badges'."""
        self.ctrl.handle_event("select_demo_account", "m_b1_1")
        sidebar_html = self.ctrl.render()
        self.assertIn("Badges", sidebar_html)
        self.assertNotIn(">Project Submission<", sidebar_html)

    def test_allocated_badges_initial_collapsed_card_view(self):
        """Verify mapped cosmonaut (m_b1_1 / Aarav) sees clean collapsed card in 3x3 grid without Target Learning Outcomes or banner clutter."""
        self.ctrl.handle_event("select_demo_account", "m_b1_1")
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")
        html = self.ctrl.render()

        # Check Page Title / Header
        self.assertIn("Allocated Badges &amp; Milestone Projects", html)
        self.assertIn("badges-grid-3x3", html)

        # Check Initial Card specific elements
        self.assertNotIn("BAND B1", html)                       # no band / code chips and no skill tree on the card
        self.assertNotIn("B1-SIG-01", html)
        self.assertNotIn("Skill :", html)
        self.assertIn("Allocated Badge", html)
        self.assertIn("Signals Foundations", html)
        self.assertIn("open_cosmonaut_badge_page", html)

        # Strictly verify 'Target Learning Outcomes' and inline banners are NOT present in the collapsed grid view
        self.assertNotIn("Target Learning Outcomes", html)
        self.assertNotIn("ASSIGNED PROJECT SPECIFICATION", html)

        # Verify Submission Portal is NOT statically embedded below (pops up as dedicated modal)
        self.assertNotIn("Project Deliverable Submission Portal", html)

    def test_other_mapped_cosmonauts_see_allocated_badge_in_clean_card(self):
        """Verify other cosmonauts in the mapping (m_b1_2, m_b1_3, m_b1_4, m_b1_5) also see the clean collapsed badge card."""
        for cid in ["m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5"]:
            self.ctrl.handle_event("select_demo_account", cid)
            self.ctrl.handle_event("nav_cosmonaut", "c_submission")
            html = self.ctrl.render()
            self.assertIn("Signals Foundations", html, f"Cosmonaut {cid} should see allocated Signals Foundations badge")
            self.assertNotIn("BAND B1", html)
            self.assertIn("Allocated Badge", html)
            self.assertNotIn("Target Learning Outcomes", html)

    def test_clicking_badge_opens_dedicated_badge_page_with_project_and_deliverables_modal(self):
        """Verify clicking a badge navigates to c_badge_detail page (not inline grid expansion), shows all sections, Project allocated modal, and Submit Deliverables popup."""
        self.ctrl.handle_event("select_demo_account", "m_b1_1")
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")

        # Click badge card -> navigates to dedicated badge detail page
        self.ctrl.handle_event("open_cosmonaut_badge_page", "badge_b1_signals")
        self.assertEqual(self.ctrl.current_view, "c_badge_detail")
        self.assertEqual(self.ctrl.cosmonaut_submission_badge_id, "badge_b1_signals")
        self.assertIsNone(self.ctrl.active_modal)

        html = self.ctrl.render()

        # Standalone badge page wrapper (NOT inline grid expansion inside badges-grid-3x3)
        self.assertIn("cbp-page", html)
        self.assertNotIn("badges-grid-3x3", html)
        self.assertNotIn("expanded-badge-card", html)
        # no page-level back row / workspace line / chips / description / reviewer banner - the top Back button is enough
        for gone in ("Back to Badges", "Back to All Badges", "Badge Workspace", "Assigned Peer Reviewer", "specializing in"):
            self.assertNotIn(gone, html)
        # the badge name carries two buttons on its right: the mapped Reviewer and the Timeline
        self.assertIn("open_cosmonaut_reviewer_modal", html)
        self.assertIn("open_cosmonaut_timeline_modal", html)

        # Location Breadcrumb Chips inside the dedicated page
        self.assertIn("Badge Location", html)
        self.assertIn("Signals Foundations", html)
        self.assertIn("Signals", html)
        self.assertIn("Data &amp; Machine", html)
        self.assertIn("Tech", html)
        self.assertIn("Band B1", html)

        # Section 1: Outcomes
        self.assertIn("badge-section-outcomes", html)
        self.assertIn("Outcomes (4)", html)
        # Emoji / dingbat glyphs are rendered as professional vector icons (iconize_html), never as raw characters
        outcomes_html = html.split("badge-section-outcomes", 1)[1][:6000]
        self.assertIn("<svg", outcomes_html)
        self.assertNotIn("✓", html)

        # Section 2: Earn the Badge (before project allocation)
        self.assertIn("badge-section-earn", html)
        self.assertIn("Earn the Badge", html)
        self.assertIn("pa-btn is-locked", html)                     # no project yet: "Project Allocated" is shown, DISABLED
        self.assertIn("Project Allocated", html)
        self.assertNotIn("Request Project", html)                   # nothing to request - the reviewer creates and sends it
        self.assertNotIn("Allocated Milestone", html)
        self.assertNotIn("Submit Project Deliverables", html)
        self.assertIn("btn-project-allocated-badge_b1_signals", html)    # the (locked) Project Allocated button

        # Section 3-6: Curriculum sections
        self.assertIn("badge-section-practice", html)
        self.assertIn("Practice Project", html)
        self.assertIn("practice-prompt-text", html)
        self.assertIn("badge-section-topics", html)
        self.assertIn("Learning Topics", html)
        self.assertIn("topic-toggle-btn-0", html)
        self.assertIn("topics-progress-bar", html)
        self.assertIn("badge-section-resources", html)
        self.assertIn("Learning Resources", html)
        self.assertIn("badge-section-related", html)
        self.assertIn("Related Skills, Capabilities &amp; Powers", html)

        # Page footer navigation & deliverable popup trigger
        self.assertNotIn("Back to All Badges", html)
        self.assertNotIn("Submit Deliverables for this Badge", html)
        self.assertNotIn("Project Deliverable Submission Portal", html)

        # The cosmonaut requests the project: the request goes to the mapped reviewer
        self.ctrl.handle_event("request_project", "badge_b1_signals")
        self.assertEqual(self.ctrl.flash_type, "success")
        self.assertIn("pa-btn is-locked", self.ctrl.render())          # still locked: the cosmonaut only waits for the reviewer
        self.assertEqual([r.badge_id for r in store.get_pending_project_requests("m_b2_1")], ["badge_b1_signals"])

        # Now mapped reviewer creates & releases a project for this badge
        rev = store.get_user_by_id("m_b2_1")
        prompt = ReviewerProjectPrompt(
            badge_id="badge_b1_signals",
            reviewer_id="m_b2_1",
            reviewer_name=rev.name if rev else "Vikram Nair",
            cosmonaut_ids=["m_b1_1"],
            title="Real-Time Telemetry FFT Analyzer",
            description="Implement an enterprise FFT pipeline over noisy telemetry streams.",
            outcomes=["Compute normalized FFT power spectra", "Emit telemetry latency alerts"],
            requirements=["Python DSP module with numpy/stdlib", "PDF architecture report"],
            deliverables={
                "code": {"name": "fft_analyzer.py", "description": "Core DSP script"},
                "pdf": {"name": "FFT_Architecture.pdf", "description": "Design spec PDF"},
                "github": {"name": "GitHub Repo", "description": "Repository URL"}
            },
            status="released",
            created_at=current_iso_timestamp(),
            sent_at=current_iso_timestamp()
        )
        store.save_reviewer_project_prompt(prompt)

        # On c_submission grid: badge card shows 'Project Allocated', but full project view stays inside that badge only
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")
        grid_html = self.ctrl.render()
        self.assertIn("Project Allocated", grid_html)
        self.assertNotIn("Real-Time Telemetry FFT Analyzer", grid_html)

        # Inside dedicated badge page (c_badge_detail): 'Project allocated' button is shown in Earn the Badge section + project view renders
        self.ctrl.handle_event("open_cosmonaut_badge_page", "badge_b1_signals")
        detail_with_proj_html = self.ctrl.render()
        self.assertIn("pa-btn is-ready", detail_with_proj_html)                  # the locked button unlocked ...
        self.assertNotIn("pa-btn is-locked", detail_with_proj_html)
        self.assertNotIn("Submit Deliverables", detail_with_proj_html)           # ... Submit Deliverables lives ONLY inside the project
        self.assertNotIn("Request Project", detail_with_proj_html)
        self.assertNotIn("Real-Time Telemetry FFT Analyzer", detail_with_proj_html)   # the project itself is not shown inside the badge
        self.assertNotIn("Implement an enterprise FFT pipeline", detail_with_proj_html)

        # Clicking 'Project allocated' opens the whole project as its OWN PAGE (no popup)
        self.ctrl.handle_event("open_allocated_project_page", "badge_b1_signals")
        self.assertEqual(self.ctrl.current_view, "c_project")
        self.assertIsNone(self.ctrl.active_modal)
        proj_page_html = self.ctrl.render()
        self.assertIn("Real-Time Telemetry FFT Analyzer", proj_page_html)
        self.assertIn("Compute normalized FFT power spectra", proj_page_html)
        self.assertIn("Sent by", proj_page_html)
        self.assertIn("Submit Deliverables", proj_page_html)

        # Clicking 'Submit Deliverables' opens the deliverable submission popup window (just the fields; the project is on the page behind it)
        self.ctrl.handle_event("open_submission_modal", "badge_b1_signals")
        self.assertEqual(self.ctrl.active_modal, "submission_portal_modal")
        modal_html = self.ctrl.render_active_modal()
        self.assertIn("Submit your deliverables", modal_html)
        self.assertLess(modal_html.index("submission-pdf-file"), modal_html.index("submission-code-file"))
        self.assertLess(modal_html.index("submission-code-file"), modal_html.index("submission-github-url"))

        # Submitting deliverables closes modal, stays on badge page, routes to reviewer, and transitions status
        self.ctrl.handle_event("submit_project_deliverable", json.dumps({
            "badge_id": "badge_b1_signals",
            "pdf_name": "FFT_Architecture.pdf",
            "pdf_payload": "data/sample.pdf",
            "code_name": "fft_analyzer.py",
            "code_payload": "def analyze(): return 'ok'",
            "github_url": "https://github.com/starapp/fft-analyzer"
        }))
        self.assertIsNone(self.ctrl.active_modal)
        self.assertEqual(self.ctrl.current_view, "c_project")                  # still on the project page, now showing the submission
        after_sub_html = self.ctrl.render()
        self.assertIn("Submitted", after_sub_html)
        self.assertIn("FFT_Architecture.pdf", after_sub_html)
        self.assertIn("Edit Deliverables", after_sub_html)
        self.ctrl.handle_event("go_back")
        self.ctrl.handle_event("open_cosmonaut_badge_page", "badge_b1_signals")
        badge_html = self.ctrl.render()                                        # the badge page shows the status, never the project
        self.assertIn("Pending reviewer evaluation", badge_html)
        self.assertIn("Project Allocated", badge_html)

    def test_back_to_badges_returns_from_detail_page_to_grid(self):
        """Verify Back to Badges / nav_cosmonaut c_submission returns cleanly from c_badge_detail to compact card grid."""
        self.ctrl.handle_event("select_demo_account", "m_b1_1")
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")

        # Open dedicated badge page
        self.ctrl.handle_event("open_cosmonaut_badge_page", "badge_b1_signals")
        self.assertEqual(self.ctrl.current_view, "c_badge_detail")

        # Check region markers preserve portalKey & activeNavId='c_submission'
        regions = getattr(self.ctrl, "last_rendered_regions", None)
        if not regions:
            self.ctrl.render()
            regions = self.ctrl.last_rendered_regions
        self.assertEqual(regions["routeKey"], "c_badge_detail:badge_b1_signals")
        self.assertEqual(regions["activeNavId"], "c_submission")

        # Navigate back to Badges overview
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")
        self.assertEqual(self.ctrl.current_view, "c_submission")

        html = self.ctrl.render()
        self.assertIn("collapsed-badge-card", html)
        self.assertNotIn("cbp-page", html)
        self.assertNotIn("badge-section-outcomes", html)
        self.assertNotIn("Target Learning Outcomes", html)


if __name__ == "__main__":
    unittest.main()
