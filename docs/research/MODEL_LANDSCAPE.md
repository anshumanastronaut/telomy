# Telomy model landscape — every function, what we run, what the field runs, and where we go next

Status as of 2026-10-14. Each section: **what Telomy does now → state of the art → public data to train/validate →
how we measure it → next step.** Claims about other work are summarised from the cited papers; check the primary
source before quoting a number externally.

---

## 1. ECG beat detection (KY-E-B1 patch, 100 Hz single lead)
- **Now:** Pan–Tompkins QRS detection with search-back + T-wave rejection, parabolic R-peak refinement; two-detector
  agreement (bSQI) for signal quality.
- **Field:** Pan–Tompkins (1985) and Hamilton remain the reference classical detectors; open toolkits (NeuroKit2,
  WFDB `xqrs`) bundle several. Deep detectors exist but give little on clean single-lead data; their value is in noise.
- **Data:** MIT-BIH Arrhythmia, MIT-BIH Noise Stress Test (PhysioNet) — standard sensitivity/PPV benchmarks.
- **Measure:** beat-level Se / +P at ±150 ms (ANSI/AAMI EC57).
- **Next:** run EC57 scoring on MIT-BIH + NSTDB resampled to 100 Hz to get a published-style number for our detector.

## 2. HRV
- **Now:** time-domain only (RMSSD, SDNN, pNN50) after Lipponen–Tarvainen artefact correction — 100 Hz is too coarse
  for frequency-domain HRV (Task Force 1996 recommends ≥ 250 Hz for spectral work).
- **Ring:** now captures **PPI (0x0616)** and computes RMSSD on-phone. Literature (e.g. Schäfer & Vagedes 2013 review)
  finds pulse-rate variability tracks ECG HRV well **at rest/sleep** and degrades with motion → we weight ring HRV
  only in still/sleep windows.
- **Measure:** Bland–Altman ring-vs-patch on paired windows (`telomy-lab/validate/ring_hrv.py`).

## 3. Rhythm / AF screening
- **Now:** on-phone gradient-boosted classifier on RR features, trained on PhysioNet/CinC 2017 (8,528 single-lead
  ECGs) with AFDB/NSRDB long-record checks.
- **Field:** CinC 2017 top entries (deep CNN/ensembles) reached F1 ≈ 0.83 on the hidden set. Large PPG-based screening
  trials — Apple Heart Study (NEJM 2019), Fitbit Heart Study (Circulation 2022) — showed irregular-pulse notifications
  have useful PPV when confirmed by ECG patch.
- **Positioning:** screening, never diagnosis; repeated flags → 12-lead ECG.
- **Next:** 1D-CNN on raw 100 Hz ECG (CinC 2017 + Chapman-Shaoxing 12-lead, lead I) as a second opinion to the GBDT.

## 4. Sleep staging
- **Now:** Conv1d+BiGRU on ECG-derived features, trained on HMC (151 nights, CC BY 4.0), 4-class W/L/D/REM, ported to
  Swift. **Fixed today:** staging is now gated to overnight sessions / ≥ 2 h of the 23:00–06:00 window (a 19:25
  awake session was being scored as 156 min of sleep).
- **Field:** cardiorespiratory/PPG stagers (e.g. SleepPPG-Net, Kotzen et al. 2022; Walch et al. 2019 Apple Watch
  motion+HR) reach roughly κ 0.6–0.75 for 4-class vs PSG — below PSG inter-scorer agreement but useful for trends.
- **Data:** NSRR cohorts (MESA, SHHS, CFS) — thousands of PSGs with ECG + PPG; access by data-use agreement.
- **Next:** add ring IMU (now capturable) as a motion channel; retrain on MESA (has PPG + actigraphy) for the ring.

## 5. Ring optical vitals (HR, SpO₂, temperature)
- **Now:** spot + on-device 5-min monitoring, history synced every 5 min (sequential protocol fixed today).
- **Honesty line:** ring **blood pressure and blood glucose are not measured** — the vendor app models them (BP needs a
  user calibration). ESH 2022 statement (Stergiou et al.) does not recommend cuffless BP for diagnosis; the FDA (Feb
  2024) warned against smartwatches/rings claiming non-invasive glucose. Telomy never stores or shows either.

