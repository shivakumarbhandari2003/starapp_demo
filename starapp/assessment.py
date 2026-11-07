"""
STARAPP STANDARD 50-MARK RUBRIC & ASSESSMENT ANALYTICS
Implements the universal 5-criterion standard (10 marks each = 50 total).
Computes aggregate batch KPIs, leaderboard rankings, and analytics.
"""

from typing import List, Dict, Any, Optional, Tuple
from starapp.models import AssessmentMarksheet, ProjectSubmission

RUBRIC_CRITERIA = [
    {
        "key": "business_understanding",
        "title": "Business Understanding",
        "max": 10.0,
        "desc": "Problem formulation, business context, compliance & domain clarity"
    },
    {
        "key": "architecture_report",
        "title": "Architecture / Report",
        "max": 10.0,
        "desc": "System architecture, modularity, data flow, diagrammatic rigor"
    },
    {
        "key": "technical_knowledge",
        "title": "Technical Knowledge",
        "max": 10.0,
        "desc": "Code quality, technical depth, optimization, engineering standards"
    },
    {
        "key": "presentation",
        "title": "Presentation",
        "max": 10.0,
        "desc": "Clarity of delivery, slide/report formatting, structured narrative"
    },
    {
        "key": "qa",
        "title": "Question & Answering",
        "max": 10.0,
        "desc": "Defense of trade-offs, edge-case analysis, problem responsiveness"
    }
]

def validate_rubric_scores(
    bu: float,
    ar: float,
    tk: float,
    pr: float,
    qa: float
) -> Tuple[bool, Optional[str]]:
    """Validates that all 5 criteria are within 0.0 to 10.0"""
    scores = {
        "Business Understanding": bu,
        "Architecture / Report": ar,
        "Technical Knowledge": tk,
        "Presentation": pr,
        "Question & Answering": qa
    }
    for name, val in scores.items():
        if val is None:
            return False, f"Missing score for {name}."
        try:
            fval = float(val)
        except (ValueError, TypeError):
            return False, f"Invalid numeric score for {name}."
        if fval < 0.0 or fval > 10.0:
            return False, f"{name} must be between 0.0 and 10.0 (received {fval})."
    return True, None

def calculate_assessment_totals(
    bu: float,
    ar: float,
    tk: float,
    pr: float,
    qa: float
) -> Tuple[float, float]:
    """Calculates total marks (/50) and percentage."""
    total = round(float(bu) + float(ar) + float(tk) + float(pr) + float(qa), 2)
    percentage = round((total / 50.0) * 100.0, 1)
    return total, percentage

def get_latest_assessments_by_badge(
    assessments: List[AssessmentMarksheet]
) -> Dict[str, AssessmentMarksheet]:
    """Returns the latest attempt assessment for each badge."""
    latest: Dict[str, AssessmentMarksheet] = {}
    for a in sorted(assessments, key=lambda x: x.attempt_number):
        latest[a.badge_id] = a
    return latest

def calculate_cosmonaut_score_summary(
    assessments: List[AssessmentMarksheet]
) -> Dict[str, Any]:
    """
    Computes individual performance based strictly on approved assessments.
    Leaderboard rule: Average of approved badge assessments out of 50.
    """
    approved = [a for a in assessments if a.decision == "approve"]
    if not approved:
        return {
            "approved_count": 0,
            "average_marks": 0.0,
            "average_percentage": 0.0,
            "best_marks": 0.0,
            "latest_decision": assessments[-1].decision if assessments else "none",
            "criterion_averages": {c["key"]: 0.0 for c in RUBRIC_CRITERIA}
        }

    latest_by_badge = {}
    for a in sorted(approved, key=lambda x: x.attempt_number):
        latest_by_badge[a.badge_id] = a

    valid_list = list(latest_by_badge.values())
    count = len(valid_list)
    total_sum = sum(a.total_marks for a in valid_list)
    avg_marks = round(total_sum / count, 2)
    avg_pct = round((avg_marks / 50.0) * 100.0, 1)
    best_marks = max(a.total_marks for a in valid_list)

    crit_avgs = {}
    for c in RUBRIC_CRITERIA:
        k = c["key"]
        crit_sum = sum(getattr(a, k) for a in valid_list)
        crit_avgs[k] = round(crit_sum / count, 2)

    return {
        "approved_count": count,
        "average_marks": avg_marks,
        "average_percentage": avg_pct,
        "best_marks": best_marks,
        "criterion_averages": crit_avgs
    }

