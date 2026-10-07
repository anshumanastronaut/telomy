"""Exposome: what the place you live in does to your body.

Daily exposures for wherever the person is (home city + logged travel): PM2.5, PM10, NO₂, ozone, UV index (Open-Meteo /
Copernicus CAMS, free, no key), temperature and humidity (Open-Meteo weather), plus slow-changing city context — groundwater
quality (CGWB / Jal Jeevan Mission WQMIS), altitude and noise. Each daily exposure becomes a covariate in the person's own
correlation engine ("PM2.5 days → next-night HRV"), and population evidence translates the dose:
  • AQLI (Greenstone, EPIC Chicago): each 10 µg/m³ of long-term PM2.5 above the WHO guideline (5 µg/m³) ≈ 0.98 years of life.
  • Berkeley Earth (Muller 2015): 22 µg/m³ PM2.5 for a day ≈ smoking one cigarette.
  • UV index ≥ 3 at midday makes vitamin D in skin (Holick); Delhi's winter smog cuts UV-B ~20–40 %.
  • Heat: each +1 °C night-time temperature above ~25 °C shortens sleep (Minor 2022, One Earth).
City values are approximate annual figures, labelled as such; live values replace them when the API is reachable.
"""
import json
import urllib.request
from datetime import date, timedelta

from . import db, engine

SCHEMA = """CREATE TABLE IF NOT EXISTS exposure (day TEXT, place TEXT, pm25 REAL, pm10 REAL, no2 REAL, o3 REAL, uv_max REAL, temp_mean REAL,
  temp_min REAL, humidity REAL, source TEXT, PRIMARY KEY (day, place));"""

CITIES = {  # lat, lon, altitude m, approx annual PM2.5 µg/m³ (CPCB/IQAir 2023–24), approx annual mean daily UV max, water notes
    "Delhi": (28.61, 77.21, 216, 102, 7.5, "Groundwater TDS often > 1,000 mg/L; fluoride and nitrate above BIS limits in parts (CGWB). Most homes use RO."),
    "Noida": (28.54, 77.39, 200, 89, 7.5, "Groundwater hardness and TDS high; fluoride hotspots in Gautam Buddh Nagar (CGWB)."),
    "Gurugram": (28.46, 77.03, 217, 75, 7.6, "Over-exploited aquifer; TDS and fluoride high in places (CGWB)."),
    "Bengaluru": (12.97, 77.59, 920, 30, 9.8, "Cauvery piped water is soft; borewells show nitrate and fluoride in peri-urban areas (CGWB)."),
    "Mumbai": (19.08, 72.88, 14, 41, 9.0, "Piped lake water is soft and low-TDS; monsoon contamination risk."),
    "Chennai": (13.08, 80.27, 6, 30, 10.5, "Seawater intrusion raises TDS/chloride in coastal borewells; desalinated supply in parts."),
    "Kolkata": (22.57, 88.36, 9, 50, 8.8, "Arsenic in groundwater in surrounding districts of West Bengal (CGWB)."),
    "Hyderabad": (17.39, 78.49, 505, 40, 9.8, "Fluoride endemic in parts of Telangana (Nalgonda); city supply is treated surface water."),
    "Pune": (18.52, 73.86, 560, 40, 9.5, "Mostly treated dam water; nitrate in some borewells."),
    "Singapore": (1.35, 103.82, 15, 13, 11.5, "Treated and NEWater supply; meets WHO guidelines."),
}
WHO_PM25 = 5.0


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def _get(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            return json.loads(r.read().decode())
    except Exception:  # noqa: BLE001 — offline is fine; we fall back to city climatology
        return None


def fetch(place: str, start: str, end: str) -> int:
    """Pull daily exposures for a city from Open-Meteo (air quality + weather) into the exposure table."""
    lat, lon = CITIES[place][:2]
    aq = _get(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=pm2_5,pm10,nitrogen_dioxide,ozone,uv_index"
              f"&start_date={start}&end_date={end}&timezone=Asia%2FKolkata")
    wx = _get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&daily=temperature_2m_mean,temperature_2m_min,"
              f"relative_humidity_2m_mean&start_date={start}&end_date={end}&timezone=Asia%2FKolkata")
    if not aq:
        return 0
    h = aq["hourly"]
    days: dict[str, dict] = {}
    for i, ts in enumerate(h["time"]):
        d = days.setdefault(ts[:10], {k: [] for k in ("pm2_5", "pm10", "nitrogen_dioxide", "ozone", "uv_index")})
        for k in d:
            v = h[k][i]
            if v is not None:
                d[k].append(v)
    w = {}
    if wx and "daily" in wx:
        for i, d in enumerate(wx["daily"]["time"]):
            w[d] = (wx["daily"]["temperature_2m_mean"][i], wx["daily"]["temperature_2m_min"][i], wx["daily"]["relative_humidity_2m_mean"][i])
    n = 0
    for d, v in days.items():
        if not v["pm2_5"]:
            continue
        mean = lambda xs: round(sum(xs) / len(xs), 1) if xs else None  # noqa: E731
        t = w.get(d, (None, None, None))
        db.exec_("INSERT OR REPLACE INTO exposure VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 (d, place, mean(v["pm2_5"]), mean(v["pm10"]), mean(v["nitrogen_dioxide"]), mean(v["ozone"]), max(v["uv_index"]) if v["uv_index"] else None,
                  t[0], t[1], t[2], "Open-Meteo / CAMS"))
        n += 1
    return n


