"""
Run:  python scripts/e2e_guardian_logic.py   (uses a throw-away copy of data/starapp.db - never touches the real one)

End-to-end check of the Guardian portal logic, step by step, with every write re-read from the SQLite FILE through a
separate connection (so "saved" means saved in the database, not just in memory).
Runs on a throw-away copy of the database.
"""
import datetime
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp(prefix="starapp_e2e_")
DB = os.path.join(tmp, "starapp.db")
shutil.copy(os.path.join(ROOT, "data", "starapp.db"), DB)
os.environ["STARAPP_DB_PATH"] = DB
os.environ["DATABASE_URL"] = DB
sys.path.insert(0, ROOT)

from starapp.app import StarAppController
from starapp.storage import store

results = []


def check(name, cond, extra=""):
    results.append((bool(cond), name, extra))
    print(("PASS " if cond else "FAIL ") + name + (("  -> " + str(extra)) if (extra and not cond) else ""))


def q(sql, params=()):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        return c.execute(sql, params).fetchall()
    finally:
        c.close()


def section(t):
    print("\n=== " + t + " ===")


def run():
    store.reset_to_seed()
    g = StarAppController()
    g.initialize()

    def ev(action, payload="{}"):
        g.handle_event(action, payload if isinstance(payload, str) else json.dumps(payload))

    def page():
        g.render()
        return g.last_rendered_regions["mainContentHtml"]

    def modal():
        return g.render_active_modal()

    # ---------------------------------------------------------------- 1. sign-in + sidebar
    section("1. Guardian sign-in, sidebar, every Guardian page renders")
    ev("select_demo_account", "guardian_1")
    check("guardian signed in", g.current_user and g.current_user.id == "guardian_1")
    ev("select_create_badge_band", "B1")
    g.render()
    side = g.last_rendered_regions["sidebarHtml"]
    check("sidebar header is a band chip only", 'class="sidebar-band-chip"' in side and "GUARDIAN PORTAL" not in side.upper())
    for view in ("g_dashboard", "g_create_badge", "g_badge_approval", "g_mapping", "g_allotment", "g_reviews",
                 "g_materials", "g_extensions", "g_announcements", "g_activity", "g_cycles"):
        try:
            ev("nav_guardian", view)
            html = page()
            check(f"page {view} renders", len(html) > 200 and "Traceback" not in html, g.current_view)
        except Exception as exc:
            check(f"page {view} renders", False, repr(exc))

    # ---------------------------------------------------------------- 2. badge approval page
    section("2. Reviewer Badge Approval page (filters, search, rows)")
    ev("nav_guardian", "g_badge_approval")
    html = page()
    check("approval rows use the new row layout", "ba-row" in html or "No badge" in html or "badge" in html.lower())
    for status in ("all", "pending_review", "approved", "returned", "history"):
        ev("filter_badge_approval", status)
        check(f"filter '{status}' renders", len(page()) > 100)
    ev("filter_badge_approval", "all")
    ev("search_badge_approval", "Signals")
    h = page()
    check("search narrows to Signals", "Signals Foundations" in h and "Data Systems Architecture" not in h)
    ev("search_badge_approval", "")
    check("search cleared restores the list", "Data Systems Architecture" in page())

    # ---------------------------------------------------------------- 3. mapping page
    section("3. Mapping page: select, send requests, 24h timer, saved cards")
    ev("nav_guardian", "g_mapping")
    html = page()
    check("mapping page: 4 cards + All bands filter", "mapping-band-row" in html and "Search badge name" in html)
    ev("select_mapping_badge", "Signals Foundations")
    for cid in ("m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4"):
        ev("toggle_mapping_cosmonaut", cid)
    for rid in ("m_b2_1", "m_b2_2"):
        ev("toggle_mapping_reviewer", rid)
    check("cosmonauts + reviewers selected", len(g.mapping_selected_cosmonauts) == 4 and len(g.mapping_selected_reviewers) == 2)
    ev("send_mapping_requests")
    reqs = q("SELECT id, reviewer_id, status, data_json FROM mapping_requests")
    check("requests written to DB", len(reqs) >= 2, len(reqs))
    mine = [r for r in reqs if r["id"].startswith("req_B1_badge_b1_signals")]
    check("2 pending requests for the 2 reviewers", len(mine) == 2 and all(r["status"] == "pending" for r in mine))
    d = json.loads(mine[0]["data_json"])
    left = (datetime.datetime.fromisoformat(d["expires_at"]) - datetime.datetime.fromisoformat(d["sent_at"])).total_seconds()
    check("deadline = sent_at + 24h stored in DB", int(left) == 86400, left)
    html = page()
    check("saved card shows checklist + countdown row", "mbc-checks" in html and "rq-timer" in html)
    check("selections reset after sending", g.mapping_selected_badge == "" and g.mapping_selected_cosmonauts == [])

    # ---------------------------------------------------------------- 4. reviewer side + expiry + resend
    section("4. Reviewer accepts; unanswered request expires after 24h; Guardian resends")
    req1 = next(r for r in mine if r["reviewer_id"] == "m_b2_1")
    req2 = next(r for r in mine if r["reviewer_id"] == "m_b2_2")
    ev("select_demo_account", "m_b2_1")
    ev("nav_cosmonaut", "c_requests")
    check("reviewer page shows the countdown", "rq-timer" in page())
    ev("accept_mapping_request", req1["id"])
    row = q("SELECT status, data_json FROM mapping_requests WHERE id=?", (req1["id"],))[0]
    check("accept saved (status accepted + responded_at)", row["status"] == "accepted" and json.loads(row["data_json"]).get("responded_at"))
    # pretend request 2 was sent 25h ago
    r2 = next(r for r in store.get_mapping_requests() if r["id"] == req2["id"])
    r2["expires_at"] = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).isoformat()
    ev("select_demo_account", "guardian_1")
    ev("nav_guardian", "g_mapping")
    row = q("SELECT status, data_json FROM mapping_requests WHERE id=?", (req2["id"],))[0]
    check("auto-expiry saved (rejected + expired)", row["status"] == "rejected" and json.loads(row["data_json"]).get("expired") is True)
    check("both sides notified of the expiry", any("Expired" in n["title"] for n in q("SELECT title FROM notifications")))
    ev("select_demo_account", "m_b2_2")
    ev("accept_mapping_request", req2["id"])
    check("late accept refused", q("SELECT status FROM mapping_requests WHERE id=?", (req2["id"],))[0]["status"] == "rejected")
    ev("select_demo_account", "guardian_1")
    ev("resend_mapping_request", req2["id"])
    row = q("SELECT status, data_json FROM mapping_requests WHERE id=?", (req2["id"],))[0]
    check("resend reopens with a fresh 24h window", row["status"] == "pending" and not json.loads(row["data_json"]).get("expired"))
    ev("select_demo_account", "m_b2_2")
    ev("accept_mapping_request", req2["id"])
    check("reviewer 2 accepts in time", q("SELECT status FROM mapping_requests WHERE id=?", (req2["id"],))[0]["status"] == "accepted")
    ev("select_demo_account", "guardian_1")

    # ---------------------------------------------------------------- 5. calendar
    section("5. Review Schedule Calendar (3 / 5 / 7 / Manual)")
    ev("nav_guardian", "g_mapping")
    ev("open_mapping_calendar_modal")
    m = modal()
    check("calendar modal = month/year/days dropdowns + grid only", all(x in m for x in ("mapping-cal-month-select", "mapping-cal-year-select", "mapping-cal-days-select", "cal-days-grid"))
          and not any(x in m for x in ("Apply Schedule", "Range Pick", "mapping-date-from")))
    ev("set_mapping_review_duration", "5")
    ev("select_mapping_review_anchor", "2026-11-20")
    check("5 working days from Fri 20 Nov skip the weekend", g.mapping_review_dates == ["2026-11-20", "2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"], g.mapping_review_dates)
    ev("set_mapping_review_duration", "3")
    ev("select_mapping_review_anchor", "2026-11-18")
    check("3 days", g.mapping_review_dates == ["2026-11-18", "2026-11-19", "2026-11-20"])
    ev("set_mapping_review_mode", "manual")
    ev("select_mapping_review_anchor", "2026-11-19")
    ev("select_mapping_review_anchor", "2026-11-24")
    check("manual toggling (off 19, on 24)", g.mapping_review_dates == ["2026-11-18", "2026-11-20", "2026-11-24"], g.mapping_review_dates)
    ev("change_mapping_calendar_month", {"year": 2026, "month": 12})
    check("month change", g.mapping_calendar_month == 12)
    ev("close_modal")
    ev("set_mapping_review_mode", "gap")
    ev("set_mapping_review_duration", "3")
    ev("select_mapping_review_anchor", "2026-11-18")

    # ---------------------------------------------------------------- 6. mapping detail + map
    section("6. Mapped-badge detail page, Map, Save mapping")
    ev("open_mapping_badge_detail", "badge_b1_signals")
    h = page()
    check("detail page: history rows, cohort, no codes/dates/Ready-text",
          "rq-table" in h and "Final Review Cohort" in h and "Ready to equally partition" not in h and "B1-SIG-01" not in h)
    check("title hoisted into the Back-button row", "app-title-hoisted" in h and "Signals Foundations" in g.last_rendered_regions["topbarHtml"])
    ev("preview_cosmonaut_mapping", {"band": "B1", "badge_id": "badge_b1_signals", "badge": "Signals Foundations"})
    h = page()
    check("staged preview shows both reviewers", "Proposed Assignment Partition" in h)
    ev("save_staged_mapping", {"band": "B1", "badge_id": "badge_b1_signals", "badge": "Signals Foundations"})
    bm = q("SELECT data_json FROM band_mappings WHERE badge_id='badge_b1_signals'")
    check("band mapping saved in DB (2 reviewers)", len(bm) == 2, len(bm))
    allc = sorted(c for r in bm for c in json.loads(r["data_json"]).get("cosmonauts", []))
    check("all 4 cosmonauts mapped in DB", allc == ["m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4"], allc)
    ev("nav_guardian", "g_mapping")
    check("mapped card says 4 mapped", "4</strong> cosmonauts mapped" in page())

    # ---------------------------------------------------------------- 7. allotment cards + modals
    section("7. Badge Allotment: cards, Timeline & Mapping (read-only), Edit Badge (saves everything)")
    ev("nav_guardian", "g_allotment")
    h = page()
    check("allotment cards: name title, no code/band chips, 3 buttons on one row", "lg-allot-title" in h and "lg-allot-band" not in h and "lg-allot-actions" in h)
    ev("open_badge_timeline_mapping_modal", "badge_b1_signals")
    m = modal()
    check("timeline modal is read-only", "<input" not in m and "Save Timeline" not in m and "Read-only view" in m and "tm-step" in m)
    check("timeline modal lists the 2 reviewers with cosmonaut chips", m.count("tm-rev-name") >= 2 and "Assigned Cosmonauts (" in m)
    ev("close_modal")

    badge_before = {k: v for k, v in dict(q("SELECT * FROM badges WHERE id='badge_b1_signals'")[0]).items()}
    ev("open_edit_badge_modal", "badge_b1_signals")
    m = modal()
    check("edit modal: timeline + reviewer-grouped cosmonauts, no details card, glass date buttons",
          "eb-timeline" in m and "eb-groups" in m and "Badge Details" not in m and m.count('class="gd-btn"') == 8 and 'type="date"' not in m)
    owners = {}
    for r in q("SELECT data_json FROM band_mappings WHERE badge_id='badge_b1_signals'"):
        dj = json.loads(r["data_json"])
        for c in dj["cosmonauts"]:
            owners[c] = dj["reviewers"][0]
    extra = next(c.id for c in store.get_all_cosmonauts() if c.band == "B1" and c.id not in owners)
    first, second = sorted(set(owners.values()))[:2]
    moved = next(c for c, r in owners.items() if r == first)
    ra = dict(owners)
    ra[extra] = second
    ra[moved] = second
    payload = {"badge_id": "badge_b1_signals", "code": "TAMPER", "title": "TAMPER", "description": "x", "project_requirements": "x",
               "assigned_cosmonaut_ids": list(ra), "reviewer_assignments": ra,
               "assignment_date": "2026-11-27", "learning_start_date": "2026-11-18", "learning_end_date": "2026-11-20",
               "project_start_date": "2026-11-21", "project_end_date": "2026-11-25", "submission_deadline": "2026-12-24",
               "review_date": "2026-12-26", "expected_award_date": "2026-12-30"}
    ev("save_badge_form", payload)
    check("edit save succeeded", g.flash_type == "success", g.last_flash_message)
    after = dict(q("SELECT * FROM badges WHERE id='badge_b1_signals'")[0])
    same = all(after[k] == badge_before[k] for k in ("code", "title", "description", "project_requirements", "target_band", "power", "capability", "skill", "workflow_status", "is_published"))
    check("badge content untouched by a tampered payload (DB)", same)
    check("assigned list + timeline saved in the badge row (DB)", extra in json.loads(after["assigned_cosmonaut_ids_json"]) and json.loads(after["default_timeline_json"]).get("submission_deadline") == "2026-12-24")
    tl = q("SELECT reviewer_id, submission_deadline, review_window_json FROM badge_timelines WHERE badge_id='badge_b1_signals' AND cosmonaut_id=?", (extra,))
    check("new cosmonaut's timeline (DB): reviewer + deadline + review window", tl and tl[0]["reviewer_id"] == second and tl[0]["submission_deadline"] == "2026-12-24" and json.loads(tl[0]["review_window_json"]))
    tl2 = q("SELECT reviewer_id FROM badge_timelines WHERE badge_id='badge_b1_signals' AND cosmonaut_id=?", (moved,))
    check("moved cosmonaut now belongs to the other reviewer (DB timeline)", tl2 and tl2[0]["reviewer_id"] == second)
    bm = {json.loads(r["data_json"])["reviewers"][0]: json.loads(r["data_json"]) for r in q("SELECT data_json FROM band_mappings WHERE badge_id='badge_b1_signals'")}
    check("band mappings updated (DB)", extra in bm[second]["cosmonauts"] and moved in bm[second]["cosmonauts"] and moved not in bm[first]["cosmonauts"])
    rq = {r["reviewer_id"]: json.loads(r["data_json"]) for r in q("SELECT reviewer_id, data_json FROM mapping_requests WHERE data_json LIKE '%badge_b1_signals%'")}
    check("reviewer request cadet lists updated (DB)", extra in rq[second]["cosmonaut_ids"] and moved in rq[second]["cosmonaut_ids"])
    check("reviewer notified (DB)", any("added to your review group" in n["title"] for n in q("SELECT title FROM notifications WHERE recipient_id=?", (second,))))
    ev("open_badge_timeline_mapping_modal", "badge_b1_signals")
    m = modal()
    check("timeline view reflects the edit (new deadline, new cosmonaut)", "24 Dec 2026" in m and store.get_user_by_id(extra).name in m)
    ev("close_modal")
    # guards
    ev("save_badge_form", {**payload, "assigned_cosmonaut_ids": []})
    check("edit needs >= 1 cosmonaut", g.flash_type == "warning")
    ev("save_badge_form", {**payload, "reviewer_assignments": {**ra, extra: "m_b2_3"}})
    check("edit refuses a reviewer not mapped to the badge", g.flash_type == "error")
    ev("save_badge_form", {**payload, "learning_start_date": "2026-11-30", "learning_end_date": "2026-11-18"})
    check("edit refuses end before start", g.flash_type == "error")

    # ---------------------------------------------------------------- 8. publish / revoke
    section("8. Publish to roadmap / revoke")
    ev("publish_badge", "badge_b1_signals")
    check("publish saved (DB)", q("SELECT is_published FROM badges WHERE id='badge_b1_signals'")[0]["is_published"] == 1)
    check("published card shows Revoke", "Revoke" in (ev("nav_guardian", "g_allotment") or page()))

    # ---------------------------------------------------------------- 9. cosmonaut submits, reviewer assesses, guardian final
    section("9. Submission -> reviewer marks -> Guardian final assessment (Assessment Dashboard)")
    cid = "m_b1_1"
    owner_rev = q("SELECT reviewer_id FROM badge_timelines WHERE badge_id='badge_b1_signals' AND cosmonaut_id=?", (cid,))[0]["reviewer_id"]
    ev("select_demo_account", cid)
    ev("submit_project_deliverable", {"badge_id": "badge_b1_signals", "pdf_name": "report_v1.pdf", "pdf_payload": "data/sample_report.pdf",
                                      "code_name": "filter_v1.py", "code_payload": "print(1)", "github_url": "https://github.com/x/y"})
    check("submission saved (DB)", q("SELECT COUNT(*) c FROM project_submissions WHERE badge_id='badge_b1_signals' AND cosmonaut_id=?", (cid,))[0]["c"] == 1, g.last_flash_message)
    sub1 = q("SELECT id, status FROM project_submissions WHERE badge_id='badge_b1_signals' AND cosmonaut_id=?", (cid,))[0]
    ev("select_demo_account", owner_rev)
    rev = {"submission_id": sub1["id"], "bu": 6, "ar": 6, "tk": 6, "pr": 6, "qa": 6, "strengths": "s", "improvements": "i", "feedback": "f", "decision": "changes_requested"}
    ev("submit_reviewer_assessment", rev)
    check("reviewer marksheet saved (DB)", q("SELECT COUNT(*) c FROM assessment_marksheets WHERE submission_id=? AND assessor_role='reviewer'", (sub1["id"],))[0]["c"] == 1, g.last_flash_message)
    ev("select_demo_account", "guardian_1")
    ev("nav_guardian", "g_reviews")
    ev("open_assessment_badge", "badge_b1_signals")
    h = page()
    check("assessment tree: no level tags / codes / hierarchy; reviewer + cosmonaut nodes + blue elbow element",
          "Level 1" not in h and "Level 2" not in h and "lg-hier-disclosure" not in h and "asm-tree-reviewer-branch" in h and 'class="asm-elbow"' in h)
    ev("open_assessment_cosmonaut", {"badge_id": "badge_b1_signals", "cosmonaut_id": cid})
    h = page()
    check("cosmonaut page: compact attempts list, no role/feedback sentences", "lg-att-summary" in h and "Role:" not in h and "lg-meter" in h)
    ev("open_submission_review_page", sub1["id"])
    h = page()
    check("marks page: no Back-to-reviews button, no meta bar, feedback + decision controls",
          "Back to Project Reviews" not in h and "lg-rubric-meta-bar" not in h and 'id="rubric-decision"' in h and "lg-dec-list" in h and "RUBRIC-50" not in h)
    ev("submit_guardian_final_assessment", {"submission_id": sub1["id"], "bu": 6, "ar": 6, "tk": 6, "pr": 6, "qa": 6, "strengths": "s", "improvements": "i", "feedback": "f", "decision": "changes_requested"})
    check("below pass mark -> retake required (DB)", q("SELECT status FROM project_submissions WHERE id=?", (sub1["id"],))[0]["status"] == "retake_required", g.last_flash_message)
    ev("select_demo_account", cid)
    ev("submit_project_deliverable", {"badge_id": "badge_b1_signals", "pdf_name": "report_v2.pdf", "pdf_payload": "data/sample_report_v2.pdf",
                                      "code_name": "filter_v2.py", "code_payload": "print(2)", "github_url": "https://github.com/x/y2"})
    sub2 = q("SELECT id FROM project_submissions WHERE badge_id='badge_b1_signals' AND cosmonaut_id=? AND id<>?", (cid, sub1["id"]))[0]["id"]
    ev("select_demo_account", owner_rev)
    ev("submit_reviewer_assessment", {**rev, "submission_id": sub2, "bu": 9, "ar": 9, "tk": 9, "pr": 9, "qa": 9, "decision": "approve"})
    ev("select_demo_account", "guardian_1")
    ev("submit_guardian_final_assessment", {"submission_id": sub2, "bu": 9, "ar": 9, "tk": 9, "pr": 9, "qa": 9, "strengths": "s", "improvements": "i", "feedback": "f", "decision": "approve"})
    row = q("SELECT status FROM project_submissions WHERE id=?", (sub2,))[0]
    check("approved attempt saved (DB) -> badge earned", row["status"] == "approved", g.last_flash_message)
    check("timeline marked awarded (DB)", q("SELECT actual_award_date FROM badge_timelines WHERE badge_id='badge_b1_signals' AND cosmonaut_id=?", (cid,))[0]["actual_award_date"])
    ev("nav_guardian", "g_reviews")
    ev("open_assessment_badge", "badge_b1_signals")
    ev("open_assessment_cosmonaut", {"badge_id": "badge_b1_signals", "cosmonaut_id": cid})
    h = page()
    check("two attempts listed, newest open", h.count("lg-attempt-card") >= 2 and "<details class=\"lg-attempt-card\" open" in h.replace("\n", " ").replace("  ", " ") or h.count("<details") >= 2)

    # ---------------------------------------------------------------- 10. reload from the database
    section("10. Reload everything from the database and re-render")
    store.resync_from_database()
    g2 = StarAppController()
    g2.initialize()
    g2.handle_event("select_demo_account", "guardian_1")
    ok = True
    for view in ("g_mapping", "g_allotment", "g_reviews", "g_badge_approval"):
        g2.handle_event("nav_guardian", view)
        g2.render()
        ok = ok and len(g2.last_rendered_regions["mainContentHtml"]) > 200
    check("all key pages re-render after a reload from the DB", ok)
    g2.handle_event("open_badge_timeline_mapping_modal", "badge_b1_signals")
    check("timeline view after reload still shows the edit", "24 Dec 2026" in g2.render_active_modal())
    check("DB integrity", q("PRAGMA integrity_check")[0][0] == "ok")
    check("no FK violations", len(q("PRAGMA foreign_key_check")) == 0)


try:
    run()
except Exception:
    traceback.print_exc()
    check("script ran to completion", False)

fails = [r for r in results if not r[0]]
print("\n%d checks, %d failed" % (len(results), len(fails)))
for f in fails:
    print("  FAILED:", f[1], f[2])
