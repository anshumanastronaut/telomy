#!/usr/bin/env python3
"""Real-calibrated synthetic biomarker data + models that estimate blood biomarkers from wearable-accessible signals.

Why this design: a model trained only on hand-written synthetic data learns back the generator's own rules. So we
(1) build the real cohort from NHANES 2017–2018 (CDC, public, de-identified), (2) compute PhenoAge (Levine 2018) as a
label, (3) fit a Gaussian-copula generator to the real joint distribution and sample a large synthetic cohort, every
row flagged `synthetic=1`, and (4) evaluate every model on HELD-OUT REAL people — real-trained vs synthetic-trained
vs synthetic-pretrain+real — so the value of synthetic data is measured, not assumed.

Data stays outside the repo (~/telomy-lab/nhanes). Nothing here touches any user's Vault.

  python ml/biomarkers/nhanes_synth.py --data ~/telomy-lab/nhanes --n-synth 50000
"""
from __future__ import annotations
import argparse, json, os
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

FILES = {
    "DEMO_J": ["RIDAGEYR", "RIAGENDR"],
    "BIOPRO_J": ["LBXSAL", "LBXSCR", "LBXSGL", "LBXSAPSI", "LBXSATSI", "LBXSASSI", "LBXSGTSI", "LBXSUA"],
    "CBC_J": ["LBXLYPCT", "LBXMCVSI", "LBXRDW", "LBXWBCSI", "LBXHGB"],
    "HSCRP_J": ["LBXHSCRP"], "GHB_J": ["LBXGH"], "TCHOL_J": ["LBXTC"], "HDL_J": ["LBDHDD"], "TRIGLY_J": ["LBXTR", "LBDLDL"],
    "BMX_J": ["BMXBMI", "BMXWAIST", "BMXHT"], "BPXO_J": ["BPXOSY1", "BPXOSY2", "BPXOSY3", "BPXOPLS1", "BPXOPLS2"],
    "SMQ_J": ["SMQ020", "SMQ040"], "ALQ_J": ["ALQ130"], "DXX_J": ["DXDLALE", "DXDRALE", "DXDLLLE", "DXDRLLE"],
}
# what a wearable + onboarding can know  →  what only a blood draw can know
WEARABLE = ["age", "male", "bmi", "waist", "sbp", "pulse", "smoker", "drinks", "almi"]
TARGETS = ["phenoage_accel", "hba1c", "ln_crp", "ldl", "tg", "alt"]


def load(d: str) -> pd.DataFrame:
    df = None
    for f, cols in FILES.items():
        x = pd.read_sas(os.path.join(d, f + ".XPT"), format="xport")[["SEQN"] + [c for c in cols]]
        df = x if df is None else df.merge(x, on="SEQN", how="left")
    o = pd.DataFrame({"seqn": df.SEQN})
    o["age"] = df.RIDAGEYR; o["male"] = (df.RIAGENDR == 1).astype(float)
    o["bmi"] = df.BMXBMI; o["waist"] = df.BMXWAIST
    o["sbp"] = df[["BPXOSY1", "BPXOSY2", "BPXOSY3"]].mean(axis=1); o["pulse"] = df[["BPXOPLS1", "BPXOPLS2"]].mean(axis=1)
    o["smoker"] = df.SMQ040.isin([1, 2]).astype(float).where(df.SMQ020.notna(), np.nan)
    o["drinks"] = df.ALQ130.where(df.ALQ130 < 77, np.nan).fillna(0)  # 77/99 = refused/don't know
    lean_kg = df[["DXDLALE", "DXDRALE", "DXDLLLE", "DXDRLLE"]].sum(axis=1, min_count=4) / 1000
    o["almi"] = lean_kg / (df.BMXHT / 100) ** 2
    o["albumin_gl"] = df.LBXSAL * 10; o["creat_umol"] = df.LBXSCR * 88.4; o["glucose_mmol"] = df.LBXSGL / 18.016
    o["crp_mgl"] = df.LBXHSCRP; o["lymph"] = df.LBXLYPCT; o["mcv"] = df.LBXMCVSI; o["rdw"] = df.LBXRDW
    o["alp"] = df.LBXSAPSI; o["wbc"] = df.LBXWBCSI; o["hba1c"] = df.LBXGH; o["ldl"] = df.LBDLDL; o["tg"] = df.LBXTR
    o["hdl"] = df.LBDHDD; o["alt"] = df.LBXSATSI; o["ast"] = df.LBXSASSI; o["ggt"] = df.LBXSGTSI; o["hgb"] = df.LBXHGB
    return o[(o.age >= 20)]


def phenoage(o: pd.DataFrame) -> pd.Series:
    """Levine et al. 2018, Aging 10:573 — units: albumin g/L, creatinine µmol/L, glucose mmol/L, CRP mg/dL."""
    crp_mgdl = (o.crp_mgl.clip(lower=0.01)) / 10
    xb = (-19.907 - 0.0336 * o.albumin_gl + 0.0095 * o.creat_umol + 0.1953 * o.glucose_mmol + 0.0954 * np.log(crp_mgdl)
          - 0.0120 * o.lymph + 0.0268 * o.mcv + 0.3306 * o.rdw + 0.00188 * o.alp + 0.0554 * o.wbc + 0.0804 * o.age)
    g = 0.0076927
    m = (1 - np.exp(-np.exp(xb) * (np.exp(120 * g) - 1) / g)).clip(1e-12, 1 - 1e-12)  # avoid log(0) at the extremes
    return 141.50225 + np.log(-0.00553 * np.log(1 - m)) / 0.090165


