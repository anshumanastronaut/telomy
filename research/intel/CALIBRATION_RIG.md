# Telomy Multi-Device Calibration Rig — System Design

*Prepared 30 Oct 2026. How we wire every device the user wears into one backend, time-align them, and use them to
calibrate and continuously improve Telomy's engines. Scope: the research/validation rig, not the shipping product.*

---

## 1. Objective

The user wears **every device, always**. We turn that into a continuous, same-body, multi-sensor stream feeding one
backend, so we can (a) **cross-calibrate** every device against the most accurate reference for each metric, and
(b) **train and validate** Telomy's engines (HR/HRV, SpO₂, sleep, activity, body-composition, biological-age) on real,
labelled, reference-anchored data. The eventual payoff is a **hardened firmware + models** for Telomy's own band and
patch, and device-agnostic engines that are superior because they were tuned against a gold-standard bench.

Core principle: **software/models are the USP; the hardware is interchangeable.** Commercial devices are the bench.

---

## 2. Architecture — two stations, one backend, one body

```
  STATION A  (iPhone, Telomy iOS)                 STATION B  (Samsung A35, Telomy Android)
  ├─ Chest patch (KY-E-B1)  → ECG = TRUTH          ├─ Galaxy Watch 8  (Samsung SDKs)
  ├─ Smart ring  (TK3040)   → PPG HR/HRV/SpO₂/temp │   ├─ raw: PPG, accel 25Hz, spot ECG, BIA  (Sensor SDK, Dev-Mode)
  ├─ JCVital V8  (ms-data-sdk)→ PPG HR/SpO₂/temp/steps│   └─ computed: HR/SpO₂/sleep+apnea/AFib/VO₂max/BIA (Data SDK)
  └─ iPhone CoreMotion → 6-axis IMU (torso ref)    ├─ WHOOP 4.0  (via NOOP) → raw PPG/HR/HRV/SpO₂/temp
                                                    └─ Android CoreMotion → 6-axis IMU
                    │                                                   │
                    └───────────────►  BACKEND (Oracle, FastAPI)  ◄─────┘
                         /vitals/ingest  (product longitudinal record, per metric, idempotent upsert)
                         /cal/ingest     (research capture: raw + labelled, one session_id, source-tagged)
```

