#!/usr/bin/env python3
"""Read a Telomy therapy capture (format telomy.capture/1) shared from the phone.

    python scripts/capture/read_capture.py SESSION.telomy.json            # summary
    python scripts/capture/read_capture.py SESSION.telomy.json --csv out/ # ecg.csv, beats.csv, metrics.csv, phases.csv

Library use:
    from read_capture import load
    cap = load("SESSION.telomy.json")
    cap.ecg_uv, cap.ecg_t        # numpy arrays: µV and unix seconds per sample (100 Hz)
    cap.beats, cap.metrics       # lists of dicts
    cap.phase_at(t)              # "baseline" / "therapy" / "recovery" for a unix time

Only numpy is needed. See docs/devices/THERAPY_CAPTURE.md for every field.
"""
import argparse
import base64
import csv
import json
import os
import sys
from dataclasses import dataclass

import numpy as np


@dataclass
class Capture:
    meta: dict
    fs: float
    ecg_uv: np.ndarray
    ecg_t: np.ndarray
    beats: list
    metrics: list
    events: list

    @property
    def phases(self) -> list:
        return [p for p in self.meta.get("phases", []) if p.get("phase") != "marker"]

    @property
    def markers(self) -> list:
        return [p for p in self.meta.get("phases", []) if p.get("phase") == "marker"]

    def phase_at(self, t: float) -> str | None:
        cur = None
        for p in self.phases:
            if p["t"] <= t:
                cur = p["phase"]
        return cur


def load(path: str) -> Capture:
    with open(path) as f:
        b = json.load(f)
    if b.get("format") != "telomy.capture/1":
        raise ValueError(f"{path}: not a telomy.capture/1 file")
    e = b["ecg"]
    fs = float(e["fs"])
    raw = np.frombuffer(base64.b64decode(e["data"]), dtype="<i2").astype(np.float64)
    meta = b["meta"]
    # segments [{sample, unix}] restart the clock after gaps (band out of range, app relaunched)
    segs = meta.get("segments") or [{"sample": 0, "unix": meta.get("ecgStartUnix") or meta.get("startedAt", 0.0)}]
    ecg_t = np.empty(raw.size)
    for k, sg in enumerate(segs):
        end = segs[k + 1]["sample"] if k + 1 < len(segs) else raw.size
        ecg_t[sg["sample"]:end] = sg["unix"] + np.arange(end - sg["sample"]) / fs
    beats = []
    for row in csv.DictReader(b.get("beats_csv", "").splitlines()):
        beats.append({"t": float(row["t_unix"]), "rr_ms": float(row["rr_ms"]) if row["rr_ms"] else None,
                      "amplitude_uv": float(row["amplitude_uv"])})
    return Capture(meta, fs, raw, ecg_t, beats, b.get("metrics", []), b.get("events", []))


def summary(c: Capture) -> str:
    m = c.meta
    lines = [f"{m.get('id')}  {m.get('therapy')}  {c.ecg_uv.size / c.fs / 60:.1f} min ECG, {len(c.beats)} beats, "
             f"{len(c.metrics)} metric rows, {len(c.events)} events",
             f"settings {m.get('settings')}", f"pre {m.get('pre')}  post {m.get('post')}"]
    for p in c.phases:
        sel = [x for x in c.metrics if c.phase_at(x["t"]) == p["phase"] and x.get("hr")]
        hr = np.median([x["hr"] for x in sel]) if sel else float("nan")
        rm = [x["rmssdSmooth"] for x in sel if x.get("rmssdSmooth") and x.get("hrvState") == "ok"]
        lines.append(f"  {p['phase']:<10} HR {hr:5.1f}  RMSSD {np.median(rm) if rm else float('nan'):5.1f} ms  ({len(sel)} s)")
    for k in c.markers:
        lines.append(f"  marker @{k['t'] - c.meta['startedAt']:.0f}s: {k.get('note', '')}")
    for e in c.meta.get("userEvents", []):
        lines.append(f"  event  @{e['t'] - c.meta['startedAt']:.0f}s: {e.get('kind')} · {e.get('label')}{' · ' + e['note'] if e.get('note') else ''}")
    if m.get("notes"):
        lines.append(f"notes: {m['notes']}")
    return "\n".join(lines)


def to_csv(c: Capture, out: str):
    os.makedirs(out, exist_ok=True)
    np.savetxt(os.path.join(out, "ecg.csv"), np.column_stack([c.ecg_t, c.ecg_uv]), delimiter=",",
               header="t_unix,ecg_uv", comments="", fmt=["%.3f", "%.0f"])
    with open(os.path.join(out, "beats.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, ["t", "rr_ms", "amplitude_uv", "phase"])
        w.writeheader()
        for b in c.beats:
            w.writerow({**b, "phase": c.phase_at(b["t"])})
    keys = sorted({k for r in c.metrics for k, v in r.items() if not isinstance(v, (dict, list))})
    with open(os.path.join(out, "metrics.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, keys + ["phase"], extrasaction="ignore")
        w.writeheader()
        for r in c.metrics:
            w.writerow({**r, "phase": c.phase_at(r["t"])})
    with open(os.path.join(out, "phases.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["phase", "t_unix", "note"])
        for p in c.meta.get("phases", []):
            w.writerow([p["phase"], p["t"], p.get("note", "")])
    with open(os.path.join(out, "events.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_unix", "kind", "label", "note", "phase"])
        for e in c.meta.get("userEvents", []):
            w.writerow([e["t"], e.get("kind", ""), e.get("label", ""), e.get("note", ""), c.phase_at(e["t"])])
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(c.meta, f, indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--csv", help="write CSVs to this folder (one sub-folder per session)")
    a = ap.parse_args()
    for p in a.files:
        try:
            c = load(p)
        except Exception as e:
            print(f"{p}: {e}", file=sys.stderr)
            continue
        print(summary(c), "\n")
        if a.csv:
            to_csv(c, os.path.join(a.csv, c.meta["id"]))
