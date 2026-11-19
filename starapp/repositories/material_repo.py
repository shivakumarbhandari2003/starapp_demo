"""
STARAPP LEARNING MATERIAL REPOSITORY
Encapsulates all SQLite queries for Documents, Resource Links, and Media.
"""

from typing import List, Optional
from starapp.repositories.base import BaseRepository
from starapp.models import LearningMaterial

class MaterialRepository(BaseRepository):
    def get_all(self) -> List[LearningMaterial]:
        rows = self.fetchall("SELECT * FROM learning_materials ORDER BY upload_date DESC")
        return [LearningMaterial.from_dict(r) for r in rows]

    def get_by_badge(self, badge_id: str) -> List[LearningMaterial]:
        rows = self.fetchall("SELECT * FROM learning_materials WHERE badge_id = ? ORDER BY upload_date DESC", (badge_id,))
        return [LearningMaterial.from_dict(r) for r in rows]

    def get_by_id(self, material_id: str) -> Optional[LearningMaterial]:
        row = self.fetchone("SELECT * FROM learning_materials WHERE id = ?", (material_id,))
        if not row:
            return None
        return LearningMaterial.from_dict(row)

    def save(self, mat: LearningMaterial):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO learning_materials (
                    id, badge_id, topic, title, description, material_type, url_or_data, upload_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mat.id,
                    mat.badge_id,
                    mat.topic,
                    mat.title,
                    mat.description,
                    mat.material_type,
                    mat.url_or_data,
                    mat.upload_date
                )
            )

    def delete(self, material_id: str):
        if not self.conn:
            return
        with self.conn:
            self.execute("DELETE FROM learning_materials WHERE id = ?", (material_id,))
