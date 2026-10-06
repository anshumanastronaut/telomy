# Telomy app — build plan (iteration 1)

Inputs: `research/nostavia_teardown.md`, `research/apple_health_teardown.md`, `research/telomy_feature_map.md`, Telomy docs (USPs, App Features, Build-Next, Engineering Guide v3.0, UI Design System v1.0).

## Principles (from the teardowns)
1. **Never fabricate.** Missing data shows as "not available", never 0 or a sample value. Scores re-weight and lower confidence when inputs are missing.
2. **Every number has provenance** (source · date · confidence) and every insight has **Receipts** (data points, window, method, model version).
3. **History is real.** Each report stays its own dated record; trends plot true per-date values; the report's own reference range is kept.
4. **Correct routing.** Each lab panel lands in its own Vault panel; bio-age reports feed the longevity dial.
5. **Clinician in the loop.** Medical-adjacent Sinc output is a draft until signed off.
6. **Quiet design.** UI Design System v1.0: Cloud Dancer / Ink, teal = science, copper = human, 1px charts, no gradients, no XP/coins/badges, no exclamation marks.

## Architecture
- `backend/` FastAPI + SQLite (single file `telomy.db`), Python 3.13.
  - `labparse.py` PDF → markers (cell + row layouts), panel classifier.
  - `engine.py` PhenoAge (Levine 2018) from blood, domain scores with weighted pillars, trends, confidence, completeness, correlation engine (event→signal effect sizes with Welch t, signal↔signal lagged Pearson, cross-panel knowledge rules lab↔genetics↔gut↔toxins↔wearables), N-of-1 analysis.
  - `sinc.py` Sinc companion: Claude (`claude-opus-5-5`) when an API key is present, otherwise a retrieval composer over the evidence store. Always cites evidence, adds clinician-review draft for medical-adjacent questions.
  - `brief.py` Pre-clinic / specialist pack (PDF + FHIR-shaped JSON).
  - `seed.py` 120 days of realistic dummy wearable data with embedded causal effects, events, meals, protocols, clinicians, the 7 dummy lab PDFs ingested through the real parser.
- `mobile/` Expo (SDK 57) + Expo Router, React Native SVG charts, talks to the backend over HTTP.

## Screens (iteration 1)
Tabs: Home · Vault · Sinc · Sessions · Profile, plus the Log sheet.
- **Home** greeting + date, longevity dial, data-card grid, Sinc insight of the day, quick actions, pinned cards, 7-day summary, Vault Rewind.
- **Vault** Timeline (events overlaid) · Biomarkers (6 panels, search, status filters) · Signals (H/D/W/M/6M/Y) · Reports (upload → parse → verify → save) · Imaging.
  - Biomarker detail: per-date history chart with optimal band + lab range, provenance, Sinc read, "what could change this", correlations.
- **Sinc** chat with evidence chips, confidence, clinician-review state, history.
- **Sessions** Protocol (pillars, today's checklist), weekly menu + swap, Breathe timer, N-of-1 studies, Protocol Marketplace.
- **Profile** consent centre (per-purpose, history), Family Vault, clinicians + appointments + pre-clinic brief, specialist pack, Vault completeness, research contribution, Sinc memory, goals, emergency card.
- **Insight detail** Receipts + clinician sign-off thread.
- **Onboarding** name + phone OTP (dev OTP), wearable connect (skippable), per-purpose consent (default off), starter goal, meet Sinc.

## Test plan
1. Backend unit tests: parser (120 markers / 7 reports), PhenoAge, correlation engine finds the seeded effects, N-of-1 verdicts, no-fabrication rules.
2. API smoke tests for every endpoint.
3. iOS Simulator: walk every screen, upload a lab PDF through the app, ask Sinc cross-report questions, generate a pre-clinic brief, toggle consents, run an N-of-1, screenshot each screen.
4. Defect log → next iteration.

## Later iterations
HealthKit / Health Connect live sync (dev build), Telomy Care clinician web, real OTP/auth, FHIR/CDA import, DICOM viewer with real studies, Android build, App Store build, push notifications, encryption at rest, offline cache.
