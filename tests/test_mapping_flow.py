"""
Tests for Guardian Role & Competency Mapping Workflow
Validates the 6 Band cards (B1 to B6), dynamic heading display,
the 'Create Badge' 4-card matrix (Select Roles, Select Badge, Select Cosmonaut, Select Reviewers),
filtering, search controls, higher-band reviewer assignment, and persistence.
"""

import json
import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from starapp.app import StarAppController
from starapp.storage import store
from starapp.mapping_data import (
    BANDS, BAND_CODES, ROLES, DUMMY_MEMBERS, MAPPING_BADGES,
    get_higher_bands, filter_members_by_band_and_roles, filter_reviewers_by_band_and_roles
)

class TestGuardianMappingFlow(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        # Login as guardian
        self.ctrl.handle_event("login", json.dumps({"username": "guardian"}))
        self.assertIsNotNone(self.ctrl.current_user)
        self.assertEqual(self.ctrl.current_user.role, "guardian")

    def test_guardian_sidebar_contains_mapping(self):
        """Verify Mapping section is present in Guardian sidebar navigation."""
        self.assertIn("g_mapping", StarAppController._GUARDIAN_VIEWS)
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.assertEqual(self.ctrl.current_view, "g_mapping")
        html = self.ctrl.render()
        self.assertIn('data-nav-id="g_mapping"', html)
        self.assertIn("Mapping", html)

    def test_cosmonaut_cannot_route_to_mapping(self):
        """Cosmonaut cannot route to g_mapping since it is Guardian-exclusive."""
        cosmo_ctrl = StarAppController()
        cosmo_ctrl.handle_event("login", json.dumps({"username": "astraea"}))
        self.assertNotIn("g_mapping", StarAppController._COSMONAUT_VIEWS)

    def test_6_band_cards_render(self):
        """Verify all 6 Band cards (B1 to B6) render with their titles and 6 members."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        html = self.ctrl.render()
        for code in ["B1", "B2", "B3", "B4", "B5", "B6"]:
            self.assertIn(f">{code}<", html)
            self.assertIn(f"select_mapping_band', '{code}'", html)

    def test_clicking_band_updates_heading_and_higher_reviewers(self):
        """Clicking on B1, B3, B5 updates respective heading and adjusts higher-band reviewers."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")

        # Test selecting B1
        self.ctrl.handle_event("select_mapping_band", "B1")
        self.assertEqual(self.ctrl.mapping_selected_band, "B1")
        # Reviewer bands should be B2 to B6
        self.assertEqual(get_higher_bands("B1"), ["B2", "B3", "B4", "B5", "B6"])
        self.assertIn(self.ctrl.mapping_selected_reviewer_band, ["B2", "B3", "B4", "B5", "B6"])
        html = self.ctrl.render()
        self.assertIn("B1 &bull; Foundation Associate", html)

        # Test selecting B3
        self.ctrl.handle_event("select_mapping_band", "B3")
        self.assertEqual(self.ctrl.mapping_selected_band, "B3")
        self.assertEqual(get_higher_bands("B3"), ["B4", "B5", "B6"])
        self.assertIn(self.ctrl.mapping_selected_reviewer_band, ["B4", "B5", "B6"])
        html = self.ctrl.render()
        self.assertIn("B3 &bull; Senior Specialist", html)

    def test_create_badge_4_cards_matrix(self):
        """Verify Create Badge box has the 4 cards: Roles, Badge, Cosmonaut, Reviewers."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        html = self.ctrl.render()
        self.assertIn("Create Badge", html)
        self.assertIn("1. Select Roles", html)
        self.assertIn("2. Select Badge", html)
        self.assertIn("3. Select Cosmonaut", html)
        self.assertIn("4. Select Reviewers", html)

        # Verify the 3 roles
        self.assertIn("Solutions Designer", html)
        self.assertIn("AI Engineer", html)
        self.assertIn("Systems Engineer", html)

        # Verify badges list includes AIOS, Network, Data Modelling
        self.assertIn("AIOS", html)
        self.assertIn("Network", html)
        self.assertIn("Data Modelling", html)

        # Verify search inputs in dropdowns
        self.assertIn('id="mapping-badge-search-input"', html)
        self.assertIn('id="mapping-cosmo-search-input"', html)
        self.assertIn('id="mapping-reviewer-search-input"', html)

    def test_role_filtering_and_cosmonaut_display(self):
        """Filtering roles updates the displayed cosmonauts of that band."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B1")

        # When all roles active, 6 members of B1 should be returned
        all_b1 = filter_members_by_band_and_roles("B1", ["Solutions Designer", "AI Engineer", "Systems Engineer"])
        self.assertEqual(len(all_b1), 6)

        # Filter to only AI Engineer
        self.ctrl.mapping_selected_roles = ["AI Engineer"]
        ai_b1 = filter_members_by_band_and_roles("B1", self.ctrl.mapping_selected_roles)
        self.assertEqual(len(ai_b1), 2)
        for m in ai_b1:
            self.assertEqual(m["role"], "AI Engineer")

    def test_higher_band_reviewer_selection(self):
        """When selecting B1, reviewers can be chosen from B2 to B6."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B1")
        self.ctrl.handle_event("select_mapping_reviewer_band", "B3")
        self.assertEqual(self.ctrl.mapping_selected_reviewer_band, "B3")

        revs_b3 = filter_reviewers_by_band_and_roles("B3", ["AI Engineer", "Solutions Designer", "Systems Engineer"])
        self.assertEqual(len(revs_b3), 6)
        for r in revs_b3:
            self.assertEqual(r["band"], "B3")

    def test_save_and_delete_band_mapping(self):
        """Guardian can save a badge mapping and delete it."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B2")
        self.ctrl.handle_event("select_mapping_badge", "Network")
        self.ctrl.handle_event("toggle_mapping_cosmonaut", "m_b2_1")
        self.ctrl.handle_event("toggle_mapping_cosmonaut", "m_b2_2")
        self.ctrl.handle_event("select_mapping_reviewer_band", "B4")
        self.ctrl.handle_event("toggle_mapping_reviewer", "m_b4_1")

        count_before = len(store.get_band_mappings())
        self.ctrl.handle_event("save_band_mapping", "{}")
        self.assertEqual(len(store.get_band_mappings()), count_before + 1)
        latest = store.get_band_mappings()[0]
        self.assertEqual(latest["band"], "B2")
        self.assertEqual(latest["badge"], "Network")
        self.assertEqual(latest["reviewer_band"], "B4")
        self.assertIn("m_b2_1", latest["cosmonauts"])
        self.assertIn("m_b4_1", latest["reviewers"])

        # Delete mapping
        self.ctrl.handle_event("delete_band_mapping", json.dumps({"mapping_id": latest["id"]}))
        self.assertEqual(len(store.get_band_mappings()), count_before)

    def test_calendar_weekend_lockout_and_consecutive_3_day_selection(self):
        """
        Verify calendar greys out weekends (Sat & Sun), anchors weekday selection,
        and enforces 3 consecutive working days (skipping Sat & Sun) for both 'after' and 'before'.
        """
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        html = self.ctrl.render()

        # Check calendar structure
        self.assertIn("Select Estimated Review Date", html)
        self.assertIn("cal-weekdays-row", html)
        self.assertIn("weekend-header", html)
        self.assertIn("Sat ✕", html)
        self.assertIn("Sun ✕", html)
        self.assertIn('class="cal-day-cell weekend"', html)

        # 1. Anchor on Friday 2026-11-20 with direction 'after':
        # Should select Friday 2026-11-20, skip Sat (21) & Sun (22), select Monday 2026-11-23 & Tuesday 2026-11-24.
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-20")
        self.ctrl.handle_event("set_mapping_review_direction", "after")
        self.assertEqual(self.ctrl.mapping_review_dates, ["2026-11-20", "2026-11-23", "2026-11-24"])
        html = self.ctrl.render()
        self.assertIn("Day 1", html)
        self.assertIn("Day 2", html)
        self.assertIn("Day 3", html)
        self.assertIn("2026-11-20", html)
        self.assertIn("2026-11-23", html)
        self.assertIn("2026-11-24", html)

        # 2. Anchor on Monday 2026-11-23 with direction 'before':
        # Should select Thursday 2026-11-19, Friday 2026-11-20, and Monday 2026-11-23 (skipping Sat 21 & Sun 22).
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-23")
        self.ctrl.handle_event("set_mapping_review_direction", "before")
        self.assertEqual(self.ctrl.mapping_review_dates, ["2026-11-19", "2026-11-20", "2026-11-23"])

        # 3. Calendar month navigation
        self.ctrl.handle_event("change_mapping_calendar_month", json.dumps({"year": 2026, "month": 12}))
        self.assertEqual(self.ctrl.mapping_calendar_year, 2026)
        self.assertEqual(self.ctrl.mapping_calendar_month, 12)
        html_dec = self.ctrl.render()
        self.assertIn("December 2026", html_dec)

    def test_visual_who_is_mapped_to_whom_and_edit_mapping_lifecycle(self):
        """
        Verify the Active Mappings table displays the visual pairing (Cosmonaut ── mapped to ──► Reviewer),
        and Guardian can click Edit, update fields, and save changes in place.
        """
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        html = self.ctrl.render()

        # Check visual pairing elements in active mappings table
        self.assertIn("Active Band & Milestone Mappings", html)
        self.assertIn("Who is Mapped to Whom (Cosmonaut ➔ Higher-Band Reviewer)", html)
        self.assertIn("mapping-pair-item", html)
        self.assertIn("mapping-connector-arrow", html)
        self.assertIn("── mapped to ──►", html)
        self.assertIn("edit_band_mapping", html)

        # Retrieve first existing mapping to edit
        mappings = store.get_band_mappings()
        self.assertGreater(len(mappings), 0)
        target = mappings[0]
        target_id = target["id"]

        # 1. Trigger Edit
        self.ctrl.handle_event("edit_band_mapping", target_id)
        self.assertEqual(self.ctrl.editing_mapping_id, target_id)
        self.assertEqual(self.ctrl.mapping_selected_band, target["band"])
        self.assertEqual(self.ctrl.mapping_selected_badge, target["badge"])

        # Verify editing UI indicators
        edit_html = self.ctrl.render()
        self.assertIn("EDITING MODE", edit_html)
        self.assertIn("Update Badge Mapping", edit_html)
        self.assertIn("Cancel Edit", edit_html)

        # 2. Modify badge and review dates in editing mode
        self.ctrl.handle_event("select_mapping_badge", "Data Modelling")
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-25")
        self.ctrl.handle_event("set_mapping_review_direction", "after")

        # 3. Save updated mapping
        count_before = len(store.get_band_mappings())
        self.ctrl.handle_event("save_band_mapping", "{}")
        # Ensure it updated the existing record, did not add duplicate
        self.assertEqual(len(store.get_band_mappings()), count_before)
        self.assertIsNone(self.ctrl.editing_mapping_id)

        # Verify target record in store updated
        updated_target = [m for m in store.get_band_mappings() if m["id"] == target_id][0]
        self.assertEqual(updated_target["badge"], "Data Modelling")
        self.assertEqual(updated_target["review_dates"], ["2026-11-25", "2026-11-26", "2026-11-27"])

        # 4. Test cancel edit
        self.ctrl.handle_event("edit_band_mapping", target_id)
        self.assertEqual(self.ctrl.editing_mapping_id, target_id)
        self.ctrl.handle_event("cancel_edit_band_mapping", "{}")
        self.assertIsNone(self.ctrl.editing_mapping_id)

    def test_sidebar_collapsible_and_expandable_controls(self):
        """
        Verify sidebar collapse controls are rendered in both Guardian and Cosmonaut layouts,
        and bridge supports toggleSidebar.
        """
        # Guardian layout has sidebar collapse button (inside sidebar HTML)
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        g_html = self.ctrl.render()
        self.assertIn("sidebar-collapse-btn", g_html)
        self.assertIn("window.StarAppBridge.toggleSidebar()", g_html)

        # Cosmonaut layout also has sidebar collapse button
        cosmo_ctrl = StarAppController()
        cosmo_ctrl.handle_event("login", json.dumps({"username": "astraea"}))
        cosmo_ctrl.handle_event("nav_cosmonaut", "c_dashboard")
        c_html = cosmo_ctrl.render()
        self.assertIn("sidebar-collapse-btn", c_html)
        self.assertIn("window.StarAppBridge.toggleSidebar()", c_html)

        # Verify CSS styles for collapsed sidebar in layout.css
        layout_css_path = ROOT_DIR / "css" / "layout.css"
        with open(layout_css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        self.assertIn(".app-sidebar.collapsed", css_content)
        self.assertIn(".sidebar-collapse-btn", css_content)
        self.assertIn(".topbar-sidebar-toggle-btn", css_content)

        # Verify render_topbar in views_common.py contains the topbar toggle button
        views_common_path = ROOT_DIR / "starapp" / "views_common.py"
        with open(views_common_path, "r", encoding="utf-8") as f:
            views_common_content = f.read()
        self.assertIn("topbar-sidebar-toggle-btn", views_common_content)
        self.assertIn("window.StarAppBridge.toggleSidebar()", views_common_content)

        # Verify bridge.js contains toggleSidebar and applyPersistedSidebarState
        bridge_js_path = ROOT_DIR / "js" / "bridge.js"
        with open(bridge_js_path, "r", encoding="utf-8") as f:
            bridge_content = f.read()
        self.assertIn("toggleSidebar", bridge_content)
        self.assertIn("applyPersistedSidebarState", bridge_content)
        self.assertIn("starapp_sidebar_collapsed", bridge_content)

if __name__ == "__main__":
    unittest.main()