def add_labels(o: pd.DataFrame, fit=None):
    o = o.copy()
    o["phenoage"] = phenoage(o)
    o["ln_crp"] = np.log(o.crp_mgl.clip(lower=0.05))
    if fit is None:  # acceleration = residual of PhenoAge on age, fitted on the REAL cohort only
        ok = o.phenoage.notna() & o.age.notna()
        fit = np.polyfit(o.age[ok], o.phenoage[ok], 1)
    o["phenoage_accel"] = o.phenoage - np.polyval(fit, o.age)
    return o, fit


class Copula:
    """Gaussian copula: per-column empirical marginals + a correlation matrix in normal-score space."""
    def fit(self, X: pd.DataFrame):
        self.cols = list(X.columns); self.q = {c: np.sort(X[c].dropna().values) for c in self.cols}
        Z = pd.DataFrame({c: stats.norm.ppf((X[c].rank(pct=True) * len(X) - 0.5).clip(0.5) / len(X)) for c in self.cols})
        self.C = Z.corr(min_periods=200).fillna(0).values
        np.fill_diagonal(self.C, 1)
        w, v = np.linalg.eigh(self.C); self.C = (v * np.clip(w, 1e-6, None)) @ v.T  # nearest PSD
        return self

    def sample(self, n: int, seed=7) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        U = stats.norm.cdf(rng.multivariate_normal(np.zeros(len(self.cols)), self.C, size=n))
        return pd.DataFrame({c: np.quantile(self.q[c], U[:, i]) for i, c in enumerate(self.cols)})


def evaluate(train: pd.DataFrame, test: pd.DataFrame, target: str, warm: pd.DataFrame | None = None):
    tr = train.dropna(subset=[target]); te = test.dropna(subset=[target])
    m = HistGradientBoostingRegressor(loss="absolute_error", max_iter=400, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0, early_stopping=warm is None, validation_fraction=0.15,
                                      random_state=0, warm_start=warm is not None)
    if warm is not None:
        w = warm.dropna(subset=[target]); m.fit(w[WEARABLE], w[target]); m.max_iter += 200
    m.fit(tr[WEARABLE], tr[target])
    p = m.predict(te[WEARABLE])
    base = mean_absolute_error(te[target], np.full(len(te), tr[target].median()))
    return {"mae": float(mean_absolute_error(te[target], p)), "r2": float(r2_score(te[target], p)),
            "mae_baseline_median": float(base), "n_train": int(len(tr)), "n_test": int(len(te))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.expanduser("~/telomy-lab/nhanes"))
    ap.add_argument("--n-synth", type=int, default=50000)
    a = ap.parse_args()
    out = os.path.join(a.data, "out"); os.makedirs(out, exist_ok=True)

    real, fit = add_labels(load(a.data))
    print(f"real cohort: {len(real)} adults; PhenoAge computable for {real.phenoage.notna().sum()}; ALMI for {real.almi.notna().sum()}")
    tr, te = train_test_split(real, test_size=0.25, random_state=42)

    gen_cols = WEARABLE + ["albumin_gl", "creat_umol", "glucose_mmol", "crp_mgl", "lymph", "mcv", "rdw", "alp", "wbc",
                           "hba1c", "ldl", "tg", "hdl", "alt", "ast", "ggt", "hgb"]
    cop = Copula().fit(tr[gen_cols])                      # fit on the TRAIN split only — the test people are never seen
    syn, _ = add_labels(cop.sample(a.n_synth), fit)
    syn["synthetic"] = 1
    syn.to_csv(os.path.join(out, "synthetic_biomarkers.csv"), index=False)

    # fidelity: do synthetic correlations match real ones?
    rc, sc = tr[gen_cols].corr().values, syn[gen_cols].corr().values
    iu = np.triu_indices_from(rc, 1); ok = ~np.isnan(rc[iu])
    fidelity = {"corr_of_correlations": float(np.corrcoef(rc[iu][ok], sc[iu][ok])[0, 1]),
                "mean_abs_corr_error": float(np.nanmean(np.abs(rc[iu] - sc[iu])))}
    print("synthetic fidelity:", fidelity)

    results = {}
    for t in TARGETS:
        results[t] = {"real_trained": evaluate(tr, te, t), "synthetic_only": evaluate(syn, te, t),
                      "synth_pretrain_then_real": evaluate(tr, te, t, warm=syn)}
        r = results[t]
        print(f"{t:15s} MAE real {r['real_trained']['mae']:.3f} | synth-only {r['synthetic_only']['mae']:.3f} | "
              f"synth+real {r['synth_pretrain_then_real']['mae']:.3f} | baseline {r['real_trained']['mae_baseline_median']:.3f} "
              f"| R² real {r['real_trained']['r2']:.2f}")

    card = {"dataset": "NHANES 2017–2018 (CDC), adults ≥20", "label": "PhenoAge (Levine 2018) and single biomarkers",
            "features": WEARABLE, "generator": "Gaussian copula on train split", "n_synthetic": a.n_synth,
            "fidelity": fidelity, "results_on_real_holdout": results,
            "caveats": ["Estimates population-level association, not an individual measurement; never shown as a lab value.",
                        "NHANES pulse is a seated BP-cuff pulse, not a wearable resting HR; HRV/VO₂max are not in NHANES.",
                        "Synthetic rows carry synthetic=1 and are never mixed into any user's Vault."]}
    json.dump(card, open(os.path.join(out, "model_card.json"), "w"), indent=2)
    print("wrote", os.path.join(out, "model_card.json"))


if __name__ == "__main__":
    main()
