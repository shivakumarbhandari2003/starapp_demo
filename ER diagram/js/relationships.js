/**
 * STAR APP DATABASE RELATIONSHIPS DATA & HELPERS
 * Preserves all 42 relationships across the 8 modules from Section 5.
 */
(function() {
  const relationships = [
    // Organization Relationships
    { id: "rel_1", source: "COMPANY", target: "BANDS", cardinality: "1:N", category: "ORGANIZATION", foreign_key: "company_id", description: "Company defines hierarchical employee bands (B1–B6)" },
    { id: "rel_2", source: "COMPANY", target: "EMPLOYEES", cardinality: "1:N", category: "ORGANIZATION", foreign_key: "company_id", description: "Company employs staff members" },
    { id: "rel_3", source: "BANDS", target: "EMPLOYEES", cardinality: "1:N", category: "ORGANIZATION", foreign_key: "band_id", description: "Band assigns seniority level to employee" },
    { id: "rel_4", source: "EMPLOYEE_CATEGORIES", target: "EMPLOYEES", cardinality: "1:N", category: "ORGANIZATION", foreign_key: "category_id", description: "Category classifies employee domain (AI Engineer, Solutions Designer, Systems Engineer)" },
    { id: "rel_5", source: "EMPLOYEES", target: "EMPLOYEE_ROLES", cardinality: "1:N", category: "ORGANIZATION", foreign_key: "employee_id", description: "Employee holds one or more application roles" },
    { id: "rel_6", source: "SYSTEM_ROLES", target: "EMPLOYEE_ROLES", cardinality: "1:N", category: "ORGANIZATION", foreign_key: "role_id", description: "System role assigned to employee (Guardian, Reviewer, Cosmonaut)" },

    // Powers, Capabilities & Skills Relationships
    { id: "rel_7", source: "EMPLOYEE_CATEGORIES", target: "CAPABILITIES", cardinality: "1:N", category: "POWERS, CAPABILITIES & SKILLS", foreign_key: "category_id", description: "Each employee category has capabilities under the three powers" },
    { id: "rel_8", source: "POWERS", target: "CAPABILITIES", cardinality: "1:N", category: "POWERS, CAPABILITIES & SKILLS", foreign_key: "power_id", description: "Power groups capabilities (DOMAIN, TECH, LEADERSHIP)" },
    { id: "rel_9", source: "CAPABILITIES", target: "SKILLS", cardinality: "1:N", category: "POWERS, CAPABILITIES & SKILLS", foreign_key: "capability_id", description: "Capability breaks down into individual technical skills" },

    // Badge Management Relationships
    { id: "rel_10", source: "SKILLS", target: "BADGES", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "skill_id", description: "Each skill can have multiple badges" },
    { id: "rel_11", source: "EMPLOYEES", target: "BADGES", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "created_by", description: "Employee (author) drafts badge" },
    { id: "rel_12", source: "BADGES", target: "BADGE_VERSIONS", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "badge_id", description: "Badge retains immutable historical versions" },
    { id: "rel_13", source: "BADGES", target: "BADGE_REVIEWS", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "badge_id", description: "Badge subjected to initial peer review" },
    { id: "rel_14", source: "BADGE_VERSIONS", target: "BADGE_REVIEWS", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "version_id", description: "Specific version subjected to review window (48h)" },
    { id: "rel_15", source: "BADGES", target: "BADGE_PUBLICATIONS", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "badge_id", description: "Guardian publishes approved badge" },
    { id: "rel_16", source: "BADGE_VERSIONS", target: "BADGE_PUBLICATIONS", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "version_id", description: "Specific approved version published" },
    { id: "rel_17", source: "BADGES", target: "BADGE_ELIGIBILITY", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "badge_id", description: "Badge specifies eligibility criteria" },
    { id: "rel_18", source: "BANDS", target: "BADGE_ELIGIBILITY", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "band_id", description: "Band eligible to take badge" },
    { id: "rel_19", source: "EMPLOYEE_CATEGORIES", target: "BADGE_ELIGIBILITY", cardinality: "1:N", category: "BADGE MANAGEMENT", foreign_key: "category_id", description: "Category eligible to take badge" },

    // Badge Allocation Relationships
    { id: "rel_20", source: "BADGES", target: "BADGE_ALLOCATION_CAMPAIGNS", cardinality: "1:N", category: "BADGE ALLOCATION", foreign_key: "badge_id", description: "Campaign targets badge curriculum" },
    { id: "rel_21", source: "BADGE_PUBLICATIONS", target: "BADGE_ALLOCATION_CAMPAIGNS", cardinality: "1:N", category: "BADGE ALLOCATION", foreign_key: "publication_id", description: "Campaign uses published active version" },
    { id: "rel_22", source: "BANDS", target: "BADGE_ALLOCATION_CAMPAIGNS", cardinality: "1:N", category: "BADGE ALLOCATION", foreign_key: "band_id", description: "Campaign targets specific candidate band" },
    { id: "rel_23", source: "EMPLOYEE_CATEGORIES", target: "BADGE_ALLOCATION_CAMPAIGNS", cardinality: "1:N", category: "BADGE ALLOCATION", foreign_key: "category_id", description: "Campaign targets specific candidate category" },
    { id: "rel_24", source: "BADGE_ALLOCATION_CAMPAIGNS", target: "CAMPAIGN_COSMONAUTS", cardinality: "1:N", category: "BADGE ALLOCATION", foreign_key: "campaign_id", description: "Campaign includes selected cohort cosmonauts" },

    // Reviewer Request & Python Mapping Relationships
    { id: "rel_25", source: "BADGE_ALLOCATION_CAMPAIGNS", target: "REVIEWER_REQUESTS", cardinality: "1:N", category: "REVIEWER REQUESTS & PYTHON MAPPING", foreign_key: "campaign_id", description: "Campaign issues reviewer invitations (24h acceptance deadline)" },
    { id: "rel_26", source: "BADGE_ALLOCATION_CAMPAIGNS", target: "MAPPING_RUNS", cardinality: "1:N", category: "REVIEWER REQUESTS & PYTHON MAPPING", foreign_key: "campaign_id", description: "Campaign triggers Python mapping batch runs" },
    { id: "rel_27", source: "BADGE_ALLOCATION_CAMPAIGNS", target: "REVIEWER_COSMONAUT_MAPPING", cardinality: "1:N", category: "REVIEWER REQUESTS & PYTHON MAPPING", foreign_key: "campaign_id", description: "Campaign retains final paired reviewer-cosmonaut allocations" },
    { id: "rel_28", source: "MAPPING_RUNS", target: "REVIEWER_COSMONAUT_MAPPING", cardinality: "1:N", category: "REVIEWER REQUESTS & PYTHON MAPPING", foreign_key: "mapping_batch_id", description: "Batch execution produces paired mappings" },

    // Project Management Relationships
    { id: "rel_29", source: "BADGE_ALLOCATION_CAMPAIGNS", target: "PROJECTS", cardinality: "1:N", category: "PROJECT MANAGEMENT", foreign_key: "campaign_id", description: "Reviewer crafts assessment project for campaign" },
    { id: "rel_30", source: "PROJECTS", target: "PROJECT_CRITERIA", cardinality: "1:N", category: "PROJECT MANAGEMENT", foreign_key: "project_id", description: "Project contains multiple assessment rubric criteria" },
    { id: "rel_31", source: "PROJECTS", target: "PROJECT_DELIVERABLES", cardinality: "1:N", category: "PROJECT MANAGEMENT", foreign_key: "project_id", description: "Project specifies mandatory deliverables and formats" },
    { id: "rel_32", source: "PROJECTS", target: "PROJECT_ASSIGNMENTS", cardinality: "1:N", category: "PROJECT MANAGEMENT", foreign_key: "project_id", description: "Project assigned to mapped cosmonauts" },
    { id: "rel_33", source: "REVIEWER_COSMONAUT_MAPPING", target: "PROJECT_ASSIGNMENTS", cardinality: "1:1", category: "PROJECT MANAGEMENT", foreign_key: "mapping_id", description: "Unique 1:1 mapping binding between paired allocation and project assignment" },

    // Assessment Management Relationships
    { id: "rel_34", source: "PROJECT_ASSIGNMENTS", target: "ASSESSMENT_ATTEMPTS", cardinality: "1:N", category: "ASSESSMENT MANAGEMENT", foreign_key: "project_assignment_id", description: "Assignment tracks initial attempt and historical reattempts" },
    { id: "rel_35", source: "ASSESSMENT_ATTEMPTS", target: "PROJECT_SUBMISSIONS", cardinality: "1:N", category: "ASSESSMENT MANAGEMENT", foreign_key: "attempt_id", description: "Attempt stores submitted artifacts and version snapshots" },
    { id: "rel_36", source: "ASSESSMENT_ATTEMPTS", target: "ASSESSMENT_SCORES", cardinality: "1:N", category: "ASSESSMENT MANAGEMENT", foreign_key: "attempt_id", description: "Attempt evaluated across criteria" },
    { id: "rel_37", source: "PROJECT_CRITERIA", target: "ASSESSMENT_SCORES", cardinality: "1:N", category: "ASSESSMENT MANAGEMENT", foreign_key: "criterion_id", description: "Criterion evaluated for marks obtained" },
    { id: "rel_38", source: "ASSESSMENT_ATTEMPTS", target: "REVIEW_REPORTS", cardinality: "1:0..1", category: "ASSESSMENT MANAGEMENT", foreign_key: "attempt_id", description: "Attempt produces single comprehensive review report with recommendations" },

    // Guardian Decision & Award Relationships
    { id: "rel_39", source: "ASSESSMENT_ATTEMPTS", target: "GUARDIAN_DECISIONS", cardinality: "1:N", category: "GUARDIAN DECISIONS & BADGE AWARDS", foreign_key: "attempt_id", description: "Guardian reviews report and issues final verdict (Award Badge / Reattempt)" },
    { id: "rel_40", source: "PROJECT_ASSIGNMENTS", target: "BADGE_AWARDS", cardinality: "1:0..1", category: "GUARDIAN DECISIONS & BADGE AWARDS", foreign_key: "project_assignment_id", description: "Successful project assignment results in awarded badge" },
    { id: "rel_41", source: "GUARDIAN_DECISIONS", target: "BADGE_AWARDS", cardinality: "1:0..1", category: "GUARDIAN DECISIONS & BADGE AWARDS", foreign_key: "decision_id", description: "Approved Guardian decision issues badge award" },
    { id: "rel_42", source: "BADGES", target: "BADGE_AWARDS", cardinality: "1:N", category: "GUARDIAN DECISIONS & BADGE AWARDS", foreign_key: "badge_id", description: "Badge awarded to cosmonaut" }
  ];

  // Build indexes for instant lookups
  const bySource = {};
  const byTarget = {};
  const byTable = {};

  relationships.forEach(rel => {
    if (!bySource[rel.source]) bySource[rel.source] = [];
    bySource[rel.source].push(rel);

    if (!byTarget[rel.target]) byTarget[rel.target] = [];
    byTarget[rel.target].push(rel);

    if (!byTable[rel.source]) byTable[rel.source] = [];
    byTable[rel.source].push(rel);

    if (!byTable[rel.target]) byTable[rel.target] = [];
    byTable[rel.target].push(rel);
  });

  window.STAR_APP_RELATIONSHIPS = relationships;
  window.STAR_APP_RELATIONSHIP_HELPERS = {
    getAll: () => relationships,
    getByTable: (tableName) => byTable[tableName] || [],
    getOutgoing: (tableName) => bySource[tableName] || [],
    getIncoming: (tableName) => byTarget[tableName] || [],
    getRelatedTableNames: (tableName) => {
      const rels = byTable[tableName] || [];
      const set = new Set();
      rels.forEach(r => {
        if (r.source === tableName) set.add(r.target);
        if (r.target === tableName) set.add(r.source);
      });
      return Array.from(set);
    },
    isRelated: (tableA, tableB) => {
      const rels = byTable[tableA] || [];
      return rels.some(r => (r.source === tableA && r.target === tableB) || (r.source === tableB && r.target === tableA));
    }
  };
})();
