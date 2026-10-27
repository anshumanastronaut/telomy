"""Fit and validate biological-age engines on NHANES 2017-2018 (public, CDC).

Builds three blood-based ages and checks them against real population data:
  * PhenoAge (Levine 2018)                 — our current engine; verify its distribution vs chronological age.
  * KDM biological age (Klemera-Doubal 2006) — fit per-biomarker regressions on age in a training reference, score out of
    sample; the canonical clinical-biomarker age used by the BioAge toolkit (Kwon & Belsky 2021).
  * Homeostatic dysregulation (HD)         — Mahalanobis distance from a young-healthy reference (Cohen 2013).

Outputs the fitted KDM/HD parameters (to port into the Telomy engine) and validation metrics on a held-out test set.
"""
import json

import numpy as np
import pandas as pd

RNG = np.random.default_rng(7)
D = "/Users/anshuman/telomy-lab/nhanes/"


def load():
    demo = pd.read_sas(D + "DEMO_J.xpt")[["SEQN", "RIDAGEYR", "RIAGENDR"]]
    bio = pd.read_sas(D + "BIOPRO_J.xpt")[["SEQN", "LBXSAL", "LBXSCR", "LBXSAPSI", "LBXSBU"]]
    cbc = pd.read_sas(D + "CBC_J.xpt")[["SEQN", "LBXWBCSI", "LBXLYPCT", "LBXMCVSI", "LBXRDW"]]
    glu = pd.read_sas(D + "GLU_J.xpt")[["SEQN", "LBXGLU"]]
    ghb = pd.read_sas(D + "GHB_J.xpt")[["SEQN", "LBXGH"]]
    crp = pd.read_sas(D + "HSCRP_J.xpt")[["SEQN", "LBXHSCRP"]]
    tc = pd.read_sas(D + "TCHOL_J.xpt")[["SEQN", "LBXTC"]]
    bp = pd.read_sas(D + "BPXO_J.xpt")[["SEQN", "BPXOSY1", "BPXOSY2", "BPXOSY3"]]
    bp["SBP"] = bp[["BPXOSY1", "BPXOSY2", "BPXOSY3"]].mean(axis=1)
    df = demo
    for x in (bio, cbc, glu, ghb, crp, tc, bp[["SEQN", "SBP"]]):
        df = df.merge(x, on="SEQN", how="left")
    df = df.rename(columns={"RIDAGEYR": "age", "RIAGENDR": "sex", "LBXSAL": "albumin", "LBXSCR": "creatinine",
        "LBXSAPSI": "alp", "LBXSBU": "bun", "LBXWBCSI": "wbc", "LBXLYPCT": "lymph_pct", "LBXMCVSI": "mcv",
        "LBXRDW": "rdw", "LBXGLU": "glucose", "LBXGH": "hba1c", "LBXHSCRP": "crp", "LBXTC": "tc"})
    return df


def phenoage(r):
    if any(pd.isna(getattr(r, k)) for k in ("albumin", "creatinine", "glucose", "crp", "lymph_pct", "mcv", "rdw", "alp", "wbc", "age")):
        return np.nan
    try:
        xb = (-19.907 - 0.0336 * r.albumin * 10 + 0.0095 * r.creatinine * 88.4 + 0.1953 * r.glucose / 18.016
              + 0.0954 * np.log(max(r.crp, 0.01) / 10) - 0.0120 * r.lymph_pct + 0.0268 * r.mcv + 0.3306 * r.rdw
              + 0.00188 * r.alp + 0.0554 * r.wbc + 0.0804 * r.age)
        g = 0.0076927
        m = min(1 - 1e-12, max(1e-12, 1 - np.exp(-np.exp(xb) * (np.exp(120 * g) - 1) / g)))
        pa = 141.50225 + np.log(-0.00553 * np.log(1 - m)) / 0.090165
        return float(min(140.0, max(5.0, pa)))   # cap to a plausible range (extreme m otherwise runs off)
    except (ValueError, FloatingPointError):
        return np.nan


# KDM uses the canonical 8 clinical biomarkers; CRP is log-transformed (right-skewed).
KDM_MARKERS = ["albumin", "creatinine", "alp", "bun", "tc", "hba1c", "crp_log", "sbp"]
RENAME = {"crp": "crp_log"}


def prep(df):
    df = df.copy()
    df["crp_log"] = np.log(df["crp"].clip(lower=0.1))
    df = df.rename(columns={"SBP": "sbp"})
    return df


def fit_kdm(train, markers, lo=30, hi=75):
    """Per-biomarker linear regression on age in the reference age band; returns q (intercept), k (slope), s (resid SD)."""
    t = train[(train.age >= lo) & (train.age <= hi)]
    params = {}
    for m in markers:
        d = t[["age", m]].dropna()
        k, q = np.polyfit(d.age, d[m], 1)
        s = np.std(d[m] - (q + k * d.age), ddof=2)
        params[m] = {"q": float(q), "k": float(k), "s": float(s)}
    return params


