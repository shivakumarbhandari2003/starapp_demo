"""
STARAPP SHARED DATA MODELS
Defines the unified data structures shared by Guardian and Cosmonaut portals.
All models serialize to/from clean JSON-compatible dictionaries.
"""

from typing import List, Dict, Any, Optional
import datetime

def current_iso_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

class User:
    def __init__(self, id: str, username: str, email: str, role: str, name: str, avatar: str = ""):
        self.id = id
        self.username = username
        self.email = email
        self.role = role  # "guardian" or "cosmonaut"
        self.name = name
        self.avatar = avatar or name[:2].upper()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "name": self.name,
            "avatar": self.avatar
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            id=data["id"],
            username=data.get("username", ""),
            email=data["email"],
            role=data["role"],
            name=data["name"],
            avatar=data.get("avatar", "")
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
        default_timeline: Optional[Dict[str, str]] = None
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
            "default_timeline": self.default_timeline
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
            default_timeline=data.get("default_timeline", {})
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
        status: str = "active"  # upcoming, active, completed, overdue, awaiting_review
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
            "status": self.status
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
            status=data.get("status", "active")
        )


class ProjectSubmission:
    def __init__(
        self,
        id: str,
        badge_id: str,
        cosmonaut_id: str,
        attempt_number: int,
        submission_type: str,  # "pdf", "github", "code"
        payload: str,          # file dataUrl or github url or code text
        file_name: str,
        submitted_at: str,
        status: str = "pending"  # "pending", "approved", "rejected", "resubmission_requested"
    ):
        self.id = id
        self.badge_id = badge_id
        self.cosmonaut_id = cosmonaut_id
        self.attempt_number = attempt_number
        self.submission_type = submission_type
        self.payload = payload
        self.file_name = file_name
        self.submitted_at = submitted_at
        self.status = status

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
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectSubmission":
        return cls(
            id=data["id"],
            badge_id=data["badge_id"],
            cosmonaut_id=data["cosmonaut_id"],
            attempt_number=data.get("attempt_number", 1),
            submission_type=data.get("submission_type", "pdf"),
            payload=data.get("payload", ""),
            file_name=data.get("file_name", ""),
            submitted_at=data.get("submitted_at", current_iso_timestamp()),
            status=data.get("status", "pending")
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
        overall_feedback: str
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
            "overall_feedback": self.overall_feedback
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
            reviewer_name=data.get("reviewer_name", "Dr. Elena Vance"),
            reviewed_at=data.get("reviewed_at", current_iso_timestamp()),
            decision=data.get("decision", "approve"),
            business_understanding=data.get("business_understanding", 0),
            architecture_report=data.get("architecture_report", 0),
            technical_knowledge=data.get("technical_knowledge", 0),
            presentation=data.get("presentation", 0),
            qa=data.get("qa", 0),
            strength_areas=data.get("strength_areas", ""),
            improvement_areas=data.get("improvement_areas", ""),
            overall_feedback=data.get("overall_feedback", "")
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
        upload_date: str
    ):
        self.id = id
        self.badge_id = badge_id
        self.topic = topic
        self.title = title
        self.description = description
        self.material_type = material_type
        self.url_or_data = url_or_data
        self.upload_date = upload_date

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "badge_id": self.badge_id,
            "topic": self.topic,
            "title": self.title,
            "description": self.description,
            "material_type": self.material_type,
            "url_or_data": self.url_or_data,
            "upload_date": self.upload_date
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
            upload_date=data.get("upload_date", current_iso_timestamp())
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
        decided_at: str = ""
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
            "decided_at": self.decided_at
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
            decided_at=data.get("decided_at", "")
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
        read_by_cosmonaut_ids: Optional[List[str]] = None
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
            "read_by_cosmonaut_ids": self.read_by_cosmonaut_ids
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Announcement":
        return cls(
            id=data["id"],
            title=data["title"],
            message=data["message"],
            author_id=data.get("author_id", "guardian_1"),
            author_name=data.get("author_name", "Dr. Elena Vance"),
            target_type=data.get("target_type", "all"),
            target_cosmonaut_ids=data.get("target_cosmonaut_ids", []),
            badge_id=data.get("badge_id", ""),
            published_at=data.get("published_at", ""),
            expiry_date=data.get("expiry_date", ""),
            read_by_cosmonaut_ids=data.get("read_by_cosmonaut_ids", [])
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
        details: str = ""
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
            "details": self.details
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
            details=data.get("details", "")
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
        is_read: bool = False
    ):
        self.id = id
        self.recipient_id = recipient_id
        self.title = title
        self.message = message
        self.link_section = link_section
        self.created_at = created_at or current_iso_timestamp()
        self.is_read = is_read

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "title": self.title,
            "message": self.message,
            "link_section": self.link_section,
            "created_at": self.created_at,
            "is_read": self.is_read
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
            is_read=data.get("is_read", False)
        )

