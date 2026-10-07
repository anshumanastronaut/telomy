# Roadmap

## Now (v0.4 — prototype)
Feature-complete prototype on the iOS Simulator with fictitious data; 115 backend tests; three roles.

## Next (v0.5 — real data in)
- [ ] Connect real centre machines: device keys + gateway/MQTT bridge per machine type (cryo, HBOT, sauna, PBM, Bonphul PEMF bed)
- [ ] Telomy patch firmware ↔ `/therapy/sessions/{id}/samples` (RR intervals, SpO₂, skin temperature); Polar H10 as interim reference
- [ ] Native dev build: HealthKit / Health Connect sync; background audio for wake word
- [ ] Anthropic key in staging; Claude for Sinc answers, intent understanding fallback and twin narration
- [ ] iPhone release build (embedded bundle) for internal testers; TestFlight

## Then (v0.6 — production foundations)
- [ ] Auth (OTP), role claims, per-patient authorisation; audit log export
- [ ] Postgres + TimescaleDB, object storage, background workers; India-region hosting; CI deploy
- [ ] Licensed drug-interaction source; partner lab and pharmacy APIs; payments (live, not test mode)
- [ ] Voice: on-device VAD + wake word ("Hey Sinc"), speaker verification, larger Whisper / AI4Bharat for Indic languages
- [ ] DICOM viewer; photo meal logging; SCORE2, FRAX; PREVENT UACR/HbA1c add-ons

## Research (Telomy Labs)
- [ ] Therapy Response Phenotype study (≥ 500 members, ≥ 10 cold sessions each; IRB + research consent)
- [ ] HSAI test–retest and vs-lab validation; PINN training on real sessions
- [ ] Voice–HRV cross-validation study

History of what was built and every bug fixed: [docs/history/ITERATIONS.md](history/ITERATIONS.md).
