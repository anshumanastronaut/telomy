# WHOOP 4.0 + NOOP: the raw data, what's missing, and how we compute it ourselves

Deep research, 2026-10-21, grounded in our **actual** data (`backend/app/whoop.py` receiver + the founder's 2.3M-row
Vault). The headline: **NOOP gives us WHOOP's *raw sensor streams* but not WHOOP's *computed metrics* — because WHOOP
computes SpO₂, HRV, recovery and respiratory rate on its own cloud, which NOOP bypasses.** That's why they're blank.
And it's an opportunity: we hold the raw signal and can build transparent, calibrated, n-of-1 engines WHOOP won't.

---

## 1. What NOOP is, and the protocol

NOOP (`com.noop.whoop.staging`, github.com/ryanbr/noop, PolyForm-Noncommercial — **study only, never copy its code**)
sideloads on Android, pairs the WHOOP 4.0 strap over BLE, reads the strap's raw characteristics, and **self-hosts a
push** to any endpoint. Telomy is that endpoint (`backend/app/whoop.py`, `POST /whoop/push`): a capabilities handshake
(`receiverStateId`, stream list, `protocolVersion`) then batched **NDJSON** records per stream, idempotent by key, with
`append` (time series) and `replace_window` (sessions/days) delivery. Our receiver stores every stream verbatim.

---

## 2. The raw streams we actually receive (founder's Vault)

| Stream | Rate | Fields (verbatim) | Count | What it is |
|---|---|---|---|---|
| `hrSample` | 1 Hz | `{bpm}` | 312,556 | Heart rate |
| `rrInterval` | per-beat | `{rrMs, seq}` | **456,983** | Beat-to-beat R-R → **the HRV source** |
| `gravitySample` | 1 Hz | `{x, y, z, dynAccel}` | 312,487 | **IMU** — gravity/orientation vector (dynAccel null) |
| `respSample` | 1 Hz | raw | 312,487 | Respiration signal |
| `skinTempSample` | 1 Hz | `{raw, aux1Raw, aux2Raw}` | 312,487 | **Raw thermistor count — NOT °C** |
| `spo2Sample` | 1 Hz | `{ir, red}` | 312,487 | **Raw red/IR PPG counts — NOT SpO₂ %** |
| `event`, `battery` | — | — | 291k / 5.5k | Markers, battery |
| `sleepSession` | per-night | stages, efficiency, `motionJSON`, endTs… | 6 | **WHOOP's on-strap sleep read** |
| `dailyMetric` | per-day | see below | 4 | **WHOOP's on-strap daily rollup** |

**We get MORE raw signal than WHOOP's own app shows** (1 Hz gravity + red/IR + thermistor + every R-R). The strap is a
rich sensor; WHOOP's app just hides the raw.

---

## 3. The gap: what NOOP leaves **null** (and why)

A real `dailyMetric` record:
```json
{"deepMin":86.5,"lightMin":111.15,"remMin":109.5,"efficiency":0.919,"restingHr":53,"strain":17.42,
 "totalSleepMin":307.15,"skinTempDevC":0.4,  "spo2Ir":615,"spo2Red":545,
 "spo2Pct":null, "avgHrv":null, "recovery":null, "respRateBpm":null, "steps":null}
```

- **`spo2Pct`, `avgHrv`, `recovery`, `respRateBpm` are all `null`.** The strap streams the **raw** signal; WHOOP's
  **cloud** turns red/IR → SpO₂ %, R-R → HRV, HRV+RHR+sleep → recovery, resp signal → breaths/min. **NOOP never touches
  WHOOP's cloud, so those arrive empty.** This is *the* reason SpO₂, HRV and recovery don't show in Telomy.
- **`skinTempDevC: 0.4` IS present** — a temperature **deviation from baseline** (+0.4 °C), the strap's own on-device
  read. So for temperature *trends* (illness/recovery) we already have a usable number; only **absolute °C** needs work.

**So the fix is not "find the missing number" — there is none to find. We compute them ourselves from the raw.**

---

## 4. How we compute each metric from the raw (and calibrate it)

### 4a. HRV — we have it already (457k R-R)
`rrInterval {rrMs}` is the gold input. Compute **RMSSD / SDNN** per 5-min window.
- ⚠️ **Correction needed:** WHOOP 4 history R-R is **~2.4× over-delivered** (duplicate/interpolated beats), so naive
  RMSSD reads inflated (~50 ms vs ECG 33 ms on 2026-10-18). **Dedupe + plausibility-gate the R-R**, then compute.
- **Calibrate against our ECG patch** (gold standard) on a shared night — the patch gives true beat-to-beat; fit a
  per-user correction so PPG HRV tracks ECG HRV. *This is our unfair advantage — no competitor has an ECG reference.*

