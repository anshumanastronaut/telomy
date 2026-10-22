# Telomy Therapy Case-Study Methodology — how to correlate what happens per person

**Date:** 2026-10-21 · How we turn each logged therapy session (cryo, HBOT, sauna, PBM, HBOT, …) and the
new diagnostics (BCA, DEXA, VO₂max, bloods) into a rigorous per-person case study, and then into a
population model. Grounded in n-of-1 / single-case causal-inference methodology.

## The core idea: three layers, three methods
A "case study" spans three time-scales. Don't conflate them — each answers a different question with a
different method.

### Layer 1 — ACUTE (within a session): the physiological signature
*Question: what happens to the body DURING this cryo/HBOT/sauna session?*
Capture continuous vitals from the ring/patch (HR, HRV, SpO₂, skin-temp; BP where available) across the
session phases, producing a per-session **signature curve** + safety flags. Known signatures to validate
against:
- **HBOT:** HR falls steadily across phases; BP steady on compression, rises on decompression. **SpO₂ is
  unreliable during HBOT** (hyperoxia + oximeter ceiling) — do not trust it as a signal inside the chamber.
- **Sauna:** HR rises like moderate exercise; BP falls after; sauna→cold-plunge gives a larger HR/BP drop.
- **Cryo:** direction is unsettled in the literature — exactly why we capture our own continuous data.
Method = signal processing (phase segmentation, peak/recovery, AUC), not statistics. This is also where
the safety agent lives (abnormal HR/SpO₂/BP → stop).

### Layer 2 — CHRONIC (across repeated sessions): the n-of-1 case study
*Question: is THIS person actually changing because of the therapy?*
Treat each client as a single-subject time series of outcomes (BCA lean/fat, DEXA bone/ALMI→muscular-age,
VO₂max→fitness-age, bloods→clocks/CRP, wearable RHR/HRV trends). Use the **strongest design the centre
can run** — this hierarchy is the whole game:

| Design | Causal strength | Feasible in a centre? |
|---|---|---|
| **Randomized n-of-1 crossover** (on/off/on/off blocks, ideally blinded) | **highest** — a real individual causal effect | yes for reversible therapies (cryo, PBM, sauna); plan deliberate ON/OFF blocks |
| **Multiple-baseline** (stagger therapy start across outcomes/body-sites) | high | yes |
| **Interrupted time-series + segmented regression / Bayesian structural TS** (pre-therapy baseline as counterfactual) | medium — needs enough baseline points | yes, the default when you can't randomize |
| **g-formula / Model-Twin Randomization on observational wearable data** (adjusts for time-varying confounders) | medium | yes, for always-on signals |
| **pre/post (person as own control)** | lowest — confounded by regression-to-mean, placebo, co-interventions | current `n_of_1()` — use only as a first look |

**Push toward ON/OFF blocks.** A deliberate wash-in / wash-out (e.g., 3 weeks cryo, 3 weeks off, repeat)
is the single cheapest upgrade from "they improved" to "the therapy caused it." Simple mean-difference or
non-overlap indices are *not* formally causal (per the n-of-1 causal-inference literature) — report them,
but earn causal language only from a crossover/ITS design.

### Layer 3 — POPULATION (pool many n-of-1s): the trained modality model
*Question: does this modality work, for whom, and how much?*
Pool every client's n-of-1 series per modality in a **hierarchical / mixed-effects model** (random effect
per person) → a population effect size + **effect modifiers** (who responds: age, sex, baseline CRP,
fitness). This is what finally **replaces the literature priors** in `modalities.py` with trained,
Telomy-owned numbers — and personalizes future recommendations. It is the real "trained model" that
emerges from the case studies; it needs no proprietary data to start (priors) and improves as data accrues.

## Confounding & honesty (non-negotiable)
- People change many things at once (diet, sleep, other therapies). **Log co-interventions** (intake
  profile + every modality + supplement + sleep/activity) and adjust for them; attribute cautiously.
- Prefer **objective biomarkers** (DEXA, VO₂max, bloods, wearable RHR/HRV) over self-report.
- Name the threats: **regression to the mean, placebo/expectancy, seasonality, measurement error** (and
  the HBOT-SpO₂ caveat). Without an ON/OFF or ITS design, say "associated with", never "caused".
- Match the **measurement cadence to each therapy's time-course**: acute = continuous in-session; short =
  daily wearables; periodic diagnostics at **baseline, 4–12 wk, then quarterly** (BCA/bloods faster;
  DEXA/VO₂max slower — don't retest DEXA monthly).

## Data model (what to log so the above is possible)
- `therapy_session`: client, modality, device, dose (temp/pressure/wavelength/duration), start/end,
  **intra-session vitals series**, operator, co-therapies that day.
- `diagnostic_event`: client, type (BCA/DEXA/VO₂max/blood panel/…), date, values, device.
- `protocol`: planned schedule incl. **designed ON/OFF blocks** for the crossover.
- `co_intervention`: supplements, sleep, activity, diet notes (for confounder adjustment).
- Outcomes link to the existing clocks/disease/fusion engines so every case study reports changes in
  blood age, muscular age, disease risk, fitness, inflammation.

## What to build next (concrete)
1. **Layer-1 session-signature extractor** (phase segmentation + safety flags) on the ring/patch stream.
2. **Layer-2 case-study engine**: ITS / Bayesian structural time-series (CausalImpact-style) + effect
   sizes (Tau-U, SMD) + co-intervention adjustment, upgrading today's pre/post `n_of_1()`; emits a
   per-client case-study report (acute signature + chronic effect + honest causal caveat).
3. **Layer-3 pooled mixed-effects recalibration** that updates `modalities.py` priors + flags responders.
Diagnostics (BCA, DEXA, VO₂max) slot in as `diagnostic_event` outcomes feeding Layers 2–3 and the
muscular-age / fitness clocks.

## Status — built & validated (2026-10-21)
Layers 1 & 2 are implemented and ground-truth-validated (no real centre data yet, so validated on
simulation where truth is known):
- **Layer 1** `telomy-slm/telomy_llx/signatures.py` — session-signature extractor (phases, peak/nadir,
  response, recovery, AUC, safety flags; HBOT SpO₂ correctly ignored in-chamber). Sauna↑ / HBOT↓ match.
- **Layer 2** `telomy-slm/telomy_llx/casestudy.py` — ITS segmented regression + CausalImpact-style
  counterfactual (residual-bootstrap CI) + Tau-U/SMD + co-intervention covariates + design-aware verdict.
- **Validation** (`benchmark_casestudy.py`, 400 sims/scenario): sensitivity 94% (strong) / 64% (weak);
  **false-"helped" on null 0%**; **regression-to-mean flagged positive 2%** (was 100% before the
  design-aware fix); effect recovery unbiased (−0.74 vs −0.75; −0.30 vs −0.30). A crossover design
  correctly rescues a level-change to "helped" where ITS flags possible-RTM. Tests: 18/18 pass.
- **Layer 3** (pooled mixed-effects recalibration of `modalities.py` priors) activates once centres log
  real sessions — the engine is ready to consume them.
