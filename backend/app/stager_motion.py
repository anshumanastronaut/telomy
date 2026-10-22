"""Telomy motion + heart-rate sleep stager (numpy inference) for 1 Hz wearable streams — WHOOP gravity + HR today,
Apple Watch / patch motion later. Trained on PSG-labelled wrist data: PhysioNet sleep-accel (Walch et al. 2019,
ODC-By attribution), 31 subjects. Leave-one-subject-out: 4-class κ 0.466 (NOOP's default stager 0.35 on its own
44-subject benchmark), per-stage bias within ±6 min/night. Training: ~/telomy-lab/sleepstage/train_motion_hr.py —
the feature code below is a line-for-line port and must stay identical to it.
"""
import json
import math
import os

import numpy as np

_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        m = json.load(open(os.path.join(os.path.dirname(__file__), "models", "motion_hr_stager.json")))
        _MODEL = {k: np.array(v, dtype=np.float64) for k, v in m["state"].items()}
        _MODEL["_loso"] = m.get("loso", {})
    return _MODEL


def features(t0: float, n: int, grav: list[tuple[int, float, float, float]], hr: list[tuple[int, float]]) -> np.ndarray:
    """grav: (unix s, x, y, z) at ~1 Hz; hr: (unix s, bpm). Epoch i covers [t0 + 30 i, +30)."""
    s0, s1 = int(t0) - 900, int(t0) + n * 30 + 900
    G = np.full((s1 - s0, 3), np.nan)
    for t, x, y, z in grav:
        i = int(t) - s0
        if 0 <= i < len(G):
            G[i] = (x, y, z)
    for k in range(3):
        v = G[:, k]; m = np.isnan(v)
        if (~m).sum() > 2:
            G[m, k] = np.interp(np.flatnonzero(m), np.flatnonzero(~m), v[~m])
    dg = np.r_[0, np.linalg.norm(np.diff(G, axis=0), axis=1)]
    ang = np.degrees(np.arctan2(G[:, 2], np.hypot(G[:, 0], G[:, 1])))
    dang = np.r_[0, np.abs(np.diff(ang))]
    ts = np.arange(s0, s1) + 0.5
    H = np.array(sorted(hr), dtype=float) if hr else np.zeros((0, 2))
    if len(H) > 2:
        h = np.interp(ts, H[:, 0], H[:, 1])
        gap = np.interp(ts, H[:, 0], np.r_[0, np.diff(H[:, 0])])
        h[gap > 60] = np.nan
    else:
        h = np.full(len(ts), np.nan)

    def win(x, a, b, f):
        out = np.zeros(n)
        for i in range(n):
            c = int(t0) + i * 30 - s0
            seg = x[max(0, c + a):max(0, c + b)]
            seg = seg[~np.isnan(seg)]
            out[i] = f(seg) if len(seg) else np.nan
        return out
    F = np.stack([
        win(dg, 0, 30, np.sum), win(dang, 0, 30, np.sum),
        win(dg, -150, 180, np.mean), win(dg, -300, 330, np.mean), win(dg, -600, 630, np.mean),
        win(h, 0, 30, np.mean), win(h, -300, 330, np.std), win(h, -330, 390, np.std),
        win(h, -60, 90, np.mean) - win(h, -600, 630, np.mean),
    ], 1)
    mv = F[:, 0] > np.nanpercentile(F[:, 0], 75)
    since = np.zeros(n); c = 0.0
    for i in range(n):
        c = 0 if mv[i] else c + 0.5; since[i] = c
    F = np.c_[F, since, np.arange(n) / n]
    for j in range(F.shape[1] - 1):
        v = F[:, j]; med = np.nanmedian(v); iqr = np.nanpercentile(v, 75) - np.nanpercentile(v, 25) or 1.0
        F[:, j] = np.clip((v - med) / iqr, -6, 6)
    return np.nan_to_num(F)


def _gru(x, A, sfx, rev):
    Wi, Wh, bi, bh = A[f"gru.weight_ih_l0{sfx}"], A[f"gru.weight_hh_l0{sfx}"], A[f"gru.bias_ih_l0{sfx}"], A[f"gru.bias_hh_l0{sfx}"]
    Hd = Wh.shape[1]; hs = np.zeros(Hd); out = np.zeros((len(x), Hd))
    sig = lambda v: 1 / (1 + np.exp(-v))  # noqa: E731
    for t in (range(len(x) - 1, -1, -1) if rev else range(len(x))):
        gi = Wi @ x[t] + bi; gh = Wh @ hs + bh
        r = sig(gi[:Hd] + gh[:Hd]); z = sig(gi[Hd:2 * Hd] + gh[Hd:2 * Hd]); nn_ = np.tanh(gi[2 * Hd:] + r * gh[2 * Hd:])
        hs = (1 - z) * nn_ + z * hs; out[t] = hs
    return out


def stage(t0: float, t1: float, grav, hr) -> dict:
    """30-s stages for [t0, t1): 0 wake, 1 light, 2 deep, 3 REM."""
    A = _model()
    n = int((t1 - t0) // 30)
    if n < 20:
        return {"ok": False, "reason": "night too short"}
    X = features(t0, n, grav, hr)
    W, b = A["conv.weight"], A["conv.bias"]
    Xp = np.pad(X, ((2, 2), (0, 0)))
    z = np.maximum(np.stack([np.einsum("hfk,kf->h", W, Xp[t:t + 5]) + b for t in range(n)]), 0)
    h = np.concatenate([_gru(z, A, "", False), _gru(z, A, "_reverse", True)], 1)
    o = h @ A["out.weight"].T + A["out.bias"]
    st = o.argmax(1).tolist()
    # one physiology rule: no REM within 15 min of sleep onset (sleep-onset REM is rare in healthy adults; the model
    # put REM at minute 0 on a real night) — affects only those first epochs
    on = next((i for i, x in enumerate(st) if x > 0), None)
    if on is not None:
        for i in range(on, min(n, on + 30)):
            if st[i] == 3:
                st[i] = 1
    mins = [st.count(c) / 2 for c in range(4)]
    return {"ok": True, "t0": t0, "epochSec": 30, "stages": st, "minutes": {"wake": mins[0], "light": mins[1], "deep": mins[2], "rem": mins[3]},
            "model": "Telomy motion+HR stager (sleep-accel, LOSO κ %.2f)" % A["_loso"].get("kappa_4class", float("nan"))}
