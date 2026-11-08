import unittest
import json
from starapp.models import User, Badge, BadgeTimeline, DeadlineExtension
from starapp.storage import store
from starapp.app import StarAppController
from starapp.views_cosmonaut import render_cosmonaut_extensions, render_cosmonaut_results
from starapp.views_guardian import render_guardian_extensions

class TestExtensionFlow(unittest.TestCase):
    def setUp(self):
        store.reset_to_seed()
        self.cosmo = store.users.get("cosmo_1")
        self.guardian = store.users.get("guardian_1")
        self.badge = store.get_badge("badge_ing_104")
        self.tl = store.get_timeline("badge_ing_104", "cosmo_1")

    def test_extension_full_lifecycle_and_rendering(self):
        app = StarAppController()
        app.current_user = self.cosmo

        # 1. Cosmonaut submits deadline extension request
        req_payload = {
            "badge_id": "badge_ing_104",
            "proposed_deadline": "2026-12-18",
            "reason": "Encountered distributed Kafka consumer rebalance lag needing custom backoff logic."
        }
        app.handle_event("submit_deadline_extension_request", json.dumps(req_payload))

        exts = [e for e in store.get_extensions_for_cosmonaut("cosmo_1") if e.proposed_deadline == "2026-12-18"]
        self.assertEqual(len(exts), 1)
        ext = exts[0]
        self.assertEqual(ext.status, "pending")
        self.assertEqual(ext.proposed_deadline, "2026-12-18")

        # 2. Render cosmonaut extensions - verify vertical layout (stacked table below)
        html_cosmo = render_cosmonaut_extensions(
            assigned_badges=[self.badge],
            extensions=exts,
            badges_map={"badge_ing_104": self.badge}
        )
        self.assertIn("Submitted Requests & Actions", html_cosmo)
        self.assertIn("ING-104", html_cosmo)
        self.assertIn("Pending Review", html_cosmo)
        self.assertIn("2026-12-18", html_cosmo)

        # 3. Guardian reviews extension requests
        app.current_user = self.guardian
        all_exts = store.get_all_extensions()
        html_guard = render_guardian_extensions(
            extensions=all_exts,
            cosmonauts_map={"cosmo_1": self.cosmo},
            badges_map={"badge_ing_104": self.badge}
        )
        self.assertIn("Requested by Astraea Nova", html_guard)
        self.assertIn("Approve Extension", html_guard)
        self.assertIn("Reject", html_guard)

        # 4. Guardian opens modal with JSON string payload
        app.handle_event("open_extension_decision_modal", json.dumps({
            "extension_id": ext.id,
            "decision": "approved"
        }))
        self.assertEqual(app.active_modal, "decide_extension")
        modal_html = app.render_active_modal()
        self.assertIn("Confirm Approved", modal_html)

        # 5. Guardian confirms approval with mentor note
        app.handle_event("submit_extension_decision", json.dumps({
            "extension_id": ext.id,
            "decision": "approved",
            "response_note": "Approved. Excellent architectural rationale provided."
        }))

        updated_ext = store.get_extension(ext.id)
        self.assertEqual(updated_ext.status, "approved")
        self.assertEqual(updated_ext.guardian_response, "Approved. Excellent architectural rationale provided.")

        # Verify timeline updated
        tl_updated = store.get_timeline("badge_ing_104", "cosmo_1")
        self.assertEqual(tl_updated.submission_deadline, "2026-12-18")

        # 6. Verify reflection in Cosmonaut extensions view (action button 'Submit Deliverable')
        html_cosmo_approved = render_cosmonaut_extensions(
            assigned_badges=[self.badge],
            extensions=[updated_ext],
            badges_map={"badge_ing_104": self.badge}
        )
        self.assertIn("Approved", html_cosmo_approved)
        self.assertIn("Submit Deliverable", html_cosmo_approved)
        self.assertIn("nav_to_submit_badge", html_cosmo_approved)

        # 7. Verify reflection in Cosmonaut Results view
        html_results = render_cosmonaut_results(
            assessments=[],
            badges_map={"badge_ing_104": self.badge},
            selected_badge_id="badge_ing_104",
            available_badges=[self.badge],
            extensions=[updated_ext]
        )
        self.assertIn("Deadline Extended", html_results)
        self.assertIn("2026-12-18", html_results)
        self.assertIn("Approved. Excellent architectural rationale provided.", html_results)

if __name__ == "__main__":
    unittest.main()
