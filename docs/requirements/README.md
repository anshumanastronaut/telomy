# Requirements: sources and traceability

Everything Telomy was built from, and where each requirement lives in the code. Status reflects the v0.4 prototype (2026-10-11):
**Built** · **Partial** · **Not built** · **Business** (not a software requirement).

## 1. Source documents (`source/`)

| Folder | Document | What it defines |
|---|---|---|
| `product/` | [Telomy_Master_DPR_v5.0.pdf](source/product/Telomy_Master_DPR_v5.0.pdf) | Vision, market, Vault data classes, Sinc, clinician-in-the-loop, N-of-1, Halo, Formulas, Care, claims firewall, privacy, roadmap, validation plan |
| | [Telomy_10_App_Features.pdf](source/product/Telomy_10_App_Features.pdf) | First 10 differentiating features |
| | [Telomy_10_Features_To_Build_Next.pdf](source/product/Telomy_10_Features_To_Build_Next.pdf) | Next 10 features |
| | [Telomy_10_Groundbreaking_USPs.pdf](source/product/Telomy_10_Groundbreaking_USPs.pdf) | 10 USPs |
| `engineering/` | [Telomy_Engineering_Guide_v3.0.pdf](source/engineering/Telomy_Engineering_Guide_v3.0.pdf) | Target stack, services, tables, API conventions, security controls, environments, SLOs |
| | [Telomy_Website_Development_Guide.pdf](source/engineering/Telomy_Website_Development_Guide.pdf) | telomy.com (not in this repo) |
| `design-brand/` | [Telomy_UI_Design_System_v1.0.pdf](source/design-brand/Telomy_UI_Design_System_v1.0.pdf) | Tokens, type, icons, motion, components |
| | Brand Identity Brief · Brand Architecture · Brand Story · Telomy Logo | Brand rules and master logo |
| `hardware/` | [Telomy Chest Patch Design Spec v2 (110 mm)](source/hardware/Telomy_Chest_Patch_Design_Spec_v2_110mm.pdf) · [Wristband Design Language & Engineering Spec](source/hardware/TELOMY_Wristband_Design_Language_and_Engineering_Spec.pdf) | Patch and band hardware (data contract in [DEVICE_INTEGRATION](../DEVICE_INTEGRATION.md)) |
| `echo-os/` | Echo OS Master DPR v2 · Disease Prediction DPR · Improved Specification · Software & AI DPR · Hardware DPR · PINN training code (zip) | Earlier iteration of the same goal: HSAI domains, disease prediction, physics-informed models for in-session physiology |

Not copied (kept by the founder): pitch decks, investor one-pager, trademark brief, CAD files (patch `.dxf`/`.step`, band Fusion pack).
They live in `~/Desktop/TELOMY/` on the founder's Mac.

Founder requirements given during the build (conversation, Oct 2026) are recorded as **FR-** rows below and in
[history/DECISIONS.md](../history/DECISIONS.md).

## 2. Traceability matrix

### 10 App Features

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | Live clinician sign-off thread | Built | `review_thread` table, `engine.py`, `app/insight/[id].tsx` |
| 2 | Receipts button | Built | `engine.py` receipts, `ui/insight.tsx` |
| 3 | One-tap N-of-1 launcher | Built | `studies` table, `app/studies.tsx` |
| 4 | In-app DICOM studio | Partial: imaging report findings; no DICOM viewer | `app/imaging.tsx` |
| 5 | Confidence gradient UI | Built | `ui/core.tsx` `ConfBar`, `Prov` |
| 6 | Vault Rewind | Built | `engine.py` `as_of`, Home |
| 7 | Family Vault (scoped, time-boxed, revocable) | Built | `shares`, `access_log`, `app/family.tsx` |
| 8 | Pre-clinic brief generator | Built | `brief.py`, `app/brief.tsx` |
| 9 | Protocol marketplace | Built | `protocols`, `app/marketplace.tsx` |
| 10 | Research contribution dashboard | Built | `app/research.tsx` |

