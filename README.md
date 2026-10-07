# Telomy

**Where human biology becomes intelligent.** Telomy is a longevity-intelligence platform: one Vault for labs, imaging, wearables,
clinic-machine sessions, medicines and life events; **Sinc**, an evidence-first AI companion; a clinician in the loop; and
**Telomy Care** for doctors and longevity / wellness centres.

> ⚠️ Private, pre-release. All people, reports and sessions in this repository are **fictitious TEST DATA**.
> Never commit real health data, credentials or API keys (see [docs/SECURITY_PRIVACY.md](docs/SECURITY_PRIVACY.md)).

| | |
|---|---|
| **Backend** | Python 3.13 · FastAPI · SQLite (dev) · numpy · local Whisper (optional) — 171 API operations, 45 tables, 115 tests |
| **Mobile** | Expo SDK 57 · React Native 0.86 · expo-router — one app, three roles (member · doctor · centre owner) |
| **Status** | v0.4 — feature-complete prototype running on the iOS Simulator; next: native build, device SDKs, hosting ([roadmap](docs/ROADMAP.md)) |

## What it does

- **Vault** — 24 report types (blood, gut, genetics, epigenetic age, metals, toxins, advanced cardio-renal-neuro, CPET/VO₂max, DEXA/BCA, cardiac CT,
  MRI, sleep study, proteomic organ age, thyroid/hormones, micronutrients, ECG/echo/ABI/PWV/ABPM, spirometry, CGM, immunity/allergy, urine,
  FibroScan, cortisol/organic acids) parsed from PDF into 221 coded markers with sex-specific zones.
- **Engine** — PhenoAge, domain scores, adjusted next-day event effects (OLS + Benjamini–Hochberg + split-half replication), lagged correlations,
  34 cross-modality rules, validated risk models (AHA PREVENT 2024, PCE, ADA, FIB-4, KFRE) with what-ifs.
- **Therapies inside the machine** — physiology priors calibrated to the literature for cryo, HBOT, sauna, cold plunge, red light, PEMF and 18 more;
  session analytics (HR surge, HRV rebound, recovery constant *k*, rewarming, SpO₂ kinetics, safety tiers); machine telemetry and patch ingestion;
  per-person "what's working" verdicts; plan builder with doctor sign-off; live therapy floor; response phenotypes; HSAI.
- **Digital twin** — a 21-variable hybrid twin calibrated to the person: 10-year what-ifs (PREVENT, PhenoAge, lipids, HbA1c, BP, bone, muscle…),
  a 24-hour twin (caffeine, nicotine, alcohol) and a mirror that scores its own fidelity.
- **Sinc** — chat with citations (Claude when `ANTHROPIC_API_KEY` is set), voice in 99 languages with action logging and voice-stress features,
  routines described in plain language, custom activities (fast bowling, golf, anything), exposome (air, UV, water by city).
- **Care** — doctor work queue (Sinc drafts, monthly reports, consults, therapy and Rx plans), AI summaries for every report and patient,
  Telomy Rx (Formulas, supplements, medicines, IVs) with interaction checks and e-prescription, centre dashboard, bookings, devices, research.

## Quick start (macOS)

```bash
git clone https://github.com/anshumanastronaut/telomy.git && cd telomy
make setup          # Python venv + backend deps + mobile npm install, creates backend/.env from the example
make seed           # builds the fictitious test Vault (≈30 s)
make api            # FastAPI on http://127.0.0.1:8787  (docs at /docs)
make mobile         # Expo dev server → press i for the iOS Simulator
make test           # backend tests + TypeScript check
```

Optional: `make voice` installs local Whisper for Sinc voice. Add your Anthropic key to `backend/.env` to switch Sinc to Claude.
Full guide: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Repository map

```
backend/            FastAPI app (app/), tests/, tools/ (device simulator, MQTT bridge), requirements*.txt, .env.example
mobile/             Expo app — src/app (routes), src/ui (components), src/lib (api, theme, role)
docs/               Architecture, development, engine & science, device integration, security & privacy, clinical safety, API, data model, roadmap
testdata/           Generator for the 24 fictitious lab-report PDFs
research/           Competitor teardowns (structure only — no personal data)
brand/              Logo and splash sources
qa/                 Simulator screen-walk scripts
scripts/            Docs generator, setup helpers
```

## Documentation

| Doc | For |
|---|---|
| [ARCHITECTURE](docs/ARCHITECTURE.md) | How the pieces fit; request flow; module map |
| [DEVELOPMENT](docs/DEVELOPMENT.md) | Setup, running, seeding, debugging, Simulator & device builds |
| [ENGINE](docs/ENGINE.md) | Every algorithm, model and its references |
| [DEVICE_INTEGRATION](docs/DEVICE_INTEGRATION.md) | Machines, Telomy patch, wearables → server contract |
| [SECURITY_PRIVACY](docs/SECURITY_PRIVACY.md) | DPDP, secrets, test-data rules |
| [CLINICAL_SAFETY](docs/CLINICAL_SAFETY.md) | Claims firewall, clinician-in-the-loop, safety envelope |
| [API](docs/API.md) · [DATA_MODEL](docs/DATA_MODEL.md) | Generated references |
| [ROADMAP](docs/ROADMAP.md) · [CHANGELOG](CHANGELOG.md) | What's next, what changed |
| [CONTRIBUTING](CONTRIBUTING.md) | Branches, reviews, commits, definition of done |

## Licence

Proprietary — © 2026 Telomy. All rights reserved. See [LICENSE](LICENSE).