## 6. VO₂max / fitness age
- **Now:** measured VO₂max from Apple Health when present; else Uth–Nes (VO₂max ≈ 15.3 · HRmax/HRrest), HRmax by
  Tanaka (208 − 0.7·age); fitness age vs FRIEND/ACSM norms.
- **Field:** wrist estimates are typically within ~±5 ml/kg/min of lab tests at the population level, with larger
  individual error; Kokkinos et al. (JACC 2022, 750k veterans) — fitness strongly and gradedly predicts mortality.
- **Next:** submaximal walk-test protocol in-app using patch HR for a better individual estimate.

## 7. Biological age clocks
| Clock | Inputs | Status in Telomy |
|---|---|---|
| **PhenoAge** (Levine 2018) | 9 blood markers + age | Live (blood) — now also computed on NHANES for validation |
| KDM (Klemera–Doubal) | Blood + physiology | Candidate — easy to add from same panel |
| GrimAge / DunedinPACE | DNA methylation | Out of scope until we offer an epigenetic test |
| **Fitness / Recovery / Cardiac / Muscle age** | VO₂max, HRV, RHR, ALMI (+EMG) | Live on device (`lib/ageclocks.ts`) |
| Wearable motion clocks (Pyrkov et al. 2018, NHANES accelerometry) | Step/activity patterns | Candidate once ring IMU is decoded |
- **Today's experiment** (`ml/biomarkers/nhanes_synth.py`, NHANES 2017–18, real held-out): wearable + basics predict
  PhenoAge acceleration with R² 0.14, hs-CRP 0.28, HbA1c 0.12; LDL/TG/ALT ≈ 0. → wearables cannot replace the blood
  panel; they can flag inflammation risk and track trends between draws.

## 8. Cardiovascular risk
- **Now:** AHA PREVENT (2023) 10/30-year in the twin.
- **Field:** PREVENT supersedes PCE in the US; SCORE2 (Europe), QRISK3 (UK). None calibrated for South Asians
  specifically — known under-estimation of risk in Indian populations is a documented concern (MASALA, INTERHEART).
- **Next:** show PREVENT with a South-Asian caveat; add ApoB/Lp(a) context which the twin already holds.

## 9. Muscle age & the EMG patch
- **Now:** Muscle age from ALMI vs NHANES DXA norms (Kelly 2009); EWGSOP2 sarcopenia cut-points; EMG test protocol and
  UI (`app/muscle.tsx`) ready for the patch.
- **Science for the patch:** during sustained contraction the sEMG **median frequency falls** as fatigue sets in
  (De Luca 1997; Merletti & Parker); its slope and recovery reflect fibre-type composition and conduction velocity,
  both of which change with age. RMS at MVC reflects neural drive. Sit-to-stand (CDC STEADI norms) anchors function.
- **Data:** open sEMG sets (e.g. NinaPro for gestures; PhysioNet EMG examples) cover signal processing, not ageing —
  **an ageing EMG dataset does not publicly exist**, so the patch's first cohort (with DEXA + grip + chair-stand) is
  itself a research contribution.

## 10. Liver
- **Now:** MRI-PDFF from imaging when available.
- **Field:** Fatty Liver Index (Bedogni 2006: BMI, waist, TG, GGT) — validated non-imaging screen; NAFLD fibrosis
  score / FIB-4 for fibrosis. All computable from NHANES variables we already load.
- **Next:** add FLI and FIB-4 to the twin's Liver system when labs exist.

## 11. Synthetic data
- **Method chosen:** Gaussian copula on real NHANES train split (fidelity: correlation-of-correlations 0.96).
  Alternatives: CTGAN/TVAE (Xu et al. 2019), synthpop (CART). Evaluation: **TSTR** (train-synthetic, test-real).
- **Result:** TSTR ≈ TRTR within 2–5 % — faithful but adds no information. Use it for: development, demos, sharing
  with partners, privacy-preserving pipelines. Do not use it to claim accuracy. Every synthetic row is `synthetic=1`
  and never enters a user's Vault.

---
**Rule that runs through all of it:** a number shown to a user must come from a measurement or a validated model with
its uncertainty — otherwise Telomy shows "measure this" instead of a guess.