### 4b. SpO₂ — ratio-of-ratios on the raw red/IR
From `spo2Sample {ir, red}`: compute AC (pulsatile) and DC (baseline) per channel over a window, then the
**ratio-of-ratios** `R = (AC_red/DC_red) / (AC_ir/DC_ir)`, and `SpO₂ = c0 − c1·R` ([TI SLAA655](https://www.ti.com/lit/pdf/slaa655), [Renesas OB1203](https://www.renesas.com/en/document/apn/ob1203-pulse-oximeter-algorithm-spo2-heart-rate-and-respiration-rate)).
- The generic `SpO₂ ≈ 110 − 25R` is only a starting point; **the curve is device-specific and must be empirically
  calibrated.** → **The "calibrate with something else" step: have the user wear a cheap FDA fingertip pulse oximeter
  for a few sessions, log (our R, reference SpO₂) pairs, fit c0/c1.** Then our SpO₂ is calibrated to *this sensor on
  this finger*. (Report overnight **trend + desaturation dips**, not a clinical number — same honesty rule as Oura.)

### 4c. Skin temperature — deviation now, absolute via thermistor fit
- **Deviation** (`skinTempDevC`) is already usable for illness/recovery/cycle trends — ship that.
- **Absolute °C** from `skinTempSample.raw`: it's an NTC thermistor ADC count. Convert via **Steinhart–Hart** (fit A,B,C
  from resistance at ~30/35/40 °C) or a lookup table, then a **per-device linear correction against a reference
  thermometer** ([TDK NTC note](https://www.tdk-electronics.tdk.com/download/2988204/740594dd4ec109808826d1b5c774b3f6/ntc-thermistors-readout-trimming-an-for-design-tools.pdf), [thermistor calibration](https://www.dataloggerinc.com/wp-content/uploads/2018/07/18-Thermistor_Calibration_for_High_Accuracy_Measurements.pdf)). Narrow span (30–40 °C) → <0.01 °C error; watch self-heating & lead resistance.

### 4d. Respiratory rate — from R-R (RSA) or respSample
Breaths/min from **respiratory sinus arrhythmia** in the R-R series, or the `respSample` stream directly. **Validate
against ECG-derived respiration from the patch** (we already do ECG respiration).

### 4e. Recovery — our own, from our own HRV + RHR + sleep
Don't chase WHOOP's `recovery` (null anyway). Compute ours from calibrated HRV + resting HR + sleep vs the person's
baseline — transparent and ours to tune.

### 4f. IMU (`gravitySample {x,y,z}`) — posture, motion, sleep
A 1 Hz gravity/orientation vector (~1 g magnitude; `dynAccel` not exported). Gives: **posture/position** (vector
direction), **movement** (vector deltas → activity, tossing), and the **z-angle-change** signal HDCZA uses for sleep.
`sleepSession.motionJSON` is WHOOP's own per-epoch motion magnitude derived from this — we can recompute richer motion
from the raw 1 Hz vector (and fuse with HR for the onset work).

---

## 5. What this means strategically

- **NOOP is a raw-data goldmine, not a metrics source.** Treat it as a sensor feed, not a finished product. Everything
  polished (SpO₂, HRV, recovery, resp) we build ourselves — which is exactly the **engine moat**.
- **We can be more transparent AND more accurate than WHOOP's black box**, because we (a) hold the raw and (b) have an
  **ECG patch as a gold-standard calibration reference** for HRV and respiration, plus simple external references
  (fingertip oximeter, thermometer) for SpO₂ and absolute temp — then **calibrate per-user (n-of-1)**.
- **Priority order** (value × feasibility): HRV from R-R (have it, just dedupe + ECG-calibrate) → respiratory rate →
  SpO₂ trend (needs oximeter calibration pass) → absolute skin temp (needs thermistor fit) → our own recovery score.
- **Ship honestly:** trends + dips + "calibrated to you," never a clinical SpO₂/temp number without the reference pass.

Sources: [TI SpO₂ design (SLAA655)](https://www.ti.com/lit/pdf/slaa655) · [Renesas OB1203 SpO₂/HR/resp](https://www.renesas.com/en/document/apn/ob1203-pulse-oximeter-algorithm-spo2-heart-rate-and-respiration-rate) · [TDK NTC readout](https://www.tdk-electronics.tdk.com/download/2988204/740594dd4ec109808826d1b5c774b3f6/ntc-thermistors-readout-trimming-an-for-design-tools.pdf) · [thermistor calibration](https://www.dataloggerinc.com/wp-content/uploads/2018/07/18-Thermistor_Calibration_for_High_Accuracy_Measurements.pdf) · internal: `backend/app/whoop.py`, `telomy-lab/whoop/`.
