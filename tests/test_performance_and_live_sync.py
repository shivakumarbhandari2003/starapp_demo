"""
UI performance guards: no repaint / flicker for an unchanged page, cheap live-sync polls, restrained glass + animation cost.

* Countdowns are rendered with the seconds left, so an unchanged page differs every second. The browser and the server must compare
  HTML with those values blanked out (`stable_html_signature` / `bridge.js::_stableHtml`) - otherwise every live-sync poll repaints the whole page.
* A live-sync poll whose page did not change answers "unchanged" (a few bytes) instead of the whole page.
* Background polls never supersede a user action; polls are single-flight and back off when idle.
* Heavy visual effects stay bounded: no endless animations on repeated cards, backdrop blur only on a few chrome surfaces.
"""
import json
import os
import re
import time
import unittest

from starapp.app import StarAppController
from starapp.storage import store
from starapp.views_common import stable_html_signature

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


def _login(uid):
    c = StarAppController()
    c.initialize()
    c.handle_event("select_demo_account", uid)
    return c


class TestStableSignature(unittest.TestCase):
    A = '<span class="rq-timer" data-remaining="86399" data-sync="x"><span class="rq-timer-text">23:59:59</span></span><p>Hello</p>'
    B = '<span class="rq-timer" data-remaining="86390" data-sync="x"><span class="rq-timer-text">23:59:50</span></span><p>Hello</p>'

    def test_only_the_ticking_values_are_ignored(self):
        self.assertNotEqual(self.A, self.B)
        self.assertEqual(stable_html_signature(self.A), stable_html_signature(self.B))
        self.assertNotEqual(stable_html_signature(self.A), stable_html_signature(self.B.replace("Hello", "Bye")))
        self.assertNotEqual(stable_html_signature(self.A), stable_html_signature(self.B.replace('data-sync="x"', 'data-sync="y"')))
        self.assertEqual(stable_html_signature(""), "")
        self.assertEqual(stable_html_signature(None), "")

    def test_the_browser_uses_the_same_rule(self):
        js = _read("js", "bridge.js")
        self.assertIn("_stableHtml(html)", js)
        self.assertIn(r'/data-remaining="\d+"|(<span class="rq-timer-text">)[\d:]+/g', js)
        self.assertIn("renderState.mainSig !== nextMainSig", js)                  # the page repaints only when the stable signature changes
        self.assertIn("renderState.modalSig === nextModalSig", js)

    def test_a_real_page_with_a_countdown_is_stable_between_renders(self):
        g = _login("guardian_1")
        g.handle_event("select_create_badge_band", "B1")
        g.handle_event("nav_guardian", "g_mapping")
        g.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2"]
        g.mapping_selected_reviewers = ["m_b2_1"]
        g.mapping_selected_badge = "Data Systems Architecture"
        g.handle_event("send_mapping_requests", "{}")
        rev = _login("m_b2_1")
        rev.current_view = "c_requests"
        rev.render()
        a = rev.last_rendered_regions["mainContentHtml"]
        self.assertIn('data-remaining="', a)                                      # a live countdown is on the page
        time.sleep(1.2)
        rev.render()
        b = rev.last_rendered_regions["mainContentHtml"]
        self.assertNotEqual(a, b)                                                 # the raw HTML moved on (the clock ticked) ...
        self.assertEqual(stable_html_signature(a), stable_html_signature(b))      # ... but nothing else did: no repaint


