# Decision log and working memory

The rules, choices and lessons that shaped Telomy during the build (Oct 2026), so a new engineer, or a new Claude session, starts
with the same context. Newest at the bottom of each section. Iteration-by-iteration history: [ITERATIONS.md](ITERATIONS.md).

## Standing rules (do not break)

1. **Fictitious data only in the repo.** People, reports, sessions and routines in code, tests, fixtures and demos are invented.
   The founder's own routine and health data live only in the founder's local database and are never committed or shown in demos.
2. **No secrets in git.** `backend/.env` is ignored; `.env.example` documents variables. API keys are never pasted into chat or code.
3. **Third-party data licences.** DDInter is CC BY-NC-SA (non-commercial): kept out of git under `backend/data/ddinter/` and must be
   replaced by a licensed source before any paid launch. Real competitor screenshots (`research/ultrahuman/shots`) stay out of git.
4. **Clinician in the loop.** Insights, report summaries, monthly reports, therapy plans and prescriptions are drafts until a
   registered clinician signs. The member sees the sign-off thread.
5. **Deterministic safety.** Contraindications, interactions and device alarms are rules with tests, never LLM output.
6. **Honest outputs.** "No reliable signal" and "too early" are first-class results. Simulated values are labelled "simulated".
7. **Payments in test mode** until live billing is set up deliberately. Consents and T&Cs are accepted by people, not by automation.
8. **Public demo servers use a separate fictitious DB** (`demo.db`) with a random admin key; testers are told not to enter real data.
9. **Original design only.** Competitor apps (Neko, Ultrahuman, Nostavia, Apple Health, Fittr) are studied for structure; their assets
   are never copied.
10. **Repo is private.** Collaborators are added by the founder on GitHub.

## Product and science decisions

| Decision | Why |
|---|---|
| One app binary, three roles (member, doctor, centre) | Same data seen from three sides; simpler distribution |
| Event-first Vault with provenance on every value | DPR §5.2; makes "what did what to me" queryable |
| Validated risk equations only (PREVENT 2024, PCE, ADA, FIB-4, KFRE) | Defensible; no home-made risk scores |
| Event effects: OLS with all event kinds as covariates, ≥ 5 events, BH-FDR, split-half replication; "promising" tier for p < 0.01 + replicated | Removed spurious verdicts (trip overlapping HBOT block, short events, chance red-light positive) |
| Therapy physiology as first-order ODE priors validated against 11 literature targets | Gives a meaningful in-session picture before live sensors; replaced by measurement when telemetry exists |
| HSAI domains from Echo OS (autonomic, recovery, cognitive, oxygenation, thermal, metabolic), ±2σ | Continuity with earlier specs |
| Digital twin as a 21-variable hybrid model calibrated per person, with a mirror fidelity score | Explainable, testable; says when it cannot explain a change |
| 24-hour twin from routine: caffeine t½ 5 h, nicotine t½ 2 h, Widmark alcohol | Simple, published kinetics |
| Routine parser tolerant of typos and iOS autocorrect; times read relative to wake-up; water is never alcohol | Real users type fast on phones |
| Voice: local faster-whisper, multilingual intent engine (English, Hindi, Hinglish), acoustic stress fused with HRV, audio not stored | Privacy and cost |
| Exposome via Open-Meteo/CAMS; AQLI and Berkeley Earth cigarette equivalence | Free, citable, India coverage |
| Tests without evidence (grade D) cannot be booked | Claims firewall |
| Doctor signs Rx with dose edits; e-prescription PDF prints prescriber and registration | Telemedicine Practice Guidelines 2020 |

## Engineering decisions

| Decision | Why |
|---|---|
| FastAPI + SQLite modular monolith for the prototype | Speed; module boundaries map to future services |
| `engine.now_iso()` as the single app clock; `TELOMY_TODAY` pins it for tests and demos | Fixed timestamp bugs (consult before request) |
| Lab reports routed to a panel by marker majority, not keywords | Fixed "thyroid"/"ECG gating" misrouting |
| Raw expo-gl WebGL for the 3D body (three.js r163+ dropped WebGL1; R3F failed) | Works on device; paused on a branch |
| Release builds embed the JS bundle; `EXPO_PUBLIC_API_URL` is baked at build time | Testers' phones don't need Metro |
| CI: pytest + `tsc --noEmit` on every push | Keep main green |
| Demo video pipeline: Simulator clips + typeset panels + per-frame voiceover, composed with ffmpeg | Re-recordable by anyone; human voice drops in per frame |

## Known gaps (tracked in the production plan)

Single-user Vault and no authentication; OTP dev code; `/admin/reset` unauthenticated; SQLite; no migrations; DDInter licence;
native wearable sync; DICOM viewer; always-on voice; Telomy Care web; 3D twin UI.

## Lessons

- Simulator automation: iOS shows "Open in Telomy?" on every deep link: approve it before recording; split long screens into clips.
- Hot reload keeps the old GL context: restart the app after GL changes.
- Uppercase text transforms change `µ` to `Μ`: keep units out of uppercased labels or render them separately.
- Long text typed into the Simulator gets autocorrected: seed via the API instead.
