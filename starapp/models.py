"""
STARAPP SHARED DATA MODELS
Defines the unified data structures shared by Guardian and Cosmonaut portals.
All models serialize to/from clean JSON-compatible dictionaries.
"""

from typing import List, Dict, Any, Optional
import calendar
import datetime
import json
import time

DEFAULT_CYCLE_ID = "cycle_1"

DEFAULT_HIKE_POLICY: Dict[str, Any] = {
    "duration_months": 6,
    "weights": {
        "cosmonaut_marks_weight": 0.55,
        "cosmonaut_completion_weight": 0.25,
        "reviewer_execution_weight": 0.20,
    },
    "slabs": [
        {"min_score": 90.0, "tier": "Outstanding", "recommended_hike_pct": 18.0},
        {"min_score": 80.0, "tier": "Exceeds Expectations", "recommended_hike_pct": 12.0},
        {"min_score": 70.0, "tier": "Meets Expectations", "recommended_hike_pct": 8.0},
        {"min_score": 1.0, "tier": "Needs Development", "recommended_hike_pct": 3.0},
        {"min_score": 0.0, "tier": "Not Assessed", "recommended_hike_pct": 0.0},
    ],
}

def current_iso_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def add_six_months_iso(start_date: str, months: int = 6) -> str:
    """Computes an inclusive 6-month cycle end date (YYYY-MM-DD)."""
    try:
        d = datetime.date.fromisoformat(str(start_date or "")[:10])
    except Exception:
        d = datetime.date.today()
    total_m = (d.month - 1) + int(months)
    year = d.year + (total_m // 12)
    month = (total_m % 12) + 1
    max_day = calendar.monthrange(year, month)[1]
    end_plus = datetime.date(year, month, min(d.day, max_day))
    return (end_plus - datetime.timedelta(days=1)).isoformat()

class User:
    def __init__(
        self,
        id: str,
        username: str,
        email: str,
        role: str,
        name: str,
        avatar: str = "",
        roles: Optional[List[str]] = None,
        band: str = "",
        learning_track: str = "",
        age: int = 30,
        reporting_manager_id: Optional[str] = None,
        reporting_manager_name: Optional[str] = None,
        reporting_manager_band: Optional[str] = None,
        password: str = "123456789"
    ):
        self.id = id
        self.username = username
        self.email = email
        self.role = role  # Primary role: "guardian", "cosmonaut", "badge_reviewer"
        self.name = name
        self.avatar = avatar or name[:2].upper()
        self.roles = roles if roles is not None else [role]
        if role not in self.roles:
            self.roles.append(role)
        self.band = band
        self.learning_track = learning_track
        self.age = age
        self.reporting_manager_id = reporting_manager_id
        self.reporting_manager_name = reporting_manager_name
        self.reporting_manager_band = reporting_manager_band
        self.password = password

    def has_role(self, role_name: str) -> bool:
        if self.role == role_name:
            return True
        return role_name in getattr(self, "roles", [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "roles": self.roles,
            "name": self.name,
            "avatar": self.avatar,
            "band": getattr(self, "band", ""),
            "learning_track": getattr(self, "learning_track", ""),
            "age": getattr(self, "age", 30),
            "reporting_manager_id": getattr(self, "reporting_manager_id", None),
            "reporting_manager_name": getattr(self, "reporting_manager_name", None),
            "reporting_manager_band": getattr(self, "reporting_manager_band", None),
            "password": getattr(self, "password", "123456789")
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            id=data["id"],
            username=data.get("username", ""),
            email=data["email"],
            role=data["role"],
            name=data["name"],
            avatar=data.get("avatar", ""),
            roles=data.get("roles"),
            band=data.get("band", ""),
            learning_track=data.get("learning_track", ""),
            age=data.get("age", 30),
            reporting_manager_id=data.get("reporting_manager_id"),
            reporting_manager_name=data.get("reporting_manager_name"),
            reporting_manager_band=data.get("reporting_manager_band"),
            password=data.get("password", "123456789")
        )


class CosmonautProfile:
    def __init__(
        self,
        user_id: str,
        batch_name: str,
        assigned_guardian_id: str,
        guardian_credentials: str,
        skills: Optional[List[str]] = None,
        certifications: Optional[List[Dict[str, str]]] = None
    ):
        self.user_id = user_id
        self.batch_name = batch_name
        self.assigned_guardian_id = assigned_guardian_id
        self.guardian_credentials = guardian_credentials
        self.skills = skills or []
        self.certifications = certifications or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "batch_name": self.batch_name,
            "assigned_guardian_id": self.assigned_guardian_id,
            "guardian_credentials": self.guardian_credentials,
            "skills": self.skills,
            "certifications": self.certifications
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CosmonautProfile":
        return cls(
            user_id=data["user_id"],
            batch_name=data.get("batch_name", "Orion-24"),
            assigned_guardian_id=data.get("assigned_guardian_id", "guardian_1"),
            guardian_credentials=data.get("guardian_credentials", "Ph.D. Computer Science, Enterprise Data Architect"),
            skills=data.get("skills", []),
            certifications=data.get("certifications", [])
        )


class Badge:
    def __init__(
        self,
        id: str,
        code: str,
        title: str,
        category: str,
        description: str,
        learning_outcomes: List[str],
        learning_topics: List[str],
        prerequisites: List[str],
        project_requirements: str,
        is_published: bool = True,
        assigned_cosmonaut_ids: Optional[List[str]] = None,
        default_timeline: Optional[Dict[str, str]] = None,
        is_allocated: bool = True,
        target_band: str = "",
        power: str = "",
        capability: str = "",
        skill: str = "",
        prompt_json: str = "",
        workflow_status: str = "approved",
        creator_id: str = "",
        assigned_reviewer_id: str = "",
        review_due_at: str = "",
        created_at: str = "",
        updated_at: str = "",
        passing_percentage: float = 70.0,
        published_at: str = "",
        published_by: str = "",
        cycle_id: str = DEFAULT_CYCLE_ID
    ):
        self.id = id
        self.code = code
        self.title = title
        self.category = category
        self.description = description
        self.learning_outcomes = learning_outcomes
        self.learning_topics = learning_topics
        self.prerequisites = prerequisites
        self.project_requirements = project_requirements
        self.is_published = is_published
        self.assigned_cosmonaut_ids = assigned_cosmonaut_ids or []
        self.default_timeline = default_timeline or {}
        self.is_allocated = is_allocated
        self.target_band = target_band
        self.power = power
        self.capability = capability
        self.skill = skill
        self.prompt_json = prompt_json
        self.workflow_status = workflow_status
        self.creator_id = creator_id
        self.assigned_reviewer_id = assigned_reviewer_id
        self.review_due_at = review_due_at
        self.created_at = created_at or current_iso_timestamp()
        self.updated_at = updated_at or current_iso_timestamp()
        self.passing_percentage = float(passing_percentage) if passing_percentage is not None else 70.0
        self.published_at = published_at or ""
        self.published_by = published_by or ""
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "learning_outcomes": self.learning_outcomes,
            "learning_topics": self.learning_topics,
            "prerequisites": self.prerequisites,
            "project_requirements": self.project_requirements,
            "is_published": self.is_published,
            "assigned_cosmonaut_ids": self.assigned_cosmonaut_ids,
            "default_timeline": self.default_timeline,
            "is_allocated": getattr(self, "is_allocated", True),
            "target_band": getattr(self, "target_band", ""),
            "power": getattr(self, "power", ""),
            "capability": getattr(self, "capability", ""),
            "skill": getattr(self, "skill", ""),
            "prompt_json": getattr(self, "prompt_json", ""),
            "workflow_status": getattr(self, "workflow_status", "approved"),
            "creator_id": getattr(self, "creator_id", ""),
            "assigned_reviewer_id": getattr(self, "assigned_reviewer_id", ""),
            "review_due_at": getattr(self, "review_due_at", ""),
            "created_at": getattr(self, "created_at", ""),
            "updated_at": getattr(self, "updated_at", ""),
            "passing_percentage": getattr(self, "passing_percentage", 70.0),
            "published_at": getattr(self, "published_at", ""),
            "published_by": getattr(self, "published_by", ""),
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Badge":
        return cls(
            id=data["id"],
            code=data.get("code", ""),
            title=data["title"],
            category=data.get("category", "Foundations"),
            description=data.get("description", ""),
            learning_outcomes=data.get("learning_outcomes", []),
            learning_topics=data.get("learning_topics", []),
            prerequisites=data.get("prerequisites", []),
            project_requirements=data.get("project_requirements", ""),
            is_published=data.get("is_published", True),
            assigned_cosmonaut_ids=data.get("assigned_cosmonaut_ids", []),
            default_timeline=data.get("default_timeline", {}),
            is_allocated=data.get("is_allocated", True),
            target_band=data.get("target_band", ""),
            power=data.get("power", ""),
            capability=data.get("capability", ""),
            skill=data.get("skill", ""),
            prompt_json=data.get("prompt_json", ""),
            workflow_status=data.get("workflow_status", "approved"),
            creator_id=data.get("creator_id", ""),
            assigned_reviewer_id=data.get("assigned_reviewer_id", ""),
            review_due_at=data.get("review_due_at", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            passing_percentage=data.get("passing_percentage", 70.0),
            published_at=data.get("published_at", ""),
            published_by=data.get("published_by", ""),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID
        )


class BadgeTimeline:
    """9-Point Detailed Timeline for a Badge Assignment"""
    def __init__(
        self,
        badge_id: str,
        cosmonaut_id: str,
        assignment_date: str,
        publication_date: str,
        learning_start_date: str,
        learning_end_date: str,
        project_start_date: str,
        project_end_date: str,
        submission_deadline: str,
        review_date: str,
        expected_award_date: str,
        actual_award_date: str = "",
        status: str = "active",  # upcoming, active, completed, overdue, awaiting_review
        reviewer_id: str = "",
        review_window_json: str = "[]",
        cycle_id: str = DEFAULT_CYCLE_ID
    ):
        self.badge_id = badge_id
        self.cosmonaut_id = cosmonaut_id
        self.assignment_date = assignment_date
        self.publication_date = publication_date
        self.learning_start_date = learning_start_date
        self.learning_end_date = learning_end_date
        self.project_start_date = project_start_date
        self.project_end_date = project_end_date
        self.submission_deadline = submission_deadline
        self.review_date = review_date
        self.expected_award_date = expected_award_date
        self.actual_award_date = actual_award_date
        self.status = status
        self.reviewer_id = reviewer_id
        self.review_window_json = review_window_json
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    @property
    def review_window(self) -> List[str]:
        try:
            return json.loads(self.review_window_json or "[]")
        except Exception:
            return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "badge_id": self.badge_id,
            "cosmonaut_id": self.cosmonaut_id,
            "assignment_date": self.assignment_date,
            "publication_date": self.publication_date,
            "learning_start_date": self.learning_start_date,
            "learning_end_date": self.learning_end_date,
            "project_start_date": self.project_start_date,
            "project_end_date": self.project_end_date,
            "submission_deadline": self.submission_deadline,
            "review_date": self.review_date,
            "expected_award_date": self.expected_award_date,
            "actual_award_date": self.actual_award_date,
            "status": self.status,
            "reviewer_id": getattr(self, "reviewer_id", ""),
            "review_window_json": getattr(self, "review_window_json", "[]"),
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BadgeTimeline":
        return cls(
            badge_id=data["badge_id"],
            cosmonaut_id=data["cosmonaut_id"],
            assignment_date=data.get("assignment_date", ""),
            publication_date=data.get("publication_date", ""),
            learning_start_date=data.get("learning_start_date", ""),
            learning_end_date=data.get("learning_end_date", ""),
            project_start_date=data.get("project_start_date", ""),
            project_end_date=data.get("project_end_date", ""),
            submission_deadline=data.get("submission_deadline", ""),
            review_date=data.get("review_date", ""),
            expected_award_date=data.get("expected_award_date", ""),
            actual_award_date=data.get("actual_award_date", ""),
            status=data.get("status", "active"),
            reviewer_id=data.get("reviewer_id", ""),
            review_window_json=data.get("review_window_json", "[]"),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID
        )


class ProjectSubmission:
    """
    A cadet's deliverable attempt. The three large payload fields (`payload`, `pdf_payload`,
    `code_payload`) can be LAZY: when the store loads thousands of submissions it keeps only the
    metadata in memory and fetches the heavy data URLs from SQLite the first time they are read.
    """
    def __init__(
        self,
        id: str,
        badge_id: str,
        cosmonaut_id: str,
        attempt_number: int,
        submission_type: str,  # "pdf", "github", "code", "multi"
        payload: str,          # file dataUrl or github url or code text
        file_name: str,
        submitted_at: str,
        status: str = "pending",  # "pending", "approved", "rejected", "resubmission_requested"
        pdf_name: str = "",
        pdf_payload: str = "",
        code_name: str = "",
        code_payload: str = "",
        github_url: str = "",
        cycle_id: str = DEFAULT_CYCLE_ID,
        lazy_payload: bool = False,
    ):
        self.id = id
        self.badge_id = badge_id
        self.cosmonaut_id = cosmonaut_id
        self.attempt_number = attempt_number
        self.submission_type = submission_type
        self.file_name = file_name
        self.submitted_at = submitted_at
        self.status = status

        # Lazy state must exist before any payload property is touched.
        self._lazy = bool(lazy_payload)
        self._loader = None
        self._payload = payload
        self._pdf_payload = pdf_payload or (payload if submission_type == "pdf" else "")
        self._code_payload = code_payload or (payload if submission_type == "code" else "")

        self.pdf_name = pdf_name or (file_name if submission_type == "pdf" else "")
        self.code_name = code_name or (file_name if submission_type == "code" else "")
        self.github_url = github_url or (payload if submission_type == "github" else "")
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    # -- lazy payload handling ------------------------------------------------
    @property
    def payload_is_lazy(self) -> bool:
        return self._lazy

    def _hydrate(self):
        if not self._lazy:
            return
        self._lazy = False
        loader = self._loader
        if loader is None:
            return
        try:
            blobs = loader(self.id) or {}
        except Exception:
            blobs = {}
        self._payload = blobs.get("payload", self._payload) or ""
        self._pdf_payload = blobs.get("pdf_payload", "") or (self._payload if self.submission_type == "pdf" else "")
        self._code_payload = blobs.get("code_payload", "") or (self._payload if self.submission_type == "code" else "")

    @property
    def payload(self) -> str:
        self._hydrate()
        return self._payload

    @payload.setter
    def payload(self, value: str):
        self._hydrate()
        self._payload = value

    @property
    def pdf_payload(self) -> str:
        self._hydrate()
        return self._pdf_payload

    @pdf_payload.setter
    def pdf_payload(self, value: str):
        self._hydrate()
        self._pdf_payload = value

    @property
    def code_payload(self) -> str:
        self._hydrate()
        return self._code_payload

    @code_payload.setter
    def code_payload(self, value: str):
        self._hydrate()
        self._code_payload = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "badge_id": self.badge_id,
            "cosmonaut_id": self.cosmonaut_id,
            "attempt_number": self.attempt_number,
            "submission_type": self.submission_type,
            "payload": self.payload,
            "file_name": self.file_name,
            "submitted_at": self.submitted_at,
            "status": self.status,
            "pdf_name": getattr(self, "pdf_name", ""),
            "pdf_payload": self.pdf_payload,
            "code_name": getattr(self, "code_name", ""),
            "code_payload": self.code_payload,
            "github_url": getattr(self, "github_url", ""),
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectSubmission":
        sub_type = data.get("submission_type", "pdf")
        payload = data.get("payload", "")
        fname = data.get("file_name", "")
        return cls(
            id=data["id"],
            badge_id=data["badge_id"],
            cosmonaut_id=data["cosmonaut_id"],
            attempt_number=data.get("attempt_number", 1),
            submission_type=sub_type,
            payload=payload,
            file_name=fname,
            submitted_at=data.get("submitted_at", current_iso_timestamp()),
            status=data.get("status", "pending"),
            pdf_name=data.get("pdf_name", fname if sub_type == "pdf" else ""),
            pdf_payload=data.get("pdf_payload", payload if sub_type == "pdf" else ""),
            code_name=data.get("code_name", fname if sub_type == "code" else ""),
            code_payload=data.get("code_payload", payload if sub_type == "code" else ""),
            github_url=data.get("github_url", payload if sub_type == "github" else ""),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID,
            lazy_payload=bool(data.get("lazy_payload", False)),
        )


class AssessmentMarksheet:
    """Standard 50-mark rubric marksheet (5 mandatory criteria x 10 marks max)"""
    def __init__(
        self,
        id: str,
        submission_id: str,
        attempt_number: int,
        badge_id: str,
        cosmonaut_id: str,
        reviewer_id: str,
        reviewer_name: str,
        reviewed_at: str,
        decision: str,  # "approve", "reject", "resubmission_requested"
        business_understanding: float,
        architecture_report: float,
        technical_knowledge: float,
        presentation: float,
        qa: float,
        strength_areas: str,
        improvement_areas: str,
        overall_feedback: str,
        assessor_role: str = "guardian",
        remarks: str = "",
        cycle_id: str = DEFAULT_CYCLE_ID
    ):
        self.id = id
        self.submission_id = submission_id
        self.attempt_number = attempt_number
        self.badge_id = badge_id
        self.cosmonaut_id = cosmonaut_id
        self.reviewer_id = reviewer_id
        self.reviewer_name = reviewer_name
        self.reviewed_at = reviewed_at
        self.decision = decision

        # 5 Mandatory Rubric Scores (0 to 10 each)
        self.business_understanding = float(business_understanding)
        self.architecture_report = float(architecture_report)
        self.technical_knowledge = float(technical_knowledge)
        self.presentation = float(presentation)
        self.qa = float(qa)

        # Automatic Calculations
        self.total_marks = round(
            self.business_understanding +
            self.architecture_report +
            self.technical_knowledge +
            self.presentation +
            self.qa,
            2
        )
        self.percentage = round((self.total_marks / 50.0) * 100.0, 1)

        self.strength_areas = strength_areas
        self.improvement_areas = improvement_areas
        self.overall_feedback = overall_feedback
        self.assessor_role = assessor_role
        self.remarks = remarks
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    @property
    def total_score(self) -> float:
        return self.total_marks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "attempt_number": self.attempt_number,
            "badge_id": self.badge_id,
            "cosmonaut_id": self.cosmonaut_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer_name,
            "reviewed_at": self.reviewed_at,
            "decision": self.decision,
            "business_understanding": self.business_understanding,
            "architecture_report": self.architecture_report,
            "technical_knowledge": self.technical_knowledge,
            "presentation": self.presentation,
            "qa": self.qa,
            "total_marks": self.total_marks,
            "percentage": self.percentage,
            "strength_areas": self.strength_areas,
            "improvement_areas": self.improvement_areas,
            "overall_feedback": self.overall_feedback,
            "assessor_role": getattr(self, "assessor_role", "guardian"),
            "remarks": getattr(self, "remarks", ""),
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssessmentMarksheet":
        return cls(
            id=data["id"],
            submission_id=data["submission_id"],
            attempt_number=data.get("attempt_number", 1),
            badge_id=data["badge_id"],
            cosmonaut_id=data["cosmonaut_id"],
            reviewer_id=data.get("reviewer_id", "guardian_1"),
            reviewer_name=data.get("reviewer_name", "Arjun Mehta"),
            reviewed_at=data.get("reviewed_at", current_iso_timestamp()),
            decision=data.get("decision", "approve"),
            business_understanding=data.get("business_understanding", 0),
            architecture_report=data.get("architecture_report", 0),
            technical_knowledge=data.get("technical_knowledge", 0),
            presentation=data.get("presentation", 0),
            qa=data.get("qa", 0),
            strength_areas=data.get("strength_areas", ""),
            improvement_areas=data.get("improvement_areas", ""),
            overall_feedback=data.get("overall_feedback", ""),
            assessor_role=data.get("assessor_role", "guardian"),
            remarks=data.get("remarks", ""),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID
        )


class LearningMaterial:
    def __init__(
        self,
        id: str,
        badge_id: str,
        topic: str,
        title: str,
        description: str,
        material_type: str,  # "pdf", "doc", "youtube", "code"
        url_or_data: str,
        upload_date: str,
        cycle_id: str = DEFAULT_CYCLE_ID
    ):
        self.id = id
        self.badge_id = badge_id
        self.topic = topic
        self.title = title
        self.description = description
        self.material_type = material_type
        self.url_or_data = url_or_data
        self.upload_date = upload_date
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "badge_id": self.badge_id,
            "topic": self.topic,
            "title": self.title,
            "description": self.description,
            "material_type": self.material_type,
            "url_or_data": self.url_or_data,
            "upload_date": self.upload_date,
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningMaterial":
        return cls(
            id=data["id"],
            badge_id=data["badge_id"],
            topic=data.get("topic", "General"),
            title=data["title"],
            description=data.get("description", ""),
            material_type=data.get("material_type", "doc"),
            url_or_data=data.get("url_or_data", ""),
            upload_date=data.get("upload_date", current_iso_timestamp()),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID
        )


class DeadlineExtension:
    def __init__(
        self,
        id: str,
        badge_id: str,
        cosmonaut_id: str,
        current_deadline: str,
        proposed_deadline: str,
        reason: str,
        status: str = "pending",  # "pending", "approved", "rejected"
        guardian_response: str = "",
        requested_at: str = "",
        decided_at: str = "",
        cycle_id: str = DEFAULT_CYCLE_ID
    ):
        self.id = id
        self.badge_id = badge_id
        self.cosmonaut_id = cosmonaut_id
        self.current_deadline = current_deadline
        self.proposed_deadline = proposed_deadline
        self.reason = reason
        self.status = status
        self.guardian_response = guardian_response
        self.requested_at = requested_at or current_iso_timestamp()
        self.decided_at = decided_at
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "badge_id": self.badge_id,
            "cosmonaut_id": self.cosmonaut_id,
            "current_deadline": self.current_deadline,
            "proposed_deadline": self.proposed_deadline,
            "reason": self.reason,
            "status": self.status,
            "guardian_response": self.guardian_response,
            "requested_at": self.requested_at,
            "decided_at": self.decided_at,
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeadlineExtension":
        return cls(
            id=data["id"],
            badge_id=data["badge_id"],
            cosmonaut_id=data["cosmonaut_id"],
            current_deadline=data.get("current_deadline", ""),
            proposed_deadline=data.get("proposed_deadline", ""),
            reason=data.get("reason", ""),
            status=data.get("status", "pending"),
            guardian_response=data.get("guardian_response", ""),
            requested_at=data.get("requested_at", ""),
            decided_at=data.get("decided_at", ""),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID
        )


class Announcement:
    def __init__(
        self,
        id: str,
        title: str,
        message: str,
        author_id: str,
        author_name: str,
        target_type: str,  # "all", "selected"
        target_cosmonaut_ids: List[str],
        badge_id: str = "",
        published_at: str = "",
        expiry_date: str = "",
        read_by_cosmonaut_ids: Optional[List[str]] = None,
        cycle_id: str = DEFAULT_CYCLE_ID
    ):
        self.id = id
        self.title = title
        self.message = message
        self.author_id = author_id
        self.author_name = author_name
        self.target_type = target_type
        self.target_cosmonaut_ids = target_cosmonaut_ids
        self.badge_id = badge_id
        self.published_at = published_at or current_iso_timestamp()
        self.expiry_date = expiry_date
        self.read_by_cosmonaut_ids = read_by_cosmonaut_ids or []
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "target_type": self.target_type,
            "target_cosmonaut_ids": self.target_cosmonaut_ids,
            "badge_id": self.badge_id,
            "published_at": self.published_at,
            "expiry_date": self.expiry_date,
            "read_by_cosmonaut_ids": self.read_by_cosmonaut_ids,
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Announcement":
        return cls(
            id=data["id"],
            title=data["title"],
            message=data["message"],
            author_id=data.get("author_id", "guardian_1"),
            author_name=data.get("author_name", "Arjun Mehta"),
            target_type=data.get("target_type", "all"),
            target_cosmonaut_ids=data.get("target_cosmonaut_ids", []),
            badge_id=data.get("badge_id", ""),
            published_at=data.get("published_at", ""),
            expiry_date=data.get("expiry_date", ""),
            read_by_cosmonaut_ids=data.get("read_by_cosmonaut_ids", []),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID
        )


class ActivityEvent:
    def __init__(
        self,
        id: str,
        timestamp: str,
        event_type: str,
        actor_id: str,
        actor_name: str,
        cosmonaut_id: str,
        badge_id: str,
        summary: str,
        details: str = "",
        cycle_id: str = DEFAULT_CYCLE_ID
    ):
        self.id = id
        self.timestamp = timestamp or current_iso_timestamp()
        self.event_type = event_type
        self.actor_id = actor_id
        self.actor_name = actor_name
        self.cosmonaut_id = cosmonaut_id
        self.badge_id = badge_id
        self.summary = summary
        self.details = details
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "cosmonaut_id": self.cosmonaut_id,
            "badge_id": self.badge_id,
            "summary": self.summary,
            "details": self.details,
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityEvent":
        return cls(
            id=data["id"],
            timestamp=data.get("timestamp", ""),
            event_type=data.get("event_type", "general"),
            actor_id=data.get("actor_id", ""),
            actor_name=data.get("actor_name", ""),
            cosmonaut_id=data.get("cosmonaut_id", ""),
            badge_id=data.get("badge_id", ""),
            summary=data.get("summary", ""),
            details=data.get("details", ""),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID
        )


class Notification:
    def __init__(
        self,
        id: str,
        recipient_id: str,
        title: str,
        message: str,
        link_section: str,
        created_at: str,
        is_read: bool = False,
        cycle_id: str = DEFAULT_CYCLE_ID
    ):
        self.id = id
        self.recipient_id = recipient_id
        self.title = title
        self.message = message
        self.link_section = link_section
        self.created_at = created_at or current_iso_timestamp()
        self.is_read = is_read
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "title": self.title,
            "message": self.message,
            "link_section": self.link_section,
            "created_at": self.created_at,
            "is_read": self.is_read,
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Notification":
        return cls(
            id=data["id"],
            recipient_id=data["recipient_id"],
            title=data["title"],
            message=data["message"],
            link_section=data.get("link_section", ""),
            created_at=data.get("created_at", ""),
            is_read=data.get("is_read", False),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID
        )


class ReviewerProjectPrompt:
    def __init__(
        self,
        id: str = "",
        badge_id: str = "",
        reviewer_id: str = "",
        cosmonaut_ids: Optional[List[str]] = None,
        title: str = "Milestone Implementation Project",
        description: str = "",
        deliverables: Optional[Dict[str, Any]] = None,
        requirements: Optional[List[str]] = None,
        created_at: str = "",
        sent_at: Optional[str] = None,
        status: str = "released",
        reviewer_name: str = "",
        objective: str = "",
        technical_requirements: Optional[List[str]] = None,
        evaluation_criteria: Optional[List[str]] = None,
        submission_deadline: str = "",
        outcomes: Optional[List[str]] = None,
        cycle_id: str = DEFAULT_CYCLE_ID,
        **kwargs
    ):
        self.id = id or f"proj_{badge_id}_{reviewer_id}"
        self.badge_id = badge_id
        self.reviewer_id = reviewer_id
        self.reviewer_name = reviewer_name
        self.cosmonaut_ids = list(cosmonaut_ids) if cosmonaut_ids else []
        self.title = title
        self.description = description or objective
        self.objective = self.description
        self.deliverables = deliverables or {}
        self.requirements = requirements or technical_requirements or []
        self.technical_requirements = self.requirements
        self.evaluation_criteria = evaluation_criteria or []
        self.submission_deadline = submission_deadline
        self.outcomes = list(outcomes) if outcomes else []
        self.created_at = created_at or current_iso_timestamp()
        self.sent_at = sent_at or self.created_at
        self.status = status
        self.cycle_id = cycle_id or DEFAULT_CYCLE_ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "badge_id": self.badge_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": getattr(self, "reviewer_name", ""),
            "cosmonaut_ids": self.cosmonaut_ids,
            "title": self.title,
            "description": self.description,
            "objective": self.description,
            "deliverables": self.deliverables,
            "requirements": self.requirements,
            "technical_requirements": self.requirements,
            "evaluation_criteria": getattr(self, "evaluation_criteria", []),
            "submission_deadline": getattr(self, "submission_deadline", ""),
            "outcomes": getattr(self, "outcomes", []),
            "created_at": self.created_at,
            "sent_at": self.sent_at,
            "status": self.status,
            "cycle_id": getattr(self, "cycle_id", DEFAULT_CYCLE_ID)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewerProjectPrompt":
        deliverables = data.get("deliverables") or data.get("deliverables_json")
        if isinstance(deliverables, str):
            try:
                deliverables = json.loads(deliverables)
            except Exception:
                deliverables = {}
        requirements = data.get("requirements") or data.get("requirements_text") or data.get("requirements_json")
        if isinstance(requirements, str):
            try:
                requirements = json.loads(requirements)
            except Exception:
                requirements = [requirements]
        outcomes = data.get("outcomes") or data.get("outcomes_json") or []
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except Exception:
                outcomes = [x.strip() for x in outcomes.split("\n") if x.strip()]
        cosmonauts = data.get("cosmonaut_ids") or data.get("cosmonaut_ids_json") or []
        if isinstance(cosmonauts, str):
            try:
                cosmonauts = json.loads(cosmonauts)
            except Exception:
                cosmonauts = []
        return cls(
            id=data["id"],
            badge_id=data["badge_id"],
            reviewer_id=data.get("reviewer_id", ""),
            cosmonaut_ids=cosmonauts,
            title=data.get("title", "Milestone Implementation Project"),
            description=data.get("description", ""),
            deliverables=deliverables or {},
            requirements=requirements or [],
            outcomes=outcomes or [],
            created_at=data.get("created_at", ""),
            sent_at=data.get("sent_at"),
            status=data.get("status", "released"),
            reviewer_name=data.get("reviewer_name", ""),
            objective=data.get("objective", ""),
            technical_requirements=requirements or [],
            evaluation_criteria=data.get("evaluation_criteria", []),
            submission_deadline=data.get("submission_deadline", ""),
            cycle_id=data.get("cycle_id") or DEFAULT_CYCLE_ID
        )


class PerformanceCycle:
    """Represents a 6-month Cohort Performance Cycle containing badges, mappings, projects, and appraisals."""
    def __init__(
        self,
        id: str,
        name: str,
        code: str = "",
        start_date: str = "2026-07-01",
        end_date: str = "",
        status: str = "active",  # "draft", "active", "evaluating", "closed"
        created_by: str = "guardian_1",
        created_at: str = "",
        closed_at: str = "",
        cloned_from_cycle_id: str = "",
        hike_policy: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ):
        self.id = id
        self.name = name
        self.code = code or id.upper()
        self.start_date = start_date or "2026-07-01"
        self.end_date = end_date or add_six_months_iso(self.start_date, 6)
        self.status = status or "active"
        self.created_by = created_by or "guardian_1"
        self.created_at = created_at or current_iso_timestamp()
        self.closed_at = closed_at or ""
        self.cloned_from_cycle_id = cloned_from_cycle_id or ""
        self.hike_policy = hike_policy if isinstance(hike_policy, dict) else dict(DEFAULT_HIKE_POLICY)
        self.notes = notes or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "closed_at": self.closed_at,
            "cloned_from_cycle_id": self.cloned_from_cycle_id,
            "hike_policy": self.hike_policy,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceCycle":
        policy = data.get("hike_policy") or data.get("hike_policy_json")
        if isinstance(policy, str):
            try:
                policy = json.loads(policy)
            except Exception:
                policy = dict(DEFAULT_HIKE_POLICY)
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            code=data.get("code", ""),
            start_date=data.get("start_date", "2026-07-01"),
            end_date=data.get("end_date", ""),
            status=data.get("status", "active"),
            created_by=data.get("created_by", "guardian_1"),
            created_at=data.get("created_at", ""),
            closed_at=data.get("closed_at", ""),
            cloned_from_cycle_id=data.get("cloned_from_cycle_id", ""),
            hike_policy=policy if isinstance(policy, dict) else dict(DEFAULT_HIKE_POLICY),
            notes=data.get("notes", "")
        )


class CycleEnrollment:
    """Snapshots a user's participation, role, band, and optional base salary within a specific 6-month cycle."""
    def __init__(
        self,
        id: str,
        cycle_id: str,
        user_id: str,
        cycle_role: str = "cosmonaut",
        band_code: str = "B1",
        track_code: str = "SD",
        base_salary: float = 0.0,
        reporting_manager_id: str = "",
        status: str = "active",
        enrolled_at: str = ""
    ):
        self.id = id
        self.cycle_id = cycle_id
        self.user_id = user_id
        self.cycle_role = cycle_role or "cosmonaut"
        self.band_code = band_code or "B1"
        self.track_code = track_code or "SD"
        self.base_salary = float(base_salary or 0.0)
        self.reporting_manager_id = reporting_manager_id or ""
        self.status = status or "active"
        self.enrolled_at = enrolled_at or current_iso_timestamp()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "user_id": self.user_id,
            "cycle_role": self.cycle_role,
            "band_code": self.band_code,
            "track_code": self.track_code,
            "base_salary": self.base_salary,
            "reporting_manager_id": self.reporting_manager_id,
            "status": self.status,
            "enrolled_at": self.enrolled_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CycleEnrollment":
        return cls(
            id=data["id"],
            cycle_id=data["cycle_id"],
            user_id=data["user_id"],
            cycle_role=data.get("cycle_role", "cosmonaut"),
            band_code=data.get("band_code", "B1"),
            track_code=data.get("track_code", "SD"),
            base_salary=float(data.get("base_salary") or 0.0),
            reporting_manager_id=data.get("reporting_manager_id", ""),
            status=data.get("status", "active"),
            enrolled_at=data.get("enrolled_at", "")
        )


class CyclePerformanceAppraisal:
    """Stores end-of-cycle dual-role (Cosmonaut + Reviewer) performance metrics and appraisal/hike outcomes."""
    def __init__(
        self,
        id: str,
        cycle_id: str,
        cosmonaut_id: str,
        band_code: str = "B1",
        badges_assigned: int = 0,
        badges_submitted: int = 0,
        badges_earned: int = 0,
        first_attempt_passes: int = 0,
        total_attempts: int = 0,
        avg_marks: float = 0.0,
        avg_percentage: float = 0.0,
        cosmo_score: float = 0.0,
        badge_reviews_assigned: int = 0,
        badge_reviews_completed: int = 0,
        projects_created: int = 0,
        projects_released: int = 0,
        submissions_assigned_to_review: int = 0,
        submissions_graded: int = 0,
        reviewer_avg_marks_given: float = 0.0,
        reviewer_score: float = 0.0,
        composite_score: float = 0.0,
        performance_tier: str = "Not Assessed",
        base_salary: float = 0.0,
        recommended_hike_pct: float = 0.0,
        approved_hike_pct: float = 0.0,
        hike_amount: float = 0.0,
        new_salary: float = 0.0,
        bonus_amount: float = 0.0,
        recommended_promotion_band: str = "",
        guardian_remarks: str = "",
        status: str = "calculated",
        calculated_at: str = "",
        finalized_by: str = "",
        finalized_at: str = "",
        details: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.cycle_id = cycle_id
        self.cosmonaut_id = cosmonaut_id
        self.band_code = band_code or "B1"
        self.badges_assigned = int(badges_assigned or 0)
        self.badges_submitted = int(badges_submitted or 0)
        self.badges_earned = int(badges_earned or 0)
        self.first_attempt_passes = int(first_attempt_passes or 0)
        self.total_attempts = int(total_attempts or 0)
        self.avg_marks = float(avg_marks or 0.0)
        self.avg_percentage = float(avg_percentage or 0.0)
        self.cosmo_score = float(cosmo_score or 0.0)
        self.badge_reviews_assigned = int(badge_reviews_assigned or 0)
        self.badge_reviews_completed = int(badge_reviews_completed or 0)
        self.projects_created = int(projects_created or 0)
        self.projects_released = int(projects_released or 0)
        self.submissions_assigned_to_review = int(submissions_assigned_to_review or 0)
        self.submissions_graded = int(submissions_graded or 0)
        self.reviewer_avg_marks_given = float(reviewer_avg_marks_given or 0.0)
        self.reviewer_score = float(reviewer_score or 0.0)
        self.composite_score = float(composite_score or 0.0)
        self.performance_tier = performance_tier or "Not Assessed"
        self.base_salary = float(base_salary or 0.0)
        self.recommended_hike_pct = float(recommended_hike_pct or 0.0)
        self.approved_hike_pct = float(approved_hike_pct or 0.0)
        self.hike_amount = float(hike_amount or 0.0)
        self.new_salary = float(new_salary or 0.0)
        self.bonus_amount = float(bonus_amount or 0.0)
        self.recommended_promotion_band = recommended_promotion_band or ""
        self.guardian_remarks = guardian_remarks or ""
        self.status = status or "calculated"
        self.calculated_at = calculated_at or current_iso_timestamp()
        self.finalized_by = finalized_by or ""
        self.finalized_at = finalized_at or ""
        self.details = details if isinstance(details, dict) else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "cosmonaut_id": self.cosmonaut_id,
            "band_code": self.band_code,
            "badges_assigned": self.badges_assigned,
            "badges_submitted": self.badges_submitted,
            "badges_earned": self.badges_earned,
            "first_attempt_passes": self.first_attempt_passes,
            "total_attempts": self.total_attempts,
            "avg_marks": self.avg_marks,
            "avg_percentage": self.avg_percentage,
            "cosmo_score": self.cosmo_score,
            "badge_reviews_assigned": self.badge_reviews_assigned,
            "badge_reviews_completed": self.badge_reviews_completed,
            "projects_created": self.projects_created,
            "projects_released": self.projects_released,
            "submissions_assigned_to_review": self.submissions_assigned_to_review,
            "submissions_graded": self.submissions_graded,
            "reviewer_avg_marks_given": self.reviewer_avg_marks_given,
            "reviewer_score": self.reviewer_score,
            "composite_score": self.composite_score,
            "performance_tier": self.performance_tier,
            "base_salary": self.base_salary,
            "recommended_hike_pct": self.recommended_hike_pct,
            "approved_hike_pct": self.approved_hike_pct,
            "hike_amount": self.hike_amount,
            "new_salary": self.new_salary,
            "bonus_amount": self.bonus_amount,
            "recommended_promotion_band": self.recommended_promotion_band,
            "guardian_remarks": self.guardian_remarks,
            "status": self.status,
            "calculated_at": self.calculated_at,
            "finalized_by": self.finalized_by,
            "finalized_at": self.finalized_at,
            "details": self.details
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CyclePerformanceAppraisal":
        details = data.get("details") or data.get("details_json")
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except Exception:
                details = {}
        return cls(
            id=data["id"],
            cycle_id=data["cycle_id"],
            cosmonaut_id=data.get("cosmonaut_id") or data.get("user_id", ""),
            band_code=data.get("band_code", "B1"),
            badges_assigned=data.get("badges_assigned", 0),
            badges_submitted=data.get("badges_submitted", 0),
            badges_earned=data.get("badges_earned", 0),
            first_attempt_passes=data.get("first_attempt_passes", 0),
            total_attempts=data.get("total_attempts", 0),
            avg_marks=data.get("avg_marks", 0.0),
            avg_percentage=data.get("avg_percentage", 0.0),
            cosmo_score=data.get("cosmo_score", 0.0),
            badge_reviews_assigned=data.get("badge_reviews_assigned", 0),
            badge_reviews_completed=data.get("badge_reviews_completed", 0),
            projects_created=data.get("projects_created", 0),
            projects_released=data.get("projects_released", 0),
            submissions_assigned_to_review=data.get("submissions_assigned_to_review", 0),
            submissions_graded=data.get("submissions_graded", 0),
            reviewer_avg_marks_given=data.get("reviewer_avg_marks_given", 0.0),
            reviewer_score=data.get("reviewer_score", 0.0),
            composite_score=data.get("composite_score", 0.0),
            performance_tier=data.get("performance_tier", "Not Assessed"),
            base_salary=data.get("base_salary", 0.0),
            recommended_hike_pct=data.get("recommended_hike_pct", 0.0),
            approved_hike_pct=data.get("approved_hike_pct", 0.0),
            hike_amount=data.get("hike_amount", 0.0),
            new_salary=data.get("new_salary", 0.0),
            bonus_amount=data.get("bonus_amount", 0.0),
            recommended_promotion_band=data.get("recommended_promotion_band", ""),
            guardian_remarks=data.get("guardian_remarks", ""),
            status=data.get("status", "calculated"),
            calculated_at=data.get("calculated_at", ""),
            finalized_by=data.get("finalized_by", ""),
            finalized_at=data.get("finalized_at", ""),
            details=details if isinstance(details, dict) else {}
        )