def calculate_batch_leaderboard(
    cosmonauts: List[Any],
    all_assessments: List[AssessmentMarksheet]
) -> List[Dict[str, Any]]:
    """
    Computes the standardized batch leaderboard for all 6 Cosmonauts.
    Ranking criteria:
    1. Average score across approved badges (/50)
    2. Number of completed badges
    """
    leaderboard = []
    asms_by_user: Dict[str, List[AssessmentMarksheet]] = {}
    for a in all_assessments:
        asms_by_user.setdefault(a.cosmonaut_id, []).append(a)

    for cosmo in cosmonauts:
        user_asms = asms_by_user.get(cosmo.id, [])
        summary = calculate_cosmonaut_score_summary(user_asms)
        leaderboard.append({
            "cosmonaut_id": cosmo.id,
            "cosmonaut_name": cosmo.name,
            "avatar": cosmo.avatar,
            "completed_badges": summary["approved_count"],
            "average_marks": summary["average_marks"],
            "average_percentage": summary["average_percentage"],
            "best_marks": summary["best_marks"]
        })

    # Sort primarily by average_marks desc, secondarily by completed_badges desc
    leaderboard.sort(key=lambda x: (x["average_marks"], x["completed_badges"]), reverse=True)

    # Assign ranks
    for idx, item in enumerate(leaderboard, start=1):
        item["rank"] = idx

    return leaderboard

def calculate_batch_aggregate_analytics(
    cosmonauts: List[Any],
    all_badges: List[Any],
    all_submissions: List[ProjectSubmission],
    all_assessments: List[AssessmentMarksheet]
) -> Dict[str, Any]:
    """Calculates batch-level KPIs for Guardian Dashboard."""
    total_cosmonauts = len(cosmonauts)
    total_assigned_badges = sum(len(b.assigned_cosmonaut_ids) for b in all_badges if b.is_published)
    
    # Approved assessments
    approved_asms = [a for a in all_assessments if a.decision == "approve"]
    completed_badge_count = len(approved_asms)

    # Submissions awaiting review
    pending_submissions = [s for s in all_submissions if s.status == "pending"]

    # Active badges count across batch
    active_badges = max(0, total_assigned_badges - completed_badge_count)

    # Batch average score
    if approved_asms:
        batch_avg_score = round(sum(a.total_marks for a in approved_asms) / len(approved_asms), 2)
        batch_avg_pct = round((batch_avg_score / 50.0) * 100.0, 1)
    else:
        batch_avg_score = 0.0
        batch_avg_pct = 0.0

    # Criterion-wise batch averages
    criterion_averages = {}
    for c in RUBRIC_CRITERIA:
        k = c["key"]
        if approved_asms:
            c_avg = round(sum(getattr(a, k) for a in approved_asms) / len(approved_asms), 2)
        else:
            c_avg = 0.0
        criterion_averages[k] = c_avg

    # Completion rate
    completion_rate = round((completed_badge_count / max(1, total_assigned_badges)) * 100.0, 1)

    return {
        "total_cosmonauts": total_cosmonauts,
        "total_assigned_badges": total_assigned_badges,
        "completed_badges": completed_badge_count,
        "active_badges": active_badges,
        "pending_reviews": len(pending_submissions),
        "batch_avg_score": batch_avg_score,
        "batch_avg_pct": batch_avg_pct,
        "completion_rate": completion_rate,
        "criterion_averages": criterion_averages
    }

