# ml/: how the on-phone models are trained and validated

This folder is code only.
- Datasets are downloaded by the scripts and are **never committed**.
- Personal recordings, logs and the vendor SDK stay outside the repo.
- The training workspace on the dev Mac is `~/telomy-lab/` (same sub-folders).

## Models shipped in the app (`mobile/modules/ky-ecg/ios/Resources/`)

| Model | Swift | Train / export | Data (licence) | Result |
|---|---|---|---|---|
| Sleep stages, Wake/Light/Deep/REM (`sleep_stager.json`) | `Core/KYSleepStager.swift` | `sleepstage/dl_hmc.py` → `train_seq.py 25` | [HMC](https://physionet.org/content/hmc-sleep-staging/1.1/), 151 nights (CC BY 4.0) | CV κ 0.51; slpdb external κ 0.36 |
| Rhythm, Normal/AF/Other/Noisy (`rhythm_model.json`) | `Core/KYRhythmModel.swift` | `af2017/prep.py` → `train_af.py` → `final_af.py` (long windows) → `domain_export.py` | [CinC 2017](https://physionet.org/content/challenge-2017/) (ODC-By) + afdb/nsrdb windows | held-out AF Se 0.80, Sp 0.993, false alarms 0.02 % |

Full methods and validation tables are in `docs/devices/SLEEP_AND_RHYTHM_MODELS.md`, `KY_E_B1_ALGORITHMS.md` and `WELLNESS_SCORES.md`.

## Folders

- `kyval/`: Swift command-line tool that runs the **phone's exact pipeline** (`KYAnalyzer` + `KYInsight` + stager + rhythm model) on a 100 Hz int16 recording.
  - The package symlinks `mobile/modules/ky-ecg/ios/Core/*.swift`.
  - Usage: `kyval in.bin out.json [restingHR]`.
  - `KY_STAGE=model.json` adds sleep staging; `KY_RHYTHM=model.json` adds 60-s rhythm windows.
- `validate/`: PhysioNet beat-detection scoring, AF calibration, sleep/wake training and noise-stress records.
  - `prep.py` downloads from the AWS mirror and converts to 100 Hz.
  - `edr/edr_proto.py` validates ECG-derived breathing against the respiration belt on slpdb.
- `sleepstage/`: HMC download (ECG channel only), 19 features (`features.py`), the numpy baselines (`train.py`) and the PyTorch Conv1d + BiGRU (`train_seq.py`).
- `af2017/`: CinC 2017 preparation, 20/21-feature extraction (`train_af.py`), model comparison, the domain-adaptation study (`domain_af.py`) and the shipped export (`domain_export.py`).
- `sinc-eval/`: PubMedQA (MIT) accuracy harness for Sinc. It needs `ANTHROPIC_API_KEY` in `backend/.env`; in retrieval mode it exits.
- `mirofish/`: simulated market test with [MiroFish-Offline](https://github.com/nikmcfly/MiroFish-Offline) (AGPL-3.0, run locally, not shipped).
  - Contents: the product brief, a panel of 150 **fictional** personas, the end-to-end driver, and a compose file (Ollama runs natively on the Mac).

## Every Swift port is checked against Python before shipping

| Port | Check |
|---|---|
| Sleep stager | 99.8 % epoch agreement, probability difference ≤ 0.008 (float64 vs float32) |
| Rhythm model | feature difference ≤ 6e-6, 100 % decision agreement |
| Night metrics, breathing rate | `kyval` outputs compared with the Python prototypes |

## Environment

- Python venv with `numpy scipy wfdb pandas<3 scikit-learn torch` (`~/telomy-app/.venv-tools`).
- Swift 6 toolchain (Xcode 26).
- PhysioNet data comes from `https://physionet-open.s3.amazonaws.com/` (physionet.org itself is slow).
