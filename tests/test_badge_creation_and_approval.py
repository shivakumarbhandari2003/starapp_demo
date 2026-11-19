"""
Test suite for StarApp Create Badge and Reviewer Badge Approval Workflows.
Verifies Band Selection, 4-Card Matrix, JSON Prompt Editor, Preview, Creation,
Reviewer Eligibility Filtering, Queue Display, Reviewer Edits, and Role Authorization.
"""

import unittest
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import User, Badge
from starapp.views_guardian import render_guardian_sidebar


class TestBadgeCreationAndApproval(unittest.TestCase):
    def setUp(self):
        self.ctrl = StarAppController()
        store.reset_to_seed()
        # Login as guardian
        self.ctrl.handle_event("select_demo_account", "guardian_1")

    def test_sidebar_navigation_order(self):
        """Verify Guardian sidebar has Create Badge and Reviewer Badge Approval at the top."""
        html = self.ctrl.render()
        self.assertIn("g_create_badge", html)
        self.assertIn("Create Badge", html)
        self.assertIn("g_badge_approval", html)
        self.assertIn("Reviewer Badge Approval", html)

        # Verify ordering: g_create_badge before g_badge_approval, and g_badge_approval before g_dashboard
        cb_idx = html.find('data-nav-id="g_create_badge"')
        ba_idx = html.find('data-nav-id="g_badge_approval"')
        db_idx = html.find('data-nav-id="g_dashboard"')
        self.assertTrue(0 < cb_idx < ba_idx < db_idx, "Sidebar items must be strictly ordered: Create Badge, Approval, Dashboard")

    def test_band_selection_view(self):
        """Verify navigating to g_create_badge without a selected band renders 6 band cards."""
        self.ctrl.handle_event("nav_guardian", "g_create_badge")
        self.assertEqual(self.ctrl.current_view, "g_create_badge")
        html = self.ctrl.render()

        self.assertIn("Select a band to configure a new badge", html)
        for b in ["B1", "B2", "B3", "B4", "B5", "B6"]:
            self.assertIn(f"BAND {b}", html)
            self.assertIn(f"select_create_badge_band', '{b}'", html)

    def test_band_specific_create_badge_workspace_and_4_cards(self):
        """Verify selecting a band renders 4 selection cards and structured JSON prompt editor."""
        self.ctrl.handle_event("nav_guardian", "g_create_badge")
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.assertEqual(self.ctrl.create_badge_band, "B1")

        html = self.ctrl.render()
        self.assertIn("BAND B1", html)
        self.assertIn("Configure Badge", html)

        # Card 1: Powers
        self.assertIn("Select Power", html)
        self.assertIn("Tech", html)
        self.assertIn("Domain", html)
        self.assertIn("Leadership", html)

        # Card 2: Capabilities
        self.assertIn("Select Capability", html)
        self.assertTrue("Data &amp; Machine" in html or "Data & Machine" in html)
        self.assertIn("Reasoning", html)
        self.assertIn("custom-capability-input", html)

        # Card 3: Skills
        self.assertIn("Select Skill", html)
        self.assertIn("Hardware", html)
        self.assertIn("AI-OS", html)
        self.assertIn("custom-skill-input", html)

        # Card 4: Reviewer Selection
        self.assertIn("Select Higher-Band Reviewer", html)

        # Right Column: Prompt Editor
        self.assertIn("badge-prompt-editor", html)
        self.assertIn("learning_objectives", html)

    def test_higher_band_reviewer_eligibility_enforcement(self):
        """Verify higher-band reviewer rules: B1 has B2-B6; B5 has B6; B6 is locked out."""
        # B1: Eligible reviewers should be from B2, B3, B4, B5, B6
        revs_b1 = store.get_eligible_badge_reviewers("B1")
        self.assertTrue(len(revs_b1) > 0)
        for r in revs_b1:
            self.assertIn(r["band"], ["B2", "B3", "B4", "B5", "B6"])
            self.assertNotEqual(r["band"], "B1")

        # B5: Eligible reviewers should strictly be from B6
        revs_b5 = store.get_eligible_badge_reviewers("B5")
        self.assertTrue(len(revs_b5) > 0)
        for r in revs_b5:
            self.assertEqual(r["band"], "B6")

        # B6: No higher band reviewer exists
        revs_b6 = store.get_eligible_badge_reviewers("B6")
        self.assertEqual(len(revs_b6), 0)

        # Selecting B6 in UI displays lockout notice
        self.ctrl.handle_event("select_create_badge_band", "B6")
        html = self.ctrl.render()
        self.assertIn("No Higher-Band Reviewer Available", html)

    def test_custom_capability_and_skill_addition(self):
        """Verify Guardian can add custom capability and skill in controller."""
        self.ctrl.handle_event("select_create_badge_band", "B2")

        # Add custom capability
        self.ctrl.handle_event("add_custom_capability", "Autonomous Agents")
        self.assertEqual(self.ctrl.create_badge_capability, "Autonomous Agents")

        # Re-adding same capability should warn about duplicate
        self.ctrl.handle_event("add_custom_capability", "autonomous agents")
        self.assertEqual(self.ctrl.flash_type, "warning")

        # Add custom skill
        self.ctrl.handle_event("add_custom_skill", "Quantization Pruning")
        self.assertEqual(self.ctrl.create_badge_skill, "Quantization Pruning")

    def test_json_prompt_validation_and_preview(self):
        """Verify invalid JSON blocks preview, while valid JSON opens creation preview modal."""
        self.ctrl.handle_event("select_create_badge_band", "B1")

        # Select valid reviewer from higher band
        revs = store.get_eligible_badge_reviewers("B1")
        self.ctrl.handle_event("select_badge_reviewer", revs[0]["id"])

        # Set invalid JSON prompt
        self.ctrl.handle_event("update_badge_prompt", "{ invalid json: true ")
        self.assertIsNotNone(self.ctrl.create_badge_json_error)

        # Attempt preview with invalid JSON
        self.ctrl.handle_event("preview_new_badge", {
            "code": "B1-TST-01",
            "title": "Hardware Validation",
            "prompt_json": "{ invalid json: true "
        })
        self.assertIsNone(self.ctrl.active_modal, "Preview modal must not open on invalid JSON")
        self.assertEqual(self.ctrl.flash_type, "error")

        # Set valid JSON prompt
        valid_json = json.dumps({
            "prompt": "Construct a hardware acceleration pipeline.",
            "learning_objectives": ["Analyze GPU compute", "Optimize PCIe bus"],
            "expected_outcomes": ["Specification doc"],
            "evaluation_focus": ["Accuracy"]
        })
        self.ctrl.handle_event("update_badge_prompt", valid_json)
        self.assertIsNone(self.ctrl.create_badge_json_error)

        # Trigger preview
        self.ctrl.handle_event("preview_new_badge", {
            "code": "B1-TST-01",
            "title": "Hardware Validation",
            "prompt_json": valid_json
        })
        self.assertEqual(self.ctrl.active_modal, "badge_creation_preview")

    def test_badge_creation_lifecycle_and_pending_review_status(self):
        """Verify creating a badge persists in SQLite with pending_review status and notifies reviewer."""
        self.ctrl.handle_event("select_create_badge_band", "B1")
        revs = store.get_eligible_badge_reviewers("B1")
        reviewer_id = revs[0]["id"]
        self.ctrl.handle_event("select_badge_reviewer", reviewer_id)

        valid_json = json.dumps({
            "prompt": "Test hardware instruction specification.",
            "learning_objectives": ["Identify system registers"],
            "expected_outcomes": ["Register mapping chart"],
            "evaluation_focus": ["Technical correctness"]
        })

        self.ctrl.handle_event("preview_new_badge", {
            "code": "B1-REG-01",
            "title": "Processor Registers",
            "prompt_json": valid_json
        })

        # Confirm creation
        self.ctrl.handle_event("create_badge", "{}")
        self.assertEqual(self.ctrl.current_view, "g_badge_approval")

        # Verify badge persisted in store / SQLite
        created = [b for b in store.get_all_badges() if b.code.startswith("B1-REG-01")]
        self.assertTrue(len(created) > 0, "Created badge must exist in database")
        b = created[0]
        self.assertEqual(b.workflow_status, "pending_review")
        self.assertFalse(b.is_published, "Badge must NOT be automatically published")
        self.assertFalse(b.is_allocated, "Badge must NOT be automatically allocated")
        self.assertEqual(b.creator_id, "guardian_1")
        self.assertEqual(b.assigned_reviewer_id, reviewer_id)

        # Verify notification sent to reviewer
        rev_notifs = store.get_notifications(reviewer_id)
        self.assertTrue(any("review" in n.title.lower() or "review" in n.message.lower() for n in rev_notifs))

    def test_reviewer_badge_approval_queue_display(self):
        """Verify g_badge_approval workspace lists pending badges and filter tabs."""
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        html = self.ctrl.render()
        self.assertIn("Reviewer Badge Approval", html)
        self.assertIn("Pending Review", html)
        self.assertIn("Approved", html)

    def test_reviewer_authorization_and_approval_flow(self):
        """Verify only an authorized reviewer can approve, and approval updates workflow_status without publishing."""
        # 1. Create a badge for B2 assigned to Aarav Sharma (m_b3_3)
        self.ctrl.handle_event("select_create_badge_band", "B2")
        self.ctrl.handle_event("select_badge_reviewer", "m_b3_3")
        valid_json = json.dumps({
            "prompt": "Design microservices router.",
            "learning_objectives": ["Build RPC interface"],
            "expected_outcomes": ["Working demo"],
            "evaluation_focus": ["Scalability"]
        })
        self.ctrl.handle_event("preview_new_badge", {
            "code": "B2-RPC-01",
            "title": "RPC Service Mesh",
            "prompt_json": valid_json
        })
        self.ctrl.handle_event("create_badge", "{}")

        created = [b for b in store.get_all_badges() if b.code.startswith("B2-RPC-01")]
        self.assertTrue(len(created) > 0)
        badge = created[0]
        self.assertEqual(badge.workflow_status, "pending_review")

        # 2. Guardian attempts direct approval -> should fail authorization check (only badge_reviewer role allowed)
        self.ctrl.handle_event("approve_submitted_badge", badge.id)
        self.assertEqual(self.ctrl.flash_type, "error")
        self.assertEqual(badge.workflow_status, "pending_review")

        # 3. Switch login to Aarav Sharma (m_b3_3, Badge Reviewer)
        self.ctrl.handle_event("select_demo_account", "m_b3_3")
        self.assertEqual(self.ctrl.current_user.id, "m_b3_3")
        self.assertTrue(self.ctrl.current_user.has_role("badge_reviewer"))

        # 4. Reviewer edits the badge proposal -> status remains pending_review
        self.ctrl.handle_event("save_reviewed_badge", {
            "badge_id": badge.id,
            "title": "RPC Service Mesh (Enhanced Specification)",
            "prompt_json": valid_json
        })
        updated_badge = store.get_badge(badge.id)
        self.assertEqual(updated_badge.workflow_status, "pending_review")
        self.assertIn("Enhanced", updated_badge.title)

        # 5. Reviewer approves the badge
        self.ctrl.handle_event("approve_submitted_badge", badge.id)
        self.assertEqual(self.ctrl.flash_type, "success")
        approved_badge = store.get_badge(badge.id)
        self.assertEqual(approved_badge.workflow_status, "approved")
        self.assertFalse(approved_badge.is_published, "Approved badge must remain unpublished until explicit publishing")
        self.assertFalse(approved_badge.is_allocated, "Approved badge must remain unallocated")

        # 6. Verify Guardian received approval notification
        guardian_notifs = store.get_notifications("guardian_1")
        self.assertTrue(any("approved" in n.title.lower() or "approved" in n.message.lower() for n in guardian_notifs))

    def test_cascading_dropdowns_and_outcome_sentence(self):
        """Verify 3 cascading dropdowns (Power, Capability, Skill) and default outcome sentence for Band 1."""
        self.ctrl.handle_event("select_create_badge_band", "B1")
        html = self.ctrl.render()

        # Check dropdown IDs exist in rendered view
        self.assertIn('id="badge-power-select"', html)
        self.assertIn('id="badge-capability-select"', html)
        self.assertIn('id="badge-skill-select"', html)
        self.assertIn('id="badge-outcome-sentence-input"', html)
        self.assertIn('id="create-badge-gemini-btn"', html)

        # Verify Band 1 default outcome sentence
        self.assertIn("Identify CPU, memory, storage, and GPU components in a given system spec and describe their basic roles", html)

        # Switch capability to 'Reasoning' -> skills should filter to Reasoning skills
        self.ctrl.handle_event("change_badge_capability", "Reasoning")
        self.assertEqual(self.ctrl.create_badge_capability, "Reasoning")
        self.assertIn(self.ctrl.create_badge_skill, ["Descriptive", "Diagnostic", "Predictive", "Prescriptive"])

        # Switch power to 'Leadership'
        self.ctrl.handle_event("change_badge_power", "Leadership")
        self.assertEqual(self.ctrl.create_badge_power, "Leadership")

    def test_gemini_badge_generation_and_location_hierarchy(self):
        """Verify badge generation format and location string 'badge name under skill, under capability, under power, under band'."""
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.ctrl.handle_event("change_badge_power", "Tech")
        self.ctrl.handle_event("change_badge_capability", "Data & Machine")
        self.ctrl.handle_event("change_badge_skill", "Hardware")

        # Simulate generated badge
        from starapp.badge_generator import generate_badge_data
        badge_data = generate_badge_data(
            band="B1",
            power="Tech",
            capability="Data & Machine",
            skill="Hardware",
            outcome_sentence="Identify CPU, memory, storage, and GPU components in a given system spec and describe their basic roles"
        )
        self.ctrl.handle_event("on_badge_generated", {"badge_data": badge_data})
        html = self.ctrl.render()

        # Verify location hierarchy string
        expected_loc = "Hardware Foundations under Hardware, under Data & Machine, under Tech, under Band B1"
        self.assertIn("Created Badge Location", html)
        self.assertIn("Hardware Foundations", html)
        self.assertIn("under", html)
        self.assertIn("Band B1", html)

    def test_all_six_badge_accordion_sections(self):
        """Verify all 6 accordion cards matching screenshots: Outcomes, Earn the Badge, Practice Project, Learning Topics, Learning Resources, Related."""
        self.ctrl.handle_event("select_create_badge_band", "B1")

        # Simulate the Gemini badge generation (triggered client-side via JS in browser)
        from starapp.badge_generator import generate_badge_data
        badge_data = generate_badge_data(
            band="B1",
            power="Tech",
            capability="Data & Machine",
            skill="Hardware",
            outcome_sentence="Identify CPU, memory, storage, and GPU components in a given system spec and describe their basic roles"
        )
        self.ctrl.handle_event("on_badge_generated", {"badge_data": badge_data})
        html = self.ctrl.render()

        # Section 1: Outcomes (4)
        self.assertIn("Outcomes (4)", html)
        self.assertIn("Can identify CPU, memory, storage, and GPU components", html)

        # Section 2: Earn the Badge with Pending Review
        self.assertIn("Earn the Badge", html)
        self.assertIn("Pending Review", html)
        self.assertIn("Great job submitting your project", html)

        # Section 3: Practice Project with LLM prompt and copy button
        self.assertIn("Practice Project", html)
        self.assertIn("Want some hands-on practice?", html)
        self.assertIn("This is a prompt which should be provided to an LLM", html)

        # Section 4: Learning Topics with 100% progress
        self.assertIn("Learning Topics", html)
        self.assertIn("100%", html)
        self.assertIn("Completed", html)
        self.assertIn("CPU &amp; processor architecture", html)

        # Section 5: Learning Resources with copy prompt
        self.assertIn("Learning Resources", html)
        self.assertIn("Not sure where to start learning?", html)

        # Section 6: Related Skills, Capabilities & Powers
        self.assertIn("Related Skills, Capabilities &amp; Powers", html)
        self.assertIn("Skills", html)
        self.assertIn("Capabilities", html)
        self.assertIn("Powers", html)

    def test_save_badge_to_saved_badges_catalog(self):
        """Verify Guardian can save generated badge and see it listed under Saved Badges."""
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.ctrl.handle_event("save_generated_badge", {})
        self.assertEqual(self.ctrl.flash_type, "success")

        # Verify badge is in store
        saved = store.get_saved_badges("B1")
        self.assertTrue(len(saved) > 0)
        saved_titles = [b["title"] for b in saved]
        self.assertIn("Hardware Foundations", saved_titles)

        # Verify rendered view shows Saved Badges section
        html = self.ctrl.render()
        self.assertIn("Saved Badges for Band B1", html)
        self.assertIn("Hardware Foundations under Hardware", html)


if __name__ == "__main__":
    unittest.main()
