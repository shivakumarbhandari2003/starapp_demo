"""
48-hour review window.

From the moment the Guardian sends a badge for review the reviewer has 48 hours to review, edit and decide. A live
countdown replaces "sent by" on the request card. When the time runs out without a decision the request closes and
the badge is kept exactly as it is (nothing is approved automatically); the reviewer keeps a read-only view. Applies
to every reviewer. Also covers the card polish and the invitation-card redesign.
"""
import datetime
import json
import os
import sqlite3
import unittest

from starapp.app import StarAppController
from starapp.database import BADGE_REVIEW_WINDOW_HOURS, parse_review_due
from starapp.storage import store

BADGE = "b1_int_01"
EDIT = {"title": "Intelligent Apps Foundations (reviewed)", "description": "Scope fixed.", "outcomes": ["Can do A."],
        "practice_prompt": "Short prompt.", "resources_prompt": "Short resources.",
        "topics": [{"title": "T1", "description": "D1"}]}


def _login(user_id, *steps):
    c = StarAppController()
    c.initialize()
    c.handle_event("select_demo_account", user_id)
    for action, payload in steps:
        c.handle_event(action, payload)
    return c


def _main(c):
    c.render()
    return c.last_rendered_regions["mainContentHtml"]


def _db(sql, params=()):
    con = sqlite3.connect(os.environ["STARAPP_DB_PATH"])
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


class ReviewWindowBase(unittest.TestCase):
    REVIEWER = "m_b2_4"

    def setUp(self):
        store.reset_to_seed()
        self.guardian = _login("guardian_1")
        self.guardian.handle_event("send_badge_review_request", json.dumps({"badge_id": BADGE, "reviewer_id": self.REVIEWER}))
        self.rev = _login(self.REVIEWER, ("nav_cosmonaut", "c_requests"))

    def assignment(self):
        return _db("SELECT * FROM badge_reviewer_assignments WHERE badge_id = ? AND reviewer_id = ? ORDER BY assigned_at DESC", (BADGE, self.REVIEWER))[0]

    def end_window(self):
        """Moves the deadline into the past (as if 48 hours had gone by) without running the sweep."""
        past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).isoformat()
        con = sqlite3.connect(os.environ["STARAPP_DB_PATH"])
        with con:
            con.execute("UPDATE badge_reviewer_assignments SET review_due_at = ? WHERE badge_id = ? AND status = 'pending'", (past, BADGE))
        con.close()


class TestFortyEightHourClock(ReviewWindowBase):
    def test_deadline_is_48_hours_after_sending(self):
        row = self.assignment()
        sent, due = parse_review_due(row["assigned_at"]), parse_review_due(row["review_due_at"])
        self.assertEqual(BADGE_REVIEW_WINDOW_HOURS, 48)
        self.assertAlmostEqual((due - sent).total_seconds(), 48 * 3600, delta=2)
        self.assertEqual(row["status"], "pending")

    def test_card_shows_the_countdown_instead_of_sent_by(self):
        html = _main(self.rev)
        self.assertIn('data-sync="sync_badge_reviews"', html)
        left = int(html.split('data-remaining="', 1)[1].split('"', 1)[0])
        self.assertTrue(48 * 3600 - 30 < left <= 48 * 3600)
        self.assertIn("left to review", html)
        self.assertNotIn("Sent by", html.split("lg-saved-badge-card")[1].split("Cosmonaut Evaluation")[0])

    def test_card_title_is_bold_and_big_and_has_no_outcome_topic_chips(self):
        html = _main(self.rev)
        self.assertIn('class="lg-sb-title is-request"', html)
        card = html.split("lg-saved-badge-card")[1].split("Cosmonaut Evaluation")[0]
        self.assertNotIn(" outcomes</span>", card)
        self.assertNotIn(" topics</span>", card)
        self.assertNotIn("3 outcomes", card)
        css = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()
        rule = css.split(".lg-saved-badge-card .lg-sb-title.is-request {")[1].split("}")[0]
        self.assertIn("font-weight: 800", rule)
        self.assertIn("1.4rem", rule)

    def test_review_page_shows_the_countdown_too(self):
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        self.assertIn('data-sync="sync_badge_reviews"', _main(self.rev))

    def test_the_browser_timer_knows_which_action_to_sync(self):
        js = open(os.path.join(os.path.dirname(__file__), "..", "js", "bridge.js"), encoding="utf-8").read()
        self.assertIn('getAttribute("data-sync")', js)
        self.assertIn("sync_badge_reviews", StarAppController._CYCLE_READONLY_SAFE_ACTIONS)


