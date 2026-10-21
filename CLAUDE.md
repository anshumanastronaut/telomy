# CLAUDE.md: working on Telomy

Context for Claude Code (and any new engineer). Read this first, then `docs/README.md`.

## What this is

Telomy is a longevity-intelligence platform: one Vault for labs, imaging, wearables, therapy sessions, medicines and life events;
Sinc, an evidence-first AI that drafts while a clinician signs; and tools for doctors and longevity centres. One Expo app serves three
roles (member, doctor, centre owner) against a FastAPI backend. **Status: v0.4 prototype; founder is the first n-of-1 test subject on
real data (private, on an always-on cloud); next is production** (see `docs/production/PRODUCTION_PLAN.md`).

Two layers sit on the Vault: the **guideline path** (PhenoAge bioage, pace-of-ageing — see `docs/ENGINE.md`) and the **trained-model
intelligence layer** (`backend/app/telomy_ml.py` + `backend/app/llx/`): NHANES-trained blood/muscle age clocks, a 13-condition disease
screen, 10-yr mortality, wearable fusion, and the supplement / modality / nutrition / voice / check-in engines, served additively at
`/me/*`. **Read [`docs/MODELS.md`](docs/MODELS.md) before touching anything under `telomy_ml.py` or `llx/`.** Every number is a grounded
tool result — engines (and the Telomy-LLX SLM) narrate, they never invent a value.

## Commands

```bash
make setup   # venv + backend deps + mobile npm install; creates backend/.env from .env.example
make seed    # build the fictitious fixture world (~30 s)
make api     # FastAPI on :8787 (docs at /docs)
make mobile  # Expo dev server → i for iOS Simulator
make test    # backend pytest (117) + mobile tsc
make docs    # regenerate docs/API.md and docs/DATA_MODEL.md after route/schema changes
```

## Rules (non-negotiable)

- **Never commit real health data, personal data, credentials or keys.** All people and reports in the repo are fictitious.
  `backend/.env`, `*.db`, `share/`, `backend/data/ddinter/`, `research/ultrahuman/shots` are git-ignored; keep it that way.
- **Clinician in the loop:** medical-adjacent outputs (insights, report summaries, monthly reports, therapy plans, Rx) stay drafts until
  a clinician signs. Don't add a path that bypasses sign-off.
- **Deterministic safety:** contraindications, drug interactions and device alarms are rules with tests, never LLM output.
- **Honesty:** return `too_early` / `no_signal` rather than invent; label simulated data as simulated; no outcome claims in copy.
- **DDInter is non-commercial**; it must not ship in a paid product.
- Payments stay in test mode; don't accept terms or consents on anyone's behalf.

## Code conventions

- Backend: one module per domain in `backend/app/`; routes and Pydantic models in `main.py`; DB via `db.rows/one/exec_/tx`;
  use `engine.now_iso()` for "now", never `datetime.now()` directly; human-readable `HTTPException` messages (the app shows them).
- Every behaviour change gets a test in `backend/tests/test_backend.py`; tests run against the fixture world with planted effects.
- Mobile: expo-router screens in `mobile/src/app`; components from `mobile/src/ui/core.tsx`; colours and fonts only via
  `mobile/src/lib/theme.ts` tokens; every screen handles loading, empty and error; data via `useApi(path)`.
- Design rules (enforced by `node mobile/tools/design-lint.mjs` — counts may only go down):
  - Colour: chrome from `usePalette()`; any signal (HR, SpO₂, sleep…) from `data.*` — never a hex literal.
  - Type: sizes from `type.*` via `<T v=…>`; Fraunces only for display numbers/headlines, Inter for everything else.
  - Space/shape: `space.*`, `radius.*` only. Group with proximity (gap inside a card < gap between cards).
  - Motion: `motion.easeOut` for entering, `motion.spring` for press/toggle; no linear easing, nothing over 360 ms.
  - Build progressively: get one widget right on its own, then compose; reuse an existing `ui/` component before
    writing a new one.
- Copy: plain and specific; sentence case; errors say what happened and what to do.

## Where things are

| Need | Look at |
|---|---|
| Product scope and priorities | `docs/product/PRD.md` |
| Architecture now and target | `docs/ARCHITECTURE.md`, `docs/architecture/HLD.md` |
| Module internals | `docs/architecture/LLD.md`, `docs/ENGINE.md` |
| Trained models & engines (clocks, disease, fusion, supplements…) | `docs/MODELS.md`; code in `backend/app/telomy_ml.py`, `backend/app/llx/`, assets in `backend/app/assets/`; training in `research/` |
| Routes / tables | `docs/API.md`, `docs/DATA_MODEL.md` (generated) |
| Cloud deploy / device builds (Oracle VM, HTTPS, multi-user) | `deploy/oracle/`, `docs/DEVICE_INTEGRATION.md`, `docs/history/DECISIONS.md` |
| Design tokens, components, brand assets | `docs/design/DESIGN_SYSTEM.md` |
| Original specs (DPR, engineering guide, UI system, Echo OS, PINN) | `docs/requirements/source/` + traceability in `docs/requirements/README.md` |
| Why things are the way they are | `docs/history/DECISIONS.md`, `docs/history/ITERATIONS.md` |
| Going to production | `docs/production/PRODUCTION_PLAN.md` |
| Machines and the patch | `docs/DEVICE_INTEGRATION.md`, `backend/tools/` |
| Demo video | `scripts/demo_video/`, `docs/demo/RECORDING.md` |

## Production work: read before touching data access

Consumer multi-user tenancy now exists: `accounts.py` (email/password + token) gives each member their **own SQLite file**
(`backend/data_local/users/<id>.db`), bound per-request by `_bind_user` in `main.py`; when accounts exist, the single-user access-password
lock is bypassed (`main.py` `_require_password`). This is how the two-account testing (demo + founder) and the cloud run. The per-user DB
schema is initialised by `accounts._ensure_user_db` — **any new domain module that owns a table must be added to its init list** (a drift
there caused a missing `vitals_ts`/`goals` table in prod). Still ahead for real production (PRODUCTION_PLAN Phase 1): `org_id` ownership on
the management plane, JWT, per-route policies, Postgres + RLS. New tables and queries carry an owner column and filter by it.

## Org, sibling repos & the engineering team

Telomy spans several repos; read `ENGINEERING.md` (this repo root) for the full map, operating cadence
and definition-of-done. Sibling repos under `/Users/anshuman/`:
- `telomy-slm` — Telomy-LLX tool-grounded longevity SLM (Qwen2.5; calls the clocks, never guesses numbers).
- `telomy-vision` — meal-photo→nutrition (USDA + IFCT 2017 India), medical-image/report ingestion, genomics annotation.
- `telomy-lab` — ECG/PPG/sleep signal R&D and validation.
- `research/ageclock` & `research/muscleclock` — trained aging-clock families (blood, muscle) + the DPR.

The virtual engineering team lives in `.claude/agents/` (ml-research, data-engineering, backend-eng,
mobile-eng, devops-sre, clinical-regulatory, qa-security) — invoke a specialist by name for scoped work.
Operate with the enabled **Engineering** and **Data** plugin skills; deep reviews via `/code-review ultra`.
