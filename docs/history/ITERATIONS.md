# Telomy — iteration log

## Iteration 1 — 2026-10-06

### Built
- **Backend** (`backend/`, FastAPI + SQLite, 71 tests passing)
  - Lab-PDF parser: 15 report types / 191 markers parsed with dates, units, the lab's own ranges and flags; panel routing for blood, advanced blood, gut, genetics, biological age, heavy metals, toxins, VO2 max/CPET + functional tests, DEXA, BCA, cardiac CT (CAC + CCTA), MRI (liver PDFF, brain, cardiac, whole-body), sleep study + screening (CIMT, MCED, FIT), proteomic organ age.
  - Catalogue of ~160 markers with optimal bands, evidence grades (A/B/C), LOINC where available, **sex-personalised clinical zones**, **15 health-concern groups**, retest intervals and retest-prep advice.
  - Derived markers: TG/HDL, AIP, TyG, ApoB/ApoA1, FIB-4, NLR, ANC, eGFR (CKD-EPI 2021 creatinine and 2012 cystatin C), HOMA-IR.
  - Engine: PhenoAge (Levine 2018) dial with contributors and history; 4 domain scores with weighted pillars that re-weight on missing data; **correlation engine** = event→signal effects (Welch t, Cohen's d, Benjamini–Hochberg FDR), signal↔signal lagged Pearson, lab trends, lab×wearable windows, and **23 cross-modality rules** (CAC×ApoB, MASLD imaging×enzymes×FIB-4, VAT×insulin resistance, sleep apnoea×SpO2, brain MRI×vascular risk×APOE, organ-age×corroborating tests, DEXA vs BCA disagreement, cystatin vs creatinine eGFR, omega-3×TG×mercury, …).
  - **Disease-risk matrix** (12 conditions) with drivers, coverage and missing tests; **action plan** (food / supplements / lifestyle) linked to target markers with impact and contraindication-aware **Avoid**; **retest nudges**.
  - Sinc (Claude `claude-opus-5-5` when a key is present, otherwise grounded retrieval) with evidence chips, confidence, clinician-review flag and draft-to-clinician; clinician review queue (sign / modify / reject with note); N-of-1 ABAB studies; meal analysis; weekly Indian menu + swap; consent centre with history; Family Vault with access log; specialist packs (PDF + FHIR) for 6 specialties.
- **Mobile** (`mobile/`, Expo SDK 57): tabs Home · Vault · Sinc · Sessions · Profile + 25 screens.

### Verified in the iOS Simulator (iPhone 17 Pro, Expo Go)
Home (dial, cards, Sinc read, domains, pinned, 7-day summary, appointment, Vault Rewind), Vault (13 panels, risk map, marker list), marker detail (zones, history, every result, levers, connected patterns), insight detail (receipts, evidence, review), Sinc chat, Sessions (checklist tick, action plan incl. Avoid), Log meal analysis, Profile, Specialist pack + FHIR.

### Defects found and fixed this iteration
| # | Defect | Fix |
|---|---|---|
| 1 | Parser read blank values (cell-per-line PDF layout) | Cell-mode parser |
| 2 | Bio-age report routed to genetics ("epigenetic") | Keyword order |
| 3 | False correlations (stress→sleep, travel→RHR) | BH FDR + ≥5 events |
| 4 | Cross-panel confidence saturated at 0.95 | Evidence-grade weighted support |
| 5 | Risk over-calls (benign renal cyst → cancer; UACR A1 → kidney) | Zones drive risk; incidental findings excluded |
| 6 | Consent history order wrong within one second | Order by id |
| 7 | Tappable cards collapsed (Domain cards) | Layout props on Pressable |
| 8 | Vault Rewind showed later hs-CRP and later insights | as_of-aware values + insight evidence dates |
| 9 | "Chicken biryani" analysed as plain chicken | Most-specific food match |
| 10 | Sinc HRV answer ranked irrelevant patterns; "p ≈ 0.0", 100 % confidence | Metric-aware ranking, period comparison, stop-words, p < 0.001, confidence cap 0.9 |
| 11 | Text polish: "121.0 on 2026-10-01", lowercase panel names, chart ticks, overflow, duplicated "test data" | Fixed |
| 12 | Cardiology brief missing CT/CCTA/advanced markers | Briefs extended; neurology brief added |

### Open — next iteration
1. Effect estimates are confounded (sauna overstated because sauna and workout days alternate) → multivariable regression / mixed model per outcome.
2. Sinc HRV answer should also surface hs-CRP×HRV and sleep-apnoea links; add Deep Research mode with literature citations (Ultrahuman Jade parity).
3. Fish "Avoid" rule should distinguish low-mercury small fish.
4. Imaging: real DICOM viewer; store radiology impressions as findings from the PDF.
5. AHA PREVENT 10/30-year risk (needs official coefficients + blood pressure input), SCORE2, FRAX.
6. HealthKit / Health Connect live sync (requires a development build, not Expo Go), Terra for Oura/WHOOP/Ultrahuman.
7. Photo meal logging + barcode; voice event capture.
8. Upload flow through the iOS document picker not yet exercised in the simulator (API path tested).
9. Install on the physical iPhone (dev build signed with the user's Apple ID) and Android APK for the Galaxy A35.
10. Teardowns pending: Fittr (phone locked), Ultrahuman Ring/M1/Home (hardware-gated).

## Iterations 2–3 — roles, plans, validated prediction

**Shipped**
- Role selection at first launch (user · doctor · wellness-centre owner); each role gets its own tabs and home. 140-patient doctor panel ranked by risk, work queue (monthly reports, Sinc drafts, consults), centre dashboard (revenue vs same days last month, utilisation, members, bookings, service outcomes).
- Plans after pricing research (Practo, Function Health, Superpower, Ultrahuman Blood Vision): Free / Essential ₹499 / Plus ₹1,499 / Longevity Pro ₹3,999 per month; on-demand GP ₹699, specialist ₹1,499, longevity physician ₹1,999; centre and doctor-seat plans. Payments are test mode only.
- Auto-generated monthly report every month → doctor signs with a note (Plus/Pro) → patient sees the signed report. On-demand consults with a pre-clinic brief → doctor completes with notes.
- Validated prediction: AHA PREVENT 2024 (10/30-year; matches the preventr reference example exactly), Pooled Cohort Equations (match guideline examples), ADA diabetes score + HbA1c bands, FIB-4, KFRE. What-if levers recompute every model.
- Multivariable (OLS) event effects with BH FDR, Deep Research mode in Sinc with curated citations, sex-specific zones, action-plan safety gating.
- Inter + Fraunces typography; Telomy logo, splash and boot video.

**Bugs found while testing all three roles (fixed)**
| # | Bug | Fix |
|---|---|---|
| 13 | Consult scheduled before it was requested (slot used app day, request used wall clock) | Single app clock (`engine.now_iso`) for every timestamp; GP slot = next half hour, others next day 10:00; regression test |
| 14 | Monthly report "auto-generated 7 Oct" while the Vault day is 6 Oct | Same app-clock fix across plans, roles, seed, Sinc, food, events |
| 15 | Revenue compared month-to-date with a full month | Same-day window |
| 16 | Steps shown with decimals in monthly report | Integer signals rounded |
| 17 | Monthly protocol adherence 0 % | Checklist history seeded |
| 18 | Monthly / vault deep-link params ignored | `useEffect` on params |
| 19 | Breathe header under the status bar | Safe-area insets |
| 20 | Doctor consult count ≠ list | Combined counts, list capped, "Needs attention" first |

**Verified end to end in the Simulator:** user books a plan-covered GP consult → doctor sees it in Work queue → completes with notes; doctor signs the September monthly report with a note; plan switching Free ↔ Essential ↔ Plus ↔ Pro (Pro shows "Unlimited GP consults"). Backend: 85 tests passing.

### Open — next iteration
1. iPhone release build with the JS bundle embedded; backend reachable from the phone (same Wi-Fi or hosted).
2. Private GitHub repo `telomy` (needs `gh auth login`).
3. HealthKit / Health Connect sync; Android build for the Galaxy A35.
4. Real Claude key for Sinc; PREVENT optional UACR/HbA1c models; SCORE2, FRAX.
5. DICOM viewer; photo meal logging.
6. Hosted backend with real authentication.

## Iteration 4 — inside the machine, the digital twin, voice and the person's own life

**Audit against Telomy DPR v5, the 10 Features / Next 10 / USP docs and the Echo OS DPRs + PINN code.**
Missing before this iteration: in-session physiology, therapy response fingerprinting, HSAI, a full tests catalogue, doctor-certified
supplements/Rx/IV, doctor-side report summaries, voice, routines, custom activities, exposome and a digital twin. All built below.

**Built**
- *In-session physiology* (`physio.py`): numpy port of the Echo OS calibrated ODE priors (cryo −90…−180 °C, cold plunge, HBOT 1.3–2.4 ATA, Finnish/IR
  sauna, contrast, IHHT, PBM, PEMF, compression, vibroacoustic, H₂, float, breathwork, IV, Halo). Passes all 11 literature targets (Louis 2020,
  Lund 2003, Laukkanen 2019, AJP-RICU 2025, cold-shock). Session analytics on any trace (simulated or device): HR surge, HRV suppression/rebound,
  recovery constant k, rewarming half-time, TRI, SpO₂ kinetics, cardiac load, PBM dose, deterministic safety tiers. Device ingest endpoint.
- *Therapies* (`therapy.py`): 24 modalities with mechanism, minute-by-minute "inside your body", evidence grade and references; 28 centre machines;
  Vault-driven safety screen (e.g. CAC 38 → cryo caution, AHI 13 → IHHT caution); per-person verdicts (Working / Promising / No reliable signal /
  Possible negative / Too early) using adjusted next-day effects + split-half replication; dose-response; plan builder → doctor sign-off → 4 weeks booked;
  live therapy floor; modality outcomes; Therapy Response Phenotype clustering (research thesis 1); HSAI (Echo OS spec, ±2σ).
- *Tests & scans* (`diagnostics.py`): 75 tests with evidence, price, prep; guideline + risk + gap recommendations; D-grade tests refused.
- *Telomy Rx* (`rx.py`): Telomy Formulas (Wind-Down, Calm, Recover + roadmap), single supplements, Rx medicines, clinic IVs; data-triggered
  (vitamin D dose personalised, statin discussion from CAC + ApoB), duplicate/interaction checks (curated + DDInter 160k pairs, local only — licence
  is non-commercial), doctor edit + sign → e-prescription PDF → test-mode order → "is it working?" tracking.
- *Doctor*: AI summary per patient and per report (grounded composer), all 24 reports reviewable and signable; therapy and Rx queues.
- *New report types* (24 total, 254 markers): thyroid/hormones, iron/minerals, heart & vascular function (ECG/Holter/echo/ABI/PWV/ABPM), spirometry,
  CGM, immunity/allergy/G6PD, urine, FibroScan, cortisol rhythm/organic acids; panel routing by marker majority; 9 new cross-modality rules.
- *Voice Sinc* (`voice.py`): local Whisper (99 languages), any-sentence → actions (meal, drink, smoke, coffee, mood, symptom, activity, therapy start,
  medication, routine, question), English/Hindi/Hinglish, voice-stress features vs own baseline fused with HRV; raw audio never stored.
- *Routine* (`routine.py`): free text → weekly schedule (typo/autocorrect tolerant), quantified (cigarettes/day, alcohol g/week, caffeine timing, water,
  sleep window, protein), evidence-graded flags, profile updates (smoker → PREVENT), daily confirm/deviate logging.
- *Custom activities* (`activities.py`): fast bowling, golf (calm index, pressure response), any user-defined activity; baselines, readiness links,
  acute:chronic workload.
- *Exposome* (`exposome.py`): daily PM2.5/UV from Copernicus CAMS (Open-Meteo) for wherever the person was; within-person effects; Delhi vs Bengaluru
  twin comparison (AQLI, Berkeley Earth, Liang 2014, CGWB water).
- *Digital twin* (`twin.py`): 21-variable hybrid twin (first-order kinetics to lifestyle/drug steady states with literature τ; Hall energy balance;
  statin/ezetimibe/psyllium; ADAG; Heaney vitamin D; BP levers; liver fat; lean mass/BMD; VO₂; HRV/sleep from the person's own effects), personal
  calibration (e.g. vitamin D response 21 % of average), 10-year what-ifs with PREVENT + PhenoAge recomputed, 24-h caffeine/nicotine/BAC twin, and a
  mirror that scores fidelity and flags lab drift the logged life can't explain.

**Bugs found and fixed this iteration**: subjective check-in partial dict crash; HBOT block scheduled during travel (impossible + confounded); confounding
from short events (all kinds now covariates); chance false positive (split-half replication); TRI depends on chamber temperature (added rewarming half-time);
cryo skin-drop and IR-sauna core calibration; MAD = 0 division; routine fuzzy-correction over-reach ("after" → "water"); "12" sleep = noon; two coffee
times in one clause; autocorrected typed text; empty-routine 500 on the day twin; trajectory sampling missed the final year; PM2.5→BP linear overstatement;
Hindi meal analysed from untranslated text. Backend tests: 113 passing.

### Open — next
1. Native dev build for HealthKit/Health Connect and real chest-strap streaming into `/therapy/sessions/{id}/samples`; Telomy patch/band SDK.
2. Wake word + VAD + speaker verification on-device (needs native build); larger Whisper / AI4Bharat for Indic accuracy.
3. Claude-backed understanding and twin narration when an API key is configured; PINN training once ≥ 500 real sessions exist.
4. Licensed drug-interaction source for commercial use; partner pharmacy and lab APIs.
5. iPhone release build with embedded bundle; hosted backend.
