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


class TestBadgeApprovalQueueReviewerControl(unittest.TestCase):
    """Reviewer Badge Approval: cards, Inspect = activity log, Edit = change / cancel the reviewer."""

    BADGE = "b1_int_01"

    def setUp(self):
        store.reset_to_seed()
        self.guardian = StarAppController()
        self.guardian.initialize()
        self.guardian.handle_event("select_demo_account", "guardian_1")

    def _assign(self, reviewer_id):
        self.guardian.handle_event(
            "send_badge_review_request", json.dumps({"badge_id": self.BADGE, "reviewer_id": reviewer_id})
        )

    def _cancel_events(self):
        return [e for e in store.get_badge_review_history(badge_id=self.BADGE) if e["event_type"] == "reviewer_cancelled"]

    def test_cancel_reviewer_resets_badge_and_revokes_authority(self):
        self._assign("m_b2_1")
        self.assertEqual(store.get_badge(self.BADGE).workflow_status, "pending_review")
        row = store.db.conn.execute("SELECT * FROM badges WHERE id = ?", (self.BADGE,)).fetchone()
        self.assertIsNone(store.db.authorize_badge_decision(row, "m_b2_1"))

        self.guardian.handle_event("cancel_badge_reviewer", self.BADGE)
        badge = store.get_badge(self.BADGE)
        self.assertEqual(badge.workflow_status, "ready_for_review")
        self.assertFalse(badge.assigned_reviewer_id)
        self.assertEqual(len(self._cancel_events()), 1)
        status = _q("SELECT status FROM badge_reviewer_assignments WHERE badge_id = ? AND reviewer_id = 'm_b2_1' "
                    "ORDER BY assigned_at DESC LIMIT 1", (self.BADGE,))
        self.assertEqual(status, "cancelled")
        row = store.db.conn.execute("SELECT * FROM badges WHERE id = ?", (self.BADGE,)).fetchone()
        self.assertIsNotNone(store.db.authorize_badge_decision(row, "m_b2_1"))

    def test_reassign_revokes_previous_reviewer(self):
        self._assign("m_b2_1")
        self._assign("m_b3_1")
        badge = store.get_badge(self.BADGE)
        self.assertEqual(badge.assigned_reviewer_id, "m_b3_1")
        row = store.db.conn.execute("SELECT * FROM badges WHERE id = ?", (self.BADGE,)).fetchone()
        self.assertIsNotNone(store.db.authorize_badge_decision(row, "m_b2_1"), "removed reviewer must not keep decision rights")
        self.assertIsNone(store.db.authorize_badge_decision(row, "m_b3_1"))
        notes = [e["notes"] for e in store.get_badge_review_history(badge_id=self.BADGE)]
        self.assertTrue(any("Reviewer changed from" in (n or "") for n in notes))

    def test_cancel_is_guardian_only_and_needs_an_active_reviewer(self):
        self._assign("m_b2_1")
        cadet = StarAppController()
        cadet.initialize()
        cadet.handle_event("select_demo_account", "m_b1_1")
        cadet.handle_event("cancel_badge_reviewer", self.BADGE)
        self.assertEqual(cadet.flash_type, "error")
        self.assertEqual(store.get_badge(self.BADGE).assigned_reviewer_id, "m_b2_1")
        # nothing to cancel once the reviewer is gone
        self.guardian.handle_event("cancel_badge_reviewer", self.BADGE)
        self.guardian.handle_event("cancel_badge_reviewer", self.BADGE)
        self.assertEqual(self.guardian.flash_type, "error")
        self.assertEqual(len(self._cancel_events()), 1)

    def test_queue_cards_and_inspect_activity_log(self):
        self._assign("m_b2_1")
        self.guardian.handle_event("select_create_badge_band", "B1")
        self.guardian.handle_event("nav_guardian", "g_badge_approval")
        html = self.guardian.render()
        self.assertIn('class="ba-row"', html)
        self.assertIn("open_badge_activity_log", html)          # Inspect now opens the log
        self.assertIn("manage_badge_reviewer", html)            # Edit = manage the reviewer
        self.assertNotIn("edit_submitted_badge", html)          # ... not the badge content
        # while a reviewer holds the badge there is no picker (changing it is done through Edit)
        self.assertNotIn('class="ba-assign"', html)
        # once the reviewer is cancelled, select + Send appear together in one .ba-assign row
        self.guardian.handle_event("cancel_badge_reviewer", self.BADGE)
        html = self.guardian.render()
        self.assertIn('class="ba-assign"', html)
        self._assign("m_b2_1")

        self.guardian.handle_event("open_badge_activity_log", self.BADGE)
        self.assertEqual(self.guardian.active_modal, "badge_activity_log")
        modal = self.guardian.render()
        self.assertIn("Activity &amp; audit log", modal)
        self.assertIn("Review requested from", modal)
        self.assertIn("al-timeline", modal)

    def test_edit_opens_reviewer_management_only(self):
        self._assign("m_b2_1")
        self.guardian.handle_event("manage_badge_reviewer", self.BADGE)
        self.assertEqual(self.guardian.active_modal, "badge_reviewer_manage")
        html = self.guardian.render()
        self.assertIn("Reviewer assignment", html)
        self.assertIn("cancel_badge_reviewer", html)
        self.assertIn("Reassign", html)
        # Edit no longer exposes the badge-content editor on this page
        self.assertNotIn("edit-badge-title", html)
        self.assertNotIn("submitReviewedBadgeEdit", html)

    def test_manage_reviewer_is_guardian_only_and_edit_hidden_for_reviewers(self):
        self._assign("m_b2_1")
        reviewer = StarAppController()
        reviewer.initialize()
        reviewer.handle_event("select_demo_account", "m_b2_1")
        reviewer.handle_event("manage_badge_reviewer", self.BADGE)
        self.assertNotEqual(reviewer.active_modal, "badge_reviewer_manage")
        self.assertEqual(reviewer.flash_type, "error")
        reviewer.handle_event("nav_cosmonaut", "c_requests")
        self.assertNotIn("manage_badge_reviewer", reviewer.render())

    def test_reassign_from_manage_modal_closes_it(self):
        self._assign("m_b2_1")
        self.guardian.handle_event("manage_badge_reviewer", self.BADGE)
        self._assign("m_b3_1")
        self.assertIsNone(self.guardian.active_modal)
        self.assertEqual(store.get_badge(self.BADGE).assigned_reviewer_id, "m_b3_1")

    def test_cancel_from_manage_modal_closes_it(self):
        self._assign("m_b2_1")
        self.guardian.handle_event("manage_badge_reviewer", self.BADGE)
        self.guardian.handle_event("cancel_badge_reviewer", self.BADGE)
        self.assertIsNone(self.guardian.active_modal)
        self.assertEqual(store.get_badge(self.BADGE).workflow_status, "ready_for_review")


