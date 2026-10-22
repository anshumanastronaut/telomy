# Telomy Digital Twin — Research & Feature Roadmap

Where the human digital twin is going (2025–26 evidence) and what Telomy should add. Telomy already has a
strong base: an interactive 3D anatomy twin (`twin3d/`, tap-to-focus organs, status colouring, layers), a
PhenoAge/PREVENT risk core, and a what-if simulator (`/twin` presets, N-year scenarios).

## The state of the art (grounded)

- **Organ-specific aging is the frontier.** The 2026 *Cell* "Digital Aging Twin" (Aging Biomarker Consortium)
  builds **per-organ clocks** (brain, liver, lung, muscle, blood vessels, skin), each from clinical markers +
  plasma proteins + imaging. Its multimodal tier hit **MAE 3.87 y**, beating every single-layer clock.
- **Organs age unevenly** — the liver shows an inflection ~age 40, the brain ~age 50. A twin should show *which*
  system is aging fastest for this person, not one global number.
- **Mechanistic, actionable links** — e.g. liver-derived coagulation factors drive vascular aging (actionable
  targets, not passive markers).
- **A twin = physical model + virtual counterpart + their interaction** (the loop), with interactive
  visualization as the clinician/consumer surface.
- **Caveat:** consumer-facing *what-if simulation* tools are still largely unvalidated — frame ours as
  decision-support, with provenance.

## Shipped this iteration

- **Organ-specific aging clocks** (NHANES 49.7k): metabolic, hepatic, renal, immune, cardiometabolic — each a
  per-organ age + **age-acceleration** residual. Coarser than the *Cell* multimodal clocks (we use routine
  chemistry, not proteomics/imaging) but a real *relative* organ-age signal. → feeds the twin's per-organ view.
- **Organ edge-rail in the 3D twin** — a side list of body-part names; tapping one **flies the camera to that
  organ** (same `selected` state as tapping the mesh). Fixes the "orbiting to a precise organ on a small screen
  is fiddly" problem without removing the free 3D interaction.

## Features to add (prioritised)

### P0 — make the twin show *uneven* aging (the differentiator)
- **Colour each organ by its own age-acceleration** (from the new organ clocks): "your metabolic system reads
  +6 y, your kidneys −2 y." This is the *Cell*-paper insight made personal, and nobody in consumer does it.
- **A per-organ age readout** on focus — tap Liver → "hepatic age 44 (chrono 38, +6 y); driver: GGT, ALT."

### P1 — the what-if loop, per organ
- **Organ-level what-if:** "if you cut alcohol, your hepatic age trajectory bends by X over 5 y" — the simulator
  already does whole-body; scope it to the focused organ using that organ's markers + the correlation engine.
- **Wearable → organ overlay:** resting-HR/HRV/SpO₂ trends nudge the heart/vessels/lung organs (via `fusion`).

### P2 — depth
- **Mechanistic links** between organs (liver→vessels), shown as edges when an organ is flagged.
- **Imaging/retina/gait hooks** (the *Cell* inputs) as "add this test to sharpen your brain/vascular clock" —
  honest about what each extra modality buys.
- **Longitudinal twin:** animate the organ ages over the member's history; show the inflection points.

## Honest framing
Our organ clocks are blood-chemistry-grade (MAE 11–14 y), not the multimodal 3.87 y of a full biobank twin —
so we present **relative** organ aging and **trajectory**, label provenance + confidence, and offer the extra
tests (proteomics, imaging) that would tighten each clock. The twin is decision-support, not a diagnosis.
