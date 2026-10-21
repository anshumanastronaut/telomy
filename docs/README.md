# Telomy documentation

Start here. Read in this order if you are new; jump by role otherwise. Claude Code users: [`/CLAUDE.md`](../CLAUDE.md) is loaded automatically.

## Step by step

| Step | Read | You will know |
|---|---|---|
| 1 | [requirements/README.md](requirements/README.md) | Every source document and where each requirement lives in the code |
| 2 | [product/PRD.md](product/PRD.md) | Problem, users, requirements with priorities and status, metrics, releases |
| 3 | [architecture/HLD.md](architecture/HLD.md) | System context, current vs target architecture, key flows (diagrams) |
| 4 | [architecture/LLD.md](architecture/LLD.md) | Module internals, API surface, data model, mobile app, tests |
| 5 | [design/DESIGN_SYSTEM.md](design/DESIGN_SYSTEM.md) | Brand, colours, fonts, components, screens, open design decisions |
| 6 | [production/PRODUCTION_PLAN.md](production/PRODUCTION_PLAN.md) | How to go from the test user to real users, phase by phase |
| 7 | [DEVELOPMENT.md](DEVELOPMENT.md) | Set up, run, seed, debug, build for Simulator and iPhone |

## Reference

| Doc | Content |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current-state overview and module table |
| [ENGINE.md](ENGINE.md) | Every algorithm and model with citations (guideline path) |
| [MODELS.md](MODELS.md) | Trained-ML suite + engines: clocks, disease, mortality, fusion, supplements, modalities, voice (datasets, metrics, `/me/*` API) |
| [API.md](API.md) · [DATA_MODEL.md](DATA_MODEL.md) | Generated (`make docs`): 171 operations, 48 tables |
| [DEVICE_INTEGRATION.md](DEVICE_INTEGRATION.md) | Centre machines, Telomy patch and wearables → server contract |
| [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md) | DPDP, secrets, test-data rules |
| [CLINICAL_SAFETY.md](CLINICAL_SAFETY.md) | Claims firewall, clinician-in-the-loop, safety envelope |
| [ROADMAP.md](ROADMAP.md) | What's next |
| [history/DECISIONS.md](history/DECISIONS.md) | Standing rules, decisions and lessons (project memory) |
| [history/ITERATIONS.md](history/ITERATIONS.md) · [history/PLAN.md](history/PLAN.md) | Build history |
| [demo/RECORDING.md](demo/RECORDING.md) | Demo video: clips, voiceover in your own voice, composition |
| [requirements/source/](requirements/source) | Original PDFs/DOCX: DPR v5, Engineering Guide v3, UI Design System, brand, hardware specs, Echo OS, PINN code |

## Dependencies used to build Telomy

| Part | Manifest | Main pieces |
|---|---|---|
| Backend | `backend/requirements.txt` | Python 3.13, FastAPI 0.142, Starlette 1.7, uvicorn 0.54, Pydantic 2.13, pypdf, reportlab, numpy, anthropic SDK, pytest, httpx |
| Voice (optional) | `backend/requirements-voice.txt` | faster-whisper 1.2 (Whisper "small" int8), ctranslate2, PyAV |
| Mobile | `mobile/package.json` | Expo SDK 57, React Native 0.86, React 19.2, expo-router, expo-audio, expo-speech, expo-symbols, reanimated, svg, zustand, TypeScript 6; fonts `@expo-google-fonts/inter`, `@expo-google-fonts/fraunces` |
| Demo video | `scripts/demo_video/requirements.txt` | Pillow, numpy; ffmpeg; Xcode Simulator |
| Device tools | `backend/tools/` | Device simulator, MQTT bridge |
| External services | n/a | Anthropic Claude (optional), Open-Meteo / CAMS (exposome), Cloudflare tunnels (demos only), GitHub Actions (CI) |
| Data licences | n/a | DDInter (CC BY-NC-SA, non-commercial, not committed); Google Fonts Inter and Fraunces (SIL OFL) |
