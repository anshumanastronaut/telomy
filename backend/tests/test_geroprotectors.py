"""Longevity-therapeutics corpus — recommender, safety gating, and n-of-1 trial designer."""
from app.llx import geroprotectors as g


def test_corpus_loads_and_is_graded():
    s = g.corpus_summary()
    assert s["total"] >= 30
    # every record has the required fields and a valid grade/status
    for iv in g.INTERVENTIONS:
        assert iv["grade"] in ("A", "B", "C", "D")
        assert iv["status"] in g.TIER
        for k in ("id", "name", "category", "scope", "mechanism", "effect", "dose", "caution", "triggers"):
            assert iv.get(k), f"{iv['id']} missing {k}"
        assert all(h in g.HALLMARKS for h in iv["hallmarks"])


def test_foundation_is_lifestyle_and_ranks_first_by_evidence():
    out = g.recommend({"age": 50, "goals": ["longevity"]}, {})
    assert out["ordering"][0] == "foundation"
    grades = [r["grade"] for r in out["tiers"]["foundation"]]
    assert grades == sorted(grades, key=lambda x: g.GRADE_ORDER[x])  # sorted best-evidence first
    # strongest lever surfaces for a longevity goal
    assert any(r["id"] == "aerobic_vo2max" for r in out["tiers"]["foundation"])


def test_biomarker_triggers_fire():
    out = g.recommend({"age": 45, "goals": ["longevity"]}, {"vitamin_d_25oh": 18, "trig": 200})
    opt = {r["id"] for r in out["tiers"]["optional"]}
    assert "vitamin_d" in opt and "omega3" in opt


def test_drug_interaction_is_flagged_not_blocked():
    out = g.recommend({"age": 45, "goals": ["longevity"], "medications": ["warfarin"]}, {"trig": 200})
    o3 = next(r for r in out["tiers"]["optional"] if r["id"] == "omega3")
    assert any("warfarin" in f for f in o3["safety_flags"])


def test_contraindication_blocks():
    # TRT must be blocked for a man with prostate cancer, not merely flagged
    out = g.recommend({"age": 55, "sex": "M", "goals": ["muscle"], "conditions": ["prostate cancer"]},
                      {"total_testosterone": 250})
    assert any(b["id"] == "trt" for b in out["blocked_by_contraindication"])
    assert all(r["id"] != "trt" for r in out["tiers"]["clinical"])


def test_growth_hormone_not_surfaced_proactively():
    # GH is explicitly steered away from (min_age 99 sentinel) — never in a proactive longevity list
    out = g.recommend({"age": 70, "sex": "M", "goals": ["longevity", "muscle", "energy"]}, {})
    all_ids = {r["id"] for tier in out["tiers"].values() for r in tier}
    assert "growth_hormone" not in all_ids


def test_experimental_can_be_excluded():
    out = g.recommend({"age": 60, "goals": ["longevity"]}, {}, include_experimental=False)
    assert out["tiers"]["experimental"] == []


def test_no_item_claims_lifespan():
    out = g.recommend({"age": 60, "goals": ["longevity"]}, {})
    assert "lifespan extension" in out["disclaimer"].lower()
    for tier in out["tiers"].values():
        for r in tier:
            assert "cure" not in r["effect"].lower()


def test_trial_designer_gates_drugs():
    t = g.design_trial("rapamycin", {"age": 50})
    assert t["doctor_gate"] is True
    assert "clinician" in t["washout_rechallenge"].lower()  # don't self-stop a drug
    assert t["retest_at_weeks"] >= 8 and t["primary_markers"]


def test_trial_designer_marks_ineligible_on_contraindication():
    t = g.design_trial("rapamycin", {"age": 50, "conditions": ["active infection"]})
    assert t["eligible"] is False
    assert any("active infection" in f for f in t["safety_flags"])


def test_lifestyle_trial_allows_washout_rechallenge():
    t = g.design_trial("omega3", {"age": 50})
    assert t["doctor_gate"] is False
    assert "re-start" in t["washout_rechallenge"]


# ── FAERS data-backed safety layer (only runs once the asset has been built) ──────────────────────────
import pytest
from app.llx import faers_safety as fs


@pytest.mark.skipif(not fs.available(), reason="FAERS signals asset not built in this environment")
def test_faers_signals_attach_to_drugs():
    out = g.recommend({"age": 55, "sex": "M", "goals": ["metabolic", "longevity"]}, {"hba1c": 6.2})
    metformin = next((r for tier in out["tiers"].values() for r in tier if r["id"] == "metformin"), None)
    assert metformin is not None
    assert metformin.get("faers_safety"), "metformin should carry FAERS signals when the asset exists"
    sig = metformin["faers_safety"]
    assert sig["total_corpus"] >= 10_000_000          # mined from the full ~20.7M-report corpus
    assert all(len(s["ror_95ci"]) == 2 for s in sig["top_signals"])


@pytest.mark.skipif(not fs.available(), reason="FAERS signals asset not built in this environment")
def test_faers_feeds_trial_watchlist():
    t = g.design_trial("rapamycin", {"age": 55})
    assert t["faers_watch"] is None or isinstance(t["faers_watch"], list)


@pytest.mark.skipif(not fs.available(), reason="FAERS signals asset not built in this environment")
def test_supplements_have_no_faers_but_dont_break():
    out = g.recommend({"age": 55, "goals": ["longevity"]}, {})
    for tier in out["tiers"].values():
        for r in tier:
            if r["category"] == "supplement":
                assert "faers_safety" not in r or r["faers_safety"] is None
