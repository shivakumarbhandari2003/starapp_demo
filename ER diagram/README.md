# STAR App — Interactive ER Mind Map (NotebookLM Inspired)

A high-performance, fully interactive, data-driven Entity Relationship Mind Map for the STAR App PostgreSQL database schema, inspired by the NotebookLM Mind Map user experience.

---

## 1. How to Open the Application

1. **Direct Browser Launch (Zero Installation / Offline / File Protocol)**:
   - Double-click `index.html` or open `file:///c:/Users/USER/Desktop/starapp_demo/ER%20diagram/index.html` in Google Chrome, Microsoft Edge, Mozilla Firefox, or Safari.
   - Built with vanilla JavaScript (no bundlers or node_modules required). Does not suffer from CORS errors on `file://`.

2. **Local HTTP Server (Optional)**:
   - From this directory, run:
     ```bash
     python -m http.server 8080
     ```
   - Navigate to `http://localhost:8080` in your web browser.

---

## 2. How the Hierarchy is Organized

The mind map visualizes the STAR App database across four distinct hierarchical tiers rooted at **STAR APP DATABASE**:

```text
STAR APP DATABASE (Root)
│
├── 01. ORGANIZATION & EMPLOYEE MANAGEMENT (Module)
│   ├── Company Management (Submodule)
│   │   ├── COMPANY (Table)
│   │   │   ├── company_id (PK)
│   │   │   ├── company_name
│   │   │   ├── description
│   │   │   └── created_at
│   │   └── BANDS (Table)
│   │
│   ├── Employee Management (Submodule)
│   │   ├── EMPLOYEE_CATEGORIES (Table)
│   │   └── EMPLOYEES (Table)
│   │
│   └── Application Role Management (Submodule)
│       ├── SYSTEM_ROLES (Table)
│       └── EMPLOYEE_ROLES (Table)
│
├── 02. POWERS, CAPABILITIES & SKILLS
│   ├── Power Management ➔ POWERS
│   ├── Capability Management ➔ CAPABILITIES
│   └── Skill Management ➔ SKILLS
│
├── 03. BADGE MANAGEMENT
│   ├── Badge Master ➔ BADGES
│   ├── Badge Version Management ➔ BADGE_VERSIONS
│   ├── Initial Badge Review ➔ BADGE_REVIEWS
│   ├── Badge Publication ➔ BADGE_PUBLICATIONS
│   └── Badge Eligibility ➔ BADGE_ELIGIBILITY
│
├── 04. BADGE ALLOCATION
│   ├── Allocation Campaign Management ➔ BADGE_ALLOCATION_CAMPAIGNS
│   └── Cosmonaut Selection ➔ CAMPAIGN_COSMONAUTS
│
├── 05. REVIEWER REQUESTS & PYTHON MAPPING
│   ├── Reviewer Request Management ➔ REVIEWER_REQUESTS
│   ├── Python Mapping Execution ➔ MAPPING_RUNS
│   └── Reviewer-Cosmonaut Mapping ➔ REVIEWER_COSMONAUT_MAPPING
│
├── 06. PROJECT MANAGEMENT
│   ├── Project Creation ➔ PROJECTS
│   ├── Project Assessment Criteria ➔ PROJECT_CRITERIA
│   ├── Project Deliverables ➔ PROJECT_DELIVERABLES
│   └── Project Assignment ➔ PROJECT_ASSIGNMENTS
│
├── 07. ASSESSMENT MANAGEMENT
│   ├── Assessment Attempts ➔ ASSESSMENT_ATTEMPTS
│   ├── Submission Management ➔ PROJECT_SUBMISSIONS
│   ├── Assessment Scoring ➔ ASSESSMENT_SCORES
│   └── Review Reports ➔ REVIEW_REPORTS
│
└── 08. GUARDIAN DECISIONS & BADGE AWARDS
    ├── Guardian Decisions ➔ GUARDIAN_DECISIONS
    └── Badge Award Management ➔ BADGE_AWARDS
```

- **Total Modules**: 8
- **Total Submodules**: 25
- **Total Database Tables**: 29
- **Total Columns & Attributes**: 195

---

## 3. How Expansion and Collapse Work

1. **Progressive Disclosure**:
   - The initial view starts cleanly with the **STAR APP DATABASE** root and the 8 main module overview cards.
