"""
STARAPP GAMIFIED ROADMAP & PREREQUISITE ENGINE
Calculates Candy Crush-inspired winding roadmap graph coordinates,
milestone progression states (completed, active, locked), and prerequisite satisfaction.
Enforces the 5-badge initial progression (3 completed, 1 at present, 1 locked)
and dynamic unlocking when the Guardian creates new badges for the cohort.
"""

from typing import List, Dict, Any, Optional
from starapp.models import Badge, AssessmentMarksheet

CANONICAL_ORDER = [
    "badge_gov_101",
    "badge_cur_102",
    "badge_dat_103",
    "badge_ing_104",
    "badge_sql_201",
    "badge_ai_301",
    "badge_cld_202",
    "badge_net_203",
    "badge_sft_105",
    "badge_hrd_106"
]

def compute_milestone_state(
    badge: Badge,
    cosmo_id: str,
    approved_badge_ids: Any,
    submission_status: Optional[str] = None
) -> str:
    """
    Computes milestone state based on approval and prerequisites.
    Returns: 'completed', 'active', or 'locked'.
    """
    if badge.id in approved_badge_ids:
        return "completed"

    if badge.prerequisites:
        if all(p in approved_badge_ids for p in badge.prerequisites):
            return "active"
        return "locked"
    return "active"

def generate_roadmap_graph(
    badges: List[Badge],
    cosmo_id: str,
    assessments: List[AssessmentMarksheet],
    submissions: List[Any]
) -> List[Dict[str, Any]]:
    """
    Constructs the sequence of roadmap milestone nodes with smooth curved path coordinates.
    Candy Crush-style serpentine pattern: center -> right -> center -> left -> center ...
    Progression rules:
    - Initially shows 5 badges:
      - 3 completed (approved assessments)
      - 1 at present (active milestone with pulsing halo)
      - 1 locked (last unallocated / pending prerequisite badge)
    - When Guardian allocates / unlocks a badge:
      - The newly allocated badge becomes AVAILABLE / ACTIVE (replaces the locked badge)
      - The NEXT route / upcoming unallocated curriculum badge becomes the new LOCKED milestone
    """
    # Approved badge IDs for this Cosmonaut
    approved_badge_ids = {
        a.badge_id for a in assessments
        if a.cosmonaut_id == cosmo_id and a.decision == "approve"
    }

    # Latest submission map: badge_id -> status
    latest_sub_status = {}
    for s in sorted(submissions, key=lambda x: x.attempt_number):
        if s.cosmonaut_id == cosmo_id:
            latest_sub_status[s.badge_id] = s.status

    # Order badges according to canonical progression, followed by newly created badges
    def sort_key(b: Badge):
        if b.id in CANONICAL_ORDER:
            return (0, CANONICAL_ORDER.index(b.id))
        return (1, b.id)

    # Filter published badges assigned to this Cosmonaut
    assigned_badges = [b for b in badges if b.is_published and cosmo_id in b.assigned_cosmonaut_ids]
    ordered_assigned = sorted(assigned_badges, key=sort_key)

    # Sequence of roadmap badges
    roadmap_badges = list(ordered_assigned)

    # Check if the last badge in assigned sequence is unallocated (e.g. SQL-201 in seed data)
    has_locked_badge = False
    if roadmap_badges:
        last_b = roadmap_badges[-1]
        if not getattr(last_b, "is_allocated", True):
            has_locked_badge = True

    # If the last assigned badge IS allocated (e.g. Guardian published/allocated AI-301),
    # or all assigned badges are completed, the newly allocated badge must be AVAILABLE (active),
    # and the NEXT unallocated curriculum badge must show as the new LOCKED route!
    if not has_locked_badge and roadmap_badges:
        assigned_ids = {b.id for b in roadmap_badges}
        unallocated_badges = [b for b in sorted(badges, key=sort_key) if b.id not in assigned_ids and b.is_published]
        if unallocated_badges:
            next_locked_badge = unallocated_badges[0]
            roadmap_badges.append(next_locked_badge)
        elif len(roadmap_badges) < len(CANONICAL_ORDER):
            next_idx = len(roadmap_badges) + 1
            next_code = CANONICAL_ORDER[len(roadmap_badges)].replace("badge_", "").upper().replace("_", "-")
            placeholder_locked = Badge(
                id=f"placeholder_milestone_{next_idx}",
                code=next_code,
                title=f"Milestone {next_idx} (Classified)",
                category="Advanced Specialization",
                description="Upcoming curriculum milestone. Requirements will unlock upon Guardian directive.",
                learning_outcomes=["Advanced engineering competency"],
                learning_topics=["Curriculum Pipeline"],
                prerequisites=[roadmap_badges[-1].id],
                project_requirements="Classified capstone deliverable.",
                is_published=True,
                assigned_cosmonaut_ids=[cosmo_id],
                is_allocated=False
            )
            roadmap_badges.append(placeholder_locked)

    total_count = len(roadmap_badges)
    nodes = []
    found_first_active = False

    for idx, badge in enumerate(roadmap_badges):
        # Progression state:
        # 1. If badge is approved -> 'completed'
        # 2. If not approved:
        #    - If it is the last badge in roadmap sequence -> 'locked'
        #    - Otherwise -> 'active' (AVAILABLE!)
        if badge.id in approved_badge_ids:
            state = "completed"
            is_current_active = False
        else:
            if idx == total_count - 1:
                state = "locked"
                is_current_active = False
            else:
                state = "active"
                if not found_first_active:
                    is_current_active = True
                    found_first_active = True
                else:
                    is_current_active = False

        # Serpentine container x-positions across 100% space (1000-unit SVG viewBox):
        # 1st badge: Left (190)
        # 2nd badge: Center (500)
        # 3rd badge: Right (810)
        # 4th badge: Middle / Center (500)
        # 5th badge: Left (190) ...
        pos_mod = idx % 4
        if pos_mod == 0:
            pos_class = "pos-left"
            cx = 190
        elif pos_mod == 1:
            pos_class = "pos-center"
            cx = 500
        elif pos_mod == 2:
            pos_class = "pos-right"
            cx = 810
        else:  # pos_mod == 3
            pos_class = "pos-center"
            cx = 500

        cy = 75 + idx * 175
        sub_status = latest_sub_status.get(badge.id, "not_started")

        nodes.append({
            "index": idx + 1,
            "badge_id": badge.id,
            "code": badge.code,
            "title": badge.title,
            "category": badge.category,
            "description": badge.description,
            "state": state,                      # 'completed', 'active', 'locked'
            "is_current_active": is_current_active,
            "submission_status": sub_status,
            "prerequisites": badge.prerequisites,
            "cx": cx,
            "cy": cy,
            "pos_class": pos_class,
            "topics_count": len(badge.learning_topics),
            "outcomes_count": len(badge.learning_outcomes)
        })

    return nodes
