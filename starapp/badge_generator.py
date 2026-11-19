"""
STARAPP BADGE GENERATOR ENGINE
Generates rich, structured engineering badges based on Power, Capability, Skill, Band,
and Outcome Sentence. Adheres to the exact layout and content specification from
StarApp curriculum architecture and Gemini API integration.
"""

import json
from typing import Dict, Any, List, Optional

# ==============================================================================
# TAXONOMY SPECIFICATIONS
# ==============================================================================

POWERS_LIST: List[str] = ["Domain", "Tech", "Leadership"]

CAPABILITIES_LIST: List[str] = [
    "Data & Machine",
    "Reasoning",
    "Action",
    "Outcome",
    "Trust"
]

CAPABILITY_SKILLS_MAP: Dict[str, List[str]] = {
    "Data & Machine": [
        "Hardware", "Software", "Network", "Cloud", "AI-OS",
        "Data Model", "Architecture", "Ingestion", "Curation", "Governance"
    ],
    "Reasoning": [
        "Descriptive", "Diagnostic", "Predictive", "Prescriptive"
    ],
    "Action": [
        "Agents", "Controls", "Signals", "Feedback"
    ],
    "Outcome": [
        "Intelligent Apps", "HITL", "HOTL"
    ],
    "Trust": [
        "Security", "Drift", "Audit", "Reliability"
    ]
}

BAND_DEFAULT_OUTCOME_SENTENCES: Dict[str, str] = {
    "B1": "Identify CPU, memory, storage, and GPU components in a given system spec and describe their basic roles",
    "B2": "Design, configure, and evaluate modular system components and services against operational benchmarks",
    "B3": "Architect and deploy resilient distributed pipelines with automated telemetry and error recovery",
    "B4": "Lead enterprise-scale system optimization, cross-functional architectural reviews, and governance",
    "B5": "Establish strategic engineering paradigms, advanced fault-tolerant topologies, and AI governance standards",
    "B6": "Pioneer breakthrough system architectures, executive council technical roadmaps, and industry patents"
}