class TestBadgeApprovalFiltersAndSearch(unittest.TestCase):
    """Status / Band dropdowns and the search box of Reviewer Badge Approval."""

    def setUp(self):
        store.reset_to_seed()
        self.g = StarAppController()
        self.g.initialize()
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("select_create_badge_band", "B1")   # a band is selected in the sidebar
        self.g.handle_event("nav_guardian", "g_badge_approval")

    def _rows(self):
        html = self.g.render()
        return html.count('class="ba-row"'), html

    def _count(self, html, label):
        import re
        m = re.search(label + r" \((\d+)\)", html)
        self.assertIsNotNone(m, label)
        return int(m.group(1))

    def test_queue_is_scoped_to_the_active_band_without_a_band_dropdown(self):
        all_badges = store.get_all_badges()
        b1 = len([b for b in all_badges if b.target_band == "B1"])
        rows, html = self._rows()
        self.assertEqual(rows, b1)
        self.assertNotIn("ba-band-filter-select", html)
        self.assertNotIn("filter_badge_approval_band", html)
        self.assertNotIn("All Bands", html)
        self.assertEqual(self._count(html, "All Submissions"), b1)

        # switching the band workspace re-scopes the queue; no active band lists every band
        self.g.handle_event("select_create_badge_band", "B2")
        self.g.handle_event("nav_guardian", "g_badge_approval")
        b2 = len([b for b in all_badges if b.target_band == "B2"])
        self.assertEqual(self._count(self.g.render(), "All Submissions"), b2)
        self.g.handle_event("select_create_badge_band", "")
        self.g.handle_event("nav_guardian", "g_badge_approval")
        self.assertEqual(self._count(self.g.render(), "All Submissions"), len(all_badges))

    def test_status_dropdown_filters_cards(self):
        for status, label in (("pending_review", "Pending Review"), ("approved", "Approved Badges")):
            self.g.handle_event("filter_badge_approval", status)
            rows, html = self._rows()
            expected = len([b for b in store.get_all_badges()
                            if b.target_band == "B1" and b.workflow_status == status])
            self.assertEqual(rows, expected, status)
            self.assertEqual(self._count(html, label), expected)

    def test_search_matches_title_code_skill_reviewer_and_status(self):
        self.g.handle_event("select_create_badge_band", "")      # no active band -> all bands
        self.g.handle_event("nav_guardian", "g_badge_approval")
        badge = next(b for b in store.get_all_badges() if b.assigned_reviewer_id)
        reviewer = store.get_user_by_id(badge.assigned_reviewer_id)
        for needle in (badge.title.split()[0], badge.code.lower(), reviewer.name.split()[0].upper()):
            self.g.handle_event("search_badge_approval", needle)
            rows, html = self._rows()
            self.assertGreaterEqual(rows, 1, needle)
            self.assertIn(badge.title, html, needle)
        self.g.handle_event("search_badge_approval", "pending review")
        rows, _ = self._rows()
        self.assertEqual(rows, len([b for b in store.get_all_badges() if b.workflow_status == "pending_review"]))
        self.g.handle_event("search_badge_approval", "zzz-no-such-badge")
        rows, html = self._rows()
        self.assertEqual(rows, 0)
        self.assertIn("No Badges Found", html)

    def test_search_and_band_apply_to_review_history_too(self):
        # the seed has no review events in the active cycle yet: dispatching a review request logs one
        self.g.handle_event("send_badge_review_request", json.dumps({"badge_id": "b1_int_01", "reviewer_id": "m_b3_1"}))
        self.g.handle_event("filter_badge_approval", "history")
        html = self.g.render()
        total = self._count(html, "Review History &amp; Audit")
        self.assertGreater(total, 0)
        self.g.handle_event("search_badge_approval", "zzz-no-such-event")
        html = self.g.render()
        self.assertEqual(self._count(html, "Review History &amp; Audit"), 0)
        self.assertIn("No review events match", html)

    def test_search_box_uses_the_debounced_dispatch(self):
        _, html = self._rows()
        self.assertIn("debouncedDispatch('search_badge_approval'", html)
        js = open(os.path.join(os.path.dirname(__file__), "..", "js", "bridge.js"), encoding="utf-8").read()
        self.assertIn("debouncedDispatch(action", js)
        self.assertIn("isTypeAheadAction", js)


