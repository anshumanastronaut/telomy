# KY-E-B1: interpretation algorithms and validation

This doc covers what runs on top of the beat detector in `KY_E_B1.md`. The code is `mobile/modules/ky-ecg/ios/Core/`: `KYAnalyzer.swift` (beats, SQI, HRV), `KYInsight.swift` (adaptive HR, noise, activity, sleep, rhythm screening) and `KYSleepNight.swift` (whole-night sleep).
All outputs are **wellness information, not a diagnosis**. Rhythm flags are screening prompts to see a doctor.

## 1. Beat detector (tuned)

The detector is Pan–Tompkins with Hamilton–Tompkins thresholds:
- thresholds come from the medians of the last 8 QRS and noise peaks (`thresholdCoef 0.2`);
- a peak is confirmed 50 ms after the local maximum of the rising integrator;
- search-back runs at 1.66 × median RR;
- T-wave slope rejection applies within 360 ms.

The coefficients were chosen by a sweep on the train split (F1 96.58 → 97.62).

Validation used PhysioNet records resampled to 100 Hz, matching within ±150 ms (`~/telomy-lab/validate`, data outside the repo):

| Database | Records | Se | +P | HR MAE |
|---|---|---|---|---|
| MIT-BIH Arrhythmia (mitdb) | 48 | 97.99 % | 97.36 % | 5.9 bpm |
| Normal Sinus Rhythm (nsrdb) | 18 | 99.14 % | 98.65 % | 1.4 bpm |
| Atrial Fibrillation (afdb) | 23 | 94.73 % | 93.57 % | 4.1 bpm |
| Sleep (slpdb) | 18 | 99.79 % | 99.33 % | 1.4 bpm |

Known weak cases:
- very low amplitude below ±0.2 mV (afdb 07162);
- dense ventricular ectopy (mitdb 208, 213, 228).

## 2. Adaptive heart rate (`KYKalmanHR`)

A scalar Kalman filter runs on instantaneous beat HR (Li, Mark & Clifford 2008):
- **Measurement noise R** is scaled by signal quality (bSQI, kSQI, window class). Poor signal is trusted less, not discarded blindly.
- **Process noise Q** adapts from the normalised innovation squared, so it follows real changes such as exercise onset.
- **Gating:** jumps beyond 4σ are rejected unless 3 in a row point the same way. That accepts a real step change and rejects a spike.
- **Coasting:** with no usable beats, the estimate holds and confidence decays. HR shows dimmed with ±sd until good beats return.

The app shows Kalman HR and keeps the 10-s artefact-corrected mean (`hr10`) as a reference.
Respiratory sinus arrhythmia (RR swinging 625–725 ms with breathing) is normal. The filter smooths it rather than "fixing" it.

## 3. Signal and motion (`KYNoiseMonitor`)

Every 2 s, the raw window is classified as one of: `clean`, `noisy`, `motion`, `no_contact`, `flat` or `saturated`. Inputs are:
- the lead-off flag;
- clipping (|x| ≥ 32000);
- standard deviation (< 8 µV means flat);
- muscle noise, as the ≥ 30 Hz power / QRS-band power ratio (> 0.35 means noisy);
- baseline excursion below 0.7 Hz (> 600 µV noisy, > 1500 µV motion);
- sample-to-sample jumps (> 4000 µV motion).

`motionIndex` is the share of non-clean windows over the last ~30 s.

Beats in non-clean windows still feed HR (with high R) but are excluded from HRV and rhythm screening.
Thresholds are first estimates marked `[cal]`. Noise-stress calibration on nstdb is next (records `nst_*` are prepared).

## 4. HRV

- HRV uses clean beats only and needs ≥ 80 % coverage of the window. Lipponen–Tarvainen correction runs first.
- RMSSD is reported at 60 s and 5 min (`rmssd5`, the standard short-term window). A display value is smoothed as an EMA of ln RMSSD.
- `hrvState` takes these values:
  - `settling` (not enough clean data yet);
  - `ok`;
  - `active` (exercise; HRV is not a recovery marker then);
  - `noisy` (coverage < 80 % or > 5 % artefacts);
  - `irregular` (rhythm screening active).

  The UI explains why HRV is hidden instead of showing a bad number.
- Frequency-domain HRV is not computed at 100 Hz.

## 5. Activity and resting HR

- Activity is classed from heart-rate reserve and the motion index:
  - `rest`;
  - `light` (reserve > 15 % or some motion);
  - `active` (reserve > 35 %);
  - `moving` (motion index > 0.5);
  - `unknown`.
- Personal resting HR is the 10th percentile of clean minute medians. It is kept on the phone and refined continuously.

## 6. Sleep

| Model | Use | Method | LOSO on slpdb |
|---|---|---|---|
| Real-time (`KYInsight`) | "asleep" chip in live view | 30-s epochs with low HR vs resting, high RMSSD and no motion, with hysteresis | 61.7 %, κ 0.21 (coefficients not yet trained in) |
| Whole-night (`KYSleepNight`) | after syncing a 24-h recording | logistic model on 24 features: 5 epoch features, per-night robust z, context windows of 3/11/21 epochs, hour of night | **68.3 %, κ 0.33** |

The whole-night output covers:
- total sleep;
- sleep onset;
- wake after sleep onset;
- efficiency;
- awakenings;
- sleep HR and RMSSD.

The slpdb subjects have sleep apnoea, so healthy sleepers should score higher. Treat this as an estimate, not polysomnography.

## 7. Rhythm screening (raw RR, before artefact correction)

| Event | Rule |
|---|---|
| `af_pattern` | Over 60-s windows, all of: nRMSSD > 0.12, normalised Shannon entropy > 0.70, turning-point ratio 0.54–1.20, COSEn > −2.2. Episode ≥ 30 s. Features: Dash et al. 2009; COSEn: Lake & Moorman 2011 |
| `pause` | RR > 2 s with clean signal |
| `bradycardia` | < 40 bpm awake / < 35 asleep, sustained |
| `tachycardia_rest` | > 100 bpm at rest, sustained |
| `very_high_hr` | > 150 bpm for 30 s while not exercising |
| `early_beats` | ≥ 6/min for 60 s, counted as Lipponen–Tarvainen ectopic beats on the raw clean RR series |
| `bigeminy` / `trigeminy` | every 2nd / 3rd RR short (< 85 % of median) for ≥ 4 consecutive cycles |
| `poor_signal` | long stretch of non-clean windows |

AF thresholds were calibrated on the afdb train split and tested on 7 held-out records:

| | Se | Sp | False-positive windows on nsrdb (96 h) |
|---|---|---|---|
| Calibrated (in use) | 96.8 % | 86.7 % | 7.0 % |
| Literature defaults | 98.8 % | 80.1 % | 9.3 % |

Single-lead 100 Hz screening has real false positives. Every event shows the disclaimer and links to the ECG for a clinician.

## 8. Still to do

- Noise-monitor threshold calibration on nstdb (Se/+P at 12/6/0 dB).
- Early-beat validation against mitdb V/A labels.
- Training the real-time sleep coefficients in.
- Validation on our own therapy captures, which is the goal of the capture programme (`docs/devices/THERAPY_CAPTURE.md`).
