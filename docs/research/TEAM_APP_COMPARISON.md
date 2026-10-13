# Telomy: two codebases, best of both

Compared on 2026-10-14.
- **Team app:** github.com/mclarenmervin/Telomy (Flutter). Latest commit c53891c, 28 Sep 2026.
- **This app:** github.com/anshumanastronaut/telomy (Expo/React Native + FastAPI + native Swift ECG module).

## At a glance

| | Team app (Flutter) | This app (Expo + FastAPI + Swift) |
|---|---|---|
| Platforms | Android (ring) + iOS shell; phone/tablet layouts | iOS (band, Live Activity); Expo can target Android once the band module is ported |
| Backend | **Supabase**: Auth, Postgres, row-level security on every personal table, `save_/load_normalized_wellness` transactions | FastAPI + SQLite on a Mac; no auth; only 5 of 48 tables carry a user id |
| Offline | Encrypted local fallback (`flutter_secure_storage`) | Band, scores and captures are fully on-phone; Vault needs the server |
| Wearables | Bonlala/"Mini Zone" ring over BLE via the vendor **Android SDK (.aar bundled in the repo)**: HR, SpO₂, HRV, stress, steps, sleep from the ring firmware | KY-E-B1 chest ECG via our **own clean-room protocol**: raw 100 Hz ECG, beat detection, HRV, AF screening (trained model), 4-stage sleep (trained), breathing rate, therapy capture |
| Apple Health / Health Connect | **Yes** (`health` package, explicit consent) | Not yet (planned: native HealthKit module) |
| Scores | readiness-v1: fixed weights (HRV 0.22, RHR 0.18, sleep duration 0.22, consistency 0.12, temperature 0.10, activity 0.08, stress 0.08) on 30-day baselines | Recovery (z-scores vs own baseline, cited), sleep score with 10 contributors, strain (TRIMP), stress, VO₂max |
| Features | dashboard, trends, correlations, readiness, longi-score, biological age, nutrition, workouts, hydration, sleep, body, goals, journal, medications, labs, therapies, consultations, community, marketplace, coach, AI copilot, reports, calculators, ring activity sessions | Vault (220 biomarkers, 21 panels), Sinc (AI over the Vault), risk predictions (PREVENT, PCE, FIB-4, KFRE), longevity age (PhenoAge/GrimAge), digital twin, routine, therapy centre, doctor and centre roles, live ECG, wellness scores, events, captures |
| Quality | `flutter analyze` clean, 15 tests | 120 backend tests, Swift tests, PhysioNet validation of every ECG algorithm |
| Design | Material, light/dark | Telomy Ink: dark-first, Liquid Glass tab bar, Apple HIG rules |

## What to take from each

**From the team app, adopt now:**
1. **Supabase as our production backend** (production plan phase 1).
   - Auth, row-level security per user, managed Postgres and storage. Their 3 migrations are a ready pattern: user-owned tables plus `auth.uid()` policies.
   - Hosting on their Supabase project needs the project ref and an anon/publishable key from the team. Never the service-role key in the app. The FastAPI engine (risk equations, Sinc, reports) can run as a Supabase Edge Function or a small container that talks to the same Postgres.
2. **Apple Health / Health Connect import** with explicit consent: steps, workouts, active energy, sleep, weight, VO₂max.
3. **Encrypted offline cache** for Vault data.
4. Their **feature breadth for daily logging** (hydration, nutrition, workouts, body composition, check-ins). Our flexible events cover part of this.
5. **Phone and tablet responsive layouts** and their widget tests.

**From this app, bring to theirs:**
1. The ECG science: beat detector (Se/+P > 97 % on MIT-BIH), artefact correction, adaptive HR, sleep stages (CV κ 0.51 on 151 nights), AF screening (CinC 2017), ECG-derived breathing. These are Swift today. Ports to Kotlin (Android) can be verified against the same PhysioNet harness (`telomy-lab/validate`).
2. Baseline-relative, cited scores instead of fixed weights.
3. Vault/biomarker depth, risk equations, longevity clocks, doctor and centre roles, therapy capture for research.

## Risks to fix before production
- **Both repositories are public.** They contain product plans and architecture; make them private (owner decision).
- **Vendor SDK in a public repo:** `android/app/libs/Bonlala_ble_v1.4.aar` and `NordicDfuLibrary.aar` are redistributed. Check the vendor licence or move them to a private artifact store.
- Medical-claim wording: both apps say "wellness, not diagnosis". Keep it consistent, especially for AF and sleep stages.

## Proposed merge path
1. One Supabase project (team's) becomes the system of record. Port this app's 48-table schema in phases, starting with profile, measurements, band minutes, captures and events, with RLS on everything.
2. Keep both clients for now. Share the schema and the scoring definitions: one `docs/scoring.md` and one test set, so a recovery score of 62 means the same thing in both apps.
3. Decide the long-term client:
   - Flutter covers Android+iOS from one codebase.
   - Expo also does, and already has the band, Live Activity and design system.
   - Either way, the band and ECG science stay **native** (Swift/Kotlin), behind one shared interface.
