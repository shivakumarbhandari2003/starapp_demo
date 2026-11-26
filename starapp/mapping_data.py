"""
STARAPP BAND & ROLE COMPETENCY MAPPING DATA
Provides static definitions for Bands B1 to B6, the 3 technical roles,
36 distinct dummy members (6 per band, 2 per role), and the curriculum badge catalog.
"""

from typing import List, Dict, Any, Optional, Union

# ==============================================================================
# 1. BANDS SPECIFICATION (B1 to B6)
# ==============================================================================

BANDS: List[Dict[str, Any]] = [
    {
        "code": "B1",
        "name": "Band 1",
        "title": "Foundation Associate",
        "level": "Entry / Graduate",
        "experience": "0 – 2 years",
        "description": "Foundational engineering practices, algorithmic problem-solving, and core platform delivery."
    },
    {
        "code": "B2",
        "name": "Band 2",
        "title": "Specialist",
        "level": "Intermediate",
        "experience": "2 – 4 years",
        "description": "Autonomous technical execution, modular design, pipeline implementation, and test automation."
    },
    {
        "code": "B3",
        "name": "Band 3",
        "title": "Senior Specialist",
        "level": "Senior",
        "experience": "4 – 7 years",
        "description": "Complex domain architecture, system optimization, cross-module integration, and peer mentorship."
    },
    {
        "code": "B4",
        "name": "Band 4",
        "title": "Lead Engineer",
        "level": "Lead",
        "experience": "7 – 10 years",
        "description": "Strategic technical leadership, architectural decision records, scalability, and code governance."
    },
    {
        "code": "B5",
        "name": "Band 5",
        "title": "Principal Architect",
        "level": "Principal",
        "experience": "10 – 14 years",
        "description": "Multi-region distributed systems, enterprise data fabric, zero-trust security, and technical roadmapping."
    },
    {
        "code": "B6",
        "name": "Band 6",
        "title": "Chief / Distinguished Fellow",
        "level": "Executive Fellow",
        "experience": "14+ years",
        "description": "Organizational technical strategy, frontier research, quantum & autonomous agent governance."
    }
]

BAND_CODES: List[str] = [b["code"] for b in BANDS]

# ==============================================================================
# 2. ROLES SPECIFICATION
# ==============================================================================

ROLES: List[str] = [
    "Solutions Designer",
    "AI Engineer",
    "Systems Engineer"
]

ROLE_CONFIG: Dict[str, Dict[str, str]] = {
    "Solutions Designer": {
        "color": "#4F46E5",
        "bg": "rgba(79, 70, 229, 0.12)",
        "border": "rgba(79, 70, 229, 0.35)",
        "icon": "layers",
        "short": "SD",
        "desc": "System architecture, domain modeling & solution workflows"
    },
    "AI Engineer": {
        "color": "#059669",
        "bg": "rgba(5, 150, 105, 0.12)",
        "border": "rgba(5, 150, 105, 0.35)",
        "icon": "cpu",
        "short": "AIE",
        "desc": "Machine learning pipelines, agent orchestration & LLM reasoning"
    },
    "Systems Engineer": {
        "color": "#0284C7",
        "bg": "rgba(2, 132, 199, 0.12)",
        "border": "rgba(2, 132, 199, 0.35)",
        "icon": "terminal",
        "short": "SE",
        "desc": "Infrastructure, networking, distributed reliability & cloud fabric"
    }
}

# ==============================================================================
# ==============================================================================
# 3. 36 CORPORATE HIERARCHY DEMO MEMBERS ACROSS B1 TO B6 & CEO
# ==============================================================================

