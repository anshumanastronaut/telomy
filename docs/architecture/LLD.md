# Telomy: Low-Level Design

**Version:** 1.0 · **Last reviewed:** 2026-10-11 · Generated references: [API](../API.md) (171 operations) · [DATA_MODEL](../DATA_MODEL.md) (48 tables) ·
algorithms and citations: [ENGINE](../ENGINE.md) · devices: [DEVICE_INTEGRATION](../DEVICE_INTEGRATION.md)

This document describes how the code is built today, module by module, and the concrete changes each module needs for production
(marked **→ prod**). Regenerate the API and data-model references with `python scripts/gen_docs.py`.

---

## 1. Repository layout

```
backend/app/        FastAPI app — one module per domain (≈ 9.9 k lines Python)
backend/tests/      pytest: 117 tests against the fixture world
backend/tools/      device_simulator.py, mqtt_bridge.py
mobile/src/app/     expo-router routes (72 screens): (tabs) member · doctor/ · centre/ · stack screens
mobile/src/ui/      design-system components, charts, therapy charts, role tabs
mobile/src/lib/     api.ts (fetch + useApi), role.tsx (role context), theme.ts (tokens)
scripts/            gen_docs.py, demo_video/ (recording, voiceover, composition)
testdata/           generator for 24 fictitious lab PDFs
docs/               this documentation; requirements/source holds the original specs
```

## 2. Backend runtime

- **Framework:** FastAPI 0.142 on Starlette 1.7, uvicorn; Pydantic 2 request models declared next to routes in `main.py`.
- **Startup (`lifespan`):** each module's `init()` creates its tables (`CREATE TABLE IF NOT EXISTS`); an empty DB is seeded with the
  fixture world. **→ prod:** Alembic migrations; no seeding outside local/ci.
- **DB access (`db.py`):** `rows(sql, params)`, `one(sql, params)`, `exec_(sql, params) → lastrowid`, `tx()` context manager,
  `j()`/`unj()` for JSON columns. SQLite. **→ prod:** psycopg 3 pool; same helper signatures; `SET app.user_id` per request
  for RLS.
- **Clock:** `engine.now_iso()` = last signal day + wall-clock time, or `TELOMY_TODAY`. **→ prod:** real UTC; member timezone.
- **Errors:** `HTTPException(status, human message)`; messages are written for end users (the app shows `detail` verbatim).
- **Config (`config.py`, env):** `TELOMY_DB`, `TELOMY_TODAY`, `TELOMY_ADMIN_KEY`, `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`,
  `TELOMY_USE_CLAUDE`. **→ prod:** add `TELOMY_ENV`, `DATABASE_URL`, `REDIS_URL`, `S3_BUCKET`, `JWT_*`, `SMS_*`, `RAZORPAY_*`.

## 3. API surface (171 operations)

Grouped by first path segment (count):

| Group | Ops | Group | Ops | Group | Ops |
|---|---|---|---|---|---|
| therapy | 15 | centre | 13 | rx | 9 |
| doctor | 7 | vault | 6 | routine, reports | 5 each |
| voice, twin, sinc, monthly-reports, meds, insights, activities | 4 each | tests, signals, shares, sessions, predict, meals, events, consults, consents, brief, appointments | 3 each | others (auth, devices, environment, studies, profile, labs …) | 1–2 each |

Conventions: JSON in/out; `GET` lists return arrays; IDs are integers today (**→ prod:** UUIDs for users, orgs, sessions);
device routes authenticate with `X-Device-Key` (SHA-256 stored), key management with `X-Admin-Key`.
**→ prod:** every route declares `Depends(principal)` plus a policy (`member`, `clinician_of`, `centre_staff_of`, `device`);
`x-purpose` header; `Idempotency-Key` on `POST /events`, `/meals`, orders; rate limits.

## 4. Module designs

### 4.1 Vault ingestion: `labparse.py`, `catalog*.py`

- `catalog.py` + `catalog_ext.py` + `catalog_more.py`: 221 markers across 21 panels, each with aliases, unit conversions, sex-specific
  zones (`optimal / in_range / out_of_range`), evidence grade (A–D; D weighted 0.45), concerns, retest rules, prep notes; "absent"
  rule recognises negative/positive/present/trace.
- `labparse.parse(pdf_bytes)`: text extraction (pypdf), two layouts (cell-per-line and inline), alias matching, unit normalisation;
  `vote_panel()` routes a report to the panel holding the majority of its markers (fixes keyword mis-routing).
- Save: `results` rows with value, unit, zone, source document, provenance. **→ prod:** OCR fallback, confidence per row, review queue,
  S3 for originals, `catalog_version` per result.

### 4.2 Engine: `engine.py`, `derived.py`, `predict.py`

- **PhenoAge** from 9 markers (Levine 2018); pace of ageing; domain scores.
- **Event effects (`effect_table`)**: OLS of next-day outcome on event indicators, *all* event kinds as covariates; only kinds with ≥ 5
  events are reported; Benjamini–Hochberg FDR; split-half replication required for "promising".
