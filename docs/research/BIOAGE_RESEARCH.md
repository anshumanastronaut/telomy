# Biological age — research, validation and the Telomy multi-age engine (2026-10-19)

A deep review of the age-estimation literature, three blood-based ages fitted/validated on real public population data
(NHANES), robustness simulations, plus fitness, muscle, heart and organ ages — all shipped in `backend/app/bioage.py`.

## 1. Methods reviewed

| Age | Method | Inputs | Why / status |
|---|---|---|---|
| **PhenoAge** | Levine 2018 — a mortality-trained transform of 9 blood markers + age | albumin, creatinine, glucose, CRP, lymphocyte %, MCV, RDW, ALP, WBC | mortality-based, most sensitive; **our existing engine** |
| **KDM biological age** | Klemera–Doubal 2006 — biomarkers regressed *on* age in a reference, inverted | 8 clinical markers (albumin, creatinine, ALP, BUN, total chol, HbA1c, log-CRP, SBP) | canonical clinical-biomarker age (BioAge toolkit, Kwon & Belsky 2021); **newly fitted on NHANES** |
| **Homeostatic dysregulation** | Cohen 2013 — Mahalanobis distance from a young-healthy reference | same biomarker set | distribution-free dysregulation score; **newly fitted** |
| **Fitness age** | VO2max vs age/sex norms (FRIEND registry, Kaminsky 2015; Nes 2013) | VO2max | the age whose median VO2max equals yours |
| **Muscle age** | ALMI (DEXA) or grip vs norms (Baumgartner 1998) | appendicular lean-mass index | sarcopenia-referenced |
| **Heart / vascular age** | Framingham heart age (D'Agostino 2008) / PCE | lipids, SBP, smoking, diabetes | optimal-risk-equivalent age for the same 10-yr CVD risk |
| **Organ ages** | imaging age-gaps + eGFR | MRI brain/liver gaps, eGFR | read from the Vault when present |

Epigenetic clocks (Horvath, Hannum, GrimAge, DunedinPACE) and proteomic/metabolomic clocks are the research frontier
but need DNA-methylation / omics assays; Telomy shows them if a lab provides them, but computes the blood-chemistry ages
above from standard panels.

KDM formula (Klemera–Doubal): for each biomarker *j* regress xⱼ on chronological age → intercept qⱼ, slope kⱼ, residual
SD sⱼ. Then `BA = [Σ(xⱼ−qⱼ)kⱼ/sⱼ² + CA/s_BA²] / [Σ(kⱼ/sⱼ)² + 1/s_BA²]`, with s_BA estimated from the training spread.

## 2. Validation on NHANES 2017-2018 (public, CDC — 5 569 adults, 70/30 train/test)

Fitted on the training set, scored on the held-out test set (`tools/bioage_study.py`):

| Age | r with chronological age | Age advancement (BA−CA) |
|---|---|---|
| PhenoAge | **0.92** (matches Levine's published ~0.94) | +0.8 ± 9.0 y |
| KDM-BA | **0.98** | +0.2 ± 3.5 y (well-calibrated) |
| Homeostatic dysregulation | 0.45 (rises with age, as expected) | — |

**Cross-method check:** PhenoAge and KDM age-advancement agree **r = 0.555** — two independent methods concur on who is
biologically older, without being redundant. PhenoAge is the sensitive (mortality) signal; KDM is the conservative,
chronological-age-anchored clinical signal.

## 3. Robustness simulations

- **Measurement noise** (±5 % on every marker): KDM shifts only **0.70 y** on average (95th pct 1.69 y) — stable.
- **Missing markers** (drop 2 of 8): KDM still correlates **r = 0.995** with the full-panel result — degrades gracefully.
- **Aging detection** (+10 y of biomarker drift): KDM rises ~1.4 y — this is KDM's known conservatism with a small marker
  set (it is anchored to chronological age); PhenoAge's ±9 y spread carries the sensitive signal. Adding more age-
  informative markers increases KDM's sensitivity.

The fitted parameters live in `backend/app/models/bioage_nhanes.json` and are loaded by the engine at runtime.

## 4. The engine (`bioage.py`, endpoint `GET /bioage`)

Returns every age it can compute from the person's Vault, each with method + citation + confidence, plus a headline
(PhenoAge if available, else KDM). On the current data it produces, for a 28.7-year-old: PhenoAge 19.3, KDM 28.1,
heart/vascular 46.6 (flagging the lipids), muscle 33.3, kidney 36, brain-age gap +0.3. Surfaced in the app on the
Biological age screen under "Validated biological ages".

## 5. Honesty & limits

- Fitted on NHANES 2017-2018 (one cross-section); the BioAge convention trains on NHANES III and validates on NHANES
  continuous — a next step is to refit on the pooled cycles for a larger reference.
- KDM/HD need the 8 clinical markers; the engine says which are missing rather than guessing.
- These are population-referenced statistical ages, not diagnoses. Anything medical routes to the clinician flow.
- Sources: Levine 2018 (Aging); Klemera & Doubal 2006 (Mech Ageing Dev); Kwon & Belsky 2021 (BioAge, GeroScience);
  Cohen 2013 (Mech Ageing Dev); Kaminsky 2015 (FRIEND, Mayo Clin Proc); Nes 2011/2013 (HUNT); D'Agostino 2008
  (Framingham heart age); Baumgartner 1998. NHANES data: CDC/NCHS, public domain.