class TestWindowEnds(ReviewWindowBase):
    def _edit_then_run_out(self):
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        self.rev.handle_event("toggle_reviewer_badge_edit")
        self.rev.handle_event("save_reviewer_badge_edits", json.dumps(EDIT))
        self.end_window()
        self.rev.handle_event("sync_badge_reviews")          # what the browser sends when the countdown hits zero
        self.rev.handle_event("nav_cosmonaut", "c_requests")

    def test_badge_is_kept_as_it_is_and_returns_to_the_guardian(self):
        self._edit_then_run_out()
        b = store.get_badge(BADGE)
        self.assertEqual(b.workflow_status, "ready_for_review")      # NOT approved
        self.assertFalse(b.assigned_reviewer_id)
        self.assertEqual(b.title, EDIT["title"])                      # the reviewer's applied edits are kept
        row = _db("SELECT title, workflow_status, assigned_reviewer_id FROM badges WHERE id = ?", (BADGE,))[0]
        self.assertEqual((row["title"], row["workflow_status"], row["assigned_reviewer_id"]), (EDIT["title"], "ready_for_review", None))
        self.assertEqual(self.assignment()["status"], "expired")

    def test_everyone_is_told_and_it_is_audited(self):
        self._edit_then_run_out()
        events = [e["event_type"] for e in store.get_badge_review_history(badge_id=BADGE)]
        self.assertIn("review_expired", events)
        creator = store.get_badge(BADGE).creator_id or "guardian_1"
        self.assertTrue(any(n.title.startswith("Review Window Ended") for n in store.get_notifications(self.REVIEWER)))
        self.assertTrue(any(n.title.startswith("Review Window Ended") for n in store.get_notifications(creator)))

    def test_reviewer_keeps_a_read_only_view(self):
        self._edit_then_run_out()
        html = _main(self.rev)
        self.assertIn("Window ended", html)                           # card state
        self.assertIn("Review window ended", html)                    # decision line, same format as history
        self.assertNotIn("rq-timer", html.split("Cosmonaut Evaluation")[0])
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        page = _main(self.rev)
        self.assertEqual(self.rev.current_view, "c_badge_review")
        self.assertIn("Review Window Ended", page)
        self.assertIn("Read-only", page)
        for gone in ("toggle_reviewer_badge_edit", "confirm_approve_badge", "confirm_return_badge", "saveReviewerBadgeEdits"):
            self.assertNotIn(gone, page)

    def test_no_write_gets_through_after_the_window(self):
        self._edit_then_run_out()
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        self.rev.handle_event("toggle_reviewer_badge_edit")
        self.assertFalse(self.rev.reviewer_review_editing)
        self.rev.handle_event("save_reviewer_badge_edits", json.dumps(dict(EDIT, title="Too late")))
        self.rev.handle_event("approve_submitted_badge", BADGE)
        self.rev.handle_event("return_submitted_badge", json.dumps({"badge_id": BADGE, "notes": "late"}))
        b = store.get_badge(BADGE)
        self.assertEqual((b.title, b.workflow_status), (EDIT["title"], "ready_for_review"))

    def test_the_server_refuses_a_decision_even_before_the_sweep_runs(self):
        self.end_window()                                              # deadline passed, no action has swept yet
        self.assertIn("review window", store.badge_review_denied_reason(BADGE, self.REVIEWER))
        ok, msg = store.approve_badge(BADGE, self.REVIEWER)
        self.assertFalse(ok)
        self.assertEqual(store.get_badge(BADGE).workflow_status, "pending_review")

    def test_a_window_that_ends_mid_edit_drops_back_to_read_only(self):
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        self.rev.handle_event("toggle_reviewer_badge_edit")
        self.assertTrue(self.rev.reviewer_review_editing)
        self.end_window()
        self.rev.handle_event("sync_badge_reviews")
        page = _main(self.rev)
        self.assertNotIn("edit-badge-title-input", page)

    def test_guardian_can_send_it_again_with_a_fresh_48_hours(self):
        self._edit_then_run_out()
        self.guardian.handle_event("send_badge_review_request", json.dumps({"badge_id": BADGE, "reviewer_id": self.REVIEWER}))
        self.assertEqual(store.get_badge(BADGE).workflow_status, "pending_review")
        row = self.assignment()
        self.assertEqual(row["status"], "pending")
        self.assertAlmostEqual((parse_review_due(row["review_due_at"]) - parse_review_due(row["assigned_at"])).total_seconds(), 48 * 3600, delta=2)
        html = _main(self.rev)
        self.assertIn("Needs your review", html)                       # newest assignment wins over the expired one
        self.assertIn('data-sync="sync_badge_reviews"', html)

    def test_the_sweep_leaves_open_and_decided_reviews_alone(self):
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        self.rev.handle_event("sync_badge_reviews")
        self.assertEqual(store.get_badge(BADGE).workflow_status, "pending_review")
        self.rev.handle_event("approve_submitted_badge", BADGE)
        self.end_window()                                              # nothing pending any more
        self.rev.handle_event("sync_badge_reviews")
        self.assertEqual(store.get_badge(BADGE).workflow_status, "approved")


