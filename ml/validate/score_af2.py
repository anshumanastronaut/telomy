"""AF screening with the P-wave gate: RR thresholds fixed (as shipped), sweep KYInsight.pWaveMax.
usage: score_af2.py OUTDIR   (kyval outputs whose af[].f = [nrmssd, shannon, tpr, cosen, pwave])"""
import json, glob, os, sys
import numpy as np
D = os.path.expanduser("~/telomy-lab/validate"); OUT = sys.argv[1]
TH = (0.12, 0.70, 0.54, 1.20, -2.2)
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
                if s0 <= t - 30 and t <= s1: lab = r; break
                if s0 <= t <= s1: lab = "MIX"; break
            rows.append((name, lab, a["f"]))
    return rows
af, nsr = load("afdb"), load("nsrdb")
train = {"afdb_04015", "afdb_04126", "afdb_04908", "afdb_05091", "afdb_06426", "afdb_07879", "afdb_08455"}
rr_ok = lambda f: f[0] > TH[0] and f[1] > TH[1] and TH[2] < f[2] < TH[3] and f[3] > TH[4]
def dec(f, pmax): return rr_ok(f) and (pmax is None or len(f) < 5 or f[4] < 0 or f[4] < pmax)
def ev(rows, pmax, lab):
    v = [dec(f, pmax) for _, l, f in rows if l == lab]
    return np.mean(v) if v else np.nan
pa = np.array([f[4] for _, l, f in af if l == "AFIB" and len(f) > 4 and f[4] >= 0])
pn = np.array([f[4] for _, l, f in af + nsr if l == "N" and len(f) > 4 and f[4] >= 0])
print(f"P-wave score  AF windows: median {np.median(pa):.2f} (p90 {np.percentile(pa, 90):.2f})   "
      f"non-AF: median {np.median(pn):.2f} (p10 {np.percentile(pn, 10):.2f})")
tr = [r for r in af if r[0] in train]; te = [r for r in af if r[0] not in train]
print(f"{'pWaveMax':>9} | {'train Se':>8} {'Sp':>6} | {'test Se':>7} {'Sp':>6} | NSR FP windows")
for pmax in [None, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]:
    print(f"{str(pmax):>9} | {100*ev(tr, pmax, 'AFIB'):7.1f}% {100*(1-ev(tr, pmax, 'N')):5.1f}% | "
          f"{100*ev(te, pmax, 'AFIB'):6.1f}% {100*(1-ev(te, pmax, 'N')):5.1f}% | {100*np.mean([dec(f, pmax) for _, _, f in nsr]):5.2f}%")
