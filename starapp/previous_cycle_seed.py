# -*- coding: utf-8 -*-
"""
Synthetic Historical Dataset Generator for the Previous 6-Month Cycle (`cycle_0`: Jan–Jun 2026).

Provides rich, consistent, relational data across every StarApp Learning stage for existing employees:
- Closed Previous Cycle (`cycle_0`: C0-2026, 2026-01-01 -> 2026-06-30)
- Curriculum Badges across Bands B1–B5 (approved, pending_review, returned) honoring Reviewer_Band > Badge_Band
- Reviewer Badge Assignments & Review Audit Events
- Mapping Requests & Band Mappings with 3-day consecutive review windows
- 9-Point Badge Timelines inside Jan–Jun 2026
- Reviewer Project Specifications (`reviewer_project_prompts`)
- Project Submissions (earned/certified, multi-attempt revisions, reviewer_assessed sign-off queue, retake_required)
- 50-Mark Rubric Assessments (`assessment_marksheets`) from both Reviewer and Guardian
- Deadline Extension Requests, Learning Materials, Announcements, Notifications, Activity Events
- Cycle Enrollments & Finalized Dual-Role Cycle Performance Appraisals (`cycle_performance_appraisals`)
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from starapp.badge_generator import generate_badge_data
from starapp.models import DEFAULT_HIKE_POLICY


PREV_CYCLE_ID = "cycle_0"
PREV_CYCLE_CODE = "C0-2026"
PREV_CYCLE_NAME = "Previous Cycle (Jan–Jun 2026)"
PREV_CYCLE_START = "2026-01-01"
PREV_CYCLE_END = "2026-06-30"
PREV_CYCLE_CLOSED_AT = "2026-06-30T18:00:00Z"


def _mk_prompt_json(band: str, power: str, cap: str, skill: str, title: str, reqs: str) -> str:
    gen = generate_badge_data(band=band, power=power, capability=cap, skill=skill, outcome_sentence="")
    gen["title"] = title
    gen["practice_prompt"] = reqs
    return json.dumps(gen)


def build_previous_cycle_dataset(users_by_id: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Builds the complete cycle_0 synthetic dataset ready for migrate_from_dict() or store injection."""
    users_by_id = users_by_id or {}

    def uname(uid: str, fallback: str) -> str:
        u = users_by_id.get(uid)
        if isinstance(u, dict):
            return u.get("name") or fallback
        return getattr(u, "name", fallback) if u else fallback

    cycle_row = {
        "id": PREV_CYCLE_ID,
        "code": PREV_CYCLE_CODE,
        "name": PREV_CYCLE_NAME,
        "start_date": PREV_CYCLE_START,
        "end_date": PREV_CYCLE_END,
        "status": "closed",
        "created_by": "guardian_1",
        "created_at": "2026-01-01T08:00:00Z",
        "closed_at": PREV_CYCLE_CLOSED_AT,
        "cloned_from_cycle_id": "",
        "hike_policy": dict(DEFAULT_HIKE_POLICY),
        "notes": "Completed H1 2026 Learning & Dual-Role Evaluation Cycle across Bands B1–B5.",
    }

    # Badge catalog specifications (Reviewer_Band strictly > Target_Band)
    badge_specs: List[Dict[str, Any]] = [
        {
            "id": "c0_b1_py", "code": "C0-B1-PY-01", "title": "Python & Backend API Foundations",
            "band": "B1", "power": "Tech", "capability": "Systems & Cloud", "skill": "Architecture",
            "category": "Foundations", "reviewer": "m_b2_1", "wf": "approved", "pub": True, "alloc": True,
            "cadets": ["cosmo_1", "m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5"],
            "created": "2026-01-05T09:00:00Z", "reviewed": "2026-01-08T15:30:00Z", "published": "2026-01-12T10:00:00Z",
            "notes": "Approved for H1 2026 Band B1 cohort onboarding.",
            "rev_dates": ["2026-02-23", "2026-02-24", "2026-02-25"],
            "tl": ("2026-01-12", "2026-01-12", "2026-01-13", "2026-01-25", "2026-01-26", "2026-02-18", "2026-02-20", "2026-02-24", "2026-02-28"),
            "reqs": "1. Build modular FastAPI REST endpoints with validation.\n2. Write unit tests & architecture PDF.\n3. Push clean GitHub repository.",
        },
        {
            "id": "c0_b1_db", "code": "C0-B1-DB-02", "title": "Relational SQL & Schema Design",
            "band": "B1", "power": "Tech", "capability": "Data & Machine", "skill": "Architecture",
            "category": "Core Data", "reviewer": "m_b2_4", "wf": "approved", "pub": True, "alloc": True,
            "cadets": ["cosmo_1", "m_b1_1", "m_b1_2", "m_b1_3", "m_b1_6"],
            "created": "2026-02-01T09:00:00Z", "reviewed": "2026-02-04T14:00:00Z", "published": "2026-02-08T10:00:00Z",
            "notes": "Strong normalization & indexing rubric verified.",
            "rev_dates": ["2026-03-23", "2026-03-24", "2026-03-25"],
            "tl": ("2026-02-08", "2026-02-08", "2026-02-09", "2026-02-22", "2026-02-23", "2026-03-18", "2026-03-20", "2026-03-24", "2026-03-28"),
            "reqs": "1. Model 3NF SQLite/Postgres schema with foreign keys & indexes.\n2. Document query plans in PDF report.\n3. Share repo link.",
        },
        {
            "id": "c0_b2_cur", "code": "C0-B2-CUR-01", "title": "Enterprise Cloud & Data Curation",
            "band": "B2", "power": "Tech", "capability": "Data & Machine", "skill": "Curation",
            "category": "Cloud Systems", "reviewer": "m_b3_1", "wf": "approved", "pub": True, "alloc": True,
            "cadets": ["m_b2_1", "m_b2_2", "m_b2_3", "m_b2_4", "m_b2_5"],
            "created": "2026-01-14T10:00:00Z", "reviewed": "2026-01-18T11:15:00Z", "published": "2026-01-22T09:30:00Z",
            "notes": "Curriculum approved with lineage auditing criteria.",
            "rev_dates": ["2026-03-09", "2026-03-10", "2026-03-11"],
            "tl": ("2026-01-22", "2026-01-22", "2026-01-23", "2026-02-08", "2026-02-09", "2026-03-04", "2026-03-06", "2026-03-10", "2026-03-15"),
            "reqs": "1. Build automated ETL curation job with deduplication.\n2. Deliver Cloud Architecture PDF.\n3. Push tested Python module.",
        },
        {
            "id": "c0_b2_sec", "code": "C0-B2-SEC-02", "title": "Zero-Trust Service Mesh Proposal",
            "band": "B2", "power": "Tech", "capability": "Systems & Cloud", "skill": "Governance",
            "category": "Security", "reviewer": "m_b3_6", "wf": "pending_review", "pub": False, "alloc": False,
            "cadets": [],
            "created": "2026-05-12T10:00:00Z", "reviewed": "", "published": "",
            "notes": "Submitted to Tanvi Shah (Band B3) prior to H1 archive close.",
            "rev_dates": [],
            "tl": ("2026-05-15", "2026-05-15", "2026-05-16", "2026-05-26", "2026-05-27", "2026-06-15", "2026-06-18", "2026-06-22", "2026-06-25"),
            "reqs": "1. Implement mTLS gateway verifier.\n2. Document zero-trust policies.\n3. Publish clean repo.",
        },
        {
            "id": "c0_b3_ing", "code": "C0-B3-ING-01", "title": "Distributed Event Ingestion Engines",
            "band": "B3", "power": "Tech", "capability": "Data & Machine", "skill": "Ingestion",
            "category": "Data Platforms", "reviewer": "m_b4_1", "wf": "approved", "pub": True, "alloc": True,
            "cadets": ["m_b3_1", "m_b3_2", "m_b3_3", "m_b3_4"],
            "created": "2026-02-10T09:00:00Z", "reviewed": "2026-02-13T16:45:00Z", "published": "2026-02-18T11:00:00Z",
            "notes": "Approved with backpressure & dead-letter queue rubric.",
            "rev_dates": ["2026-04-13", "2026-04-14", "2026-04-15"],
            "tl": ("2026-02-18", "2026-02-18", "2026-02-19", "2026-03-10", "2026-03-11", "2026-04-08", "2026-04-10", "2026-04-14", "2026-04-18"),
            "reqs": "1. Build idempotent event ingestion pipeline with DLQ.\n2. Author throughput benchmark PDF.\n3. Submit GitHub link.",
        },
        {
            "id": "c0_b3_ret", "code": "C0-B3-RET-02", "title": "Multi-Region Fault Recovery",
            "band": "B3", "power": "Tech", "capability": "Systems & Cloud", "skill": "Architecture",
            "category": "Reliability", "reviewer": "m_b4_2", "wf": "returned", "pub": False, "alloc": False,
            "cadets": [],
            "created": "2026-04-04T09:00:00Z", "reviewed": "2026-04-07T14:20:00Z", "published": "",
            "notes": "Returned by Shalini Desai (Band B4): Add RPO/RTO chaos drill metrics to rubric criteria.",
            "rev_dates": [],
            "tl": ("2026-04-10", "2026-04-10", "2026-04-11", "2026-04-20", "2026-04-21", "2026-05-10", "2026-05-12", "2026-05-15", "2026-05-18"),
            "reqs": "1. Simulate multi-region failover.\n2. Measure RPO/RTO benchmarks.",
        },
        {
            "id": "c0_b4_aios", "code": "C0-B4-AIOS-01", "title": "Enterprise AI-OS & Telemetry",
            "band": "B4", "power": "Tech", "capability": "Intelligent Apps", "skill": "AI-OS",
            "category": "AI Platforms", "reviewer": "m_b5_1", "wf": "approved", "pub": True, "alloc": True,
            "cadets": ["m_b4_1", "m_b4_2", "m_b4_3", "m_b4_4"],
            "created": "2026-03-01T09:00:00Z", "reviewed": "2026-03-04T12:10:00Z", "published": "2026-03-08T10:00:00Z",
            "notes": "Approved for senior B4 AI-OS orchestration cohort.",
            "rev_dates": ["2026-05-04", "2026-05-05", "2026-05-06"],
            "tl": ("2026-03-08", "2026-03-08", "2026-03-09", "2026-03-28", "2026-03-29", "2026-04-28", "2026-04-30", "2026-05-05", "2026-05-10"),
            "reqs": "1. Build policy-enforced AI-OS agent router with telemetry.\n2. Deliver Enterprise Architecture PDF.\n3. Clean repo commit log.",
        },
        {
            "id": "c0_b5_gov", "code": "C0-B5-GOV-01", "title": "Autonomous Governance Frameworks",
            "band": "B5", "power": "Tech", "capability": "Systems & Cloud", "skill": "Governance",
            "category": "Executive Systems", "reviewer": "m_b6_1", "wf": "approved", "pub": True, "alloc": True,
            "cadets": ["m_b5_1", "m_b5_2", "m_b5_3"],
            "created": "2026-03-18T09:00:00Z", "reviewed": "2026-03-21T16:00:00Z", "published": "2026-03-25T10:00:00Z",
            "notes": "Approved by Band B6 Executive Reviewer Devika Narayanan.",
            "rev_dates": ["2026-05-18", "2026-05-19", "2026-05-20"],
            "tl": ("2026-03-25", "2026-03-25", "2026-03-26", "2026-04-15", "2026-04-16", "2026-05-12", "2026-05-15", "2026-05-19", "2026-05-24"),
            "reqs": "1. Implement deterministic RBAC audit engine.\n2. Author compliance architecture brief.\n3. Share repo.",
        },
        {
            "id": "c0_b6_exec", "code": "C0-B6-EXC-01", "title": "Enterprise Strategy & Capital Allocation",
            "band": "B6", "power": "Business", "capability": "Strategy & Scale", "skill": "Architecture",
            "category": "Executive Council", "reviewer": "guardian_1", "wf": "approved", "pub": True, "alloc": True,
            "cadets": ["m_b6_1", "m_b6_2"],
            "created": "2026-04-02T09:00:00Z", "reviewed": "2026-04-05T15:00:00Z", "published": "2026-04-08T10:00:00Z",
            "notes": "Authorized directly by Executive Council (Guardian Arjun Mehta) — Band B6 Executive tier.",
            "rev_dates": ["2026-05-25", "2026-05-26", "2026-05-27"],
            "tl": ("2026-04-08", "2026-04-08", "2026-04-09", "2026-04-26", "2026-04-27", "2026-05-20", "2026-05-22", "2026-05-26", "2026-05-30"),
            "reqs": "1. Model multi-division AI capability investment roadmap.\n2. Deliver Executive Council PDF brief.\n3. Publish strategy repo.",
        },
    ]

    badges: List[Dict[str, Any]] = []
    badge_reviewer_assignments: List[Dict[str, Any]] = []
    badge_review_events: List[Dict[str, Any]] = []
    mapping_requests: List[Dict[str, Any]] = []
    band_mappings: List[Dict[str, Any]] = []
    timelines: List[Dict[str, Any]] = []
    reviewer_projects: List[Dict[str, Any]] = []

    for sp in badge_specs:
        bid = sp["id"]
        t0, t1, t2, t3, t4, t5, t6, t7, t8 = sp["tl"]
        default_tl = {
            "assignment_date": t0, "publication_date": t1,
            "learning_start_date": t2, "learning_end_date": t3,
            "project_start_date": t4, "project_end_date": t5,
            "submission_deadline": t6, "review_date": t7, "expected_award_date": t8,
        }
        badges.append({
            "id": bid,
            "code": sp["code"],
            "title": sp["title"],
            "category": sp["category"],
            "description": f"H1 2026 milestone for Band {sp['band']}: {sp['title']} ({sp['capability']} / {sp['skill']}).",
            "learning_outcomes": [
                f"Design production-grade {sp['skill']} components for Band {sp['band']}",
                f"Satisfy enterprise resilience, observability, and security rubrics",
                f"Present architecture trade-offs in 50-mark peer review",
            ],
            "learning_topics": [sp["skill"], sp["capability"], "System Design", "Observability", "Testing", "Security"],
            "prerequisites": [],
            "project_requirements": sp["reqs"],
            "is_published": sp["pub"],
            "is_allocated": sp["alloc"],
            "target_band": sp["band"],
            "power": sp["power"],
            "capability": sp["capability"],
            "skill": sp["skill"],
            "prompt_json": _mk_prompt_json(sp["band"], sp["power"], sp["capability"], sp["skill"], sp["title"], sp["reqs"]),
            "workflow_status": sp["wf"],
            "creator_id": "guardian_1",
            "assigned_reviewer_id": sp["reviewer"],
            "assigned_cosmonaut_ids": list(sp["cadets"]),
            "default_timeline": default_tl,
            "created_at": sp["created"],
            "updated_at": sp["reviewed"] or sp["created"],
            "passing_percentage": 70.0,
            "published_at": sp["published"],
            "published_by": "guardian_1" if sp["pub"] else "",
            "cycle_id": PREV_CYCLE_ID,
        })

        # Reviewer assignment & review events
        ra_status = "approved" if sp["wf"] == "approved" else ("returned" if sp["wf"] == "returned" else "pending")
        badge_reviewer_assignments.append({
            "id": f"ra_{bid}",
            "badge_id": bid,
            "reviewer_id": sp["reviewer"],
            "assigned_at": sp["created"],
            "review_due_at": t1,
            "status": ra_status,
            "decision_notes": sp["notes"],
            "decided_at": sp["reviewed"] or None,
            "cycle_id": PREV_CYCLE_ID,
        })
        badge_review_events.append({
            "id": f"bre_{bid}_1",
            "badge_id": bid,
            "actor_id": "guardian_1",
            "event_type": "created_for_review",
            "previous_status": None,
            "new_status": "pending_review",
            "notes": f"Assigned to {uname(sp['reviewer'], sp['reviewer'])} for H1 2026 approval.",
            "timestamp": sp["created"],
            "cycle_id": PREV_CYCLE_ID,
        })
        if sp["wf"] in ("approved", "returned"):
            badge_review_events.append({
                "id": f"bre_{bid}_2",
                "badge_id": bid,
                "actor_id": sp["reviewer"],
                "event_type": sp["wf"],
                "previous_status": "pending_review",
                "new_status": sp["wf"],
                "notes": sp["notes"],
                "timestamp": sp["reviewed"],
                "cycle_id": PREV_CYCLE_ID,
            })

        # Mappings & reviewer project prompts for published badges
        if sp["pub"] and sp["cadets"]:
            mr_id = f"mr_{bid}"
            bm_id = f"bm_{bid}"
            rev_id = sp["reviewer"]
            mapping_requests.append({
                "id": mr_id,
                "band": sp["band"],
                "badge": sp["title"],
                "badge_id": bid,
                "reviewer_id": rev_id,
                "reviewer_name": uname(rev_id, rev_id),
                "cosmonauts": list(sp["cadets"]),
                "cosmonaut_names": [uname(cid, cid) for cid in sp["cadets"]],
                "review_dates": sp["rev_dates"],
                "status": "accepted",
                "created_at": sp["created"],
                "responded_at": sp["published"],
                "cycle_id": PREV_CYCLE_ID,
            })
            band_mappings.append({
                "id": bm_id,
                "band": sp["band"],
                "badge": sp["title"],
                "badge_id": bid,
                "cosmonauts": list(sp["cadets"]),
                "cosmonaut_names": [uname(cid, cid) for cid in sp["cadets"]],
                "reviewers": [rev_id],
                "reviewer_names": [uname(rev_id, rev_id)],
                "review_dates": sp["rev_dates"],
                "status": "completed",
                "created_at": sp["published"],
                "cycle_id": PREV_CYCLE_ID,
            })
            reviewer_projects.append({
                "id": f"proj_{bid}_{rev_id}",
                "badge_id": bid,
                "reviewer_id": rev_id,
                "cosmonaut_ids": list(sp["cadets"]),
                "title": f"{sp['title']} — Capstone Delivery Brief",
                "description": (
                    f"Authored by {uname(rev_id, rev_id)} for {sp['title']} (Band {sp['band']} • Cycle C0-2026). "
                    f"Implement the full production solution, benchmark edge cases, and submit code + PDF architecture report."
                ),
                "deliverables": {
                    "code": "Modular Python package + automated unit tests (.py)",
                    "pdf": "Enterprise Architecture & Trade-Off Report (.pdf)",
                    "github": "Clean repository commit history URL",
                },
                "requirements": [line.strip() for line in sp["reqs"].split("\n") if line.strip()],
                "outcomes": [
                    f"Verified {sp['skill']} runtime implementation",
                    "Complete 50-mark architecture defense readiness",
                ],
                "status": "sent",
                "created_at": f"{t3}T10:00:00Z",
                "sent_at": f"{t4}T09:00:00Z",
                "cycle_id": PREV_CYCLE_ID,
            })

    # Submissions & Marksheets across cohorts (certified, multi-attempt, reviewer_assessed, retake_required)
    # (badge_id, cosmo_id, reviewer_id, attempt, status, sub_ts, rev_marks_tuple, guard_marks_tuple, feedback)
    eval_outcomes: List[Tuple[str, str, str, int, str, str, Optional[Tuple[float, ...]], Optional[Tuple[float, ...]], str]] = [
        # Band B1 Python & API Foundations
        ("c0_b1_py", "cosmo_1", "m_b2_1", 1, "approved", "2026-02-19T14:20:00Z", (9.0, 9.0, 9.5, 8.5, 9.0), (9.5, 9.0, 9.5, 9.0, 9.0), "Outstanding API schema validation and test suite."),
        ("c0_b1_py", "m_b1_1", "m_b2_1", 1, "approved", "2026-02-19T15:10:00Z", (9.0, 9.5, 9.0, 9.0, 9.0), (9.5, 9.5, 9.0, 9.0, 9.5), "Excellent FastAPI modular routing and error handling."),
        ("c0_b1_py", "m_b1_2", "m_b2_1", 1, "approved", "2026-02-19T16:40:00Z", (8.5, 9.0, 8.5, 9.0, 8.5), (9.0, 9.0, 8.5, 9.0, 8.5), "Clean architecture report and solid unit coverage."),
        ("c0_b1_py", "m_b1_3", "m_b2_1", 1, "retake_required", "2026-02-16T11:00:00Z", (6.0, 5.5, 6.0, 6.0, 5.5), None, "Missing error boundary tests and incomplete PDF architecture diagram; please revise."),
        ("c0_b1_py", "m_b1_3", "m_b2_1", 2, "approved", "2026-02-20T17:15:00Z", (8.5, 9.0, 9.0, 8.5, 9.0), (9.0, 9.0, 9.0, 8.5, 9.0), "Strong recovery on Attempt #2; all missing test boundaries addressed."),
        ("c0_b1_py", "m_b1_4", "m_b2_1", 1, "approved", "2026-02-20T10:30:00Z", (9.0, 8.5, 9.0, 8.5, 9.0), (9.0, 9.0, 9.0, 8.5, 9.0), "Deterministic request models and clear observability hooks."),
        ("c0_b1_py", "m_b1_5", "m_b2_1", 1, "reviewer_assessed", "2026-02-20T18:05:00Z", (8.0, 8.5, 8.5, 8.0, 8.5), None, "Reviewer assessment complete (41.5/50); queued in Guardian historical sign-off."),
        # Band B1 SQL
        ("c0_b1_db", "cosmo_1", "m_b2_4", 1, "approved", "2026-03-19T11:30:00Z", (9.5, 9.0, 9.0, 9.0, 9.0), (9.5, 9.0, 9.5, 9.0, 9.0), "Clean 3NF normalization with composite index benchmarks."),
        ("c0_b1_db", "m_b1_1", "m_b2_4", 1, "approved", "2026-03-19T13:15:00Z", (9.0, 9.5, 9.5, 9.0, 9.0), (9.5, 9.5, 9.5, 9.0, 9.5), "Top-tier query plan analysis and migration scripts."),
        ("c0_b1_db", "m_b1_2", "m_b2_4", 1, "approved", "2026-03-19T16:10:00Z", (8.5, 8.5, 9.0, 8.5, 8.5), (9.0, 8.5, 9.0, 8.5, 9.0), "Well-structured foreign key constraints and documentation."),
        ("c0_b1_db", "m_b1_6", "m_b2_4", 1, "approved", "2026-03-20T14:50:00Z", (8.5, 9.0, 8.5, 8.0, 8.5), (8.5, 9.0, 8.5, 8.5, 8.5), "Solid transactional integrity and index verification."),
        # Band B2 Curation
        ("c0_b2_cur", "m_b2_1", "m_b3_1", 1, "approved", "2026-03-05T14:00:00Z", (9.5, 9.0, 9.5, 9.0, 9.0), (9.5, 9.5, 9.5, 9.0, 9.5), "Exemplary cloud curation DAG and dual-role leadership."),
        ("c0_b2_cur", "m_b2_2", "m_b3_1", 1, "approved", "2026-03-05T16:20:00Z", (9.0, 9.0, 8.5, 9.0, 8.5), (9.0, 9.0, 9.0, 9.0, 8.5), "Clear lineage schemas and automated contract tests."),
        ("c0_b2_cur", "m_b2_4", "m_b3_1", 1, "approved", "2026-03-06T12:15:00Z", (9.0, 9.0, 9.0, 9.0, 9.0), (9.0, 9.5, 9.0, 9.0, 9.0), "Strong incremental compaction and schema evolution design."),
        # Band B3 Ingestion
        ("c0_b3_ing", "m_b3_1", "m_b4_1", 1, "approved", "2026-04-09T15:00:00Z", (9.0, 9.5, 9.0, 9.0, 9.0), (9.5, 9.5, 9.0, 9.0, 9.0), "Production-ready DLQ ingestion router with zero message loss."),
        ("c0_b3_ing", "m_b3_2", "m_b4_1", 1, "approved", "2026-04-09T17:30:00Z", (8.5, 8.5, 9.0, 8.5, 8.5), (9.0, 8.5, 9.0, 8.5, 8.5), "Well-measured throughput telemetry and retry backoff."),
        ("c0_b3_ing", "m_b3_3", "m_b4_1", 1, "retake_required", "2026-04-10T18:20:00Z", (6.0, 5.5, 6.0, 5.5, 5.5), None, "Dead-letter consumer replay lacks idempotency key; resubmission requested."),
        # Band B4 AI-OS
        ("c0_b4_aios", "m_b4_1", "m_b5_1", 1, "approved", "2026-04-29T15:40:00Z", (9.5, 9.5, 9.5, 9.0, 9.5), (9.5, 9.5, 9.5, 9.5, 9.5), "Distinguished AI-OS policy engine architecture and Q&A defense."),
        ("c0_b4_aios", "m_b4_2", "m_b5_1", 1, "approved", "2026-04-30T11:25:00Z", (9.0, 9.0, 9.0, 9.0, 8.5), (9.0, 9.0, 9.0, 9.0, 9.0), "Resilient telemetry pipeline and crisp trade-off matrix."),
        # Band B5 Governance
        ("c0_b5_gov", "m_b5_1", "m_b6_1", 1, "approved", "2026-05-14T16:10:00Z", (9.5, 9.5, 9.5, 9.5, 9.5), (9.5, 9.5, 9.5, 9.5, 9.5), "Executive benchmark across RBAC isolation and audit lineage."),
        ("c0_b5_gov", "m_b5_2", "m_b6_1", 1, "approved", "2026-05-15T14:00:00Z", (9.0, 9.0, 8.5, 9.0, 9.0), (9.0, 9.0, 9.0, 9.0, 9.0), "Comprehensive compliance matrix and operational runbook."),
        # Band B6 Executive Council
        ("c0_b6_exec", "m_b6_1", "guardian_1", 1, "approved", "2026-05-21T15:30:00Z", None, (9.5, 9.5, 9.5, 9.5, 9.5), "Executive Council approved Band B6 strategy & enterprise capital model."),
        ("c0_b6_exec", "m_b6_2", "guardian_1", 1, "approved", "2026-05-22T11:45:00Z", None, (9.0, 9.0, 9.5, 9.0, 9.0), "Executive Council verified division governance scorecard & roadmap."),
    ]

    pair_final_status: Dict[Tuple[str, str], str] = {}
    pair_award_date: Dict[Tuple[str, str], str] = {}
    submissions: List[Dict[str, Any]] = []
    assessments: List[Dict[str, Any]] = []

    for bid, cid, rev_id, att, status, sub_ts, rev_m, grd_m, fb in eval_outcomes:
        sub_id = f"sub_{bid}_{cid}_a{att}"
        c_slug = cid.replace("_", "")
        submissions.append({
            "id": sub_id,
            "badge_id": bid,
            "cosmonaut_id": cid,
            "attempt_number": att,
            "submission_type": "bundle",
            "payload": f"https://github.com/starapp-cohort/{bid}-{c_slug}",
            "file_name": f"{bid}_{c_slug}_architecture_v{att}.pdf",
            "submitted_at": sub_ts,
            "status": status,
            "pdf_name": f"{bid}_{c_slug}_architecture_v{att}.pdf",
            "pdf_payload": f"PDF Architecture Report — {bid} Attempt {att} by {uname(cid, cid)}",
            "code_name": f"{bid}_{c_slug}_v{att}.py",
            "code_payload": f"# {bid} solution for {uname(cid, cid)} (Attempt {att})\ndef run_pipeline():\n    return {{'status': 'ok', 'attempt': {att}}}\n",
            "github_url": f"https://github.com/starapp-cohort/{bid}-{c_slug}",
            "cycle_id": PREV_CYCLE_ID,
        })
        pair_final_status[(bid, cid)] = "completed" if status == "approved" else "active"
        if status == "approved":
            pair_award_date[(bid, cid)] = sub_ts[:10]

        if rev_m:
            r_tot = round(sum(rev_m), 2)
            r_pct = round((r_tot / 50.0) * 100.0, 1)
            r_dec = "approve" if r_tot >= 35.0 else "request_revision"
            assessments.append({
                "id": f"asm_{sub_id}_rev",
                "submission_id": sub_id,
                "attempt_number": att,
                "badge_id": bid,
                "cosmonaut_id": cid,
                "reviewer_id": rev_id,
                "reviewer_name": uname(rev_id, rev_id),
                "reviewed_at": sub_ts.replace("T", "T")[:10] + "T19:00:00Z",
                "decision": r_dec,
                "business_understanding": rev_m[0],
                "architecture_report": rev_m[1],
                "technical_knowledge": rev_m[2],
                "presentation": rev_m[3],
                "qa": rev_m[4],
                "total_marks": r_tot,
                "percentage": r_pct,
                "strength_areas": "Modular system design and structured technical explanation." if r_tot >= 35 else "Core problem understanding.",
                "improvement_areas": "Minor benchmark docs." if r_tot >= 35 else "Complete unit tests & PDF diagrams.",
                "overall_feedback": fb,
                "assessor_role": "reviewer",
                "remarks": fb,
                "cycle_id": PREV_CYCLE_ID,
            })

        if grd_m:
            g_tot = round(sum(grd_m), 2)
            g_pct = round((g_tot / 50.0) * 100.0, 1)
            assessments.append({
                "id": f"asm_{sub_id}_grd",
                "submission_id": sub_id,
                "attempt_number": att,
                "badge_id": bid,
                "cosmonaut_id": cid,
                "reviewer_id": "guardian_1",
                "reviewer_name": uname("guardian_1", "Arjun Mehta"),
                "reviewed_at": sub_ts[:10] + "T20:30:00Z",
                "decision": "approve",
                "business_understanding": grd_m[0],
                "architecture_report": grd_m[1],
                "technical_knowledge": grd_m[2],
                "presentation": grd_m[3],
                "qa": grd_m[4],
                "total_marks": g_tot,
                "percentage": g_pct,
                "strength_areas": "Verified production quality matching Band expectations.",
                "improvement_areas": "Continue mentoring lower-band cadets.",
                "overall_feedback": f"Guardian Approved: {fb}",
                "assessor_role": "guardian",
                "remarks": fb,
                "cycle_id": PREV_CYCLE_ID,
            })

    # Build 9-point timelines for every mapped (badge, cadet) pair
    for sp in badge_specs:
        if not sp["pub"] or not sp["cadets"]:
            continue
        t0, t1, t2, t3, t4, t5, t6, t7, t8 = sp["tl"]
        for cid in sp["cadets"]:
            st = pair_final_status.get((sp["id"], cid), "completed")
            aw = pair_award_date.get((sp["id"], cid), t8 if st == "completed" else None)
            timelines.append({
                "badge_id": sp["id"],
                "cosmonaut_id": cid,
                "assignment_date": t0,
                "publication_date": t1,
                "learning_start_date": t2,
                "learning_end_date": t3,
                "project_start_date": t4,
                "project_end_date": t5,
                "submission_deadline": t6,
                "review_date": t7,
                "expected_award_date": t8,
                "actual_award_date": aw,
                "status": st,
                "reviewer_id": sp["reviewer"],
                "review_window_json": json.dumps(sp["rev_dates"]),
                "cycle_id": PREV_CYCLE_ID,
            })

    extensions = [
        {
            "id": "ext_c0_1", "badge_id": "c0_b1_py", "cosmonaut_id": "m_b1_3",
            "current_deadline": "2026-02-20", "proposed_deadline": "2026-02-23",
            "reason": "Needed 3 extra days to add unit tests after Attempt #1 revision feedback.",
            "requested_at": "2026-02-17T10:00:00Z", "status": "approved",
            "guardian_response": "Approved — Attempt #2 completed & passed cleanly (44.5/50).",
            "decided_at": "2026-02-17T16:00:00Z", "cycle_id": PREV_CYCLE_ID,
        },
        {
            "id": "ext_c0_2", "badge_id": "c0_b2_cur", "cosmonaut_id": "m_b2_5",
            "current_deadline": "2026-03-06", "proposed_deadline": "2026-03-14",
            "reason": "Cross-team production release duty overlapped curation window.",
            "requested_at": "2026-03-04T09:15:00Z", "status": "approved",
            "guardian_response": "Approved 8-day window shift for sprint coverage.",
            "decided_at": "2026-03-04T14:10:00Z", "cycle_id": PREV_CYCLE_ID,
        },
        {
            "id": "ext_c0_3", "badge_id": "c0_b3_ing", "cosmonaut_id": "m_b3_3",
            "current_deadline": "2026-04-10", "proposed_deadline": "2026-04-28",
            "reason": "Requesting extended deferral past H1 cohort window.",
            "requested_at": "2026-04-11T11:00:00Z", "status": "rejected",
            "guardian_response": "Rejected: please address Attempt #1 DLQ idempotency fixes within sprint.",
            "decided_at": "2026-04-11T17:00:00Z", "cycle_id": PREV_CYCLE_ID,
        },
    ]

    materials = [
        {
            "id": "mat_c0_1", "badge_id": "c0_b1_py", "topic": "Architecture",
            "title": "FastAPI Modular Design Patterns (H1 2026 Guide)",
            "description": "Guide covering Pydantic schemas, router separation, and repository abstraction.",
            "material_type": "pdf", "url_or_data": "https://starapp.internal/h1-2026/fastapi-patterns.pdf",
            "upload_date": "2026-01-13", "cycle_id": PREV_CYCLE_ID,
        },
        {
            "id": "mat_c0_2", "badge_id": "c0_b3_ing", "topic": "Ingestion",
            "title": "Backpressure & Dead-Letter Replay Walkthrough",
            "description": "Recorded technical session covering idempotent DLQ consumer replay.",
            "material_type": "video", "url_or_data": "https://starapp.internal/h1-2026/dlq-walkthrough",
            "upload_date": "2026-02-20", "cycle_id": PREV_CYCLE_ID,
        },
    ]

    announcements = [
        {
            "id": "ann_c0_1",
            "title": "H1 2026 Previous Cycle Closed & Appraisals Archived",
            "message": "Previous Cycle (Jan–Jun 2026) badges, evaluations, and dual-role performance appraisals are archived.",
            "published_at": "2026-06-30T17:00:00Z", "author_id": "guardian_1", "author_name": "Arjun Mehta",
            "target_type": "all", "target_cosmonaut_ids": ["cosmo_1", "m_b1_1", "m_b2_1", "m_b3_1"],
            "badge_id": "c0_b1_py", "read_by_cosmonaut_ids": ["cosmo_1"], "cycle_id": PREV_CYCLE_ID,
        }
    ]

    # Build comprehensive stage-by-stage, band-level & person-level audit activity_events
    activities = []
    for sp in badge_specs:
        bid = sp["id"]
        activities.append({
            "id": f"act_c0_crt_{bid}", "timestamp": sp["created"], "event_type": "badge_created",
            "actor_id": "guardian_1", "actor_name": uname("guardian_1", "Arjun Mehta"),
            "cosmonaut_id": "", "badge_id": bid,
            "summary": f"Created {sp['code']}: {sp['title']} (Band {sp['band']}).",
            "details": f"Assigned Reviewer: {uname(sp['reviewer'], sp['reviewer'])} ({sp['wf']}).", "cycle_id": PREV_CYCLE_ID,
        })
        if sp["wf"] == "approved":
            activities.append({
                "id": f"act_c0_app_{bid}", "timestamp": sp["reviewed"] or sp["created"], "event_type": "badge_approved",
                "actor_id": sp["reviewer"], "actor_name": uname(sp["reviewer"], sp['reviewer']),
                "cosmonaut_id": "", "badge_id": bid,
                "summary": f"Approved badge {sp['code']} ({sp['title']}) for Band {sp['band']}.",
                "details": sp["notes"], "cycle_id": PREV_CYCLE_ID,
            })
        elif sp["wf"] == "returned":
            activities.append({
                "id": f"act_c0_ret_{bid}", "timestamp": sp["reviewed"] or sp["created"], "event_type": "badge_returned",
                "actor_id": sp["reviewer"], "actor_name": uname(sp["reviewer"], sp['reviewer']),
                "cosmonaut_id": "", "badge_id": bid,
                "summary": f"Returned badge {sp['code']} ({sp['title']}) with feedback.",
                "details": sp["notes"], "cycle_id": PREV_CYCLE_ID,
            })
        if sp["pub"] and sp["cadets"]:
            activities.append({
                "id": f"act_c0_map_{bid}", "timestamp": sp["published"], "event_type": "badge_mapped",
                "actor_id": "guardian_1", "actor_name": uname("guardian_1", "Arjun Mehta"),
                "cosmonaut_id": "", "badge_id": bid,
                "summary": f"Mapped {len(sp['cadets'])} Band {sp['band']} employees to {sp['code']} with {uname(sp['reviewer'], sp['reviewer'])}.",
                "details": f"Review dates: {', '.join(sp['rev_dates'])}", "cycle_id": PREV_CYCLE_ID,
            })
            activities.append({
                "id": f"act_c0_pub_{bid}", "timestamp": sp["published"], "event_type": "badge_published",
                "actor_id": "guardian_1", "actor_name": uname("guardian_1", "Arjun Mehta"),
                "cosmonaut_id": "", "badge_id": bid,
                "summary": f"Published H1 2026 Band {sp['band']} badge '{sp['title']}'.",
                "details": f"Assigned Reviewer: {uname(sp['reviewer'], sp['reviewer'])}.", "cycle_id": PREV_CYCLE_ID,
            })
            for cid in sp["cadets"]:
                activities.append({
                    "id": f"act_c0_mc_{bid}_{cid}", "timestamp": sp["published"], "event_type": "cadet_mapped_to_badge",
                    "actor_id": "guardian_1", "actor_name": uname("guardian_1", "Arjun Mehta"),
                    "cosmonaut_id": cid, "badge_id": bid,
                    "summary": f"Mapped {uname(cid, cid)} ({cid}) to {sp['code']} (Band {sp['band']}).",
                    "details": f"Reviewer: {uname(sp['reviewer'], sp['reviewer'])}.", "cycle_id": PREV_CYCLE_ID,
                })
                activities.append({
                    "id": f"act_c0_pa_{bid}_{cid}", "timestamp": f"{sp['tl'][4]}T09:00:00Z", "event_type": "reviewer_project_assigned",
                    "actor_id": sp["reviewer"], "actor_name": uname(sp["reviewer"], sp['reviewer']),
                    "cosmonaut_id": cid, "badge_id": bid,
                    "summary": f"Project Assigned for {sp['code']} to {uname(cid, cid)}.",
                    "details": f"Authored by {uname(sp['reviewer'], sp['reviewer'])}.", "cycle_id": PREV_CYCLE_ID,
                })

    for bid, cid, rev_id, att, status, sub_ts, rev_m, grd_m, fb in eval_outcomes:
        activities.append({
            "id": f"act_c0_sub_{bid}_{cid}_a{att}", "timestamp": sub_ts, "event_type": "project_submitted",
            "actor_id": cid, "actor_name": uname(cid, cid),
            "cosmonaut_id": cid, "badge_id": bid,
            "summary": f"{uname(cid, cid)} submitted {bid} deliverables (Attempt #{att}).",
            "details": fb, "cycle_id": PREV_CYCLE_ID,
        })
        if rev_m:
            r_tot = round(sum(rev_m), 1)
            activities.append({
                "id": f"act_c0_reval_{bid}_{cid}_a{att}", "timestamp": f"{sub_ts[:10]}T19:00:00Z", "event_type": "reviewer_assessment_completed",
                "actor_id": rev_id, "actor_name": uname(rev_id, rev_id),
                "cosmonaut_id": cid, "badge_id": bid,
                "summary": f"Reviewer {uname(rev_id, rev_id)} graded {uname(cid, cid)} ({r_tot}/50).",
                "details": fb, "cycle_id": PREV_CYCLE_ID,
            })
        if grd_m:
            g_tot = round(sum(grd_m), 1)
            activities.append({
                "id": f"act_c0_awd_{bid}_{cid}_a{att}", "timestamp": f"{sub_ts[:10]}T20:30:00Z", "event_type": "badge_awarded",
                "actor_id": "guardian_1", "actor_name": uname("guardian_1", "Arjun Mehta"),
                "cosmonaut_id": cid, "badge_id": bid,
                "summary": f"Awarded {bid} to {uname(cid, cid)} ({g_tot}/50).",
                "details": fb, "cycle_id": PREV_CYCLE_ID,
            })
        elif status == "retake_required":
            activities.append({
                "id": f"act_c0_rtk_{bid}_{cid}_a{att}", "timestamp": f"{sub_ts[:10]}T19:30:00Z", "event_type": "retake_required",
                "actor_id": rev_id, "actor_name": uname(rev_id, rev_id),
                "cosmonaut_id": cid, "badge_id": bid,
                "summary": f"Retake required for {uname(cid, cid)} on {bid} Attempt #{att}.",
                "details": fb, "cycle_id": PREV_CYCLE_ID,
            })

    for ex in extensions:
        activities.append({
            "id": f"act_c0_{ex['id']}_req", "timestamp": ex["requested_at"], "event_type": "extension_requested",
            "actor_id": ex["cosmonaut_id"], "actor_name": uname(ex["cosmonaut_id"], ex["cosmonaut_id"]),
            "cosmonaut_id": ex["cosmonaut_id"], "badge_id": ex["badge_id"],
            "summary": f"Deadline extension requested for {ex['badge_id']} by {uname(ex['cosmonaut_id'], ex['cosmonaut_id'])}.",
            "details": ex["reason"], "cycle_id": PREV_CYCLE_ID,
        })
        activities.append({
            "id": f"act_c0_{ex['id']}_dec", "timestamp": ex["decided_at"], "event_type": f"extension_{ex['status']}",
            "actor_id": "guardian_1", "actor_name": uname("guardian_1", "Arjun Mehta"),
            "cosmonaut_id": ex["cosmonaut_id"], "badge_id": ex["badge_id"],
            "summary": f"Deadline extension {ex['status']} for {uname(ex['cosmonaut_id'], ex['cosmonaut_id'])}.",
            "details": ex["guardian_response"], "cycle_id": PREV_CYCLE_ID,
        })

    activities.append({
        "id": "act_c0_close", "timestamp": PREV_CYCLE_CLOSED_AT, "event_type": "cycle_closed",
        "actor_id": "guardian_1", "actor_name": uname("guardian_1", "Arjun Mehta"), "cosmonaut_id": "", "badge_id": "",
        "summary": "Finalized & Closed Previous Cycle (Jan–Jun 2026) with dual-role appraisals.",
        "details": "All Bands B1–B6 archived for H1 2026.", "cycle_id": PREV_CYCLE_ID,
    })

    notifications = [
        {
            "id": "notif_c0_1", "recipient_id": "cosmo_1",
            "title": "Previous Cycle Complete: 2 Badges Earned (C0-2026)",
            "message": "Your H1 2026 Learning evaluations for Python API Foundations & Relational SQL are finalized.",
            "created_at": PREV_CYCLE_CLOSED_AT, "is_read": True, "link_section": "c_cycles",
            "event_type": "cycle_finalized", "related_badge_id": "c0_b1_py", "cycle_id": PREV_CYCLE_ID,
        },
        {
            "id": "notif_c0_2", "recipient_id": "m_b2_1",
            "title": "H1 2026 Dual-Role Appraisal Finalized",
            "message": "Evaluated 6 Band B1 submissions and earned Enterprise Cloud & Data Curation.",
            "created_at": PREV_CYCLE_CLOSED_AT, "is_read": False, "link_section": "c_cycles",
            "event_type": "cycle_finalized", "related_badge_id": "c0_b2_cur", "cycle_id": PREV_CYCLE_ID,
        },
    ]

    return {
        "cycle": cycle_row,
        "badges": badges,
        "badge_reviewer_assignments": badge_reviewer_assignments,
        "badge_review_events": badge_review_events,
        "mapping_requests": mapping_requests,
        "band_mappings": band_mappings,
        "timelines": timelines,
        "reviewer_projects": reviewer_projects,
        "submissions": submissions,
        "assessments": assessments,
        "extensions": extensions,
        "materials": materials,
        "announcements": announcements,
        "activities": activities,
        "notifications": notifications,
    }


