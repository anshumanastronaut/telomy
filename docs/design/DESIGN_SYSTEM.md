# Telomy design system: what we used and how to keep using it

**Last reviewed:** 2026-10-11 · Canonical spec: *Telomy UI Design System v1.0* ([PDF](../requirements/source/design-brand/Telomy_UI_Design_System_v1.0.pdf)) ·
brand: *Brand Identity Brief*, *Brand Architecture*, *Brand Story*, *Telomy Logo* (same folder) · implementation: `mobile/src/lib/theme.ts`, `mobile/src/ui/`

The spec is the source of truth. The prototype implements most of it; where it deliberately or temporarily differs, the difference is
listed in §7 with a decision to make before v1.0.

---

## 1. Brand

- **Name and line:** TELOMY: *Where human biology becomes intelligent.*
- **Mark:** an infinity loop drawn as two waveform-filled lobes. One continuous line stands for continuity of life; the waveform
  stands for signal. Ink on Cloud Dancer, white on dark; teal glow on the app icon.
- **Colour roles:** teal = science (data, charts, links); copper = human (CTAs, annotations, signatures).
- **Assets in the repo**

| Asset | File | Use |
|---|---|---|
| App icon | `mobile/assets/images/icon.png` (mark at 70 % on `#0A0B0C`, teal glow) | iOS icon |
| Android adaptive icon | `android-icon-foreground.png` (56 %), `-background.png`, `-monochrome.png` | Android |
| Full logo | `logo-full-ink.png`, `logo-full-white.png` | Welcome screen, video cards |
| Mark only | `logo-mark-ink.png`, `logo-mark-white.png`, `logo-glow.png` | Home header, splash |
| Wordmark | `wordmark-ink.png`, `wordmark-white.png` | Headers |
| Splash | `splash-telomy.png`, `splash-icon.png`; boot animation `mobile/assets/boot.mp4` | Launch |
| Tab icons | `mobile/assets/images/tabIcons/` | Legacy; tabs now use SF Symbols |
| Brand stills | `brand/` (`icon.png`, `splash.png`, `strip.jpg`, animation frames) | Source images |
| Original logo | [Telomy_Logo.pdf](../requirements/source/design-brand/Telomy_Logo.pdf) | Master artwork |

Unused Expo template files (`react-logo*`, `expo-*`, `tutorial-web.png`) can be deleted.

## 2. Colour tokens (as implemented, `theme.ts`)

| Token | Light | Dark | Role |
|---|---|---|---|
| `bg` | `#F0EEE9` | `#121413` | App background (Cloud Dancer family) |
| `surface` | `#FFFFFF` | `#1B1E1C` | Cards, sheets |
| `surfaceAlt` | `#E8E5DE` | `#242825` | Segmented controls, secondary surfaces |
| `text` | `#1B1C1A` | `#ECEAE4` | Primary text |
| `muted` / `faint` | `#6B6A64` / `#9A988F` | `#A19F97` / `#77756E` | Secondary text, metadata |
| `border` / `borderStrong` | `#D9D5CC` / `#B9B4A8` | `#2E332F` / `#454B46` | Dividers |
| `teal` / `tealSoft` | `#1F5C4E` / `#DCE8E3` | `#6FBBA4` / `#1E3A33` | Science accent |
| `copper` / `copperSoft` | `#A9643A` / `#F3E6DB` | `#D69466` / `#3A2A20` | Human accent |
| `success` / `warn` / `danger` (+ soft) | `#2F7A55` / `#A86E12` / `#A33A2A` | `#6CC394` / `#E0A84A` / `#E07B69` | Status only |

Status mapping (`statusColor`): optimal/typical/signed/helpful → success; in range/awaiting/info → warn; out of range/detected → danger.
Colour is never the only carrier: every status chip also has text.

## 3. Typography

| Role | Implemented | Spec |
|---|---|---|
| Display (titles, big numbers) | **Fraunces** 400/500 (`@expo-google-fonts/fraunces`, SIL OFL) | *Telomy Display* (custom), fallback Cambria/Georgia |
| UI | **Inter** 300/400/500/600 (`@expo-google-fonts/inter`, SIL OFL) | Inter |
| Mono | Menlo / platform monospace | JetBrains Mono |
| Editorial (web) | n/a | Source Serif 4 |
| Annotations | n/a | *Anshuman Hand* (custom), fallback Kalam |

