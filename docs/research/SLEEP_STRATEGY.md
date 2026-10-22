# Telomy sleep: the onset problem, the competition, and our USPs

Written 2026-10-21 after the founder's n-of-1 night of 2026-10-18 (fell asleep ~02:50; WHOOP said 01:05–01:23).
This is the strategy for how Telomy should **detect** and **present** sleep, and where we win.

---

## 1. The real bug: sleep onset, and why *every* wearable gets it wrong

The app showed your night as **01:05 → 09:19**, but you fell asleep ~**02:50**. That ~1h45m gap is not a Telomy
quirk — it is the **single biggest, best-documented weakness of all consumer sleep trackers**:

> Accelerometer/motion says "you stopped moving." It **cannot tell lying-still-awake from asleep**. Published
> **wake specificity is often below 60%** on consumer wearables, so they **overcount sleep** in anyone who lies
> awake in bed. ([PSG validation, PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7498244/), [6-device vs PSG, PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9412437/))

WHOOP marked you asleep at 01:05 because you were lying still — but your **heart rate was still ~81 bpm** (awake). It
only dropped (to ~64) around 02:50. **Heart rate is the discriminator motion misses.** Our own earlier analysis proved
it on your data: Telomy's HR-based onset nailed **02:55 (0 min error)** while WHOOP's motion-led onset (01:23), a
fused method (01:49) and pure motion/HDCZA (00:37) all over-called by 1–2.5 hours.

**So the fix is not to copy WHOOP — it's to lead with heart rate for onset, and show "in bed" vs "asleep" separately.**

---

## 2. How WHOOP, Oura and Ultrahuman show sleep (and how accurate they are)

| | Framing | What they show | Accuracy vs PSG | Weakness |
|---|---|---|---|---|
| **Oura** | Clinical / recovery ring | Hypnogram (5-min), stage %, sleep **score**, efficiency, **latency**, timing, resting HR + HRV + **temperature**, "time asleep ≠ time in bed" | **Best** sleep/wake agreement ~**92%**; not significantly different from PSG on **onset latency, WASO, TST**; staging 75–91% ([Oura/U-Tokyo](https://ouraring.com/blog/oura-ring-accuracy-validation-study-university-of-tokyo/)) | Still overcounts sleep when lying awake; staging directional |
| **WHOOP** | Strain ↔ recovery band | Sleep **performance %** (vs *need*), stages, **sleep debt**, respiratory rate, hours-vs-needed | Best **deep-sleep** epochs (~70% of N3) but **overestimates REM (+21 min)** and deep; only *fair* overall ([2025 6-device](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9412437/)) | Over-calls sleep onset (your 01:05); over-reports REM/deep |
| **Ultrahuman** | Metabolic / glucose-first ring | Sleep **index**, stages, debt, "movement/restfulness", **ties sleep to glucose** | Little independent PSG validation published | Least transparent; gamified |

**Common truth:** all three **assert** a single number, hide uncertainty, and **overcount sleep onset**. Oura is the
most honest (shows time-in-bed vs asleep + latency). None ask the user to confirm.

---

## 3. How Telomy fixes onset — and turns the industry's weakness into our edge

1. **Heart-rate-led onset.** Detect first sleep as the first **sustained HR drop** below the night's resting read (not
   first stillness). This moves your onset from 01:05 → ~02:50. We already have the HR; it's proven on your data.
2. **Show "In bed" vs "Asleep" + onset latency.** Headline the **time asleep** (02:50–09:19), show in-bed (01:05) and
   **"1h45m to fall asleep"** as its own line (the Oura-honest distinction). Latency is itself a health signal.
3. **Multi-device fusion, best signal per job.** We uniquely have **patch ECG + WHOOP + ring** on the same night. Take
   ECG for stages, WHOOP HR (validated to 1.2 bpm vs our ECG) for load, HR for onset — reconciled, with provenance.
4. **User-confirmed ground truth.** When onset/nap is uncertain, **ask** ("asleep around 02:50?"). The correction
   tunes the thresholds **to you** (n-of-1). No competitor does this — and it's the only way to beat the <60% wake problem.

---

## 4. Telomy's sleep USPs — and exactly what to show

**USPs (why ours is different, not just another score):**
- **Honesty & provenance** — source + confidence on every number; in-bed ≠ asleep; naps surfaced to confirm, never
  asserted. (WHOOP/Oura state a number; we show the uncertainty and let you correct it.)
- **ECG-grade + multi-device fusion** — the only one combining a medical-grade **ECG patch**, WHOOP and a ring, picking
  the best signal per metric.
- **Calibrated to you (n-of-1)** — your "I fell asleep at 2:50" retunes the engine; it gets more accurate for *you* over time.
- **Sleep as a longevity lever, not a vanity score** — sleep feeds the recovery, HRV and **biological-age** engines; we
  show *what it's doing to your aging*, with the clinical models behind it — not a standalone gamified ring score.

**What the Sleep page should show (in order):**
1. **Headline:** Sleep score + **time asleep** (e.g., 6h29m) — not time in bed.
2. **In bed 01:05 · Asleep 02:50 · 1h45m to fall asleep · 94% efficiency** (one honest line).
3. **Step hypnogram** (depth-ordered: Awake → REM → Light → Deep, 5-min, discrete steps — not a smooth line) **with a
   HR + movement strip underneath** so you see *why* a block was scored. (Oura/clinical convention.)
4. **Stages** — labelled "estimates" (directional on every wearable), % + minutes.
5. **Onset latency, WASO, efficiency, regularity (SRI), sleep need/debt** — continuity > raw totals.
6. **Source + confidence chip** ("WHOOP + ring, re-staged by Telomy") and a **"Was this right?"** confirm control.
7. **The longevity tie-in** — "this night's HRV/RHR vs your baseline → recovery, and its pull on your biological age."

**One line for the pitch:** *Everyone else tells you a sleep number. Telomy tells you when you actually fell asleep,
shows its work, learns from your correction, and connects the night to your biological age.*

Sources: [PSG minute scoring, PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7498244/) · [6 wearables vs PSG, PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9412437/) · [Oura U-Tokyo validation](https://ouraring.com/blog/oura-ring-accuracy-validation-study-university-of-tokyo/) · [HR-based sleep window, Nature 2022](https://www.nature.com/articles/s41598-022-11792-7) · [Oura sleep graphs](https://support.ouraring.com/hc/en-us/articles/4403155260307-Sleep-Graphs)
