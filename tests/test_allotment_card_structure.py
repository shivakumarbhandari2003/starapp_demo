"""
Badge Allotment card: plain glass card (no highlighted border); the data is one click away behind two separate buttons,
Mapping and Timeline; the only buttons underneath are Edit (left) and Publish / Revoke (right).
"""
import os
import unittest

from starapp.app import StarAppController
from starapp.storage import store

BADGE = "badge_b1_signals"            # published in the seed


def _guardian(*steps):
    c = StarAppController()
    c.initialize()
    c.handle_event("select_demo_account", "guardian_1")
    for a, p in steps:
        c.handle_event(a, p)
    return c


def _card_parts(c, title):
    """(everything above the action row, the action row) of one allotment card."""
    c.render()
    html = c.last_rendered_regions["mainContentHtml"]
    after = html.split(f"{title}</h3>")[1]
    top, rest = after.split('<div class="lg-allot-actions">', 1)
    return top, rest.split("</div>\n        </div>", 1)[0]


class TestAllotmentCardButtons(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.g = _guardian(("select_create_badge_band", "B1"), ("nav_guardian", "g_allotment"))

    def test_card_has_two_view_buttons_and_no_inline_data(self):
        top, _ = _card_parts(self.g, "Signals Foundations")
        self.assertEqual(top.count("lg-allot-view-btn"), 2)
        self.assertIn("open_badge_mapping_modal", top)
        self.assertIn("open_badge_timeline_modal", top)
        for gone in ("Rohan Deshmukh", "Mapped Cadets", "allot-rev", "lg-allot-meta-cell"):
            self.assertNotIn(gone, top, gone)

    def test_review_window_and_submission_date_sit_under_the_two_buttons(self):
        top, _ = _card_parts(self.g, "Signals Foundations")
        self.assertLess(top.rindex("lg-allot-view-btn"), top.index("lg-allot-dates"))
        dates = top.split("lg-allot-dates")[1]
        for part in ("Review Window", "Submission Date", "15 Dec 2026", "12 Dec 2026", "working day"):
            self.assertIn(part, dates, part)

    def test_edit_and_publish_buttons_are_small(self):
        css = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()
        rule = css.split(".lg-allot-actions .lg-allot-btn {")[1].split("}")[0]
        self.assertIn("min-height: 32px", rule)
        self.assertIn("font-size: 0.8125rem", rule)
        self.assertNotIn("46%", css)

    def test_only_edit_left_and_publish_or_revoke_right_underneath(self):
        for title, expect in (("Signals Foundations", "Revoke"), ("Data Systems Architecture", "Publish")):
            _, bottom = _card_parts(self.g, title)
            self.assertEqual(bottom.count("<button"), 2, title)
            self.assertLess(bottom.index("open_edit_badge_modal"), bottom.index(expect), title)     # Edit first (left), then the action
            self.assertNotIn("open_badge_timeline", bottom)

    def test_no_highlighted_border_on_published_or_mapped_cards(self):
        self.g.render()
        html = self.g.last_rendered_regions["mainContentHtml"]
        self.assertNotIn("lg-allot-card is-published", html)
        self.assertNotIn("lg-allot-card is-mapped", html)
        css = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()
        self.assertNotIn(".lg-allot-card.is-published", css)
        self.assertNotIn(".lg-allot-card.is-mapped", css)


class TestMappingAndTimelineModals(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.g = _guardian(("select_create_badge_band", "B1"), ("nav_guardian", "g_allotment"))

    def test_mapping_button_shows_reviewers_and_their_cosmonauts_only(self):
        self.g.handle_event("open_badge_mapping_modal", BADGE)
        self.assertEqual(self.g.active_modal, "badge_mapping_view")
        m = self.g.render_active_modal()
        for part in ("Personnel Mapping", "Assigned Cosmonauts", "Rohan Deshmukh", "tm-rev"):
            self.assertIn(part, m, part)
        # Badge -> Reviewer -> Cosmonaut hierarchy, glass nodes, no coloured side-border cards
        # the SAME tree as the Assessment Dashboard: badge node -> reviewer panels -> cosmonaut cards, same elbows / ringed dots
        for part in ("asm-tree-root", "asm-tree-badge-node", "asm-tree-trunk", "asm-tree-reviewer-branch", "asm-reviewer-panel",
                     "asm-tree-cosmo-list", "asm-tree-cosmo-branch", "asm-elbow", "asm-cosmonaut-card is-static", "Review window", "Submission deadline"):
            self.assertIn(part, m, part)
        self.assertNotIn("mp-tree", m)                                  # the earlier custom connector markup is gone
        css = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()
        self.assertNotIn(".mp-tree", css)
        self.assertEqual(m.count("asm-tree-cosmo-branch"), m.count("asm-elbow"))      # every cosmonaut has its elbow
        self.assertNotIn("Milestone Timeline Schedule", m)
        self.assertNotIn("tm-steps", m)

    def test_timeline_button_shows_the_schedule_only(self):
        self.g.handle_event("open_badge_timeline_modal", BADGE)
        self.assertEqual(self.g.active_modal, "badge_timeline_view")
        m = self.g.render_active_modal()
        for part in ("Milestone Timeline Schedule", "Submission Deadline", "Review Date", "Read-only view"):
            self.assertIn(part, m, part)
        self.assertNotIn("Personnel Mapping", m)
        self.assertNotIn("<input", m)

    def test_modal_titles_and_size(self):
        self.g.handle_event("open_badge_mapping_modal", BADGE)
        self.g.render()
        self.assertIn("modal-xl", self.g.last_rendered_regions["modalHtml"])
        self.assertIn("Mapping —", self.g.last_rendered_regions["modalHtml"])
        self.g.handle_event("open_badge_timeline_modal", BADGE)
        self.g.render()
        self.assertIn("Timeline —", self.g.last_rendered_regions["modalHtml"])

    def test_legacy_combined_modal_still_has_both(self):
        self.g.handle_event("open_badge_timeline_mapping_modal", BADGE)
        m = self.g.render_active_modal()
        self.assertIn("Personnel Mapping", m)
        self.assertIn("Milestone Timeline Schedule", m)


class TestOnlyGuardiansSeeWhoIsMappedToWhom(unittest.TestCase):
    def test_other_roles_cannot_open_the_mapping_or_timeline_modals(self):
        store.reset_to_seed()
        for user in ("m_b2_1", "m_b1_1"):
            c = StarAppController()
            c.initialize()
            c.handle_event("select_demo_account", user)
            for action in ("open_badge_mapping_modal", "open_badge_timeline_modal", "open_badge_timeline_mapping_modal"):
                self.assertIn(action, StarAppController._GUARDIAN_ONLY_ACTIONS)
                c.handle_event(action, BADGE)
                self.assertIsNone(c.active_modal, (user, action))


if __name__ == "__main__":
    unittest.main()


class TestPublishAndRevokeConfirmation(unittest.TestCase):
    """Publish / Revoke ask first, in the app's own glass dialog (no browser confirm()); only OK changes anything."""

    UNPUBLISHED = "b1_dat_01"

    def setUp(self):
        store.reset_to_seed()
        self.g = _guardian(("select_create_badge_band", "B1"), ("nav_guardian", "g_allotment"))

    def tearDown(self):
        store.reset_to_seed()            # these tests publish / revoke badges; leave the shared store as they found it

    def test_buttons_open_the_dialog_instead_of_a_browser_confirm(self):
        self.g.render()
        html = self.g.last_rendered_regions["mainContentHtml"]
        self.assertIn("confirm_publish_badge", html)
        self.assertIn("confirm_revoke_badge", html)
        self.assertNotIn("confirm(", html)
        self.assertNotIn("publishBadge", html)
        js = open(os.path.join(os.path.dirname(__file__), "..", "js", "bridge.js"), encoding="utf-8").read()
        self.assertNotIn('confirm("Publish', js)
        self.assertIn('dispatchAction("confirm_publish_badge"', js)

    def test_publish_dialog_asks_and_cancel_changes_nothing(self):
        self.g.handle_event("confirm_publish_badge", self.UNPUBLISHED)
        self.assertEqual(self.g.active_modal, "badge_publish_confirm")
        self.assertFalse(store.get_badge(self.UNPUBLISHED).is_published)
        self.g.render()
        m = self.g.last_rendered_regions["modalHtml"]
        for part in ("Publish Badge to Roadmap", "Data Systems Architecture", "goes live on the Cosmonaut roadmap", "Cancel", "Publish Badge", "rc-confirm is-publish"):
            self.assertIn(part, m, part)
        self.g.handle_event("close_modal", "{}")                         # Cancel
        self.assertFalse(store.get_badge(self.UNPUBLISHED).is_published)

    def test_ok_publishes_and_closes_the_dialog(self):
        self.g.handle_event("confirm_publish_badge", self.UNPUBLISHED)
        self.g.handle_event("publish_badge", self.UNPUBLISHED)          # the dialog's confirm button
        b = store.get_badge(self.UNPUBLISHED)
        self.assertTrue(b.is_published)
        self.assertIsNone(self.g.active_modal)

    def test_revoke_dialog_asks_then_revokes(self):
        self.g.handle_event("confirm_revoke_badge", BADGE)
        self.assertEqual(self.g.active_modal, "badge_revoke_confirm")
        self.assertTrue(store.get_badge(BADGE).is_published)
        self.g.render()
        m = self.g.last_rendered_regions["modalHtml"]
        self.assertIn("Revoke Badge from Roadmap", m)
        self.assertIn("Keep Published", m)
        self.g.handle_event("revoke_badge", BADGE)
        self.assertFalse(store.get_badge(BADGE).is_published)
        self.assertIsNone(self.g.active_modal)

    def test_only_guardians_can_open_the_dialogs(self):
        for user in ("m_b2_1", "m_b1_1"):
            c = StarAppController()
            c.initialize()
            c.handle_event("select_demo_account", user)
            for action in ("confirm_publish_badge", "confirm_revoke_badge"):
                self.assertIn(action, StarAppController._GUARDIAN_ONLY_ACTIONS)
                c.handle_event(action, self.UNPUBLISHED)
                self.assertIsNone(c.active_modal)