class TestPageTitleInBackStrip(unittest.TestCase):
    """The page title sits in the Back-button row; the heading stays in the DOM (visually hidden)."""

    def test_hoist_page_title_unit(self):
        from starapp.views_common import hoist_page_title, render_global_back_bar
        html, title = hoist_page_title('<div><h2 style="x:1">Role &amp; Competency <b>Matrix</b></h2><p>sub</p></div>')
        self.assertEqual(title, "Role & Competency Matrix")
        self.assertIn('<h2 style="x:1" class="app-title-hoisted">', html)
        html, title = hoist_page_title('<h1 class="a b">Page</h1>')
        self.assertIn('class="app-title-hoisted a b"', html)
        self.assertEqual(hoist_page_title("<div>no heading</div>"), ("<div>no heading</div>", ""))
        far = "<p>" + "x" * 2000 + "</p><h2>Deep heading</h2>"
        self.assertEqual(hoist_page_title(far), (far, ""))
        self.assertNotIn("app-strip-title", render_global_back_bar())
        self.assertIn('class="app-strip-title"', render_global_back_bar("A & B"))
        self.assertIn("A &amp; B", render_global_back_bar("A & B"))

    def test_badge_approval_title_is_in_the_back_strip(self):
        store.reset_to_seed()
        g = StarAppController()
        g.initialize()
        g.handle_event("select_demo_account", "guardian_1")
        g.handle_event("nav_guardian", "g_badge_approval")
        g.render()
        regions = g.last_rendered_regions
        self.assertIn('class="app-strip-title"', regions["topbarHtml"])
        self.assertIn("Reviewer Badge Approval", regions["topbarHtml"])
        self.assertIn("app-title-hoisted", regions["mainContentHtml"])
        # the visible title is no longer a big block inside the page
        self.assertNotIn("margin:0 0 18px 0;\">Reviewer Badge Approval", regions["mainContentHtml"].replace("app-title-hoisted ", ""))

    def test_other_titled_pages_and_hero_pages(self):
        store.reset_to_seed()
        r = StarAppController()
        r.initialize()
        r.handle_event("select_demo_account", "m_b2_1")
        r.handle_event("nav_cosmonaut", "c_requests")
        r.render()
        self.assertIn("Review Requests", r.last_rendered_regions["topbarHtml"])
        r.handle_event("nav_cosmonaut", "c_dashboard")          # hero page keeps its own designed header
        r.render()
        self.assertNotIn("app-strip-title", r.last_rendered_regions["topbarHtml"])
        self.assertNotIn("app-title-hoisted", r.last_rendered_regions["mainContentHtml"])


class TestGuardianSidebarHeader(unittest.TestCase):
    """The Guardian sidebar top-left shows only the band (no brand, portal name or role pill)."""

    def test_header_shows_only_the_band(self):
        store.reset_to_seed()
        g = StarAppController()
        g.initialize()
        g.handle_event("select_demo_account", "guardian_1")
        g.handle_event("select_create_badge_band", "B1")
        g.handle_event("nav_guardian", "g_badge_approval")
        g.render()
        side = g.last_rendered_regions["sidebarHtml"]
        self.assertIn('class="sidebar-band-chip"', side)
        self.assertIn(">B1</span>", side)
        for gone in ("TARAPP", "GUARDIAN PORTAL", "role-badge-pill", "Training Mentor", "brand-title", "sidebar-band-switcher"):
            self.assertNotIn(gone, side, gone)
        self.assertEqual(side.count(">B1</span>"), 1)           # shown once, not mini + expanded copies
        self.assertIn("sidebar-collapse-btn", side)             # the (hidden) toggle hook is kept

    def test_footer_and_signout_have_their_own_spacing(self):
        css = open(os.path.join(os.path.dirname(__file__), "..", "css", "layout.css"), encoding="utf-8").read()
        footer = css[css.index(".sidebar-footer {"):]
        footer = footer[:footer.index("}")]
        self.assertIn("padding: 12px 12px 16px", footer)
        profile = css[css.index(".lg-sidebar-profile {"):]
        profile = profile[:profile.index("}")]
        self.assertIn("box-sizing: border-box", profile)
        self.assertIn("padding: 12px 14px 14px", profile)


