"""
Create Project: a synthetic, well-structured sample (heading, case study, challenge, project details, deliverables, evaluation)
pre-fills the reviewer's form, and the cosmonaut (and the reviewer) read the project in badge-style sections.
"""
import json
import os
import unittest

from starapp.app import StarAppController
from starapp.badge_generator import (
    PROJECT_SECTIONS, compose_project_content, generate_project_brief, parse_project_content,
)
from starapp.storage import store

BADGE = "b1_int_01"


def _login(uid):
    c = StarAppController()
    c.initialize()
    c.handle_event("select_demo_account", uid)
    return c


class TestSyntheticProjectBrief(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.badge = store.get_badge(BADGE)

    def test_sample_has_every_section_built_from_the_badge(self):
        b = generate_project_brief(self.badge)
        for key in ("title", "case_study", "challenge", "details", "deliverables", "evaluation"):
            self.assertTrue(b[key], key)
        self.assertIn(self.badge.skill, b["title"])
        self.assertIn(self.badge.title, b["case_study"])
        self.assertIn(self.badge.target_band, b["case_study"])
        self.assertEqual(len(b["deliverables"]), 3)                                    # PDF report, source code, GitHub repository
        self.assertTrue(b["deliverables"][0].startswith("PDF report"))
        self.assertTrue(b["deliverables"][1].startswith("Source code"))
        self.assertTrue(b["deliverables"][2].startswith("GitHub repository"))
        self.assertEqual(len(b["evaluation"]), 5)                                      # the five rubric criteria, 10 marks each
        self.assertTrue(all("10 marks" in e for e in b["evaluation"]))

    def test_sample_is_deterministic_and_differs_per_badge(self):
        self.assertEqual(generate_project_brief(self.badge), generate_project_brief(self.badge))
        other = store.get_badge("b1_dat_01")
        self.assertNotEqual(generate_project_brief(self.badge)["title"], generate_project_brief(other)["title"])

    def test_compose_and_parse_round_trip(self):
        b = generate_project_brief(self.badge)
        text = compose_project_content(b)
        for _, title, _ in PROJECT_SECTIONS:
            self.assertIn(title + "\n", text)
        back = parse_project_content(text)
        self.assertEqual(back["case_study"], b["case_study"])
        self.assertEqual(back["details"], b["details"])
        self.assertEqual(back["deliverables"], b["deliverables"])

    def test_free_text_projects_still_render_as_before(self):
        self.assertIsNone(parse_project_content("Just a paragraph of text without any headings."))
        self.assertIsNone(parse_project_content("Case Study\nOnly one heading is not enough."))
        self.assertIsNotNone(parse_project_content("Case Study\nA.\n\nYour Challenge\nB."))


class TestCreateProjectForm(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        badge = store.get_badge(BADGE)
        badge.is_published = True
        badge.assigned_cosmonaut_ids = ["m_b1_1", "m_b1_2"]
        badge.assigned_reviewer_id = "m_b2_1"
        store.save_badge(badge)
        self.rev = _login("m_b2_1")

    def tearDown(self):
        store.reset_to_seed()

    def _modal(self):
        self.rev.handle_event("open_create_reviewer_project_modal", BADGE)
        return self.rev.render_active_modal()

    def test_new_project_is_prefilled_with_the_sample_in_structured_fields(self):
        m = self._modal()
        sample = generate_project_brief(store.get_badge(BADGE))
        for field in ("rev_proj_title", "rev_proj_case", "rev_proj_challenge", "rev_proj_details", "rev_proj_del_0", "rev_proj_del_1",
                      "rev_proj_del_2", "rev_proj_eval"):
            self.assertIn(f'id="{field}"', m, field)
        self.assertIn("Sample project ready", m)
        self.assertIn("Reset to sample", m)
        self.assertIn("data-sample=", m)
        self.assertIn(sample["title"], m)
        self.assertIn("Heading", m)
        self.assertIn("Project Content", m)
        for title in ("Case Study", "Your Challenge", "Project Details", "Deliverables", "Evaluation", "Send to mapped cosmonauts"):
            self.assertIn(title, m, title)
        self.assertIn("Send Project to Mapped Cosmonauts", m)
        for old in ("Expected Project Outcomes", "Mandatory Deliverables", "Save Draft"):
            self.assertNotIn(old, m)

    def test_content_is_shown_formatted_and_edit_swaps_in_the_fields(self):
        m = self._modal()
        for key in ("title", "case_study", "challenge", "details", "deliverables", "evaluation"):
            self.assertIn(f'id="rp-view-{key}"', m, key)
            self.assertIn(f'data-pj-toggle="{key}"', m, key)
        for key in ("case_study", "challenge", "details", "deliverables", "evaluation"):
            self.assertIn(f'id="rp-edit-{key}" hidden', m, key)                      # the plain fields start hidden
        self.assertIn('id="rp-edit-title" hidden', m)
        for part in ('class="pj-text"', 'class="pj-list"', "pj-deliv-grid", 'id="rp-del-name-0"', 'id="rp-del-text-2"', "rp-title-view", "toggleProjectSection('case_study')"):
            self.assertIn(part, m, part)
        self.assertEqual(m.count('class="pj-deliv"'), 3)
        sample = generate_project_brief(store.get_badge(BADGE))
        self.assertIn(sample["details"][0].split(":")[0], m.split('id="rp-view-details"')[1].split("</ul>")[0])    # the bullets are in the formatted view

    def test_bridge_composes_the_sections_and_has_a_reset(self):
        js = open(os.path.join(os.path.dirname(__file__), "..", "js", "bridge.js"), encoding="utf-8").read()
        for part in ('"Case Study"', '"Your Challenge"', '"Project Details"', '"Deliverables"', '"Evaluation"', "resetReviewerProjectSample", "rev_proj_del_",
                     "toggleProjectSection", "_pjRenderSection"):
            self.assertIn(part, js, part)

    def test_sending_the_composed_sample_reaches_the_cosmonaut_in_sections(self):
        sample = generate_project_brief(store.get_badge(BADGE))
        self.rev.handle_event("send_reviewer_project", json.dumps({
            "badge_id": BADGE, "title": sample["title"], "content": compose_project_content(sample), "cosmonaut_ids": ["m_b1_1"]}))
        proj = store.get_project_prompt_for_cadet(BADGE, "m_b1_1")
        self.assertEqual(proj.title, sample["title"])
        c = _login("m_b1_1")
        c.handle_event("open_allocated_project_page", BADGE)
        c.render()
        m = c.last_rendered_regions["mainContentHtml"]
        self.assertIn(sample["title"], m)
        self.assertIn("font-size:1.75rem; font-weight:900", m)                         # the big heading is kept
        for part in ("project-brief is-structured", "Case Study", "Your Challenge", "Project Details", "pj-deliv-grid", "Evaluation", "Submit Deliverables"):
            self.assertIn(part, m, part)
        self.assertEqual(m.count('class="pj-deliv"'), 3)
        self.assertIn("pj-deliv-ico", m)
        self.assertIn(sample["challenge"][:40], m)

    def test_editing_an_earlier_project_shows_its_own_sections_not_the_sample(self):
        content = "Case Study" + chr(10) + "Our own case." + chr(10) + chr(10) + "Your Challenge" + chr(10) + "Our own challenge."
        self.rev.handle_event("send_reviewer_project", json.dumps({"badge_id": BADGE, "title": "Hand-written", "content": content, "cosmonaut_ids": ["m_b1_1"]}))
        m = self._modal()
        self.assertIn("Editing your earlier project", m)
        self.assertIn("Our own case.", m)
        self.assertIn("Our own challenge.", m)
        self.assertNotIn("Sample project ready", m)

    def test_a_legacy_free_text_project_is_kept_whole(self):
        self.rev.handle_event("send_reviewer_project", json.dumps({"badge_id": BADGE, "title": "Old style", "content": "Just free text from before.", "cosmonaut_ids": ["m_b1_1"]}))
        self.assertIn("Just free text from before.", self._modal())
        c = _login("m_b1_1")
        c.handle_event("open_allocated_project_page", BADGE)
        c.render()
        m = c.last_rendered_regions["mainContentHtml"]
        self.assertIn("Just free text from before.", m)
        self.assertNotIn("is-structured", m)

    def test_pdf_report_gets_a_document_icon_not_the_github_one(self):
        from starapp.views_cosmonaut import _pj_deliverable_icon
        self.assertNotEqual(_pj_deliverable_icon("PDF report"), _pj_deliverable_icon("GitHub repository"))
        self.assertEqual(_pj_deliverable_icon("Source code"), _pj_deliverable_icon("Source code (x.py)"))


if __name__ == "__main__":
    unittest.main()
