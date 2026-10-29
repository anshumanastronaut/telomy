# Galaxy Watch 8 — Raw + Computed Data Extraction for the Telomy Engine

*Prepared 29 Oct 2026. Can we pull all the raw and all the computed data off a Galaxy Watch 8 into our engine, and is it worth buying? Short answer: mostly yes, through two Android-only channels; worth buying one as a research/engine unit, and the computed panel is even shippable to customers without Samsung approval.*

## Verdict
**Buy ONE Galaxy Watch 8 (~₹30k) as a research + engine-strengthening unit** (+ an Android phone as companion; **iOS cannot talk to the watch at all**). It's genuinely additive to what we own — not a patch replacement. Two channels, both Android-companion → FastAPI:

1. **Samsung Health *Sensor* SDK** (on-watch app) → **RAW** signals. Dev-Mode on our own watch = **no partner approval**.
2. **Samsung Health *Data* SDK v1.1.0** (phone app) → **COMPUTED** metrics. User-consent only, **no partner gate** → **shippable to customers now**.

The biggest engine win: **BIA body composition** (skeletal muscle mass, body fat %, body water, BMR) — a data class we don't currently capture, and it feeds the **muscular-age clock** (ALMI) directly. Plus Energy Score, sleep stages + apnea, AFib flag, and a second multi-wavelength raw-PPG source.

## What's reachable

### RAW (Sensor SDK v1.4.1, on-watch, Dev-Mode = no partner approval)
| Stream | Rate | Overnight? |
|---|---|---|
| PPG green/IR/red | 25 Hz continuous / 100 Hz on-demand | ✅ (continuous) |
| Accelerometer | 25 Hz | ✅ |
| HR + **IBI** (for HRV) | 1 Hz / per-beat | ✅ |
| ECG raw | **500 Hz**, mV | ✗ on-demand spot only (needs 2-hand contact) |
| SpO₂, EDA, skin temp | 1 Hz / on-demand | partial |
| **BIA bioimpedance** | multi-freq 5–250 kHz | ✗ on-demand spot only |
Continuous PPG+accel+IBI run **concurrently** (the overnight combo); ECG/BIA are spot-only (no overnight ECG). Covers Galaxy Watch4+ incl. Watch 8.

### COMPUTED (Data SDK v1.1.0, on-phone, user-consent, **no partner gate**)
Full **BIA body composition** (body fat %/mass, **skeletal muscle %/kg**, body water, BMR, fat-free mass, BMI), **Energy Score**, Sleep + stages + **Sleep-apnea flag**, **Irregular-heart-rhythm (AFib) flag**, HR, SpO₂, Blood pressure, Skin/Body temp, VO₂max, Steps/Floors, glucose/nutrition/water. Read + incremental `read-changes`. Requires Samsung Health ≥ 6.30.2, Android 10+, Java 17, real device.

### Easy fallback (Health Connect) — lossy
Samsung writes only a subset: HR, SpO₂, BP, VO₂max, sleep+stages, steps, **body fat % + BMR only**, weight, height, menstrual cycle. **Not** synced: skeletal muscle, body water, HRV, stress, Energy Score, ECG, skin temp. ~30–60 min lag, no backfill. Use for cross-device + cycle data; it won't give the BIA-muscle or Energy Score.

### Locked — no programmatic channel (Oct 2026)
**HRV, continuous Stress, Antioxidant Index, Vascular Load.** All computed-only and Samsung-app-only. BUT we get the **raw overnight PPG** these are built from, so we compute our own HRV/stress/vascular metric. Don't architect any dependency on Samsung's versions.

## iOS — confirmed dead end
Samsung's accessory protocol is Android-only; the Sensor SDK has no iOS binding. Everything routes **Watch → Android companion → FastAPI** (exactly our adb/dev-mode skill set). Our iOS/CoreBluetooth app stays for the ring + patch.

## Partner Program — when it's actually needed
- **Not needed:** our own research rig (raw via Dev-Mode), and the **entire computed Data-SDK panel for customers** (consent-based).
- **Needed:** shipping **raw** Sensor-SDK capture to *customers'* watches, or raw ECG/PPG at scale. Multi-week, business-gated, periodically closed — treat as a separate calendar item, not dev effort.

## Effort + repos
- **Computed reader (Data SDK): medium** — Android companion, permissions UI, push to FastAPI device endpoint. **Primary near-term, customer-shippable.**
- **Raw capture (Sensor SDK, Dev-Mode): ~3–7 days** — fork **`Kaist-ICLab/EnPULSE`** (Apache-2.0, active, validated vs Polar H10) + **`EnPULSE-backend`** (MIT) for ingest patterns; **`GalaxyPPG-Logger`** + Supplementary notebooks for proven PPG/accel capture + analysis. +2–4 days for ECG/BIA on-demand.
- Health Connect template: **`android/health-samples`** (Apache-2.0). `teqxnology/healthexport` = reference only (unstated license; and it only exports what's already in HC, so Samsung HRV/muscle fields come back empty).

## Setup (raw, Dev-Mode)
1. Watch: Settings → Apps → **Health Sensor Service** → tap title ~10× → **Developer mode** → accept license → on. (This is what clears the "Error 2003 / SDK_POLICY" gate.)
2. Pair phone+watch via Galaxy Wearable; enable watch ADB.
3. Add `samsung-health-sensor-api.aar` (1.4.1) to a Wear OS Kotlin module; request `PPG_CONTINUOUS`+`ACCELEROMETER_CONTINUOUS`+`HEART_RATE_CONTINUOUS` concurrently; `ECG_ON_DEMAND`/`BIA_ON_DEMAND` as spot captures.
4. Buffer raw to watch storage → sync to phone via Data Layer `ChannelClient` → POST batches to FastAPI → validate vs the patch/Polar before trusting in the engine.

## Compliance
Sensitive health data under **DPDP** — explicit, granular, revocable per-type consent at permission grant; purpose limitation; retention/deletion path. Samsung ToS = "wellness, not diagnosis" → keep clinical claims off anything derived from it (coordinate with the clinical-regulatory track). Permissive licenses only (EnPULSE Apache, EnPULSE-backend/health-samples MIT/Apache); no AGPL/GPL in the key repos.

## How it fits what we already decided
Patch stays our ECG reference (we maximize its features); WHOOP 4 via OpenStrap; TK3040 fixed via Colmi docs. The Watch 8 **adds** three things we don't have: (1) **BIA body composition → muscular-age clock / ALMI**, (2) a rich **customer-shippable computed panel** (Energy Score, sleep-apnea, AFib), (3) a **second raw PPG source** for HRV/vascular R&D. That's why it earns a buy where Polar didn't.
