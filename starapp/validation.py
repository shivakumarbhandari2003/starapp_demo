"""
STARAPP VALIDATION & BUSINESS INTEGRITY ENGINE
Enforces strict domain validation for submissions, rubric marks, timelines, and permissions.
"""

from typing import Tuple, Optional, Dict, Any, List

def validate_badge_input(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    title = str(data.get("title", "")).strip()
    code = str(data.get("code", "")).strip()
    if not title:
        return False, "Badge title cannot be blank."
    if not code:
        return False, "Badge code (e.g. GOV-101) cannot be blank."
    if len(title) < 3:
        return False, "Badge title must be at least 3 characters."
    return True, None

def validate_timeline_dates(dates: Dict[str, str]) -> Tuple[bool, Optional[str]]:
    """Verifies chronological order of key milestone dates."""
    sub_deadline = dates.get("submission_deadline", "")
    learning_start = dates.get("learning_start_date", "")
    learning_end = dates.get("learning_end_date", "")

    if not sub_deadline:
        return False, "Submission deadline date is required."

    if learning_start and learning_end and learning_start > learning_end:
        return False, "Learning start date cannot be after learning end date."

    if learning_end and sub_deadline and learning_end > sub_deadline:
        return False, "Learning end date cannot be after submission deadline."

    return True, None

def validate_submission_input(
    badge_id: str,
    cosmo_id: str,
    sub_type: str,
    payload: str
) -> Tuple[bool, Optional[str]]:
    if not badge_id:
        return False, "A target badge must be selected."
    if not cosmo_id:
        return False, "Invalid Cosmonaut identifier."
    if sub_type not in ["pdf", "github", "code"]:
        return False, "Invalid submission type. Choose PDF, GitHub, or Code file."
    if not payload or not str(payload).strip():
        return False, "Submission payload (file or URL) cannot be empty."

    if sub_type == "github":
        clean_url = str(payload).strip().lower()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://") or "github.com" in clean_url):
            return False, "Please enter a valid GitHub repository URL."

    return True, None

def validate_extension_request(
    current_deadline: str,
    proposed_deadline: str,
    reason: str
) -> Tuple[bool, Optional[str]]:
    if not proposed_deadline or not proposed_deadline.strip():
        return False, "Proposed new deadline date is required."
    if not reason or len(reason.strip()) < 10:
        return False, "Please provide a detailed reason (at least 10 characters)."
    if current_deadline and proposed_deadline <= current_deadline:
        return False, "Proposed deadline must be later than the current deadline."
    return True, None

def validate_announcement_input(
    title: str,
    message: str,
    target_type: str,
    target_ids: List[str]
) -> Tuple[bool, Optional[str]]:
    if not title or len(title.strip()) < 3:
        return False, "Announcement title must be at least 3 characters."
    if not message or len(message.strip()) < 5:
        return False, "Announcement message must be at least 5 characters."
    if target_type == "selected" and not target_ids:
        return False, "At least one target Cosmonaut must be selected."
    return True, None

