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

def build_practice_project_prompt(title: str, skill: str, capability: str, power: str, band: str, topics: List[Any], outcomes: List[str]) -> str:
    """Builds a rich, multi-line hands-on practice project prompt listing all topics and target outcomes."""
    topic_bullets = []
    for idx, t in enumerate(topics):
        if isinstance(t, dict):
            t_title = t.get("title", f"Topic {idx+1}")
            t_desc = t.get("description", "")
            topic_bullets.append(f"- {t_title}: {t_desc}" if t_desc else f"- {t_title}")
        else:
            topic_bullets.append(f"- {str(t)}")
    bullets_str = "\n".join(topic_bullets) if topic_bullets else f"- {skill} Fundamentals"
    outcomes_str = "; ".join(outcomes) if outcomes else f"Demonstrate mastery in {skill}"

    return (
        f"I'm working toward the \"{title}\" badge ({skill} / {capability} / {power}) in Band {band}.\n"
        f"I want to practice the following topics for this badge:\n"
        f"{bullets_str}\n\n"
        f"By the end I need to be able to: {outcomes_str}\n\n"
        f"Design one small, hands-on practice project that lets me demonstrate all of the topics and outcomes above together. "
        f"Include a clear task description, any starting constraints or inputs I should assume, and what a finished/successful result looks like."
    )


