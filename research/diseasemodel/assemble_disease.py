#!/usr/bin/env python3
"""Join NHANES physician-diagnosis questionnaires to the assembled blood panel, keyed by SEQN.

Output: disease_dataset.csv = blood labs + age + sex + binary disease labels (1=diagnosed, 0=not;
NHANES 7/9/refused/don't-know -> NaN and dropped per-model).
"""
import glob, os
import pandas as pd, pyreadstat

HERE = os.path.dirname(__file__)
PANEL = os.path.join(HERE, "..", "ageclock", "nhanes_bloodpanel.csv")
SUF = ["F", "G", "H", "I", "J"]

# questionnaire file -> {NHANES var: disease label}
OUTCOMES = {
    "DIQ":   {"DIQ010": "diabetes"},
    "BPQ":   {"BPQ020": "hypertension", "BPQ080": "high_cholesterol"},
    "KIQ_U": {"KIQ022": "kidney_disease"},
    "MCQ":   {"MCQ160B": "heart_failure", "MCQ160C": "coronary_hd", "MCQ160D": "angina",
              "MCQ160E": "heart_attack", "MCQ160F": "stroke", "MCQ160L": "liver_disease",
              "MCQ220": "cancer", "MCQ160O": "copd"},
}

def rx(stem):
    hits = [h for h in glob.glob(os.path.join(HERE, "raw", stem + ".*")) if h.lower().endswith(".xpt")]
    return pyreadstat.read_xport(hits[0])[0] if hits else None

def cycle(s):
    parts = []
    for fam, mapping in OUTCOMES.items():
        df = rx(f"{fam}_{s}")
        if df is None:
            continue
        cols = ["SEQN"] + [c for c in mapping if c in df.columns]
        d = df[cols].rename(columns={k: v for k, v in mapping.items() if k in df.columns})
        parts.append(d.set_index("SEQN"))
    if not parts:
        return None
    return pd.concat(parts, axis=1).reset_index()

def main():
    dis = pd.concat([c for c in (cycle(s) for s in SUF) if c is not None], ignore_index=True)
    # encode: 1=Yes->1, 2=No->0, everything else (3 borderline, 7 refused, 9 dk)-> NaN
    labels = [v for m in OUTCOMES.values() for v in m.values()]
    for c in labels:
        if c in dis:
            dis[c] = dis[c].map({1: 1, 2: 0})
    panel = pd.read_csv(PANEL)
    df = panel.merge(dis, on="SEQN", how="inner")
    df = df[(df["age"] >= 18) & (df["age"] <= 80)]
    df.to_csv(os.path.join(HERE, "disease_dataset.csv"), index=False)
    print(f"disease_dataset.csv: {len(df):,} adults x {df.shape[1]} cols")
    print("\ndiagnosed prevalence (n positive / n labelled):")
    for c in labels:
        if c in df:
            pos, lab = int((df[c] == 1).sum()), int(df[c].notna().sum())
            print(f"  {c:<16} {pos:>5} / {lab:>6}  ({100*pos/max(1,lab):4.1f}%)")

if __name__ == "__main__":
    main()
