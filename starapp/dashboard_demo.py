"""
STARAPP DASHBOARD DEMONSTRATION DATASET
Provides 5 isolated, fictional Cosmonaut profiles for Guardian dashboard analytics.

STRICT DATA ISOLATION:
These profiles exist ONLY for Guardian dashboard analytics demonstration.
They are NOT actual application users and MUST NOT be added to authentication,
user management, badge assignments, submissions, or non-dashboard pages.
"""

from typing import List, Dict, Any, Optional

DASHBOARD_DEMO_COSMONAUTS: List[Dict[str, Any]] = [
    {
        "id": "demo_orion",
        "name": "Orion Blake",
        "email": "orion.blake@orion.starapp.io",
        "avatar": "OB",
        "batch": "Batch Orion-24",
        "is_demo": True,
        "completed_count": 4,
        "total_assigned": 5,
        "active_badge_id": "badge_sql_201",
        "active_badge_code": "SQL-201",
        "active_badge_title": "Advanced Analytical SQL",
        "upcoming_deadline": "2026-12-15",
        "deadline_status": "On Schedule",
        "last_active": "2026-11-08",
        "days_inactive": 0,
        "last_activity_summary": "Completed SQL query optimization benchmark",
        "risk_status": "On Track",
        "risk_reason": "Progress aligned with roadmap pacing. Excellent code quality across all four cleared milestones.",
        "assessments": [
            {
                "badge_id": "badge_gov_101",
                "badge_code": "GOV-101",
                "badge_title": "Data Governance Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-10-20",
                "business_understanding": 10.0,
                "architecture_report": 9.5,
                "technical_knowledge": 10.0,
                "presentation": 9.5,
                "qa": 10.0,
                "total_marks": 49.0,
                "percentage": 98.0
            },
            {
                "badge_id": "badge_cur_102",
                "badge_code": "CUR-102",
                "badge_title": "Data Curation & Stewardship",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-10-28",
                "business_understanding": 9.5,
                "architecture_report": 9.5,
                "technical_knowledge": 10.0,
                "presentation": 9.5,
                "qa": 9.5,
                "total_marks": 48.0,
                "percentage": 96.0
            },
            {
                "badge_id": "badge_dat_103",
                "badge_code": "DAT-103",
                "badge_title": "In-Memory Datastores",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-02",
                "business_understanding": 9.5,
                "architecture_report": 9.0,
                "technical_knowledge": 9.5,
                "presentation": 9.5,
                "qa": 9.5,
                "total_marks": 47.0,
                "percentage": 94.0
            },
            {
                "badge_id": "badge_ing_104",
                "badge_code": "ING-104",
                "badge_title": "Ingestion Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-06",
                "business_understanding": 9.5,
                "architecture_report": 9.5,
                "technical_knowledge": 10.0,
                "presentation": 9.5,
                "qa": 9.5,
                "total_marks": 48.0,
                "percentage": 96.0
            },
            {
                "id": "asm_demo_orion_sql_201",
                "badge_id": "badge_sql_201",
                "badge_code": "SQL-201",
                "badge_title": "Advanced Analytical SQL",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-08",
                "business_understanding": 10.0,
                "architecture_report": 9.5,
                "technical_knowledge": 10.0,
                "presentation": 9.5,
                "qa": 10.0,
                "total_marks": 49.0,
                "percentage": 98.0
            }
        ],
        "submissions_count": 5,
        "first_attempt_passes": 5,
        "first_attempt_eligible": 5,
        "resubmission_count": 0,
        "average_marks": 48.2,
        "average_percentage": 96.4,
        "standing_tier": "Excellent Performance",
        "skills": [
            {"name": "ReactJS", "category": "Frontend Architecture", "proficiency": "Advanced", "level_color": "#2563EB", "pct": 92, "rating": 9.2, "badge": "DAT-103"},
            {"name": "Nodejs", "category": "Backend Engineering", "proficiency": "Expert", "level_color": "#10B981", "pct": 95, "rating": 9.5, "badge": "ING-104"},
            {"name": "SQL", "category": "Analytical Querying", "proficiency": "Expert", "level_color": "#10B981", "pct": 98, "rating": 9.8, "badge": "SQL-201"},
            {"name": "Python", "category": "Data Engineering", "proficiency": "Expert", "level_color": "#10B981", "pct": 96, "rating": 9.6, "badge": "CUR-102"},
            {"name": "Database", "category": "Storage Systems", "proficiency": "Expert", "level_color": "#10B981", "pct": 97, "rating": 9.7, "badge": "DAT-103"},
            {"name": "Cloud", "category": "Cloud Architecture", "proficiency": "Advanced", "level_color": "#2563EB", "pct": 94, "rating": 9.4, "badge": "GOV-101"}
        ],
        "certifications": [
            {"code": "GOV-101", "title": "Data Governance Foundations", "credential_id": "STAR-CERT-2026-GOV-0112", "issued_at": "2026-10-20", "score": "49.0 / 50.0 (98%)", "honors": "Honors with Distinction"},
            {"code": "CUR-102", "title": "Data Curation & Stewardship", "credential_id": "STAR-CERT-2026-CUR-0125", "issued_at": "2026-10-28", "score": "48.0 / 50.0 (96%)", "honors": "Honors with Distinction"},
            {"code": "DAT-103", "title": "In-Memory Datastores", "credential_id": "STAR-CERT-2026-DAT-0139", "issued_at": "2026-11-02", "score": "47.0 / 50.0 (94%)", "honors": "Certified with Merit"},
            {"code": "ING-104", "title": "Ingestion Foundations", "credential_id": "STAR-CERT-2026-ING-0144", "issued_at": "2026-11-06", "score": "48.0 / 50.0 (96%)", "honors": "Honors with Distinction"}
        ],
        "strengths": [
            "Flawless first-attempt clearance across 4 consecutive milestones with zero resubmissions.",
            "High architectural precision in Kafka consumer group lag monitoring and partition rebalancing.",
            "Clean modular repository structure with automated end-to-end integration test harnesses."
        ],
        "improvements": [
            "Explore cost-based optimization (CBO) spill-to-disk mitigation for multi-way joins in SQL-201.",
            "Document partition pruning benchmarks under high-skew dataset distributions."
        ],
        "mentoring_plan": "Fast-track for Advanced Distributed Systems Honors upon SQL-201 Capstone defense."
    },
    {
        "id": "demo_lyra",
        "name": "Lyra Bennett",
        "email": "lyra.bennett@orion.starapp.io",
        "avatar": "LB",
        "batch": "Batch Orion-24",
        "is_demo": True,
        "completed_count": 3,
        "total_assigned": 5,
        "active_badge_id": "badge_ing_104",
        "active_badge_code": "ING-104",
        "active_badge_title": "Ingestion Foundations",
        "upcoming_deadline": "2026-11-25",
        "deadline_status": "On Schedule",
        "last_active": "2026-11-07",
        "days_inactive": 1,
        "last_activity_summary": "Pushed Kafka partition consumer test suite",
        "risk_status": "On Track",
        "risk_reason": "Three milestone deliverables certified. Ingestion sprint currently on schedule.",
        "assessments": [
            {
                "badge_id": "badge_gov_101",
                "badge_code": "GOV-101",
                "badge_title": "Data Governance Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-10-21",
                "business_understanding": 9.0,
                "architecture_report": 8.5,
                "technical_knowledge": 9.0,
                "presentation": 9.0,
                "qa": 8.5,
                "total_marks": 44.0,
                "percentage": 88.0
            },
            {
                "badge_id": "badge_cur_102",
                "badge_code": "CUR-102",
                "badge_title": "Data Curation & Stewardship",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-10-30",
                "business_understanding": 9.0,
                "architecture_report": 9.0,
                "technical_knowledge": 9.0,
                "presentation": 9.0,
                "qa": 9.0,
                "total_marks": 45.0,
                "percentage": 90.0
            },
            {
                "badge_id": "badge_dat_103",
                "badge_code": "DAT-103",
                "badge_title": "In-Memory Datastores",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-04",
                "business_understanding": 9.5,
                "architecture_report": 9.0,
                "technical_knowledge": 9.5,
                "presentation": 9.0,
                "qa": 9.0,
                "total_marks": 46.0,
                "percentage": 92.0
            },
            {
                "id": "asm_demo_lyra_ing_104",
                "badge_id": "badge_ing_104",
                "badge_code": "ING-104",
                "badge_title": "Ingestion Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-06",
                "business_understanding": 9.0,
                "architecture_report": 9.0,
                "technical_knowledge": 9.0,
                "presentation": 9.0,
                "qa": 9.0,
                "total_marks": 45.0,
                "percentage": 90.0
            },
            {
                "id": "asm_demo_lyra_sql_201",
                "badge_id": "badge_sql_201",
                "badge_code": "SQL-201",
                "badge_title": "Advanced Analytical SQL",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-08",
                "business_understanding": 9.0,
                "architecture_report": 9.5,
                "technical_knowledge": 9.5,
                "presentation": 9.0,
                "qa": 9.0,
                "total_marks": 46.0,
                "percentage": 92.0
            }
        ],
        "submissions_count": 5,
        "first_attempt_passes": 5,
        "first_attempt_eligible": 5,
        "resubmission_count": 0,
        "average_marks": 45.2,
        "average_percentage": 90.4,
        "standing_tier": "Excellent Performance",
        "skills": [
            {"name": "ReactJS", "category": "Frontend Architecture", "proficiency": "Proficient", "level_color": "#3B82F6", "pct": 88, "rating": 8.8, "badge": "DAT-103"},
            {"name": "Nodejs", "category": "Backend Engineering", "proficiency": "Advanced", "level_color": "#2563EB", "pct": 91, "rating": 9.1, "badge": "ING-104"},
            {"name": "SQL", "category": "Analytical Querying", "proficiency": "Advanced", "level_color": "#2563EB", "pct": 92, "rating": 9.2, "badge": "SQL-201"},
            {"name": "Python", "category": "Data Engineering", "proficiency": "Advanced", "level_color": "#2563EB", "pct": 94, "rating": 9.4, "badge": "CUR-102"},
            {"name": "Database", "category": "Storage Systems", "proficiency": "Advanced", "level_color": "#2563EB", "pct": 93, "rating": 9.3, "badge": "DAT-103"},
            {"name": "Cloud", "category": "Cloud Architecture", "proficiency": "Advanced", "level_color": "#2563EB", "pct": 90, "rating": 9.0, "badge": "GOV-101"}
        ],
        "certifications": [
            {"code": "GOV-101", "title": "Data Governance Foundations", "credential_id": "STAR-CERT-2026-GOV-0118", "issued_at": "2026-10-21", "score": "44.0 / 50.0 (88%)", "honors": "Certified with Merit"},
            {"code": "CUR-102", "title": "Data Curation & Stewardship", "credential_id": "STAR-CERT-2026-CUR-0131", "issued_at": "2026-10-30", "score": "45.0 / 50.0 (90%)", "honors": "Certified with Merit"},
            {"code": "DAT-103", "title": "In-Memory Datastores", "credential_id": "STAR-CERT-2026-DAT-0145", "issued_at": "2026-11-04", "score": "46.0 / 50.0 (92%)", "honors": "Honors with Distinction"}
        ],
        "strengths": [
            "Consistent score improvement curve (+2 marks per milestone clearance).",
            "Solid implementation of Redis caching policies and TTL key expiration architectures.",
            "Proactive testing of Kafka partition consumer groups ahead of the milestone target."
        ],
        "improvements": [
            "Strengthen idempotency consumer test coverage to prevent duplicate record processing in ING-104.",
            "Refine architectural diagrams with formal failure recovery sequence flows."
        ],
        "mentoring_plan": "Provide peer review guidance on Kafka idempotent producer configuration before initial submission."
    },
    {
        "id": "demo_cassian",
        "name": "Cassian Reed",
        "email": "cassian.reed@orion.starapp.io",
        "avatar": "CR",
        "batch": "Batch Orion-24",
        "is_demo": True,
        "completed_count": 2,
        "total_assigned": 5,
        "active_badge_id": "badge_dat_103",
        "active_badge_code": "DAT-103",
        "active_badge_title": "In-Memory Datastores",
        "upcoming_deadline": "2026-11-12",
        "deadline_status": "Approaching (3 days)",
        "last_active": "2026-11-05",
        "days_inactive": 3,
        "last_activity_summary": "Viewed Redis eviction policies study guide",
        "risk_status": "Monitor",
        "risk_reason": "Submission velocity slowed over the last week. DAT-103 milestone deadline approaching.",
        "assessments": [
            {
                "badge_id": "badge_gov_101",
                "badge_code": "GOV-101",
                "badge_title": "Data Governance Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-10-23",
                "business_understanding": 8.5,
                "architecture_report": 8.0,
                "technical_knowledge": 8.5,
                "presentation": 8.5,
                "qa": 8.5,
                "total_marks": 42.0,
                "percentage": 84.0
            },
            {
                "badge_id": "badge_cur_102",
                "badge_code": "CUR-102",
                "badge_title": "Data Curation & Stewardship",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-01",
                "business_understanding": 8.5,
                "architecture_report": 8.0,
                "technical_knowledge": 8.0,
                "presentation": 8.5,
                "qa": 8.0,
                "total_marks": 41.0,
                "percentage": 82.0
            },
            {
                "id": "asm_demo_cassian_dat_103",
                "badge_id": "badge_dat_103",
                "badge_code": "DAT-103",
                "badge_title": "In-Memory Datastores",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-05",
                "business_understanding": 8.5,
                "architecture_report": 8.0,
                "technical_knowledge": 8.5,
                "presentation": 8.0,
                "qa": 8.5,
                "total_marks": 41.5,
                "percentage": 83.0
            },
            {
                "id": "asm_demo_cassian_ing_104",
                "badge_id": "badge_ing_104",
                "badge_code": "ING-104",
                "badge_title": "Ingestion Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-07",
                "business_understanding": 8.5,
                "architecture_report": 8.5,
                "technical_knowledge": 8.5,
                "presentation": 8.5,
                "qa": 8.0,
                "total_marks": 42.0,
                "percentage": 84.0
            },
            {
                "id": "asm_demo_cassian_sql_201",
                "badge_id": "badge_sql_201",
                "badge_code": "SQL-201",
                "badge_title": "Advanced Analytical SQL",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-08",
                "business_understanding": 8.0,
                "architecture_report": 8.0,
                "technical_knowledge": 8.5,
                "presentation": 8.5,
                "qa": 8.0,
                "total_marks": 41.0,
                "percentage": 82.0
            }
        ],
        "submissions_count": 5,
        "first_attempt_passes": 5,
        "first_attempt_eligible": 5,
        "resubmission_count": 0,
        "average_marks": 41.5,
        "average_percentage": 83.0,
        "standing_tier": "Strong Performance",
        "skills": [
            {"name": "ReactJS", "category": "Frontend Architecture", "proficiency": "Proficient", "level_color": "#3B82F6", "pct": 85, "rating": 8.5, "badge": "DAT-103"},
            {"name": "Nodejs", "category": "Backend Engineering", "proficiency": "Proficient", "level_color": "#3B82F6", "pct": 86, "rating": 8.6, "badge": "ING-104"},
            {"name": "SQL", "category": "Analytical Querying", "proficiency": "Proficient", "level_color": "#3B82F6", "pct": 88, "rating": 8.8, "badge": "SQL-201"},
            {"name": "Python", "category": "Data Engineering", "proficiency": "Proficient", "level_color": "#3B82F6", "pct": 89, "rating": 8.9, "badge": "CUR-102"},
            {"name": "Database", "category": "Storage Systems", "proficiency": "Proficient", "level_color": "#3B82F6", "pct": 87, "rating": 8.7, "badge": "DAT-103"},
            {"name": "Cloud", "category": "Cloud Architecture", "proficiency": "Proficient", "level_color": "#3B82F6", "pct": 84, "rating": 8.4, "badge": "GOV-101"}
        ],
        "certifications": [
            {"code": "GOV-101", "title": "Data Governance Foundations", "credential_id": "STAR-CERT-2026-GOV-0122", "issued_at": "2026-10-23", "score": "42.0 / 50.0 (84%)", "honors": "Certified with Merit"},
            {"code": "CUR-102", "title": "Data Curation & Stewardship", "credential_id": "STAR-CERT-2026-CUR-0136", "issued_at": "2026-11-01", "score": "41.0 / 50.0 (82%)", "honors": "Certified with Merit"}
        ],
        "strengths": [
            "100% first-attempt clearance on completed milestone deliverables with reliable passing scores.",
            "Comprehensive data governance policy writeups and regulatory audit documentation."
        ],
        "improvements": [
            "Submission velocity has slowed; currently approaching the 3-day deadline window for DAT-103.",
            "Needs deeper study of Redis memory allocation limits under concurrent workload spikes."
        ],
        "mentoring_plan": "Schedule a 15-minute 1-on-1 sprint check-in on DAT-103 Redis architecture to ensure on-time delivery."
    },
    {
        "id": "demo_kaelen",
        "name": "Kaelen Frost",
        "email": "kaelen.frost@orion.starapp.io",
        "avatar": "KF",
        "batch": "Batch Orion-24",
        "is_demo": True,
        "completed_count": 1,
        "total_assigned": 5,
        "active_badge_id": "badge_cur_102",
        "active_badge_code": "CUR-102",
        "active_badge_title": "Data Curation & Stewardship",
        "upcoming_deadline": "2026-11-06",
        "deadline_status": "Overdue (Extension Requested)",
        "last_active": "2026-11-03",
        "days_inactive": 5,
        "last_activity_summary": "Submitted deadline extension request for CUR-102",
        "risk_status": "Needs Attention",
        "risk_reason": "Pending extension request requires Guardian review. Unresolved resubmission on Curation schema.",
        "assessments": [
            {
                "badge_id": "badge_gov_101",
                "badge_code": "GOV-101",
                "badge_title": "Data Governance Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-10-25",
                "business_understanding": 8.0,
                "architecture_report": 7.5,
                "technical_knowledge": 7.5,
                "presentation": 8.0,
                "qa": 7.0,
                "total_marks": 38.0,
                "percentage": 76.0
            },
            {
                "id": "asm_demo_kaelen_cur_102",
                "badge_id": "badge_cur_102",
                "badge_code": "CUR-102",
                "badge_title": "Data Curation & Stewardship",
                "attempt_number": 2,
                "decision": "approve",
                "reviewed_at": "2026-11-04",
                "business_understanding": 8.0,
                "architecture_report": 7.5,
                "technical_knowledge": 8.0,
                "presentation": 8.0,
                "qa": 7.5,
                "total_marks": 39.0,
                "percentage": 78.0
            },
            {
                "id": "asm_demo_kaelen_dat_103",
                "badge_id": "badge_dat_103",
                "badge_code": "DAT-103",
                "badge_title": "In-Memory Datastores",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-06",
                "business_understanding": 8.0,
                "architecture_report": 7.5,
                "technical_knowledge": 7.5,
                "presentation": 8.0,
                "qa": 7.5,
                "total_marks": 38.5,
                "percentage": 77.0
            },
            {
                "id": "asm_demo_kaelen_ing_104",
                "badge_id": "badge_ing_104",
                "badge_code": "ING-104",
                "badge_title": "Ingestion Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-07",
                "business_understanding": 8.0,
                "architecture_report": 8.0,
                "technical_knowledge": 7.5,
                "presentation": 8.0,
                "qa": 7.5,
                "total_marks": 39.0,
                "percentage": 78.0
            },
            {
                "id": "asm_demo_kaelen_sql_201",
                "badge_id": "badge_sql_201",
                "badge_code": "SQL-201",
                "badge_title": "Advanced Analytical SQL",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-08",
                "business_understanding": 7.5,
                "architecture_report": 7.5,
                "technical_knowledge": 8.0,
                "presentation": 7.5,
                "qa": 7.5,
                "total_marks": 38.0,
                "percentage": 76.0
            }
        ],
        "submissions_count": 6,
        "first_attempt_passes": 4,
        "first_attempt_eligible": 5,
        "resubmission_count": 1,
        "average_marks": 38.5,
        "average_percentage": 77.0,
        "standing_tier": "Developing Performance",
        "skills": [
            {"name": "ReactJS", "category": "Frontend Architecture", "proficiency": "Developing", "level_color": "#F59E0B", "pct": 78, "rating": 7.8, "badge": "DAT-103"},
            {"name": "Nodejs", "category": "Backend Engineering", "proficiency": "Developing", "level_color": "#F59E0B", "pct": 80, "rating": 8.0, "badge": "ING-104"},
            {"name": "SQL", "category": "Analytical Querying", "proficiency": "Proficient", "level_color": "#3B82F6", "pct": 82, "rating": 8.2, "badge": "SQL-201"},
            {"name": "Python", "category": "Data Engineering", "proficiency": "Proficient", "level_color": "#3B82F6", "pct": 81, "rating": 8.1, "badge": "CUR-102"},
            {"name": "Database", "category": "Storage Systems", "proficiency": "Developing", "level_color": "#F59E0B", "pct": 79, "rating": 7.9, "badge": "DAT-103"},
            {"name": "Cloud", "category": "Cloud Architecture", "proficiency": "Developing", "level_color": "#F59E0B", "pct": 76, "rating": 7.6, "badge": "GOV-101"}
        ],
        "certifications": [
            {"code": "GOV-101", "title": "Data Governance Foundations", "credential_id": "STAR-CERT-2026-GOV-0129", "issued_at": "2026-10-25", "score": "38.0 / 50.0 (76%)", "honors": "Certified Milestone"}
        ],
        "strengths": [
            "Proactive in recognizing submission roadblocks and requesting deadline extensions with clear technical reasoning.",
            "Persistent troubleshooting attitude in diagnosing malformed schema rejection events."
        ],
        "improvements": [
            "Dead-Letter Queue exponential backoff logic requires remediation to prevent queue buildup.",
            "Schema evolution validation needs defensive error handling for unexpected null payload attributes."
        ],
        "mentoring_plan": "Review and approve CUR-102 deadline extension; provide sample DLQ backoff implementation patterns."
    },
    {
        "id": "demo_seraphina",
        "name": "Seraphina Vale",
        "email": "seraphina.vale@orion.starapp.io",
        "avatar": "SV",
        "batch": "Batch Orion-24",
        "is_demo": True,
        "completed_count": 4,
        "total_assigned": 5,
        "active_badge_id": "badge_sql_201",
        "active_badge_code": "SQL-201",
        "active_badge_title": "Advanced Analytical SQL",
        "upcoming_deadline": "2026-12-10",
        "deadline_status": "On Schedule",
        "last_active": "2026-11-08",
        "days_inactive": 0,
        "last_activity_summary": "Executed distributed window analytics queries",
        "risk_status": "On Track",
        "risk_reason": "Top tier performance across all criteria. Advanced SQL milestone in final verification.",
        "assessments": [
            {
                "badge_id": "badge_gov_101",
                "badge_code": "GOV-101",
                "badge_title": "Data Governance Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-10-19",
                "business_understanding": 10.0,
                "architecture_report": 10.0,
                "technical_knowledge": 10.0,
                "presentation": 10.0,
                "qa": 10.0,
                "total_marks": 50.0,
                "percentage": 100.0
            },
            {
                "badge_id": "badge_cur_102",
                "badge_code": "CUR-102",
                "badge_title": "Data Curation & Stewardship",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-10-27",
                "business_understanding": 10.0,
                "architecture_report": 9.5,
                "technical_knowledge": 10.0,
                "presentation": 10.0,
                "qa": 9.5,
                "total_marks": 49.0,
                "percentage": 98.0
            },
            {
                "badge_id": "badge_dat_103",
                "badge_code": "DAT-103",
                "badge_title": "In-Memory Datastores",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-01",
                "business_understanding": 10.0,
                "architecture_report": 10.0,
                "technical_knowledge": 10.0,
                "presentation": 10.0,
                "qa": 10.0,
                "total_marks": 50.0,
                "percentage": 100.0
            },
            {
                "badge_id": "badge_ing_104",
                "badge_code": "ING-104",
                "badge_title": "Ingestion Foundations",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-05",
                "business_understanding": 10.0,
                "architecture_report": 9.5,
                "technical_knowledge": 10.0,
                "presentation": 10.0,
                "qa": 9.5,
                "total_marks": 49.0,
                "percentage": 98.0
            },
            {
                "id": "asm_demo_seraphina_sql_201",
                "badge_id": "badge_sql_201",
                "badge_code": "SQL-201",
                "badge_title": "Advanced Analytical SQL",
                "attempt_number": 1,
                "decision": "approve",
                "reviewed_at": "2026-11-08",
                "business_understanding": 10.0,
                "architecture_report": 10.0,
                "technical_knowledge": 10.0,
                "presentation": 10.0,
                "qa": 10.0,
                "total_marks": 50.0,
                "percentage": 100.0
            }
        ],
        "submissions_count": 5,
        "first_attempt_passes": 5,
        "first_attempt_eligible": 5,
        "resubmission_count": 0,
        "average_marks": 49.6,
        "average_percentage": 99.2,
        "standing_tier": "Excellent Performance",
        "skills": [
            {"name": "ReactJS", "category": "Frontend Architecture", "proficiency": "Expert", "level_color": "#10B981", "pct": 98, "rating": 9.8, "badge": "DAT-103"},
            {"name": "Nodejs", "category": "Backend Engineering", "proficiency": "Expert", "level_color": "#10B981", "pct": 99, "rating": 9.9, "badge": "ING-104"},
            {"name": "SQL", "category": "Analytical Querying", "proficiency": "Expert", "level_color": "#10B981", "pct": 100, "rating": 10.0, "badge": "SQL-201"},
            {"name": "Python", "category": "Data Engineering", "proficiency": "Expert", "level_color": "#10B981", "pct": 99, "rating": 9.9, "badge": "CUR-102"},
            {"name": "Database", "category": "Storage Systems", "proficiency": "Expert", "level_color": "#10B981", "pct": 100, "rating": 10.0, "badge": "DAT-103"},
            {"name": "Cloud", "category": "Cloud Architecture", "proficiency": "Expert", "level_color": "#10B981", "pct": 97, "rating": 9.7, "badge": "GOV-101"}
        ],
        "certifications": [
            {"code": "GOV-101", "title": "Data Governance Foundations", "credential_id": "STAR-CERT-2026-GOV-0112", "issued_at": "2026-10-19", "score": "50.0 / 50.0 (100%)", "honors": "Highest Honors (Perfect Score)"},
            {"code": "CUR-102", "title": "Data Curation & Stewardship", "credential_id": "STAR-CERT-2026-CUR-0125", "issued_at": "2026-10-27", "score": "49.0 / 50.0 (98%)", "honors": "Honors with Distinction"},
            {"code": "DAT-103", "title": "In-Memory Datastores", "credential_id": "STAR-CERT-2026-DAT-0139", "issued_at": "2026-11-01", "score": "50.0 / 50.0 (100%)", "honors": "Highest Honors (Perfect Score)"},
            {"code": "ING-104", "title": "Ingestion Foundations", "credential_id": "STAR-CERT-2026-ING-0155", "issued_at": "2026-11-05", "score": "49.0 / 50.0 (98%)", "honors": "Honors with Distinction"}
        ],
        "strengths": [
            "Flawless rubric scoring across multiple criteria with near-perfect marksheet record (49.5 / 50.0 average).",
            "Deep comprehension of distributed Redis clustering topologies and partition failover guarantees.",
            "Exceptionally clean codebase architecture with comprehensive test fixtures and edge-case mocking."
        ],
        "improvements": [
            "Explore distributed query execution plan cost estimation under massive data skew scenarios.",
            "Consider contributing mentorship tips or peer code review feedback to junior cohort members."
        ],
        "mentoring_plan": "Fast-track capstone research topics; explore lead architect or peer mentor designation for Batch Orion-24."
    }
]

def get_dashboard_demo_cosmonauts() -> List[Dict[str, Any]]:
    """Returns the 5 isolated demonstration profiles for Guardian analytics."""
    return DASHBOARD_DEMO_COSMONAUTS

def get_demo_cosmonaut_by_id(demo_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific demonstration profile by its ID."""
    for c in DASHBOARD_DEMO_COSMONAUTS:
        if c["id"] == demo_id:
            return c
    return None

