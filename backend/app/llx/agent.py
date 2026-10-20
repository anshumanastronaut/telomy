"""Telomy Health Agent — the single entry point that unifies the whole stack.

Two jobs, one agent:
  • assess(...)       — periodic deep assessment: fuse the blood models + wearable overlay into one
                        grounded Telomy Risk Profile (tool-grounded; numbers come from trained models
                        and cited evidence, never invented).
  • real-time safety  — stream accelerometer + vitals through the emergency workflow (fall / hypoxemia
                        / HR alarms) with a confirmation window and consent-gated escalation.

Everything downstream (clocks, PhenoAge, disease models, mortality, fusion, fall detector, monitor) is
already built and tested; this class is the thin, well-defined orchestration layer the app talks to.
"""
from __future__ import annotations
from . import fusion
from .falldetect import detect_fall, FallConfig
from .monitor import EmergencyMonitor, MonitorConfig

class TelomyHealthAgent:
    def __init__(self, monitor_cfg: MonitorConfig | None = None, fall_cfg: FallConfig | None = None):
        self.monitor = EmergencyMonitor(monitor_cfg or MonitorConfig())
        self.fall_cfg = fall_cfg or FallConfig()

    # ---- periodic assessment -------------------------------------------------
    def assess(self, blood_panel: dict, wearable: dict | None = None) -> dict:
        """One report in -> the full grounded risk profile (ages, diseases, mortality, wearable tier)."""
        return fusion.risk_profile(blood_panel, wearable)

    # ---- real-time safety stream --------------------------------------------
    def ingest_accelerometer(self, samples, now: float):
        ev = detect_fall(samples, self.fall_cfg)
        return {"fall": ev, "monitor": self.monitor.on_fall(ev, now)}

    def ingest_vitals(self, hr=None, spo2=None, now: float = 0.0, at_rest: bool = True):
        return self.monitor.on_vitals(hr=hr, spo2=spo2, now=now, at_rest=at_rest)

    def ingest_motion(self, moving: bool):
        self.monitor.on_motion(moving)

    def user_respond(self, ok: bool, now: float = 0.0):
        return self.monitor.user_respond(ok=ok, now=now)

    def tick(self, now: float):
        return self.monitor.tick(now)

    @property
    def state(self):
        return self.monitor.state

if __name__ == "__main__":
    import json
    agent = TelomyHealthAgent()
    panel = {"age": 58, "sex": 1, "albumin": 4.0, "creatinine": 1.3, "glucose": 141, "crp_mgL": 5.5,
             "lymph_pct": 24, "mcv": 93, "rdw": 14.3, "wbc": 8.1, "alp": 98, "hba1c": 6.5, "hdl": 36,
             "trig": 200, "total_chol": 215, "ast": 40, "alt": 42, "bun": 20, "hgb": 14.5, "platelets": 240}
    wearable = {"resting_hr": 84, "sdnn": 38, "spo2_mean": 92, "spo2_min": 86}
    print("ASSESSMENT:\n ", agent.assess(panel, wearable)["summary"])
    print("\nSAFETY STREAM (simulated fall, no response):")
    import math, random
    hz = 50
    sig = [1.0 + random.uniform(-0.05, 0.05) for _ in range(hz * 6)]
    for i in range(hz * 2 - 15, hz * 2): sig[i] = 0.4
    sig[hz * 2] = 3.4
    for i in range(hz * 2 + 15, hz * 2 + 150): sig[i] = 1.0 + random.uniform(-0.05, 0.05)
    r = agent.ingest_accelerometer(sig, now=0)
    print("  fall:", r["fall"]["fall"], "conf", r["fall"]["confidence"], "-> state", agent.state)
    print("  t=46:", agent.tick(46)["state"], "->", agent.monitor.alert_payload["message"][:90], "...")
