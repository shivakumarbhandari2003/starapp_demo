"""
STARAPP DASHBOARD DEMONSTRATION DATASET
All cohort analytics are driven directly from SQLite database users.
Synthetic fictional data has been removed in favor of relational records.
"""

from typing import List, Dict, Any, Optional

DASHBOARD_DEMO_COSMONAUTS: List[Dict[str, Any]] = []

def get_dashboard_demo_cosmonauts() -> List[Dict[str, Any]]:
    """Returns empty list — all cohort analytics are loaded directly from SQLite database."""
    return DASHBOARD_DEMO_COSMONAUTS

def get_demo_cosmonaut_by_id(demo_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a cosmonaut profile from SQLite by user ID."""
    from starapp.storage import store
    user = store.get_user_by_id(demo_id)
    if user:
        from starapp.analytics import build_cosmonaut_analytics_record
        return build_cosmonaut_analytics_record(
            user,
            store.get_badges_for_cosmonaut(user.id),
            store.get_assessments_for_cosmonaut(user.id),
            store.get_submissions_for_cosmonaut(user.id),
            store.get_extensions_for_cosmonaut(user.id)
        )
    return None
