# STARAPP ROLE-BASED ACCESS CONTROL (RBAC) & PERMISSION SPECIFICATION

> **Security Model:** Server-Enforced RBAC  
> **Session Transport:** HttpOnly, SameSite Session Cookies + Bearer Header Fallback

---

## 1. System Roles

| Role | Description | Default Personas | Permissions |
|:---|:---|:---|:---|
| **Guardian** | Platform Administrator & Lead Mentor | `admin` | Full authoring, publishing, allotment, extension approvals, reviewer dispatch |
| **Reviewer** | Higher-Band Evaluator | Employees in B2–B6 | Peer review lower band badges, evaluate project submissions, grade 50-mark rubrics |
| **Cosmonaut** | Candidate / Cadet Engineer | Employees in B1–B6 | View roadmap, access allotted badges, submit projects, request extensions, view marksheets |

---

## 2. Band Restrictions & Reviewer Eligibility Matrix

Reviewer assignment is strictly governed by the rule:

$$\text{Reviewer\_Band} > \text{Badge\_Band}$$

| Badge Band | B1 Reviewer | B2 Reviewer | B3 Reviewer | B4 Reviewer | B5 Reviewer | B6 Reviewer |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **B1** | ❌ (Peer) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **B2** | ❌ | ❌ (Peer) | ✅ | ✅ | ✅ | ✅ |
| **B3** | ❌ | ❌ | ❌ (Peer) | ✅ | ✅ | ✅ |
| **B4** | ❌ | ❌ | ❌ | ❌ (Peer) | ✅ | ✅ |
| **B5** | ❌ | ❌ | ❌ | ❌ | ❌ (Peer) | ✅ |
| **B6** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ (Executive) |

*Note: Band 6 badges can only be reviewed by the CEO or Academic Executive Committee.*

---

## 3. Server-Side Enforcement Mechanics

In `backend/app/core/dependencies.py`:
- `require_guardian`: Verifies `user.active_role in ["guardian", "admin"]`.
- `require_reviewer`: Verifies `user.active_role in ["reviewer", "guardian", "admin"]`.
- `require_cosmonaut`: Verifies valid user session.
- `verify_reviewer_eligibility`: Invoked on `/api/v1/reviews/request`. Direct API calls bypassing frontend validation are rejected with HTTP 403 Forbidden.
