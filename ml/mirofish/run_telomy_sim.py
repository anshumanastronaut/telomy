"""Drive MiroFish-Offline end to end for the Telomy market test (local Ollama qwen2.5:7b + Neo4j).
Steps: ontology (brief + panel) → graph build → create simulation → prepare (agent profiles) → start → report.
Writes progress to sim_log.txt and the final report to telomy_sim_report.md."""
import json, time, urllib.request, uuid, os

API = "http://localhost:5001/api"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = open(os.path.join(HERE, "sim_log.txt"), "a")
def log(*a):
    msg = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(msg, flush=True); LOG.write(msg + "\n"); LOG.flush()

def req(method, path, body=None, timeout=600):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))

def multipart(path, fields, files):
    b = uuid.uuid4().hex; parts = []
    for k, v in fields.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for name in files:
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="files"; filename="{os.path.basename(name)}"\r\nContent-Type: text/markdown\r\n\r\n'.encode()
                     + open(name, "rb").read() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    r = urllib.request.Request(API + path, data=b"".join(parts), method="POST", headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.load(urllib.request.urlopen(r, timeout=3600))

def wait_task(task_id, what):
    while True:
        t = req("GET", f"/graph/task/{task_id}").get("data", {})
        log(what, t.get("status"), t.get("progress"), (t.get("message") or "")[:120])
        if t.get("status") in ("completed", "failed"): return t
        time.sleep(30)

REQ = ("Simulate how a cross-section of Indian adults (the people in the market panel) react on social media to the launch of "
       "Telomy as described in the brief: who would pay and for which plan, which features matter most, what stops them "
       "(price, privacy, trust in AI, wearing a chest band, iPhone-only) and how they compare it with Ultrahuman, WHOOP, Oura, "
       "Apple Watch, HealthifyMe and Tata 1mg. Agents are fictional and must stay consistent with their persona.")

o = multipart("/graph/ontology/generate", {"simulation_requirement": REQ, "project_name": "Telomy market test"},
              [os.path.join(HERE, "telomy_brief.md"), os.path.join(HERE, "telomy_panel.md")])
log("ontology", o.get("success"), str(o)[:300])
pid = o["data"]["project_id"]
b = req("POST", "/graph/build", {"project_id": pid, "graph_name": "Telomy market test"})
log("build", str(b)[:200])
t = wait_task(b["data"]["task_id"], "graph")
proj = req("GET", f"/graph/project/{pid}")["data"]; gid = proj.get("graph_id"); log("graph id", gid)
s = req("POST", "/simulation/create", {"project_id": pid, "graph_id": gid, "enable_twitter": True, "enable_reddit": True})
sid = s["data"]["simulation_id"]; log("simulation", sid)
p = req("POST", "/simulation/prepare", {"simulation_id": sid, "use_llm_for_profiles": True, "parallel_profile_count": 4})
log("prepare", str(p)[:200])
while True:
    st = req("POST", "/simulation/prepare/status", {"simulation_id": sid, "task_id": (p.get("data") or {}).get("task_id")}).get("data", {})
    log("prepare", st.get("status"), st.get("progress"), (st.get("message") or "")[:120])
    if st.get("status") in ("completed", "ready", "failed") or st.get("already_prepared"): break
    time.sleep(30)
r = req("POST", "/simulation/start", {"simulation_id": sid, "platform": "parallel", "max_rounds": 24})
log("start", str(r)[:200])
while True:
    rs = req("GET", f"/simulation/{sid}/run-status").get("data", {})
    log("run", rs.get("runner_status") or rs.get("status"), rs.get("current_round"), "/", rs.get("total_rounds"))
    if (rs.get("runner_status") or rs.get("status")) in ("completed", "stopped", "failed"): break
    time.sleep(60)
g = req("POST", "/report/generate", {"simulation_id": sid})
log("report", str(g)[:200])
rid = (g.get("data") or {}).get("report_id")
while True:
    gs = req("POST", "/report/generate/status", {"simulation_id": sid, "task_id": (g.get("data") or {}).get("task_id")}).get("data", {})
    log("report", gs.get("status"), gs.get("progress"))
    if gs.get("status") in ("completed", "failed"): rid = gs.get("report_id") or rid; break
    time.sleep(30)
rep = req("GET", f"/report/by-simulation/{sid}").get("data", {})
open(os.path.join(HERE, "telomy_sim_report.md"), "w").write(rep.get("markdown_content") or json.dumps(rep, indent=2))
log("DONE report saved", rid)
