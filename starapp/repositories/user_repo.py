"""
STARAPP USER REPOSITORY
Encapsulates all SQLite queries for Users, Roles, Band Memberships, and Profiles.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from starapp.repositories.base import BaseRepository
from starapp.models import User, CosmonautProfile, current_iso_timestamp

class UserRepository(BaseRepository):
    def get_by_id(self, user_id: str) -> Optional[User]:
        if not user_id:
            return None
        row = self.fetchone("SELECT * FROM users WHERE id = ? OR lower(username) = ?", (user_id, user_id.lower()))
        if not row:
            return None

        roles = [r["role_id"] for r in self.fetchall("SELECT role_id FROM user_role_assignments WHERE user_id = ?", (row["id"],))]
        band_row = self.fetchone("SELECT band_code, track_code FROM user_band_memberships WHERE user_id = ?", (row["id"],))

        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            role=row["primary_role"],
            name=row["name"],
            avatar=row["avatar"] or row["name"][:2].upper(),
            roles=roles,
            band=band_row["band_code"] if band_row else "",
            learning_track=band_row["track_code"] if band_row else ""
        )

    def get_by_username(self, username: str) -> Optional[User]:
        if not username:
            return None
        u_clean = username.lower().strip()
        row = self.fetchone("SELECT id FROM users WHERE lower(username) = ? OR lower(email) = ?", (u_clean, u_clean))
        if row:
            return self.get_by_id(row["id"])
        return None

    def get_all_cosmonauts(self) -> List[User]:
        rows = self.fetchall("SELECT id FROM users WHERE primary_role = 'cosmonaut' ORDER BY name ASC")
        return [u for uid in rows if (u := self.get_by_id(uid["id"])) is not None]

    def get_cosmonaut_profile(self, user_id: str) -> CosmonautProfile:
        row = self.fetchone("SELECT * FROM cosmonaut_profiles WHERE user_id = ?", (user_id,))
        if row:
            skills = json.loads(row["skills_json"]) if row.get("skills_json") else []
            certs = json.loads(row["certifications_json"]) if row.get("certifications_json") else []
            return CosmonautProfile(
                user_id=row["user_id"],
                batch_name=row.get("batch_name", "Orion-24"),
                assigned_guardian_id=row.get("assigned_guardian_id", "guardian_1"),
                guardian_credentials=row.get("guardian_credentials", ""),
                skills=skills,
                certifications=certs
            )
        return CosmonautProfile(
            user_id=user_id,
            batch_name="Orion-24",
            assigned_guardian_id="guardian_1",
            guardian_credentials="Ph.D. Distributed Systems & AI, Lead Academy Mentor"
        )

    def save_user(self, user: User):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO users (id, username, email, name, primary_role, avatar, status, is_demo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'active', 0, ?)
                """,
                (user.id, user.username, user.email, user.name, user.role, user.avatar, current_iso_timestamp())
            )
            for r in getattr(user, "roles", [user.role]):
                self.execute(
                    "INSERT OR IGNORE INTO user_role_assignments (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                    (user.id, r, current_iso_timestamp())
                )
            if getattr(user, "band", None):
                self.execute(
                    "INSERT OR REPLACE INTO user_band_memberships (user_id, band_code, track_code, assigned_at) VALUES (?, ?, ?, ?)",
                    (user.id, user.band, getattr(user, "learning_track", "AI-ENG"), current_iso_timestamp())
                )

    def save_profile(self, profile: CosmonautProfile):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO cosmonaut_profiles (user_id, batch_name, assigned_guardian_id, guardian_credentials, skills_json, certifications_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.user_id,
                    profile.batch_name,
                    profile.assigned_guardian_id,
                    profile.guardian_credentials,
                    json.dumps(profile.skills),
                    json.dumps(profile.certifications)
                )
            )

    def get_eligible_badge_reviewers(self, target_band: str) -> List[Dict[str, Any]]:
        """Queries eligible higher-band reviewers directly from SQLite."""
        return self.db.get_eligible_badge_reviewers(target_band)

    def verify_reviewer_eligibility(self, reviewer_id: str, target_band: str) -> Tuple[bool, str]:
        """Strict verification of reviewer eligibility for badge authorization."""
        return self.db.verify_reviewer_eligibility(reviewer_id, target_band)
