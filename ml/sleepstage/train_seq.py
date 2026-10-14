"""Whole-night sequence model for 4-class sleep staging from ECG-derived features.
Conv1d(F→32, k=5) → ReLU → BiGRU(32) → Linear(64→4), ~15k params, trained on HMC with subject-wise 5-fold CV,
external test on slpdb. Small on purpose: it is ported to Swift (KYSleepStager) and runs on the phone.
usage: train_seq.py [epochs]  → metrics + seq_model.json"""
import glob, json, os, sys
import numpy as np
import torch, torch.nn as nn
from train import build, kappa, report, D, V
from features import NAMES, normalise_night

torch.manual_seed(0); np.random.seed(0)

class Stager(nn.Module):
    def __init__(self, f, h=32):
        super().__init__()
        self.conv = nn.Conv1d(f, h, 5, padding=2)
        self.gru = nn.GRU(h, h, batch_first=True, bidirectional=True)
        self.out = nn.Linear(2 * h, 4)
        self.drop = nn.Dropout(0.2)
    def forward(self, x):                      # x: (B, T, F)
        z = torch.relu(self.conv(x.transpose(1, 2))).transpose(1, 2)
        z, _ = self.gru(self.drop(z))
        return self.out(self.drop(z))

def nights(kind, names):
    """Per-night normalised features (no context columns: the network learns context) + labels."""
    from train import load_night
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex: raw = list(ex.map(lambda n: load_night(kind, n), names))
    out = []
    for F, y in raw:
        G = normalise_night(F); ok = ~np.isnan(F[:, 0])
        y = np.where(ok, y, -1)                # epochs without beats: no label, still in the sequence
        out.append((G.astype(np.float32), y))
    return out

def train(data, epochs, w):
    m = Stager(len(NAMES)); opt = torch.optim.AdamW(m.parameters(), 2e-3, weight_decay=1e-3)
    lossf = nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32), ignore_index=-1)
    for ep in range(epochs):
        m.train()
        for i in np.random.permutation(len(data)):
            G, y = data[i]
            # random crop for augmentation (keeps whole-night context most of the time)
            s = np.random.randint(0, max(1, len(y) - 600)) if np.random.rand() < 0.5 else 0
            x = torch.tensor(G[s:]).unsqueeze(0); t = torch.tensor(y[s:], dtype=torch.long).unsqueeze(0)
            loss = lossf(m(x).reshape(-1, 4), t.reshape(-1))
            opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step()
    return m

def predict(m, G):
    m.eval()
    with torch.no_grad(): return torch.softmax(m(torch.tensor(G).unsqueeze(0))[0], -1).numpy()

if __name__ == "__main__":
    E = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    hmc = sorted(os.path.basename(f)[4:-4] for f in glob.glob(f"{D}/data/hmc_*.bin"))
    data = nights("hmc", hmc)
    ally = np.concatenate([y[y >= 0] for _, y in data]); prior = np.bincount(ally, minlength=4) / len(ally)
    w = list((1 / prior) / (1 / prior).mean() * 0.5 + 0.5)
    print(f"HMC nights {len(data)}, epochs {len(ally)}, prior {np.round(prior, 3)}")
    folds = np.arange(len(data)) % 5; ys, ps = [], []
    for f in range(5):
        tr = [data[i] for i in range(len(data)) if folds[i] != f]
        m = train(tr, E, w)
        for i in range(len(data)):
            if folds[i] != f: continue
            G, y = data[i]; P = predict(m, G); ok = y >= 0
            ys.append(y[ok]); ps.append(P.argmax(1)[ok])
        print(f"fold {f} done", flush=True)
    k, C = report(f"BiGRU CV ({E} epochs)", ys, ps)
    print("confusion (rows true W/L/D/R):\n", C.astype(int))
    m = train(data, E, w)
    slp = sorted(os.path.basename(f)[6:-4] for f in glob.glob(f"{V}/data/slpdb_*.bin"))
    if slp:
        sd = nights("slpdb", slp); ys2, ps2 = [], []
        for G, y in sd:
            P = predict(m, G); ok = y >= 0; ys2.append(y[ok]); ps2.append(P.argmax(1)[ok])
        report("slpdb external", ys2, ps2)
    sdict = {k2: v.detach().numpy().tolist() for k2, v in m.state_dict().items()}
    json.dump({"arch": "conv5-bigru32-linear", "features": NAMES, "classes": ["Wake", "Light", "Deep", "REM"],
               "state": sdict, "cv_kappa": k, "trained_on": f"HMC {len(data)} nights"}, open(f"{D}/seq_model.json", "w"))
    print("→ seq_model.json")
