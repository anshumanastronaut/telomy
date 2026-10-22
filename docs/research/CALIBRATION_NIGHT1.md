# Night-1 Calibration & Cross-Device Analysis

First full overnight capture with the Telomy recorder — chest ECG patch, TK3040 ring, BerryMed oximeter, and
WHOOP raw, all on one session clock (session `2026-10-21T20-49-24Z`, **47,541 readings**). This is the honest
read-out: what the data lets us conclude, and what it doesn't.

## Headline

The **pipeline works end-to-end** — four devices, one clock, durable sync, ~8 h of aligned data through
device dropouts. The **cross-device HRV/HR comparison is valid and informative**. The **WHOOP SpO₂ and skin-temp
calibrations could not be fit from this night** — for concrete, fixable reasons, not a tooling failure.

## 1. Cross-device HRV — the ECG patch as reference ✅

Patch ECG (beat-accurate) is the ground truth; PPG devices paired to it by time:

| Device HRV | vs patch (ECG) | Reading |
|---|---|---|
| **Ring** | bias **+12.6 ms**, SD 7.3 ms | overestimates |
| **WHOOP** | bias **+17.6 ms**, SD 7.1 ms | overestimates more |

Patch median HRV **28 ms**; ring **41**, WHOOP **38**. Both PPG devices read HRV **13–18 ms high** vs ECG, and
point-to-point correlation is ~0 (both PPG series are near-flat computed values). **This is exactly the thesis
the ECG patch exists to prove:** wrist/finger PPG systematically inflates HRV, and only an ECG reference reveals
it. This bias is itself a usable per-device correction.

## 2. Cross-device HR

| Device HR | vs patch | SD |
|---|---|---|
| WHOOP | **−8.5 bpm** (reads low) | 6.6 |
| Ring | +2.7 bpm | **17.5** (noisy) |
| Oximeter | −11.5 bpm | 12.9 |

Patch HR 62–91 bpm (clean). WHOOP runs ~8 low; the ring is centred but noisy (SD 17). Patch is clearly the
cleanest HR source.

## 3. WHOOP SpO₂ calibration — could not fit ❌ (and why)

- Oximeter saw SpO₂ **85–100%**, but at per-minute resolution the night was **96–100% almost throughout** — only
  1 minute below 97%. The real dips (to 93%, one to 86%) were **sub-minute**.
- WHOOP's **raw red/IR ratio barely moved** (0.856–0.862 across the whole night) and did **not** track the dips.
  Per-minute fit R² = 0.01.
- **Root cause:** (a) not enough physiological SpO₂ *range* this night to define a slope — a healthy sleeper
  stays flat; (b) WHOOP's wrist PPG SpO₂ signal is weak and its raw ratio is nearly constant. You cannot
  calibrate a sensor against a variable it isn't resolving, over a range that didn't occur.
- **To actually calibrate SpO₂:** run a **controlled desaturation protocol** — a short breath-hold series
  (watch the oximeter drop to ~90–94% and recover), with both devices logging, so the raw ratio is forced across
  a real range. One such session gives the 2–3 points the fit needs.

## 4. WHOOP skin-temp calibration — could not fit ❌ (and why)

- WHOOP's raw thermistor value swung **613–885** while true skin temp (ring) was **stable at 36.6–36.8 °C**.
- A huge raw swing under a physically stable temperature means the raw field is **artifact-dominated** (wrist
  contact/motion), or is not a clean thermistor code — a linear (or even Steinhart-Hart) fit can't recover a
  stable temperature from an artifact-driven raw. R² = 0.00.
- **To calibrate temp:** a **temperature-challenge protocol** (warm then cool the skin over ~10 °C of real
  variation) against a contact thermometer, plus confirming what WHOOP's `skinTempSample.raw` actually encodes.
  The ring's own temp (36.6–36.8, physiologically sane) is the more trustworthy skin-temp source tonight.

## 5. Motion (WHOOP IMU) ✅

Median 1.4 mg, p90 4.9 mg, **27% of samples "still" (<1 mg)** — a real nocturnal movement profile, usable for
wake-detection and as the artifact gate for the HRV/SpO₂ above.

## What this night proves

- The **recorder + cloud + one-clock architecture is sound** — it produced 47k aligned readings across 8 h and
  survived every device dropout (patch, ring, oximeter each dropped and recovered; WHOOP via cloud never did).
- The **ECG patch earns its place**: it quantified a +13–18 ms HRV inflation in both PPG devices that no
  single-sensor product can see.
- **Calibration needs *driven* protocols, not a passive night.** A healthy sleeper doesn't vary SpO₂ or temp
  enough to fit a curve. The next session should be a 15-minute **active calibration block** (breath-hold series
  for SpO₂, warm/cool for temp) with all devices logging — that is what closes the WHOOP calibration.

## Still to run (needs the on-device raw ECG)

Sleep-stage verification against WHOOP's own hypnogram needs the **full-rate ECG** from the patch's on-device log
(`ecg-<session>.csv`), pulled off the phone and run through the KYECG HSMM stager. The cloud has only the
decimated trace. That's the next pull + analysis.
