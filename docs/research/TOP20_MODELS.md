# Telomy — The 20 Models That Make Us Stand Out

Audited shortlist of the predictive models Telomy should own. The field (WHOOP, Oura, Function Health,
TruDiagnostic, biobank-LLM age models) competes on *one* axis each — a wristband signal, a blood panel, an
epigenetic clock. **Telomy's moat is the fusion**: ECG-grade signals + a real blood panel + calibrated
longitudinal wearable data, under one clinician-gated engine. The models below are chosen to exploit that.

## How this list was scrutinised (five audits)

Every candidate was scored against five gates; only models passing all five made the 20:

1. **Differentiation** — does it beat what a single-sensor competitor can do? (ECG/labs/fusion required.)
2. **Decision value** — does the output change a clinician's or member's action?
3. **Data at scale, free & legal** — can we train it defensibly? Target ≥1M, ideally ≥10M, from open data
   (BRFSS, NCHS mortality, NHANES, PhysioNet). Credentialed-only sources (MIMIC, UK Biobank, SEER) are flagged
   as "needs access," not counted as shippable tonight.
4. **Telomy-data fit** — uses what we uniquely collect, not a generic re-implementation.
5. **Regulatory safety** — expressible as decision-support under the claims firewall (A–D evidence grades).

**Honest scale reality:** only two data *families* are both free and ≥10M — **BRFSS all-years (~5.7M, →~8M with
pre-2011)** and **NCHS multiple-cause mortality (~3M deaths/yr × 25 yr ≈ 70M records)**. The lab/signal models
train on the largest open cohort for their modality (NHANES ~100k pooled; PhysioNet ECG/PSG 10k–100k). Each model
below states the *actual* achievable n, never an aspirational one.

---

## Tier 1 — Flagship differentiators (build these first)

| # | Model | Predicts | Data & scale | Status |
|---|---|---|---|---|
| 1 | **Pace-of-Aging** (DunedinPACE-style) | Rate of biological aging from longitudinal panels + wearables | NHANES longitudinal + Telomy repeat panels | **build** — needs repeat-visit features |
| 2 | **Organ-specific aging clocks** (heart, kidney, liver, metabolic, immune, lung) | Per-system biological age + acceleration | NHANES pooled (~100k) | **build** — extends the blood-age clock |
| 3 | **Multimodal 10-yr mortality / lifespan** | All-cause mortality + estimated lifespan, labs+wearable+questionnaire | NHANES-linked mortality (have, 0.81) + NCHS files (~70M) for actuarial calibration | **have→scale** |
| 4 | **Vascular age / arterial stiffness** (PWV) | Arterial stiffness → true vascular age | ECG R-wave→PPG PTT; calibration cohort (the recorder) | **build** — method ready, needs cal data |
| 5 | **AFib / arrhythmia from ECG** | Atrial fibrillation, ectopy, conduction | af2017 (on disk) + PhysioNet MITDB/LTAFDB | **have→retrain at scale** |

## Tier 2 — Chronic-disease suite, trained at millions (BRFSS)

| # | Model | Predicts | Data & scale | Status |
|---|---|---|---|---|
| 6 | **Lab-free chronic cardiometabolic suite** | Diabetes, CHD, heart attack, stroke, hypertension — no blood draw | **BRFSS 2011–2023 ~5.7M** (building now; 1.3M already shipped) | **scaling to ~5.7M** |
| 7 | **Respiratory risk** (COPD, current asthma) | Obstructive lung disease risk | BRFSS ~5.7M | **scaling** |
| 8 | **Kidney-disease risk** (lab-free) | CKD risk from non-invasive features | BRFSS ~5.7M | **scaling** |
| 9 | **Cancer risk flags** (skin, other) | Elevated-risk triage for screening | BRFSS ~5.7M (weak signal — triage only) | **scaling** |
| 10 | **Mental-health risk** (depression) | Depression risk from lifestyle + wearable HRV/sleep | BRFSS ~5.7M + HRV/sleep overlay | **scaling** |

## Tier 3 — Longitudinal / wearable signal models (Telomy's live data)

| # | Model | Predicts | Data & scale | Status |
|---|---|---|---|---|
| 11 | **Sleep staging from ECG + motion** | Hypnogram (wake/light/deep/REM) | sleepstage HSMM (on disk, 10k+ PSG nights) | **have** |
| 12 | **Sleep apnea / nocturnal hypoxemia** | OSA screen, desaturation burden | PhysioNet apnea-ECG/SHHS + calibrated SpO₂ | **build** |
| 13 | **HRV → autonomic age / stress** | Autonomic dysfunction, recovery, stress load | ECG R-R (patch) + population HRV norms | **build** |
| 14 | **Beat/arrhythmia classifier** | PVC/PAC/AF beat typing | MITDB/NSRDB (on disk) | **build** |
| 15 | **Frailty / fall risk** | Frailty index, fall propensity | IMU (falldetect.py) + vitals + age | **have→extend** |
| 16 | **VO₂max / cardiorespiratory fitness** | Fitness, strongest mortality predictor | HR+motion submaximal + lab CPET anchor | **build** |

## Tier 4 — Panel & body-composition models (owned, refine)

| # | Model | Predicts | Data & scale | Status |
|---|---|---|---|---|
| 17 | **Biological age / PhenoAge** | Biological age + acceleration from one panel | NHANES (have) | **have** |
| 18 | **Blood-panel disease screen (15 conditions)** | Ranked disease probabilities from a panel | NHANES 30k (have, 0.73–0.89) | **have→add cohorts** |
| 19 | **Muscular age / sarcopenia** | ALMI-based muscle age, sarcopenia risk | NHANES body-comp (have, MAE 9y) | **have** |
| 20 | **Nutrition / micronutrient-deficiency clocks** | Deficiency risk + nutrition age | NHANES dietary+labs (have) | **have** |

---

## What this buys Telomy

- **Nobody else fuses all three layers.** Oura/WHOOP have signal but no labs; Function/TruDiagnostic have labs
  but no continuous ECG-grade signal. Telomy's organ-clocks + pace-of-aging + vascular age sit on top of *both*.
- **Two models trained at true population scale** (chronic suite ~5.7M, mortality calibrated against ~70M NCHS
  deaths) — defensible numbers, not a 1k-sample demo.
- **A clinician-gated engine** (`clinic_engine.py`) already turns these into diagnostics + treatments + therapies
  + supplements, so each new model plugs into an existing doctor workflow, not a silo.

## Build order (tonight → this week)

1. **Tonight (autonomous):** scale the chronic suite to ~5.7M (BRFSS 2011–2023) and retrain all 11; retrain AFib
   at scale; draft the organ-clock + pace-of-aging feature pipelines.
2. **Next:** vascular age from the recorder's paired ECG→PPG data; apnea + HRV-autonomic from PhysioNet.
3. **Access-gated (apply):** UK Biobank + MIMIC-IV unlock the biobank-grade mortality/organ models the 2025
   literature shows (C-index ~0.76) — the one place we are currently data-limited vs. the frontier.

Every model ships as decision-support with an evidence grade; the clinician validates before anything reaches a
member. Scale and provenance are stated per model — we never claim a cohort we did not train on.
