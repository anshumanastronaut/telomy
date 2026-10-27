# Bonphul Modalities — device suite, evidence, and the centre modality engine

**Date:** 2026-10-21 · Source: Bonphul product list + bonphulapl.com + a literature review per modality.
These are the hardware modalities Telomy supplies to wellness/longevity centres. This grades each honestly
and defines how the engine recommends, safety-screens, and tracks them (n-of-1), with no outcome-overreach.

## The device suite (bonphulapl.com)
CryoGen/CryoGun (whole-body + localised cryotherapy) · ZIMA (cold plunge) · AGNEE & IMMORTAL-T (red/NIR
photobiomodulation; 410–1064 nm) · ZENITH (far-infrared sauna, 2–10 seat) · AERION (longevity pod:
O₂/H₂/O₃/salt/sound/PEMF/aroma/vibro-acoustic) · Hyperion (HBOT 2–3 ATA, PVHO/ASME) · EMS suit · Red-light
cabins/panels. (The site makes only general "medical-grade/patented" claims and cites no studies — so we
supply the evidence layer ourselves.)

## Evidence grades (A strong · B moderate · C preliminary · D weak/controversial)
| Modality | Device | Grade | What the evidence supports | Honest caveat |
|---|---|---|---|---|
| Far-infrared sauna | ZENITH | **B** | Sauna cohorts (KIHD): ↑frequency → up to ~60% lower CV mortality, ↓BP/stroke/dementia | observational, men; **FIR ≠ traditional sauna** (cooler) — an extrapolation |
| Whole-body cryo | CryoGen | **B** | Meta of 11 RCTs: ↓inflammatory response; hsCRP ↓ (cohort) | mood/recovery weaker; small trials |
| Cold plunge | ZIMA | **B** | CWI: ↑sleep & quality-of-life | **mood NOT significant** in meta |
| Photobiomodulation | AGNEE/IMMORTAL-T | **B** | Red/NIR: scars & skin-aging moderate; biphasic (fluence matters) | pain/recovery mixed, small trials; industry-funded skin data |
| HBOT | Hyperion | **C** (B for approved indications) | small uncontrolled trial +~20% telomere, ↓senescent T-cells (newer cohort +29%) | **no control, same group; longevity "reversal" claims overreach** |
| Molecular hydrogen | AERION/IMMORTAL-T | **C** | 81+ early trials; safe; antioxidant/anti-inflammatory signals | dosing unstandardised; needs multicentre RCTs |
| PEMF | AERION | **C** (B bone/wound) | established for bone healing & wound repair | broader wellness thin |
| Halotherapy (salt) | AERION | **C** | preliminary respiratory (FEV1, mucociliary) | no guidelines |
| Vibro-acoustic | AERION/IMMORTAL-T | **C** | ↑parasympathetic, ↓perceived stress (small) | preliminary |
| Ozone (O₃) | AERION | **D** | weak/controversial for wellness | **inhaled ozone is toxic; medical-supervision only — not a general wellness offering** |

## The modality engine (`telomy-slm/telomy_llx/modalities.py`)
- **`recommend_for_goal(goal, profile)`** → evidence-graded modalities for a goal (cardiovascular,
  recovery, inflammation, sleep, skin, longevity, respiratory, stress, cognitive, pain), each with a
  protocol (dose/frequency) and the markers to track — ordered by evidence grade, grade-D warned.
- **Deterministic contraindication screen** (hard-coded safety, never a model output): e.g. PEMF blocked
  for pacemaker/ICD; cryo/cold blocked for cold urticaria/Raynaud's/uncontrolled HTN/recent cardiac event;
  HBOT for untreated pneumothorax / bleomycin chemo / recent ENT surgery; sauna for unstable angina /
  severe aortic stenosis; ozone for G6PD / never-inhale. Verified (pacemaker → PEMF blocked).
- **`n_of_1(modality, before, after, weeks)`** → per-client verdict (helped / no_signal / too_early) from
  whether the tracked markers moved in the expected direction vs that client's own baseline. Verified
  (8-wk sauna → "helped": RHR −6, BP −10, CRP −0.9).

## "Training" — honest framing
There is no proprietary outcome dataset for these devices, so expected effects are **literature priors**
(graded above). The engine tracks each client's real before/after response at the centre; as that data
accrues it **recalibrates the priors per modality/centre** — the same n-of-1 loop as the supplement
engine, and the path to a genuinely trained modality-response model once centre data exists. No
lifespan/cure claims; a clinician signs off every protocol; ozone is not offered as wellness.
