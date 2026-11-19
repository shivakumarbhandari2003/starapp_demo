"""
STARAPP MAPPING REPOSITORY
Encapsulates all SQLite queries for Band Mappings, Reviewer Allocation Requests, and Pairings.
"""

import json
from typing import List, Dict, Any, Optional
from starapp.repositories.base import BaseRepository
from starapp.models import current_iso_timestamp

class MappingRepository(BaseRepository):
    def get_band_mappings(self) -> List[Dict[str, Any]]:
        rows = self.fetchall("SELECT * FROM band_mappings ORDER BY created_at DESC")
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "badge_id": r["badge_id"],
                "band_id": r["band_id"],
                "role_id": r["role_id"],
                "cosmonaut_ids": json.loads(r["cosmonaut_ids_json"]) if r.get("cosmonaut_ids_json") else [],
                "reviewer_ids": json.loads(r["reviewer_ids_json"]) if r.get("reviewer_ids_json") else [],
                "start_date": r.get("start_date", ""),
                "end_date": r.get("end_date", ""),
                "created_at": r.get("created_at", "")
            })
        return results

    def save_band_mapping(self, mapping: Dict[str, Any]):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO band_mappings (
                    id, badge_id, band_id, role_id, cosmonaut_ids_json, reviewer_ids_json,
                    start_date, end_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mapping["id"],
                    mapping.get("badge_id", ""),
                    mapping.get("band_id", ""),
                    mapping.get("role_id", ""),
                    json.dumps(mapping.get("cosmonaut_ids", [])),
                    json.dumps(mapping.get("reviewer_ids", [])),
                    mapping.get("start_date", ""),
                    mapping.get("end_date", ""),
                    mapping.get("created_at", current_iso_timestamp())
                )
            )

    def delete_band_mapping(self, mapping_id: str):
        if not self.conn:
            return
        with self.conn:
            self.execute("DELETE FROM band_mappings WHERE id = ?", (mapping_id,))

    def get_mapping_requests(self) -> List[Dict[str, Any]]:
        rows = self.fetchall("SELECT * FROM reviewer_requests ORDER BY sent_at DESC")
        return [dict(r) for r in rows]

    def save_mapping_request(self, req: Dict[str, Any]):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO reviewer_requests (
                    id, reviewer_id, badge_id, band_id, requested_by, sent_at,
                    deadline, status, responded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    req["id"],
                    req["reviewer_id"],
                    req["badge_id"],
                    req["band_id"],
                    req["requested_by"],
                    req.get("sent_at", current_iso_timestamp()),
                    req["deadline"],
                    req.get("status", "pending"),
                    req.get("responded_at")
                )
            )

    def update_mapping_request_status(self, req_id: str, status: str):
        if not self.conn:
            return
        with self.conn:
            self.execute("UPDATE reviewer_requests SET status = ?, responded_at = ? WHERE id = ?", (status, current_iso_timestamp(), req_id))
