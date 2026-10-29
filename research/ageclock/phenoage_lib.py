#!/usr/bin/env python3
"""Mortality-anchored biological-age estimators for the organ clocks.

Two estimators, both fit on the NHANES Linked Mortality Files (all-cause):

1. PhenoAge (Levine 2018, PLoS Med / Liu 2018) — a parametric Gompertz proportional-hazards
   mortality model on a biomarker panel + chronological age, whose predicted 10-year mortality
   risk is mapped back onto an age scale via an age-only Gompertz. This reproduces the exact
   clinical-PhenoAge construction on our own cohort (so the mapping constants are ours, not
   Levine's borrowed numbers, and are reported for provenance).

2. KDM / BioAge (Klemera & Doubal 2006) — each marker is regressed on chronological age over
   the reference sample; the biomarker deviations are pooled into an age-scale estimate.

Pure-numpy serving: fitting uses scipy; the serialized params (coeffs, standardization, Gompertz
shape, age-mapping constants) are enough to score a new panel with numpy alone, so the backend
needs no scipy/lifelines at inference.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize

T10 = 120.0  # 10-year horizon in months (NHANES permth is months of follow-up)


# ----------------------------------------------------------------------------- Gompertz PH MLE
def _neg_loglik(params, X, t, event):
    """Gompertz proportional-hazards negative log-likelihood (right-censored).

    hazard  h(t|x) = exp(a + x.beta + gamma*t)
    cum.haz H(t|x) = exp(a + x.beta) * (exp(gamma*t) - 1) / gamma
    """
    a = params[0]
    beta = params[1:-1]
    g = params[-1]
    lp = a + X @ beta                      # linear predictor (age/markers), excl. time
    if abs(g) < 1e-8:
        g = 1e-8
    H = np.exp(lp) * (np.exp(g * t) - 1.0) / g
    ln_h = lp + g * t
    ll = np.sum(event * ln_h - H)
    if not np.isfinite(ll):
        return 1e12
    return -ll


def fit_gompertz(X, t, event, maxiter=2000):
    """Fit Gompertz PH. X standardized (n,p). Returns dict(a, beta, gamma)."""
    X = np.asarray(X, float)
    p = X.shape[1]
    x0 = np.concatenate([[-8.0], np.zeros(p), [0.001]])   # small +ve shape
    res = minimize(_neg_loglik, x0, args=(X, t, event), method="Nelder-Mead",
                   options={"maxiter": maxiter * (p + 2), "xatol": 1e-6, "fatol": 1e-6})
    # polish with BFGS from the simplex optimum
    res = minimize(_neg_loglik, res.x, args=(X, t, event), method="BFGS",
                   options={"maxiter": 1000})
    a, beta, g = float(res.x[0]), res.x[1:-1].astype(float), float(res.x[-1])
    return {"a": a, "beta": beta.tolist(), "gamma": g, "neg_ll": float(res.fun),
            "converged": bool(res.success)}


def gompertz_risk(a, beta, gamma, X, t=T10):
    """10-year all-cause mortality risk M = 1 - exp(-H(t))."""
    X = np.asarray(X, float)
    lp = a + X @ np.asarray(beta, float)
    g = gamma if abs(gamma) > 1e-8 else 1e-8
    H = np.exp(lp) * (np.exp(g * t) - 1.0) / g
    return 1.0 - np.exp(-H)


def fit_age_mapping(age, t, event):
    """Age-only Gompertz; returns constants to invert a 10-yr risk back to an age scale."""
    age = np.asarray(age, float)
    fit = fit_gompertz(age.reshape(-1, 1), t, event)
    a_age, b_age, g_age = fit["a"], fit["beta"][0], fit["gamma"]
    g = g_age if abs(g_age) > 1e-8 else 1e-8
    K = (np.exp(g * T10) - 1.0) / g
    return {"a_age": a_age, "b_age": b_age, "gamma_age": g_age, "K": float(K)}


def risk_to_phenoage(M, amap):
    """Invert the age-only Gompertz: phenoage s.t. age-only 10-yr risk == M."""
    M = np.clip(np.asarray(M, float), 1e-7, 1 - 1e-7)
    inner = -np.log(1.0 - M) / amap["K"]
    return (np.log(inner) - amap["a_age"]) / amap["b_age"]


# ----------------------------------------------------------------------------- KDM (Klemera-Doubal)
def fit_kdm(markers, age):
    """markers: (n,p) raw; age: (n,). Returns per-marker regression params + s_BA."""
    markers = np.asarray(markers, float)
    age = np.asarray(age, float)
    n, p = markers.shape
    q, k, s = [], [], []
    for j in range(p):
        xj = markers[:, j]
        kk, qq = np.polyfit(age, xj, 1)          # xj ~ qq + kk*age
        resid = xj - (qq + kk * age)
        ss = float(resid.std(ddof=2))
        q.append(float(qq)); k.append(float(kk)); s.append(ss)
    k = np.array(k); s = np.array(s); q = np.array(q)
    # characteristic variance s_BA^2 (KDM 2006, eq. for BA with the CA regularizer)
    ba_uncorr = _kdm_core(markers, q, k, s, age, None)
    resid_ba = ba_uncorr - age
    s_ba = float(resid_ba.std(ddof=1))
    return {"q": q.tolist(), "k": k.tolist(), "s": s.tolist(), "s_ba": s_ba}


def _kdm_core(markers, q, k, s, age, s_ba):
    num = np.sum((markers - q) * (k / s**2), axis=1)
    den = np.sum((k / s) ** 2)
    if s_ba is not None:
        num = num + age / s_ba**2
        den = den + 1.0 / s_ba**2
    return num / den


def kdm_bioage(markers, age, params):
    q = np.asarray(params["q"]); k = np.asarray(params["k"])
    s = np.asarray(params["s"]); s_ba = params["s_ba"]
    return _kdm_core(np.asarray(markers, float), q, k, s, age, s_ba)
