import unittest
import json
from starapp.app import StarAppController, store
from starapp.models import LearningMaterial

class TestLearningMaterialsFlow(unittest.TestCase):
    def setUp(self):
        self.app = StarAppController()
        store.reset_to_seed()

    def test_materials_lifecycle_guardian_and_cosmonaut(self):
        # 1. Initially materials are clean/empty
        self.assertEqual(len(store.get_materials()), 0)

        # 2. Guardian visits g_materials
        self.app.current_user = store.users.get("guardian_1")
        self.app.current_view = "g_materials"
        html_g = self.app.render()

        self.assertIn("Learning & Development Hub", html_g)
        self.assertIn("No Learning Materials Published Yet", html_g)
        self.assertIn("+ Upload Learning Materials", html_g)

        # 3. Cosmonaut visits c_materials
        self.app.current_user = store.users.get("cosmo_1")
        self.app.current_view = "c_materials"
        html_c = self.app.render()

        self.assertIn("Course Documents & Video Lectures", html_c)
        self.assertIn("No Learning Materials Available", html_c)
        self.assertNotIn("+ Upload Learning Materials", html_c)

        # 4. Guardian opens Add Material Modal
        self.app.current_user = store.users.get("guardian_1")
        self.app.handle_event("open_add_material_modal")
        self.assertEqual(self.app.active_modal, "add_material")
        html_modal = self.app.render()
        self.assertIn("Upload Learning Materials", html_modal)
        self.assertIn("Upload PDF Documents (Multiple Files Supported)", html_modal)
        self.assertIn("YouTube Video Lectures (Multiple Links Supported)", html_modal)
        self.assertIn("+ Add Another YouTube Link", html_modal)

        # 5. Guardian publishes 2 PDFs and 2 YouTube videos in bulk
        bulk_payload = {
            "badge_id": "badge_ing_104",
            "topic": "Module 1: Ingestion Pipelines",
            "description": "Foundational curriculum and reference lectures.",
            "pdfs": [
                {"name": "Kafka_Architecture_Spec.pdf", "dataUrl": "data:application/pdf;base64,JVBERi0xLjQK..."},
                {"name": "Schema_Registry_Manual.pdf", "dataUrl": "data:application/pdf;base64,JVBERi0xLjQK..."}
            ],
            "youtube_links": [
                {"title": "Kafka Consumer Deep Dive", "url": "https://www.youtube.com/watch?v=9ZGFF_bYenc"},
                {"title": "Idempotent Producer Architecture", "url": "https://youtu.be/F0sqfPkCcyM"}
            ]
        }
        self.app.handle_event("save_bulk_materials", bulk_payload)
        self.assertIsNone(self.app.active_modal)

        # Verify store has 4 materials
        all_mats = store.get_materials("badge_ing_104")
        self.assertEqual(len(all_mats), 4)

        # 6. Verify Guardian view
        self.app.current_view = "g_materials"
        html_g_updated = self.app.render()
        self.assertIn("ING-104", html_g_updated)
        self.assertIn("Kafka Architecture Spec", html_g_updated)
        self.assertIn("Schema Registry Manual", html_g_updated)
        self.assertIn("Kafka Consumer Deep Dive", html_g_updated)
        self.assertIn("Idempotent Producer Architecture", html_g_updated)
        # Guardian should see Edit and Delete buttons
        self.assertIn("open_edit_material_modal", html_g_updated)
        self.assertIn("delete_material", html_g_updated)
        self.assertIn("Theater View", html_g_updated)

        # 7. Verify Cosmonaut view
        self.app.current_user = store.users.get("cosmo_1")
        self.app.current_view = "c_materials"
        html_c_updated = self.app.render()
        self.assertIn("ING-104", html_c_updated)
        self.assertIn("Kafka Architecture Spec", html_c_updated)
        self.assertIn("Idempotent Producer Architecture", html_c_updated)
        self.assertIn("Theater View", html_c_updated)
        # Cosmonaut must NOT see Edit, Delete, or Add buttons!
        self.assertNotIn("open_edit_material_modal", html_c_updated)
        self.assertNotIn("delete_material", html_c_updated)
        self.assertNotIn("+ Upload Learning Materials", html_c_updated)

        # 8. Guardian edits one material
        self.app.current_user = store.users.get("guardian_1")
        self.app.current_view = "g_materials"
        yt_mat = next(m for m in all_mats if m.material_type == "youtube")
        self.app.handle_event("open_edit_material_modal", {"material_id": yt_mat.id})
        self.assertEqual(self.app.active_modal, "edit_material")

        edit_payload = {
            "material_id": yt_mat.id,
            "badge_id": yt_mat.badge_id,
            "title": "Kafka Consumer Masterclass (Updated)",
            "topic": "Advanced Ingestion",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=9ZGFF_bYenc",
            "description": "Updated masterclass description."
        }
        self.app.handle_event("update_material", edit_payload)
        self.assertIsNone(self.app.active_modal)

        # Verify update in store
        updated_mat = store.get_material(yt_mat.id)
        self.assertEqual(updated_mat.title, "Kafka Consumer Masterclass (Updated)")

        # 9. Guardian deletes one PDF material
        pdf_mat = next(m for m in all_mats if m.material_type == "pdf")
        self.app.handle_event("delete_material", {"material_id": pdf_mat.id})
        self.assertEqual(len(store.get_materials("badge_ing_104")), 3)

        # 10. Filter verification
        self.app.handle_event("filter_materials_type", "pdf")
        self.assertEqual(self.app.materials_type_filter, "pdf")
        html_pdf_only = self.app.render()
        self.assertIn("PDF Documents", html_pdf_only)

if __name__ == "__main__":
    unittest.main()
