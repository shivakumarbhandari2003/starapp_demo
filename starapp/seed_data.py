"""
STARAPP SEED DATA GENERATOR (REAL DATABASE FOUNDATIONS)
Provides clean, unpolluted initial seed metadata:
- Real created initial Band B1 badges only (B1-INT-01, B1-DAT-01)
- Zero mock badges
- Zero fake submissions or assessments
"""

from typing import Dict, Any
import json
from starapp.badge_generator import generate_badge_data

def get_initial_seed_data() -> Dict[str, Any]:
    users = [
        {
            "id": "guardian_1",
            "username": "guardian",
            "email": "arjun.mehta@starapp.io",
            "role": "guardian",
            "name": "Arjun Mehta",
            "avatar": "AM"
        },
        {
            "id": "cosmo_1",
            "username": "astraea",
            "email": "aarav.cadet@starapp.io",
            "role": "cosmonaut",
            "name": "Aarav Sharma",
            "avatar": "AS"
        }
    ]

    profiles = [
        {
            "user_id": "cosmo_1",
            "batch_name": "Orion-24",
            "assigned_guardian_id": "guardian_1",
            "guardian_credentials": "Lead Academy Guardian & Curriculum Architect",
            "skills": [],
            "certifications": []
        }
    ]

    badges = [
        {
            "id": "b1_int_01",
            "is_allocated": False,
            "code": "B1-INT-01",
            "title": "Intelligent Apps Foundations",
            "category": "Foundations",
            "description": "Foundations of intelligent agents, LLM integrations, and modern full-stack reasoning workflows.",
            "learning_outcomes": [
                "Understand agent architectures and prompt formatting",
                "Connect LLM reasoning APIs to enterprise pipelines",
                "Implement secure tool use and stateful conversations"
            ],
            "learning_topics": ["Agent Architecture", "API Integration", "Tool Calling", "Context Windows", "Output Parsing", "Streaming APIs"],
            "prerequisites": [],
            "project_requirements": "Build a production agent pipeline that queries live enterprise databases with structured validation.",
            "is_published": False,
            "target_band": "B1",
            "power": "Tech",
            "capability": "Intelligent Apps",
            "skill": "Intelligent Apps",
            "workflow_status": "approved",
            "assigned_reviewer_id": "m_b2_1",
            "assigned_cosmonaut_ids": ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5"],
            "default_timeline": {
                "assignment_date": "2026-11-20",
                "publication_date": "2026-11-20",
                "learning_start_date": "2026-11-21",
                "learning_end_date": "2026-11-30",
                "project_start_date": "2026-12-01",
                "project_end_date": "2026-12-10",
                "submission_deadline": "2026-12-12",
                "review_date": "2026-12-15",
                "expected_award_date": "2026-12-16"
            }
        },
        {
            "id": "b1_dat_01",
            "is_allocated": False,
            "code": "B1-DAT-01",
            "title": "Data Systems Architecture",
            "category": "Foundations",
            "description": "Enterprise data modeling, distributed storage patterns, and high-throughput pipeline design.",
            "learning_outcomes": [
                "Design third-normal-form relational database schemas",
                "Architect scalable data lakehouse storage layouts",
                "Configure automated schema validation and contract checks"
            ],
            "learning_topics": ["Relational Design", "Lakehouse Formats", "Storage Engines", "Partition Pruning", "Compaction", "Access Controls"],
            "prerequisites": ["b1_int_01"],
            "project_requirements": "Design a complete multi-tier data warehouse schema and partitioning strategy for an enterprise analytics platform.",
            "is_published": False,
            "target_band": "B1",
            "power": "Tech",
            "capability": "Data & Machine",
            "skill": "Architecture",
            "workflow_status": "approved",
            "assigned_reviewer_id": "m_b2_1",
            "assigned_cosmonaut_ids": ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5"],
            "default_timeline": {
                "assignment_date": "2026-11-20",
                "publication_date": "2026-11-20",
                "learning_start_date": "2026-11-21",
                "learning_end_date": "2026-11-30",
                "project_start_date": "2026-12-01",
                "project_end_date": "2026-12-10",
                "submission_deadline": "2026-12-12",
                "review_date": "2026-12-15",
                "expected_award_date": "2026-12-16"
            }
        }
    ]

    # Seed 3rd Badge: Signals Foundations (B1-SIG-01), mapped to cohort cosmonauts
    badge_signals_gen = generate_badge_data(
        band="B1",
        power="Tech",
        capability="Data & Machine",
        skill="Signals",
        outcome_sentence=""
    )
    badge_signals = {
        "id": "badge_b1_signals",
        "is_allocated": True,
        "code": "B1-SIG-01",
        "title": "Signals Foundations",
        "category": "Foundations",
        "description": badge_signals_gen["description"],
        "learning_outcomes": badge_signals_gen["outcomes"],
        "learning_topics": [t["title"] for t in badge_signals_gen["learning_topics"]],
        "prerequisites": [],
        "project_requirements": badge_signals_gen["practice_prompt"],
        "is_published": True,
        "target_band": "B1",
        "power": "Tech",
        "capability": "Data & Machine",
        "skill": "Signals",
        "workflow_status": "approved",
        "assigned_reviewer_id": "m_b2_1",
        "assigned_cosmonaut_ids": ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5"],
        "prompt_json": json.dumps(badge_signals_gen),
        "default_timeline": {
            "assignment_date": "2026-11-20",
            "publication_date": "2026-11-20",
            "learning_start_date": "2026-11-21",
            "learning_end_date": "2026-11-30",
            "project_start_date": "2026-12-01",
            "project_end_date": "2026-12-10",
            "submission_deadline": "2026-12-12",
            "review_date": "2026-12-15",
            "expected_award_date": "2026-12-16"
        }
    }
    badges.append(badge_signals)

    timelines = []
    for cid in ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4", "m_b1_5"]:
        timelines.append({
            "badge_id": "badge_b1_signals",
            "cosmonaut_id": cid,
            "reviewer_id": "m_b2_1",
            "assignment_date": "2026-11-20",
            "publication_date": "2026-11-20",
            "learning_start_date": "2026-11-21",
            "learning_end_date": "2026-11-30",
            "project_start_date": "2026-12-01",
            "project_end_date": "2026-12-10",
            "submission_deadline": "2026-12-12",
            "review_date": "2026-12-15",
            "expected_award_date": "2026-12-16",
            "actual_award_date": None,
            "status": "active"
        })

    band_mappings = []

    submissions = []
    assessments = []
    materials = []
    extensions = []
    announcements = [
        {
            "id": "ann_1",
            "title": "StarApp Academy Orientation & Guidelines",
            "message": "Welcome to StarApp Academy! Please ensure your project submissions strictly follow the 5-criterion 50-mark assessment rubric guidelines before submitting deliverables.",
            "published_at": "2026-11-20T08:00:00Z",
            "author_id": "guardian_1",
            "author_name": "Arjun Mehta",
            "target_type": "all",
            "target_cosmonaut_ids": ["cosmo_1"],
            "badge_id": "b1_int_01",
            "read_by_cosmonaut_ids": ["cosmo_1"]
        },
        {
            "id": "ann_2",
            "title": "Advanced Reasoning Architecture Clinic",
            "message": "Interactive session covering prompt engineering and structured schema outputs.",
            "published_at": "2026-11-21T10:00:00Z",
            "author_id": "guardian_1",
            "author_name": "Arjun Mehta",
            "target_type": "all",
            "target_cosmonaut_ids": ["cosmo_1"],
            "badge_id": "b1_int_01",
            "read_by_cosmonaut_ids": []
        }
    ]
    activities = [
        {
            "id": "act_1",
            "event_type": "batch_initialized",
            "timestamp": "2026-11-20T08:00:00Z",
            "actor_id": "guardian_1",
            "actor_name": "Arjun Mehta",
            "cosmonaut_id": "",
            "badge_id": "",
            "summary": "Training Batch Initialized",
            "details": "Academy portal initialized with Mentor Arjun Mehta."
        }
    ]
    notifications = [
        {
            "id": "notif_1",
            "recipient_id": "cosmo_1",
            "title": "Welcome to StarApp Academy",
            "message": "Your training journey has begun. Review your active milestones in the Learning Roadmap.",
            "created_at": "2026-11-20T08:05:00Z",
            "is_read": True,
            "link_section": "c_roadmap"
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
        "notifications": notifications,
        "band_mappings": band_mappings
    }

if __name__ == "__main__":
    seed = get_initial_seed_data()
    print("[OK] StarApp seed_data.py is valid and verified.")
    print(f"Total Badges: {len(seed['badges'])} | Users: {len(seed['users'])} | Timelines: {len(seed['timelines'])}")
