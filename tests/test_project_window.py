"""
72-hour project window.

When the Guardian publishes a badge, every mapped reviewer gets a live 72-hour countdown (from the moment of publishing) to
create the project and send it to all their mapped cosmonauts. The cosmonaut's "Earn the Badge" shows a DISABLED
"Project Allocated" button until the reviewer sends the project; then it unlocks and opens the project, which holds the
Submit Deliverables button.
"""
import datetime
import json
import unittest

from starapp.app import StarAppController
from starapp.database import PROJECT_WINDOW_HOURS
from starapp.storage import project_window_seconds_left, store

BADGE = "b1_dat_01"
PAYLOAD = {"band": "B1", "badge_id": BADGE, "badge": "Data Systems Architecture"}
BRIEF = "Case Study" + chr(10) + "A warehouse." + chr(10) + chr(10) + "Your Challenge" + chr(10) + "Design a pipeline."


def _login(uid):
    c = StarAppController()
    c.initialize()
    c.handle_event("select_demo_account", uid)
    return c


def _main(c):
    c.render()
    return c.last_rendered_regions["mainContentHtml"]


class PublishedBadgeBase(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.g = _login("guardian_1")
        self.g.handle_event("select_create_badge_band", "B1")
        self.g.handle_event("nav_guardian", "g_mapping")
        self.g.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4"]
        self.g.mapping_selected_reviewers = ["m_b2_1", "m_b2_2"]
        self.g.mapping_selected_badge = "Data Systems Architecture"
        self.g.handle_event("send_mapping_requests", "{}")
        for req in store.get_mapping_requests():
            _login(req["reviewer_id"]).handle_event("accept_mapping_request", req["id"])
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("preview_cosmonaut_mapping", PAYLOAD)
        self.g.handle_event("save_staged_mapping", PAYLOAD)
        self.g.handle_event("publish_badge", BADGE)
        self.assertTrue(store.get_badge(BADGE).is_published)

    def tearDown(self):
        store.reset_to_seed()

    def mapped(self, reviewer_id):
        return sorted(store.get_reviewer_mapped_cosmonaut_ids(reviewer_id, BADGE))

    def schedule(self, reviewer_id):
        r = _login(reviewer_id)
        r.handle_event("nav_cosmonaut", "c_badge_reviews")
        return _main(r)


class TestWindowStartsAtPublish(PublishedBadgeBase):
    def test_publish_stamps_the_time_and_the_window_is_72_hours(self):
        self.assertEqual(PROJECT_WINDOW_HOURS, 72)
        left = project_window_seconds_left(store.get_badge(BADGE).published_at)
        self.assertTrue(72 * 3600 - 60 < left <= 72 * 3600)

    def test_helper_edge_cases(self):
        now = datetime.datetime(2026, 11, 27, 12, 0, tzinfo=datetime.timezone.utc)
        self.assertIsNone(project_window_seconds_left("", now))
        self.assertEqual(project_window_seconds_left("2026-11-27T12:00:00+00:00", now), 72 * 3600)
        self.assertEqual(project_window_seconds_left("2026-11-26T12:00:00+00:00", now), 48 * 3600)
        self.assertEqual(project_window_seconds_left("2026-11-20T12:00:00+00:00", now), 0)      # never negative

    def test_every_mapped_reviewer_is_told_they_have_72_hours(self):
        for rid in ("m_b2_1", "m_b2_2"):
            msgs = [n.message for n in store.get_notifications(rid) if "published" in n.message.lower()]
            self.assertTrue(any("72 hours" in m for m in msgs), (rid, msgs))


class TestReviewerCountdown(PublishedBadgeBase):
    def test_each_reviewer_sees_a_live_countdown_on_their_badge(self):
        for rid in ("m_b2_1", "m_b2_2"):
            html = self.schedule(rid)
            self.assertIn("Project window", html)
            self.assertIn("left to send projects", html)
            self.assertIn('data-sync="sync_badge_reviews"', html)
            left = int(html.split('data-remaining="', 1)[1].split('"', 1)[0])
            self.assertTrue(72 * 3600 - 120 < left <= 72 * 3600, (rid, left))

    def test_header_shows_the_values_and_one_create_project_button(self):
        html = self.schedule("m_b2_2")
        head = html.split('class="rv-badge-card"')[1].split("rv-tree")[0]
        for part in ("Review window", "Submission deadline", "Project window", "Create Project", "mapped cosmonaut"):
            self.assertIn(part, head, part)
        self.assertEqual(head.count("rv-create"), 1)

    def test_cosmonauts_hang_off_the_connected_dot_tree(self):
        html = self.schedule("m_b2_2")
        n = len(self.mapped("m_b2_2"))
        self.assertGreaterEqual(n, 1)
        self.assertEqual(html.count("asm-tree-cosmo-branch"), n)
        self.assertEqual(html.count("asm-elbow"), n)
        self.assertIn("asm-cosmonaut-card is-static is-wide", html)
        for gone in ("liquid-glass-card\" style=\"padding:18px 22px; border:1.5px solid var(--icy-steel)", "Cadet Assessments"):
            self.assertNotIn(gone, html)

    def test_the_countdown_goes_away_once_every_project_is_sent(self):
        rev = _login("m_b2_2")
        ids = self.mapped("m_b2_2")
        rev.handle_event("send_reviewer_project", json.dumps({"badge_id": BADGE, "title": "Pipeline", "content": BRIEF, "cosmonaut_ids": ids}))
        rev.handle_event("nav_cosmonaut", "c_badge_reviews")
        html = _main(rev)
        self.assertIn("All projects sent", html)
        self.assertNotIn("left to send projects", html)
        self.assertNotIn("Project pending", html)

    def test_a_partial_send_keeps_the_countdown_for_the_rest(self):
        rev = _login("m_b2_2")
        ids = self.mapped("m_b2_2")
        rev.handle_event("send_reviewer_project", json.dumps({"badge_id": BADGE, "title": "Pipeline", "content": BRIEF, "cosmonaut_ids": ids[:1]}))
        rev.handle_event("nav_cosmonaut", "c_badge_reviews")
        html = _main(rev)
        self.assertIn("left to send projects", html)

    def test_after_72_hours_the_chip_says_the_window_ended(self):
        badge = store.get_badge(BADGE)
        badge.published_at = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=73)).isoformat()
        store.save_badge(badge)
        html = self.schedule("m_b2_2")
        self.assertIn("Project window ended", html)
        self.assertNotIn("left to send projects", html)

    def test_other_reviewers_never_see_this_badge_card(self):
        html = self.schedule("m_b2_5")
        self.assertNotIn("Data Systems Architecture", html)


