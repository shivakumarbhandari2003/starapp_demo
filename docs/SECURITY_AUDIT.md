# SECURITY AUDIT AND VULNERABILITY REMEDIATION

> **Application:** StarApp  
> **Date:** 2026-11-20  
> **Status:** Phase 0 Baseline Security Findings

---

## 1. High-Severity Security Findings in Legacy Implementation

### Finding S1: Client-Side Gemini API Key Exposure (CRITICAL)
- **Location:** `index.html`, Line 189:
  ```javascript
  const GEMINI_API_KEY = "AIzaSy...";
  ```
- **Vulnerability:** An active Google Gemini API key was embedded in plaintext in client-side HTML, delivered directly to all browsers and stored in version control.
- **Impact:** Unauthorized usage, quota exhaustion, billing compromise, and API impersonation.
- **Remediation Plan:**
  1. Remove key from `index.html`.
  2. Implement backend endpoint `/api/v1/integrations/gemini/chat` and `/api/v1/integrations/gemini/generate-badge`.
  3. Load key securely via server-side `.env` (`GEMINI_API_KEY`).
  4. Flag that the previously exposed key must be revoked and rotated in Google Cloud Console.

### Finding S2: Client-Side Authorization & RBAC Bypass (HIGH)
- **Location:** `views_guardian.py`, `views_cosmonaut.py`, `app.py`.
- **Vulnerability:** Role checking was partially performed by toggling UI views in the browser DOM. A user could invoke `dispatchAction` directly from the browser console with arbitrary parameters.
- **Remediation Plan:**
  - Enforce server-side RBAC on all FastAPI endpoints using FastAPI dependency injection (`get_current_active_user`, `require_role`, `verify_reviewer_band_eligibility`).

### Finding S3: Plaintext Password Storage (HIGH)
- **Location:** `starapp/database.py` (Default password `"12345678"`).
- **Vulnerability:** User passwords were stored in plaintext without cryptographic hashing.
- **Remediation Plan:**
  - Implement `bcrypt` password hashing for all user accounts during database migration.
  - Transparently upgrade existing passwords to bcrypt hashes upon first backend initialization.

### Finding S4: Client-Side Database Tampering (MEDIUM)
- **Location:** IndexedDB / LocalStorage state serialization.
- **Vulnerability:** Because SQLite database state was serialized into the browser's IndexedDB, a user could inspect or modify badge status or evaluation marks using browser developer tools.
- **Remediation Plan:**
  - Retire browser-side database storage. The server-side disk SQLite database (`data/starapp.db`) becomes the single authoritative source of truth.
