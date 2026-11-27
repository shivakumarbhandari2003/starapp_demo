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
        """Verify Mapping loads into the 4-card matrix for the active band context."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        html = self.ctrl.render()
        self.assertIn("Role & Competency Mapping Matrix", html)
        self.assertIn("Map Approved Badge", html)
        self.assertIn("Band B1", html)

    def test_clicking_band_updates_heading_and_higher_reviewers(self):
        """Selecting band updates respective heading and adjusts higher-band reviewers."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")

        # Test selecting B1
        self.ctrl.handle_event("select_mapping_band", "B1")
        self.assertEqual(self.ctrl.mapping_selected_band, "B1")
        # Reviewer bands should be B2 to B6
        self.assertEqual(get_higher_bands("B1"), ["B2", "B3", "B4", "B5", "B6"])
        self.assertIn(self.ctrl.mapping_selected_reviewer_band, ["B2", "B3", "B4", "B5", "B6"])
        html = self.ctrl.render()
        self.assertIn("Band B1", html)

        # Test selecting B3
        self.ctrl.handle_event("select_mapping_band", "B3")
        self.assertEqual(self.ctrl.mapping_selected_band, "B3")
        self.assertEqual(get_higher_bands("B3"), ["B4", "B5", "B6"])
        self.assertIn(self.ctrl.mapping_selected_reviewer_band, ["B4", "B5", "B6"])
        html = self.ctrl.render()
        self.assertIn("Band B3", html)

    def test_create_badge_4_cards_matrix(self):
        """Verify Create Badge box has the 4 cards: Roles, Badge, Cosmonaut, Reviewers."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        html = self.ctrl.render()
        self.assertIn("Map Approved Badge", html)
        self.assertIn("1. Select Roles", html)
        self.assertIn("2. Select Badge", html)
        self.assertIn("3. Select Cosmonaut", html)
        self.assertIn("4. Select Reviewers", html)

        # Verify the 3 roles
        self.assertIn("Solutions Designer", html)
        self.assertIn("AI Engineer", html)
        self.assertIn("Systems Engineer", html)

        # Verify badges list includes real approved B1 badge from SQLite
        self.assertIn("Intelligent Apps Foundations", html)
        self.assertNotIn("B1-INT-01", html)          # badge codes are not shown in the selection card any more

        # Verify search inputs in dropdowns
        self.assertIn('id="mapping-badge-search-input"', html)
        self.assertIn('id="mapping-cosmo-search-input"', html)
        self.assertIn('id="mapping-reviewer-search-input"', html)

    def test_role_filtering_and_cosmonaut_display(self):
        """Filtering roles updates the displayed cosmonauts of that band."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B1")

        # When all roles active, 6 members of B1 should be returned (2 per role)
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
        base_html = self.ctrl.render()
        self.assertIn('id="mapping-open-calendar-btn"', base_html)
        self.assertIn("Reset", base_html)
        self.assertNotIn("cal-days-grid", base_html)

        # Click calendar icon beside Reset -> opens Glass Calendar modal
        self.ctrl.handle_event("open_mapping_calendar_modal", "{}")
        html = self.ctrl.render()

        # Check real calendar structure & controls inside Liquid-Glass modal
        self.assertIn("mapping-calendar-modal-glass", html)
        for gone in ("Select Estimated Review Date", "Selection Mode", "Range Pick", "Apply Schedule", "mapping-date-from", "mapping-cal-today-btn", "lg-mapcal-side"):
            self.assertNotIn(gone, html)                               # the window is ONLY a calendar + one row of dropdowns
        self.assertIn("cal-weekdays-row", html)
        self.assertIn("weekend-header", html)
        self.assertIn("Sat", html)
        self.assertIn("Sun", html)
        self.assertNotIn("Sat ✕", html)
        self.assertIn('id="mapping-cal-month-select"', html)
        self.assertIn('id="mapping-cal-year-select"', html)
        self.assertIn('id="mapping-cal-days-select"', html)
        self.assertIn('<option value="manual"', html)
        self.assertIn('class="cal-day-cell weekend', html)

        # 1. Anchor on Friday 2026-11-20 with direction 'after':
        # Should select Friday 2026-11-20, skip Sat (21) & Sun (22), select Monday 2026-11-23 & Tuesday 2026-11-24.
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-20")
        self.ctrl.handle_event("set_mapping_review_direction", "after")
        self.assertEqual(self.ctrl.mapping_review_dates, ["2026-11-20", "2026-11-23", "2026-11-24"])
        html = self.ctrl.render()
        self.assertEqual(html.count("selected-review-day"), 3)          # three highlighted working days
        self.assertIn("2026-11-20", html)
        self.assertIn("2026-11-23", html)
        self.assertIn("2026-11-24", html)

        # 2. Anchor on Monday 2026-11-23 with direction 'before':
        # Should select Thursday 2026-11-19, Friday 2026-11-20, and Monday 2026-11-23 (skipping Sat 21 & Sun 22).
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-23")
        self.ctrl.handle_event("set_mapping_review_direction", "before")
        self.assertEqual(self.ctrl.mapping_review_dates, ["2026-11-19", "2026-11-20", "2026-11-23"])

        # 3. Calendar month navigation, Today jump & direct From/To date range input
        self.ctrl.handle_event("change_mapping_calendar_month", json.dumps({"year": 2026, "month": 12}))
        self.assertEqual(self.ctrl.mapping_calendar_year, 2026)
        self.assertEqual(self.ctrl.mapping_calendar_month, 12)
        html_dec = self.ctrl.render()
        self.assertIn('<option value="12" selected>December</option>', html_dec)
        self.assertIn('<option value="2026" selected>2026</option>', html_dec)

        self.ctrl.handle_event("set_mapping_date_range", json.dumps({"start": "2026-12-07", "end": "2026-12-10"}))
        self.assertEqual(self.ctrl.mapping_review_dates, ["2026-12-07", "2026-12-08", "2026-12-09", "2026-12-10"])
        self.ctrl.handle_event("jump_mapping_calendar_today", "{}")
        import datetime as _dt
        self.assertEqual(self.ctrl.mapping_calendar_year, _dt.date.today().year)
        self.assertEqual(self.ctrl.mapping_calendar_month, _dt.date.today().month)

    def test_calendar_days_dropdown_3_5_7_and_manual(self):
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("open_mapping_calendar_modal", "{}")
        # 5 working days from Fri 20 Nov skip the weekend
        self.ctrl.handle_event("set_mapping_review_duration", "5")
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-20")
        self.assertEqual(self.ctrl.mapping_review_dates, ["2026-11-20", "2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"])
        html = self.ctrl.render()
        self.assertIn('<option value="5" selected>5 Days</option>', html)
        # 7 days
        self.ctrl.handle_event("set_mapping_review_duration", "7")
        self.assertEqual(len(self.ctrl.mapping_review_dates), 7)
        # Manual: keeps the current days, then every click toggles one working day; weekends are ignored; one day always stays
        self.ctrl.handle_event("set_mapping_review_mode", "manual")
        self.assertEqual(self.ctrl.mapping_review_mode, "manual")
        before = list(self.ctrl.mapping_review_dates)
        self.assertEqual(before[0], "2026-11-20")
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-23")            # off
        self.assertNotIn("2026-11-23", self.ctrl.mapping_review_dates)
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-12-01")            # on (a non-consecutive day)
        self.assertIn("2026-12-01", self.ctrl.mapping_review_dates)
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-21")            # Saturday: ignored
        self.assertNotIn("2026-11-21", self.ctrl.mapping_review_dates)
        self.assertEqual(self.ctrl.mapping_review_dates, sorted(self.ctrl.mapping_review_dates))
        self.assertIn('<option value="manual" selected>Manual</option>', self.ctrl.render())
        for d in list(self.ctrl.mapping_review_dates)[1:]:
            self.ctrl.handle_event("select_mapping_review_anchor", d)
        self.assertEqual(len(self.ctrl.mapping_review_dates), 1)                         # the last day can't be switched off
        self.ctrl.handle_event("select_mapping_review_anchor", self.ctrl.mapping_review_dates[0])
        self.assertEqual(len(self.ctrl.mapping_review_dates), 1)

    def test_visual_who_is_mapped_to_whom_and_edit_mapping_lifecycle(self):
        """
        Verify the old table section is removed, and when mapping is created,
        Live Mapped Allocations displays the visual pairing (Cosmonaut ── mapped to ──► Reviewer).
        """
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B1")
        initial_html = self.ctrl.render()

        # The old static table is completely removed
        self.assertNotIn("Active Band & Milestone Mappings", initial_html)
        self.assertNotIn("2 Mappings Defined", initial_html)

        # 1. Create a mapping record for B1
        mapping_record = {
            "id": "map_test_b1",
            "band": "B1",
            "badge": "AIOS",
            "roles": ["Solutions Designer", "AI Engineer"],
            "cosmonauts": ["m_b1_1", "m_b1_2"],
            "reviewer_band": "B2",
            "reviewers": ["m_b2_1"],
            "review_dates": ["2026-11-18", "2026-11-19", "2026-11-20"],
            "created_at": "2026-11-15T12:00:00Z",
            "status": "active"
        }
        store.save_band_mapping(mapping_record)

        # Click the AIOS badge card to expand its saved mapping table
        self.ctrl.handle_event("toggle_mapping_badge_card", "AIOS")
        html = self.ctrl.render()
        self.assertIn("Live Mapped Review Allocations", html)
        self.assertIn("Band B1", html)
        self.assertIn("mapped-cosmo-chip", html)
        self.assertIn("Rohan Deshmukh", html)

        # 2. Trigger Edit
        target_id = "map_test_b1"
        self.ctrl.handle_event("edit_band_mapping", target_id)
        self.assertEqual(self.ctrl.editing_mapping_id, target_id)
        self.assertEqual(self.ctrl.mapping_selected_band, "B1")
        self.assertEqual(self.ctrl.mapping_selected_badge, "AIOS")

        # Verify editing UI indicators
        edit_html = self.ctrl.render()
        self.assertIn("Editing Mode", edit_html)
        self.assertIn("Update Badge Mapping", edit_html)
        self.assertIn("Cancel Edit", edit_html)

        # 3. Modify badge and review dates in editing mode
        self.ctrl.handle_event("select_mapping_badge", "Data Modelling")
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-25")
        self.ctrl.handle_event("set_mapping_review_direction", "after")

        # Save updated mapping
        count_before = len(store.get_band_mappings())
        self.ctrl.handle_event("save_band_mapping", "{}")
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

        # 5. Test clear mapping
        self.ctrl.handle_event("clear_band_mappings", "B1")
        self.assertEqual(len([m for m in store.get_band_mappings() if m.get("band") == "B1"]), 0)

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

    def test_send_accept_reject_mapping_requests(self):
        """Review requests can be sent to guardians, accepted, and rejected."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B1")
        self.ctrl.handle_event("select_mapping_badge", "AIOS")
        self.ctrl.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2", "m_b1_3"]
        self.ctrl.mapping_selected_reviewers = ["m_b2_1", "m_b2_2"]

        # Send request
        self.ctrl.handle_event("send_mapping_requests", "{}")
        reqs = store.get_mapping_requests()
        self.assertTrue(len(reqs) >= 2)
        b1_reqs = [r for r in reqs if r.get("band") == "B1"]
        self.assertEqual(len(b1_reqs), 2)
        for r in b1_reqs:
            self.assertEqual(r["status"], "pending")
            self.assertEqual(r["badge"], "AIOS")

        # Accept one guardian request
        target_req = b1_reqs[0]
        self.ctrl.handle_event("accept_mapping_request", target_req["id"])
        updated_req = next(r for r in store.get_mapping_requests() if r["id"] == target_req["id"])
        self.assertEqual(updated_req["status"], "accepted")

        # Reject the other guardian request
        other_req = b1_reqs[1]
        self.ctrl.handle_event("reject_mapping_request", other_req["id"])
        updated_other = next(r for r in store.get_mapping_requests() if r["id"] == other_req["id"])
        self.assertEqual(updated_other["status"], "rejected")

        # Delete rejected request
        self.ctrl.handle_event("delete_mapping_request", other_req["id"])
        self.assertIsNone(next((r for r in store.get_mapping_requests() if r["id"] == other_req["id"]), None))

    def test_execute_cosmonaut_mapping_equal_distribution_and_replacement(self):
        """Execute equal partitioning of cosmonauts across accepted guardians and replace old mapping."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B1")
        self.ctrl.handle_event("select_mapping_badge", "AIOS")
        
        # 6 cosmonauts selected
        cosmo_ids = ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5", "m_b1_6"]
        self.ctrl.mapping_selected_cosmonauts = list(cosmo_ids)
        self.ctrl.mapping_selected_reviewers = ["m_b2_1", "m_b2_2"]

        # 1. Dispatch requests and accept both guardians
        self.ctrl.handle_event("send_mapping_requests", "{}")
        self.ctrl.handle_event("accept_mapping_request", "req_B1_m_b2_1")
        self.ctrl.handle_event("accept_mapping_request", "req_B1_m_b2_2")

        # 2. Trigger equal cosmonaut mapping
        self.ctrl.handle_event("execute_cosmonaut_mapping", "{}")

        # Verify mappings for B1
        b1_mappings = [m for m in store.get_band_mappings() if m.get("band") == "B1"]
        self.assertEqual(len(b1_mappings), 2)
        # Check equal partition: 6 cosmonauts distributed to 2 guardians = 3 each
        m1 = next(m for m in b1_mappings if "m_b2_1" in m.get("reviewers", []))
        m2 = next(m for m in b1_mappings if "m_b2_2" in m.get("reviewers", []))
        self.assertEqual(len(m1["cosmonauts"]), 3)
        self.assertEqual(len(m2["cosmonauts"]), 3)
        # All 6 accounted for with no duplicates
        combined_cosmonauts = m1["cosmonauts"] + m2["cosmonauts"]
        self.assertEqual(sorted(combined_cosmonauts), sorted(cosmo_ids))

        # 3. Test that old mapping vanishes and is replaced when mapped again with new set
        new_cosmo_ids = ["m_b1_7", "m_b1_8", "m_b1_9", "m_b1_10"]
        self.ctrl.mapping_selected_cosmonauts = list(new_cosmo_ids)
        self.ctrl.handle_event("execute_cosmonaut_mapping", "{}")

        # Old mappings must vanish
        new_b1_mappings = [m for m in store.get_band_mappings() if m.get("band") == "B1"]
        self.assertEqual(len(new_b1_mappings), 2)
        new_combined = []
        for m in new_b1_mappings:
            new_combined.extend(m["cosmonauts"])
        self.assertEqual(sorted(new_combined), sorted(new_cosmo_ids))
        # Ensure previous cosmo_ids are completely gone from B1 mappings
        for cid in cosmo_ids:
            self.assertNotIn(cid, new_combined)

    def test_multi_band_reviewer_selection_and_reset(self):
        """Guardian can select reviewers across multiple bands and reset everything."""
        self.ctrl.handle_event("nav_guardian", "g_mapping")
        self.ctrl.handle_event("select_mapping_band", "B1")

        # B2 is active initially; toggle B3 to add B3 to active reviewer bands
        self.ctrl.handle_event("toggle_mapping_reviewer_band", "B3")
        self.assertIn("B2", self.ctrl.mapping_selected_reviewer_bands)
        self.assertIn("B3", self.ctrl.mapping_selected_reviewer_bands)

        # Select reviewers from B2 and B3
        self.ctrl.handle_event("toggle_mapping_reviewer", "m_b2_1")
        self.ctrl.handle_event("toggle_mapping_reviewer", "m_b3_1")
        self.assertIn("m_b2_1", self.ctrl.mapping_selected_reviewers)
        self.assertIn("m_b3_1", self.ctrl.mapping_selected_reviewers)

        # Send request
        self.ctrl.handle_event("select_mapping_badge", "badge_b1_signals")
        self.ctrl.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2"]
        self.ctrl.handle_event("send_mapping_requests", "{}")
        self.ctrl.handle_event("accept_mapping_request", "req_B1_m_b2_1")

        # Verify Reset demo banner is removed from main g_mapping page, then open badge card detail page
        main_html = self.ctrl.render()
        self.assertNotIn("Reset Everything (Demo Mode)", main_html)
        self.assertNotIn("Reset Workspace", main_html)
        self.ctrl.handle_event("open_mapping_badge_detail", "badge_b1_signals")
        html = self.ctrl.render()
        self.assertIn("Final Review Cohort", html)
        self.assertNotIn("Candidate Cosmonauts &amp; Accepted Reviewers", html)   # sub-title removed

        # Execute map
        self.ctrl.handle_event("execute_cosmonaut_mapping", json.dumps({"band": "B1", "badge_id": "badge_b1_signals", "badge": "Signals Foundations"}))
        mapped_html = self.ctrl.render()
        self.assertIn("Live Mapped Review Allocations", mapped_html)
        self.assertIn("md-alloc-name", mapped_html)      # one allocation card per mapped reviewer
        self.assertIn("md-chip", mapped_html)            # ... listing the cosmonauts mapped to them

        # Test Reset
        self.ctrl.handle_event("reset_all_mapping_state", "{}")
        self.assertEqual(len(store.get_band_mappings()), 0)
        self.assertEqual(len(store.get_mapping_requests()), 0)
        self.assertEqual(len(self.ctrl.mapping_selected_cosmonauts), 0)
        self.assertEqual(len(self.ctrl.mapping_selected_reviewers), 0)

    def test_zero_defaults_select_all_flexible_calendar_and_staged_per_badge_flow(self):
        """
        Verify:
        1. Zero default people are pre-selected on controller init or reset.
        2. Clutter strings & top/calendar Save Mapping button are removed; Select All replaces Select Filtered.
        3. Flexible working-day durations and Start->End range picking work cleanly.
        4. Send Request refreshes badge, cosmonauts, and reviewers and shows collapsed badge card below.
        5. Clicking the badge card opens Requests -> Candidate Cosmonauts & Accepted Reviewers -> Map -> Save Mapping -> Badge-scoped Saved Mapping.
        """
        fresh_ctrl = StarAppController()
        self.assertEqual(fresh_ctrl.mapping_selected_cosmonauts, [])
        self.assertEqual(fresh_ctrl.mapping_selected_reviewers, [])
        self.assertEqual(fresh_ctrl.mapping_selected_badge, "")

        self.ctrl.handle_event("nav_guardian", "g_mapping")
        html = self.ctrl.render()
        self.assertIn("Select All", html)
        self.assertNotIn("Select Filtered", html)
        self.assertNotIn("Multiselect options for cohort roles", html)
        self.assertNotIn("Choose 3-Day Window from Anchor:", html)
        self.assertNotIn("Selected Anchor:", html)
        self.assertNotIn("Guardian Portal", html)
        self.assertNotIn("Real SQLite Data", html)
        before_req_section = html.split("Badge Requests &amp; Mappings")[0]
        self.assertNotIn("Save Mapping", before_req_section)

        # Flexible duration (5 working days)
        self.ctrl.handle_event("set_mapping_review_duration", "5")
        self.assertEqual(self.ctrl.mapping_review_days_count, 5)
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-18")
        self.assertEqual(
            self.ctrl.mapping_review_dates,
            ["2026-11-18", "2026-11-19", "2026-11-20", "2026-11-23", "2026-11-24"]
        )

        # Custom range mode (Start -> End)
        self.ctrl.handle_event("set_mapping_review_mode", "range")
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-19")
        self.assertEqual(self.ctrl.mapping_range_start, "2026-11-19")
        self.ctrl.handle_event("select_mapping_review_anchor", "2026-11-25")
        self.assertEqual(
            self.ctrl.mapping_review_dates,
            ["2026-11-19", "2026-11-20", "2026-11-23", "2026-11-24", "2026-11-25"]
        )

        # Send Request refreshes ALL top selections (badge, cosmonauts, reviewers)
        self.ctrl.handle_event("select_mapping_band", "B1")
        self.ctrl.handle_event("select_all_mapping_cosmonauts", "{}")
        self.assertTrue(len(self.ctrl.mapping_selected_cosmonauts) > 0)
        self.ctrl.handle_event("toggle_mapping_reviewer", "m_b2_1")
        self.ctrl.handle_event("send_mapping_requests", "{}")
        self.assertEqual(self.ctrl.mapping_selected_badge, "")
        self.assertEqual(self.ctrl.mapping_selected_badge_id, "")
        self.assertEqual(self.ctrl.mapping_selected_cosmonauts, [])
        self.assertEqual(self.ctrl.mapping_selected_reviewers, [])

        # Rectangular badge card renders immediately below; details live on the dedicated detail page
        collapsed_html = self.ctrl.render()
        self.assertIn("Signals Foundations", collapsed_html)
        self.assertIn("mapping-badge-rect-card", collapsed_html)
        self.assertIn("Open Requests, Cohort &amp; Mapping", collapsed_html)
        self.assertNotIn("Reviewer Requests History", collapsed_html)

        reqs = [r for r in store.get_mapping_requests() if r.get("band") == "B1"]
        self.assertTrue(len(reqs) >= 1)
        req = reqs[0]
        self.assertEqual(len(req["review_dates"]), 5)
        self.ctrl.handle_event("accept_mapping_request", req["id"])

        # Click the rectangular badge card -> opens dedicated badge mapping detail page
        card_key = req.get("badge_id") or req["badge"]
        self.ctrl.handle_event("open_mapping_badge_detail", json.dumps({"band": "B1", "badge_key": card_key}))
        self.assertEqual(self.ctrl.current_view, "g_mapping_badge_detail")
        expanded_html = self.ctrl.render()
        self.assertIn("Reviewer Requests History", expanded_html)
        self.assertIn("Final Review Cohort", expanded_html)
        self.assertIn("Selected Cosmonauts", expanded_html)
        self.assertIn("Accepted Reviewers", expanded_html)

        # Click Map -> stages preview without committing to DB
        count_before_map = len(store.get_band_mappings())
        payload = json.dumps({"band": "B1", "badge_id": req.get("badge_id", ""), "badge": req["badge"]})
        self.ctrl.handle_event("preview_cosmonaut_mapping", payload)
        self.assertEqual(len(store.get_band_mappings()), count_before_map)
        staged_html = self.ctrl.render()
        self.assertIn("Proposed Assignment Partition", staged_html)
        self.assertIn("Save Mapping", staged_html)

        # Click Save Mapping -> commits staged preview & displays inside that badge's detail page
        self.ctrl.handle_event("save_staged_mapping", payload)
        self.assertEqual(len(store.get_band_mappings()), count_before_map + 1)
        saved_card_html = self.ctrl.render()
        self.assertIn("Live Mapped Review Allocations", saved_card_html)

        # Back button returns smoothly to g_mapping
        self.ctrl.handle_event("go_back", "{}")
        self.assertEqual(self.ctrl.current_view, "g_mapping")

        # Verify Liquid-Glass Timeline & Mapping modal in Badge Allotment
        self.ctrl.handle_event("open_badge_timeline_mapping_modal", card_key)
        modal_html = self.ctrl.render_active_modal()
        self.assertIn("tm-steps", modal_html)        # numbered, editable timeline
        self.assertIn("tm-head", modal_html)
        self.assertIn("lg-mapping-glass-card", modal_html)
        self.ctrl.handle_event("close_modal", "{}")

        # Dispatch request for a second B1 badge independently
        self.ctrl.handle_event("select_mapping_badge", json.dumps({"badge_id": "b1_int_01", "badge": "Intelligent Apps Foundations"}))
        self.ctrl.mapping_selected_cosmonauts = ["m_b1_1"]
        self.ctrl.mapping_selected_reviewers = ["m_b2_2"]
        self.ctrl.handle_event("send_mapping_requests", "{}")
        self.assertEqual(self.ctrl.mapping_selected_badge, "")
        self.assertEqual(self.ctrl.mapping_expanded_badge_key, "")
        multi_html = self.ctrl.render()
        self.assertIn("Signals Foundations", multi_html)
        self.assertIn("Intelligent Apps Foundations", multi_html)
        self.assertNotIn("Live Mapped Review Allocations", multi_html)

if __name__ == "__main__":
    unittest.main()
