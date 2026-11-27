"""
Reviewer -> Review Requests -> badge review page.

The Guardian sends a badge for review; the reviewer sees it as a CARD, opens it in the SAME structured format the
Guardian authored it in (views_badge_document), corrects it, and approves / returns it. Edits go to the REAL badge, so
the Guardian sees them too. Every rule is enforced on the server.
"""
import json
import os
import sqlite3
import unittest

from starapp.app import StarAppController
from starapp.storage import store

BADGE = "b1_int_01"
REVIEWER = "m_b2_4"          # Nisha Menon, Band B2 - may review Band B1 badges
OTHER_REVIEWER = "m_b2_1"    # a different B2 reviewer, not assigned to the badge
CADET = "m_b1_1"

EDIT = {
    "title": "Intelligent Apps Foundations (reviewed)",
    "description": "Scope corrected by the reviewer.",
    "outcomes": ["Can build a retrieval pipeline.", "Can evaluate an agent."],
    "practice_prompt": "Build a tiny RAG app.",
    "resources_prompt": "Official docs only.",
    "topics": [
        {"title": "Retrieval basics", "description": "Chunking and embeddings."},
        {"title": "Evaluation", "description": "Golden sets."},
    ],
}


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


class ReviewerBadgeReviewBase(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.guardian = _login("guardian_1")
        self.guardian.handle_event(
            "send_badge_review_request", json.dumps({"badge_id": BADGE, "reviewer_id": REVIEWER})
        )
        self.assertEqual(store.get_badge(BADGE).workflow_status, "pending_review")
        self.rev = _login(REVIEWER, ("nav_cosmonaut", "c_requests"))

    def open_page(self):
        self.rev.handle_event("open_reviewer_badge_review", BADGE)
        self.assertEqual(self.rev.current_view, "c_badge_review")
        return _main(self.rev)

    def db_row(self):
        con = sqlite3.connect(os.environ["STARAPP_DB_PATH"])
        con.row_factory = sqlite3.Row
        try:
            return con.execute("SELECT * FROM badges WHERE id = ?", (BADGE,)).fetchone()
        finally:
            con.close()


class TestRequestCards(ReviewerBadgeReviewBase):
    def test_heading_block_and_dashboard_button_are_gone(self):
        html = _main(self.rev)
        self.assertEqual(self.rev.current_view, "c_requests")
        self.assertNotIn("&larr; Dashboard", html)
        self.assertNotIn("BAND B2", html)                       # the band chip above the title
        self.assertNotIn("app-global-back-btn", html)           # the Back button lives in the top strip only
        self.assertIn('<div class="app-strip-title"', self.rev.render())   # the title is in the strip instead

    def test_requested_badge_is_a_card_that_opens_the_review_page(self):
        html = _main(self.rev)
        self.assertIn("lg-saved-badge-card is-clickable", html)
        self.assertIn("open_reviewer_badge_review", html)
        self.assertIn("Intelligent Apps Foundations", html)
        self.assertIn("Needs your review", html)
        # the decision is made INSIDE the badge, not from a button on the card
        for gone in ("Accept &amp; Approve", "Accept & Approve", "Edit Badge", "Inspect Badge", "confirm_approve_badge"):
            self.assertNotIn(gone, html)

    def test_cards_follow_the_status_filter_and_search(self):
        self.rev.handle_event("filter_cosmo_requests", "approved")
        self.assertNotIn("lg-saved-badge-card", _main(self.rev))
        self.rev.handle_event("filter_cosmo_requests", "all")
        self.rev.handle_event("search_cosmo_requests", "zzz-nothing")
        self.assertNotIn("lg-saved-badge-card", _main(self.rev))


class TestSameFormatAsGuardian(ReviewerBadgeReviewBase):
    SECTIONS = ("created-badge-display-area", "badge-section-outcomes", "badge-section-earn", "badge-section-practice",
                "badge-section-topics", "badge-section-resources", "badge-section-related")
    EDIT_IDS = ("edit-badge-title-input", "edit-badge-desc-input", "edit-badge-outcomes-input", "edit-topic-title-0",
                "edit-topic-desc-0", "edit-practice-prompt-input", "edit-resources-prompt-input")

    def _guardian_view(self, edit=False):
        g = _login("guardian_1", ("select_create_badge_band", "B1"), ("view_saved_badge", BADGE))
        if edit:
            g.handle_event("toggle_edit_badge")
        return _main(g)

    def test_read_only_page_has_the_guardians_sections(self):
        page = self.open_page()
        guardian = self._guardian_view()
        for sid in self.SECTIONS:
            self.assertIn(f'id="{sid}"', page, sid)
            self.assertIn(f'id="{sid}"', guardian, sid)
        for text in ("Created Badge Location", "Toggle All", "Learning Topics", "Learning Resources",
                     "Related Skills, Capabilities &amp; Powers", "Copy Prompt", "Intelligent Apps Foundations"):
            self.assertIn(text, page, text)
        self.assertIn("Review This Badge", page)

    def test_reviewer_reads_topics_as_curriculum_not_as_learner_progress(self):
        page = self.open_page()
        self.assertNotIn("Mark Complete", page)
        self.assertNotIn("topics-progress-bar", page)
        self.assertIn("Mark Complete", self._guardian_view())      # the Guardian's draft keeps its progress controls

    def test_edit_mode_uses_the_same_inputs_as_the_guardians_edit(self):
        self.open_page()
        self.rev.handle_event("toggle_reviewer_badge_edit")
        page = _main(self.rev)
        guardian = self._guardian_view(edit=True)
        for eid in self.EDIT_IDS:
            self.assertIn(f'id="{eid}"', page, eid)
            self.assertIn(f'id="{eid}"', guardian, eid)
        self.assertIn("saveReviewerBadgeEdits()", page)
        self.assertIn("Apply Changes", page)
        self.assertNotIn("confirm_approve_badge", page)           # decide after the edit is applied or cancelled

    def test_cancel_leaves_the_badge_untouched(self):
        self.open_page()
        self.rev.handle_event("toggle_reviewer_badge_edit")
        self.assertTrue(self.rev.reviewer_review_editing)
        self.rev.handle_event("toggle_reviewer_badge_edit")
        self.assertFalse(self.rev.reviewer_review_editing)
        self.assertEqual(store.get_badge(BADGE).title, "Intelligent Apps Foundations")


class TestEditsReachTheRealBadge(ReviewerBadgeReviewBase):
    def _save(self, payload=None):
        self.open_page()
        self.rev.handle_event("toggle_reviewer_badge_edit")
        self.rev.handle_event("save_reviewer_badge_edits", json.dumps(payload or EDIT))

    def test_saved_to_memory_and_to_the_database_file(self):
        self._save()
        b = store.get_badge(BADGE)
        self.assertEqual((b.title, b.description), (EDIT["title"], EDIT["description"]))
        self.assertEqual(b.learning_outcomes, EDIT["outcomes"])
        self.assertEqual(b.learning_topics, ["Retrieval basics", "Evaluation"])
        self.assertEqual(b.project_requirements, EDIT["practice_prompt"])
        row = self.db_row()                                         # re-read through a separate connection
        self.assertEqual(row["title"], EDIT["title"])
        self.assertEqual(json.loads(row["learning_outcomes_json"]), EDIT["outcomes"])
        self.assertEqual(json.loads(row["learning_topics_json"]), ["Retrieval basics", "Evaluation"])
        pj = json.loads(row["prompt_json"])
        self.assertEqual(pj["practice_project"]["prompt"], EDIT["practice_prompt"])
        self.assertEqual(pj["learning_resources"]["prompt"], EDIT["resources_prompt"])
        self.assertEqual(pj["learning_topics"][1]["description"], "Golden sets.")
        self.assertEqual(pj["reviewed_by"], store.get_user_by_id(REVIEWER).name)
        self.assertEqual(row["workflow_status"], "pending_review")  # editing is not deciding
        self.assertFalse(self.rev.reviewer_review_editing)

    def test_reviewer_page_shows_the_saved_edits(self):
        self._save()
        page = _main(self.rev)
        for text in (EDIT["title"], EDIT["description"], "Can build a retrieval pipeline.", "Build a tiny RAG app.", "Golden sets."):
            self.assertIn(text, page, text)

    def test_guardian_sees_the_same_edited_badge_and_is_told(self):
        self._save()
        g = _login("guardian_1", ("select_create_badge_band", "B1"), ("view_saved_badge", BADGE))
        page = _main(g)
        for text in (EDIT["title"], EDIT["description"], "Can evaluate an agent.", "Build a tiny RAG app.", "Official docs only.", "Golden sets."):
            self.assertIn(text, page, text)
        creator = store.get_badge(BADGE).creator_id
        self.assertTrue(any("edited by reviewer" in n.title.lower() for n in store.get_notifications(creator)))
        events = [e["event_type"] for e in store.get_badge_review_history(badge_id=BADGE)]
        self.assertIn("edited", events)

    def test_a_short_reviewer_prompt_is_not_replaced_by_the_generated_one(self):
        self._save()
        page = _main(self.rev)
        self.assertIn("Build a tiny RAG app.", page)
        self.assertNotIn("Design one small, hands-on practice project", page)

    def test_blank_title_or_no_outcomes_is_refused_and_nothing_changes(self):
        self._save(dict(EDIT, outcomes=[]))
        self.assertIn("at least one outcome", self.rev.last_flash_message)
        self.assertEqual(store.get_badge(BADGE).title, "Intelligent Apps Foundations")
        self.assertTrue(self.rev.reviewer_review_editing)           # still editing, nothing lost

    def test_title_of_another_band_b1_badge_is_refused(self):
        other = next(b for b in store.get_all_badges() if b.target_band == "B1" and b.id != BADGE)
        self._save(dict(EDIT, title=other.title))
        self.assertIn("already has a badge titled", self.rev.last_flash_message)
        self.assertEqual(store.get_badge(BADGE).title, "Intelligent Apps Foundations")


class TestDecisionFromThePage(ReviewerBadgeReviewBase):
    def test_edit_then_approve_keeps_the_edits(self):
        self.open_page()
        self.rev.handle_event("toggle_reviewer_badge_edit")
        self.rev.handle_event("save_reviewer_badge_edits", json.dumps(EDIT))
        page = _main(self.rev)
        self.assertIn("confirm_approve_badge", page)
        self.assertIn("confirm_return_badge", page)
        self.rev.handle_event("confirm_approve_badge", BADGE)
        self.assertEqual(self.rev.active_modal, "badge_approval_confirm")
        self.rev.handle_event("approve_submitted_badge", BADGE)
        b = store.get_badge(BADGE)
        self.assertEqual(b.workflow_status, "approved")
        self.assertEqual(b.title, EDIT["title"])
        self.assertEqual(self.db_row()["workflow_status"], "approved")
        self.assertEqual(self.rev.current_view, "c_badge_review")   # stays on the badge, now read-only
        page = _main(self.rev)
        self.assertIn("Approved", page)
        self.assertNotIn("toggle_reviewer_badge_edit", page)
        self.assertNotIn("confirm_approve_badge", page)

    def test_an_approved_badge_can_no_longer_be_edited(self):
        self.open_page()
        self.rev.handle_event("approve_submitted_badge", BADGE)
        self.rev.handle_event("toggle_reviewer_badge_edit")
        self.assertFalse(self.rev.reviewer_review_editing)
        self.assertIn("no longer awaiting review", self.rev.last_flash_message)
        self.rev.handle_event("save_reviewer_badge_edits", json.dumps(EDIT))
        self.assertEqual(store.get_badge(BADGE).title, "Intelligent Apps Foundations")

    def test_return_with_feedback_closes_the_review_read_only(self):
        self.open_page()
        self.rev.handle_event("confirm_return_badge", BADGE)
        self.assertEqual(self.rev.active_modal, "badge_reviewer_return")
        self.rev.handle_event("return_submitted_badge", json.dumps({"badge_id": BADGE, "notes": "Outcomes are too vague."}))
        self.assertEqual(store.get_badge(BADGE).workflow_status, "returned")
        page = _main(self.rev)
        self.assertIn("Returned for Changes", page)
        self.assertIn("Outcomes are too vague.", page)
        self.assertNotIn("toggle_reviewer_badge_edit", page)

    def test_queue_card_follows_the_decision(self):
        self.open_page()
        self.rev.handle_event("approve_submitted_badge", BADGE)
        self.rev.handle_event("nav_cosmonaut", "c_requests")
        html = _main(self.rev)
        self.assertIn("Approved", html)
        self.assertIn("View Badge", html)
        self.assertNotIn("Needs your review", html)


class TestServerEnforcesWhoMayReview(ReviewerBadgeReviewBase):
    def test_only_the_assigned_reviewer_can_open_the_page(self):
        other = _login(OTHER_REVIEWER, ("nav_cosmonaut", "c_requests"))
        other.handle_event("open_reviewer_badge_review", BADGE)
        self.assertNotEqual(other.current_view, "c_badge_review")
        self.assertIn("not sent to you", other.last_flash_message)

    def test_a_cosmonaut_cannot_open_it(self):
        cadet = _login(CADET)
        cadet.handle_event("open_reviewer_badge_review", BADGE)
        self.assertNotEqual(cadet.current_view, "c_badge_review")

    def test_a_forged_session_state_cannot_edit_someone_elses_badge(self):
        other = _login(OTHER_REVIEWER, ("nav_cosmonaut", "c_requests"))
        other.reviewer_review_badge_id = BADGE                      # crafted state, never opened legitimately
        other.current_view = "c_badge_review"
        html = _main(other)
        self.assertEqual(other.current_view, "c_requests")           # the render falls back to the queue
        other.reviewer_review_badge_id = BADGE
        other.handle_event("save_reviewer_badge_edits", json.dumps(EDIT))
        self.assertEqual(store.get_badge(BADGE).title, "Intelligent Apps Foundations")
        self.assertNotIn("(reviewed)", html)

    def test_unknown_badge_and_stale_session_fall_back_to_the_queue(self):
        self.rev.handle_event("open_reviewer_badge_review", "no-such-badge")
        self.assertEqual(self.rev.current_view, "c_requests")
        self.rev.current_view = "c_badge_review"
        self.rev.reviewer_review_badge_id = ""
        _main(self.rev)
        self.assertEqual(self.rev.current_view, "c_requests")

    def test_the_page_is_a_reviewer_view_and_highlights_review_requests(self):
        from starapp.views_common import COSMONAUT_REVIEWER_VIEWS, TITLE_HOIST_VIEWS
        self.assertIn("c_badge_review", COSMONAUT_REVIEWER_VIEWS)
        self.assertIn("c_badge_review", TITLE_HOIST_VIEWS)
        self.open_page()
        side = self.rev.last_rendered_regions["sidebarHtml"]
        self.assertIn('class="nav-link active" data-nav-id="c_requests"', side)

    def test_write_actions_are_not_in_the_read_only_cycle_allow_list(self):
        safe = StarAppController._CYCLE_READONLY_SAFE_ACTIONS
        self.assertIn("open_reviewer_badge_review", safe)            # opening is navigation
        self.assertNotIn("save_reviewer_badge_edits", safe)          # saving is a write
        self.assertNotIn("toggle_reviewer_badge_edit", safe)


class TestSharedBadgeDocumentAssets(unittest.TestCase):
    def test_bridge_collects_the_form_once_for_both_portals(self):
        js = open(os.path.join(os.path.dirname(__file__), "..", "js", "bridge.js"), encoding="utf-8").read()
        self.assertIn("_collectBadgeEditPayload()", js)
        self.assertIn('dispatchAction("save_reviewer_badge_edits"', js)
        self.assertIn('dispatchAction("save_badge_edits"', js)

    def test_one_renderer_serves_both_portals(self):
        root = os.path.join(os.path.dirname(__file__), "..", "starapp")
        guardian = open(os.path.join(root, "views_guardian.py"), encoding="utf-8").read()
        cosmo = open(os.path.join(root, "views_cosmonaut.py"), encoding="utf-8").read()
        self.assertIn("render_badge_document(", guardian)
        self.assertIn("render_badge_document(", cosmo)
        self.assertNotIn('id="edit-badge-title-input"', guardian)    # the markup lives in views_badge_document only
        self.assertNotIn('id="edit-badge-title-input"', cosmo)


if __name__ == "__main__":
    unittest.main()
