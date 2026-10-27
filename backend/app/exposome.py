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
import time as _time
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

# ---- global city-environment database (WHO Ambient Air Quality V8.0, 7,482 cities) ----
# Replaces the 10-city hardcoded table above for coverage: any city or lat/lon resolves to a real PM2.5/PM10/NO2
# profile + AQLI life-years-lost. The CITIES dict above is kept for its richer India UV + groundwater notes.
import os as _os  # noqa: E402
try:
    _G = json.load(open(_os.path.join(_os.path.dirname(__file__), "assets", "env", "cities.json")))
    GLOBAL = {c["city"].lower(): c for c in _G["cities"]}
    GLOBAL_LIST = [c for c in _G["cities"] if c.get("pm25") is not None]
    GLOBAL_SRC = _G.get("source", "WHO AAQ V8.0")
except Exception:  # noqa: BLE001
    GLOBAL, GLOBAL_LIST, GLOBAL_SRC = {}, [], ""


def _nearest(lat: float, lon: float):
    import math
    def d2(a):
        dla = math.radians(a["lat"] - lat); dlo = math.radians(a["lon"] - lon)
        return math.sin(dla / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(a["lat"])) * math.sin(dlo / 2) ** 2
    return min(GLOBAL_LIST, key=d2) if GLOBAL_LIST else None


def city_profile(name: str | None = None, lat: float | None = None, lon: float | None = None) -> dict | None:
    """Resolve ANY city to a real environmental profile. Match order: rich India table → exact WHO name →
    name prefix → nearest WHO station by lat/lon. Merges real pollution (WHO) with UV/water (India table)."""
    prof: dict = {}
    g = None
    if name and name.lower() in GLOBAL:
        g = GLOBAL[name.lower()]
    elif name:
        g = next((c for c in GLOBAL_LIST if c["city"].lower().startswith(name.lower())), None)
    if g is None and lat is not None and lon is not None:
        g = _nearest(lat, lon)
    if g:
        pm = g.get("pm25")
        prof = {"city": g["city"], "country": g.get("country"), "iso3": g.get("iso3"), "lat": g["lat"], "lon": g["lon"],
                "pm25": pm, "pm10": g.get("pm10"), "no2": g.get("no2"), "life_years_lost": g.get("life_years_lost"),
                "population": g.get("pop"), "data_year": g.get("year"),
                "cigarettes_per_day_equiv": round(pm / 22, 1) if pm else None,
                "source": GLOBAL_SRC, "resolved_by": "nearest-station" if (name and name.lower() not in GLOBAL) else "name"}
    if name and name in CITIES:          # overlay richer India UV + groundwater notes
        la, lo, alt, pm, uv, water = CITIES[name]
        prof.setdefault("city", name)
        prof.update({"lat": la, "lon": lo, "altitude_m": alt, "uv_mean_max": uv, "water": water})
        if not prof.get("pm25"):
            prof["pm25"] = pm
            prof["life_years_lost"] = round(max(0, pm - WHO_PM25) / 10 * 0.98, 2)
            prof["cigarettes_per_day_equiv"] = round(pm / 22, 1)
    return prof or None


# ---- social connection (the single biggest non-medical longevity lever) ----
# Loneliness prevalence by country (% who felt lonely "a lot yesterday", Gallup World Poll 2023, 142 countries;
# global mean 23%). Only documented values are listed; everything else falls back to the global mean, labelled.
GLOBAL_LONELY = 23.0
SOCIAL = {"Comoros": 45, "Denmark": 12, "Finland": 11, "Iceland": 11, "Poland": 11, "Slovenia": 11,
          "Taiwan": 11, "Estonia": 10, "Kosovo": 10, "Kazakhstan": 10, "Vietnam": 6}
LONELY_OR = 1.26        # Holt-Lunstad 2015 meta-analysis: loneliness → mortality odds ratio
ISOLATION_OR = 1.29     # objective social isolation → mortality OR


