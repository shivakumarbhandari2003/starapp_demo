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
        """Verify Guardian opens on 4-pillar sidebar (Choose Cycle, Learning, Earning, Contribution) and Learning shows exact ordered sidebar."""
        # 1. Initial landing view is Choose Cycle (g_cycles) with 4 pillars
        self.assertEqual(self.ctrl.current_view, "g_cycles")
        pillar_html = self.ctrl.render()
        p_cyc = pillar_html.find('data-nav-id="g_cycles"')
        p_lrn = pillar_html.find('data-nav-id="g_learning"')
        p_ern = pillar_html.find('data-nav-id="g_earning"')
        p_cnt = pillar_html.find('data-nav-id="g_contribution"')
        self.assertTrue(0 < p_cyc < p_lrn < p_ern < p_cnt, "Portal pillars must be: Choose Cycle, Learning, Earning, Contribution")
        self.assertNotIn('data-nav-id="g_create_badge"', pillar_html)

        # 2. Entering Learning shows all Band cards + exact ordered Learning sidebar
        self.ctrl.handle_event("nav_guardian", "g_learning")
        html = self.ctrl.render()
        for b in ["B1", "B2", "B3", "B4", "B5", "B6"]:
            self.assertIn(f"Band {b}", html)

        cb_idx = html.find('data-nav-id="g_create_badge"')
        ba_idx = html.find('data-nav-id="g_badge_approval"')
        mp_idx = html.find('data-nav-id="g_mapping"')
        al_idx = html.find('data-nav-id="g_allotment"')
        rv_idx = html.find('data-nav-id="g_reviews"')
        ex_idx = html.find('data-nav-id="g_extensions"')
        self.assertTrue(
            0 < cb_idx < ba_idx < mp_idx < al_idx < rv_idx < ex_idx,
            "Learning sidebar items must follow exact order: Create Badge, Approval, Mapping, Allotment, Assessment, Deadline Extension"
        )
        # Learning Materials and Learning Roadmap removed from sidebar
        self.assertNotIn('data-nav-id="g_materials"', html)
        self.assertNotIn('data-nav-id="g_roadmap"', html)

        # 3. Earning & Contribution pillars stay blank/future-ready and cycle-filtered
        self.ctrl.handle_event("nav_guardian", "g_earning")
        earn_html = self.ctrl.render()
        self.assertIn("Earning Module", earn_html)
        self.assertIn("Cycle 1", earn_html)
        self.ctrl.handle_event("nav_guardian", "g_contribution")
        contrib_html = self.ctrl.render()
        self.assertIn("Contribution Module", contrib_html)
        self.assertIn("Cycle 1", contrib_html)

    def test_band_selection_view(self):
        """Verify navigating to g_create_badge without a selected band hides sidebar and renders 6 band cards."""
        self.ctrl.handle_event("nav_guardian", "g_create_badge")
        self.assertEqual(self.ctrl.current_view, "g_create_badge")
        html = self.ctrl.render()

        self.assertIn("band-selection-hidden", html)
        self.assertIn("Select Band Workspace", html)
        self.assertNotIn("Global Filter:", html)
        self.assertNotIn("Learning Pillar", html)
        self.assertNotIn("Select Operational Band", html)
        self.assertNotIn("Select a band to configure a new badge", html)
        for b in ["B1", "B2", "B3", "B4", "B5", "B6"]:
            self.assertIn(f"Band {b}", html)
            self.assertIn(f"select_create_badge_band', '{b}'", html)

        # Entering a band restores the sidebar cleanly
        self.ctrl.handle_event("select_create_badge_band", "B1")
        inside_html = self.ctrl.render()
        self.assertNotIn("band-selection-hidden", inside_html)

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

        # Verify location hierarchy string: Badge name -> skill name -> capability name -> power name -> Band number
        expected_loc = "Hardware Foundations -> Hardware -> Data & Machine -> Tech -> Band B1"
        self.assertIn("Created Badge Location", html)
        self.assertIn("Hardware Foundations", html)
        self.assertTrue("→" in html or "->" in html or "-&gt;" in html)
        self.assertIn("Band B1", html)

        # Verify advanced reviewer assignment section is hidden from visible view
        self.assertNotIn("<summary>Advanced Reviewer Assignment", html)
        self.assertIn("id=\"advanced-reviewer-settings\" style=\"display:none !important;\"", html)

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

        # Section 4: Learning Topics with real-time completion support
        self.assertIn("Learning Topics", html)
        self.assertTrue("0%" in html or "100%" in html)
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

        # Verify rendered view shows Saved Badges section with vertical taxonomy hierarchy
        html = self.ctrl.render()
        self.assertIn("Saved Badges for Band B1", html)
        self.assertIn("lg-saved-badge-card", html)
        self.assertIn("lg-hier-tree", html)
        self.assertIn("Hardware", html)
        self.assertIn("Data &amp; Machine", html)

    def test_no_skeleton_on_band_entry_and_hides_preview_after_save(self):
        """Verify band entry displays clean guidance card with zero skeleton shimmer, and save hides preview."""
        self.ctrl.handle_event("select_create_badge_band", "B2")
        html = self.ctrl.render()

        # 1. On entry: no skeleton, clean guidance card
        self.assertIn('id="badge-empty-guidance-card"', html)
        self.assertNotIn('id="created-badge-display-area"', html)
        self.assertNotIn('skeleton-shimmer', html)

        # 2. After generation: badge structure displays
        from starapp.badge_generator import generate_badge_data
        b_data = generate_badge_data("B2", "Tech", "Data & Machine", "Hardware", "Learn system hardware")
        self.ctrl.handle_event("on_badge_generated", {"badge_data": b_data})
        html_gen = self.ctrl.render()
        self.assertIn('id="created-badge-display-area"', html_gen)
        self.assertNotIn('id="badge-empty-guidance-card"', html_gen)

        # 3. After save: preview hidden again, saved in catalog
        self.ctrl.handle_event("save_generated_badge", {})
        self.assertIsNone(self.ctrl.created_badge_data)
        html_saved = self.ctrl.render()
        self.assertNotIn('id="created-badge-display-area"', html_saved)
        self.assertIn('id="badge-empty-guidance-card"', html_saved)
        self.assertIn("Saved Badges for Band B2", html_saved)

    def test_deduplication_enforcement_in_same_band(self):
        """Verify deduplication prevents saving 2 identical badges in the same band."""
        from starapp.badge_generator import generate_badge_data
        self.ctrl.handle_event("select_create_badge_band", "B3")
        b1 = generate_badge_data("B3", "Tech", "Data & Machine", "AI-OS", "Master AI-OS fundamentals")
        b1["id"] = "test_dup_badge_1"
        self.ctrl.handle_event("on_badge_generated", {"badge_data": b1})
        self.ctrl.handle_event("save_generated_badge", {})
        self.assertEqual(self.ctrl.flash_type, "success")

        # Attempt to save a second badge with the same skill in the same band
        b2 = generate_badge_data("B3", "Tech", "Data & Machine", "AI-OS", "Master AI-OS advanced")
        b2["id"] = "test_dup_badge_2"
        self.ctrl.handle_event("on_badge_generated", {"badge_data": b2})
        self.ctrl.handle_event("save_generated_badge", {})
        self.assertEqual(self.ctrl.flash_type, "error")
        self.assertIn("Duplicate badges are not allowed", self.ctrl.last_flash_message)

    def test_custom_capability_and_skill_sqlite_roundtrip(self):
        """Verify custom capability and skill addition persists in SQLite and updates dropdowns."""
        self.ctrl.handle_event("select_create_badge_band", "B1")
        self.ctrl.handle_event("add_custom_capability", '{"name": "Quantum Systems"}')
        self.assertEqual(self.ctrl.flash_type, "success")
        self.assertEqual(self.ctrl.create_badge_capability, "Quantum Systems")

        # Add skill under that capability
        self.ctrl.handle_event("add_custom_skill", '{"name": "Qubits & Gates", "capability": "Quantum Systems"}')
        self.assertEqual(self.ctrl.flash_type, "success")
        self.assertEqual(self.ctrl.create_badge_skill, "Qubits & Gates")

        html = self.ctrl.render()
        self.assertIn("Quantum Systems", html)
        self.assertIn("Qubits &amp; Gates", html)

    def test_gemini_fallback_badge_learning_resources_and_practice_project_content(self):
        """Verify Gemini fallback badge generates rich practice project and learning resource content."""
        from backend.app.integrations.gemini.router import generate_fallback_badge
        badge = generate_fallback_badge("B2", "Tech", "Data & Machine", "Hardware", "Can optimize memory bus and cache timings.")

        # Check practice project
        self.assertIn("practice_project", badge)
        self.assertIn("prompt", badge["practice_project"])
        self.assertTrue(len(badge["practice_project"]["prompt"]) > 100)
        self.assertIn("Hardware", badge["practice_project"]["prompt"])
        self.assertIn("practice_prompt", badge)

        # Check learning resources
        self.assertIn("learning_resources", badge)
        self.assertIn("prompt", badge["learning_resources"])
        self.assertTrue(len(badge["learning_resources"]["prompt"]) > 100)
        self.assertIn("free, current, high-quality learning resources", badge["learning_resources"]["prompt"])
        self.assertIn("resources_prompt", badge)

        # Verify preview render in Guardian UI displays non-empty practice project and learning resources
        self.ctrl.handle_event("select_create_badge_band", "B2")
        self.ctrl.handle_event("on_badge_generated", {"badge_data": badge})
        html = self.ctrl.render()

        self.assertIn('id="practice-prompt-text"', html)
        self.assertIn("Design one small, hands-on practice project", html)
        self.assertIn('id="resources-prompt-text"', html)
        self.assertIn("learning resources (official docs, free courses, tutorials, videos)", html)

        # Save and verify inspect modal displays them
        self.ctrl.handle_event("save_generated_badge", {})
        saved_badge_id = self.ctrl.last_flash_message  # Just verify it saved
        saved_badges = store.get_saved_badges("B2")
        self.assertTrue(len(saved_badges) > 0)
        sb = saved_badges[0]

        # Inspect modal
        self.ctrl.handle_event("open_badge_for_review", sb["id"])
        modal_html = self.ctrl.render()
        self.assertIn("Practice Project Prompt:", modal_html)
        self.assertIn("Learning Resources Prompt:", modal_html)

    def test_inside_band_create_badge_ui_and_edit_flow(self):
        """Verify streamlined Create Badge workspace, inside-dropdown taxonomy adds, Liquid-Glass output, auto-grow textareas, and top-right Back."""
        self.ctrl.handle_event("select_create_badge_band", "B1")
        full_html = self.ctrl.render()
        main_html = self.ctrl.last_rendered_regions["mainContentHtml"]
        topbar_html = self.ctrl.last_rendered_regions["topbarHtml"]

        # Back button lives only in topbar-right, never inline in Create Badge workspace
        self.assertIn('class="topbar-right"', topbar_html)
        self.assertIn("dispatchAction('go_back'", topbar_html)
        self.assertIn('class="topbar-right"', full_html)
        topbar_right = full_html.split('class="topbar-right"', 1)[1]
        self.assertIn("dispatchAction('go_back'", topbar_right)
        for clutter in (
            "Back to Bands",
            "Create Badge &rsaquo;",
            "Choose Power, Capability",
            "Badges authored and saved for curriculum allotment.",
            "+ Add Capability",
            "+ Add Skill",
        ):
            self.assertNotIn(clutter, main_html)

        # Add options reside inside Capability and Skill selects; Selected strip is structured
        self.assertIn('value="__add_custom_capability__"', main_html)
        self.assertIn('value="__add_custom_skill__"', main_html)
        self.assertIn("cb-taxonomy-row", main_html)
        self.assertIn("cb-selection-bar", main_html)
        self.assertIn('id="cb-crumb-power"', main_html)
        self.assertIn('id="cb-crumb-cap"', main_html)
        self.assertIn('id="cb-crumb-skill"', main_html)
        self.assertIn("auto-grow-textarea", main_html)

        # Generate badge -> structured Liquid-Glass result without emojis
        from starapp.badge_generator import generate_badge_data
        badge_data = generate_badge_data(
            band="B1",
            power="Tech",
            capability="Data & Machine",
            skill="Hardware",
            outcome_sentence="Design telemetry circuits."
        )
        self.ctrl.handle_event("on_badge_generated", {"badge_data": badge_data})
        self.ctrl.render()
        res_html = self.ctrl.last_rendered_regions["mainContentHtml"]
        self.assertIn("cb-result-hero", res_html)
        self.assertIn("cb-section-card", res_html)
        self.assertIn("cb-prompt-surface", res_html)
        for emoji in ("✏️", "💾", "▲", "▼", "①", "②", "③"):
            self.assertNotIn(emoji, res_html)

        # Enter Edit Mode -> all edit textareas non-resizable auto-grow + Apply Changes works
        self.ctrl.handle_event("toggle_edit_badge", {})
        self.ctrl.render()
        edit_html = self.ctrl.last_rendered_regions["mainContentHtml"]
        for eid in (
            "edit-badge-title-input",
            "edit-badge-desc-input",
            "edit-badge-outcomes-input",
            "edit-practice-prompt-input",
            "edit-resources-prompt-input",
            "edit-topic-title-0",
            "edit-topic-desc-0",
        ):
            self.assertIn(eid, edit_html)
        self.assertIn("saveBadgeEdits()", edit_html)
        self.assertNotIn("resize:vertical", edit_html)

        self.ctrl.handle_event("save_badge_edits", json.dumps({
            "title": "Edited Hardware Badge",
            "description": "Updated scope description.",
            "outcomes": ["Can validate hardware timing"],
            "practice_prompt": "Role: Architect\n- Build test fixture\n- Measure jitter",
            "resources_prompt": "- Official docs\n- Video walkthrough",
        }))
        self.ctrl.render()
        saved_edit_html = self.ctrl.last_rendered_regions["mainContentHtml"]
        self.assertIn("Edited Hardware Badge", saved_edit_html)
        self.assertIn("cb-prompt-bullets", saved_edit_html)

    def test_reviewer_badge_approval_toolbar_hierarchy_and_titlecase(self):
        """Verify streamlined Reviewer Badge Approval toolbar dropdowns, Title Case table, and visual Taxonomy Hierarchy."""
        self.ctrl.handle_event("nav_guardian", "g_badge_approval")
        self.ctrl.render()
        ba_html = self.ctrl.last_rendered_regions["mainContentHtml"]

        for removed in (
            "Curriculum Management",
            "Reviewer Badge Approval Queue",
            "Review, update and approve badges submitted for authorization.",
            "+ Create New Badge",
            "BAND B1",
            "text-transform:uppercase",
            "var(--frost-navy-50)",
            "var(--frost-navy-75)",
        ):
            self.assertNotIn(removed, ba_html)

        for required in (
            "Reviewer Badge Approval",
            "ba-toolbar-card",
            'id="ba-status-filter-select"',
            'id="ba-history-toggle-btn"',
            'id="ba-band-filter-select"',
            'id="ba-search-input"',
            "All Submissions (",
            "Ready for Review (",
            "Pending Review (",
            "Approved Badges (",
            "Returned (",
            "Review History &amp; Audit (",
            "Taxonomy Hierarchy",
            "lg-hier-tree",
            "lg-hier-row",
            "Band B1",
        ):
            self.assertIn(required, ba_html)

        self.assertIn("ba-toolbar-card", ba_html)
        self.assertIn("lg-hier-tree", ba_html)
        self.assertIn("Power :", ba_html)
        self.assertIn("Capability :", ba_html)
        self.assertIn("Skill :", ba_html)
        self.assertIn("lg-hier-branch", ba_html)
        self.assertNotIn("liquid-select-chevron", ba_html)

        # Switching to history renders visual hierarchy chips too
        self.ctrl.handle_event("filter_badge_approval", "history")
        self.ctrl.render()
        hist_html = self.ctrl.last_rendered_regions["mainContentHtml"]
        self.assertIn("ba-history-btn is-active", hist_html)
        self.assertIn("Taxonomy Hierarchy", hist_html)

    def test_band_cards_positions_and_minimal_fields(self):
        """Verify streamlined Band cards show only Band number, position name, member count, and button."""
        self.ctrl.handle_event("nav_guardian", "g_learning")
        self.ctrl.render()
        bands_html = self.ctrl.last_rendered_regions["mainContentHtml"]

        for pos in ("Trainee", "Associate", "Lead", "Expert", "Architect", "Principal"):
            self.assertIn(pos, bands_html)
        self.assertIn("Members", bands_html)
        for clutter in ("Cohort", "Submissions", "Eligible Reviewers", "0 Badges", "Foundational engineering"):
            self.assertNotIn(clutter, bands_html)


if __name__ == "__main__":
    unittest.main()
