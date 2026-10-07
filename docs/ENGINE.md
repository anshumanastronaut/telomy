# Engine & science

Every number Telomy shows comes from one of the methods below. Each carries its references in code (docstrings) and in the app ("Receipts",
"How this is calculated"). Evidence grades: **A** guideline / strong RCT · **B** moderate · **C** emerging · **D** insufficient.

## Biological age & scores
| Output | Method | Reference |
|---|---|---|
| Longevity dial | PhenoAge from 9 blood markers + age | Levine 2018, *Aging* |
| Domain scores | Weighted pillars, re-weighted when data is missing, confidence from n and recency | Telomy |
| HSAI (adaptability) | Echo OS spec: autonomic .25, recovery .20, cognitive .15, oxygen .13, thermoregulation .12, voice .10, metabolic .05→.15 (CGM); ±2σ; missing domains re-weighted | Lipsitz & Goldberger 1992; Echo OS DPR |

## Correlation engine (`engine.py`)
- **Event effects** — one OLS per outcome (HRV, RHR, deep sleep, sleep score, sleep hours): outcome(t) ~ every event kind on day t−1 + weekend + trend.
  All logged kinds are covariates; only kinds with ≥ 5 events are reported. Benjamini–Hochberg FDR (q = 0.05) across all tests.
  Receipts show adjusted vs unadjusted effects, 95% CI, p, n, covariates.
- **Therapy verdicts** — *Helped* (FDR-significant + split-half replication), *Promising* (p < 0.01, CI excludes 0, replicated, not yet past FDR),
  *Possible negative*, *No reliable signal*, *Too early* (< 5 sessions), *In-session only* (no wearable).
- Lagged signal correlations, lab trends, lab × wearable windows, **34 cross-modality rules** (e.g. CAC × ApoB, MASLD triple-concordance,
  masked hypertension, OSA × non-dipping, thyroid autoimmunity, CGM vs HbA1c, allergic airway, cortisol rhythm, G6PD gate).
- N-of-1 studies: ABAB with Welch t-test, three honest verdicts.

## Risk prediction (`predict.py`)
| Model | Notes |
|---|---|
| AHA PREVENT 2024 (10/30-y, 5 outcomes) | Coefficients from the `preventr` R package; matches the published example exactly |
| Pooled Cohort Equations + risk enhancers | Guideline examples reproduced; South-Asian caveat shown |
| ADA risk score + HbA1c bands | 5-y diabetes |
| FIB-4, KFRE (4-variable) | Liver fibrosis, kidney failure |

## In-session physiology (`physio.py`)
First-order state model integrated at 1 Hz (exact exponential step): each signal relaxes toward phase- and stimulus-dependent targets with
literature time constants; personal θ from the Vault (resting HR/HRV, fitness, metabolic and vascular markers); habituation ×0.8 per consecutive
cryo day; morning HRV scales the response. **Validated** against 11 targets (`GET /physio/validation`):
cryo HR +8–20 bpm, rebound +50–100 %, skin −8 to −15 °C (Louis 2020); cold-shock HR +15–40; HBOT SpO₂ 99–100 %, HR −5 to −15 (Lund 2003; PMC 2025);
sauna peak HR 100–150, post −5 to −12, core +0.5–1.1 °C (Laukkanen 2019); IR sauna peak 80–110, core +0.3–0.6 (AJP-RICU 2025).
Analytics on any trace: HR surge, time to peak, HRV suppression, rebound at 15–21 min, recovery constant *k* (log-linear fit), half-life,
rewarming half-time and TRI, SpO₂ kinetics, cardiac load, perfusion, PBM dose, deterministic safety tiers. Echo OS PINN training (ODE prior +
residual network) is the upgrade path once ≥ 500 real sessions exist.

## Digital twin (`twin.py`)
21 state variables; first-order kinetics toward lifestyle/drug-dependent steady states:
Hall 2011 energy balance (22 kcal/day per kg, τ ≈ 1 y); statins (CTT 2010; STELLAR), ezetimibe (IMPROVE-IT), psyllium (Jovanovski 2018);
ADAG HbA1c ↔ glucose; Look AHEAD; DPP; Heaney 2003 vitamin D; omega-3 index (Harris 2004); BP: −1 mmHg/kg (Neter 2003), alcohol (Roerecke 2017),
aerobic (Cornelissen 2013), ARB, PM2.5 (Liang 2014, flattening per GEMM/Burnett 2018); liver fat (Patel 2016; Keating 2012); lean mass (Morton 2018);
BMD ageing/smoking/training; VO₂ training/ageing; smoking-cessation weight gain (Aubin 2012). PREVENT and PhenoAge recomputed from projected values.
Personal calibration from the person's history (vitamin D response, alcohol → HRV, sauna → HRV, late caffeine → sleep). Mirror = fidelity score.

## Other models
| Area | Method |
|---|---|
| Voice stress | F0 mean/CV, jitter, shimmer, HNR, speech rate, pause ratio vs own baseline; fused 50/50 with 7-day HRV (Echo OS CLI). Evidence C. |
| Exposome | Open-Meteo / Copernicus CAMS daily PM2.5, UV, weather; within-person regression; AQLI (0.98 y per 10 µg/m³ above 5); Berkeley Earth (22 µg/m³ ≈ 1 cigarette/day) |
| Activities | Median ± MAD baselines (last 10), calm index (HR level/stability vs HRV), acute:chronic workload (Hulin 2014) |
| Food | Most-specific match food table; added sugar/sat-fat % of daily limits |
| Rx | Data triggers (labs, N-of-1, genetics), curated supplement–drug rules (NIH ODS / monographs), DDInter drug–drug pairs |
| Tests | USPSTF / ADA / ESC-EAS / KDIGO / CPIC triggers + Vault gaps |
