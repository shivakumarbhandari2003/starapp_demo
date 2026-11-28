"""
Reviewer recommendation (Give Badge / Re-attempt / Reject) -> Guardian decision -> loop / gold badge.

* The reviewer's rubric panel has the three icon options; the choice is a RECOMMENDATION stored on the reviewer's marksheet.
* Marks are final per attempt: once submitted the panel is read-only; a new assessment exists only for a new attempt.
* The Guardian sees the recommendation, can overrule it, and their option drives the outcome (badge / re-attempt / reject).
* Re-attempt and Reject restart the loop (the cosmonaut submits a new attempt, the reviewer assesses it again).
* An earned badge turns gold.
"""
import json
import unittest

from starapp.app import StarAppController
from starapp.storage import store

BADGE = "b1_int_01"
CID = "m_b1_1"
REV = "m_b2_1"
BRIEF = "Case Study" + chr(10) + "A freight company." + chr(10) + chr(10) + "Your Challenge" + chr(10) + "Design a pipeline."
SUBMISSION = {"badge_id": BADGE, "pdf_name": "report.pdf", "pdf_payload": "data:application/pdf;base64,AAAA",
              "code_name": "solution.py", "code_payload": "print(1)", "github_url": "https://github.com/org/project-repo"}


def marks(each, decision=None, sid=""):
    d = {"submission_id": sid, "bu": each, "ar": each, "tk": each, "pr": each, "qa": each,
         "strengths": "Clean.", "improvements": "More tests.", "feedback": "Good work."}
    if decision is not None:
        d["decision"] = decision
    return json.dumps(d)


def _login(uid):
    c = StarAppController()
    c.initialize()
    c.handle_event("select_demo_account", uid)
    return c


def _main(c):
    c.render()
    return c.last_rendered_regions["mainContentHtml"]


