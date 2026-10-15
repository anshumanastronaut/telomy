# Activity recognition for Telomy — what is possible, what we built, what we build next

## The honest ceiling
- No product auto-detects 60+ activities from motion alone. Apple Watch auto-detects about six workout types; WHOOP
  auto-detects a handful and asks the user to confirm the rest. Physics separates ~10–15 classes cleanly from body-worn
  motion (still, walk, brisk walk, run, cycle, stairs up/down, strength sets, swim, row, elliptical, drive).
- The TK3040 ring does **not** stream raw accelerometer data (verified 2026-10-14: no reply to the MEMS commands);
  it exposes live step/motion counters only. Ring motion therefore helps with "still vs moving", not activity type.
- "60+ types, accurate" is achieved the way every serious platform does it: **auto-detect what physics allows, accept
  named sessions from Apple Health (80+ HKWorkoutActivityType values), and measure every session's intensity with
  heart rate**, so the load is right even when the label came from the user.

## Built now (2026-10-15) — `mobile/src/lib/training.ts`, `app/training.tsx`
1. Apple Health workouts: all HKWorkoutActivityType values named, with duration, energy, distance and source device.
2. iPhone motion coprocessor (CMMotionActivityManager): walk / run / cycle ≥ 10 min auto-detected as sessions when no
   workout covers them; 7 days of history, works even when Telomy was not running.
3. Telomy patch sessions.
4. Load per session: Edwards TRIMP from patch/ring heart-rate zones when ≥ 50 % of the session has heart rate, else
   duration × a per-activity intensity factor (flagged "estimated").
5. Training status: acute (7-day) : chronic (28-day weekly mean) load ratio (Gabbett 2016), shown as guidance only
   because the ACWR's injury claims are contested (Impellizzeri et al. 2020).

## Next: Telomy's own multi-sensor model
**Inputs** (5-s windows, 50 % overlap): iPhone accelerometer + gyroscope at 50 Hz (CMMotionManager, during an
active session or a background workout), GPS speed and altitude change (CLLocation, only during a session), heart
rate and RR from the patch, ring motion counters, phone pocket/hand orientation.
**Model**: a small 1D-CNN + GRU (TFLite / Core ML, < 1 MB) on raw IMU, fused late with GPS-speed and HR features;
post-processed with an HMM over windows so a 40-minute run is not fragmented into 480 guesses.
**Training data (public)**:
| Dataset | Sensors | Activities | Why |
|---|---|---|---|
| PAMAP2 (UCI) | 3 IMUs + heart rate, 9 people | 18 (walk, run, cycle, stairs, rope jumping, Nordic walking…) | IMU **and** HR together |
| WISDM 2019 (UCI) | phone + watch accel/gyro, 51 people | 18 incl. jogging, stairs, sitting, eating, typing | phone-in-pocket placement |
| HHAR (UCI) | 8 phones, 4 watches | 6 | device heterogeneity — robustness across iPhones |
| MHEALTH (UCI) | chest/wrist/ankle IMU + ECG | 12 | ECG alongside motion |
| Capture-24 (Oxford) | wrist accel, 151 people, free-living, 24 h | 200+ labels → 10 | real-life, not lab |
| UCI HAR | phone accel/gyro | 6 | classic benchmark |
**Evaluation**: leave-subjects-out macro-F1 per class; target ≥ 0.90 on walk/run/cycle/stairs/still, ≥ 0.75 on
strength-set detection; never ship a class below 0.70. Then a 2-week personal calibration: confirmations the user
gives in the app become personal training labels (on-device fine-tuning of the last layer).
**Strength training**: rep counting from phone-on-bench or EMG band (when it ships) — research-grade; ship as
"sets detected", not exact reps, until validated.