def social_impact(country: str | None = None, lonely_pct: float | None = None) -> dict:
    """Social-connection exposure. Loneliness raises mortality ~26% (Holt-Lunstad) — on par with smoking 15
    cig/day and larger than obesity. Country prevalence here; the member's own social data (if logged) overrides."""
    documented = country in SOCIAL if country else False
    pct = lonely_pct if lonely_pct is not None else (SOCIAL.get(country, GLOBAL_LONELY) if country else GLOBAL_LONELY)
    return {"factor": "social_connection", "lonely_pct": pct,
            "mortality_or_if_lonely": LONELY_OR, "isolation_or": ISOLATION_OR,
            "note": ("Loneliness ≈ +26% mortality risk (Holt-Lunstad 2015) — comparable to smoking 15 cigarettes/day. "
                     "Strongest modifiable non-medical factor Telomy can surface."),
            "source": "Gallup World Poll 2023" + ("" if documented else " (global mean — country value not released)"),
            "confidence": "country-level" if documented else "global-default"}


# ---- environmental noise (estimated from urban density; measured EEA/DOT noise maps are the roadmap) ----
import math as _math  # noqa: E402


def noise_estimate(population: float | None, pm25: float | None = None) -> dict:
    """Day-evening-night noise (Lden) estimated from settlement size (proxy); road-traffic noise raises coronary
    disease ~8% per 10 dB above 50 dB (WHO 2018 meta-analysis). Measured noise maps are a roadmap integration."""
    pop = population or 500_000
    lden = max(45.0, min(75.0, 42 + 4.5 * _math.log10(max(pop, 1000) / 1000)))
    cad_increase = round(max(0.0, (lden - 50)) / 10 * 8, 1)
    return {"factor": "noise", "lden_db_estimated": round(lden, 0), "coronary_disease_risk_increase_pct": cad_increase,
            "note": "Above 50 dB, road-traffic noise ≈ +8% coronary disease per 10 dB (WHO 2018); also fragments sleep.",
            "source": "estimated from population density — measured EEA/US-DOT noise maps are the integration roadmap",
            "confidence": "estimated"}


def exposome_profile(name: str | None = None, lat: float | None = None, lon: float | None = None,
                     country: str | None = None) -> dict:
    """The full multi-factor exposome for a place: air + social connection + noise + heat/UV/water, each with its
    evidence-based health translation and honest confidence. Food quality is PERSONAL (the member's diet log via
    the nutrition/NOVA engine), not a postcode factor, so it is referenced, not geolocated."""
    air = city_profile(name=name, lat=lat, lon=lon) or {}
    ctry = country or air.get("country")
    factors = []
    if air.get("pm25") is not None:
        factors.append({"factor": "air_quality", "pm25": air["pm25"], "pm10": air.get("pm10"), "no2": air.get("no2"),
                        "life_years_lost": air.get("life_years_lost"), "cigarettes_per_day_equiv": air.get("cigarettes_per_day_equiv"),
                        "note": "Each 10 µg/m³ PM2.5 above the WHO guideline (5) ≈ 0.98 yr of life (AQLI).",
                        "source": air.get("source", "WHO AAQ V8.0"), "confidence": "measured"})
    factors.append(social_impact(ctry))
    factors.append(noise_estimate(air.get("population"), air.get("pm25")))
    if air.get("uv_mean_max"):
        factors.append({"factor": "uv", "uv_mean_max": air["uv_mean_max"], "note": "UV ≥3 drives skin vitamin-D synthesis and photo-ageing.", "confidence": "annual-estimate"})
    if air.get("water"):
        factors.append({"factor": "water", "note": air["water"], "source": "CGWB / Jal Jeevan Mission (India)", "confidence": "city-note"})
    factors.append({"factor": "food_quality", "note": "Food quality is measured from your own diet log (NOVA processing + Nutri-score), "
                    "not your location — see the nutrition engine. Ultra-processed-heavy diets ≈ +10–18% mortality (Naghshi 2024).",
                    "source": "Telomy nutrition engine (food_quality / NOVA)", "confidence": "personal-if-logged"})
    return {"place": air.get("city", name), "country": ctry, "lat": air.get("lat"), "lon": air.get("lon"),
            "factors": factors,
            "summary": f"{air.get('city', name)}'s exposome: air {('loses ≈%.1f yr (AQLI)' % air['life_years_lost']) if air.get('life_years_lost') else 'n/a'}; "
                       f"social {'elevated' if social_impact(ctry)['lonely_pct'] >= GLOBAL_LONELY else 'lower'}-loneliness context; "
                       f"noise ~{noise_estimate(air.get('population'))['lden_db_estimated']:.0f} dB est.",
            "honesty": "Evidence-translation engine (cited dose-responses), not a trained outcome model — no free "
                       "location-exposome→mortality cohort exists to train on. Air is measured; social is country-level; "
                       "noise is estimated; food is personal. Each factor states its own confidence."}


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


