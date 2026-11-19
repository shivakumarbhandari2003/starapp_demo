"""
STARAPP REPOSITORIES PACKAGE
Provides clean, modular Data Access Objects (DAOs) for SQLite3.
"""

from starapp.repositories.base import BaseRepository
from starapp.repositories.user_repo import UserRepository
from starapp.repositories.badge_repo import BadgeRepository
from starapp.repositories.timeline_repo import TimelineRepository
from starapp.repositories.assessment_repo import AssessmentRepository
from starapp.repositories.mapping_repo import MappingRepository
from starapp.repositories.material_repo import MaterialRepository
from starapp.repositories.extension_repo import ExtensionRepository
from starapp.repositories.announcement_repo import AnnouncementRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "BadgeRepository",
    "TimelineRepository",
    "AssessmentRepository",
    "MappingRepository",
    "MaterialRepository",
    "ExtensionRepository",
    "AnnouncementRepository"
]
