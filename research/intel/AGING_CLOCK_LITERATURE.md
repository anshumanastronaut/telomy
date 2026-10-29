# Aging-clock literature set — for Telomy's organ clocks

*Prepared 29 Oct 2026 from Shen 2024 (Nature Aging, nonlinear aging) + the organ-aging literature. Guides the organ-clock builds in `research/ageclock/` and `backend/app/organs.py`. Confidence: ✅ verified this session; ⚠️ high-confidence, pages not re-verified.*

## Shen 2024 — what we can use
**Shen X, … Snyder MP. Nonlinear dynamics of multi-omics profiles during human aging. Nature Aging 4, 1619–1634 (2024).** ✅ doi:10.1038/s43587-024-00692-2 (Open Access). N=108 adults, 10 omics, 135k features; code at GitHub `jaspershen-lab/ipop_aging`, data on iPOP/HMP2.
- **Finding:** aging is predominantly **nonlinear** — two reproducible crests of change at **~44** and **~60**. ~44: lipid/alcohol/caffeine metabolism, CVD, skin/muscle ECM. ~60: immune regulation/immunosenescence, carbohydrate metabolism, kidney (BUN↑, glucose↑), CVD.
- **Usable as:** (a) **twin presentation** — show organ ages as nonlinear trajectories with named inflection windows (early-40s / ~60), mapped to our organ set; strong peer-reviewed copy + chart structure for the twin + SLM. (b) **Calibration argument** — motivates replacing our linear residual bias-correction with a spline/LOESS (but it's bias-removal, not a claim aging is linear). **NOT a training corpus** (N=108, research-grade assays, non-representative). Corroborated by Lehallier 2019 (DE-SWAN crests ~34/60/78) ✅ — present as a *window*, not a point.

## Organ-specific aging (proteomic) — our twin's precedent
- **Oh HS, … Wyss-Coray T. Nature 624, 164–172 (2023).** ✅ 11-organ plasma-proteome clocks (SomaScan, N≈5,676). The canonical citation for our organ twin. Method reusable; data gated.
- **Oh HS, … Wyss-Coray T. Nature Medicine (2025).** ✅ 11 organs, 2,916 proteins, 44,498 UKB; aged brain → Alzheimer's. Evidence a brain clock predicts dementia.
- **Goeminne LJE, … Cell Metabolism (2024).** ✅ organ + mortality + longitudinal elastic-net clocks, >50k incl. UKB Olink. **Template for multi-target (age+mortality) training.**
- **Argentieri MA, … Nature Medicine (2024).** ✅ doi:10.1038/s41591-024-03164-7. 204-protein (and 20-protein subset ~91% accuracy) clock; multi-ancestry (UKB+Kadoorie+FinnGen). Business case for a lean proteomic add-on; disease-linkage = our validation bar.

## Methodology to replicate on routine labs (public = trainable)
- **Liu Z, … Levine M. PLoS Medicine 15(12):e1002718 (2018).** ✅ **Clinical PhenoAge** — chrono + 9 routine markers, mortality-anchored (Gompertz), NHANES. **Those 9 markers = our `clinic9` set.** PUBLIC — the clock to re-anchor to mortality.
- **Klemera & Doubal. Mech Ageing Dev 127:240 (2006).** ⚠️ **KDM** — second interpretable biological-age estimator; cross-check.
- **Kwon & Belsky. GeroScience 43:2795 (2021).** ⚠️ **BioAge R package** — open reference impl of KDM+PhenoAge on NHANES; our reproducibility anchor.
- **Tian YE, … Zalesky A. Nature Medicine 29:1221 (2023).** ✅ normative org-age models (3 brain + 7 body), multi-organ aging network, survival AUC 0.77. Closest clinical-data precedent; method fully reusable on NHANES.
- **Nie C, … Cell Reports 38(10):110459 (2022).** ⚠️ organ indexes from blood+stool+exam, Shenzhen cohort (Asian-ancestry, relevant to India focus).

## Per-organ clinical reference equations (defensible anchors)
- **Kidney:** Inker, CKD-EPI 2021, NEJM 385:1737 (2021) ✅ — race-free eGFR as the kidney backbone; renal clock = trajectory overlay.
- **Liver:** Sterling, FIB-4, Hepatology 43:1317 (2006) ⚠️ — inputs ast/alt/platelets/age all in our panel.
- **Lung:** Morris 1985 ⚠️ (display) + **GLI-2012** (Quanjer, ERJ 40:1324, 2012) ⚠️ for % predicted (ethnicity term for Indian users).
- **Muscle/bone:** EWGSOP2 (Cruz-Jentoft, Age Ageing 48:16, 2019) ⚠️ + Baumgartner ALMI 1998 ⚠️ + **Dodds grip centiles** PLoS One 2014 ⚠️ (replace crude 0.3 kg/yr slope).
- **Brain:** **Benkert 2022** age-adjusted sNfL reference (Lancet Neurol 21:246) ⚠️ (replace hand-tuned NfL curve) + Cole MRI brain-age ⚠️.
- **Immune:** iAge (Sayed, Nature Aging 1:598, 2021) ✅ + IMM-AGE (Alpert, Nat Med 25:487, 2019) ⚠️ — target once a cytokine panel exists; current CBC/CRP immune clock is interim (weakest, MAE ~14y).
- **Pace-of-aging:** DunedinPACE (Belsky, eLife 11:e73420, 2022) ✅ — concept for a future *rate* metric; do NOT claim methylation-grade accuracy from blood.

## What to change in our approach
1. **Fix provenance** — replace the unverifiable "Cell 2026 Digital Aging Twin" string (organ_tools.py, build_organ_clocks.py) with Oh 2023 + Tian 2023 + Nie 2022.
2. **Mortality-anchored target** — biggest upgrade; PhenoAge/KDM on the NHANES Linked Mortality Files (we have them locally). [In progress — training agent.]
3. **Nonlinear calibration** — spline/LOESS residual-on-age + per-decade residual report (replaces linear polyfit). Motivated by Shen crests.
4. **Anchor each clinical organ to its reference equation** (eGFR/FIB-4/GLI-2012/Dodds/Benkert), HistGBR clock as trajectory overlay.
5. **Twin = trajectories not lines** — Shen ~44/~60 crest windows structure the organ-trajectory UI + SLM copy.
6. **Honesty** — the phenoage r=0.917 is inflated (PhenoAge takes chrono as input); never imply proteomic/methylation precision from routine blood; proteomics (Argentieri 20-protein subset) is the honest tightening roadmap.
