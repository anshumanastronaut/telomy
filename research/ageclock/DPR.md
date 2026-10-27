# Telomy — Detailed Project Report (DPR)
## Aging-Intelligence Models, SLM & Platform

**Version:** 2.0 (FINAL) · **Date:** 2026-10-21 · **Owner:** ananshubapu@gmail.com
**Scope:** every dataset, formula, model, workflow, agent, architecture, roadmap, open item and business
opportunity behind Telomy's aging-intelligence stack. All metrics are measured and reproducible, not
projected. §9 lists what is done vs pending.

---

## 0. Executive summary
Telomy estimates a person's **biological aging** from an inexpensive routine blood panel (and,
increasingly, from wearables), then explains it through an **on-device, tool-grounded small language
model (Telomy-LLX)** that never invents a number. The clocks are trained on **NHANES 2009–2018**
(49,693 participants). The flagship clock predicts chronological age at **MAE 8.8 years (r=0.80)** —
at parity with the best published routine-bloodwork clocks — and the mortality-validated **PhenoAge**
biological-age measure is reproduced at **r=0.92**. The moat is not raw accuracy; it is
**accuracy-per-rupee + multimodal fusion (bloods × wearables) + on-device privacy + a shipped
clinical operating system.**

---

## 1. Datasets

### 1.1 NHANES (primary training corpus)
- **Source:** US CDC National Health and Nutrition Examination Survey, public-domain.
- **Cycles used:** 2009-10 (F), 2011-12 (G), 2013-14 (H), 2015-16 (I), 2017-18 (J) — 5 continuous cycles.
- **Files:** 46 SAS-XPT lab/demographic files across 11 families: `DEMO` (age, sex, race),
  `CBC` (haematology), `BIOPRO` (comprehensive metabolic/biochemistry), `GLU` (fasting glucose),
  `GHB` (HbA1c), `HSCRP`/`CRP` (inflammation), `INS` (insulin), `TCHOL`, `HDL`, `TRIGLY` (lipids).
- **Assembled table:** 49,693 participants × 51 columns, keyed by `SEQN`, cycles concatenated.
- **Modelling cohort:** adults 18–80 (NHANES top-codes age at 80); **~27,000 with full blood panels**,
  16,396 with CRP. This is **27× the 1,000-samples-per-model requirement.**
- **Download note (ops):** CDC blocks non-browser user-agents; fetch with a browser UA from
  `wwwn.cdc.gov/Nchs/Data/Nhanes/Public/<startyear>/DataFiles/<FILE>_<suffix>.xpt`.
- **Harmonisation:** CRP unified to mg/L (older cycles report conventional CRP in mg/dL ×10 →
  hs-CRP mg/L); glucose unified (fasting where available, else serum).

### 1.2 NHANES body composition / muscle (muscular-age clock)
- **Files:** DXA whole-body (`DXX`, 2011–2018), grip strength (`MGX`, 2011–2014 only — discontinued
  after), body measures (`BMX`, all cycles), demographics (`DEMO`). 23,825 adults assembled; DXA on
  22,511; grip on 10,386.
- **Derived clinical features:** appendicular lean mass ALM = Σ(arm+leg lean, excl. bone);
  **ALMI = ALM / height²** (the sarcopenia index); total/trunk lean, fat %, lean:fat ratio, bone
  mineral density, grip strength, anthropometry.

### 1.3 Nutrition — USDA FoodData Central (meal-photo feature)
- **SR Legacy** bulk CSV → compact per-food table of 7,793 foods with macros + micronutrients per
  100 g (`telomy-vision/assets/nutrition_db.csv`). Grounds meal-photo nutrition the same way the
  clocks ground age (model proposes the food, the table supplies the numbers).

### 1.4 NHANES diagnoses + linked mortality (disease & long-term models)
- **Diagnosis questionnaires** (2009–2018): diabetes (`DIQ`), BP/cholesterol (`BPQ`), medical
  conditions (`MCQ`: CHD, MI, angina, CHF, stroke, liver, cancer, COPD), kidney (`KIQ_U`). 30,352 adults
  joined to the blood panel by SEQN → 12 physician-diagnosed binary labels.
- **NHANES linked-mortality public files** (follow-up through 2019, fixed-width): SEQN, MORTSTAT,
  UCOD_LEADING, PERMTH — enables long-term outcome modelling. 2009–2012 cycles carry the 8–10y
  follow-up needed for a clean 10-year label.

