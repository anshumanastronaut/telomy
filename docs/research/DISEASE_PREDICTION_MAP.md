# Telomy Disease-Prediction Map

What Telomy can predict, from what data, with which model — and what each future sensor unlocks. This is the
clinical-intelligence backbone of the doctor side: every prediction is a **trained model or a cited evidence
rule**, never a free-text guess, and every output is **decision-support, not a diagnosis**.

Three prediction layers, by what the member has given us:

| Layer | Source | Model | When it fires |
|---|---|---|---|
| **A · Blood-panel** | lab PDF (34+ markers) + age/sex | NHANES 2009–2018, 30k adults, 15 conditions, AUC 0.73–0.89 | a recent panel exists |
| **B · Lab-free chronic** | onboarding questionnaire + wearable-derived lifestyle | **BRFSS 2021–2023, ~1.3M adults** (this build) | no recent bloods — wearable + Q only |
| **C · Longitudinal / device** | ECG patch, ring, oximeter, WHOOP over time | trained signal models (AFib, sleep-stage) + cited evidence overlays | continuous capture is running |

The engine uses the strongest layer available and fuses them: B screens everyone from day one, A takes over
once bloods arrive, C sharpens both with the continuous signal.

---

## Layer A — from a blood panel (trained, NHANES)

Routine panel + age/sex → ranked condition probabilities. Held-out AUC (PR-AUC in parentheses):

| Condition | AUC | | Condition | AUC |
|---|---:|---|---|---:|
| Diabetes* | 0.887 (0.62) | | Heart attack | 0.842 |
| Heart failure | 0.858 | | COPD | 0.826 |
| Coronary heart disease | 0.849 | | Hypertension | 0.823 |
| Cancer (any) | 0.811 | | Kidney disease | 0.803 |
| Stroke | 0.792 | | Angina | 0.793 |
| High cholesterol | 0.770 | | Liver disease | 0.731 |
| **10-year all-cause mortality** | **0.81** | | CVD death (long-term) | trained on linked-mortality |

\* diabetes scored **without** glucose/HbA1c to avoid circularity (with them, 0.929). The blood markers that
carry each prediction (e.g. RDW + albumin + creatinine for mortality; GGT + triglycerides for liver) are the
same ones PhenoAge uses — so the disease screen, the blood-age clock, and the biological-age estimate all come
out of one panel, each with marker-level provenance.

**What the panel predicts beyond the 15 models:** biological age + acceleration (PhenoAge), blood-age clock,
muscular age (when body-composition markers present), and the deficiency/nutrition clocks.

---

## Layer B — lab-free chronic risk (trained, BRFSS ~1.3M, NEW)

The gap Layer A can't fill: a member with a wearable and a filled questionnaire but **no blood draw yet**. BRFSS
has the chronic-disease outcomes at population scale and the non-invasive predictors Telomy already collects:

**Predictors (no blood needed):** age, sex, BMI, smoking status, physical-activity, **sleep hours**, general /
mental / physical health days, known-high-BP flag, known-high-cholesterol flag, heavy-alcohol flag, income,
education, insurance, race.

**Conditions screened:** diabetes, heart attack, coronary heart disease, stroke, COPD, current asthma, kidney
disease, skin cancer, other cancer, arthritis, depression.

Honest framing: BRFSS outcomes are self-reported "ever told by a doctor" and predictors are survey items, so
these are **risk-stratification screens** — they decide *who should get a panel / see a doctor first*, which is
exactly the triage value on the doctor side. (AUCs land in results.json after training; expected 0.75–0.85 for
the cardiometabolic set, lower for cancer which is weakly tied to lifestyle.)

As Telomy's own device cohort accrues outcomes, the questionnaire predictors are progressively replaced by
measured wearable features (real resting HR vs self-reported activity, measured sleep vs reported hours).

---

## Layer C — from longitudinal / device data

What the continuous capture (ECG patch + ring + oximeter + WHOOP, one clock) predicts. Trained models where we
have labelled data; cited population evidence otherwise (clearly flagged, upgradeable to trained when our cohort
matures).

