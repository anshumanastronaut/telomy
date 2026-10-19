# Telomy — open work from the build thread (kept current; nothing is dropped, only moved to Done)

Legend: [ ] open · [~] in progress · [x] done (date) · [u] needs the user (account, purchase, signature, wearing a device)

## Capture & devices
- [x] 2026-10-19 Ring timestamps (local→UTC), store de-dupe, sleep-record decode, resync after wake
- [x] 2026-10-19 Patch continuous recording (rolling 2 h, sleep hand-over, 14-day retention)
- [u] Wear the patch overnight to confirm continuous recording end to end
- [x] 2026-10-19 WHOOP 4.0 via NOOP push receiver (12/12 streams)
- [x] 2026-10-19 CGM receiver (Nightscout-compatible); [u] buy Libre 2 Plus/3 Plus + install Juggluco on the Samsung
- [ ] Device purchase advice follow-up once the user picks (Galaxy Watch 8 / Apple Watch 11 / WHOOP 5 / ring)

## Sleep
- [x] Fusion priority + fragment merge + uncovered tails; WHOOP nights staged by the Telomy motion+HR stager
- [x] Architecture norms (HMC) + uncertain-minute flag; sleep need (0.55 recurrence)
- [ ] Re-run the Telomy-vs-WHOOP night comparison on a fully-captured patch night
- [ ] Better REM/deep staging: train on DREAMT/MESA once access is granted ([u] PhysioNet DUA, NSRR request)

## ML / algorithms / physics models
- [x] Motion+HR stager (LOSO κ 0.47), effect engine calibration on the 100-person cohort, Banister + Borbély
- [ ] Activity / workout / sport / therapy recogniser (PAMAP2, WISDM, Capture-24) → WHOOP + phone motion
- [ ] Biological-age refit and lab-projection priors from NHANES
- [ ] Rhythm model from PTB-XL for the patch
- [x] Daily cohort sim bot (04:30) and data-health bot (3 h) running
- [ ] MiroFish-style 5 000-agent USP/niche simulation ([u] free provider keys in OmniRoute)

## Twin & labs
- [x] 2026-10-19 Routine-panel insight rules (CBC/LFT/KFT) — real report now yields 5 insights (was 0)
- [u] Ultrahuman Blood Vision holds the Telomy DEMO report (hs-CRP 3.4, LDL 148 …), not the real one — its "blood age 33"
      is computed on synthetic values. User to replace it with the real report there (or delete it) — not done by Claude.
- [ ] Blood age: keep PhenoAge (Levine 2018, NHANES-validated) as the headline; add a separate, clearly-labelled
      "metabolic age" view using lipids/insulin/HbA1c/vitamin D only after it is validated on NHANES mortality
      (Ultrahuman's 12-contributor model reads 33 vs PhenoAge 28.2 on the same demo values)
- [x] Real report parsed (52/52), twin projections every 10 days from real anchors, labelled "projected"
- [ ] Score projections when the next real report arrives ([u] next blood test)

## Nutrition, supplements, medicines (closed loop)
- [x] Targets (Mifflin × measured PAL, protein, fibre, ICMR-NIN carb cap, WHO limits) + lab notes
- [x] 2026-10-19 USDA FoodData Central SR Legacy (7 793 foods, micronutrients) behind the meal analyser
- [ ] (next) Daily intake signals from logged meals (kcal, protein, fibre, added sugar, late meals) → effect engine
- [ ] Adherence vs targets + plan proposals (accept / drop) + 14-day review → recalibrate
- [ ] Open Food Facts barcode lookup (ODbL attribution)
- [ ] NIH DSLD supplement products + openFDA/DailyMed labels; interaction checks via rx.py
- [ ] Weekly nutrition-loop bot
- [ ] Indian dish coverage beyond the curated 40 (INDB licence unclear — ask the Jaacks lab, or compose recipes from USDA ingredients)

## Sinc & the SLM
- [x] 2026-10-19 On-device Sinc (Qwen3-1.7B via Cactus) with grounded facts + number guard; server fallback
- [x] 2026-10-19 Talk-to-track: any statement → tracker (pain, symptom, supplement, medicine, habit, measure, custom),
      baseline, plan, red-flag safety, drivers analysis; Trackers screens
- [ ] Download + try the on-device model on the iPhone (1.1 GB, Wi-Fi) and measure speed / guard pass rate
- [ ] Evening check-in notification for today's trackers
- [ ] Fine-tune a Telomy SLM (LoRA on Qwen3-1.7B) from grounded Q&A generated on the cohort — after the guard data shows where the base model fails
- [x] 2026-10-19 Voice screen → trackers (voice.command calls trackers.capture)

## App quality
- [~] End-to-end audit (tools/audit.py): wiring 177/177 app calls have routes; 104 GET routes, 0 server errors.
      Fixed: insights empty on real data, WHOOP strain never stored as a signal. Open: /whoop/status 5 s (cache it);
      per-screen check on the phone of every feature with real data
- [ ] Full UI design pass; slow tab switching (Twin WebView)

## Hygiene
- [x] Personal values redacted from code/docs; commit 246780e message still has sleep times (user informed, not rewritten)
