"""
Run:  python scripts/e2e_mobile_layout.py   (needs Google Chrome; env SW / SH = viewport, default 390 x 844)

Phone-layout sweep: live server on a throw-away DB copy + headless Chrome in MOBILE emulation. Visits every sidebar page of the Guardian,
Cosmonaut and Reviewer portals plus the project / reviewer-assessment / Guardian-review pages, reports horizontal overflow and
elements sticking out of the viewport, opens the hamburger drawer (closes on page tap / backdrop) and saves screenshots to a temp folder.
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
ev("request_project", "badge_b1_signals")
ev("select_demo_account", owner)
ev("send_reviewer_project", {"badge_id": "badge_b1_signals", "title": "Signals filter challenge", "content": "Case Study\nA telemetry stream.\n\nYour Challenge\nDesign a filter.", "cosmonaut_ids": ["m_b1_1"]})
ev("select_demo_account", "m_b1_1")
ev("submit_project_deliverable", {"badge_id": "badge_b1_signals", "pdf_name": "report_v1.pdf", "pdf_payload": "data:application/pdf;base64,JVBERi0xLjQKJSVFT0YK",
                                  "code_name": "filter_v1.py", "code_payload": "print(1)", "github_url": "https://github.com/x/y"})
sub = store.get_submissions_for_cosmonaut("m_b1_1", "badge_b1_signals")[0]
store_sub_id = sub.id
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
    import base64
    SCR_DIR = os.path.join(tmp, "shots")
    os.makedirs(SCR_DIR, exist_ok=True)
    W = int(os.environ.get("SW", "390"))
    H = int(os.environ.get("SH", "844"))
    TAG = os.environ.get("STAG", "m")
    call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=True)
    call("Page.navigate", url="http://127.0.0.1:%d/" % PORT)
    for _ in range(40):
        if js("!!(window.StarAppBridge && window.StarAppBridge.dispatchAction)"):
            break
        wait(0.5)
    wait(1.5)

    def shot(name, full=False):
        params = dict(format="png")
        if full:
            h = js("Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)") or H
            call("Emulation.setDeviceMetricsOverride", width=W, height=min(int(h), 3000), deviceScaleFactor=1, mobile=True)
            time.sleep(0.3)
        res = call("Page.captureScreenshot", **params)
        open(os.path.join(SCR_DIR, "mob_%s_%s.png" % (TAG, name)), "wb").write(base64.b64decode(res["data"]))
        if full:
            call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=True)

    MEASURE = """(function(){
      var vw=window.innerWidth, out={ov:document.documentElement.scrollWidth-vw, wide:[]};
      var all=document.querySelectorAll('#starapp-page-body *, .app-sidebar *');
      for(var i=0;i<all.length&&out.wide.length<6;i++){
        var e=all[i], r=e.getBoundingClientRect();
        if(r.width===0||r.height===0) continue;
        var cs=getComputedStyle(e); if(cs.position==='fixed'||cs.visibility==='hidden') continue;
        if(r.right>vw+1 || r.left<-1){
          var p=e.parentElement, scrolls=false;
          while(p&&p!==document.body){var ps=getComputedStyle(p); if(/(auto|scroll|hidden)/.test(ps.overflowX)&&p.getBoundingClientRect().right<=vw+1){scrolls=true;break;} p=p.parentElement;}
          if(!scrolls) out.wide.push((e.tagName+'.'+(e.className&&e.className.baseVal===undefined?String(e.className).split(' ')[0]:''))+' '+Math.round(r.left)+'-'+Math.round(r.right));
        }
      }
      var sb=document.querySelector('.app-sidebar'), sr=sb?sb.getBoundingClientRect():null;
      out.sb=sr?[Math.round(sr.top),Math.round(sr.height),Math.round(sr.width)]:null;
      var m=document.querySelector('.app-main'); out.main=m?Math.round(m.getBoundingClientRect().width):null;
      out.lastBottom=(function(){var b=document.getElementById('starapp-page-body'); if(!b) return null; var kids=b.querySelectorAll('*'); var mx=0; for(var i=0;i<kids.length;i++){var rr=kids[i].getBoundingClientRect(); if(rr.height>0&&rr.bottom>mx) mx=rr.bottom;} return Math.round(mx+window.scrollY);})();
      out.docH=document.documentElement.scrollHeight;
      return JSON.stringify(out);})()"""

    problems = []

    def sweep(role, nids, prefix):
        for nid in nids:
            ok = click('.app-sidebar [data-nav-id="%s"]' % nid)
            m = json.loads(js(MEASURE) or "{}")
            bad = (m.get("ov", 0) or 0) > 1 or bool(m.get("wide"))
            print(("BAD  " if bad else "ok   ") + "%s %-22s ov=%s sb=%s main=%s docH=%s %s" % (role, nid, m.get("ov"), m.get("sb"), m.get("main"), m.get("docH"), m.get("wide") or ""), flush=True)
            if bad:
                problems.append((role, nid, m))
            shot("%s_%s" % (prefix, nid))

    owner = "m_b2_1"
    act("select_demo_account", "guardian_1")
    act("select_create_badge_band", "B1")
    wait(0.5)
    shot("g_home")
    gnav = js("Array.from(document.querySelectorAll('.app-sidebar [data-nav-id]')).map(function(a){return a.getAttribute('data-nav-id')})") or []
    print("guardian nav:", gnav, flush=True)
    sweep("guardian", gnav, "g")
    act("select_demo_account", "m_b1_1")
    wait(0.5)
    cnav = js("Array.from(document.querySelectorAll('.app-sidebar [data-nav-id]')).map(function(a){return a.getAttribute('data-nav-id')})") or []
    print("cosmonaut nav:", cnav, flush=True)
    sweep("cosmonaut", cnav, "c")
    act("select_demo_account", owner)
    wait(0.5)
    rnav = js("Array.from(document.querySelectorAll('.app-sidebar [data-nav-id]')).map(function(a){return a.getAttribute('data-nav-id')})") or []
    print("reviewer nav:", rnav, flush=True)
    sweep("reviewer", [n for n in rnav if n not in cnav], "r")
    # deep pages
    act("select_demo_account", "m_b1_1")
    act("open_allocated_project_page", "badge_b1_signals")
    m = json.loads(js(MEASURE) or "{}"); print("project page", m.get("ov"), m.get("wide")); shot("c_project")
    act("select_demo_account", owner)
    sub = store_sub_id
    act("open_reviewer_assessment_page", sub)
    m = json.loads(js(MEASURE) or "{}"); print("reviewer assess", m.get("ov"), m.get("wide")); shot("r_assess")
    act("select_demo_account", "guardian_1")
    act("open_submission_review_page", sub)
    m = json.loads(js(MEASURE) or "{}"); print("guardian review", m.get("ov"), m.get("wide")); shot("g_review")
    act("select_demo_account", "m_b1_1")
    click('.app-sidebar [data-nav-id="c_results"]')
    shot("c_marksheet")
    # drawer
    act("select_demo_account", "m_b1_1")
    js("document.getElementById('starapp-menu-btn').click()"); wait(0.5)
    shot("drawer_c")
    print("drawer open:", js("document.body.classList.contains('m-nav-open')"), js("JSON.stringify(document.querySelector('.app-sidebar').getBoundingClientRect())"), flush=True)
    click('.app-sidebar [data-nav-id="c_results"]')
    print("closed after nav:", not js("document.body.classList.contains('m-nav-open')"), flush=True)
    act("select_demo_account", owner)
    js("document.getElementById('starapp-menu-btn').click()"); wait(0.5)
    shot("drawer_r")
    js("document.getElementById('starapp-menu-backdrop').click()"); wait(0.4)
    print("closed by backdrop:", not js("document.body.classList.contains('m-nav-open')"), flush=True)
    act("select_demo_account", "guardian_1"); act("select_create_badge_band", "B1")
    js("document.getElementById('starapp-menu-btn').click()"); wait(0.5)
    shot("drawer_g")
    js("document.getElementById('starapp-menu-btn').click()"); wait(0.4)
    print("\nPROBLEMS:", len(problems))
    for p in problems:
        print("  ", p[0], p[1], p[2].get("ov"), p[2].get("wide"))
    print("JS errors:", errors[:5])

except Exception:
    import traceback; traceback.print_exc()
finally:
    for p_ in (proc, server):
        try: p_.kill()
        except Exception: pass
