"""Telomy calibration workbench (local dev tool, this branch only).

A live dashboard to calibrate WHOOP/ring/patch raw signals against reference instruments:
  • pulls + decodes WHOOP raw from the cloud (HRV from R-R, SpO2 red/IR ratio, thermistor, IMU)
  • you feed reference readings by hand (fingertip oximeter SpO2, thermometer C, ECG-patch HRV)
  • it fits the calibration curves (SpO2 = c0 - c1*ratio, degC = a*raw + b, HRV factor) and plots them

Run:  cd research/calibration && uvicorn app:app --port 8799   (then open http://127.0.0.1:8799)
Needs the Oracle ssh key at ~/.ssh/telomy-oracle.key. Readings persist to readings.json (git-ignored).
"""
from __future__ import annotations
import json, os, subprocess, time
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

HERE = Path(__file__).parent
READINGS = HERE / "readings.json"
SSH = ["ssh", "-i", os.path.expanduser("~/.ssh/telomy-oracle.key"), "-o", "ConnectTimeout=15", "opc@129.225.98.159"]
REMOTE_PY = (HERE / "remote_decode.py").read_text()

app = FastAPI(title="Telomy calibration workbench")


def _load():
    try:
        return json.loads(READINGS.read_text())
    except Exception:
        return []


def _save(rs):
    READINGS.write_text(json.dumps(rs, indent=2))


def _linfit(xs, ys):
    """Least-squares y = m*x + b with R²."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    m = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / sxx
    b = my - m * mx
    ss_tot = sum((y - my) ** 2 for y in ys) or 1e-9
    ss_res = sum((ys[i] - (m * xs[i] + b)) ** 2 for i in range(n))
    return {"m": m, "b": b, "r2": 1 - ss_res / ss_tot, "n": n}


@app.get("/api/decode")
def decode():
    """Pull + decode the current WHOOP raw from the cloud."""
    try:
        r = subprocess.run(SSH + ["cd /opt/telomy && TELOMY_DATA_DIR=/opt/telomy/data_local .venv/bin/python -I -"],
                           input=REMOTE_PY, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return JSONResponse({"error": r.stderr[-500:] or "ssh failed"}, status_code=502)
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)


class Reading(BaseModel):
    metric: str          # 'spo2' | 'temp' | 'hrv'
    device: float        # the device/raw value (WHOOP ratio, thermistor raw, WHOOP RMSSD)
    reference: float     # the reference instrument reading (oximeter %, thermometer C, ECG RMSSD)
    note: str | None = None


@app.get("/api/readings")
def get_readings():
    return _load()


@app.post("/api/readings")
def add_reading(r: Reading):
    rs = _load()
    rs.append({**r.model_dump(), "ts": int(time.time())})
    _save(rs)
    return {"ok": True, "count": len(rs)}


@app.post("/api/readings/clear")
def clear(metric: str | None = None):
    rs = [x for x in _load() if metric and x["metric"] != metric] if metric else []
    _save(rs)
    return {"ok": True, "count": len(rs)}


@app.get("/api/fit")
def fit():
    rs = _load()
    out = {}
    for metric in ("spo2", "temp", "hrv"):
        pts = [(x["device"], x["reference"]) for x in rs if x["metric"] == metric]
        f = _linfit([p[0] for p in pts], [p[1] for p in pts]) if len(pts) >= 2 else None
        out[metric] = {"points": pts, "fit": f}
    return out


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return (HERE / "dashboard.html").read_text()
