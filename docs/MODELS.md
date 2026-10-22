# Telomy models & engines

The trained-model intelligence layer: how a blood/body panel plus wearable and
lifestyle signals become grounded, explainable longevity outputs. This is the
reference for the `telomy_ml` API (`backend/app/telomy_ml.py`) and the LLX engine
suite (`backend/app/llx/`). For the guideline-based bioage/longevity path (PhenoAge,
pace-of-ageing) see [`ENGINE.md`](ENGINE.md); this doc covers the **learned** models
and the engines that orchestrate them.

> **Status & honesty.** All models are trained on public, de-identified population
> cohorts (mostly US NHANES). They are **screening and risk-stratification** tools,
> not diagnoses. Metrics below are held-out test metrics on the training population;
> real-world accuracy on an individual (especially a non-US individual) will differ.
> Every number the app shows is a *tool result with provenance* — the engines and the
> SLM narrate, they never invent a value. n-of-1 validation (the founder as the first
> subject) certifies the **pipeline**, not population accuracy.

---

## 1. Architecture of the intelligence layer

```
          panel (labs + body comp)            wearable (ring/patch/WHOOP)      lifestyle / voice
                  │                                     │                            │
                  ▼                                     ▼                            ▼
   ┌───────────────────────────┐          ┌───────────────────────┐    ┌───────────────────────┐
   │  trained models (joblib)  │          │   fusion.py            │    │ voice_biomarkers.py   │
   │  clocks · muscle · disease│          │  personal-baseline     │    │ personal_agent.py     │
   │  mortality  (sklearn)     │          │  RHR/VO2max/HR-recovery│    │ checkin_engine.py     │
   └───────────┬───────────────┘          └───────────┬───────────┘    └───────────┬───────────┘
               │     grounded "tools" (tools.py, disease_tools.py)                  │
               ▼                                                                    ▼
   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │  report.py  —  composes one grounded picture (blood age, bio age, muscle age,            │
   │               disease screen, 10-yr mortality, drivers, plain-language summary)          │
   └───────────────────────────────┬─────────────────────────────────────────────────────────┘
                                    │
   supplements.py · modalities.py · food_quality.py · nutrition.py · casestudy.py · signatures.py
                                    │
                                    ▼
          telomy_ml.py  (FastAPI APIRouter, per-user)  →  /me/report, /me/supplements, …
```

- **Trained models** are scikit-learn estimators serialised with `joblib`, stored in
  `backend/app/assets/{clocks,muscle,disease}/` (~25 MB total) with a sibling
  `*_metrics.json`. They load lazily on first `/me/*` call.
- **LLX engines** (`backend/app/llx/`) are deterministic Python that call the models as
  **grounded tools** and compose explanations. Named for the Telomy-LLX SLM
  (`telomy-slm/`), a tool-grounded small language model that will narrate these outputs
  on-device; the engines run with or without the SLM.
- **`telomy_ml.py`** mounts an additive `APIRouter` (the `/me/*` routes) on top of the
  existing app. It never changes the legacy bioage/predict routes — it reconciles the
  **trained** clock with the app's **clinical** PhenoAge and shows both, labelled.

Dependencies (pinned so joblib loads without version drift):
`scikit-learn==1.9.1`, `scipy==1.18.1`, `joblib==1.6.0`, `numpy==2.5.3`.

---

## 2. Data sources

| Source | Licence | Used for |
|---|---|---|
| **NHANES** 2009–2018 (CDC) | Public domain | Aging clocks, muscle clocks, disease models, 10-yr mortality (linked mortality file) |
| **Open Food Facts** (4.86 M products) | ODbL | Food-quality model (`food_quality.py`) |
| **IFCT 2017** (542 Indian foods) | Govt. of India | Indian meal nutrition (`nutrition.py`) |
| **NIH DSLD** (~215 k supplement labels) | CC0 | Supplement catalog + market dose-norms (`dsld.py`) |
| **gnomAD r4** (South-Asian frequencies) | Open | Genome/variant frequency context |

Training code and raw-download scripts live in `research/` (`ageclock/`, `muscleclock/`,
`diseasemodel/`, `nutritionmodel/`, `deficiencymodel/`), each with a `results.json` and a
`download_*.sh`. Personal health data is **never** in the repo (`backend/data_local/`,
`backend/telomy.db`, `*.db` are git-ignored).

