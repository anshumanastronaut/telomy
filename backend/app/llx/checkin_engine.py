"""Proactive check-in engine — trust-first, self-tuning JITAI prompts.

Decides WHEN and WHAT to ask the user during the day (hydration, mood, symptom follow-up, protocol
adherence, encouragement), grounded in JITAI / EMA / notification-fatigue research:
  • RECEPTIVITY FIRST — never prompt in quiet hours, within the min gap, over the daily cap, or when the
    user is flagged busy / driving / sleeping / mid-session, or while snoozed. (Ill-timed prompts destroy
    trust.)
  • EVENT-TRIGGERED > random — fire on a real signal (voice-arousal spike, RHR/HRV spike, long sedentary,
    a symptom mention, a due protocol) rather than nagging; a little rate-limited random EMA for data.
  • SELF-TUNING CONFIDENCE — every prompt type tracks precision (did the user confirm it was useful?) and
    the engine's overall response-rate. Low-confidence triggers get a higher bar; a falling response-rate
    cuts frequency. This is the trust / confidence factor: the engine earns the right to interrupt.
  • USER CONTROL + TRANSPARENCY — conservative defaults (~3/day), adjustable quiet hours & frequency,
    snooze, and a plain "why" on every prompt.
Nothing here sends a notification; it RETURNS the decision (the app delivers it on-device).
"""
from __future__ import annotations
from dataclasses import dataclass, field

# prompt library: type -> template + why + base value (0..1) + whether it's safety-critical (bypasses tuning)
PROMPTS = {
    "hydration":   {"msg": "Quick one — had any water in the last couple of hours?", "why": "staying ahead of dehydration (affects HR, energy)", "value": 0.4},
    "mood_ema":    {"msg": "How are you feeling right now, 1–5?", "why": "a quick read to tie mood to your day's signals", "value": 0.5},
    "stress_check":{"msg": "Your voice sounded a bit tense — want a 2-minute breathing reset?", "why": "we detected elevated arousal vs your baseline", "value": 0.7},
    "sedentary":   {"msg": "You've been still a while — a short walk? (great for glucose + mood)", "why": "long sedentary stretch detected", "value": 0.5},
    "symptom_fu":  {"msg": "Earlier you mentioned feeling off — want to log it to your Vault for your doctor?", "why": "a symptom came up in conversation", "value": 0.8},
    "protocol_due":{"msg": "Gentle nudge: your {item} is due today — done it yet?", "why": "keeps your n-of-1 protocol on track", "value": 0.6},
    "alcohol_reconfirm": {"msg": "Logging check: anything to drink (alcohol) today?", "why": "it shifts your overnight RHR/HRV — helps us read tomorrow", "value": 0.5},
    "encourage":   {"msg": "Nice — your resting HR is trending down this week. Keep going.", "why": "positive reinforcement from a real trend", "value": 0.6},
}
_SAFETY = {"symptom_fu"}   # always allowed to surface (still receptivity-gated, never tuned away)

@dataclass
class CheckinConfig:
    max_per_day: int = 3            # conservative default; user can raise
    min_gap_min: int = 90
    quiet_start: int = 21           # 9pm
    quiet_end: int = 8              # 8am
    random_ema_per_day: int = 1