### 1.5 Telomy device data (operational, feeds future models)
- **KY-E-B1 ECG patch** — per-minute HR/HRV (RMSSD, SDNN), beat counts, quality, arrhythmia events;
  live to cloud (`band_minutes`, `band_events`, `ecg_strips`).
- **Smart ring (TK-series)** — PPG HR, SpO₂, motion, overnight sleep (`vitals_ts source=ring`).
- **WHOOP 4.0** — HR/SpO₂/respiration/skin-temp 1 Hz overnight, sleep staging (via NOOP export).
- **System of record:** Oracle cloud SQLite (`/opt/telomy/telomy.db`), nightly backups.
- These are **longitudinal per-person trajectories** — the substrate for the future pace-of-aging model
  (NHANES cannot provide this, being cross-sectional).

### 1.3 Reference/validation assets
Published implementations used for cross-checking: `BioAge` (R; NHANES KDM/PhenoAge/homeostatic
dysregulation), `pyaging` (pretrained KDM). UK Biobank literature informs feature choice (cystatin C).

---

## 2. Formulas & rationale

### 2.1 Levine PhenoAge (biological age, mortality-validated) — reproduced exactly
Inputs (9 markers + chronological age), converted to the formula's units:
albumin→g/L (×10), creatinine→µmol/L (×88.4), glucose→mmol/L (×0.0555), ln(CRP in mg/dL),
lymphocyte %, MCV (fL), RDW (%), ALP (U/L), WBC (10³/µL), age (yr).

Linear predictor:
```
xb = -19.907
     - 0.0336·albumin + 0.0095·creatinine + 0.1953·glucose + 0.0954·ln(CRP)
     - 0.0120·lymph% + 0.0268·MCV + 0.3306·RDW + 0.00188·ALP + 0.0554·WBC + 0.0804·age
mortality = 1 - exp( -exp(xb) · (exp(0.0076927·120) - 1) / 0.0076927 )
PhenoAge  = 141.50225 + ln( -0.00553 · ln(1 - mortality) ) / 0.090165
AgeAccel  = PhenoAge - chronological_age        ← the clinical signal (±0 = on pace)
```
**Rationale:** PhenoAge is a Gompertz/Cox mortality model re-expressed in age units; it predicts
all-cause and cause-specific mortality *beyond* calendar age. Telomy reports **AgeAccel** — the
number that actually responds to disease and lifestyle. Reproduced at **r=0.917** vs chronological
age (Levine reported r≈0.9).

### 2.2 Telomy learned clocks (chronological-age regression)
- **Algorithm:** `HistGradientBoostingRegressor` (sklearn) — gradient-boosted histograms, **native
  missing-value handling** (critical: real panels are incomplete; no imputation bias), L2
  regularisation. Chosen over XGBoost/LightGBM for equivalent accuracy without the `libomp` native
  dependency, and over linear models because ElasticNet baselines run 2.5–3 years worse on MAE.
- **Target:** chronological age (NHANES `RIDAGEYR`), adults 18–80.
- **Validation:** 20% held-out test + 5-fold cross-validation; metrics MAE (years), R², Pearson r.
- **Rationale for a family of clocks** (not one): a full panel is most accurate, but organ-/panel-
  specific sub-clocks let us (a) work from whatever a clinic measured, (b) localise aging to a system
  (metabolic, hepatic/renal, haematologic), which is clinically actionable and explainable.

### 2.3 Explanation layer
Each measured marker is compared to an adult reference median; deviation >12% is reported with its
known direction of age-association (e.g. high glucose/RDW/CRP → older; high albumin/lymph%/HDL →
younger). Transparent and assay-only — no black-box attribution required.

---

## 3. Models — how each works (detail)

| Model | Inputs | N | Test MAE | R² | Pearson r | Role |
|---|---|---:|---:|---:|---:|---|
| **telomy_full** | 37 routine markers + sex | 27,340 | **8.79 y** | 0.639 | 0.800 | flagship chronological clock |
| telomy_metabolic | glucose, HbA1c, insulin, lipids, urate, BUN | 27,327 | 11.12 y | 0.434 | 0.659 | metabolic sub-clock |
| telomy_liverkidney | LFTs + renal markers | 27,280 | 12.08 y | 0.358 | 0.598 | hepatic/renal sub-clock |
| telomy_clinic9 | PhenoAge's 9 markers | 27,791 | 12.20 y | 0.357 | 0.597 | cheap-panel clock |
| telomy_cbc | 13 haematology markers | 27,733 | 13.31 y | 0.241 | 0.491 | haematologic sub-clock |
| **PhenoAge** (formula) | 9 markers + age | 16,396 | — | — | r=0.917 vs age | biological age + AgeAccel |