def where(day: str) -> str:
    """Home city unless a travel event covers that day."""
    trip = db.one("SELECT label FROM events WHERE kind = 'travel' AND substr(ts,1,10) = ?", (day,))
    if trip:
        for c in CITIES:
            if c.lower() in trip["label"].lower():
                return c
    return engine.profile().get("city", "Bengaluru")


def ensure(days: int = 120) -> dict:
    end = date.fromisoformat(engine.last_signal_day() or date.today().isoformat())
    start = end - timedelta(days=days - 1)
    places = {where((start + timedelta(days=i)).isoformat()) for i in range(days)}
    got = {}
    for pl in places:
        have = db.one("SELECT COUNT(*) AS n FROM exposure WHERE place = ? AND day BETWEEN ? AND ?", (pl, start.isoformat(), end.isoformat()))["n"]
        got[pl] = have if have >= days * 0.8 else fetch(pl, start.isoformat(), end.isoformat())
    return got


def personal(days: int = 120) -> dict:
    """The person's own exposure timeline and what it did to them (within-person regression on next-night HRV & sleep)."""
    import numpy as np
    end = date.fromisoformat(engine.last_signal_day() or date.today().isoformat())
    rows = []
    for i in range(days):
        d = (end - timedelta(days=days - 1 - i)).isoformat()
        pl = where(d)
        e = db.one("SELECT * FROM exposure WHERE day = ? AND place = ?", (d, pl))
        if e:
            rows.append(e)
    if not rows:
        return {"available": False, "message": "Exposure data not downloaded yet (needs internet)."}
    pm = [r["pm25"] for r in rows if r["pm25"] is not None]
    uv = [r["uv_max"] for r in rows if r["uv_max"] is not None]
    effects = []
    for metric in ("hrv", "sleep_hours", "rhr"):
        s = dict(engine.series(metric))
        pairs = [(r["pm25"], s.get((date.fromisoformat(r["day"]) + timedelta(days=1)).isoformat())) for r in rows]
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
        if len(pairs) >= 30:
            x = np.array([a for a, _ in pairs]) / 10
            y = np.array([b for _, b in pairs])
            X = np.vstack([np.ones_like(x), x, np.arange(len(x)) / 30]).T
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            res = y - X @ beta
            se = float(np.sqrt((res @ res) / (len(y) - 3) * np.linalg.pinv(X.T @ X)[1, 1]))
            label, unit, better, dec = engine.SIGNALS[metric]
            p = 2 * (1 - engine._phi(abs(beta[1] / se))) if se else 1
            effects.append({"metric": metric, "label": label, "unit": unit, "per_10ug": round(float(beta[1]), 2),
                            "ci95": [round(float(beta[1] - 1.96 * se), 2), round(float(beta[1] + 1.96 * se), 2)], "p": engine.fmt_p(p), "n": len(pairs)})
    home = engine.profile().get("city", "Bengaluru")
    avg = sum(pm) / len(pm)
    return {"available": True, "home": home, "days": len(rows), "pm25_mean": round(avg, 1), "pm25_max": max(pm), "uv_mean_max": round(sum(uv) / len(uv), 1) if uv else None,
            "cigarette_equivalent_per_day": round(avg / 22, 2), "aqli_years_if_lifelong": round(max(0, avg - WHO_PM25) / 10 * 0.98, 1),
            "timeline": [{"day": r["day"], "place": r["place"], "pm25": r["pm25"], "uv": r["uv_max"], "temp": r["temp_mean"]} for r in rows],
            "effects": effects, "water": CITIES.get(home, (0, 0, 0, 0, 0, ""))[5],
            "method": "Daily PM2.5/UV from Copernicus CAMS via Open-Meteo for the city you were in; your next-night outcome regressed on PM2.5 (per 10 µg/m³) with a trend term."}