class TestAnyReviewer(TestWindowEnds):
    """The same rules for a reviewer of a higher band (B3) as for a B2 one."""
    REVIEWER = "m_b3_6"


class TestReviewedBadgesStayAsCards(ReviewWindowBase):
    def test_decided_badge_card_reads_like_a_history_row_and_page_is_read_only(self):
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        self.rev.handle_event("confirm_return_badge", BADGE)
        self.rev.handle_event("return_submitted_badge", json.dumps({"badge_id": BADGE, "notes": "Outcomes too vague."}))
        self.rev.handle_event("nav_cosmonaut", "c_requests")
        html = _main(self.rev)
        card = html.split("lg-saved-badge-card")[1].split("Cosmonaut Evaluation")[0]
        self.assertIn("Returned with feedback", card)
        self.assertIn("UTC", card)                                    # the decision time, formatted like the history table
        self.assertIn("Outcomes too vague.", card)
        self.assertNotIn("rq-timer", card)
        self.rev.handle_event("filter_cosmo_requests", "returned")
        self.assertIn("lg-saved-badge-card", _main(self.rev))
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        page = _main(self.rev)
        self.assertIn("Read-only", page)
        self.assertNotIn("toggle_reviewer_badge_edit", page)

    def test_approved_badge_card_and_expired_tab(self):
        self.rev.handle_event("approve_submitted_badge", BADGE)
        html = _main(self.rev)
        self.assertIn("lg-sb-decision is-approved", html)
        self.assertIn("Expired (0)", html)


class TestRequestsToolbar(ReviewWindowBase):
    """Status dropdown + Review History button + search sit on the heading line, right side, and all of them work."""

    def _html(self):
        return _main(self.rev)

    def test_dropdown_history_and_search_are_on_the_heading_line(self):
        html = self._html()
        head = html.split('class="rr-head"')[1].split("Request Cards List")[0]
        self.assertIn("Badge Approval Requests", head)
        for part in ('id="rr-status-filter-select"', 'id="rr-history-toggle-btn"', 'id="rr-search-input"', "rr-tools"):
            self.assertIn(part, head, part)
        for opt in ("All Requests (1)", "Pending Review (1)", "Approved Badges (0)", "Returned (0)", "Expired (0)"):
            self.assertIn(opt, head, opt)
        self.assertNotIn("btn-secondary btn-sm\" style=\"background:var(--deep-frozen-midnight)", head)   # the old tab buttons are gone
        self.assertIn("debouncedDispatch('search_cosmo_requests'", head)
        css = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()
        self.assertIn("margin-left: auto;", css.split(".rr-tools {")[1].split("}")[0])          # pushed to the right

    def test_dropdown_filters_the_cards(self):
        self.rev.handle_event("filter_cosmo_requests", "approved")
        html = self._html()
        self.assertNotIn("lg-saved-badge-card", html)
        self.assertIn('<option value="approved" selected>', html)
        self.rev.handle_event("filter_cosmo_requests", "pending_review")
        self.assertIn("lg-saved-badge-card", self._html())

    def test_history_button_toggles_the_history_and_keeps_the_dropdown_in_sync(self):
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        self.rev.handle_event("approve_submitted_badge", BADGE)
        self.rev.handle_event("nav_cosmonaut", "c_requests")
        self.rev.handle_event("filter_cosmo_requests", "history")
        html = self._html()
        self.assertIn("ba-history-btn is-active", html)
        self.assertIn('<option value="history" selected hidden>Review History', html)
        self.assertIn("Authorized & Approved", html)
        self.assertNotIn("lg-saved-badge-card", html)
        self.rev.handle_event("filter_cosmo_requests", "all")                   # the same button again, or any status option
        html = self._html()
        self.assertNotIn("ba-history-btn is-active", html)
        self.assertIn("lg-saved-badge-card", html)

    def test_search_filters_cards_and_history(self):
        self.rev.handle_event("search_cosmo_requests", "intelligent")
        self.assertIn("lg-saved-badge-card", self._html())
        self.rev.handle_event("search_cosmo_requests", "zzz-nothing")
        html = self._html()
        self.assertNotIn("lg-saved-badge-card", html)
        self.assertIn("No Review Requests in this Queue", html)
        self.rev.handle_event("search_cosmo_requests", "")
        self.rev.handle_event("filter_cosmo_requests", "history")
        self.assertIn("Review Dispatched", self._html())
        self.rev.handle_event("search_cosmo_requests", "zzz-nothing")
        self.assertIn("No history matches your search.", self._html())
        self.rev.handle_event("search_cosmo_requests", "b1-int")
        self.assertIn("Review Dispatched", self._html())

    def test_expiry_is_a_history_row_too(self):
        self.end_window()
        self.rev.handle_event("sync_badge_reviews")
        self.rev.handle_event("filter_cosmo_requests", "history")
        self.assertIn("Review Window Ended", self._html())


