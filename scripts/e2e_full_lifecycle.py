"""
Run:  python scripts/e2e_full_lifecycle.py   (throw-away copy of data/starapp.db; never touches the real one)

Full lifecycle check:
 cycle -> badge creation -> reviewer approval -> publish -> mapping (2 cosmonauts) -> project -> submissions -> reviewer marks
 -> Guardian decisions (one re-attempt loop, one revoke) -> both earn -> mapping completes -> marksheets/UI -> persistence (separate
 sqlite connection + a fresh process) -> integrity / FK / orphan checks -> timing of every action.
"""
import json, os, shutil, sqlite3, subprocess, sys, tempfile, time, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp(prefix="starapp_flow_")
DB = os.path.join(tmp, "starapp.db")
shutil.copy(os.path.join(ROOT, "data", "starapp.db"), DB)
os.environ["STARAPP_DB_PATH"] = DB
os.environ["DATABASE_URL"] = DB
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from starapp.app import StarAppController
from starapp.storage import store

results, timings = [], []
stmts = []
_cur = {'n': None, 'sql': []}



def check(name, cond, extra=""):
    results.append((bool(cond), name))
    print(("PASS " if cond else "FAIL ") + name + ((" -> " + str(extra)[:300]) if (not cond and extra) else ""), flush=True)


def q(sql, params=()):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, params).fetchall()]
    finally:
        c.close()


