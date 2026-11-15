"""
STARAPP GAMIFIED ROADMAP & PREREQUISITE ENGINE
Calculates Candy Crush-inspired winding roadmap graph coordinates,
milestone progression states (completed, active, locked), and prerequisite satisfaction.
Enforces the 5-badge initial progression (3 completed, 1 at present, 1 locked)
and dynamic unlocking when the Guardian creates new badges for the cohort.
"""

from typing import List, Dict, Any, Optional
from starapp.models import Badge, AssessmentMarksheet

TOTAL_ROADMAP_MILESTONES = 25

CANONICAL_ORDER = [
    "badge_gov_101",
    "badge_cur_102",
    "badge_dat_103",
    "badge_ing_104",
    "badge_sql_201",
    "badge_ai_301",
    "badge_cld_202",
    "badge_net_203",
    "badge_sec_204",
    "badge_str_205",
    "badge_dbt_206",
    "badge_lkh_207",
    "badge_orc_208",
    "badge_dq_209",
    "badge_ml_302",
    "badge_rag_303",
    "badge_agt_304",
    "badge_evl_305",
    "badge_inf_306",
    "badge_k8s_307",
    "badge_iac_308",
    "badge_mon_309",
    "badge_gov_401",
    "badge_arc_402",
    "badge_cap_500",
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

    # Partition into Candy Crush progression tiers while preserving canonical ordering:
    # 1. Completed milestones (approved)
    # 2. Unlocked / published & allocated milestones available to the Cosmonaut
    # 3. Remaining locked catalog milestones up to TOTAL_ROADMAP_MILESTONES (25)
    ordered_all = sorted(badges, key=sort_key)
    completed_badges = []
    active_badges = []
    locked_badges = []

    for b in ordered_all:
        if b.id in approved_badge_ids:
            completed_badges.append(b)
        elif getattr(b, "is_allocated", False) and b.is_published and cosmo_id in b.assigned_cosmonaut_ids:
            active_badges.append(b)
        else:
            locked_badges.append(b)

    unlocked_badges = completed_badges + active_badges
    remaining_locked_slots = max(0, TOTAL_ROADMAP_MILESTONES - len(unlocked_badges))
    roadmap_badges = unlocked_badges + locked_badges[:remaining_locked_slots]

    # If fewer than 25 badges exist in a minimal test fixture, pad with locked placeholder levels
    while len(roadmap_badges) < TOTAL_ROADMAP_MILESTONES:
        next_idx = len(roadmap_badges) + 1
        code_hint = (
            CANONICAL_ORDER[len(roadmap_badges)].replace("badge_", "").upper().replace("_", "-")
            if len(roadmap_badges) < len(CANONICAL_ORDER)
            else f"LVL-{next_idx:03d}"
        )
        roadmap_badges.append(
            Badge(
                id=f"placeholder_milestone_{next_idx}",
                code=code_hint,
                title=f"Milestone {next_idx} (Classified)",
                category="Advanced Specialization",
                description="Upcoming curriculum milestone. Requirements will unlock upon Guardian publication.",
                learning_outcomes=["Advanced engineering competency"],
                learning_topics=["Curriculum Pipeline"],
                prerequisites=[roadmap_badges[-1].id] if roadmap_badges else [],
                project_requirements="Classified capstone deliverable.",
                is_published=False,
                assigned_cosmonaut_ids=[],
                is_allocated=False,
            )
        )

    nodes = []
    found_first_active = False

    for idx, badge in enumerate(roadmap_badges):
        # Candy Crush progression state:
        # 1. Approved -> 'completed'
        # 2. Published & allocated to Cosmonaut -> 'active' (unlocked)
        # 3. Unallocated / unpublished -> 'locked'
        if badge.id in approved_badge_ids:
            state = "completed"
            is_current_active = False
        elif getattr(badge, "is_allocated", False) and badge.is_published and cosmo_id in badge.assigned_cosmonaut_ids:
            state = "active"
            if not found_first_active:
                is_current_active = True
                found_first_active = True
            else:
                is_current_active = False
        else:
            state = "locked"
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
