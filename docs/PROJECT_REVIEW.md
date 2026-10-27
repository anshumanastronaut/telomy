# Telomy — Complete Project Review

A project-wide audit: what exists, which model is used where, where a model *should* be used but isn't, where
more training is needed, and what to add next. Grounded in the actual code (≈40 backend engines, 310 routes,
~38 mobile screens, ~37 trained models, the device recorder).

---

## 1. Feature surface (what's built)

**Backend engines (`backend/app/`)**
- **Vault & labs** — `labparse` (89-marker catalog incl. HbA1c, insulin, HOMA-IR, IGF-1), per-user SQLite tenancy.
- **Ages & clocks** — `bioage` (PhenoAge, KDM, dysregulation, blood/fitness/muscle/heart/organ ages), `engine.longevity_age`.
- **Disease & risk** — `predict` (PREVENT, PCE, FIB-4, KFRE), `llx/disease_tools` (14 NHANES models), `llx/chronic_tools` (11 BRFSS 5.89M), `llx/report` (unified), `llx/fusion` (wearable overlay).
- **Clinic (doctor)** — `llx/clinic_engine` (diagnostics + treatments + therapies + supplements, gated), `therapy`, `llx/supplements`.
- **Correlation** — `engine.effect_table` (n-of-1: does a behaviour change tomorrow's HRV/sleep).
- **Sleep & dynamics** — ECG/HSMM stager, `stager_motion`, `dynamics` (sleep pressure, load).
- **Nutrition** — `food`/`llx/food_quality` (NOVA 703k, Nutri-score), `llx/nutrition`, `llx/dsld`.
- **Environment** — `exposome` (WHO 7,482 cities + social connection + noise + UV/water, multi-factor).
- **Devices** — `band`, `whoop` (NOOP raw), `cgm`, `devices`; the native **recorder** (`TelomyRec`) + `/cal/*`.
- **Twin, cellular, science, brief, trackers, goals, routine, rx, activities, exposome.**
- **Platform** — multi-role (`roles`, `staff`, `tenancy`, `centre`, `clinic`, `platform`, `billing`, `interop/FHIR`).
- **AI** — `llx/agent` (grounded SLM + tools), `llx/monitor`, `llx/personal_agent`, RAG/retrieval.

**Mobile (`mobile/src/app`, ~38 screens):** longevity, predict, risks, twin, muscle, trackers, therapy-plan,
therapies, brief, monitor, upload, devices, captures, imaging, tests, rx, routine, goals, plans, activities,
family, emergency, insurance, marketplace, research, studies, onboarding…

**Devices:** patch (ECG) · ring (TK3040) · band — one-device-per-user spec; recorder + calibration workbench.

---

## 2. Which model is used where (the map)

| Model family | Scale | Served by | Surface |
|---|---|---|---|
| PhenoAge / blood-age / KDM | NHANES | `bioage.all_ages` → **/bioage**, `engine.longevity_age` → **/longevity** | **consumer** ✅ |
| Muscle-age clock | 21k | `bioage`, `diagnostics` → /bioage, /muscle | consumer ✅ |
| Disease screen (14, NHANES) | 30k | `disease_tools` → `report` → **/me/report** | consumer ✅ |
| **Chronic suite (11, BRFSS 5.89M)** | **5.89M** | `chronic_tools` → `clinic_engine` → **/mgmt/clinic/assess** | **doctor only** ⚠️ |
| Published risk (PREVENT/PCE/FIB-4/KFRE) | equations | `predict.run` → **/predict**, /risks | consumer ✅ |
| 10-yr mortality | NHANES-linked | `disease_tools.mortality_risk_10y` | consumer ✅ |
| Wearable fusion overlay | evidence | `fusion.risk_profile` → clinic + physio/devices | mixed ✅ |
| NOVA / Nutri-score | 703k | `food_quality` → **/me/foodscore**, nutrition | consumer ✅ |
| Deficiency (vit-D…) | 10k | `catalog_ext`, `cellular`, `diagnostics` | consumer ✅ |
| Sleep stager (ECG/HSMM + motion) | PSG | `stager_motion` → `whoop`, sleep routes | consumer ✅ |
| AFib / rhythm | af2017 | `band` (af_pattern events) → `diagnostics` | consumer ✅ |
| Fall / activity | — | `falldetect` → `agent`, `monitor` | consumer ✅ |
| Exposome (air+social+noise) | WHO/Gallup | `exposome` → **/environment/\*** | **backend only — not in app** ⚠️ |
| Clinic engine (treat+therapy+supp) | — | → **/mgmt/clinic/\*** | **doctor only** ⚠️ |

---

## 3. Gaps — where a model should be used but isn't

1. **Lab-free chronic suite (5.89M) is doctor-only.** The single biggest gap: a consumer with *no bloods* gets
   nothing from our largest model. **Wire a consumer route** (`/me/chronic`, or auto-fallback inside `/predict`
   and the longevity view when a panel is absent). This makes every new user — before any lab — get a real risk
   screen from wearable + questionnaire. **High value, low effort.**
2. **Exposome engine isn't surfaced in the app.** 7,482-city air + social-connection + noise profile exists at
   `/environment/exposome` but there's **no environment screen** in mobile. Add one; it's a strong differentiator.
3. **Clinic engine (unified treatments + therapies) is doctor-only.** Consumers get the pieces (/me/report,
   /me/supplements) but not the composed, prioritised assessment. A consumer (ungated, decision-support) view
   would raise perceived intelligence.
4. **Fusion overlay under-surfaced.** The wearable→risk overlay exists but isn't clearly in the consumer
   longevity/risk card. Make the "your HRV/RHR/SpO₂ shifts your risk by X" explicit to the user.
5. **AFib + nocturnal-desat events aren't fed into the risk/mortality context.** Night-1 caught real 85–86%
   sleep desats; band detects af_pattern. These should flow into the stroke/CVD risk narrative, not just sit as
   events.

## 4. Where more training is required

| Priority | Model | Why / data |
|---|---|---|
| **High** | **Apnea / nocturnal-hypoxemia** | real signal seen (85% desats); train on PhysioNet SHHS/apnea-ECG + calibrated SpO₂ |
| **High** | **AFib retrain at scale** | af2017 is small; add MITDB/LTAFDB/LTAFDB for robustness |
| **High** | **Sleep-stager validation** | verify the ECG HSMM stager vs the patch raw ECG (pending on-device pull) + PSG |
| Med | **Organ-specific aging clocks** (heart/kidney/liver/metabolic/immune) | NHANES — Tier-1 differentiator |
| Med | **HRV → autonomic age** | patch R-R + population norms |
| Med | **Vascular age (PWV)** | ECG→PPG PTT; needs the driven calibration cohort |
| Med | **Deficiency clocks** | only vit-D (AUC 0.72); expand B12/ferritin/folate, improve |
| Med | **Pace-of-aging** (DunedinPACE-style) | needs repeat-visit panel features |
| Low | **Biobank-grade mortality/organ** | UK Biobank / MIMIC — **access applications required** |
| Ongoing | **Trained wearable-fusion head** | replace the evidence overlay once the Telomy device cohort has outcomes |

## 5. What to add (extra)

**Product / wiring (fast wins)**
- Consumer lab-free chronic screen (#3.1) — wire the 5.89M model to `/me/*`.
- Environment screen in the app (the exposome profile).
- Red-flag + nocturnal-desat **alerts/notifications** (the OSA signal, out-of-range biomarkers).
- The **driven SpO₂ calibration** flow (ring vs oximeter) — the one calibration that works.

**Data / sensors (measured, not estimated)**
- **CGM** + **cuff BP** integration → promote glucose/BP from estimate to measured.
- **WHOOP processed-data puller** (if subscription) → benchmark our HRV/sleep/recovery.
- Routine **multi-night capture** (clock-drift now fixed) → build the Telomy outcome cohort → trained fusion.

**Platform / infra**
- **SQLite → Postgres** for the multi-tenant plane at scale.
- Model **monitoring/drift** + a scheduled **retrain pipeline** (BRFSS/NHANES refresh).
- A **model registry** (MODELS_STATUS.md is the start) + CI that runs the PentAGI harness on every merge.

**Clinical / differentiation**
- Organ clocks + pace-of-aging + vascular age (Tier-1, `TOP20_MODELS.md`).
- Food quality from the **diet log** (NOVA), surfaced as a daily score (training showed survey food flags are weak).
- Social-connection prompt in onboarding (training showed marital/social is a top-3 exposome predictor for CVD/depression).

---

## Bottom line
The engine is deep and mostly well-wired. The **three highest-leverage moves** are: (1) expose the **5.89M lab-free
chronic model to consumers** (biggest unused asset), (2) **surface the exposome** in the app, and (3) start the
**routine multi-night device capture** so the evidence overlays become *trained* fusion models — the thing no
competitor can copy, because it needs our own ECG-grade longitudinal cohort. Training priorities are
apnea, AFib-at-scale, and sleep-stager validation, all of which have data in hand.
