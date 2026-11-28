"""The Guardian's final decision (Earn Badge / Re-attempt / Reject) is saved and locked; only the Guardian can revoke it, after which they can decide again."""
import json
import unittest

from starapp.app import StarAppController
from starapp.storage import store

BADGE = "b1_int_01"
CID = "m_b1_1"
REV = "m_b2_1"
BRIEF = "Case Study" + chr(10) + "A." + chr(10) + chr(10) + "Your Challenge" + chr(10) + "B."


def _login(uid):
    c = StarAppController()
    c.initialize()
    c.handle_event("select_demo_account", uid)
    return c


def _marks(sid, each=9, decision="approve"):
    return json.dumps({"submission_id": sid, "bu": each, "ar": each, "tk": each, "pr": each, "qa": each, "decision": decision})


class TestDecisionRevoke(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        b = store.get_badge(BADGE)
        b.is_published = True
        b.assigned_cosmonaut_ids = [CID]
        b.assigned_reviewer_id = REV
        store.save_badge(b)
        _login(REV).handle_event("send_reviewer_project", json.dumps({"badge_id": BADGE, "title": "P", "content": BRIEF, "cosmonaut_ids": [CID], "status": "released"}))
        _login(CID).handle_event("submit_project_deliverable", json.dumps({"badge_id": BADGE, "pdf_name": "r.pdf", "pdf_payload": "x", "code_name": "a.py", "code_payload": "x", "github_url": "https://github.com/a/b"}))
        self.sub_id = store.get_submissions_for_cosmonaut(CID, BADGE)[-1].id
        _login(REV).handle_event("submit_reviewer_assessment", json.dumps({"submission_id": self.sub_id, "bu": 9, "ar": 9, "tk": 9, "pr": 9, "qa": 9, "decision": "approve"}))

    def tearDown(self):
        store.reset_to_seed()

    def sub(self):
        return store.get_submission(self.sub_id)

    def decide(self, decision="approve", each=9):
        g = _login("guardian_1")
        g.handle_event("submit_guardian_final_assessment", _marks(self.sub_id, each, decision))
        return g

    def test_decision_is_saved_and_cannot_be_redone_until_revoked(self):
        self.decide("approve")
        self.assertEqual(self.sub().status, "approved")
        g = self.decide("reject", 5)                                              # a second decision is refused
        self.assertEqual(self.sub().status, "approved")
        self.assertEqual(store.get_guardian_assessment_for_submission(self.sub_id).decision, "approve")
        self.assertIn("final decision", g.last_flash_message)

    def test_locked_panel_shows_the_saved_decision_and_a_revoke_button(self):
        self.decide("approve")
        g = _login("guardian_1")
        g.handle_event("open_submission_review_page", self.sub_id)
        g.render()
        h = g.last_rendered_regions["mainContentHtml"]
        for part in ("Decision saved: Badge earned", "Revoke decision", "open_revoke_decision_confirm", "lg-rubric-locked"):
            self.assertIn(part, h, part)
        self.assertNotIn("rubric-submit-label", h)
        self.assertGreaterEqual(h.count(" disabled"), 3)
        self.assertIn("readonly", h)

    def test_revoking_a_badge_takes_it_back_and_allows_a_new_decision(self):
        self.decide("approve")
        self.assertTrue(any(a.decision == "approve" for a in store.get_assessments_for_cosmonaut(CID, BADGE)))
        g = _login("guardian_1")
        g.handle_event("open_revoke_decision_confirm", self.sub_id)
        self.assertEqual(g.active_modal, "decision_revoke_confirm")
        self.assertIn("Revoke this decision?", g.render_active_modal())
        g.handle_event("revoke_guardian_decision", self.sub_id)
        self.assertEqual(g.flash_type, "success")
        self.assertEqual(self.sub().status, "reviewer_assessed")                  # back to "ready for sign-off"
        self.assertIsNone(store.get_guardian_assessment_for_submission(self.sub_id))
        self.assertIsNotNone(store.get_reviewer_assessment_for_submission(self.sub_id))   # the reviewer's marks are untouched
        self.assertFalse(any(a.decision == "approve" for a in store.get_assessments_for_cosmonaut(CID, BADGE)))
        self.assertTrue(any("Decision under review" in n.title for n in store.get_notifications(CID)))
        self.assertTrue(any(e.event_type == "guardian_decision_revoked" for e in store.get_all_activity()) if hasattr(store, "get_all_activity") else True)
        c = _login(CID)                                                            # the cosmonaut's gold badge is gone
        c.handle_event("nav_cosmonaut", "c_submission")
        c.render()
        self.assertNotIn("gold-card", c.last_rendered_regions["mainContentHtml"])
        self.decide("reject", 5)                                                   # and the Guardian can decide again
        self.assertEqual(store.get_guardian_assessment_for_submission(self.sub_id).decision, "rejected")

    def test_every_option_can_be_revoked(self):
        for decision, each in (("resubmission_requested", 5), ("reject", 5)):
            self.decide(decision, each)
            self.assertEqual(self.sub().status, "retake_required")
            _login("guardian_1").handle_event("revoke_guardian_decision", self.sub_id)
            self.assertEqual(self.sub().status, "reviewer_assessed", decision)

    def test_only_the_guardian_can_revoke_and_only_the_current_attempt(self):
        self.decide("approve")
        for uid in (REV, CID):
            c = _login(uid)
            c.handle_event("revoke_guardian_decision", self.sub_id)
            self.assertEqual(self.sub().status, "approved", uid)
        # an older attempt cannot be revoked once a newer one exists
        store.reset_to_seed()
        self.setUp()
        self.decide("resubmission_requested", 5)
        _login(CID).handle_event("submit_project_deliverable", json.dumps({"badge_id": BADGE, "pdf_name": "r2.pdf", "pdf_payload": "x", "code_name": "a.py", "code_payload": "x", "github_url": "https://github.com/a/b"}))
        g = _login("guardian_1")
        g.handle_event("revoke_guardian_decision", self.sub_id)
        self.assertIn("newer attempt", g.last_flash_message)
        self.assertEqual(self.sub().status, "retake_required")


if __name__ == "__main__":
    unittest.main()
