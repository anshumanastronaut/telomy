"""Roles: user, doctor, wellness-centre owner. Accounts, patient panel, centre operations.

Patient 1 is the full-Vault test user (all engine endpoints). Other patients carry a compact clinical snapshot so the
doctor and centre views can rank, predict and act on a realistic panel. All seed people are fictitious TEST data.
"""
import random
from datetime import date, datetime, timedelta

from . import db, derived, engine, predict

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, name TEXT, phone TEXT, org TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY, name TEXT, age REAL, sex TEXT, city TEXT, doctor_id INTEGER,
  member INTEGER DEFAULT 0, plan TEXT, data TEXT, joined TEXT);
CREATE TABLE IF NOT EXISTS clinical_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, author TEXT, ts TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS services (id TEXT PRIMARY KEY, name TEXT, minutes INTEGER, price INTEGER, capacity INTEGER, category TEXT, evidence TEXT, targets TEXT);
CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, service_id TEXT, ts TEXT, status TEXT, price INTEGER);
"""

SERVICES = [
    ("sauna", "Infrared sauna", 30, 900, 4, "Recovery", "B", ["hrv", "deep_sleep"]),
    ("cold", "Cold plunge", 10, 600, 3, "Recovery", "C", ["hrv"]),
    ("hbot", "Hyperbaric oxygen (HBOT)", 60, 4500, 2, "Therapy", "C", ["hrv"]),
    ("iv", "IV micronutrient drip", 45, 3500, 4, "Therapy", "C", ["vitd", "b12"]),
    ("redlight", "Red-light therapy", 20, 800, 2, "Recovery", "C", []),
    ("dexa", "DEXA body-composition scan", 20, 3500, 1, "Diagnostics", "A", ["vat_area", "almi"]),
    ("vo2", "VO2 max test (CPET)", 45, 6000, 1, "Diagnostics", "A", ["vo2max_lab"]),
    ("blood", "Longevity blood panel", 15, 5500, 6, "Diagnostics", "A", ["apob", "hba1c", "hscrp"]),
    ("consult", "Doctor consultation", 30, 1500, 3, "Consultation", "A", []),
    ("coach", "Strength coaching session", 60, 1800, 2, "Training", "B", ["almi", "grip"]),
]

FIRST = {"female": ["Priya", "Ananya", "Meera", "Kavya", "Ishita", "Neha", "Aditi", "Sneha", "Pooja", "Divya", "Riya", "Tanvi",
                    "Lakshmi", "Shruti", "Nandini"],
         "male": ["Rohan", "Vikram", "Arjun", "Siddharth", "Rahul", "Karan", "Manish", "Deepak", "Nikhil", "Aditya", "Varun",
                  "Kunal", "Suresh", "Harish", "Imran"]}
LAST = ["Sharma", "Iyer", "Reddy", "Menon", "Gupta", "Nair", "Rao", "Bose", "Kapoor", "Joshi", "Pillai", "Singh"]


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def seed(rnd: random.Random, today: date, sauna_days=()):
    init()
    now = engine.now_iso()
    accts = [("user", "Aarav (Test User)", "+91 90000 00000", None),
             ("doctor", "Dr. Meera Rao", "+91 90000 00010", "Telomy Care · Indiranagar"),
             ("centre", "Halo Longevity Centre (test)", "+91 90000 00020", "Halo Longevity Centre")]
    for role, name, phone, org in accts:
        db.exec_("INSERT INTO accounts (role, name, phone, org, data) VALUES (?,?,?,?,?)", (role, name, phone, org, "{}"))
    # patient 1 = full Vault user
    db.exec_("INSERT INTO patients (id, name, age, sex, city, doctor_id, member, plan, data, joined) VALUES (1,?,?,?,?,2,1,?,?,?)",
             ("Aarav (Test User)", round(engine.age_on() or 34, 1), "male", "Bengaluru", "Longevity Plus", "{}", "2026-06-01"))
    for i in range(2, 141):
        sex = rnd.choice(["male", "female"])
        age = rnd.randint(29, 72)
        tier = rnd.random()  # 0 healthy … 1 high risk
        snap = {
            "tc": round(rnd.gauss(185 + 50 * tier, 18)), "hdl": round(rnd.gauss(58 - 16 * tier, 6)),
            "ldl": round(rnd.gauss(105 + 50 * tier, 15)), "apob": round(rnd.gauss(85 + 45 * tier, 10)),
            "sbp": round(rnd.gauss(118 + 24 * tier + 0.3 * (age - 40), 7)), "bp_treated": tier > 0.75 and rnd.random() < 0.6,
            "smoker": rnd.random() < 0.12 + 0.15 * tier, "hba1c": round(rnd.gauss(5.3 + 0.9 * tier, 0.2), 1),
            "glucose": round(rnd.gauss(88 + 22 * tier, 6)), "bmi": round(rnd.gauss(23 + 6 * tier, 2), 1),
            "hscrp": round(abs(rnd.gauss(0.8 + 3 * tier, 0.6)), 1), "lpa": round(abs(rnd.gauss(25, 25))),
            "ast": round(rnd.gauss(24 + 18 * tier, 5)), "alt": round(rnd.gauss(24 + 22 * tier, 6)),
            "platelets": round(rnd.gauss(250 - 30 * tier, 30)), "egfr": round(rnd.gauss(100 - 0.6 * (age - 40) - 25 * tier * (age > 60), 8)),
            "uacr": round(abs(rnd.gauss(8 + 60 * tier * (age > 55), 6))), "vitd": round(rnd.gauss(28, 9)),
            "hrv": round(rnd.gauss(55 - 0.5 * (age - 40) - 10 * tier, 6)), "vo2max": round(rnd.gauss(44 - 0.35 * (age - 30) - 6 * tier, 3), 1),
            "family_history_dm": rnd.random() < 0.4, "last_report": (today - timedelta(days=rnd.randint(5, 260))).isoformat(),
            "conditions": [c for c, p in (("Hypertension", 0.5 * tier), ("Prediabetes", 0.5 * tier), ("Hypothyroid", 0.1)) if rnd.random() < p],
        }
        snap["diabetic"] = snap["hba1c"] >= 6.5
        db.exec_("INSERT INTO patients (id, name, age, sex, city, doctor_id, member, plan, data, joined) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (i, f"{rnd.choice(FIRST[sex])} {rnd.choice(LAST)}", age, sex, rnd.choice(["Bengaluru", "Mumbai", "Pune", "Chennai"]),
                  2 if i <= 14 else None, 1 if i >= 6 else 0, rnd.choice(["Essential", "Longevity Plus", "Performance"]),
                  db.j(snap), (today - timedelta(days=rnd.randint(10, 400))).isoformat()))
    for s in SERVICES:
        db.exec_("INSERT INTO services (id, name, minutes, price, capacity, category, evidence, targets) VALUES (?,?,?,?,?,?,?,?)",
                 (*s[:7], db.j(s[7])))
    members = [r["id"] for r in db.rows("SELECT id FROM patients WHERE member = 1")]
    for d in range(-62, 8):
        day = today + timedelta(days=d)
        for _ in range(rnd.randint(32, 48)):  # ~40 sessions/day across ~135 members
            sv = rnd.choices(SERVICES, weights=[5, 3, 2, 2, 2, 1, 1, 2, 2, 3])[0]
            hour = rnd.choice([7, 8, 9, 10, 11, 16, 17, 18, 19])
            status = "completed" if d < 0 else "booked" if d > 0 else rnd.choice(["completed", "checked_in", "booked"])
            if d < 0 and rnd.random() < 0.07:
                status = "no_show"
            db.exec_("INSERT INTO bookings (patient_id, service_id, ts, status, price) VALUES (?,?,?,?,?)",
                     (rnd.choice(members), sv[0], f"{day.isoformat()}T{hour:02d}:00:00", status, sv[3]))
    # The full-Vault member's sauna bookings are the days they logged sauna, so outcomes line up with wearable data.
    db.exec_("DELETE FROM bookings WHERE patient_id = 1 AND service_id = 'sauna'")
    for d in sauna_days:
        db.exec_("INSERT INTO bookings (patient_id, service_id, ts, status, price) VALUES (1,'sauna',?,?,900)",
                 (f"{d.isoformat()}T18:00:00", "completed" if d < today else "booked"))
    db.exec_("INSERT INTO clinical_notes (patient_id, author, ts, text) VALUES (?,?,?,?)",
             (1, "Dr. Meera Rao", now, "Reviewed CT (CAC 38) and ApoB 121. Discussed lipid lowering; patient prefers lifestyle first for 12 weeks, then reassess ApoB. Refer sleep medicine for AHI 13."))


# --------------------------------------------------------------------------- shared helpers

def snapshot(pid: int) -> dict:
    if pid == 1:
        return predict.inputs_from_vault()
    r = db.one("SELECT * FROM patients WHERE id = ?", (pid,))
    s = db.unj(r["data"], {})
    return {**s, "age": r["age"], "sex": r["sex"], "active": s.get("vo2max", 40) > 38}


def predictions(pid: int) -> dict:
    return predict.run(snapshot(pid))


def _priority(pid: int, preds: dict, x: dict) -> tuple[float, list[str]]:
    m = preds["models"]
    flags, score = [], 0.0
    cv = m["cvd"].get("risk") or 0
    if cv >= 7.5:
        flags.append(f"10-y CVD {cv}%"); score += cv
    if m["cvd"].get("enhancers"):
        flags += m["cvd"]["enhancers"][:2]; score += 5 * len(m["cvd"]["enhancers"])
    dm = m["diabetes"]
    if dm.get("already"):
        flags.append("HbA1c in diabetes range"); score += 25
    elif (dm.get("risk") or 0) >= 25:
        flags.append(f"Diabetes 5-y {dm['risk']}%"); score += dm["risk"] / 2
    if m["liver"].get("score") and m["liver"]["score"] >= 1.3:
        flags.append(f"FIB-4 {m['liver']['score']}"); score += 15
    if (m["kidney"].get("risk") or 0) >= 3:
        flags.append(f"Kidney failure 5-y {m['kidney']['risk']}%"); score += 20
    if (x.get("sbp") or 0) >= 140:
        flags.append(f"BP {round(x['sbp'])}"); score += 10
    return score, flags


def patient_card(r: dict) -> dict:
    x = snapshot(r["id"])
    p = predictions(r["id"])
    score, flags = _priority(r["id"], p, x)
    awaiting = db.one("SELECT COUNT(*) AS n FROM insights WHERE review_state = 'awaiting'")["n"] if r["id"] == 1 else 0
    last = (db.one("SELECT MAX(collected_on) AS d FROM reports") or {}).get("d") if r["id"] == 1 else db.unj(r["data"], {}).get("last_report")
    return {"id": r["id"], "name": r["name"], "age": round(r["age"]), "sex": r["sex"], "city": r["city"], "plan": r["plan"],
            "member": bool(r["member"]), "priority": round(score), "flags": flags[:4], "awaiting_reviews": awaiting,
            "last_report": last, "cvd": p["models"]["cvd"].get("risk"), "diabetes": p["models"]["diabetes"].get("risk"),
            "full_vault": r["id"] == 1, "conditions": db.unj(r["data"], {}).get("conditions", [])}


# --------------------------------------------------------------------------- doctor

def doctor_patients(doctor_id: int = 2) -> list[dict]:
    rows = db.rows("SELECT * FROM patients WHERE doctor_id = ?", (doctor_id,))
    return sorted((patient_card(r) for r in rows), key=lambda c: -c["priority"])


def doctor_patient(pid: int) -> dict:
    r = db.one("SELECT * FROM patients WHERE id = ?", (pid,))
    if not r:
        return None
    card = patient_card(r)
    x = snapshot(pid)
    out = {**card, "predictions": predictions(pid), "inputs": x,
           "notes": db.rows("SELECT * FROM clinical_notes WHERE patient_id = ? ORDER BY ts DESC", (pid,)),
           "bookings": db.rows("SELECT b.*, s.name AS service FROM bookings b JOIN services s ON s.id = b.service_id WHERE patient_id = ? ORDER BY ts DESC LIMIT 8", (pid,))}
    if pid == 1:
        out["awaiting"] = [i for i in engine.list_insights() if i["review_state"] == "awaiting"]
        out["risk_map"] = derived.risk_matrix()
        out["top"] = __import__("app.features", fromlist=["clinician_notes"]).clinician_notes()["top"]
    return out


def doctor_today(today: str) -> dict:
    pts = doctor_patients()
    appts = db.rows("""SELECT a.*, c.data AS cl FROM appointments a JOIN clinicians c ON c.id = a.clinician_id
                       WHERE a.status != 'cancelled' ORDER BY a.ts""")
    consults = db.rows("""SELECT b.*, p.name FROM bookings b JOIN patients p ON p.id = b.patient_id
                          WHERE b.service_id = 'consult' AND substr(b.ts,1,10) >= ? ORDER BY b.ts LIMIT 10""", (today,))
    queue = db.one("SELECT COUNT(*) AS n FROM insights WHERE review_state = 'awaiting' AND dismissed = 0")["n"]
    return {"patients": len(pts), "high_priority": [p for p in pts if p["priority"] >= 25][:5], "awaiting_reviews": queue,
            "consults": consults, "appointments": len(appts),
            "overdue_reports": sum(1 for p in pts if p["last_report"] and (date.fromisoformat(today) - date.fromisoformat(p["last_report"])).days > 180)}


# --------------------------------------------------------------------------- wellness centre

def centre_dashboard(today: str) -> dict:
    t = date.fromisoformat(today)
    m0 = t.replace(day=1).isoformat()
    todays = db.rows("""SELECT b.*, s.name AS service, s.capacity, p.name FROM bookings b JOIN services s ON s.id = b.service_id
                        JOIN patients p ON p.id = b.patient_id WHERE substr(b.ts,1,10) = ? ORDER BY b.ts""", (today,))
    rev = db.one("SELECT COALESCE(SUM(price),0) AS r, COUNT(*) AS n FROM bookings WHERE status IN ('completed','checked_in') AND ts >= ? AND ts <= ?",
                 (m0, today + "T23:59"))
    prev_m0 = (t.replace(day=1) - timedelta(days=1)).replace(day=1)
    prev_same = (prev_m0 + timedelta(days=t.day - 1)).isoformat()
    prev = db.one("SELECT COALESCE(SUM(price),0) AS r FROM bookings WHERE status IN ('completed','checked_in') AND ts >= ? AND ts <= ?",
                  (prev_m0.isoformat(), prev_same + "T23:59"))
    util = []
    for s in db.rows("SELECT * FROM services"):
        used = db.one("SELECT COUNT(*) AS n FROM bookings WHERE service_id = ? AND ts >= ? AND ts <= ? AND status != 'no_show'",
                      (s["id"], (t - timedelta(days=29)).isoformat(), today + "T23:59"))["n"]
        slots = s["capacity"] * 9 * 30
        util.append({"id": s["id"], "name": s["name"], "sessions": used, "utilisation": round(100 * used / slots)})
    noshow = db.one("SELECT COUNT(*) AS n FROM bookings WHERE status = 'no_show' AND ts >= ?", ((t - timedelta(days=30)).isoformat(),))["n"]
    members = db.rows("SELECT * FROM patients WHERE member = 1")
    cards = [patient_card(r) for r in members]
    active = {r["patient_id"] for r in db.rows("SELECT DISTINCT patient_id FROM bookings WHERE ts >= ? AND status = 'completed'",
                                                 ((t - timedelta(days=30)).isoformat(),))}
    return {"today": todays, "revenue_month": rev["r"], "sessions_month": rev["n"], "revenue_prev_month": prev["r"], "revenue_compare": f"1–{t.day} {prev_m0.strftime('%b')}",
            "members": len(members), "active_30d": len(active & {m["id"] for m in members}), "no_shows_30d": noshow,
            "utilisation": sorted(util, key=lambda u: -u["utilisation"]),
            "at_risk": sorted([c for c in cards if c["priority"] >= 25], key=lambda c: -c["priority"])[:5],
            "lapsing": [c for c in cards if c["id"] not in active][:5]}


def centre_members() -> list[dict]:
    out = []
    for r in db.rows("SELECT * FROM patients WHERE member = 1"):
        c = patient_card(r)
        c["visits_30d"] = db.one("SELECT COUNT(*) AS n FROM bookings WHERE patient_id = ? AND status = 'completed' AND ts >= date('now','-30 day')", (r["id"],))["n"]
        c["last_visit"] = (db.one("SELECT MAX(ts) AS t FROM bookings WHERE patient_id = ? AND status = 'completed'", (r["id"],)) or {}).get("t")
        out.append(c)
    return sorted(out, key=lambda c: -c["priority"])


def services() -> list[dict]:
    rs = db.rows("SELECT * FROM services ORDER BY category, name")
    for r in rs:
        r["targets"] = db.unj(r["targets"], [])
    return rs


def service_outcomes(service_id: str) -> dict:
    """Members' next-day HRV after the service vs their own other days — only the full-Vault member has nightly data."""
    s = dict(engine.series("hrv"))
    days = {r["ts"][:10] for r in db.rows("SELECT ts FROM bookings WHERE patient_id = 1 AND service_id = ? AND status = 'completed'", (service_id,))}
    after = [s[(date.fromisoformat(d) + timedelta(days=1)).isoformat()] for d in days if (date.fromisoformat(d) + timedelta(days=1)).isoformat() in s]
    other = [v for d, v in s.items() if (date.fromisoformat(d) - timedelta(days=1)).isoformat() not in days]
    if len(after) < 3:
        return {"service": service_id, "n": len(after), "message": "Not enough member sessions with wearable data yet."}
    w = engine.welch(after, other)
    return {"service": service_id, "n": len(after), "hrv_after": round(w["mean_a"], 1), "hrv_other": round(w["mean_b"], 1),
            "d": w["d"], "p": w["p"], "message": "Next-night HRV after this service vs other nights, members with wearables."}
