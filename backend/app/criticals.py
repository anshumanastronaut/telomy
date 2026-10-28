"""Critical-value (panic-value) classification on lab ingest.

This is the patient-SAFETY tier described in research/intel/NOTIFICATIONS.md (Part D.2). Every lab-ingest path runs
`classify()` on each marker before notifying; a `critical` result drives the closed-loop critical notification
(patient U4 / doctor D1 / centre C1) and is written back onto results.status so the rest of the app can see it.

⚠️  CLINICAL SIGN-OFF REQUIRED. The thresholds below are *generic adult* panic values assembled as a working
default so the pipeline is correct end-to-end. They are NOT age/sex-specific and NOT tuned to Indian reference
ranges. Before this ships to real users a clinician must own this table (per NOTIFICATIONS.md Part E.5). Treat it
as data pending review, not settled medicine.

Posture (per the agreed recommendation): Telomy *routes to a clinician*, it does not *assert* criticality to the
patient. So the patient-facing copy never states the dangerous number — only that an important result needs
attention — while the clinician-facing alert carries the value. That split lives in notifs.py, not here.
"""

# marker_id -> {"low": panic-low (value <= low is critical), "high": panic-high (value >= high is critical), "unit": expected unit}
# Only markers that exist in catalog.MARKERS are meaningful; extras are harmless (classify only fires when present).
CRITICAL: dict[str, dict] = {
    "glucose":    {"low": 50,   "high": 450,  "unit": "mg/dL"},   # severe hypo- / hyperglycaemia
    "potassium":  {"low": 2.8,  "high": 6.0,  "unit": "mmol/L"},  # hypo-/hyperkalaemia (arrhythmia risk)
    "sodium":     {"low": 120,  "high": 160,  "unit": "mmol/L"},  # severe hypo-/hypernatraemia
    "calcium":    {"low": 6.5,  "high": 13.0, "unit": "mg/dL"},   # total calcium panic range
    "hemoglobin": {"low": 7.0,  "high": 20.0, "unit": "g/dL"},    # severe anaemia / polycythaemia
    "platelets":  {"low": 20,   "high": 1000, "unit": "10³/µL"},  # bleeding / thrombosis risk
    "wbc":        {"low": 1.0,  "high": 50.0, "unit": "10³/µL"},  # severe leukopenia / leukocytosis
    "creatinine": {"low": None, "high": 7.4,  "unit": "mg/dL"},   # acute renal failure range
}


def classify(marker_id: str, value_num, ref_low=None, ref_high=None) -> str | None:
    """Return 'critical' | 'out_of_range' | 'in_range', or None when it can't be judged.

    Critical takes precedence over the reference range. When no critical rule applies, fall back to the
    report's own reference interval (ref_low/ref_high) so we still flag plain out-of-range values (→ U3).
    """
    if not isinstance(value_num, (int, float)):
        return None
    c = CRITICAL.get(marker_id)
    if c is not None:
        lo, hi = c.get("low"), c.get("high")
        if (lo is not None and value_num <= lo) or (hi is not None and value_num >= hi):
            return "critical"
    if isinstance(ref_low, (int, float)) and value_num < ref_low:
        return "out_of_range"
    if isinstance(ref_high, (int, float)) and value_num > ref_high:
        return "out_of_range"
    if isinstance(ref_low, (int, float)) or isinstance(ref_high, (int, float)):
        return "in_range"
    return None


def is_critical(marker_id: str, value_num) -> bool:
    return classify(marker_id, value_num) == "critical"
