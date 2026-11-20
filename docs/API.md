# STARAPP REST API SPECIFICATION (v1)

> **Base URL:** `http://127.0.0.1:8000/api/v1`  
> **Interactive Swagger UI:** `http://127.0.0.1:8000/docs`  
> **Format:** JSON (`application/json`)

---

## 1. Authentication Endpoints (`/auth`)

### `POST /auth/login`
- **Description:** Authenticates user credentials, generates high-entropy session token, and sets HttpOnly cookie `starapp_session`.
- **Request Body:**
  ```json
  {
    "username_or_email": "admin",
    "password": "12345678",
    "selected_role": "guardian"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "token": "d7a4f9...",
    "user": { "id": "admin", "name": "Guardian Admin", "active_role": "guardian" }
  }
  ```

### `POST /auth/logout`
- **Description:** Invalidates active session in database and clears session cookie.
- **Response (200 OK):** `{"success": true, "message": "Logged out successfully."}`

### `GET /auth/me`
- **Description:** Returns profile of the currently authenticated user.

---

## 2. Users & Corporate Hierarchy (`/users`)

### `GET /users/`
- **Query Params:** `band` (optional, e.g. `B1`), `track` (optional, e.g. `SD`)
- **Response (200 OK):** List of employees matching criteria.

### `GET /users/eligible-reviewers/{badge_band}`
- **Description:** Returns only reviewers whose band is strictly higher than `badge_band` ($\text{Reviewer\_Band} > \text{Badge\_Band}$).

### `GET /users/hierarchy/tree`
- **Description:** Returns the organization hierarchy from CEO Arjun Mehta down through Bands B6 to B1.

---

## 3. Bands & Taxonomy (`/bands`)

### `GET /bands/`
- **Description:** Lists all 6 bands (B1 to B6) with titles, experience requirements, and levels.

### `GET /bands/taxonomy`
- **Description:** Returns cascading dropdown taxonomy (Powers → Capabilities → Skills) including custom database additions.

### `POST /bands/capabilities`
- **Description:** Adds custom capability to taxonomy (Guardian only).

### `POST /bands/skills`
- **Description:** Adds custom skill to taxonomy (Guardian only).

---

## 4. Badges (`/badges`)

### `GET /badges/`
- **Query Params:** `band` (e.g. `B1`), `status` (e.g. `approved`, `pending_review`).

### `POST /badges/`
- **Description:** Authors a new badge. Enforces deduplication within target band.
- **Request Body:**
  ```json
  {
    "code": "B1-HAR-01",
    "title": "Hardware Foundations",
    "category": "Tech",
    "description": "Core hardware architecture",
    "target_band": "B1",
    "power": "Tech",
    "capability": "Data & Machine",
    "skill": "Hardware",
    "learning_outcomes": ["Outcome 1", "Outcome 2"]
  }
  ```

### `PUT /badges/{badge_id}`
- **Description:** Updates badge details or approval status.

---

## 5. Reviews & Approval (`/reviews`)

### `POST /reviews/request`
- **Description:** Guardian dispatches review request to a higher-band reviewer.
- **Server Rule:** Validates $\text{Reviewer\_Band} > \text{Badge\_Band}$. Returns 403 Forbidden if violated.

### `GET /reviews/inbox`
- **Description:** Returns list of badge review assignments assigned to the logged-in reviewer.

### `POST /reviews/{badge_id}/decision`
- **Description:** Records reviewer decision (`approved` or `returned`) and permanently persists any inline edits made to badge outcomes or description.

---

## 6. Allotments & Roadmaps (`/allotments`)

### `POST /allotments/`
- **Description:** Allots badge to specified cosmonaut IDs and sets timeline milestones.

### `GET /allotments/roadmap`
- **Description:** Returns Candy Crush roadmap badges and status for the current cosmonaut.

### `POST /allotments/extensions/request`
- **Description:** Cosmonaut submits deadline extension request with reason.

---

## 7. Project Submissions (`/submissions`)

### `POST /submissions/`
- **Description:** Submits project attempt (GitHub URL or code/pdf payload). Automatically increments `attempt_number`.

### `GET /submissions/history/{badge_id}`
- **Description:** Returns complete multi-attempt history for current cosmonaut and badge.

---

## 8. Evaluations & Marksheets (`/evaluations`)

### `POST /evaluations/`
- **Description:** Records 5-criterion 50-mark scorecard evaluation.
- **Request Body:**
  ```json
  {
    "submission_id": "sub-12345",
    "decision": "approved",
    "business_understanding": 9.0,
    "architecture_report": 9.5,
    "technical_knowledge": 8.5,
    "presentation": 9.0,
    "qa": 9.0,
    "overall_feedback": "Exemplary submission"
  }
  ```

### `GET /evaluations/leaderboard`
- **Description:** Returns batch ranking based on aggregate scores and badges earned.

---

## 9. Gemini AI Integrations (`/integrations/gemini`)

### `POST /integrations/gemini/generate-badge`
- **Description:** Server-side proxy calling Gemini API with server-side `.env` key, with deterministic fallback.