2. **Independent Branch Expansion**:
   - Every expandable node features an interactive circular button `(+)` / `(−)`.
   - Expanding one branch (e.g., `03. BADGE MANAGEMENT`) does **not** collapse any other branch. Multiple modules and submodules can remain open simultaneously.
   - Collapsing a node only hides its descendants, immediately reclaiming canvas real estate without disturbing adjacent branches.
3. **Table & Column Level Expansion**:
   - Expanding a Table reveals all of its individual columns, displaying PK, FK, DERIVED badges and clickable target jump links (`➔ TARGET_TABLE.col`).
4. **Global Controls**:
   - **Expand All**: Expands all 8 modules, 25 submodules, and 29 tables at once.
   - **Collapse All**: Smoothly returns to the high-level root overview.

---

## 4. How Database Relationships Are Represented

1. **Hierarchical Connectors**:
   - Solid cubic bezier spline curves matching the module's accent color (Blue, Purple, Pink, Amber, Emerald, Cyan, Indigo, Rose).
2. **Relational Connectors (Foreign Keys)**:
   - Separate, dashed glowing curves linking tables across modules with cardinality badges (`1:N`, `1:1`, `1:0..1`) and arrowheads.
   - All 42 database relationships from Section 5 are supported.
   - **Toggle Visibility**: The `Hide Relationships` / `Show Relationships` button in the header toolbar lets users declutter the canvas at will.
   - **Hover & Select Highlighting**: Hovering over or clicking any table illuminates its relational lines and dim-filters unrelated connections.
3. **Table Detail Drawer**:
   - Clicking any table opens a side panel detailing:
     - Table Number & Module Path
     - Business Rules & Seniority Matrix (from Section 4)
     - Complete Columns Schema (PK / FK / DERIVED / UNIQUE)
     - Incoming and Outgoing Foreign Key Relationships with clickable jump links.

---

## 5. How the Dynamic Layout Engine Works

Located in `js/layout-engine.js`:
- Uses a recursive, bounding-box calculation that computes visible subtree extents dynamically.
- Automatically adjusts sibling spacing, submodule gap, and module separation so **no two nodes or branches ever overlap**.
- Supports both **Horizontal (L➔R)** and **Vertical (T➔B)** orientations via the header toolbar toggle.
- When nodes are expanded or collapsed, layout recalculates instantly and SVG connector paths are smoothly updated.

---

## 6. How to Add a New Database Table

1. Open `js/schema-data.js`.
2. Locate the appropriate module and submodule under `window.STAR_APP_SCHEMA.modules`. Add the table name to the `tables` array:
   ```javascript
   {
     "id": "submod_01_1",
     "name": "Company Management",
     "tables": ["COMPANY", "BANDS", "NEW_TABLE"]
   }
   ```
3. Add the table definition to `window.STAR_APP_SCHEMA.tables`:
   ```javascript
   "NEW_TABLE": {
     "table_number": 30,
     "name": "NEW_TABLE",
     "module_info": {
       "module_id": "mod_01",
       "module_name": "ORGANIZATION & EMPLOYEE MANAGEMENT",
       "module_color": "#3B82F6",
       "submodule_id": "submod_01_1",
       "submodule_name": "Company Management"
     },
     "columns": [
       { "name": "id", "key": "PK", "is_pk": true, "is_fk": false, "is_derived": false, "references": null },
       { "name": "company_id", "key": "FK", "is_pk": false, "is_fk": true, "is_derived": false, "references": "COMPANY.company_id" }
     ],
     "notes": ["Notes or business rules for NEW_TABLE"]
   }
   ```
4. Save the file. The mind map, search index, and layout engine automatically pick up the new table.

---

## 7. How to Add a New Relationship

1. Open `js/relationships.js`.
2. Add a new entry to the `relationships` array:
   ```javascript
   {
     id: "rel_43",
     source: "COMPANY",
     target: "NEW_TABLE",
     cardinality: "1:N",
     category: "ORGANIZATION",
     foreign_key: "company_id",
     description: "Company has many records in NEW_TABLE"
   }
   ```
3. Save the file. The relational spline renderer and table details drawer automatically index the connection.

---

## 8. Dependencies Introduced

- **Zero External Dependencies**: Pure vanilla JavaScript (ES6+), standard CSS3, and HTML5 SVG/Canvas.
- No React, no Vue, no D3, no npm packages, and no network dependencies. Runs 100% offline.
