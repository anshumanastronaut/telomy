# Telomy data & models roadmap (2026-10-19)

## Principles
- Real person data stays the user's; synthetic data is labelled and never enters the Vault.
- Generated lab values are **twin projections**, never reports: separate store, "projected" label, anchored to the
  latest real report, replaced by the next real one.
- Every model ships with held-out evidence (NOOP_STUDY §4 rules); the bots re-check it daily.

## 1. Training data — what is open now vs what needs an application
| Dataset | What | Access | Status |
|---|---|---|---|
| PhysioNet sleep-accel (Walch 2019) | Apple Watch accel + HR + PSG, 31 people | open (ODC-By) | **used** — motion+HR stager, LOSO κ 0.47 |
| HMC sleep staging | ECG + PSG, 151 nights | open (CC BY) | used — ECG stager |
| PhysioNet slpdb, MIT-BIH, AFDB, PTB-XL | ECG sleep / arrhythmia | open | slpdb used for external test; PTB-XL next for rhythm |
| DREAMT (PhysioNet) | Empatica E4 wrist + PSG, 100 people | credentialed PhysioNet | user signs PhysioNet DUA |
| MESA, SHHS, CHAT (NSRR) | ECG + actigraphy + PSG, thousands of nights | NSRR data-use request | user applies at sleepdata.org |
| NHANES | labs, body measures, diet, mortality linkage | open | partly used (biomarkers); next: biological-age refit, lab projection priors |
| UK Biobank, All of Us | everything, very large | institutional application | later (needs an organisation) |
| PAMAP2, WISDM, Capture-24 | activity recognition | open | next: activity model |
| MIMIC-IV | ICU records | credentialed | not needed for consumer features |

## 2. Nutrition, supplements and medicines
| Source | Use | Licence |
|---|---|---|
| IFCT 2017 (ICMR-NIN) | Indian food composition (528 foods) | check NIN terms before bundling |
| USDA FoodData Central | 380k foods, nutrients | public domain |
| Open Food Facts | packaged foods, barcodes | ODbL (attribution, share-alike) |
| NIH ODS Dietary Supplement Label Database | supplement products, doses | public domain |
| NIH ODS fact sheets, ICMR-NIN RDA 2020 | targets per age/sex | public guidance |
| openFDA / DailyMed / RxNorm | drug labels, interactions text, normalised names | public / free UMLS licence |
| DDInter | drug-drug interactions | academic licence — check |

Loop (closed, per person):
1. Targets: protein (1.2–1.6 g/kg when training), fibre (≥ 30 g), carbs by CGM response, micronutrients from labs.
2. Plan: meals from the food tables + the user's preferences; supplements only where labs/diet show a gap
   (e.g. vitamin D < 30 ng/mL), never replacing prescribed medicines; interactions checked.
3. Measure: the effect engine (calibrated: 95 % CI coverage, 1.2 % false positives on the cohort) tests each change
   against sleep, HRV, resting HR, glucose; N-of-1 ABAB studies for supplements.
4. Recalibrate: keep what measurably helps, drop what doesn't, re-test labs at the planned interval.
Safety: anything touching medicines goes to a clinician review queue (exists: /care/queue); no dose changes by the app.

## 3. Twin lab projections (every 10 days, labelled "projected")
From the latest real report (2026-08-20) + real daily signals since → per-marker drift models (fitness, weight,
sleep, alcohol, smoking, diet) with uncertainty bands; shown only on the Twin, never in the Vault; each new real
report scores the projections (mean absolute error per marker) and refits.

## 4. CGM
No open-source *sensor* is medically approved; the open part is the reader software.
Recommended: FreeStyle Libre 2 Plus / 3 Plus sensor + **Juggluco** (open source, Android) on the Samsung, which
uploads to a Nightscout-compatible endpoint → Telomy adds a Nightscout receiver (same pattern as the WHOOP push).
iPhone alternative: xDrip4iOS (open source; self-built; Libre 3 support unconfirmed).

## 5. Bots (scheduled tasks)
- telomy-daily-cohort-sim (04:30): 100-person cohort + 5 000-person simulation, regressions, small tested fixes.
- telomy-data-health-bot (every 3 h): every pipe fresh? alert if not.
- next: nutrition-loop bot (weekly: review effects, propose plan updates for the user to accept).
