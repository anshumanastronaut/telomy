# Therapy capture: recording sessions for research

Therapy capture records a full ECG session around a therapy (sauna, cold plunge, PEMF, red light, and so on) on the iPhone.
- It works **offline**: no server or internet needed.
- Each session can be shared as one file for the data/ML team.

## Running a session (on the phone)

1. Put on the band and open Telomy.
   - Home or Therapy → **Record therapy** (or `telomy://capture`).
   - Wait for live HR.
2. Pick the therapy and enter the machine settings: temperature, duration, wavelength, pressure, and so on.
   - HBOT is blocked: the band's manual forbids oxygen-rich or pressurised use.
   - Cold plunge and float show a water warning. Cryo has a frostbite caution.
3. Rate **energy, calm, pain, sleepiness** (0–10) before the session.
4. **Start**. The session begins in **baseline**.
   - Sit still for 5 minutes. A 5-min baseline gives the standard short-term HRV.
5. Tap **Therapy** when it starts and **Recovery** when it ends. Record at least 10 minutes of recovery.
   - Add **markers** at any time (e.g. "entered plunge", "felt dizzy").
6. **Stop & save**, then fill in the post ratings and notes.
7. **Saved sessions** gives three actions per session:
   - **Share** (AirDrop, Files, mail or Drive): one `.telomy.json` file;
   - **Upload** to the Telomy server, if reachable (`POST /band/captures`);
   - **Delete**.

Tips:
- Wet the electrodes.
- Keep the phone within ~5 m.
- Don't let the app get killed during a session. It keeps running with the screen locked (Bluetooth background mode).

## File format `telomy.capture/1`

One JSON file, `<id>.telomy.json`, where id is `YYYYMMDD-HHMMSS-<therapy>`:

```jsonc
{
  "format": "telomy.capture/1",
  "meta": {
    "id": "20261012-191500-finnish_sauna", "therapy": "Finnish sauna", "therapyId": "sauna",
    "settings": {"temperature_c": "85", "planned_min": "15", "humidity_pct": "10"},   // as typed, strings
    "pre":  {"energy": 5, "calm": 4, "pain": 2, "sleepiness": 3},             // 0–10
    "post": {"energy": 7, "calm": 8, "pain": 1, "sleepiness": 5},
    "notes": "…",
    "phases": [{"phase": "baseline", "t": 1791815000.1},
               {"phase": "therapy",  "t": 1791815300.4},
               {"phase": "marker",   "t": 1791815400.0, "note": "poured water"},
               {"phase": "recovery", "t": 1791816200.9}],
    "startedAt": 1791815000.1, "endedAt": 1791817000.0, "durationSec": 1999.6,
    "ecgStartUnix": 1791815001.0, "samples": 199960, "tz": "Asia/Kolkata",
    "device": {"name": "…", "hardware": "B1_V1.1", "firmware": "B1_1.00.39_250728"},
    "app": {"analysis": "KYAnalyzer/KYInsight", "fs": 100},
    "summary": {"beats": 2900, "droppedFrames": 0, "restingHr": 62, "rmssd300End": 31.2, "events": [...]}
  },
  "ecg": {"fs": 100, "unit": "uV", "dtype": "int16le", "encoding": "base64", "data": "…"},
  "beats_csv": "t_unix,rr_ms,amplitude_uv\n…",
  "metrics": [ { "t": …, "hr": …, … }, … ],   // about 1 per second
  "events":  [ { "type": "af_pattern", "start": …, "end": …, "detail": {…} }, … ]
}
```

All times are **unix seconds**. The ECG may have gaps (band out of range, app relaunched by iOS). `meta.segments` is
`[{sample, unix}, …]`, and sample *i* belongs to the last segment with `sample ≤ i`, at `unix + (i − sample) / 100`.
The reader script handles this. `meta.resumes` counts relaunches, and `wallSec` vs `durationSec` gives wall time vs recorded ECG.

**Overnight sleep** is a capture type of its own:
- Its phases are In bed, Lights out and Awake, stored as baseline / therapy / recovery.
- It records the **live stream only**. With firmware B1_1.00.39, the band's on-board memory recording stored little or nothing when mixed with live streaming (dry runs 2026-10-12/13), so it is not used.
- On stop, `summary.sleep` holds the whole-night estimate: total sleep, efficiency, WASO, awakenings, sleeping HR and HRV, and a hypnogram per 30-s epoch.

**Re-analyse** (Saved sessions) re-runs the current algorithms over a session's raw ECG on the phone:
- each gap-free segment is analysed separately;
- `beats.csv`, the summary and the bundle are rewritten;
- the original live beats are kept as `beats-live.csv`;
- `meta.analysis.version` records which algorithms produced the numbers.
The ECG is the raw band signal, unfiltered, so any pipeline can be re-run on it. Size is about 0.7 MB per 10 min.

### `metrics` fields (computed live on the phone)

| Field | Meaning |
|---|---|
| `hr` | Adaptive (Kalman) heart rate, bpm. **Use this.** |
| `hrSd`, `hrConfidence` | Uncertainty of `hr` (bpm), and 0–1 confidence |
| `hr10` | Plain 10-s artefact-corrected mean HR (reference) |
| `rmssdSmooth` | Smoothed RMSSD (ms). Valid when `hrvState == "ok"` |
| `rmssd60`, `rmssd300`, `rmssd5`, `sdnn60`, `sdnn300`, `meanNN60`, `pnn50` | Task Force time-domain HRV over 60 s / 5 min (absent when not enough clean data) |
| `hrvState` | `ok`, `settling`, `active`, `noisy` or `irregular` |
| `quality` | `good`, `acceptable`, `poor`, `no_contact` or `warming_up` (10-s SQI gate) |
| `sqi` | bSQI, kSQI, pSQI, basSQI |
| `signal` | Current 2-s window: `clean`, `noisy`, `motion`, `no_contact`, `flat` or `saturated` |
| `motionIndex` | 0–1 share of non-clean windows over ~30 s |
| `activity`, `sleep` | `rest`/`light`/`active`/`moving`/`unknown`; `awake`/`asleep`/`unknown` |
| `restingHr` | Personal resting HR learned on this phone |
| `earlyBeatsPerMin`, `afBurden60`, `irregularBeats60`, `openEvents` | Rhythm screening state |
| `artefactPercent`, `droppedFrames`, `beats` | Data-quality counters |

Algorithms and validation are in [KY_E_B1_ALGORITHMS.md](KY_E_B1_ALGORITHMS.md).

## Reading the files

```bash
python scripts/capture/read_capture.py sessions/*.telomy.json             # per-phase HR / RMSSD summary
python scripts/capture/read_capture.py sessions/*.telomy.json --csv out/  # ecg.csv, beats.csv, metrics.csv, phases.csv, meta.json
```

Each row in the CSVs is labelled with its phase.

## Guidance for analysis

- Compare **recovery vs baseline** within a person. Absolute HRV varies a lot between people.
- Use ln RMSSD over ≥ 2–5 min windows with `hrvState == "ok"`.
- Drop windows with `signal` ≠ `clean` for anything beyond HR.
- Heat and cold change electrode contact and add muscle noise. Check `quality` and `motionIndex` per phase before drawing conclusions.
- Rhythm `events` are screening flags from a single-lead 100 Hz wearable. They are not diagnoses.

## Privacy

These files are **personal health data**:
- Get written consent from each participant.
- Share them only with the research team, through a private channel.
- Pseudonymise file names before pooling.
- Never commit them to git.
