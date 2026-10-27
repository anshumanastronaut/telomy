# Telomy Personal Health Agent — always-on, privacy-first (Omi-style)

`telomy-slm/telomy_llx/{voice_biomarkers.py, personal_agent.py}`. The app captures audio on-device with
explicit, revocable consent; each moment is processed locally into DERIVED signals only — a voice-arousal
index + extracted health mentions — and raw audio/transcript are dropped unless the user opts to keep them.

- **Voice biomarkers:** acoustic features (F0, energy, voiced/pause, speaking-rate, spectral alpha-ratio,
  jitter/shimmer) → a **personal-baseline** arousal index (z-score vs the user's own calm baseline).
  Honest per the 2024-25 literature: speech tracks *physiological arousal*, not labelled emotion;
  absolute thresholds are unreliable/sex-dependent — so we require a ≥3-segment calm baseline and never
  claim an emotion diagnosis. Verified: tense→elevated, calm→calm only after calibration.
- **Personal agent:** consent-gated `observe()` loop → voice arousal + health-mention extraction
  (symptom/mood/sleep/meal/activity/meds) → updates the intake profile, logs derived moments, fires
  gentle nudges (stress pattern → breathing + ties to HRV; symptom → log to Vault), `daily_summary()`
  feeds the daily n-of-1 audit. Privacy controls: `pause()`, `resume()`, `forget(since)`. Nothing sent
  externally. 22/22 tests pass.

Status: engine built + tested. Native hooks pending: on-device mic capture + ASR (Whisper) in the iOS
app; wiring arousal into the wearable-fusion stress signal; surfacing moments in the app.
