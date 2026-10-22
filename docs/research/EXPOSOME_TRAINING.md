# Exposome-Aware Chronic Models — Training Results (5.89M)

Retrained all 11 BRFSS chronic-disease models on **5,891,176 adults** with the exposome / social / food
parameters BRFSS measures per person added to the lifestyle/demographic set:

- **location** (`state`) — absorbs state-level environment (UV, air, policy)
- **social connection** (`marital` — living alone raises mortality, Holt-Lunstad OR 1.32)
- **urban/rural** (`urban`) — noise / air / activity context
- **food** (`fruit_lt1`, `veg_lt1` — eats fruit / veg < 1×/day)

## Did it help? Yes — small but consistent (every model improved)

| Disease | AUC (lifestyle only) | AUC (+ exposome) | Δ |
|---|---:|---:|---:|
| skin cancer | 0.783 | **0.792** | **+0.009** |
| depression | 0.821 | **0.824** | +0.003 |
| coronary HD | 0.840 | 0.843 | +0.003 |
| heart attack | 0.830 | 0.833 | +0.003 |
| stroke | 0.809 | 0.812 | +0.003 |
| asthma | 0.705 | 0.709 | +0.004 |
| …all others | | | +0.001–0.002 |

## Which exposome parameter matters, for which disease (permutation Δ-AUC)

| Parameter | Strongest for | Reading |
|---|---|---|
| **location (state)** | **skin cancer (0.011)**, asthma (0.006), depression, COPD | geography encodes **UV** (skin cancer) and **air** (asthma/COPD) — environment is real and captured by location |
| **social connection (marital)** | **stroke (0.005)**, heart attack (0.005), arthritis, CHD, depression | living alone / unpartnered is a consistent **cardiovascular + mental-health** risk — matches the isolation→CVD literature |
| **urban/rural** | skin cancer, other cancer, stroke | modest built-environment signal |
| **food (fruit/veg flags)** | — (0.000–0.001) | **weak** — a binary "<1×/day" flag carries little; real food quality needs the detailed diet log (nutrition/NOVA engine), not a postcode or a yes/no |

## Honest takeaways

1. **Environment is real and location captures it** — the clearest win is skin cancer (UV by state) and asthma/COPD
   (air by state). This validates serving the **measured** air/UV layers (WHO 7,482-city engine) on top of the model.
2. **Social connection is a genuine predictor** — marital status is consistently the #2–3 exposome feature for
   cardiovascular disease and depression. Surfacing social isolation is worth it.
3. **Binary food flags are weak** — food quality belongs in the **personal nutrition engine** (measured from the
   diet log), not as a coarse location/survey flag. Confirmed empirically.
4. A **fully-measured** exposome (air+noise+social+food instrumented per person) at a million scale does not exist
   as free data — this is the defensible maximum: 5.89M with the determinants BRFSS captures, + measured
   environmental overlays at serving time.

Models installed to `backend/app/assets/chronic/` (21 features). The app can pass `state / marital / urban /
fruit_lt1 / veg_lt1` via `chronic_tools.predict_chronic`; absent features default to NaN (handled).