def build_learning_resources_prompt(title: str, skill: str, capability: str, power: str, band: str, topics: List[Any], outcomes: List[str]) -> str:
    """Builds a rich, multi-line learning resources prompt listing all topics and target outcomes."""
    topic_bullets = []
    for idx, t in enumerate(topics):
        if isinstance(t, dict):
            t_title = t.get("title", f"Topic {idx+1}")
            t_desc = t.get("description", "")
            topic_bullets.append(f"- {t_title}: {t_desc}" if t_desc else f"- {t_title}")
        else:
            topic_bullets.append(f"- {str(t)}")
    bullets_str = "\n".join(topic_bullets) if topic_bullets else f"- {skill} Fundamentals"
    outcomes_str = "; ".join(outcomes) if outcomes else f"Demonstrate mastery in {skill}"

    return (
        f"I'm working toward the \"{title}\" badge ({skill} / {capability} / {power}) in Band {band}.\n"
        f"I need free, current, high-quality learning resources (official docs, free courses, tutorials, videos) that help me learn:\n"
        f"{bullets_str}\n\n"
        f"By the end I need to be able to: {outcomes_str}\n\n"
        f"Please suggest specific free resources for each topic above (prefer official docs, free interactive tutorials, and reputable free video/blog content over paid courses), "
        f"and suggest one small hands-on project that lets me demonstrate all of the topics together."
    )


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

    # Suffix matching band progression tier
    suffix = "Foundations" if band_clean in ["B1", "B2"] else ("Architecture" if band_clean in ["B3", "B4"] else "Mastery")

    # Look up preset or synthesize customized content
    preset = SKILL_TOPIC_PRESETS.get(skill_clean)
    if preset:
        base_title = preset["title"].replace(" Foundations", "").replace(" Architecture", "").replace(" Mastery", "")
        title = f"{base_title} {suffix}"
        summary = preset["category_summary"]
        topics = preset["topics"]
        raw_outcomes = list(preset["default_outcomes"])
    else:
        title = f"{skill_clean} {suffix}"
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

    # Rich prompts
    practice_prompt = build_practice_project_prompt(title, skill_clean, cap_clean, power_clean, band_clean, topics, outcomes)
    resources_prompt = build_learning_resources_prompt(title, skill_clean, cap_clean, power_clean, band_clean, topics, outcomes)

    badge_code = f"{band_clean}-{skill_clean[:3].upper()}-01"
    badge_id = f"badge_{band_clean.lower()}_{skill_clean.lower().replace(' ', '_').replace('-', '_')}"

    return {
        "id": badge_id,
        "code": badge_code,
        "title": title,
        "description": f"{band_clean} badge specializing in {skill_clean} under the {cap_clean} capability ({power_clean} domain). {outcome_clean or ''}".strip(),
        "target_band": band_clean,
        "power": power_clean,
        "capability": cap_clean,
        "skill": skill_clean,
        "location": location_str,
        "outcomes": outcomes,
        "earn_badge_status": "Pending Review",
        "earn_badge_text": "Great job submitting your project — your guardian is reviewing it now.",
        "practice_prompt": practice_prompt,
        "resources_prompt": resources_prompt,
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


# Backward-compatibility alias
synthesize_badge_data = generate_badge_data


# ==============================================================================
# PROJECT BRIEF (what a reviewer sends to the mapped cosmonauts): sections + synthetic sample
# ==============================================================================

PROJECT_SECTIONS = (
    ("case_study", "Case Study", "text"),
    ("challenge", "Your Challenge", "text"),
    ("details", "Project Details", "list"),
    ("deliverables", "Deliverables", "list"),
    ("evaluation", "Evaluation", "list"),
)
_PROJECT_TITLE_TO_KEY = {title.lower(): key for key, title, _ in PROJECT_SECTIONS}

_PROJECT_COMPANIES = (
    ("NorthLake Retail", "an omnichannel retailer with 400 stores and a fast-growing online shop"),
    ("MediCore Health", "a regional hospital network that is digitising patient records and appointment scheduling"),
    ("SkyLine Logistics", "a freight company that tracks 20,000 shipments a day across three continents"),
    ("FinEdge Payments", "a payments start-up that processes card transactions for two million customers"),
    ("GreenGrid Energy", "a utility that is rolling out smart meters to half a million homes"),
)


def _plain_outcome(text: str) -> str:
    """'Can design a pipeline.' -> 'design a pipeline' (so it reads inside a sentence)."""
    t = str(text or "").strip().rstrip(".")
    t = t[4:] if t.lower().startswith("can ") else t
    return (t[0].lower() + t[1:]) if len(t) > 1 and t[0].isupper() and t[1].islower() else t


def generate_project_brief(badge: Any) -> Dict[str, Any]:
    """
    A synthetic but realistic project for a badge, ready to edit: a heading, a case study, the challenge, the project details,
    the deliverables (PDF report, code, GitHub) and how it is evaluated (the 50-mark rubric). Deterministic - the same badge
    always gets the same sample - and built only from the badge's own title, skill, band, outcomes and topics.
    """
    title = getattr(badge, "title", "") or "Milestone Badge"
    skill = (getattr(badge, "skill", "") or "Core Engineering").strip()
    cap = getattr(badge, "capability", "") or ""
    power = getattr(badge, "power", "") or ""
    band = getattr(badge, "target_band", "") or "B1"
    outcomes = [str(o) for o in (getattr(badge, "learning_outcomes", None) or []) if str(o).strip()]
    topics = [str(t.get("title") if isinstance(t, dict) else t) for t in (getattr(badge, "learning_topics", None) or [])]
    topics = [t for t in topics if t.strip()]
    if not outcomes or not topics:
        try:
            gen = generate_badge_data(band=band, power=power or "Tech", capability=cap or "Data & Machine", skill=skill, outcome_sentence="")
            outcomes = outcomes or list(gen.get("outcomes", []))
            topics = topics or [t["title"] for t in gen.get("learning_topics", [])]
        except Exception:
            pass

    company, about = _PROJECT_COMPANIES[(sum(ord(c) for c in skill + band)) % len(_PROJECT_COMPANIES)]
    low = skill.lower()
    slug = low.replace(" ", "_").replace("&", "and").replace("-", "_")
    ghslug = low.replace(" ", "-").replace("&", "and")
    ocs = [_plain_outcome(o) for o in outcomes[:3]]

    heading = f"{company}: The {skill} Challenge"
    case_study = (
        f"{company} is {about}. Its engineering team has been asked to strengthen how the business handles {low}, because delays and "
        f"incidents in this area are starting to cost real time and customer trust.\n\n"
        f"You have joined the team as a Band {band} engineer working toward the \"{title}\" badge"
        f"{f' ({power} / {cap})' if power or cap else ''}. Your reviewer plays the role of the engineering lead: "
        f"you report to them and you will present your solution to them."
    )
    challenge = (
        f"Design and build a small but production-minded {low} solution for {company}. "
        + (f"Show that you can {', '.join(ocs[:-1])} and {ocs[-1]}. " if len(ocs) > 1 else (f"Show that you can {ocs[0]}. " if ocs else ""))
        + "Explain every important choice you make and the alternatives you rejected."
    )
    details = []
    if topics:
        details.append(f"Cover the core of {skill}: {', '.join(topics[:3])}" + (f" and {topics[3]}." if len(topics) > 3 else "."))
    for o in outcomes[:3]:
        details.append(f"Demonstrate this outcome clearly: {str(o).strip().rstrip('.')}.")
    details += [
        f"Work to Band {band} engineering standards: a clear structure, error handling, logging and tests.",
        "State every assumption you make. Synthetic or sample data is fine; say where it comes from.",
        "Keep the scope realistic for the time you have - a small, finished solution beats a large, unfinished one.",
    ]
    deliverables = [
        f"PDF report ({skill.replace(' ', '_')}_Report.pdf): the problem, your design, the trade-offs you weighed, and what you would do next.",
        f"Source code ({slug}.py): readable, modular code with comments, error handling and a short run guide.",
        f"GitHub repository (github.com/your-handle/{ghslug}-project): the code, a README with setup steps, tests and a clean commit history.",
    ]
    evaluation = [
        "Business understanding (10 marks): you framed the problem and its goals correctly.",
        "Architecture report (10 marks): the design, interfaces and failure cases are explained and justified.",
        "Technical knowledge (10 marks): the code is correct, efficient and idiomatic.",
        "Presentation (10 marks): the repository, documentation and walkthrough are clear.",
        "Q&A defense (10 marks): you can justify your trade-offs and handle edge cases when questioned.",
    ]
    return {
        "title": heading,
        "case_study": case_study,
        "challenge": challenge,
        "details": details,
        "deliverables": deliverables,
        "evaluation": evaluation,
    }


def compose_project_content(sections: Dict[str, Any]) -> str:
    """Sections dict -> the text stored as the project's content ('Case Study', blank line, ..., bullet lists as '- ' lines)."""
    blocks = []
    for key, title, kind in PROJECT_SECTIONS:
        val = sections.get(key)
        if kind == "list":
            items = [str(i).strip().lstrip("-*\u2022 ").strip() for i in (val or []) if str(i).strip()]
            body = "\n".join(f"- {i}" for i in items)
        else:
            body = str(val or "").strip()
        if body:
            blocks.append(f"{title}\n{body}")
    return "\n\n".join(blocks)


def parse_project_content(content: str) -> Optional[Dict[str, Any]]:
    """
    Inverse of `compose_project_content`. Returns None unless the text has at least two of the known section headings on their
    own lines - older free-text projects keep rendering exactly as they were written.
    """
    sections: Dict[str, List[str]] = {}
    current = None
    for line in str(content or "").splitlines():
        head = line.strip().rstrip(":").strip().lower()
        if head in _PROJECT_TITLE_TO_KEY:
            current = _PROJECT_TITLE_TO_KEY[head]
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    if len(sections) < 2:
        return None
    out: Dict[str, Any] = {}
    for key, title, kind in PROJECT_SECTIONS:
        lines = sections.get(key)
        if lines is None:
            continue
        if kind == "list":
            out[key] = [ln.strip().lstrip("-*\u2022 ").strip() for ln in lines if ln.strip()]
        else:
            out[key] = "\n".join(lines).strip()
    return out


# ==============================================================================
# STRUCTURED BADGE (prompt_json) HELPERS - shared by the Guardian and Reviewer portals
# ==============================================================================

PRACTICE_PROJECT_INTRO = "Want some hands-on practice? Use this prompt to generate a practice project."
PRACTICE_PROJECT_FOOTNOTE = "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
LEARNING_RESOURCES_INTRO = "Not sure where to start learning? Use this prompt to find free resources tailored to this badge."
LEARNING_RESOURCES_FOOTNOTE = "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."


def _prompt_is_placeholder(prompt: str) -> bool:
    text = (prompt or "").strip()
    return (not text) or len(text) < 120 or "\n-" not in text


def set_practice_prompt(data: Dict[str, Any], prompt: str) -> None:
    """Writes the practice-project prompt to both places the structured badge keeps it."""
    if not isinstance(data.get("practice_project"), dict):
        data["practice_project"] = {"intro": PRACTICE_PROJECT_INTRO, "prompt": prompt, "footnote": PRACTICE_PROJECT_FOOTNOTE}
    else:
        data["practice_project"]["prompt"] = prompt
    data["practice_prompt"] = prompt


def set_resources_prompt(data: Dict[str, Any], prompt: str) -> None:
    """Writes the learning-resources prompt to both places the structured badge keeps it."""
    if not isinstance(data.get("learning_resources"), dict):
        data["learning_resources"] = {"intro": LEARNING_RESOURCES_INTRO, "prompt": prompt, "footnote": LEARNING_RESOURCES_FOOTNOTE}
    else:
        data["learning_resources"]["prompt"] = prompt
    data["resources_prompt"] = prompt


def complete_badge_prompts(data: Dict[str, Any], title: str, skill: str, capability: str, power: str, band: str) -> Dict[str, Any]:
    """
    Defense-in-depth: a practice / resources prompt that is missing or a one-line placeholder is replaced by the full
    curriculum prompt. Prompts a reviewer has edited (`reviewed_by` is set) are never replaced - the reviewer may
    legitimately shorten them. Mutates and returns `data`.
    """
    outcomes = data.get("outcomes") or data.get("learning_outcomes") or []
    topics = data.get("learning_topics") or []
    pp = data.get("practice_project")
    practice = (pp.get("prompt", "") if isinstance(pp, dict) else (str(pp) if pp else "")) or data.get("practice_prompt", "")
    lr = data.get("learning_resources")
    resources = (lr.get("prompt", "") if isinstance(lr, dict) else (str(lr) if lr else "")) or data.get("resources_prompt", "")
    reviewed = bool(data.get("reviewed_by"))
    if not (practice or "").strip() or (not reviewed and _prompt_is_placeholder(practice)):
        practice = build_practice_project_prompt(title, skill, capability, power, band, topics, outcomes)
    if not (resources or "").strip() or (not reviewed and _prompt_is_placeholder(resources)):
        resources = build_learning_resources_prompt(title, skill, capability, power, band, topics, outcomes)
    set_practice_prompt(data, practice)
    set_resources_prompt(data, resources)
    return data


def apply_badge_edits(data: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies the fields collected by the badge edit form (title, description, outcomes, practice_prompt,
    resources_prompt, topics) to a structured badge dict. A blank title keeps the old one. Mutates and returns `data`.
    """
    if not isinstance(payload, dict):
        return data
    title = payload.get("title")
    if isinstance(title, str) and title.strip():
        data["title"] = title.strip()
    if "description" in payload:
        data["description"] = str(payload.get("description") or "").strip()
    if "outcomes" in payload:
        outs = payload["outcomes"]
        if isinstance(outs, str):
            outs = outs.split("\n")
        data["outcomes"] = [str(o).strip() for o in (outs or []) if str(o).strip()]
    if "practice_prompt" in payload:
        set_practice_prompt(data, str(payload.get("practice_prompt") or ""))
    if "resources_prompt" in payload:
        set_resources_prompt(data, str(payload.get("resources_prompt") or ""))
    topics = payload.get("topics")
    if isinstance(topics, list):
        data["learning_topics"] = [t for t in topics if isinstance(t, dict)]
    return data


def structured_badge_from_row(badge: Any) -> Dict[str, Any]:
    """
    The structured badge dict (the shape the Guardian authored it in) for a saved Badge. `prompt_json` is authoritative;
    a badge without one (seeded / legacy) is built from the generator and overlaid with the real columns.
    """
    data: Dict[str, Any] = {}
    raw = getattr(badge, "prompt_json", "") or ""
    if raw:
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, dict):
                data = parsed
        except Exception:
            data = {}
    band = getattr(badge, "target_band", "") or "B1"
    power = getattr(badge, "power", "") or "Tech"
    cap = getattr(badge, "capability", "") or "Data & Machine"
    skill = getattr(badge, "skill", "") or "Hardware"
    if not data:
        data = generate_badge_data(band=band, power=power, capability=cap, skill=skill, outcome_sentence="")
        if getattr(badge, "title", ""):
            data["title"] = badge.title
        if getattr(badge, "description", ""):
            data["description"] = badge.description
        if getattr(badge, "learning_outcomes", None):
            data["outcomes"] = [str(o) for o in badge.learning_outcomes]
        titles = [str(t.get("title") if isinstance(t, dict) else t) for t in (getattr(badge, "learning_topics", None) or [])]
        if titles:
            by_title = {t.get("title"): t for t in data.get("learning_topics", []) if isinstance(t, dict)}
            data["learning_topics"] = [
                dict(by_title.get(t) or {"title": t, "description": "", "status": "In Progress", "completed": False}) for t in titles
            ]
        if getattr(badge, "project_requirements", ""):
            set_practice_prompt(data, badge.project_requirements)
    if not data.get("outcomes") and data.get("learning_outcomes"):
        data["outcomes"] = list(data["learning_outcomes"])
    data["target_band"] = band
    data["power"], data["capability"], data["skill"] = power, cap, skill
    return complete_badge_prompts(data, data.get("title") or badge.title, skill, cap, power, band)


def generate_reviewer_project_spec(
    band: str = "B1",
    power: str = "Tech",
    capability: str = "Data & Machine",
    skill: str = "Signals",
    badge_title: str = "Signals Foundations",
    reviewer_name: str = "Institutional Reviewer"
) -> Dict[str, Any]:
    """
    Generates a structured, industry-aligned milestone project specification
    authored by higher-band reviewers for mapped cadets.
    """
    skill_clean = skill.strip() if skill else "Core Engineering"
    proj_title = f"{skill_clean} Enterprise Pipeline & Architecture Project"
    scenario = (
        f"As an engineering cadet working toward '{badge_title}' (Band {band} • {power} › {capability}), "
        f"you are tasked with implementing a production-ready, fault-tolerant {skill_clean.lower()} system. "
        f"Your deliverables must satisfy rigorous industry resilience standards, modular design patterns, "
        f"and include clear telemetry hooks for auditability."
    )
    deliverables = {
        "code": {
            "name": f"{skill_clean.lower().replace(' ', '_')}_pipeline.py",
            "format": "Python Script (.py)",
            "description": f"Modular, executable implementation of core {skill_clean.lower()} mechanics with comprehensive logging and error handling."
        },
        "pdf": {
            "name": f"{skill_clean.replace(' ', '_')}_Architecture_Report.pdf",
            "format": "PDF Technical Spec",
            "description": f"End-to-end architecture specification detailing component interfaces, data flow topologies, resilience strategies, and failure recovery."
        },
        "github": {
            "name": f"https://github.com/starapp-cadets/{skill_clean.lower().replace(' ', '-')}-project",
            "format": "Git Repository",
            "description": "Version-controlled repository containing source code, README setup instructions, tests, and CI/CD workflow configuration."
        }
    }
    requirements = [
        f"1. Implement core pipeline logic in executable code meeting Band {band} engineering benchmarks.",
        f"2. Provide robust exception handling, structured JSON logging, and configuration management.",
        f"3. Author a structured PDF Architecture Report answering scalability, security, and component trade-offs.",
        f"4. Provide a public or accessible GitHub repository link with clean commit history.",
        f"5. Prepare a technical walkthrough and Q&A defense addressing all 5 rubric criteria."
    ]
    rubric_guidelines = {
        "business_understanding": "Domain scope formulation, problem definition, and operational objectives (Max: 10 Marks).",
        "architecture_report": "System topology, interface specifications, failure mode analysis, and diagrams (Max: 10 Marks).",
        "technical_knowledge": "Idiomatic code execution, data structure efficiency, and modularity (Max: 10 Marks).",
        "presentation": "Clean repository structure, documentation clarity, and coherent walkthrough (Max: 10 Marks).",
        "qa": "Technical justification of architectural trade-offs, edge-case resilience, and defense (Max: 10 Marks)."
    }
    return {
        "title": proj_title,
        "scenario": scenario,
        "badge_title": badge_title,
        "band": band,
        "power": power,
        "capability": capability,
        "skill": skill_clean,
        "reviewer_name": reviewer_name,
        "deliverables": deliverables,
        "requirements": requirements,
        "rubric_guidelines": rubric_guidelines,
        "timeline_prep_note": "3 Days allocated for concept learning and project sprint preparation before milestone deliverable submission."
    }