def kdm_score(df, params, s_ba):
    markers = list(params)
    rchar = sum((params[m]["k"] / params[m]["s"]) ** 2 for m in markers)
    out = []
    for _, r in df.iterrows():
        num = 0.0
        ok = True
        for m in markers:
            if pd.isna(r[m]):
                ok = False
                break
            p = params[m]
            num += (r[m] - p["q"]) * p["k"] / p["s"] ** 2
        if not ok:
            out.append(np.nan)
            continue
        ba = (num + r.age / s_ba ** 2) / (rchar + 1 / s_ba ** 2)
        out.append(ba)
    return np.array(out), rchar


def estimate_s_ba(train, params):
    """Klemera-Doubal s_BA: spread of the uncorrected BA_E around CA, minus the characteristic measurement variance."""
    markers = list(params)
    rchar = sum((params[m]["k"] / params[m]["s"]) ** 2 for m in markers)
    bae, ca = [], []
    for _, r in train.iterrows():
        if any(pd.isna(r[m]) for m in markers):
            continue
        num = sum((r[m] - params[m]["q"]) * params[m]["k"] / params[m]["s"] ** 2 for m in markers)
        bae.append(num / rchar)
        ca.append(r.age)
    bae, ca = np.array(bae), np.array(ca)
    s2 = np.mean((bae - ca) ** 2) - 1 / rchar
    return float(np.sqrt(max(s2, 1.0)))


def fit_hd(train, markers):
    """Homeostatic dysregulation: mean + covariance of a young-healthy reference (ages 20-30)."""
    ref = train[(train.age >= 20) & (train.age <= 30)][markers].dropna()
    mu = ref.mean().values
    cov = np.cov(ref.values, rowvar=False)
    inv = np.linalg.pinv(cov)
    return {"mu": mu.tolist(), "inv": inv.tolist(), "markers": markers}


def hd_score(df, hd):
    mu = np.array(hd["mu"]); inv = np.array(hd["inv"]); markers = hd["markers"]
    out = []
    for _, r in df.iterrows():
        x = r[markers].values.astype(float)
        if np.any(pd.isna(x)):
            out.append(np.nan); continue
        d = x - mu
        out.append(float(np.log(max(d @ inv @ d, 1e-6))))
    return np.array(out)


def main():
    df = prep(load())
    df = df[(df.age >= 20) & (df.age <= 84)].reset_index(drop=True)
    # train/test split
    idx = RNG.permutation(len(df))
    cut = int(0.7 * len(df))
    train, test = df.iloc[idx[:cut]], df.iloc[idx[cut:]]

    # ---- PhenoAge
    for part in (train, test):
        part["phenoage"] = part.apply(phenoage, axis=1)
    pa = test[["age", "phenoage"]].dropna()
    r_pa = np.corrcoef(pa.age, pa.phenoage)[0, 1]

    # ---- KDM
    params = fit_kdm(train, KDM_MARKERS)
    s_ba = estimate_s_ba(train, params)
    kdm_test, rchar = kdm_score(test, params, s_ba)
    test = test.assign(kdm=kdm_test)
    kd = test[["age", "kdm"]].dropna()
    r_kdm = np.corrcoef(kd.age, kd.kdm)[0, 1]

    # ---- HD
    hd = fit_hd(train, KDM_MARKERS)
    test = test.assign(hd=hd_score(test, hd))
    hdv = test[["age", "hd"]].dropna()
    r_hd = np.corrcoef(hdv.age, hdv.hd)[0, 1]

    # ---- cross-method agreement on age advancement
    m = test[["age", "phenoage", "kdm", "hd"]].dropna()
    adv_pa = m.phenoage - m.age
    adv_kdm = m.kdm - m.age
    r_adv = np.corrcoef(adv_pa, adv_kdm)[0, 1]

    out = {
        "n_total": len(df), "n_train": len(train), "n_test": len(test),
        "phenoage": {"r_with_chrono_age": round(r_pa, 3), "mean_advancement": round(float(adv_pa.mean()), 2),
                     "sd_advancement": round(float(adv_pa.std()), 2)},
        "kdm": {"r_with_chrono_age": round(r_kdm, 3), "s_ba": round(s_ba, 2), "rchar": round(rchar, 5),
                "mean_advancement": round(float(adv_kdm.mean()), 2), "sd_advancement": round(float(adv_kdm.std()), 2),
                "params": params},
        "hd": {"r_with_chrono_age": round(r_hd, 3)},
        "cross_method": {"phenoage_vs_kdm_advancement_r": round(r_adv, 3), "n": len(m)},
    }
    json.dump(out, open(D + "bioage_fit.json", "w"), indent=2)
    print(f"NHANES 2017-18: {len(df)} adults (train {len(train)}, test {len(test)})")
    print(f"PhenoAge  r(CA) = {r_pa:.3f}   advancement {adv_pa.mean():+.1f} ± {adv_pa.std():.1f} y")
    print(f"KDM-BA    r(CA) = {r_kdm:.3f}   s_BA = {s_ba:.1f}   advancement {adv_kdm.mean():+.1f} ± {adv_kdm.std():.1f} y")
    print(f"HD        r(CA) = {r_hd:.3f}   (rises with age, as expected)")
    print(f"PhenoAge vs KDM advancement agreement r = {r_adv:.3f}  (n={len(m)})")
    print("\nFitted KDM params (per biomarker: slope k per year, resid SD s):")
    for mk, p in params.items():
        print(f"  {mk:11s} k={p['k']:+.4f}/yr  s={p['s']:.3f}")


if __name__ == "__main__":
    main()