Scale used in `T` (`ui/core.tsx`): display 34/40 · h1 26/32 · h2 20/26 · h3 16/22 (600) · body 15/22 · small 13/18 · label 11, 600,
uppercase, tracking 1.4 · num 24 (tabular) · numLg 52/58 (tabular). Max font scale 2×. Uppercase labels keep `µ`-units in lower case
(native uppercasing turns µg into "MG").

The Telomy wordmark typeface appears only in the logo, splash and boot animation.

## 4. Space, radius, motion

- Space (`space`): 4, 8, 12, 16, 20, 24, 32, 40 (8-pt system with a 4/12/20 half-step).
- Radius (`radius`): sm 6 · md 10 · lg 14 · xl 20 · pill 999 (spec: 4 / 8 / 12 / 20 / round).
- Motion (spec): 80 / 160 / 200 / 400 ms; easing standard `cubic-bezier(.4,0,.2,1)`; the mark's 8 s ambient trace is the only
  always-on motion; respect reduced motion.

## 5. Components (`mobile/src/ui`)

| Component | Purpose |
|---|---|
| `T` | All text; variants above |
| `Screen`, `Section`, `Card`, `Row`, `Spacer`, `Divider`, `ListRow` | Layout |
| `Chip`, `StatusChip`, `Prov`, `ConfBar` | Labels, status, **provenance chip** (source · date · confidence), confidence bar |
| `Button`, `Segmented`, `Toast`/`useToast` | Actions and feedback |
| `Stat`, `Loading`, `Empty`, `ErrorState` | Numbers and states (every screen has loading, empty and error) |
| `charts.tsx` | `LineChart` (zones band, **life-event overlay**, scrub, "View as table"), `Dual`, sparklines |
| `therapy.tsx` | `VerdictChip`, `SafetyChip`, `SessionChart` (phases), `PhaseLegend`, `HsaiCard` |
| `insight.tsx`, `predictions.tsx`, `patient.tsx`, `roleprofile.tsx`, `tabs.tsx`, `slider.tsx`, `logo.tsx`, `intro.tsx` | Feature components |

Icons: SF Symbols through `expo-symbols` (e.g. `bolt.heart`, `list.bullet.clipboard`, `waveform.path.ecg.rectangle`).

## 6. Screens (72 routes)

| Role | Tabs | Key stack screens |
|---|---|---|
| Member | Home · Vault · Therapy · Plan · Sinc · Profile | marker, report, insight, predict, longevity, therapy/[id], session/[id], therapy-plan, therapies, tests, rx, twin, voice, routine, activities, activity/[id], environment, plans, monthly, consult, family, consent, studies, imaging, brief, completeness, memory, notifications |
| Doctor | Today · Patients · Work queue · Profile | patient/[id] (AI summary, reports, therapies), review/[id] |
| Centre | Home · Floor · Members · Bookings · Services · Profile | centre-research |
| Shared | welcome (role picker), onboarding | |

QA contact sheets of every screen per role: `qa/user.jpg`, `qa/doctor.jpg`, `qa/centre.jpg`; walk scripts `qa/walk*.sh`.

## 7. Spec vs implementation: decisions before v1.0

| Item | Spec | App | Recommendation |
|---|---|---|---|
| Background | `#F8F8F5` | `#F0EEE9` | Keep app value (better card contrast) and update the spec, or switch; decide once |
| Copper | `#B8946A` | `#A9643A` | Spec copper is 2.6:1 on its background (fails text contrast); app copper is 4.6:1 on white cards, 4.0:1 on the page. Use app copper for text on cards and large text only; update spec |
| Display face | Telomy Display (custom) | Fraunces | Ship custom face when the type designer delivers; Fraunces until then |
| Icons | Custom 24-icon set | SF Symbols | Commission the set; SF Symbols are iOS-only, so Android needs it anyway |
| Mono | JetBrains Mono | Menlo | Bundle JetBrains Mono for parity |
| Tokens package | `@telomy/design-tokens` shared with web | `theme.ts` | Extract when Telomy Care web starts |
| Digital-twin 3D body | n/a | Branch `feat/twin-3d-body` (expo-gl point cloud) | Resume UI work there; do not copy third-party assets |

## 8. Voice and tone

Plain, specific, honest. Name things as people know them. Say "no reliable signal yet" when that is true. Errors say what happened and
what to do. Medical outputs say "draft for clinician review" until signed. Never promise outcomes (claims firewall in
[CLINICAL_SAFETY](../CLINICAL_SAFETY.md)).