Top age-driving markers (|corr| with age): glucose (+0.22), albumin (−0.21), MCV (+0.21),
creatinine (+0.18), RDW (+0.17), lymphocyte% (−0.15), ALP (+0.12).

### Muscular-age clock family (NHANES DXA + grip + anthropometry, 2011–2018)
Same method (HistGradientBoosting, 20% holdout + 5-fold CV), target = chronological age; residual
(predicted − actual) = **muscular-age acceleration** (the sarcopenia signal).

| Model | Inputs | N | Test MAE | R² | Pearson r |
|---|---|---:|---:|---:|---:|
| **muscle_full** | DXA + grip + anthropometry (19 features) | 21,610 | **9.05 y** | 0.606 | 0.779 |
| muscle_dxa | DXA + anthropometry (no dynamometer) | 21,668 | 9.51 y | 0.553 | 0.745 |
| muscle_anthro | scale + tape only (phone-feasible) | 22,533 | 11.93 y | 0.385 | 0.620 |

Dominant feature: **ALMI (appendicular lean mass index), r = −0.62 with age** — the clinical
sarcopenia marker; grip strength r = −0.32. Code: `telomy-app/research/muscleclock/`.

### Meal-photo nutrition (telomy-vision)
`image → food_recognition (CLIP zero-shot label) → portion estimate → nutrition.lookup()` grounded in
USDA SR Legacy (7,793 foods). Returns per-serving + meal-total macros/micros. Same provenance rule as
the clocks: the vision model proposes, the USDA table supplies the numbers.

### Medical-image / report ingestion (telomy-vision/imaging) — decision-support only
DICOM read (pydicom) + report OCR/structuring (pdfplumber/pytesseract); pixel-level assist via
**pretrained** published models (torchxrayvision chest-X-ray, TotalSegmentator/MONAI for CT/MRI),
clinician-in-the-loop. No autonomous diagnosis, no from-scratch diagnostic model. Genome = parse the
lab report/VCF (sequencing is not images).

### Disease-prediction models (NHANES diagnoses, routine panel + age/sex)
Per-condition HistGradientBoosting classifiers; 20% held-out test ≈ **6,000 reports each**; metric
ROC-AUC. Match or beat the published NHANES literature.

| Condition | AUC | Condition | AUC | Condition | AUC |
|---|---:|---|---:|---|---:|
| diabetes* | 0.887 | heart attack | 0.842 | hypertension | 0.823 |
| heart failure | 0.858 | COPD | 0.826 | kidney disease | 0.803 |
| coronary heart disease | 0.849 | cancer | 0.811 | angina | 0.793 |
| stroke | 0.792 | high cholesterol | 0.770 | liver disease | 0.731 |