class TestMappingPageCards(unittest.TestCase):
    """Mapping page: minimal selection cards (no icons / ids / descriptions) and compact saved-mapping cards."""

    def setUp(self):
        store.reset_to_seed()
        self.g = StarAppController()
        self.g.initialize()
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("select_create_badge_band", "B1")
        self.g.handle_event("nav_guardian", "g_mapping")

    def _page(self):
        self.g.render()
        return self.g.last_rendered_regions["mainContentHtml"]

    def test_selection_cards_have_no_subtitles_icons_ids_or_descriptions(self):
        html = self._page()
        for gone in ("Cohort Roles", "Approved Badges (", "Candidates", "Eligible", "mapping-card-subtitle",
                     "All Higher Bands", "B1-INT-01", "B1-ARC-01"):
            self.assertNotIn(gone, html, gone)
        # no letter icons / avatars / category-and-band description lines inside the lists
        self.assertNotIn("mapping-badge-item selected\"><div style", html)
        self.assertNotIn("border-radius:999px; background:rgba(23,52,92,0.12)", html)     # cosmonaut avatar circle
        self.assertNotIn("border-radius:999px; background:rgba(5,150,105,0.14)", html)    # reviewer avatar circle
        self.assertNotIn("Data &amp; Machine / ", html)
        self.assertNotIn(" &bull; Band B1</div>", html)
        # names are still there
        for name in ("Intelligent Apps Foundations", "Solutions Designer", "Aarav Sharma"):
            self.assertIn(name, html)

    def test_reviewer_band_filter_is_all_bands_in_one_row(self):
        html = self._page()
        self.assertIn('class="mapping-band-row"', html)
        row = html.split('class="mapping-band-row"', 1)[1].split("</div>", 1)[0]
        self.assertIn("All bands", row)
        for b in ("B2", "B3", "B4", "B5", "B6"):
            self.assertIn(">%s</button>" % b, row)
        css = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()
        rule = css[css.index(".mapping-band-row {"):]
        rule = rule[:rule.index("}")]
        self.assertIn("flex-wrap: nowrap", rule)
        self.assertIn("flex: 0 0 auto", rule)       # must not be squeezed (it clipped the pills once)
        # the 'All bands' pill still toggles every higher band
        before = len(self.g.mapping_selected_reviewer_bands)
        self.g.handle_event("select_mapping_reviewer_band", "ALL")
        self.assertGreaterEqual(len(self.g.mapping_selected_reviewer_bands), before)

    def test_saved_mapping_cards_show_only_title_state_stats_and_link(self):
        self.g.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2"]
        self.g.mapping_selected_reviewers = ["m_b2_1"]
        self.g.mapping_selected_badge = "Signals Foundations"
        self.g.handle_event("send_mapping_requests", "{}")
        html = self._page()
        self.assertIn("mapping-badge-rect-card", html)
        card = html.split('class="mapping-badge-rect-card"', 1)[1].split("</button>", 1)[0]
        self.assertIn('class="mbc-title"', card)
        self.assertIn("requests accepted", card)
        self.assertIn("cosmonauts selected", card)
        self.assertIn("Open Requests, Cohort &amp; Mapping", card)
        self.assertNotIn("Band B1", card)            # no band chip
        self.assertNotIn("ba-code-tag", card)
        self.assertNotIn("font-family:var(--font-family-mono)", card)   # no code chip
        self.assertNotRegex(card, r"\d{4}-\d{2}-\d{2}")                # no dates / timestamp pill
        self.assertNotIn("Nov", card)


class TestMappingListsScrollAndFlow(unittest.TestCase):
    """Long selection lists scroll inside their card (rows keep their height); saved cards show the flow."""

    def setUp(self):
        store.reset_to_seed()
        self.g = StarAppController()
        self.g.initialize()
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("select_create_badge_band", "B1")
        self.g.handle_event("nav_guardian", "g_mapping")
        self.css = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()

    def test_rows_never_shrink_and_the_list_scrolls(self):
        rule = self.css[self.css.index(".mapping-scroll-list {"):]
        rule = rule[:rule.index("}")]
        self.assertIn("overflow-y: auto", rule)
        self.assertIn("max-height: clamp(", rule)          # responsive to the window height
        child = self.css[self.css.index(".mapping-scroll-list > * {"):]
        child = child[:child.index("}")]
        self.assertIn("flex: 0 0 auto", child)             # overflow:hidden rows used to be squashed instead of scrolling
        row = self.css[self.css.index(".mapping-member-item,\n.mapping-role-toggle,\n.mapping-badge-item {"):]
        row = row[:row.index("}")]
        self.assertIn("min-height: 56px", row)

    def test_select_all_renders_every_person_in_a_scroll_list(self):
        self.g.handle_event("select_mapping_reviewer_band", "ALL")
        self.g.handle_event("select_all_mapping_reviewers", "{}")
        self.g.handle_event("select_all_mapping_cosmonauts", "{}")
        self.g.render()
        html = self.g.last_rendered_regions["mainContentHtml"]
        self.assertIn('id="mapping-reviewer-scroll"', html)
        self.assertGreater(html.count("mapping-member-item selected"), 20)

    def test_saved_cards_show_a_tick_checklist(self):
        self.g.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2"]
        self.g.mapping_selected_reviewers = ["m_b2_1"]
        self.g.mapping_selected_badge = "Signals Foundations"
        self.g.handle_event("send_mapping_requests", "{}")
        self.g.render()
        html = self.g.last_rendered_regions["mainContentHtml"]
        card = html.split('class="mapping-badge-rect-card"', 1)[1].split("</button>", 1)[0]
        self.assertIn('class="mbc-checks"', card)
        self.assertEqual(card.count('class="mbc-check '), 3)
        for sentence in ("requests accepted", "cosmonauts selected", "Not mapped yet"):
            self.assertIn(sentence, card)
        self.assertIn("mbc-check is-done", card)           # a ticked line ...
        self.assertIn("mbc-check is-none", card)           # ... and a dash line (not mapped yet)
        for gone in ("mbc-flow", "mbc-step", "mbc-stats"):
            self.assertNotIn(gone, card)                   # earlier layouts are gone