- **Cross-panel rules** (34): e.g. `masked_htn`, `osa_nondipper`, `arterial_stiffness`, `thyroid_autoimmune`, `folate_hcy`,
  `cgm_a1c`, `liver_fibrosis`, `cortisol_rhythm`, `g6pd` … each → insight draft with receipts.
- **Risk models (`predict.py`)**: PREVENT 2024 (`prevent_coef.json`), PCE, ADA, FIB-4, KFRE; `whatif(levers)` recomputes all.
- `derived.py`: eGFR, FIB-4, ratios, risk matrix, action plan, retest nudges.
- **→ prod:** every function takes `user_id`; nightly per-member job; results cached per member and invalidated on new data.

### 4.3 Sinc: `sinc.py`, `summaries.py`, `evidence.py`, `brief.py`

- `sinc.answer(question)`: Claude (`claude-opus-5-5`, structured output, grounded context from the Vault) when a key is present;
  otherwise the grounded retrieval composer. Citations from `evidence.py`.
- `summaries.report_summary(rid)`, `review_report(rid, …)`, `patient_reports(pid)`, `patient_summary(pid)`: every sentence built
  from stored values ("grounded composer v1"); state = draft until a clinician reviews.
- `brief.py`: pre-clinic brief and specialist packs (PDF via reportlab + FHIR bundle).
- **→ prod:** PHI minimisation before any LLM call; prompt/response logging without identifiers; LLM output never bypasses sign-off.

### 4.4 Therapy: `therapy.py`, `physio.py`, `devices.py`

- `therapy.MODALITIES` (24) and `DEVICES` (28): mechanism, "inside your body", contraindications (`no` / `caution`), references.
- `physio.simulate(modality, params, theta, seed, prior_sessions, day_state, step, dt)`: first-order ODE prior per signal,
  exact step `x += (T − x)(1 − e^(−dt/τ))`, 1 Hz; phases `baseline → active → recovery`. Validated by `validate_prior()` against 11
  literature targets (Louis 2020, Lund 2003, Laukkanen 2019, …).
- `physio.analyse(trace)`: HR surge, HRV suppression and rebound, recovery constant *k*, half-life, skin drop, rewarm half-time, TRI,
  SpO₂ kinetics; `safety()` → tiers.
- `therapy.response(modality)`: next-night outcome effects with split-half replication → verdict
  `helped | promising | possible_negative | no_signal | too_early | in_session_only`.
- Plans: `build_plan(goal, per_week)` → `save_plan` (awaiting doctor) → `decide_plan` (books 4 weeks).
- Sessions: `start_session` (safety screen), `ingest(samples)` (RR → RMSSD server-side), `finish_session`, `live_floor()`.
- `devices.ingest(device_id, key, payload)`: channel limits per modality → alarms; `for_session()` delivered vs prescribed;
  `measured_params()` drives the prior from real telemetry.
- Research: `phenotypes()` (k-means on cold-response features), `hsai()` (6 domains, ±2σ).
- **→ prod:** `org_id` on devices/telemetry; session ownership by `user_id`; Timescale hypertable for telemetry.

### 4.5 Digital twin: `twin.py`

- `STATE` (21 variables) with first-order kinetics to steady states driven by `LEVERS` (statin table, alcohol, smoking, training,
  vitamin D, PM2.5 with GEMM-style flattening, lean mass, BMD rates).
- `calibration()` fits personal response (e.g. vitamin D response 21 % of population; alcohol → HRV −9.2 ms).
- `simulate(preset|levers, years)` → trajectories, recomputes PREVENT and PhenoAge; `day(drinking)` 24-hour twin (caffeine t½ 5 h,
  nicotine t½ 2 h, Widmark alcohol); `mirror()` fidelity backtest and unexplained lab drift.

### 4.6 Life: `routine.py`, `activities.py`, `exposome.py`, `voice.py`

- `routine.parse(text)`: typo/autocorrect repair (`FIX` regexes, difflib against `VOCAB` excluding `COMMON`), clause splitting, kinds
  (wake, sleep, smoke, alcohol, caffeine, water, supplement, commute, work, walk, exercise, meal, screen), times relative to wake-up,
  conditions (`when_drinking` / `not_drinking`), metrics and flags. Personal routines are user data, never fixtures.
- `activities`: templates (fast bowling, golf, running, strength, meditation), `create_type`, `log_session` (vitals from HR/HRV, calm
  index, workload), `detail()` baselines (median/MAD, MAD floor 0.05) and insights.
- `exposome`: `CITIES`, Open-Meteo / CAMS fetch with cache, AQLI (0.98 y per 10 µg/m³ above 5), Berkeley Earth cigarette equivalence.
- `voice`: custom WAV decode, faster-whisper "small" int8, `normalise` (Hindi map), `understand` → intents, `act` logs events/meals/
  activities, acoustic stress (F0, jitter, shimmer, HNR, rate, pauses) fused with HRV. Audio is not stored.

### 4.7 Care and commerce: `roles.py`, `plans.py`, `rx.py`, `diagnostics.py`

