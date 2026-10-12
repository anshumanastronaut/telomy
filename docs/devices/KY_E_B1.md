# KY-E-B1 ECG band (live ECG, HR, HRV)

Single-lead dynamic ECG from Guangzhou Kangyuan (sold as "AiLL"): chest strap, adhesive patch or vest. Telomy talks to it directly
over Bluetooth with its own iOS code. The vendor's Android SDK was studied for interoperability; **no vendor code is in this repo**.

| | |
|---|---|
| Code | `mobile/modules/ky-ecg` (Expo native module) · `mobile/src/lib/band.ts` (store) · `mobile/src/ui/ecg.tsx` (visuals) · `mobile/src/app/monitor.tsx`, `app/ecg/[id].tsx` · `backend/app/band.py` |
| Firmware tested | HW `B1_V1.1`, FW `B1_1.00.39_250728` |
| Sampling | **100 Hz** live and recorded (87 samples per frame every 0.87 s), int16 µV |
| Not for | HBOT (manual: no oxygen-rich use, 700–1060 hPa operating pressure). Diagnosis (wellness single-lead) |

## Bluetooth protocol

Service `DE5BF728-D711-4E47-AF26-65E3012A5DC7`; notify `…729`; write-without-response `…72A`.
Frame `0xBC | cmd | len (u16 LE) | checksum (u16 LE, sum of payload bytes) | payload`. Implemented in `ios/Core/KYProtocol.swift`.

| Cmd | Use | Payload → reply |
|---|---|---|
| 0x2A | Handshake after notifications are on | empty → `01` |
| 0x10 | Device info | → battery, hw (len-prefixed), fw (len-prefixed), adcRef |
| 0x32 | Electrode contact | → `isLeadOn (1)`, dropCount |
| 0x30 | Live ECG start/stop | `1/2, seconds u24 LE` → status, 2 unknown bytes |
| 0x31 | Live ECG frame | `index u24, pad, int16 × 87` |
| 0x22 | On-device recording start/stop | `1/0, seconds u24, motion 0` → `01`/`00` |
| 0x24 | Recording state | → 0 off · 1 single · 2 sleep · 3 continuous · 4 reading · 5 charging · 6 low battery |
| 0x2D | Recording start time | `op (0 get / 1 set), unix u32` → unix u32 |
| 0x27 | Stored frame count | → u32 |
| 0x23 | Read stored frames from index | `index u24` → stream of frames (same 178-byte format as live) |
| 0x2C | End read session | empty |
| 0x40–0x43 | Firmware update | **never used** |

## Signal processing (on the phone, `ios/Core/KYAnalyzer.swift`)

| Stage | Method | Source |
|---|---|---|
| Baseline wander | 200 ms + 600 ms median filters | de Chazal et al. 2004 |
| Display band | 40 Hz Butterworth low-pass (bilinear zero at Nyquist cancels 50 Hz mains at fs = 100 Hz) | AHA monitoring bandwidth (Kligfield 2007) |
| QRS detection | Pan–Tompkins: 5–15 Hz band-pass, 5-point derivative, squaring, 150 ms integration, adaptive SPK/NPK, 200 ms refractory, T-wave slope test, search-back at 1.66 × mean RR | Pan & Tompkins 1985 |
| Fiducial point | R peak with learned polarity; parabolic interpolation | HRV Task Force 1996 (≥ 100 Hz with interpolation) |
| Signal quality (10 s) | bSQI (agreement with an independent Elgendi detector), kSQI (kurtosis), pSQI (5–15/5–40 Hz power), basSQI | Clifford, Behar et al. 2012; Elgendi 2013 |
| Quality gate | good: bSQI ≥ 0.9, kSQI > 5, basSQI > 0.9, pSQI 0.4–0.9 · acceptable: bSQI ≥ 0.8, kSQI > 3 | calibrated on our recordings |
| RR artefacts | ectopic / long-short / missed / extra beats from dRR with time-varying thresholds; corrected by interpolation, split or merge | Lipponen & Tarvainen 2019 (Kubios) |
| HRV | Mean NN, SDNN, RMSSD, pNN50 over 60 s and 300 s; shown only when quality is good/acceptable, ≥ 30 NN and ≤ 5 % corrected | Task Force 1996 |
| Not computed | Frequency-domain HRV (100 Hz is not adequate), rhythm diagnosis | |

Adaptive HR (Kalman), noise/motion classes, activity, sleep (live and whole-night) and rhythm screening (AF pattern, pauses,
brady/tachy, early beats, bigeminy/trigeminy) are documented, with PhysioNet validation, in [KY_E_B1_ALGORITHMS.md](KY_E_B1_ALGORITHMS.md).
Offline therapy recording and the research export format are in [THERAPY_CAPTURE.md](THERAPY_CAPTURE.md).

Display **cushion**: frames arrive in 0.87 s bursts, so the monitor draws 1.0 s behind real time from a 12 s ring buffer for a
continuous sweep (25 mm/s, 10 mm/mV ECG paper).

## Validation (2026-10-12, iPhone 13 + band, seated)

| Check | Result |
|---|---|
| Live stream 4 min | 278/278 frames, 0 lost, 99.9 Hz |
| On-device recording 192 s → sync | 220 frames in ~10 s, sequential, 99.6 Hz |
| Beats vs offline reference | 280 vs 283 (3 in the 2 s warm-up); RR identical ± 1 ms |
| HRV vs offline reference | RMSSD60 12.8 vs 12.8 ms · SDNN60 24.3 vs 24.2 ms |
| Quality | bSQI 0.94, kSQI 11–12, pSQI 0.6, basSQI 0.94–0.95 |
| Artefact correction | ectopic beat: RMSSD 63.6 → 4.5 ms (clean 4.4); missed/extra beats split/merged |

Recordings used for validation are personal health data and are kept outside the repo.

## Data flow

Band → `KYBand` (CoreBluetooth, auto-reconnect, background restore) → `KYAnalyzer` → JS events (`onEcg`, `onBeat`, `onMetrics`,
`onStatus`, `onRecording`, `onRhythm`) → `lib/band.ts` → minute summaries `POST /band/minutes`, strips `POST /band/strips`, synced
recordings with whole-night sleep `POST /band/recordings`, rhythm events `POST /band/events`; during a live therapy session, 5-s samples
`{t, hr, rr_ms}` → `POST /therapy/sessions/{id}/samples`. Therapy captures are written on the phone (`KYCapture`,
`Documents/therapy-sessions/`) and shared as files or uploaded with `POST /band/captures`.
