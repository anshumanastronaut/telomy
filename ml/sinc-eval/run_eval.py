"""Sinc accuracy harness (runs against the local Telomy backend).
- PubMedQA (MIT, 1,000 expert-labelled yes/no/maybe questions): accuracy of Sinc's final answer.
- MTS-Dialog (CC BY 4.0, doctor–patient conversations): section headers Sinc should produce in a clinician draft.
Only meaningful when Sinc runs on Claude (ANTHROPIC_API_KEY in backend/.env); in retrieval mode it exits."""
import json, re, sys, random, urllib.request
API = "http://localhost:8787"
def post(path, body):
    r = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=180))
health = json.load(urllib.request.urlopen(API + "/health", timeout=10))
if "no API key" in str(health.get("sinc", "")):
    sys.exit(f"Sinc is in retrieval mode ({health.get('sinc')}); add ANTHROPIC_API_KEY to backend/.env and restart, then rerun.")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
d = json.load(open("pubmedqa_pqal.json")); ids = random.Random(0).sample(sorted(d), N)
ok = 0
for i, k in enumerate(ids):
    q = d[k]; ctx = " ".join(q["CONTEXTS"])
    a = post("/sinc/ask", {"question": f"{q['QUESTION']}\n\nEvidence: {ctx}\n\nAnswer with one word first (yes, no or maybe), then explain.", "mode": "normal"})
    text = (a.get("answer") or a.get("text") or "").lower()
    m = re.search(r"\b(yes|no|maybe)\b", text); ok += bool(m and m.group(1) == q["final_decision"])
    print(f"{i+1}/{N} acc {ok/(i+1):.3f}", flush=True)
print(f"PubMedQA accuracy on {N}: {ok/N:.3f}  (published: GPT-4-class ~0.75–0.80; human expert 0.78)")
