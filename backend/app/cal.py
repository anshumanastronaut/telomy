"""Calibration capture backend for the Telomy Recorder iPhone app.

Two jobs:
  • /cal/ingest  — the app streams time-aligned readings (patch, band, ring, WHOOP, reference) on one clock;
                   we store them so the workbench fit code (SpO2=c0−c1·ratio, °C=a·raw+b, HRV factor) can run on
                   real paired data.
  • /cal/whoop_latest — decode the last ~15 min of WHOOP raw already in the Vault into the values the app shows
                   on the same timeline (SpO2 red/IR ratio, skin-temp raw, HRV RMSSD, HR).

Bound to the WHOOP owner's Vault by the caller (TELOMY_WHOOP_USER_ID), same as /whoop/push. Read-mostly.
"""
from __future__ import annotations
import json
import math
import statistics as st
import time as _time

from . import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS cal_readings (
  session_id TEXT, source TEXT, channel TEXT, value REAL, t REAL, wall REAL, note TEXT, ingested REAL
);
CREATE INDEX IF NOT EXISTS cal_readings_sess ON cal_readings (session_id, channel);
"""


def init():
    for stmt in SCHEMA.strip().split(";"):
        if stmt.strip():
            db.exec_(stmt)
    try:                                  # older DBs predate the server-side ingest timestamp
        db.exec_("ALTER TABLE cal_readings ADD COLUMN ingested REAL")
    except Exception:  # noqa: BLE001
        pass


def ingest(session_id: str, readings: list[dict]) -> int:
    init()
    now = _time.time()
    n = 0
    for r in readings:
        try:
            db.exec_(
                "INSERT INTO cal_readings (session_id, source, channel, value, t, wall, note, ingested) VALUES (?,?,?,?,?,?,?,?)",
                (session_id, str(r.get("source")), str(r.get("channel")),
                 float(r.get("value")), float(r.get("t", 0)), float(r.get("wall", 0)), r.get("note"), now),
            )
            n += 1
        except (TypeError, ValueError):
            continue        # skip a malformed reading rather than failing the whole batch
    return n


def status(session_id: str | None = None) -> dict:
    """Live health of the current (or named) capture session: per source.channel count, last value, and age in
    seconds since the server last received a reading (clock-skew-proof — uses the server ingest time)."""
    init()
    now = _time.time()
    if not session_id:
        row = db.one("SELECT session_id FROM cal_readings ORDER BY rowid DESC LIMIT 1")
        session_id = (row or {}).get("session_id")
    if not session_id:
        return {"session_id": None, "now": now, "total": 0, "channels": {}}
    rows = db.rows(
        "SELECT source, channel, COUNT(*) n, "
        "       (SELECT value FROM cal_readings c2 WHERE c2.session_id=c1.session_id AND c2.source=c1.source AND c2.channel=c1.channel ORDER BY rowid DESC LIMIT 1) last_value, "
        "       MAX(ingested) last_ing, MAX(t) last_t "
        "FROM cal_readings c1 WHERE session_id=? GROUP BY source, channel", (session_id,))
    chans = {}
    for r in rows:
        age = (now - r["last_ing"]) if r.get("last_ing") else None
        chans[f'{r["source"]}.{r["channel"]}'] = {
            "source": r["source"], "channel": r["channel"], "n": r["n"],
            "last_value": r["last_value"], "age_sec": round(age, 1) if age is not None else None,
            "session_t": round(r["last_t"], 1) if r.get("last_t") else 0,
        }
    total = db.one("SELECT COUNT(*) c, MIN(ingested) a, MAX(ingested) b FROM cal_readings WHERE session_id=?", (session_id,)) or {}
    return {"session_id": session_id, "now": now, "total": total.get("c", 0),
            "started": total.get("a"), "last": total.get("b"), "channels": chans}


def _win_rows(stream: str, t0: int, t1: int) -> list[dict]:
    return db.rows("SELECT key, data FROM whoop_rows WHERE stream=? AND ts BETWEEN ? AND ? ORDER BY ts", (stream, t0, t1))


def _clean_hrv(recs: list[tuple[int, float]]):
    """WHOOP over-delivers R-R ~2.4x. Collapse beats sharing a second (median), then Malik 20% filter → RMSSD."""
    byts: dict[int, list[float]] = {}
    for t, v in recs:
        if 300 <= v <= 2000:
            byts.setdefault(t, []).append(v)
    onep = [st.median(vs) for _, vs in sorted(byts.items())]
    if len(onep) < 2:
        return None, 0
    filt = [onep[0]]
    for v in onep[1:]:
        if abs(v - filt[-1]) / filt[-1] <= 0.20:
            filt.append(v)
    diffs = [(filt[i + 1] - filt[i]) ** 2 for i in range(len(filt) - 1)]
    return (math.sqrt(sum(diffs) / len(diffs)) if diffs else None), len(filt)


def whoop_latest(window_sec: int = 15 * 60) -> dict:
    """Decode the most recent WHOOP raw into the app's channels. Empty dict-ish if there's nothing recent."""
    init()
    tmaxrow = db.one("SELECT max(ts) AS m FROM whoop_rows WHERE stream='hrSample'")
    tmax = (tmaxrow or {}).get("m") or 0
    if not tmax:
        return {"live": {}, "note": "no WHOOP raw yet"}
    t0, t1 = tmax - window_sec, tmax
    live: dict = {}

    hr = [json.loads(r["data"]).get("bpm") for r in _win_rows("hrSample", t0, t1)]
    hr = [x for x in hr if x]
    if hr:
        live["hr"] = round(st.mean(hr), 1)

    sp = [json.loads(r["data"]) for r in _win_rows("spo2Sample", t0, t1)]
    red = [x["red"] for x in sp if x.get("red")]
    ir = [x["ir"] for x in sp if x.get("ir")]
    if red and ir:
        live["red"] = round(st.mean(red), 1)
        live["ir"] = round(st.mean(ir), 1)
        live["spo2_ratio"] = round(st.mean(red) / st.mean(ir), 4)

    tp = [json.loads(r["data"]).get("raw") for r in _win_rows("skinTempSample", t0, t1)]
    tp = [x for x in tp if x is not None]
    if tp:
        live["temp_raw"] = round(st.mean(tp), 1)

    # IMU (wrist motion) from the gravity vector — for motion correlation + artifact rejection in SpO2/HRV/sleep
    vecs = []
    for r in _win_rows("gravitySample", t0, t1):
        x = json.loads(r["data"])
        if x.get("z") is not None:
            vecs.append((x.get("x", 0.0), x.get("y", 0.0), x["z"]))
    if vecs:
        mags = [math.sqrt(a * a + b * b + c * c) for a, b, c in vecs]
        zang = [math.degrees(math.atan2(c, math.sqrt(a * a + b * b))) for a, b, c in vecs]
        motion = [abs(mags[i + 1] - mags[i]) for i in range(len(mags) - 1)]
        live["g_mag"] = round(st.mean(mags), 3)
        live["z_angle"] = round(st.mean(zang), 1)
        live["motion_mg"] = round(st.mean(motion) * 1000, 1) if motion else 0.0

    rr = []
    for r in _win_rows("rrInterval", t0, t1):
        try:
            k = json.loads(r["key"])
            rr.append((int(k["ts"]), float(k["rrMs"])))
        except (KeyError, ValueError, TypeError):
            continue
    rmssd, beats = _clean_hrv(rr)
    if rmssd:
        live["hrv_rmssd"] = round(rmssd, 1)
        live["hrv_beats"] = beats

    return {"live": live, "t0": t0, "t1": t1}


MONITOR_HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Telomy capture monitor</title>
<style>
 :root{--bg:#0b0f0e;--card:#141a18;--line:#243029;--txt:#e8efe9;--muted:#8aa093;--teal:#4fd1a5;--amber:#e8c267;--red:#e0786a;--mono:'SF Mono',ui-monospace,monospace}
 *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.4 -apple-system,system-ui,sans-serif;padding:16px;max-width:1000px;margin:auto}
 h1{font-size:19px;margin:0 0 2px}.sub{color:var(--muted);font-size:13px;margin-bottom:16px}
 .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
 .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;border-left:4px solid var(--line)}
 .card.ok{border-left-color:var(--teal)}.card.warn{border-left-color:var(--amber)}.card.stale{border-left-color:var(--red);opacity:.75}
 .card h2{font-size:14px;margin:0 0 2px;text-transform:uppercase;letter-spacing:.04em}
 .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
 .ok .dot{background:var(--teal)}.warn .dot{background:var(--amber)}.stale .dot{background:var(--red)}
 .age{font-size:12px;color:var(--muted);font-family:var(--mono)}
 .row{display:flex;justify-content:space-between;margin-top:8px;font-family:var(--mono);font-size:13px}
 .row .k{color:var(--muted)}.row .v{font-weight:600}
 .pill{display:inline-block;background:#0b0f0e;border:1px solid var(--line);border-radius:999px;padding:2px 9px;font-size:12px;color:var(--muted);font-family:var(--mono);margin-right:6px}
 .big{font-family:var(--mono);font-size:26px}
</style></head><body>
<h1>Telomy capture monitor</h1>
<div class="sub">Live overnight capture health · <span id="status" class="pill">connecting…</span>
 <span class="pill" id="sess">—</span><span class="pill" id="elapsed">—</span><span class="pill" id="total">—</span></div>
<div class="grid" id="cards"></div>
<script>
const DEVS=[['patch','ECG patch'],['ring','Ring'],['reference','BerryMed oximeter'],['whoop','WHOOP raw']];
function fmtAge(s){if(s==null)return '—';if(s<90)return s.toFixed(0)+'s ago';if(s<5400)return (s/60).toFixed(0)+'m ago';return (s/3600).toFixed(1)+'h ago';}
function cls(s){if(s==null||s>120)return 'stale';if(s>30)return 'warn';return 'ok';}
async function tick(){
 const el=document.getElementById('status');
 try{
  const d=await (await fetch('/cal/status',{cache:'no-store'})).json();
  el.textContent=new Date().toLocaleTimeString();el.className='pill';
  document.getElementById('sess').textContent=d.session_id||'no session';
  document.getElementById('total').textContent=(d.total||0)+' readings';
  if(d.started&&d.last)document.getElementById('elapsed').textContent=((d.last-d.started)/3600).toFixed(2)+'h elapsed';
  const byDev={};for(const k in (d.channels||{})){const c=d.channels[k];(byDev[c.source]=byDev[c.source]||[]).push(c);}
  const cards=DEVS.map(([src,name])=>{
    const chs=(byDev[src]||[]).sort((a,b)=>a.channel<b.channel?-1:1);
    const minAge=chs.length?Math.min(...chs.map(c=>c.age_sec==null?1e9:c.age_sec)):null;
    const k=chs.length?cls(minAge):'stale';
    const rows=chs.map(c=>`<div class="row"><span class="k">${c.channel}</span><span class="v">${c.last_value==null?'—':(+c.last_value).toFixed(c.channel.includes('Ratio')?3:(c.channel==='tempC'?1:0))} <span class="age">·${fmtAge(c.age_sec)}·${c.n}</span></span></div>`).join('');
    return `<div class="card ${k}"><h2><span class="dot"></span>${name}</h2>`+
           (chs.length?rows:`<div class="age">no data yet</div>`)+`</div>`;
  }).join('');
  document.getElementById('cards').innerHTML=cards;
 }catch(e){el.textContent='offline';el.className='pill';}
}
tick();setInterval(tick,5000);
</script></body></html>"""


def monitor_html() -> str:
    return MONITOR_HTML
