"""
Phase 9 Regression Tests: UI Flickering, 3-Region Rendering & Asset Remediation.
Validates navigation stability, session restoration, stale async render guards,
3-region payload separation, modal lifecycle stability, single-dispatch PDF
preview markup, accessible tooltip siblings, and CSS/bridge invariants.
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from starapp.app import StarAppController
from starapp.storage import store


class TestUIRemediation(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        self.captured_regions = []

        orig_dispatch = self.ctrl._dispatch_browser_render

        def capture_dispatch(regions_payload, full_html):
            self.captured_regions.append(regions_payload)
            return orig_dispatch(regions_payload, full_html)

        self.ctrl._dispatch_browser_render = capture_dispatch

    def _login(self, username: str):
        self.ctrl.handle_event("login", json.dumps({"username": username}))
        self.assertIsNotNone(self.ctrl.current_user)

    def test_guardian_all_views_and_session_restore_includes_g_allotment(self):
        """Every Guardian view renders cleanly and g_allotment is restorable from sessionStorage."""
        session_json = json.dumps({"user_id": "guardian_1", "current_view": "g_allotment"})
        self.ctrl.initialize(None, session_json)
        self.assertEqual(self.ctrl.current_view, "g_allotment")
        self.assertIn("g_allotment", StarAppController._GUARDIAN_VIEWS)

        guardian_views = [
            "g_dashboard",
            "g_allotment",
            "g_reviews",
            "g_review_detail",
            "g_materials",
            "g_extensions",
            "g_announcements",
            "g_activity",
        ]
        for view in guardian_views:
            self.ctrl.handle_event("nav_guardian", view)
            self.assertEqual(self.ctrl.current_view, view)
            payload = self.captured_regions[-1]
            self.assertEqual(payload["mode"], "workspace")
            self.assertTrue(payload["mainContentHtml"].strip())
            self.assertIn('id="starapp-shell-sidebar"', payload["sidebarHtml"])

    def test_cosmonaut_all_views_render_cleanly_with_persistent_region_markers(self):
        """Every Cosmonaut view emits the 3-region DOM shell markers and stable portalKey."""
        self._login("astraea")
        first_portal_key = self.captured_regions[-1]["portalKey"]

        cosmo_views = [
            "c_dashboard",
            "c_roadmap",
            "c_submission",
            "c_results",
            "c_materials",
            "c_profile",
            "c_announcements",
            "c_extensions",
            "c_activity",
        ]
        for view in cosmo_views:
            self.ctrl.handle_event("nav_cosmonaut", view)
            self.assertEqual(self.ctrl.current_view, view)
            payload = self.captured_regions[-1]
            self.assertEqual(payload["portalKey"], first_portal_key)
            self.assertEqual(payload["routeKey"], view)
            self.assertIn('id="starapp-shell-sidebar"', payload["sidebarHtml"])

        full_html = self.ctrl.render()
        for region_id in (
            'id="starapp-shell-sidebar"',
            'id="starapp-main-viewport"',
            'id="starapp-page-slot"',
            'id="starapp-flash-slot"',
            'id="starapp-page-body"',
            'id="starapp-modal-root"',
        ):
            self.assertIn(region_id, full_html)

    def test_stale_async_render_generation_guard(self):
        """Stale reload_data calls with older expected_generation must be ignored without overwriting newer navigation."""
        self._login("astraea")
        self.ctrl.handle_event("nav_cosmonaut", "c_roadmap")
        gen_before = self.ctrl.render_generation
        count_before = len(self.captured_regions)

        stale_snapshot = store.to_json()
        self.ctrl.handle_event("nav_cosmonaut", "c_submission")
        self.assertGreater(self.ctrl.render_generation, gen_before)
        count_after_nav = len(self.captured_regions)

        # Older generation reload must no-op cleanly
        self.ctrl.reload_data(stale_snapshot, expected_generation=gen_before)
        self.assertEqual(self.ctrl.current_view, "c_submission")
        self.assertEqual(len(self.captured_regions), count_after_nav)

        # Matching current generation marks payload as cross-tab reload
        self.ctrl.reload_data(stale_snapshot, expected_generation=self.ctrl.render_generation)
        self.assertEqual(len(self.captured_regions), count_after_nav + 1)
        self.assertTrue(self.captured_regions[-1]["isCrossTabReload"])
        self.assertGreater(count_after_nav, count_before)

    def test_modal_lifecycle_preserves_page_region_and_stable_modal_key(self):
        """Opening and closing a modal leaves mainContentHtml & routeKey unchanged."""
        self._login("astraea")
        self.ctrl.handle_event("nav_cosmonaut", "c_roadmap")
        page_snapshot = self.captured_regions[-1]

        self.ctrl.handle_event("open_badge_detail_modal", "badge_gov_101")
        open_snapshot = self.captured_regions[-1]
        self.assertEqual(open_snapshot["activeModal"], "badge_detail")
        self.assertIn("badge_gov_101", open_snapshot["modalKey"])
        self.assertEqual(open_snapshot["routeKey"], page_snapshot["routeKey"])
        self.assertEqual(open_snapshot["mainContentHtml"], page_snapshot["mainContentHtml"])

        self.ctrl.handle_event("close_modal", "{}")
        closed_snapshot = self.captured_regions[-1]
        self.assertEqual(closed_snapshot["activeModal"], "")
        self.assertEqual(closed_snapshot["modalHtml"], "")
        self.assertEqual(closed_snapshot["mainContentHtml"], page_snapshot["mainContentHtml"])

    def test_review_detail_tab_switch_preserves_route_key_and_removes_iframe_translatez(self):
        """Switching g_review_detail viewer tabs keeps the same routeKey and clean PDF iframe wrapper."""
        self._login("guardian")
        subs = store.get_all_submissions()
        self.assertTrue(subs)
        sub_id = subs[0].id

        self.ctrl.handle_event("open_submission_review_page", sub_id)
        pdf_payload = self.captured_regions[-1]
        self.assertEqual(pdf_payload["routeKey"], f"g_review_detail:{sub_id}")
        self.assertEqual(pdf_payload["pageContainerClass"], "page-container page-review-detail")
        self.assertIn('id="pdf-document-frame"', pdf_payload["mainContentHtml"])
        self.assertNotIn("isolation:isolate; transform:translateZ(0);", pdf_payload["mainContentHtml"])

        self.ctrl.handle_event("change_viewer_tab", "code")
        code_payload = self.captured_regions[-1]
        self.assertEqual(code_payload["routeKey"], f"g_review_detail:{sub_id}")
        self.assertNotEqual(code_payload["mainContentHtml"], pdf_payload["mainContentHtml"])

    def test_materials_pdf_overlay_single_dispatch_and_focus_id(self):
        """Materials view uses a single view_material_preview onclick per card and stable filter select id."""
        self._login("guardian")
        self.ctrl.handle_event(
            "save_bulk_materials",
            json.dumps({
                "badge_id": "badge_ing_104",
                "topic": "Remediation Verification PDF",
                "description": "Single-dispatch verification artifact.",
                "pdfs": [{"name": "Remediation_Spec.pdf", "dataUrl": "data:application/pdf;base64,JVBERi0xLjQK"}],
                "youtube_links": [],
            }),
        )
        mats = store.get_materials("badge_ing_104")
        self.assertEqual(len(mats), 1)
        mat_id = mats[0].id

        self.ctrl.handle_event("nav_guardian", "g_materials")
        html = self.captured_regions[-1]["mainContentHtml"]

        self.assertIn('id="materials-badge-filter-select"', html)
        self.assertIn('for="materials-badge-filter-select"', html)
        # Exactly one dispatch on .media-pdf-box and one on the explicit Theater View button
        pdf_box_match = re.search(r'<div class="media-pdf-box".*?</div>\s*</div>', html, re.S)
        self.assertIsNotNone(pdf_box_match)
        box_occurrences = len(re.findall(r"view_material_preview'\s*,\s*'" + re.escape(mat_id) + "'", pdf_box_match.group(0)))
        self.assertEqual(box_occurrences, 1)
        total_occurrences = len(re.findall(r"view_material_preview'\s*,\s*'" + re.escape(mat_id) + "'", html))
        self.assertEqual(total_occurrences, 2)

        # Clicking preview opens material_preview modal cleanly
        self.ctrl.handle_event("view_material_preview", mat_id)
        modal_html = self.captured_regions[-1]["modalHtml"]
        self.assertIn("Remediation Spec", modal_html)
        self.assertIn("Open in Full Tab", modal_html)

    def test_tooltip_popover_sibling_structure_and_no_inline_mouseover(self):
        """Tooltip popovers are siblings outside <button>, and roadmap nodes use CSS hover rather than inline JS."""
        self._login("guardian")
        self.ctrl.handle_event("nav_guardian", "g_dashboard")
        g_html = self.captured_regions[-1]["mainContentHtml"]
        self.assertNotRegex(
            g_html,
            r'<button[^>]*class="metric-info-trigger"[^>]*>[^<]*<div class="glass-tooltip-popover',
        )

        self._login("astraea")
        self.ctrl.handle_event("nav_cosmonaut", "c_dashboard")
        c_dash_html = self.captured_regions[-1]["mainContentHtml"]
        self.assertNotRegex(
            c_dash_html,
            r'<button[^>]*class="metric-info-trigger"[^>]*>[^<]*<div class="glass-tooltip-popover',
        )

        self.ctrl.handle_event("nav_cosmonaut", "c_roadmap")
        roadmap_html = self.captured_regions[-1]["mainContentHtml"]
        self.assertIn("milestone-container-node", roadmap_html)
        self.assertNotIn("onmouseover=", roadmap_html)
        self.assertNotIn("onmouseout=", roadmap_html)

    def test_static_css_bridge_and_sw_invariants(self):
        """Verify bridge guards, CSS transition hygiene, SVG cleanup, and versioned SW cache exist."""
        css_dir = ROOT_DIR / "css"
        for css_file in css_dir.glob("*.css"):
            content = css_file.read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(r"transition\s*:\s*all\b", content),
                f"Disallowed 'transition: all' found in {css_file.name}",
            )

        bridge_js = (ROOT_DIR / "js" / "bridge.js").read_text(encoding="utf-8")
        for symbol in (
            "updateRegions",
            "localActionSeq",
            "lastKnownDataJson",
            "pendingSyncTimer",
            "_captureScrolls",
            "_restoreScrolls",
            "isActivelyEditingFormControl",
            "modal-no-replay",
        ):
            self.assertIn(symbol, bridge_js)

        index_html = (ROOT_DIR / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("glass-svg-defs", index_html)
        self.assertIn("js/bridge.js?v=9", index_html)
        self.assertIn("js/starapp_bundle.js?v=9", index_html)

        sw_js = (ROOT_DIR / "sw.js").read_text(encoding="utf-8")
        self.assertIn("starapp-runtime-cache-v2", sw_js)
        self.assertIn("./css/liquid_glass.css?v=9", sw_js)


if __name__ == "__main__":
    unittest.main()
