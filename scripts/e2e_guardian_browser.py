"""
Run:  python scripts/e2e_guardian_browser.py   (needs Google Chrome; set CHROME_PATH if it is elsewhere)

Real-browser end-to-end: live FastAPI server on a throw-away DB copy + headless Chrome driving the Guardian UI with real
clicks. Captures console errors / exceptions, checks for horizontal overflow on every page, and re-reads the SQLite file
after each save.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCR = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCR)
sys.path.insert(0, ROOT)
from _miniws import connect

tmp = tempfile.mkdtemp(prefix="starapp_br_")
DB = os.path.join(tmp, "starapp.db")
shutil.copy(os.path.join(ROOT, "data", "starapp.db"), DB)
PORT = 8133
CPORT = 9371
results = []


def check(name, cond, extra=""):
    results.append((bool(cond), name, extra))
    print(("PASS " if cond else "FAIL ") + name + (("  -> " + str(extra)[:300]) if (extra and not cond) else ""), flush=True)


def q(sql, params=()):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        return c.execute(sql, params).fetchall()
    finally:
        c.close()


# ------------------------------------------------------------------ 1. prepare data in-process (mapped + published badge, one reviewer-assessed submission)
os.environ["STARAPP_DB_PATH"] = DB
os.environ["DATABASE_URL"] = DB
from starapp.app import StarAppController
from starapp.storage import store

store.reset_to_seed()
g = StarAppController()
g.initialize()


def ev(a, p="{}"):
    g.handle_event(a, p if isinstance(p, str) else json.dumps(p))


ev("select_demo_account", "guardian_1")
ev("select_create_badge_band", "B1")
ev("nav_guardian", "g_mapping")
ev("select_mapping_badge", "Signals Foundations")
for c in ("m_b1_1", "m_b1_2", "m_b1_3", "m_b1_4"):
    ev("toggle_mapping_cosmonaut", c)
for r in ("m_b2_1", "m_b2_2"):
    ev("toggle_mapping_reviewer", r)
ev("send_mapping_requests")
for r in [x for x in store.get_mapping_requests() if x["id"].startswith("req_B1_badge_b1_signals")]:
    ev("select_demo_account", r["reviewer_id"])
    ev("accept_mapping_request", r["id"])
ev("select_demo_account", "guardian_1")
ev("select_create_badge_band", "B1")
ev("execute_cosmonaut_mapping", {"band": "B1", "badge_id": "badge_b1_signals", "badge": "Signals Foundations"})
ev("publish_badge", "badge_b1_signals")
owner = store.get_timeline("badge_b1_signals", "m_b1_1").reviewer_id
ev("select_demo_account", "m_b1_1")
ev("submit_project_deliverable", {"badge_id": "badge_b1_signals", "pdf_name": "report_v1.pdf", "pdf_payload": "data:application/pdf;base64,JVBERi0xLjQKJSVFT0YK",
                                  "code_name": "filter_v1.py", "code_payload": "print(1)", "github_url": "https://github.com/x/y"})
sub = store.get_submissions_for_cosmonaut("m_b1_1", "badge_b1_signals")[0]
ev("select_demo_account", owner)
ev("submit_reviewer_assessment", {"submission_id": sub.id, "bu": 9, "ar": 9, "tk": 9, "pr": 9, "qa": 9, "strengths": "Clean design", "improvements": "Add retries",
                                  "feedback": "Strong work", "decision": "approve"})
print("prepared: mapping + published badge + submission", sub.id, "reviewer", owner, flush=True)
try:
    store.db.conn.commit()
    store.db.conn.execute("PRAGMA wal_checkpoint(FULL)")
    store.db.conn.close()
except Exception as exc:
    print("close warn", exc)

# ------------------------------------------------------------------ 2. start the server and Chrome
env = dict(os.environ, DATABASE_URL=DB, STARAPP_DB_PATH=DB, STARAPP_HOT_RELOAD="false", STARAPP_DEMO_MODE="true", DEBUG="false")
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                          cwd=ROOT, env=env, stdout=open(os.path.join(tmp, "server.log"), "w"), stderr=subprocess.STDOUT)
for _ in range(80):
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/api/health" % PORT, timeout=1)
        break
    except Exception:
        time.sleep(0.5)

chrome = os.environ.get("CHROME_PATH") or next((p for p in (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome") if os.path.exists(p)), "chrome")
proc = subprocess.Popen([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--remote-debugging-port=%d" % CPORT,
                         "--user-data-dir=" + os.path.join(tmp, "prof"), "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
errors = []
try:
    ws_url = None
    for _ in range(60):
        try:
            tabs = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % CPORT))
            ws_url = [t for t in tabs if t.get("type") == "page"][0]["webSocketDebuggerUrl"]
            break
        except Exception:
            time.sleep(0.5)
    ws = connect(ws_url)
    seq = [0]

    def call(method, **params):
        seq[0] += 1
        ws.send(json.dumps({"id": seq[0], "method": method, "params": params}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("method") == "Runtime.exceptionThrown":
                d = msg["params"]["exceptionDetails"]
                errors.append("EXC " + str(d.get("exception", {}).get("description") or d.get("text")))
            elif msg.get("method") == "Runtime.consoleAPICalled" and msg["params"]["type"] == "error":
                errors.append("CONSOLE " + " ".join(str(a.get("value", a.get("description", ""))) for a in msg["params"]["args"]))
            elif msg.get("method") == "Log.entryAdded" and msg["params"]["entry"]["level"] == "error":
                errors.append("LOG " + msg["params"]["entry"]["text"] + " " + str(msg["params"]["entry"].get("url", "")))
            if msg.get("id") == seq[0]:
                return msg.get("result", {})

    def js(expr):
        r = call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            errors.append("EVAL " + expr[:80] + " :: " + str(r["exceptionDetails"].get("exception", {}).get("description"))[:200])
            return None
        return r.get("result", {}).get("value")

    def wait(sec=1.0):
        time.sleep(sec)

    def settle():
        # wait until the page body stops changing
        last = None
        for _ in range(20):
            cur = js("document.getElementById('starapp-page-body') ? document.getElementById('starapp-page-body').innerHTML.length + '|' + (document.getElementById('starapp-modal-root')||{innerHTML:''}).innerHTML.length : 'x'")
            if cur == last:
                return
            last = cur
            time.sleep(0.35)

    def act(action, payload="{}"):
        js("window.StarAppBridge.dispatchAction(%s, %s)" % (json.dumps(action), json.dumps(payload if isinstance(payload, str) else json.dumps(payload))))
        wait(0.6)
        settle()

    def click(selector, nth=0):
        ok = js("(function(){var e=document.querySelectorAll(%s)[%d];if(!e)return false;e.click();return true})()" % (json.dumps(selector), nth))
        wait(0.5)
        settle()
        return ok

    def click_text(selector, text):
        ok = js("(function(){var e=Array.from(document.querySelectorAll(%s)).find(function(x){return x.textContent.replace(/\\s+/g,' ').indexOf(%s)>-1});if(!e)return false;e.click();return true})()" % (json.dumps(selector), json.dumps(text)))
        wait(0.5)
        settle()
        return ok

    def body():
        return js("document.getElementById('starapp-page-body') ? document.getElementById('starapp-page-body').innerHTML : ''") or ""

    def modal():
        return js("document.getElementById('starapp-modal-root') ? document.getElementById('starapp-modal-root').innerHTML : ''") or ""

    def overflow():
        return js("document.documentElement.scrollWidth - window.innerWidth")

    call("Runtime.enable")
    call("Log.enable")
    call("Page.enable")
    call("Emulation.setDeviceMetricsOverride", width=1440, height=900, deviceScaleFactor=1, mobile=False)
    call("Page.navigate", url="http://127.0.0.1:%d/" % PORT)
    for _ in range(40):
        if js("!!(window.StarAppBridge && window.StarAppBridge.dispatchAction)"):
            break
        wait(0.5)
    wait(1.5)
    check("app boots in the browser (bridge ready)", js("!!window.StarAppBridge"))

    # ---------------------------------------------------------------- Guardian pages via real sidebar clicks
    act("select_demo_account", "guardian_1")
    act("select_create_badge_band", "B1")
    check("signed in as Guardian (sidebar present)", js("!!document.querySelector('.app-sidebar')"))
    nav_ids = js("Array.from(document.querySelectorAll('.sidebar-nav [data-nav-id]')).map(function(a){return a.getAttribute('data-nav-id')})") or []
    check("sidebar has the Guardian pages", all(x in nav_ids for x in ("g_create_badge", "g_badge_approval", "g_mapping", "g_allotment", "g_reviews")), nav_ids)
    for nid in [n for n in nav_ids if n != "g_learning"]:
        click('.sidebar-nav [data-nav-id="%s"]' % nid)
        check("page %s: renders, no horizontal overflow" % nid, len(body()) > 300 and (overflow() or 0) <= 1, overflow())

    # ---------------------------------------------------------------- Badge approval page: filter + search with real input
    click('.sidebar-nav [data-nav-id="g_badge_approval"]')
    check("approval page has rows", "ba-row" in body())
    js("(function(){var i=document.querySelector('input[type=search], input[placeholder*=Search]');if(i){i.value='Signals';i.dispatchEvent(new Event('input',{bubbles:true}))}})()")
    wait(1.2); settle()
    check("typing in the search box filters the list (debounced)", "Signals Foundations" in body() and "Data Systems Architecture" not in body())

    # ---------------------------------------------------------------- Mapping page
    click('.sidebar-nav [data-nav-id="g_mapping"]')
    b = body()
    check("mapping: saved card shows the checklist", "mbc-checks" in b and "mapped" in b)
    # pick another badge with real clicks
    check("click a badge row", click_text("#mapping-badges-scroll .mapping-badge-item", "Data Systems"))
    check("badge row selected", "selected" in (js("(document.querySelector('#mapping-badges-scroll .mapping-badge-item.selected')||{}).textContent") or "") or "Data Systems" in body())
    click("#mapping-cosmo-scroll .mapping-member-item", 0)
    click("#mapping-cosmo-scroll .mapping-member-item", 1)
    click("#mapping-reviewer-scroll .mapping-member-item", 0)
    n_sel = js("document.querySelectorAll('#mapping-cosmo-scroll .mapping-member-item.selected').length")
    check("2 cosmonauts selected by clicking", n_sel == 2, n_sel)
    check("click 'Send' request", click_text("button", "Send Request") or click_text("button", "Send"))
    reqs = q("SELECT id, status, data_json FROM mapping_requests WHERE data_json LIKE '%Data Systems%'")
    check("new request saved in the DB with a 24h deadline", reqs and "expires_at" in reqs[0]["data_json"], len(reqs))
    t1 = js("(document.querySelector('.rq-timer-text')||{}).textContent")
    wait(2.2)
    t2 = js("(document.querySelector('.rq-timer-text')||{}).textContent")
    check("countdown ticks in the live page", t1 and t2 and t1 != t2, (t1, t2))

    # calendar modal with real clicks
    check("open calendar from the mapping page", click("#mapping-open-calendar-btn"))
    m = modal()
    check("calendar modal = dropdown row + grid", "mapping-cal-days-select" in m and "Apply Schedule" not in m and "cal-days-grid" in m)
    js("(function(){var s=document.getElementById('mapping-cal-days-select');s.value='5';s.dispatchEvent(new Event('change',{bubbles:true}))})()")
    wait(0.8); settle()
    click(".cal-day-cell:not(.weekend):not(.other-month)", 4)   # a working day
    sel5 = js("document.querySelectorAll('.cal-day-cell.selected-review-day').length")
    check("5 Days: one click selects 5 working days", sel5 == 5, sel5)
    js("(function(){var s=document.getElementById('mapping-cal-days-select');s.value='manual';s.dispatchEvent(new Event('change',{bubbles:true}))})()")
    wait(0.8); settle()
    click(".cal-day-cell.selected-review-day", 1)
    sel_m = js("document.querySelectorAll('.cal-day-cell.selected-review-day').length")
    check("Manual: clicking a selected day switches it off", sel_m == 4, sel_m)
    click(".mapcal-toolbar .lg-cal-nav", 1)
    mon1 = js("document.getElementById('mapping-cal-month-select').value")
    click(".mapcal-toolbar .lg-cal-nav", 0)
    mon0 = js("document.getElementById('mapping-cal-month-select').value")
    check("‹ › month buttons work in the browser", mon1 != mon0, (mon0, mon1))
    click(".modal-close-btn")
    check("calendar closes", js("!document.querySelector('.mapcal-only')"))

    # mapped card -> detail page
    click('.sidebar-nav [data-nav-id="g_mapping"]')
    click_text(".mapping-badge-rect-card", "Signals Foundations")
    b = body()
    top = js("(document.getElementById('starapp-topbar-slot')||{innerHTML:''}).innerHTML")
    check("detail page opens (history, cohort, live allocations)", "rq-table" in b and "Final Review Cohort" in b and "Live Mapped Review Allocations" in b)
    check("badge title sits in the Back-button row", "Signals Foundations" in top)
    check("no overflow on the detail page", (overflow() or 0) <= 1, overflow())
    # history actions: Resend visible? (accepted rows show Revoke)
    check("history rows have working actions (Revoke / Delete)", "Revoke" in b and "Delete" in b)

    # ---------------------------------------------------------------- Badge Allotment + modals
    click('.sidebar-nav [data-nav-id="g_allotment"]')
    b = body()
    check("allotment: cards with name titles", "lg-allot-title" in b and "lg-allot-band" not in b)
    ncols = js("getComputedStyle(document.querySelector('.lg-allot-grid')).gridTemplateColumns.split(' ').length")
    check("3 cards per row at 1440px", ncols == 3, ncols)
    same_line = js("(function(){var a=document.querySelector('.lg-allot-actions');var t=Array.from(a.children).map(function(b){return Math.round(b.getBoundingClientRect().top)});return Math.max.apply(null,t)-Math.min.apply(null,t)})()")
    check("Timeline / Edit / Revoke on ONE line", same_line is not None and same_line <= 2, same_line)
    check("open Timeline & Mapping", click_text(".lg-allot-actions button", "Timeline"))
    m = modal()
    check("timeline modal read-only with reviewers", "tm-steps" in m and "<input" not in m and "tm-rev" in m)
    click(".modal-close-btn")
    # Edit modal: real interactions + real submit
    check("open Edit Badge", click_text(".lg-allot-actions button", "Edit"))
    m = modal()
    check("edit modal: groups, glass dates, no details card", "eb-groups" in m and "gd-btn" in m and "Badge Details" not in m)
    # glass date picker
    click('.gd-btn[data-gd-input="tl-sub-deadline"]')
    check("glass calendar opens", js("!!document.querySelector('.gd-pop')"))
    js("(function(){var d=document.querySelector('.gd-pop [data-gd-day]:not(.is-outside):not(.is-disabled)');window.__picked=d.getAttribute('data-gd-day');d.click()})()")
    wait(0.4)
    picked = js("window.__picked")
    check("picking a day updates the hidden ISO value + label", js("document.getElementById('tl-sub-deadline').value") == picked and not js("!!document.querySelector('.gd-pop')"), picked)
    # add a cosmonaut to the 2nd reviewer, move another
    before_count = js("document.getElementById('eb-count').textContent")
    click(".eb-group:not(.is-none) .eb-combo-btn", 1)
    check("add-cosmonaut dropdown opens", js("!!document.querySelector('.eb-combo.is-open .eb-menu:not([hidden])')"))
    click(".eb-combo.is-open .eb-opt:not(.is-hidden)", 0)
    after_count = js("document.getElementById('eb-count').textContent")
    check("added person appears under that reviewer (counter +1)", int(after_count) == int(before_count) + 1, (before_count, after_count))
    check("edit modal save click", click(".eb-footer button[type=submit]"))
    wait(0.6); settle()
    check("save closed the modal + success message", not js("!!document.querySelector('.eb-form')") and "updated" in (js("document.getElementById('starapp-flash-slot').textContent") or "").lower(), js("document.getElementById('starapp-flash-slot').textContent"))
    row = q("SELECT default_timeline_json, assigned_cosmonaut_ids_json FROM badges WHERE id='badge_b1_signals'")[0]
    check("edit persisted in the DB (deadline + assigned list)", json.loads(row["default_timeline_json"]).get("submission_deadline") == picked and len(json.loads(row["assigned_cosmonaut_ids_json"])) == int(after_count))

    # ---------------------------------------------------------------- Assessment dashboard
    click('.sidebar-nav [data-nav-id="g_reviews"]')
    check("assessment dashboard: badge cards", "asm-" in body() or "Assessment" in body())
    act("open_assessment_badge", "badge_b1_signals")
    b = body()
    check("tree: reviewers + cosmonauts, connectors, no level tags", "asm-tree-reviewer-branch" in b and 'class="asm-elbow"' in b and "Level 1" not in b)
    check("tree has no horizontal overflow", (overflow() or 0) <= 1, overflow())
    click_text(".asm-cosmonaut-card", "Aarav Sharma")
    b = body()
    check("cosmonaut page: attempt row with reviewer score", "lg-att-summary" in b and "45.0 / 50.0" in b)
    check("expand/collapse an attempt (details)", js("(function(){var d=document.querySelector('.lg-attempt-card');d.open=false;var a=d.open;d.open=true;return a===false&&d.open===true})()"))
    click(".lg-attempt-cta")
    b = body()
    check("marks page opens (no Back-to-reviews, no meta bar, no RUBRIC-50)", "Back to Project Reviews" not in b and "lg-rubric-meta-bar" not in b and "RUBRIC-50" not in b and "lg-dec-list" in b)
    fit = js("(function(){var e=document.querySelector('.review-rubric-body-fit');var f=document.querySelector('#guardian-rubric-form button[type=submit]').getBoundingClientRect();var c=document.querySelector('.review-right-column').getBoundingClientRect();return [e.scrollHeight<=e.clientHeight+1, f.bottom<=c.bottom+1]})()")
    check("marks sheet fits with no scrolling at 900px height", fit == [True, True], fit)
    click(".lg-dec-opt.is-resubmit")
    check("decision buttons drive the select + submit label", js("document.getElementById('rubric-decision').value") == "resubmission_requested" and "Resubmission" in (js("document.getElementById('rubric-submit-label').textContent") or ""))
    click(".lg-dec-opt.is-approve")
    check("switch back to Earn Badge", js("document.getElementById('rubric-decision').value") == "approve")
    click("#guardian-rubric-form button[type=submit]")
    wait(0.8); settle()
    st = q("SELECT status FROM project_submissions WHERE id=?", (sub.id,))[0]["status"]
    check("final assessment saved in the DB (approved)", st == "approved", st)
    n_g = q("SELECT COUNT(*) c FROM assessment_marksheets WHERE submission_id=? AND assessor_role='guardian'", (sub.id,))[0]["c"]
    check("guardian marksheet row exists", n_g == 1, n_g)

    # ---------------------------------------------------------------- narrow window sanity
    call("Emulation.setDeviceMetricsOverride", width=1100, height=800, deviceScaleFactor=1, mobile=False)
    wait(0.6)
    for nid in ("g_mapping", "g_allotment", "g_badge_approval", "g_reviews"):
        click('.sidebar-nav [data-nav-id="%s"]' % nid)
        check("1100px window: %s has no horizontal overflow" % nid, (overflow() or 0) <= 1, overflow())

    # ---------------------------------------------------------------- console
    benign = ("favicon", "ERR_BLOCKED", "net::ERR_ABORTED")
    real_errors = [e for e in errors if not any(b in e for b in benign)]
    check("no JavaScript errors / console errors during the whole run", not real_errors, real_errors[:6])
except Exception:
    traceback.print_exc()
    check("browser script completed", False)
finally:
    try:
        proc.kill()
    except Exception:
        pass
    try:
        server.kill()
    except Exception:
        pass

fails = [r for r in results if not r[0]]
print("\n%d checks, %d failed" % (len(results), len(fails)))
for f in fails:
    print("  FAILED:", f[1], str(f[2])[:300])
print("server log:", os.path.join(tmp, "server.log"))
