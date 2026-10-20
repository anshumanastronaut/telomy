"""Personal Health Agent — the always-on, privacy-first layer (Omi-style).

The app captures audio on-device with the user's explicit, revocable consent. Each "moment" is processed
locally into DERIVED signals only — a voice-arousal index + extracted health mentions — and the raw audio
and transcript are DROPPED unless the user opts to keep them. The agent builds the person's profile over
time, flags stress patterns, ties them to the wearable/biomarker engines, and surfaces gentle nudges.

Privacy contract (enforced here):
  • consent is required and per-session; `pause()` stops processing; `forget(since)` erases moments.
  • raw audio/transcript are never stored by default — only {arousal index, extracted mentions}.
  • nothing is sent externally; this runs beside the on-device model.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from .voice_biomarkers import features, build_baseline, arousal_index
from .intake import Profile, ingest

# lightweight health-entity extraction from a transcript (symptoms/meals/mood/sleep/activity/meds)
_ENTITIES = {
    "symptom": ["headache", "tired", "fatigue", "dizzy", "nausea", "pain", "cramp", "palpitation", "breathless", "bloated"],
    "mood": ["stressed", "anxious", "calm", "happy", "low", "irritable", "overwhelmed", "relaxed"],
    "sleep": ["slept", "insomnia", "woke", "nap", "restless", "bedtime"],
    "meal": ["ate", "lunch", "dinner", "breakfast", "coffee", "alcohol", "sugar", "protein", "fasting"],
    "activity": ["walked", "ran", "gym", "workout", "yoga", "sedentary", "steps"],
    "medication": ["took", "dose", "supplement", "vitamin", "medicine"],
}

@dataclass
class PersonalHealthAgent:
    profile: Profile = field(default_factory=Profile)
    consent: bool = False
    active: bool = True
    keep_transcript: bool = False
    voice_baseline: dict | None = None
    moments: list = field(default_factory=list)       # derived only

    # ---- privacy controls ----
    def grant_consent(self): self.consent = True
    def pause(self): self.active = False
    def resume(self): self.active = True
    def forget(self, since_ts: float = 0.0):
        self.moments = [m for m in self.moments if m["ts"] < since_ts]
        return {"remaining_moments": len(self.moments)}

    # ---- calibration ----
    def calibrate_voice(self, calm_waveforms, sr: int):
        self.voice_baseline = build_baseline([features(w, sr) for w in calm_waveforms])
        return self.voice_baseline

    # ---- the always-on observe loop ----
    def observe(self, ts: float | None = None, waveform=None, sr: int | None = None, transcript: str | None = None) -> dict:
        if not self.consent:
            return {"skipped": "no consent"}
        if not self.active:
            return {"skipped": "paused"}
        ts = ts if ts is not None else time.time()
        moment = {"ts": ts, "arousal": None, "mentions": {}}
        # voice -> arousal (raw audio dropped after feature extraction)
        if waveform is not None and sr:
            feat = features(waveform, sr)
            moment["arousal"] = arousal_index(feat, self.voice_baseline)
        # transcript -> health mentions -> profile (raw text dropped unless opted in)
        if transcript:
            low = transcript.lower()
            ment = {cat: [w for w in words if w in low] for cat, words in _ENTITIES.items()}
            moment["mentions"] = {k: v for k, v in ment.items() if v}
            ingest(self.profile, "voice", transcript, consent=True)  # updates structured profile
            if self.keep_transcript:
                moment["transcript"] = transcript
        self.moments.append(moment)
        moment["nudge"] = self._nudge()
        return moment

    def _nudge(self):
        recent = [m for m in self.moments[-5:] if m.get("arousal") and m["arousal"].get("index") is not None]
        elevated = [m for m in recent if m["arousal"]["index"] >= 1.0]
        if len(elevated) >= 3:
            return {"type": "stress_pattern", "message": "Your voice has read elevated a few times recently — "
                    "a 2-minute slow-breathing break now is a small, high-value reset.",
                    "ties_to": "pairs with your HRV/RHR trend in the wearable fusion engine"}
        mentions = [c for m in self.moments[-3:] for c in m.get("mentions", {})]
        if "symptom" in mentions:
            return {"type": "symptom_followup", "message": "I noted a symptom — want to log it to your Vault so "
                    "your doctor sees it, and check it against your recent biomarkers?"}
        return None

    def daily_summary(self, day_start: float, day_end: float) -> dict:
        day = [m for m in self.moments if day_start <= m["ts"] < day_end]
        ar = [m["arousal"]["index"] for m in day if m.get("arousal") and m["arousal"].get("index") is not None]
        allm = {}
        for m in day:
            for c, ws in m.get("mentions", {}).items():
                allm.setdefault(c, set()).update(ws)
        return {"moments": len(day), "mean_arousal": round(sum(ar) / len(ar), 2) if ar else None,
                "stress_episodes": sum(1 for z in ar if z >= 1.0), "mentions": {k: sorted(v) for k, v in allm.items()},
                "note": "derived signals only; feeds the daily n-of-1 audit + the intake profile"}

if __name__ == "__main__":
    import numpy as np, json
    sr = 16000
    def seg(f0, amp, voic, seed):
        r = np.random.default_rng(seed); t = np.arange(int(2.5 * sr)) / sr
        return amp * np.sin(2 * np.pi * f0 * t) * (r.random(len(t)) > voic)
    a = PersonalHealthAgent(); a.grant_consent()
    a.calibrate_voice([seg(119 + i, 0.3, 0.35, i) for i in range(5)], sr)
    print("no-consent check:", PersonalHealthAgent().observe(transcript="I feel tired")["skipped"])
    for i in range(3):
        m = a.observe(ts=1000 + i, waveform=seg(178, 0.6, 0.15, 50 + i), sr=sr,
                      transcript="I'm stressed and tired, slept badly, had too much coffee")
    print("latest moment:", json.dumps({k: m[k] for k in ("arousal", "mentions", "nudge")}, indent=2))
    print("profile learned:", {k: v for k, v in a.profile.data.items() if v})
    print("daily summary:", json.dumps(a.daily_summary(0, 2000), indent=2))
