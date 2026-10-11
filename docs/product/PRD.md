# Telomy: Product Requirements Document

**Version:** 1.0 (derived from the v0.4 prototype) · **Status:** approved for production planning · **Last reviewed:** 2026-10-11
**Sources:** *Telomy Master DPR v5.0*, *10 App Features*, *10 Features to Build Next*, *10 Groundbreaking USPs*, *Echo OS* DPRs and
specification, founder requirements captured during the build (therapy physiology, voice, exposome, athletes, routine, digital twin,
Rx, diagnostics). Originals in [requirements/source](../requirements/source); traceability in [requirements/README.md](../requirements/README.md).

---

## 1. Problem

- Health data is scattered: lab PDFs on phones, wearables in separate apps, imaging on CDs, therapy sessions not recorded at all.
- More than one in four Indian adults has diabetes or prediabetes (ICMR-INDIAB, *Lancet Diabetes & Endocrinology* 2023: 101 M and
  136 M). Most find out late, although earlier signals existed in data they already had.
- Longevity and wellness centres sell cryotherapy, hyperbaric oxygen, red light, sauna, IV drips, compression, PEMF, vibroacoustics
  and molecular hydrogen, but rarely measure what each session does to each person, or whether it works for them.
- Doctors see one report, once a year, without the context of the person's life.

## 2. Vision and positioning

*Where human biology becomes intelligent.* Telomy sells **precision insight, not another device** (DPR §2.1): one Vault for every
source, an evidence-first AI (Sinc) that drafts and a clinician who signs, and an operating system for longevity centres.

## 3. Users and roles

| Role | Who | Primary jobs |
|---|---|---|
| **Member** | Health-conscious adults 28–55 in Indian metros; athletes; centre members | See my biology in one place; know what is working; act on the next best step; log life effortlessly |
| **Doctor** | Registered physicians (NMC), longevity physicians, centre medical directors | Review a prioritised panel; read AI summaries; sign insights, reports, plans and prescriptions |
| **Centre owner / staff** | Longevity, recovery and wellness centres | Run the floor and bookings; see live sessions safely; prove outcomes; grow revenue |

One app binary serves all three roles; a person can hold more than one.

## 4. Goals and non-goals

**Goals (v1.0):** real members onboard and see an honest Vault within 10 minutes; every medical-adjacent output is clinician-signed;
centres measure every session; therapy verdicts and risk predictions are reproducible and explainable.

**Non-goals (v1.0):** diagnosing disease; autonomous prescribing; selling unproven tests; replacing a doctor; storing raw voice audio;
our own wearable hardware (the Telomy Band/Halo are roadmap; the patch is in development).

## 5. Functional requirements

Priority: **P0** = required for v1.0 pilot, **P1** = v1.x, **P2** = later. Status = state of the v0.4 prototype.

### 5.1 Vault and ingestion

| ID | Requirement | Pri | v0.4 |
|---|---|---|---|
| VLT-1 | Ingest lab/imaging PDFs into coded markers with units, ranges, sex-specific zones and provenance | P0 | Built (24 report types, 221 markers) |
| VLT-2 | Wearable streams (Apple Health, Health Connect, Oura, Whoop, Garmin, CGM) with source on every sample | P0 | Simulated; native sync not built |
| VLT-3 | Event-first model: meals, drinks, cigarettes, workouts, illness, stress, medications, supplements, therapies, travel | P0 | Built |
| VLT-4 | Medications and supplements log with dose, timing, start/stop, adherence | P0 | Built |
| VLT-5 | Imaging: radiology report findings; DICOM viewer | P1 | Report findings built; DICOM viewer not built |
| VLT-6 | Vault Rewind: view Home as of any past date | P1 | Built |
| VLT-7 | Vault completeness score | P1 | Built |
| VLT-8 | Provenance chip and confidence on every number | P0 | Built |

### 5.2 Engine and Sinc

| ID | Requirement | Pri | v0.4 |
|---|---|---|---|
| ENG-1 | Biological age (PhenoAge), pace of ageing, domain scores | P0 | Built |
| ENG-2 | Adjusted next-day event effects with false-discovery control and replication; minimum-data thresholds | P0 | Built |
| ENG-3 | Cross-modality rules across panels (e.g. plaque + ApoB, liver fat on imaging + blood) | P0 | Built (34 rules) |
| ENG-4 | Validated risk models with what-if levers: AHA PREVENT 2024, PCE, ADA, FIB-4, KFRE | P0 | Built |
| ENG-5 | Sinc chat with citations; Claude when a key is configured, grounded composer otherwise | P0 | Built |
| ENG-6 | Receipts on every insight: data, method, confidence, model version | P0 | Built |
| ENG-7 | Structured N-of-1 studies (ABAB, washout, pre-registered primary marker) | P1 | Built |
| ENG-8 | AI summary per report and per patient, grounded to values | P0 | Built |
| ENG-9 | Daily reflection / memories referenced by Sinc | P1 | Built |

### 5.3 Therapies and centres

