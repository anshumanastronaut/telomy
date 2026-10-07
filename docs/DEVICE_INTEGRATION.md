# Device integration — centre machines, Telomy patch, wearables

Three data streams describe one therapy session:

| Stream | What it tells us | Endpoint |
|---|---|---|
| **Machine telemetry** | What the machine did to the body — chamber temperature, pressure, O₂, irradiance, field strength… | `POST /devices/{device_id}/telemetry` |
| **Body signals** (Telomy patch, chest strap, band) | How the body responded — HR, RR intervals/HRV, SpO₂, skin temperature, respiration… | `POST /therapy/sessions/{session_id}/samples` |
| **Context** | Who, which therapy, prescribed settings, how they felt | `POST /therapy/sessions` · `…/finish` |

The server links them by **device + time window**, computes the delivered dose vs the prescription, raises alarms and analyses the physiology.

## 1. Machines

### Onboarding a machine

1. The centre owner creates the device in Telomy (seeded examples: `CRY-1`, `HBO-1`, `HBM-1`, `SAU-1`, `PBM-1`, `PMF-1`, `CMP-1`… — `GET /centre/devices`).
2. Issue a key (shown once; store in the gateway; re-issue to rotate):

```bash
curl -X POST https://<server>/centre/devices/HBO-1/key -H "X-Admin-Key: $TELOMY_ADMIN_KEY"
# → {"device_id": "HBO-1", "key": "tdk_…"}
```

### Sending telemetry (HTTPS)

```http
POST /devices/HBO-1/telemetry
X-Device-Key: tdk_…
Content-Type: application/json

{"samples": [
  {"ts": "2026-10-06T11:00:00", "pressure_ata": 1.00, "o2_pct": 21.0, "chamber_temp_c": 23.1, "status": "running"},
  {"ts": "2026-10-06T11:00:05", "pressure_ata": 1.02, "o2_pct": 98.5, "chamber_temp_c": 23.2, "status": "running"}
]}
```

- 1–10 s resolution; batch up to 20,000 samples per request (recommend 60–120 every 5–10 s).
- `ts` is local ISO-8601 (centre time zone, IST). `status` is `ok`/`running`/`idle` or a machine error code (raised as an alarm).
- Unknown channels are ignored, never stored. Values outside hard limits raise alarms in the response and on the live floor.
- Responses: `200 {"stored", "alarms"}` · `401` bad key · `404` unknown device · `422` invalid sample.

### Channels per machine type

`GET /devices/channels` returns the authoritative list with units and hard limits. Summary:

| Modality | Channels |
|---|---|
| cryo | `chamber_temp_c`, `door_open` |
| hbot / hbot_mild | `pressure_ata`, `o2_pct`, `chamber_temp_c`, `co2_ppm`, `humidity_pct` |
| sauna / sauna_ir / contrast | `temp_c`, `humidity_pct`, `panel_power_pct`, `water_temp_c` |
| redlight | `irradiance_mw_cm2`, `panel_temp_c` |
| pemf / halo | `field_gauss`, `frequency_hz`, `coil_temp_c` (45 °C hard limit = Halo firmware cut-off), `irradiance_mw_cm2`, `bed_temp_c` |
| cold / float | `water_temp_c` |
| compression | `pressure_mmhg` |
| vibroacoustic | `frequency_hz`, `amplitude_pct` |
| h2_inhal | `h2_pct`, `flow_ml_min` |
| ihht / ewot | `fio2_pct` / `o2_lpm`, `power_w` |
| iv | `rate_ml_h`, `volume_ml` |

New machine type: add it to `CHANNELS` in `backend/app/devices.py` (+ a dose rule in `for_session`) and a profile in `tools/device_simulator.py`.

### MQTT (machines on the clinic LAN)

Publish to `telomy/<centre_id>/<device_id>/telemetry` with one sample or `{"samples": [...]}`. Run the bridge on a clinic gateway:

```bash
pip install paho-mqtt
TELOMY_SERVER=https://<server> DEVICE_KEYS='{"HBO-1":"tdk_…"}' python -m tools.mqtt_bridge --broker 192.168.1.10
```

The bridge buffers and retries, so a run is never lost if the internet drops.

### What the server does with it

- **Session link** — telemetry on the session's device from 10 min before to (planned minutes + 40 min) after the slot.
- **Delivered vs prescribed** — e.g. cryo: seconds below −110 °C, mean active temperature; HBOT: max ATA, minutes at pressure, mean O₂,
  compression time; sauna: mean temperature, minutes hot; PBM: delivered J/cm²; PEMF: mean gauss, minutes on, max coil temperature.
- **Telemetry-driven physiology** — until body signals arrive, the person's physiology prior is re-run with the *measured* machine inputs
  (labelled "ODE prior driven by machine telemetry").
- **Live floor** — `GET /centre/floor`, `GET /centre/devices/{id}/telemetry`.

Test without hardware: `python -m tools.device_simulator --device CRY-1 --key tdk_… --start 2026-10-06T07:55:00 --target '{"chamber_c": -150}'`.

## 2. Telomy patch (in development) and other body sensors

Create or reuse a session (`POST /therapy/sessions` with `{"modality": "cryo", "params": {...}}` → `id`), then upload samples — live or after the
session (the HBOT Faraday-cage case: buffer to flash, upload on exit):

```http
POST /therapy/sessions/{id}/samples
{"source": "Telomy patch v0.3", "samples": [
  {"t": 0,  "rr_ms": [812, 798, 825, 810], "spo2": 97.4, "skin": 33.1, "resp": 14.2},
  {"t": 5,  "hr": 74, "rmssd": 41.0, "spo2": 97.5, "skin": 33.0}
]}
```

- `t` = seconds from session start (5 min baseline precedes the active phase). ≥ 20 samples.
- Signals: `hr`, `rmssd`, `spo2`, `skin`, `core`, `resp`, `sbp`, `eda`, `perf` — or raw `rr_ms` arrays from which HRV (RMSSD) and HR are computed server-side.
- Optional phase marks: send the session's phases from the expected trace (`GET /therapy/sessions/{id}`) or let the server infer them.
- The response returns the full feature set (HR surge, HRV suppression/rebound, *k*, rewarming half-time, TRI, SpO₂ kinetics, safety tier).

Recommended patch firmware behaviour (from the Echo OS spec): ECG 500 Hz → R-peak detection on device → RR intervals; PPG for SpO₂; TMP117 skin
temperature at 1–5 Hz; BioZ respiration; flash-buffer during HBOT; BLE upload in 5-s windows otherwise.

Until the patch ships: a **Polar H10** chest strap (RR intervals over BLE) is the reference device for real in-session HRV.

## 3. Wearables (daily signals)

`POST /signals` accepts manual or integration values (`{"metric": "hrv", "value": 52}`). HealthKit / Health Connect sync needs the native build
(roadmap) and will write the same `signals` rows with source = device.