| Signal | Device | Predicts | Basis |
|---|---|---|---|
| **ECG rhythm/morphology** | patch | **Atrial fibrillation**, ectopy, conduction | trained AF model (af2017 cohort) |
| **HRV (RMSSD/SDNN)** | patch (ECG-grade), ring, WHOOP | Autonomic dysfunction, CVD & all-cause mortality risk, overtraining | evidence overlay (fusion.py HRs) |
| **Resting HR** | all | Cardiorespiratory fitness, mortality (RHR >80 ≈ 1.5× HR) | evidence overlay |
| **Nocturnal SpO₂ + desat index** | oximeter, WHOOP | **Sleep apnea (OSA)** screen, nocturnal hypoxemia | evidence rule → refer to PSG |
| **Sleep architecture** | patch ECG + motion | Sleep-stage hypnogram, deep/REM debt, insomnia | trained HSMM stager (sleepstage) |
| **Skin temperature** | ring, WHOOP (calibrated) | Infection onset, menstrual phase, circadian disruption | evidence rule |
| **IMU / motion** | ring, WHOOP | Sleep/wake, physical-activity dose, frailty/fall risk | trained wake-detection + falldetect.py |
| **Pulse-transit / PWV** | patch R-wave → PPG | Arterial stiffness → **vascular age**, hypertension | method ready; needs calibration cohort |

The differentiator (`fusion.py`): join these device signals to the blood models into one **Telomy Risk Profile**,
stating plainly which part is a trained model and which is an evidence overlay.

---

## What each future sensor unlocks

Ordered by clinical ROI for the prediction map, not by novelty:

| Add | Unlocks (new or upgraded prediction) | Priority |
|---|---|---|
| **CGM (integrate)** | Glucose variability, true dysglycemia, upgrades the diabetes screen from "risk" to "measured" | High — integrate, don't build |
| **Cuff BP (integrate) + ECG→PPG PTT** | Calibrated cuffless BP trend; promotes the hypertension + vascular-age predictions | High |
| **Calibrated SpO₂ (in progress)** | Turns the OSA screen from investigational to usable; nocturnal hypoxemia burden | High — underway in the recorder |
| **Multi-site PPG timing / true PWV** | Segmental pulse-wave velocity → the real vascular-age biomarker (vs single-site proxy) | Medium |
| **In-ear / patch EEG (integrate, watch)** | Gold-standard sleep staging (validates the ECG stager), slow-wave % → cognitive-aging axis | Medium — integrate a reference device |
| **Continuous core/skin temp** | Circadian phase, infection prediction days earlier, ovulation | Medium |
| **Bioimpedance (ring/band)** | Body composition trend → muscular-age clock without DEXA | Low–Medium |
| **Sweat/optical biomarkers** | Cortisol, lactate, hydration — **do not build**, no validation; integrate labs/CGM instead | Avoid building |

Rule that holds across the map: **measure the gold standard where it exists (labs, CGM, cuff, PSG) and integrate
it; use the wearable for the continuous trend and the triage.** Telomy's edge is the ECG reference + per-user
calibration that lifts each wearable signal from "estimate" toward "clinical," plus the fusion of all three layers
into one longitudinal risk picture a doctor can act on.

---

## Doctor-side engine (how the map is served)

One patient → one grounded assessment the doctor validates, assembling the existing engines:

1. **Diagnostics** (`llx/report.py` + `disease_tools.py` + the new `chronic_tools.py`): Layer A if bloods exist,
   else Layer B; plus the clocks, PhenoAge, 10-yr mortality, and the Layer-C device overlay via `fusion.py`.
2. **Therapy** (`therapy.py`): centre-modality screening, a protocol builder with **clinician sign-off**, and
   per-person dose-response tracking — evidence-graded A–D, claims firewall enforced.
3. **Supplements** (`supplements.py`): biomarker-driven, safety-gated (interactions / contraindications), a
   **doctor-validation payload** (nothing ships without sign-off, like an Rx), and a retest/recalibration plan.

The orchestration (`llx/clinic_engine.py`) returns one payload: ranked risks with provenance → candidate
therapies → candidate supplements → the retest plan → a single doctor decision gate. The doctor validates or
edits; only then does anything reach the member. Decision-support throughout; the clinician is always in the loop.
