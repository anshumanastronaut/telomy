# Wearable Correlational Signals — evidence review + what Telomy does vs should do

**Date:** 2026-10-21 · Prompted by Bryan Johnson's "resting heart rate is the single most important
marker I track" claim. This reviews RHR and the adjacent wearable signals against the literature, says
where each is solid vs weak, and maps it to Telomy's engine. Core principle unchanged: these are
**correlational/observational** — we rank risk and flag trends, we never claim lowering a number extends
lifespan.

## 1. Resting heart rate (RHR) — the signal Johnson highlights
**Evidence: strong (population) + strong face-validity (personal).**
- **Population mortality:** meta-analysis of ~1.2M people → **+10 bpm ≈ +9% all-cause mortality**; other
  meta-analyses +17% to +26% per 10 bpm; **RHR >80 ≈ 1.45× vs lowest**. Holds after adjusting for fitness
  (3,000-men, 16-yr cohort). (Zhang 2016 CMAJ; Aune 2017; Jensen 2013.)
- **Johnson's actual use is personal + nocturnal:** pre-sleep / nocturnal RHR **relative to his own
  baseline** (late meal → bedtime RHR up → worse sleep). This is an **n-of-1 deviation** signal, not a
  population cutoff — and nocturnal RHR on consumer wearables validates well (MAE ~2 bpm).
- **Caveat:** one lifetime-follow-up male cohort found baseline RHR non-significant but **time-updated**
  (trend) RHR informative — i.e., the *trend/baseline-relative* view is the stronger one.

**Telomy today:** ✅ `fusion.py` uses population RHR bands (≥90 high, 80–89 elevated, <70 healthy) with
cited hazard ratios. **Gap:** we do NOT yet use **personal-baseline / nocturnal RHR deviation** — which
is exactly Johnson's (solid) insight, and we already stream continuous RHR from the ring/patch.

## 2. VO₂max / cardiorespiratory fitness — the strongest *modifiable* predictor
**Evidence: very strong.** 750k-veteran study ~**14% lower mortality per fitness increment**; the
dose-response is among the largest in the mortality literature ("fitness age"). Wearable VO₂max estimates
(from HR + pace/HRV) are directional but less reliable (resting-based estimates overestimate vs lab).
**Telomy today:** ✗ not used. **Highest-value addition** — we can estimate a "fitness age" from
ring/patch HR + activity, labelled as an estimate.

## 3. Heart-rate recovery (post-exercise)
**Evidence: strong.** Abnormal recovery (≤12 bpm drop at 1 min) ≈ **2× mortality** (classic NEJM/Cole).
**Telomy today:** ✗ not used. Computable from the ring/patch HR trace around activity. Worth adding.

## 4. RHR trend → early-illness / overtraining flag
**Evidence: indirect but useful.** Elevated RHR tracked worse COVID outcomes; a personal-baseline RHR
spike is the basis of Oura/WHOOP illness/readiness flags (not outcome-validated, so label as a *signal*).
**Telomy today:** ✗ not used. Pairs naturally with #1 (baseline deviation) and the safety agent.

## 5. HRV — the one to be careful with
**Evidence: WEAK for consumer wearables / mortality.** Clinical ECG-HRV (SDNN) has mortality
associations (Dekker 2000), but **consumer PPG-HRV has no mortality cohort**, and a **UK Biobank
Mendelian-randomization analysis suggests HRV is likely NOT causal**. Readiness scores built on it are
unvalidated against outcomes.
**Telomy today:** ◐ `fusion.py` includes an HRV/SDNN band (clinical, cited). **Correction to make:** keep
HRV for *trend/recovery/context*, but **do not let consumer-PPG HRV carry a mortality claim** — weight
RHR and fitness above HRV for hard-outcome risk.

## 6. SpO₂ (nocturnal)
**Evidence: moderate** — mean <90% / min <88% = clinically significant desaturation, CV/mortality
relevance. **Telomy today:** ✅ in `fusion.py`.

---

## Verdict: are we "doing this logic"?
**Partly yes.** The population RHR→risk logic underpinning Johnson's "most important marker" claim is
already in `fusion.py` (cited hazard ratios). What's missing is the part Johnson *actually* relies on —
**personal-baseline / nocturnal RHR deviation** — plus the signals the literature rates even higher than
RHR: **VO₂max/fitness** and **HR-recovery**. And we should **down-weight consumer HRV** for mortality.

## Recommended additions (all feed from data we already collect)
1. **Personal-baseline RHR (n-of-1):** rolling baseline + z-score; flag deviations (illness/overtraining,
   or Johnson-style "late meal → worse sleep"). *Highest value, closes the Johnson gap.*
2. **Nocturnal RHR** as the primary RHR metric (cleaner than daytime resting).
3. **VO₂max / "fitness age"** estimate from HR + activity (labelled an estimate). *Strongest modifiable signal.*
4. **HR-recovery** from the post-activity HR trace.
5. **HRV re-weight:** trend/recovery only, not a mortality claim.

Implemented in `telomy-slm/telomy_llx/fusion.py` (baseline-relative RHR, HR-recovery, VO₂max/fitness-age
bands) — see that module. Everything stays correlational, device-fed, and clinician-in-the-loop.
