# Clinical safety & claims firewall

Telomy is a wellness and clinician-decision-support platform. It never diagnoses or prescribes on its own.

## Claims firewall (Telomy DPR §12.1)
| Do say | Do not say |
|---|---|
| Tracks how your body responds | Diagnoses / cures / treats disease |
| Surfaces patterns for you and your clinician | Detects cancer / heart disease / dementia |
| Personalised protocols reviewed by your clinician | AI prescribes / AI decides your treatment |
| Your clinician recommended this supplement | Take this to fix X |
| Supports relaxation / recovery / sleep readiness | Guaranteed weight loss / reversal / anti-ageing |
| Telomere-inspired longevity intelligence | Measures your telomere length (unless that test is ordered) |

Every score screen carries "not a diagnosis"; HSAI, voice stress and the digital twin are labelled wellness indices / decision aids.

## Clinician in the loop
Drafts that require a registered clinician's signature (with a note) before the person can act: medical Sinc insights, monthly reports,
therapy plans (then sessions are booked), Rx plans (then ordering is possible; doctor may remove items and edit doses), report reviews.
Prescription medicines are dispensed only via a licensed pharmacy partner against the e-prescription; IVs only at the centre.

## Deterministic safety envelope (never model output)
- **Therapy screen** from the Vault: e.g. pregnancy, pacemaker, uncontrolled BP, recent cardiac event, Raynaud's, untreated pneumothorax (HBOT),
  DVT (compression), photosensitising drugs (PBM), G6PD deficiency (IV vitamin C), alcohol today (sauna), coronary plaque (cryo caution).
  Not-suitable therapies cannot be started or booked.
- **In-session tiers**: HR > 90% of age-max, SpO₂ < 90 % (< 80 % for IHHT), BP-proxy rise > 35 mmHg, sauna core rise > 1.6 °C.
- **Machine alarms**: channel hard limits (e.g. HBOT pressure, PEMF coil 45 °C), machine error codes.
- **Rx**: major interactions block an item; D-grade tests and products are refused; exclusions listed with reasons (melatonin Rx-only, NMN not
  FSSAI-listed, under-dosed stacks, high-dose antioxidants).

## Honesty requirements
- Simulated values (physiology priors, seeded data) are labelled as simulated everywhere they appear.
- "No reliable signal" and "too early" are first-class outputs; confidence and uncertainty bands are shown.
- Population evidence and personal evidence are distinguished in every explanation.
