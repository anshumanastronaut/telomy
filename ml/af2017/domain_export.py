"""Domain-adapted rhythm model in the KYRhythmModel.swift format (20 features: train_af.NAMES without n_beats).
Held-out check (afdb TRAIN_AF / first half of nsrdb used for training, rest tested) with 2-window confirmation, then the
final model trained on CinC 2017 + all long-record windows → rhythm_model.json (af_threshold 0.63, persist_windows 2)."""
import json, os, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from train_af import NAMES

D = os.path.expanduser("~/telomy-lab/af2017")
TRAIN_AF = {"afdb_04015", "afdb_04126", "afdb_04908", "afdb_05091", "afdb_06426", "afdb_07879", "afdb_08455"}
keep = [i for i, n in enumerate(NAMES) if n != "n_beats"]
Xc = np.load(f"{D}/X.npy")[:, keep]; yc = np.load(f"{D}/y.npy")
recs = sorted(f[4:-4] for f in os.listdir(D) if f.startswith("win_") and f.endswith(".npz"))
W = {r: np.load(f"{D}/win_{r}.npz") for r in recs}
nsr = [r for r in recs if r.startswith("nsrdb")]; nsr_train = set(nsr[: len(nsr) // 2])
istrain = lambda r: r in TRAIN_AF or r in nsr_train
mk = lambda: HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=15, learning_rate=0.08, class_weight="balanced", random_state=0)
def stack(sel):
    xs, ys = [Xc], [yc]
    for r in recs:
        if not sel(r): continue
        k = W[r]["L"] >= 0
        if k.sum(): xs.append(W[r]["X"][k][:, keep]); ys.append(np.where(W[r]["L"][k] == 1, 1, 0))
    return np.concatenate(xs), np.concatenate(ys)
persist = lambda p: p & (np.r_[False, p[:-1]] | np.r_[p[1:], False])
TH = 0.63
m = mk().fit(*stack(istrain))
tp = fn = fp = tn = 0; nf = nn = 0
for r in recs:
    if istrain(r): continue
    X, L = W[r]["X"][:, keep], W[r]["L"]
    pr = persist(m.predict_proba(X)[:, 1] > TH)
    if r.startswith("afdb"):
        k = L >= 0; p, l = pr[k], L[k] == 1; tp += (p & l).sum(); fn += (~p & l).sum(); fp += (p & ~l).sum(); tn += (~p & ~l).sum()
    else: nf += pr.sum(); nn += len(pr)
print(f"held-out: afdb AF Se {tp/(tp+fn):.3f} Sp {tn/(tn+fp):.3f} | nsrdb false-alarm windows {nf/nn:.4f}")

m = mk().fit(*stack(lambda r: True))
trees = [[{"f": t.nodes["feature_idx"].tolist(), "t": [float(v) for v in t.nodes["num_threshold"]], "l": t.nodes["left"].tolist(),
           "r": t.nodes["right"].tolist(), "leaf": t.nodes["is_leaf"].astype(int).tolist(), "v": [float(v) for v in t.nodes["value"]],
           "ml": t.nodes["missing_go_to_left"].astype(int).tolist()} for t in it] for it in m._predictors]
json.dump({"features": [NAMES[i] for i in keep], "classes": ["Normal", "AF", "Other", "Noisy"],
           "baseline": np.asarray(m._baseline_prediction).reshape(-1).tolist(), "trees": trees, "af_threshold": TH, "persist_windows": 2,
           "trained_on": f"CinC 2017 (8528) + afdb/nsrdb 60-s windows; held-out AF Se {tp/(tp+fn):.2f} Sp {tn/(tn+fp):.3f}, nsrdb false alarms {100*nf/nn:.2f}%"},
          open(f"{D}/rhythm_model.json", "w"), separators=(",", ":"))
print("trees", len(trees), "size KB", os.path.getsize(f"{D}/rhythm_model.json") // 1024)