class TestLiveSyncIsCheap(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app, _session_controllers
        self._cm = TestClient(app)
        self.client = self._cm.__enter__()
        self.sessions = _session_controllers
        self.sid = "perf_test_session_01"

    def tearDown(self):
        self.sessions.pop(self.sid, None)
        self._cm.__exit__(None, None, None)

    def post(self, action, payload=""):
        r = self.client.post("/api/v1/dispatch", json={"action": action, "payload": payload, "session_id": self.sid}, headers={"X-Session-Id": self.sid})
        self.assertEqual(r.status_code, 200)
        return r.json()

    def test_an_unchanged_poll_answers_unchanged_and_a_changed_page_is_sent(self):
        self.post("select_demo_account", "m_b2_1")
        self.post("nav_cosmonaut", "c_badge_reviews")
        first = self.post("sync_badge_reviews", "{}")
        self.assertTrue(first.get("unchanged") or first.get("regions"))         # (the page was already sent with the nav action)
        again = self.post("sync_badge_reviews", "{}")
        self.assertTrue(again.get("unchanged"))
        self.assertIsNone(again.get("regions"))
        small = len(json.dumps(again))
        self.assertTrue(again.get("session_state"))                               # session bookkeeping still comes with it
        self.sessions[self.sid]._sent_regions_sig = "stale"                       # the client's page is out of date -> the full page is sent
        changed = self.post("sync_badge_reviews", "{}")
        self.assertFalse(changed.get("unchanged"))
        self.assertTrue(changed["regions"]["mainContentHtml"])
        self.assertLess(small * 4, len(json.dumps(changed)))                      # the poll answer is a fraction of the page
        self.assertTrue(self.post("sync_badge_reviews", "{}").get("unchanged"))

    def test_only_sync_polls_may_answer_unchanged(self):
        self.post("select_demo_account", "m_b2_1")
        self.post("nav_cosmonaut", "c_badge_reviews")
        again = self.post("nav_cosmonaut", "c_badge_reviews")                     # a user action always gets its page
        self.assertFalse(again.get("unchanged"))
        self.assertTrue(again["regions"]["mainContentHtml"])


class TestClientBehaviour(unittest.TestCase):
    def setUp(self):
        self.js = _read("js", "bridge.js")

    def test_polls_do_not_supersede_user_actions_and_stale_answers_are_dropped(self):
        self.assertIn("const isSyncPoll = /^sync_/.test(String(action));", self.js)
        self.assertIn("if (!isSyncPoll) {\n        localActionSeq += 1;", self.js.replace("\r\n", "\n"))
        self.assertIn("const isTypeAheadAction = isSyncPoll ||", self.js)
        self.assertIn("data.unchanged", self.js)

    def test_live_sync_is_single_flight_and_backs_off_when_idle(self):
        body = self.js.split("function startLiveSync()")[1].split("startRequestCountdowns")[0]
        for part in ("let busy = false;", "pending.finally(", "IDLE_AFTER_MS", "document.hidden", "pointerdown", "% 4"):
            self.assertIn(part, body, part)
        self.assertIn("return fetch(\"/api/v1/dispatch\"", self.js)                # the promise is returned so a poll can be awaited

    def test_the_countdown_ticker_sleeps_in_a_hidden_tab(self):
        body = self.js.split("function startRequestCountdowns()")[1]
        self.assertIn("if (document.hidden) return;", body.split("function tick()")[1][:200])


class TestVisualCost(unittest.TestCase):
    def setUp(self):
        self.css = "\n".join(_read("css", f) for f in ("components.css", "liquid_glass.css", "layout.css"))

    def test_no_endless_animation_on_repeated_cards(self):
        for sel in (".gold-card::after", ".gold-medal::after", ".rq-timer.is-urgent"):
            block = self.css.split(sel + " {")[1].split("}")[0]
            self.assertNotIn("infinite", block, sel)

    def test_backdrop_blur_stays_on_a_handful_of_chrome_surfaces(self):
        blurred = set()
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", self.css):
            sel = m.group(1).strip().split("\n")[-1].strip()
            bf = re.search(r"(?<!-webkit-)backdrop-filter:\s*([^;]+);", m.group(2))
            if bf and bf.group(1).strip().startswith("blur"):
                blurred.add(sel)
        # the glass CARDS themselves never blur (that is what made large pages heavy): only chrome, popovers and the modal veil
        for card in (".liquid-glass-card", ".rv-badge-card", ".lg-saved-badge-card", ".cb-section-card", ".pjp-page", ".ms-sheet", ".earn-card", ".mbe-card"):
            self.assertNotIn(card, blurred, card)
        self.assertLessEqual(len(blurred), 14, sorted(blurred))


class TestScrollCost(unittest.TestCase):
    """Large translucent gradients were the dominant scroll cost (measured: Guardian dashboard 26 ms -> 17 ms per frame, p95 51 -> 17 ms, with
    them flattened). The glass look is kept with a flat tint; real colour ramps (gold card, buttons, avatars) are small and stay."""

    def test_big_glass_surfaces_use_a_flat_tint_not_a_gradient(self):
        css = chr(10).join(_read("css", f) for f in ("components.css", "liquid_glass.css"))
        for sel in (".liquid-glass-card", ".cb-section-card", ".rv-badge-card", ".lg-allot-card", ".lg-saved-badge-card", ".earn-card", ".pjp-bar", ".pjp-sub-card", ".ms-toolbar"):
            pattern = r"(?:^|[\n,])\s*" + re.escape(sel) + r"\s*(?:,[^{]*)?\{([^{}]*)\}"
            for m in re.finditer(pattern, css):
                bg = re.search(r"(?<![\w-])background(?:-image)?\s*:\s*([^;]+);", m.group(1))
                if bg:
                    self.assertNotIn("gradient", bg.group(1), f"{sel}: {bg.group(1)[:80]}")

    def test_no_scroll_listeners_and_listeners_are_passive(self):
        js = _read("js", "bridge.js")
        self.assertNotIn('addEventListener("scroll"', js)
        self.assertIn('{ passive: true }', js)


class TestServerStaysFast(unittest.TestCase):
    """Loose ceilings (CI machines vary a lot): they only catch an accidental order-of-magnitude regression."""

    def test_live_sync_round_trip_and_key_pages_render_quickly(self):
        store.reset_to_seed()
        rev = _login("m_b2_1")
        rev.current_view = "c_badge_reviews"
        rev.render()
        t = time.perf_counter()
        for _ in range(10):
            rev.handle_event("sync_badge_reviews")
        per_poll_ms = (time.perf_counter() - t) * 100
        self.assertLess(per_poll_ms, 250, per_poll_ms)
        for uid, views in (("guardian_1", ("g_dashboard", "g_mapping", "g_reviews")), ("m_b1_1", ("c_submission", "c_results", "c_dashboard"))):
            c = _login(uid)
            for v in views:
                c.current_view = v
                t = time.perf_counter()
                c.render()
                self.assertLess((time.perf_counter() - t) * 1000, 1500, (uid, v))


if __name__ == "__main__":
    unittest.main()