class TestCosmonautProjectAllocatedButton(PublishedBadgeBase):
    def _badge_page(self, uid):
        c = _login(uid)
        c.handle_event("nav_cosmonaut", "c_submission")
        c.handle_event("open_cosmonaut_badge_page", BADGE)
        return c, _main(c)

    def test_locked_until_the_reviewer_sends_then_it_unlocks_and_opens_the_project(self):
        cid = self.mapped("m_b2_2")[0]
        c, html = self._badge_page(cid)
        self.assertIn("Earn the Badge", html)
        self.assertIn("pa-btn is-locked", html)
        self.assertIn("disabled", html.split("pa-btn is-locked")[1].split(">")[0] + html.split("pa-btn is-locked")[0][-200:])
        for gone in ("Request Project", "Submit Deliverables", "Submit Project Deliverables"):
            self.assertNotIn(gone, html)
        rev = _login("m_b2_2")
        rev.handle_event("send_reviewer_project", json.dumps({"badge_id": BADGE, "title": "Pipeline", "content": BRIEF, "cosmonaut_ids": [cid]}))
        c, html = self._badge_page(cid)
        self.assertIn("pa-btn is-ready", html)
        self.assertNotIn("pa-btn is-locked", html)
        self.assertIn("open_allocated_project_page", html)
        c.handle_event("open_allocated_project_page", BADGE)
        self.assertEqual(c.current_view, "c_project")                                 # a page, not a popup
        c.render()
        page = c.last_rendered_regions["mainContentHtml"]
        self.assertIn("Pipeline", page)
        self.assertIn("Submit Deliverables", page)                                    # the submit button lives inside the project
        c.handle_event("open_submission_modal", BADGE)
        self.assertEqual(c.active_modal, "submission_portal_modal")

    def test_a_cosmonaut_without_a_sent_project_cannot_open_the_submission(self):
        cid = self.mapped("m_b2_2")[0]
        c, _ = self._badge_page(cid)
        c.handle_event("open_submission_modal", BADGE)
        self.assertIsNone(c.active_modal)
        c.handle_event("open_allocated_project_page", BADGE)
        self.assertNotEqual(c.current_view, "c_project")                              # nothing to open yet
        self.assertIn("not been sent", c.last_flash_message)

    def test_the_button_is_glass_not_a_coloured_border_card(self):
        import os
        css = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()
        rule = css.split(".earn-card {")[1].split("}")[0]
        self.assertIn("rgba(157, 183, 213", rule)
        self.assertNotIn("#3B82F6", rule)