_LAST_FETCH: dict[tuple, float] = {}
_LIVE: dict = {"t": 0.0, "end": None, "v": None}
_TTL = 6 * 3600    # Open-Meteo data changes slowly; one network round per place per 6 h (was every request)


def ensure(days: int = 120) -> dict:
    end = date.fromisoformat(engine.last_signal_day() or date.today().isoformat())
    start = end - timedelta(days=days - 1)
    places = {where((start + timedelta(days=i)).isoformat()) for i in range(days)}
    got = {}
    for pl in places:
        have = db.one("SELECT COUNT(*) AS n FROM exposure WHERE place = ? AND day BETWEEN ? AND ?", (pl, start.isoformat(), end.isoformat()))["n"]
        key = (db.db_path(), pl, start.isoformat())
        if have >= days * 0.8 or _time.time() - _LAST_FETCH.get(key, 0) < _TTL:
            got[pl] = have
        else:
            _LAST_FETCH[key] = _time.time()
            got[pl] = fetch(pl, start.isoformat(), end.isoformat())
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
    """Two identical people, two cities: what differs and what it is estimated to cost. Works for any of the
    7,482 WHO cities (resolved via city_profile), not just the hardcoded India set."""
    out = []
    for c in (a, b):
        p = city_profile(c) or {"city": c, "pm25": None}
        pm = p.get("pm25")
        out.append({"city": p.get("city", c), "country": p.get("country"), "pm25_annual": pm,
                    "pm25_last_week": (live.get(c) if live else None), "pm10_annual": p.get("pm10"), "no2_annual": p.get("no2"),
                    "uv_mean_max": p.get("uv_mean_max"), "altitude_m": p.get("altitude_m"), "water": p.get("water"),
                    "aqli_years_lost": p.get("life_years_lost"), "cigarettes_per_day_equiv": p.get("cigarettes_per_day_equiv"),
                    "data_year": p.get("data_year"), "source": p.get("source")})
    da, db_ = out
    lines = []
    if da["pm25_annual"] is not None and db_["pm25_annual"] is not None:
        lines.append(f"Same person, same habits: living in {da['city']} vs {db_['city']} means breathing about "
                     f"{da['pm25_annual'] - db_['pm25_annual']:+.0f} µg/m³ more PM2.5 every day — like smoking "
                     f"{da['cigarettes_per_day_equiv']:.1f} vs {db_['cigarettes_per_day_equiv']:.1f} cigarettes a day (Berkeley Earth).")
        if da["aqli_years_lost"] is not None and db_["aqli_years_lost"] is not None:
            lines.append(f"AQLI estimates the long-term difference at ≈ {da['aqli_years_lost'] - db_['aqli_years_lost']:.1f} years of life expectancy.")
        lines.append("Short-term: each +10 µg/m³ PM2.5 lowers HRV and raises blood pressure within days (Pieters 2012, Heart; "
                     "Liang 2014, Hypertension). Telomy measures this in your own data.")
    if da.get("uv_mean_max") and db_.get("uv_mean_max"):
        lines.append(f"UV: {db_['city']} averages a midday UV maximum near {db_['uv_mean_max']}, {da['city']} near {da['uv_mean_max']} — "
                     f"vitamin D synthesis and skin photo-ageing both follow UV dose.")
    if da.get("water") or db_.get("water"):
        lines.append(f"Water: {da['city']}: {da.get('water','—')} {db_['city']}: {db_.get('water','—')}")
    return {"cities": out, "summary": lines,
            "sources": ["WHO Ambient Air Quality Database V8.0 (2026) — 7,482 cities", "AQLI 2024 (EPIC, University of Chicago)",
                        "Berkeley Earth — air pollution and cigarette equivalence (Muller 2015)",
                        "Pieters N et al. 2012, Heart — PM and HRV meta-analysis", "Liang R et al. 2014, Hypertension — PM2.5 and blood pressure",
                        "CGWB groundwater quality reports; Jal Jeevan Mission WQMIS", "Copernicus CAMS via Open-Meteo"]}


