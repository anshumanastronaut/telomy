"""Stream realistic machine telemetry to a Telomy server — for testing gateways before real machines are connected.

  python -m tools.device_simulator --device CRY-1 --key tdk_... --start 2026-10-06T08:00:00 [--server http://127.0.0.1:8787]

Profiles: cryo (cool-down → hold → door open), hbot/hbot_mild (compression → plateau → decompression), sauna, redlight, pemf,
cold, compression. Sends 5-second samples in batches of 120.
"""
import argparse
import json
import math
import random
import urllib.request
from datetime import datetime, timedelta


def profile(modality: str, target: dict, rnd: random.Random):
    """Yield (seconds_from_start, sample dict)."""
    if modality == "cryo":
        t_target = target.get("chamber_c", -140)
        for s in range(0, 300 + 180 + 120, 5):
            if s < 300:
                v = -60 + (t_target + 60) * (1 - math.exp(-s / 90))           # pre-cool
            elif s < 480:
                v = t_target + 6 * math.exp(-(s - 300) / 20) + rnd.gauss(0, 1.5)  # person inside: small warm-up then hold
            else:
                v = t_target + 35 * (1 - math.exp(-(s - 480) / 60))           # door open, warming
            yield s, {"chamber_temp_c": round(v, 1), "door_open": 1 if s >= 480 else 0, "status": "running"}
    elif modality in ("hbot", "hbot_mild"):
        ata, o2 = target.get("ata", 2.0), target.get("o2_pct", 100)
        total = target.get("minutes", 90) * 60
        for s in range(0, total + 1, 5):
            p = 1 + (ata - 1) * min(1, s / 600) if s < total - 600 else 1 + (ata - 1) * max(0, (total - s) / 600)
            yield s, {"pressure_ata": round(p + rnd.gauss(0, 0.005), 3), "o2_pct": round(o2 - abs(rnd.gauss(0, 1.2)), 1),
                      "chamber_temp_c": round(23 + 2 * min(1, s / 600) + rnd.gauss(0, 0.2), 1), "co2_ppm": round(600 + rnd.gauss(0, 40)), "status": "running"}
    elif modality in ("sauna", "sauna_ir"):
        temp, total = target.get("temp_c", 80), target.get("minutes", 20) * 60
        for s in range(0, total + 1, 5):
            yield s, {"temp_c": round(temp - 4 * math.exp(-s / 120) + rnd.gauss(0, 0.6), 1), "humidity_pct": round(12 + rnd.gauss(0, 1), 1), "status": "running"}
    elif modality == "redlight":
        irr, total = target.get("irradiance_mw_cm2", 50), target.get("minutes", 20) * 60
        for s in range(0, total + 1, 5):
            yield s, {"irradiance_mw_cm2": round(irr * (0.97 + 0.03 * rnd.random()), 1), "panel_temp_c": round(25 + 8 * min(1, s / 600), 1), "status": "running"}
    elif modality == "pemf":
        g, total = target.get("intensity_gauss", 20), target.get("minutes", 25) * 60
        for s in range(0, total + 1, 5):
            yield s, {"field_gauss": round(g + rnd.gauss(0, 0.5), 1), "frequency_hz": target.get("frequency_hz", 10),
                      "coil_temp_c": round(26 + 12 * (1 - math.exp(-s / 900)), 1), "status": "running"}
    elif modality == "cold":
        w, total = target.get("water_c", 8), target.get("minutes", 3) * 60
        for s in range(0, total + 1, 5):
            yield s, {"water_temp_c": round(w + 0.3 * s / max(total, 1) + rnd.gauss(0, 0.1), 2), "status": "running"}
    elif modality == "compression":
        m, total = target.get("pressure_mmhg", 80), target.get("minutes", 30) * 60
        for s in range(0, total + 1, 5):
            yield s, {"pressure_mmhg": round(m * (0.5 + 0.5 * math.sin(s / 15)) if s % 60 < 45 else 0, 1), "status": "running"}
    else:
        raise SystemExit(f"No profile for {modality}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--start", required=True, help="ISO time the machine run starts (5 min before the booked slot for cryo)")
    ap.add_argument("--server", default="http://127.0.0.1:8787")
    ap.add_argument("--modality", help="override (default: looked up from the server)")
    ap.add_argument("--target", default="{}", help='JSON, e.g. {"chamber_c": -150}')
    a = ap.parse_args()
    mod = a.modality or json.load(urllib.request.urlopen(f"{a.server}/centre/devices/{a.device}/telemetry"))["device"]["modality"]
    t0 = datetime.fromisoformat(a.start)
    rows = [{"ts": (t0 + timedelta(seconds=s)).isoformat(timespec="seconds"), **v} for s, v in profile(mod, json.loads(a.target), random.Random(1))]
    for i in range(0, len(rows), 120):
        req = urllib.request.Request(f"{a.server}/devices/{a.device}/telemetry", data=json.dumps({"samples": rows[i:i + 120]}).encode(),
                                     headers={"Content-Type": "application/json", "X-Device-Key": a.key}, method="POST")
        r = json.load(urllib.request.urlopen(req))
        if r["alarms"]:
            print("alarms:", r["alarms"][:3])
    print(f"sent {len(rows)} samples for {a.device} ({mod})")


if __name__ == "__main__":
    main()
