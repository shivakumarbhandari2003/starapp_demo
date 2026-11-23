"""
Tests for Cosmonaut Badges View and In-Card Expansion:
1. Sidebar option renamed to 'Badges'.
2. Initial allocated badge card in 3x3 grid showing strictly:
   - BAND B1
   - B1-SIG-01
   - Allocated Project
   - Tech › Data & Machine › Signals
   - Signals Foundations
   - And NOT 'Target Learning Outcomes'.
3. In-card expansion (NOT a popup modal) displaying all 6 sections:
   - Outcomes (with checkmarks)
   - Earn the badge (Allocated Milestone)
   - Practice project (with prompt and copy)
   - Learning topics (with 6 modules and progress bar)
   - Learning resources (with prompt and copy)
   - Related skills, capabilities, powers
   - Below it: Project Deliverable Submission Portal.
4. Toggling collapses back to the clean initial card view.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from starapp.app import StarAppController
from starapp.storage import store

class TestCosmonautBadgesView(unittest.TestCase):
    def setUp(self):
        self.ctrl = StarAppController()
        self.ctrl.initialize()

    def test_sidebar_option_renamed_to_badges(self):
        """Verify sidebar option is renamed from 'Project Submission' to 'Badges'."""
        self.ctrl.handle_event("select_demo_account", "m_b1_1")
        sidebar_html = self.ctrl.render()
        self.assertIn("Badges", sidebar_html)
        self.assertNotIn(">Project Submission<", sidebar_html)

    def test_allocated_badges_initial_collapsed_card_view(self):
        """Verify mapped cosmonaut (m_b1_1 / Aarav) sees clean collapsed card in 3x3 grid without Target Learning Outcomes."""
        self.ctrl.handle_event("select_demo_account", "m_b1_1")
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")
        html = self.ctrl.render()

        # Check Page Title / Header
        self.assertIn("Allocated Badges &amp; Milestone Projects", html)
        self.assertIn("badges-grid-3x3", html)

        # Check Initial Card specific elements
        self.assertIn("BAND B1", html)
        self.assertIn("B1-SIG-01", html)
        self.assertIn("Allocated Project", html)
        self.assertIn("Signals Foundations", html)
        self.assertIn("Signals", html)
        self.assertIn("Data &amp; Machine", html)
        self.assertIn("Tech", html)

        # Strictly verify 'Target Learning Outcomes' is NOT present in the collapsed card view
        self.assertNotIn("Target Learning Outcomes", html)

        # Verify Submission Portal is NOT statically embedded below (pops up as dedicated modal)
        self.assertNotIn("Project Deliverable Submission Portal", html)

    def test_other_mapped_cosmonauts_see_allocated_badge_in_clean_card(self):
        """Verify other cosmonauts in the mapping (m_b1_2, m_b1_3, m_b1_4, m_b1_5) also see the clean collapsed badge card."""
        for cid in ["m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5"]:
            self.ctrl.handle_event("select_demo_account", cid)
            self.ctrl.handle_event("nav_cosmonaut", "c_submission")
            html = self.ctrl.render()
            self.assertIn("Signals Foundations", html, f"Cosmonaut {cid} should see allocated Signals Foundations badge")
            self.assertIn("BAND B1", html)
            self.assertIn("Allocated Project", html)
            self.assertNotIn("Target Learning Outcomes", html)

    def test_cosmonaut_badge_card_expands_inside_card_not_modal(self):
        """Verify clicking on badge expands all 6 sections inside the card, NOT as a popup modal."""
        self.ctrl.handle_event("select_demo_account", "m_b1_1")
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")

        # Dispatch card toggle
        self.ctrl.handle_event("toggle_cosmonaut_badge_card", "badge_b1_signals")

        # Crucial check: MUST NOT open a popup modal!
        self.assertIsNone(self.ctrl.active_modal)
        self.assertEqual(self.ctrl.cosmonaut_expanded_badge_id, "badge_b1_signals")

        html = self.ctrl.render()

        # In-card expanded wrapper checks
        self.assertIn("expanded-badge-card", html)
        self.assertIn("grid-column: 1 / -1", html)

        # Location Breadcrumb Chips inside the card
        self.assertIn("Badge Location", html)
        self.assertIn("Signals Foundations", html)
        self.assertIn("Signals", html)
        self.assertIn("Data &amp; Machine", html)
        self.assertIn("Tech", html)
        self.assertIn("Band B1", html)

        # Section 1: Outcomes (inside card)
        self.assertIn("badge-section-outcomes", html)
        self.assertIn("Outcomes (4)", html)
        self.assertIn("✓", html)

        # Section 2: Earn the Badge (inside card)
        self.assertIn("badge-section-earn", html)
        self.assertIn("Earn the Badge", html)
        self.assertIn("Allocated Milestone", html)

        # Section 3: Practice Project (inside card)
        self.assertIn("badge-section-practice", html)
        self.assertIn("Practice Project", html)
        self.assertIn("practice-prompt-text", html)
        self.assertIn("Want some hands-on practice?", html)

        # Section 4: Learning Topics (inside card)
        self.assertIn("badge-section-topics", html)
        self.assertIn("Learning Topics", html)
        self.assertIn("Curriculum Module", html)
        self.assertIn("topic-toggle-btn-0", html)
        self.assertIn("topics-progress-bar", html)

        # Section 5: Learning Resources (inside card)
        self.assertIn("badge-section-resources", html)
        self.assertIn("Learning Resources", html)
        self.assertIn("resources-prompt-text", html)

        # Section 6: Related Skills, Capabilities & Powers (inside card)
        self.assertIn("badge-section-related", html)
        self.assertIn("Related Skills, Capabilities &amp; Powers", html)

        # Card action to collapse and portal submission link
        self.assertIn("Collapse Badge Details", html)
        self.assertIn("Submit Deliverables for this Badge", html)

        # Below the grid: Deliverable Submission Portal is NOT statically embedded
        self.assertNotIn("Project Deliverable Submission Portal", html)

        # Clicking 'Submit Deliverables for this Badge' opens the dedicated modal popup
        self.ctrl.handle_event("open_submission_modal", "badge_b1_signals")
        self.assertEqual(self.ctrl.active_modal, "submission_portal_modal")
        modal_html = self.ctrl.render()
        self.assertIn("Project Deliverable Submission Portal", modal_html)

    def test_cosmonaut_badge_card_collapses_back_on_toggle(self):
        """Verify clicking toggle again collapses the expanded badge card back to compact view."""
        self.ctrl.handle_event("select_demo_account", "m_b1_1")
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")

        # First click: expand
        self.ctrl.handle_event("toggle_cosmonaut_badge_card", "badge_b1_signals")
        self.assertEqual(self.ctrl.cosmonaut_expanded_badge_id, "badge_b1_signals")

        # Second click: collapse
        self.ctrl.handle_event("toggle_cosmonaut_badge_card", "badge_b1_signals")
        self.assertIsNone(self.ctrl.cosmonaut_expanded_badge_id)

        html = self.ctrl.render()
        self.assertIn("collapsed-badge-card", html)
        self.assertNotIn("expanded-badge-card", html)
        self.assertNotIn("badge-section-outcomes", html)
        self.assertNotIn("Target Learning Outcomes", html)
