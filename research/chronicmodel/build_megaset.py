"""Stream-build a multi-year BRFSS feature store WITHOUT blowing the disk.

Disk is tight, so for each year we: download the zip -> unzip -> read only the columns we need -> append the
harmonised rows to a single parquet -> delete the raw XPT + zip. Peak extra disk ~ one year (~1 GB), not all of them.
The result is one compact parquet (~16 features + 11 outcomes over millions of rows) that train_chronic reads.

Years 2011-2023 share a stable calculated-variable schema (~5.7M adults). Older years are attempted with tolerant
aliases; a year that doesn't yield the core outcomes is skipped (logged), never silently corrupting the set.

Run:  python3 build_megaset.py 2011 2012 ... 2023
"""
from __future__ import annotations
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "raw")
STORE = os.path.join(HERE, "megaset.parquet")
os.makedirs(RAW, exist_ok=True)

# predictors (calculated vars are stable across years; list every known alias)
PRED = {
    "age":        ["_AGE80"],
    "sex":        ["SEXVAR", "_SEX", "SEX"],
    "bmi":        ["_BMI5"],
    "smoker":     ["_SMOKER3"],
    "phys_act":   ["_TOTINDA"],
    "gen_health": ["GENHLTH"],
    "ment_days":  ["MENTHLTH"],
    "phys_days":  ["PHYSHLTH"],
    "sleep_hrs":  ["SLEPTIM1", "SLEPTIME"],
    "hi_bp_flag": ["_RFHYPE6", "_RFHYPE5"],
    "hi_chol":    ["_RFCHOL3", "_RFCHOL2", "_RFCHOL"],
    "heavy_drink":["_RFDRHV8", "_RFDRHV7", "_RFDRHV6", "_RFDRHV5"],
    "income":     ["INCOME3", "INCOME2"],
    "educ":       ["_EDUCAG"],
    "race":       ["_RACE1", "_RACE", "_RACEGR3"],
    "has_insur":  ["_HLTHPL1", "HLTHPLN1", "HLTHPLN"],
    # ---- exposome / social / food parameters (BRFSS-measured; partial coverage handled as NaN) ----
    "state":      ["_STATE"],                       # location → absorbs state-level environment/policy
    "marital":    ["MARITAL"],                      # social connection (living alone → mortality OR 1.32)
    "urban":      ["_URBSTAT", "MSCODE"],           # urban/rural → noise/air/activity context
    "fruit_lt1":  ["_FRTLT1", "_FRTLT1A"],          # food quality: eats fruit <1×/day
    "veg_lt1":    ["_VEGLT1", "_VEGLT1A"],          # food quality: eats veg <1×/day
}
OUT = {
    "diabetes":       (["DIABETE4", "DIABETE3", "DIABETE2"], {1}),
    "heart_attack":   (["CVDINFR4"], {1}),
    "coronary_hd":    (["CVDCRHD4"], {1}),
    "stroke":         (["CVDSTRK3"], {1}),
    "copd":           (["CHCCOPD3", "CHCCOPD2", "CHCCOPD1"], {1}),
    "asthma_current": (["_ASTHMS1"], {1}),
    "kidney_disease": (["CHCKDNY2", "CHCKIDNY"], {1}),
    "skin_cancer":    (["CHCSCNC1", "CHCSCNCR"], {1}),
    "other_cancer":   (["CHCOCNC1", "CHCOCNCR"], {1}),
    "arthritis":      (["_DRDXAR3", "_DRDXAR2", "_DRDXAR1"], {1}),
    "depression":     (["ADDEPEV3", "ADDEPEV2", "ADDEPEV"], {1}),
}
SENTINEL = {7, 9, 77, 99, 777, 999, 7777, 9999}


def _pick(df, names):
    for n in names:
        if n in df.columns:
            return df[n]
    return pd.Series(np.nan, index=df.index)


def harmonise(df):
    df.columns = [c.strip().upper() for c in df.columns]
    out = pd.DataFrame(index=df.index)
    for name, cands in PRED.items():
        s = _pick(df, [c.upper() for c in cands]).astype("float64").where(lambda x: ~x.isin(SENTINEL))
        if name == "bmi":
            s = s / 100.0
        elif name == "sleep_hrs":
            s = s.where((s >= 1) & (s <= 24))
        elif name in ("ment_days", "phys_days"):
            s = s.replace(88, 0).where(lambda x: x <= 30)
        out[name] = s
    core_ok = 0
    for name, (cands, pos) in OUT.items():
        s = _pick(df, [c.upper() for c in cands]).astype("float64")
        y = pd.Series(np.nan, index=df.index)
        y[s.isin(pos)] = 1.0
        y[s.notna() & ~s.isin(pos) & ~s.isin(SENTINEL)] = 0.0
        out["y_" + name] = y
        if y.notna().mean() > 0.5:
            core_ok += 1
    return out, core_ok


def do_year(y: int) -> int:
    import glob
    # already captured? (resume-safe)
    if os.path.exists(STORE):
        try:
            if y in set(pd.read_parquet(STORE, columns=["year"])["year"].unique()):
                print(f"  {y}: already in store — skip"); return 0
        except Exception:  # noqa: BLE001
            pass
    zp = os.path.join(RAW, f"LLCP{y}.zip")
    url = f"https://www.cdc.gov/brfss/annual_data/{y}/files/LLCP{y}XPT.zip"
    r = subprocess.run(["curl", "-sL", "--max-time", "900", url, "-o", zp])
    if r.returncode != 0 or not os.path.exists(zp):
        print(f"  {y}: download failed"); return 0
    subprocess.run(["unzip", "-o", "-q", zp, "-d", RAW])
    os.remove(zp)
    # find the actual XPT regardless of trailing spaces / case / subfolder
    cands = [c for c in glob.glob(os.path.join(RAW, "**", "*.[xX][pP][tT]*"), recursive=True) if os.path.isfile(c)]
    if not cands:
        print(f"  {y}: no XPT after unzip"); return 0
    xpt = cands[0]
    try:
        try:
            os.chmod(xpt, 0o644)
        except Exception:  # noqa: BLE001
            pass
        with open(xpt, "rb") as fh:
            df = pd.read_sas(fh, format="xport")
        rows, core = harmonise(df)
        rows["year"] = y
        if core < 6:
            print(f"  {y}: only {core} core outcomes — skip"); return 0
        if os.path.exists(STORE):
            prev = pd.read_parquet(STORE)
            pd.concat([prev, rows], ignore_index=True).to_parquet(STORE, index=False)
        else:
            rows.to_parquet(STORE, index=False)
        print(f"  {y}: +{len(rows):,} rows (core outcomes {core}/11)")
        return len(rows)
    except Exception as e:  # noqa: BLE001
        print(f"  {y}: read failed ({type(e).__name__}: {e})"); return 0
    finally:
        for c in cands:
            try:
                os.remove(c)
            except Exception:  # noqa: BLE001
                pass


def main(years):
    total = 0
    for y in years:
        total += do_year(int(y))
    final = pd.read_parquet(STORE)
    print(f"MEGASET: {len(final):,} rows across {final['year'].nunique()} years -> {STORE} "
          f"({os.path.getsize(STORE)/1e6:.0f} MB)")


if __name__ == "__main__":
    yrs = sys.argv[1:] or list(range(2011, 2024))
    main(yrs)
