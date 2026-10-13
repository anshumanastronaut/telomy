# Wellness scores from the ECG band

Recovery, Sleep, Strain, Stress, overnight vitals and heart fitness are all computed **on the phone** from the KY-E-B1 band, so they work offline.
- Code: `mobile/src/lib/wellness.ts` (scores), `mobile/modules/ky-ecg/ios/Core/KYNightMetrics.swift` (overnight metrics) and `KYSleepNight.swift` (sleep/wake).
- UI: `mobile/src/ui/wellness.tsx` and `app/wellness/[metric].tsx`.
- Everything is a wellness estimate, not a diagnosis.

## What leading wearables show, and what we can compute

| Feature | Ultrahuman | WHOOP | Oura | Apple (2026) | Garmin | Telomy band |
|---|---|---|---|---|---|---|
| Recovery / readiness | Recovery score | Recovery % | Readiness | Readiness 0–10 | Body Battery | **Recovery 0–100 + guidance** |
| Sleep score + contributors | Sleep index | Sleep performance | Sleep score | Sleep score | Sleep score | **Sleep score, 8 contributors** |
| Sleep stages | yes (PPG + motion + temp) | yes | yes | yes | yes | Asleep/awake only (ECG-only, no motion) |
| Overnight HRV / lowest HR and timing | yes | yes | yes ("recovery index") | yes (Vitals) | yes | **yes** |
| Breathing rate | – | yes | yes | yes (Vitals) | yes | **yes (ECG-derived)** |
| Strain / load | Movement index | Strain 0–21 | Activity | Activity rings | Training load | **Strain 0–21 (TRIMP), HR zones** |
| Stress | Stress rhythm | Stress monitor | Daytime stress | – | Stress 0–100 | **Stress rhythm + score** |
| VO₂max | yes | – | Cardio capacity | Cardio fitness | VO₂max | **Estimate (Uth 2004)** |
| Rhythm screening | AFib detection | – | – | AFib, ECG app | ECG app | **AF pattern, pauses, ectopy** |
| Skin temperature, SpO₂, steps | yes | yes | yes | yes | yes | **no sensor on this band** |

Recovery formulas are proprietary everywhere (WHOOP, Oura and Apple publish inputs, not weights). Ours are below, with sources.

## Overnight metrics (`KYNightMetrics`)

