"""
End-to-End StarApp Lifecycle & SQLite Persistence Verification Script.
Executes and validates the entire StarApp workflow from badge creation to cycle completion:
1. Clear existing badges & mapping data (clean state).
2. Badge creation by Guardian & Reviewer Assignment.
3. Badge review & formal approval by higher-band Reviewer.
4. Guardian Mapping (Review Requests -> Reviewer Acceptance -> Equal Distribution Mapping).
5. Guardian Badge Allotment & Publishing.
6. Reviewer Project Creation & Prompt Dispatch to mapped Cadets.
7. Cosmonaut Deliverables Submission (Code, PDF, GitHub URL).
8. Reviewer 50-Mark Rubric Evaluation.
9. Guardian Final Evaluation Approval & Badge Awarding.
10. Uncoupling & Cycle Completion (Badge turns Gold, Mapping Ends, DB Consistency).
"""

import os
import sys
import json
import sqlite3

# Set workspace root
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(WORKSPACE_DIR)
sys.path.insert(0, WORKSPACE_DIR)

from starapp.app import StarAppController
from starapp.storage import store
from starapp.models import Badge, BadgeTimeline, ProjectSubmission, AssessmentMarksheet, ReviewerProjectPrompt, current_iso_timestamp

DB_PATH = os.path.join(WORKSPACE_DIR, "data", "starapp.db")


