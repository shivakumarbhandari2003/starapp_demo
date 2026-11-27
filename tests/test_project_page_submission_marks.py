"""
Project page -> submit dialog -> mapped reviewer -> marks -> cosmonaut marksheet + Guardian.

* "Project Allocated" opens the whole project as its OWN PAGE (c_project), never a popup.
* Submit Deliverables opens a clean glass dialog (PDF / source code / GitHub); submitting routes the work to the mapped reviewer only.
* The reviewer sees the deliverables and allocates marks; the marks show on the cosmonaut's marksheet (live) and to the Guardian.
"""
import json
import os
import unittest

from starapp.app import StarAppController
from starapp.storage import store

BADGE = "b1_int_01"
CID = "m_b1_1"
REV = "m_b2_1"
BRIEF = ("Case Study" + chr(10) + "A freight company." + chr(10) + chr(10) + "Your Challenge" + chr(10) + "Design an intelligent pipeline." + chr(10) + chr(10)
         + "Deliverables" + chr(10) + "- PDF report: the design." + chr(10) + "- Source code: the build." + chr(10) + "- GitHub repository: the history.")
SUBMISSION = {"badge_id": BADGE, "pdf_name": "report.pdf", "pdf_payload": "data:application/pdf;base64,AAAA",
              "code_name": "solution.py", "code_payload": "print(1)", "github_url": "https://github.com/org/project-repo"}
MARKS = {"bu": 8.5, "ar": 9, "tk": 7.5, "pr": 8, "qa": 6.5, "strengths": "Clean modular design.", "improvements": "More tests.",
         "feedback": "Solid, production-minded delivery."}


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
        badge = store.get_badge(BADGE)
        badge.is_published = True
        badge.assigned_cosmonaut_ids = [CID, "m_b1_2"]
        badge.assigned_reviewer_id = REV
        store.save_badge(badge)

    def tearDown(self):
        store.reset_to_seed()

    def send_project(self):
        _login(REV).handle_event("send_reviewer_project", json.dumps({
            "badge_id": BADGE, "title": "Freight Intelligence", "content": BRIEF, "cosmonaut_ids": [CID], "status": "released"}))

    def submit(self):
        c = _login(CID)
        c.handle_event("open_allocated_project_page", BADGE)
        c.handle_event("submit_project_deliverable", json.dumps(SUBMISSION))
        return c

    def sub(self):
        return store.get_submissions_for_cosmonaut(CID, BADGE)[-1]


class TestProjectIsAPage(Base):
    def test_project_allocated_opens_a_page_not_a_popup(self):
        self.send_project()
        c = _login(CID)
        c.handle_event("open_cosmonaut_badge_page", BADGE)
        self.assertIn("open_allocated_project_page", _main(c))
        c.handle_event("open_allocated_project_page", BADGE)
        self.assertEqual(c.current_view, "c_project")
        self.assertIsNone(c.active_modal)
        page = _main(c)
        for part in ("pjp-page", "Freight Intelligence", "Case Study", "Your Challenge", "Deliverables", "Sent by", "Submit Deliverables", "Your submission"):
            self.assertIn(part, page, part)
        self.assertEqual(c.last_rendered_regions["activeNavId"], "c_submission")          # the Badges item stays highlighted
        self.assertEqual(c.last_rendered_regions["routeKey"], f"c_project:{BADGE}")

    def test_old_popup_names_land_on_the_page_too(self):
        self.send_project()
        for name in ("open_allocated_project_modal", "view_allocated_project"):
            c = _login(CID)
            c.handle_event(name, BADGE)
            self.assertEqual(c.current_view, "c_project", name)
            self.assertIsNone(c.active_modal, name)

    def test_back_returns_to_the_badge_page(self):
        self.send_project()
        c = _login(CID)
        c.handle_event("open_cosmonaut_badge_page", BADGE)
        c.handle_event("open_allocated_project_page", BADGE)
        c.handle_event("go_back")
        self.assertEqual(c.current_view, "c_badge_detail")

    def test_it_cannot_be_opened_before_the_project_is_sent_or_by_someone_else(self):
        c = _login(CID)
        c.handle_event("open_allocated_project_page", BADGE)                               # nothing sent yet
        self.assertNotEqual(c.current_view, "c_project")
        self.assertIn("not been sent", c.last_flash_message)
        self.send_project()
        outsider = _login("m_b1_6")                                                        # a badge that is not allotted to them
        outsider.handle_event("open_allocated_project_page", BADGE)
        self.assertNotEqual(outsider.current_view, "c_project")
        self.assertIn("not allotted", outsider.last_flash_message)

    def test_a_crafted_or_stale_c_project_view_falls_back(self):
        c = _login(CID)
        c.cosmonaut_submission_badge_id = BADGE
        c.current_view = "c_project"                                                       # no project sent
        c.render()
        self.assertEqual(c.current_view, "c_badge_detail")
        c.cosmonaut_submission_badge_id = "no-such-badge"
        c.current_view = "c_project"
        c.render()
        self.assertEqual(c.current_view, StarAppController.COSMONAUT_HOME_VIEW)

    def test_the_page_is_live(self):
        self.send_project()
        c = _login(CID)
        c.handle_event("open_allocated_project_page", BADGE)
        self.assertIn('data-live-sync="project"', _main(c))


