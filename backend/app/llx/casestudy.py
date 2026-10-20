"""Layer-2 n-of-1 case-study engine — did THIS person change because of the therapy?

Methods (strongest the logged design supports):
  • Interrupted time-series (ITS) segmented regression: level change + slope change at therapy onset,
    with optional co-intervention covariates (confounder adjustment).
  • CausalImpact-style counterfactual: fit the pre-period trend, project the counterfactual through the
    post period, measure the deviation with a residual-bootstrap confidence interval.
  • Effect sizes: Tau-U (non-overlap) and standardized mean difference.
Verdict is tempered by DESIGN strength: a randomized ON/OFF crossover earns causal language; plain ITS
earns "associated with"; too few points → too_early. No lifespan/cure claims.

Dependencies: numpy, scipy (both in the project venv).
"""
from __future__ import annotations
import numpy as np
from scipy import stats

def _ols(X, y):
    """OLS with coefficient SEs and two-sided p-values."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    dof = max(1, n - k)
    sigma2 = float(resid @ resid) / dof
    try:
        cov = sigma2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.clip(np.diag(cov), 0, None))
        t = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
        p = 2 * stats.t.sf(np.abs(t), dof)
    except np.linalg.LinAlgError:
        se = np.full_like(beta, np.nan); p = np.full_like(beta, np.nan)
    return beta, se, p, resid

def interrupted_ts(y, onset, covariates=None):
    """Segmented regression: y = b0 + b1*t + b2*D + b3*(t-onset)*D [+ covariates].
    Returns level_change (b2), slope_change (b3) with p-values."""
    y = np.asarray(y, float); n = len(y)
    t = np.arange(n)
    D = (t >= onset).astype(float)
    tt = (t - onset) * D
    cols = [np.ones(n), t, D, tt]
    names = ["intercept", "pre_slope", "level_change", "slope_change"]
    if covariates is not None:
        C = np.asarray(covariates, float)
        if C.ndim == 1: C = C[:, None]
        for j in range(C.shape[1]):
            cols.append(C[:, j]); names.append(f"covar_{j}")
    X = np.column_stack(cols)
    beta, se, p, _ = _ols(X, y)
    out = {nm: {"coef": round(float(b), 4), "p": round(float(pp), 4)} for nm, b, pp in zip(names, beta, p)}
    return {"level_change": out["level_change"], "slope_change": out["slope_change"], "all": out, "n": n}

def counterfactual(y, onset, covariates=None, n_boot=2000, seed=42):
    """CausalImpact-lite: fit pre-period (trend [+covariates]), project counterfactual post, effect = obs-cf
    with a residual-bootstrap 95% CI on the average post effect."""
    y = np.asarray(y, float); n = len(y); t = np.arange(n)
    pre = t < onset
    cols = [np.ones(n), t]
    if covariates is not None:
        C = np.asarray(covariates, float); C = C[:, None] if C.ndim == 1 else C
        cols += [C[:, j] for j in range(C.shape[1])]
    X = np.column_stack(cols)
    beta, *_ , resid = _ols(X[pre], y[pre])
    cf = X @ beta
    effect = y - cf
    post = t >= onset
    avg = float(effect[post].mean())
    rng = np.random.default_rng(seed)
    pre_resid = (y[pre] - X[pre] @ beta)
    boots = [float((y[post] - (X[post] @ beta + rng.choice(pre_resid, post.sum(), replace=True))).mean())
             for _ in range(n_boot)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"avg_post_effect": round(avg, 3), "ci95": [round(float(lo), 3), round(float(hi), 3)],
            "cumulative_effect": round(float(effect[post].sum()), 3),
            "counterfactual_mean": round(float(cf[post].mean()), 3), "observed_mean": round(float(y[post].mean()), 3)}

def tau_u(baseline, treatment, improvement="down"):
    """Non-overlap effect size in [-1,1]. improvement='down' => lower is better (CRP/HR/BP)."""
    b, tr = np.asarray(baseline, float), np.asarray(treatment, float)
    s = 0
    for x in b:
        for z in tr:
            d = np.sign(z - x)
            s += (-d if improvement == "down" else d)
    denom = len(b) * len(tr)
    return round(float(s / denom), 3) if denom else 0.0

def smd(baseline, treatment):
    b, tr = np.asarray(baseline, float), np.asarray(treatment, float)
    sd = np.sqrt((b.var(ddof=1) + tr.var(ddof=1)) / 2) if len(b) > 1 and len(tr) > 1 else np.nan
    return round(float((tr.mean() - b.mean()) / sd), 3) if sd and sd > 0 else None

_DESIGN_CAVEAT = {
    "crossover": "randomized ON/OFF crossover — causal effect for this individual",
    "multiple_baseline": "multiple-baseline design — strong individual evidence",
    "ITS": "interrupted time-series — 'associated with' (confounders adjusted where logged, not randomized)",
    "prepost": "pre/post only — weakest; confounded by regression-to-mean & placebo; a first look, not causal",
}

def case_study(series, onset, improvement="down", covariates=None, design="ITS", min_each=4):
    """Full per-client case study. series: outcome values over time (equal spacing); onset: index therapy began."""
    y = np.asarray(series, float); n = len(y)
    base, treat = y[:onset], y[onset:]
    if len(base) < min_each or len(treat) < min_each:
        return {"verdict": "too_early", "reason": f"need >={min_each} points each side (have {len(base)}/{len(treat)})",
                "design": design, "design_strength": _DESIGN_CAVEAT.get(design)}
    its = interrupted_ts(y, onset, covariates)
    cf = counterfactual(y, onset, covariates)
    tu = tau_u(base, treat, improvement); d = smd(base, treat)
    eff = cf["avg_post_effect"]
    beneficial = (eff < 0) if improvement == "down" else (eff > 0)
    ci = cf["ci95"]; excludes_zero = (ci[0] > 0) or (ci[1] < 0)
    lc, sc = its["level_change"], its["slope_change"]
    want = -1 if improvement == "down" else 1                 # beneficial sign for coefficients
    # a SUSTAINED post-onset trend (slope change in the beneficial direction) is the signature that is
    # hard to explain by regression-to-mean; a pure LEVEL drop is NOT (a transiently-high baseline returning
    # to normal looks identical) -> under a non-randomized design a level-only change cannot earn "helped".
    sustained = sc["p"] < 0.05 and np.sign(sc["coef"]) == want
    level_only = lc["p"] < 0.05 and np.sign(lc["coef"]) == want and not sustained
    strong_overlap = abs(tu) >= 0.4
    randomized = design in ("crossover", "multiple_baseline")  # replication controls RTM

    if beneficial and sustained and strong_overlap and excludes_zero:
        verdict = "helped"
    elif beneficial and randomized and (sustained or level_only) and strong_overlap and excludes_zero:
        verdict = "helped"                                     # crossover/multiple-baseline rules out RTM
    elif beneficial and level_only and not randomized:
        verdict = "possible_regression_to_mean"                # the RTM trap — needs an ON/OFF block
    elif beneficial and (sustained or (excludes_zero and strong_overlap)):
        verdict = "promising"
    elif (not excludes_zero) and abs(tu) < 0.3 and not sustained:
        verdict = "no_signal"
    else:
        verdict = "mixed"
    note = ("n-of-1 for this person; threats: regression-to-mean, placebo, co-interventions, "
            "autocorrelation. Causal language requires a crossover/multiple-baseline design.")
    if verdict == "possible_regression_to_mean":
        note = ("A level drop with no sustained trend cannot be separated from regression-to-mean on a "
                "non-randomized design — schedule an ON/OFF (crossover) block to confirm before claiming benefit.")
    return {"verdict": verdict, "design": design, "design_strength": _DESIGN_CAVEAT.get(design),
            "avg_effect": eff, "effect_ci95": ci, "ci_excludes_zero": bool(excludes_zero),
            "sustained_trend": bool(sustained), "level_only": bool(level_only),
            "level_change": lc, "slope_change": sc, "tau_u": tu, "smd": d,
            "n_baseline": len(base), "n_treatment": len(treat), "caveat": note}

if __name__ == "__main__":
    import json
    rng = np.random.default_rng(1)
    # simulated CRP series: 10 baseline weeks ~3.0, therapy from wk10 drops ~1.0 over time
    base = 3.0 + rng.normal(0, 0.25, 10)
    treat = 3.0 - np.linspace(0.2, 1.1, 10) + rng.normal(0, 0.25, 10)
    y = np.concatenate([base, treat])
    print("REAL effect (CRP down after therapy):")
    print(json.dumps(case_study(y, onset=10, improvement="down", design="ITS"), indent=2))
    # null series: no change
    yn = 3.0 + rng.normal(0, 0.25, 20)
    print("\nNULL effect (no real change):", case_study(yn, onset=10, improvement="down")["verdict"])
