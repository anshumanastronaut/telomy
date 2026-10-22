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

### Nutrition & deficiency ✅
| Model | Scale | Metric |
|---|---|---|
| NOVA food-processing classifier | **703,003** | accuracy 0.81, macro-F1 0.78 |
| Micronutrient deficiency (e.g. vitamin D) | ~10k | AUC 0.72 |

### Signal models (on-device data) ✅ / partial
| Model | Source | Status |
|---|---|---|
| AFib / arrhythmia (ECG) | af2017 cohort | trained; retrain-at-scale pending |
| Sleep staging (HSMM, ECG+motion) | sleepstage PSG | trained |
| Fall / activity (IMU) | falldetect | have |

## Roadmap (not yet trained — see TOP20_MODELS.md)
Pace-of-aging, organ-specific aging clocks, vascular age (PWV), apnea/nocturnal-hypoxemia, HRV→autonomic age,
VO₂max. Scale/data notes per model in `TOP20_MODELS.md`. Biobank-grade mortality/organ models need UK Biobank /
MIMIC access (application, not a download).

## Serving
All trained models plug into the doctor engine (`llx/clinic_engine.py`) → diagnostics + treatments + therapies
+ supplements, clinician-gated. Blood models fire when a panel exists; the lab-free chronic suite screens
everyone from day one on wearable + questionnaire features.

**Total trained: ~37 models** across 6 families. Committed on `telomy/calibration-workbench`.
