# Sleep tracking: what the best products do, and what Telomy does (2026-10-15)

## What the field knows
- **WHOOP** stages sleep with a proprietary model trained on in-house PSG (30-s epochs: Wake/Light/SWS/REM) using PPG
  heart rate, HRV, respiratory rate and 3-axis accel + gyro. Its **Sleep Need** = baseline + strain + debt − naps, and
  **sleep debt** feeds the next night's need. None of the weights are public.
- **Independent PSG comparisons** (4-stage Cohen's κ): Apple Watch ≈ 0.53 (Schyvens 2025, six devices), Oura 0.65 /
  Apple 0.60 / Fitbit 0.55 in an Oura-funded study (Robbins 2024), WHOOP 0.37 but strongest on deep sleep in Schyvens.
  In clinic patients κ falls to ≈ 0.35. Human scorers agree with each other at ≈ 0.75. Every source agrees that
  sleep-vs-wake and total sleep time are reliable; stage minutes are trends.
- **Open source**: SleepECG (cbrnr, BSD-3, HRV-based, trained on MESA/SHHS), Walch sleep_classifiers (Apple Watch accel +
  HR, PhysioNet sleep-accel, 31 people), Sridhar 2020 (IHR + deep net, κ 0.66 on SHHS/MESA). Telomy's patch stager
  follows Sridhar/Radha (HRV + ECG-derived breathing → Conv1d + BiGRU, trained on HMC).
- Reddit users largely echo the studies: trust total sleep and trends, not nightly deep/REM numbers.

## What Telomy now does (`mobile/src/lib/sleepfuse.ts`)
1. **One night per sleep period, from the best device worn**: patch (ECG stages) > Apple Watch stages (Apple Health
   segments, new `healthSleep` bridge) > ring only > other Health sleep. No double counting.
2. **Ring-only nights**: sleep/wake from the ring's 5-min HR log (within max(8 bpm, 12 %) of the night's 10th-percentile
   HR) gated by iPhone motion, smoothed, longest run ≥ 3 h. No stages are claimed from 5-min HR.
3. **Ring overlay**: lowest 15-min HR, sleeping HR, HR dip and ring HRV fill nights that lack them, so a Watch or ring
   night still gets a recovery score. HRV baselines only compare like with like (ECG vs ring).
4. **Sleep need** (transparent WHOOP-style): baseline 8 h → personal after 14 nights (mean of the longer half, 7–9 h),
   + up to 45 min for strain, + 30 % of debt (≤ 90 min). Suggested bedtime from your usual wake time.
5. **Sleep debt**: debt ← max(0, 0.85·debt + need − slept) over 14 nights (Van Dongen 2003); gaps decay, not count.
6. **Sleep Regularity Index** (Phillips 2017) replaces midpoint SD once 4 consecutive day-pairs exist.
7. Sleep score's duration term is now **sleep vs your need**.

## Next
- Decode the ring's own sleep record (bytes are logged verbatim in `Documents/ring-raw/ring-sleep-*.log`).
- Benchmark the patch stager against SleepECG on MESA with the same held-out subjects; add HMM smoothing if κ improves.
- Naps (Health segments < 3 h, 10:00–19:00) subtracted from need.