- `roles`: doctor today/panel/patient, centre dashboard/members/services, `patient_card` (risk chips). **→ prod:** derived from real
  memberships and care relationships.
- `plans`: plans, subscriptions, monthly reports (`awaiting_doctor` → signed), consults.
- `rx`: `PRODUCTS` (Formulas, supplements, medicines, IVs), `EXCLUDED`, curated rules + DDInter loader → `recommend(goal)` → `submit`
  → `decide` (keep list, dose edits, signature) → `order` → `prescription_pdf` (prescriber + reg. no.). **→ prod:** licensed DB.
- `diagnostics`: 75 tests, `recommend()` (guidelines, risk, gaps), `book()` refuses grade-D tests.

### 4.8 Trained intelligence: `telomy_ml.py`, `llx/*`

- `telomy_ml.py`: mounts an **additive** `APIRouter` (the `/me/*` routes) on the app in `main.py` — it never changes the legacy
  bioage/predict routes. `_ALIAS` maps app catalogue marker codes → engine panel keys (incl. body-composition); `_panel()` builds the
  current user's most-recent-value panel from the Vault (bound by `_bind_user`). All heavy imports are lazy so the app boots without the
  ML extra. Routes: `/me/report` (reconciles the **trained** clock with the app's **clinical** bioage, both labelled), `/me/report/compute`,
  `/me/supplements`, `/me/foodscore`, `/me/modalities`, `/me/checkin`, `/me/health`.
- `llx/` (vendored from `telomy-slm`): deterministic engines that call the trained joblib models (`app/assets/{clocks,muscle,disease}/`)
  as **grounded tools** and compose explanations — `report`, `tools`/`disease_tools`, `fusion` (wearable, personal-baseline),
  `supplements` (+`dsld`, `AWAITING_DOCTOR_VALIDATION` gate), `modalities` (Bonphul, evidence-graded, contraindication screen),
  `casestudy` (n-of-1, ITS + counterfactual), `food_quality`/`nutrition`, `voice_biomarkers`/`personal_agent`/`checkin_engine`,
  `signatures`, `intake`. Models pinned to `scikit-learn==1.9.1`/`scipy==1.18.1`/`joblib==1.6.0`. Full model/metric reference:
  [MODELS.md](../MODELS.md). **→ prod:** the Telomy-LLX SLM narrates these on-device; engines run with or without it.
- **Tenancy note:** per-user DBs are schema-initialised by `accounts._ensure_user_db`; any module that owns a table must be in its init
  list (a drift there left prod DBs without `vitals_ts`/`goals`).

## 5. Data model

48 tables today; full column list in [DATA_MODEL.md](../DATA_MODEL.md). Domain grouping and the production ownership mapping are in
[PRODUCTION_PLAN §3 Phase 1](../production/PRODUCTION_PLAN.md#phase-1--identity-roles-and-tenancy-34-weeks-the-critical-path).
Conventions: `ts` ISO-8601 text; JSON payloads in `data`/`params` columns; soft state machines in `state`/`status` text columns.
**→ prod:** UUID keys for principals, `timestamptz`, `jsonb`, foreign keys, Timescale hypertables for `signals`, `events`, `telemetry`.

## 6. Mobile app

- **Routing (expo-router):** `app/_layout.tsx` registers all stacks; `(tabs)` member tabs Home · Vault · Therapy · Plan · Sinc ·
  Profile; `doctor/` Today · Patients · Work queue · Profile; `centre/` Home · Floor · Members · Bookings · Services · Profile.
  Deep links use the `telomy://` scheme.
- **Data:** `lib/api.ts` `api(path, {method, body, form})` and `useApi(path)` (`data`, `error`, `loading`, `reload`); base URL from
  `EXPO_PUBLIC_API_URL` (baked at build time) or the Metro host. **→ prod:** auth header, refresh, `x-purpose`, retries, offline queue.
- **Role:** `lib/role.tsx` keeps the chosen role in AsyncStorage. **→ prod:** roles from the token's memberships.
- **UI:** `ui/core.tsx` (T, Screen, Card, Row, Chip, StatusChip, Prov, ConfBar, Button, Section, Segmented, Stat, Empty, ErrorState, Toast, ListRow), `ui/charts.tsx` (LineChart with event overlay and table view,
  Dual, sparklines), `ui/therapy.tsx`. Tokens in `lib/theme.ts`; see [DESIGN_SYSTEM](../design/DESIGN_SYSTEM.md).
- **Native modules:** expo-audio (recording), expo-speech, expo-document-picker, expo-print, expo-symbols, expo-gl (3D branch).

## 7. Testing

- `backend/tests/test_backend.py`: 117 tests on the fixture world: parser (24 reports), engine effects vs planted ground truth,
  therapy verdicts, physiology literature targets, devices and patch RR, Rx, diagnostics, summaries, voice, routine, activities,
  exposome, twin. CI: `.github/workflows/ci.yml` runs pytest and `tsc --noEmit`.
- **→ prod:** tenancy tests (two members, one doctor, one centre), RLS test, route-policy enumeration test, migration tests, load test
  for Vault writes, contract tests for the mobile client.
