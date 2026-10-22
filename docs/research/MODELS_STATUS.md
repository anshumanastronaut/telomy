# Telomy Models — Status (single source of truth)

Every trained model, sorted by family, with its real scale, metric, and status. Updated after the
2026-10-22 run (chronic suite scaled to 5.9M). All are **decision-support** with provenance; a probability is
not a diagnosis.

## Trained & shipped

### Blood-panel disease screen — NHANES (14 models) ✅
From a routine panel + age/sex. ~30k adults, 20% held-out + 5-fold CV, ROC-AUC.

| Condition | AUC | Condition | AUC |
|---|---:|---|---:|
| diabetes (no glycemic) | 0.887 | heart attack | 0.842 |
| heart failure | 0.858 | cancer | 0.811 |
| coronary heart disease | 0.849 | kidney disease | 0.803 |
| hypertension | 0.823 | angina | 0.793 |
| stroke | 0.792 | high cholesterol | 0.770 |
| liver disease | 0.731 | COPD | 0.826 |
| **10-yr mortality** | **0.81** | diabetes (w/ glycemic) | 0.929 |

### Lab-free chronic suite — BRFSS **5,891,176** (11 models) ✅ *(scaled this run)*
From non-invasive features (age, sex, BMI, smoking, activity, sleep, self-rated health, known BP/chol flags).

| Condition | AUC | Condition | AUC |
|---|---:|---|---:|
| COPD | 0.844 | arthritis | 0.799 |
| coronary heart disease | 0.840 | kidney disease | 0.791 |
| heart attack | 0.830 | skin cancer | 0.783 |
| diabetes | 0.824 | other cancer | 0.757 |
| depression | 0.821 | asthma (current) | 0.705 |
| stroke | 0.809 | | |

### Aging / body-composition clocks ✅
| Model | Scale | Metric |
|---|---|---|
| Blood-age clock (telomy_full) | 27,340 | MAE **8.79 y**, R² 0.64, r 0.80 |
| Muscular-age clock | 21,610 | MAE **9.05 y**, R² 0.61 |
| PhenoAge / biological age | NHANES | published PhenoAge coefficients |
| **Organ clocks ×5** (metabolic/hepatic/renal/immune/cardiometabolic) | **49,693** | MAE 11.9–13.9 y; per-organ age-acceleration (served at `/me/organs`) |

### Nutrition & deficiency ✅
| Model | Scale | Metric |
|---|---|---|
| NOVA food-processing classifier | **703,003** | accuracy 0.81, macro-F1 0.78 |
| Deficiency clocks (vit D/iron/B12) | NHANES 18k | vit D 0.74, iron 0.79, B12 0.55 (diet ≠ B12 status) |

### Signal models (on-device data) ✅ / partial
| Model | Source | Status |
|---|---|---|
| AFib / rhythm (ECG, GBDT) | PhysioNet CinC-2017 (8,528) | **trained: challenge F1 0.783, AF Se 0.79/Sp 0.98** (served `/me/rhythm`) |
| Sleep staging (HSMM, ECG+motion) | sleepstage PSG | trained |
| Fall / activity (IMU) | falldetect | have |

## Roadmap (not yet trained — see TOP20_MODELS.md)
Pace-of-aging, vascular age (PWV), apnea/nocturnal-hypoxemia, HRV→autonomic age, VO₂max, activity-type
(NHANES accelerometer). Scale/data notes per model in `TOP20_MODELS.md`. **Honest caveat:** apnea/VO₂max labeled
data is small/discontinued (not "at scale"); AFib is already at its free-data max (8,528). Biobank-grade models
need UK Biobank / MIMIC access (application, not a download).

## Serving
All trained models plug into the doctor engine (`llx/clinic_engine.py`) → diagnostics + treatments + therapies
+ supplements, clinician-gated. Blood models fire when a panel exists; the lab-free chronic suite screens
everyone from day one on wearable + questionnaire features.

**Total trained: ~47 models** across 7 families. Consumer serving added this iteration: `/me/chronic` (lab-free 5.89M), `/me/organs` (organ clocks), `/me/rhythm` (AFib), `/me/environment` (exposome). All on `telomy/calibration-workbench`, deployed.
