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
    ("13_*", "mri", 6, "2026-08-30"), ("14_*", "screening", 7, "2026-09-05"), ("15_*", "proteomic", 8, "2026-09-25"),
    ("16_*", "hormones", 10, "2026-09-30"), ("17_*", "micronutrients", 11, "2026-10-01"), ("18_*", "cardio", 11, "2026-09-20"),
    ("19_*", "lung", 4, "2026-09-12"), ("20_*", "cgm", 6, "2026-10-06"), ("21_*", "immune", 7, "2026-09-30"),
    ("22_*", "urine", 6, "2026-10-01"), ("23_*", "screening", 2, "2026-09-18"), ("24_*", "functional", 6, "2026-09-22")])
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
                      "11": 6, "12": 6, "13": 6, "14": 7, "15": 8, "16": 10, "17": 11, "18": 11, "19": 4, "20": 6, "21": 7,
                      "22": 6, "23": 2, "24": 6}


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
    assert abs(sauna["adjusted_effect"] - 0.25) <= abs(sauna["unadjusted_effect"] - 0.25)  # adjustment moves toward the truth


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


# ---------------------------------------------------------------- roles & prediction

def test_pce_matches_guideline_examples():
    from app import predict
    m = predict.ascvd_pce(55, "male", 213, 50, 120)
    f = predict.ascvd_pce(55, "female", 213, 50, 120)
    assert abs(m["risk"] - 5.3) <= 0.2, m
    assert abs(f["risk"] - 2.1) <= 0.2, f
    assert predict.ascvd_pce(55, "male", None, 50, 120)["missing"] == ["total cholesterol"]


def test_prediction_models_and_what_if(client):
    p = client.get("/predict").json()["models"]
    assert p["cvd"]["risk"] is not None and any("calcium" in e for e in p["cvd"]["enhancers"])
    assert p["diabetes"]["risk"] >= 15 and p["liver"]["score"] < 1.3 and "not applicable" in p["kidney"]["band"]
    w = client.post("/predict/what-if", json={"tc": 170, "hdl": 55, "sbp": 115}).json()
    assert w["delta"]["cvd"]["to"] < w["delta"]["cvd"]["from"]
    from app import predict
    assert predict.kfre(70, "male", 35, 300)["risk"] > predict.kfre(70, "male", 55, 10)["risk"]
    assert predict.diabetes(50, "male", 31, 6.7, 130)["already"]


def test_doctor_views(client):
    pts = client.get("/doctor/patients").json()
    assert len(pts) >= 10 and pts == sorted(pts, key=lambda x: -x["priority"])
    me = client.get("/doctor/patients/1").json()
    assert me["full_vault"] and me["risk_map"] and me["notes"]
    other = client.get(f"/doctor/patients/{pts[0]['id']}").json()
    assert other["predictions"]["models"]["cvd"]
    assert client.post("/doctor/patients/3/notes", json={"text": "Start statin discussion"}).json()["ok"]
    assert client.post("/doctor/patients/3/notes", json={"text": " "}).status_code == 400
    assert client.get("/doctor/patients/999").status_code == 404
    t = client.get("/doctor/today").json()
    assert t["patients"] == len(pts) and "awaiting_reviews" in t


def test_centre_views(client):
    d = client.get("/centre/dashboard").json()
    assert d["members"] > 5 and d["today"] and d["utilisation"] and d["revenue_prev_month"] > 0
    assert client.get("/centre/members").json()
    o = client.get("/centre/services/sauna/outcomes").json()
    assert o["n"] >= 10 and o["hrv_after"] > o["hrv_other"]
    b = client.post("/centre/bookings", json={"patient_id": 6, "service_id": "dexa", "ts": "2026-10-09T13:00:00"}).json()
    assert b["id"]
    assert client.post("/centre/bookings", json={"patient_id": 7, "service_id": "dexa", "ts": "2026-10-09T13:00:00"}).status_code == 409
    assert client.post(f"/centre/bookings/{b['id']}/status", json={"status": "checked_in"}).json()["ok"]
    assert client.post(f"/centre/bookings/{b['id']}/status", json={"status": "weird"}).status_code == 400


def test_prevent_matches_reference_package():
    from app import predict
    r = predict.prevent(50, "female", 200, 45, 160, bp_treated=True, statin=False, diabetic=True, smoker=False, egfr=90, bmi=35)
    assert r["ten_year"] == {"total_cvd": 14.7, "ascvd": 9.2, "heart_failure": 8.1, "chd": 4.4, "stroke": 5.4}
    assert r["thirty_year"]["total_cvd"] == 53.0 and r["thirty_year"]["heart_failure"] == 39.0