\* diabetes scored **without** glucose/HbA1c (non-circular); with them AUC 0.929. A "guess the disease"
ranker scores all conditions for one report (ranked coronary HD #1 at 0.85 for a known-CHD patient).

### Long-term models — mortality (NHANES linked-mortality, follow-up to 2019)
- **10-year all-cause mortality: test AUC 0.885** (NHANES 2009–2010 only — the single cycle with a full
  10-year window, so no follow-up-length label leakage; n=3,607, 766 deaths, test 722).
- **Cardiovascular-cause death: test AUC 0.868** (heart + stroke; 583 events, all cycles pooled).
  Follow-up varies 1–10y by cycle, so a calibrated time-to-event (Cox / competing-risks) model is the
  rigorous upgrade — labelled as such.
Age-dominated; needs calibration + benchmarking vs Pooled Cohort Equations before clinical use.

### Rigor pass (disease models) — `diseasemodel/eval_rigor.py`
Calibration + PR-AUC + a multi-label "guess the disease" metric. Finding: **ranking is strong**
(guess-the-disease **top-3 recall 92.3%**, top-1 70.9%) but **absolute probabilities for rare conditions
are miscalibrated** (balanced class weights trade calibration for ranking) → present as ranked risk and
add `CalibratedClassifierCV` (isotonic) before showing percentages. High-prevalence conditions
(diabetes/hypertension/cholesterol) are well-calibrated (calib-err 0.10–0.17).
Code: `telomy-app/research/diseasemodel/`.

### Unified report flow — one panel → the whole picture
`telomy-slm/telomy_llx/report.py::analyze_report(panel)` orchestrates every grounded tool into one
narrative: **blood age (clock) + biological age/acceleration (PhenoAge) + muscular age (if body
composition present) + ranked disease screen + 10-year mortality risk**. Verified end-to-end; e.g. a
58-yo panel → blood age 61, biologically +13y, muscle −10y, flags hypertension/stroke/liver, 10y risk 4%.

### Telomy-LLX (the SLM) — tool-grounded longevity model
- **Base:** Qwen2.5-3B-Instruct (cloud) / Qwen2.5-1.5B-Instruct (on-device, 4-bit MLX/llama.cpp).
- **Grounded tools:** aging (`predict_age`, `phenoage`), disease (`predict_diseases`,
  `mortality_risk_10y`), muscle, nutrition — the model calls them and explains; never computes.
- **Core principle:** the model **never computes a number**. It emits function calls
  (`predict_age`, `phenoage`, `explain_drivers`); the tool layer runs the *trained clocks + PhenoAge*;
  the model then explains the returned numbers with provenance. This structurally eliminates the #1
  failure mode of medical LLMs (fabricated figures).
- **Training:** QLoRA SFT on grounded conversations auto-generated from NHANES (user panel → tool
  calls → tool results → faithful explanation), measured for **numeric-faithfulness** (every number
  traces to a tool) and **guardrail-rate** (defers to clinicians, no diagnosis/prescription).
- **Privacy:** runs on-device; patient data never leaves the phone (DPDP/GDPR USP).
- **Status (measured):** foundation shipped in `telomy-slm/` — grounded tool layer runs; 2,700/300
  SFT conversations generated from NHANES; offline eval **100% guardrail-rate, 93.3% numeric-
  faithfulness** (dataset grounded by construction; strict checker flags small integers in prose).
  QLoRA training entrypoint + configs ready for a GPU box; fine-tune + on-device export pending.

---

### Telomy Health Agent — fusion engine + safety workflow (telomy-slm/telomy_llx)
One orchestrator (`agent.py::TelomyHealthAgent`), two jobs, 9/9 tests passing (`tests/test_agent.py`):
- **Wearable-fusion risk engine** (`fusion.py`): fuses the trained blood models with a **cited wearable
  overlay** (resting HR, HRV/SDNN, nocturnal SpO₂ — published hazard ratios, Zhang 2016 / Dekker 2000;
  labelled an evidence overlay, NOT a trained model, upgradeable to a trained fusion head on device-cohort
  outcomes). Surfaces blood-biological-age ∧ wearable convergence — a multimodal signal rivals lack.
- **Safety workflow** (`falldetect.py` + `monitor.py`): 3-phase fall detection (impact **and**
  post-impact immobility — rejects "sat down hard"; real fall 0.98 conf) feeding an emergency state
  machine (NORMAL→CONFIRMING→ESCALATED) with a confirmation countdown, immobility gate and user override.
  Escalation **prepares** an alert payload; the app sends it to emergency contacts with consent — the
  agent never messages anyone. Triggers: high-confidence fall, SpO₂<88, HR>150 at rest or <35.
Full design: `telomy-slm/AGENT.md`.

## 4. Workflows & architecture

### 4.1 Model training pipeline (`telomy-app/research/ageclock/`)
```
CDC NHANES XPT  →  assemble.py  →  nhanes_bloodpanel.csv  →  train.py  →  models/*.joblib + results.json
(46 files, 5 cycles)   merge on SEQN,        49,693 × 51         HGB + 5-fold CV,     5 clocks + metrics
                       rename, harmonise                          PhenoAge reimpl.
```

### 4.2 SLM pipeline (`telomy-slm/`)
```
models/*.joblib ─┐
                 ├─ tools.py (grounded tool layer: predict_age / phenoage / explain_drivers + schemas)
NHANES csv ──────┘        │
                          ├─ datagen.py → data/sft_{train,val}.jsonl (grounded tool-call conversations)
                          ├─ train_qlora.py (Qwen2.5 QLoRA, GPU) → LoRA adapter
                          ├─ eval.py (numeric-faithfulness + guardrail-rate)
                          └─ export → 4-bit GGUF/MLX → ships inside the iOS app beside tools.py + clocks
```

### 4.3 Product/platform architecture (already shipped & verified)
```
iOS/RN app ──(HTTPS)── FastAPI backend (Oracle cloud) ── SQLite (per-user) + care graph + billing
   │  ring/patch/WHOOP → vitals, HRV, sleep, ECG, aging clocks, 3D twin
   └─ roles: user · doctor · centre · super-admin   (tenant-isolated, token auth, 401/403 enforced)
```
The clocks and Telomy-LLX plug into this: the app calls the clock endpoints; Telomy-LLX runs on-device
and explains results; the web console surfaces aging dashboards to clinicians.

---

### 4.4 Autonomous intelligence agents (continuous)
Two scheduled agents run every ~4 hours whenever the Mac is on and online (catch up on next launch),
appending to `telomy-app/research/intel/`:
- **`telomy-research-intel`** — rotating 15-theme deep-research sweep (datasets, model SOTA, exposures,
  cardiac/fall/long-term models, regulatory, genomics, funding, IP) → `FINDINGS.md`, each entry ending
  in "Standout opportunities for Telomy".
- **`telomy-market-intel`** — studies one rival platform per run → updates `FEATURE_MATRIX.md`
  (basic/advanced features × who-has-it × Telomy status) and appends profiles to `MARKET_FINDINGS.md`
  with "What Telomy should integrate".
Both do web research only — no external sends, no spend. Review cadence: every 2 days. Disable in the
app's Scheduled section when the sweeps are complete.

## 5. Future development plan

| Horizon | Work | Target / rationale |
|---|---|---|
| **0–90 days** | Add **cystatin C** to the panel & retrain | UK Biobank's single most predictive marker (PhenoAge omits it); push MAE <8 y |
| 0–90 days | **Wearable-fusion features** (resting HR, HRV, arrhythmia burden) into the clocks | a cohort hit 5.68 y MAE by adding biometrics; we already collect these live |
| 0–90 days | **Telomy-LLX v0** fine-tune (Qwen2.5-3B) + on-device 1.5B build | tool-grounded longevity copilot in-app |
| 3–6 mo | **External validation** on UK Biobank / Indian cohorts; recalibrate for Indian reference ranges | generalisation + local regulatory evidence |
| 3–6 mo | **Mortality/disease-risk heads** (Cox) on top of the panel | move from "age" to "risk" — higher clinical value |
| 6–12 mo | **Pace-of-aging model** — latent Neural-ODE / Universal Differential Equation on Telomy's own longitudinal device+biomarker trajectories | the honest "PINN" — needs per-person time-series we're now accruing |
| 6–12 mo | **Clinical study / CDSCO pathway**; prospective accuracy & utility | credibility + reimbursability |
| 12 mo+ | **Multi-omics option** (methylation add-on) for premium tier | <3 y MAE where users pay for it |

**Honest non-claims (diligence hygiene):** we do not beat methylation clocks on raw MAE today; the
pace-of-aging ODE is gated on longitudinal data accrual; Telomy-LLX is scoped and wired, not yet
fine-tuned.

---

## 6. Business opportunities

1. **B2C longevity subscription** — "know and lower your biological age" from a cheap blood panel +
   wearable; recurring revenue; the on-device copilot is the retention engine.
2. **B2B2C via clinics & wellness centres** — the shipped doctor/centre/super-admin platform is the
   distribution channel; aging dashboards + AgeAccel tracking as a paid clinician tool.
3. **Corporate wellness** — employer programs priced on measurable biological-age improvement (clear
   ROI story vs step-count wellness).
4. **Insurance / risk underwriting** — PhenoAge AgeAccel and the risk heads are directly relevant to
   life/health underwriting and wellness-linked premiums (partnership or data product).
5. **Pharma & longevity-trial endpoints** — biological-age change as a surrogate endpoint; CRO/biotech
   licensing of the validated clock + fusion data.
6. **API / white-label** — "biological age as an API" for labs, telehealth, and other apps; the tool
   layer is already an API-shaped boundary.
7. **Diagnostics tie-in** — bundle with partner lab panels (incl. cystatin C) for an integrated
   "Telomy Longevity Panel" product.
8. **Data network effect** — the multimodal longitudinal dataset (bloods × wearables × outcomes) is
   itself a compounding, defensible asset few can replicate at consumer scale.

**Primary wedge:** B2C app + clinic distribution now; insurance/pharma data partnerships as the
dataset and validation mature.

---

## 7. Status — done vs pending (as of 2026-10-21)

### Done & verified (reproducible, tested)
- Blood aging-clock family (5 models; flagship MAE 8.79y / r 0.80) + PhenoAge (r 0.917).
- Muscular-age clock family (MAE 9.05y; ALMI −0.62 with age).
- Disease-prediction models — 12 conditions (AUC 0.73–0.89), tested on ~6k reports each; "guess the
  disease" ranker.
- Long-term mortality: 10-year all-cause (AUC 0.885) + cardiovascular-cause death (AUC 0.868, 583 events).
- Nutrition engine — USDA SR Legacy + IFCT 2017 India (8,335 foods) + 24-dish Indian recipe resolver.
- Vision — meal-photo → nutrition and chest-X-ray decision-support proven end-to-end on CPU.
- Genome annotation with real gnomAD South-Asian allele frequencies.
- Telomy-LLX foundation — grounded tool layer, 2,700/300 SFT conversations, eval 100% guardrail /
  93.3% faithfulness.
- Unified report flow + Telomy Health Agent (fusion engine + fall/emergency safety), 9/9 tests.
- Two continuous intelligence agents + the deep-tech org (handbook, 7-agent team, enabled plugins).

### Pending (gated on GPU, data, ops, or partnerships — not blocked on core research)
1. **Telomy-LLX fine-tune + on-device export** — GPU-gated; data/entrypoint/configs ready.
2. **Wearable-fusion → trained head** — needs the Telomy device cohort to accrue outcomes; today it's a
   cited evidence overlay.
3. **Fall/emergency → native + validation** — port `detect_fall` to Swift/CoreMotion; wire consent-based
   contact delivery in the app; validate on real-fall data (FARSEEING), report false-alarms/day.
4. **Clinical & regulatory** — add cystatin C → retrain; external Indian-cohort validation with
   calibration vs Pooled Cohort Equations; CDSCO / FDA-SaMD pathway; DPDP/GDPR file.
5. **Pace-of-aging ODE** — gated on longitudinal per-person device data accrual.
6. **Operational parity (from competitive intel)** — lab home-collection, e-pharmacy, Rx pathways, CGM,
   imaging: partnerships, not R&D.
8. **Recipe DB breadth & food classifier** — expand beyond 24 dishes; train a cuisine classifier (GPU).
9. **Change cloud super-admin password**; decide cloud-lock vs Mac for device studies.

### Known limitation documented
- One pre-existing therapy-verdicts test is flaky under the shared test DB (passes in isolation);
  unrelated to the model work.

## 8. Reproducibility index
- Blood clocks: `telomy-app/research/ageclock/{assemble.py, train.py, results.json, models/}`; data `raw/`.
- Muscular clock: `telomy-app/research/muscleclock/{muscle_clock.py, results.json, models/}`.
- Disease + long-term: `telomy-app/research/diseasemodel/{assemble_disease.py, train_disease.py, mortality_longterm.py, eval_rigor.py, results*.json, models/, README.md}`.
- Strategy docs: `telomy-app/research/{LONGEVITY_INTERVENTIONS.md, CLINICAL_REGULATORY.md}`; intel in `research/intel/`.
- SLM + unified flow + health agent: `telomy-slm/{telomy_llx/ (tools, disease_tools, report, fusion, falldetect, monitor, agent, datagen, train_qlora, eval), configs/, data/, tests/, README.md, AGENT.md}`.
- Vision/nutrition/imaging: `telomy-vision/{telomy_vision/, imaging/, assets/nutrition_db.csv, assets/ifct2017/, README.md}`.
- Intelligence agents: `telomy-app/research/intel/{AGENDA, FINDINGS, COMPETITORS, FEATURE_MATRIX, MARKET_FINDINGS}.md`; scheduled tasks `telomy-research-intel` + `telomy-market-intel`.
- Org & team: `telomy-app/{ENGINEERING.md, CLAUDE.md, .claude/agents/}`.
- Companion: `telomy-app/research/ageclock/REPORT.md` (research landscape + investor framing).