- **One account** for both phones (same login). One person, one digital twin, fed by all devices — the simplest and
  most correct model for calibration (the engines already assume one user's data). The Android app logs into the same
  account; nothing needs a second account.
- **Two write paths** on purpose: `/vitals/ingest` for the normal product record (what the twin/engines read), and
  `/cal/ingest` for research sessions (raw + labelled, a shared `session_id` across both phones). `/cal` stays the
  calibration lake; `/vitals` stays the clean product record.

---

## 3. Device data inventory — what we get, and what's worth adding

| Device | Live / continuous | Stored / fetchable | Raw signals | Worth adding beyond today |
|---|---|---|---|---|
| **Chest patch** (iPhone) | ECG, HR, HRV (R-R), rhythm/AF, resp, motion(ECG-derived) | 2-h ECG records, nights | **raw ECG ~100–250 Hz** | — (this is the HR/HRV/rhythm **truth**) |
| **Ring** (iPhone) | HR, HRV, SpO₂, skin-temp | 5-min history, own sleep detection | PPG, IMU (not exposed) | already fused |
| **JCVital V8** (iPhone) | **HR, SpO₂, skin-temp, steps, distance, calories** (~1 Hz, now continuous ✅) | **sleep + stages + body-movement + sleep-temp; HRV (5-min test); workouts/sport; GPS; detailed activity** | raw PPG (0x20); **no raw IMU** | **sleep, HRV, activity/GPS** (history fetch) |
| **Galaxy Watch 8** (Android) | HR, SpO₂, skin/body-temp, steps | **sleep + stages + apnea flag, AFib flag, VO₂max, BP, Energy** | **raw PPG, raw accel 25 Hz, spot ECG 500 Hz, BIA** | **BIA body-comp → muscle clock; sleep+apnea; AFib; VO₂max; raw accel (motion); raw PPG** |
| **WHOOP 4.0** (NOOP) | HR, HRV, SpO₂-ratio, temp, motion | — | raw PPG red/IR | route NOOP → `/cal` durably |
| **Phone** (both) | 6-axis IMU, steps, activity, GPS, barometer | — | **raw 6-axis** | torso IMU = reference for the in-dev chest device |

**Direct answer to "motion / sleep / anything worth adding":**
- **Motion:** raw IMU worth adding from **Galaxy (25 Hz accel)** and **phone (torso 6-axis)** — these are the raw-motion
  training sources. JCVital gives **no raw IMU**, but its **processed steps/activity + sleep body-movement** are worth
  adding as labels/cross-checks.
- **Sleep:** **yes, from both** — JCVital (stages + body-movement + sleep-temperature) and Galaxy (stages + **apnea flag**).
  Both fold into Telomy's sleep-fusion engine alongside patch/ring/WHOOP.
- **High-value extras:** Galaxy **BIA body-composition** (skeletal-muscle mass → the muscle-age clock; nothing else we own
  measures it), **AFib** and **VO₂max** flags, and the **raw PPG** (a second optical source for HRV/vascular R&D); JCVital
  **HRV test** and **GPS workout routes** (pace + exposome tie-in).

---

## 4. Time synchronization (two phones = two clocks)

- Both phones are NTP-synced (~tens of ms) — adequate for 1 Hz metrics (HR/SpO₂/temp/steps).
- For **high-rate raw** (ECG/PPG/accel), we lock the two timelines **automatically by cross-correlating the HR series**
  (every device measures HR; the lag that maximises correlation is the clock offset). No manual sync needed for the
  always-on stream.
- Optional **sub-100 ms marker** for raw sessions: a sharp **triple-tap / stomp** at the start and end — spikes in every
  IMU/ECG — gives a hard fiducial.

---

## 5. Calibration methodology

Reference hierarchy, then per-device fit (same discipline as the organ/blood clocks):

| Metric | Gold reference | Calibrate |
|---|---|---|
| HR | patch ECG R-R | ring, JCVital, Galaxy, WHOOP → bias/scale + confidence |
| HRV (RMSSD/SDNN) | patch ECG R-R | PPG-HRV from ring/Galaxy/WHOOP (optical HRV is softer — grade it) |
| SpO₂ | fingertip pulse-ox spot-checks (add a BerryMed) | ring / JCVital / Galaxy |
| Skin temp | cross-device consistency + a reference thermometer | ring / JCVital / Galaxy |
| Steps / activity | **manually counted** walks (true ground truth) | phone pedometer, JCVital, Galaxy |
| Body composition | Galaxy **BIA** (and ideally one DEXA) | → muscle-age clock input |
| Sleep | fuse all + **one PSG / home-sleep night** anchor | staging accuracy per device |

Method per device×metric: collect paired samples vs the reference → fit offset/scale (or a small regression) →
validate out-of-sample → **ship the calibrated parameters into the engine** (as versioned params, like the clocks'
joblib assets). Because capture is always-on, calibrations **update continuously** rather than from one lab session.

---

## 6. Data pipeline

1. **Capture** → each app posts tagged readings. Product metrics → `/vitals/ingest` (idempotent upsert, cursor-advanced).
   Research/raw + labels → `/cal/ingest` (shared `session_id`, `source` tag).
2. **Align** → `research/calibration` pulls `/cal` + the vault, HR-cross-correlates the two stations onto one axis.
3. **Fit + validate** → per-device calibration models with honest error bars; out-of-sample checks.
4. **Ship** → calibrated params + fused models into the engines; a dashboard tracks drift per device.

---

## 7. Build phases & status

- **Phase 0 — iPhone always-on (DONE / in progress).** Patch + ring + JCVital now continuous into `/vitals` (JCVital
  wired this session: `lib/jcvitalsource.ts` → auto-connect + stream + vault sync, like the ring). Phone CoreMotion ref
  exists via TelomyRec. *Next:* fetch JCVital **sleep + HRV + activity** history into the record.
- **Phase 1 — Samsung baseline.** Pair Galaxy to A35 (done); **Android Telomy app** (Expo Android build, same account);
  route **WHOOP/NOOP + Galaxy Data-SDK computed** → backend. *In progress (Android build).* 
- **Phase 2 — Galaxy raw.** Wear OS **Sensor-SDK** module (Dev-Mode) for raw PPG / accel 25 Hz / BIA / spot ECG →
  backend (fork `Kaist-ICLab/EnPULSE`). ~3–7 days.
- **Phase 3 — calibration engine.** `research/calibration` pipeline: align, fit, validate, ship, dashboard.

---

## 8. Honest limitations & risks

- **JCVital on iOS is continuous while the app is ACTIVE** (ble-plx is JS). True 24/7 background needs a native
  CoreBluetooth module (like the patch/ring) — a later step. The patch/ring keep streaming in the background already.
- **First Android build** — Expo supports it; the patch's Swift module is iOS-only (fine — the patch stays on the
  iPhone, features degrade gracefully on Android). ble-plx + ms-data-sdk are cross-platform (ring/JCVital can run on
  Android too if wanted). Requires the Android SDK/toolchain installed on the build machine.
- **Galaxy raw at customer scale is business-gated**; our own research unit via Dev-Mode is not.
- **Sleep truth** is the weakest link without a PSG night — until then "sleep" calibration is device-consensus, stated
  honestly.
- **Security:** the JCVital Flutter SDK PDF leaked a GitHub PAT — rotate it (we use only the public MIT RN SDK).

---

*Companion: GALAXY_WATCH8.md (Samsung SDK data map), NOOP_ADOPT.md, DEVICE_INTERCEPTION.md. Clinical/medical features
remain decision-support; device readings are wellness-grade until calibrated and validated.*
