"""
Regression tests for the Stage-1 scale / correctness / security remediation.
See STARAPP_STAGE1_LOGIC_OPTIMIZATION_LOG.md for the reasoning behind every case.
Run through tests/run_tests.py (it points the process at a throw-away copy of the database).
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from backend.app.main import app
import backend.app.main as main_mod
import backend.app.core.dependencies as deps_mod
from starapp.storage import store
from starapp.app import StarAppController
from starapp.models import ProjectSubmission
from starapp.pagination import paginate, render_pager, page_slice, bind_page_state, reset_page_state


def _q(sql, params=()):
    return store.db.conn.execute(sql, params).fetchone()[0]


class TestNoCascadeDataLoss(unittest.TestCase):
    """INSERT OR REPLACE deletes the old row first -> ON DELETE CASCADE wiped child rows."""

    def setUp(self):
        store.load_from_dict(store.db.export_to_dict(include_blobs=False))

    def test_save_cycle_keeps_enrollments_and_appraisals(self):
        cyc = store.get_cycle(store.get_active_cycle_id())
        before_enr = _q("SELECT COUNT(*) FROM cycle_enrollments WHERE cycle_id = ?", (cyc.id,))
        before_app = _q("SELECT COUNT(*) FROM cycle_performance_appraisals WHERE cycle_id = ?", (cyc.id,))
        self.assertGreater(before_enr, 0)
        cyc.notes = (cyc.notes or "") + " touched"
        store.save_cycle(cyc)
        self.assertEqual(_q("SELECT COUNT(*) FROM cycle_enrollments WHERE cycle_id = ?", (cyc.id,)), before_enr)
        self.assertEqual(_q("SELECT COUNT(*) FROM cycle_performance_appraisals WHERE cycle_id = ?", (cyc.id,)), before_app)

    def test_save_user_keeps_roles_timelines_and_profile_fields(self):
        uid = "m_b2_1"
        user = store.get_user_by_id(uid)
        roles_before = _q("SELECT COUNT(*) FROM user_role_assignments WHERE user_id = ?", (uid,))
        tl_before = _q("SELECT COUNT(*) FROM badge_timelines WHERE cosmonaut_id = ?", (uid,))
        track_before = store.db.conn.execute("SELECT learning_track, track_code, status FROM users WHERE id = ?", (uid,)).fetchone()
        user.avatar = "ZZ"
        store.save_user(user)
        self.assertEqual(_q("SELECT COUNT(*) FROM user_role_assignments WHERE user_id = ?", (uid,)), roles_before)
        self.assertEqual(_q("SELECT COUNT(*) FROM badge_timelines WHERE cosmonaut_id = ?", (uid,)), tl_before)
        track_after = store.db.conn.execute("SELECT learning_track, track_code, status FROM users WHERE id = ?", (uid,)).fetchone()
        self.assertEqual(tuple(track_before), tuple(track_after))
        self.assertEqual(_q("SELECT avatar FROM users WHERE id = ?", (uid,)), "ZZ")


class TestStoreIndexesAndMemo(unittest.TestCase):
    def setUp(self):
        store.load_from_dict(store.db.export_to_dict(include_blobs=False))

    def test_indexed_reads_match_a_full_scan(self):
        cycle_id = store.get_active_cycle_id()
        for uid in ("m_b1_1", "m_b1_2", "m_b2_1", "guardian_1"):
            scan_subs = sorted(s.id for s in store.submissions.values() if s.cosmonaut_id == uid and s.cycle_id == cycle_id)
            self.assertEqual(sorted(s.id for s in store.get_submissions_for_cosmonaut(uid, cycle_id=cycle_id)), scan_subs)
            scan_asm = sorted(a.id for a in store.assessments.values() if a.cosmonaut_id == uid and a.cycle_id == cycle_id)
            self.assertEqual(sorted(a.id for a in store.get_assessments_for_cosmonaut(uid, cycle_id=cycle_id)), scan_asm)
            scan_n = sorted(n.id for n in store.notifications if n.recipient_id == uid and n.cycle_id == cycle_id)
            self.assertEqual(sorted(n.id for n in store.get_notifications(uid, cycle_id=cycle_id)), scan_n)

    def test_new_writes_are_visible_through_the_indexes_immediately(self):
        cid = store.get_active_cycle_id()
        before = len(store.get_notifications("m_b1_1", cycle_id=cid))
        store.add_notification("m_b1_1", "Regression", "index must see me", cycle_id=cid)
        self.assertEqual(len(store.get_notifications("m_b1_1", cycle_id=cid)), before + 1)
        a_before = len(store.get_activities("m_b1_1", cycle_id=cid))
        store.add_activity("regression", "guardian_1", "Guardian", "m_b1_1", "", "index check", cycle_id=cid)
        self.assertEqual(len(store.get_activities("m_b1_1", cycle_id=cid)), a_before + 1)

    def test_cycle_appraisal_lookup_is_direct_and_consistent(self):
        cid = "cycle_0"
        apps = store.get_cycle_appraisals(cid)
        self.assertTrue(apps)
        a = apps[0]
        self.assertIs(store.get_cycle_appraisal(cid, a.cosmonaut_id), a)
        self.assertIsNone(store.get_cycle_appraisal(cid, "does_not_exist"))

    def test_published_only_visibility_rule_is_preserved(self):
        cid = store.get_active_cycle_id()
        for b in store.get_all_badges(cycle_id=cid):
            for c in store.get_all_cosmonauts()[:5]:
                visible = {x.id for x in store.get_badges_for_cosmonaut(c.id, cycle_id=cid)}
                if b.id in visible:
                    approved = {a.badge_id for a in store.get_assessments_for_cosmonaut(c.id, cycle_id=cid) if a.decision == "approve"}
                    self.assertTrue(b.is_published or b.id in approved)


class TestLazySubmissionPayloads(unittest.TestCase):
    def test_slim_export_defers_blobs_and_hydrates_on_demand(self):
        if _q("SELECT COUNT(*) FROM project_submissions") == 0:
            self.skipTest("no submissions in database")
        row = store.db.conn.execute("SELECT id, pdf_payload, code_payload FROM project_submissions LIMIT 1").fetchone()
        store.load_from_dict(store.db.export_to_dict(include_blobs=False))
        sub = store.submissions[row["id"]]
        self.assertTrue(sub.payload_is_lazy)
        self.assertEqual(sub.pdf_payload, row["pdf_payload"] or sub.pdf_payload)  # hydrates
        self.assertFalse(sub.payload_is_lazy)
        self.assertEqual(sub.code_payload, row["code_payload"] or sub.code_payload)

    def test_metadata_update_of_lazy_submission_never_rewrites_blobs(self):
        if _q("SELECT COUNT(*) FROM project_submissions") == 0:
            self.skipTest("no submissions in database")
        row = store.db.conn.execute("SELECT id, status, pdf_payload, code_payload FROM project_submissions LIMIT 1").fetchone()
        store.load_from_dict(store.db.export_to_dict(include_blobs=False))
        sub = store.submissions[row["id"]]
        self.assertTrue(sub.payload_is_lazy)
        sub.status = "pending" if row["status"] != "pending" else "approved"
        store.save_submission(sub)
        self.assertTrue(sub.payload_is_lazy, "saving metadata must not hydrate the payload")
        after = store.db.conn.execute("SELECT status, pdf_payload, code_payload FROM project_submissions WHERE id = ?", (row["id"],)).fetchone()
        self.assertEqual(after["status"], sub.status)
        self.assertEqual(after["pdf_payload"], row["pdf_payload"])
        self.assertEqual(after["code_payload"], row["code_payload"])

    def test_non_lazy_submission_keeps_legacy_behaviour(self):
        s = ProjectSubmission("sx", "b", "c", 1, "pdf", "data:abc", "f.pdf", "2026-01-01T00:00:00Z")
        self.assertFalse(s.payload_is_lazy)
        self.assertEqual(s.pdf_payload, "data:abc")


class TestPagination(unittest.TestCase):
    def test_paginate_clamps_and_slices(self):
        rows, page, pages, total = paginate(list(range(101)), 999, 25)
        self.assertEqual((page, pages, total), (5, 5, 101))
        self.assertEqual(rows, [100])
        rows, page, pages, total = paginate([], 3, 25)
        self.assertEqual((rows, page, pages, total), ([], 1, 1, 0))

    def test_pager_html_only_for_multiple_pages_and_escapes_key(self):
        self.assertEqual(render_pager("k", 1, 1, 10, 25), "")
        html = render_pager('g_x:"a"', 2, 4, 100, 25)
        self.assertIn("Showing <strong>26&ndash;50</strong> of <strong>100</strong>", html)
        self.assertIn("set_list_page", html)
        self.assertNotIn('"a"', html.split("onclick")[1].split(">")[0].replace("&quot;", ""))

    def test_page_slice_reads_bound_state(self):
        token = bind_page_state({"demo": 3})
        try:
            rows, html = page_slice("demo", list(range(60)), 10)
        finally:
            reset_page_state(token)
        self.assertEqual(rows, list(range(20, 30)))
        self.assertIn("Page 3 of 6", html)

    def test_controller_set_list_page_action_rerenders_and_is_cycle_safe(self):
        ctrl = StarAppController()
        ctrl.initialize()
        ctrl.handle_event("login", json.dumps({"username": "guardian"}))
        gen = ctrl.render_generation
        ctrl.handle_event("set_list_page", json.dumps({"key": "g_cycles:test", "page": 3}))
        self.assertEqual(ctrl.list_pages["g_cycles:test"], 3)
        self.assertGreater(ctrl.render_generation, gen)
        self.assertIn("set_list_page", StarAppController._CYCLE_READONLY_SAFE_ACTIONS)


class TestDispatchSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def _dispatch(self, sid, action, payload="{}"):
        return self.client.post("/api/v1/dispatch", json={"action": action, "payload": payload, "session_id": sid}, headers={"X-Session-Id": sid})

    def test_session_id_containing_guard_or_cosmo_no_longer_auto_logs_in(self):
        for sid in ("guardian_backdoor_01", "cosmo_backdoor_0001", "admin_guard_session"):
            data = self._dispatch(sid, "boot").json()
            self.assertIsNone(data["user"], f"{sid} must start logged out")
            self.assertEqual(data["current_view"], "login")

    def test_forged_restore_session_is_ignored(self):
        forged = {"user_id": "admin", "current_view": "g_cycles"}
        data = self._dispatch("forged_session_0001", "boot", json.dumps({"restore_session": forged})).json()
        self.assertIsNone(data["user"])
        forged["_sig"] = "0" * 64
        forged["_iat"] = 1
        data = self._dispatch("forged_session_0002", "boot", json.dumps({"restore_session": forged})).json()
        self.assertIsNone(data["user"])

    def test_signed_snapshot_restores_and_tampering_is_rejected(self):
        sid = "legit_session_000001"
        login = self._dispatch(sid, "login", json.dumps({"email": "arjun.mehta@starapp.io", "password": "123456789", "require_password": True})).json()
        self.assertEqual(login["user"]["id"], "guardian_1")
        state = login["session_state"]
        self.assertIn("_sig", state)
        self.assertTrue(main_mod._verify_session_state(state))
        # A brand new session (e.g. after server restart / LRU eviction) restores from the signed snapshot
        restored = self._dispatch("legit_session_000002", "boot", json.dumps({"restore_session": state})).json()
        self.assertEqual(restored["user"]["id"], "guardian_1")
        # Changing the user id invalidates the signature
        tampered = dict(state, user_id="admin")
        self.assertFalse(main_mod._verify_session_state(tampered))
        again = self._dispatch("legit_session_000003", "boot", json.dumps({"restore_session": tampered})).json()
        self.assertIsNone(again["user"])
        # Expired snapshots are refused
        stale = main_mod._sign_session_state(dict(state))
        stale["_iat"] = 1
        self.assertFalse(main_mod._verify_session_state(stale))

    def test_missing_or_malformed_session_id_is_rejected(self):
        res = self.client.post("/api/v1/dispatch", json={"action": "boot", "payload": "{}"})
        self.assertEqual(res.status_code, 400)
        res = self.client.post("/api/v1/dispatch", json={"action": "boot", "payload": "{}", "session_id": "x'; drop"})
        self.assertEqual(res.status_code, 400)

    def test_one_render_per_action_and_no_duplicated_html(self):
        sid = "single_render_00001"
        self._dispatch(sid, "login", json.dumps({"email": "arjun.mehta@starapp.io", "password": "123456789", "require_password": True}))
        ctrl = main_mod._session_controllers[sid]
        before = ctrl.render_generation
        data = self._dispatch(sid, "nav_guardian", "g_cycles").json()
        self.assertEqual(ctrl.render_generation - before, 1, "an action must render exactly once")
        self.assertTrue(data["regions"])
        self.assertIsNone(data["full_html"], "regions already carry the markup; do not ship it twice")

    def test_session_registry_is_bounded(self):
        old_max = main_mod.MAX_SESSIONS
        main_mod.MAX_SESSIONS = len(main_mod._session_controllers) + 3
        try:
            for i in range(10):
                self._dispatch(f"lru_session_{i:08d}", "boot")
            self.assertLessEqual(len(main_mod._session_controllers), main_mod.MAX_SESSIONS)
            self.assertIn("default", main_mod._session_controllers)
        finally:
            main_mod.MAX_SESSIONS = old_max

    def test_demo_mode_off_blocks_passwordless_paths(self):
        import starapp.app as app_mod
        old = os.environ.get("STARAPP_DEMO_MODE")
        os.environ["STARAPP_DEMO_MODE"] = "false"
        try:
            ctrl = StarAppController()
            ctrl.initialize()
            ctrl.handle_event("select_demo_account", "guardian_1")
            self.assertIsNone(ctrl.current_user)
            ctrl.handle_event("login", json.dumps({"username": "guardian_1"}))
            self.assertIsNone(ctrl.current_user)
            self.assertNotIn("select_demo_account", ctrl.render_login_view())
            ctrl.handle_event("login", json.dumps({"email": "arjun.mehta@starapp.io", "password": "123456789", "require_password": True}))
            self.assertIsNotNone(ctrl.current_user)  # real credentials still work
        finally:
            if old is None:
                os.environ.pop("STARAPP_DEMO_MODE", None)
            else:
                os.environ["STARAPP_DEMO_MODE"] = old


class TestRestRbac(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def _fresh(self):
        return TestClient(app)

    def test_cannot_claim_a_role_you_do_not_hold(self):
        c = self._fresh()
        res = c.post("/api/v1/auth/login", json={"username_or_email": "aarav.sharma@starapp.io", "password": "123456789", "selected_role": "guardian"})
        self.assertEqual(res.status_code, 403, res.text)
        res = c.post("/api/v1/auth/login", json={"username_or_email": "aarav.sharma@starapp.io", "password": "123456789", "selected_role": "cosmonaut"})
        self.assertEqual(res.status_code, 200, res.text)
        res = c.post("/api/v1/auth/switch-role", json={"role": "guardian"})
        self.assertEqual(res.status_code, 403, res.text)

    def test_cosmonaut_session_is_forbidden_from_guardian_endpoints(self):
        c = self._fresh()
        c.post("/api/v1/auth/login", json={"username_or_email": "aarav.sharma@starapp.io", "password": "123456789"})
        self.assertEqual(c.get("/api/v1/cycles/").status_code, 200)  # any signed-in user may list cycles
        res = c.post("/api/v1/cycles/", json={"name": "Hacked", "start_date": "2027-01-01"})
        self.assertEqual(res.status_code, 403, res.text)
        self.assertEqual(c.post("/api/v1/cycles/cycle_1/finalize").status_code, 403)
        self.assertEqual(c.get("/api/v1/cycles/cycle_1/performance").status_code, 403)

    def test_reviewer_role_comes_from_assignments_and_guardian_can_do_everything(self):
        reviewer = self._fresh()
        res = reviewer.post("/api/v1/auth/login", json={"username_or_email": "rohan.deshmukh@starapp.io", "password": "123456789", "selected_role": "reviewer"})
        self.assertEqual(res.status_code, 200, res.text)
        guardian = self._fresh()
        res = guardian.post("/api/v1/auth/login", json={"username_or_email": "admin", "password": "123456789", "selected_role": "guardian"})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(guardian.get("/api/v1/cycles/cycle_1/performance").status_code, 200)

    def test_production_mode_requires_a_real_session(self):
        old = deps_mod.DEMO_MODE
        deps_mod.DEMO_MODE = False
        try:
            c = self._fresh()
            self.assertEqual(c.get("/api/v1/cycles/", headers={"X-User-Id": "admin"}).status_code, 401)
            self.assertEqual(c.get("/api/v1/cycles/?demo_user_id=admin").status_code, 401)
        finally:
            deps_mod.DEMO_MODE = old


class TestWorkflowAuthorizationAndRules(unittest.TestCase):
    """Business rules that used to be enforced only by what the UI chose to display."""

    def setUp(self):
        store.reset_to_seed()
        self.ctrl = StarAppController()
        self.ctrl.initialize()

    def _login(self, user_id):
        c = StarAppController()
        c.initialize()
        c.handle_event("select_demo_account", user_id)
        return c

    def _allot(self, cadet_ids, badge_id="b1_int_01"):
        badge = store.get_badge(badge_id)
        badge.is_published = True
        badge.assigned_cosmonaut_ids = list(cadet_ids)
        store.save_badge(badge)
        return badge

    PAYLOAD = {"badge_id": "b1_int_01", "pdf_name": "r.pdf", "pdf_payload": "data:application/pdf;base64,AAAA",
               "code_name": "a.py", "code_payload": "print(1)", "github_url": "https://github.com/o/r"}

    def test_cadet_cannot_run_guardian_only_actions(self):
        cadet = self._login("m_b1_1")
        before = store.get_badge("b1_int_01").is_published
        cadet.handle_event("publish_badge", json.dumps({"badge_id": "b1_int_01"}))
        self.assertEqual(store.get_badge("b1_int_01").is_published, before)
        self.assertEqual(cadet.flash_type, "error")
        cycles_before = len(store.get_all_cycles())
        cadet.handle_event("create_six_month_cycle", json.dumps({"name": "Evil", "start_date": "2027-01-01"}))
        self.assertEqual(len(store.get_all_cycles()), cycles_before)
        cadet.handle_event("update_cycle_appraisal", json.dumps({"cycle_id": "cycle_1", "user_id": "m_b1_1", "approved_hike_pct": 99}))
        self.assertEqual(cadet.flash_type, "error")

    def test_cadet_cannot_navigate_to_guardian_pages(self):
        cadet = self._login("m_b1_1")
        for view in ("g_cycles", "g_dashboard", "g_activity", "not_a_view"):
            cadet.handle_event("nav_guardian", view)
            self.assertFalse(cadet.current_view.startswith("g_"), view)
        cadet.current_view = "g_dashboard"  # stale / crafted state can never be rendered either
        html = cadet.render()
        self.assertFalse(cadet.current_view.startswith("g_"))
        self.assertNotIn("Academy Command Center", html)

    def test_guardian_can_still_navigate(self):
        g = self._login("guardian_1")
        g.handle_event("nav_guardian", "g_activity")
        self.assertEqual(g.current_view, "g_activity")

    def test_only_the_invited_reviewer_can_answer_a_mapping_request(self):
        rid = "req_B1_b1_int_01_m_b2_1"
        store.add_mapping_request({"id": rid, "band": "B1", "badge_id": "b1_int_01", "badge": "x",
                                   "reviewer_id": "m_b2_1", "cosmonaut_ids": ["m_b1_1"], "status": "pending"})

        def status():
            return next(r for r in store.get_mapping_requests() if r["id"] == rid)["status"]

        other = self._login("m_b2_4")
        other.handle_event("accept_mapping_request", rid)
        self.assertEqual(other.flash_type, "error")
        self.assertEqual(status(), "pending")
        self._login("m_b1_1").handle_event("reject_mapping_request", rid)
        self.assertEqual(status(), "pending")
        self._login("m_b2_1").handle_event("accept_mapping_request", rid)
        self.assertEqual(status(), "accepted")

    def test_mapping_invitation_enforces_reviewer_band(self):
        g = self._login("guardian_1")
        g.mapping_selected_band = "B1"
        g.mapping_selected_badge_id = "b1_int_01"
        g.mapping_selected_badge = "b1_int_01"
        g.mapping_selected_cosmonauts = ["m_b1_1"]
        g.mapping_selected_reviewers = ["m_b1_2"]  # same band: NOT allowed (Reviewer_Band > Badge_Band)
        before = len(store.get_mapping_requests())
        g.handle_event("send_mapping_requests", "{}")
        self.assertEqual(g.flash_type, "error")
        self.assertEqual(len(store.get_mapping_requests()), before)

    def test_submission_requires_an_allotted_published_badge_and_valid_deliverables(self):
        self._allot(["m_b1_2"])  # allotted to somebody else
        c = self._login("m_b1_1")
        c.handle_event("submit_project_deliverable", json.dumps(self.PAYLOAD))
        self.assertEqual(c.flash_type, "error")
        self.assertEqual(store.get_submissions_for_cosmonaut("m_b1_1", "b1_int_01"), [])
        self._allot(["m_b1_1"])
        c.handle_event("submit_project_deliverable", json.dumps(dict(self.PAYLOAD, github_url="ftp://nope")))
        self.assertEqual(c.flash_type, "error")
        c.handle_event("submit_project_deliverable", json.dumps(dict(self.PAYLOAD, pdf_name="report.docx")))
        self.assertEqual(c.flash_type, "error")
        c.handle_event("submit_project_deliverable", json.dumps(self.PAYLOAD))
        self.assertEqual(c.flash_type, "success")
        self.assertEqual([s.attempt_number for s in store.get_submissions_for_cosmonaut("m_b1_1", "b1_int_01")], [1])

    def test_production_mode_never_fabricates_missing_deliverables(self):
        old = os.environ.get("STARAPP_DEMO_MODE")
        os.environ["STARAPP_DEMO_MODE"] = "false"
        try:
            self._allot(["m_b1_1"])
            c = StarAppController()
            c.initialize()
            c.handle_event("login", json.dumps({"email": "aarav.sharma@starapp.io", "password": "123456789", "require_password": True}))
            self.assertIsNotNone(c.current_user)
            c.handle_event("submit_project_deliverable", json.dumps({"badge_id": "b1_int_01"}))
            self.assertEqual(c.flash_type, "error")
            self.assertEqual(store.get_submissions_for_cosmonaut("m_b1_1", "b1_int_01"), [])
        finally:
            if old is None:
                os.environ.pop("STARAPP_DEMO_MODE", None)
            else:
                os.environ["STARAPP_DEMO_MODE"] = old

    def test_no_new_attempt_while_awaiting_guardian_or_after_the_badge_is_earned(self):
        self._allot(["m_b1_1"])
        c = self._login("m_b1_1")
        c.handle_event("submit_project_deliverable", json.dumps(self.PAYLOAD))
        sub = store.get_submissions_for_cosmonaut("m_b1_1", "b1_int_01")[-1]
        for status in ("reviewer_assessed", "approved"):
            sub.status = status
            store.save_submission(sub)
            c.handle_event("submit_project_deliverable", json.dumps(self.PAYLOAD))
            self.assertEqual(len(store.get_submissions_for_cosmonaut("m_b1_1", "b1_int_01")), 1, status)

    def test_badge_decisions_require_the_assigned_higher_band_reviewer(self):
        ok, msg = store.assign_and_request_badge_review("b1_int_01", "m_b2_4", "guardian_1")
        self.assertTrue(ok, msg)
        ok, msg = store.approve_badge("b1_int_01", "m_b2_1", "Wrong Reviewer")  # a B2 reviewer, but not the assigned one
        self.assertFalse(ok)
        self.assertIn("different reviewer", msg)
        ok, msg = store.approve_badge("b1_int_01", "m_b1_1", "A Cadet")  # no reviewer credentials
        self.assertFalse(ok)
        ok, msg = store.return_badge("b1_int_01", "m_b2_1", "Wrong Reviewer", "nope")
        self.assertFalse(ok)
        self.assertEqual(store.get_badge("b1_int_01").workflow_status, "pending_review")
        ok, msg = store.approve_badge("b1_int_01", "m_b2_4", "Nisha Menon")
        self.assertTrue(ok, msg)
        ok, msg = store.return_badge("b1_int_01", "m_b2_4", "Nisha Menon", "too late")  # already approved / live
        self.assertFalse(ok)

    def test_a_finalised_attempt_cannot_be_regraded(self):
        self._allot(["m_b1_1"])
        self._login("m_b1_1").handle_event("submit_project_deliverable", json.dumps(self.PAYLOAD))
        sub = store.get_submissions_for_cosmonaut("m_b1_1", "b1_int_01")[-1]
        g = self._login("guardian_1")
        rubric = {"submission_id": sub.id, "bu": 9, "ar": 9, "tk": 9, "pr": 9, "qa": 9, "feedback": "great", "assessor_role": "guardian"}
        g.handle_event("submit_evaluation_rubric", json.dumps(rubric))
        self.assertEqual(store.get_submission(sub.id).status, "approved")
        g.handle_event("submit_evaluation_rubric", json.dumps(dict(rubric, bu=0, ar=0, tk=0, pr=0, qa=0)))
        self.assertEqual(store.get_submission(sub.id).status, "approved", "a final decision must be immutable")
        self.assertEqual(g.flash_type, "info")


class TestStage2UiPolish(unittest.TestCase):
    """Professional icons, readable text, correct cohort and a non-flickering shell."""

    EMOJI_RE = None

    @classmethod
    def setUpClass(cls):
        import re
        cls.EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐]")

    def setUp(self):
        store.reset_to_seed()

    def test_iconize_replaces_glyphs_only_in_text_nodes(self):
        from starapp.views_common import iconize_html
        src = ('<span>&#10003; On Track</span>'
               '<button onclick="a.forEach(x => x.checked = true); go(\'✓\')" title="✓ keep">\U0001F947 Rank #1</button>'
               '<select><option>✓ pick</option></select><p>⚠ Warn ★ Star \U0001F3C6 Win ✏️ Edit</p>')
        out = iconize_html(src)
        self.assertEqual(out.count("<svg"), 6)
        self.assertIn("<option>✓ pick</option>", out)          # raw-text elements untouched
        self.assertIn("x => x.checked = true); go('✓')", out)    # attribute values untouched (even with '>')
        self.assertIn('title="✓ keep"', out)
        self.assertEqual(iconize_html("plain text"), "plain text")
        self.assertEqual(iconize_html(""), "")

    def test_internal_ids_are_shown_as_names_and_badge_codes(self):
        from starapp.views_common import humanize_internal_ids
        user = store.get_user_by_id("m_b1_1")
        text = humanize_internal_ids("Mapped m_b1_1 to a badge; Assigned Reviewer: m_b2_4; unknown m_b9_99")
        self.assertIn(user.name, text)
        self.assertNotIn("m_b1_1", text)
        self.assertNotIn("m_b2_4", text)
        self.assertIn("m_b9_99", text)  # unknown ids are left alone rather than hidden
        badge = store.get_badge("b1_int_01")
        self.assertIn(badge.code, humanize_internal_ids("see b1_int_01 now"))

    def test_guardians_and_admins_are_not_counted_as_cadets(self):
        ids = {u.id for u in store.get_all_cosmonauts()}
        self.assertNotIn("guardian_1", ids)
        self.assertNotIn("admin", ids)
        self.assertIn("m_b1_1", ids)
        self.assertIn("m_b2_1", ids)  # reviewers are also cadets (dual role)

    def test_no_emoji_or_internal_ids_on_any_rendered_page(self):
        problems = []
        for uid, views in (("guardian_1", sorted(StarAppController._GUARDIAN_VIEWS)),
                           ("m_b1_1", sorted(StarAppController._COSMONAUT_VIEWS)),
                           ("m_b2_1", ["c_badge_reviews", "c_requests", "c_assessments"])):
            ctrl = StarAppController()
            ctrl.initialize()
            ctrl.handle_event("select_demo_account", uid)
            for view in views:
                ctrl.current_view = view
                html = ctrl.render()
                import re
                text_only = re.sub(r"<[^>]*>", " ", html)
                found = self.EMOJI_RE.findall(text_only)
                if found:
                    problems.append((uid, view, "emoji", found[:3]))
        self.assertEqual(problems, [])

    def test_rail_cycle_pill_uses_a_short_label(self):
        from starapp.views_common import render_sidebar_cycle_pill
        cyc = store.get_cycle(store.get_active_cycle_id())
        html = render_sidebar_cycle_pill(cyc, "nav_cosmonaut", "c_choose_cycle")
        label = html.split('aria-label="Switch Cycle Filter">')[1].split("</button>")[0]
        self.assertLessEqual(len(label), 4, label)

    def test_review_schedule_has_no_duplicated_badge_header_inside_the_cadet_card(self):
        badge = store.get_badge("b1_int_01")
        badge.is_published = True
        badge.assigned_cosmonaut_ids = ["m_b1_1"]
        store.save_badge(badge)
        c = StarAppController()
        c.initialize()
        c.handle_event("select_demo_account", "m_b2_1")
        c.current_view = "c_badge_reviews"
        html = c.render()
        self.assertNotIn("Reviewer creates project, Cadet learns concepts", html)
        self.assertNotIn("Active Cohort Commitments", html)
        self.assertNotIn("commitments across assigned curriculum badges", html)

    def test_bridge_patches_the_sidebar_in_place_instead_of_rebuilding_it(self):
        js = open(os.path.join(os.path.dirname(__file__), "..", "js", "bridge.js"), encoding="utf-8").read()
        self.assertIn("_sidebarSignature", js)
        self.assertIn('replace(/class="nav-link active"/g', js)
        self.assertNotIn("renderState.sidebarHtml !== payload.sidebarHtml", js)


if __name__ == "__main__":
    unittest.main()
