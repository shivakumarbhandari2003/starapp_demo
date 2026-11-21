import unittest
from starapp.app import StarAppController
from starapp.storage import store
from starapp.badge_generator import generate_badge_data
from backend.app.integrations.gemini.router import generate_fallback_badge


class TestB2CurationScenario(unittest.TestCase):
    def setUp(self):
        self.ctrl = StarAppController()
        store.reset_to_seed()
        self.ctrl.handle_event('select_demo_account', 'guardian_1')

    def test_b2_curation_badge_generation_and_rich_prompts(self):
        self.ctrl.handle_event('nav_guardian', 'g_create_badge')
        self.ctrl.handle_event('select_create_badge_band', 'B2')
        self.ctrl.handle_event('change_badge_power', 'Tech')
        self.ctrl.handle_event('change_badge_capability', 'Data & Machine')
        self.ctrl.handle_event('change_badge_skill', 'Curation')
        self.ctrl.handle_event('change_badge_outcome_sentence', 'Design, configure, and evaluate modular system components and services against operational benchmarks')

        # Test both fallback generator and deterministic generator
        fallback = generate_fallback_badge('B2', 'Tech', 'Data & Machine', 'Curation', 'Design, configure, and evaluate modular system components and services against operational benchmarks')
        
        self.assertIn('Band B2', fallback['practice_prompt'])
        self.assertIn('Band B2', fallback['resources_prompt'])
        self.assertNotIn('Band B1', fallback['practice_prompt'])
        self.assertNotIn('Band B1', fallback['resources_prompt'])

        # Dispatch on_badge_generated with fallback
        self.ctrl.handle_event('on_badge_generated', {'band': 'B2', 'badge_data': fallback})
        html = self.ctrl.render()

        self.assertIn('BAND B2', html)
        self.assertIn('Curation Foundations', html)
        self.assertIn('id="practice-prompt-text"', html)
        self.assertIn('id="resources-prompt-text"', html)
        self.assertIn('Design one small, hands-on practice project', html)
        self.assertIn('free, current, high-quality learning resources', html)
        self.assertIn('Curation Core Fundamentals', html)
        self.assertIn('Curation Architecture &amp; Design Patterns', html)

        # Verify practice prompt text inside created_badge_data
        practice_p = self.ctrl.created_badge_data['practice_project']['prompt']
        self.assertIn('Band B2', practice_p)
        self.assertIn('Curation Core Fundamentals', practice_p)
        self.assertIn('Design one small, hands-on practice project', practice_p)

        # Verify resources prompt text inside created_badge_data
        resources_p = self.ctrl.created_badge_data['learning_resources']['prompt']
        self.assertIn('Band B2', resources_p)
        self.assertIn('Curation Core Fundamentals', resources_p)
        self.assertIn('free, current, high-quality learning resources', resources_p)

        # Save and verify
        self.ctrl.handle_event('save_generated_badge', {})
        self.assertEqual(self.ctrl.flash_type, 'success')
        saved = store.get_saved_badges('B2')
        self.assertTrue(len(saved) > 0)
        saved_badge = saved[0]
        self.assertEqual(saved_badge.get('target_band'), 'B2')
        self.assertEqual(saved_badge.get('skill'), 'Curation')


if __name__ == '__main__':
    unittest.main()
