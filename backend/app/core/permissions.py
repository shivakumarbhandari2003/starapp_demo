"""
Authoritative business rule permissions and RBAC enforcement.
"""
from typing import Dict, Any, Tuple

BAND_HIERARCHY: Dict[str, int] = {
    "B1": 1,
    "B2": 2,
    "B3": 3,
    "B4": 4,
    "B5": 5,
    "B6": 6,
}


def verify_reviewer_eligibility(reviewer_band: str, badge_band: str) -> bool:
    """
    Enforces the non-negotiable reviewer eligibility rule:
    Reviewer_Band > Badge_Band
    
    B1 badges: Reviewable by B2, B3, B4, B5, B6.
    B2 badges: Reviewable by B3, B4, B5, B6.
    B3 badges: Reviewable by B4, B5, B6.
    B4 badges: Reviewable by B5, B6.
    B5 badges: Reviewable by B6.
    B6 badges: Locked out from peer review.
    """
    r_val = BAND_HIERARCHY.get(reviewer_band.upper(), 0)
    b_val = BAND_HIERARCHY.get(badge_band.upper(), 0)
    if b_val == 0 or r_val == 0:
        return False
    return r_val > b_val


def validate_50_mark_rubric(marks: Dict[str, Any]) -> Tuple[bool, str, int]:
    """
    Enforces the non-negotiable 5-criterion, 50-mark assessment rubric:
    1. Business Understanding — 0-10 marks
    2. Architecture / Report — 0-10 marks
    3. Technical Knowledge — 0-10 marks
    4. Presentation — 0-10 marks
    5. Question & Answering — 0-10 marks
    Total: 50 marks.
    """
    criteria_keys = [
        "business_understanding",
        "architecture_report",
        "technical_knowledge",
        "presentation",
        "question_answering",
    ]
    total = 0
    for key in criteria_keys:
        val = marks.get(key)
        if val is None:
            return False, f"Missing required criterion: {key}", 0
        try:
            val_int = int(val)
        except (ValueError, TypeError):
            return False, f"Criterion {key} mark must be an integer", 0
        if not (0 <= val_int <= 10):
            return False, f"Criterion {key} mark {val_int} out of range [0, 10]", 0
        total += val_int

    return True, "", total