---

## 3. Aging clocks — "blood age"

`backend/app/assets/clocks/` · trainer `research/ageclock/train.py` · tool `llx/tools.py:predict_age`

Regress chronological age on a routine blood panel with **HistGradientBoosting**
(handles missing markers natively, so a partial panel still scores). Five models by
panel richness; `report.py` picks the richest the inputs support.

| Model | Features | n | Test MAE | Test R² | Pearson r | CV5 MAE |
|---|---|---|---|---|---|---|
| `telomy_full` | 37 | 27,340 | **8.79 y** | 0.64 | 0.80 | 8.91 ± 0.20 |
| `telomy_metabolic` | metabolic subset | 27,327 | ~ | — | — | — |
| `telomy_liverkidney` | liver+kidney subset | — | — | — | — | — |
| `telomy_cbc` | 13 (CBC only) | 27,733 | 13.3 y | 0.24 | 0.49 | 13.4 |
| `telomy_clinic9` | 9 (minimal) | 27,791 | 12.2 y | 0.36 | 0.60 | 12.1 |

- **Blood age** = model prediction; **acceleration** = blood age − chronological age.
- Baseline ElasticNet is ~2–3 y worse (e.g. 11.5 vs 8.79 y on the full panel), which is
  why the gradient-boosted model is shipped.
- Alongside this, `tools.phenoage` computes the **Levine PhenoAge** (a fixed clinical
  formula) so the report shows learned-vs-guideline side by side.

---

## 4. Muscular-age clock

`backend/app/assets/muscle/` · tool `llx/report.py:muscular_age`

Body-composition / anthropometry → predicted age. Picks the richest of three models.

| Model | Features | n | Test MAE | R² | r |
|---|---|---|---|---|---|
| `muscle_full` | 19 (DXA + anthro + strength) | 21,610 | 9.05 y | 0.61 | 0.78 |
| `muscle_dxa` | 15 (DXA-led) | 21,668 | 9.5 y | 0.55 | 0.75 |
| `muscle_anthro` | 8 (tape + scale only) | 22,533 | 11.9 y | 0.39 | 0.62 |

Strongest single signal is **ALMI** (appendicular lean mass index), corr −0.62 with age.
Enables muscular-age acceleration when DXA/BCA or even just BMI+waist+weight+height exist.

---

## 5. Disease screen

`backend/app/assets/disease/` · trainer `research/diseasemodel/` · tool `llx/disease_tools.py:predict_diseases`

Thirteen binary risk models from routine markers, each **probability-calibrated**
(`CalibratedClassifierCV`, isotonic) so the percentages are honest, ranked by probability.

| Condition | Test AUC | Prevalence (train) | Notes |
|---|---|---|---|
| diabetes | **0.887** | 13.1% | features exclude glycemic markers (so it screens, not restates HbA1c) |
| hypertension | 0.823 | 35% | full panel |
| high_cholesterol | 0.77 | 34.8% | full panel |
| kidney_disease | ~0.8 | 3.5% | |
| coronary_hd, angina, heart_attack, heart_failure, stroke | 0.7–0.85 | low | cardiovascular family |
| cancer, copd, liver_disease | 0.6–0.8 | low | |

Output is a *ranked screen*: a high number is a reason to look with a clinician, never a
diagnosis. `report.py` surfaces conditions ≥ 50% in the plain-language summary.

---

## 6. Ten-year mortality

`backend/app/assets/disease/mortality_10y.joblib` · trainer `research/diseasemodel/mortality_longterm.py`

NHANES panel + the linked mortality file → 10-year all-cause risk (population ranking,
**not** a personal prognosis).

| Model | n | Deaths | Test AUC |
|---|---|---|---|
| `all_cause_10y` | 2,965 | 124 | 0.81 |

Methodology note: pooling later NHANES cycles inflates AUC via a regression-to-mean /
short-follow-up artefact; the shipped model is restricted to an honest follow-up window.

---

## 7. Wearable-fusion risk engine — the differentiator

`backend/app/llx/fusion.py`

Overlays wearable signals on the panel-based picture using **personal baselines**, not
population cut-offs:

- **Resting HR** vs the person's own trend; **VO₂max** and **HR-recovery** as fitness-age
  inputs; **HRV** demoted to context (device HRV is noisy and over-delivered — see the
  WHOOP study note in `docs/history/DECISIONS.md`).
- Produces a fused risk profile and feeds the fitness/autonomic/cardiac age clocks on the
  app's Age screen.

---

## 8. Recommendation & lifestyle engines

| Engine | File | What it does | Safety |
|---|---|---|---|
| **Supplements** | `supplements.py` + `dsld.py` | Biomarker-driven suggestions with mechanism, dose-check vs DSLD market norms, interaction screen | **`AWAITING_DOCTOR_VALIDATION` gate** — never a prescription; user verifies with a clinician |
| **Modalities** | `modalities.py` | Bonphul device suite (cryo, HBOT, PEMF, red-light, EBOO…) matched to a goal, **evidence-graded**, with a contraindication screen and n-of-1 framing | ozone/EBOO never offered as "wellness"; CDSCO/PVHO/ASME caveats |
| **Food quality** | `food_quality.py` | Nutrient label → quality grade (Open Food Facts–trained) | — |
| **Meal nutrition** | `nutrition.py` | Recognised food + grams → nutrition (IFCT for Indian foods) | — |
| **Case study** | `casestudy.py` | n-of-1: did *this* therapy change *this* person? Interrupted time-series + counterfactual, design-aware verdict (guards the regression-to-mean trap) | returns `possible_regression_to_mean`, not a false positive |
| **Session signatures** | `signatures.py` | What happens *during* a therapy session (Layer-1) | — |
| **Intake** | `intake.py` | Build the whole-person profile, then nudge | consent-gated |

---

## 9. Always-on / proactive layer (Omi-style, privacy-first)

| Engine | File | Role |
|---|---|---|
| **Voice biomarkers** | `voice_biomarkers.py` | F0, jitter/shimmer, alpha-ratio → **personal-baseline arousal z-score**; needs a calm baseline before it reports |
| **Personal health agent** | `personal_agent.py` | On-device moments → derived signals only (arousal + health mentions); raw audio dropped; `pause()`/`forget()` controls |
| **Check-in engine** | `checkin_engine.py` | JITAI prompts — receptivity-gated, event-triggered, **self-tuning confidence** (earns the right to interrupt) |

Privacy contract: on-device (SFSpeechRecognizer, `requiresOnDeviceRecognition`), explicit
consent, raw audio/transcript dropped by default, nothing sent externally.

---

## 10. API surface (`telomy_ml.py`, per-user)

All routes resolve the signed-in user and bind their Vault (`_bind_user`). Marker codes
from the app catalogue are mapped to engine keys by `_ALIAS` (incl. body-composition).

| Route | Method | Returns |
|---|---|---|
| `/me/report` | GET | Unified report: trained clocks + engines, **reconciled** with the app's clinical bioage |
| `/me/report/compute` | POST | Full risk profile from a panel (+ optional wearable) — demo/trial template |
| `/me/supplements` | POST | Biomarker-driven suggestions (gated) |
| `/me/foodscore` | POST | Food-quality grade from nutrients/100g |
| `/me/modalities` | GET | Modalities for a goal |
| `/me/checkin` | POST | The check-in engine's decision for the app to deliver |
| `/me/health` | GET | ML readiness + loaded assets |

---

## 11. The SLM (Telomy-LLX)

`telomy-slm/` — a Qwen2.5-3B/1.5B **tool-grounded** small model that will narrate the
outputs of these engines on-device. It calls the models as tools and never invents a
number. Shipping the engines first (this doc) lets the product work today; the SLM is the
natural-language layer on top. On-device voice uses `SFSpeechRecognizer`.

---

## 12. Where to go next

- Algorithms with citations (guideline path): [`ENGINE.md`](ENGINE.md)
- Module internals & schemas: [`architecture/LLD.md`](architecture/LLD.md)
- System architecture & deployment: [`architecture/HLD.md`](architecture/HLD.md)
- Clinical claims firewall: [`CLINICAL_SAFETY.md`](CLINICAL_SAFETY.md)
- Training code & results: `research/{ageclock,muscleclock,diseasemodel,nutritionmodel,deficiencymodel}/`
- Device/sleep validation findings: [`history/DECISIONS.md`](history/DECISIONS.md)