### 10 Features to Build Next

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | Provenance chip on every number | Built | `ui/core.tsx` `Prov` |
| 2 | Confidence gradient, coloured | Built | `ConfBar`, chart zones |
| 3 | Life-event overlay on charts | Built | `ui/charts.tsx` `events`, `app/signal/[id].tsx` |
| 4 | Daily reflection | Built | `memories`, `app/memory.tsx`, used by `sinc.py` |
| 5 | Pending-clinician queue (even without a clinician) | Built | `app/queue.tsx`, doctor Work queue |
| 6 | Open methods button | Built | receipts + `evidence.py` |
| 7 | Specialist pack generator | Built (6 specialties, PDF + FHIR) | `brief.py` |
| 8 | Vault completeness score | Built | `app/completeness.tsx` |
| 9 | Household dashboard | Partial: Family Vault sharing; no combined household view | `app/family.tsx` |
| 10 | Preprint reader | Built (prototype content) | `app/research.tsx` |

### 10 USPs

| # | USP | Status | Where |
|---|---|---|---|
| 1 | Six-stream Vault | Partial: labs, imaging, events, meds, sessions, notes built; native wearable sync pending | Vault modules |
| 2 | Event-tagging as first-class data model | Built | `events`, `engine.effect_table` |
| 3 | Sinc drafts, clinician signs | Built | `sinc.py`, `summaries.py`, Work queue |
| 4 | Structured N-of-1 studies | Built | studies |
| 5 | Telomy Halo adaptive chamber | Not built (hardware); device API ready | `devices.py` |
| 6 | Imaging ingest (MRI, DEXA, CT) | Partial: report parsing built; DICOM pending | `labparse.py`, imaging |
| 7 | Telomy Care clinician layer | Built in app; web dashboard not built | doctor and centre roles |
| 8 | Clinic-network distribution | Business | centre role supports it |
| 9 | DPDP-native per-purpose consent | Partial: consent centre built; enforcement in production plan | `consents`, `app/consent.tsx` |
| 10 | Telomy Labs publication engine | Partial: phenotypes and outcomes built; publishing not | `therapy.phenotypes`, `app/centre-research.tsx` |

### Founder requirements during the build

| ID | Requirement | Status | Where |
|---|---|---|---|
| FR-1 | Therapy and wellness machines: cryo, HBOT, red light, sauna, IV, compression, PEMF, vibroacoustics, molecular hydrogen and more | Built (24 modalities, 28 devices) | `therapy.py` |
| FR-2 | What happens inside the body during cryo (−175 °C), HBOT, red light, sauna | Built | `physio.py`, `app/session/[id].tsx` |
| FR-3 | See my centre, build a therapy plan, know which therapy works | Built | Therapy tab, `therapy-plan.tsx` |
| FR-4 | All scans and reports (gut, CBC, DEXA, BCA, VO₂ max …) | Built (24 report types) | `catalog*`, `testdata/` |
| FR-5 | Doctor-certified supplements, medicines, IVs | Built | `rx.py`, `app/rx.tsx` |
| FR-6 | Doctor sees all reports with AI summary | Built | `summaries.py`, `patient/[id].tsx`, `review/[id].tsx` |
| FR-7 | Models trained on available medicine and prediction databases | Partial: validated equations + DDInter (non-commercial); licensed DB required | `predict.py`, `rx.py` |
| FR-8 | Voice Sinc: multilingual, logs anything, stress from voice | Built (push-to-talk) | `voice.py`, `app/voice.tsx` |
| FR-9 | Always-on wake word, speaker recognition, noise robustness, band mic | Not built (designed) | `voice.DESIGN` |
| FR-10 | Location effects (Delhi vs Bengaluru: air, UV, water) | Built | `exposome.py`, `app/environment.tsx` |
| FR-11 | Athletes: custom activities by voice or manually, longitudinal vitals (bowler, golf calmness) | Built | `activities.py` |
| FR-12 | Routine by talking, typing or manually | Built | `routine.py`, `app/routine.tsx` |
| FR-13 | Digital twin correlated with biomarkers, vitals, supplements, medicines, bone and muscle | Built | `twin.py`, `app/twin.tsx` |
| FR-14 | Machines send temperature, pressure etc. to the server; patch in development | Built (API + simulator + MQTT bridge) | `devices.py`, `backend/tools/` |
| FR-15 | Neko-style 3D body for the twin | Partial (paused) | branch `feat/twin-3d-body` |
| FR-16 | Demo app on iPhone with the Telomy icon; shareable to testers | Built | release build, `docs/DEVELOPMENT.md` |
| FR-17 | Demo and investor video with a human voice | Built (tooling); voice recording pending | `scripts/demo_video/`, [demo/RECORDING.md](../demo/RECORDING.md) |
| FR-18 | Move from the test user to real production users | Planned | [production/PRODUCTION_PLAN.md](../production/PRODUCTION_PLAN.md) |