class TestSubmitDialog(Base):
    def test_dialog_is_just_the_deliverable_fields_in_glass(self):
        self.send_project()
        c = _login(CID)
        c.handle_event("open_allocated_project_page", BADGE)
        c.handle_event("open_submission_modal", BADGE)
        self.assertEqual(c.active_modal, "submission_portal_modal")
        m = c.render_active_modal()
        for part in ("sd-wrap", "Submit your deliverables", "PDF report", "Source code", "GitHub repository", "submission-pdf-file",
                     "submission-code-file", "submission-github-url", "project-submission-form", "Cancel", "showPickedFile"):
            self.assertIn(part, m, part)
        self.assertIn("Submit to Rohan", m)                                                # the button names who receives it
        for gone in ("Required", "your mapped reviewer", "Link to the repository", "Freight Intelligence"):
            self.assertNotIn(gone, m, gone)                                                # no extra sentences / tags
        for gone in ("Case Study", "Your Challenge", "Freight Intelligence\n", "liquid-submission-portal"):
            self.assertNotIn(gone, m, gone)                                                # the project is on the page, not repeated here
        self.assertLess(m.index("submission-pdf-file"), m.index("submission-code-file"))
        self.assertLess(m.index("submission-code-file"), m.index("submission-github-url"))
        html = c.render()
        self.assertIn("modal-form", html)                                                  # a compact dialog, not the full-width one

    def test_editing_shows_the_current_files(self):
        self.send_project()
        self.submit()
        c = _login(CID)
        c.handle_event("open_allocated_project_page", BADGE)
        c.handle_event("open_submission_modal", BADGE)
        m = c.render_active_modal()
        for part in ("Edit your deliverables", "report.pdf", "solution.py", "https://github.com/org/project-repo", "Update deliverables"):
            self.assertIn(part, m, part)

    def test_bridge_has_the_file_name_helper_and_the_css_exists(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        js = open(os.path.join(root, "js", "bridge.js"), encoding="utf-8").read()
        css = open(os.path.join(root, "css", "components.css"), encoding="utf-8").read()
        self.assertIn("showPickedFile(input, nameId, dropId)", js)
        for rule in (".sd-drop", ".sd-wrap", ".pjp-page", ".ms-sheet", ".ms-ring", ".ms-crit"):
            self.assertIn(rule, css, rule)


class TestSubmissionReachesTheMappedReviewer(Base):
    def test_submission_goes_to_the_mapped_reviewer_with_a_notification_and_status_on_the_page(self):
        self.send_project()
        c = self.submit()
        self.assertEqual(c.flash_type, "success")
        self.assertIsNone(c.active_modal)
        self.assertEqual(c.current_view, "c_project")                                      # stays on the project page
        page = _main(c)
        for part in ("Submitted", "Attempt #1", "report.pdf", "solution.py", "project-repo", "Edit Deliverables"):
            self.assertIn(part, page, part)
        self.assertTrue(any(CID in n.message or "submitted" in n.message.lower() for n in store.get_notifications(REV)))
        rev = _login(REV)
        rev.handle_event("nav_cosmonaut", "c_badge_reviews")
        q = _main(rev)
        for part in ("Aarav Sharma", "Deliverables submitted", "rv-assess", f"open_reviewer_assessment_page', '{self.sub().id}'"):
            self.assertIn(part, q, part)
        for gone in ("report.pdf", "solution.py", "Submitted Deliverables", "Inspect"):            # the files are in the workspace, not on the card
            self.assertNotIn(gone, q, gone)
        other = _login("m_b2_2")                                                           # another reviewer sees nothing of it
        other.handle_event("nav_cosmonaut", "c_badge_reviews")
        self.assertNotIn("Aarav Sharma", _main(other))

    def test_assessment_button_is_disabled_until_the_cosmonaut_submits(self):
        self.send_project()
        rev = _login(REV)
        rev.handle_event("nav_cosmonaut", "c_badge_reviews")
        before = _main(rev)
        self.assertIn("Project sent - waiting for deliverables", before)
        self.assertIn("rv-assess is-locked", before)
        self.assertIn("disabled", before.split("rv-assess is-locked")[1].split(">")[0])
        self.assertNotIn("open_reviewer_assessment_page", before)
        self.submit()
        rev.handle_event("sync_badge_reviews")
        after = _main(rev)
        self.assertIn(f"open_reviewer_assessment_page', '{self.sub().id}'", after)               # enabled for the one who submitted ...
        self.assertEqual(after.count("rv-assess is-locked"), before.count("rv-assess is-locked") - 1)   # one fewer locked button
        rev.handle_event("open_reviewer_assessment_page", self.sub().id)
        w = _main(rev)
        self.assertIn("Back to Badge Reviews", w)
        self.assertEqual(rev.last_rendered_regions["activeNavId"], "c_badge_reviews")
        rev.handle_event("submit_reviewer_assessment", json.dumps(dict(MARKS, submission_id=self.sub().id)))
        self.assertEqual(rev.current_view, "c_badge_reviews")                                # marks allocated -> back on the schedule
        self.assertIn("Evaluated 39.5/50", _main(rev))

    def test_reviewer_workspace_shows_the_deliverables_and_the_rubric(self):
        self.send_project()
        self.submit()
        rev = _login(REV)
        rev.handle_event("open_reviewer_assessment_page", self.sub().id)
        w = _main(rev)
        for part in ("reviewer-rubric-form", "rubric-bu", "rubric-qa", "View Source Code", "View GitHub Repo", "pdf-document-frame"):
            self.assertIn(part, w, part)

    def test_only_the_mapped_reviewer_can_allocate_marks(self):
        self.send_project()
        self.submit()
        sid = self.sub().id
        other = _login("m_b2_2")
        other.handle_event("submit_reviewer_assessment", json.dumps(dict(MARKS, submission_id=sid)))
        self.assertEqual(other.flash_type, "error")
        self.assertIsNone(store.get_reviewer_assessment_for_submission(sid))
        rev = _login(REV)                                                                  # the badge's own reviewer is accepted too
        rev.handle_event("submit_reviewer_assessment", json.dumps(dict(MARKS, submission_id=sid)))
        self.assertEqual(rev.flash_type, "success")
        self.assertIsNotNone(store.get_reviewer_assessment_for_submission(sid))


class TestMarksReachCosmonautAndGuardian(Base):
    def grade(self):
        self.send_project()
        self.submit()
        sid = self.sub().id
        _login(REV).handle_event("submit_reviewer_assessment", json.dumps(dict(MARKS, submission_id=sid)))
        return sid

    def test_reviewer_marks_show_on_the_cosmonaut_marksheet(self):
        self.grade()
        self.assertTrue(any("Assessment Graded" in n.title for n in store.get_notifications(CID)))
        c = _login(CID)
        c.handle_event("nav_cosmonaut", "c_results")
        m = _main(c)
        for part in ("ms-sheet", "ms-ring", "39.5", "79.0%", "Awaiting Guardian", "Peer Reviewer", "Rohan Deshmukh", "Business Understanding",
                     "8.5", "Clean modular design.", "More tests.", "Solid, production-minded delivery.", 'data-live-sync="marksheet"'):
            self.assertIn(part, m, part)
        self.assertEqual(m.count('class="ms-crit"'), 5)
        self.assertNotIn("Badge earned", m.split("ms-head")[1].split("ms-body")[0])        # not final yet

    def test_marksheet_opens_on_the_newest_evaluated_badge_and_page_updates_live(self):
        self.send_project()
        self.submit()
        c = _login(CID)
        c.handle_event("nav_cosmonaut", "c_results")
        self.assertIn("waiting for evaluation", _main(c))                                  # submitted, not graded yet
        _login(REV).handle_event("submit_reviewer_assessment", json.dumps(dict(MARKS, submission_id=self.sub().id)))
        c.handle_event("sync_badge_reviews")                                               # the browser's 6 s live sync
        self.assertIn("39.5", _main(c))

    def test_guardian_sees_the_reviewer_marks_and_the_final_adds_a_tab(self):
        sid = self.grade()
        g = _login("guardian_1")
        self.assertTrue(any("Reviewer Assessed" in n.title for n in store.get_notifications("guardian_1")))
        g.handle_event("nav_guardian", "g_reviews")
        self.assertIn("1 Ready for Sign-off", _main(g))                                    # the badge card flags it
        g.handle_event("open_assessment_badge", BADGE)
        g.handle_event("open_assessment_cosmonaut", CID)
        drill = _main(g)
        self.assertIn("39.5 / 50.0", drill)                                                # the reviewer's marks on the cosmonaut's card
        self.assertIn("Ready for Guardian Sign-off", drill)
        g.handle_event("open_submission_review_page", sid)
        d = _main(g)
        self.assertIn('id="rubric-bu"', d)
        self.assertIn("8.5", d)                                                            # the reviewer's marks pre-fill the Guardian's rubric
        g.handle_event("submit_guardian_final_assessment", json.dumps({"submission_id": sid, "bu": 9, "ar": 9, "tk": 9, "pr": 9, "qa": 9, "decision": "approve"}))
        c = _login(CID)
        c.handle_event("nav_cosmonaut", "c_results")
        m = _main(c)
        for part in ("Badge earned", "45.0", "Guardian Official", "Peer Reviewer", "ms-tab"):
            self.assertIn(part, m, part)
        asm = next(a for a in store.get_assessments_for_cosmonaut(CID, BADGE) if a.assessor_role == "reviewer")
        c.handle_event("select_results_marksheet", json.dumps({"marksheet_id": asm.id}))
        m2 = _main(c)
        self.assertIn("39.5", m2)
        self.assertIn("Awaiting Guardian", m2)                                             # the reviewer tab is selectable

    def test_a_cosmonaut_cannot_select_someone_elses_marksheet(self):
        self.grade()
        mine = next(a for a in store.get_assessments_for_cosmonaut(CID, BADGE) if a.assessor_role == "reviewer")
        other = _login("m_b1_2")
        other.handle_event("select_results_marksheet", json.dumps({"marksheet_id": mine.id}))
        self.assertEqual(other.cosmonaut_results_asm_id, "")

    def test_open_marksheet_buttons_target_the_badge(self):
        self.grade()
        c = _login(CID)
        c.handle_event("open_cosmonaut_badge_page", BADGE)
        self.assertIn("open_badge_marksheet", _main(c))                                    # "View marks" on the badge page
        c.handle_event("open_allocated_project_page", BADGE)
        self.assertIn("open_badge_marksheet", _main(c))                                    # and on the project page
        c.handle_event("open_badge_marksheet", BADGE)
        self.assertEqual(c.current_view, "c_results")
        self.assertEqual(c.cosmonaut_results_badge_id, BADGE)
        c.handle_event("open_badge_marksheet", "no-such-badge")
        self.assertEqual(c.current_view, "c_results")                                      # ignored, nothing changes


class TestMarksheetGlass(unittest.TestCase):
    def test_marksheet_has_no_inline_navy_header_or_table(self):
        from starapp.models import AssessmentMarksheet
        from starapp.views_common import render_standard_marksheet
        a = AssessmentMarksheet(id="x", submission_id="s", attempt_number=2, badge_id="b", cosmonaut_id="c", reviewer_id="r", reviewer_name="Arjun Mehta",
                                reviewed_at="2026-11-27T10:00:00", decision="resubmission_requested", business_understanding=4, architecture_report=5,
                                technical_knowledge=6, presentation=7, qa=8, strength_areas="s", improvement_areas="i", overall_feedback="f", assessor_role="guardian")
        html = render_standard_marksheet(a)
        self.assertIn("Re-attempt", html)
        self.assertIn("ms-meter-fill is-low", html)
        self.assertIn("ms-meter-fill is-high", html)
        for gone in ("<table", "linear-gradient(135deg, #071629", "marksheet-rubric-table"):
            self.assertNotIn(gone, html, gone)


if __name__ == "__main__":
    unittest.main()
