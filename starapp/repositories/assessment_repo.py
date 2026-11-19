"""
STARAPP ASSESSMENT REPOSITORY
Encapsulates all SQLite queries for Project Submissions, Attempts, and Marksheets.
"""

from typing import List, Optional
from starapp.repositories.base import BaseRepository
from starapp.models import ProjectSubmission, AssessmentMarksheet

class AssessmentRepository(BaseRepository):
    def get_submission_by_id(self, sub_id: str) -> Optional[ProjectSubmission]:
        row = self.fetchone("SELECT * FROM project_submissions WHERE id = ?", (sub_id,))
        if not row:
            return None
        return ProjectSubmission.from_dict(row)

    def get_submissions_by_cosmonaut(self, cosmonaut_id: str) -> List[ProjectSubmission]:
        rows = self.fetchall("SELECT * FROM project_submissions WHERE cosmonaut_id = ? ORDER BY submitted_at DESC", (cosmonaut_id,))
        return [ProjectSubmission.from_dict(r) for r in rows]

    def get_submissions_by_badge(self, badge_id: str) -> List[ProjectSubmission]:
        rows = self.fetchall("SELECT * FROM project_submissions WHERE badge_id = ? ORDER BY submitted_at DESC", (badge_id,))
        return [ProjectSubmission.from_dict(r) for r in rows]

    def save_submission(self, sub: ProjectSubmission):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO project_submissions (
                    id, badge_id, cosmonaut_id, attempt_number,
                    submission_type, payload, file_name, submitted_at, status,
                    pdf_name, pdf_payload, code_name, code_payload, github_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sub.id,
                    sub.badge_id,
                    sub.cosmonaut_id,
                    sub.attempt_number,
                    sub.submission_type,
                    sub.payload,
                    sub.file_name,
                    sub.submitted_at,
                    sub.status,
                    getattr(sub, "pdf_name", ""),
                    getattr(sub, "pdf_payload", ""),
                    getattr(sub, "code_name", ""),
                    getattr(sub, "code_payload", ""),
                    getattr(sub, "github_url", "")
                )
            )

    def get_assessment_by_id(self, marksheet_id: str) -> Optional[AssessmentMarksheet]:
        row = self.fetchone("SELECT * FROM assessment_marksheets WHERE id = ?", (marksheet_id,))
        if not row:
            return None
        return AssessmentMarksheet.from_dict(row)

    def get_assessment_for_submission(self, sub_id: str, attempt_num: int = 1) -> Optional[AssessmentMarksheet]:
        row = self.fetchone("SELECT * FROM assessment_marksheets WHERE submission_id = ? AND attempt_number = ?", (sub_id, attempt_num))
        if not row:
            return None
        return AssessmentMarksheet.from_dict(row)

    def get_all_assessments(self) -> List[AssessmentMarksheet]:
        rows = self.fetchall("SELECT * FROM assessment_marksheets ORDER BY reviewed_at DESC")
        return [AssessmentMarksheet.from_dict(r) for r in rows]

    def save_assessment(self, sheet: AssessmentMarksheet):
        if not self.conn:
            return
        with self.conn:
            self.execute(
                """
                INSERT OR REPLACE INTO assessment_marksheets (
                    id, submission_id, attempt_number, badge_id, cosmonaut_id,
                    reviewer_id, reviewer_name, reviewed_at, decision,
                    business_understanding, architecture_report, technical_knowledge,
                    presentation, qa, total_marks, percentage,
                    strength_areas, improvement_areas, overall_feedback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sheet.id,
                    sheet.submission_id,
                    sheet.attempt_number,
                    sheet.badge_id,
                    sheet.cosmonaut_id,
                    sheet.reviewer_id,
                    sheet.reviewer_name,
                    sheet.reviewed_at,
                    sheet.decision,
                    sheet.business_understanding,
                    sheet.architecture_report,
                    sheet.technical_knowledge,
                    sheet.presentation,
                    sheet.qa,
                    sheet.total_marks,
                    sheet.percentage,
                    sheet.strength_areas,
                    sheet.improvement_areas,
                    sheet.overall_feedback
                )
            )
