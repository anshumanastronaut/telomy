# Changelog

Detailed history, including every bug found and fixed: [docs/history/ITERATIONS.md](docs/history/ITERATIONS.md).

## v0.4.0 — 2026-10-07
- In-session physiology priors (11 literature targets) and session analytics; 24 therapies, 28 machines, safety screen, verdicts, plans, live floor, phenotypes, HSAI
- Machine telemetry ingestion (device keys, HTTPS + MQTT bridge, delivered vs prescribed, telemetry-driven priors); patch RR-interval ingestion
- Digital twin (21 variables, personal calibration, 10-year what-ifs, 24-h twin, mirror)
- Voice Sinc (local Whisper, 99 languages, intent engine, voice stress); routines from free text; custom activities; exposome
- Tests & scans catalogue (75); Telomy Rx with doctor sign-off, interactions and e-prescription; doctor AI summaries for every report
- 9 new report types (24 total, 254 markers); 9 new cross-modality rules
- Repo: docs, CI, templates, Makefile, `.env` configuration, pinned requirements

## v0.3.0 — 2026-10-06
- Three roles (member, doctor, centre), plans and pricing, monthly doctor-signed reports, on-demand consults
- AHA PREVENT 2024, PCE, ADA, FIB-4, KFRE with what-ifs; Inter + Fraunces; Telomy logo, splash and boot video

## v0.2.0 / v0.1.0
- Vault, parser (15 report types), PhenoAge, correlation engine with adjusted effects and FDR, risk map, action plan, Sinc, briefs, 45-screen app
