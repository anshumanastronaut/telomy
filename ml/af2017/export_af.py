"""Export the CinC2017 GBDT (150 iters × 4 classes, ≤15 leaves) to JSON for KYRhythmModel.swift and self-check."""
import json, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from train_af import NAMES
X = np.load('X.npy'); y = np.load('y.npy'); keep = [i for i, n in enumerate(NAMES) if n != 'n_beats']; Xk = X[:, keep]
m = HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=15, learning_rate=0.08, class_weight='balanced', random_state=0).fit(Xk, y)
trees = []
for it in m._predictors:
    row = []
    for tp in it:
        nd = tp.nodes
        row.append({"f": nd["feature_idx"].tolist(), "t": [float(v) for v in nd["num_threshold"]], "l": nd["left"].tolist(), "r": nd["right"].tolist(),
                    "leaf": nd["is_leaf"].astype(int).tolist(), "v": [float(v) for v in nd["value"]], "ml": nd["missing_go_to_left"].astype(int).tolist()})
    trees.append(row)
base = np.asarray(m._baseline_prediction).reshape(-1).tolist()
def predict(x):
    raw = np.array(base, float)
    for it in trees:
        for c, t in enumerate(it):
            i = 0
            while not t["leaf"][i]: i = t["l"][i] if x[t["f"][i]] <= t["t"][i] else t["r"][i]
            raw[c] += t["v"][i]
    e = np.exp(raw - raw.max()); return e / e.sum()
ref = m.predict_proba(Xk[:300]); mine = np.array([predict(r) for r in Xk[:300]])
print("self-check max diff", np.abs(ref - mine).max())
json.dump({"features": [NAMES[i] for i in keep], "classes": ["Normal", "AF", "Other", "Noisy"], "baseline": base, "trees": trees,
           "trained_on": "PhysioNet CinC 2017 (8528 single-lead ECGs) via Telomy beat detector at 100 Hz", "af_threshold": 0.5},
          open('rhythm_model.json', 'w'), separators=(',', ':'))
import os; print("size KB", os.path.getsize('rhythm_model.json') // 1024)
