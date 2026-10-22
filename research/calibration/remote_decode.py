"""Runs ON the Oracle VM (piped in over ssh). Decodes the WHOOP raw streams into the metrics NOOP leaves null and
prints one JSON blob: live HR/HRV/IMU (last ~15 min) + the last sleep window's SpO2-ratio / thermistor series (for
SpO2 & temp calibration). No deps beyond the stdlib + the user's SQLite Vault. Read-only."""
import sqlite3, json, math, statistics as st, sys, os

DB = os.environ.get("CAL_DB", "/opt/telomy/data_local/users/2.db")
db = sqlite3.connect(DB)


def rows(stream, t0, t1):
    return [(r[0], r[1]) for r in db.execute(
        "SELECT ts,data FROM whoop_rows WHERE stream=? AND ts BETWEEN ? AND ? ORDER BY ts", (stream, t0, t1))]


def rr_in(t0, t1):   # rrMs lives in the KEY column
    return [(json.loads(k)["ts"], json.loads(k)["rrMs"]) for k, _ in
            db.execute("SELECT key,data FROM whoop_rows WHERE stream='rrInterval' AND ts BETWEEN ? AND ? ORDER BY ts", (t0, t1))]


def rmssd(s):
    d = [(s[i + 1] - s[i]) ** 2 for i in range(len(s) - 1)]
    return math.sqrt(sum(d) / len(d)) if d else None


def clean_hrv(recs):
    """WHOOP over-delivers R-R ~2.4x. Collapse beats sharing a second (median), then Malik 20% successive-difference filter."""
    byts = {}
    for t, v in recs:
        if 300 <= v <= 2000:
            byts.setdefault(t, []).append(v)
    onep = [st.median(vs) for _, vs in sorted(byts.items())]
    if not onep:
        return None, 0
    filt = [onep[0]]
    for v in onep[1:]:
        if abs(v - filt[-1]) / filt[-1] <= 0.20:
            filt.append(v)
    return (rmssd(filt), len(filt))


out = {"db": DB}
# --- live window: last 15 min of whatever's streaming now ---
tmax = db.execute("SELECT max(ts) FROM whoop_rows WHERE stream='hrSample'").fetchone()[0] or 0
t0, t1 = tmax - 15 * 60, tmax
out["live"] = {"t0": t0, "t1": t1}
hr = [json.loads(d).get("bpm") for _, d in rows("hrSample", t0, t1)]
hr = [x for x in hr if x]
out["live"]["hr"] = round(st.mean(hr), 1) if hr else None
rmv, n = clean_hrv(rr_in(t0, t1))
out["live"]["hrv_rmssd"] = round(rmv, 1) if rmv else None
out["live"]["hrv_beats"] = n
g = [json.loads(d) for _, d in rows("gravitySample", t0, t1)]
vecs = [(x["x"], x["y"], x["z"]) for x in g if x.get("z") is not None]
if vecs:
    mags = [math.sqrt(a * a + b * b + c * c) for a, b, c in vecs]
    zang = [math.degrees(math.atan2(c, math.sqrt(a * a + b * b))) for a, b, c in vecs]
    motion = [abs(mags[i + 1] - mags[i]) for i in range(len(mags) - 1)]
    out["live"]["imu"] = {"g_mag": round(st.mean(mags), 3), "z_angle": round(st.mean(zang), 1),
                          "motion_mg": round(st.mean(motion) * 1000, 1) if motion else 0, "n": len(vecs)}

# --- last sleep window: SpO2 red/IR ratio + thermistor raw, per 5 min (for the calibration curves) ---
sess = db.execute("SELECT key,data FROM whoop_rows WHERE stream='sleepSession' ORDER BY ts DESC LIMIT 1").fetchone()
if sess:
    ss = json.loads(sess[0])["startTs"]; se = json.loads(sess[1])["endTs"]
    out["sleep"] = {"start": ss, "end": se, "spo2": [], "temp": []}
    step = 5 * 60
    t = ss
    while t < se:
        sp = [json.loads(d) for _, d in rows("spo2Sample", t, t + step)]
        red = [x["red"] for x in sp if x.get("red")]; ir = [x["ir"] for x in sp if x.get("ir")]
        if red and ir:
            out["sleep"]["spo2"].append({"ts": t + step // 2, "red": round(st.mean(red), 1),
                                         "ir": round(st.mean(ir), 1), "ratio": round(st.mean(red) / st.mean(ir), 4)})
        tp = [json.loads(d).get("raw") for _, d in rows("skinTempSample", t, t + step)]
        tp = [x for x in tp if x]
        if tp:
            out["sleep"]["temp"].append({"ts": t + step // 2, "raw": round(st.mean(tp), 1)})
        t += step

print(json.dumps(out))
