# Ultrahuman Blood Vision — UI study (2026-10-19)

Observed by driving the Ultrahuman Android app (Samsung A35, read-only). What they do well, and what Telomy should
adopt or deliberately reject.

## What Blood Vision shows
- **Blood Age hero.** A single big number (33) vs a horizontal gradient bar with a marker for chronological age and a
  marker for blood age, labelled "5 years older". Instant, emotional, one glance.
- **Biomarker tally.** `74 BIOMARKERS · 48 OPTIMAL · 16 BORDERLINE · 10 OUT OF RANGE` with a dot-grid (one coloured dot
  per marker). Shows breadth and status distribution without scrolling.
- **Visualize — a radial node graph.** Blood Age sits in the centre (with a small body render); around it float six
  *systems* (Thyroid, Hormone, Cholesterol, Heart, Hair, Glucose Regulation). Each system expands to its markers as
  connected nodes, each coloured by status, each carrying a trend phrase ("borderline and getting worse"). A marker can
  belong to several systems (e.g. Free T3 appears under Thyroid, Hormone and Hair).
- **Contributors list.** The Blood Age page lists the 12 markers that drive the number, each with value, unit, its
  optimal range, and WITHIN/OUT OF RANGE.
- **Trend language on every status**, not just a static flag: "stable", "getting worse".

## Worth adopting (ranked)
1. **System/organ grouping of markers as the primary lens.** Telomy has panels but no "what organ system is this
   about" view. Our `retrieval._LINKS` already maps findings → systems (cardiovascular, metabolic, liver, sleep,
   inflammation, nutrient). Surface that as a grouped view: each system with its markers + the live wearable signals and
   the food lever. This is strictly richer than Ultrahuman's (they don't connect wearables). → **new `/sinc/insights`
   threads already do the data side; add a Systems screen that renders them.**
2. **Status carries a trend, always.** Adopt "X and getting worse / stable / improving" wording wherever we show a
   marker or signal. We already compute `marker_trend`; put the phrase on the chip, not just an arrow.
3. **The hero + distribution tally.** A single Blood-Age hero with a chrono-vs-bio bar, plus an `optimal / borderline /
   out-of-range` tally with a dot grid, as the top of the Vault or Longevity screen. We have PhenoAge; we lack the
   one-glance hero and the tally.
4. **A marker belonging to several systems.** Model markers as many-to-many with systems (ApoB → Heart + Metabolic),
   so tapping a system shows everything relevant, and tapping a marker shows every system it touches.

## Deliberately NOT adopting
- **A 12-marker blood age with hidden weights.** Their number read 33 vs our PhenoAge 28 on the same values; their model
  isn't validated against mortality and its weights aren't published. Keep PhenoAge (Levine 2018, NHANES-validated) as
  the headline; a "metabolic age" view only after NHANES validation.
- **The free-floating node graph as the main navigation.** It looks striking but is slow to read precise values and
  hard on a phone. Use a grouped list/cards for the data, and keep any radial view as a secondary "map", not the way to
  read a number.
- **Selling tests inside the data view.** "Book a Test" is woven through their reads. Keep Telomy's reads clean.

## Telomy's advantage to lean into
Ultrahuman connects *blood to blood*. Telomy connects **blood ↔ wearables ↔ trackers ↔ genetics ↔ nutrition** — the
new RAG `connect()` already produces those threads. The Systems screen should make that the headline: not "your LDL is
high" but "your LDL, your deep-sleep trend, your saturated-fat target and your APOE ε4 are one cardiovascular story."