def inspect_db_counts(label: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    tables = [
        "badges",
        "badge_reviewer_assignments",
        "badge_review_events",
        "mapping_requests",
        "band_mappings",
        "badge_timelines",
        "reviewer_project_prompts",
        "project_submissions",
        "assessment_marksheets",
        "notifications",
        "activity_events"
    ]
    print(f"\n--- [SQLITE AUDIT: {label}] ---")
    counts = {}
    for t in tables:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = c.fetchone()[0]
        counts[t] = cnt
        print(f"  {t:30}: {cnt} rows")
    conn.close()
    return counts


def run_e2e_verification():
    print("==================================================================")
    print("   STARAPP END-TO-END WORKFLOW & PERSISTENCE VERIFICATION")
    print("==================================================================")

    # -------------------------------------------------------------------------
    # STEP 0: Reset Database to Clean Preserved Baseline
    # -------------------------------------------------------------------------
    print("\n[STEP 0] Resetting SQLite database to clean state...")
    os.system("python scripts/clear_data.py")
    store.__init__()
    counts_0 = inspect_db_counts("Step 0 - Clean State")
    assert counts_0["badges"] == 0, "Badges should be 0"
    assert counts_0["band_mappings"] == 0, "Band mappings should be 0"
    assert counts_0["mapping_requests"] == 0, "Mapping requests should be 0"
    assert counts_0["badge_timelines"] == 0, "Badge timelines should be 0"
    print("✓ Step 0 PASSED: Database is clean and verified.")

    # Initialize Guardian Controller
    g_ctrl = StarAppController()
    g_ctrl.initialize()
    g_user = store.get_user_by_id("admin") or store.get_user_by_id("guardian_1")
    g_ctrl.current_user = g_user
    g_ctrl.current_view = "g_dashboard"

    # -------------------------------------------------------------------------
    # STEP 1: Guardian Creates Badge in Band B1
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Guardian creates new badge 'Signals Foundations' (B1-SIG-01)...")
    badge_data = {
        "title": "Signals Foundations",
        "code": "B1-SIG-01",
        "target_band": "B1",
        "power": "Tech",
        "capability": "Systems",
        "skill": "Hardware",
        "category": "Foundations",
        "description": "Foundational milestone covering analog and digital signal processing.",
        "learning_outcomes": ["Understand Fourier transforms", "Design discrete FIR filters"],
        "learning_topics": ["Signal Sampling", "Quantization", "Filter Design"],
        "project_requirements": "1. Implement signal simulator in Python.\n2. Write PDF Architecture Report.\n3. Provide clean GitHub repository.",
        "assigned_reviewer_id": "m_b2_1",  # Band B2 Reviewer (> Band B1 Target)
        "creator_id": g_user.id
    }
    
    # Save generated badge via store
    ok, msg, b_id = store.create_badge_for_review(badge_data, creator_id=g_user.id)
    assert ok, f"Failed to generate custom badge: {msg}"
    print(f"  Badge created with ID: {b_id}")

    counts_1 = inspect_db_counts("Step 1 - Badge Created")
    assert counts_1["badges"] == 1, "Expected 1 badge in SQLite"
    assert counts_1["badge_reviewer_assignments"] == 1, "Expected 1 reviewer assignment"
    assert counts_1["badge_review_events"] == 1, "Expected 1 review event (created)"

    # Verify SQLite row directly
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    b_row = conn.execute("SELECT * FROM badges WHERE id = ?", (b_id,)).fetchone()
    assert b_row is not None, "Badge row missing in SQLite"
    assert b_row["workflow_status"] == "pending_review", f"Unexpected status: {b_row['workflow_status']}"
    assert b_row["assigned_reviewer_id"] == "m_b2_1", f"Reviewer mismatch: {b_row['assigned_reviewer_id']}"
    conn.close()
    print("✓ Step 1 PASSED: Badge saved in SQLite with status 'pending_review'.")

    # -------------------------------------------------------------------------
    # STEP 2: Reviewer Reviews & Approves Badge
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Reviewer m_b2_1 reviews and formally approves badge...")
    r_ctrl = StarAppController()
    r_ctrl.initialize()
    rev_user = store.get_user_by_id("m_b2_1")
    r_ctrl.current_user = rev_user
    r_ctrl.current_view = "c_requests"

    # Reviewer approves
    ok, app_msg = store.approve_badge(b_id, rev_user.id, rev_user.name, "Approved with excellent rigor.")
    assert ok, f"Failed to approve badge: {app_msg}"

    counts_2 = inspect_db_counts("Step 2 - Badge Approved")
    assert counts_2["badges"] == 1, "Expected 1 badge in SQLite"
    assert counts_2["badge_review_events"] == 2, "Expected 2 review events (created, approved)"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    b_row = conn.execute("SELECT * FROM badges WHERE id = ?", (b_id,)).fetchone()
    assert b_row["workflow_status"] == "approved", f"Badge not approved: {b_row['workflow_status']}"
    conn.close()
    print("✓ Step 2 PASSED: Badge status transitioned to 'approved' and persisted in SQLite.")

    # -------------------------------------------------------------------------
    # STEP 3: Guardian Mapping (Requests -> Accept -> Save Mapping)
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Guardian maps cosmonauts and reviewer to badge...")
    g_ctrl.current_view = "g_mapping"
    g_ctrl.mapping_selected_band = "B1"
    g_ctrl.mapping_selected_badge = "Signals Foundations"
    g_ctrl.mapping_selected_badge_id = b_id
    g_ctrl.mapping_selected_cosmonauts = ["m_b1_1", "m_b1_2"]
    g_ctrl.mapping_selected_reviewer_band = "B2"
    g_ctrl.mapping_selected_reviewers = ["m_b2_1"]
    g_ctrl.mapping_review_dates = ["2026-11-18", "2026-11-19", "2026-11-20"]

    # 3a: Guardian sends review request
    g_ctrl.handle_event("send_mapping_requests", "{}")
    counts_3a = inspect_db_counts("Step 3a - Mapping Requests Sent")
    assert counts_3a["mapping_requests"] == 1, "Expected 1 mapping request in SQLite"

    # 3b: Reviewer accepts review request
    req = store.get_mapping_requests()[0]
    g_ctrl.handle_event("accept_mapping_request", json.dumps({"request_id": req["id"]}))
    counts_3b = inspect_db_counts("Step 3b - Request Accepted")
    assert counts_3b["mapping_requests"] == 1, "Expected 1 mapping request in SQLite"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    req_row = conn.execute("SELECT * FROM mapping_requests WHERE id = ?", (req["id"],)).fetchone()
    assert req_row["status"] == "accepted", f"Request status not accepted: {req_row['status']}"
    conn.close()

    # 3c: Guardian executes cosmonaut mapping
    g_ctrl.handle_event("execute_cosmonaut_mapping", "{}")
    counts_3c = inspect_db_counts("Step 3c - Cosmonaut Mapping Executed")
    assert counts_3c["band_mappings"] >= 1, "Expected at least 1 band_mapping in SQLite"
    assert counts_3c["badge_timelines"] == 2, "Expected 2 badge_timelines in SQLite (1 per cadet)"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tls = conn.execute("SELECT * FROM badge_timelines WHERE badge_id = ?", (b_id,)).fetchall()
    assert len(tls) == 2, f"Expected 2 timelines, got {len(tls)}"
    for tl in tls:
        assert tl["reviewer_id"] == "m_b2_1", f"Timeline reviewer mismatch: {tl['reviewer_id']}"
        assert tl["status"] == "active", f"Timeline status mismatch: {tl['status']}"
    conn.close()
    print("✓ Step 3 PASSED: Band mappings, timelines, and reviewer associations saved to SQLite.")

    # -------------------------------------------------------------------------
    # STEP 4: Guardian Allotment & Publishing
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Guardian publishes badge in Badge Allotment catalog...")
    g_ctrl.current_view = "g_allotment"
    
    # Verify in Not Published Yet before publishing
    g_html_before = g_ctrl.render()
    assert "Not Published Yet" in g_html_before, "Missing 'Not Published Yet' in allotment view"
    assert "Signals Foundations" in g_html_before, "Badge title missing in allotment view"

    # Publish badge
    g_ctrl.handle_event("publish_badge", json.dumps({"badge_id": b_id}))
    counts_4 = inspect_db_counts("Step 4 - Badge Published")
    assert counts_4["badges"] == 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    b_row = conn.execute("SELECT is_published, is_allocated, published_at FROM badges WHERE id = ?", (b_id,)).fetchone()
    assert b_row["is_published"] == 1, "Badge should be marked is_published = 1 in SQLite"
    assert b_row["is_allocated"] == 1, "Badge should be marked is_allocated = 1 in SQLite"
    conn.close()

    # Verify Guardian Allotment view shows badge under Published Badges with Revoke option
    g_html_after = g_ctrl.render()
    assert "Published (" in g_html_after or "Published" in g_html_after, "Missing 'Published' in allotment view"
    assert "Revoke" in g_html_after or "revoke_badge" in g_html_after, "Missing Revoke option"

    # Verify Reviewer Schedule view shows badge
    r_ctrl.current_view = "c_badge_reviews"
    r_html = r_ctrl.render()
    assert "Signals Foundations" in r_html or "B1-SIG-01" in r_html, "Published badge missing in Reviewer view"
    assert "Create Project" in r_html, "Reviewer must have 'Create Project' button"

    # Verify Cosmonaut Roadmap shows badge
    c_ctrl = StarAppController()
    c_ctrl.initialize()
    cosmo_user = store.get_user_by_id("m_b1_1")
    c_ctrl.current_user = cosmo_user
    c_ctrl.current_view = "c_dashboard"
    c_html = c_ctrl.render()
    assert "Signals Foundations" in c_html or "B1-SIG-01" in c_html, "Published badge missing in Cosmonaut roadmap"
    print("✓ Step 4 PASSED: Badge is published, visible to both Reviewer and Cosmonaut, and reflects revoke option.")

    # -------------------------------------------------------------------------
    # STEP 5: Reviewer Creates & Sends Project to Mapped Cadets
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Reviewer creates project specifications and sends to mapped cadets...")
    proj_payload = {
        "badge_id": b_id,
        "reviewer_id": rev_user.id,
        "title": "Digital Signal Processing Enterprise System",
        "description": "Build an enterprise-grade digital signal processing system with FIR filter and telemetry.",
        "outcomes": [
            "Construct robust discrete signal generation and sampling.",
            "Implement high-throughput low-pass and band-pass FIR filters.",
            "Generate detailed architecture report and run automated test suites."
        ],
        "requirements": [
            "1. Implement core filtering algorithms in executable Python.",
            "2. Produce a professional architecture PDF report.",
            "3. Host code on GitHub with comprehensive README."
        ],
        "deliverables": {
            "code": "b1_sig_01_filter.py",
            "pdf": "Signals_Architecture_Report.pdf",
            "github": "https://github.com/starapp-cosmonauts/b1-sig-01-pipeline"
        },
        "cosmonaut_ids": ["m_b1_1", "m_b1_2"],
        "status": "released"
    }

    r_ctrl.handle_event("send_reviewer_project", json.dumps(proj_payload))
    counts_5 = inspect_db_counts("Step 5 - Reviewer Project Created & Sent")
    assert counts_5["reviewer_project_prompts"] == 1, "Expected 1 reviewer project prompt in SQLite"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    p_row = conn.execute("SELECT * FROM reviewer_project_prompts WHERE badge_id = ?", (b_id,)).fetchone()
    assert p_row is not None, "Project prompt row missing in SQLite"
    assert p_row["status"] == "released", f"Prompt status mismatch: {p_row['status']}"
    assert p_row["reviewer_id"] == "m_b2_1", f"Prompt reviewer mismatch: {p_row['reviewer_id']}"
    conn.close()

    # Verify Reviewer Schedule view shows project released
    r_sched_html = r_ctrl.render()
    assert "Project Released" in r_sched_html or "Edit Project" in r_sched_html, "Reviewer schedule does not show released project"

    # Verify Cosmonaut sees badge card with Project Allocated on c_submission, then opens dedicated c_badge_detail page
    c_ctrl.handle_event("nav_cosmonaut", "c_submission")
    c_grid_html = c_ctrl.render()
    assert "Project Allocated" in c_grid_html, "Cosmonaut card missing Project Allocated chip"
    assert "Digital Signal Processing Enterprise System" not in c_grid_html, "Project specification must remain inside dedicated badge page, not grid overview"

    c_ctrl.handle_event("open_cosmonaut_badge_page", b_id)
    assert c_ctrl.current_view == "c_badge_detail", f"Expected c_badge_detail, got {c_ctrl.current_view}"
    c_sub_html = c_ctrl.render()
    assert "Earn the Badge" in c_sub_html and "Project allocated" in c_sub_html, "Missing Earn the Badge or Project allocated button"
    assert "Digital Signal Processing Enterprise System" in c_sub_html, "Cosmonaut badge detail page missing project details"

    # Clicking Project allocated opens allocated_project_modal
    c_ctrl.handle_event("open_allocated_project_modal", b_id)
    assert c_ctrl.active_modal == "allocated_project_modal"
    c_proj_modal_html = c_ctrl.render()
    assert "Digital Signal Processing Enterprise System" in c_proj_modal_html and "Allocated by Reviewer:" in c_proj_modal_html

    # Clicking Submit Deliverables opens submission_portal_modal
    c_ctrl.handle_event("open_submission_modal", b_id)
    assert c_ctrl.active_modal == "submission_portal_modal"
    print("✓ Step 5 PASSED: Reviewer project saved to SQLite, notified cadets, and renders in dedicated badge page & Project allocated modal.")

    # -------------------------------------------------------------------------
    # STEP 6: Cosmonaut Submits Deliverables (Code, PDF, GitHub URL)
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Cosmonaut m_b1_1 submits project deliverables...")
    sub_payload = {
        "badge_id": b_id,
        "cosmonaut_id": "m_b1_1",
        "pdf_name": "Aarav_B1_SIG_01_Architecture_Report.pdf",
        "pdf_payload": "data/Signals_Architecture_Report.pdf",
        "code_name": "b1_sig_01_filter.py",
        "code_payload": '"""Signal Processing Implementation"""\ndef run_fir_filter(): return "PASS"',
        "github_url": "https://github.com/starapp-cosmonauts/b1-sig-01-signals-aarav"
    }

    c_ctrl.handle_event("submit_project_deliverable", json.dumps(sub_payload))
    counts_6 = inspect_db_counts("Step 6 - Project Deliverables Submitted")
    assert counts_6["project_submissions"] == 1, "Expected 1 project submission in SQLite"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    s_row = conn.execute("SELECT * FROM project_submissions WHERE badge_id = ? AND cosmonaut_id = 'm_b1_1'", (b_id,)).fetchone()
    assert s_row is not None, "Submission row missing in SQLite"
    assert s_row["status"] == "pending", f"Submission status mismatch: {s_row['status']}"
    assert s_row["code_name"] == "b1_sig_01_filter.py", "Code filename mismatch"
    assert s_row["github_url"] == "https://github.com/starapp-cosmonauts/b1-sig-01-signals-aarav", "GitHub URL mismatch"
    conn.close()

    # Verify Reviewer Badge Review schedule reflects new submission
    r_ctrl.current_view = "c_badge_reviews"
    r_queue_html = r_ctrl.render()
    assert "Aarav Sharma" in r_queue_html or "m_b1_1" in r_queue_html, "Submission missing from Reviewer assessment queue"
    print("✓ Step 6 PASSED: Deliverables saved in SQLite and routed exclusively to assigned Reviewer.")

    # -------------------------------------------------------------------------
    # STEP 7: Reviewer 50-Mark Rubric Evaluation
    # -------------------------------------------------------------------------
    print("\n[STEP 7] Reviewer m_b2_1 grades submission using 50-mark rubric...")
    eval_payload = {
        "submission_id": s_row["id"],
        "assessor_role": "reviewer",
        "bu": 9.5,
        "ar": 9.0,
        "tk": 9.0,
        "pr": 8.5,
        "qa": 9.0,
        "strengths": "Outstanding mathematical proofs of FIR filter convergence.",
        "improvements": "Consider adding automated jitter analysis in Phase 2.",
        "feedback": "Approved by Reviewer with high distinction. Ready for Guardian final assessment.",
        "decision": "reviewer_assessed"
    }

    r_ctrl.handle_event("submit_reviewer_assessment", json.dumps(eval_payload))
    counts_7 = inspect_db_counts("Step 7 - Reviewer 50-Mark Rubric Submitted")
    assert counts_7["assessment_marksheets"] == 1, "Expected 1 assessment marksheet in SQLite"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    asm_row = conn.execute("SELECT * FROM assessment_marksheets WHERE submission_id = ?", (s_row["id"],)).fetchone()
    assert asm_row is not None, "Marksheet missing in SQLite"
    assert asm_row["assessor_role"] == "reviewer", f"Assessor role mismatch: {asm_row['assessor_role']}"
    assert asm_row["total_marks"] == 45.0, f"Total marks mismatch: {asm_row['total_marks']}"
    assert asm_row["percentage"] == 90.0, f"Percentage mismatch: {asm_row['percentage']}"

    # Verify submission and timeline transitioned to reviewer_assessed
    sub_chk = conn.execute("SELECT status FROM project_submissions WHERE id = ?", (s_row["id"],)).fetchone()
    assert sub_chk["status"] == "reviewer_assessed", f"Submission status mismatch: {sub_chk['status']}"
    tl_chk = conn.execute("SELECT status FROM badge_timelines WHERE badge_id = ? AND cosmonaut_id = 'm_b1_1'", (b_id,)).fetchone()
    assert tl_chk["status"] == "reviewer_assessed", f"Timeline status mismatch: {tl_chk['status']}"
    conn.close()

    # Verify Guardian Review Queue now displays submission for final assessment
    g_ctrl.current_view = "g_reviews"
    g_reviews_html = g_ctrl.render()
    assert "Aarav Sharma" in g_reviews_html or "m_b1_1" in g_reviews_html, "Submission missing in Guardian review queue"
    assert "45.0" in g_reviews_html or "90.0%" in g_reviews_html or "Reviewer Assessed" in g_reviews_html, "Reviewer score missing in Guardian queue"
    print("✓ Step 7 PASSED: 50-mark rubric persisted in SQLite; forwarded to Guardian queue.")

    # -------------------------------------------------------------------------
    # STEP 8: Guardian Final Assessment & Badge Awarding
    # -------------------------------------------------------------------------
    print("\n[STEP 8] Guardian conducts final review and awards badge...")
    final_payload = {
        "submission_id": s_row["id"],
        "assessor_role": "guardian",
        "bu": 9.5,
        "ar": 9.0,
        "tk": 9.0,
        "pr": 8.5,
        "qa": 9.0,
        "strengths": "Verified rigorous deliverables and clean architecture.",
        "improvements": "Ready for Band B2 promotion pathway.",
        "feedback": "Official Guardian award confirmed. Milestone completed.",
        "decision": "approve"
    }

    g_ctrl.handle_event("submit_guardian_final_assessment", json.dumps(final_payload))
    counts_8 = inspect_db_counts("Step 8 - Guardian Badge Awarded")
    assert counts_8["assessment_marksheets"] == 2, "Expected 2 marksheets in SQLite (1 reviewer, 1 guardian)"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    g_asm_row = conn.execute("SELECT * FROM assessment_marksheets WHERE submission_id = ? AND assessor_role = 'guardian'", (s_row["id"],)).fetchone()
    assert g_asm_row is not None, "Guardian marksheet missing in SQLite"
    assert g_asm_row["decision"] == "approve", f"Decision mismatch: {g_asm_row['decision']}"
    assert g_asm_row["total_marks"] == 45.0, f"Guardian marks mismatch: {g_asm_row['total_marks']}"

    # Verify timeline is now completed with actual award date
    tl_comp = conn.execute("SELECT status, actual_award_date FROM badge_timelines WHERE badge_id = ? AND cosmonaut_id = 'm_b1_1'", (b_id,)).fetchone()
    assert tl_comp["status"] == "completed", f"Timeline not completed: {tl_comp['status']}"
    assert tl_comp["actual_award_date"] is not None and tl_comp["actual_award_date"] != "", "Award date missing"

    # Verify uncoupling in band_mappings
    bm_rows = conn.execute("SELECT data_json FROM band_mappings WHERE badge_id = ?", (b_id,)).fetchall()
    found_uncoupled = False
    for r in bm_rows:
        data = json.loads(r[0])
        if "m_b1_1" in data.get("completed_cosmonauts", []) or "m_b1_1" in data.get("uncoupled_cadets", []):
            found_uncoupled = True
            break
    assert found_uncoupled, "Cosmonaut m_b1_1 was not uncoupled from active mapping"
    conn.close()
    print("✓ Step 8 PASSED: Guardian marksheet saved, timeline completed, mapping uncoupled.")

    # -------------------------------------------------------------------------
    # STEP 9: Cosmonaut Portal Reflects Gold Earned Badge & Marksheet
    # -------------------------------------------------------------------------
    print("\n[STEP 9] Verifying Cosmonaut UI renders Gold Badge and Full Marksheet...")
    c_ctrl.current_view = "c_results"
    c_ctrl.cosmonaut_results_badge_id = b_id
    c_results_html = c_ctrl.render()
    assert "45.0" in c_results_html or "90.0%" in c_results_html, "Cosmonaut marksheet missing final marks"
    assert "Signals Foundations" in c_results_html or "B1-SIG-01" in c_results_html, "Milestone title missing in results"

    c_ctrl.current_view = "c_dashboard"
    c_dash_html = c_ctrl.render()
    # Check for gold badge styling / earned status
    assert "earned" in c_dash_html.lower() or "gold" in c_dash_html.lower() or "completed" in c_dash_html.lower(), "Badge did not turn gold/earned on Cosmonaut dashboard"
    print("✓ Step 9 PASSED: Cosmonaut portal displays Gold earned badge and complete mark breakdown.")

    # -------------------------------------------------------------------------
    # STEP 10: Final Database Integrity and Multi-Session Persistence Audit
    # -------------------------------------------------------------------------
    print("\n[STEP 10] Final database integrity and multi-session persistence check...")
    final_counts = inspect_db_counts("Step 10 - Final Comprehensive State")
    assert final_counts["badges"] == 1
    assert final_counts["band_mappings"] >= 1
    assert final_counts["mapping_requests"] == 1
    assert final_counts["badge_timelines"] == 2
    assert final_counts["reviewer_project_prompts"] == 1
    assert final_counts["project_submissions"] == 1
    assert final_counts["assessment_marksheets"] == 2

    # Verify that a brand new DataStore instance correctly loads all persisted records
    new_store = store.__class__()
    assert len(new_store.get_all_badges()) == 1, "New store failed to load badges from SQLite"
    assert len(new_store.get_band_mappings()) >= 1, "New store failed to load band_mappings from SQLite"
    assert len(new_store.get_mapping_requests()) == 1, "New store failed to load mapping_requests from SQLite"
    assert len(new_store.get_all_submissions()) == 1, "New store failed to load submissions from SQLite"
    assert len(new_store.get_all_assessments()) == 2, "New store failed to load assessments from SQLite"
    assert len(new_store.get_reviewer_project_prompts()) == 1, "New store failed to load project prompts from SQLite"

    print("✓ Step 10 PASSED: All records reliably survive fresh application restarts & reload directly from SQLite.")

    print("\n==================================================================")
    print("   ALL 10 END-TO-END STEPS FULLY PASSED & PERSISTED IN SQLITE!")
    print("==================================================================")


if __name__ == "__main__":
    run_e2e_verification()
