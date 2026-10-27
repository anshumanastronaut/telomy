# NOOP / WHOOP 4.0 deep study — what it assumes, what it found, what Telomy changes (2026-10-19)

Sources: NOOP source + docs (github.com/ryanbr/noop @ 8e4b0c1, PolyForm Noncommercial — studied, not copied),
the user's own WHOOP 4.0 data (NOOP backup, 2026-10-17/18), the Telomy patch session 20261018-012027 and the
Telomy ring flash log for the same night. Lab scripts (personal data stays outside the repo):
`~/telomy-lab/whoop/{analyse_night,compare_devices,ring_vs_whoop}.py`, `~/telomy-lab/sleepstage/eval_post.py`.

## 1. Measured on the shared night (n = 1 night, one wearer — direction, not population truth)

| Check | Instrument | Result | Verdict |
|---|---|---|---|
| WHOOP HR vs ECG patch | per-minute, 213 min | bias −0.6 bpm, MAE 1.2, r 0.94 | WHOOP HR trustworthy |
| NOOP HRV vs ECG RMSSD | 5-min RMSSD | NOOP ≈ 1.5–1.6× the ECG value | NOOP HRV inflated (WHOOP 4.0 history RR is re-delivered ~2.4×; NOOP itself reports beatAccurate 0.30–0.35) |
| Ring HR vs WHOOP | ±2.5 min | before fix MAE 17.6 bpm, r −0.18; after fix bias +1.4, MAE 5.0 | ring flash log was stamped local wall-clock (+5 h 30); fixed |
| Ring store | sample count | 20 000 rows → 3 287 distinct | dedup key used random dictionary key order; fixed |
| Ring SpO₂ overnight | history | median 77 %, range 54–146 | unusable; out-of-range rejected, nightly ring SpO₂ not used in scores |
| Sleep/wake vs NOOP | every epoch with data | ring 5-min HR κ 0.62; motion (HDCZA) κ 0.84 | motion must lead sleep/wake |
| Night continuity | session log | patch night ended ~4 h before the wearer woke | "ring disconnected" was read as "up"; fixed (positive evidence only) |
| BLE | ring log | ~205 link time-outs 20:00–09:00 | radio range (hand under body/pillow); data recovered from the ring's flash log |
| Stages, Telomy patch vs NOOP | 422 epochs | 45 % / κ 0.20; deep 29 vs 67 min; REM at onset (Telomy) | neither is PSG — see §3 |
| WHOOP 4.0 "resp" channel | 13 350 samples | only 2 distinct values | a status word, NOT a breathing waveform |
| Telomy breathing rate | ECG, 41 windows | the two ECG methods disagree by a median 12.7 /min (one locks on a harmonic) | the reported value is not trustworthy; gate on agreement |

## 2. NOOP's design — assumptions and what Telomy adopts