class TestMappingRequestTwentyFourHourWindow(unittest.TestCase):
    """A reviewer has 24 hours to answer a mapping request; silence = not accepted. Both sides see a live countdown."""

    def setUp(self):
        store.reset_to_seed()
        self.g = StarAppController()
        self.g.initialize()
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("select_create_badge_band", "B1")
        self.g.handle_event("nav_guardian", "g_mapping")
        self.g.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2"]
        self.g.mapping_selected_reviewers = ["m_b2_1"]
        self.g.mapping_selected_badge = "Signals Foundations"
        self.g.handle_event("send_mapping_requests", "{}")
        self.req = next(r for r in store.get_mapping_requests() if r["reviewer_id"] == "m_b2_1")

    def _expire_now(self):
        import datetime
        past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).isoformat()
        self.req["expires_at"] = past

    def _guardian_detail(self):
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("open_mapping_badge_detail", "badge_b1_signals")
        self.g.render()
        return self.g.last_rendered_regions["mainContentHtml"]

    def test_send_stamps_a_deadline_24_hours_after_sending(self):
        from starapp.storage import _parse_utc
        sent, due = _parse_utc(self.req["sent_at"]), _parse_utc(self.req["expires_at"])
        self.assertEqual(int((due - sent).total_seconds()), 24 * 3600)
        self.assertEqual(self.req["status"], "pending")

    def test_guardian_and_reviewer_both_see_the_countdown(self):
        html = self._guardian_detail()
        self.assertIn('class="rq-timer', html)
        left = int(html.split('data-remaining="', 1)[1].split('"', 1)[0])
        self.assertTrue(86000 < left <= 86400)                                      # ~24h left
        self.g.handle_event("select_demo_account", "m_b2_1")
        self.g.handle_event("nav_cosmonaut", "c_requests")
        self.g.render()
        self.assertIn('class="rq-timer', self.g.last_rendered_regions["mainContentHtml"])

    def test_unanswered_request_is_auto_declined_after_24_hours(self):
        self._expire_now()
        self.g.handle_event("nav_guardian", "g_mapping")          # any action runs the sweep
        req = next(r for r in store.get_mapping_requests() if r["id"] == self.req["id"])
        self.assertEqual(req["status"], "rejected")
        self.assertTrue(req["expired"])
        titles = [n.title for n in store.notifications]
        self.assertTrue(any(t.startswith("Mapping Request Expired") for t in titles))     # Guardian told
        self.assertTrue(any(t.startswith("Review Request Expired") for t in titles))      # reviewer told
        html = self._guardian_detail()
        self.assertIn("Expired", html)
        self.assertIn("Resend", html)
        self.assertNotIn('class="rq-timer', html)                                         # no countdown once closed

    def test_late_accept_is_refused_even_if_the_sweep_has_not_run(self):
        self._expire_now()
        self.g.handle_event("select_demo_account", "m_b2_1")      # the sweep runs at the start of this very event
        self.g.handle_event("accept_mapping_request", self.req["id"])
        req = next(r for r in store.get_mapping_requests() if r["id"] == self.req["id"])
        self.assertEqual(req["status"], "rejected")
        self.assertTrue(req["expired"])

    def test_answering_in_time_clears_the_deadline_and_is_final(self):
        self.g.handle_event("select_demo_account", "m_b2_1")
        self.g.handle_event("accept_mapping_request", self.req["id"])
        self._expire_now()                                        # an old deadline must not touch an answered request
        self.g.handle_event("nav_cosmonaut", "c_requests")
        req = next(r for r in store.get_mapping_requests() if r["id"] == self.req["id"])
        self.assertEqual(req["status"], "accepted")
        self.assertTrue(req.get("responded_at"))

    def test_guardian_can_resend_an_expired_request_and_only_a_guardian(self):
        self._expire_now()
        self.g.handle_event("nav_guardian", "g_mapping")
        self.g.handle_event("select_demo_account", "m_b2_1")
        self.g.handle_event("resend_mapping_request", self.req["id"])          # a reviewer may not
        req = next(r for r in store.get_mapping_requests() if r["id"] == self.req["id"])
        self.assertEqual(req["status"], "rejected")
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("resend_mapping_request", self.req["id"])
        req = next(r for r in store.get_mapping_requests() if r["id"] == self.req["id"])
        self.assertEqual(req["status"], "pending")
        self.assertFalse(req.get("expired"))
        from starapp.storage import mapping_request_seconds_left
        self.assertGreater(mapping_request_seconds_left(req), 86000)

    def test_badge_title_sits_in_the_back_button_row_and_history_borders_are_coded(self):
        html = self._guardian_detail()
        regions = self.g.last_rendered_regions
        self.assertIn("Signals Foundations", regions["topbarHtml"])        # title is in the Back-button row ...
        self.assertIn("app-title-hoisted", html)                           # ... the page keeps only a hidden heading
        self.assertNotIn("md-hero", html)
        css = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()
        self.assertIn(".rq-row.is-pending { border-left-color: #071629;", css)     # not accepted yet -> black
        self.assertIn(".rq-row.is-accepted { border-left-color: #059669;", css)    # accepted -> green
        rej = css[css.index(".rq-row.is-rejected,"):]
        self.assertIn("border-left-color: #dc2626", rej[:120])                     # rejected / expired -> red

    def test_detail_page_no_longer_shows_codes_dates_or_the_ready_sentence(self):
        html = self._guardian_detail()
        self.assertNotIn("Ready to equally partition", html)
        self.assertNotIn("(5 Days)", html)
        self.assertNotIn("B1-SIG", html)
        for cls in ("md-card", "rq-table", "md-title"):
            self.assertIn(cls, html)
        for gone in ("24 hours to respond", "md-hero-pills", "md-sub"):
            self.assertNotIn(gone, html)                  # no sub-titles / counter pills under the titles


