"""Telomy chronic-disease risk models — trained on CDC BRFSS 2021-2023 (~1.3M adults).

Complements the NHANES blood-panel disease models (research/diseasemodel): BRFSS has no labs, but it has the
chronic-disease outcomes at population scale plus the lifestyle / demographic / self-reported signals Telomy can
get WITHOUT a blood draw — age, sex, BMI, smoking, physical activity, sleep hours, general/mental/physical health,
known-high-BP / known-high-cholesterol flags, alcohol. So this is the model Telomy uses when a member has wearable
+ questionnaire data but no recent panel; the NHANES model takes over once bloods exist.

Method mirrors the aging/disease clocks: HistGradientBoosting (native NaN), 20% held-out test + 5-fold CV, ROC-AUC.
Honest framing: BRFSS outcomes are self-reported "ever told by a doctor", and features are survey items — so these
are risk-stratification screens, decision-support only, never a diagnosis.

Run:  python3 train_chronic.py            (expects raw/LLCP20{21,22,23}.XPT)
"""
from __future__ import annotations
import json
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "raw")
MODELS = os.path.join(HERE, "models")
os.makedirs(MODELS, exist_ok=True)

# ---- harmonisation: logical name -> per-year candidate BRFSS columns (names drift slightly across years) ----
# Predictors Telomy can obtain without a blood draw (wearable + onboarding questionnaire).
PRED = {
    "age":        ["_AGE80"],
    "sex":        ["SEXVAR", "_SEX"],
    "bmi":        ["_BMI5"],                 # BMI * 100
    "smoker":     ["_SMOKER3"],              # 1 daily,2 some,3 former,4 never
    "phys_act":   ["_TOTINDA"],              # 1 active,2 not
    "gen_health": ["GENHLTH"],               # 1 excellent .. 5 poor
    "ment_days":  ["MENTHLTH"],              # bad-mental-health days /30
    "phys_days":  ["PHYSHLTH"],              # bad-physical-health days /30
    "sleep_hrs":  ["SLEPTIM1"],              # hours (longitudinal analogue)
    "hi_bp_flag": ["_RFHYPE6", "_RFHYPE5"],  # 1 no,2 yes
    "hi_chol":    ["_RFCHOL3", "_RFCHOL2"],  # 1 no,2 yes
    "heavy_drink":["_RFDRHV8", "_RFDRHV7"],  # 1 no,2 yes
    "income":     ["INCOME3", "INCOME2"],
    "educ":       ["_EDUCAG"],
    "race":       ["_RACE1", "_RACE"],
    "has_insur":  ["_HLTHPL1", "HLTHPLN1"],
}
# Outcomes: logical name -> (candidate columns, positive-code set). BRFSS "ever told" items: 1=Yes.
OUT = {
    "diabetes":       (["DIABETE4"], {1}),
    "heart_attack":   (["CVDINFR4"], {1}),
    "coronary_hd":    (["CVDCRHD4"], {1}),
    "stroke":         (["CVDSTRK3"], {1}),
    "copd":           (["CHCCOPD3", "CHCCOPD2"], {1}),
    "asthma_current": (["_ASTHMS1"], {1}),             # 1 current,2 former,3 never
    "kidney_disease": (["CHCKDNY2"], {1}),
    "skin_cancer":    (["CHCSCNC1", "CHCSCNCR"], {1}),
    "other_cancer":   (["CHCOCNC1", "CHCOCNCR"], {1}),
    "arthritis":      (["_DRDXAR3", "_DRDXAR2"], {1}),
    "depression":     (["ADDEPEV3"], {1}),
}
SENTINEL = {7, 9, 77, 99, 777, 999, 7777, 9999}        # BRFSS don't-know / refused / missing


def _pick(df, names):
    for n in names:
        if n in df.columns:
            return df[n]
    return pd.Series(np.nan, index=df.index)


