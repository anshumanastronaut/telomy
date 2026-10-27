"""Mine FDA FAERS (~20.7M adverse-event reports, via openFDA) for disproportionality signals on every drug /
hormone in the geroprotector corpus, so Telomy's safety screen is data-backed, not only hand-coded.

For a drug D and reaction R across N total reports:
    a = reports with D and R      n_D = reports with D      n_R = reports with R
    ROR = (a·d)/(b·c)  where b=n_D−a, c=n_R−a, d=N−n_D−n_R+a
    PRR = (a/n_D) / ((n_R−a)/(N−n_D))
    95% CI(lnROR): ±1.96·sqrt(1/a+1/b+1/c+1/d)
A reaction is a SIGNAL if a≥3 and ROR lower-95%CI > 1 (a standard pharmacovigilance threshold).

This is disproportionality (reporting bias ≠ causation) — a monitoring/consent aid, not a verdict. FAERS is
drug-centric, so consumer supplements have little data here; those stay on the hand-coded screen.

Run:  python -I research/safety/build_faers_signals.py        (no API key needed; ~150 calls, well under the
      1000/day anonymous limit). Writes backend/app/assets/safety/faers_signals.json.
"""
from __future__ import annotations
import json, math, os, time, urllib.parse, urllib.request

BASE = "https://api.fda.gov/drug/event.json"
API_KEY = os.environ.get("OPENFDA_API_KEY")   # optional: lifts the anon 1000/day limit; not required here
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "app", "assets", "safety", "faers_signals.json")

# geroprotector id -> (FAERS generic/substance name, note). Class drugs use a representative agent.
DRUGS = {
    "metformin":        ("METFORMIN", None),
    "rapamycin":        ("SIROLIMUS", "rapamycin = sirolimus"),
    "acarbose":         ("ACARBOSE", None),
    "sglt2i":           ("EMPAGLIFLOZIN", "class, representative agent"),
    "glp1_ra":          ("SEMAGLUTIDE", "class, representative agent"),
    "low_dose_lithium": ("LITHIUM", "FAERS includes therapeutic-dose lithium"),
    "statin":           ("ATORVASTATIN", "class, representative agent"),
    "pcsk9":            ("EVOLOCUMAB", "class, representative agent"),
    "low_dose_aspirin": ("ASPIRIN", None),
    "trt":              ("TESTOSTERONE", None),
    "dhea":             ("DEHYDROEPIANDROSTERONE", None),
    "melatonin":        ("MELATONIN", None),
    "growth_hormone":   ("SOMATROPIN", None),
    "mht":              ("ESTRADIOL", None),
    "tesamorelin":      ("TESAMORELIN", None),
    "dq_senolytic":     ("DASATINIB", "senolytic D+Q uses dasatinib — FAERS reflects its oncology use/toxicity"),
}

MIN_A = 3            # minimum co-reports to consider a signal
TOP_REACTIONS = 15   # reactions to pull per drug (search-scoped; dedup across drugs keeps total calls modest)
KEEP_SIGNALS = 10    # strongest signals to store per drug


def _get(params: dict, tries: int = 4) -> dict:
    if API_KEY:
        params = {**params, "api_key": API_KEY}
    url = BASE + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "telomy-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                return {"_error": str(e)}
            time.sleep(1.5 * (i + 1))
    return {"_error": "unreachable"}


def _total(search: str) -> int:
    d = _get({"search": search, "limit": 1})
    return int(d.get("meta", {}).get("results", {}).get("total", 0)) if "_error" not in d else 0


def _reaction_counts(search: str) -> list[tuple[str, int]]:
    d = _get({"search": search, "count": "patient.reaction.reactionmeddrapt.exact", "limit": TOP_REACTIONS})
    return [(x["term"], int(x["count"])) for x in d.get("results", [])] if "_error" not in d else []




def ror(a: int, n_d: int, n_r: int, n: int) -> dict:
    b, c = n_d - a, n_r - a
    d = n - n_d - n_r + a
    if min(a, b, c, d) <= 0:
        return {}
    _ror = (a * d) / (b * c)
    se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    lo, hi = math.exp(math.log(_ror) - 1.96 * se), math.exp(math.log(_ror) + 1.96 * se)
    prr = (a / n_d) / (c / (n - n_d)) if (c and n - n_d) else 0.0
    return {"a": a, "ror": round(_ror, 2), "ror_lo": round(lo, 2), "ror_hi": round(hi, 2), "prr": round(prr, 2)}


def main() -> None:
    N = int(_get({"limit": 1}).get("meta", {}).get("results", {}).get("total", 0)) or 20_692_690  # cheap, anon-OK
    print(f"FAERS total reports: {N:,}", flush=True)
    reaction_total_cache: dict[str, int] = {}   # n_R per reaction, filled on demand via search totals (anon-OK)
    out = {"meta": {"source": "FDA FAERS via openFDA (api.fda.gov/drug/event)", "total_reports": N,
                    "method": f"disproportionality: ROR + PRR with 95pct CI; signal if a>={MIN_A} and ROR_lo>1",
                    "caveat": "Reporting disproportionality is not causation; a monitoring/consent aid only."},
           "drugs": {}}
    for gid, (name, note) in DRUGS.items():
        dsearch = f'patient.drug.openfda.generic_name.exact:"{name}"'
        n_d = _total(dsearch)
        if n_d < 30:  # try substance_name fallback
            dsearch = f'patient.drug.openfda.substance_name.exact:"{name}"'
            n_d = _total(dsearch)
        counts = _reaction_counts(dsearch)
        print(f"  {gid:16s} {name:24s} n_D={n_d:>9,}  reactions={len(counts)}", flush=True)
        signals = []
        for reaction, a in counts:
            if a < MIN_A:
                continue
            n_r = reaction_total_cache.get(reaction)
            if n_r is None:   # search-scoped total (anon-OK); cached so shared reactions cost one call total
                n_r = _total(f'patient.reaction.reactionmeddrapt.exact:"{reaction}"')
                reaction_total_cache[reaction] = n_r
            stats = ror(a, n_d, n_r, N)
            if stats and stats["ror_lo"] > 1:
                signals.append({"reaction": reaction.title(), **stats})
        signals.sort(key=lambda s: -s["ror_lo"])
        out["drugs"][gid] = {"faers_name": name, "note": note, "n_reports": n_d,
                             "signals": signals[:KEEP_SIGNALS]}
        time.sleep(0.4)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(os.path.abspath(OUT), "w") as f:
        json.dump(out, f, indent=1)
    tot = sum(len(v["signals"]) for v in out["drugs"].values())
    print(f"\nwrote {os.path.abspath(OUT)}  ({len(out['drugs'])} drugs, {tot} signals)")


if __name__ == "__main__":
    main()