| NOOP assumption / finding | Evidence level | Telomy action |
|---|---|---|
| Sleep/wake from a 1 Hz gravity-stillness spine, HR only confirms | their bench + our night (κ 0.84 vs 0.62) | adopt motion-first for every device with motion (WHOOP, patch motionIndex, phone CoreMotion) |
| Elevated HR without motion is NOT wake (supplements, fever, heat) | 2 relabelled nights | adopt: no wake call on HR alone; same rule now in the auto-stop |
| Bridge night fragments with gaps < 60 min | design | adopted (90 min, `mergeFragments`) |
| Resting HR = lowest 5-min bin mean with ≥ 5 samples and ≥ 25 bpm | design | adopt the qualification gate (we take the raw lowest 15-min mean) |
| Recovery: HRV 0.55, RHR 0.20, sleep 0.15, resp 0.05, |skin-temp dev| 0.05; logistic k 1.6, z0 −0.2 (z=0 → 58 %) | design, anchored to WHOOP's published mean 58 | adopt skin-temp term + robust baselines; keep our weights until a temporal-split test says otherwise |
| Baselines: winsorised EWMA (half-life 14/21 nights, winsor 3 spread, reject > 5 spread), calibrating < 4, provisional 4–13, trusted ≥ 14, stale > 14 d | design | adopt (ours: plain mean/SD over 30 nights — one odd night moves it) |
| Effort: Karvonen %HRR zones, log scale, HRmax = max(observed p99.5, Tanaka) | a design choice, no accuracy evidence | NOT adopted: Telomy keeps Edwards' original %HRmax zones (rule 6: no change without evidence) |
| Workouts: HR > RHR + 15 AND gravity motion > 0.2 for ≥ 5 min, merge gaps < 150 s, ≥ 50 % in zone 2+ | design | adopt as the detector for WHOOP/patch streams |
| Calories: Keytel 2005 active + Harris–Benedict resting | published | adopt |
| Sleep debt: next = 0.55 × max(0, base + debt − slept); need = base + debt; < 10 min = balanced; surplus never banks | fitted on 853 consecutive WHOOP nights: within 15 min of WHOOP 93 % | **replace** Telomy's unvalidated 0.85-decay recurrence |
| Rest: duration vs need 0.5, efficiency 0.2, (deep+REM) share 0.2, consistency 0.1 | design | keep ours (richer) but make duration-vs-need dominant |
| Illness heads-up: ≥ 2 of RHR +5, HRV −20 %, skin temp +0.6 °C, resp +1.5 over last 2 d vs 28-d baseline ending 3 d ago | design | adopt |
| Confidence tier on every score: Calibrating / Building / Solid; show nothing rather than a fake number | design | adopt |
| Stager V2 (HR-flatness deep gate, cycle prior, relative jerk wake gate, RSA regularity, HMM) | LOSO 44 subjects (AAUWSS + Walch): κ 0.35, deep recall 55 % | not better than Telomy's ECG stager (external κ 0.36); borrow the 11-min HR-flatness feature for retraining |
| WHOOP 4.0 SpO₂ / resp raw words are not calibrated quantities | their protocol notes + our check | never show SpO₂ or breathing from WHOOP 4.0 raw words |

## 3. Things NOOP gets wrong or cannot do (do not copy)
- HRV from WHOOP 4.0 history R-R (re-delivered beats). Telomy's ECG patch is the HRV reference.
- An afternoon "nap" scored with deep sleep while HR stayed ~15 % above the sleeping level, and a near-maximal day Effort with no workout logged — both suspect.
- Stage accuracy claims: their own default is κ 0.35 cross-subject — the same ceiling every HR+motion stager hits.

## 4. Validation rules Telomy now follows (adapted from NOOP's VALIDATION_PROTOCOL — process, not code)
1. Pre-register prediction, threshold, domain (whole-record vs in-session), exclusions and n before measuring.
2. Never score against a reference our own scorer produced.
3. Every number ships with the command that regenerates it and the input/date.
4. Stage fractions → signed per-stage bias in minutes/pp; timing → onset/final-wake error in minutes; κ only next to class marginals; raw agreement only next to the constant predictor.
5. Temporal split for anything fitted on one wearer.
6. Check the mechanism is possible and the base rate before believing it.
7. n, instrument, units and measured-vs-inherited travel with every figure.

## 5. Fix list (status)
- [x] Ring timestamps, ring dedup, ring junk values, false morning stop, fragment merge, uncovered tails
- [x] Stager HMM/time-prior post-processing tested on PSG — made it worse (slpdb κ 0.356 → 0.30); NOT shipped
- [x] Sleep debt → NOOP-validated 0.55 recurrence
- [x] Robust winsorised-EWMA baselines + confidence tiers; skin-temp term in recovery (ring temperature per night)
- [ ] Workout detector (HR + motion) and Keytel calories
- [x] Illness heads-up (2-of-4 rule) on the Recovery screen
- [ ] Breathing rate: report only when RSA and EDR agree within 2 /min; 60-s counted-breaths calibration
- [ ] WHOOP nights (from the push receiver) into the app's fused nights, motion-first, HR from WHOOP
- [ ] Retrain the stager with motion + HR-flatness on more PSG data (MESA/SHHS via NSRR; Walch; AAUWSS) — needs PyTorch
- [ ] 5 000-person virtual population run over all engines (tools/vpop)
