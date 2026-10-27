"""Telomy intake & personalization — know the whole person, then nudge gently.

At sign-up the user may share everything, in any form: speak, type, or upload photos / videos / reports.
This builds one structured, consented profile (habits, routines, activity, diet, sleep, goals,
conditions, meds). The profile + biomarkers drive (a) the supplement & report engines and (b) a
"slow introduction" nudge engine that suggests ONE small, achievable step at a time so the user becomes
health-conscious gradually rather than being overwhelmed.

Privacy: "share everything" is explicit opt-in, per-category consent, and data stays on-device by
default (DPDP). Nothing here transmits or decides unilaterally.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

PROFILE_SECTIONS = ["demographics", "diet", "sleep", "activity", "substances", "stress", "routine",
                    "goals", "conditions", "medications", "allergies", "family_history", "preferences"]

@dataclass
class Profile:
    data: dict = field(default_factory=lambda: {s: None for s in PROFILE_SECTIONS})
    consent: dict = field(default_factory=dict)          # per-category opt-in
    sources: list = field(default_factory=list)          # provenance of each ingested item

    def set(self, section, value, source="manual"):
        if section in self.data:
            self.data[section] = value
            self.sources.append({"section": section, "source": source})

# --- multimodal ingestion -------------------------------------------------
# Each modality is normalised to text/fields then merged. Heavy extractors live in sister packages
# (telomy-vision imaging.ocr_report for reports, an ASR for voice, frame-sampling for video); this
# layer defines the contract + a working keyword extractor so the pipeline runs end-to-end today.
_KEYWORDS = {
    "diet": ["vegetarian", "vegan", "non-veg", "eggetarian", "jain", "keto", "fasting", "sugar", "junk"],
    "sleep": ["sleep", "bedtime", "insomnia", "wake", "nap", "snore"],
    "activity": ["walk", "run", "gym", "yoga", "sedentary", "steps", "workout", "sport", "cycling"],
    "substances": ["smoke", "cigarette", "alcohol", "drink", "tobacco", "vape"],
    "stress": ["stress", "anxious", "anxiety", "burnout", "relax", "meditat"],
    "routine": ["morning", "night shift", "wake up", "schedule", "commute", "desk job"],
    "goals": ["lose weight", "muscle", "energy", "longevity", "sleep better", "diabetes", "fitness"],
    "conditions": ["diabetes", "hypertension", "thyroid", "pcos", "asthma", "cholesterol"],
}

def ingest(profile: Profile, kind: str, content: str, consent: bool = True) -> dict:
    """kind: 'text'|'voice'|'image'|'report'|'video'. Returns the fields extracted and merged.

    text/voice      -> keyword/field extraction (voice is transcribed upstream by ASR).
    report/image    -> OCR + structure via telomy-vision imaging.ocr_report (biomarkers, meds).
    video           -> sample frames -> image pipeline (e.g., a food video, a gait clip).
    """
    if not consent:
        return {"skipped": "no consent for this item"}
    found = {}
    if kind in ("text", "voice"):
        low = content.lower()
        for section, kws in _KEYWORDS.items():
            hits = [k for k in kws if k in low]
            if hits:
                found[section] = hits
                prev = profile.data.get(section) or []
                profile.set(section, sorted(set((prev if isinstance(prev, list) else []) + hits)), kind)
    elif kind in ("report", "image"):
        found = {"_pipeline": "telomy-vision imaging.ocr_report -> structured biomarkers/meds (OCR)"}
        profile.sources.append({"section": "report", "source": kind})
    elif kind == "video":
        found = {"_pipeline": "sample frames -> image pipeline (food/gait/activity)"}
        profile.sources.append({"section": "video", "source": kind})
    return {"kind": kind, "extracted": found}

# --- completeness + gentle nudges -----------------------------------------
def completeness(profile: Profile) -> dict:
    filled = [s for s in PROFILE_SECTIONS if profile.data.get(s)]
    missing = [s for s in PROFILE_SECTIONS if not profile.data.get(s)]
    return {"score": round(len(filled) / len(PROFILE_SECTIONS), 2), "filled": filled, "missing": missing}

# one step at a time, ordered by gentle-onboarding priority
_NUDGES = [
    ("sleep", "Mind telling me your usual bedtime and wake time? Sleep is the easiest lever to start with."),
    ("activity", "Roughly how active is your day? If it's mostly sitting, a 10-minute post-lunch walk is a great first step."),
    ("diet", "What does a normal day of eating look like? No judgement — it just helps me tailor things."),
    ("stress", "How are your stress levels lately? Even two minutes of slow breathing counts."),
    ("goals", "What's the one health goal you'd most like to reach? We'll build toward it gently."),
    ("substances", "Do you smoke or drink at all? Honest answers help me keep you safe with any suggestions."),
]

def next_nudge(profile: Profile, biomarker_flags: list | None = None) -> dict:
    """Return ONE small next step — a profile gap first, else a gentle habit tied to a biomarker flag."""
    comp = completeness(profile)
    for section, prompt in _NUDGES:
        if section in comp["missing"]:
            return {"type": "learn_about_you", "section": section, "message": prompt,
                    "why": "building your profile a little at a time"}
    if biomarker_flags:
        f = biomarker_flags[0]
        return {"type": "gentle_habit", "flag": f,
                "message": f"Your {f} is something we can nudge with a small habit — want one easy change to try this week?",
                "why": "introducing one change at a time, tied to your own data"}
    return {"type": "encourage", "message": "You're doing great — let's keep one small habit going this week."}

def profile_summary(profile: Profile) -> dict:
    return {"profile": {k: v for k, v in profile.data.items() if v}, "completeness": completeness(profile),
            "consented_categories": [k for k, v in profile.consent.items() if v], "sources": profile.sources}

if __name__ == "__main__":
    import json
    p = Profile()
    p.consent = {s: True for s in PROFILE_SECTIONS}
    print(ingest(p, "voice", "I have a desk job, mostly sedentary, I smoke sometimes and want more energy"))
    print(ingest(p, "text", "I'm vegetarian and my sleep is poor, I wake up at 6 for a long commute"))
    print("completeness:", completeness(p))
    print("next nudge:", json.dumps(next_nudge(p, biomarker_flags=["vitamin D"]), indent=2))