def test_prevent_in_vault_and_what_if(client):
    m = client.get("/predict").json()["models"]["prevent"]
    assert m["ten_year"]["total_cvd"] > 0 and m["thirty_year"]["total_cvd"] > m["ten_year"]["total_cvd"]
    d = client.post("/predict/what-if", json={"sbp": 115, "statin": True}).json()["delta"]
    assert d["prevent_thirty_year"]["ascvd"]["to"] < d["prevent_thirty_year"]["ascvd"]["from"]


def test_plans_monthly_reports_and_consults(client):
    p = client.get("/plans").json()
    assert [x["id"] for x in p["plans"]] == ["free", "essential", "plus", "pro"] and p["test_mode"]
    reps = {r["period"]: r for r in client.get("/monthly-reports").json()}
    assert reps["2026-08"]["state"] == "signed" and reps["2026-09"]["state"] == "awaiting_doctor"
    r = client.get("/monthly-reports/2026-09").json()["data"]
    assert r["signals"] and r["priorities"] and r["actions"] and 0 < r["protocol_adherence"] <= 100
    assert client.post("/monthly-reports/2026-09/sign", json={"note": " "}).status_code == 400
    assert client.post("/monthly-reports/2026-09/sign", json={"note": "Looks good"}).json()["state"] == "signed"
    c1 = client.post("/consults", json={"kind": "gp", "mode": "video"}).json()
    row = next(c for c in client.get("/consults").json() if c["id"] == c1["id"])
    assert row["scheduled_at"] > row["requested_at"][:16]
    assert client.post("/consults", json={"kind": "dentist"}).status_code == 400
    assert client.post(f"/consults/{c1['id']}/complete", json={"notes": ""}).status_code == 400
    client.post("/subscription", json={"plan": "free"})
    assert client.post("/monthly-reports/2026-10/generate").status_code == 402
    client.post("/subscription", json={"plan": "plus", "billing": "year"})


# ---------------------------------------------------------------- therapies & in-session physiology

def test_ode_prior_reproduces_literature_targets():
    from app import physio
    r = physio.validate_prior(12)
    assert r["all_pass"], r


def test_session_analytics_on_device_samples(client):
    s = client.post("/therapy/sessions", json={"modality": "cryo", "params": {"chamber_c": -140}}).json()
    assert s["expected"]["source"].startswith("simulated")
    samples = []
    for t in range(0, 2000, 5):  # a real chest-strap style trace: baseline, 3-min cold, recovery
        cold = 300 <= t < 480
        rec = t >= 480
        samples.append({"t": t, "hr": 70 + (14 if cold else -3 if rec else 0), "rmssd": 40 * (0.65 if cold else 1.0 + (0.7 * (1 - 2.718 ** (-(t - 480) / 600)) if rec else 0)),
                        "skin": 33 - (10 * min(1, (t - 300) / 120) if cold else 10 * 2.718 ** (-(t - 480) / 700) if rec else 0), "spo2": 97.5})
    f = client.post(f"/therapy/sessions/{s['id']}/samples", json={"samples": samples, "source": "Polar H10 (test)"}).json()["features"]
    assert f["source"] == "Polar H10 (test)" and 12 <= f["hr_peak_delta"] <= 16 and f["rebound_pct"] > 40 and f["skin_drop"] < -8
    assert f["rewarm_half_min"] is not None and f["safety"]["tier"] == 0
    done = client.post(f"/therapy/sessions/{s['id']}/finish", json={"subjective": {"pre": {"energy": 5}, "post": {"energy": 7}}}).json()
    assert done["status"] == "completed"


def test_therapy_verdicts_match_seeded_truth(client):
    v = {r["modality"]: r["verdict"] for r in client.get("/therapy/working").json()}
    assert v["sauna"] == "helped"                                  # embedded +0.25 h deep sleep, +4 HRV
    assert v["pemf"] in ("helped", "promising") and v["cryo"] in ("helped", "promising")
    for m in ("hbot_mild", "redlight", "h2_inhal", "compression"):  # nothing embedded → never "helped"
        assert v[m] in ("no_signal", "too_early"), (m, v[m])
    assert v["iv"] == "too_early"


def test_safety_screen_uses_the_vault(client):
    s = {x["modality"]: x for x in client.get("/therapy/safety").json()["screen"]}
    assert s["cryo"]["status"] == "caution" and "CAC" in s["cryo"]["summary"]    # coronary plaque on CT
    assert s["ihht"]["status"] == "caution"                                       # sleep apnoea
    assert s["redlight"]["status"] == "ok"