# Rich topic and skill taxonomy presets
SKILL_TOPIC_PRESETS: Dict[str, Dict[str, Any]] = {
    "Curation": {
        "title": "Curation Foundations",
        "category_summary": "core data curation concepts — data modeling, semantic layers, entity resolution, business metrics, transformation logic, and data lineage",
        "topics": [
            {
                "title": "Data modeling for curation",
                "description": "Recognizing how dimensional, domain, and product data models can be used to structure curated data for downstream consumption."
            },
            {
                "title": "Semantic layer fundamentals",
                "description": "Explaining how a semantic layer provides consistent business meaning and definitions across curated data and analytics use cases."
            },
            {
                "title": "Entity resolution fundamentals",
                "description": "Recognizing how records representing the same real-world entity can be identified and consolidated across different data sources."
            },
            {
                "title": "Business metric definitions",
                "description": "Defining business metrics with clear and consistent meanings, calculations, and measurement rules."
            },
            {
                "title": "Transformation logic",
                "description": "Explaining how raw data is transformed, standardized, and prepared for reliable downstream analysis and consumption."
            },
            {
                "title": "Lineage awareness",
                "description": "Recognizing how data lineage helps trace curated data back to its source and understand how it has been transformed."
            }
        ],
        "default_outcomes": [
            "Can recognize appropriate data modeling approaches for curated data used by different consumers.",
            "Can explain how semantic layers and business metric definitions create consistent meaning across analytics.",
            "Can recognize basic entity resolution and transformation techniques used to prepare reliable data.",
            "Can use basic lineage awareness to understand where curated data originated and how it was transformed."
        ]
    },
    "Hardware": {
        "title": "Hardware Foundations",
        "category_summary": "core hardware concepts — CPU architectures, memory hierarchy, persistent storage, GPU acceleration, and system bus interfaces",
        "topics": [
            {
                "title": "CPU & processor architecture",
                "description": "Recognizing instruction pipelines, ALU operations, register sets, and multicore execution models."
            },
            {
                "title": "Memory hierarchy & caching",
                "description": "Explaining L1/L2/L3 cache latency, RAM access timing, and virtual memory page translation."
            },
            {
                "title": "Storage subsystems",
                "description": "Evaluating NVMe, PCIe bus throughput, and persistent block device I/O characteristics."
            },
            {
                "title": "GPU & parallel compute",
                "description": "Understanding SIMD execution models, GPU streaming multiprocessors, and tensor cores."
            },
            {
                "title": "System bus & interconnects",
                "description": "Describing PCIe lanes, memory controllers, and DMA data transfer mechanisms."
            },
            {
                "title": "Hardware benchmarking",
                "description": "Measuring FLOPS, memory bandwidth, and thermal throttling limits under compute load."
            }
        ],
        "default_outcomes": [
            "Can identify CPU, memory, storage, and GPU components in a given system spec and describe their basic roles.",
            "Can explain how processor cache hierarchies and system memory bandwidth impact application execution speeds.",
            "Can recognize persistent storage types (NVMe, SSD, HDD) and select appropriate storage tiers for data workloads.",
            "Can evaluate GPU compute architecture and parallel processing advantages for modern machine learning workflows."
        ]
    },
    "Software": {
        "title": "Software Engineering Foundations",
        "category_summary": "core software engineering concepts — runtime environments, compiler toolchains, memory management, concurrency, and packaging",
        "topics": [
            {
                "title": "Runtime environments",
                "description": "Understanding process isolation, WebAssembly VM sandboxes, and bytecode interpretation."
            },
            {
                "title": "Memory management & lifecycles",
                "description": "Explaining stack vs. heap allocation, garbage collection strategies, and pointer safety."
            },
            {
                "title": "Concurrency & asynchronous execution",
                "description": "Implementing event loops, coroutines, thread safety, and race condition prevention."
            },
            {
                "title": "Modular software packaging",
                "description": "Managing software dependencies, semantic versioning, and deterministic build artifacts."
            },
            {
                "title": "Performance profiling & tracing",
                "description": "Profiling CPU hotspots, memory leak detection, and micro-benchmark optimization."
            },
            {
                "title": "Software interface design",
                "description": "Authoring clean API contracts, error boundaries, and defensive data validation logic."
            }
        ],
        "default_outcomes": [
            "Can analyze runtime process execution and optimize memory allocation patterns.",
            "Can implement asynchronous concurrency patterns without blocking the main event loop.",
            "Can structure modular packages with deterministic dependency versioning.",
            "Can profile application performance and eliminate CPU or memory bottlenecks."
        ]
    },
    "Cloud": {
        "title": "Cloud Architecture Foundations",
        "category_summary": "core cloud architecture concepts — virtual networks, serverless compute, storage tiers, IAM security, and multi-region resilience",
        "topics": [
            {
                "title": "Virtual private clouds & subnets",
                "description": "Designing isolated VPC network topologies, CIDR blocks, and secure routing tables."
            },
            {
                "title": "Container orchestration",
                "description": "Managing containerized microservices, ingress controllers, and auto-scaling pods."
            },
            {
                "title": "Serverless compute paradigms",
                "description": "Configuring event-driven function executions, cold-start mitigation, and timeout thresholds."
            },
            {
                "title": "Identity & access management",
                "description": "Enforcing least-privilege RBAC roles, service accounts, and temporary token federation."
            },
            {
                "title": "Cloud storage architectures",
                "description": "Selecting object stores, block volumes, and managed distributed databases."
            },
            {
                "title": "High availability & disaster recovery",
                "description": "Configuring cross-zone replication, automated health probes, and failover topologies."
            }
        ],
        "default_outcomes": [
            "Can design resilient cloud VPC topologies with secure ingress and egress boundaries.",
            "Can configure scalable container and serverless workloads with auto-scaling triggers.",
            "Can implement least-privilege IAM policies and service account token federation.",
            "Can evaluate multi-zone redundancy and disaster recovery configurations."
        ]
    },
    "Security": {
        "title": "Security & Trust Engineering",
        "category_summary": "core security concepts — zero-trust networking, cryptography, prompt injection defense, audit trails, and access control",
        "topics": [
            {
                "title": "Zero-trust network architecture",
                "description": "Enforcing mutual TLS, strict identity verification, and microsegmentation."
            },
            {
                "title": "Data encryption & secret management",
                "description": "Implementing envelope encryption, KMS key rotation, and secure secret vaults."
            },
            {
                "title": "Adversarial prompt & injection defense",
                "description": "Applying boundary delimiters, input sanitization, and output validation safeguards."
            },
            {
                "title": "Role-based access control",
                "description": "Enforcing granular role and permission matrices with principle of least privilege."
            },
            {
                "title": "Immutable audit trails",
                "description": "Recording tamper-evident audit logs and cryptographic chain-of-custody receipts."
            },
            {
                "title": "Vulnerability assessment & hardening",
                "description": "Running static dependency audits, penetration analysis, and runtime container hardening."
            }
        ],
        "default_outcomes": [
            "Can implement zero-trust network boundaries and mutual TLS encryption.",
            "Can defend against adversarial input injection and unauthorized data exfiltration.",
            "Can enforce fine-grained role-based access control across API endpoints.",
            "Can maintain tamper-evident audit logs and compliance attestation records."
        ]
    }
}

# ==============================================================================
# BADGE GENERATOR IMPLEMENTATION
# ==============================================================================