| ID | Requirement | Pri | v0.4 |
|---|---|---|---|
| THR-1 | Catalogue of 24 modalities with mechanism, "inside your body", contraindications, references | P0 | Built |
| THR-2 | Safety screen against the member's Vault before booking | P0 | Built |
| THR-3 | In-session physiology (HR, HRV, skin/core temperature, SpO₂) and session analytics (HR surge, HRV rebound, recovery constant *k*, rewarming, safety tiers) | P0 | Built on validated priors; live data via device API |
| THR-4 | Per-member verdicts: helped / promising / possible negative / no signal / too early | P0 | Built |
| THR-5 | Therapy plan builder for a goal, doctor-signed before booking | P0 | Built |
| THR-6 | Live therapy floor: who is in which machine, vitals, alerts, device status | P0 | Built (simulated vitals until machines stream) |
| THR-7 | Machine and patch telemetry ingestion with per-device keys and channel limits | P0 | Built |
| THR-8 | Response phenotypes and outcomes across members (research) | P1 | Built |
| THR-9 | Health-span adaptability index (HSAI) | P1 | Built |

### 5.4 Care, commerce and life

| ID | Requirement | Pri | v0.4 |
|---|---|---|---|
| CAR-1 | Doctor panel ranked by validated risk; patient page with AI summary and all reports | P0 | Built |
| CAR-2 | Work queue: insights, monthly reports, consults, therapy plans, Rx | P0 | Built |
| CAR-3 | Live clinician sign-off thread visible to the member | P0 | Built |
| CAR-4 | Monthly reports (AI on Essential, doctor-signed on Plus/Pro); consults; pre-clinic brief | P0 | Built |
| CAR-5 | Specialist packs (PDF + FHIR) | P1 | Built |
| RX-1 | Data-triggered supplements, medicines, IVs, Telomy Formulas; interaction checks; doctor edits and signs; e-prescription PDF | P0 | Built (DDInter must be replaced, see production plan) |
| DX-1 | Tests & scans recommendations (guidelines, follow-ups, gaps); refuse tests without evidence | P0 | Built (75 tests) |
| LIFE-1 | Routine described by text or voice → schedule, metrics, daily confirmation | P1 | Built |
| LIFE-2 | Custom activities (e.g. fast bowling, golf) with personal baselines and longitudinal vitals | P1 | Built |
| LIFE-3 | Exposome: city air (PM2.5), UV and water effects; city comparison | P1 | Built |
| VOX-1 | Voice: multilingual (99 languages incl. Hindi/Hinglish), logs anything, voice-stress features, audio never stored | P1 | Built (push-to-talk) |
| VOX-2 | Always-on wake word, speaker verification, band microphone | P2 | Designed, not built |
| TWN-1 | Digital twin: 21-variable state calibrated to the person, 10-year what-ifs, 24-hour twin, mirror fidelity | P1 | Built |
| TWN-2 | 3D body visualisation of the twin | P2 | Prototype on branch `feat/twin-3d-body` |
| SHR-1 | Family Vault: scoped, time-boxed, revocable sharing with access log | P1 | Built |
| CNS-1 | Consent centre per purpose with history | P0 | Built (enforcement in production plan) |
| PAY-1 | Plans: Free, Essential ₹499, Plus ₹1,499, Pro ₹3,999 /month; centre plans ₹14,999–39,999 /month | P0 | Built (test-mode payments) |

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| Privacy | DPDP Act 2023: per-purpose consent, data residency in India, DSR self-service, DPO, breach notice |
| Security | OTP + JWT; clinician TOTP; RLS; encryption at rest (KMS) and in transit (TLS 1.2+); audit log of third-party reads |
| Clinical safety | Drafts until a registered clinician signs; deterministic contraindication and alarm rules; claims firewall |
| Honesty | "No reliable signal" and "too early" are valid outputs; simulated data is always labelled |
| Performance | API availability 99.9 %; Vault write p99 < 150 ms; Sinc first token p95 < 900 ms (Engineering Guide v3 §10.4) |
| Accessibility | Dynamic type up to 2×; contrast AA in light and dark; every chart has a table view |
| Localisation | English first; Hindi and Hinglish voice; INR pricing; Indian labs and units |
| Quality | Every PR runs backend tests and the TypeScript check; no merge on red |

## 7. Success metrics

Pilot (DPR §20): 50 members, 3–5 clinics, 12 weeks. Primary: 12-week retention and rated usefulness. Secondary: events logged per
week, insight opens, clinician-review rate and time-to-sign, share of centre sessions with measured (not simulated) data.

## 8. Release plan

| Release | Scope |
|---|---|
| v0.4 (done) | Feature-complete prototype on fictitious data; iOS release build for testers |
| v0.5 | Production Phases 0–1 (hardening, identity and tenancy) |
| v0.6 | Phases 2–3 (real data in, AWS Mumbai infrastructure) |
| v1.0 pilot | Phase 4 compliance gates passed; 50-member, 3–5 clinic pilot |
| v1.x | Wake word and speaker verification, DICOM viewer, 3D twin, partner-lab APIs, Telomy Band |

## 9. Risks

Regulatory classification (SaMD), data breach, over-claiming, sparse real data making insights rare, centre adoption, model drift.
Mitigations: [PRODUCTION_PLAN](../production/PRODUCTION_PLAN.md) Phase 4, [CLINICAL_SAFETY](../CLINICAL_SAFETY.md), DPR §18.
