# Telomy

Longevity app: one Vault for labs, imaging, fitness tests, genetics and wearables, read by Sinc — an evidence-first companion with a clinician in the loop.

## Layout
- `backend/` — FastAPI + SQLite. Lab/imaging PDF parser (15 report types, ~160 markers), PhenoAge dial, domain scores, correlation engine (adjusted OLS with FDR, lagged correlations, 25 cross-modality rules), risk map, action plan, Sinc (Claude when `ANTHROPIC_API_KEY` is set, grounded retrieval otherwise), specialist briefs (PDF + FHIR).
- `mobile/` — Expo (SDK 57) app: Home · Vault · Sinc · Sessions · Profile and ~35 screens.
- `testdata/` — generator + 15 dummy reports (clearly marked TEST DATA).
- `research/` — teardowns of Nostavia, Apple Health, Ultrahuman, Fittr (structure only).
- `qa/` — screen-walk script used to test every screen in the iOS Simulator.

## Run
```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8787
.venv/bin/python -m pytest -q
cd ../mobile && npm install && npx expo start --ios
```
See `PLAN.md` and `ITERATIONS.md`.