def generate_badge_data(
    band: str,
    power: str,
    capability: str,
    skill: str,
    outcome_sentence: str
) -> Dict[str, Any]:
    """
    Generates structured badge data adhering to the exact StarApp visual layout specification.
    """
    band_clean = band.upper().strip() if band else "B1"
    power_clean = power.strip() if power else "Tech"
    cap_clean = capability.strip() if capability else "Data & Machine"
    skill_clean = skill.strip() if skill else "Hardware"
    outcome_clean = outcome_sentence.strip() if outcome_sentence else BAND_DEFAULT_OUTCOME_SENTENCES.get(band_clean, "")

    # Look up preset or synthesize customized content
    preset = SKILL_TOPIC_PRESETS.get(skill_clean)
    if preset:
        title = preset["title"]
        summary = preset["category_summary"]
        topics = preset["topics"]
        raw_outcomes = list(preset["default_outcomes"])
    else:
        title = f"{skill_clean} Foundations" if band_clean in ["B1", "B2"] else (f"{skill_clean} Architecture" if band_clean in ["B3", "B4"] else f"{skill_clean} Mastery")
        summary = f"core {skill_clean.lower()} concepts and practices — design, implementation, operational telemetry, and performance optimization"
        topics = [
            {"title": f"{skill_clean} fundamentals", "description": f"Understanding foundational {skill_clean.lower()} concepts, architectural primitives, and lifecycle management."},
            {"title": f"{skill_clean} system modeling", "description": f"Designing structured models, interface boundaries, and contract specifications for {skill_clean.lower()}."},
            {"title": f"{skill_clean} integration & telemetry", "description": f"Integrating {skill_clean.lower()} services with automated telemetry, health checks, and error logging."},
            {"title": f"{skill_clean} optimization", "description": f"Tuning execution throughput, latency boundaries, and resource utilization for {skill_clean.lower()}."},
            {"title": f"{skill_clean} verification & testing", "description": f"Implementing robust test suites, validation harnesses, and benchmark verification."},
            {"title": f"{skill_clean} governance & reliability", "description": f"Applying operational governance, access boundaries, and failure-recovery mechanisms."}
        ]
        raw_outcomes = [
            f"Can explain foundational {skill_clean.lower()} principles and operational constraints.",
            f"Can design and implement robust {skill_clean.lower()} components meeting architectural specifications.",
            f"Can verify and benchmark {skill_clean.lower()} behavior under rigorous performance conditions.",
            f"Can establish reliable operational boundaries and telemetry for {skill_clean.lower()} workloads."
        ]

    # Incorporate user-specified outcome sentence into the outcomes list
    if outcome_clean:
        formatted_outcome = outcome_clean if outcome_clean.startswith("Can ") else f"Can {outcome_clean[0].lower() + outcome_clean[1:]}"
        if not formatted_outcome.endswith("."):
            formatted_outcome += "."
        # Place as first outcome
        outcomes = [formatted_outcome] + [o for o in raw_outcomes if o.lower() != formatted_outcome.lower()][:3]
    else:
        outcomes = raw_outcomes[:4]

    # Location breadcrumb string: Badge name -> skill name -> capability name -> power name -> Band number
    location_str = f"{title} -> {skill_clean} -> {cap_clean} -> {power_clean} -> Band {band_clean}"

    # Build topics description bullets for LLM prompts
    topics_bullets = "\n".join([f"- {t['title']}: {t['description']}" for t in topics])
    outcomes_semicolon = "; ".join(outcomes)

    # Practice Project Prompt (matching user prompt & screenshot)
    practice_prompt = (
        f"I'm working toward the \"{title}\" badge ({skill_clean} / {cap_clean} / {power_clean}).\n"
        f"I want to practice the following topics for this badge:\n"
        f"{topics_bullets}\n\n"
        f"By the end I need to be able to: {outcomes_semicolon}\n\n"
        f"Design one small, hands-on practice project that lets me demonstrate all of the topics and outcomes above together. "
        f"Include a clear task description, any starting constraints or inputs I should assume, and what a finished/successful result looks like."
    )

    # Learning Resources Prompt (matching user prompt & screenshot)
    resources_prompt = (
        f"I'm working toward the \"{title}\" badge ({skill_clean} / {cap_clean} / {power_clean}).\n"
        f"I need free, current, high-quality learning resources (official docs, free courses, tutorials, videos) that help me learn:\n"
        f"{topics_bullets}\n\n"
        f"By the end I need to be able to: {outcomes_semicolon}\n\n"
        f"Please suggest specific free resources for each topic above (prefer official docs, free interactive tutorials, and reputable free video/blog content over paid courses), "
        f"and suggest one small hands-on project that lets me demonstrate all of the topics together."
    )

    badge_code = f"{band_clean}-{skill_clean[:3].upper()}-01"
    badge_id = f"badge_{band_clean.lower()}_{skill_clean.lower().replace(' ', '_').replace('-', '_')}"

    return {
        "id": badge_id,
        "code": badge_code,
        "title": title,
        "description": f"Foundational badge covering {summary}.",
        "target_band": band_clean,
        "power": power_clean,
        "capability": cap_clean,
        "skill": skill_clean,
        "location": location_str,
        "outcomes": outcomes,
        "earn_badge_status": "Pending Review",
        "earn_badge_text": "Great job submitting your project — your guardian is reviewing it now.",
        "practice_project": {
            "intro": "Want some hands-on practice? Use this prompt to generate a practice project.",
            "prompt": practice_prompt,
            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
        },
        "learning_topics": [
            {
                "title": t["title"],
                "status": "In Progress",
                "completed": False,
                "description": t["description"]
            }
            for t in topics
        ],
        "learning_resources": {
            "intro": "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
            "prompt": resources_prompt,
            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
        },
        "related": {
            "skill": skill_clean,
            "capability": cap_clean,
            "power": power_clean
        }
    }
