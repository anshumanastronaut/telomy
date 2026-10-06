import glob
import os
import tempfile

os.environ["TELOMY_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["TELOMY_TODAY"] = "2026-10-06"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db, engine, food, seed  # noqa: E402
from app.labparse import parse_pdf  # noqa: E402
from app.main import app  # noqa: E402

LABS = os.path.join(os.path.dirname(__file__), "..", "..", "testdata", "lab_reports")


@pytest.fixture(scope="module")
def client():
    seed.run(reset=True)
    with TestClient(app) as c:
        yield c


def parsed(name):
    path = glob.glob(os.path.join(LABS, name))[0]
    return parse_pdf(open(path, "rb").read())


# ---------------------------------------------------------------- parser

@pytest.mark.parametrize("name,panel,n,date", [
    ("01_*", "blood", 34, "2026-07-02"), ("02_*", "blood", 34, "2026-10-01"), ("03_*", "gut", 17, "2026-09-18"),
    ("04_*", "genetic", 14, "2026-03-11"), ("05_*", "bioage", 8, "2026-09-25"), ("06_*", "metals", 8, "2026-08-14"),
    ("07_*", "toxins", 11, "2026-08-14"), ("08_*", "advanced", 16, "2026-09-30"), ("09_*", "fitness", 10, "2026-09-12"),
    ("10_*", "bodycomp", 6, "2026-07-20"), ("11_*", "bodycomp", 6, "2026-09-28"), ("12_*", "ct", 6, "2026-08-02"),
    ("13_*", "mri", 6, "2026-08-30"), ("14_*", "screening", 7, "2026-09-05"), ("15_*", "proteomic", 8, "2026-09-25")])
def test_parser_routes_and_counts(name, panel, n, date):
    p = parsed(name)
    assert p["panel"] == panel and len(p["markers"]) == n and p["collected_on"] == date and p["is_test_data"]


def test_parser_keeps_report_values_and_ranges():
    m = {x["marker_id"]: x for x in parsed("02_*")["markers"]}
    assert m["hemoglobin"]["value"] == 14.6 and m["hemoglobin"]["ref_low"] == 13.0 and m["hemoglobin"]["ref_high"] == 17.0
    assert m["hscrp"]["value"] == 3.4 and m["hscrp"]["ref_high"] == 1.0 and m["hscrp"]["status"] == "out_of_range"
    assert m["hdl"]["flag"] == "L" and m["wbc"]["unit"] == "10³/µL"


def test_genotypes_are_variants_not_outliers():
    m = {x["marker_id"]: x for x in parsed("04_*")["markers"]}
    assert m["apoe"]["value"] == "ε3/ε4" and m["apoe"]["status"] == "variant"
    assert m["mthfr_a1298c"]["status"] == "typical"


# ---------------------------------------------------------------- history integrity (Nostavia defect 1–3)

def test_history_has_true_per_date_values(client):
    h = client.get("/vault/marker/hemoglobin").json()["history"]
    assert [(x["day"], x["value"]) for x in h] == [("2026-07-02", 14.9), ("2026-10-01", 14.6)]
    v = client.get("/vault/marker/vitd").json()["history"]
    assert [x["value"] for x in v] == [18.0, 22.0]
    assert v[0]["ref_text"] == "30 – 100"


def test_every_report_keeps_all_markers(client):
    counts = {r["filename"][:2]: r["markers"] for r in client.get("/reports").json()}
    assert counts == {"01": 34, "02": 34, "03": 17, "04": 14, "05": 8, "06": 8, "07": 11, "08": 16, "09": 10, "10": 6,
                      "11": 6, "12": 6, "13": 6, "14": 7, "15": 8}


def test_each_panel_has_its_own_data(client):
    for p in client.get("/vault/panels").json():
        assert p["markers"] > 0, p["panel"]


# ---------------------------------------------------------------- engine

def test_phenoage_reference_case():
    vals = {"albumin": 4.5, "creatinine": 0.98, "glucose": 104, "hscrp": 3.4, "lymph_pct": 29, "mcv": 92, "rdw": 13.1,
            "alp": 74, "wbc": 7.8}
    r = engine.phenoage(vals, 34.2)
    assert 30 < r["value"] < 40
    assert engine.phenoage({"albumin": 4.5}, 34)["value"] is None


def test_longevity_dial_uses_bioage_and_blood(client):
    la = client.get("/longevity").json()
    assert la["value"] is not None and la["pace"] == 1.12 and "phenoage_lab" in la["clocks"]
    assert len(la["history"]) == 2


def test_correlation_engine_recovers_seeded_effects(client):
    eff = {(e["event"], e["metric"]): e for e in engine.event_effects()}
    assert ("alcohol", "hrv") in eff and eff[("alcohol", "hrv")]["receipts"]["effect_d"] < 0
    assert ("late_meal", "deep_sleep") in eff
    assert ("workout_hard", "hrv") in eff
    assert ("stress", "sleep_hours") not in eff  # no effect was seeded → must not be reported


def test_cross_panel_rules_fire_with_evidence(client):
    titles = {i["receipts"]["rule"]: i for i in client.get("/insights?kind=cross_panel").json()}
    for rule in ("hcy_mthfr", "apoe_lipids", "glycaemia_genetics", "gut_inflammation", "liver"):
        assert rule in titles and len(titles[rule]["evidence"]) >= 2


def test_missing_inputs_lower_confidence_never_fabricate(client):
    cv = client.get("/domains/cardiovascular").json()
    if "VO2 max" in cv["missing"]:
        assert cv["coverage"] < 1
    db.exec_("DELETE FROM signals WHERE metric = 'hrv'")
    card = client.get("/home").json()["cards"][0]
    assert card["value"] is None and card["reason"]
    seed.run(reset=True)


def test_n_of_1_returns_honest_verdict(client):
    s = client.get("/studies").json()[0]
    assert s["result"]["verdict"] in ("Helped", "No reliable signal", "Possible negative")


# ---------------------------------------------------------------- API smoke

@pytest.mark.parametrize("path", ["/health", "/home", "/vault/panels", "/vault/panel/blood", "/vault/panel/genetic",
                                  "/vault/timeline", "/signals", "/signals/hrv?range=W", "/signals/sleep_score?range=Y",
                                  "/insights", "/protocols", "/today", "/menu", "/studies", "/consents",
                                  "/consents/history", "/shares", "/clinicians", "/appointments", "/brief", "/completeness",
                                  "/imaging", "/research", "/memories", "/meals", "/nutrition/trends", "/sessions",
                                  "/care/queue", "/domains/metabolic", "/profile", "/sinc/chats", "/reports"])
def test_get_endpoints(client, path):
    r = client.get(path)
    assert r.status_code == 200, r.text


def test_upload_flow(client):
    path = glob.glob(os.path.join(LABS, "03_*"))[0]
    with open(path, "rb") as fh:
        p = client.post("/labs/parse", files={"file": ("gut.pdf", fh, "application/pdf")}).json()
    assert p["panel"] == "gut" and p["duplicate_of"]
    r = client.post("/labs/save", json={**{k: p[k] for k in ("title", "panel", "collected_on", "markers")},
                                         "replace_id": p["duplicate_of"], "is_test_data": True}).json()
    assert r["markers"] == 17
    bad = client.post("/labs/parse", files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert bad.status_code == 400


def test_sinc_cross_report_answer_cites_evidence(client):
    r = client.post("/sinc/ask", json={"question": "What correlations do you see across all my lab reports?"}).json()
    assert r["chips"] and "!" not in r["answer"] and r["confidence"] > 0
    m = client.post("/sinc/ask", json={"question": "Should I take a statin for my ApoB?"}).json()
    assert m["medical"] and m["review_state"] == "awaiting" and "clinician" in m["answer"]
    d = client.post("/sinc/draft-for-clinician", json={"message_id": m["message_id"]}).json()
    assert d["insight_id"] in {i["id"] for i in client.get("/care/queue").json()}


def test_clinician_review_cycle(client):
    iid = client.get("/care/queue").json()[0]["id"]
    assert client.post(f"/insights/{iid}/review", json={"action": "rejected"}).status_code == 400
    r = client.post(f"/insights/{iid}/review", json={"action": "signed", "note": "Agree"}).json()
    assert r["review_state"] == "signed" and r["thread"][-1]["author"] == "Dr. Meera Rao"


def test_consent_revoke_is_recorded(client):
    client.post("/consents/research", json={"granted": True})
    r = client.post("/consents/research", json={"granted": False}).json()
    assert "deleted within 24 hours" in r["message"]
    h = [x for x in client.get("/consents/history").json() if x["purpose"] == "research"]
    assert [x["granted"] for x in h][:2] == [0, 1]


def test_supplement_event_suggests_study(client):
    r = client.post("/events", json={"kind": "supplement", "label": "Ashwagandha 600 mg"}).json()
    assert r["suggest"]["type"] == "n_of_1"
    s = client.post("/studies", json={"title": "Ashwagandha and HRV", "intervention": "Ashwagandha", "outcome": "hrv"}).json()
    assert s["min_detectable"] > 0


def test_meal_analysis():
    a = food.analyze("2 eggs, toast and a banana")
    assert len(a["items"]) == 3 and a["protein"] > 12 and a["confidence"] > 0.8
    assert food.analyze("xyzzy")["confidence"] == 0
    b = food.analyze("Chicken biryani and a coke")
    assert [i["food"] for i in b["items"]] == ["biryani", "soda"] and b["glucose_response"] == "sharp rise likely"


def test_brief_pdf_and_fhir(client):
    r = client.get("/brief/cardiology.pdf")
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"
    b = client.get("/brief/cardiology.json").json()
    assert b["resourceType"] == "Bundle" and len(b["entry"]) > 5 and b["meta"]["tag"][0]["code"] == "test-data"


# ---------------------------------------------------------------- extended modalities

def test_cross_modality_rules(client):
    rules = {i["receipts"]["rule"] for i in client.get("/insights?kind=cross_panel").json()}
    for r in ("cac_apob", "masld", "vat_metabolic", "osa", "brain_vascular", "fitness_reserve", "organ_age", "bf_methods", "omega3"):
        assert r in rules, r


def test_derived_markers(client):
    d = {x["id"]: x for x in client.get("/vault/derived").json()}
    assert round(d["tg_hdl"]["value"], 2) == round(182 / 38, 2)
    assert 0.5 < d["fib4"]["value"] < 1.3 and d["fib4"]["inputs"]["ast"] == 41.0
    assert "egfr_cr" in d and "egfr_cys" in d and "nlr" in d


def test_zones_are_personalised(client):
    m = client.get("/vault/marker/vo2max_lab").json()
    assert m["zone"]["label"] == "Below average" and m["evidence_grade"] == "B"
    assert client.get("/vault/marker/cac").json()["zone"]["label"] == "Mild plaque"
    assert client.get("/vault/marker/ast").json()["retest_prep"]


def test_risk_matrix_and_actions(client):
    r = {x["condition"]: x for x in client.get("/risks").json()}
    assert r["Fatty liver (MASLD)"]["level"] == "high" and r["Fatty liver (MASLD)"]["drivers"]
    assert r["Osteoporosis & fracture"]["level"] == "low"
    plan = client.get("/action-plan").json()
    assert plan["food"] and plan["lifestyle"]
    fish = next(a for a in plan["food"] if "Small oily fish" in a["title"])
    assert fish["avoid"] is None and "mercury" in fish["caution"]
    iron = [a for a in plan["supplement"] if a["title"] == "Iron"]
    assert not iron or iron[0]["avoid"]


def test_concerns_and_nudges(client):
    c = {x["concern"]: x for x in client.get("/vault/concerns").json()}
    assert c["Heart & arteries"]["flagged"] >= 3
    assert client.get("/nudges").json() == []  # everything out of range was tested recently
    later = client.get("/nudges?day=2027-01-20").json()
    assert later and later[0]["days_since"] > 100 and later[0]["markers"]


def test_rewind_uses_values_known_then(client):
    h = client.get("/home?as_of=2026-07-08").json()
    assert h["key_biomarker"]["value"] == 2.1 and h["key_biomarker"]["trend"] is None
    assert h["longevity"]["as_of"] == "2026-07-02"


def test_adjusted_effects_cover_ground_truth(client):
    """Seeded truths: alcohol→HRV −9, late meal→deep −0.35, sauna→deep +0.25, hard workout→HRV −6."""
    eff = {(e["event"], e["metric"]): e["receipts"] for e in engine.event_effects()}
    for key, truth in [(("alcohol", "hrv"), -9), (("late_meal", "deep_sleep"), -0.35), (("sauna", "deep_sleep"), 0.25),
                       (("workout_hard", "hrv"), -6)]:
        lo, hi = eff[key]["ci95"]
        assert lo - 0.05 <= truth <= hi + 0.05, (key, eff[key]["ci95"])
    sauna = eff[("sauna", "deep_sleep")]
    assert abs(sauna["adjusted_effect"]) < abs(sauna["unadjusted_effect"])  # confounding removed


def test_future_report_date_rejected(client):
    r = client.post("/labs/save", json={"title": "x", "panel": "blood", "collected_on": "2099-01-01", "markers": [
        {"marker_id": "ldl", "name": "LDL", "value": 100, "unit": "mg/dL", "ref_low": None, "ref_high": 100, "status": "in_range"}]})
    assert r.status_code == 400


def test_sinc_deep_research_cites_literature(client):
    r = client.post("/sinc/ask", json={"question": "What does my CT calcium score mean with my ApoB?", "mode": "deep"}).json()
    assert r["mode"] == "deep" and r["references"]
    assert any("Greenland" in x["citation"] or "Sniderman" in x["citation"] for x in r["references"])
    assert client.get("/evidence/rule/masld").json()


def test_calculators_and_sugar(client):
    c = client.get("/calculators").json()
    assert 1600 < c["bmr"]["value"] < 2000 and c["protein_target"]["value"] > 100 and c["macros"]["carbs"] > 0
    a = food.analyze("Chicken biryani and a coke")
    assert a["added_sugar"] >= 39 and a["pct_daily"]["added_sugar"] >= 150


# ---------------------------------------------------------------- iteration 3

def test_dashboard_and_categories(client):
    d = client.get("/dashboard").json()
    assert len(d["rings"]) == 3 and d["recovery"] is not None and len(d["heatmap"]) == 63
    cats = {c["name"]: c for c in client.get("/categories").json()}
    assert cats["Heart"]["markers"] > 5 and cats["Sleep"]["signals"] == 4
    assert client.get("/categories/Heart").json()["signals"]
    assert client.put("/pins", json=["hrv", "steps"]).json() == ["hrv", "steps"]
    assert client.put("/pins", json=["nope"]).status_code == 400


def test_meds_interactions_and_adherence(client):
    m = client.get("/meds").json()
    assert all(0 < x["adherence_30d"] <= 100 for x in m["items"])
    r = client.post("/meds", json={"name": "Levothyroxine", "dose": "50mcg"}).json()
    assert any("levothyroxine" in i["between"][0] for i in r["interactions"])
    assert client.post("/meds", json={"name": " "}).status_code == 400


def test_notifications_notes_stats_documents(client):
    n = client.get("/notifications").json()
    assert n and all("key" in x for x in n)
    client.post("/notifications/read", json=[n[0]["key"]])
    assert client.get("/notifications").json()[0]["read"]
    cn = client.get("/clinician-notes").json()
    assert len(cn["top"]) == 3 and "MASLD" in cn["tldr"]
    assert client.get("/sessions/stats").json()["sessions"] >= 9
    assert client.get("/documents").json()[0]["kind"] == "discharge"
    from app import features
    meds = features.extract_meds("Rx: Tab. Atorvastatin 10 mg OD at night\nTab. Metformin 500 mg BD")
    assert [m["name"] for m in meds] == ["Atorvastatin", "Metformin"] and meds[1]["times"] == ["08:00", "20:00"]
