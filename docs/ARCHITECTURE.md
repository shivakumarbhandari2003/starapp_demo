# STARAPP FULL-STACK ARCHITECTURE SPECIFICATION

> **Document Version:** 2.0.0-PROD  
> **Target Environment:** Local Full-Stack Application  
> **Backend:** Python 3.12 / 3.13 + FastAPI  
> **Database:** Authoritative Persistent SQLite3 (`data/starapp.db`)  
> **Frontend:** Native HTML5, Liquid-Glass CSS, Vanilla JS API Client (`js/api.js`)

---

## 1. System Topology

```mermaid
graph TD
    Client[Web Browser Client] --> Static_Assets[Static Assets: CSS / JS / HTML]
    Client --> API_Client[js/api.js - Typed REST Client]
    
    subgraph FastAPI_Backend ["FastAPI Modular Backend (Port 8000)"]
        API_Client <==>|HTTP JSON REST| APIRouter["/api/v1 Routers"]
        
        APIRouter --> Auth_Middleware[Session Cookie & RBAC Dependencies]
        Auth_Middleware --> Services[Feature Service Layer]
        
        Services --> Gemini_Proxy[Integrations: Gemini AI Proxy]
        Services --> Repositories[Repository Layer: Param SQL]
    end
    
    subgraph Storage ["Local Persistent Storage"]
        Repositories <==>|PRAGMA WAL + foreign_keys=ON| SQLite_DB[("data/starapp.db (33 Tables)")]
    end
```

---

## 2. Layered Responsibilities

### 2.1 Frontend Presentation Layer
- **No Heavy Frameworks:** Preserves original responsive HTML/CSS/JS design tokens without React, Angular, or Vue overhead.
- **Client Communication:** Driven by `js/api.js`, providing unified fetch wrappers with session credentials (`credentials: "same-origin"`).
- **Security:** Zero plaintext API keys or credentials shipped to the browser.

### 2.2 API Layer (`backend/app/api/v1/` or `backend/app/features/*/router.py`)
- Thin controllers handling request validation via Pydantic models.
- Standardized HTTP status codes (200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict).
- Centralized exception mapping via `StarAppException`.

### 2.3 Feature Service Layer (`backend/app/features/*/service.py`)
- Encapsulates all business rules, eligibility algorithms, and state machines.
- Coordinates database queries across multiple repositories within safe transaction boundaries.

### 2.4 Repository Layer (`backend/app/features/*/repository.py`)
- Pure parameterized SQL queries (`sqlite3.Cursor.execute(query, params)`).
- SQL injection immunity through explicit parameter binding (`?`).
- Object-to-dictionary mapping via `sqlite3.Row`.

### 2.5 Database Layer (`backend/app/database/`)
- Single authoritative persistent SQLite3 database on disk (`data/starapp.db`).
- Configured with `PRAGMA foreign_keys = ON;`, `PRAGMA journal_mode = WAL;`, and `PRAGMA busy_timeout = 5000;`.
