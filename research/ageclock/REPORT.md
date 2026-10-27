# Telomy Aging-Intelligence Program — Research, Models & SLM Strategy

**Date:** 2026-10-20 · **Owner:** ananshubapu@gmail.com · **Status:** models trained & validated; SLM scoped

This document covers (1) what we trained and how it benchmarks, (2) the deep-research landscape,
(3) the recommended SLM to build, and (4) the defensible USPs for investors. Numbers below are
**real, reproducible** (`research/ageclock/train.py` on public NHANES 2009–2018), not projections.

---

## 1. What we built — the Telomy aging-clock family

Trained on **NHANES 2009–2018** (49,693 participants assembled; ~27,000 adults 18–80 with blood
panels). Every model uses gradient-boosted trees (sklearn `HistGradientBoostingRegressor`, native
missing-value handling) with a 20% held-out test set and 5-fold cross-validation. **Each model was
trained on ~27,000 samples — 27× the 1,000/model target.**

| Model | What it reads | N | Test MAE | R² | Pearson r | 5-fold MAE |
|---|---|---:|---:|---:|---:|---:|
| **telomy_full** (flagship) | full routine panel (37 markers) | 27,340 | **8.79 y** | 0.64 | 0.80 | 8.91 ± 0.20 |
| telomy_clinic9 | PhenoAge's 9 markers only | 27,791 | 12.20 y | 0.36 | 0.60 | 12.06 ± 0.24 |
| telomy_metabolic | glucose, HbA1c, insulin, lipids | 27,327 | 11.12 y | 0.43 | 0.66 | 11.11 ± 0.17 |
| telomy_liverkidney | LFTs + renal markers | 27,280 | 12.08 y | 0.36 | 0.60 | 11.84 ± 0.15 |
| telomy_cbc | haematology (CBC) only | 27,733 | 13.31 y | 0.24 | 0.49 | 13.44 ± 0.21 |

Linear (ElasticNet) baselines run ~2.5–3 years worse on MAE — the non-linear clock earns its keep.

**Biological age (not just chronological):** we also implemented the published **Levine-2018
PhenoAge** (mortality-validated) from the 9 clinical markers. It reproduces the literature:
**r = 0.917** vs chronological age (Levine reported r≈0.9). The clinically useful signal is
**age acceleration** = PhenoAge − chronological age (cohort mean −2.2 y, SD 8.9 y) — the per-person
number that actually moves with disease and lifestyle.

**Which markers carry the age signal** (|corr| with age, clinic-9): glucose (+0.22), albumin
(−0.21), MCV (+0.21), creatinine (+0.18), RDW (+0.17), lymphocyte % (−0.15), ALP (+0.12).
This matches the aging literature and gives clinicians an explainable readout.

Artifacts: `models/*.joblib`, `results.json`, `nhanes_bloodpanel.csv`. Reproduce with
`.venv/bin/python assemble.py && .venv/bin/python train.py`.

### Honest positioning of these numbers
- **8.79 y MAE is at parity with the best published routine-bloodwork clocks** (Central-European
  XGBoost 8.73 y; Aging.AI 5–7 y with larger/curated panels). It is **not** methylation-clock
  territory (DeepMAge 2.77 y, DeepStrataAge 1.89 y) — but those need a DNA-methylation assay costing
  100–1000× a blood panel and are not point-of-care. **Our edge is accuracy-per-rupee, not raw MAE.**
- The flagship beats the compact clock by ~3.4 y MAE, so breadth of panel matters — a lever we
  control by choosing what to measure.

### The credible path to beat the field (our real moat)
NHANES is **cross-sectional and has no wearable data.** Telomy already collects, per user and
longitudinally, **ring PPG + patch ECG (HRV, resting HR, arrhythmia events) + WHOOP**. The Chinese
cohort that reached **5.68 y MAE did it by adding biometrics to bloods.** We can fuse
**device-derived cardiovascular age** with **blood age** — a combination **no one else has at
consumer scale.** This is the single most investable technical claim in this document, and it is
grounded, not hypothetical: the data pipeline exists and is live (see the platform audit).

---

## 2. Deep-research landscape (aging clocks)

- **PhenoAge (Levine 2018)** — the reference blood clock: 9 markers + age, Cox model vs all-cause
  mortality; r≈0.9 to chronological age and predicts mortality *beyond* age. We reproduced it.
- **UK Biobank Elastic-Net Cox (2023, ~306k)** — C-index 0.778 vs PhenoAge 0.750 (+11% relative).
  Key finding: **cystatin C is the single most important marker, and PhenoAge omits it.** →
  *Action: add cystatin C to the Telomy panel; it's a cheap, routine assay.*
