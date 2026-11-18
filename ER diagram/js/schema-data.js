/**
 * STAR APP DATABASE SCHEMA DATA
 * Preserves all 29 tables, attributes, PK/FK classifications and notes.
 */
window.STAR_APP_SCHEMA = {
  "rootName": "STAR APP DATABASE",
  "modules": [
    {
        "id": "mod_01",
        "num": "01",
        "name": "ORGANIZATION & EMPLOYEE MANAGEMENT",
        "color": "#3B82F6",
        "submodules": [
            {
                "id": "submod_01_1",
                "name": "Company Management",
                "tables": [
                    "COMPANY",
                    "BANDS"
                ]
            },
            {
                "id": "submod_01_2",
                "name": "Employee Management",
                "tables": [
                    "EMPLOYEE_CATEGORIES",
                    "EMPLOYEES"
                ]
            },
            {
                "id": "submod_01_3",
                "name": "Application Role Management",
                "tables": [
                    "SYSTEM_ROLES",
                    "EMPLOYEE_ROLES"
                ]
            }
        ]
    },
    {
        "id": "mod_02",
        "num": "02",
        "name": "POWERS, CAPABILITIES & SKILLS",
        "color": "#8B5CF6",
        "submodules": [
            {
                "id": "submod_02_1",
                "name": "Power Management",
                "tables": [
                    "POWERS"
                ]
            },
            {
                "id": "submod_02_2",
                "name": "Capability Management",
                "tables": [
                    "CAPABILITIES"
                ]
            },
            {
                "id": "submod_02_3",
                "name": "Skill Management",
                "tables": [
                    "SKILLS"
                ]
            }
        ]
    },
    {
        "id": "mod_03",
        "num": "03",
        "name": "BADGE MANAGEMENT",
        "color": "#EC4899",
        "submodules": [
            {
                "id": "submod_03_1",
                "name": "Badge Master",
                "tables": [
                    "BADGES"
                ]
            },
            {
                "id": "submod_03_2",
                "name": "Badge Version Management",
                "tables": [
                    "BADGE_VERSIONS"
                ]
            },
            {
                "id": "submod_03_3",
                "name": "Initial Badge Review",
                "tables": [
                    "BADGE_REVIEWS"
                ]
            },
            {
                "id": "submod_03_4",
                "name": "Badge Publication",
                "tables": [
                    "BADGE_PUBLICATIONS"
                ]
            },
            {
                "id": "submod_03_5",
                "name": "Badge Eligibility",
                "tables": [
                    "BADGE_ELIGIBILITY"
                ]
            }
        ]
    },
    {
        "id": "mod_04",
        "num": "04",
        "name": "BADGE ALLOCATION",
        "color": "#F59E0B",
        "submodules": [
            {
                "id": "submod_04_1",
                "name": "Allocation Campaign Management",
                "tables": [
                    "BADGE_ALLOCATION_CAMPAIGNS"
                ]
            },
            {
                "id": "submod_04_2",
                "name": "Cosmonaut Selection",
                "tables": [
                    "CAMPAIGN_COSMONAUTS"
                ]
            }
        ]
    },
    {
        "id": "mod_05",
        "num": "05",
        "name": "REVIEWER REQUESTS & PYTHON MAPPING",
        "color": "#10B981",
        "submodules": [
            {
                "id": "submod_05_1",
                "name": "Reviewer Request Management",
                "tables": [
                    "REVIEWER_REQUESTS"
                ]
            },
            {
                "id": "submod_05_2",
                "name": "Python Mapping Execution",
                "tables": [
                    "MAPPING_RUNS"
                ]
            },
            {
                "id": "submod_05_3",
                "name": "Reviewer-Cosmonaut Mapping",
                "tables": [
                    "REVIEWER_COSMONAUT_MAPPING"
                ]
            }
        ]
    },
    {
        "id": "mod_06",
        "num": "06",
        "name": "PROJECT MANAGEMENT",
        "color": "#06B6D4",
        "submodules": [
            {
                "id": "submod_06_1",
                "name": "Project Creation",
                "tables": [
                    "PROJECTS"
                ]
            },
            {
                "id": "submod_06_2",
                "name": "Project Assessment Criteria",
                "tables": [
                    "PROJECT_CRITERIA"
                ]
            },
            {
                "id": "submod_06_3",
                "name": "Project Deliverables",
                "tables": [
                    "PROJECT_DELIVERABLES"
                ]
            },
            {
                "id": "submod_06_4",
                "name": "Project Assignment",
                "tables": [
                    "PROJECT_ASSIGNMENTS"
                ]
            }
        ]
    },
    {
        "id": "mod_07",
        "num": "07",
        "name": "ASSESSMENT MANAGEMENT",
        "color": "#6366F1",
        "submodules": [
            {
                "id": "submod_07_1",
                "name": "Assessment Attempts",
                "tables": [
                    "ASSESSMENT_ATTEMPTS"
                ]
            },
            {
                "id": "submod_07_2",
                "name": "Submission Management",
                "tables": [
                    "PROJECT_SUBMISSIONS"
                ]
            },
            {
                "id": "submod_07_3",
                "name": "Assessment Scoring",
                "tables": [
                    "ASSESSMENT_SCORES"
                ]
            },
            {
                "id": "submod_07_4",
                "name": "Review Reports",
                "tables": [
                    "REVIEW_REPORTS"
                ]
            }
        ]
    },
    {
        "id": "mod_08",
        "num": "08",
        "name": "GUARDIAN DECISIONS & BADGE AWARDS",
        "color": "#F43F5E",
        "submodules": [
            {
                "id": "submod_08_1",
                "name": "Guardian Decisions",
                "tables": [
                    "GUARDIAN_DECISIONS"
                ]
            },
            {
                "id": "submod_08_2",
                "name": "Badge Award Management",
                "tables": [
                    "BADGE_AWARDS"
                ]
            }
        ]
    }
],
  "tables": {
    "COMPANY": {
        "table_number": 1,
        "name": "COMPANY",
        "module_info": {
            "module_id": "mod_01",
            "module_name": "ORGANIZATION & EMPLOYEE MANAGEMENT",
            "module_color": "#3B82F6",
            "submodule_id": "submod_01_1",
            "submodule_name": "Company Management"
        },
        "columns": [
            {
                "name": "company_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: company_id"
            },
            {
                "name": "company_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "company_name"
            },
            {
                "name": "description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "description"
            },
            {
                "name": "created_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "created_at"
            }
        ],
        "notes": []
    },
    "BANDS": {
        "table_number": 2,
        "name": "BANDS",
        "module_info": {
            "module_id": "mod_01",
            "module_name": "ORGANIZATION & EMPLOYEE MANAGEMENT",
            "module_color": "#3B82F6",
            "submodule_id": "submod_01_1",
            "submodule_name": "Company Management"
        },
        "columns": [
            {
                "name": "band_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: band_id"
            },
            {
                "name": "company_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "COMPANY.company_id",
                "raw": "FK: company_id \u2192 COMPANY.company_id"
            },
            {
                "name": "band_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "band_name"
            },
            {
                "name": "band_level",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "band_level"
            },
            {
                "name": "description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "description"
            }
        ],
        "notes": [
            "Band records:",
            "- B1",
            "- B2",
            "- B3",
            "- B4",
            "- B5",
            "- B6",
            "band_level represents employee seniority."
        ]
    },
    "EMPLOYEE_CATEGORIES": {
        "table_number": 3,
        "name": "EMPLOYEE_CATEGORIES",
        "module_info": {
            "module_id": "mod_01",
            "module_name": "ORGANIZATION & EMPLOYEE MANAGEMENT",
            "module_color": "#3B82F6",
            "submodule_id": "submod_01_2",
            "submodule_name": "Employee Management"
        },
        "columns": [
            {
                "name": "category_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: category_id"
            },
            {
                "name": "category_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "category_name"
            },
            {
                "name": "description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "description"
            }
        ],
        "notes": [
            "Employee categories:",
            "- AI Engineer",
            "- Solution Designer",
            "- System Engineer"
        ]
    },
    "EMPLOYEES": {
        "table_number": 4,
        "name": "EMPLOYEES",
        "module_info": {
            "module_id": "mod_01",
            "module_name": "ORGANIZATION & EMPLOYEE MANAGEMENT",
            "module_color": "#3B82F6",
            "submodule_id": "submod_01_2",
            "submodule_name": "Employee Management"
        },
        "columns": [
            {
                "name": "employee_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: employee_id"
            },
            {
                "name": "company_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "COMPANY.company_id",
                "raw": "FK: company_id \u2192 COMPANY.company_id"
            },
            {
                "name": "band_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BANDS.band_id",
                "raw": "FK: band_id \u2192 BANDS.band_id"
            },
            {
                "name": "category_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEE_CATEGORIES.category_id",
                "raw": "FK: category_id \u2192 EMPLOYEE_CATEGORIES.category_id"
            },
            {
                "name": "employee_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "employee_name"
            },
            {
                "name": "email",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "email"
            },
            {
                "name": "employee_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "employee_status"
            },
            {
                "name": "created_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "created_at"
            }
        ],
        "notes": []
    },
    "SYSTEM_ROLES": {
        "table_number": 5,
        "name": "SYSTEM_ROLES",
        "module_info": {
            "module_id": "mod_01",
            "module_name": "ORGANIZATION & EMPLOYEE MANAGEMENT",
            "module_color": "#3B82F6",
            "submodule_id": "submod_01_3",
            "submodule_name": "Application Role Management"
        },
        "columns": [
            {
                "name": "role_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: role_id"
            },
            {
                "name": "role_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "role_name"
            },
            {
                "name": "description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "description"
            }
        ],
        "notes": [
            "Application roles:",
            "- Guardian",
            "- Badge Reviewer",
            "- Project Reviewer",
            "- Cosmonaut"
        ]
    },
    "EMPLOYEE_ROLES": {
        "table_number": 6,
        "name": "EMPLOYEE_ROLES",
        "module_info": {
            "module_id": "mod_01",
            "module_name": "ORGANIZATION & EMPLOYEE MANAGEMENT",
            "module_color": "#3B82F6",
            "submodule_id": "submod_01_3",
            "submodule_name": "Application Role Management"
        },
        "columns": [
            {
                "name": "employee_role_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: employee_role_id"
            },
            {
                "name": "employee_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: employee_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "role_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "SYSTEM_ROLES.role_id",
                "raw": "FK: role_id \u2192 SYSTEM_ROLES.role_id"
            },
            {
                "name": "assigned_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "assigned_at"
            },
            {
                "name": "assigned_by",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: assigned_by \u2192 EMPLOYEES.employee_id"
            }
        ],
        "notes": [
            "Important business rule:",
            "One employee can have multiple application roles.",
            "A Badge Reviewer can also be a Project Reviewer.",
            "Do not create separate employee tables for each role."
        ]
    },
    "POWERS": {
        "table_number": 7,
        "name": "POWERS",
        "module_info": {
            "module_id": "mod_02",
            "module_name": "POWERS, CAPABILITIES & SKILLS",
            "module_color": "#8B5CF6",
            "submodule_id": "submod_02_1",
            "submodule_name": "Power Management"
        },
        "columns": [
            {
                "name": "power_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: power_id"
            },
            {
                "name": "power_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "power_name"
            },
            {
                "name": "description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "description"
            }
        ],
        "notes": [
            "Power records:",
            "- DOMAIN",
            "- TECH",
            "- LEADERSHIP"
        ]
    },
    "CAPABILITIES": {
        "table_number": 8,
        "name": "CAPABILITIES",
        "module_info": {
            "module_id": "mod_02",
            "module_name": "POWERS, CAPABILITIES & SKILLS",
            "module_color": "#8B5CF6",
            "submodule_id": "submod_02_2",
            "submodule_name": "Capability Management"
        },
        "columns": [
            {
                "name": "capability_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: capability_id"
            },
            {
                "name": "category_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEE_CATEGORIES.category_id",
                "raw": "FK: category_id \u2192 EMPLOYEE_CATEGORIES.category_id"
            },
            {
                "name": "power_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "POWERS.power_id",
                "raw": "FK: power_id \u2192 POWERS.power_id"
            },
            {
                "name": "capability_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "capability_name"
            },
            {
                "name": "description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "description"
            }
        ],
        "notes": []
    },
    "SKILLS": {
        "table_number": 9,
        "name": "SKILLS",
        "module_info": {
            "module_id": "mod_02",
            "module_name": "POWERS, CAPABILITIES & SKILLS",
            "module_color": "#8B5CF6",
            "submodule_id": "submod_02_3",
            "submodule_name": "Skill Management"
        },
        "columns": [
            {
                "name": "skill_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: skill_id"
            },
            {
                "name": "capability_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "CAPABILITIES.capability_id",
                "raw": "FK: capability_id \u2192 CAPABILITIES.capability_id"
            },
            {
                "name": "skill_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "skill_name"
            },
            {
                "name": "description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "description"
            }
        ],
        "notes": [
            "Important relationship:",
            "Each employee category has capabilities under the three powers.",
            "Each capability has its associated skills.",
            "Each skill can have multiple badges."
        ]
    },
    "BADGES": {
        "table_number": 10,
        "name": "BADGES",
        "module_info": {
            "module_id": "mod_03",
            "module_name": "BADGE MANAGEMENT",
            "module_color": "#EC4899",
            "submodule_id": "submod_03_1",
            "submodule_name": "Badge Master"
        },
        "columns": [
            {
                "name": "badge_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: badge_id"
            },
            {
                "name": "skill_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "SKILLS.skill_id",
                "raw": "FK: skill_id \u2192 SKILLS.skill_id"
            },
            {
                "name": "created_by",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: created_by \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "badge_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "badge_name"
            },
            {
                "name": "badge_description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "badge_description"
            },
            {
                "name": "current_version",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "current_version"
            },
            {
                "name": "badge_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "badge_status"
            },
            {
                "name": "created_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "created_at"
            },
            {
                "name": "updated_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "updated_at"
            }
        ],
        "notes": [
            "Possible badge statuses:",
            "- Draft",
            "- Under Review",
            "- Approved",
            "- Published",
            "- Archived"
        ]
    },
    "BADGE_VERSIONS": {
        "table_number": 11,
        "name": "BADGE_VERSIONS",
        "module_info": {
            "module_id": "mod_03",
            "module_name": "BADGE MANAGEMENT",
            "module_color": "#EC4899",
            "submodule_id": "submod_03_2",
            "submodule_name": "Badge Version Management"
        },
        "columns": [
            {
                "name": "version_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: version_id"
            },
            {
                "name": "badge_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGES.badge_id",
                "raw": "FK: badge_id \u2192 BADGES.badge_id"
            },
            {
                "name": "version_number",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "version_number"
            },
            {
                "name": "badge_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "badge_name"
            },
            {
                "name": "badge_description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "badge_description"
            },
            {
                "name": "badge_content",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "badge_content"
            },
            {
                "name": "created_by",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: created_by \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "created_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "created_at"
            }
        ],
        "notes": [
            "Purpose:",
            "Maintain historical versions of badges.",
            "Do not overwrite previous versions when a badge is edited."
        ]
    },
    "BADGE_REVIEWS": {
        "table_number": 12,
        "name": "BADGE_REVIEWS",
        "module_info": {
            "module_id": "mod_03",
            "module_name": "BADGE MANAGEMENT",
            "module_color": "#EC4899",
            "submodule_id": "submod_03_3",
            "submodule_name": "Initial Badge Review"
        },
        "columns": [
            {
                "name": "badge_review_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: badge_review_id"
            },
            {
                "name": "badge_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGES.badge_id",
                "raw": "FK: badge_id \u2192 BADGES.badge_id"
            },
            {
                "name": "version_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGE_VERSIONS.version_id",
                "raw": "FK: version_id \u2192 BADGE_VERSIONS.version_id"
            },
            {
                "name": "reviewer_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: reviewer_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "assigned_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "assigned_at"
            },
            {
                "name": "deadline_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "deadline_at"
            },
            {
                "name": "completed_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "completed_at"
            },
            {
                "name": "review_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "review_status"
            },
            {
                "name": "reviewer_comments",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "reviewer_comments"
            },
            {
                "name": "decision",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "decision"
            }
        ],
        "notes": [
            "The initial badge review has a 48-hour review window.",
            "Possible decisions:",
            "- Approved",
            "- Changes Requested"
        ]
    },
    "BADGE_PUBLICATIONS": {
        "table_number": 13,
        "name": "BADGE_PUBLICATIONS",
        "module_info": {
            "module_id": "mod_03",
            "module_name": "BADGE MANAGEMENT",
            "module_color": "#EC4899",
            "submodule_id": "submod_03_4",
            "submodule_name": "Badge Publication"
        },
        "columns": [
            {
                "name": "publication_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: publication_id"
            },
            {
                "name": "badge_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGES.badge_id",
                "raw": "FK: badge_id \u2192 BADGES.badge_id"
            },
            {
                "name": "version_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGE_VERSIONS.version_id",
                "raw": "FK: version_id \u2192 BADGE_VERSIONS.version_id"
            },
            {
                "name": "published_by",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: published_by \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "published_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "published_at"
            },
            {
                "name": "publication_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "publication_status"
            }
        ],
        "notes": [
            "The Guardian publishes the approved badge."
        ]
    },
    "BADGE_ELIGIBILITY": {
        "table_number": 14,
        "name": "BADGE_ELIGIBILITY",
        "module_info": {
            "module_id": "mod_03",
            "module_name": "BADGE MANAGEMENT",
            "module_color": "#EC4899",
            "submodule_id": "submod_03_5",
            "submodule_name": "Badge Eligibility"
        },
        "columns": [
            {
                "name": "eligibility_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: eligibility_id"
            },
            {
                "name": "badge_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGES.badge_id",
                "raw": "FK: badge_id \u2192 BADGES.badge_id"
            },
            {
                "name": "band_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BANDS.band_id",
                "raw": "FK: band_id \u2192 BANDS.band_id"
            },
            {
                "name": "category_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEE_CATEGORIES.category_id",
                "raw": "FK: category_id \u2192 EMPLOYEE_CATEGORIES.category_id"
            },
            {
                "name": "is_active",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "is_active"
            }
        ],
        "notes": [
            "Purpose:",
            "Define which bands and employee categories are eligible for a particular badge."
        ]
    },
    "BADGE_ALLOCATION_CAMPAIGNS": {
        "table_number": 15,
        "name": "BADGE_ALLOCATION_CAMPAIGNS",
        "module_info": {
            "module_id": "mod_04",
            "module_name": "BADGE ALLOCATION",
            "module_color": "#F59E0B",
            "submodule_id": "submod_04_1",
            "submodule_name": "Allocation Campaign Management"
        },
        "columns": [
            {
                "name": "campaign_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: campaign_id"
            },
            {
                "name": "badge_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGES.badge_id",
                "raw": "FK: badge_id \u2192 BADGES.badge_id"
            },
            {
                "name": "publication_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGE_PUBLICATIONS.publication_id",
                "raw": "FK: publication_id \u2192 BADGE_PUBLICATIONS.publication_id"
            },
            {
                "name": "band_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BANDS.band_id",
                "raw": "FK: band_id \u2192 BANDS.band_id"
            },
            {
                "name": "category_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEE_CATEGORIES.category_id",
                "raw": "FK: category_id \u2192 EMPLOYEE_CATEGORIES.category_id"
            },
            {
                "name": "guardian_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: guardian_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "campaign_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "campaign_name"
            },
            {
                "name": "campaign_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "campaign_status"
            },
            {
                "name": "estimated_review_start_date",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "estimated_review_start_date"
            },
            {
                "name": "estimated_review_end_date",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "estimated_review_end_date"
            },
            {
                "name": "created_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "created_at"
            }
        ],
        "notes": [
            "Purpose:",
            "Represent one badge allocation activity initiated by the Guardian."
        ]
    },
    "CAMPAIGN_COSMONAUTS": {
        "table_number": 16,
        "name": "CAMPAIGN_COSMONAUTS",
        "module_info": {
            "module_id": "mod_04",
            "module_name": "BADGE ALLOCATION",
            "module_color": "#F59E0B",
            "submodule_id": "submod_04_2",
            "submodule_name": "Cosmonaut Selection"
        },
        "columns": [
            {
                "name": "campaign_cosmonaut_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: campaign_cosmonaut_id"
            },
            {
                "name": "campaign_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGE_ALLOCATION_CAMPAIGNS.campaign_id",
                "raw": "FK: campaign_id \u2192 BADGE_ALLOCATION_CAMPAIGNS.campaign_id"
            },
            {
                "name": "cosmonaut_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: cosmonaut_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "selected_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "selected_at"
            },
            {
                "name": "assignment_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "assignment_status"
            }
        ],
        "notes": [
            "Purpose:",
            "Maintain the Cosmonauts selected for each allocation campaign."
        ]
    },
    "REVIEWER_REQUESTS": {
        "table_number": 17,
        "name": "REVIEWER_REQUESTS",
        "module_info": {
            "module_id": "mod_05",
            "module_name": "REVIEWER REQUESTS & PYTHON MAPPING",
            "module_color": "#10B981",
            "submodule_id": "submod_05_1",
            "submodule_name": "Reviewer Request Management"
        },
        "columns": [
            {
                "name": "request_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: request_id"
            },
            {
                "name": "campaign_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGE_ALLOCATION_CAMPAIGNS.campaign_id",
                "raw": "FK: campaign_id \u2192 BADGE_ALLOCATION_CAMPAIGNS.campaign_id"
            },
            {
                "name": "reviewer_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: reviewer_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "requested_by",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: requested_by \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "sent_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "sent_at"
            },
            {
                "name": "response_deadline",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "response_deadline"
            },
            {
                "name": "responded_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "responded_at"
            },
            {
                "name": "response_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "response_status"
            },
            {
                "name": "rejection_reason",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "rejection_reason"
            }
        ],
        "notes": [
            "Possible response statuses:",
            "- Pending",
            "- Accepted",
            "- Declined",
            "- No Response",
            "Business rule:",
            "Reviewers have 24 hours to accept or decline.",
            "If they do not respond within 24 hours, their request is automatically considered NO.",
            "The Guardian proceeds without that reviewer.",
            "Do not automatically select another reviewer.",
            "Only accepted reviewers are eligible for Python mapping."
        ]
    },
    "MAPPING_RUNS": {
        "table_number": 18,
        "name": "MAPPING_RUNS",
        "module_info": {
            "module_id": "mod_05",
            "module_name": "REVIEWER REQUESTS & PYTHON MAPPING",
            "module_color": "#10B981",
            "submodule_id": "submod_05_2",
            "submodule_name": "Python Mapping Execution"
        },
        "columns": [
            {
                "name": "mapping_batch_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: mapping_batch_id"
            },
            {
                "name": "campaign_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGE_ALLOCATION_CAMPAIGNS.campaign_id",
                "raw": "FK: campaign_id \u2192 BADGE_ALLOCATION_CAMPAIGNS.campaign_id"
            },
            {
                "name": "algorithm_version",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "algorithm_version"
            },
            {
                "name": "started_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "started_at"
            },
            {
                "name": "completed_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "completed_at"
            },
            {
                "name": "run_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "run_status"
            },
            {
                "name": "input_cosmonaut_count",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "input_cosmonaut_count"
            },
            {
                "name": "approved_reviewer_count",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "approved_reviewer_count"
            }
        ],
        "notes": [
            "Purpose:",
            "Maintain the history of Python mapping executions."
        ]
    },
    "REVIEWER_COSMONAUT_MAPPING": {
        "table_number": 19,
        "name": "REVIEWER_COSMONAUT_MAPPING",
        "module_info": {
            "module_id": "mod_05",
            "module_name": "REVIEWER REQUESTS & PYTHON MAPPING",
            "module_color": "#10B981",
            "submodule_id": "submod_05_3",
            "submodule_name": "Reviewer-Cosmonaut Mapping"
        },
        "columns": [
            {
                "name": "mapping_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: mapping_id"
            },
            {
                "name": "campaign_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGE_ALLOCATION_CAMPAIGNS.campaign_id",
                "raw": "FK: campaign_id \u2192 BADGE_ALLOCATION_CAMPAIGNS.campaign_id"
            },
            {
                "name": "mapping_batch_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "MAPPING_RUNS.mapping_batch_id",
                "raw": "FK: mapping_batch_id \u2192 MAPPING_RUNS.mapping_batch_id"
            },
            {
                "name": "cosmonaut_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: cosmonaut_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "reviewer_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: reviewer_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "mapped_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "mapped_at"
            },
            {
                "name": "mapping_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "mapping_status"
            }
        ],
        "notes": [
            "Business rules:",
            "- Only accepted reviewers can receive assignments.",
            "- Reviewers must belong to higher bands than their assigned Cosmonauts.",
            "- Python distributes Cosmonauts as equally as possible among accepted reviewers.",
            "- Each Cosmonaut has one assigned reviewer within a campaign.",
            "Reviewer band eligibility:",
            "Do not hardcode six separate eligibility tables. The band_level attribute determines seniority."
        ]
    },
    "PROJECTS": {
        "table_number": 20,
        "name": "PROJECTS",
        "module_info": {
            "module_id": "mod_06",
            "module_name": "PROJECT MANAGEMENT",
            "module_color": "#06B6D4",
            "submodule_id": "submod_06_1",
            "submodule_name": "Project Creation"
        },
        "columns": [
            {
                "name": "project_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: project_id"
            },
            {
                "name": "campaign_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGE_ALLOCATION_CAMPAIGNS.campaign_id",
                "raw": "FK: campaign_id \u2192 BADGE_ALLOCATION_CAMPAIGNS.campaign_id"
            },
            {
                "name": "reviewer_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: reviewer_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "project_title",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "project_title"
            },
            {
                "name": "project_description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "project_description"
            },
            {
                "name": "project_prompt",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "project_prompt"
            },
            {
                "name": "difficulty_level",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "difficulty_level"
            },
            {
                "name": "badge_details",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "badge_details"
            },
            {
                "name": "creation_started_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "creation_started_at"
            },
            {
                "name": "creation_deadline",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "creation_deadline"
            },
            {
                "name": "created_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "created_at"
            },
            {
                "name": "submitted_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "submitted_at"
            },
            {
                "name": "project_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "project_status"
            }
        ],
        "notes": [
            "Purpose:",
            "The Project Reviewer creates the assessment project.",
            "The project creation timeline is initially three days (72 hours), but can be changed."
        ]
    },
    "PROJECT_CRITERIA": {
        "table_number": 21,
        "name": "PROJECT_CRITERIA",
        "module_info": {
            "module_id": "mod_06",
            "module_name": "PROJECT MANAGEMENT",
            "module_color": "#06B6D4",
            "submodule_id": "submod_06_2",
            "submodule_name": "Project Assessment Criteria"
        },
        "columns": [
            {
                "name": "criterion_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: criterion_id"
            },
            {
                "name": "project_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "PROJECTS.project_id",
                "raw": "FK: project_id \u2192 PROJECTS.project_id"
            },
            {
                "name": "criterion_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "criterion_name"
            },
            {
                "name": "criterion_description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "criterion_description"
            },
            {
                "name": "maximum_marks",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "maximum_marks"
            },
            {
                "name": "display_order",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "display_order"
            }
        ],
        "notes": [
            "A project can contain multiple assessment criteria."
        ]
    },
    "PROJECT_DELIVERABLES": {
        "table_number": 22,
        "name": "PROJECT_DELIVERABLES",
        "module_info": {
            "module_id": "mod_06",
            "module_name": "PROJECT MANAGEMENT",
            "module_color": "#06B6D4",
            "submodule_id": "submod_06_3",
            "submodule_name": "Project Deliverables"
        },
        "columns": [
            {
                "name": "deliverable_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: deliverable_id"
            },
            {
                "name": "project_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "PROJECTS.project_id",
                "raw": "FK: project_id \u2192 PROJECTS.project_id"
            },
            {
                "name": "deliverable_name",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "deliverable_name"
            },
            {
                "name": "deliverable_description",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "deliverable_description"
            },
            {
                "name": "submission_format",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "submission_format"
            },
            {
                "name": "is_mandatory",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "is_mandatory"
            }
        ],
        "notes": [
            "Purpose:",
            "Define the required project deliverables."
        ]
    },
    "PROJECT_ASSIGNMENTS": {
        "table_number": 23,
        "name": "PROJECT_ASSIGNMENTS",
        "module_info": {
            "module_id": "mod_06",
            "module_name": "PROJECT MANAGEMENT",
            "module_color": "#06B6D4",
            "submodule_id": "submod_06_4",
            "submodule_name": "Project Assignment"
        },
        "columns": [
            {
                "name": "project_assignment_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: project_assignment_id"
            },
            {
                "name": "project_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "PROJECTS.project_id",
                "raw": "FK: project_id \u2192 PROJECTS.project_id"
            },
            {
                "name": "mapping_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": true,
                "references": "REVIEWER_COSMONAUT_MAPPING.mapping_id",
                "raw": "FK: mapping_id \u2192 REVIEWER_COSMONAUT_MAPPING.mapping_id"
            },
            {
                "name": "assigned_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "assigned_at"
            },
            {
                "name": "assignment_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "assignment_status"
            }
        ],
        "notes": [
            "Purpose:",
            "Connect a project with an individual mapped Cosmonaut.",
            "A reviewer may create a project for multiple Cosmonauts.",
            "Use project assignments to maintain individual assignment records without unnecessarily duplicating project definitions."
        ]
    },
    "ASSESSMENT_ATTEMPTS": {
        "table_number": 24,
        "name": "ASSESSMENT_ATTEMPTS",
        "module_info": {
            "module_id": "mod_07",
            "module_name": "ASSESSMENT MANAGEMENT",
            "module_color": "#6366F1",
            "submodule_id": "submod_07_1",
            "submodule_name": "Assessment Attempts"
        },
        "columns": [
            {
                "name": "attempt_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: attempt_id"
            },
            {
                "name": "project_assignment_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "PROJECT_ASSIGNMENTS.project_assignment_id",
                "raw": "FK: project_assignment_id \u2192 PROJECT_ASSIGNMENTS.project_assignment_id"
            },
            {
                "name": "attempt_number",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "attempt_number"
            },
            {
                "name": "preparation_start_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "preparation_start_at"
            },
            {
                "name": "preparation_deadline",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "preparation_deadline"
            },
            {
                "name": "assessment_date",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "assessment_date"
            },
            {
                "name": "assessment_start_time",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "assessment_start_time"
            },
            {
                "name": "assessment_end_time",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "assessment_end_time"
            },
            {
                "name": "scheduled_by",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: scheduled_by \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "attempt_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "attempt_status"
            },
            {
                "name": "started_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "started_at"
            },
            {
                "name": "completed_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "completed_at"
            }
        ],
        "notes": [
            "Purpose:",
            "Maintain every initial assessment and reattempt.",
            "Each attempt can have different preparation and assessment schedules.",
            "The three-day preparation period is configurable.",
            "Important:",
            "Reattempts must use the same Project Reviewer associated with the original project assignment.",
            "A new assessment attempt must not create a new reviewer mapping."
        ]
    },
    "PROJECT_SUBMISSIONS": {
        "table_number": 25,
        "name": "PROJECT_SUBMISSIONS",
        "module_info": {
            "module_id": "mod_07",
            "module_name": "ASSESSMENT MANAGEMENT",
            "module_color": "#6366F1",
            "submodule_id": "submod_07_2",
            "submodule_name": "Submission Management"
        },
        "columns": [
            {
                "name": "submission_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: submission_id"
            },
            {
                "name": "attempt_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "ASSESSMENT_ATTEMPTS.attempt_id",
                "raw": "FK: attempt_id \u2192 ASSESSMENT_ATTEMPTS.attempt_id"
            },
            {
                "name": "submission_version",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "submission_version"
            },
            {
                "name": "submission_content",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "submission_content"
            },
            {
                "name": "submission_file_url",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "submission_file_url"
            },
            {
                "name": "submitted_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "submitted_at"
            },
            {
                "name": "submission_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "submission_status"
            }
        ],
        "notes": [
            "Purpose:",
            "Store individual submissions and their versions.",
            "Previous submissions must remain available during reattempts."
        ]
    },
    "ASSESSMENT_SCORES": {
        "table_number": 26,
        "name": "ASSESSMENT_SCORES",
        "module_info": {
            "module_id": "mod_07",
            "module_name": "ASSESSMENT MANAGEMENT",
            "module_color": "#6366F1",
            "submodule_id": "submod_07_3",
            "submodule_name": "Assessment Scoring"
        },
        "columns": [
            {
                "name": "score_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: score_id"
            },
            {
                "name": "attempt_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "ASSESSMENT_ATTEMPTS.attempt_id",
                "raw": "FK: attempt_id \u2192 ASSESSMENT_ATTEMPTS.attempt_id"
            },
            {
                "name": "criterion_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "PROJECT_CRITERIA.criterion_id",
                "raw": "FK: criterion_id \u2192 PROJECT_CRITERIA.criterion_id"
            },
            {
                "name": "marks_obtained",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "marks_obtained"
            },
            {
                "name": "reviewer_comments",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "reviewer_comments"
            },
            {
                "name": "evaluated_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "evaluated_at"
            }
        ],
        "notes": [
            "Purpose:",
            "Store marks for individual assessment criteria.",
            "Example assessment structure:",
            "- Business Understanding \u2014 10 marks",
            "- Architecture / Report \u2014 10 marks",
            "- Technical Knowledge \u2014 10 marks",
            "- Presentation \u2014 10 marks",
            "- Question & Answering \u2014 10 marks",
            "Total: 50 marks.",
            "Do not hardcode these five criteria into the database schema. They should be stored as project criteria."
        ]
    },
    "REVIEW_REPORTS": {
        "table_number": 27,
        "name": "REVIEW_REPORTS",
        "module_info": {
            "module_id": "mod_07",
            "module_name": "ASSESSMENT MANAGEMENT",
            "module_color": "#6366F1",
            "submodule_id": "submod_07_4",
            "submodule_name": "Review Reports"
        },
        "columns": [
            {
                "name": "report_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: report_id"
            },
            {
                "name": "attempt_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "ASSESSMENT_ATTEMPTS.attempt_id",
                "raw": "FK: attempt_id \u2192 ASSESSMENT_ATTEMPTS.attempt_id"
            },
            {
                "name": "total_marks",
                "key": "DERIVED",
                "is_pk": false,
                "is_fk": false,
                "is_derived": true,
                "is_unique": false,
                "references": null,
                "raw": "total_marks [DERIVED FROM ASSESSMENT_SCORES]"
            },
            {
                "name": "strengths",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "strengths"
            },
            {
                "name": "areas_of_improvement",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "areas_of_improvement"
            },
            {
                "name": "reviewer_recommendation",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "reviewer_recommendation"
            },
            {
                "name": "reviewer_comments",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "reviewer_comments"
            },
            {
                "name": "submitted_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "submitted_at"
            }
        ],
        "notes": [
            "Reviewer recommendations:",
            "- Award Badge",
            "- Reattempt",
            "The reviewer submits the completed report to the Guardian.",
            "Do not independently edit total_marks when it is calculated from assessment scores."
        ]
    },
    "GUARDIAN_DECISIONS": {
        "table_number": 28,
        "name": "GUARDIAN_DECISIONS",
        "module_info": {
            "module_id": "mod_08",
            "module_name": "GUARDIAN DECISIONS & BADGE AWARDS",
            "module_color": "#F43F5E",
            "submodule_id": "submod_08_1",
            "submodule_name": "Guardian Decisions"
        },
        "columns": [
            {
                "name": "decision_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: decision_id"
            },
            {
                "name": "attempt_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "ASSESSMENT_ATTEMPTS.attempt_id",
                "raw": "FK: attempt_id \u2192 ASSESSMENT_ATTEMPTS.attempt_id"
            },
            {
                "name": "guardian_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: guardian_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "decision",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "decision"
            },
            {
                "name": "decision_comments",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "decision_comments"
            },
            {
                "name": "decided_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "decided_at"
            }
        ],
        "notes": [
            "Possible decisions:",
            "- Award Badge",
            "- Reattempt",
            "The Guardian is the final administrator and makes the final decision.",
            "The Guardian can approve or reject the reviewer's recommendation."
        ]
    },
    "BADGE_AWARDS": {
        "table_number": 29,
        "name": "BADGE_AWARDS",
        "module_info": {
            "module_id": "mod_08",
            "module_name": "GUARDIAN DECISIONS & BADGE AWARDS",
            "module_color": "#F43F5E",
            "submodule_id": "submod_08_2",
            "submodule_name": "Badge Award Management"
        },
        "columns": [
            {
                "name": "award_id",
                "key": "PK",
                "is_pk": true,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "PK: award_id"
            },
            {
                "name": "project_assignment_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "PROJECT_ASSIGNMENTS.project_assignment_id",
                "raw": "FK: project_assignment_id \u2192 PROJECT_ASSIGNMENTS.project_assignment_id"
            },
            {
                "name": "badge_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "BADGES.badge_id",
                "raw": "FK: badge_id \u2192 BADGES.badge_id"
            },
            {
                "name": "cosmonaut_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: cosmonaut_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "guardian_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": false,
                "references": "EMPLOYEES.employee_id",
                "raw": "FK: guardian_id \u2192 EMPLOYEES.employee_id"
            },
            {
                "name": "decision_id",
                "key": "FK",
                "is_pk": false,
                "is_fk": true,
                "is_derived": false,
                "is_unique": true,
                "references": "GUARDIAN_DECISIONS.decision_id",
                "raw": "FK: decision_id \u2192 GUARDIAN_DECISIONS.decision_id"
            },
            {
                "name": "awarded_at",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "awarded_at"
            },
            {
                "name": "award_status",
                "key": null,
                "is_pk": false,
                "is_fk": false,
                "is_derived": false,
                "is_unique": false,
                "references": null,
                "raw": "award_status"
            }
        ],
        "notes": [
            "Purpose:",
            "Store successfully awarded badges.",
            "Only approved Cosmonauts should receive badge awards.",
            "# 5. COMPLETE TABLE RELATIONSHIPS",
            "Implement all relationships below.",
            "These are actual database relationships, not merely visual groupings.",
            "Use the PK and FK information to identify the correct relationship direction.",
            "```text",
            "COMPANY 1:N BANDS",
            "COMPANY 1:N EMPLOYEES",
            "BANDS 1:N EMPLOYEES",
            "EMPLOYEE_CATEGORIES 1:N EMPLOYEES",
            "EMPLOYEES 1:N EMPLOYEE_ROLES",
            "SYSTEM_ROLES 1:N EMPLOYEE_ROLES",
            "```",
            "EMPLOYEE_ROLES resolves the many-to-many relationship between EMPLOYEES and SYSTEM_ROLES.",
            "```text",
            "EMPLOYEE_CATEGORIES 1:N CAPABILITIES",
            "POWERS 1:N CAPABILITIES",
            "CAPABILITIES 1:N SKILLS",
            "```",
            "```text",
            "SKILLS 1:N BADGES",
            "EMPLOYEES 1:N BADGES",
            "(through created_by)",
            "BADGES 1:N BADGE_VERSIONS",
            "BADGES 1:N BADGE_REVIEWS",
            "BADGE_VERSIONS 1:N BADGE_REVIEWS",
            "BADGES 1:N BADGE_PUBLICATIONS",
            "BADGE_VERSIONS 1:N BADGE_PUBLICATIONS",
            "BADGES 1:N BADGE_ELIGIBILITY",
            "BANDS 1:N BADGE_ELIGIBILITY",
            "EMPLOYEE_CATEGORIES 1:N BADGE_ELIGIBILITY",
            "```",
            "```text",
            "BADGES 1:N BADGE_ALLOCATION_CAMPAIGNS",
            "BADGE_PUBLICATIONS 1:N BADGE_ALLOCATION_CAMPAIGNS",
            "BANDS 1:N BADGE_ALLOCATION_CAMPAIGNS",
            "EMPLOYEE_CATEGORIES 1:N BADGE_ALLOCATION_CAMPAIGNS",
            "BADGE_ALLOCATION_CAMPAIGNS 1:N CAMPAIGN_COSMONAUTS",
            "```",
            "```text",
            "BADGE_ALLOCATION_CAMPAIGNS 1:N REVIEWER_REQUESTS",
            "BADGE_ALLOCATION_CAMPAIGNS 1:N MAPPING_RUNS",
            "BADGE_ALLOCATION_CAMPAIGNS 1:N REVIEWER_COSMONAUT_MAPPING",
            "MAPPING_RUNS 1:N REVIEWER_COSMONAUT_MAPPING",
            "```",
            "```text",
            "BADGE_ALLOCATION_CAMPAIGNS 1:N PROJECTS",
            "PROJECTS 1:N PROJECT_CRITERIA",
            "PROJECTS 1:N PROJECT_DELIVERABLES",
            "PROJECTS 1:N PROJECT_ASSIGNMENTS",
            "REVIEWER_COSMONAUT_MAPPING 1:1 PROJECT_ASSIGNMENTS",
            "```",
            "The mapping_id in PROJECT_ASSIGNMENTS is UNIQUE.",
            "```text",
            "PROJECT_ASSIGNMENTS 1:N ASSESSMENT_ATTEMPTS",
            "ASSESSMENT_ATTEMPTS 1:N PROJECT_SUBMISSIONS",
            "ASSESSMENT_ATTEMPTS 1:N ASSESSMENT_SCORES",
            "PROJECT_CRITERIA 1:N ASSESSMENT_SCORES",
            "ASSESSMENT_ATTEMPTS 1:0..1 REVIEW_REPORTS",
            "```",
            "The assessment attempt can have one review report.",
            "```text",
            "ASSESSMENT_ATTEMPTS 1:N GUARDIAN_DECISIONS",
            "PROJECT_ASSIGNMENTS 1:0..1 BADGE_AWARDS",
            "GUARDIAN_DECISIONS 1:0..1 BADGE_AWARDS",
            "BADGES 1:N BADGE_AWARDS",
            "```",
            "# 6. PRIMARY KEY AND FOREIGN KEY VISUALIZATION",
            "When a user expands a table node, display the schema in a clear and structured format.",
            "Example:",
            "```text",
            "\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510",
            "\u2502 EMPLOYEES                                  \u2502",
            "\u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524",
            "\u2502 PK  employee_id                            \u2502",
            "\u2502 FK  company_id                              \u2502",
            "\u2502 FK  band_id                                 \u2502",
            "\u2502 FK  category_id                             \u2502",
            "\u2502     employee_name                           \u2502",
            "\u2502     email                                   \u2502",
            "\u2502     employee_status                         \u2502",
            "\u2502     created_at                              \u2502",
            "\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518",
            "```",
            "Use the following visual indicators:",
            "- PK \u2014 Primary Key",
            "- FK \u2014 Foreign Key",
            "- DERIVED \u2014 Calculated attribute",
            "Do not invent column data types.",
            "If data types are not available, display the column name and key classification without a fabricated type.",
            "When clicking an FK attribute, allow the user to navigate to the referenced table.",
            "When clicking a PK attribute, highlight all tables that reference that primary key.",
            "# 7. INTERACTIVE MIND MAP REQUIREMENTS",
            "This is the most important part of the implementation.",
            "The ER diagram must behave like an interactive hierarchical mind map.",
            "When the user opens the HTML file:",
            "Display only the main root node:",
            "STAR APP DATABASE",
            "Alternatively, you may show a clean overview with the eight main module nodes, but do not display all 29 tables and their attributes immediately.",
            "The initial view must be clean and uncluttered.",
            "Every expandable node must have its own independent expand/collapse control.",
            "Use:",
            "- (+) to expand.",
            "- (-) to collapse.",
            "Expected behavior:",
            "```text",
            "STAR APP DATABASE",
            "+ ORGANIZATION & EMPLOYEE MANAGEMENT",
            "+ POWERS, CAPABILITIES & SKILLS",
            "+ BADGE MANAGEMENT",
            "+ BADGE ALLOCATION",
            "+ REVIEWER REQUESTS & PYTHON MAPPING",
            "+ PROJECT MANAGEMENT",
            "+ ASSESSMENT MANAGEMENT",
            "+ GUARDIAN DECISIONS & BADGE AWARDS",
            "```",
            "When the user expands BADGE MANAGEMENT:",
            "```text",
            "BADGE MANAGEMENT",
            "+ Badge Master",
            "+ Badge Version Management",
            "+ Initial Badge Review",
            "+ Badge Publication",
            "+ Badge Eligibility",
            "```",
            "When the user expands Badge Master:",
            "```text",
            "Badge Master",
            "+ BADGES",
            "```",
            "When the user expands BADGES:",
            "```text",
            "BADGES",
            "+ badge_id (PK)",
            "+ skill_id (FK)",
            "+ created_by (FK)",
            "+ badge_name",
            "+ badge_description",
            "+ current_version",
            "+ badge_status",
            "+ created_at",
            "+ updated_at",
            "```",
            "This must continue for every table and every module.",
            "Multiple branches must remain expanded simultaneously.",
            "Example:",
            "The user should be able to expand:",
            "- Organization Management",
            "- Badge Management",
            "- Project Management",
            "All three branches must remain open.",
            "Expanding one branch must not automatically collapse another branch.",
            "Collapsing one branch must hide only its descendants.",
            "Do not reset the entire diagram when a single branch is collapsed.",
            "When clicking a table node, open a detailed schema panel.",
            "The panel should display:",
            "1. Table name.",
            "2. Module name.",
            "3. All columns.",
            "4. Primary key attributes.",
            "5. Foreign key attributes.",
            "6. Data types, if available.",
            "7. Referenced tables.",
            "8. Referencing tables.",
            "9. Relationship cardinalities.",
            "10. Short table description.",
            "Use a clean side panel or expandable detail card.",
            "The detailed panel should not force the entire mind map to reload.",
            "The mind map hierarchy and database relationships are two different things.",
            "Implement both.",
            "**Hierarchical relationships:**",
            "These connect the database root, modules, submodules, tables, and table attributes.",
            "**Relational relationships:**",
            "These connect actual database tables through their primary and foreign keys.",
            "For example:",
            "```text",
            "EMPLOYEES",
            "EMPLOYEE_ROLES",
            "SYSTEM_ROLES",
            "```",
            "When selecting a table, highlight its directly connected tables and their relationship lines.",
            "Provide a way to navigate to related tables.",
            "Do not confuse a logical module parent-child connection with an actual database foreign-key relationship.",
            "For readability, relational connectors should be visually distinguishable from hierarchical connectors.",
            "Consider a toggle:",
            "- Show/Hide Database Relationships.",
            "This will prevent the diagram from becoming cluttered when many branches are expanded.",
            "# 8. DYNAMIC LAYOUT ENGINE",
            "Dynamic layout is critical.",
            "Do not implement a static layout where nodes overlap when expanded.",
            "The system must automatically reposition nodes.",
            "Requirements:",
            "1. Newly expanded children must appear in the correct hierarchical position.",
            "2. Existing nodes must reposition smoothly.",
            "3. Connecting lines must update automatically.",
            "4. No overlapping nodes.",
            "5. No broken connectors.",
            "6. No clipped labels.",
            "7. No nodes appearing outside the visible workspace unexpectedly.",
            "8. Layout must remain readable with all 29 tables expanded.",
            "9. Collapsing nodes must reclaim unnecessary space.",
            "10. Multiple expanded branches must remain organized.",
            "Use a recursive, data-driven layout.",
            "The implementation should calculate node positions based on the visible hierarchy.",
            "Choose an appropriate layout direction:",
            "- Left-to-right mind map.",
            "- Top-to-bottom hierarchical layout.",
            "Prefer left-to-right if it provides better readability.",
            "The layout must support large expanded branches.",
            "Implement:",
            "- Smooth expansion.",
            "- Smooth collapse.",
            "- Smooth repositioning.",
            "- Smooth connector updates.",
            "- No sudden page-wide flickering.",
            "- No excessive re-rendering.",
            "Animations should be subtle and professional.",
            "Avoid expensive effects that reduce performance.",
            "# 9. ZOOM, PAN AND NAVIGATION",
            "Implement the following controls:",
            "- Zoom in.",
            "- Zoom out.",
            "- Reset zoom.",
            "- Fit to screen.",
            "- Drag to pan.",
            "- Mouse-wheel zoom.",
            "- Optional minimap for large diagrams.",
            "The diagram must remain usable even when many modules and tables are expanded.",
            "The user must be able to navigate the entire database without losing their position.",
            "Keep controls accessible and clearly visible.",
            "Add a search feature.",
            "Search should support:",
            "- Table names.",
            "- Column names.",
            "- Module names.",
            "- Attribute names.",
            "When a result is selected:",
            "- Navigate to the corresponding node.",
            "- Expand its parent branches if necessary.",
            "- Highlight the matching node.",
            "- Open its table details when appropriate.",
            "# 10. EXPAND ALL AND COLLAPSE ALL",
            "Provide two global controls:",
            "**Expand All**",
            "Expands all modules, submodules and tables.",
            "Table attributes may remain collapsed until the user chooses to reveal them, or be included as a separate deeper expansion level.",
            "**Collapse All**",
            "Returns the diagram to the initial root view.",
            "These actions must not remove any underlying data.",
            "Add a confirmation or warning if expanding every attribute would create a very large view.",
            "# 11. VISUAL DESIGN REQUIREMENTS",
            "Take inspiration from NotebookLM's Mind Map interface.",
            "Do not directly copy its branding or exact interface.",
            "Create a professional database visualization.",
            "- Clean and modern interface.",
            "- Rounded rectangular nodes.",
            "- Clear hierarchy.",
            "- Consistent typography.",
            "- Proper spacing.",
            "- Visible connectors.",
            "- Professional hover effects.",
            "- Smooth transitions.",
            "- No unnecessary decorations.",
            "- No overcrowded layout.",
            "- No excessive shadows or gradients.",
            "Use visually distinguishable node types:",
            "1. Root database node.",
            "2. Main module nodes.",
            "3. Submodule nodes.",
            "4. Database table nodes.",
            "5. Attribute/column nodes.",
            "Each node type should have a consistent design.",
            "Table nodes should visually identify whether they contain primary keys or foreign keys.",
            "Use small, clear PK and FK labels.",
            "Use icons only when they improve understanding.",
            "Connectors must be:",
            "- Clearly visible.",
            "- Properly aligned.",
            "- Attached to node boundaries.",
            "- Updated dynamically.",
            "- Free from unnecessary crossing where possible.",
            "Use different connector styles for:",
            "- Hierarchical parent-child connections.",
            "- Actual foreign-key relationships.",
            "Do not draw every relational connection permanently if it makes the interface unreadable. Allow users to toggle relational connections or highlight them on selection.",
            "# 12. TECHNICAL IMPLEMENTATION REQUIREMENTS",
            "Work with my existing HTML, CSS and JavaScript files.",
            "Before modifying anything:",
            "1. Inspect the complete existing project.",
            "2. Identify the existing ER diagram implementation.",
            "3. Understand how its data is stored.",
            "4. Identify reusable functions and components.",
            "5. Inspect the existing styling and dependencies.",
            "6. Determine the best way to integrate the mind map.",
            "Do not create a separate unrelated project.",
            "Do not unnecessarily rewrite existing files.",
            "Preserve the original database schema and its information.",
            "Store the database schema in a structured JavaScript data object or JSON file.",
            "Use a recursive hierarchy.",
            "Example structure:",
            "```javascript",
            "{",
            "id: \"database\",",
            "name: \"STAR APP DATABASE\",",
            "type: \"root\",",
            "children: [",
            "{",
            "id: \"organization\",",
            "name: \"ORGANIZATION & EMPLOYEE MANAGEMENT\",",
            "type: \"module\",",
            "children: [",
            "{",
            "id: \"employee-management\",",
            "name: \"Employee Management\",",
            "type: \"submodule\",",
            "children: [",
            "{",
            "id: \"employees\",",
            "name: \"EMPLOYEES\",",
            "type: \"table\",",
            "columns: [",
            "{",
            "name: \"employee_id\",",
            "key: \"PK\"",
            "},",
            "{",
            "name: \"company_id\",",
            "key: \"FK\",",
            "references: \"COMPANY.company_id\"",
            "}",
            "]",
            "}",
            "]",
            "}",
            "]",
            "}",
            "]",
            "}",
            "```",
            "This is an illustrative structure.",
            "Implement the complete data for all 29 actual tables.",
            "Do not manually hardcode individual click handlers for every table.",
            "All nodes should be generated from the structured data.",
            "Keep these responsibilities separate:",
            "- Database schema data.",
            "- Hierarchical mind map data.",
            "- Relational relationship data.",
            "- Node rendering.",
            "- Expansion and collapse state.",
            "- Layout calculation.",
            "- Connector rendering.",
            "- Search and navigation.",
            "- Table details.",
            "Prefer the existing project dependencies.",
            "Do not introduce unnecessary libraries.",
            "If you need a graph layout library, first examine the existing implementation and determine whether it can handle the required dynamic positioning.",
            "If an additional library is genuinely necessary:",
            "1. Explain why it is needed.",
            "2. Explain what problem it solves.",
            "3. Select the smallest suitable dependency.",
            "4. Avoid adding multiple libraries that perform the same function.",
            "Do not introduce an unnecessary framework migration.",
            "Ensure:",
            "- Efficient rendering.",
            "- No unnecessary full-page re-rendering.",
            "- Independent branch state.",
            "- Stable node identities.",
            "- Efficient connector updates.",
            "- No memory leaks.",
            "- No repeated event listeners.",
            "- No continuous unnecessary animation.",
            "- No UI flickering.",
            "- No layout recalculation loops.",
            "# 13. USER INTERFACE STRUCTURE",
            "Create a professional workspace.",
            "Suggested layout:",
            "```text",
            "\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510",
            "\u2502 STAR APP \u2014 DATABASE MIND MAP                                \u2502",
            "\u2502                                                             \u2502",
            "\u2502 Search tables / columns         Expand All   Collapse All   \u2502",
            "\u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524",
            "\u2502                                                             \u2502",
            "\u2502                                                             \u2502",
            "\u2502                  INTERACTIVE MIND MAP                       \u2502",
            "\u2502                                                             \u2502",
            "\u2502                                                             \u2502",
            "\u2502                                                             \u2502",
            "\u2502                                                             \u2502",
            "\u2502                                                             \u2502",
            "\u2502                                                             \u2502",
            "\u2502                                                             \u2502",
            "\u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524",
            "\u2502 Zoom -     Zoom +      Fit to Screen      Reset View        \u2502",
            "\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518",
            "```",
            "When a table is selected, show a detail panel:",
            "```text",
            "\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510",
            "\u2502 TABLE DETAILS                               \u2502",
            "\u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524",
            "\u2502 Table: EMPLOYEES                            \u2502",
            "\u2502 Module: ORGANIZATION & EMPLOYEE MANAGEMENT \u2502",
            "\u2502                                             \u2502",
            "\u2502 COLUMNS                                     \u2502",
            "\u2502                                             \u2502",
            "\u2502 PK  employee_id                             \u2502",
            "\u2502 FK  company_id                              \u2502",
            "\u2502 FK  band_id                                 \u2502",
            "\u2502 FK  category_id                             \u2502",
            "\u2502     employee_name                           \u2502",
            "\u2502     email                                   \u2502",
            "\u2502     employee_status                         \u2502",
            "\u2502     created_at                              \u2502",
            "\u2502                                             \u2502",
            "\u2502 RELATIONSHIPS                               \u2502",
            "\u2502                                             \u2502",
            "\u2502 COMPANY \u2192 EMPLOYEES                         \u2502",
            "\u2502 BANDS \u2192 EMPLOYEES                           \u2502",
            "\u2502 EMPLOYEE_CATEGORIES \u2192 EMPLOYEES             \u2502",
            "\u2502                                             \u2502",
            "\u2502 [View Related Tables]                       \u2502",
            "\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518",
            "```",
            "This is a suggested layout. You can improve the UI while preserving the required functionality.",
            "# 14. IMPORTANT DATABASE INTEGRITY REQUIREMENTS",
            "Do not alter these business rules.",
            "1. An employee can hold multiple application roles.",
            "2. Badge Reviewer can also become Project Reviewer.",
            "3. Guardian is the administrator and makes the final badge decision.",
            "4. Only published badges should be available for allocation.",
            "5. Cosmonauts belong to the selected band and employee category.",
            "6. Project Reviewers must belong to higher bands than their assigned Cosmonauts.",
            "7. Reviewer invitations have a 24-hour response deadline.",
            "8. No response after 24 hours is treated as NO.",
            "9. The Guardian proceeds without reviewers who decline or do not respond.",
            "10. Only accepted reviewers participate in Python mapping.",
            "11. Python distributes Cosmonauts as equally as possible.",
            "12. Each Cosmonaut receives one reviewer per campaign.",
            "13. A reviewer creates and submits the project.",
            "14. Project creation initially has a 72-hour timeline.",
            "15. Cosmonauts initially receive 72 hours to study.",
            "16. Timings can be changed.",
            "17. Projects contain criteria and deliverables.",
            "18. Each Cosmonaut has an individual project assignment.",
            "19. Assessment attempts must be maintained historically.",
            "20. Reattempts use the same original Project Reviewer.",
            "21. Reattempts can have new preparation and assessment schedules.",
            "22. Previous submissions and assessment results must not be overwritten.",
            "23. The reviewer submits marks and feedback to the Guardian.",
            "24. The Guardian makes the final Award Badge or Reattempt decision.",
            "25. Badge awards must only be created for approved Cosmonauts.",
            "The mind map is a visualization of the database. Do not implement new business rules or modify the actual database design as part of this task.",
            "# 15. TESTING AND VALIDATION",
            "After implementation, test the complete mind map.",
            "- Root node appears correctly.",
            "- All eight modules are present.",
            "- All submodules are present.",
            "- All 29 database tables are present.",
            "- Every table contains all its specified attributes.",
            "- Every expandable node has an independent control.",
            "- Expand works.",
            "- Collapse works.",
            "- Multiple branches remain expanded.",
            "- Collapsing one branch does not affect unrelated branches.",
            "- Nested expansion works at every level.",
            "- All PK attributes are identified correctly.",
            "- All FK attributes are identified correctly.",
            "- All specified table relationships are represented.",
            "- Correct relationship cardinalities are displayed.",
            "- Selecting a table highlights its related tables.",
            "- FK navigation works.",
            "- Hierarchical and relational connectors are distinguishable.",
            "- No overlapping nodes.",
            "- No broken connectors.",
            "- No clipped text.",
            "- Layout adjusts after expansion.",
            "- Layout adjusts after collapse.",
            "- Multiple expanded branches remain readable.",
            "- Large diagrams remain navigable.",
            "- Search works.",
            "- Table details open.",
            "- Zoom works.",
            "- Pan works.",
            "- Fit to screen works.",
            "- Expand All works.",
            "- Collapse All works.",
            "- Hover highlighting works.",
            "Test the final HTML file in the browser.",
            "Check for:",
            "- JavaScript errors.",
            "- Console errors.",
            "- Missing assets.",
            "- Broken interactions.",
            "- Incorrect node positioning.",
            "- Performance problems.",
            "The implementation must work as a real interactive application, not just a static illustration.",
            "# 16. EXPECTED FINAL OUTPUT",
            "I want a complete, working implementation.",
            "Deliver the following:",
            "A fully functional HTML-based mind map containing:",
            "- One root database node.",
            "- Eight logical modules.",
            "- All submodules.",
            "- All 29 database tables.",
            "- All table attributes.",
            "- PK and FK classifications.",
            "- Database relationship connectors.",
            "- Expand and collapse functionality.",
            "- Table detail exploration.",
            "- Search.",
            "- Zoom and pan.",
            "- Expand All and Collapse All.",
            "Provide the complete implementation files.",
            "Use an organized structure similar to:",
            "```text",
            "STAR-APP-ER-MINDMAP/",
            "\u2502",
            "\u251c\u2500\u2500 index.html",
            "\u2502",
            "\u251c\u2500\u2500 css/",
            "\u2502   \u2514\u2500\u2500 mindmap.css",
            "\u2502",
            "\u251c\u2500\u2500 js/",
            "\u2502   \u251c\u2500\u2500 schema-data.js",
            "\u2502   \u251c\u2500\u2500 relationships.js",
            "\u2502   \u251c\u2500\u2500 mindmap-renderer.js",
            "\u2502   \u251c\u2500\u2500 layout-engine.js",
            "\u2502   \u251c\u2500\u2500 interactions.js",
            "\u2502   \u251c\u2500\u2500 search.js",
            "\u2502   \u2514\u2500\u2500 app.js",
            "\u2502",
            "\u2514\u2500\u2500 README.md",
            "```",
            "This is a suggested structure. Reuse my existing project structure wherever possible.",
            "Do not create unnecessary files.",
            "Provide a README explaining:",
            "- How to open the application.",
            "- How the hierarchy is organized.",
            "- How expansion and collapse work.",
            "- How database relationships are represented.",
            "- How the layout engine works.",
            "- How to add a new database table.",
            "- How to add a new relationship.",
            "- Any dependencies introduced.",
            "After completing the implementation, provide a report containing:",
            "1. Files inspected.",
            "2. Files created or modified.",
            "3. Number of modules implemented.",
            "4. Number of tables implemented.",
            "5. Number of attributes implemented.",
            "6. Number of relationships implemented.",
            "7. Interactive features completed.",
            "8. Testing performed.",
            "9. Any known limitations.",
            "Do not claim that a feature is complete unless you have actually tested it.",
            "# 17. FINAL IMPLEMENTATION INSTRUCTIONS",
            "Follow these instructions strictly.",
            "**1. Preserve the database design.**",
            "All 29 tables, attributes, primary keys, foreign keys, and specified relationships must remain intact.",
            "**2. Build a real interactive mind map.**",
            "Do not simply display the existing ER diagram as an image.",
            "**3. Use progressive information disclosure.**",
            "Do not display all table attributes immediately. Reveal them when users expand the relevant nodes or select a table.",
            "**4. Prioritize dynamic layout.**",
            "The layout must automatically adjust to expansion and collapse without overlapping nodes or breaking connectors.",
            "**5. Maintain independent branches.**",
            "Users must be able to explore different database modules simultaneously.",
            "**6. Keep the visualization data-driven.**",
            "The mind map must be generated from structured database schema data, not individually hardcoded nodes.",
            "**7. Preserve the existing project.**",
            "Inspect before modifying. Reuse existing implementation wherever possible.",
            "**8. Do not stop at a visual prototype.**",
            "All interactions must work.",
            "**9. Do not omit any database information.**",
            "Verify the final implementation against all 29 tables and the complete relationship list in this prompt.",
            "**10. Do not provide only instructions or a code suggestion.**",
            "Actually implement the changes in the existing project, test them, and provide the final working HTML application and source files.",
            "Transform my current static STAR App ER diagram into a professional, interactive, dynamically expanding database mind map inspired by NotebookLM.",
            "I should be able to start from STAR APP DATABASE, progressively explore every module and submodule, expand all 29 tables, inspect every attribute, understand PK/FK relationships, navigate between related tables, and explore the entire database through a clean, responsive, smoothly animated interface.",
            "The result must be accurate, complete, maintainable, and ready to use in my browser.",
            "**Database accuracy and functional correctness are more important than decorative visual effects.**"
        ]
    }
}
};
