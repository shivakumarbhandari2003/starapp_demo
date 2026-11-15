"""
STARAPP BAND & ROLE COMPETENCY MAPPING DATA
Provides static definitions for Bands B1 to B6, the 3 technical roles,
36 distinct dummy members (6 per band, 2 per role), and the curriculum badge catalog.
"""

from typing import List, Dict, Any, Optional

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
# 3. 36 DUMMY MEMBERS (6 DISTINCT MEMBERS PER BAND, 2 PER ROLE)
# ==============================================================================

DUMMY_MEMBERS: List[Dict[str, Any]] = [
    # Band B1 (Foundation Associate)
    {"id": "m_b1_1", "band": "B1", "name": "Leo Vance", "role": "AI Engineer", "avatar": "LV", "email": "leo.vance@starapp.io"},
    {"id": "m_b1_2", "band": "B1", "name": "Maya Lin", "role": "Solutions Designer", "avatar": "ML", "email": "maya.lin@starapp.io"},
    {"id": "m_b1_3", "band": "B1", "name": "Kai Chen", "role": "Systems Engineer", "avatar": "KC", "email": "kai.chen@starapp.io"},
    {"id": "m_b1_4", "band": "B1", "name": "Priya Sharma", "role": "AI Engineer", "avatar": "PS", "email": "priya.sharma@starapp.io"},
    {"id": "m_b1_5", "band": "B1", "name": "Lucas Silva", "role": "Solutions Designer", "avatar": "LS", "email": "lucas.silva@starapp.io"},
    {"id": "m_b1_6", "band": "B1", "name": "Zoe Martinez", "role": "Systems Engineer", "avatar": "ZM", "email": "zoe.martinez@starapp.io"},

    # Band B2 (Specialist)
    {"id": "m_b2_1", "band": "B2", "name": "Ethan Hunt", "role": "AI Engineer", "avatar": "EH", "email": "ethan.hunt@starapp.io"},
    {"id": "m_b2_2", "band": "B2", "name": "Aria Stark", "role": "Solutions Designer", "avatar": "AS", "email": "aria.stark@starapp.io"},
    {"id": "m_b2_3", "band": "B2", "name": "Noah Williams", "role": "Systems Engineer", "avatar": "NW", "email": "noah.williams@starapp.io"},
    {"id": "m_b2_4", "band": "B2", "name": "Chloe Dubois", "role": "AI Engineer", "avatar": "CD", "email": "chloe.dubois@starapp.io"},
    {"id": "m_b2_5", "band": "B2", "name": "Liam O'Connor", "role": "Solutions Designer", "avatar": "LO", "email": "liam.oconnor@starapp.io"},
    {"id": "m_b2_6", "band": "B2", "name": "Sophia Rossi", "role": "Systems Engineer", "avatar": "SR", "email": "sophia.rossi@starapp.io"},

    # Band B3 (Senior Specialist)
    {"id": "m_b3_1", "band": "B3", "name": "Marcus Thorne", "role": "AI Engineer", "avatar": "MT", "email": "marcus.thorne@starapp.io"},
    {"id": "m_b3_2", "band": "B3", "name": "Elena Rostova", "role": "Solutions Designer", "avatar": "ER", "email": "elena.rostova@starapp.io"},
    {"id": "m_b3_3", "band": "B3", "name": "Jason Bourne", "role": "Systems Engineer", "avatar": "JB", "email": "jason.bourne@starapp.io"},
    {"id": "m_b3_4", "band": "B3", "name": "Natasha Roman", "role": "AI Engineer", "avatar": "NR", "email": "natasha.roman@starapp.io"},
    {"id": "m_b3_5", "band": "B3", "name": "David Kim", "role": "Solutions Designer", "avatar": "DK", "email": "david.kim@starapp.io"},
    {"id": "m_b3_6", "band": "B3", "name": "Amara Okafor", "role": "Systems Engineer", "avatar": "AO", "email": "amara.okafor@starapp.io"},

    # Band B4 (Lead Engineer)
    {"id": "m_b4_1", "band": "B4", "name": "Victor Stone", "role": "AI Engineer", "avatar": "VS", "email": "victor.stone@starapp.io"},
    {"id": "m_b4_2", "band": "B4", "name": "Samantha Reed", "role": "Solutions Designer", "avatar": "SR", "email": "samantha.reed@starapp.io"},
    {"id": "m_b4_3", "band": "B4", "name": "Arthur Pendelton", "role": "Systems Engineer", "avatar": "AP", "email": "arthur.pendelton@starapp.io"},
    {"id": "m_b4_4", "band": "B4", "name": "Cassandra Nova", "role": "AI Engineer", "avatar": "CN", "email": "cassandra.nova@starapp.io"},
    {"id": "m_b4_5", "band": "B4", "name": "Bruce Wayne", "role": "Solutions Designer", "avatar": "BW", "email": "bruce.wayne@starapp.io"},
    {"id": "m_b4_6", "band": "B4", "name": "Diana Prince", "role": "Systems Engineer", "avatar": "DP", "email": "diana.prince@starapp.io"},

    # Band B5 (Principal Architect)
    {"id": "m_b5_1", "band": "B5", "name": "Dr. Aris Thorne", "role": "AI Engineer", "avatar": "AT", "email": "aris.thorne@starapp.io"},
    {"id": "m_b5_2", "band": "B5", "name": "Dr. Thalia Vance", "role": "Solutions Designer", "avatar": "TV", "email": "thalia.vance@starapp.io"},
    {"id": "m_b5_3", "band": "B5", "name": "Sterling Archer", "role": "Systems Engineer", "avatar": "SA", "email": "sterling.archer@starapp.io"},
    {"id": "m_b5_4", "band": "B5", "name": "Dr. Helena Troy", "role": "AI Engineer", "avatar": "HT", "email": "helena.troy@starapp.io"},
    {"id": "m_b5_5", "band": "B5", "name": "Xavier Morales", "role": "Solutions Designer", "avatar": "XM", "email": "xavier.morales@starapp.io"},
    {"id": "m_b5_6", "band": "B5", "name": "Seraphina Drake", "role": "Systems Engineer", "avatar": "SD", "email": "seraphina.drake@starapp.io"},

    # Band B6 (Chief / Distinguished Fellow)
    {"id": "m_b6_1", "band": "B6", "name": "Prof. Kenneth Drake", "role": "AI Engineer", "avatar": "KD", "email": "kenneth.drake@starapp.io"},
    {"id": "m_b6_2", "band": "B6", "name": "Dr. Vivienne Westwood", "role": "Solutions Designer", "avatar": "VW", "email": "vivienne.westwood@starapp.io"},
    {"id": "m_b6_3", "band": "B6", "name": "Chief Arch. Jonathan Myers", "role": "Systems Engineer", "avatar": "JM", "email": "jonathan.myers@starapp.io"},
    {"id": "m_b6_4", "band": "B6", "name": "Prof. Althea Blackwood", "role": "AI Engineer", "avatar": "AB", "email": "althea.blackwood@starapp.io"},
    {"id": "m_b6_5", "band": "B6", "name": "Fellow Roland Chang", "role": "Solutions Designer", "avatar": "RC", "email": "roland.chang@starapp.io"},
    {"id": "m_b6_6", "band": "B6", "name": "Fellow Beatrice Bell", "role": "Systems Engineer", "avatar": "BB", "email": "beatrice.bell@starapp.io"},
]

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

def get_band_info(band_code: str) -> Dict[str, Any]:
    """Retrieves metadata dictionary for a band code (e.g. 'B1')."""
    for b in BANDS:
        if b["code"] == band_code:
            return b
    return BANDS[0]

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
    band_code: str,
    selected_roles: Optional[List[str]] = None,
    search_query: str = ""
) -> List[Dict[str, Any]]:
    """
    Filters the 6 dummy members of a band by active role selection and search text.
    """
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
    reviewer_band: str,
    selected_roles: Optional[List[str]] = None,
    search_query: str = ""
) -> List[Dict[str, Any]]:
    """
    Filters members of the selected reviewer band by role and search query.
    """
    return filter_members_by_band_and_roles(reviewer_band, selected_roles, search_query)

# ==============================================================================
# 6. ESTIMATED REVIEW DATE & BUSINESS DAY CALENDAR HELPERS
# ==============================================================================

import calendar
import datetime

def parse_iso_date(iso_str: str) -> datetime.date:
    """Parses an ISO date string (YYYY-MM-DD) into a datetime.date object."""
    try:
        parts = [int(p) for p in iso_str.strip().split("-")]
        return datetime.date(parts[0], parts[1], parts[2])
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

