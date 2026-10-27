#!/usr/bin/env python3
"""Assemble a clean blood-panel + age table from multi-cycle NHANES XPT files.

Each NHANES cycle is keyed by SEQN. We merge DEMO (age, sex) with the lab files,
concatenate 5 cycles (2009-2018), rename the cryptic LBX* variables to clean
feature names, and harmonise CRP (older cycles report conventional CRP in mg/dL;
newer report hs-CRP in mg/L -> convert to a single mg/L column).
"""
import glob, os, sys
import pandas as pd

RAW = os.path.join(os.path.dirname(__file__), "raw")
OUT = os.path.join(os.path.dirname(__file__), "nhanes_bloodpanel.csv")

# cycle suffix -> (start year label just for provenance)
CYCLES = {"F": "2009-2010", "G": "2011-2012", "H": "2013-2014", "I": "2015-2016", "J": "2017-2018"}

# file -> {NHANES var : clean name}.  Only pulls the columns we want.
WANT = {
    "DEMO":   {"RIDAGEYR": "age", "RIAGENDR": "sex", "RIDRETH1": "race"},
    "CBC":    {"LBXWBCSI": "wbc", "LBXLYPCT": "lymph_pct", "LBXNEPCT": "neut_pct",
               "LBXMOPCT": "mono_pct", "LBXEOPCT": "eos_pct", "LBXBAPCT": "baso_pct",
               "LBXRBCSI": "rbc", "LBXHGB": "hgb", "LBXHCT": "hct", "LBXMCVSI": "mcv",
               "LBXMC": "mch", "LBXMCHSI": "mchc", "LBXRDW": "rdw",
               "LBXPLTSI": "platelets", "LBXMPSI": "mpv"},
    "BIOPRO": {"LBXSAL": "albumin", "LBXSATSI": "alt", "LBXSASSI": "ast",
               "LBXSAPSI": "alp", "LBXSGTSI": "ggt", "LBXSCR": "creatinine",
               "LBXSBU": "bun", "LBXSUA": "uric_acid", "LBXSGL": "glucose_serum",
               "LBXSCA": "calcium", "LBXSPH": "phosphorus", "LBXSNASI": "sodium",
               "LBXSKSI": "potassium", "LBXSCLSI": "chloride", "LBXSC3SI": "bicarb",
               "LBXSTB": "bilirubin", "LBXSTP": "total_protein", "LBXSGB": "globulin",
               "LBXSTR": "trig_serum", "LBXSCH": "chol_serum", "LBXSIR": "iron",
               "LBXSOSSI": "osmolality"},
    "GLU":    {"LBXGLU": "glucose_fasting"},
    "GHB":    {"LBXGH": "hba1c"},
    "HSCRP":  {"LBXHSCRP": "crp_mgL"},            # hs-CRP already mg/L
    "CRP":    {"LBXCRP": "crp_mgdL"},             # conventional CRP mg/dL (older cycles)
    "INS":    {"LBXIN": "insulin"},
    "TCHOL":  {"LBXTC": "total_chol"},
    "HDL":    {"LBDHDD": "hdl"},
    "TRIGLY": {"LBXTR": "trig", "LBDLDL": "ldl"},
}

def read_xpt(path):
    # pandas reads SAS xport directly; macOS FS is case-insensitive so .XPT/.xpt both resolve
    return pd.read_sas(path, format="xport")

def cycle_frame(suf):
    demo_path = find(f"DEMO_{suf}")
    if not demo_path:
        return None
    df = read_xpt(demo_path)[["SEQN"] + list(WANT["DEMO"])].rename(columns=WANT["DEMO"])
    for fam, mapping in WANT.items():
        if fam == "DEMO":
            continue
        p = find(f"{fam}_{suf}")
        if not p:
            continue
        lab = read_xpt(p)
        cols = ["SEQN"] + [c for c in mapping if c in lab.columns]
        lab = lab[cols].rename(columns={k: v for k, v in mapping.items() if k in lab.columns})
        df = df.merge(lab, on="SEQN", how="left")
    df["cycle"] = CYCLES[suf]
    return df

def find(stem):
    hits = glob.glob(os.path.join(RAW, stem + ".*"))
    hits = [h for h in hits if h.lower().endswith(".xpt")]
    return hits[0] if hits else None

def main():
    frames = []
    for suf in CYCLES:
        f = cycle_frame(suf)
        if f is not None:
            frames.append(f)
            print(f"  cycle {CYCLES[suf]}: {len(f):>6} rows, {f.shape[1]} cols")
    df = pd.concat(frames, ignore_index=True)
    # harmonise CRP: prefer hs-CRP (mg/L); else conventional CRP mg/dL * 10 -> mg/L
    if "crp_mgL" not in df: df["crp_mgL"] = pd.NA
    if "crp_mgdL" in df:
        df["crp_mgL"] = df["crp_mgL"].fillna(df["crp_mgdL"] * 10.0)
        df = df.drop(columns=["crp_mgdL"])
    # unify glucose (fasting where available, else serum)
    if "glucose_fasting" in df and "glucose_serum" in df:
        df["glucose"] = df["glucose_fasting"].fillna(df["glucose_serum"])
    df.to_csv(OUT, index=False)
    print(f"\nAssembled {len(df):,} participants x {df.shape[1]} columns -> {os.path.basename(OUT)}")
    print(f"age: n={df['age'].notna().sum():,}  range {df['age'].min():.0f}-{df['age'].max():.0f}")
    # coverage of key markers
    key = ["albumin","creatinine","glucose","crp_mgL","lymph_pct","mcv","rdw","alp","wbc","hba1c","hdl","total_chol"]
    print("marker coverage (non-null, adults 18+):")
    adults = df[df["age"] >= 18]
    for k in key:
        if k in df:
            print(f"  {k:<16} {adults[k].notna().sum():>6}")

if __name__ == "__main__":
    main()