class Base(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        b = store.get_badge(BADGE)
        b.is_published = True
        b.assigned_cosmonaut_ids = [CID, "m_b1_2"]
        b.assigned_reviewer_id = REV
        store.save_badge(b)
        _login(REV).handle_event("send_reviewer_project", json.dumps({
            "badge_id": BADGE, "title": "Freight", "content": BRIEF, "cosmonaut_ids": [CID], "status": "released"}))

    def tearDown(self):
        store.reset_to_seed()

    def submit(self):
        c = _login(CID)
        c.handle_event("submit_project_deliverable", json.dumps(SUBMISSION))
        return c

    def sub(self):
        return store.get_submissions_for_cosmonaut(CID, BADGE)[-1]

    def assess(self, each=9, decision="approve"):
        rev = _login(REV)
        rev.handle_event("submit_reviewer_assessment", marks(each, decision, self.sub().id))
        return rev


class TestReviewerPanel(Base):
    def test_the_rubric_panel_shows_three_icon_options(self):
        self.submit()
        rev = _login(REV)
        rev.handle_event("open_reviewer_assessment_page", self.sub().id)
        w = _main(rev)
        for part in ("Your recommendation to the Guardian", "Give Badge", "Re-attempt", "Reject", "lg-dec-opt is-approve", "lg-dec-opt is-resubmit",
                     "lg-dec-opt is-reject", 'id="rubric-decision"', "Submit Assessment"):
            self.assertIn(part, w, part)
        self.assertGreaterEqual(w.split("lg-dec-list")[1].count("<svg"), 3)                  # an icon on each option
        self.assertIn("lg-dec-opt is-approve is-on", w)                                      # 9.0 each = 90% -> Give Badge pre-selected

    def test_the_choice_is_saved_as_a_recommendation_and_nothing_is_awarded(self):
        self.submit()
        self.assess(9, "approve")
        asm = store.get_reviewer_assessment_for_submission(self.sub().id)
        self.assertEqual(asm.decision, "recommend_approve")
        self.assertEqual(self.sub().status, "reviewer_assessed")                            # not approved: the Guardian decides
        self.assertNotEqual(getattr(store.get_timeline(BADGE, CID), "status", ""), "completed")
        self.assertFalse(any(a.decision == "approve" for a in store.get_assessments_for_cosmonaut(CID, BADGE)))

    def test_each_option_is_stored(self):
        for each, dec, stored in ((9, "approve", "recommend_approve"), (5, "resubmission_requested", "recommend_resubmit"), (5, "reject", "recommend_reject")):
            store.reset_to_seed()
            self.setUp()
            self.submit()
            self.assess(each, dec)
            self.assertEqual(store.get_reviewer_assessment_for_submission(self.sub().id).decision, stored, dec)

    def test_give_badge_cannot_be_recommended_below_the_pass_mark(self):
        self.submit()
        rev = _login(REV)
        rev.handle_event("submit_reviewer_assessment", marks(5, "approve", self.sub().id))
        self.assertEqual(rev.flash_type, "error")
        self.assertIn("pass mark", rev.last_flash_message)
        self.assertIsNone(store.get_reviewer_assessment_for_submission(self.sub().id))

    def test_marks_are_final_per_attempt_and_the_panel_is_read_only(self):
        self.submit()
        rev = self.assess(9, "approve")
        sid = self.sub().id
        rev.handle_event("submit_reviewer_assessment", marks(6, "reject", sid))                # a second try is refused
        self.assertEqual(rev.flash_type, "info")
        self.assertIn("locked", rev.last_flash_message)
        self.assertEqual(store.get_reviewer_assessment_for_submission(sid).decision, "recommend_approve")
        self.assertEqual(store.get_reviewer_assessment_for_submission(sid).total_marks, 45.0)
        rev.handle_event("open_reviewer_assessment_page", sid)
        w = _main(rev)
        self.assertIn("lg-rubric-locked", w)
        self.assertIn("Marks submitted and locked", w)
        self.assertNotIn("rubric-submit-label", w)                                           # no submit button any more
        self.assertGreaterEqual(w.count(" disabled"), 3)
        self.assertIn("readonly", w)
        self.assertIn("lg-dec-opt is-approve is-on", w)                                      # the saved recommendation stays selected


class TestGuardianSeesAndDecides(Base):
    def open_detail(self):
        g = _login("guardian_1")
        g.handle_event("open_submission_review_page", self.sub().id)
        return g, _main(g)

    def test_the_guardian_sees_the_recommendation_and_it_is_preselected(self):
        self.submit()
        self.assess(5, "reject")
        g, d = self.open_detail()
        for part in ("Reviewer's recommendation", "rec-banner", "Reject", "lg-dec-opt is-reject is-on"):
            self.assertIn(part, d, part)
        g.handle_event("nav_guardian", "g_reviews")
        g.handle_event("open_assessment_badge", BADGE)
        g.handle_event("open_assessment_cosmonaut", CID)
        self.assertIn("Recommends", _main(g))
        self.assertIn("rec-chip", _main(g))

    def test_guardian_can_overrule_give_badge_and_asks_for_a_re_attempt(self):
        self.submit()
        self.assess(9, "approve")
        g = _login("guardian_1")
        g.handle_event("submit_guardian_final_assessment", marks(9, "resubmission_requested", self.sub().id))
        self.assertEqual(self.sub().status, "retake_required")
        self.assertEqual(store.get_guardian_assessment_for_submission(self.sub().id).decision, "resubmission_requested")
        self.assertNotEqual(getattr(store.get_timeline(BADGE, CID), "status", ""), "completed")             # a passing score, but no badge: the Guardian decides

    def test_guardian_cannot_award_below_the_pass_mark(self):
        self.submit()
        self.assess(5, "reject")
        g = _login("guardian_1")
        g.handle_event("submit_guardian_final_assessment", marks(5, "approve", self.sub().id))
        self.assertEqual(g.flash_type, "error")
        self.assertEqual(self.sub().status, "reviewer_assessed")

    def test_give_badge_makes_the_badge_gold(self):
        self.submit()
        c = _login(CID)
        c.handle_event("nav_cosmonaut", "c_submission")
        self.assertNotIn("gold-medal", _main(c))                                             # not earned yet: no gold
        c.handle_event("open_cosmonaut_badge_page", BADGE)
        self.assertNotIn("gold-medal", _main(c))
        self.assess(9, "approve")
        _login("guardian_1").handle_event("submit_guardian_final_assessment", marks(9, "approve", self.sub().id))
        self.assertEqual(self.sub().status, "approved")
        c2 = _login(CID)
        c2.handle_event("nav_cosmonaut", "c_submission")
        grid = _main(c2)
        self.assertIn("gold-medal", grid)                                                    # gold medal on the badge card ...
        self.assertIn("Badge Earned", grid)
        c2.handle_event("open_cosmonaut_badge_page", BADGE)
        page = _main(c2)
        self.assertGreaterEqual(page.count("gold-medal"), 2)                                 # ... beside the badge name and on the earned card
        self.assertIn("gold-medal is-lg", page)
        c2.handle_event("nav_cosmonaut", "c_results")
        self.assertIn("ms-sheet", _main(c2))
        css = open("css/components.css", encoding="utf-8").read()
        self.assertIn(".gold-medal", css)
        self.assertIn("#fcd34d", css)


class TestLoopRestarts(Base):
    def loop(self, guardian_choice, label):
        self.submit()
        self.assess(5, "resubmission_requested")
        first = self.sub()
        g = _login("guardian_1")
        g.handle_event("submit_guardian_final_assessment", marks(5, guardian_choice, first.id))
        self.assertEqual(self.sub().status, "retake_required")
        c = _login(CID)
        c.handle_event("nav_cosmonaut", "c_results")
        m = _main(c)
        self.assertIn("ms-sheet", m)
        c.handle_event("open_allocated_project_page", BADGE)
        self.assertIn("Submit Deliverables", _main(c))                                       # the cosmonaut can start a new attempt
        rev = _login(REV)
        rev.handle_event("nav_cosmonaut", "c_badge_reviews")
        self.assertIn("rv-assess is-locked", _main(rev))                                     # reviewer waits for the new submission
        c.handle_event("submit_project_deliverable", json.dumps(dict(SUBMISSION, pdf_name="report_v2.pdf")))
        second = self.sub()
        self.assertEqual(second.attempt_number, 2)
        self.assertNotEqual(second.id, first.id)
        rev.handle_event("sync_badge_reviews")
        self.assertIn(f"open_reviewer_assessment_page', '{second.id}'", _main(rev))          # Assessment is enabled again: the loop restarts
        rev.handle_event("submit_reviewer_assessment", marks(9, "approve", second.id))
        self.assertEqual(rev.flash_type, "success")
        self.assertEqual(store.get_reviewer_assessment_for_submission(second.id).decision, "recommend_approve")
        self.assertEqual(store.get_reviewer_assessment_for_submission(first.id).decision, "recommend_resubmit")   # attempt 1 stays on record

    def test_re_attempt_restarts_the_loop(self):
        self.loop("resubmission_requested", "Re-attempt")

    def test_reject_closes_the_attempt_and_the_cosmonaut_can_try_again(self):
        self.loop("reject", "Rejected")
        asm = store.get_guardian_assessment_for_submission(store.get_submissions_for_cosmonaut(CID, BADGE)[0].id)
        self.assertEqual(asm.decision, "rejected")


if __name__ == "__main__":
    unittest.main()
