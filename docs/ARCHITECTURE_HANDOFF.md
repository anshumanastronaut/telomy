# Telomy — Architecture & Handoff

**Purpose:** explain this app's design so your team can take it forward from this git repo. It covers the system
layers, every engine and how it computes, the **device-agnostic integration layer** (built for not-yet-finalised
hardware and multiple devices), the AI stack, multi-user, and how it maps onto the `healthagent` + Supabase backend.

**Repo:** `anshumanastronaut/telomy`, branch `telomy/twin3d-sinc-design-ring`.
**Stacks:** mobile = React Native (Expo) + native Swift modules; backend = Python **FastAPI** + SQLite (today) →
Supabase (target). Deeper engine detail is in `docs/ENGINEERING_DPR.md`; biological-age validation in
`docs/research/BIOAGE_RESEARCH.md`.

---

## 1. The idea in one paragraph

Telomy turns a person's labs, genetics, imaging, wearables and logged life events into one longitudinal record, runs
published medical/physiology models on it (biological age, disease risk, sleep, training load, nutrition, correlations),
and explains it through a grounded AI companion ("Sinc") that never invents a number. Everything is evidence-graded and
cited; synthetic data is always labelled and kept out of the real record.

---

## 2. System layers

```
┌──────────────────────────── Mobile app (RN/Expo + native Swift) ───────────────────────────┐
│  Screens: Today (customisable home), Twin (3D), Sinc (AI), Vault, Biological age, Trackers  │
│  On-device: sleep fusion + scores (lib/sleepfuse, wellness-core), on-device SLM (Cactus),   │
│             native device adapters (patch ECG, ring BLE, HealthKit), continuous vital store │
└───────────────┬──────────────────────────────────────────────┬──────────────────────────────┘
                │ HTTPS (daily summaries, Vault, AI, vitals)     │ BLE / HealthKit / device push
                ▼                                                ▼
┌──────────────────────────────── Backend (FastAPI) ─────────────────────────────────────────┐
│  Engine: biological age · disease risk · effect/correlation engine · sleep · dynamics (PINN)│
│          · nutrition · CGM analytics · twin projections                                     │
│  AI: retrieval (RAG) → model wrapper (provider-agnostic) → number-grounding guard → composer │
│  Extensible: science registry (new findings as data) · cellular-effects KB                  │
│  Device receivers: WHOOP push · CGM (Nightscout) · phone daily · unified /vitals ingest      │
│  Data: SQLite (per-user) today → Supabase/Postgres+RLS (target)                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

Two clean layers: a **data + auth layer** (today SQLite-per-user; target your Supabase) and an **intelligence layer**
(the FastAPI engine). They are separable on purpose — see §8 (integration).

---

## 3. Device integration layer — built for flexible, multi-device hardware

**This is the part designed for your not-yet-final hardware.** The engine never depends on a specific device; it
consumes **normalised signals** and a **source-agnostic vitals timeline**. Any device plugs in by producing those.

### 3.1 Two ingestion shapes
1. **Daily summaries** → `POST /signals/daily`: one value per day × metric (e.g. `hrv`, `rhr`, `sleep_hours`,
   `deep_sleep`, `spo2`, `steps`, `vo2max`, `glucose_mean`), each tagged with its `source`. This is what feeds the
   engine (biological age, correlations, twin).
2. **High-frequency longitudinal vitals** → `POST /vitals/ingest`: batches of `{ts, metric, value, source, step_s}`.
   One tall table (`vitals_ts`), idempotent upsert, downsampled reads. `step_s` encodes the cadence — **adaptive**:
   ~5–10 s at rest, 1 Hz for a live view, continuous 1 Hz during a therapy/workout. `/vitals/day` puts every source on
   one clock with events overlaid so any window correlates.

### 3.2 How each current device maps (and how a new one would)
| Device | How it captures | How it reaches the record |
|---|---|---|
| **ECG patch** (KY) | native Swift (`KYBand.swift`): continuous 10 s vital summary (HR, HRV, motion, quality) while worn + full ECG on tap / overnight / therapy | native store → `lib/vitalsync` → `/vitals/ingest`; nights → `sleepfuse` → `/signals/daily` |
| **Ring** (TK3040) | native Swift (`KYRing.swift`): 5-min HR/SpO₂/temp log + sleep records over BLE | same sync path (5-min cadence) |
| **WHOOP 4.0** | the NOOP app pushes ~1 Hz streams (RR, HR, motion, SpO₂, temp) to the server | `POST /whoop/push` (server-side), staged by our motion+HR model |
| **CGM** (Libre/Dexcom) | an open reader (Juggluco/xDrip) uploads to a Nightscout URL | `POST /nightscout/...` → `glucose_mean` daily + CGM analytics |
| **Apple Health / Watch** | HealthKit | `lib/health` → `/signals/daily` |

**Adding a NEW device is a small, well-scoped job — no engine changes:**
1. A native BLE (or SDK) adapter that decodes the device and emits either daily summaries or `{ts, metric, value}`
   samples (and, for sleep, a staged or asleep/awake hypnogram).
2. Point it at the same two endpoints. That's it — the engine, scores, timeline and AI immediately use it.

### 3.3 Multi-device fusion (already built)
When several devices cover the same night/day, `lib/sleepfuse.ts` fuses them by a **configurable source priority**
(patch ECG > Apple Watch stages > ring firmware > ring HR estimate > other Health; WHOOP staged by our model), merges
fragments (<90 min gaps), keeps uncovered tails, and never fails when a device is missing — each metric/clock that
lacks its input shows "connect X" instead of a number. A new device simply slots into the priority ladder. Device
quirks (ring timezone, WHOOP's re-delivered R-R) are handled per-device so the engine sees clean, normalised signals.

**Design principle:** the hardware is a pluggable source; the intelligence is fixed. You can swap or add rings,
patches, watches or CGMs without touching the engine.

---

## 4. The engines (what they compute)

All are published methods, cited, with confidence; medical-adjacent outputs route to a clinician review flow.

- **Biological age** (`bioage.py`, validated on NHANES 2017-18): PhenoAge (Levine 2018, r=0.92 vs age), KDM
  (Klemera-Doubal, r=0.98, fitted on NHANES), homeostatic dysregulation (Cohen 2013), plus **fitness, muscle, heart
  (vascular), and organ (liver/brain/kidney)** ages. Endpoint `GET /bioage`.
- **Disease risk** (`predict.py`): AHA PREVENT 2024, Pooled Cohort Equations, diabetes, FIB-4 (liver), KFRE (kidney) —
  each computed only from the inputs present; missing inputs are named, not imputed.
- **Correlation / effect engine** (`engine.py`): OLS of each outcome (HRV, RHR, deep sleep…) on the prior day's logged
  events + weekend + trend, Benjamini–Hochberg FDR control. Calibrated on a planted-truth cohort (95% CI coverage,
  1.2% FPR). Trackers get the same via Spearman + BH.
- **Sleep** (`sleepfuse.ts`, `stager_motion.py`): per-source staging, fusion, sleep need (WHOOP-style debt recurrence,
  one night per calendar day), recovery (robust personal baselines), illness watch.
- **Dynamics (physics-informed)** (`dynamics.py`): Banister load→HRV, Borbély two-process sleep pressure.
- **Nutrition** (`nutrition.py`): Mifflin-St Jeor × measured PAL, protein/fibre/WHO limits, lab-aware; meal analysis
  over a curated Indian table + USDA FoodData Central.
- **CGM** (`cgm.py`): International Consensus TIR metrics.
- **Twin** (`twin.py`): runs the person's routine through the physiology to project risk and labelled lab projections.

---

## 5. The AI stack (Sinc)

A grounded companion, not a chatbot. Pipeline: **retrieval (RAG) → model wrapper → number-grounding guard → composer**.
- **Retrieval** (`retrieval.py`): every data source becomes a small "card" (~300+); BM25 returns the cards relevant to
  the question; `connect()` builds cross-domain threads (labs↔wearables↔genetics↔food).
- **Model wrapper** (`telomy_llm.py`): provider-agnostic — Anthropic, or any OpenAI-compatible endpoint, or a local SLM
  on the phone (Cactus, int4). Cache + timeout.
- **Guard:** every number in the answer must appear in the grounding context, else the answer is rejected and the
  deterministic composer answers from the Vault directly. This is the safety core.
- **Talk-to-track** (`trackers.py`): any statement ("my knee hurts 5/10", "started magnesium") becomes a tracker with a
  baseline, plan, red-flag safety routing, and a drivers analysis.

> Your `healthagent/app/agent` (context_loader + graph + guardrails + llm + narration) is the same pattern — this maps
> onto it almost one-to-one.

---

## 6. Extensibility — new science without redeploying

`science.py` + `GET/POST /science`: a new paper or guideline is added as a **row**, not code — a declarative
cross-panel rule, a marker-range override, or a cellular mechanism — each cited and evidence-graded, reversible. The
engine merges active findings into insights, the AI's grounding, and the age/range calculations on the next request.
`cellular.py` is the evidence-graded map of supplement/med/food/stress → cell → pathway → marker.

---

## 7. Multi-user

Today: per-user SQLite file selected by a context variable + token auth (`accounts.py`, `db.py`) — physical file-per-
user isolation. **This is a stopgap.** Your **Supabase Auth + Row-Level Security is the real multi-user layer** and the
target (see §8).

---

## 8. Integration with your `healthagent` + Supabase backend

Your `AGENTS.md` states the contract: *"the two sides integrate exclusively through Supabase tables."* We agree. The
clean convergence:

1. **Data + auth → your Supabase.** Postgres + RLS + Auth becomes the single system of record and multi-user layer.
   Our RN app reads/writes the same Supabase tables (the "separate mobile team integrates via Supabase" role your doc
   describes). Our per-user SQLite retires.
2. **Intelligence → merge our engine into `healthagent`.** Same FastAPI stack. Our modules (`bioage`, `retrieval`,
   `engine`/effect, `trackers`, `sleepfuse` server pieces, `cellular`, `science`, `predict`, `nutrition`) move into
   `healthagent/app/analytics` + `app/agent`, with the data layer reading `app/common/supabase_client.py` instead of
   our SQLite `db.py`. Our engine is more developed than `analytics/event_analysis.py`; it slots in as the analytics
   core.
3. **Devices → the same ingest contract**, writing to Supabase tables (daily signals + a `vitals_ts` table) via your
   gateway/webhooks. WHOOP/CGM receivers become gateway webhooks.

**The main integration work** is schema mapping: your `wellness_documents` (JSONB) + `normalized_wellness` +
`activity_sessions` vs our relational model (reports, results, signals, events, trackers, insights, vitals_ts). Either
expand the Supabase schema to hold these (recommended — the engine needs queryable rows, e.g. per-marker lab history,
daily signals, high-frequency vitals) or add an adapter that reads/writes the JSONB.

**What we need from you to build it:** Supabase project URL + anon key (app) and a service-role key or RLS policies
(engine), and the current table schema. With those we can ship a Supabase data-layer adapter and prove one engine
(e.g. `/bioage`) end-to-end before the full merge.

---

## 9. Build, validate, run

- Backend: `backend/`, FastAPI, `pytest` (168 tests). `tools/audit.py` checks every app→route wiring and sweeps every
  GET endpoint.
- Mobile: `mobile/`, Expo; native modules under `mobile/modules/ky-ecg`.
- Biological age is validated on real NHANES (reproduce with `backend/tools/bioage_study.py`).
- Nothing is faked: synthetic data carries `is_test_data`, is labelled in the UI, and the real record is always
  preferred.

---

## 10. TL;DR for your team

- Same backend framework (FastAPI) and the same AI pattern (RAG + guard + composer) you already have — easy to merge.
- A **device-agnostic ingestion contract** (daily signals + a high-frequency vitals timeline) means **new/undecided
  hardware plugs in with a small native adapter and zero engine changes** — multi-device fusion is already built.
- Converge on **Supabase as the data/auth bus** (your design) and fold our **engine** into `healthagent/app/analytics`.
- Ask us for a Supabase reader invite + schema; we'll deliver a data-layer adapter and a working `/bioage` on your
  stack as the first proof.