@dataclass
class CheckinEngine:
    cfg: CheckinConfig = field(default_factory=CheckinConfig)
    sent_today: int = 0
    last_sent_min: int | None = None     # minutes-since-midnight of last prompt
    snoozed_until_min: int | None = None
    random_ema_today: int = 0
    stats: dict = field(default_factory=dict)   # type -> {asked, answered, confirmed}

    # ---- receptivity gate ----
    def receptive(self, now_min: int, context: dict) -> bool:
        q = self.cfg
        hr = (now_min // 60) % 24
        in_quiet = (q.quiet_start <= hr or hr < q.quiet_end) if q.quiet_start > q.quiet_end else (q.quiet_start <= hr < q.quiet_end)
        if in_quiet: return False
        if self.snoozed_until_min and now_min < self.snoozed_until_min: return False
        if self.sent_today >= q.max_per_day: return False
        if self.last_sent_min is not None and (now_min - self.last_sent_min) < q.min_gap_min: return False
        if any(context.get(flag) for flag in ("driving", "sleeping", "busy", "in_session", "do_not_disturb")): return False
        return True

    def confidence(self, ptype: str) -> float:
        s = self.stats.get(ptype, {})
        asked = s.get("asked", 0)
        return (s.get("confirmed", 0) + 1) / (asked + 2)   # Laplace-smoothed precision (starts ~0.5)

    def response_rate(self) -> float:
        a = sum(s.get("asked", 0) for s in self.stats.values())
        ans = sum(s.get("answered", 0) for s in self.stats.values())
        return (ans + 1) / (a + 2)

    def trust_score(self) -> float:
        """Composite 'confidence factor': response-rate x mean trigger-confidence, lightly penalised for over-asking."""
        if not self.stats: return 0.5
        mc = sum(self.confidence(t) for t in self.stats) / len(self.stats)
        over = min(1.0, self.sent_today / max(1, self.cfg.max_per_day))
        return round(self.response_rate() * mc * (1 - 0.15 * over), 3)

    # ---- the decision ----
    def decide(self, now_min: int, context: dict, signals: dict) -> dict | None:
        if not self.receptive(now_min, context):
            return None
        rr = self.response_rate()
        bar = 0.35 if rr >= 0.5 else 0.55     # if the user isn't responding, only fire high-confidence prompts
        cands = []
        # event triggers from live signals
        if signals.get("voice_arousal_elevated"): cands.append("stress_check")
        if signals.get("symptom_mentioned"):      cands.append("symptom_fu")
        if signals.get("sedentary_minutes", 0) >= 90: cands.append("sedentary")
        if signals.get("rhr_above_baseline"):     cands.append("stress_check")
        if signals.get("protocol_due"):           cands.append("protocol_due")
        if signals.get("positive_trend"):         cands.append("encourage")
        # occasional data EMA when nothing else + budget left
        if not cands and self.random_ema_today < self.cfg.random_ema_per_day:
            cands += ["mood_ema", "hydration", "alcohol_reconfirm"][:1]
        # rank by confidence x value; safety prompts bypass the confidence bar
        best, best_score = None, -1
        for t in cands:
            score = self.confidence(t) * PROMPTS[t]["value"]
            allowed = (t in _SAFETY) or self.confidence(t) >= bar
            if allowed and score > best_score:
                best, best_score = t, score
        if not best:
            return None
        self.sent_today += 1; self.last_sent_min = now_min
        if best in ("mood_ema", "hydration", "alcohol_reconfirm"): self.random_ema_today += 1
        self.stats.setdefault(best, {"asked": 0, "answered": 0, "confirmed": 0})["asked"] += 1
        p = PROMPTS[best]
        msg = p["msg"].format(item=signals.get("protocol_item", "session")) if "{item}" in p["msg"] else p["msg"]
        return {"type": best, "message": msg, "why": p["why"], "options": ["Yes", "No", "Snooze", "Not now"],
                "trust_score": self.trust_score()}

    # ---- learning + user control ----
    def record(self, ptype: str, answered: bool, confirmed_useful: bool | None = None):
        s = self.stats.setdefault(ptype, {"asked": 0, "answered": 0, "confirmed": 0})
        if answered: s["answered"] += 1
        if confirmed_useful: s["confirmed"] += 1
        return {"type": ptype, "confidence": round(self.confidence(ptype), 3), "trust_score": self.trust_score()}

    def snooze(self, now_min: int, hours: float = 2): self.snoozed_until_min = now_min + int(hours * 60)
    def set_frequency(self, per_day: int): self.cfg.max_per_day = max(0, per_day)
    def set_quiet_hours(self, start: int, end: int): self.cfg.quiet_start, self.cfg.quiet_end = start, end
    def new_day(self): self.sent_today = 0; self.last_sent_min = None; self.random_ema_today = 0

if __name__ == "__main__":
    import json
    e = CheckinEngine()
    print("quiet hours (2am):", e.decide(2 * 60, {}, {"voice_arousal_elevated": True}))   # None
    print("driving:", e.decide(14 * 60, {"driving": True}, {"symptom_mentioned": True}))   # None
    p1 = e.decide(14 * 60, {}, {"voice_arousal_elevated": True}); print("\nstress trigger:", json.dumps(p1))
    print("too soon (30m later):", e.decide(14 * 60 + 30, {}, {"sedentary_minutes": 120}))  # None (min gap)
    p2 = e.decide(16 * 60, {}, {"symptom_mentioned": True}); print("symptom (safety):", json.dumps(p2))
    print("\nuser confirms stress prompt was useful:", e.record("stress_check", answered=True, confirmed_useful=True))
    print("over daily cap now:", e.decide(18 * 60, {}, {"positive_trend": True}))           # None (cap=3)
