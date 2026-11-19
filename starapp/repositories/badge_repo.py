"""
STARAPP BADGE REPOSITORY
Encapsulates all SQLite queries for Badges, Taxonomy (Powers, Capabilities, Skills),
and Badge Review Workflow lifecycles.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from starapp.repositories.base import BaseRepository
from starapp.models import Badge, current_iso_timestamp

class BadgeRepository(BaseRepository):
    def get_all(self) -> List[Badge]:
        rows = self.fetchall("SELECT * FROM badges ORDER BY created_at ASC")
        badges = []
        for r in rows:
            badges.append(Badge(
                id=r["id"],
                code=r["code"],
                title=r["title"],
                category=r["category"],
                description=r["description"],
                learning_outcomes=json.loads(r["learning_outcomes_json"]) if r.get("learning_outcomes_json") else [],
                learning_topics=json.loads(r["learning_topics_json"]) if r.get("learning_topics_json") else [],
                project_requirements=r.get("project_requirements", ""),
                is_published=bool(r.get("is_published", 1)),
                is_allocated=bool(r.get("is_allocated", 1)),
                target_band=r.get("target_band"),
                power=r.get("power"),
                capability=r.get("capability"),
                skill=r.get("skill"),
                prompt_json=r.get("prompt_json"),
                workflow_status=r.get("workflow_status", "approved")
            ))
        return badges

    def get_by_id(self, badge_id: str) -> Optional[Badge]:
        if not badge_id:
            return None
        r = self.fetchone("SELECT * FROM badges WHERE id = ?", (badge_id,))
        if not r:
            return None
        return Badge(
            id=r["id"],
            code=r["code"],
            title=r["title"],
            category=r["category"],
            description=r["description"],
            learning_outcomes=json.loads(r["learning_outcomes_json"]) if r.get("learning_outcomes_json") else [],
            learning_topics=json.loads(r["learning_topics_json"]) if r.get("learning_topics_json") else [],
            project_requirements=r.get("project_requirements", ""),
            is_published=bool(r.get("is_published", 1)),
            is_allocated=bool(r.get("is_allocated", 1)),
            target_band=r.get("target_band"),
            power=r.get("power"),
            capability=r.get("capability"),
            skill=r.get("skill"),
            prompt_json=r.get("prompt_json"),
            workflow_status=r.get("workflow_status", "approved")
        )

    def get_by_code(self, code: str) -> Optional[Badge]:
        if not code:
            return None
        r = self.fetchone("SELECT id FROM badges WHERE lower(code) = ?", (code.lower(),))
        if r:
            return self.get_by_id(r["id"])
        return None

    def save(self, badge: Badge):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO badges (
                    id, code, title, category, description,
                    learning_outcomes_json, learning_topics_json, project_requirements,
                    is_published, is_allocated, target_band, power, capability, skill,
                    prompt_json, workflow_status, creator_id, assigned_reviewer_id,
                    assigned_cosmonaut_ids_json, default_timeline_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    badge.id,
                    badge.code,
                    badge.title,
                    badge.category,
                    badge.description,
                    json.dumps(badge.learning_outcomes),
                    json.dumps(badge.learning_topics),
                    badge.project_requirements,
                    1 if badge.is_published else 0,
                    1 if badge.is_allocated else 0,
                    getattr(badge, "target_band", None),
                    getattr(badge, "power", None),
                    getattr(badge, "capability", None),
                    getattr(badge, "skill", None),
                    getattr(badge, "prompt_json", None),
                    getattr(badge, "workflow_status", "approved"),
                    "guardian_1",
                    None,
                    "[]",
                    "{}",
                    current_iso_timestamp(),
                    current_iso_timestamp()
                )
            )
            if getattr(badge, "power", None):
                self.conn.execute("INSERT OR REPLACE INTO badge_powers (badge_id, power_name) VALUES (?, ?)", (badge.id, badge.power))
            if getattr(badge, "capability", None):
                self.conn.execute("INSERT OR REPLACE INTO badge_capabilities (badge_id, capability_name, is_custom) VALUES (?, ?, 0)", (badge.id, badge.capability))
            if getattr(badge, "skill", None):
                self.conn.execute("INSERT OR REPLACE INTO badge_skills (badge_id, skill_name, is_custom) VALUES (?, ?, 0)", (badge.id, badge.skill))

    # Workflow methods delegated to authoritative DatabaseManager implementation
    def create_badge_for_review(self, badge_data: Dict[str, Any], creator_id: str, creator_name: str = "") -> Tuple[bool, str, Optional[str]]:
        return self.db.create_badge_for_review(badge_data, creator_id, creator_name)

    def update_badge_by_reviewer(self, badge_id: str, reviewer_id: str, reviewer_name: str, updates: Dict[str, Any], review_notes: str = "") -> Tuple[bool, str]:
        return self.db.update_badge_by_reviewer(badge_id, reviewer_id, reviewer_name, updates, review_notes)

    def approve_badge(self, badge_id: str, reviewer_id: str, reviewer_name: str, decision_notes: str = "") -> Tuple[bool, str]:
        return self.db.approve_badge(badge_id, reviewer_id, reviewer_name, decision_notes)

    def get_submitted_badges_for_approval(self, status_filter: str = "all") -> List[Dict[str, Any]]:
        return self.db.get_submitted_badges_for_approval(status_filter)

    def get_badge_review_detail(self, badge_id: str) -> Optional[Dict[str, Any]]:
        return self.db.get_badge_review_detail(badge_id)

    def get_custom_capabilities(self) -> List[str]:
        return self.db.get_custom_capabilities()

    def add_custom_capability(self, name: str, user_id: str = "guardian_1") -> Tuple[bool, str]:
        return self.db.add_custom_capability(name, user_id)

    def get_custom_skills(self) -> List[str]:
        return self.db.get_custom_skills()

    def add_custom_skill(self, name: str, user_id: str = "guardian_1") -> Tuple[bool, str]:
        return self.db.add_custom_skill(name, user_id)
