# Engine validation — sim-testing findings (iteration 1)

Reproducible harnesses that generate synthetic patients across clinical archetypes + randomised
perturbations, run each engine, and compare behaviour to clinical expectation. All run **isolated**
(pure functions or a throwaway scratchpad DB) — nothing is written to `telomy.db` or Oracle.

Run: `backend/.venv/bin/python research/validation/organ_clocks.py` · `.../risk_map.py`

## Headline fix — organ-clock age-compression bias (all 5 clocks)

The organ clocks (gradient boosting → chronological age; residual = "age acceleration") **regressed toward the
population mean (~50)**: they over-aged the young and under-aged the old. NHANES population-median panels,
which should read ≈0 acceleration at every age, instead read:

| age band | before (worst) | after calibration |
|---|---|---|
| 25–35 | **+7 to +21y** (hepatic 51 for a 30yo) | ±5y |
| 65–75 | **−8 to −23y** (renal 46 for a 69yo) | ±5–9y |

A healthy 30-year-old was being told their organs were 15–25 years old**er**; a 69-year-old got a falsely
reassuring reading. **Fix:** per-organ linear bias correction `pred* = pred − (a + b·age)` fitted on NHANES
(`research/ageclock/calibrate_organ_clocks.py` → `backend/app/assets/organ_calibration.json`), applied in
`app/llx/organ_tools.py`. Bias at young/old collapses from ±20y to ≈±0.5y; existing tests still pass (17/17);
disease signals preserved (uniform per-age shift). Residual non-linear drift remains on renal (−5 to −9y at
older ages) — a quadratic/isotonic correction would tighten it further (iteration 2).

## What behaves correctly ✓

- **Organ clocks (relative test, post-calibration): 6/6 disease archetypes.** diabetic→metabolic+cardiometabolic
  (+22/+17 vs healthy), fatty-liver→hepatic (+7), CKD→renal (+15), inflammation→immune (+14), metabolic-syndrome
  →both, dyslipidemia→cardiometabolic top-moved (+4). Each target organ is the most-elevated vs a clean panel.
- **Vault risk map (`derived.risk_matrix`): 5/5.** healthy→no highs; diabetic→T2D high; fatty-liver→MASLD high;
  dyslipidemia→ASCVD high (ApoB/Lp(a)/LDL drivers); CKD→CKD high. Deterministic, correctly weighted.
- **Chronic-risk ML (BRFSS, lab-free): strong discrimination.** high-risk vs healthy lifestyle separates every
  condition — diabetes 0.06→0.59, stroke 0.07→0.63, COPD 0.10→0.85, kidney 0.08→0.64.

## Open items (iteration 2)

1. **Chronic ML — `skin_cancer` probability is inflated.** A perfectly healthy 45yo white male reads **36.6%**
   (4× its 9% prevalence) and it ranks #1. Discrimination AUC is fine (0.79); the absolute probability is
   mis-calibrated → scary number for a healthy user. Needs probability calibration (Platt/isotonic) or a
   per-condition prior correction.
2. **Organ age-clock ≠ cardiovascular risk (by design).** The cardiometabolic clock is glucose-driven and only
   weakly moved by isolated dyslipidemia, because high LDL isn't a strong *chronological-age* predictor in NHANES
   (statins, young hyperlipidemics). This is inherent to age clocks — **do not present "cardiometabolic age" as
   capturing cholesterol/CVD risk**; `risk_matrix` is the correct surface for ASCVD (and it works). Product/UX note.
3. **Renal clock residual non-linearity** after linear calibration (above).
4. **Risk map depends on parser-set `status`.** Markers without zone bands (ALT/GGT/TG) can't self-classify in
   `risk_matrix`; manual `/labs/save` entries should compute `status` from ref ranges like the PDF parser does.

## Next engines to cover (harness extension)

longevity Rx (geroprotectors), macros, circadian (on real rhythm data), Sinc retrieval grounding, bioage
clocks, exposome. Same pattern: archetype in → assert expected direction → perturb × N → catalogue deviations.

---
# Iteration 2 — longevity Rx + macros (research/validation/longevity_macros.py)

**7/7 checks pass.** Longevity Rx: foundation tier always present; a condition adds clinical interventions
(healthy clinical 3 → diabetic 6); claims firewall holds. Macros: protein tracks 1.2–1.6 g/kg (75kg→90–120,
92kg→110–147 g/day), scales with weight, and **renal impairment caps protein to 0.6–0.8 g/kg + gates to a
doctor** (key safety behaviour, verified). Note: the engine's language is appropriately precise — "treat the
apnoea" and "detoxification pathways (clinical outcomes preliminary)" are legitimate, not overclaims.

**Correction on the iteration-1 skin_cancer note.** The 36.6% for a healthy white male is likely NOT a
mis-calibration: BRFSS skin_cancer is *"ever told you had skin cancer"* (lifetime history), and for older
white males lifetime non-melanoma skin cancer genuinely runs 20–40% — so the number may be correctly
calibrated. It reads alarming because lifetime history is surfaced like imminent risk → a **presentation/UX**
issue (label it "lifetime history", separate from forward risk), not clearly a model bug. Verifying properly
needs a reliability curve on held-out BRFSS, but `megaset.parquet` is not present locally (the raw dir is
empty); confirming/recalibrating would require re-downloading the BRFSS megaset via
research/chronicmodel/build_megaset.py. Left as a verify-first item, not a blind fix.