def merge_previous_cycle_into_seed_dict(seed_data: Dict[str, Any], users_by_id: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Merges cycle_0 synthetic records cleanly into a get_initial_seed_data() snapshot alongside cycle_1."""
    if not users_by_id:
        try:
            from starapp.mapping_data import MEMBERS_MAP
            users_by_id = dict(MEMBERS_MAP)
        except Exception:
            users_by_id = {}
    users_by_id.setdefault("cosmo_1", {"id": "cosmo_1", "name": "Aarav Sharma"})
    users_by_id.setdefault("guardian_1", {"id": "guardian_1", "name": "Arjun Mehta"})

    prev = build_previous_cycle_dataset(users_by_id=users_by_id)
    now_iso = "2026-07-01T08:00:00Z"

    # Explicit cycles: cycle_0 (closed historical) + cycle_1 (active current Jul-Dec 2026)
    seed_data["cycles"] = [
        {
            "id": "cycle_1",
            "code": "C1-2026",
            "name": "Cycle 1 (Jul–Dec 2026)",
            "start_date": "2026-07-01",
            "end_date": "2026-12-31",
            "status": "active",
            "created_by": "guardian_1",
            "created_at": now_iso,
            "closed_at": "",
            "cloned_from_cycle_id": "",
            "hike_policy": dict(DEFAULT_HIKE_POLICY),
            "notes": "Active H2 2026 6-month cohort performance cycle.",
        },
        prev["cycle"],
    ]

    # Ensure existing cycle_1 records carry cycle_id='cycle_1' explicitly
    for key in ("badges", "timelines", "submissions", "assessments", "materials", "extensions", "announcements", "activities", "notifications", "band_mappings"):
        for item in seed_data.get(key, []):
            if not item.get("cycle_id"):
                item["cycle_id"] = "cycle_1"

    # Append cycle_0 records
    for key in (
        "badges", "badge_reviewer_assignments", "badge_review_events",
        "mapping_requests", "band_mappings", "timelines", "reviewer_projects",
        "submissions", "assessments", "extensions", "materials",
        "announcements", "activities", "notifications"
    ):
        seed_data.setdefault(key, [])
        existing_ids = {x.get("id") for x in seed_data[key] if isinstance(x, dict) and x.get("id")}
        for row in prev[key]:
            rid = row.get("id")
            if not rid or rid not in existing_ids:
                seed_data[key].append(row)

    return seed_data


def ensure_previous_cycle_in_store(store: Any, finalize_appraisals: bool = True) -> bool:
    """
    Idempotently seeds `cycle_0` (Previous Cycle Jan–Jun 2026) and its synthetic Learning data
    into SQLite via `store` WITHOUT touching any existing `cycle_1` active records.
    Returns True if newly seeded, False if cycle_0 already exists.
    """
    if store.get_cycle(PREV_CYCLE_ID) and store.get_badge("c0_b6_exec") and len(store.get_all_badges(cycle_id=PREV_CYCLE_ID)) >= 9:
        return False

    users_map = {u.id: u for u in store.get_all_users()}
    prev = build_previous_cycle_dataset(users_by_id=users_map)

    c = store.db.conn
    with c:
        cyc = prev["cycle"]
        c.execute(
            """INSERT OR REPLACE INTO performance_cycles (
                id, code, name, start_date, end_date, status, created_by,
                created_at, closed_at, cloned_from_cycle_id, hike_policy_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cyc["id"], cyc["code"], cyc["name"], cyc["start_date"], cyc["end_date"],
                cyc["status"], cyc["created_by"], cyc["created_at"], cyc["closed_at"],
                cyc["cloned_from_cycle_id"], json.dumps(cyc["hike_policy"]), cyc["notes"]
            )
        )

        # Badges & related tables
        for b in prev["badges"]:
            c.execute(
                """INSERT OR REPLACE INTO badges (
                    id, code, title, category, description,
                    learning_outcomes_json, learning_topics_json, project_requirements,
                    is_published, is_allocated, target_band, power, capability, skill,
                    prompt_json, workflow_status, creator_id, assigned_reviewer_id,
                    assigned_cosmonaut_ids_json, default_timeline_json, created_at, updated_at,
                    passing_percentage, published_at, published_by, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    b["id"], b["code"], b["title"], b["category"], b["description"],
                    json.dumps(b["learning_outcomes"]), json.dumps(b["learning_topics"]), b["project_requirements"],
                    1 if b["is_published"] else 0, 1 if b["is_allocated"] else 0,
                    b["target_band"], b["power"], b["capability"], b["skill"], b["prompt_json"],
                    b["workflow_status"], b["creator_id"], b["assigned_reviewer_id"],
                    json.dumps(b["assigned_cosmonaut_ids"]), json.dumps(b["default_timeline"]),
                    b["created_at"], b["updated_at"], float(b["passing_percentage"]),
                    b["published_at"], b["published_by"], PREV_CYCLE_ID
                )
            )
            c.execute("INSERT OR REPLACE INTO badge_powers (badge_id, power_name) VALUES (?, ?)", (b["id"], b["power"]))
            c.execute("INSERT OR REPLACE INTO badge_capabilities (badge_id, capability_name, is_custom) VALUES (?, ?, 0)", (b["id"], b["capability"]))
            c.execute("INSERT OR REPLACE INTO badge_skills (badge_id, skill_name, is_custom) VALUES (?, ?, 0)", (b["id"], b["skill"]))

        for bra in prev["badge_reviewer_assignments"]:
            c.execute(
                """INSERT OR REPLACE INTO badge_reviewer_assignments (
                    id, badge_id, reviewer_id, assigned_at, review_due_at, status, decision_notes, decided_at, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    bra["id"], bra["badge_id"], bra["reviewer_id"], bra["assigned_at"],
                    bra["review_due_at"], bra["status"], bra["decision_notes"], bra["decided_at"], PREV_CYCLE_ID
                )
            )

        for bre in prev["badge_review_events"]:
            c.execute(
                """INSERT OR REPLACE INTO badge_review_events (
                    id, badge_id, actor_id, event_type, previous_status, new_status, notes, timestamp, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    bre["id"], bre["badge_id"], bre["actor_id"], bre["event_type"],
                    bre["previous_status"], bre["new_status"], bre["notes"], bre["timestamp"], PREV_CYCLE_ID
                )
            )

        for mr in prev["mapping_requests"]:
            c.execute(
                "INSERT OR REPLACE INTO mapping_requests (id, band, reviewer_id, status, data_json, cycle_id) VALUES (?, ?, ?, ?, ?, ?)",
                (mr["id"], mr["band"], mr["reviewer_id"], mr["status"], json.dumps(mr), PREV_CYCLE_ID)
            )

        for bm in prev["band_mappings"]:
            c.execute(
                "INSERT OR REPLACE INTO band_mappings (id, band, badge_id, data_json, cycle_id) VALUES (?, ?, ?, ?, ?)",
                (bm["id"], bm["band"], bm["badge_id"], json.dumps(bm), PREV_CYCLE_ID)
            )

        for tl in prev["timelines"]:
            c.execute(
                """INSERT OR REPLACE INTO badge_timelines (
                    badge_id, cosmonaut_id, assignment_date, publication_date,
                    learning_start_date, learning_end_date, project_start_date, project_end_date,
                    submission_deadline, review_date, expected_award_date, actual_award_date, status,
                    reviewer_id, review_window_json, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tl["badge_id"], tl["cosmonaut_id"], tl["assignment_date"], tl["publication_date"],
                    tl["learning_start_date"], tl["learning_end_date"], tl["project_start_date"], tl["project_end_date"],
                    tl["submission_deadline"], tl["review_date"], tl["expected_award_date"], tl["actual_award_date"],
                    tl["status"], tl["reviewer_id"], tl["review_window_json"], PREV_CYCLE_ID
                )
            )

        for rp in prev["reviewer_projects"]:
            c.execute(
                """INSERT OR REPLACE INTO reviewer_project_prompts (
                    id, badge_id, reviewer_id, cosmonaut_ids_json, title, description,
                    deliverables_json, requirements_text, outcomes_json, status, created_at, sent_at, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rp["id"], rp["badge_id"], rp["reviewer_id"], json.dumps(rp["cosmonaut_ids"]),
                    rp["title"], rp["description"], json.dumps(rp["deliverables"]),
                    json.dumps(rp["requirements"]), json.dumps(rp["outcomes"]),
                    rp["status"], rp["created_at"], rp["sent_at"], PREV_CYCLE_ID
                )
            )

        for s in prev["submissions"]:
            c.execute(
                """INSERT OR REPLACE INTO project_submissions (
                    id, badge_id, cosmonaut_id, attempt_number, submission_type,
                    payload, file_name, submitted_at, status, pdf_name, pdf_payload,
                    code_name, code_payload, github_url, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    s["id"], s["badge_id"], s["cosmonaut_id"], s["attempt_number"], s["submission_type"],
                    s["payload"], s["file_name"], s["submitted_at"], s["status"], s["pdf_name"], s["pdf_payload"],
                    s["code_name"], s["code_payload"], s["github_url"], PREV_CYCLE_ID
                )
            )

        for a in prev["assessments"]:
            c.execute(
                """INSERT OR REPLACE INTO assessment_marksheets (
                    id, submission_id, attempt_number, badge_id, cosmonaut_id,
                    reviewer_id, reviewer_name, reviewed_at, decision,
                    business_understanding, architecture_report, technical_knowledge,
                    presentation, qa, total_marks, percentage,
                    strength_areas, improvement_areas, overall_feedback,
                    assessor_role, remarks, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    a["id"], a["submission_id"], a["attempt_number"], a["badge_id"], a["cosmonaut_id"],
                    a["reviewer_id"], a["reviewer_name"], a["reviewed_at"], a["decision"],
                    a["business_understanding"], a["architecture_report"], a["technical_knowledge"],
                    a["presentation"], a["qa"], a["total_marks"], a["percentage"],
                    a["strength_areas"], a["improvement_areas"], a["overall_feedback"],
                    a["assessor_role"], a["remarks"], PREV_CYCLE_ID
                )
            )

        for ex in prev["extensions"]:
            c.execute(
                """INSERT OR REPLACE INTO deadline_extensions (
                    id, badge_id, cosmonaut_id, current_deadline, proposed_deadline,
                    reason, status, guardian_response, requested_at, decided_at, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ex["id"], ex["badge_id"], ex["cosmonaut_id"], ex["current_deadline"], ex["proposed_deadline"],
                    ex["reason"], ex["status"], ex["guardian_response"], ex["requested_at"], ex["decided_at"], PREV_CYCLE_ID
                )
            )

        for m in prev["materials"]:
            c.execute(
                """INSERT OR REPLACE INTO learning_materials (
                    id, badge_id, topic, title, description, material_type, url_or_data, upload_date, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (m["id"], m["badge_id"], m["topic"], m["title"], m["description"], m["material_type"], m["url_or_data"], m["upload_date"], PREV_CYCLE_ID)
            )

        for ann in prev["announcements"]:
            c.execute(
                """INSERT OR REPLACE INTO announcements (
                    id, title, message, author_id, author_name, target_type, badge_id, published_at, expiry_date, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ann["id"], ann["title"], ann["message"], ann["author_id"], ann["author_name"], ann["target_type"], ann["badge_id"], ann["published_at"], "", PREV_CYCLE_ID)
            )
            for rid in ann.get("target_cosmonaut_ids", []):
                c.execute("INSERT OR IGNORE INTO announcement_recipients (announcement_id, cosmonaut_id) VALUES (?, ?)", (ann["id"], rid))
            for rby in ann.get("read_by_cosmonaut_ids", []):
                c.execute("INSERT OR IGNORE INTO announcement_read_receipts (announcement_id, cosmonaut_id, read_at) VALUES (?, ?, ?)", (ann["id"], rby, PREV_CYCLE_CLOSED_AT))

        for act in prev["activities"]:
            c.execute(
                """INSERT OR REPLACE INTO activity_events (
                    id, timestamp, event_type, actor_id, actor_name, cosmonaut_id, badge_id, summary, details, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (act["id"], act["timestamp"], act["event_type"], act["actor_id"], act["actor_name"], act["cosmonaut_id"], act["badge_id"], act["summary"], act["details"], PREV_CYCLE_ID)
            )

        for n in prev["notifications"]:
            c.execute(
                """INSERT OR REPLACE INTO notifications (
                    id, recipient_id, title, message, link_section, created_at, is_read, event_type, related_badge_id, cycle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (n["id"], n["recipient_id"], n["title"], n["message"], n["link_section"], n["created_at"], 1 if n["is_read"] else 0, n["event_type"], n["related_badge_id"], PREV_CYCLE_ID)
            )

        for u in store.get_all_users():
            c.execute(
                """INSERT OR IGNORE INTO cycle_enrollments (
                    id, cycle_id, user_id, cycle_role, band_code, track_code, base_salary, reporting_manager_id, status, enrolled_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, 'closed', '2026-01-01T08:00:00Z')""",
                (f"enr_{PREV_CYCLE_ID}_{u.id}", PREV_CYCLE_ID, u.id, getattr(u, "role", "cosmonaut") or "cosmonaut", getattr(u, "band", "B1") or "B1", getattr(u, "track_code", "SD") or "SD", getattr(u, "reporting_manager_id", "") or "")
            )

    # Refresh in-memory DataStore from SQLite & finalize cycle_0 dual-role performance appraisals
    store.load_from_dict(store.db.export_to_dict())
    if finalize_appraisals:
        from starapp.cycles import calculate_and_save_cycle_appraisals
        with store.cycle_scope(PREV_CYCLE_ID):
            apps = calculate_and_save_cycle_appraisals(PREV_CYCLE_ID, store, actor_id="guardian_1", preserve_manual_overrides=True)
            for app_obj in apps:
                app_obj.status = "finalized"
                app_obj.finalized_by = "guardian_1"
                app_obj.finalized_at = PREV_CYCLE_CLOSED_AT
                store.save_cycle_appraisal(app_obj)
        store.load_from_dict(store.db.export_to_dict())
    store.mark_dirty()
    return True