if __name__ == "__main__":
    unittest.main()


class TestReviewerSchedulePageAndTimelineModal(PublishedBadgeBase):
    def test_schedule_page_has_no_band_chip_role_or_dashboard_buttons(self):
        html = self.schedule("m_b2_2")
        self.assertNotIn("Project Reviewer", html)
        self.assertNotIn("&larr; Dashboard", html)
        self.assertNotIn("Assessment Queue", html)
        self.assertNotIn("BAND B2", html)                       # the chip that sat above the title
        r = _login("m_b2_2")
        r.handle_event("nav_cosmonaut", "c_badge_reviews")
        r.render()
        self.assertIn('class="app-strip-title"', r.last_rendered_regions["topbarHtml"])   # the title lives in the Back strip
        self.assertIn("Badge Review Schedule", r.last_rendered_regions["topbarHtml"])

    def _timeline(self, reviewer_id="m_b2_2"):
        r = _login(reviewer_id)
        r.handle_event("nav_cosmonaut", "c_badge_reviews")
        r.handle_event("open_reviewer_badge_timeline_modal", BADGE)
        return r, r.render_active_modal()

    def test_timeline_is_a_vertical_timeline_of_connected_dots_with_the_72_hour_step(self):
        _, m = self._timeline()
        for part in ("tlv-steps", "tlv-dot", "Allocated &amp; published", "Project window (72 hours)", "Learning period", "Project sprint",
                     "Submission deadline", "Review window", "Certification award", "left to send projects", "Create Project"):
            self.assertIn(part, m, part)
        self.assertEqual(m.count('<li class="tlv-step'), 7)
        self.assertEqual(m.count("tlv-dot"), 7)

    def test_timeline_describes_this_reviewers_own_cosmonauts_not_a_hardcoded_one(self):
        _, m = self._timeline("m_b2_2")
        ids = self.mapped("m_b2_2")
        for cid in ids:
            self.assertIn(store.get_user_by_id(cid).name, m)
        for other in self.mapped("m_b2_1"):
            if other not in ids:
                self.assertNotIn(store.get_user_by_id(other).name, m)
        self.assertIn(f"0 / {len(ids)}", m)                                 # projects sent / mapped

    def test_window_step_turns_done_when_every_project_is_sent(self):
        rev = _login("m_b2_2")
        ids = self.mapped("m_b2_2")
        rev.handle_event("send_reviewer_project", json.dumps({"badge_id": BADGE, "title": "P", "content": BRIEF, "cosmonaut_ids": ids}))
        rev.handle_event("open_reviewer_badge_timeline_modal", BADGE)
        m = rev.render_active_modal()
        self.assertIn(f"All {len(ids)} project", m)
        self.assertIn(f"{len(ids)} / {len(ids)}", m)
        self.assertIn("Edit Project", m)
        self.assertNotIn("left to send projects", m)

    def test_window_step_is_flagged_after_72_hours(self):
        badge = store.get_badge(BADGE)
        badge.published_at = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=80)).isoformat()
        store.save_badge(badge)
        _, m = self._timeline()
        self.assertIn("Window ended", m)
        self.assertIn("still to send", m)
        self.assertNotIn("3-Day", m)                                         # the old hard-coded 3-day notice is gone

    def test_timeline_is_glass_with_no_emoji_or_coloured_border_boxes(self):
        _, m = self._timeline()
        for gone in ("\u23f1", "\u2728", "border:1.5px solid #0284C7", "border:1.5px solid rgba(239,68,68,0.3)"):
            self.assertNotIn(gone, m)


class TestBadgeCardHeaderIsMinimal(PublishedBadgeBase):
    def test_code_band_status_pills_and_skill_lineage_are_not_on_the_card(self):
        html = self.schedule("m_b2_2")
        head = html.split('class="rv-badge-card"')[1].split("rv-tree")[0]
        self.assertIn("Data Systems Architecture", head)
        for gone in ("B1-DAT-01", "BAND B1", "Upcoming review", "projects to send", "Skill :", "lg-hier-disclosure", "rv-code", "rv-band"):
            self.assertNotIn(gone, head, gone)
        for kept in ("Review window", "Submission deadline", "Project window", "Create Project", "mapped cosmonaut"):
            self.assertIn(kept, head, kept)