def test_plan_needs_doctor_and_books_sessions(client):
    p = client.post("/therapy/plans", json={"goal": "sleep", "per_week": 4}).json()
    assert p["state"] == "awaiting_doctor" and p["plan"]["items"][0]["modality"] == "sauna"
    assert any(x["id"] == p["id"] for x in client.get("/doctor/work").json()["therapy_plans"])
    assert client.post(f"/therapy/plans/{p['id']}/decide", json={"approve": True, "note": " "}).status_code == 400
    d = client.post(f"/therapy/plans/{p['id']}/decide", json={"approve": True, "note": "Go ahead; recheck HRV at week 4."}).json()
    assert d["state"] == "active" and d["booked"] == 16
    assert client.post(f"/therapy/plans/{p['id']}/decide", json={"approve": True, "note": "again"}).status_code == 400


def test_hsai_and_floor_and_phenotypes(client):
    h = client.get("/therapy/hsai").json()
    assert h["available"] and 0 <= h["score"] <= 100 and h["range"][0] <= h["score"] <= h["range"][1]
    assert "not a diagnosis" in h["message"]
    floor = client.get("/centre/floor").json()
    assert len(floor["devices"]) >= 25
    ph = client.get("/centre/research/phenotypes").json()
    assert ph["n"] >= 8 and len(ph["groups"]) >= 2 and "Simulated" in ph["caveat"]


def test_new_report_rules_fire(client):
    keys = {i["receipts"].get("rule") for i in client.get("/insights").json() if i["kind"] == "cross_panel"}
    for k in ("masked_htn", "osa_nondipper", "thyroid_autoimmune", "cgm_a1c", "liver_fibrosis", "allergic_airway", "folate_hcy", "g6pd"):
        assert k in keys, k


# ---------------------------------------------------------------- tests catalogue, Telomy Rx, doctor AI summaries

def test_tests_catalogue_and_recommendations(client):
    cat = {t["id"]: t for t in client.get("/tests").json()}
    assert len(cat) >= 70 and cat["food_igg"]["evidence"] == "D" and cat["dexa"]["status"]["state"] == "current"
    rec = client.get("/tests/recommended").json()
    assert any(r["id"] == "pgx" for r in rec)                       # statin discussion → SLCO1B1 first
    assert client.post("/tests/book", json={"test_id": "food_igg", "day": "2026-10-09"}).status_code == 409
    assert client.post("/tests/book", json={"test_id": "pgx", "day": "2026-10-09"}).status_code == 200


