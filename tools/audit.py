"""Telomy end-to-end audit.

1. Wiring  — every API path the mobile app calls (api('/…'), useApi('/…')) must match a backend route.
2. Engines — every parameter-free GET route on a running server is called: status, latency, empty / "ok": false.
Usage: backend/.venv/bin/python tools/audit.py [BASE_URL] [TOKEN_FILE]
Prints a table; exits 1 if anything is broken. Never prints response bodies (they hold personal health data).
"""
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("TELOMY_DB", "/tmp/telomy-audit.db")
from app.main import app  # noqa: E402

routes = [(m, r.path) for r in app.routes if hasattr(r, "methods") for m in r.methods if m in ("GET", "POST", "PUT", "DELETE")]


def to_re(path):
    return re.compile("^" + re.sub(r"\{[^}]+\}", r"[^/]+", path) + "$")


RX = [(m, p, to_re(p)) for m, p in routes]

# ---------------------------------------------------------------- 1. wiring
calls = set()
for d, _, fs in os.walk(os.path.join(ROOT, "mobile", "src")):
    for f in fs:
        if f.endswith((".ts", ".tsx")):
            src = open(os.path.join(d, f)).read()
            for m in re.finditer(r"(?:api|useApi)(?:<[^>]*>)?\(\s*[`'\"](/[^`'\"?]*)", src):
                path = re.sub(r"\$\{[^}]+\}", "X", m.group(1)).rstrip("/") or "/"
                calls.add((path, os.path.relpath(os.path.join(d, f), ROOT)))
missing = [(p, f) for p, f in sorted(calls) if not any(rx.match(p) for _, _, rx in RX)]
print(f"WIRING: {len(calls)} app→server calls, {len(missing)} with no backend route")
for p, f in missing:
    print(f"  MISSING  {p:45s} {f}")

# ---------------------------------------------------------------- 2. engines
base = sys.argv[1] if len(sys.argv) > 1 else None
bad = list(missing)
if base:
    tok = open(os.path.expanduser(sys.argv[2])).read().strip() if len(sys.argv) > 2 else ""
    gets = sorted({p for m, p in routes if m == "GET" and "{" not in p and not p.startswith(("/nightscout", "/docs", "/openapi", "/redoc"))})
    print(f"\nENGINES: {len(gets)} GET routes on {base}")
    for p in gets:
        t0 = time.time()
        req = urllib.request.Request(base + p, headers={"Authorization": f"Bearer {tok}"} if tok else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read(); code = r.status
        except urllib.error.HTTPError as e:
            body, code = e.read(), e.code
        except Exception as e:  # noqa: BLE001
            body, code = str(e).encode(), 0
        ms = (time.time() - t0) * 1000
        note = ""
        try:
            j = json.loads(body)
            if isinstance(j, dict) and j.get("ok") is False:
                note = "ok:false — " + str(j.get("reason") or j.get("missing") or "")[:70]
            elif j in ([], {}, None):
                note = "empty"
        except Exception:  # noqa: BLE001
            note = "non-JSON" if "json" not in p else ""
        flag = "FAIL" if code >= 500 or code == 0 else "WARN" if code >= 400 or note or ms > 5000 else "ok"
        if flag != "ok":
            bad.append((p, flag))
        print(f"  {flag:4s} {code:3d} {ms:7.0f} ms  {p:42s} {note}")
print(f"\n{len(bad)} items to look at")
sys.exit(1 if any(f == "FAIL" for _, f in bad) or missing else 0)
