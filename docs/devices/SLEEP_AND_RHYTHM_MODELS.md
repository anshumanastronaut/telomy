# Trained models on the phone: sleep stages and rhythm

Both models run **on the iPhone**, offline. Their weights are bundled in `KyEcgModels.bundle`.

The training code is in `~/telomy-lab` (outside the repo):
- `sleepstage/`: download, features, training;
- `af2017/`: data preparation, features, training, export.

Every Swift port was checked against Python on real recordings. These are wellness and screening estimates, not a diagnosis.

## Sleep stages: Wake · Light · Deep · REM (`Core/KYSleepStager.swift`)

**Data.** [HMC sleep staging database](https://physionet.org/content/hmc-sleep-staging/1.1/) (PhysioNet, CC BY 4.0): 151 hospital sleep-lab nights with expert 30-s scoring. Only the ECG channel is used, resampled to 100 Hz, through the Telomy beat detector, exactly as the band's data is processed.

**Features.** 19 per epoch:
- HR, 5-min HR and its slope;
- RMSSD (30 s and 5 min), SDNN, pNN50;
- VLF/LF/HF power, LF/HF, HF peak;
- DFA α1;
- ECG-derived respiration: amplitude, rate, rate regularity;
- RR coefficient of variation, artefact fraction;
- position in the night.

All features are robust-normalised per night (median / IQR).

**Model.** Conv1d(19→32, k = 5) → bidirectional GRU(32) → linear(4), about 15 k parameters, run over the whole night. The approach follows Sridhar et al. 2020 and Radha et al. 2019.

**Validation**

| | κ | Accuracy | Deep / REM minutes error per night |
|---|---|---|---|
| HMC, 5-fold subject-wise cross-validation, 151 nights | **0.51** | 0.66 | – |
| PhysioNet slpdb (external, sleep-apnoea patients) | 0.36 | 0.59 | 41 / 24 min |
| Published ECG-only state of the art, > 10 k nights (Sridhar 2020) | 0.66 | 0.77 | – |

For comparison, before the sequence model a per-epoch softmax gave κ 0.32, and the BiGRU on 31 nights gave κ 0.45.

**Swift port vs PyTorch.** Stages agree on 99.8 % of epochs and probabilities differ by at most 0.008. Swift runs in float64, PyTorch in float32. A 7-hour night takes about 0.4 s on a Mac.

**Outputs.** Stages per epoch, light/deep/REM minutes and %, REM latency, sleep cycles, plus total sleep, efficiency, WASO and awakenings. The sleep score gains Deep and REM contributors, with typical ranges from Ohayon 2004.

## Rhythm: Normal · AF · Other · Noisy (`Core/KYRhythmModel.swift`)

**Data.**
- [PhysioNet CinC 2017](https://physionet.org/content/challenge-2017/): 8,528 single-lead ECGs (5,076 N, 758 AF, 2,415 other, 279 noisy).
- 60-s windows from PhysioNet afdb and nsrdb training records (Holter-like, continuous data).

All at 100 Hz through the Telomy beat detector.

**Features.** 20 per 60-s window:
- RR irregularity: CV, nRMSSD, pNN50/20, normalised Shannon entropy, turning-point ratio, COSEn, SD1/SD2, irregular fraction, MAD/range/min/max ratios;
- P-wave consistency and amplitude;
- R-amplitude CV, beat coverage, high-frequency noise, flat fraction.

Beat count was dropped because it depends on the window length.

**Model.** Gradient-boosted trees (≤ 15 leaves, early-stopped at 47 rounds × 4 classes). An AF flag needs P(AF) > 0.63 in **two consecutive windows** (60 s, step 30 s). The previous threshold rule stays as a fallback.

**Validation** (on 60-s windows of held-out afdb / nsrdb records)

| | AF sensitivity | AF specificity | False-alarm windows, 24-h normal recordings |
|---|---|---|---|
| Previous rule | 0.67 | 0.983 | 11.4 % |
| CinC-only model | 0.88 | 0.977 | 10.2 % |
| **Shipped model** (CinC + long-record windows, 2-window confirmation) | **0.80** | **0.993** | **0.02 %** |
| CinC 2017 5-fold CV, 4 classes | challenge F1 0.78 (winners 0.83 at 300 Hz) | | |

**Swift port vs Python.** Over 400 windows the largest feature difference is 6e-6, and the AF decision agrees 100 %.

Two sessions built this in parallel on 2026-10-14. The shipped files are the shared loader/feature format (`KYRhythmModel.swift`) with the domain-adapted weights from `telomy-lab/af2017/domain_export.py`.
