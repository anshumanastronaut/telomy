# Telomy hardware: sensors & features for the patch, band and ring

Deep research, 2026-10-21. What to put on each device, graded by **real-world validation** (ship-now vs emerging vs
avoid), benchmarked against the world's best-validated wearables. The guiding rule: **a sensor is only as good as the
engine behind it, and only worth shipping if it's validated. Match each sensor to the body location that validates it,
fuse across the three, and integrate gold-standard externals (CGM) rather than faking them.**

---

## 0. Principles (why this matters commercially)

- **Validation is the moat.** Oura has deep peer-reviewed PSG/ECG validation; Samsung, Ultrahuman, RingConn have
  "much less independently published data." ([validation comparison](https://www.sensai.fit/blog/oura-vs-galaxy-ring-vs-ultrahuman-ring-2026)) Telomy's claim to be *clinical* only holds if every number is validated.
- **Placement decides accuracy.** ECG wants the chest; PPG/SpO₂/temperature want the finger; EDA/activity want the wrist.
  Don't put a sensor where it can't be trusted (e.g. SpO₂ on a chest patch).
- **Our real differentiator is the patch's true ECG.** Consumer rings/bands only do PPG or a finger-touch spot ECG.
  A continuous **medical-grade ECG patch** is a category most "wellness" players can't match — lead into it.
- **Trend vs clinical.** SpO₂ and skin temperature from rings/bands are **trend indicators** (finger position, cold
  hands, skin tone), *not* oximeter/thermometer readings. ([smart-ring review](https://acibademinternational.com/blog/smart-rings-compared-galaxy-ring-ultrahuman-and-oura-what-they-measure-well/)) Label them honestly.

---

## 1. The PATCH (chest/torso) — our medical-grade anchor

Today: ECG + HRV (+ some respiration). The chest is the **only** consumer location that gives true ECG and chest-wall
respiration, so this is where we can be genuinely clinical. The gold reference is **VitalConnect VitalPatch** (FDA) and
**iRhythm Zio** (FDA, 14-day).

| Sensor | Enables | Validation benchmark | Priority |
|---|---|---|---|
| **Multi-/single-lead ECG** (have) | Continuous **AFib/arrhythmia**, true beat-to-beat **HRV**, QT/HR | Zio FDA-cleared AI (K222389); patches "high accuracy, no signal degradation over time" ([MDPI 2025](https://www.mdpi.com/1424-8220/25/9/2848)) | **Ship — our edge** |
| **Respiratory rate** (ECG/impedance-derived) | Breathing rate, **sleep apnea** screen, stress | VitalPatch **< 3 breaths/min MAE** ([VitalConnect](https://vitalconnect.com/wp-content/uploads/2017/02/Longterm-Remote-Monitoring_HealthInnovations_2014_published.pdf)) | **Ship — add next** |
| **Skin temperature** (NTC) | Illness/fever, recovery, circadian | VitalPatch **< 1.2 °C** | **Ship — cheap, high value** |
| **3-axis accelerometer** | **Fall detection**, **posture**, activity/steps, ECG-motion gating | VitalPatch fall **>90% sens / >98% spec**, posture >70%, FP 0.0027/day | **Ship — big safety feature** |
| **Lead-off / contact impedance** | Signal-quality gating (don't show junk) | standard | Ship — quality |

**Patch feature set to build:** continuous arrhythmia/AFib flag → clinician review (not auto-diagnosis), ECG-grade HRV,
respiratory rate, **apnea/overnight breathing screen**, ECG-based sleep staging (we already do), **fall detection**,
posture, activity. This is the clinical spine the rings/bands feed into.

---

## 2. The RING (finger) — the overnight / trend device

The finger has the **best perfusion** for PPG and the best skin-temperature trend, and a ring is the only thing
comfortable to wear **asleep**. Benchmark: **Oura** (most validated ring).

| Sensor | Enables | Validation | Priority |
|---|---|---|---|
| **PPG (red + IR + green)** | Resting **HR**, **HRV**, overnight SpO₂ **trend** | Oura **RHR MAPE 1.94%, HRV 5.96%** ([study](https://www.sensai.fit/blog/oura-vs-galaxy-ring-vs-ultrahuman-ring-2026)); SpO₂ = trend only | **Ship** |
| **Skin temperature** (NTC) | **Illness onset, menstrual cycle, personal baseline deviation** — Oura's killer feature | Oura validated for cycle/fever *trends* | **Ship — differentiator for a ring** |
| **3-axis accelerometer** | Sleep/wake motion, movement index, HR-onset gating | standard | **Ship** |
| Red/IR for SpO₂ dips | Overnight desaturation **trend** (apnea hint) | trend, not clinical | Ship (labelled trend) |

**Ring feature set:** best-in-class **sleep** (comfort + HR for onset — see SLEEP_STRATEGY.md), resting HR/HRV,
**temperature-baseline** alerts (illness/cycle), overnight SpO₂ trend. Keep SpO₂/temp framed as *trends vs your
baseline*, never as a medical reading.

---

## 3. The BAND (wrist) — the all-day sensor hub

The wrist trades PPG quality for **all-day wear + more real estate** (gyro, EDA electrodes, BIA, a touch-ECG pad).
Benchmarks: **WHOOP** (PPG HR validated to ~1.2 bpm vs ECG), **Apple Watch** (FDA ECG + fall/crash), **Fitbit Sense**
(EDA), **Samsung** (BIA).

| Sensor | Enables | Validation | Priority |
|---|---|---|---|
| **PPG** | All-day **HR**, strain, HRV, SpO₂ trend | WHOOP HR ~1.2 bpm vs ECG | **Ship** |
| **3-axis accel + gyro** | Workouts/auto-detect, steps, **fall + crash detection** | Apple fall/crash validated | **Ship** |
| **Single-lead ECG pad** (finger-touch) | On-demand **AFib spot-check** | Apple/Samsung FDA-cleared | **Ship — complements the patch** |
| **Skin temperature** | Illness/recovery trend | trend | Ship |
| **EDA / electrodermal (cEDA)** | **Stress / arousal** (sweat-gland activity) — a real, under-served signal | Fitbit Sense (consumer), Empatica (research-grade) | **Ship — distinctive, pairs with voice stress** |
| **Bioimpedance (BIA)** | **Body composition** (fat/muscle/water) → feeds the muscle-age clock | Samsung hand-to-hand; directional | **Phase 2** |
| **Cuffless BP** (PPG/PTT) | BP trend | ⚠️ **No cuffless device has clinical-grade accuracy; societies don't recommend them** ([Hypertension Research 2025](https://www.nature.com/articles/s41440-025-02410-w)); needs per-user calibration | **Research-only, heavy caveats** |
| **Non-invasive glucose** | Glucose | ⚠️ **Not real yet** — only manufacturer press-release claims (~10.8% MARD, no peer review) | **Do NOT build — integrate CGM instead** |

**Band feature set:** all-day HR/strain/recovery, workouts, **fall/crash safety**, **EDA stress** (unique, pairs with
our voice-tonality engine), touch-ECG AFib check, skin temp. BIA body-comp in Phase 2.

---

## 4. Don't build these — integrate the gold standard instead

- **Glucose** → integrate **Dexcom / Abbott Libre CGM** (we already have the Nightscout receiver). Non-invasive glucose
  is unvalidated; building it would wreck our clinical credibility.
- **Blood pressure** → a validated **cuff** (Omron/withings BPM) over Bluetooth beats any cuffless wrist estimate.
- **Blood labs** → the lab-report pipeline (already shipped). Don't chase a "blood from skin" sensor.

---

## 5. The unified picture — one body, three sensors, best signal per job

| Signal | Best source | Why |
|---|---|---|
| Heart rhythm / AFib / true HRV | **Patch ECG** | only medical-grade source |
| Respiration / apnea | **Patch** (ECG/impedance) | chest wall |
| Sleep (onset, stages) | **Ring** (comfort + HR) confirmed by **Patch ECG** when worn | overnight + HR-led onset |
| Resting HR/HRV, temperature baseline | **Ring** | finger perfusion + NTC temp |
| All-day strain, workouts, steps | **Band** | all-day wrist motion |
| Stress / arousal | **Band EDA** + **voice tonality** | sweat glands + acoustics |
| Fall / crash safety | **Patch + Band** accel | validated |
| SpO₂ trend | Ring/Band (labelled trend) | not clinical anywhere |
| Body composition | **Band BIA** (P2) + DEXA upload | feeds muscle-age clock |
| Glucose, BP, blood labs | **external CGM / cuff / lab PDF** | validated gold standards |

**The Telomy edge no single-device player can claim:** a **clinical ECG patch** + an **overnight ring** + an **all-day
band**, fused into one record with provenance, each measuring what its location actually validates — then run through
engines that tie it all to **biological age** and a clinician in the loop.

Sources: [VitalPatch IFU/validation](https://vitalconnect.com/wp-content/uploads/2017/02/Longterm-Remote-Monitoring_HealthInnovations_2014_published.pdf) · [Zio/arrhythmia review (MDPI 2025)](https://www.mdpi.com/1424-8220/25/9/2848) · [smart-ring validation 2026](https://www.sensai.fit/blog/oura-vs-galaxy-ring-vs-ultrahuman-ring-2026) · [what rings measure well](https://acibademinternational.com/blog/smart-rings-compared-galaxy-ring-ultrahuman-and-oura-what-they-measure-well/) · [cuffless BP — not clinic-ready (Hypertension Research 2025)](https://www.nature.com/articles/s41440-025-02410-w) · [cuffless wrist BP validation](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7642418/)