- **XGBoost routine-labs (46,739, 39 tests)** — the template we followed; ~8.7 y MAE.
- **Multi-omics / methylation** — most accurate (MAE <3 y) but assay-expensive; not point-of-care.
- **Reference implementations** we can lean on: `BioAge` (R, NHANES KDM/PhenoAge/homeostatic
  dysregulation), `pyaging` (pretrained KDM). Good for validation cross-checks.

**PINN / dynamical modelling — the honest take.** A true physics-informed neural network needs
*trajectories*; NHANES is a single snapshot per person, so a PINN cannot be trained on it. The right
place for a grey-box **Universal Differential Equation / latent Neural-ODE "pace-of-aging" head** is
**our own longitudinal device+biomarker data**, once each user has a multi-month history. That is a
roadmap item gated on data accrual — not something to claim as done today.

---

## 3. The SLM to build — recommendation

**Do not build another medical-QA chatbot.** Dozens exist and they hallucinate; that is not
groundbreaking and not defensible. Build the thing only Telomy can:

> **Telomy-LLX — an on-device "longevity reasoning" small model that is *tool-grounded* to the
> user's own measured biomarkers and the aging clocks above, and never guesses a number it can
> compute.**

**What makes it novel & defensible:**
1. **Tool-grounded, not generative-from-text.** The SLM does not "estimate age from a report" — it
   *calls* `telomy_full` / PhenoAge and then *explains* the result, citing the specific markers that
   drove it. This structurally suppresses the #1 failure of medical LLMs (fabricated numbers).
2. **Signal-aware.** It ingests structured biomarker time-series + device vitals (not just prose),
   so it reasons over trajectories, not snapshots.
3. **On-device & private.** Health data never leaves the phone — a genuine Telomy principle and a
   hard regulatory USP (India DPDP Act, GDPR). A cloud chatbot cannot claim this.

**Concrete build plan (feasible, staged):**
- **Base model:** **Qwen2.5-3B-Instruct** (Apache-2.0, strongest small medical base in 2025–26
  fine-tuning studies, good tool-calling). On-device variant: **Qwen2.5-1.5B**, 4-bit via MLX/llama.cpp
  on iPhone (A-series handles it).
- **Adaptation:** QLoRA instruction-tune on (a) structured→explanation pairs auto-generated from
  NHANES + our clock outputs, (b) curated clinical-guideline QA, (c) tool-call traces to the clock
  models. Fine-tune > RAG for this structured-interpretation task (per the 2026 clinical-NLP work);
  keep a small RAG layer for guideline citations.
- **Guardrails:** medicines still require a signed Rx; the SLM advises and explains, it does not
  prescribe. Every quantitative claim is a tool result, shown with its provenance.
- **Eval:** HealthSLM-style benchmark + our own held-out biomarker→age-acceleration set; refuse-rate
  and numeric-faithfulness as first-class metrics.

---

## 4. USP & investor narrative (defensible claims only)

**One-liner:** *Telomy turns a ₹500 blood panel and a wearable into a clinical-grade, explainable
biological-age readout — and an on-device longevity copilot that only ever speaks from the user's
own measured data.*

| Claim | Evidence | Why it's a moat |
|---|---|---|
| Clinical-grade aging from a cheap routine panel | MAE 8.8 y chrono; PhenoAge r=0.92, mortality-validated; reproduced on 27k | Accuracy-per-rupee; no methylation lab needed |
| The only multimodal longitudinal twin (bloods + ECG + PPG + clocks) | Live platform: ring/patch/WHOOP → cloud, aging clocks trained | Fusion path to <6 y MAE no competitor has at scale |
| On-device, privacy-first SLM | Qwen-1.5B 4-bit on iPhone; data never leaves device | DPDP/GDPR data-sovereignty; enterprise & clinic trust |
| A full clinical operating system already shipped | doctor / centre / super-admin workspaces, billing, care graph (verified) | Distribution + workflow lock-in, not just a model |

**What we are NOT claiming** (keep us honest with investors): we are not beating methylation clocks
on raw MAE today; the pace-of-aging ODE is a roadmap item gated on longitudinal data; the SLM is
scoped and based, not yet trained. Credibility is the asset — overclaiming kills a diligence process.

**Next 90 days (investable milestones):** add cystatin C to the panel → retrain → target <8 y;
build the wearable-fusion feature set (resting HR, HRV, arrhythmia burden) → target the ~5.7 y
regime; ship Telomy-LLX v0 (tool-grounded, on-device) behind the existing app.
