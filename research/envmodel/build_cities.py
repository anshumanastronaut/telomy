"""Build the Telomy global city-environment database from the WHO Ambient Air Quality Database V8.0
(8k+ settlements, 2010-2024). Output: a compact cities.json the exposome engine loads to resolve ANY city or
lat/lon to a real pollution profile (PM2.5/PM10/NO2) + the AQLI life-years-lost estimate — replacing the old
10-city hardcoded table.
"""
import csv, io, json, os

HERE = os.path.dirname(__file__)
XLSX = os.path.join(HERE, "who_aaq_v8.xlsx")
OUT = os.path.join(HERE, "..", "..", "backend", "app", "assets", "env", "cities.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def na(v):
    try:
        if v is None or str(v).strip().upper() in ("NA", "", "NAN"):
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


def main():
    import openpyxl
    ws = openpyxl.load_workbook(XLSX, read_only=True).active
    best = {}  # key -> record, keeping the most recent year that has a PM2.5 value
    n = 0
    for row in ws.iter_rows(values_only=True):
        line = row[0]
        if not line or str(line).startswith("who_region"):
            continue
        rec = next(csv.reader(io.StringIO(str(line))))
        if len(rec) < 20:
            continue
        iso3, country, city_raw, year = rec[1], rec[2], rec[3], rec[4]
        pm25, pm10, no2 = na(rec[7]), na(rec[6]), na(rec[8])
        pop, lat, lon = na(rec[16]), na(rec[18]), na(rec[19])
        city = city_raw.rsplit("/", 1)[0].strip()  # "Kabul/AFG" -> "Kabul"
        try:
            yr = int(float(year))
        except (ValueError, TypeError):
            continue
        if lat is None or lon is None:
            continue
        key = f"{city}|{iso3}"
        cur = best.get(key)
        # prefer the most recent year that carries a PM2.5 reading
        score = (1 if pm25 is not None else 0, yr)
        if cur is None or score > cur["_score"]:
            best[key] = {"_score": score, "city": city, "country": country, "iso3": iso3, "year": yr,
                         "pm25": pm25, "pm10": pm10, "no2": no2, "pop": pop, "lat": round(lat, 4), "lon": round(lon, 4)}
        n += 1

    cities = []
    for r in best.values():
        pm = r["pm25"]
        # AQLI (EPIC Chicago): each 10 µg/m³ of PM2.5 above the WHO guideline (5) ≈ 0.98 years of life lost
        lyl = round(max(0.0, (pm - 5) / 10.0) * 0.98, 2) if pm is not None else None
        cities.append({"city": r["city"], "country": r["country"], "iso3": r["iso3"], "year": r["year"],
                       "pm25": pm, "pm10": r["pm10"], "no2": r["no2"], "pop": r["pop"],
                       "lat": r["lat"], "lon": r["lon"], "life_years_lost": lyl})
    cities.sort(key=lambda c: (c["pm25"] is None, -(c["pm25"] or 0)))
    json.dump({"source": "WHO Ambient Air Quality Database V8.0 (2026); AQLI life-years-lost (EPIC 2024)",
               "n_cities": len(cities), "n_records_scanned": n, "cities": cities},
              open(OUT, "w"))
    print(f"scanned {n:,} city-year records -> {len(cities):,} unique cities -> {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")
    withpm = [c for c in cities if c["pm25"] is not None]
    print(f"cities with PM2.5: {len(withpm):,}")
    print("dirtiest 5:", [(c["city"], c["pm25"], c["life_years_lost"]) for c in withpm[:5]])
    print("cleanest 5:", [(c["city"], c["pm25"]) for c in withpm[-5:]])


if __name__ == "__main__":
    main()
