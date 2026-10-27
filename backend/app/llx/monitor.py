"""Emergency workflow — a safety-first state machine for falls and vital-sign alarms.

Design principles (learned from the Apple pattern + the false-alarm literature):
  • Never escalate on a single spike. A trigger opens a CONFIRMING window with a countdown.
  • The user can always cancel ("I'm OK"). Auto-escalation happens only if the window expires
    AND (for falls) the person is still immobile.
  • Escalation PREPARES an alert payload (reason, vitals, severity, location slot, message); it does
    NOT send anything. The app sends to the user's emergency contacts with their prior consent — this
    module never contacts anyone itself. (No autonomous external messaging.)

States: NORMAL → CONFIRMING → ESCALATED, with CONFIRMING → NORMAL on user-cancel.
"""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class MonitorConfig:
    confirm_seconds: float = 45.0      # countdown before auto-escalation
    spo2_critical: float = 88.0        # sustained SpO2 below -> alarm
    hr_high: float = 150.0             # sustained tachy at rest
    hr_low: float = 35.0               # brady
    fall_confidence: float = 0.75      # min fall confidence to open the window

@dataclass
class EmergencyMonitor:
    cfg: MonitorConfig = field(default_factory=MonitorConfig)
    state: str = "NORMAL"
    trigger: dict | None = None
    opened_at: float | None = None
    last_vitals: dict = field(default_factory=dict)
    still_immobile: bool = True        # updated by motion input during the window

    def _open(self, reason, detail, now, severity):
        if self.state == "ESCALATED":
            return self.status(now)
        self.state = "CONFIRMING"
        self.trigger = {"reason": reason, "detail": detail, "severity": severity}
        self.opened_at = now
        self.still_immobile = True
        return self.status(now)

    def on_fall(self, event: dict, now: float):
        if event.get("fall") and event.get("confidence", 0) >= self.cfg.fall_confidence and self.state == "NORMAL":
            return self._open("fall_detected", event, now, "high")
        return self.status(now)

    def on_vitals(self, hr=None, spo2=None, now: float = 0.0, at_rest: bool = True):
        self.last_vitals = {"hr": hr, "spo2": spo2}
        if self.state != "NORMAL":
            return self.status(now)
        if spo2 is not None and spo2 < self.cfg.spo2_critical:
            return self._open("hypoxemia", {"spo2": spo2}, now, "high")
        if hr is not None and at_rest and (hr > self.cfg.hr_high or hr < self.cfg.hr_low):
            return self._open("heart_rate_alarm", {"hr": hr}, now, "high")
        return self.status(now)

    def on_motion(self, moving: bool):
        if moving:
            self.still_immobile = False     # movement is a sign of responsiveness

    def user_respond(self, ok: bool, now: float = 0.0):
        """User tapped 'I'm OK' (ok=True -> cancel) or 'Get help' (ok=False -> escalate now)."""
        if self.state != "CONFIRMING":
            return self.status(now)
        if ok:
            self.state, self.trigger, self.opened_at = "NORMAL", None, None
        else:
            self._escalate(now, forced=True)
        return self.status(now)

    def tick(self, now: float):
        """Call periodically. Auto-escalates if the window expired (+ immobility for falls)."""
        if self.state == "CONFIRMING" and now - self.opened_at >= self.cfg.confirm_seconds:
            if self.trigger["reason"] == "fall_detected" and not self.still_immobile:
                # moved during the window -> treat as recovered, stand down
                self.state, self.trigger, self.opened_at = "NORMAL", None, None
            else:
                self._escalate(now)
        return self.status(now)

    def _escalate(self, now, forced=False):
        self.state = "ESCALATED"
        self.alert_payload = {
            "reason": self.trigger["reason"], "severity": self.trigger["severity"],
            "triggered_at": self.opened_at, "escalated_at": now, "forced_by_user": forced,
            "vitals": self.last_vitals, "detail": self.trigger.get("detail"),
            "location": None,  # filled by the app from device GPS at send time
            "message": self._message(),
            "delivery": "PREPARED — the app sends this to the user's emergency contacts with their consent; this module does not send.",
        }

    def _message(self):
        r = self.trigger["reason"].replace("_", " ")
        return (f"Telomy detected a possible emergency ({r}). The wearer did not respond within "
                f"{int(self.cfg.confirm_seconds)}s. Vitals: {self.last_vitals}. Please check on them "
                f"or call emergency services.")

    def status(self, now: float = 0.0):
        s = {"state": self.state, "trigger": self.trigger}
        if self.state == "CONFIRMING":
            s["seconds_left"] = round(max(0.0, self.cfg.confirm_seconds - (now - self.opened_at)), 1)
        if self.state == "ESCALATED":
            s["alert_payload"] = getattr(self, "alert_payload", None)
        return s

if __name__ == "__main__":
    import json
    from .falldetect import detect_fall
    cfg = MonitorConfig(confirm_seconds=45)
    print("=== scenario A: real fall, no response -> escalates ===")
    m = EmergencyMonitor(cfg)
    m.on_fall({"fall": True, "confidence": 0.98}, now=0)
    print(" t=0 ", m.status(0))
    print(" t=46", json.dumps(m.tick(46)["alert_payload"]["message"]))
    print("=== scenario B: fall, user taps I'm OK -> cancels ===")
    m = EmergencyMonitor(cfg); m.on_fall({"fall": True, "confidence": 0.9}, 0)
    print(" after I'm OK:", m.user_respond(ok=True, now=10)["state"])
    print("=== scenario C: SpO2 crash -> escalates ===")
    m = EmergencyMonitor(cfg); m.on_vitals(spo2=84, now=0)
    print(" state:", m.status(0)["state"], "-> t=46:", m.tick(46)["state"])
    print("=== scenario D: fall but user moves during window -> stands down ===")
    m = EmergencyMonitor(cfg); m.on_fall({"fall": True, "confidence": 0.9}, 0); m.on_motion(True)
    print(" t=46:", m.tick(46)["state"])
