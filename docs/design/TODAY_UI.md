# Today (Home) UI: design decisions

Researched on 2026-10-13: the Oura 2025 redesign, WHOOP Home and Overview, the Apple Health iOS 27 redesign, and health-dashboard practice (NN/g progressive disclosure, JMIR 2026 scoping review).
Code: `mobile/src/ui/today.tsx` and `ui/wellness.tsx`; scores in `lib/wellness.ts` (methods in `docs/devices/WELLNESS_SCORES.md`).

| Principle | Source | How Telomy applies it |
|---|---|---|
| One big thing | Oura Today ("the most critical score you need right now") | Recovery is the hero: a 270° dial with a 64 pt number. Sleep and Strain are secondary doorways |
| Primary number readable at arm's length | WHOOP (~72 pt) | 64 pt Fraunces numerals that count up on load |
| Colour reflects body state | Oura state colours | A radial glow and gradient arc in the recovery band colour: green ≥ 67, amber 34–66, red ≤ 33. The guidance words use the same bands |
| Narrow colour vocabulary | WHOOP | Recovery = green/amber/red, Sleep = indigo `#8EA8FF`, Strain = orange `#FF9A5A`, Stress = amber. Teal only for app chrome |
| Tiles are doorways, not destinations | WHOOP | Every tile has a chevron, haptic tick and ≥ 44 pt target, and opens a detail screen with the same dark hero |
| Coaching next to the number | WHOOP | A one-line coach sentence directly under the dial |
| Progressive disclosure, 3 levels | NN/g; JMIR 2026 | Level 1 hero → level 2 cards (last night, stress, fitness) → level 3 detail (contributors, charts, method, sources) |
| Compare with *your* normal | Oura baselines, Apple Vitals | Vitals show "▲/▼ x vs your normal" once 3 nights exist. Until then a "Learning your normal" chip |
| Header earns its space | — | One line: real date (label) and short greeting. The Vault (Longevity age etc.) follows under "Your Vault" |
| Honest empty and calibrating states | — | "Wear the band tonight", "No band data today", "Learning your normal: night n of 4" |
| Dark hero works in both themes | Apple HIG | Ink gradient hero with a hairline border, so it keeps its edge in dark mode |

## Hierarchy (top to bottom)
1. Date and greeting (one line), with notifications and clinician queue.
2. **Recovery hero:** dial, guidance word, coach line, calibrating chip, and doorways to Sleep and Strain. The live-heart pill opens Live ECG.
3. **Last night:** duration, score chip, sleep/wake timeline with hour ticks, and vitals tiles (lowest HR and when, overnight HRV, breathing, HR drop).
4. **Body:** Stress and Fitness (VO₂max estimate) tiles.
5. **Your Vault:** Longevity age, biomarkers, next action, insights, domains, pinned signals, Rewind (unchanged).

## Next design passes
- A daily timeline ("your day so far": sleep → stress → activity), like Oura's Today timeline.
- Swipe between days on Recovery and Sleep detail.
- 7- and 30-day trend views with a baseline band (HRV, resting HR, breathing).
- A widget and Live Activity for the live band.
