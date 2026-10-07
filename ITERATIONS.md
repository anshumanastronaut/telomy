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