DUMMY_MEMBERS: List[Dict[str, Any]] = [
    # Band B1 (Foundation Associate) - 6 Members
    {
        "id": "m_b1_1", "band": "B1", "name": "Aarav Sharma", "age": 26, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "aarav.sharma",
        "avatar": "AS", "email": "aarav.sharma@starapp.io", "password": "12345678",
        "reporting_manager": "Rohan Deshmukh (B2)", "reporting_manager_id": "m_b2_1", "reporting_manager_name": "Rohan Deshmukh", "reporting_manager_band": "B2",
        "application_roles": ["cosmonaut"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b1_2", "band": "B1", "name": "Ananya Iyer", "age": 25, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "ananya.iyer",
        "avatar": "AI", "email": "ananya.iyer@starapp.io", "password": "12345678",
        "reporting_manager": "Rohan Deshmukh (B2)", "reporting_manager_id": "m_b2_1", "reporting_manager_name": "Rohan Deshmukh", "reporting_manager_band": "B2",
        "application_roles": ["cosmonaut"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b1_3", "band": "B1", "name": "Vivaan Patel", "age": 27, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "vivaan.patel",
        "avatar": "VP", "email": "vivaan.patel@starapp.io", "password": "12345678",
        "reporting_manager": "Rohan Deshmukh (B2)", "reporting_manager_id": "m_b2_1", "reporting_manager_name": "Rohan Deshmukh", "reporting_manager_band": "B2",
        "application_roles": ["cosmonaut"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b1_4", "band": "B1", "name": "Kavya Reddy", "age": 26, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "kavya.reddy",
        "avatar": "KR", "email": "kavya.reddy@starapp.io", "password": "12345678",
        "reporting_manager": "Aditya Kulkarni (B2)", "reporting_manager_id": "m_b2_3", "reporting_manager_name": "Aditya Kulkarni", "reporting_manager_band": "B2",
        "application_roles": ["cosmonaut"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b1_5", "band": "B1", "name": "Ishaan Gupta", "age": 28, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "ishaan.gupta",
        "avatar": "IG", "email": "ishaan.gupta@starapp.io", "password": "12345678",
        "reporting_manager": "Aditya Kulkarni (B2)", "reporting_manager_id": "m_b2_3", "reporting_manager_name": "Aditya Kulkarni", "reporting_manager_band": "B2",
        "application_roles": ["cosmonaut"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b1_6", "band": "B1", "name": "Diya Chatterjee", "age": 25, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "diya.chatterjee",
        "avatar": "DC", "email": "diya.chatterjee@starapp.io", "password": "12345678",
        "reporting_manager": "Aditya Kulkarni (B2)", "reporting_manager_id": "m_b2_3", "reporting_manager_name": "Aditya Kulkarni", "reporting_manager_band": "B2",
        "application_roles": ["cosmonaut"], "status": "active", "is_demo": False
    },

    # Band B2 (Specialist) - 6 Members (2 Managers, 4 ICs)
    {
        "id": "m_b2_1", "band": "B2", "name": "Rohan Deshmukh", "age": 31, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "rohan.deshmukh",
        "avatar": "RD", "email": "rohan.deshmukh@starapp.io", "password": "12345678",
        "reporting_manager": "Vikram Rao (B3)", "reporting_manager_id": "m_b3_1", "reporting_manager_name": "Vikram Rao", "reporting_manager_band": "B3",
        "direct_reports": ["m_b1_1", "m_b1_2", "m_b1_3"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b2_2", "band": "B2", "name": "Meera Nair", "age": 29, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "meera.nair",
        "avatar": "MN", "email": "meera.nair@starapp.io", "password": "12345678",
        "reporting_manager": "Vikram Rao (B3)", "reporting_manager_id": "m_b3_1", "reporting_manager_name": "Vikram Rao", "reporting_manager_band": "B3",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b2_3", "band": "B2", "name": "Aditya Kulkarni", "age": 32, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "aditya.kulkarni",
        "avatar": "AK", "email": "aditya.kulkarni@starapp.io", "password": "12345678",
        "reporting_manager": "Vikram Rao (B3)", "reporting_manager_id": "m_b3_1", "reporting_manager_name": "Vikram Rao", "reporting_manager_band": "B3",
        "direct_reports": ["m_b1_4", "m_b1_5", "m_b1_6"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b2_4", "band": "B2", "name": "Nisha Menon", "age": 30, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "nisha.menon",
        "avatar": "NM", "email": "nisha.menon@starapp.io", "password": "12345678",
        "reporting_manager": "Arjun Malhotra (B3)", "reporting_manager_id": "m_b3_3", "reporting_manager_name": "Arjun Malhotra", "reporting_manager_band": "B3",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b2_5", "band": "B2", "name": "Karthik Subramanian", "age": 33, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "karthik.subramanian",
        "avatar": "KS", "email": "karthik.subramanian@starapp.io", "password": "12345678",
        "reporting_manager": "Arjun Malhotra (B3)", "reporting_manager_id": "m_b3_3", "reporting_manager_name": "Arjun Malhotra", "reporting_manager_band": "B3",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b2_6", "band": "B2", "name": "Pooja Joshi", "age": 28, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "pooja.joshi",
        "avatar": "PJ", "email": "pooja.joshi@starapp.io", "password": "12345678",
        "reporting_manager": "Arjun Malhotra (B3)", "reporting_manager_id": "m_b3_3", "reporting_manager_name": "Arjun Malhotra", "reporting_manager_band": "B3",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },

    # Band B3 (Senior Specialist) - 6 Members (2 Managers, 4 ICs)
    {
        "id": "m_b3_1", "band": "B3", "name": "Vikram Rao", "age": 36, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "vikram.rao",
        "avatar": "VR", "email": "vikram.rao@starapp.io", "password": "12345678",
        "reporting_manager": "Rajiv Menon (B4)", "reporting_manager_id": "m_b4_1", "reporting_manager_name": "Rajiv Menon", "reporting_manager_band": "B4",
        "direct_reports": ["m_b2_1", "m_b2_2", "m_b2_3"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b3_2", "band": "B3", "name": "Sneha Kapoor", "age": 35, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "sneha.kapoor",
        "avatar": "SK", "email": "sneha.kapoor@starapp.io", "password": "12345678",
        "reporting_manager": "Rajiv Menon (B4)", "reporting_manager_id": "m_b4_1", "reporting_manager_name": "Rajiv Menon", "reporting_manager_band": "B4",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b3_3", "band": "B3", "name": "Arjun Malhotra", "age": 37, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "arjun.malhotra",
        "avatar": "AM", "email": "arjun.malhotra@starapp.io", "password": "12345678",
        "reporting_manager": "Rajiv Menon (B4)", "reporting_manager_id": "m_b4_1", "reporting_manager_name": "Rajiv Menon", "reporting_manager_band": "B4",
        "direct_reports": ["m_b2_4", "m_b2_5", "m_b2_6"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b3_4", "band": "B3", "name": "Divya Krishnan", "age": 34, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "divya.krishnan",
        "avatar": "DK", "email": "divya.krishnan@starapp.io", "password": "12345678",
        "reporting_manager": "Pranav Sethi (B4)", "reporting_manager_id": "m_b4_3", "reporting_manager_name": "Pranav Sethi", "reporting_manager_band": "B4",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b3_5", "band": "B3", "name": "Sandeep Bhat", "age": 38, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "sandeep.bhat",
        "avatar": "SB", "email": "sandeep.bhat@starapp.io", "password": "12345678",
        "reporting_manager": "Pranav Sethi (B4)", "reporting_manager_id": "m_b4_3", "reporting_manager_name": "Pranav Sethi", "reporting_manager_band": "B4",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b3_6", "band": "B3", "name": "Tanvi Shah", "age": 35, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "tanvi.shah",
        "avatar": "TS", "email": "tanvi.shah@starapp.io", "password": "12345678",
        "reporting_manager": "Pranav Sethi (B4)", "reporting_manager_id": "m_b4_3", "reporting_manager_name": "Pranav Sethi", "reporting_manager_band": "B4",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },

    # Band B4 (Lead Engineer) - 6 Members (2 Managers, 4 ICs)
    {
        "id": "m_b4_1", "band": "B4", "name": "Rajiv Menon", "age": 42, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "rajiv.menon",
        "avatar": "RM", "email": "rajiv.menon@starapp.io", "password": "12345678",
        "reporting_manager": "Anirudh Krishnan (B5)", "reporting_manager_id": "m_b5_1", "reporting_manager_name": "Anirudh Krishnan", "reporting_manager_band": "B5",
        "direct_reports": ["m_b3_1", "m_b3_2", "m_b3_3"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b4_2", "band": "B4", "name": "Shalini Desai", "age": 40, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "shalini.desai",
        "avatar": "SD", "email": "shalini.desai@starapp.io", "password": "12345678",
        "reporting_manager": "Anirudh Krishnan (B5)", "reporting_manager_id": "m_b5_1", "reporting_manager_name": "Anirudh Krishnan", "reporting_manager_band": "B5",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b4_3", "band": "B4", "name": "Pranav Sethi", "age": 43, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "pranav.sethi",
        "avatar": "PS", "email": "pranav.sethi@starapp.io", "password": "12345678",
        "reporting_manager": "Anirudh Krishnan (B5)", "reporting_manager_id": "m_b5_1", "reporting_manager_name": "Anirudh Krishnan", "reporting_manager_band": "B5",
        "direct_reports": ["m_b3_4", "m_b3_5", "m_b3_6"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b4_4", "band": "B4", "name": "Neha Pillai", "age": 39, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "neha.pillai",
        "avatar": "NP", "email": "neha.pillai@starapp.io", "password": "12345678",
        "reporting_manager": "Sameer Kulkarni (B5)", "reporting_manager_id": "m_b5_3", "reporting_manager_name": "Sameer Kulkarni", "reporting_manager_band": "B5",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b4_5", "band": "B4", "name": "Gaurav Mukherjee", "age": 44, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "gaurav.mukherjee",
        "avatar": "GM", "email": "gaurav.mukherjee@starapp.io", "password": "12345678",
        "reporting_manager": "Sameer Kulkarni (B5)", "reporting_manager_id": "m_b5_3", "reporting_manager_name": "Sameer Kulkarni", "reporting_manager_band": "B5",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b4_6", "band": "B4", "name": "Aditi Rao", "age": 41, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "aditi.rao",
        "avatar": "AR", "email": "aditi.rao@starapp.io", "password": "12345678",
        "reporting_manager": "Sameer Kulkarni (B5)", "reporting_manager_id": "m_b5_3", "reporting_manager_name": "Sameer Kulkarni", "reporting_manager_band": "B5",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },

    # Band B5 (Principal Architect) - 6 Members (2 Managers, 4 ICs)
    {
        "id": "m_b5_1", "band": "B5", "name": "Anirudh Krishnan", "age": 48, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "anirudh.krishnan",
        "avatar": "AK", "email": "anirudh.krishnan@starapp.io", "password": "12345678",
        "reporting_manager": "Devika Narayanan (B6)", "reporting_manager_id": "m_b6_1", "reporting_manager_name": "Devika Narayanan", "reporting_manager_band": "B6",
        "direct_reports": ["m_b4_1", "m_b4_2", "m_b4_3"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b5_2", "band": "B5", "name": "Kavita Shah", "age": 47, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "kavita.shah",
        "avatar": "KS", "email": "kavita.shah@starapp.io", "password": "12345678",
        "reporting_manager": "Devika Narayanan (B6)", "reporting_manager_id": "m_b6_1", "reporting_manager_name": "Devika Narayanan", "reporting_manager_band": "B6",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b5_3", "band": "B5", "name": "Sameer Kulkarni", "age": 49, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "sameer.kulkarni",
        "avatar": "SK", "email": "sameer.kulkarni@starapp.io", "password": "12345678",
        "reporting_manager": "Devika Narayanan (B6)", "reporting_manager_id": "m_b6_1", "reporting_manager_name": "Devika Narayanan", "reporting_manager_band": "B6",
        "direct_reports": ["m_b4_4", "m_b4_5", "m_b4_6"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b5_4", "band": "B5", "name": "Ritu Malhotra", "age": 46, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "ritu.malhotra",
        "avatar": "RM", "email": "ritu.malhotra@starapp.io", "password": "12345678",
        "reporting_manager": "Manish Bansal (B6)", "reporting_manager_id": "m_b6_3", "reporting_manager_name": "Manish Bansal", "reporting_manager_band": "B6",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b5_5", "band": "B5", "name": "Harish Iyer", "age": 50, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "harish.iyer",
        "avatar": "HI", "email": "harish.iyer@starapp.io", "password": "12345678",
        "reporting_manager": "Manish Bansal (B6)", "reporting_manager_id": "m_b6_3", "reporting_manager_name": "Manish Bansal", "reporting_manager_band": "B6",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b5_6", "band": "B5", "name": "Lakshmi Nambiar", "age": 47, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "lakshmi.nambiar",
        "avatar": "LN", "email": "lakshmi.nambiar@starapp.io", "password": "12345678",
        "reporting_manager": "Manish Bansal (B6)", "reporting_manager_id": "m_b6_3", "reporting_manager_name": "Manish Bansal", "reporting_manager_band": "B6",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },

    # Band B6 (Chief / Distinguished Fellow) - Exactly 5 Employees (2 Managers, 3 ICs)
    {
        "id": "m_b6_1", "band": "B6", "name": "Devika Narayanan", "age": 53, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "devika.narayanan",
        "avatar": "DN", "email": "devika.narayanan@starapp.io", "password": "12345678",
        "reporting_manager": "Arjun Mehta (CEO)", "reporting_manager_id": "guardian_1", "reporting_manager_name": "Arjun Mehta", "reporting_manager_band": "CEO",
        "direct_reports": ["m_b5_1", "m_b5_2", "m_b5_3"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b6_2", "band": "B6", "name": "Siddharth Banerjee", "age": 54, "role": "Solutions Designer",
        "learning_track": "Solutions Designer", "track_code": "SD", "username": "siddharth.banerjee",
        "avatar": "SB", "email": "siddharth.banerjee@starapp.io", "password": "12345678",
        "reporting_manager": "Arjun Mehta (CEO)", "reporting_manager_id": "guardian_1", "reporting_manager_name": "Arjun Mehta", "reporting_manager_band": "CEO",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b6_3", "band": "B6", "name": "Manish Bansal", "age": 53, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "manish.bansal",
        "avatar": "MB", "email": "manish.bansal@starapp.io", "password": "12345678",
        "reporting_manager": "Arjun Mehta (CEO)", "reporting_manager_id": "guardian_1", "reporting_manager_name": "Arjun Mehta", "reporting_manager_band": "CEO",
        "direct_reports": ["m_b5_4", "m_b5_5", "m_b5_6"],
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b6_4", "band": "B6", "name": "Farah Contractor", "age": 52, "role": "AI Engineer",
        "learning_track": "AI Engineer", "track_code": "AIE", "username": "farah.contractor",
        "avatar": "FC", "email": "farah.contractor@starapp.io", "password": "12345678",
        "reporting_manager": "Arjun Mehta (CEO)", "reporting_manager_id": "guardian_1", "reporting_manager_name": "Arjun Mehta", "reporting_manager_band": "CEO",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },
    {
        "id": "m_b6_5", "band": "B6", "name": "Prakash Venkataraman", "age": 54, "role": "Systems Engineer",
        "learning_track": "Systems Engineer", "track_code": "SE", "username": "prakash.venkataraman",
        "avatar": "PV", "email": "prakash.venkataraman@starapp.io", "password": "12345678",
        "reporting_manager": "Arjun Mehta (CEO)", "reporting_manager_id": "guardian_1", "reporting_manager_name": "Arjun Mehta", "reporting_manager_band": "CEO",
        "application_roles": ["cosmonaut", "badge_reviewer", "project_reviewer"], "status": "active", "is_demo": False
    },

    # Executive Leadership - CEO & Admin (Arjun Mehta)
    {
        "id": "guardian_1", "band": "CEO", "name": "Arjun Mehta", "age": 55, "role": "Chief Executive Officer",
        "learning_track": "Executive Leadership", "track_code": "EXEC", "username": "arjun.mehta",
        "avatar": "AM", "email": "arjun.mehta@starapp.io", "password": "12345678",
        "reporting_manager": None, "reporting_manager_id": None, "reporting_manager_name": None, "reporting_manager_band": None,
        "direct_reports": ["m_b6_1", "m_b6_2", "m_b6_3", "m_b6_4", "m_b6_5"],
        "application_roles": ["guardian", "project_reviewer"], "status": "active", "is_demo": False
    }
]

# The 36 Corporate Hierarchy Profiles across B1-B6 and CEO
INDIAN_DEMO_MEMBERS: List[Dict[str, Any]] = DUMMY_MEMBERS

# Quick lookup maps
MEMBERS_MAP: Dict[str, Dict[str, Any]] = {m["id"]: m for m in DUMMY_MEMBERS}

MEMBERS_BY_BAND: Dict[str, List[Dict[str, Any]]] = {}
for m in DUMMY_MEMBERS:
    MEMBERS_BY_BAND.setdefault(m["band"], []).append(m)


# ==============================================================================
# 4. BADGES CATALOG FOR MAPPING
# ==============================================================================

MAPPING_BADGES: List[Dict[str, Any]] = [
    {
        "id": "AIOS",
        "code": "AIOS-101",
        "name": "AIOS",
        "title": "Autonomous Intelligent Operating System",
        "category": "AI & Architecture",
        "icon": "cpu",
        "description": "Kernel abstractions, multi-tenant memory arenas, and LLM agent runtime scheduling."
    },
    {
        "id": "Network",
        "code": "NET-201",
        "name": "Network",
        "title": "Distributed Mesh & Protocol Fabric",
        "category": "Systems & Infrastructure",
        "icon": "wifi",
        "description": "Peer-to-peer protocols, zero-copy packet switching, eBPF telemetry, and edge consensus."
    },
    {
        "id": "Data Modelling",
        "code": "DATA-201",
        "name": "Data Modelling",
        "title": "Enterprise Graph & Vector Schemas",
        "category": "Solutions & Data",
        "icon": "database",
        "description": "Polyglot persistence, distributed graph partitioning, and high-dimensional vector embeddings."
    },
    {
        "id": "Cloud Architecture",
        "code": "CLD-301",
        "name": "Cloud Architecture",
        "title": "Multi-Region Cloud Fabric & Resiliency",
        "category": "Systems & Cloud",
        "icon": "cloud",
        "description": "Active-active multi-cloud topologies, infrastructure-as-code, and automated disaster recovery."
    },
    {
        "id": "Systems Security",
        "code": "SEC-301",
        "name": "Systems Security",
        "title": "Zero-Trust & Cryptographic Enclaves",
        "category": "Systems & SecOps",
        "icon": "shield",
        "description": "Hardware enclaves (SGX/SEV), mTLS authentication, and continuous attestation."
    },
    {
        "id": "Streaming Pipelines",
        "code": "STR-301",
        "name": "Streaming Pipelines",
        "title": "Real-Time Event Streams & Lakehouses",
        "category": "Solutions & Data",
        "icon": "activity",
        "description": "Low-latency streaming with Kafka/Flink, tumbling event windows, and exactly-once processing."
    },
    {
        "id": "Autonomous Agents",
        "code": "AGT-401",
        "name": "Autonomous Agents",
        "title": "Multi-Agent Swarm Orchestration",
        "category": "AI & Intelligence",
        "icon": "zap",
        "description": "Swarm consensus protocols, hierarchical planning, and tool-augmented reasoning workflows."
    },
    {
        "id": "Machine Learning Ops",
        "code": "MLO-401",
        "name": "Machine Learning Ops",
        "title": "Continuous Training & Safety Guardrails",
        "category": "AI & Operations",
        "icon": "git-branch",
        "description": "Model registry lifecycle, feature store lineage, drift detection, and automated adversarial red-teaming."
    },
    {
        "id": "Enterprise Governance",
        "code": "GOV-401",
        "name": "Enterprise Governance",
        "title": "Algorithmic Auditing & Compliance",
        "category": "Solutions & Governance",
        "icon": "check-circle",
        "description": "Data provenance tracking, SOC2/HIPAA guardrails, and deterministic rubric verification."
    },
    {
        "id": "Quantum Computing",
        "code": "QNT-501",
        "name": "Quantum Computing",
        "title": "Qubit Circuit Logic & Variational Solvers",
        "category": "Advanced Systems",
        "icon": "compass",
        "description": "Quantum circuit depth optimization, error mitigation, and hybrid classical-quantum algorithms."
    }
]

BADGES_MAP: Dict[str, Dict[str, Any]] = {b["name"]: b for b in MAPPING_BADGES}

# ==============================================================================
# 5. FILTERING AND ACCESSOR HELPERS
# ==============================================================================

BANDS_MAP: Dict[str, Dict[str, Any]] = {b["code"]: b for b in BANDS}

def get_band_info(band_code: str) -> Dict[str, Any]:
    """Retrieves metadata dictionary for a band code in O(1) time."""
    return BANDS_MAP.get(band_code, BANDS[0])

def get_higher_bands(band_code: str) -> List[str]:
    """
    Returns list of higher bands than the current band.
    e.g. B1 -> ['B2', 'B3', 'B4', 'B5', 'B6']
         B3 -> ['B4', 'B5', 'B6']
         B6 -> ['B6'] (Peer/Fellow reviewers for the highest band)
    """
    try:
        idx = BAND_CODES.index(band_code)
    except ValueError:
        idx = 0
    higher = BAND_CODES[idx + 1:]
    return higher if higher else ["B6"]

def filter_members_by_band_and_roles(
    band_code: Union[str, List[str]],
    selected_roles: Optional[List[str]] = None,
    search_query: str = ""
) -> List[Dict[str, Any]]:
    """
    Filters members of one or multiple bands by active role selection and search text.
    """
    if isinstance(band_code, (list, tuple, set)):
        members = []
        for b in band_code:
            members.extend(MEMBERS_BY_BAND.get(b, []))
    else:
        members = MEMBERS_BY_BAND.get(band_code, [])

    roles_set = set(selected_roles) if selected_roles else set(ROLES)
    query = search_query.strip().lower()

    filtered = []
    for m in members:
        if m["role"] not in roles_set:
            continue
        if query:
            match_name = query in m["name"].lower()
            match_role = query in m["role"].lower()
            match_email = query in m["email"].lower()
            if not (match_name or match_role or match_email):
                continue
        filtered.append(m)

    return filtered

def filter_reviewers_by_band_and_roles(
    reviewer_band: Union[str, List[str]],
    selected_roles: Optional[List[str]] = None,
    search_query: str = ""
) -> List[Dict[str, Any]]:
    """
    Filters members of the selected reviewer band(s) by role and search query.
    """
    return filter_members_by_band_and_roles(reviewer_band, selected_roles, search_query)

# ==============================================================================
# 6. ESTIMATED REVIEW DATE & BUSINESS DAY CALENDAR HELPERS
# ==============================================================================

import calendar
import datetime

_PARSED_DATE_CACHE: Dict[str, datetime.date] = {}

def parse_iso_date(iso_str: str) -> datetime.date:
    """Parses an ISO date string (YYYY-MM-DD) into a datetime.date object with O(1) caching."""
    if not iso_str:
        return datetime.date(2026, 11, 18)
    cached = _PARSED_DATE_CACHE.get(iso_str)
    if cached is not None:
        return cached
    try:
        parts = [int(p) for p in iso_str.strip().split("-")]
        d = datetime.date(parts[0], parts[1], parts[2])
        _PARSED_DATE_CACHE[iso_str] = d
        return d
    except Exception:
        return datetime.date(2026, 11, 18)

def is_weekend_date(d: datetime.date) -> bool:
    """Returns True if the date is a Saturday (5) or Sunday (6)."""
    return d.weekday() >= 5

def get_consecutive_review_days(anchor_iso: str, direction: str = "after", count: int = 3) -> List[str]:
    """
    Computes exactly 3 consecutive business days starting or ending at anchor_iso,
    strictly skipping Saturday and Sunday (weekends).
    - direction == 'after': anchor + next 2 business days
    - direction == 'before': previous 2 business days + anchor
    """
    anchor = parse_iso_date(anchor_iso)
    if is_weekend_date(anchor):
        shift = 1 if direction == "after" else -1
        while is_weekend_date(anchor):
            anchor += datetime.timedelta(days=shift)

    dates = []
    curr = anchor
    step = 1 if direction == "after" else -1

    while len(dates) < count:
        if not is_weekend_date(curr):
            dates.append(curr.isoformat())
        curr += datetime.timedelta(days=step)

    return sorted(dates)


def get_working_days_between(start_iso: str, end_iso: str, max_days: int = 45) -> List[str]:
    """Returns sorted ISO strings for all weekdays (Mon–Fri) between start_iso and end_iso inclusive."""
    d1 = parse_iso_date(start_iso)
    d2 = parse_iso_date(end_iso)
    if d2 < d1:
        d1, d2 = d2, d1
    dates: List[str] = []
    curr = d1
    while curr <= d2 and len(dates) < max_days:
        if not is_weekend_date(curr):
            dates.append(curr.isoformat())
        curr += datetime.timedelta(days=1)
    return dates

def format_review_date_human(iso_str: str) -> str:
    """Formats YYYY-MM-DD into 'Wed, Nov 18, 2026'."""
    try:
        d = parse_iso_date(iso_str)
        return d.strftime("%a, %b %d, %Y")
    except Exception:
        return iso_str

def generate_calendar_month_grid(
    year: int,
    month: int,
    selected_dates: List[str],
    anchor_date: str
) -> Dict[str, Any]:
    """
    Generates a 7-column calendar grid (Mon - Sun) for the given year and month.
    Flags weekends, selected review dates, and anchor dates.
    """
    cal = calendar.Calendar(firstweekday=0)  # Monday = 0
    weeks = []
    month_name = datetime.date(year, month, 1).strftime("%B")

    for week in cal.monthdatescalendar(year, month):
        week_days = []
        for d in week:
            is_cur_month = (d.month == month)
            is_weekend = is_weekend_date(d)
            iso = d.isoformat()
            is_selected = (iso in selected_dates)
            is_anchor = (iso == anchor_date)
            order_idx = (selected_dates.index(iso) + 1) if is_selected else None
            week_days.append({
                "day": d.day,
                "date": iso,
                "is_current_month": is_cur_month,
                "is_weekend": is_weekend,
                "is_selected": is_selected,
                "is_anchor": is_anchor,
                "order_idx": order_idx,
                "weekday": d.weekday(),
                "day_name": d.strftime("%a")
            })
        weeks.append(week_days)

    # Calculate previous and next month
    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    next_m = month + 1 if month < 12 else 1
    next_y = year if month < 12 else year + 1

    return {
        "year": year,
        "month": month,
        "month_name": month_name,
        "prev_year": prev_y,
        "prev_month": prev_m,
        "next_year": next_y,
        "next_month": next_m,
        "weeks": weeks
    }