def compare(a: str = "Delhi", b: str = "Bengaluru", live: dict | None = None) -> dict:
    """Two identical people, two cities: what differs and what it is estimated to cost."""
    out = []
    for c in (a, b):
        lat, lon, alt, pm, uv, water = CITIES[c]
        cur = live.get(c) if live else None
        out.append({"city": c, "pm25_annual": pm, "pm25_last_week": cur, "uv_mean_max": uv, "altitude_m": alt, "water": water,
                    "aqli_years_lost": round(max(0, pm - WHO_PM25) / 10 * 0.98, 1), "cigarettes_per_day_equiv": round(pm / 22, 1)})
    da, db_ = out
    lines = [f"Same person, same habits: living in {a} vs {b} means breathing about {da['pm25_annual'] - db_['pm25_annual']:+.0f} µg/m³ more PM2.5 every day — "
             f"like smoking {da['cigarettes_per_day_equiv']:.1f} vs {db_['cigarettes_per_day_equiv']:.1f} cigarettes a day (Berkeley Earth).",
             f"AQLI estimates the long-term difference at ≈ {da['aqli_years_lost'] - db_['aqli_years_lost']:.1f} years of life expectancy.",
             f"Short-term: each +10 µg/m³ PM2.5 lowers HRV and raises blood pressure within days (Pieters 2012, Heart; Liang 2014, Hypertension). "
             f"Telomy measures this in your own data.",
             f"UV: {b} averages a midday UV maximum near {db_['uv_mean_max']}, {a} near {da['uv_mean_max']} — vitamin D synthesis and skin photo-ageing both follow UV dose; "
             f"{a}'s winter smog cuts UV-B further.",
             f"Water: {a}: {da['water']} {b}: {db_['water']}"]
    return {"cities": out, "summary": lines,
            "sources": ["AQLI 2024 (EPIC, University of Chicago)", "Berkeley Earth — air pollution and cigarette equivalence (Muller 2015)",
                        "Pieters N et al. 2012, Heart — PM and HRV meta-analysis", "Liang R et al. 2014, Hypertension — PM2.5 and blood pressure",
                        "CGWB groundwater quality reports; Jal Jeevan Mission WQMIS", "Copernicus CAMS via Open-Meteo"]}


def live_week() -> dict:
    out = {}
    end = date.fromisoformat(engine.last_signal_day() or date.today().isoformat())
    for c in ("Delhi", "Bengaluru"):
        lat, lon = CITIES[c][:2]
        aq = _get(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=pm2_5"
                  f"&start_date={(end - timedelta(days=6)).isoformat()}&end_date={end.isoformat()}&timezone=Asia%2FKolkata")
        if aq:
            v = [x for x in aq["hourly"]["pm2_5"] if x is not None]
            out[c] = round(sum(v) / len(v), 1) if v else None
    return out
