# Telomy — UI/UX Audit

Audit of the mobile app (~38 screens, `mobile/src/app`) against a mature design system (`ui/core.tsx`,
`theme.ts` — "Telomy Ink", dark-first, teal=science/copper=human, provenance + confidence components built in)
and the current consumer-health UX evidence (Oura 2025 overhaul, WHOOP coaching loop, Function Health labs).

## What's genuinely strong (keep + lean into)

1. **Provenance as a first-class UI primitive** (`Prov`, `ConfBar`, `StatusChip`). Every number can show its
   source + confidence. **No competitor does this** — Function/WHOOP/Oura show numbers, not where they came
   from. This is a *trust* moat; surface it more, not less.
2. **The flagship longevity screen already follows best practice** — leads with ONE answer (the age Dial vs
   chronological + confidence), then "what moves your number" (per-marker ± years), history, honest caveats
   ("clocks rarely agree; the trend matters"). This is the Oura "tell me something, don't dump data" pattern.
3. **Mature, accessible design system** — dark-first, HIG-compliant contrast (`faint` ≥ 4.5:1), a full component
   kit (Screen/Card/Chip/Button/Section/Stat/Empty/ErrorState/Loading). New screens are cheap to build well.
4. **Honesty in the copy** — caveats and "needs a test to show X" empty states build credibility.

## The evidence (what makes consumer health apps work)

- **Oura (2025):** surface **one key metric — "what your body needs now"** — to kill the data-dump.
- **WHOOP:** a **daily coaching loop** (prompts, journaling) → members open it 8×/day. Engagement comes from
  *recurring prompts*, not passive tracking.
- **The competitive layer is interpretation** — WHOOP Coach / Oura Advisor explain **"why"** a score changed.
- **Tie it together:** the common failure is "apps log numbers but don't connect them." The winner fuses labs +
  wearables (+ environment) into **one story**.

## Prioritised improvements

### P0 — the engagement loop (biggest lever, currently missing)
- **A daily "one thing" home card.** Right now the app is screen-per-domain; there's no single daily answer.
  Build a home that leads with **the one thing that matters today** (from the check-in engine `/me/checkin` +
  Sinc), e.g. "Your HRV is down 18% — likely last night's late meal. Here's today's one move." This is the
  WHOOP/Oura loop and the single biggest retention driver.
- **Surface the AI "why" everywhere.** Telomy already has the grounded SLM — put an **"ask why / explain this"**
  affordance on every metric (longevity, risk, sleep). The grounding + provenance makes our "why" more
  trustworthy than WHOOP Coach's.

### P1 — make the fusion story explicit (our differentiator)
- The longevity Dial is blood-only (PhenoAge). **Fuse the wearable overlay + the new exposome into the number's
  narrative:** "PhenoAge 38 · your resting-HR/HRV trend and Delhi's air (−10 yr AQLI) push your *lived* risk
  higher." We have `fusion.risk_profile` and the exposome engine — the UI should tie them into one story, not
  three separate screens. This directly answers the "apps don't connect the numbers" gap.

### P1 — screens for the two newly-wired consumer assets
- **Lab-free chronic screen** (`/me/chronic`, 5.89M) — a "your risk before any blood test" card for Day-1 users
  (age/sex/BMI/lifestyle → ranked risks). Converts a cold start into instant value.
- **Environment / exposome screen** (`/me/environment`) — air (7,482 cities) + social connection + noise + UV,
  each with its life-years translation. A strong, shareable differentiator. (No competitor has social + air +
  noise fused.)

### P2 — polish
- **Onboarding should route to the right device** (patch/ring/band) by the user's goal — the one-device-per-user
  spec in `DEVICE_SENSOR_SPEC.md`. Currently onboarding (154 lines) doesn't branch by goal.
- **Thin screens to enrich:** `risks` (43 lines) should show the ranked disease screen + the chronic screen +
  the "what to do" from the clinic engine, not a bare list.
- **Dense screens to summarise-first:** `twin` (289) and `monitor` (264) should open with a one-line verdict
  before the detail, per the Oura principle.
- **Alerts/notifications:** push red-flag biomarkers and the real **nocturnal-desat** signal (we captured 85%
  dips) — proactive, not pull-only. The push-token plumbing already exists.

## The one-line recommendation
The design system and the flagship screen are already excellent. The gap is **the daily loop and the fused
story**: build a home that leads with *one AI-explained thing a day* and make the longevity number visibly fuse
blood + wearable + environment. That converts a good analytical app into a daily habit — the difference between
WHOOP's 8-opens/day and a quarterly-labs app.
