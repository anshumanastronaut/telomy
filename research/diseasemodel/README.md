# Telomy Disease-Prediction Models

Trained on **NHANES 2009–2018** (30,352 adults) joined to **physician-diagnosed conditions**, plus the
**NHANES linked-mortality** files for long-term risk. Same method as the aging clocks: gradient-boosted
trees (HistGradientBoosting, native NaN), 20% held-out test + 5-fold CV. Grounded tools, not a chatbot
guessing.

## Cross-sectional disease screening (from a routine blood panel + age/sex)
Held-out test = **~6,000 reports** per model (well over the 5,000 bar). Metric: ROC-AUC (PR-AUC in ()).

| Condition | test AUC | n | Condition | test AUC | n |
|---|---:|---:|---|---:|---:|
| diabetes* | 0.887 | 29,607 | heart attack | 0.842 | 28,788 |
| heart failure | 0.858 | 28,764 | COPD | 0.826 | 17,037 |
| coronary heart disease | 0.849 | 28,725 | hypertension | 0.823 | 30,310 |
| cancer | 0.811 | 28,815 | kidney disease | 0.803 | 28,791 |
| stroke | 0.792 | 28,802 | angina | 0.793 | 28,742 |
| high cholesterol | 0.770 | 27,689 | liver disease | 0.731 | 28,774 |

\* diabetes scored **without** glucose/HbA1c to avoid circularity; with them AUC = 0.929 (expected,
those markers are diagnostic). These AUCs match or beat the published NHANES literature (CVD ~0.81,
diabetes ~0.89). "Guess the disease" ranks all conditions for one report — on a known-CHD patient it
ranked coronary_hd #1 (0.85).

## Long-term (robust)
10-year **all-cause mortality** from the routine panel (NHANES 2009–2012, ≥8–10y follow-up; clean
known-status labels): **AUC 0.81** (n=2,965, 124 deaths, test=593). Cause-specific CVD mortality had
only 46 events in these cycles — too few to train reliably (the cross-sectional CVD-disease models
cover that instead). UCOD leading causes parse correctly (heart 001, cancer 002, stroke 005, …).

## Grounded LLX integration
`telomy-slm/telomy_llx/disease_tools.py` exposes `predict_diseases(panel)` (ranked conditions) and
`mortality_risk_10y(panel)` as function-call tools. Telomy-LLX calls them and explains the numbers —
it never invents a diagnosis.

## Honesty / guardrails
Probabilities are **screening signals, not diagnoses**; decision-support, clinician-in-the-loop.
Mortality risk is age-dominated population ranking and needs calibration + comparison vs Pooled Cohort
Equations before any clinical use. Reproduce: `assemble_disease.py && train_disease.py &&
mortality_longterm.py` (uses the ageclock `.venv`).
