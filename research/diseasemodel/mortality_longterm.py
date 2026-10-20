#!/usr/bin/env python3
"""Robust LONG-TERM model: 10-year all-cause and cardiovascular mortality from a routine blood panel.

Parses the NHANES linked-mortality public-use files (fixed-width, follow-up through 2019), joins to the
blood panel by SEQN, and trains gradient-boosted risk models. To keep the 10-year label clean we use
only participants whose 10-year status is known: died within 120 months (=1), or alive with >=120
months of follow-up (=0); still-alive-but-under-10y (censored) are excluded. This is the honest way to
report a 10-year risk AUC without survival-model censoring tricks.
"""
import glob, os, json
import numpy as np, pandas as pd, joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score

HERE = os.path.dirname(__file__); RNG = 42
# fixed-width column spans (0-indexed slices) for the 2019 public-use linked mortality file (line len 48)
SPANS = {"SEQN": (0, 6), "ELIGSTAT": (14, 15), "MORTSTAT": (15, 16), "UCOD_LEADING": (16, 19),
         "PERMTH_EXM": (45, 48)}

def parse_mort():
    rows = []
    for f in glob.glob(os.path.join(HERE, "mort", "*.dat")):
        for line in open(f):
            line = line.rstrip("\n")
            if len(line) < 47:
                continue
            def g(k):
                return line[SPANS[k][0]:SPANS[k][1]].strip()
            seqn, elig, mort = g("SEQN"), g("ELIGSTAT"), g("MORTSTAT")
            if not seqn or elig != "1" or mort not in ("0", "1"):   # eligible, known status only
                continue
            rows.append({"SEQN": int(seqn), "mortstat": int(mort),
                         "ucod": g("UCOD_LEADING") or None,
                         "permth": int(g("PERMTH_EXM")) if g("PERMTH_EXM").isdigit() else None})
    return pd.DataFrame(rows)

def label_10y(m):
    # died within 10y -> 1 ; alive with >=10y follow-up -> 0 ; else NaN (censored, excluded)
    if m["mortstat"] == 1 and m["permth"] is not None and m["permth"] <= 120:
        return 1
    if m["mortstat"] == 0 and m["permth"] is not None and m["permth"] >= 120:
        return 0
    return np.nan

def main():
    mort = parse_mort()
    print(f"parsed {len(mort):,} mortality records; deceased={int((mort.mortstat==1).sum()):,}")
    mort["dead10y"] = mort.apply(label_10y, axis=1)
    mort["cvd_death"] = ((mort.mortstat == 1) & (mort.ucod.isin(["001", "005"]))).astype(int)  # heart, stroke
    panel = pd.read_csv(os.path.join(HERE, "disease_dataset.csv"))
    df = panel.merge(mort, on="SEQN", how="inner")
    IDS = {"SEQN", "cycle", "mortstat", "ucod", "permth", "dead10y", "cvd_death"}
    DIS = ["diabetes","hypertension","high_cholesterol","kidney_disease","heart_failure","coronary_hd",
           "angina","heart_attack","stroke","liver_disease","cancer","copd"]
    feats = [c for c in df.columns if c not in IDS | set(DIS) and pd.api.types.is_numeric_dtype(df[c])]

    def usable(frame, cols):
        # HistGradientBoosting binning fails on an all-NaN/constant column; keep only informative ones
        return [c for c in cols if frame[c].nunique(dropna=True) >= 2]

    results = {}
    os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
    # 1) clean 10-year all-cause mortality — ONLY the 2009-2010 cycle has a full 10-year window by the
    # 2019 cutoff; pooling later cycles would let the model exploit follow-up length (label leakage).
    sub = df[df.dead10y.notna() & (df["cycle"] == "2009-2010")]
    feats10 = usable(sub, feats)
    X, y = sub[feats10].values, sub.dead10y.astype(int).values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG, stratify=y)
    m = HistGradientBoostingClassifier(max_iter=500, learning_rate=0.05, l2_regularization=1.0,
                                       class_weight="balanced", random_state=RNG).fit(Xtr, ytr)
    p = m.predict_proba(Xte)[:, 1]
    joblib.dump(m, os.path.join(HERE, "models", "mortality_10y.joblib"))
    results["all_cause_10y"] = {"n": int(len(sub)), "n_dead": int(y.sum()), "n_test": int(len(yte)),
        "test_AUC": round(float(roc_auc_score(yte, p)), 3),
        "test_AP": round(float(average_precision_score(yte, p)), 3)}
    print(f"10y all-cause mortality: AUC={results['all_cause_10y']['test_AUC']} "
          f"(n={len(sub):,}, dead={int(y.sum()):,}, test={len(yte):,})")

    # 2) cardiovascular-death risk over full follow-up (heart + stroke)
    featsC = usable(df, feats)
    X2, y2 = df[featsC].values, df.cvd_death.values
    if y2.sum() > 80:
        Xtr, Xte, ytr, yte = train_test_split(X2, y2, test_size=0.2, random_state=RNG, stratify=y2)
        m2 = HistGradientBoostingClassifier(max_iter=500, learning_rate=0.05, l2_regularization=1.0,
                                            class_weight="balanced", random_state=RNG).fit(Xtr, ytr)
        p2 = m2.predict_proba(Xte)[:, 1]
        joblib.dump(m2, os.path.join(HERE, "models", "cvd_death.joblib"))
        results["cardiovascular_death"] = {"n": int(len(df)), "n_events": int(y2.sum()),
            "n_test": int(len(yte)), "test_AUC": round(float(roc_auc_score(yte, p2)), 3),
            "test_AP": round(float(average_precision_score(yte, p2)), 3)}
        print(f"CVD mortality: AUC={results['cardiovascular_death']['test_AUC']} (events={int(y2.sum()):,})")

    results["_meta"] = {"features": feats, "label_rule": "10y: died<=120mo=1, alive>=120mo=0, else excluded",
                        "cohort_10y": "NHANES 2009-2010 only (full 10-year follow-up window)",
                        "cohort_cvd": "all cycles pooled; follow-up varies 1-10y -> a calibrated "
                                      "time-to-event (Cox/competing-risks) model is the rigorous upgrade",
                        "note": "age is the dominant mortality predictor; AUC is for ranking risk, "
                                "needs calibration + comparison vs Pooled Cohort Equations before clinical use"}
    json.dump(results, open(os.path.join(HERE, "results_longterm.json"), "w"), indent=2)
    print("saved -> models/mortality_10y.joblib, cvd_death.joblib, results_longterm.json")

if __name__ == "__main__":
    main()
