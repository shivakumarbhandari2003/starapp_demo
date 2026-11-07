"""
STARAPP SEED DATA GENERATOR (SINGLE GUARDIAN + SINGLE COSMONAUT)
Constructs the initial synthetic demo environment:
- 1 Guardian: Dr. Elena Vance (guardian_1 / 'guardian')
- 1 Cosmonaut: Astraea Nova (cosmo_1 / 'astraea')
- Batch Orion-24
- Exactly 5 badges on the initial learning roadmap:
  1. GOV-101 (Completed)
  2. CUR-102 (Completed)
  3. DAT-103 (Completed)
  4. ING-104 (At Present / Active)
  5. SQL-201 (Locked)
- Additional catalog milestones ready to dynamically unlock when Guardian creates badges.
"""

from typing import Dict, Any

def get_initial_seed_data() -> Dict[str, Any]:
    users = [
        {
            "id": "guardian_1",
            "username": "guardian",
            "email": "guardian@starapp.dev",
            "role": "guardian",
            "name": "Dr. Elena Vance",
            "avatar": "EV"
        },
        {
            "id": "cosmo_1",
            "username": "astraea",
            "email": "astraea@starapp.dev",
            "role": "cosmonaut",
            "name": "Astraea Nova",
            "avatar": "AN"
        }
    ]

    all_cosmo_ids = ["cosmo_1"]

    profiles = [
        {
            "user_id": "cosmo_1",
            "batch_name": "Orion-24",
            "assigned_guardian_id": "guardian_1",
            "guardian_credentials": "Ph.D. Distributed Systems & AI, Lead Academy Mentor",
            "skills": ["Data Governance", "SQL Optimization", "Data Modeling", "Python ETL", "Kafka Ingestion"],
            "certifications": [
                {"name": "Enterprise Data Governance Associate", "issuer": "Data Council", "year": "2024"},
                {"name": "Advanced Relational Modeling", "issuer": "OpenData Org", "year": "2025"}
            ]
        }
    ]

    badges = [
        # Milestone 1: GOV-101 (Completed)
        {
            "id": "badge_gov_101",
            "code": "GOV-101",
            "title": "Governance Foundations",
            "category": "Foundations",
            "description": "Master data classification schemes, regulatory frameworks (GDPR, HIPAA, CCPA), and role-based data governance policies.",
            "learning_outcomes": [
                "Formulate comprehensive data stewardship agreements",
                "Implement role-based access control and masking policies",
                "Establish compliance reporting pipelines"
            ],
            "learning_topics": ["Data Classification", "Audit Trails", "Privacy Compliance", "Access Roles"],
            "prerequisites": [],
            "project_requirements": "Design a complete Data Governance Framework Charter and Access Matrix for an enterprise healthcare dataset.",
            "is_published": True,
            "assigned_cosmonaut_ids": ["cosmo_1"],
            "default_timeline": {
                "assignment_date": "2026-10-01",
                "publication_date": "2026-10-01",
                "learning_start_date": "2026-10-02",
                "learning_end_date": "2026-10-10",
                "project_start_date": "2026-10-11",
                "project_end_date": "2026-10-20",
                "submission_deadline": "2026-10-22",
                "review_date": "2026-10-25",
                "expected_award_date": "2026-10-26"
            }
        },
        # Milestone 2: CUR-102 (Completed)
        {
            "id": "badge_cur_102",
            "code": "CUR-102",
            "title": "Curation Foundations",
            "category": "Foundations",
            "description": "Learn dataset quality assessment, deduplication pipelines, anomaly detection heuristics, and silver-layer enrichment.",
            "learning_outcomes": [
                "Perform automated schema validation",
                "Implement outlier detection and missing-value imputation",
                "Document end-to-end data lineage"
            ],
            "learning_topics": ["Data Profiling", "Anomaly Detection", "Lineage Graphs", "Cleanliness Metrics"],
            "prerequisites": ["badge_gov_101"],
            "project_requirements": "Build an automated quality profiling script and audit report verifying a dirty customer telemetry dataset.",
            "is_published": True,
            "assigned_cosmonaut_ids": ["cosmo_1"],
            "default_timeline": {
                "assignment_date": "2026-10-15",
                "publication_date": "2026-10-15",
                "learning_start_date": "2026-10-16",
                "learning_end_date": "2026-10-25",
                "project_start_date": "2026-10-26",
                "project_end_date": "2026-11-05",
                "submission_deadline": "2026-11-08",
                "review_date": "2026-11-12",
                "expected_award_date": "2026-11-14"
            }
        },
        # Milestone 3: DAT-103 (Completed)
        {
            "id": "badge_dat_103",
            "code": "DAT-103",
            "title": "Data Model Foundations",
            "category": "Foundations",
            "description": "Architect normalized 3NF schemas, dimensional star/snowflake warehouses, slowly changing dimensions (SCD Type 2), and surrogate keys.",
            "learning_outcomes": [
                "Translate business requirements into relational ERDs",
                "Design dimensional star schemas with fact and dimension tables",
                "Handle historical tracking using SCD Type 2 strategies"
            ],
            "learning_topics": ["3NF Normalization", "Star Schemas", "Grain Definition", "SCD Strategies"],
            "prerequisites": ["badge_cur_102"],
            "project_requirements": "Produce an architectural report and DDL statements for a high-volume fintech transaction warehouse.",
            "is_published": True,
            "assigned_cosmonaut_ids": ["cosmo_1"],
            "default_timeline": {
                "assignment_date": "2026-11-01",
                "publication_date": "2026-11-01",
                "learning_start_date": "2026-11-02",
                "learning_end_date": "2026-11-12",
                "project_start_date": "2026-11-13",
                "project_end_date": "2026-11-24",
                "submission_deadline": "2026-11-26",
                "review_date": "2026-11-29",
                "expected_award_date": "2026-11-30"
            }
        },
        # Milestone 4: ING-104 (At Present / Active)
        {
            "id": "badge_ing_104",
            "code": "ING-104",
            "title": "Ingestion Foundations",
            "category": "Core Engineering",
            "description": "Implement robust batch and streaming ingest architectures, backpressure regulation, idempotency guarantees, and dead-letter queues.",
            "learning_outcomes": [
                "Construct fault-tolerant REST and webhook ingestion connectors",
                "Guarantee exactly-once or idempotent delivery semantics",
                "Route malformed payloads to DLQs with alerting triggers"
            ],
            "learning_topics": ["Kafka / PubSub Ingestion", "Dead Letter Queues", "Idempotency", "Backpressure"],
            "prerequisites": ["badge_dat_103"],
            "project_requirements": "Implement an idempotent streaming ingestion consumer with a dead-letter recovery pipeline.",
            "is_published": True,
            "assigned_cosmonaut_ids": ["cosmo_1"],
            "default_timeline": {
                "assignment_date": "2026-11-05",
                "publication_date": "2026-11-05",
                "learning_start_date": "2026-11-06",
                "learning_end_date": "2026-11-18",
                "project_start_date": "2026-11-19",
                "project_end_date": "2026-11-30",
                "submission_deadline": "2026-12-02",
                "review_date": "2026-12-05",
                "expected_award_date": "2026-12-07"
            }
        },
        # Milestone 5: SQL-201 (Locked)
        {
            "id": "badge_sql_201",
            "code": "SQL-201",
            "title": "SQL-1",
            "category": "Core Engineering",
            "description": "Deep dive into advanced analytic queries, window functions, recursive CTEs, indexing strategies (B-Tree vs Hash), and EXPLAIN query plan optimization.",
            "learning_outcomes": [
                "Execute complex cohort and retention window aggregations",
                "Analyze query execution plans and resolve sequential table scans",
                "Formulate recursive CTEs for hierarchical tree traversal"
            ],
            "learning_topics": ["Window Functions", "Query Plan Costing", "Recursive CTEs", "Partial Indexes"],
            "prerequisites": ["badge_dat_103"],
            "project_requirements": "Optimize 5 pathological slow queries in an enterprise schema and document the 10x latency reduction.",
            "is_published": True,
            "assigned_cosmonaut_ids": ["cosmo_1"],
            "default_timeline": {
                "assignment_date": "2026-11-10",
                "publication_date": "2026-11-10",
                "learning_start_date": "2026-11-11",
                "learning_end_date": "2026-11-20",
                "project_start_date": "2026-11-21",
                "project_end_date": "2026-12-01",
                "submission_deadline": "2026-12-03",
                "review_date": "2026-12-06",
                "expected_award_date": "2026-12-08"
            }
        },
        # Catalog Badges (Unassigned initially, ready to be unlocked)
        {
            "id": "badge_ai_301",
            "code": "AI-301",
            "title": "AI Operating Systems Foundations",
            "category": "Advanced AI",
            "description": "Integrate autonomous LLM reasoning agents, embedding index retrievals, context window optimization, tool-use safety guardrails, and latency caching.",
            "learning_outcomes": [
                "Deploy local vector embedding pipelines",
                "Construct deterministic tool-calling workflows for LLM agents",
                "Implement safety filters and prompt injection shields"
            ],
            "learning_topics": ["Vector Stores", "Agentic Tool Calling", "Context Compression", "Prompt Defense"],
            "prerequisites": ["badge_sql_201"],
            "project_requirements": "Build a secure agentic assistant that queries an internal knowledge base with tool verification.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-11-15",
                "publication_date": "2026-11-15",
                "learning_start_date": "2026-11-16",
                "learning_end_date": "2026-12-01",
                "project_start_date": "2026-12-02",
                "project_end_date": "2026-12-15",
                "submission_deadline": "2026-12-18",
                "review_date": "2026-12-21",
                "expected_award_date": "2026-12-23"
            }
        },
        {
            "id": "badge_cld_202",
            "code": "CLD-202",
            "title": "Cloud Foundations",
            "category": "Infrastructure",
            "description": "Deploy immutable cloud infrastructure with declarative specs, VPC isolation, zero-trust security groups, and object store lifecycle policies.",
            "learning_outcomes": [
                "Provision secure multi-tier cloud network topologies",
                "Configure cloud object storage with tiering and replication",
                "Enforce IAM principle of least privilege"
            ],
            "learning_topics": ["VPC Topologies", "Object Storage", "IAM Least Privilege", "CloudWatch / Logs"],
            "prerequisites": ["badge_gov_101"],
            "project_requirements": "Write a complete cloud infrastructure blueprint specification for a HIPAA-compliant app environment.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-10-20",
                "publication_date": "2026-10-20",
                "learning_start_date": "2026-10-21",
                "learning_end_date": "2026-11-02",
                "project_start_date": "2026-11-03",
                "project_end_date": "2026-11-15",
                "submission_deadline": "2026-11-18",
                "review_date": "2026-11-21",
                "expected_award_date": "2026-11-23"
            }
        }
    ]

    # Generate timelines for Astraea (cosmo_1) on the assigned 5 badges
    timelines = []
    for b in badges[:5]:
        dt = b["default_timeline"]
        is_completed = b["id"] in ["badge_gov_101", "badge_cur_102", "badge_dat_103"]
        status = "completed" if is_completed else ("active" if b["id"] == "badge_ing_104" else "locked")
        award_date = dt["expected_award_date"] if is_completed else None

        timelines.append({
            "badge_id": b["id"],
            "cosmonaut_id": "cosmo_1",
            "assignment_date": dt["assignment_date"],
            "publication_date": dt["publication_date"],
            "learning_start_date": dt["learning_start_date"],
            "learning_end_date": dt["learning_end_date"],
            "project_start_date": dt["project_start_date"],
            "project_end_date": dt["project_end_date"],
            "submission_deadline": dt["submission_deadline"],
            "review_date": dt["review_date"],
            "expected_award_date": dt["expected_award_date"],
            "actual_award_date": award_date,
            "status": status
        })

    # Submissions for Astraea (cosmo_1)
    submissions = [
        {
            "id": "sub_cosmo_1_gov",
            "badge_id": "badge_gov_101",
            "cosmonaut_id": "cosmo_1",
            "attempt_number": 1,
            "submission_type": "pdf",
            "payload": "data:application/pdf;base64,JVBERi0xLjQKJcTl8uXrp/Og0MTGCjEgMCBvYmoKPDwKL1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDIgMCBSCj4+CmVuZG9iag==",
            "file_name": "Astraea_Governance_Blueprint.pdf",
            "submitted_at": "2026-10-21T14:30:00Z",
            "status": "approved"
        },
        {
            "id": "sub_cosmo_1_cur",
            "badge_id": "badge_cur_102",
            "cosmonaut_id": "cosmo_1",
            "attempt_number": 1,
            "submission_type": "github",
            "payload": "https://github.com/starapp-cosmonauts/curation-pipeline-astraea",
            "file_name": "curation-pipeline-astraea",
            "submitted_at": "2026-11-03T09:15:00Z",
            "status": "approved"
        },
        {
            "id": "sub_cosmo_1_dat",
            "badge_id": "badge_dat_103",
            "cosmonaut_id": "cosmo_1",
            "attempt_number": 1,
            "submission_type": "pdf",
            "payload": "data:application/pdf;base64,JVBERi0xLjQKJcTl8uXrp/Og0MTGCjEgMCBvYmoKPDwKL1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDIgMCBSCj4+CmVuZG9iag==",
            "file_name": "Astraea_Fintech_Data_Warehouse.pdf",
            "submitted_at": "2026-11-05T18:00:00Z",
            "status": "approved"
        },
        # Milestone 4 (ING-104): Attempt 1 had resubmission requested; Attempt 2 is pending review
        {
            "id": "sub_cosmo_1_ing_1",
            "badge_id": "badge_ing_104",
            "cosmonaut_id": "cosmo_1",
            "attempt_number": 1,
            "submission_type": "github",
            "payload": "https://github.com/starapp-cosmonauts/ingestion-service-astraea/tree/v1",
            "file_name": "ingestion-service-astraea-v1",
            "submitted_at": "2026-11-06T10:00:00Z",
            "status": "resubmission_requested"
        },
        {
            "id": "sub_cosmo_1_ing_2",
            "badge_id": "badge_ing_104",
            "cosmonaut_id": "cosmo_1",
            "attempt_number": 2,
            "submission_type": "github",
            "payload": "https://github.com/starapp-cosmonauts/ingestion-service-astraea/tree/v2-fix",
            "file_name": "ingestion-service-astraea-v2-idempotent",
            "submitted_at": "2026-11-07T14:30:00Z",
            "status": "pending"
        }
    ]

    # Assessments for Astraea (cosmo_1): 3 approved + 1 resubmission requested on attempt 1
    assessments = [
        {
            "id": "asm_c1_gov",
            "submission_id": "sub_cosmo_1_gov",
            "attempt_number": 1,
            "badge_id": "badge_gov_101",
            "cosmonaut_id": "cosmo_1",
            "reviewer_id": "guardian_1",
            "reviewer_name": "Dr. Elena Vance",
            "reviewed_at": "2026-10-24T16:00:00Z",
            "decision": "approve",
            "business_understanding": 10.0,
            "architecture_report": 9.5,
            "technical_knowledge": 9.5,
            "presentation": 10.0,
            "qa": 9.0,
            "strength_areas": "Flawless articulation of HIPAA/GDPR boundaries; exemplary role-based matrix.",
            "improvement_areas": "Document automated edge-gateway policy triggers.",
            "overall_feedback": "Exemplary standard for enterprise governance blueprints. Approved."
        },
        {
            "id": "asm_c1_cur",
            "submission_id": "sub_cosmo_1_cur",
            "attempt_number": 1,
            "badge_id": "badge_cur_102",
            "cosmonaut_id": "cosmo_1",
            "reviewer_id": "guardian_1",
            "reviewer_name": "Dr. Elena Vance",
            "reviewed_at": "2026-11-04T14:30:00Z",
            "decision": "approve",
            "business_understanding": 9.5,
            "architecture_report": 9.5,
            "technical_knowledge": 10.0,
            "presentation": 9.0,
            "qa": 9.0,
            "strength_areas": "High-throughput deduplication heuristic; clean statistical variance charts.",
            "improvement_areas": "Explore Bayesian adaptive imputation.",
            "overall_feedback": "Deep comprehension of silver-layer data quality. Approved."
        },
        {
            "id": "asm_c1_dat",
            "submission_id": "sub_cosmo_1_dat",
            "attempt_number": 1,
            "badge_id": "badge_dat_103",
            "cosmonaut_id": "cosmo_1",
            "reviewer_id": "guardian_1",
            "reviewer_name": "Dr. Elena Vance",
            "reviewed_at": "2026-11-06T11:00:00Z",
            "decision": "approve",
            "business_understanding": 10.0,
            "architecture_report": 10.0,
            "technical_knowledge": 10.0,
            "presentation": 9.5,
            "qa": 9.5,
            "strength_areas": "Exceptional star schema grain definition and SCD Type 2 tracking strategy.",
            "improvement_areas": "Consider partitioning on timestamp key.",
            "overall_feedback": "Flawless data warehouse architecture. Ready for Ingestion Foundations."
        },
        {
            "id": "asm_c1_ing_1",
            "submission_id": "sub_cosmo_1_ing_1",
            "attempt_number": 1,
            "badge_id": "badge_ing_104",
            "cosmonaut_id": "cosmo_1",
            "reviewer_id": "guardian_1",
            "reviewer_name": "Dr. Elena Vance",
            "reviewed_at": "2026-11-06T18:00:00Z",
            "decision": "resubmission_requested",
            "business_understanding": 7.0,
            "architecture_report": 6.5,
            "technical_knowledge": 6.5,
            "presentation": 6.0,
            "qa": 6.0,
            "strength_areas": "Basic streaming consumer connects reliably and processes happy-path events.",
            "improvement_areas": "Lacks idempotency keys in Kafka consumer offsets; duplicate payloads result in duplicate DB writes.",
            "overall_feedback": "Promising start, but critical enterprise ingestion requirements (idempotency and DLQ backoff) must be resolved. Please resubmit Attempt 2."
        }
    ]

    materials = [
        # GOV-101
        {
            "id": "mat_gov_101_v1",
            "badge_id": "badge_gov_101",
            "topic": "Video Lecture 1",
            "title": "GOV-101: Tactical Operations & Scenario Engineering (Video 1)",
            "description": "Video lecture analyzing scenario orchestration, runtime mechanics, and foundational tactics.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=9ZGFF_bYenc&pp=ygUDYW90",
            "upload_date": "2026-10-02T10:00:00Z"
        },
        {
            "id": "mat_gov_101_v2",
            "badge_id": "badge_gov_101",
            "topic": "Video Lecture 2",
            "title": "GOV-101: Technical Analysis & Mechanics (Video 2)",
            "description": "Video lecture covering core structural frameworks, operational diagnostics, and system workflows.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=F0sqfPkCcyM&pp=ygUDYW90",
            "upload_date": "2026-10-05T14:00:00Z"
        },
        {
            "id": "mat_gov_101_pdf",
            "badge_id": "badge_gov_101",
            "topic": "Curriculum Manual",
            "title": "GOV-101: Chemistry & Technical Curriculum Syllabus",
            "description": "Official specification manual from the data folder. Read and review directly inside the container.",
            "material_type": "pdf",
            "url_or_data": "data/Chemistry%20Syllabus.pdf",
            "upload_date": "2026-10-10T12:00:00Z"
        },
        # CUR-102
        {
            "id": "mat_cur_102_v1",
            "badge_id": "badge_cur_102",
            "topic": "Video Lecture 1",
            "title": "CUR-102: Tactical Operations & Scenario Engineering (Video 1)",
            "description": "Video lecture analyzing scenario orchestration, runtime mechanics, and foundational tactics.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=9ZGFF_bYenc&pp=ygUDYW90",
            "upload_date": "2026-10-12T10:00:00Z"
        },
        {
            "id": "mat_cur_102_v2",
            "badge_id": "badge_cur_102",
            "topic": "Video Lecture 2",
            "title": "CUR-102: Technical Analysis & Mechanics (Video 2)",
            "description": "Video lecture covering core structural frameworks, operational diagnostics, and system workflows.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=F0sqfPkCcyM&pp=ygUDYW90",
            "upload_date": "2026-10-15T14:00:00Z"
        },
        {
            "id": "mat_cur_102_pdf",
            "badge_id": "badge_cur_102",
            "topic": "Curriculum Manual",
            "title": "CUR-102: Chemistry & Technical Curriculum Syllabus",
            "description": "Official specification manual from the data folder. Read and review directly inside the container.",
            "material_type": "pdf",
            "url_or_data": "data/Chemistry%20Syllabus.pdf",
            "upload_date": "2026-10-18T12:00:00Z"
        },
        # DAT-103
        {
            "id": "mat_dat_103_v1",
            "badge_id": "badge_dat_103",
            "topic": "Video Lecture 1",
            "title": "DAT-103: Tactical Operations & Scenario Engineering (Video 1)",
            "description": "Video lecture analyzing scenario orchestration, runtime mechanics, and foundational tactics.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=9ZGFF_bYenc&pp=ygUDYW90",
            "upload_date": "2026-10-22T10:00:00Z"
        },
        {
            "id": "mat_dat_103_v2",
            "badge_id": "badge_dat_103",
            "topic": "Video Lecture 2",
            "title": "DAT-103: Technical Analysis & Mechanics (Video 2)",
            "description": "Video lecture covering core structural frameworks, operational diagnostics, and system workflows.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=F0sqfPkCcyM&pp=ygUDYW90",
            "upload_date": "2026-10-25T14:00:00Z"
        },
        {
            "id": "mat_dat_103_pdf",
            "badge_id": "badge_dat_103",
            "topic": "Curriculum Manual",
            "title": "DAT-103: Chemistry & Technical Curriculum Syllabus",
            "description": "Official specification manual from the data folder. Read and review directly inside the container.",
            "material_type": "pdf",
            "url_or_data": "data/Chemistry%20Syllabus.pdf",
            "upload_date": "2026-10-28T12:00:00Z"
        },
        # ING-104
        {
            "id": "mat_ing_104_v1",
            "badge_id": "badge_ing_104",
            "topic": "Video Lecture 1",
            "title": "ING-104: Tactical Operations & Scenario Engineering (Video 1)",
            "description": "Video lecture analyzing scenario orchestration, runtime mechanics, and foundational tactics.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=9ZGFF_bYenc&pp=ygUDYW90",
            "upload_date": "2026-11-01T10:00:00Z"
        },
        {
            "id": "mat_ing_104_v2",
            "badge_id": "badge_ing_104",
            "topic": "Video Lecture 2",
            "title": "ING-104: Technical Analysis & Mechanics (Video 2)",
            "description": "Video lecture covering core structural frameworks, operational diagnostics, and system workflows.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=F0sqfPkCcyM&pp=ygUDYW90",
            "upload_date": "2026-11-03T14:00:00Z"
        },
        {
            "id": "mat_ing_104_pdf",
            "badge_id": "badge_ing_104",
            "topic": "Curriculum Manual",
            "title": "ING-104: Chemistry & Technical Curriculum Syllabus",
            "description": "Official specification manual from the data folder. Read and review directly inside the container.",
            "material_type": "pdf",
            "url_or_data": "data/Chemistry%20Syllabus.pdf",
            "upload_date": "2026-11-05T12:00:00Z"
        },
        # SQL-201
        {
            "id": "mat_sql_201_v1",
            "badge_id": "badge_sql_201",
            "topic": "Video Lecture 1",
            "title": "SQL-201: Tactical Operations & Scenario Engineering (Video 1)",
            "description": "Video lecture analyzing scenario orchestration, runtime mechanics, and foundational tactics.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=9ZGFF_bYenc&pp=ygUDYW90",
            "upload_date": "2026-11-08T10:00:00Z"
        },
        {
            "id": "mat_sql_201_v2",
            "badge_id": "badge_sql_201",
            "topic": "Video Lecture 2",
            "title": "SQL-201: Technical Analysis & Mechanics (Video 2)",
            "description": "Video lecture covering core structural frameworks, operational diagnostics, and system workflows.",
            "material_type": "youtube",
            "url_or_data": "https://www.youtube.com/watch?v=F0sqfPkCcyM&pp=ygUDYW90",
            "upload_date": "2026-11-10T14:00:00Z"
        },
        {
            "id": "mat_sql_201_pdf",
            "badge_id": "badge_sql_201",
            "topic": "Curriculum Manual",
            "title": "SQL-201: Chemistry & Technical Curriculum Syllabus",
            "description": "Official specification manual from the data folder. Read and review directly inside the container.",
            "material_type": "pdf",
            "url_or_data": "data/Chemistry%20Syllabus.pdf",
            "upload_date": "2026-11-12T12:00:00Z"
        }
    ]

    extensions = [
        {
            "id": "ext_1",
            "badge_id": "badge_ing_104",
            "cosmonaut_id": "cosmo_1",
            "current_deadline": "2026-12-02",
            "proposed_deadline": "2026-12-10",
            "reason": "Encountered backpressure buffering bottlenecks in high-volume mock stream. Requesting additional days to benchmark Kafka consumer offsets.",
            "status": "pending",
            "requested_at": "2026-11-06T11:00:00Z",
            "guardian_response": "",
            "decided_at": None
        }
    ]

    announcements = [
        {
            "id": "ann_1",
            "title": "StarApp Cohort Orientation & Academy Guidelines",
            "message": "Welcome to Batch Orion-24! Please ensure your project submissions strictly follow the 5-criterion 50-mark assessment rubric guidelines before submitting deliverables.",
            "published_at": "2026-10-01T08:00:00Z",
            "author_id": "guardian_1",
            "author_name": "Dr. Elena Vance",
            "target_type": "all",
            "target_cosmonaut_ids": ["cosmo_1"],
            "badge_id": "badge_gov_101",
            "read_by_cosmonaut_ids": ["cosmo_1"]
        },
        {
            "id": "ann_2",
            "title": "Advanced Ingestion Architecture Mentorship Clinic",
            "message": "We are hosting an interactive session on Kafka consumer offsets, idempotency keys, and dead-letter queues this Friday at 14:00 UTC.",
            "published_at": "2026-11-05T10:00:00Z",
            "author_id": "guardian_1",
            "author_name": "Dr. Elena Vance",
            "target_type": "all",
            "target_cosmonaut_ids": ["cosmo_1"],
            "badge_id": "badge_ing_104",
            "read_by_cosmonaut_ids": []
        }
    ]

    activities = [
        {
            "id": "act_1",
            "event_type": "batch_initialized",
            "timestamp": "2026-10-01T08:00:00Z",
            "actor_id": "guardian_1",
            "actor_name": "Dr. Elena Vance",
            "cosmonaut_id": "",
            "badge_id": "",
            "summary": "Training Batch Orion-24 Initialized",
            "details": "Academy portal initialized with Mentor Dr. Elena Vance and Cosmonaut Astraea Nova."
        },
        {
            "id": "act_2",
            "event_type": "badge_awarded",
            "timestamp": "2026-10-24T16:00:00Z",
            "actor_id": "guardian_1",
            "actor_name": "Dr. Elena Vance",
            "cosmonaut_id": "cosmo_1",
            "badge_id": "badge_gov_101",
            "summary": "Milestone Awarded: GOV-101",
            "details": "Astraea Nova passed Governance Foundations with 48.0/50 (96.0%)."
        },
        {
            "id": "act_3",
            "event_type": "badge_awarded",
            "timestamp": "2026-11-04T14:30:00Z",
            "actor_id": "guardian_1",
            "actor_name": "Dr. Elena Vance",
            "cosmonaut_id": "cosmo_1",
            "badge_id": "badge_cur_102",
            "summary": "Milestone Awarded: CUR-102",
            "details": "Astraea Nova passed Curation Foundations with 47.0/50 (94.0%)."
        },
        {
            "id": "act_4",
            "event_type": "badge_awarded",
            "timestamp": "2026-11-06T11:00:00Z",
            "actor_id": "guardian_1",
            "actor_name": "Dr. Elena Vance",
            "cosmonaut_id": "cosmo_1",
            "badge_id": "badge_dat_103",
            "summary": "Milestone Awarded: DAT-103",
            "details": "Astraea Nova passed Data Model Foundations with 49.0/50 (98.0%)."
        }
    ]

    notifications = [
        {
            "id": "notif_1",
            "recipient_id": "cosmo_1",
            "title": "Welcome to StarApp Academy",
            "message": "Your training journey has begun. Review your active milestones in the Learning Roadmap.",
            "created_at": "2026-10-01T08:05:00Z",
            "is_read": True,
            "link_section": "c_roadmap"
        },
        {
            "id": "notif_2",
            "recipient_id": "cosmo_1",
            "title": "Milestone Awarded: DAT-103",
            "message": "Dr. Elena Vance approved your Data Model Foundations project deliverable (49.0/50).",
            "created_at": "2026-11-06T11:05:00Z",
            "is_read": False,
            "link_section": "c_results"
        },
        {
            "id": "notif_3",
            "recipient_id": "guardian_1",
            "title": "Ingestion Deliverable Submitted",
            "message": "Astraea Nova submitted Attempt #2 for ING-104 Ingestion Foundations.",
            "created_at": "2026-11-07T14:30:00Z",
            "is_read": False,
            "link_section": "g_reviews"
        }
    ]

    return {
        "users": users,
        "profiles": profiles,
        "badges": badges,
        "timelines": timelines,
        "submissions": submissions,
        "assessments": assessments,
        "materials": materials,
        "extensions": extensions,
        "announcements": announcements,
        "activities": activities,
        "notifications": notifications
    }
