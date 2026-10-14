import json, glob, os, sys, itertools
import numpy as np
D = os.path.expanduser("~/telomy-lab/validate"); OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
def load(db):
    rows = []
    for f in sorted(glob.glob(f"{D}/data/{db}_*.json")):
        name = os.path.basename(f)[:-5]; m = json.load(open(f))
        try: o = json.load(open(f"{D}/{OUT}/{name}.json"))
        except FileNotFoundError: continue
        segs = m.get("rhythm", [])
        for a in o["af"]:
            t = a["t"]; lab = "N"
            for s0, s1, r in segs:
                if s0 <= t - 30 and t <= s1: lab = r; break     # whole 60-s window inside one rhythm
                if s0 <= t <= s1: lab = "MIX"; break
            rows.append((name, lab, a["f"], a["af"]))
    return rows
af, nsr = load("afdb"), load("nsrdb")
train = {"afdb_04015", "afdb_04126", "afdb_04908", "afdb_05091", "afdb_06426", "afdb_07879", "afdb_08455"}
def evaluate(rows, nsr_rows, th):
    def dec(f): return f[0] > th[0] and f[1] > th[1] and th[2] < f[2] < th[3] and f[3] > th[4]
    pos = [dec(f) for _, l, f, _ in rows if l == "AFIB"]; neg = [dec(f) for _, l, f, _ in rows if l == "N"]
    fpn = [dec(f) for _, _, f, _ in nsr_rows]
    return np.mean(pos) if pos else np.nan, 1 - np.mean(neg) if neg else np.nan, np.mean(fpn) if fpn else np.nan
tr = [r for r in af if r[0] in train]; te = [r for r in af if r[0] not in train]
best = None
for th in itertools.product([0.06, 0.08, 0.1, 0.12, 0.15], [0.4, 0.5, 0.6, 0.7, 0.8], [0.4, 0.54], [1.2, 1.4], [-2.2, -1.9, -1.6, -1.4, -1.2, -1.0]):
    se, sp, _ = evaluate(tr, [], th)
    score = se + sp
    if best is None or score > best[0]: best = (score, th, se, sp)
th = best[1]
print("calibrated thresholds (nrmssd, shannon, tprLo, tprHi, cosen):", th)
print(f"TRAIN AF records: Se {100*best[2]:.1f}%  Sp {100*best[3]:.1f}%")
se, sp, _ = evaluate(te, [], th); print(f"TEST  AF records ({len(set(r[0] for r in te))}): Se {100*se:.1f}%  Sp {100*sp:.1f}%  (per 60-s window)")
_, _, fp = evaluate([], nsr, th)
hours = len(nsr) * 5 / 3600
print(f"NSR false-positive windows: {100*fp:.2f}% of {len(nsr)} windows ({hours:.0f} h)")
cur = (0.10, 0.55, 0.54, 1.25, -1.6)
se, sp, _ = evaluate(te, [], cur); _, _, fp = evaluate([], nsr, cur)
print(f"(current defaults on TEST: Se {100*se:.1f}% Sp {100*sp:.1f}% NSR FP {100*fp:.2f}%)")
