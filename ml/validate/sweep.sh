#!/bin/bash
# usage: sweep.sh TH DELAY TSLOPE "records..."  → prints Se/+P over the records
cd ~/telomy-lab/validate; tag="th$1_d$2_t$3"; mkdir -p sweep/$tag
for r in $4; do echo $r; done | xargs -P 8 -I{} sh -c "KY_TH=$1 KY_DELAY=$2 KY_TSLOPE=$3 ~/telomy-lab/ky-e-b1/KYECG/.build/release/kyval data/{}.bin sweep/$tag/{}.json"
~/telomy-app/.venv-tools/bin/python - "$tag" $4 <<'PY'
import json, sys, os, numpy as np
tag, recs = sys.argv[1], sys.argv[2:]
T=F=P=0
for r in recs:
    m=json.load(open(f"data/{r}.json")); o=json.load(open(f"sweep/{tag}/{r}.json"))
    ref=np.array(sorted(b[0] for b in m["beats"] if b[0]>300)); det=np.array(sorted(b for b in o["beats"] if b>300))
    i=j=tp=0
    while i<len(ref) and j<len(det):
        if abs(ref[i]-det[j])<=15: tp+=1;i+=1;j+=1
        elif det[j]<ref[i]: j+=1
        else: i+=1
    T+=tp;F+=len(ref)-tp;P+=len(det)-tp
print(f"{tag:22s} Se {100*T/(T+F):6.2f}  +P {100*T/(T+P):6.2f}  F1 {200*T/(2*T+F+P):6.2f}")
PY
