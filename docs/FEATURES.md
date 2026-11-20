# COMPLETE FEATURE INVENTORY

This document catalogs all 48+ functional features discovered in the StarApp repository across all user roles.

---

## Feature Matrix

| ID | Feature Name | Primary Role | Implementation Files | Database Tables | Status |
|:---|:---|:---|:---|:---|:---|
| **F01** | User Authentication & Session | All | `app.py`, `models.py`, `database.py` | `users`, `employees` | Baseline |
| **F02** | Role Switching (Guardian / Cosmonaut / Reviewer) | All | `app.py`, `index.html` | `users` | Baseline |
| **F03** | Demo Persona Quick-Switch (Ananya B1, Nisha B2, Tanvi B3) | All | `app.py`, `index.html` | `users`, `employees` | Baseline |
| **F04** | Corporate Hierarchy (36 Members across B1-B6 + CEO) | Guardian | `database.py`, `models.py` | `employees`, `bands`, `tracks` | Baseline |
| **F05** | Band Cards Navigation & Workspace | Guardian | `views_guardian.py`, `app.py` | `bands` | Baseline |
| **F06** | Cascading Dropdowns (Power → Capability → Skill) | Guardian | `views_guardian.py`, `app.py` | `capabilities`, `skills`, `powers` | Baseline |
| **F07** | Custom Capability & Skill Addition | Guardian | `app.py`, `database.py` | `capabilities`, `skills` | Baseline |
| **F08** | JSON Prompt Editor & Auto-Fill | Guardian | `views_guardian.py`, `app.py` | - | Baseline |
| **F09** | AI Badge Generation (Gemini API) | Guardian | `app.py`, `index.html` | - | Baseline |
| **F10** | Badge Creation & 6 Accordion Cards | Guardian | `views_guardian.py`, `app.py` | `badges`, `badge_criteria` | Baseline |
| **F11** | Badge Deduplication in Same Band | Guardian | `app.py`, `database.py` | `badges` | Baseline |
| **F12** | Higher-Band Reviewer Selection ($Reviewer_{Band} > Badge_{Band}$) | Guardian | `app.py`, `database.py` | `employees`, `bands` | Baseline |
| **F13** | Review Request Dispatch & Status Tracking | Guardian | `app.py`, `database.py` | `badge_review_requests` | Baseline |
| **F14** | Reviewer Inbox & Notification Badge | Reviewer | `views_cosmonaut.py`, `app.py` | `badge_review_requests` | Baseline |
| **F15** | Reviewer Badge Inspection & Inline Editor | Reviewer | `views_guardian.py`, `app.py` | `badges`, `badge_criteria` | Baseline |
| **F16** | Badge Approval / Rejection Workflow | Reviewer | `app.py`, `database.py` | `badges`, `badge_review_requests` | Baseline |
| **F17** | Badge Allotment to Cosmonauts | Guardian | `app.py`, `views_guardian.py` | `badge_allotments` | Baseline |
| **F18** | Candy Crush Style Interactive Roadmap (B1-B6) | Cosmonaut | `views_cosmonaut.py`, `app.py` | `badges`, `badge_allotments` | Baseline |
| **F19** | Prerequisite Graph & Sequential Unlocking | Cosmonaut | `app.py`, `models.py` | `badge_prerequisites` | Baseline |
| **F20** | Badge Lifecycle Timeline (6 Milestones) | Cosmonaut | `views_cosmonaut.py`, `app.py` | `badge_allotments` | Baseline |
| **F21** | Project Submission Drawer (GitHub URL / File Upload) | Cosmonaut | `views_cosmonaut.py`, `app.py` | `submissions` | Baseline |
| **F22** | Multi-Attempt Submission History Retention | Cosmonaut | `app.py`, `database.py` | `submissions` | Baseline |
| **F23** | 5-Criterion, 50-Mark Rubric Evaluation | Reviewer/Guardian | `views_guardian.py`, `app.py` | `evaluations`, `evaluation_marks` | Baseline |
| **F24** | Marksheet & Scorecard Rendering | Cosmonaut | `views_cosmonaut.py`, `app.py` | `evaluations`, `evaluation_marks` | Baseline |
| **F25** | Resubmission Request & Workflow | Guardian | `app.py`, `database.py` | `submissions`, `evaluations` | Baseline |
| **F26** | Deadline Extension Request & Approval | Cosmonaut/Guardian | `app.py`, `database.py` | `extension_requests` | Baseline |
| **F27** | Broadcast Announcements & Read Receipts | Guardian/Cosmonaut | `views_guardian.py`, `app.py` | `announcements`, `announcement_reads` | Baseline |
| **F28** | Learning Materials Library & PDF Preview Overlay | Cosmonaut | `views_guardian.py`, `app.py` | `materials` | Baseline |
| **F29** | Private Cadet Dossier & Privacy Protection | Cosmonaut | `app.py`, `views_cosmonaut.py` | `employees` | Baseline |
| **F30** | Batch Leaderboard & Ranking Calculation | Guardian/Cosmonaut | `app.py`, `views_guardian.py` | `evaluations` | Baseline |
| **F31** | AI Mentor Chat & Real-Time Advice | Cosmonaut | `views_cosmonaut.py`, `index.html` | - | Baseline |
| **F32** | Direct Mentor Chat Messaging | Cosmonaut | `views_cosmonaut.py`, `app.py` | `mentor_messages` | Baseline |
| **F33** | Audit Logging & Change History | Guardian | `app.py`, `database.py` | `audit_logs` | Baseline |
| **F34** | Binary Database Export & Import | Guardian | `app.py`, `database.py` | SQLite VFS | Baseline |

---

## Non-Negotiable Business Rules

1. **Reviewer Eligibility Rule:**
   $$\text{Reviewer\_Band} > \text{Badge\_Band}$$
   - Band 1 badges: Reviewable by Bands B2, B3, B4, B5, B6.
   - Band 2 badges: Reviewable by Bands B3, B4, B5, B6.
   - Band 3 badges: Reviewable by Bands B4, B5, B6.
   - Band 4 badges: Reviewable by Bands B5, B6.
   - Band 5 badges: Reviewable only by Band B6.
   - Band 6 badges: Locked out from peer review (reviewed by Committee/CEO).
   *The backend must enforce this rule authoritatively on request dispatch.*

2. **50-Mark Assessment Rubric:**
   - Business Understanding: 0–10 marks
   - Architecture / Report: 0–10 marks
   - Technical Knowledge: 0–10 marks
   - Presentation: 0–10 marks
   - Question & Answering: 0–10 marks
   $$\text{Total} = \sum_{i=1}^{5} \text{Criterion}_i \in [0, 50]$$
   - Pass threshold: $\ge 35/50$ (70%).
