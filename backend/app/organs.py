"""Complete per-organ biological-age fusion for the 3D twin.

Eight organs from the organ-aging framework — Heart, Metabolic, Liver, Kidney, Immune, Lung, Muscle & Bone, Brain
— each surfaced ONLY when enough of its own inputs are on file (graceful gating), from the best available method:
  • trained NHANES blood clocks (llx/organ_tools)  → Heart, Metabolic, Liver, Kidney, Immune
  • clinical formulas                              → Lung (spirometry), Muscle & Bone (ALMI/grip + BMD T-score)
  • imaging / plasma biomarker                     → Brain (MRI brain-age gap, else plasma NfL)

A RELATIVE signal (which system is aging faster), not a precise number. Decision-support, not a diagnosis. The
trained clocks sharpen over time (mortality-anchored retrain); the clinical organs become trained clocks as the
datasets are added (Phase 2). The twin + overview render whatever organs come back.
"""
from . import engine


def _status(accel):
    if accel is None:
        return None
    return "older" if accel > 2 else "younger" if accel < -2 else "on_track"


def _male(sex) -> bool:
    return bool(sex) and str(sex).lower().startswith("m")


def _lung(age, v):
    """Lung age from spirometry: FEV1 declines ~1 percentage-point of predicted per year of lung age, so 80 %
    predicted ≈ ~20 y older lungs (Morris & Temple 1985; GLI-2012 normed % predicted)."""
    fev1 = v("fev1_pct")
    if fev1 is None or age is None:
        return None
    la = max(18.0, min(95.0, age + (100.0 - fev1)))
    return {"organ": "lung", "label": "Lung", "organ_age": round(la, 1), "age_acceleration_years": round(la - age, 1),
            "status": _status(la - age), "source": "clinical", "confidence": "spirometry (FEV1 % predicted)"}


def _muscle_bone(age, sex, v):
    """Muscle & bone age. Muscle from DEXA ALMI (Baumgartner 1998) or grip strength (Dodds 2014); bone from the
    worse BMD T-score (ISCD). Averaged into one system age — appears if any input is present."""
    if age is None:
        return None
    ages = []
    almi = v("almi")
    if almi is not None:
        peak, decline = (8.5, 0.03) if _male(sex) else (6.8, 0.025)       # ALMI kg/m² per year post-peak ~30
        ages.append(30 + (peak - almi) / decline)
    else:
        grip = v("grip")
        if grip is not None:
            peak = 45.0 if _male(sex) else 27.0                           # grip kg peak ~35; ~0.3 kg/yr decline
            ages.append(35 + (peak - grip) / 0.3)
    ts = [t for t in (v("bmd_hip_t"), v("bmd_spine_t")) if t is not None]
    if ts:
        ages.append(30 - min(ts) * 12.0)                                  # ~ −1 T ≈ +12 y of bone age
    if not ages:
        return None
    mb = max(18.0, min(95.0, sum(ages) / len(ages)))
    return {"organ": "muscle_bone", "label": "Muscle & Bone", "organ_age": round(mb, 1),
            "age_acceleration_years": round(mb - age, 1), "status": _status(mb - age),
            "source": "clinical", "confidence": "ALMI / grip / BMD T-score"}


def _brain(age, v):
    """Brain age: an MRI brain-age gap when a report carries one, else plasma NfL (rises ~2.5 %/yr in adults).
    Gated — only appears with a brain-specific input; routine bloods don't produce a brain age."""
    if age is None:
        return None
    try:
        from . import bioage
        for o in bioage.organ_ages(age):
            if o.get("organ") == "brain" and o.get("gap_years") is not None:
                ba = max(18.0, min(95.0, age + o["gap_years"]))
                return {"organ": "brain", "label": "Brain", "organ_age": round(ba, 1),
                        "age_acceleration_years": round(o["gap_years"], 1), "status": _status(o["gap_years"]),
                        "source": "imaging", "confidence": "MRI brain-age gap"}
    except Exception:  # noqa: BLE001
        pass
    nfl = v("nfl")
    if nfl is not None and nfl > 0:
        import math
        try:                                                              # expected plasma NfL ≈ 5·1.025^(age−30) pg/mL
            implied = max(18.0, min(95.0, 30 + math.log(nfl / 5.0) / math.log(1.025)))
            return {"organ": "brain", "label": "Brain", "organ_age": round(implied, 1),
                    "age_acceleration_years": round(implied - age, 1), "status": _status(implied - age),
                    "source": "biomarker", "confidence": "plasma NfL (coarse)"}
        except ValueError:
            pass
    return None


def organ_ages_for_member() -> dict:
    """All eight organs for the signed-in member; each present only when its data is on file (graceful gating)."""
    from .llx import organ_tools
    from . import telomy_ml
    age = engine.age_on()
    prof = engine.profile() or {}
    sex = prof.get("sex")
    panel = telomy_ml._panel()
    if sex:
        panel["sex"] = 1 if _male(sex) else 2
    lv = engine.latest_values() or {}

    def v(key):
        r = lv.get(key)
        x = r.get("value_num") if r else None
        try:
            return float(x) if x is not None else None
        except (TypeError, ValueError):
            return None

    organs = []
    # 1–5: trained NHANES blood clocks (each gated inside organ_tools on marker count). cardiometabolic → Heart.
    if organ_tools.available():
        relabel = {"cardiometabolic": "Heart", "metabolic": "Metabolic", "hepatic": "Liver",
                   "renal": "Kidney", "immune": "Immune"}
        for o in organ_tools.organ_ages(panel, chronological_age=float(age) if age else None).get("organs", []):
            o2 = {**o, "label": relabel.get(o["organ"], o["label"]), "source": "trained", "confidence": "blood (NHANES)"}
            if o["organ"] == "cardiometabolic":
                o2["organ"] = "heart"
            organs.append(o2)
    # 6–8: clinical / imaging organs, each gated on its own inputs. Clamp their acceleration to ±30 y — these are
    # coarse single-input estimates (esp. exponential NfL), and a larger displayed number would overclaim precision.
    for r in (_lung(age, v), _muscle_bone(age, sex, v), _brain(age, v)):
        if not r:
            continue
        if age is not None and r.get("age_acceleration_years") is not None and abs(r["age_acceleration_years"]) > 30:
            r["age_acceleration_years"] = round(max(-30.0, min(30.0, r["age_acceleration_years"])), 1)
            r["organ_age"] = round(age + r["age_acceleration_years"], 1)
            r["status"] = _status(r["age_acceleration_years"])
        organs.append(r)

    organs.sort(key=lambda r: -(r.get("age_acceleration_years") or 0))
    return {"chronological_age": round(age, 1) if age else None, "organs": organs,
            "note": "Per-organ biological ages — each system appears once enough of its data is on file. A relative "
                    "signal (which system is aging faster), not a precise number. Decision-support, not a diagnosis.",
            "source": "Telomy organ clocks (trained blood + clinical)"}