def live_week() -> dict:
    end = date.fromisoformat(engine.last_signal_day() or date.today().isoformat())
    if _LIVE["v"] is not None and _LIVE["end"] == end and _time.time() - _LIVE["t"] < _TTL:
        return _LIVE["v"]
    out = {}
    for c in ("Delhi", "Bengaluru"):
        lat, lon = CITIES[c][:2]
        aq = _get(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=pm2_5"
                  f"&start_date={(end - timedelta(days=6)).isoformat()}&end_date={end.isoformat()}&timezone=Asia%2FKolkata")
        if aq:
            v = [x for x in aq["hourly"]["pm2_5"] if x is not None]
            out[c] = round(sum(v) / len(v), 1) if v else None
    _LIVE.update(t=_time.time(), end=end, v=out)
    return out


# ---- live "right here, right now": real-time AQI/UV/weather → an outdoor-activity score + actionable alerts --------
_HERE: dict = {}          # "lat,lon" (2dp ≈ 1 km) -> {"t": ts, "v": result}
_HERE_TTL = 900           # 15 min — current conditions change slowly; don't hammer Open-Meteo on every screen open

_WX = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog", 51: "Light drizzle",
       53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle", 61: "Light rain", 63: "Rain",
       65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
       77: "Snow grains", 80: "Showers", 81: "Showers", 82: "Heavy showers", 85: "Snow showers", 86: "Snow showers",
       95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ hail"}


def _r(x, n: int = 1):
    return round(x, n) if isinstance(x, (int, float)) else None


def _aqi_cat(pm25):
    if pm25 is None:
        return "Unknown"
    if pm25 <= 12: return "Good"
    if pm25 <= 35: return "Moderate"
    if pm25 <= 55: return "Poor"
    if pm25 <= 150: return "Unhealthy"
    return "Hazardous"


