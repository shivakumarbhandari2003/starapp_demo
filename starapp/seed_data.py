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
            "is_allocated": True,
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
            "is_allocated": True,
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
            "is_allocated": True,
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
            "is_allocated": True,
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
            "is_allocated": False,
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
            "is_allocated": False,
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
            "is_allocated": False,
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
        },
        {
            "id": "badge_net_203",
            "is_allocated": False,
            "code": "NET-203",
            "title": "Distributed APIs & Service Mesh",
            "category": "Infrastructure",
            "description": "Design resilient microservice gateways, circuit breakers, and zero-trust mTLS service-to-service communication.",
            "learning_outcomes": [
                "Implement rate limiting, retries, and circuit breakers",
                "Configure mTLS service-mesh traffic routing",
                "Instrument distributed tracing headers across API boundaries"
            ],
            "learning_topics": ["API Gateways", "Circuit Breakers", "mTLS", "OpenTelemetry"],
            "prerequisites": ["badge_cld_202"],
            "project_requirements": "Build an API gateway policy blueprint with circuit-breaking thresholds and distributed trace propagation.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-11-20",
                "publication_date": "2026-11-20",
                "learning_start_date": "2026-11-21",
                "learning_end_date": "2026-11-30",
                "project_start_date": "2026-12-01",
                "project_end_date": "2026-12-10",
                "submission_deadline": "2026-12-12",
                "review_date": "2026-12-15",
                "expected_award_date": "2026-12-18"
            }
        },
        {
            "id": "badge_sec_204",
            "is_allocated": False,
            "code": "SEC-204",
            "title": "Data Security & Zero-Trust IAM",
            "category": "Governance",
            "description": "Enforce envelope encryption, fine-grained RBAC/ABAC authorization, key rotation, and secrets lifecycle security.",
            "learning_outcomes": [
                "Design KMS envelope encryption workflows for sensitive datasets",
                "Implement least-privilege policy-as-code access controls",
                "Audit secret rotation and credential leakage prevention"
            ],
            "learning_topics": ["KMS Envelope Encryption", "ABAC Policies", "Key Rotation", "Secrets Management"],
            "prerequisites": ["badge_gov_101", "badge_cld_202"],
            "project_requirements": "Deliver a zero-trust IAM policy bundle and key-rotation verification spec for multi-tenant data stores.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-11-25",
                "publication_date": "2026-11-25",
                "learning_start_date": "2026-11-26",
                "learning_end_date": "2026-12-05",
                "project_start_date": "2026-12-06",
                "project_end_date": "2026-12-15",
                "submission_deadline": "2026-12-18",
                "review_date": "2026-12-21",
                "expected_award_date": "2026-12-24"
            }
        },
        {
            "id": "badge_str_205",
            "is_allocated": False,
            "code": "STR-205",
            "title": "Real-Time Stream Processing",
            "category": "Data Engineering",
            "description": "Build stateful event-time streaming pipelines with tumbling/sliding windows, watermarks, and late-event handling.",
            "learning_outcomes": [
                "Construct watermarked event-time aggregations",
                "Manage RocksDB-backed stateful checkpointing",
                "Handle out-of-order and late-arriving telemetry records"
            ],
            "learning_topics": ["Event-Time Windows", "Watermarks", "Stateful Checkpoints", "Stream Joins"],
            "prerequisites": ["badge_ing_104"],
            "project_requirements": "Implement a stateful windowed stream aggregation pipeline with exactly-once sink guarantees.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-12-01",
                "publication_date": "2026-12-01",
                "learning_start_date": "2026-12-02",
                "learning_end_date": "2026-12-11",
                "project_start_date": "2026-12-12",
                "project_end_date": "2026-12-21",
                "submission_deadline": "2026-12-23",
                "review_date": "2026-12-26",
                "expected_award_date": "2026-12-29"
            }
        },
        {
            "id": "badge_dbt_206",
            "is_allocated": False,
            "code": "DBT-206",
            "title": "Analytics Engineering & Dimensional Models",
            "category": "Core Engineering",
            "description": "Transform raw lake tables into tested, documented medallion/dimensional data marts using modular SQL models.",
            "learning_outcomes": [
                "Structure Bronze-Silver-Gold analytical SQL DAGs",
                "Write schema, referential, and freshness assertions",
                "Optimize incremental model materializations"
            ],
            "learning_topics": ["Medallion Architecture", "Incremental Models", "Schema Tests", "Lineage Docs"],
            "prerequisites": ["badge_sql_201"],
            "project_requirements": "Build an incremental analytics mart DAG with automated contract tests and lineage documentation.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-12-05",
                "publication_date": "2026-12-05",
                "learning_start_date": "2026-12-06",
                "learning_end_date": "2026-12-15",
                "project_start_date": "2026-12-16",
                "project_end_date": "2026-12-26",
                "submission_deadline": "2026-12-28",
                "review_date": "2026-12-30",
                "expected_award_date": "2027-01-02"
            }
        },
        {
            "id": "badge_lkh_207",
            "is_allocated": False,
            "code": "LKH-207",
            "title": "Open Lakehouse Table Formats",
            "category": "Data Engineering",
            "description": "Operate ACID transactions, schema evolution, time-travel queries, and Parquet file compaction on open lakehouse tables.",
            "learning_outcomes": [
                "Configure Iceberg/Delta snapshot isolation and time-travel",
                "Optimize Z-ordering and small-file compaction jobs",
                "Manage safe zero-downtime schema evolution"
            ],
            "learning_topics": ["Apache Iceberg", "ACID Snapshots", "File Compaction", "Schema Evolution"],
            "prerequisites": ["badge_dat_103", "badge_sql_201"],
            "project_requirements": "Design an open lakehouse storage compaction and snapshot-retention strategy for petabyte tables.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-12-10",
                "publication_date": "2026-12-10",
                "learning_start_date": "2026-12-11",
                "learning_end_date": "2026-12-20",
                "project_start_date": "2026-12-21",
                "project_end_date": "2026-12-30",
                "submission_deadline": "2027-01-02",
                "review_date": "2027-01-05",
                "expected_award_date": "2027-01-08"
            }
        },
        {
            "id": "badge_orc_208",
            "is_allocated": False,
            "code": "ORC-208",
            "title": "Workflow Orchestration & DAG Scheduling",
            "category": "Data Engineering",
            "description": "Coordinate multi-stage pipelines with asset-aware scheduling, SLA alerting, dynamic task mapping, and backfill safety.",
            "learning_outcomes": [
                "Author idempotent orchestrated DAGs with sensor triggers",
                "Implement backfill isolation and retry backoff strategies",
                "Track SLA breaches with automated incident hooks"
            ],
            "learning_topics": ["DAG Scheduling", "Dynamic Mapping", "Backfill Safety", "SLA Alerting"],
            "prerequisites": ["badge_ing_104"],
            "project_requirements": "Deliver an asset-driven orchestration pipeline supporting safe historical partition backfills.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-12-15",
                "publication_date": "2026-12-15",
                "learning_start_date": "2026-12-16",
                "learning_end_date": "2026-12-26",
                "project_start_date": "2026-12-27",
                "project_end_date": "2027-01-05",
                "submission_deadline": "2027-01-08",
                "review_date": "2027-01-11",
                "expected_award_date": "2027-01-14"
            }
        },
        {
            "id": "badge_dq_209",
            "is_allocated": False,
            "code": "DQ-209",
            "title": "Data Quality & Contract Observability",
            "category": "Governance",
            "description": "Enforce producer-consumer data contracts, statistical anomaly detection, and circuit-breaker quarantine tables.",
            "learning_outcomes": [
                "Define enforceable YAML/JSON schema contracts",
                "Detect distribution drift and null spikes automatically",
                "Route quarantined payloads without halting clean traffic"
            ],
            "learning_topics": ["Data Contracts", "Anomaly Detection", "Quarantine Sinks", "Freshness SLIs"],
            "prerequisites": ["badge_cur_102", "badge_dbt_206"],
            "project_requirements": "Create a data contract validator and anomaly monitor with quarantine routing for broken upstream feeds.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-12-20",
                "publication_date": "2026-12-20",
                "learning_start_date": "2026-12-21",
                "learning_end_date": "2026-12-31",
                "project_start_date": "2027-01-01",
                "project_end_date": "2027-01-10",
                "submission_deadline": "2027-01-12",
                "review_date": "2027-01-15",
                "expected_award_date": "2027-01-18"
            }
        },
        {
            "id": "badge_ml_302",
            "is_allocated": False,
            "code": "ML-302",
            "title": "Applied ML Feature Pipelines",
            "category": "Advanced AI",
            "description": "Build point-in-time-correct online/offline feature stores preventing training-serving skew in production ML models.",
            "learning_outcomes": [
                "Prevent data leakage with point-in-time feature joins",
                "Synchronize low-latency online stores with batch backfills",
                "Track feature lineage and model version reproducibility"
            ],
            "learning_topics": ["Feature Stores", "Point-in-Time Joins", "Online Sync", "Model Lineage"],
            "prerequisites": ["badge_sql_201", "badge_ai_301"],
            "project_requirements": "Implement a feature pipeline specification serving consistent batch training and online inference vectors.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2026-12-25",
                "publication_date": "2026-12-25",
                "learning_start_date": "2026-12-26",
                "learning_end_date": "2027-01-05",
                "project_start_date": "2027-01-06",
                "project_end_date": "2027-01-16",
                "submission_deadline": "2027-01-18",
                "review_date": "2027-01-21",
                "expected_award_date": "2027-01-24"
            }
        },
        {
            "id": "badge_rag_303",
            "is_allocated": False,
            "code": "RAG-303",
            "title": "Vector Databases & Hybrid RAG",
            "category": "Advanced AI",
            "description": "Architect semantic chunking, HNSW vector indexing, BM25 hybrid reranking, and citation-grounded retrieval pipelines.",
            "learning_outcomes": [
                "Tune HNSW index parameters for recall vs latency",
                "Combine dense embeddings with BM25 lexical fusion",
                "Enforce provenance citations and ACL document filtering"
            ],
            "learning_topics": ["HNSW Indexing", "Hybrid Retrieval", "Cross-Encoder Rerank", "ACL Grounding"],
            "prerequisites": ["badge_ai_301"],
            "project_requirements": "Deliver a multi-tenant hybrid RAG architecture benchmarked for precision@k and ACL isolation.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-01-01",
                "publication_date": "2027-01-01",
                "learning_start_date": "2027-01-02",
                "learning_end_date": "2027-01-12",
                "project_start_date": "2027-01-13",
                "project_end_date": "2027-01-22",
                "submission_deadline": "2027-01-25",
                "review_date": "2027-01-28",
                "expected_award_date": "2027-01-31"
            }
        },
        {
            "id": "badge_agt_304",
            "is_allocated": False,
            "code": "AGT-304",
            "title": "Autonomous Tool-Use Agents",
            "category": "Advanced AI",
            "description": "Design deterministic state-machine workflows, structured function-calling schemas, sandboxing, and human-in-the-loop checkpoints.",
            "learning_outcomes": [
                "Constrain agent tool execution with typed schemas",
                "Implement approval gates for high-impact state mutations",
                "Recover gracefully from tool timeouts and partial states"
            ],
            "learning_topics": ["Function Calling", "Agent State Graphs", "Tool Sandboxing", "Human Approval Gates"],
            "prerequisites": ["badge_ai_301", "badge_rag_303"],
            "project_requirements": "Build an autonomous multi-step operations agent with typed tool contracts and human confirmation hooks.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-01-05",
                "publication_date": "2027-01-05",
                "learning_start_date": "2027-01-06",
                "learning_end_date": "2027-01-16",
                "project_start_date": "2027-01-17",
                "project_end_date": "2027-01-26",
                "submission_deadline": "2027-01-29",
                "review_date": "2027-02-01",
                "expected_award_date": "2027-02-04"
            }
        },
        {
            "id": "badge_evl_305",
            "is_allocated": False,
            "code": "EVL-305",
            "title": "AI Evaluation & Safety Guardrails",
            "category": "Advanced AI",
            "description": "Construct automated golden evaluation suites, groundedness judges, prompt-injection defenses, and PII redaction filters.",
            "learning_outcomes": [
                "Measure faithfulness, relevance, and regression baselines",
                "Block indirect prompt injection and jailbreak vectors",
                "Validate output schemas and PII redaction SLAs"
            ],
            "learning_topics": ["Golden Eval Sets", "LLM-as-Judge", "Prompt Injection", "Output Guardrails"],
            "prerequisites": ["badge_agt_304"],
            "project_requirements": "Author an automated CI evaluation harness and guardrail policy suite for production AI endpoints.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-01-10",
                "publication_date": "2027-01-10",
                "learning_start_date": "2027-01-11",
                "learning_end_date": "2027-01-21",
                "project_start_date": "2027-01-22",
                "project_end_date": "2027-01-31",
                "submission_deadline": "2027-02-03",
                "review_date": "2027-02-06",
                "expected_award_date": "2027-02-09"
            }
        },
        {
            "id": "badge_inf_306",
            "is_allocated": False,
            "code": "INF-306",
            "title": "High-Throughput Model Inference",
            "category": "Advanced AI",
            "description": "Scale GPU model serving with continuous batching, KV-cache quantization, speculative decoding, and latency SLO routing.",
            "learning_outcomes": [
                "Optimize tokens-per-second via continuous batching",
                "Quantize weights cleanly without quality degradation",
                "Design multi-tier model routing for cost/latency optimization"
            ],
            "learning_topics": ["Continuous Batching", "KV-Cache Tuning", "Quantization", "Model Routing"],
            "prerequisites": ["badge_ai_301"],
            "project_requirements": "Produce a serving architecture benchmark comparing quantized vs FP16 throughput under P99 SLOs.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-01-15",
                "publication_date": "2027-01-15",
                "learning_start_date": "2027-01-16",
                "learning_end_date": "2027-01-26",
                "project_start_date": "2027-01-27",
                "project_end_date": "2027-02-05",
                "submission_deadline": "2027-02-08",
                "review_date": "2027-02-11",
                "expected_award_date": "2027-02-14"
            }
        },
        {
            "id": "badge_k8s_307",
            "is_allocated": False,
            "code": "K8S-307",
            "title": "Kubernetes Workload Scaling",
            "category": "Infrastructure",
            "description": "Orchestrate containerized workloads with HPA/KEDA autoscaling, pod disruption budgets, network policies, and GitOps sync.",
            "learning_outcomes": [
                "Configure GPU and queue-depth autoscaling policies",
                "Harden namespace isolation with Kubernetes NetworkPolicies",
                "Automate progressive canary rollouts via GitOps"
            ],
            "learning_topics": ["KEDA Autoscaling", "NetworkPolicies", "Canary Rollouts", "Pod Resilience"],
            "prerequisites": ["badge_cld_202", "badge_net_203"],
            "project_requirements": "Deliver hardened Kubernetes manifests with autoscaling triggers and zero-downtime canary probes.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-01-20",
                "publication_date": "2027-01-20",
                "learning_start_date": "2027-01-21",
                "learning_end_date": "2027-01-31",
                "project_start_date": "2027-02-01",
                "project_end_date": "2027-02-10",
                "submission_deadline": "2027-02-13",
                "review_date": "2027-02-16",
                "expected_award_date": "2027-02-19"
            }
        },
        {
            "id": "badge_iac_308",
            "is_allocated": False,
            "code": "IAC-308",
            "title": "Infrastructure as Code & GitOps",
            "category": "Infrastructure",
            "description": "Manage reproducible multi-environment cloud platforms via modular Terraform state locking, drift detection, and policy checks.",
            "learning_outcomes": [
                "Structure composable IaC modules across dev/stage/prod",
                "Enforce OPA/Conftest guardrails on terraform plans",
                "Automate drift reconciliation and state-locking pipelines"
            ],
            "learning_topics": ["Terraform Modules", "OPA Policy Checks", "State Locking", "Drift Detection"],
            "prerequisites": ["badge_cld_202", "badge_k8s_307"],
            "project_requirements": "Submit a modular IaC repository blueprint with automated policy checks and drift remediation.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-01-25",
                "publication_date": "2027-01-25",
                "learning_start_date": "2027-01-26",
                "learning_end_date": "2027-02-05",
                "project_start_date": "2027-02-06",
                "project_end_date": "2027-02-15",
                "submission_deadline": "2027-02-18",
                "review_date": "2027-02-21",
                "expected_award_date": "2027-02-24"
            }
        },
        {
            "id": "badge_mon_309",
            "is_allocated": False,
            "code": "MON-309",
            "title": "Production Telemetry & SRE",
            "category": "Infrastructure",
            "description": "Operationalize golden-signal dashboards, error-budget burn alerts, chaos experiments, and automated incident runbooks.",
            "learning_outcomes": [
                "Define multi-window SLO burn-rate alerting policies",
                "Correlate metrics, structured logs, and flamegraph traces",
                "Execute automated game-day fault injection drills"
            ],
            "learning_topics": ["SLO Burn Alerts", "Prometheus/Grafana", "Chaos Engineering", "Incident Runbooks"],
            "prerequisites": ["badge_net_203", "badge_k8s_307"],
            "project_requirements": "Build a complete SRE observability stack with error-budget alerts and failure-recovery playbooks.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-02-01",
                "publication_date": "2027-02-01",
                "learning_start_date": "2027-02-02",
                "learning_end_date": "2027-02-12",
                "project_start_date": "2027-02-13",
                "project_end_date": "2027-02-22",
                "submission_deadline": "2027-02-25",
                "review_date": "2027-02-28",
                "expected_award_date": "2027-03-03"
            }
        },
        {
            "id": "badge_gov_401",
            "is_allocated": False,
            "code": "GOV-401",
            "title": "Enterprise AI Compliance & Audit",
            "category": "Governance",
            "description": "Implement immutable audit trails, model cards, bias fairness telemetry, and GDPR/AI Act regulatory readiness controls.",
            "learning_outcomes": [
                "Construct cryptographic tamper-evident decision audit logs",
                "Author standardized model risk cards and impact assessments",
                "Enforce automated right-to-erasure across data & vector stores"
            ],
            "learning_topics": ["AI Governance", "Model Risk Cards", "Immutable Audit", "Privacy Erasure"],
            "prerequisites": ["badge_gov_101", "badge_sec_204", "badge_evl_305"],
            "project_requirements": "Produce an enterprise AI compliance framework covering immutable audit logging and automated erasure.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-02-05",
                "publication_date": "2027-02-05",
                "learning_start_date": "2027-02-06",
                "learning_end_date": "2027-02-16",
                "project_start_date": "2027-02-17",
                "project_end_date": "2027-02-26",
                "submission_deadline": "2027-03-01",
                "review_date": "2027-03-04",
                "expected_award_date": "2027-03-07"
            }
        },
        {
            "id": "badge_arc_402",
            "is_allocated": False,
            "code": "ARC-402",
            "title": "Multi-Region System Architecture",
            "category": "Core Engineering",
            "description": "Architect active-active multi-region platforms balancing CAP consistency tradeoffs, geo-failover, and disaster recovery RTO/RPO.",
            "learning_outcomes": [
                "Model global replication topologies and conflict resolution",
                "Engineer sub-minute automated DNS/traffic failover",
                "Verify RPO/RTO targets through regional evacuation tests"
            ],
            "learning_topics": ["Active-Active Geo", "Conflict Resolution", "Disaster Recovery", "Global Failover"],
            "prerequisites": ["badge_k8s_307", "badge_mon_309"],
            "project_requirements": "Design an active-active two-region platform architecture achieving sub-60s failover recovery.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-02-10",
                "publication_date": "2027-02-10",
                "learning_start_date": "2027-02-11",
                "learning_end_date": "2027-02-21",
                "project_start_date": "2027-02-22",
                "project_end_date": "2027-03-03",
                "submission_deadline": "2027-03-06",
                "review_date": "2027-03-09",
                "expected_award_date": "2027-03-12"
            }
        },
        {
            "id": "badge_cap_500",
            "is_allocated": False,
            "code": "CAP-500",
            "title": "Grand Orbit Capstone Defense",
            "category": "Capstone",
            "description": "Integrate governance, real-time lakehouse pipelines, agentic AI, Kubernetes resilience, and SRE telemetry in a full academy defense.",
            "learning_outcomes": [
                "Synthesize end-to-end data, AI, and cloud architecture under real constraints",
                "Demonstrate live resilience, observability, and compliance evidence",
                "Defend architectural tradeoffs before the Guardian Evaluation Board"
            ],
            "learning_topics": ["System Integration", "Architecture Defense", "Production Readiness", "Full-Stack AIOS"],
            "prerequisites": ["badge_gov_401", "badge_arc_402"],
            "project_requirements": "Present and defend a production-grade end-to-end AI & Data platform uniting all academy disciplines.",
            "is_published": True,
            "assigned_cosmonaut_ids": [],
            "default_timeline": {
                "assignment_date": "2027-02-15",
                "publication_date": "2027-02-15",
                "learning_start_date": "2027-02-16",
                "learning_end_date": "2027-02-28",
                "project_start_date": "2027-03-01",
                "project_end_date": "2027-03-15",
                "submission_deadline": "2027-03-18",
                "review_date": "2027-03-22",
                "expected_award_date": "2027-03-25"
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
            "status": "approved",
            "pdf_name": "Astraea_Governance_Blueprint.pdf",
            "pdf_payload": "data/Chemistry%20Syllabus.pdf",
            "code_name": "healthcare_rbac_policy.sql",
            "code_payload": """-- StarApp Academy: Enterprise Data Governance Framework
-- Target: HIPAA & GDPR Compliant Relational Security & Row Filtering
CREATE SCHEMA IF NOT EXISTS clinical_vault;

CREATE TABLE clinical_vault.patient_records (
    patient_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ssn_hash VARCHAR(64) NOT NULL,
    full_name_encrypted BYTEA NOT NULL,
    diagnosis_code VARCHAR(12) NOT NULL,
    attending_physician_id UUID NOT NULL,
    data_classification VARCHAR(20) DEFAULT 'RESTRICTED_PHI'
);

ALTER TABLE clinical_vault.patient_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY practitioner_access_policy ON clinical_vault.patient_records
    FOR SELECT TO clinical_staff
    USING (attending_physician_id = current_setting('jwt.claims.physician_id')::UUID);

CREATE POLICY compliance_audit_policy ON clinical_vault.patient_records
    FOR ALL TO compliance_officer
    USING (true);""",
            "github_url": "https://github.com/starapp-cosmonauts/governance-framework-astraea"
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
            "status": "approved",
            "pdf_name": "Astraea_Dataset_Curation_Audit.pdf",
            "pdf_payload": "data/Chemistry%20Syllabus.pdf",
            "code_name": "curation_anomaly_detector.py",
            "code_payload": '''\"\"\"
StarApp Academy: Automated Dataset Curation & Anomaly Detection
Silver-layer enrichment and deduplication pipeline
\"\"\"
import pandas as pd
import numpy as np

def validate_schema_and_profile(df: pd.DataFrame) -> dict:
    profile = {
        "record_count": len(df),
        "duplicate_count": df.duplicated(subset=["telemetry_id"]).sum(),
        "missing_values": df.isnull().sum().to_dict(),
        "anomalous_outliers": []
    }
    if "latency_ms" in df.columns:
        mean_lat = df["latency_ms"].mean()
        std_lat = df["latency_ms"].std()
        outliers = df[np.abs(df["latency_ms"] - mean_lat) > (3 * std_lat)]
        profile["anomalous_outliers"] = outliers["telemetry_id"].tolist()
    return profile''',
            "github_url": "https://github.com/starapp-cosmonauts/curation-pipeline-astraea"
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
            "status": "approved",
            "pdf_name": "Astraea_Fintech_Data_Warehouse.pdf",
            "pdf_payload": "data/Chemistry%20Syllabus.pdf",
            "code_name": "fintech_dimensional_model.sql",
            "code_payload": """-- StarApp Academy: Fintech Transaction Star Schema with SCD Type 2
CREATE TABLE dim_customer_scd2 (
    customer_key BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL,
    risk_tier VARCHAR(10) NOT NULL,
    kyc_status VARCHAR(20) NOT NULL,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_to TIMESTAMP WITH TIME ZONE,
    is_current BOOLEAN DEFAULT TRUE
);

CREATE TABLE fact_ledger_transactions (
    transaction_id UUID PRIMARY KEY,
    customer_key BIGINT REFERENCES dim_customer_scd2(customer_key),
    amount_cents BIGINT NOT NULL,
    settlement_status VARCHAR(20) NOT NULL,
    transacted_at TIMESTAMP WITH TIME ZONE NOT NULL
) PARTITION BY RANGE (transacted_at);""",
            "github_url": "https://github.com/starapp-cosmonauts/fintech-warehouse-astraea"
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
            "status": "resubmission_requested",
            "pdf_name": "ING104_Draft_Spec.pdf",
            "pdf_payload": "data/Chemistry%20Syllabus.pdf",
            "code_name": "basic_kafka_consumer_v1.py",
            "code_payload": """# Attempt #1: Basic Consumer without Idempotency keys (Resubmitted)
from kafka import KafkaConsumer
consumer = KafkaConsumer("telemetry-events", bootstrap_servers=["localhost:9092"])
for msg in consumer:
    save_to_db(msg.value) # Flaw: duplicate writes on rebalance""",
            "github_url": "https://github.com/starapp-cosmonauts/ingestion-service-astraea/tree/v1"
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
            "status": "pending",
            "pdf_name": "Astraea_ING104_Idempotent_Architecture.pdf",
            "pdf_payload": "data/Chemistry%20Syllabus.pdf",
            "code_name": "idempotent_streaming_consumer.py",
            "code_payload": '''\"\"\"
StarApp Academy: High-Throughput Idempotent Kafka Stream Consumer
Batch Orion-24: Ingestion Foundations (Attempt #2 Deliverable)
Cosmonaut: Astraea Nova (cosmo_1)
Mentor: Dr. Elena Vance (guardian_1)
\"\"\"
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IdempotentIngestion")

class IdempotentKafkaConsumer:
    def __init__(self, dedup_store, dlq_publisher):
        self.dedup_store = dedup_store
        self.dlq_publisher = dlq_publisher
        self.processed_count = 0
        self.dlq_count = 0

    def process_event(self, raw_message: str) -> bool:
        try:
            payload = json.loads(raw_message)
            idempotency_key = payload.get("idempotency_key")
            if not idempotency_key:
                raise ValueError("Missing mandatory idempotency_key in payload header")

            # Check if payload was already processed (atomic deduplication check)
            if self.dedup_store.exists(idempotency_key):
                logger.info(f"Duplicate event skipped: {idempotency_key}")
                return True

            # Execute transactional ingestion
            self._write_to_primary_store(payload)
            self.dedup_store.set(idempotency_key, ttl_seconds=86400)
            self.processed_count += 1
            return True

        except Exception as exc:
            logger.error(f"Ingestion anomaly, routing to DLQ: {exc}")
            self.dlq_publisher.publish_dead_letter(raw_message, str(exc))
            self.dlq_count += 1
            return False

    def _write_to_primary_store(self, payload: Dict[str, Any]):
        logger.info(f"Successfully committed payload to Bronze ingestion lake: {payload.get('id')}")
''',
            "github_url": "https://github.com/starapp-cosmonauts/ingestion-service-astraea/tree/v2-fix"
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

    materials = []

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


if __name__ == "__main__":
    seed = get_initial_seed_data()
    print("[OK] StarApp seed_data.py is valid and verified.")
    print(f"Total Badges: {len(seed['badges'])} | Users: {len(seed['users'])} | Timelines: {len(seed['timelines'])}")