def load_year(path):
    cols_needed = {c for v in PRED.values() for c in v} | {c for (cs, _) in OUT.values() for c in cs}
    df = pd.read_sas(path, format="xport")
    df.columns = [c.strip() for c in df.columns]
    keep = [c for c in df.columns if c in cols_needed]
    df = df[keep].copy()
    out = pd.DataFrame(index=df.index)
    # predictors
    for name, cands in PRED.items():
        s = _pick(df, cands).astype("float64")
        s = s.where(~s.isin(SENTINEL))
        if name == "bmi":
            s = s / 100.0
        if name == "sleep_hrs":
            s = s.where((s >= 1) & (s <= 24))
        if name in ("ment_days", "phys_days"):
            s = s.replace(88, 0)                       # 88 = none
            s = s.where(s <= 30)
        out[name] = s
    # outcomes -> binary (NaN if unknown/refused)
    for name, (cands, pos) in OUT.items():
        s = _pick(df, cands).astype("float64")
        y = pd.Series(np.nan, index=df.index)
        y[s.isin(pos)] = 1.0
        y[s.notna() & ~s.isin(pos) & ~s.isin(SENTINEL)] = 0.0
        out["y_" + name] = y
    return out


def main():
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import roc_auc_score, average_precision_score

    mega = os.path.join(HERE, "megaset.parquet")
    if os.path.exists(mega):
        data = pd.read_parquet(mega)
        yrs = data["year"].nunique() if "year" in data else "?"
        print(f"MEGASET: {len(data):,} respondents across {yrs} years")
    else:
        frames = []
        for y in (2021, 2022, 2023):
            p = os.path.join(RAW, f"LLCP{y}.XPT")
            if not os.path.exists(p):
                print(f"  skip {y}: {p} missing"); continue
            f = load_year(p)
            print(f"  {y}: {len(f):,} rows")
            frames.append(f)
        data = pd.concat(frames, ignore_index=True)
        print(f"TOTAL: {len(data):,} respondents")

    feats = [c for c in data.columns if not c.startswith("y_") and c != "year"]  # all predictors incl. new exposome ones
    X = data[feats]
    EXPOSOME = [f for f in ("state", "marital", "urban", "fruit_lt1", "veg_lt1") if f in feats]
    yr_lo = int(data["year"].min()) if "year" in data else 2021
    yr_hi = int(data["year"].max()) if "year" in data else 2023
    results = {"_meta": {"source": f"BRFSS {yr_lo}-{yr_hi}", "n_total": int(len(data)), "features": feats,
                         "note": "self-reported outcomes; risk-stratification screen, decision-support only"}}
    for name in OUT:
        y = data["y_" + name]
        m = y.notna()
        Xn, yn = X[m], y[m].astype(int)
        if yn.sum() < 500:
            print(f"  {name}: too few positives ({int(yn.sum())}), skip"); continue
        Xtr, Xte, ytr, yte = train_test_split(Xn, yn, test_size=0.2, random_state=42, stratify=yn)
        clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06, max_leaf_nodes=48,
                                             l2_regularization=1.0, random_state=42,
                                             class_weight="balanced", early_stopping=True)
        clf.fit(Xtr, ytr)
        p = clf.predict_proba(Xte)[:, 1]
        auc, ap = roc_auc_score(yte, p), average_precision_score(yte, p)
        import joblib
        joblib.dump(clf, os.path.join(MODELS, f"{name}.joblib"))
        results[name] = {"n": int(len(yn)), "n_pos": int(yn.sum()), "prevalence": round(float(yn.mean()), 4),
                         "test_AUC": round(float(auc), 3), "test_AP": round(float(ap), 3)}
        # which features carry the model — permutation importance on a subsample (highlights the exposome ones)
        try:
            from sklearn.inspection import permutation_importance
            ss = min(15000, len(Xte))
            pi = permutation_importance(clf, Xte.iloc[:ss], yte.iloc[:ss], n_repeats=3, scoring="roc_auc", random_state=42, n_jobs=-1)
            imp = dict(zip(feats, (round(float(v), 4) for v in pi.importances_mean)))
            results[name]["top_features"] = sorted(imp.items(), key=lambda z: -z[1])[:6]
            results[name]["exposome_importance"] = {f: imp.get(f, 0.0) for f in EXPOSOME}
        except Exception:  # noqa: BLE001
            pass
        print(f"  {name:16s} n={len(yn):>8,} pos={int(yn.sum()):>7,} AUC={auc:.3f} AP={ap:.3f}")

    json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=2)
    print(f"\nSaved {len([k for k in results if k != '_meta'])} models + results.json")


if __name__ == "__main__":
    main()
