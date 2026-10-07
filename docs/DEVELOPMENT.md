# Development guide

## Prerequisites

- macOS with Xcode 26+ (iOS Simulator) — or any OS for backend-only work
- Python **3.13**, Node **20+**, npm
- Optional: `gh` CLI, an Anthropic API key, an iPhone with Developer Mode for device builds

## Setup

```bash
make setup     # backend/.venv + pip install -r backend/requirements.txt, mobile npm install, backend/.env from .env.example
make voice     # optional: local Whisper for Sinc voice (≈250 MB model downloads on first use)
```

### Configuration — `backend/.env` (git-ignored)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Enables Claude for Sinc. Create at console.anthropic.com → Settings → API Keys. Never commit or paste into chat/issues. |
| `TELOMY_TODAY` | Pins "today" for the seeded test profile (`2026-10-06`) so demos/tests are reproducible |
| `TELOMY_ADMIN_KEY` | Protects device-key issuance (`POST /centre/devices/{id}/key`) |
| `TELOMY_DB` | SQLite path override |

Mobile: `EXPO_PUBLIC_API_URL` overrides the API base URL (default: the Metro host's IP on port 8787 — works for the Simulator and for a phone on the same Wi-Fi).

## Running

```bash
make seed      # rebuild the fictitious test Vault (deletes backend/telomy.db)
make api       # uvicorn on 0.0.0.0:8787 — interactive docs at http://127.0.0.1:8787/docs
make mobile    # Expo dev server; press i for the iOS Simulator
```

Roles: the app asks *Who's signing in?* on first launch (member · doctor · centre owner). Switch from Profile, or deep-link
`exp://127.0.0.1:8081/--/welcome`. Any screen can be opened with `xcrun simctl openurl booted "exp://127.0.0.1:8081/--/<route>"`.

## Tests

```bash
make test      # = backend pytest (115 tests, ~30 s; seeds a fresh DB) + mobile `tsc --noEmit`
```

- Tests run against a freshly seeded DB with **documented ground truth** (see the docstring in `backend/app/seed.py`), so engine tests assert
  that known effects are recovered and that nothing spurious is reported.
- Add a test with every feature and every bug fix. Prefer end-to-end API tests through `TestClient`.
- Screen walks: `qa/walk.sh` and `qa/walk_role.sh` open every route in the Simulator and build contact sheets.

## Test data rules

- Everything under `testdata/` and in the seed is fictitious and marked **TEST DATA**.
- Regenerate report PDFs: `.venv-tools/bin/python testdata/make_lab_reports.py` (or any venv with reportlab).
- Never add real reports, screenshots of real apps with personal data, or real routines to the repo.

## Device builds (iPhone)

```bash
cd mobile && npx expo prebuild -p ios
cd ios && LANG=en_US.UTF-8 pod install
xcodebuild -workspace Telomy.xcworkspace -scheme Telomy -configuration Release -destination 'generic/platform=iOS' \
  -allowProvisioningUpdates DEVELOPMENT_TEAM=<TEAM_ID> -derivedDataPath build
xcrun devicectl device install app --device <UDID> build/Build/Products/Release-iphoneos/Telomy.app
```

Release builds embed the JS bundle (no Metro needed). The phone must reach the API: same Wi-Fi with `EXPO_PUBLIC_API_URL=http://<mac-ip>:8787`,
or a hosted backend. `mobile/ios` and `mobile/android` are generated — not committed.

## Useful tools

| Command | What |
|---|---|
| `backend/.venv/bin/python scripts/gen_docs.py` | Regenerate `docs/API.md` and `docs/DATA_MODEL.md` |
| `backend/.venv/bin/python -m tools.device_simulator --device CRY-1 --key <key> --start <iso>` | Stream fake machine telemetry (run from `backend/`) |
| `curl localhost:8787/physio/validation` | Check physiology priors still reproduce literature targets |
| `curl -X POST localhost:8787/voice/command -H 'content-type: application/json' -d '{"text":"had 2 eggs and a coffee"}'` | Exercise the intent engine |