| Metric | Method |
|---|---|
| Sleep/wake per 30 s, total sleep, efficiency, latency, WASO, wake-ups | Whole-night logistic model on HR/HRV features (`KYSleepNight`). Leave-one-subject-out on PhysioNet slpdb: 68 % agreement, κ 0.33 |
| Lowest HR and when | Minimum 5-min mean HR asleep. Position in the night: early is better (Oura's "recovery index" idea) |
| HR drop | Pre-sleep (20 min in bed, awake) vs mean HR asleep. Nocturnal dipping of 10 % or more is typical |
| Overnight HRV | RMSSD per 5 min of clean, artefact-corrected beats (Task Force 1996). Median asleep, and median in the last third of the night |
| Breathing rate | ECG-derived respiration (Charlton et al. 2016). Per 64-s window, two series (RR intervals, R amplitude) at 4 Hz with an 8-s detrend and a Welch peak in 0.16–0.5 Hz; "smart fusion" accepts the window when both agree within 4 br/min (Karlen et al. 2013). Against the respiration belt on 10 slpdb nights: **MAE 1.4 br/min, 85 % of windows within 2**. Shown only when ≥ 30 % of sleep windows agree. Apnoea nights are unreliable. Rates under 9.6 br/min are out of range |

## Scores (`wellness.ts`)

**Sleep score (0–100).** A weighted mean of contributors, each 0–100; weights are renormalised when a contributor is missing.

| Contributor | Weight | Reference points |
|---|---|---|
| Total sleep | 30 % | 7–9 h → 100 (Hirshkowitz 2015) |
| Efficiency | 15 % | ≥ 90 % → 100, 85 % → 75 (Ohayon 2017) |
| Time to fall asleep | 10 % | ≤ 15 min → 100 (Ohayon 2017) |
| Awake after falling asleep | 10 % | ≤ 20 min → 100 (Ohayon 2017) |
| Wake-ups | 5 % | ≤ 2 → 100 |
| Restoration | 15 % | overnight ln RMSSD vs own last 30 nights; needs 3 |
| HR drop | 10 % | ≥ 15 % → 100, 10 % → 70 |
| Regular timing | 5 % | SD of sleep midpoint over 7 nights ≤ 30 min → 100 (proxy for SRI, Phillips 2017) |

**Recovery (0–100).**
- **Inputs:** z-scores against the previous ≤ 30 nights:
  - HRV, ln RMSSD (Plews 2013; Buchheit 2014): 45 %;
  - lowest HR, inverted: 25 %;
  - breathing rate, penalised only when above normal: 10 %;
  - sleep score: 15 %;
  - yesterday's load above the weekly mean: 5 %.
- **Formula:** recovery = 100 / (1 + e^−(0.4 + 1.1 z)), so a normal day ≈ 60.
- **Bands:** green ≥ 67, amber 34–66, red ≤ 33.
- **Guidance:** ≥ 80 Go for it · 67–79 Ready · 34–66 Pace yourself · ≤ 33 Recover (same as the colour bands).
- **Before 3 nights exist**, the comparison is with healthy-adult references (RMSSD 42 ± 15 ms, Nunan 2010; RHR 60 ± 8) and the app says "Learning your normal".

**Strain (0–21).**
- Edwards TRIMP: minutes in 50–60 … 90–100 % of HRmax are weighted 1–5. HRmax = 208 − 0.7 × age (Tanaka 2001).
- Strain = 4 ln(1 + TRIMP / 6). This is Telomy's own log mapping; WHOOP's 0–21 scale is proprietary.

**Stress (0–100).** Uses awake, non-exercise, good-signal minutes only.
- **Stress minute:** HR ≥ resting + 10 and RMSSD below the person's 25th percentile of calm-minute RMSSD.
- **Calm minute:** HR ≤ resting + 5 and RMSSD at or above their median.
- Score = 100 × stress minutes / classified minutes, after at least 30 minutes. Firstbeat-style HRV stress/recovery classification (Firstbeat 2014; Kim 2018 meta-analysis).

**VO₂max estimate.**
- 15.3 × HRmax / HRrest (Uth et al. 2004, about ±5 ml/kg/min).
- HRrest is the personal resting HR: the 10th percentile of calm awake minutes.

## Data

- **Nights:** Overnight-sleep captures (`Documents/therapy-sessions`). Old nights are re-analysed once automatically when new night metrics are added.
- **Day minutes:** `Documents/wellness/minutes/<date>.jsonl`, one line per minute with HR, RMSSD, quality, activity, sleep, motion and resting HR. The same summary is uploaded to `/band/minutes` when the server is reachable.
- **Profile:** last known age in `Documents/wellness/profile`.

## Sources

- Plews DJ, Laursen PB, Stanley J, Kilding AE, Buchheit M. Training adaptation and heart rate variability in elite endurance athletes. *Sports Med* 2013.
- Buchheit M. Monitoring training status with HR measures. *Front Physiol* 2014.
- Nunan D, Sandercock GRH, Brodie DA. A quantitative systematic review of normal values for short-term HRV. *PACE* 2010.
- Hirshkowitz M et al. National Sleep Foundation's sleep time duration recommendations. *Sleep Health* 2015.
- Ohayon M et al. National Sleep Foundation's sleep quality recommendations. *Sleep Health* 2017.
- Phillips AJK et al. Irregular sleep/wake patterns are associated with poorer academic performance. *Sci Rep* 2017.
- Charlton PH et al. An assessment of algorithms to estimate respiratory rate from the ECG and PPG. *Physiol Meas* 2016.
- Karlen W et al. Multiparameter respiratory rate estimation from the photoplethysmogram. *IEEE TBME* 2013.
- Edwards S. *The Heart Rate Monitor Book*, 1993. Banister EW, 1991.
- Tanaka H, Monahan KD, Seals DR. Age-predicted maximal heart rate revisited. *JACC* 2001.
- Uth N et al. Estimation of VO₂max from the ratio between HRmax and HRrest. *Eur J Appl Physiol* 2004.
- Firstbeat Technologies. Stress and recovery analysis method based on 24-hour HRV. White paper, 2014.
- Kim HG et al. Stress and heart rate variability: a meta-analysis. *Psychiatry Investig* 2018.
- Task Force of the ESC and NASPE. Heart rate variability: standards of measurement. *Circulation* 1996.
- Product references (inputs only): [WHOOP Recovery](https://support.whoop.com/s/article/WHOOP-Recovery?language=en_US), [Oura Readiness](https://ouraring.com/blog/readiness-score/), [Apple Vitals](https://support.apple.com/en-us/120142), [Ultrahuman how it works](https://www.ultrahuman.com/us/how-it-works/), [Garmin Body Battery / Firstbeat](https://www.firstbeat.com/en/science-and-physiology/white-papers-and-publications/).
