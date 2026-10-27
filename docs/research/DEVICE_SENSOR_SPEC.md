# Telomy Device Sensor Spec — Patch · Ring · Band

**Design constraint:** a user wears **one** device, not all three. So each device must be **standalone-complete**
— whichever one someone picks, it has to deliver a useful, defensible health picture on its own, and feed enough
features into the models to be worth wearing. This changes everything: we don't split sensors across devices to
avoid duplication; we **duplicate the baseline in all three** and then give each a *hero* capability its anatomy
is genuinely best at.

Grounding (body-site validation): chest = highest signal quality for ECG/respiration but lowest wearability;
**finger has the densest capillary bed → by far the best PPG/SpO₂ site** (ring PPG signal is far stronger than
wrist); **wrist is the activity site** (IMU) but has thick, low-perfusion tissue so its PPG/SpO₂ is weak; wrist
EDA exists but validates poorly vs palm/reference. We build to those physics, not around them.

---

## The common baseline — in ALL three devices

So that any single device covers the essentials:

- **PPG (HR)** — resting/continuous heart rate.
- **Skin temperature** (thermistor) — cycle, fever, circadian, stress.
- **3-axis accelerometer (IMU)** — activity level, sleep/wake, movement.
- **On-device flash + BLE + ~5–7 day battery** — log-then-sync, survives phone-off (the recorder proved why this
  matters).

With just the baseline, **every device can deliver: resting HR, a temperature trend, an activity/movement
profile, and a basic sleep estimate** — and feed the **lab-free chronic model** (which only needs HR, activity,
sleep, and questionnaire features). That's the floor. Now the hero per device:

---

## 1 · PATCH (chest) — the **cardiac** device

**Hero: single-lead ECG** (chest is the gold-standard ECG site). Add:

| Sensor | Delivers |
|---|---|
| **1-lead ECG** (hero) | beat-accurate HR, **ECG-grade HRV** (RMSSD/SDNN), **AFib/arrhythmia**, ectopy, QT/conduction |
| **Respiration** (ECG-derived + impedance) | respiratory rate, breathing pattern, apnea context |
| Skin temp (chest) | core-ish temperature, fever/circadian |
| IMU (accel) | posture, activity, sleep position, fall context |

**Standalone picture:** the most *clinical* of the three. Continuous ECG rhythm, the only true HRV, respiration,
and sleep staging from ECG+respiration+motion (the KYECG HSMM stager). **Best for cardiac/at-risk users.**

**Models it feeds:** AFib/arrhythmia, ECG-HRV → autonomic/stress, sleep staging, respiration, + the chronic
suite. **Honest gap:** no SpO₂ (chest reflectance PPG is poor), not a step-counter. Comfort/adhesive limits
all-day-forever wear.

---

## 2 · RING (finger) — the **sleep + metabolic** device

**Hero: finger PPG/SpO₂** (the validated oximetry site — this is where our Night-1 analysis says SpO₂ actually
works). Add:

| Sensor | Delivers |
|---|---|
| **Red+IR PPG (SpO₂)** (hero) | **blood-oxygen** (the one site that measures it well), perfusion |
| PPG (HR, HRV) | resting HR, PPG-HRV (good, not ECG-grade) |
| **Skin temp (finger)** | strong signal for **cycle/ovulation, fever, circadian** (finger temp is sensitive) |
| IMU (accel) | sleep/wake, movement |
| *Optional:* dual-electrode **spot ECG** (touch with other hand) | on-demand AFib spot-check |

**Standalone picture:** the best **sleep + SpO₂ + metabolic/cycle** device, and the most comfortable for 24/7
wear. Sleep/wake ~85% epoch accuracy is achievable (rings match or beat wrist); SpO₂ and temp are its strengths.
**Best for general-wellness, sleep, women's-health, and metabolic users.**

**Models it feeds:** SpO₂ → nocturnal-hypoxemia/apnea screen, sleep, temp → cycle/ovulation, HR/HRV → recovery,
+ chronic suite. **Honest gap:** finger IMU is a poor step-counter/activity source; no continuous ECG rhythm
(only the optional spot ECG). PWV/vascular-age needs an ECG reference it doesn't have alone.

---

## 3 · BAND (wrist) — the **activity + all-day** device

**Hero: IMU/activity** (wrist is the validated activity site) + the convenience of effortless all-day wear. Add:

| Sensor | Delivers |
|---|---|
| **6-axis IMU** (hero: accel + gyro) | **steps, exercise type, intensity, falls, gestures**, sleep/wake |
| PPG (HR) | continuous HR (wrist HR is reliable); SpO₂ **estimate only** (weak at wrist — flag it) |
| Skin temp (wrist) | temperature trend |
| **EDA/GSR** (wrist) | stress/arousal — *use with caution; wrist EDA validates weaker than palm* |
| *Optional:* dual-electrode **spot ECG** (finger-to-crown) | on-demand AFib spot-check, like Apple Watch |

**Standalone picture:** the **activity + lifestyle + convenience** device — all-day HR, the best movement/steps
data, stress via EDA+HRV, spot-ECG on demand. **Best for fitness/lifestyle users who want one effortless device.**

**Models it feeds:** activity/VO₂max-trend, fall risk, EDA/HRV → stress, spot-ECG → AFib screen, + chronic
suite. **Honest gap:** SpO₂ is unreliable at the wrist (estimate, never clinical — our data shows wrist SpO₂ is
the weakest site); EDA is noisy; no continuous ECG.

---

## Who's best at what (so we don't over-promise any single device)

| Metric | Patch | Ring | Band |
|---|:--:|:--:|:--:|
| ECG rhythm / AFib | **●● continuous** | ○ spot | ○ spot |
| HRV | **●● ECG-grade** | ● PPG | ● PPG |
| Respiration | **●●** | ○ | ○ |
| SpO₂ | ✗ | **●● best site** | ○ estimate |
| Skin temp / cycle | ● | **●● finger** | ● |
| Sleep staging | **●● ECG+resp** | ● good | ● ok |
| Steps / activity | ● | ✗ | **●● best site** |
| Stress (EDA) | — (HRV only) | — | ● wrist EDA (weak) |
| All-day comfort | ○ | **●●** | **●●** |

**●● = hero/clinical · ● = good · ○ = usable/estimate · ✗ = don't claim**

## Matching the device to the user

Because it's one device per user, **recommend by primary need, not by spec sheet:**
- **Cardiac / at-risk / arrhythmia / clinical** → **Patch** (ECG, HRV, respiration, best sleep staging).
- **Sleep / recovery / metabolic / women's health / 24-7 comfort** → **Ring** (SpO₂, temp, sleep).
- **Fitness / activity / stress / effortless lifestyle** → **Band** (steps, HR, EDA, spot-ECG).

The onboarding questionnaire should route the user to the device whose hero matches their goal — and every device,
whatever they pick, still feeds the chronic risk suite so no one is left without a health picture.

## The Telomy edge across all three
- **The spot-ECG electrode** on the ring and band (cheap to add) gives every device an AFib/arrhythmia
  capability — a differentiator no single-PPG competitor matches.
- **Per-user calibration** (the workbench) lifts each device's SpO₂/temp/HRV from "estimate" toward "clinical,"
  per site.
- **One model backend** serves all three: whichever device a user wears, its features flow into the same clocks,
  disease screen, and chronic suite — the device changes, the intelligence doesn't.
