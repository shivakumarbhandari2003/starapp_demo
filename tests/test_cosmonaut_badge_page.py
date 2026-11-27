"""
Cosmonaut badge page: the badge in the same glass structure the Guardian / reviewer use, with Reviewer and Timeline buttons on the
badge-name line (live modals), no back rows / chips / description / reviewer banner, and the project shown ONLY from
"Project Allocated" (never inside the badge).
"""
import json
import os
import unittest

from starapp.app import StarAppController
from starapp.badge_generator import compose_project_content, generate_project_brief
from starapp.storage import store

BADGE = "b1_dat_01"
PAYLOAD = {"band": "B1", "badge_id": BADGE, "badge": "Data Systems Architecture"}


def _login(uid):
    c = StarAppController()
    c.initialize()
    c.handle_event("select_demo_account", uid)
    return c


class CosmonautBadgeBase(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        g = _login("guardian_1")
        g.handle_event("select_create_badge_band", "B1")
        g.handle_event("nav_guardian", "g_mapping")
        g.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4"]
        g.mapping_selected_reviewers = ["m_b2_1", "m_b2_2"]
        g.mapping_selected_badge = "Data Systems Architecture"
        g.handle_event("send_mapping_requests", "{}")
        for req in store.get_mapping_requests():
            _login(req["reviewer_id"]).handle_event("accept_mapping_request", req["id"])
        g.handle_event("select_demo_account", "guardian_1")
        g.handle_event("preview_cosmonaut_mapping", PAYLOAD)
        g.handle_event("save_staged_mapping", PAYLOAD)
        g.handle_event("publish_badge", BADGE)
        self.rev_id = store.get_mapped_reviewer_id(BADGE, "m_b1_2")
        self.cid = "m_b1_2"

    def tearDown(self):
        store.reset_to_seed()

    def page(self, uid=None):
        c = _login(uid or self.cid)
        c.handle_event("nav_cosmonaut", "c_submission")
        c.handle_event("open_cosmonaut_badge_page", BADGE)
        c.render()
        return c, c.last_rendered_regions["mainContentHtml"]


class TestBadgePageStructure(CosmonautBadgeBase):
    def test_removed_chrome_is_gone(self):
        _, html = self.page()
        for gone in ("Back to Badges", "Back to All Badges", "Badge Workspace", "B1-DAT-01", "Assigned Peer Reviewer", "Review Window:",
                     "Submission Deadline:", "specializing in", "Allocated Badge"):
            self.assertNotIn(gone, html, gone)

    def test_badge_uses_the_shared_structured_document_in_glass(self):
        _, html = self.page()
        for part in ('id="created-badge-display-area"', "badge-section-outcomes", "badge-section-earn", "badge-section-practice",
                     "badge-section-topics", "badge-section-resources", "badge-section-related", "Badge Location", "cbp-page"):
            self.assertIn(part, html, part)
        self.assertNotIn("Created Badge Location", html)
        self.assertNotIn("Save Badge", html)                         # none of the Guardian's authoring controls
        self.assertNotIn("edit-badge-title-input", html)

    def test_reviewer_and_timeline_buttons_sit_on_the_badge_name_line(self):
        _, html = self.page()
        line = html.split("cb-title-actions")[1].split("</div>")[0]
        self.assertIn("open_cosmonaut_reviewer_modal", line)
        self.assertIn("open_cosmonaut_timeline_modal", line)
        self.assertIn("Reviewer", line)
        self.assertIn("Timeline", line)
        before = html.split("cb-title-actions")[0]
        self.assertIn("Data Systems Architecture", before.split("created-badge-display-area")[1])    # the title is on that same row

    def test_the_project_is_never_shown_inside_the_badge(self):
        _login(self.rev_id).handle_event("send_reviewer_project", json.dumps({
            "badge_id": BADGE, "title": "Hidden-from-badge Project", "content": compose_project_content(generate_project_brief(store.get_badge(BADGE))),
            "cosmonaut_ids": [self.cid]}))
        c, html = self.page()
        self.assertIn("pa-btn is-ready", html)
        for gone in ("Hidden-from-badge Project", "badge-section-allocated-project", "Your Project", "Submit Deliverables", "Case Study"):
            self.assertNotIn(gone, html, gone)
        c.handle_event("open_allocated_project_page", BADGE)                  # "Project Allocated" opens the project PAGE, not a popup
        self.assertEqual(c.current_view, "c_project")
        self.assertIsNone(c.active_modal)
        c.render()
        page = c.last_rendered_regions["mainContentHtml"]
        for part in ("Hidden-from-badge Project", "Case Study", "Submit Deliverables"):
            self.assertIn(part, page, part)


class TestReviewerAndTimelinePopups(CosmonautBadgeBase):
    def test_reviewer_popup_shows_the_mapped_reviewer_and_project_state(self):
        c, _ = self.page()
        c.handle_event("open_cosmonaut_reviewer_modal", BADGE)
        self.assertEqual(c.active_modal, "cosmonaut_reviewer_view")
        m = c.render_active_modal()
        self.assertIn(store.get_user_by_id(self.rev_id).name, m)
        for part in ("Mapped to you", "Review window", "Submission deadline", "Project pending", "left to send projects".replace("left to send projects", "until it is sent"), 'data-live-sync="reviewer"'):
            self.assertIn(part, m, part)
        other = "m_b2_1" if self.rev_id == "m_b2_2" else "m_b2_2"
        self.assertNotIn(store.get_user_by_id(other).name, m)             # only THEIR reviewer

    def test_popups_update_when_the_state_changes(self):
        c, _ = self.page()
        c.handle_event("open_cosmonaut_reviewer_modal", BADGE)
        self.assertIn("Project pending", c.render_active_modal())
        _login(self.rev_id).handle_event("send_reviewer_project", json.dumps({
            "badge_id": BADGE, "title": "P", "content": "Case Study" + chr(10) + "A." + chr(10) + chr(10) + "Your Challenge" + chr(10) + "B.", "cosmonaut_ids": [self.cid]}))
        c.handle_event("sync_badge_reviews")                              # what the browser's live sync sends
        m = c.render_active_modal()
        self.assertIn("Project sent", m)
        self.assertNotIn("Project pending", m)

    def test_timeline_popup_is_the_cosmonauts_own_connected_dot_timeline(self):
        c, _ = self.page()
        c.handle_event("open_cosmonaut_timeline_modal", BADGE)
        self.assertEqual(c.active_modal, "cosmonaut_timeline_view")
        m = c.render_active_modal()
        for part in ("tlv-steps", "Project from your reviewer", "Learning period", "Project sprint", "Submission deadline", "Review window",
                     "Certification award", "until your project is sent", 'data-live-sync="timeline"'):
            self.assertIn(part, m, part)
        self.assertEqual(m.count('<li class="tlv-step'), 7)
        self.assertNotIn("Create Project", m)                              # reviewer-only wording / actions

    def test_timeline_step_flips_to_done_once_the_project_arrives(self):
        c, _ = self.page()
        _login(self.rev_id).handle_event("send_reviewer_project", json.dumps({
            "badge_id": BADGE, "title": "P", "content": "Case Study" + chr(10) + "A." + chr(10) + chr(10) + "Your Challenge" + chr(10) + "B.", "cosmonaut_ids": [self.cid]}))
        c.handle_event("open_cosmonaut_timeline_modal", BADGE)
        m = c.render_active_modal()
        self.assertIn("Project received", m)
        self.assertIn(">Received<", m)

    def test_only_a_cosmonaut_the_badge_is_allotted_to_can_open_them(self):
        outsider = _login("m_b1_6")                                       # not mapped to this badge
        for action in ("open_cosmonaut_reviewer_modal", "open_cosmonaut_timeline_modal"):
            outsider.handle_event(action, BADGE)
            self.assertIsNone(outsider.active_modal, action)
        c, _ = self.page()
        c.handle_event("open_cosmonaut_reviewer_modal", "no-such-badge")
        self.assertIsNone(c.active_modal)

    def test_no_reviewer_mapped_says_so(self):
        from starapp.views_cosmonaut import render_cosmonaut_reviewer_modal

        class NoReviewerStore:                                            # a cosmonaut nobody has mapped a reviewer to yet
            def get_timeline(self, *a):
                return None

            def get_mapped_reviewer_id(self, *a):
                return ""

        user = store.get_user_by_id("m_b1_6")
        html = render_cosmonaut_reviewer_modal(store.get_badge(BADGE), user, NoReviewerStore())
        self.assertIn("No reviewer mapped yet", html)
        self.assertIn("updates by itself", html)
        self.assertIn('data-live-sync="reviewer"', html)


class TestLiveUpdates(CosmonautBadgeBase):
    def test_page_and_popups_carry_the_live_sync_marker_and_the_bridge_polls(self):
        _, html = self.page()
        self.assertIn('data-live-sync="badge"', html)
        js = open(os.path.join(os.path.dirname(__file__), "..", "js", "bridge.js"), encoding="utf-8").read()
        self.assertIn("startLiveSync", js)
        self.assertIn("data-live-sync", js)
        self.assertIn('dispatchAction("sync_badge_reviews"', js)
        self.assertIn("sync_badge_reviews", StarAppController._CYCLE_READONLY_SAFE_ACTIONS)

    def test_the_locked_button_unlocks_on_the_next_sync(self):
        c, html = self.page()
        self.assertIn("pa-btn is-locked", html)
        _login(self.rev_id).handle_event("send_reviewer_project", json.dumps({
            "badge_id": BADGE, "title": "P", "content": "Case Study" + chr(10) + "A." + chr(10) + chr(10) + "Your Challenge" + chr(10) + "B.", "cosmonaut_ids": [self.cid]}))
        c.handle_event("sync_badge_reviews")
        c.render()
        html = c.last_rendered_regions["mainContentHtml"]
        self.assertIn("pa-btn is-ready", html)
        self.assertNotIn("pa-btn is-locked", html)


if __name__ == "__main__":
    unittest.main()