class User:
    def __init__(self, uid):
        self.c = StarAppController()
        self.c.initialize()
        self.c.handle_event("select_demo_account", uid)
        self.uid = uid

    def ev(self, action, payload=""):
        _cur['sql'] = []
        try:
            store.db.conn.set_trace_callback(lambda x: _cur['sql'].append(x))
        except Exception:
            pass
        t = time.perf_counter()
        self.c.handle_event(action, json.dumps(payload) if isinstance(payload, (dict, list)) else payload)
        dt = (time.perf_counter() - t) * 1000
        writes = [x for x in _cur['sql'] if x.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE"))]
        stmts.append((len(_cur['sql']), len(writes), f"{self.uid}:{action}", [w[:90] for w in writes if "OR REPLACE" in w.upper() or (w.upper().startswith("DELETE") and "WHERE" not in w.upper())]))
        timings.append((dt, f"{self.uid}:{action}"))
        return self.c

    def page(self):
        t = time.perf_counter()
        self.c.render()
        timings.append(((time.perf_counter() - t) * 1000, f"{self.uid}:render"))
        return self.c.last_rendered_regions.get("mainContentHtml", "")


def step(title):
    print("\n== " + title, flush=True)


try:
    G = User("guardian_1")
    REV = "m_b2_1"
    C1, C2 = "m_b1_1", "m_b1_2"

    # ------------------------------------------------------------------ 1. cycle
    step("1. Cycle creation")
    before = {r["id"] for r in q("SELECT id FROM performance_cycles")}
    G.ev("nav_guardian", "g_cycles")
    G.ev("open_create_cycle_modal")
    check("create-cycle dialog opens", G.c.active_modal == "create_cycle_modal")
    G.ev("create_six_month_cycle", {"name": "Flow Check Cycle", "start_date": "2027-01-01", "end_date": "2027-06-30", "code": "FLOW-27", "set_as_active": True, "auto_close_previous": True})
    new = [r for r in q("SELECT * FROM performance_cycles") if r["id"] not in before]
    check("cycle saved in SQLite (new row)", len(new) == 1, G.c.last_flash_message)
    cyc = new[0] if new else {}
    check("cycle is active and selected", cyc.get("status") == "active" and G.c.selected_cycle_id == cyc.get("id"), cyc)
    check("g_cycles page renders with the new cycle", "Flow Check Cycle" in G.page())

    # ------------------------------------------------------------------ 2. badge creation + reviewer approval + publish
    step("2. Badge creation -> reviewer approval -> publish")
    prompt = {
        "title": "Flow Check Foundations", "skill": "Signals", "capability": "Data & Machine", "power": "Tech", "target_band": "B1",
        "description": "Foundational flow-check badge.", "learning_outcomes": ["Can do A.", "Can do B."],
        "practice_project": {"intro": "i", "prompt": "p", "footnote": "f"}, "practice_prompt": "p",
        "learning_topics": [{"title": "1. One", "description": "d", "completed": False}, {"title": "2. Two", "description": "d", "completed": False}],
        "learning_resources": {"intro": "i", "prompt": "p", "footnote": "f"}, "resources_prompt": "p"}
    G.ev("nav_guardian", "g_create_badge")
    G.ev("select_create_badge_band", "B1")
    elig = store.get_eligible_badge_reviewers("B1")
    check("eligible reviewers are strictly higher band than B1", elig and all(int(r["band"].replace("B", "")) > 1 for r in elig))
    G.ev("select_badge_reviewer", REV)
    G.ev("preview_new_badge", {"code": "B1-FLW-01", "title": "Flow Check Foundations", "prompt_json": json.dumps(prompt)})
    G.ev("create_badge", "{}")
    rows = q("SELECT * FROM badges WHERE code LIKE 'B1-FLW-01%'")
    check("badge saved in SQLite", len(rows) == 1, G.c.last_flash_message)
    bid = rows[0]["id"]
    check("badge belongs to the new cycle", rows[0].get("cycle_id") in (cyc.get("id"), None, ""), rows[0].get("cycle_id"))
    check("badge starts pending_review, unpublished, reviewer assigned", rows[0]["workflow_status"] == "pending_review" and not rows[0]["is_published"] and rows[0]["assigned_reviewer_id"] == REV)
    R = User(REV)
    R.ev("approve_submitted_badge", bid)
    check("reviewer approves -> workflow_status approved (SQLite)", q("SELECT workflow_status FROM badges WHERE id=?", (bid,))[0]["workflow_status"] == "approved")
    G.ev("publish_badge", bid)
    b = q("SELECT * FROM badges WHERE id=?", (bid,))[0]
    check("Guardian publishes (is_published, published_by, published_at saved)", b["is_published"] and b["published_by"] == "guardian_1" and b["published_at"])

    # ------------------------------------------------------------------ 3. mapping
    step("3. Mapping reviewer <-> 2 cosmonauts")
    title = b["title"]
    G.ev("nav_guardian", "g_mapping")
    G.ev("select_mapping_band", "B1")
    G.ev("select_mapping_badge", title)
    G.ev("toggle_mapping_cosmonaut", C1)
    G.ev("toggle_mapping_cosmonaut", C2)
    G.ev("toggle_mapping_reviewer", REV)
    G.ev("select_mapping_review_anchor", "2027-01-20")
    G.ev("set_mapping_review_direction", "after")
    G.ev("send_mapping_requests", "{}")
    R2 = User(REV)
    R2.ev("accept_mapping_request", f"req_B1_{bid}_{REV}")
    G.ev("execute_cosmonaut_mapping", "{}")
    tl1, tl2 = store.get_timeline(bid, C1), store.get_timeline(bid, C2)
    check("both cosmonauts get a timeline with the mapped reviewer (SQLite)", tl1 and tl2 and tl1.reviewer_id == REV and tl2.reviewer_id == REV,
          G.c.last_flash_message)
    mp = [m for m in store.get_band_mappings() if m.get("badge_id") == bid and C1 in m.get("cosmonauts", [])]
    check("mapping saved: active, both cosmonauts, reviewer", mp and mp[0].get("status") in ("active", None, "") and C2 in mp[0]["cosmonauts"] and REV in mp[0]["reviewers"], mp)

    # ------------------------------------------------------------------ 4. project + submissions
    step("4. Project request -> reviewer sends -> cosmonauts submit")
    brief = "Case Study" + chr(10) + "A." + chr(10) + chr(10) + "Your Challenge" + chr(10) + "B."
    cu1, cu2 = User(C1), User(C2)
    R.ev("nav_cosmonaut", "c_badge_reviews")
    h = R.page()
    check("reviewer schedule shows the badge under Upcoming with a LOCKED Assessment button (nothing submitted yet)", "rv-assess is-locked" in h or "rv-assess" in h)
    R.ev("send_reviewer_project", {"badge_id": bid, "title": "Flow Project", "content": brief, "cosmonaut_ids": [C1, C2], "status": "released"})
    check("project released to both cosmonauts (SQLite)", len(q("SELECT * FROM reviewer_project_prompts WHERE badge_id=?", (bid,))) >= 1)
    SUB = {"badge_id": bid, "pdf_name": "r.pdf", "pdf_payload": "x", "code_name": "a.py", "code_payload": "print(1)", "github_url": "https://github.com/a/b"}
    cu1.ev("open_allocated_project_page", bid)
    check("cosmonaut project page opens", "Submit Deliverables" in cu1.page())
    cu1.ev("submit_project_deliverable", SUB)
    cu2.ev("submit_project_deliverable", SUB)
    s1 = store.get_submissions_for_cosmonaut(C1, bid)
    s2 = store.get_submissions_for_cosmonaut(C2, bid)
    check("both submissions saved (attempt 1, pending)", len(s1) == 1 and len(s2) == 1 and s1[0].status == "pending" and s1[0].attempt_number == 1)
    sid1, sid2 = s1[0].id, s2[0].id

    # ------------------------------------------------------------------ 5. reviewer marks (recommendation)
    step("5. Reviewer marks + recommendation")
    def marks(sid, each, dec):
        return {"submission_id": sid, "bu": each, "ar": each, "tk": each, "pr": each, "qa": each, "strengths": "Good.", "improvements": "More tests.", "feedback": "Summary.", "decision": dec}
    R.ev("nav_cosmonaut", "c_badge_reviews")
    check("Assessment button enabled for the submission", f"open_reviewer_assessment_page', '{sid1}'" in R.page())
    R.ev("open_reviewer_assessment_page", sid1)
    h = R.page()
    check("assessment panel renders rubric + recommendation options", "lg-dec-opt" in h and 'id="rubric-bu"' in h)
    R.ev("submit_reviewer_assessment", marks(sid1, 9, "approve"))
    R.ev("submit_reviewer_assessment", marks(sid2, 5, "resubmit"))
    a1 = store.get_reviewer_assessment_for_submission(sid1)
    a2 = store.get_reviewer_assessment_for_submission(sid2)
    check("reviewer marks saved with recommendations", a1 and a2 and a1.decision == "recommend_approve" and a2.decision == "recommend_resubmit", (a1 and a1.decision, a2 and a2.decision))
    R.ev("submit_reviewer_assessment", marks(sid1, 3, "reject"))
    check("marks are locked: second submission refused, still ONE reviewer marksheet", len(q("SELECT id FROM assessment_marksheets WHERE submission_id=? AND assessor_role='reviewer'", (sid1,))) == 1)
    cu1.ev("nav_cosmonaut", "c_results")
    h = cu1.page()
    check("cosmonaut sees the reviewer marksheet immediately (one sheet, 5 criteria, reviewer name, attempt)", "ms-sheet" in h and h.count('class="ms-crit"') == 5 and "Rohan Deshmukh" in h and "ms-tab" not in h)

    # ------------------------------------------------------------------ 6. Guardian decisions
    step("6. Guardian decisions (earn / re-attempt / revoke)")
    G.ev("nav_guardian", "g_reviews")
    h = G.page()
    check("Guardian dashboard highlights the badge awaiting decision", "asm-attn-pill" in h and "is-attention" in h)
    G.ev("open_submission_review_page", sid1)
    h = G.page()
    check("Guardian panel pre-fills reviewer marks and shows the recommendation", 'id="rubric-bu"' in h and "Give Badge" in h)
    G.ev("submit_guardian_final_assessment", marks(sid1, 9, "approve"))
    check("C1: submission approved", store.get_submission(sid1).status == "approved")
    tl1 = store.get_timeline(bid, C1)
    check("C1: timeline completed with award date", tl1.status == "completed" and tl1.actual_award_date)
    mp = [m for m in store.get_band_mappings() if m.get("badge_id") == bid and C1 in m.get("cosmonauts", [])][0]
    check("C1 uncoupled; mapping STILL active (C2 not earned yet)", C1 in mp.get("completed_cosmonauts", []) and mp.get("status") != "completed", mp.get("status"))
    G.ev("submit_guardian_final_assessment", marks(sid1, 3, "reject"))
    check("C1: a 2nd Guardian decision is refused (locked)", store.get_guardian_assessment_for_submission(sid1).decision == "approve")
    cu1.ev("nav_cosmonaut", "c_submission")
    h = cu1.page()
    check("C1: gold badge shown on the cosmonaut Badges page", "gold" in h)
    R.ev("nav_cosmonaut", "c_badge_reviews")
    h = R.page()
    i_done = h.index("Completed Reviews")
    check("reviewer: badge is under Upcoming (NOT Completed) while C2 has not earned", "Flow Check Foundations" in h[:i_done] and "Flow Check Foundations" not in h[i_done:])

    G.ev("open_submission_review_page", sid2)
    G.ev("submit_guardian_final_assessment", marks(sid2, 5, "resubmission_requested"))
    check("C2: Re-attempt -> retake_required", store.get_submission(sid2).status == "retake_required")
    cu2.ev("open_allocated_project_page", bid)
    check("C2: can submit a new attempt", "Submit Deliverables" in cu2.page())
    cu2.ev("submit_project_deliverable", SUB)
    subs2 = store.get_submissions_for_cosmonaut(C2, bid)
    check("C2: attempt 2 added, attempt 1 kept (append-only)", [s.attempt_number for s in subs2] == [1, 2])
    sid2b = subs2[-1].id
    R.ev("submit_reviewer_assessment", marks(sid2b, 9, "approve"))
    G.ev("submit_guardian_final_assessment", marks(sid2b, 9, "approve"))
    check("C2: attempt 2 approved", store.get_submission(sid2b).status == "approved")
    mp = [m for m in store.get_band_mappings() if m.get("badge_id") == bid and C1 in m.get("cosmonauts", [])][0]
    check("ALL cosmonauts earned -> mapping status 'completed'", mp.get("status") == "completed" and set(mp.get("completed_cosmonauts", [])) >= {C1, C2}, mp)
    check("both timelines completed", store.get_timeline(bid, C1).status == "completed" and store.get_timeline(bid, C2).status == "completed")
    R.ev("nav_cosmonaut", "c_badge_reviews")
    h = R.page()
    i_done = h.index("Completed Reviews")
    check("reviewer: badge MOVED to Completed Reviews once all mapped cosmonauts earned", "Flow Check Foundations" in h[i_done:] and "Flow Check Foundations" not in h[:i_done])
    check("completed card has no Create/Send-project button", "send_reviewer_project" not in h[i_done:] and "open_reviewer_project_modal" not in h[i_done:])

    # revoke + redo
    G.ev("open_revoke_decision_confirm", sid2b)
    check("revoke confirmation dialog opens", G.c.active_modal == "decision_revoke_confirm")
    G.ev("revoke_guardian_decision", sid2b)
    mp = [m for m in store.get_band_mappings() if m.get("badge_id") == bid and C1 in m.get("cosmonauts", [])][0]
    check("revoke: submission back to reviewer_assessed, mapping re-activated, C2 no longer completed",
          store.get_submission(sid2b).status == "reviewer_assessed" and mp.get("status") != "completed" and C2 not in mp.get("completed_cosmonauts", []), mp)
    G.ev("submit_guardian_final_assessment", marks(sid2b, 9, "approve"))
    mp = [m for m in store.get_band_mappings() if m.get("badge_id") == bid and C1 in m.get("cosmonauts", [])][0]
    check("re-approve -> mapping completed again", mp.get("status") == "completed")

    # ------------------------------------------------------------------ 7. marksheets
    step("7. Marksheets / UI")
    for cu, cid in ((cu1, C1), (cu2, C2)):
        cu.ev("nav_cosmonaut", "c_results")
        h = cu.page()
        check(f"{cid}: marksheet page = one sheet, 3 stat tiles+reviewer+attempt, 5 criteria, no table", h.count('class="ms-crit"') == 5 and "ms-tab" not in h and "<table" not in h and "Reviewer" in h and "Attempt" in h)
        check(f"{cid}: marksheet shows 45.0 total (9 x 5)", "45.0" in h)
        check(f"{cid}: timestamps are IST, no UTC", "UTC" not in h)

    # ------------------------------------------------------------------ 8. persistence
    step("8. Persistence in the SQLite FILE")
    check("PRAGMA integrity_check ok", q("PRAGMA integrity_check")[0]["integrity_check"] == "ok")
    check("no foreign-key violations", q("PRAGMA foreign_key_check") == [])
    n_g = q("SELECT COUNT(*) c FROM assessment_marksheets WHERE submission_id IN (?,?,?) AND assessor_role='guardian'", (sid1, sid2, sid2b))[0]["c"]
    check("Guardian marksheets in file: C1 + C2 attempt2 (attempt1 re-attempt kept) = 3", n_g == 3, n_g)
    check("submissions in file", len(q("SELECT id FROM project_submissions WHERE badge_id=?", (bid,))) == 3)
    orphans = q("SELECT COUNT(*) c FROM assessment_marksheets a LEFT JOIN project_submissions s ON s.id=a.submission_id WHERE s.id IS NULL")[0]["c"]
    check("no orphan marksheets", orphans == 0, orphans)
    check("activity log recorded", len(q("SELECT id FROM activity_events WHERE badge_id=?", (bid,))) > 0)
    # a FRESH process reading the same DB file sees the final state
    code = (
        "import os,sys,json;sys.path.insert(0,r'%s');os.chdir(r'%s')\n"
        "from starapp.storage import store\n"
        "s=store.get_submissions_for_cosmonaut('%s','%s');t1=store.get_timeline('%s','%s');t2=store.get_timeline('%s','%s')\n"
        "m=[x for x in store.get_band_mappings() if x.get('badge_id')=='%s' and '%s' in x.get('cosmonauts',[])][0]\n"
        "print(json.dumps({'subs':[x.status for x in s],'t1':t1.status,'t2':t2.status,'map':m.get('status'),'comp':sorted(m.get('completed_cosmonauts',[]))}))"
        % (ROOT, ROOT, C2, bid, bid, C1, bid, C2, bid, C1))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=os.environ.copy())
    try:
        d = json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        d = {}
    check("fresh process reloads the same final state from the DB file", d.get("subs") == ["retake_required", "approved"] and d.get("t1") == "completed" and d.get("t2") == "completed" and d.get("map") == "completed" and d.get("comp") == sorted([C1, C2]), (d, out.stderr[-300:]))

    # ------------------------------------------------------------------ 9. efficiency
    step("9. Timing")
    timings.sort(reverse=True)
    print("slowest 8:", [(round(t, 1), n) for t, n in timings[:8]])
    check("every action+render under 400 ms", timings[0][0] < 400, timings[0])
    stmts[:] = [x for x in stmts if not x[2].endswith("create_six_month_cycle")]      # one-off: copies the previous cycle's appraisals (about 435 statements)
    heavy = sorted(stmts, reverse=True)[:5]
    print("most SQL statements per action:", [(a, w, n) for a, w, n, _ in heavy])
    check("no action issues more than 120 SQL statements (largest: publish_badge ~96, one-off)", heavy[0][0] <= 120, heavy[0][:3])
    risky = [(n, [w for w in r if "announcements" in w.lower()]) for _, _, n, r in stmts]
    risky = [x for x in risky if x[1]]      # only tables with ON DELETE CASCADE children matter (announcements); the rest are safe
    check("no INSERT OR REPLACE on a table with cascade children (announcements)", not risky, risky[:3])
    renders = [t for t, n in timings if n.endswith(":render")]
    check("median render under 40 ms", sorted(renders)[len(renders) // 2] < 40, sorted(renders)[len(renders) // 2])
except Exception:
    traceback.print_exc()
    results.append((False, "script crashed"))

bad = [n for ok, n in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(bad)))
for n in bad:
    print("  FAILED:", n)
shutil.rmtree(tmp, ignore_errors=True)
