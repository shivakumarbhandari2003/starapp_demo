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
# 3. 36 DUMMY MEMBERS (6 DISTINCT MEMBERS PER BAND, 2 PER ROLE)
# ==============================================================================

DUMMY_MEMBERS: List[Dict[str, Any]] = [
    # Band B1 (Foundation Associate) - 27 Members (9 per Domain)
    {"id": "m_b1_1", "band": "B1", "name": "Leo Vance", "role": "AI Engineer", "avatar": "LV", "email": "leo.vance.b1@starapp.io"},
    {"id": "m_b1_2", "band": "B1", "name": "Maya Lin", "role": "Solutions Designer", "avatar": "ML", "email": "maya.lin.b1@starapp.io"},
    {"id": "m_b1_3", "band": "B1", "name": "Kai Chen", "role": "Systems Engineer", "avatar": "KC", "email": "kai.chen.b1@starapp.io"},
    {"id": "m_b1_4", "band": "B1", "name": "Priya Sharma", "role": "AI Engineer", "avatar": "PS", "email": "priya.sharma.b1@starapp.io"},
    {"id": "m_b1_5", "band": "B1", "name": "Lucas Silva", "role": "Solutions Designer", "avatar": "LS", "email": "lucas.silva.b1@starapp.io"},
    {"id": "m_b1_6", "band": "B1", "name": "Zoe Martinez", "role": "Systems Engineer", "avatar": "ZM", "email": "zoe.martinez.b1@starapp.io"},
    {"id": "m_b1_7", "band": "B1", "name": "Rowan Chen", "role": "AI Engineer", "avatar": "RC", "email": "rowan.chen.b1@starapp.io"},
    {"id": "m_b1_8", "band": "B1", "name": "Anya Petrova", "role": "AI Engineer", "avatar": "AP", "email": "anya.petrova.b1@starapp.io"},
    {"id": "m_b1_9", "band": "B1", "name": "Mateo Gomez", "role": "AI Engineer", "avatar": "MG", "email": "mateo.gomez.b1@starapp.io"},
    {"id": "m_b1_10", "band": "B1", "name": "Zara Al-Mansoor", "role": "AI Engineer", "avatar": "ZA", "email": "zara.al.mansoor.b1@starapp.io"},
    {"id": "m_b1_11", "band": "B1", "name": "Julian Hayes", "role": "AI Engineer", "avatar": "JH", "email": "julian.hayes.b1@starapp.io"},
    {"id": "m_b1_12", "band": "B1", "name": "Kaelen Voss", "role": "AI Engineer", "avatar": "KV", "email": "kaelen.voss.b1@starapp.io"},
    {"id": "m_b1_13", "band": "B1", "name": "Devon Ross", "role": "AI Engineer", "avatar": "DR", "email": "devon.ross.b1@starapp.io"},
    {"id": "m_b1_14", "band": "B1", "name": "Clara Oswald", "role": "Solutions Designer", "avatar": "CO", "email": "clara.oswald.b1@starapp.io"},
    {"id": "m_b1_15", "band": "B1", "name": "Aiden Shaw", "role": "Solutions Designer", "avatar": "AS", "email": "aiden.shaw.b1@starapp.io"},
    {"id": "m_b1_16", "band": "B1", "name": "Naomi Nagata", "role": "Solutions Designer", "avatar": "NN", "email": "naomi.nagata.b1@starapp.io"},
    {"id": "m_b1_17", "band": "B1", "name": "Tariq Vance", "role": "Solutions Designer", "avatar": "TV", "email": "tariq.vance.b1@starapp.io"},
    {"id": "m_b1_18", "band": "B1", "name": "Felix Richter", "role": "Solutions Designer", "avatar": "FR", "email": "felix.richter.b1@starapp.io"},
    {"id": "m_b1_19", "band": "B1", "name": "Mira Sorvino", "role": "Solutions Designer", "avatar": "MS", "email": "mira.sorvino.b1@starapp.io"},
    {"id": "m_b1_20", "band": "B1", "name": "Liam Sterling", "role": "Solutions Designer", "avatar": "LS", "email": "liam.sterling.b1@starapp.io"},
    {"id": "m_b1_21", "band": "B1", "name": "Eric Hansen", "role": "Systems Engineer", "avatar": "EH", "email": "eric.hansen.b1@starapp.io"},
    {"id": "m_b1_22", "band": "B1", "name": "Samira Khan", "role": "Systems Engineer", "avatar": "SK", "email": "samira.khan.b1@starapp.io"},
    {"id": "m_b1_23", "band": "B1", "name": "Tobias Becker", "role": "Systems Engineer", "avatar": "TB", "email": "tobias.becker.b1@starapp.io"},
    {"id": "m_b1_24", "band": "B1", "name": "Hana Takahashi", "role": "Systems Engineer", "avatar": "HT", "email": "hana.takahashi.b1@starapp.io"},
    {"id": "m_b1_25", "band": "B1", "name": "Caleb Miller", "role": "Systems Engineer", "avatar": "CM", "email": "caleb.miller.b1@starapp.io"},
    {"id": "m_b1_26", "band": "B1", "name": "Siobhan O'Riley", "role": "Systems Engineer", "avatar": "SO", "email": "siobhan.o.riley.b1@starapp.io"},
    {"id": "m_b1_27", "band": "B1", "name": "Nikhil Patel", "role": "Systems Engineer", "avatar": "NP", "email": "nikhil.patel.b1@starapp.io"},

    # Band B2 (Specialist) - 27 Members (9 per Domain)
    {"id": "m_b2_1", "band": "B2", "name": "Ethan Hunt", "role": "AI Engineer", "avatar": "EH", "email": "ethan.hunt.b2@starapp.io"},
    {"id": "m_b2_2", "band": "B2", "name": "Aria Stark", "role": "Solutions Designer", "avatar": "AS", "email": "aria.stark.b2@starapp.io"},
    {"id": "m_b2_3", "band": "B2", "name": "Noah Williams", "role": "Systems Engineer", "avatar": "NW", "email": "noah.williams.b2@starapp.io"},
    {"id": "m_b2_4", "band": "B2", "name": "Chloe Dubois", "role": "AI Engineer", "avatar": "CD", "email": "chloe.dubois.b2@starapp.io"},
    {"id": "m_b2_5", "band": "B2", "name": "Liam O'Connor", "role": "Solutions Designer", "avatar": "LO", "email": "liam.o.connor.b2@starapp.io"},
    {"id": "m_b2_6", "band": "B2", "name": "Sophia Rossi", "role": "Systems Engineer", "avatar": "SR", "email": "sophia.rossi.b2@starapp.io"},
    {"id": "m_b2_7", "band": "B2", "name": "Neil Armstrong", "role": "AI Engineer", "avatar": "NA", "email": "neil.armstrong.b2@starapp.io"},
    {"id": "m_b2_8", "band": "B2", "name": "Alan Turing", "role": "AI Engineer", "avatar": "AT", "email": "alan.turing.b2@starapp.io"},
    {"id": "m_b2_9", "band": "B2", "name": "Ada Lovelace", "role": "AI Engineer", "avatar": "AL", "email": "ada.lovelace.b2@starapp.io"},
    {"id": "m_b2_10", "band": "B2", "name": "Grace Hopper", "role": "AI Engineer", "avatar": "GH", "email": "grace.hopper.b2@starapp.io"},
    {"id": "m_b2_11", "band": "B2", "name": "John McCarthy", "role": "AI Engineer", "avatar": "JM", "email": "john.mccarthy.b2@starapp.io"},
    {"id": "m_b2_12", "band": "B2", "name": "Marvin Minsky", "role": "AI Engineer", "avatar": "MM", "email": "marvin.minsky.b2@starapp.io"},
    {"id": "m_b2_13", "band": "B2", "name": "Geoffrey Hinton", "role": "AI Engineer", "avatar": "GH", "email": "geoffrey.hinton.b2@starapp.io"},
    {"id": "m_b2_14", "band": "B2", "name": "Thomas Shelby", "role": "Solutions Designer", "avatar": "TS", "email": "thomas.shelby.b2@starapp.io"},
    {"id": "m_b2_15", "band": "B2", "name": "Arthur Dent", "role": "Solutions Designer", "avatar": "AD", "email": "arthur.dent.b2@starapp.io"},
    {"id": "m_b2_16", "band": "B2", "name": "Ford Prefect", "role": "Solutions Designer", "avatar": "FP", "email": "ford.prefect.b2@starapp.io"},
    {"id": "m_b2_17", "band": "B2", "name": "Tricia McMillan", "role": "Solutions Designer", "avatar": "TM", "email": "tricia.mcmillan.b2@starapp.io"},
    {"id": "m_b2_18", "band": "B2", "name": "Zaphod Beeblebrox", "role": "Solutions Designer", "avatar": "ZB", "email": "zaphod.beeblebrox.b2@starapp.io"},
    {"id": "m_b2_19", "band": "B2", "name": "Slartibartfast", "role": "Solutions Designer", "avatar": "SL", "email": "slartibartfast.b2@starapp.io"},
    {"id": "m_b2_20", "band": "B2", "name": "Dirk Gently", "role": "Solutions Designer", "avatar": "DG", "email": "dirk.gently.b2@starapp.io"},
    {"id": "m_b2_21", "band": "B2", "name": "James Kirk", "role": "Systems Engineer", "avatar": "JK", "email": "james.kirk.b2@starapp.io"},
    {"id": "m_b2_22", "band": "B2", "name": "Spock", "role": "Systems Engineer", "avatar": "SP", "email": "spock.b2@starapp.io"},
    {"id": "m_b2_23", "band": "B2", "name": "Leonard McCoy", "role": "Systems Engineer", "avatar": "LM", "email": "leonard.mccoy.b2@starapp.io"},
    {"id": "m_b2_24", "band": "B2", "name": "Montgomery Scott", "role": "Systems Engineer", "avatar": "MS", "email": "montgomery.scott.b2@starapp.io"},
    {"id": "m_b2_25", "band": "B2", "name": "Hikaru Sulu", "role": "Systems Engineer", "avatar": "HS", "email": "hikaru.sulu.b2@starapp.io"},
    {"id": "m_b2_26", "band": "B2", "name": "Nyota Uhura", "role": "Systems Engineer", "avatar": "NU", "email": "nyota.uhura.b2@starapp.io"},
    {"id": "m_b2_27", "band": "B2", "name": "Pavel Chekov", "role": "Systems Engineer", "avatar": "PC", "email": "pavel.chekov.b2@starapp.io"},

    # Band B3 (Senior Specialist) - 27 Members (9 per Domain)
    {"id": "m_b3_1", "band": "B3", "name": "Marcus Thorne", "role": "AI Engineer", "avatar": "MT", "email": "marcus.thorne.b3@starapp.io"},
    {"id": "m_b3_2", "band": "B3", "name": "Elena Rostova", "role": "Solutions Designer", "avatar": "ER", "email": "elena.rostova.b3@starapp.io"},
    {"id": "m_b3_3", "band": "B3", "name": "Jason Bourne", "role": "Systems Engineer", "avatar": "JB", "email": "jason.bourne.b3@starapp.io"},
    {"id": "m_b3_4", "band": "B3", "name": "Natasha Roman", "role": "AI Engineer", "avatar": "NR", "email": "natasha.roman.b3@starapp.io"},
    {"id": "m_b3_5", "band": "B3", "name": "David Kim", "role": "Solutions Designer", "avatar": "DK", "email": "david.kim.b3@starapp.io"},
    {"id": "m_b3_6", "band": "B3", "name": "Amara Okafor", "role": "Systems Engineer", "avatar": "AO", "email": "amara.okafor.b3@starapp.io"},
    {"id": "m_b3_7", "band": "B3", "name": "Yann LeCun", "role": "AI Engineer", "avatar": "YL", "email": "yann.lecun.b3@starapp.io"},
    {"id": "m_b3_8", "band": "B3", "name": "Yoshua Bengio", "role": "AI Engineer", "avatar": "YB", "email": "yoshua.bengio.b3@starapp.io"},
    {"id": "m_b3_9", "band": "B3", "name": "Demis Hassabis", "role": "AI Engineer", "avatar": "DH", "email": "demis.hassabis.b3@starapp.io"},
    {"id": "m_b3_10", "band": "B3", "name": "Fei-Fei Li", "role": "AI Engineer", "avatar": "FL", "email": "fei.fei.li.b3@starapp.io"},
    {"id": "m_b3_11", "band": "B3", "name": "Andrew Ng", "role": "AI Engineer", "avatar": "AN", "email": "andrew.ng.b3@starapp.io"},
    {"id": "m_b3_12", "band": "B3", "name": "Ian Goodfellow", "role": "AI Engineer", "avatar": "IG", "email": "ian.goodfellow.b3@starapp.io"},
    {"id": "m_b3_13", "band": "B3", "name": "Ilya Sutskever", "role": "AI Engineer", "avatar": "IS", "email": "ilya.sutskever.b3@starapp.io"},
    {"id": "m_b3_14", "band": "B3", "name": "Sarah Connor", "role": "Solutions Designer", "avatar": "SC", "email": "sarah.connor.b3@starapp.io"},
    {"id": "m_b3_15", "band": "B3", "name": "Kyle Reese", "role": "Solutions Designer", "avatar": "KR", "email": "kyle.reese.b3@starapp.io"},
    {"id": "m_b3_16", "band": "B3", "name": "John Connor", "role": "Solutions Designer", "avatar": "JC", "email": "john.connor.b3@starapp.io"},
    {"id": "m_b3_17", "band": "B3", "name": "Ellen Ripley", "role": "Solutions Designer", "avatar": "ER", "email": "ellen.ripley.b3@starapp.io"},
    {"id": "m_b3_18", "band": "B3", "name": "James Cole", "role": "Solutions Designer", "avatar": "JC", "email": "james.cole.b3@starapp.io"},
    {"id": "m_b3_19", "band": "B3", "name": "Martin Seamus", "role": "Solutions Designer", "avatar": "MS", "email": "martin.seamus.b3@starapp.io"},
    {"id": "m_b3_20", "band": "B3", "name": "Marty McFly", "role": "Solutions Designer", "avatar": "MM", "email": "marty.mcfly.b3@starapp.io"},
    {"id": "m_b3_21", "band": "B3", "name": "Luke Skywalker", "role": "Systems Engineer", "avatar": "LS", "email": "luke.skywalker.b3@starapp.io"},
    {"id": "m_b3_22", "band": "B3", "name": "Leia Organa", "role": "Systems Engineer", "avatar": "LO", "email": "leia.organa.b3@starapp.io"},
    {"id": "m_b3_23", "band": "B3", "name": "Han Solo", "role": "Systems Engineer", "avatar": "HS", "email": "han.solo.b3@starapp.io"},
    {"id": "m_b3_24", "band": "B3", "name": "Chewbacca", "role": "Systems Engineer", "avatar": "CH", "email": "chewbacca.b3@starapp.io"},
    {"id": "m_b3_25", "band": "B3", "name": "Lando Calrissian", "role": "Systems Engineer", "avatar": "LC", "email": "lando.calrissian.b3@starapp.io"},
    {"id": "m_b3_26", "band": "B3", "name": "Wedge Antilles", "role": "Systems Engineer", "avatar": "WA", "email": "wedge.antilles.b3@starapp.io"},
    {"id": "m_b3_27", "band": "B3", "name": "Cassian Andor", "role": "Systems Engineer", "avatar": "CA", "email": "cassian.andor.b3@starapp.io"},

    # Band B4 (Lead Engineer) - 27 Members (9 per Domain)
    {"id": "m_b4_1", "band": "B4", "name": "Victor Stone", "role": "AI Engineer", "avatar": "VS", "email": "victor.stone.b4@starapp.io"},
    {"id": "m_b4_2", "band": "B4", "name": "Samantha Reed", "role": "Solutions Designer", "avatar": "SR", "email": "samantha.reed.b4@starapp.io"},
    {"id": "m_b4_3", "band": "B4", "name": "Arthur Pendelton", "role": "Systems Engineer", "avatar": "AP", "email": "arthur.pendelton.b4@starapp.io"},
    {"id": "m_b4_4", "band": "B4", "name": "Cassandra Nova", "role": "AI Engineer", "avatar": "CN", "email": "cassandra.nova.b4@starapp.io"},
    {"id": "m_b4_5", "band": "B4", "name": "Bruce Wayne", "role": "Solutions Designer", "avatar": "BW", "email": "bruce.wayne.b4@starapp.io"},
    {"id": "m_b4_6", "band": "B4", "name": "Diana Prince", "role": "Systems Engineer", "avatar": "DP", "email": "diana.prince.b4@starapp.io"},
    {"id": "m_b4_7", "band": "B4", "name": "Dario Amodei", "role": "AI Engineer", "avatar": "DA", "email": "dario.amodei.b4@starapp.io"},
    {"id": "m_b4_8", "band": "B4", "name": "Mira Murati", "role": "AI Engineer", "avatar": "MM", "email": "mira.murati.b4@starapp.io"},
    {"id": "m_b4_9", "band": "B4", "name": "Sam Altman", "role": "AI Engineer", "avatar": "SA", "email": "sam.altman.b4@starapp.io"},
    {"id": "m_b4_10", "band": "B4", "name": "Greg Brockman", "role": "AI Engineer", "avatar": "GB", "email": "greg.brockman.b4@starapp.io"},
    {"id": "m_b4_11", "band": "B4", "name": "Andrej Karpathy", "role": "AI Engineer", "avatar": "AK", "email": "andrej.karpathy.b4@starapp.io"},
    {"id": "m_b4_12", "band": "B4", "name": "Chris Lattner", "role": "AI Engineer", "avatar": "CL", "email": "chris.lattner.b4@starapp.io"},
    {"id": "m_b4_13", "band": "B4", "name": "Jeff Dean", "role": "AI Engineer", "avatar": "JD", "email": "jeff.dean.b4@starapp.io"},
    {"id": "m_b4_14", "band": "B4", "name": "Tony Stark", "role": "Solutions Designer", "avatar": "TS", "email": "tony.stark.b4@starapp.io"},
    {"id": "m_b4_15", "band": "B4", "name": "Pepper Potts", "role": "Solutions Designer", "avatar": "PP", "email": "pepper.potts.b4@starapp.io"},
    {"id": "m_b4_16", "band": "B4", "name": "James Rhodes", "role": "Solutions Designer", "avatar": "JR", "email": "james.rhodes.b4@starapp.io"},
    {"id": "m_b4_17", "band": "B4", "name": "Peter Parker", "role": "Solutions Designer", "avatar": "PP", "email": "peter.parker.b4@starapp.io"},
    {"id": "m_b4_18", "band": "B4", "name": "Stephen Strange", "role": "Solutions Designer", "avatar": "SS", "email": "stephen.strange.b4@starapp.io"},
    {"id": "m_b4_19", "band": "B4", "name": "Reed Richards", "role": "Solutions Designer", "avatar": "RR", "email": "reed.richards.b4@starapp.io"},
    {"id": "m_b4_20", "band": "B4", "name": "Charles Xavier", "role": "Solutions Designer", "avatar": "CX", "email": "charles.xavier.b4@starapp.io"},
    {"id": "m_b4_21", "band": "B4", "name": "Clark Kent", "role": "Systems Engineer", "avatar": "CK", "email": "clark.kent.b4@starapp.io"},
    {"id": "m_b4_22", "band": "B4", "name": "Barry Allen", "role": "Systems Engineer", "avatar": "BA", "email": "barry.allen.b4@starapp.io"},
    {"id": "m_b4_23", "band": "B4", "name": "Hal Jordan", "role": "Systems Engineer", "avatar": "HJ", "email": "hal.jordan.b4@starapp.io"},
    {"id": "m_b4_24", "band": "B4", "name": "Victor Fries", "role": "Systems Engineer", "avatar": "VF", "email": "victor.fries.b4@starapp.io"},
    {"id": "m_b4_25", "band": "B4", "name": "Oliver Queen", "role": "Systems Engineer", "avatar": "OQ", "email": "oliver.queen.b4@starapp.io"},
    {"id": "m_b4_26", "band": "B4", "name": "Din Djarin", "role": "Systems Engineer", "avatar": "DD", "email": "din.djarin.b4@starapp.io"},
    {"id": "m_b4_27", "band": "B4", "name": "Boba Fett", "role": "Systems Engineer", "avatar": "BF", "email": "boba.fett.b4@starapp.io"},

    # Band B5 (Principal Architect) - 27 Members (9 per Domain)
    {"id": "m_b5_1", "band": "B5", "name": "Dr. Aris Thorne", "role": "AI Engineer", "avatar": "AT", "email": "aris.thorne.b5@starapp.io"},
    {"id": "m_b5_2", "band": "B5", "name": "Dr. Thalia Vance", "role": "Solutions Designer", "avatar": "TV", "email": "thalia.vance.b5@starapp.io"},
    {"id": "m_b5_3", "band": "B5", "name": "Sterling Archer", "role": "Systems Engineer", "avatar": "SA", "email": "sterling.archer.b5@starapp.io"},
    {"id": "m_b5_4", "band": "B5", "name": "Dr. Helena Troy", "role": "AI Engineer", "avatar": "HT", "email": "helena.troy.b5@starapp.io"},
    {"id": "m_b5_5", "band": "B5", "name": "Xavier Morales", "role": "Solutions Designer", "avatar": "XM", "email": "xavier.morales.b5@starapp.io"},
    {"id": "m_b5_6", "band": "B5", "name": "Seraphina Drake", "role": "Systems Engineer", "avatar": "SD", "email": "seraphina.drake.b5@starapp.io"},
    {"id": "m_b5_7", "band": "B5", "name": "Sanjay Ghemawat", "role": "AI Engineer", "avatar": "SG", "email": "sanjay.ghemawat.b5@starapp.io"},
    {"id": "m_b5_8", "band": "B5", "name": "Urs Holzle", "role": "AI Engineer", "avatar": "UH", "email": "urs.holzle.b5@starapp.io"},
    {"id": "m_b5_9", "band": "B5", "name": "Peter Norvig", "role": "AI Engineer", "avatar": "PN", "email": "peter.norvig.b5@starapp.io"},
    {"id": "m_b5_10", "band": "B5", "name": "Sebastian Thrun", "role": "AI Engineer", "avatar": "ST", "email": "sebastian.thrun.b5@starapp.io"},
    {"id": "m_b5_11", "band": "B5", "name": "Daphne Koller", "role": "AI Engineer", "avatar": "DK", "email": "daphne.koller.b5@starapp.io"},
    {"id": "m_b5_12", "band": "B5", "name": "Cynthia Dwork", "role": "AI Engineer", "avatar": "CD", "email": "cynthia.dwork.b5@starapp.io"},
    {"id": "m_b5_13", "band": "B5", "name": "Judea Pearl", "role": "AI Engineer", "avatar": "JP", "email": "judea.pearl.b5@starapp.io"},
    {"id": "m_b5_14", "band": "B5", "name": "Erik Lehnsherr", "role": "Solutions Designer", "avatar": "EL", "email": "erik.lehnsherr.b5@starapp.io"},
    {"id": "m_b5_15", "band": "B5", "name": "Jean Grey", "role": "Solutions Designer", "avatar": "JG", "email": "jean.grey.b5@starapp.io"},
    {"id": "m_b5_16", "band": "B5", "name": "Ororo Munroe", "role": "Solutions Designer", "avatar": "OM", "email": "ororo.munroe.b5@starapp.io"},
    {"id": "m_b5_17", "band": "B5", "name": "Hank McCoy", "role": "Solutions Designer", "avatar": "HM", "email": "hank.mccoy.b5@starapp.io"},
    {"id": "m_b5_18", "band": "B5", "name": "Scott Summers", "role": "Solutions Designer", "avatar": "SS", "email": "scott.summers.b5@starapp.io"},
    {"id": "m_b5_19", "band": "B5", "name": "Emma Frost", "role": "Solutions Designer", "avatar": "EF", "email": "emma.frost.b5@starapp.io"},
    {"id": "m_b5_20", "band": "B5", "name": "Warren Worthington", "role": "Solutions Designer", "avatar": "WW", "email": "warren.worthington.b5@starapp.io"},
    {"id": "m_b5_21", "band": "B5", "name": "Cobb Vanth", "role": "Systems Engineer", "avatar": "CV", "email": "cobb.vanth.b5@starapp.io"},
    {"id": "m_b5_22", "band": "B5", "name": "Greef Karga", "role": "Systems Engineer", "avatar": "GK", "email": "greef.karga.b5@starapp.io"},
    {"id": "m_b5_23", "band": "B5", "name": "Bo-Katan Kryze", "role": "Systems Engineer", "avatar": "BK", "email": "bo.katan.kryze.b5@starapp.io"},
    {"id": "m_b5_24", "band": "B5", "name": "Fennec Shand", "role": "Systems Engineer", "avatar": "FS", "email": "fennec.shand.b5@starapp.io"},
    {"id": "m_b5_25", "band": "B5", "name": "Carson Teva", "role": "Systems Engineer", "avatar": "CT", "email": "carson.teva.b5@starapp.io"},
    {"id": "m_b5_26", "band": "B5", "name": "Peli Motto", "role": "Systems Engineer", "avatar": "PM", "email": "peli.motto.b5@starapp.io"},
    {"id": "m_b5_27", "band": "B5", "name": "Kuiil", "role": "Systems Engineer", "avatar": "KU", "email": "kuiil.b5@starapp.io"},

    # Band B6 (Chief / Distinguished Fellow) - 27 Members (9 per Domain)
    {"id": "m_b6_1", "band": "B6", "name": "Prof. Kenneth Drake", "role": "AI Engineer", "avatar": "KD", "email": "kenneth.drake.b6@starapp.io"},
    {"id": "m_b6_2", "band": "B6", "name": "Dr. Vivienne Westwood", "role": "Solutions Designer", "avatar": "VW", "email": "vivienne.westwood.b6@starapp.io"},
    {"id": "m_b6_3", "band": "B6", "name": "Chief Arch. Jonathan Myers", "role": "Systems Engineer", "avatar": "JM", "email": "jonathan.myers.b6@starapp.io"},
    {"id": "m_b6_4", "band": "B6", "name": "Prof. Althea Blackwood", "role": "AI Engineer", "avatar": "AB", "email": "althea.blackwood.b6@starapp.io"},
    {"id": "m_b6_5", "band": "B6", "name": "Fellow Roland Chang", "role": "Solutions Designer", "avatar": "RC", "email": "roland.chang.b6@starapp.io"},
    {"id": "m_b6_6", "band": "B6", "name": "Fellow Beatrice Bell", "role": "Systems Engineer", "avatar": "BB", "email": "beatrice.bell.b6@starapp.io"},
    {"id": "m_b6_7", "band": "B6", "name": "Leslie Lamport", "role": "AI Engineer", "avatar": "LL", "email": "leslie.lamport.b6@starapp.io"},
    {"id": "m_b6_8", "band": "B6", "name": "Barbara Liskov", "role": "AI Engineer", "avatar": "BL", "email": "barbara.liskov.b6@starapp.io"},
    {"id": "m_b6_9", "band": "B6", "name": "Michael Stonebraker", "role": "AI Engineer", "avatar": "MS", "email": "michael.stonebraker.b6@starapp.io"},
    {"id": "m_b6_10", "band": "B6", "name": "Donald Knuth", "role": "AI Engineer", "avatar": "DK", "email": "donald.knuth.b6@starapp.io"},
    {"id": "m_b6_11", "band": "B6", "name": "Edsger Dijkstra", "role": "AI Engineer", "avatar": "ED", "email": "edsger.dijkstra.b6@starapp.io"},
    {"id": "m_b6_12", "band": "B6", "name": "Tim Berners-Lee", "role": "AI Engineer", "avatar": "TB", "email": "tim.berners.lee.b6@starapp.io"},
    {"id": "m_b6_13", "band": "B6", "name": "Vint Cerf", "role": "AI Engineer", "avatar": "VC", "email": "vint.cerf.b6@starapp.io"},
    {"id": "m_b6_14", "band": "B6", "name": "Stephen Hawking", "role": "Solutions Designer", "avatar": "SH", "email": "stephen.hawking.b6@starapp.io"},
    {"id": "m_b6_15", "band": "B6", "name": "Richard Feynman", "role": "Solutions Designer", "avatar": "RF", "email": "richard.feynman.b6@starapp.io"},
    {"id": "m_b6_16", "band": "B6", "name": "Carl Sagan", "role": "Solutions Designer", "avatar": "CS", "email": "carl.sagan.b6@starapp.io"},
    {"id": "m_b6_17", "band": "B6", "name": "Neil deGrasse", "role": "Solutions Designer", "avatar": "ND", "email": "neil.degrasse.b6@starapp.io"},
    {"id": "m_b6_18", "band": "B6", "name": "Kip Thorne", "role": "Solutions Designer", "avatar": "KT", "email": "kip.thorne.b6@starapp.io"},
    {"id": "m_b6_19", "band": "B6", "name": "Roger Penrose", "role": "Solutions Designer", "avatar": "RP", "email": "roger.penrose.b6@starapp.io"},
    {"id": "m_b6_20", "band": "B6", "name": "Freeman Dyson", "role": "Solutions Designer", "avatar": "FD", "email": "freeman.dyson.b6@starapp.io"},
    {"id": "m_b6_21", "band": "B6", "name": "Linus Torvalds", "role": "Systems Engineer", "avatar": "LT", "email": "linus.torvalds.b6@starapp.io"},
    {"id": "m_b6_22", "band": "B6", "name": "Ken Thompson", "role": "Systems Engineer", "avatar": "KT", "email": "ken.thompson.b6@starapp.io"},
    {"id": "m_b6_23", "band": "B6", "name": "Dennis Ritchie", "role": "Systems Engineer", "avatar": "DR", "email": "dennis.ritchie.b6@starapp.io"},
    {"id": "m_b6_24", "band": "B6", "name": "Brian Kernighan", "role": "Systems Engineer", "avatar": "BK", "email": "brian.kernighan.b6@starapp.io"},
    {"id": "m_b6_25", "band": "B6", "name": "Bjarne Stroustrup", "role": "Systems Engineer", "avatar": "BS", "email": "bjarne.stroustrup.b6@starapp.io"},
    {"id": "m_b6_26", "band": "B6", "name": "Guido van Rossum", "role": "Systems Engineer", "avatar": "GV", "email": "guido.van.rossum.b6@starapp.io"},
    {"id": "m_b6_27", "band": "B6", "name": "Rob Pike", "role": "Systems Engineer", "avatar": "RP", "email": "rob.pike.b6@starapp.io"},

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

