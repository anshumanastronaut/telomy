"""Curated protein/fibre/fat fix — targets, biomarker tuning, gut tuning, and the renal safety gate."""
from app.llx import macros as m


def test_protein_scales_with_weight_and_goal():
    out = m.prescribe({"weight_kg": 80, "age": 40, "sex": "M", "activity": "active", "goals": ["muscle"]}, {})
    lo, hi = out["protein"]["target_g_per_kg"]
    assert hi >= 1.6                      # training/muscle → higher end
    assert out["protein"]["target_g_per_day"][1] == round(80 * hi)
    assert out["protein"]["doctor_gate"] is False


def test_renal_restricts_protein_and_gates():
    out = m.prescribe({"weight_kg": 62, "age": 70, "sex": "F", "goals": ["longevity"], "conditions": ["CKD"]},
                      {"egfr": 48})
    assert out["protein"]["target_g_per_kg"] == [0.6, 0.8]
    assert out["protein"]["doctor_gate"] is True
    assert out["doctor_gate"]["status"] == "pending_validation"
    assert any("KDIGO" in r for r in out["protein"]["rationale"])


def test_fibre_emphasis_follows_biomarkers_and_gut():
    out = m.prescribe({"weight_kg": 82, "sex": "M", "age": 46}, {"apob": 110, "hba1c": 6.0}, {"fibre_g_per_day": 14}, {"bristol": 2})
    emph = " ".join(out["fibre"]["emphasis"]).lower()
    assert "soluble" in emph and "insoluble" in emph        # ApoB→soluble, constipation→insoluble
    assert out["fibre"]["titration"] is not None             # big gap from 14 → titrate
    assert any("ApoB" in r or "LDL" in r for r in out["fibre"]["rationale"])


def test_ibs_biases_low_fodmap():
    out = m.prescribe({"weight_kg": 70, "sex": "F"}, {}, {}, {"conditions": ["IBS"], "bloating": True})
    assert any("fodmap" in e.lower() for e in out["fibre"]["emphasis"])


def test_fat_fix_targets_the_lipid_problem():
    out = m.prescribe({"weight_kg": 80, "sex": "M"}, {"apob": 110, "trig": 200, "omega3_index": 4})
    fix = " ".join(out["fat"]["fix"]).lower()
    assert "saturated" in fix and "omega-3" in fix
    assert any("triglyceride" in r.lower() for r in out["fat"]["rationale"])


def test_every_block_carries_rationale():
    out = m.prescribe({"weight_kg": 70, "sex": "F", "age": 50}, {})
    for k in ("protein", "fibre", "fat"):
        assert out[k]["rationale"], f"{k} missing rationale"
    assert "cure" not in out["disclaimer"].lower()
