"""A brand-new REAL user (no seed, no history) must get a working app: every parameterless GET answers without a
server error. The seeded demo hid crashes on this path (2026-10-19: /twin and /twin/mirror)."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_endpoint_works_for_a_new_real_profile():
    d = tempfile.mkdtemp()
    old, new = os.path.join(d, "old.db"), os.path.join(d, "new.db")
    env = {**os.environ, "TELOMY_TODAY": "2026-10-19"}
    env.pop("TELOMY_ACCESS_PASSWORD", None)
    subprocess.run([sys.executable, "-c", "from app import seed; seed.run(reset=True)"], cwd=ROOT, env={**env, "TELOMY_DB": old}, check=True, capture_output=True)
    subprocess.run([sys.executable, "-m", "tools.make_real_db", old], cwd=ROOT, env={**env, "TELOMY_DB": new}, check=True, capture_output=True)
    code = """
from fastapi.testclient import TestClient
from app.main import app
skip = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect", "/static/telomy_anatomy.glb", "/whoop/push"}
paths = [r.path for r in app.routes if "GET" in getattr(r, "methods", set()) and "{" not in r.path and r.path not in skip]
with TestClient(app) as c:
    assert c.get("/profile").json()["is_test_profile"] is False
    bad = [p for p in paths if c.get(p).status_code >= 500]
print("BAD", bad)
assert not bad, bad
"""
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env={**env, "TELOMY_DB": new}, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-1500:]
