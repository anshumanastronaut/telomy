# CLAUDE.md: working on Telomy

Context for Claude Code (and any new engineer). Read this first, then `docs/README.md`.

## What this is

Telomy is a longevity-intelligence platform: one Vault for labs, imaging, wearables, therapy sessions, medicines and life events;
Sinc, an evidence-first AI that drafts while a clinician signs; and tools for doctors and longevity centres. One Expo app serves three
roles (member, doctor, centre owner) against a FastAPI backend. **Status: v0.4 prototype on fictitious data; next is production**
(see `docs/production/PRODUCTION_PLAN.md`).

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
| Routes / tables | `docs/API.md`, `docs/DATA_MODEL.md` (generated) |
| Design tokens, components, brand assets | `docs/design/DESIGN_SYSTEM.md` |
| Original specs (DPR, engineering guide, UI system, Echo OS, PINN) | `docs/requirements/source/` + traceability in `docs/requirements/README.md` |
| Why things are the way they are | `docs/history/DECISIONS.md`, `docs/history/ITERATIONS.md` |
| Going to production | `docs/production/PRODUCTION_PLAN.md` |
| Machines and the patch | `docs/DEVICE_INTEGRATION.md`, `backend/tools/` |
| Demo video | `scripts/demo_video/`, `docs/demo/RECORDING.md` |

## Production work: read before touching data access

The member Vault is single-user today (only 5 of 48 tables have `patient_id`) and there is no auth. Phase 1 of the production plan adds
`user_id`/`org_id` ownership, JWT auth, per-route policies and Postgres RLS. New tables and queries must already carry an owner column
and filter by it.
