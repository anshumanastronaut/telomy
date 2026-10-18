"""Physics-informed personal models — the governing equations are fixed physiology; each person's parameters are
learnt from their own data (grey-box identification: data loss + the ODE as a hard constraint). Small data, so the
parameters are few, bounded, and every fit reports its out-of-sample skill against a naive baseline. A model that
does not beat the baseline says so and is not used for advice.

1. Training load → next-day HRV (Banister 1975 impulse-response "fitness–fatigue" model; Busso 2003):
     fitness'  = load − fitness/τ1,   fatigue' = load − fatigue/τ2     (discrete daily: x_t = x_{t-1}·e^{-1/τ} + load_t)
     HRV_{t+1} = p0 + k1·fitness_t − k2·fatigue_t
   τ1 ∈ [10, 60] d, τ2 ∈ [1, 10] d (grid); p0, k1, k2 by least squares. Skill = MAE vs predicting the trailing
   14-day mean, on the last third of days (temporal split — validation rule 5).
2. Sleep pressure (Borbély 1982 two-process model; Daan, Beersma & Borbély 1984 parameters):
     wake: S' = (1 − S)/τr (τr 18.2 h)   sleep: S' = −S/τd (τd 4.2 h)
     C(t) = 0.12·cos(2π(t − φ)/24), φ anchored to the person's own sleep midpoint (personal circadian phase).
   Output: current pressure, and the evening window where S − C crosses the upper threshold (best time to sleep).
"""
import math
from datetime import date, timedelta

from . import db


def _series(metric: str) -> dict[str, float]:
    return {r["day"]: r["value"] for r in db.rows("SELECT day, value FROM signals WHERE metric = ? ORDER BY day", (metric,))}


def daily_load() -> dict[str, float]:
    """Training impulse per day: Edwards-style minutes × intensity where available, else exercise minutes."""
    ex = _series("exercise_min")
    strain = _series("strain")
    days = sorted(set(ex) | set(strain))
    return {d: (strain[d] * 10 if d in strain else ex.get(d, 0.0)) for d in days}


def banister(outcome: str = "hrv") -> dict:
    load, y = daily_load(), _series(outcome)
    days = sorted(set(load) & set(y))
    if len(days) < 45:
        return {"ok": False, "reason": f"needs ≥ 45 days with both load and {outcome} ({len(days)} so far)"}
    d0 = date.fromisoformat(days[0])
    span = [(d0 + timedelta(days=i)).isoformat() for i in range((date.fromisoformat(days[-1]) - d0).days + 1)]
    L = [load.get(d, 0.0) for d in span]

    def states(t1, t2):
        f = g = 0.0; F, G = [], []
        a1, a2 = math.exp(-1 / t1), math.exp(-1 / t2)
        for x in L:
            f = f * a1 + x; g = g * a2 + x; F.append(f); G.append(g)
        return F, G
    idx = {d: i for i, d in enumerate(span)}
    pairs = [(idx[d] - 1, y[d]) for d in days if idx[d] >= 1]   # state at t-1 predicts outcome at t
    cut = int(len(pairs) * 2 / 3)
    train, test = pairs[:cut], pairs[cut:]
    best = None
    for t1 in (10, 15, 20, 30, 45, 60):
        for t2 in (1, 1.5, 2, 3, 5, 7, 10):
            F, G = states(t1, t2)
            # least squares p0, k1, k2 on train (3×3 normal equations)
            X = [(1.0, F[i], -G[i]) for i, _ in train]; Y = [v for _, v in train]
            beta = _lstsq(X, Y)
            if beta is None:
                continue
            err = sum(abs(beta[0] + beta[1] * F[i] - beta[2] * G[i] - v) for i, v in train) / len(train)
            if best is None or err < best[0]:
                best = (err, t1, t2, beta)
    if not best:
        return {"ok": False, "reason": "fit failed"}
    _, t1, t2, (p0, k1, k2) = best
    F, G = states(t1, t2)
    pred = [(p0 + k1 * F[i] - k2 * G[i], v) for i, v in test]
    mae = sum(abs(a - b) for a, b in pred) / len(pred)
    vals = [v for _, v in pairs]
    naive = sum(abs(sum(vals[max(0, j - 14):j]) / len(vals[max(0, j - 14):j]) - vals[j]) for j in range(cut, len(pairs))) / len(test)
    skill = 1 - mae / naive if naive else 0.0
    last = len(span) - 1
    return {"ok": True, "outcome": outcome, "tau_fitness_days": t1, "tau_fatigue_days": t2, "p0": round(p0, 1),
            "k_fitness": round(k1, 4), "k_fatigue": round(k2, 4), "test_mae": round(mae, 2), "naive_mae": round(naive, 2),
            "skill": round(skill, 3), "useful": skill > 0.05 and k2 > 0,
            "tomorrow_if_rest": round(p0 + k1 * F[last] * math.exp(-1 / t1) - k2 * G[last] * math.exp(-1 / t2), 1),
            "tomorrow_if_hard_60": round(p0 + k1 * (F[last] * math.exp(-1 / t1) + 60) - k2 * (G[last] * math.exp(-1 / t2) + 60), 1),
            "method": "Banister impulse-response, grid τ + least squares, temporal split (last third held out)"}


def _lstsq(X, Y):
    n = len(X[0]); A = [[sum(x[i] * x[j] for x in X) for j in range(n)] for i in range(n)]
    b = [sum(x[i] * y for x, y in zip(X, Y)) for i in range(n)]
    for i in range(n):                       # small ridge for stability
        A[i][i] += 1e-6
    # Gaussian elimination
    M = [row[:] + [bv] for row, bv in zip(A, b)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            return None
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * bb for a, bb in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def sleep_pressure(sleep_periods: list[tuple[float, float]], now: float, tz_offset_h: float = 5.5) -> dict:
    """Two-process model over the last ≥ 3 days of sleep periods [(start_unix, end_unix)], in hours of local time."""
    if len(sleep_periods) < 3:
        return {"ok": False, "reason": "needs 3 nights of sleep timing"}
    tr, td, amp = 18.2, 4.2, 0.12
    mids = [((s + e) / 2 / 3600 + tz_offset_h) % 24 for s, e in sleep_periods[-7:]]
    ang = [m / 24 * 2 * math.pi for m in mids]
    mid = (math.degrees(math.atan2(sum(math.sin(a) for a in ang), sum(math.cos(a) for a in ang))) / 15) % 24
    phi = (mid + 12) % 24                 # circadian alertness peak ~12 h after the sleep midpoint
    t, S = sleep_periods[0][0], 0.3
    step = 600
    asleep = lambda x: any(s <= x < e for s, e in sleep_periods)   # noqa: E731
    while t < now:
        S = S - S / td * (step / 3600) if asleep(t) else S + (1 - S) / tr * (step / 3600)
        t += step
    C = lambda x: amp * math.cos(2 * math.pi * (((x / 3600 + tz_offset_h) % 24) - phi) / 24)   # noqa: E731
    # tonight's window: project forward awake until S exceeds the upper threshold (0.6 + C)
    t2, S2, window = now, S, None
    for _ in range(int(18 * 3600 / step)):
        if S2 >= 0.6 + C(t2) and window is None:
            window = t2
        S2 = S2 + (1 - S2) / tr * (step / 3600); t2 += step
    return {"ok": True, "pressure": round(S, 3), "circadian": round(C(now), 3), "sleep_midpoint_h": round(mid, 2),
            "best_sleep_from": window, "method": "Borbély two-process (Daan 1984 τr 18.2 h, τd 4.2 h), personal phase"}