def test_rx_is_data_triggered_and_doctor_gated(client):
    r = client.get("/rx/recommend", params={"goal": "heart"}).json()
    ids = {i["id"]: i for i in r["supplements"] + r["medicines"]}
    assert "4,000 IU" in ids["vitd"]["dose"] and ids["vitd"]["status"] == "adjust_dose"   # 22 ng/mL on 2,000 IU
    assert ids["rosuva"]["status"] == "discuss" and "CAC" not in ids["rosuva"]["why"] or "Coronary calcium" in ids["rosuva"]["why"]
    assert "Magnesium glycinate" in [i["name"] for i in r["already_taking"]]
    assert {e["name"] for e in r["excluded"]} >= {"NMN", "Melatonin"}
    plan = client.post("/rx/plans", json={"goal": "heart", "items": ["vitd", "psyllium", "rosuva"]}).json()
    assert plan["state"] == "awaiting_doctor"
    assert client.post(f"/rx/plans/{plan['id']}/order").status_code == 403                 # cannot order before sign-off
    assert any(p["id"] == plan["id"] for p in client.get("/doctor/work").json()["rx_plans"])
    d = client.post(f"/rx/plans/{plan['id']}/decide", json={"approve": True, "note": "Start D3 4,000 IU and psyllium; statin 5 mg after PGx.",
                                                           "keep": ["vitd", "psyllium", "rosuva"], "doses": {"rosuva": "5 mg nightly"}}).json()
    assert d["state"] == "approved" and d["plan"]["signed"]["reg_no"]
    assert next(i for i in d["plan"]["items"] if i["id"] == "rosuva")["dose"] == "5 mg nightly"
    o = client.post(f"/rx/plans/{plan['id']}/order").json()
    assert "test mode" in o["message"] and any("pharmacy" in c for c in o["channels"])
    pdf = client.get(f"/rx/plans/{plan['id']}/prescription.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_iv_vitamin_c_needs_g6pd(client):
    from app import rx
    ctx = rx._context()
    ctx["flags"] = (ctx["flags"] - {"g6pd_ok"}) | {"g6pd_def"}
    assert any(i["severity"] == "major" for i in rx.screen("iv_vitc", ctx))


def test_doctor_sees_every_report_with_ai_summary(client):
    reps = client.get("/doctor/patients/1/reports").json()
    assert len(reps) == 24 and all(r["summary"] for r in reps)
    cardio = next(r for r in reps if r["panel"] == "cardio")
    s = client.get(f"/reports/{cardio['id']}/summary").json()
    assert s["flagged"] == 3 and "Non-dipper" in s["summary"] and s["patterns"]
    assert client.post(f"/reports/{cardio['id']}/review", json={"action": "signed", "note": ""}).status_code == 400
    s2 = client.post(f"/reports/{cardio['id']}/review", json={"action": "signed", "note": "ABPM confirms; start telmisartan discussion."}).json()
    assert s2["reviews"][0]["doctor"] == "Dr. Meera Rao"
    ps = client.get("/doctor/patients/1/summary").json()
    assert "PREVENT" in ps["summary"] and "HSAI" in ps["summary"] and ps["problems"]
    assert "Latest labs" in client.get("/doctor/patients/7/summary").json()["summary"]


# ---------------------------------------------------------------- voice, routine, activities, environment

def test_voice_text_any_sentence_becomes_actions(client):
    r = client.post("/voice/command", json={"text": "Had 2 boiled eggs and dal for lunch, then 2 cigarettes, feeling stressed"}).json()
    kinds = {i["intent"] for i in r["intents"]}
    assert {"meal", "smoke", "mood"} <= kinds
    assert any("cigarette" in a["message"] for a in r["actions"])
    hi = client.post("/voice/command", json={"text": "आज मैंने दो अंडे और दाल खाई, थोड़ा तनाव है"}).json()      # Hindi
    assert {"meal", "mood"} <= {i["intent"] for i in hi["intents"]}
    v = client.post("/voice/command", json={"text": "had 120 ml vodka at 9 pm"}).json()
    a = next(i for i in v["intents"] if i["intent"] == "alcohol")
    assert a["grams_alcohol"] == 37.9 and a["ts"][11:16] == "21:00"
    q = client.post("/voice/command", json={"text": "why is my HRV low this week?"}).json()
    assert q["intents"][0]["intent"] == "question" and q["actions"][0]["answer"]


def test_voice_audio_pipeline_extracts_features(client):
    import io, math, wave
    sr, buf = 16000, io.BytesIO()
    w = wave.open(buf, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    frames = bytearray()
    for i in range(sr * 2):  # 2 s of a 140 Hz 'voice' with syllable-like amplitude modulation
        amp = 0.4 * (0.5 + 0.5 * math.sin(2 * math.pi * 3 * i / sr)) if (i // 4000) % 2 == 0 else 0.002
        v = int(32767 * amp * math.sin(2 * math.pi * 140 * i / sr))
        frames += v.to_bytes(2, "little", signed=True)
    w.writeframes(bytes(frames)); w.close()
    from app import voice
    f = voice.acoustics(voice.decode(buf.getvalue()))
    assert 120 <= f["f0_mean"] <= 160 and f["jitter_pct"] < 5 and 0 < f["pause_ratio"] < 1
    assert voice.stress_score(f)["score"] is not None


def test_routine_text_becomes_schedule_and_metrics(client):
    txt = ("I wake up around 7-8 am every day and sleep around 12-1. After waking I take a cigarette. Office from monday to friday, "
           "a 30 min drive. Black coffee at 10am and at 5. Lunch at 1 with 2 eggs and dal. I drink 2 times a week in the evening 90 ml of whisky each. "
           "While drinking I take 3 cigarettes, otherwise 1. I drink 3 litres of water a day.")
    r = client.post("/routine/parse", json={"text": txt}).json()
    m = r["metrics"]
    assert m["alcohol_g_week"] == round(90 * 0.4 * 0.789 * 2, 1) and m["drink_days_per_week"] == 2
    assert m["sleep_hours"] == 7.0 and m["caffeine_times"] == ["10:00", "17:00"] and m["water_litres"] == [3.0, 3.0]
    assert 1 < m["cigarettes_per_day"] < 3
    saved = client.post("/routine", json={"text": txt}).json()
    assert "smoker = yes" in " ".join(saved["profile_changes"])
    pred = client.get("/predict").json()["models"]["cvd"]
    assert pred.get("risk") is not None
    t = client.get("/routine/today", params={"day": "2026-10-06", "drinking": False}).json()
    smoke = next(i for i in t["items"] if i["kind"] == "smoke")
    t2 = client.post("/routine/mark", json={"day": "2026-10-06", "key": smoke["key"], "status": "done"}).json()
    assert next(i for i in t2["items"] if i["key"] == smoke["key"])["status"] == "done"
    from app import db
    db.exec_("UPDATE profile SET data = json_set(data, '$.smoker', json('false')) WHERE id = 1")  # keep later tests' assumptions


def test_routine_times_keep_minutes_and_follow_wake_up():
    from app import routine
    items = routine.parse("I wake up at 6:30 am. Black coffee at 7. Lunch at 1. Green tea at 4. Sleep at 10:45 pm.")["items"]
    t = {i["kind"]: i.get("time") for i in items}
    assert t["wake"] == "06:30" and t["sleep"] == "22:45"
    assert [i["time"] for i in items if i["kind"] == "caffeine"] == ["07:00", "16:00"]
    assert next(i["time"] for i in items if i["kind"] == "meal") == "13:00"


def test_custom_activities_build_baselines(client):
    lst = client.get("/activities").json()
    assert {a["id"] for a in lst["mine"]} >= {"fast_bowling", "golf"}
    d = client.get("/activities/fast_bowling").json()
    assert d["series"]["max_speed"]["baseline"]["n"] >= 3 and any("workload" in i for i in d["insights"])
    g = client.get("/activities/golf").json()
    assert "calm_index" in g["series"]
    new = client.post("/activities", json={"name": "Padel match", "fields": [{"key": "games", "label": "Games won", "unit": ""}]}).json()
    assert new["id"] == "padel_match"
    s = client.post("/activities/padel_match/sessions", json={"values": {"games": 6}, "minutes": 60, "hr": [120, 135, 142, 150, 138], "hrv": [20, 18, 15, 14, 17]}).json()
    assert s["vitals"]["hr_max"] == 150
    v = client.post("/voice/command", json={"text": "bowled 6 overs at nets, fastest 134 kmph, 2 wickets"}).json()
    assert v["actions"][0]["activity"] == "fast_bowling"


def test_environment_compare_offline_math(client):
    from app import exposome
    c = exposome.compare("Delhi", "Bengaluru")
    d, b = c["cities"]
    assert d["pm25_annual"] > b["pm25_annual"] and d["aqli_years_lost"] > b["aqli_years_lost"] and len(c["sources"]) >= 5


# ---------------------------------------------------------------- digital twin

def test_twin_calibrates_to_this_person(client):
    o = client.get("/twin").json()
    cal = o["calibration"]
    assert 0.1 <= cal["vitd_response"] < 0.5          # seeded: 18 → 22 ng/mL on 2,000 IU ≈ 20 % of the population response
    assert cal["hrv_per_alcohol_night"] < -5           # from the engine's adjusted effect (truth −9)
    assert {s["name"] for s in o["systems"]} >= {"Heart & vessels", "Muscle & bone"}


def test_twin_scenarios_follow_the_evidence(client):
    base = client.post("/twin/simulate", json={"years": 5}).json()
    from app import twin
    now = twin.inputs_now()["statin"]                  # an earlier test may already have ordered rosuvastatin via Rx
    st = client.post("/twin/simulate", json={"changes": {"statin": "rosuva20"}, "years": 5}).json()
    v = {x["key"]: x for x in st["variables"]}
    expected = (1 - twin.STATIN["rosuva20"]) / (1 - twin.STATIN[now])
    assert abs(v["ldl"]["scenario_end"] / v["ldl"]["baseline_end"] - expected) < 0.03
    assert st["risk_scenario"][-1][1]["prevent_30y"] < base["risk_baseline"][-1][1]["prevent_30y"]
    s = client.post("/twin/simulate", json={"changes": {"strength_per_week": 3, "protein_g_kg": 1.6}, "years": 2}).json()
    v = {x["key"]: x for x in s["variables"]}
    assert v["lean_kg"]["difference"] > 0.5 and v["bmd_t"]["difference"] > 0
    d = client.post("/twin/simulate", json={"preset": "move_delhi", "years": 3}).json()
    v = {x["key"]: x for x in d["variables"]}
    assert 3 < v["sbp"]["difference"] < 9 and v["hrv"]["difference"] < 0
    assert client.post("/twin/simulate", json={"changes": {"teleport": 1}}).status_code == 400


def test_twin_day_and_mirror(client):
    client.post("/routine", json={"text": "I wake up around 7-8 am and sleep around 12-1. Black coffee at 10am and at 5. "
                                           "I drink 2 times a week in the evening 90 ml of whisky each. While drinking I take 3 cigarettes, otherwise 1.",
                                  "apply_to_profile": False})
    dd = client.get("/twin/day", params={"drinking": True, "day": "2026-10-06"}).json()
    assert dd["peak_bac"] > 0.02 and dd["caffeine_at_bed_mg"] > 20 and dd["tonight"]["hrv"] < dd["tonight"]["hrv_baseline"]
    m = client.get("/twin/mirror").json()
    assert m["hrv"]["r2"] > 0.3 and any(l["marker"] == "hs-CRP" and l["unexplained_pct"] > 30 for l in m["labs"])


# ---------------------------------------------------------------- machine telemetry & patch ingestion

def test_device_telemetry_links_to_session_and_drives_physiology(client):
    from datetime import datetime, timedelta
    assert client.post("/centre/devices/CRY-1/key").status_code == 401                      # admin key required
    key = client.post("/centre/devices/CRY-1/key", headers={"X-Admin-Key": "dev-admin"}).json()["key"]
    assert client.post("/devices/CRY-1/telemetry", json={"samples": [{"ts": "2026-10-06T08:00:00", "chamber_temp_c": -100}]},
                       headers={"X-Device-Key": "wrong"}).status_code == 401
    from app import db
    s = db.one("SELECT id, ts FROM therapy_sessions WHERE patient_id = 1 AND modality = 'cryo' AND device_id = 'CRY-1' ORDER BY ts DESC")
    t0 = datetime.fromisoformat(s["ts"]) - timedelta(minutes=5)
    samples = []
    for k in range(0, 600, 5):           # pre-cool, 180 s at ≈ −158 °C with the person inside, then the door opens
        v = -60 - 98 * min(1, k / 120) if k < 300 else (-158 if k < 480 else -120)
        samples.append({"ts": (t0 + timedelta(seconds=k)).isoformat(timespec="seconds"), "chamber_temp_c": v, "door_open": int(k >= 480), "status": "running"})
    samples.append({"ts": (t0 + timedelta(seconds=605)).isoformat(timespec="seconds"), "chamber_temp_c": -195, "status": "E12_sensor"})
    r = client.post("/devices/CRY-1/telemetry", json={"samples": samples}, headers={"X-Device-Key": key}).json()
    assert r["stored"] == len(samples) and any(a["channel"] == "chamber_temp_c" for a in r["alarms"]) and any(a["channel"] == "status" for a in r["alarms"])
    sess = client.get(f"/therapy/sessions/{s['id']}").json()
    m = sess["machine"]
    assert m and m["seconds_below_minus110"] >= 150 and m["vs_prescribed"]
    assert sess["source"] == "simulated (ODE prior driven by machine telemetry)" and sess["measured_params"]["chamber_c"] < -140
    assert client.get("/centre/devices/CRY-1/telemetry").json()["connected"]


def test_patch_rr_intervals_become_hrv(client):
    blocked = client.post("/therapy/sessions", json={"modality": "sauna"})   # earlier test logged vodka today → sauna blocked
    assert blocked.status_code in (200, 403)
    s = client.post("/therapy/sessions", json={"modality": "pemf"}).json()
    samples = [{"t": t, "rr_ms": [860, 840, 880, 850, 870] if t < 300 else [520, 515, 530, 512, 525] if t < 1500 else [900, 870, 930, 880, 920]}
               for t in range(0, 3000, 10)]
    f = client.post(f"/therapy/sessions/{s['id']}/samples", json={"samples": samples, "source": "Telomy patch (prototype)"}).json()["features"]
    assert f["hr_pre"] and 65 < f["hr_pre"] < 75 and f["hr_peak"] > 110 and f["rmssd_pre"] > 15


def test_routine_water_in_ml_is_not_alcohol():
    from app import routine
    items = routine.parse("I wake up at 7. Drink 500 ml of water. Wine twice a week, 1 glass.")["items"]
    alc = [i for i in items if i["kind"] == "alcohol"]
    assert len(alc) == 1 and alc[0]["drink"] == "wine" and alc[0]["ml"] == 150 and alc[0]["per_week"] == 2
    assert any(i["kind"] == "water" for i in items)