class TestInvitationCardRedesign(unittest.TestCase):
    """The invitation shows only Band, badge name, countdown and review window. Cosmonauts appear only once they are the
    reviewer's: request accepted + mapping completed by the Guardian + badge published."""

    MAPPED = ["m_b1_1", "m_b1_2"]

    def setUp(self):
        store.reset_to_seed()
        self.g = _login("guardian_1", ("select_create_badge_band", "B1"), ("nav_guardian", "g_mapping"))
        self.g.mapping_selected_cosmonauts = list(self.MAPPED)
        self.g.mapping_selected_reviewers = ["m_b2_1"]
        self.g.mapping_selected_badge = "Data Systems Architecture"
        self.g.handle_event("send_mapping_requests", "{}")
        self.req = next(r for r in store.get_mapping_requests() if r["reviewer_id"] == "m_b2_1")
        self.rev = _login("m_b2_1", ("nav_cosmonaut", "c_requests"))

    def _card(self):
        html = _main(self.rev)
        return html.split('class="inv-card')[1].split("inv-actions")[0]

    def _complete_mapping_and_publish(self):
        self.g.handle_event("select_demo_account", "guardian_1")
        payload = {"band": "B1", "badge_id": "b1_dat_01", "badge": "Data Systems Architecture"}
        self.g.handle_event("preview_cosmonaut_mapping", payload)
        self.g.handle_event("save_staged_mapping", payload)
        self.g.handle_event("publish_badge", "b1_dat_01")
        self.rev.handle_event("nav_cosmonaut", "c_requests")

    def test_pending_invitation_shows_only_band_badge_countdown_and_window(self):
        html = _main(self.rev)
        card = self._card()
        self.assertIn('class="inv-card is-pending"', html)
        for part in ("inv-title", "Data Systems Architecture", "inv-band", "BAND B1", "rq-timer", "Respond within", "Review window", "inv-window"):
            self.assertIn(part, card, part)
        self.assertIn("accept_mapping_request", html)
        self.assertIn("reject_mapping_request", html)
        for hidden in ("inv-people", "inv-av", "Cosmonauts", "inv-count", "Sent 2"):
            self.assertNotIn(hidden, card, hidden)
        for cid in self.MAPPED:                                       # no name of a not-yet-mapped cosmonaut anywhere on the page
            self.assertNotIn(store.get_user_by_id(cid).name, html, cid)

    def test_accepting_alone_does_not_reveal_cosmonauts(self):
        self.rev.handle_event("accept_mapping_request", self.req["id"])
        html = _main(self.rev)
        card = self._card()
        self.assertIn('class="inv-card is-accepted"', html)
        self.assertIn("Decline / Revoke", html)
        self.assertNotIn("inv-people", card)
        for cid in self.MAPPED:
            self.assertNotIn(store.get_user_by_id(cid).name, html)

    def test_mapped_but_not_published_still_hides_them(self):
        self.rev.handle_event("accept_mapping_request", self.req["id"])
        self.g.handle_event("select_demo_account", "guardian_1")
        payload = {"band": "B1", "badge_id": "b1_dat_01", "badge": "Data Systems Architecture"}
        self.g.handle_event("preview_cosmonaut_mapping", payload)
        self.g.handle_event("save_staged_mapping", payload)
        self.assertFalse(store.get_badge("b1_dat_01").is_published)
        self.rev.handle_event("nav_cosmonaut", "c_requests")
        self.assertNotIn("inv-people", self._card())

    def test_accepted_mapped_and_published_shows_the_mapped_cosmonauts(self):
        self.rev.handle_event("accept_mapping_request", self.req["id"])
        self._complete_mapping_and_publish()
        self.assertTrue(store.get_badge("b1_dat_01").is_published)
        mine = store.get_reviewer_mapped_cosmonaut_ids("m_b2_1", "b1_dat_01")
        self.assertTrue(mine)
        card = self._card()
        self.assertIn("Mapped Cosmonauts", card)
        self.assertIn("inv-people", card)
        for cid in sorted(mine)[:3]:                                  # the first three are named, the rest are "+N more"
            self.assertIn(store.get_user_by_id(cid).name, card)
        self.assertIn(f'<span class="inv-count">{len(mine)}</span>', card)

    def test_a_declined_request_never_shows_them_even_if_mapped_and_published(self):
        self.rev.handle_event("accept_mapping_request", self.req["id"])
        self._complete_mapping_and_publish()
        self.rev.handle_event("reject_mapping_request", self.req["id"])
        self.assertNotIn("inv-people", self._card())


if __name__ == "__main__":
    unittest.main()