class TestAllotmentModals(unittest.TestCase):
    """Badge Allotment -> Timeline & Mapping and Edit Badge modals: structured, every field still wired."""

    def setUp(self):
        store.reset_to_seed()
        self.g = StarAppController()
        self.g.initialize()
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("nav_guardian", "g_allotment")

    def _map_signals(self):
        self.g.handle_event("select_create_badge_band", "B1")
        self.g.handle_event("nav_guardian", "g_mapping")
        self.g.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2"]
        self.g.mapping_selected_reviewers = ["m_b2_1"]
        self.g.mapping_selected_badge = "Signals Foundations"
        self.g.handle_event("send_mapping_requests", "{}")
        req = next(r for r in store.get_mapping_requests() if r["reviewer_id"] == "m_b2_1")
        self.g.handle_event("select_demo_account", "m_b2_1")
        self.g.handle_event("accept_mapping_request", req["id"])
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("execute_cosmonaut_mapping", json.dumps({"band": "B1", "badge_id": "badge_b1_signals", "badge": "Signals Foundations"}))

    def test_timeline_modal_is_read_only_with_mapping_and_numbered_steps(self):
        self._map_signals()
        self.g.handle_event("open_badge_timeline_mapping_modal", "badge_b1_signals")
        html = self.g.render_active_modal()
        for cls in ("tm-wrap", "tm-grid", "tm-rev", "tm-steps", "tm-date-ro"):
            self.assertIn(cls, html)
        self.assertIn("Personnel Mapping", html)
        self.assertIn("Assigned Cosmonauts (", html)
        self.assertEqual(html.count('<li class="tm-step '), 6)               # six numbered gates
        self.assertNotIn("<input", html)                                     # nothing can be typed or picked here
        self.assertNotIn("Save Timeline", html)
        self.assertIn("Read-only view", html)
        self.assertNotIn("(3 Working Days)", html)
        self.assertNotIn("2026-11-18 →", html)

    def test_timeline_modal_still_saves(self):
        payload = {"badge_id": "badge_b1_signals", "learning_start_date": "2026-11-12", "learning_end_date": "2026-11-22",
                   "project_start_date": "2026-11-23", "project_end_date": "2026-12-02", "submission_deadline": "2026-12-04",
                   "review_date": "2026-12-07", "expected_award_date": "2026-12-09"}
        self.g.handle_event("save_allotment_timeline", json.dumps(payload))
        self.assertEqual(store.get_badge("badge_b1_signals").default_timeline["submission_deadline"], "2026-12-04")

    def _map_two_reviewers(self):
        self.g.handle_event("select_create_badge_band", "B1")
        self.g.handle_event("nav_guardian", "g_mapping")
        self.g.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4"]
        self.g.mapping_selected_reviewers = ["m_b2_1", "m_b2_2"]
        self.g.mapping_selected_badge = "Signals Foundations"
        self.g.handle_event("send_mapping_requests", "{}")
        for r in [r for r in store.get_mapping_requests() if r["reviewer_id"] in ("m_b2_1", "m_b2_2")]:
            self.g.handle_event("select_demo_account", r["reviewer_id"])
            self.g.handle_event("accept_mapping_request", r["id"])
        self.g.handle_event("select_demo_account", "guardian_1")
        self.g.handle_event("execute_cosmonaut_mapping", json.dumps({"band": "B1", "badge_id": "badge_b1_signals", "badge": "Signals Foundations"}))

    def _owners(self):
        out = {}
        for m in store.get_band_mappings():
            if m.get("badge_id") == "badge_b1_signals":
                for c in m.get("cosmonauts") or []:
                    out[c] = (m.get("reviewers") or [""])[0]
        return out

    def test_edit_modal_groups_cosmonauts_under_their_reviewers_with_add_dropdowns(self):
        self._map_two_reviewers()
        self.g.handle_event("open_edit_badge_modal", "badge_b1_signals")
        html = self.g.render_active_modal()
        for fid in ("badge-code", "badge-title", "badge-desc", "badge-reqs", "tl-alloc-date", "tl-learn-start", "tl-learn-end",
                    "tl-proj-start", "tl-proj-end", "tl-sub-deadline", "tl-review-date", "tl-award-date"):
            self.assertIn(f'id="{fid}"', html)                          # the submit handler reads these ids
        for cls in ("eb-grid", "eb-assign", "eb-timeline", "eb-groups", "eb-pool"):
            self.assertIn(cls, html)
        self.assertIn("modal-xl", html)
        owners = self._owners()
        self.assertEqual(set(owners.values()), {"m_b2_1", "m_b2_2"})
        self.assertEqual(html.count('class="eb-group"'), 2)             # one group per mapped reviewer
        for rid in ("m_b2_1", "m_b2_2"):
            self.assertIn(f'<div class="eb-group" data-rid="{rid}"', html)
        self.assertEqual(html.count('class="eb-combo"'), 2)             # each reviewer has its own Add dropdown
        self.assertEqual(html.count('name="badge-assignee" value'), len(store.get_all_cosmonauts()))   # one row per cosmonaut
        assigned = set(store.get_badge("badge_b1_signals").assigned_cosmonaut_ids)
        groups_part = html.split('id="eb-groups"', 1)[1].split('id="eb-pool"', 1)[0]
        self.assertEqual(groups_part.count('class="eb-person is-on"'), len(assigned))                 # only assigned people are listed
        self.assertIn("Band B1 cosmonauts not on this badge yet", html)                              # criteria shown in the menu
        for fn in ("toggleAssignMenu", "filterAssignMenu", "addAssignee", "removeAssignee", "moveAssignee",
                   "addAllShownAssignees", "clearAssignees", "collectReviewerAssignments"):
            self.assertIn(fn, html)

    def test_dropdown_only_offers_cosmonauts_of_the_badge_band(self):
        self._map_two_reviewers()
        self.g.handle_event("open_edit_badge_modal", "badge_b1_signals")
        html = self.g.render_active_modal()
        menu = html.split('class="eb-menu"', 1)[1].split("eb-menu-foot", 1)[0]
        n_b1 = len([c for c in store.get_all_cosmonauts() if c.band == "B1"])
        self.assertEqual(menu.count('<button type="button" class="eb-opt'), n_b1)             # B2+ cosmonauts are not offered

    def test_adding_a_cosmonaut_to_a_chosen_reviewer_updates_everything(self):
        self._map_two_reviewers()
        before = self._owners()
        extra = next(c.id for c in store.get_all_cosmonauts() if c.band == "B1" and c.id not in before)
        wanted = list(before) + [extra]
        ra = dict(before)
        ra[extra] = "m_b2_2"                                            # hand the new cosmonaut to the SECOND reviewer
        self._save_edit(assigned_cosmonaut_ids=wanted, reviewer_assignments=ra)
        self.assertEqual(self.g.flash_type, "success")
        self.assertEqual(self._owners()[extra], "m_b2_2")                                       # band mapping (database)
        tl = store.get_timeline("badge_b1_signals", extra)
        self.assertEqual(tl.reviewer_id, "m_b2_2")                                              # timeline -> reviewer portal
        self.assertTrue(json.loads(tl.review_window_json))                                      # with the review window
        self.assertIn(extra, [t.cosmonaut_id for t in store.get_timelines_for_reviewer("m_b2_2")])
        req = next(r for r in store.get_mapping_requests() if r["reviewer_id"] == "m_b2_2" and r.get("badge_id") == "badge_b1_signals")
        self.assertIn(extra, req["cosmonaut_ids"])                                              # the reviewer's request
        self.assertTrue(any(n.recipient_id == "m_b2_2" and "added to your review group" in n.title for n in store.notifications))
        # it is really in the database, not only in memory
        row = store.db.conn.execute("SELECT data_json FROM band_mappings WHERE data_json LIKE ?", (f'%{extra}%',)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(store.db.conn.execute("SELECT reviewer_id FROM badge_timelines WHERE badge_id = ? AND cosmonaut_id = ?",
                                               ("badge_b1_signals", extra)).fetchone()[0], "m_b2_2")

    def test_moving_a_cosmonaut_between_reviewers(self):
        self._map_two_reviewers()
        before = self._owners()
        cid, old = next(iter(before.items()))
        new = "m_b2_2" if old == "m_b2_1" else "m_b2_1"
        ra = dict(before)
        ra[cid] = new
        self._save_edit(assigned_cosmonaut_ids=list(before), reviewer_assignments=ra)
        self.assertEqual(self._owners()[cid], new)
        self.assertEqual(store.get_timeline("badge_b1_signals", cid).reviewer_id, new)

    def test_server_rejects_unmapped_reviewers_and_wrong_band_cosmonauts(self):
        self._map_two_reviewers()
        before = self._owners()
        ids = list(before)
        self._save_edit(assigned_cosmonaut_ids=ids, reviewer_assignments={**before, ids[0]: "m_b2_3"})     # not mapped to this badge
        self.assertEqual(self.g.flash_type, "error")
        self.assertEqual(self._owners(), before)
        b2 = next(c.id for c in store.get_all_cosmonauts() if c.band == "B2" and c.id not in before)
        self._save_edit(assigned_cosmonaut_ids=ids + [b2])                                               # Band B2 on a B1 badge
        self.assertEqual(self.g.flash_type, "error")
        self.assertNotIn(b2, store.get_badge("badge_b1_signals").assigned_cosmonaut_ids)

    def test_payload_without_reviewer_assignments_keeps_existing_reviewers(self):
        self._map_two_reviewers()
        before = self._owners()
        self._save_edit(assigned_cosmonaut_ids=list(before))
        self.assertEqual(self._owners(), before)

    def test_edit_modal_has_read_only_details_and_glass_calendar_dates(self):
        self.g.handle_event("open_edit_badge_modal", "badge_b1_signals")
        html = self.g.render_active_modal()
        self.assertNotIn("Badge Details", html)                              # no details card: only cosmonauts + timeline
        self.assertNotIn("eb-hero-title", html)
        self.assertNotIn("bi-prompt-real", html)
        self.assertIn('class="eb-grid is-edit"', html)
        self.assertEqual(html.count('<section class="eb-card'), 2)                     # exactly two cards side by side
        self.assertNotIn('<textarea id="badge-desc"', html)                  # content is not editable ...
        self.assertNotIn('<input type="text" id="badge-title"', html)
        self.assertIn('<input type="hidden" id="badge-title"', html)         # ... (kept hidden so the payload shape is unchanged)
        self.assertNotIn('type="date"', html)                                # no native calendar anywhere
        self.assertEqual(html.count('class="gd-btn"'), 8)                    # eight glass-calendar triggers
        for fid in ("tl-alloc-date", "tl-learn-start", "tl-learn-end", "tl-proj-start", "tl-proj-end", "tl-sub-deadline", "tl-review-date", "tl-award-date"):
            self.assertIn(f'<input type="hidden" id="{fid}" value="20', html)

    def test_glass_date_picker_is_wired_in_the_bridge_and_css(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        js = open(os.path.join(root, "js", "bridge.js"), encoding="utf-8").read()
        css = open(os.path.join(root, "css", "liquid_glass.css"), encoding="utf-8").read()
        self.assertIn("openDatePicker", js)
        self.assertIn("data-gd-min", js)
        for cls in (".gd-pop", ".gd-btn", ".gd-today"):
            self.assertIn(cls, css)
        self.assertIn("backdrop-filter", css[css.index(".gd-pop {"):][:900])

    def _save_edit(self, **over):
        payload = {
            "badge_id": "badge_b1_signals", "code": "B1-SIG-01", "title": "Signals Foundations",
            "description": "d", "project_requirements": "r", "assigned_cosmonaut_ids": ["m_b1_1", "m_b1_2"],
            "assignment_date": "2026-11-27", "learning_start_date": "2026-11-18", "learning_end_date": "2026-11-20",
            "project_start_date": "2026-11-21", "project_end_date": "2026-11-25", "submission_deadline": "2026-11-26",
            "review_date": "2026-11-28", "expected_award_date": "2026-11-30"}
        payload.update(over)
        self.g.handle_event("save_badge_form", json.dumps(payload))

    def test_edit_save_changes_only_cosmonauts_and_timeline(self):
        before = store.get_badge("badge_b1_signals")
        keep = {k: getattr(before, k) for k in ("code", "title", "description", "project_requirements", "target_band",
                                                "power", "capability", "skill", "workflow_status", "is_published",
                                                "learning_outcomes", "passing_percentage")}
        # a tampered payload (different title / description / brief) must not change the badge
        self._save_edit(title="HACKED", description="HACKED", project_requirements="HACKED", code="X-1")
        after = store.get_badge("badge_b1_signals")
        for k, v in keep.items():
            self.assertEqual(getattr(after, k), v, k)
        self.assertEqual(after.assigned_cosmonaut_ids, ["m_b1_1", "m_b1_2"])
        self.assertEqual(after.default_timeline["submission_deadline"], "2026-11-26")
        self.assertEqual(store.get_timeline("badge_b1_signals", "m_b1_2").submission_deadline, "2026-11-26")

    def test_edit_save_needs_a_cosmonaut_and_sane_dates(self):
        self._save_edit(assigned_cosmonaut_ids=[])
        self.assertEqual(self.g.flash_type, "warning")
        self._save_edit(learning_start_date="2026-11-20", learning_end_date="2026-11-18")
        self.assertEqual(self.g.flash_type, "error")
        self._save_edit(submission_deadline="not-a-date")
        self.assertEqual(self.g.flash_type, "error")

    def test_changes_made_in_edit_show_up_in_the_timeline_view(self):
        self._map_signals()
        # add m_b1_5 (not mapped to any reviewer), drop m_b1_2 (mapped), move the deadline
        self._save_edit(assigned_cosmonaut_ids=["m_b1_1", "m_b1_5"], submission_deadline="2026-12-24")
        self.assertEqual(self.g.flash_type, "success")
        self.g.handle_event("open_badge_timeline_mapping_modal", "badge_b1_signals")
        html = self.g.render_active_modal()
        self.assertIn("24 Dec 2026", html)                                   # new deadline
        self.assertIn("Not mapped to a reviewer yet", html)                  # the added cosmonaut is listed ...
        self.assertIn(store.get_user_by_id("m_b1_5").name, html)
        self.assertNotIn(store.get_user_by_id("m_b1_2").name, html)          # ... the removed one is gone everywhere
        self.assertIsNone(store.get_timeline("badge_b1_signals", "m_b1_2"))
        mapped = [m for m in store.get_band_mappings() if m.get("badge_id") == "badge_b1_signals"]
        self.assertTrue(all("m_b1_2" not in (m.get("cosmonauts") or []) for m in mapped))

    def test_cannot_remove_a_cosmonaut_who_already_submitted(self):
        sub = ProjectSubmission("sub_edit_t1", "badge_b1_signals", "m_b1_2", 1, "pdf", "data:abc", "f.pdf", "2026-11-20T00:00:00Z")
        store.save_submission(sub)
        self._save_edit(assigned_cosmonaut_ids=["m_b1_1"])
        self.assertEqual(self.g.flash_type, "error")
        self.assertIn("m_b1_2", store.get_badge("badge_b1_signals").assigned_cosmonaut_ids)

    def test_edit_modal_save_round_trip(self):
        self._save_edit(assigned_cosmonaut_ids=["m_b1_1"])
        self.assertEqual(store.get_badge("badge_b1_signals").assigned_cosmonaut_ids, ["m_b1_1"])

    def test_bridge_defines_the_assignee_helpers(self):
        js = open(os.path.join(os.path.dirname(__file__), "..", "js", "bridge.js"), encoding="utf-8").read()
        for fn in ("refreshAssigneeCount", "addAssignee", "removeAssignee", "clearAssignees", "addAllShownAssignees", "filterAssignMenu", "toggleAssignMenu"):
            self.assertIn(fn, js)


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
