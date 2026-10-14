"""Convert PhysioNet records to the band format: 100 Hz, int16 µV (.bin) + annotations (.json)."""
import json, os, sys
import numpy as np, wfdb
from math import gcd
from scipy.signal import resample_poly

SRC = os.path.expanduser("~/telomy-lab/physionet")
OUT = os.path.expanduser("~/telomy-lab/validate/data")
os.makedirs(OUT, exist_ok=True)
NORMAL, VENT, SUPRA = set("NLRej"), set("VE"), set("AaJS")

def to100(x, fs):
    g = gcd(100, int(fs)); return resample_poly(x, 100 // g, int(fs) // g)

def ecg_channel(rec):
    for i, n in enumerate(rec.sig_name):
        if "ECG" in n.upper() or n.upper() in ("MLII", "V1", "V5", "II"):
            return i
    return 0

def convert(db, name, beat_ext=None, rhythm_ext=None, stage_ext=None):
    path = f"{SRC}/{db}/{name}"
    if not os.path.exists(path + ".dat"):
        return None
    rec = wfdb.rdrecord(path)
    ch = ecg_channel(rec)
    fs = rec.fs
    x = rec.p_signal[:, ch]
    x = np.nan_to_num(x) * 1000.0
    y = np.clip(np.round(to100(x, fs)), -32767, 32767).astype("<i2")
    y.tofile(f"{OUT}/{db}_{name}.bin")
    meta = {"db": db, "rec": name, "fs_orig": fs, "seconds": len(y) / 100, "channel": rec.sig_name[ch]}
    if beat_ext:
        a = wfdb.rdann(path, beat_ext)
        meta["beats"] = [[round(s * 100 / fs, 2), sym] for s, sym in zip(a.sample, a.symbol) if sym in NORMAL | VENT | SUPRA | set("Q/f")]
    if rhythm_ext:
        a = wfdb.rdann(path, rhythm_ext)
        segs, cur, start = [], None, 0.0
        for s, note in zip(a.sample, a.aux_note):
            note = note.strip("\x00 ")
            if note.startswith("("):
                if cur: segs.append([start, s / fs, cur])
                cur, start = note[1:], s / fs
        if cur: segs.append([start, len(x) / fs, cur])
        meta["rhythm"] = segs
    if stage_ext:
        a = wfdb.rdann(path, stage_ext)
        meta["stages"] = [[s / fs, (n.strip("\x00 ").split() or ["?"])[0]] for s, n in zip(a.sample, a.aux_note)]
    json.dump(meta, open(f"{OUT}/{db}_{name}.json", "w"))
    return meta

jobs = []
for r in "100 101 103 105 106 108 119 200 201 203 208 210 213 221 228 233".split(): jobs.append(("mitdb", r, "atr", "atr", None))
for r in "04015 04043 04048 04126 04746 04908 04936 05091 05121 06426 07162 07879 08215 08455".split(): jobs.append(("afdb", r, "qrs", "atr", None))
for r in "slp01a slp02a slp03 slp04 slp14 slp16 slp32 slp37 slp41 slp45".split(): jobs.append(("slpdb", r, "ecg", None, "st"))
for r in "16265 16272 16420 16483 16539".split(): jobs.append(("nsrdb", r, "atr", None, None))
for db, r, b, rh, st in jobs:
    try:
        m = convert(db, r, b, rh, st)
        print(db, r, "ok" if m else "missing", f"{m['seconds']/3600:.1f} h {m['channel']}" if m else "", flush=True)
    except Exception as e:
        print(db, r, "FAIL", e, flush=True)