def _reverse_geocode(lat: float, lon: float):
    r = _get(f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=en")
    if r:
        return r.get("city") or r.get("locality") or r.get("principalSubdivision") or r.get("countryName")
    return None


def here(lat: float, lon: float) -> dict:
    """Current conditions right where the person is: live AQI/UV/weather + a 0–100 outdoor-activity score and
    actionable alerts (UV/sun, air, heat, cold). Cached ~15 min per ~1 km cell."""
    key = f"{round(lat, 2)},{round(lon, 2)}"
    c = _HERE.get(key)
    if c and _time.time() - c["t"] < _HERE_TTL:
        return c["v"]
    aq = _get(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}"
              f"&current=pm2_5,pm10,nitrogen_dioxide,ozone,uv_index,us_aqi&timezone=auto")
    wx = _get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
              f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m"
              f"&daily=uv_index_max,temperature_2m_max,temperature_2m_min,sunrise,sunset&forecast_days=1&timezone=auto")
    if not aq and not wx:
        return {"ok": False, "reason": "Couldn't reach the live air-quality / weather service — check connectivity."}
    a = (aq or {}).get("current", {})
    w = (wx or {}).get("current", {})
    daily = (wx or {}).get("daily", {})
    pm25, uv = a.get("pm2_5"), a.get("uv_index")
    temp, feels, hum = w.get("temperature_2m"), w.get("apparent_temperature"), w.get("relative_humidity_2m")
    is_day, wcode = bool(w.get("is_day")), w.get("weather_code")
    cat = _aqi_cat(pm25)

    score = 100.0
    if pm25 is not None:
        score -= min(60.0, max(0.0, (pm25 - 10) * 1.2))          # clean air below ~10 µg/m³
    if uv is not None and is_day:
        score -= min(25.0, max(0.0, (uv - 5) * 5))               # UV above 5 taxes an outdoor session
    if temp is not None:
        if temp > 30: score -= min(25.0, (temp - 30) * 2.5)
        elif temp < 8: score -= min(20.0, (8 - temp) * 2)
    if wcode in (61, 63, 65, 80, 81, 82, 95, 96, 99, 71, 73, 75):
        score -= 15.0
    score = max(0, round(score))
    band = "Great" if score >= 80 else "Good" if score >= 60 else "Fair" if score >= 40 else "Poor"

    alerts = []
    if pm25 is not None and pm25 > 35:
        alerts.append({"level": "warn" if pm25 <= 55 else "danger", "icon": "aqi.medium",
                       "text": f"Air {cat.lower()} — PM2.5 {round(pm25)} µg/m³. An N95 helps; move hard cardio indoors."})
    if uv is not None and is_day and uv >= 6:
        alerts.append({"level": "warn" if uv < 8 else "danger", "icon": "sun.max.fill",
                       "text": f"UV {round(uv)} — {'very high' if uv >= 8 else 'high'}. SPF 30+, hat and shade; peak 11am–3pm."})
    if temp is not None and temp >= 35:
        alerts.append({"level": "warn", "icon": "thermometer.sun.fill",
                       "text": f"Hot — {round(temp)}°C (feels {round(feels)}°C). Hydrate; train early morning or evening."})
    if temp is not None and temp <= 5:
        alerts.append({"level": "warn", "icon": "thermometer.snowflake",
                       "text": f"Cold — {round(temp)}°C. Warm up longer and cover extremities."})
    if uv is not None and is_day and 3 <= uv < 6 and not alerts:
        alerts.append({"level": "ok", "icon": "sun.max",
                       "text": f"UV {round(uv)} — moderate. ~15 min of midday sun makes vitamin D; longer needs SPF."})
    if not alerts and score >= 70:
        alerts.append({"level": "ok", "icon": "figure.walk",
                       "text": "Clean air and comfortable conditions — a good window for a walk or outdoor training."})

    out = {"ok": True, "place": _reverse_geocode(lat, lon) or "Your location", "lat": lat, "lon": lon,
           "as_of": a.get("time") or w.get("time"),
           "current": {"pm2_5": _r(pm25), "pm10": _r(a.get("pm10")), "no2": _r(a.get("nitrogen_dioxide")),
                       "ozone": _r(a.get("ozone")), "us_aqi": a.get("us_aqi"), "uv_index": _r(uv),
                       "aqi_category": cat, "temp_c": _r(temp), "feels_like_c": _r(feels), "humidity": _r(hum),
                       "wind_kmh": _r(w.get("wind_speed_10m")), "is_day": is_day,
                       "weather": _WX.get(wcode) if wcode is not None else None},
           "uv_max_today": _r((daily.get("uv_index_max") or [None])[0]),
           "temp_min_today": _r((daily.get("temperature_2m_min") or [None])[0]),
           "temp_max_today": _r((daily.get("temperature_2m_max") or [None])[0]),
           "sunrise": (daily.get("sunrise") or [None])[0], "sunset": (daily.get("sunset") or [None])[0],
           "outdoor_score": score, "outdoor_band": band, "alerts": alerts,
           "source": "Open-Meteo (CAMS air quality + weather) · place via BigDataCloud"}
    _HERE[key] = {"t": _time.time(), "v": out}
    return out
