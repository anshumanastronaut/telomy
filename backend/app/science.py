"""Science registry — the engine's open edge. New findings (a fresh paper, a new guideline, a lab-specific range, a
new cellular mechanism) can be added as DATA and take effect immediately, without changing engine code or redeploying.

A finding is a row with a `kind`, a JSON `payload`, a `citation`, an `evidence` grade (A–D), who added it, when, and an
`active` flag. The engine reads active findings at runtime and merges them with its built-in knowledge:

  * cross_panel_rule — a declarative lab-pattern rule. When its conditions hold for the person, it fires an insight.
      payload: {conditions: [{marker, op, value?}], title, body, markers, confidence?, medical?, direction?}
      op ∈ >,<,>=,<=,==, "high" (above the marker's optimal range), "low", "present". Conditions are AND-ed.
  * marker_range — override a marker's optimal low/high (e.g. a guideline tightens the ApoB target).
      payload: {marker, low?, high?}
  * cellular_effect — add a mechanism to the cellular KB (same shape as cellular.EFFECTS entries).
      payload: {kind, name, terms, cells, site, pathway, mechanism, markers, direction}

Everything is append-only and reversible: deactivate a finding and its effect disappears. This is how "integrate the new
science" works operationally — add a row, cite it, grade it; the whole engine (insights, Sinc, cellular answers, blood
age via the range override) uses it from the next request.
"""
import json

from . import db, engine
from .catalog import MARKERS

SCHEMA = """
CREATE TABLE IF NOT EXISTS science_findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, payload TEXT, citation TEXT, evidence TEXT,
  added_by TEXT, added_on TEXT, active INTEGER DEFAULT 1, note TEXT);
"""
_OPS = {">": lambda a, b: a > b, "<": lambda a, b: a < b, ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b, "==": lambda a, b: a == b}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def _active(kind: str) -> list[dict]:
    try:
        rows = db.rows("SELECT * FROM science_findings WHERE kind = ? AND active = 1 ORDER BY id", (kind,))
    except Exception:  # noqa: BLE001 — table not created yet
        return []
    out = []
    for r in rows:
        try:
            out.append({**r, "payload": json.loads(r["payload"])})
        except (TypeError, ValueError):
            pass
    return out


# ---- marker range overrides (guideline updates) -----------------------------------------------------------------

def range_overrides() -> dict[str, tuple]:
    out = {}
    for f in _active("marker_range"):
        p = f["payload"]
        m = p.get("marker")
        if m in MARKERS:
            lo = p.get("low", MARKERS[m][3])
            hi = p.get("high", MARKERS[m][4])
            out[m] = (lo, hi)
    return out


def effective_range(marker_id: str) -> tuple:
    """A marker's optimal (low, high), with any active guideline override applied."""
    ov = range_overrides().get(marker_id)
    if ov:
        return ov
    return (MARKERS[marker_id][3], MARKERS[marker_id][4]) if marker_id in MARKERS else (None, None)


# ---- declarative cross-panel rules ------------------------------------------------------------------------------

def _val(L, m):
    r = L.get(m)
    return (r["value_num"] if r and r["value_num"] is not None else None)


def _cond_holds(cond: dict, L: dict) -> bool:
    m = cond.get("marker")
    if m not in MARKERS:
        return False
    v = _val(L, m)
    op = cond.get("op")
    if op == "present":
        return m in L
    if v is None:
        return False
    lo, hi = effective_range(m)
    if op == "high":
        return hi is not None and v > hi
    if op == "low":
        return lo is not None and v < lo
    fn = _OPS.get(op)
    return bool(fn and cond.get("value") is not None and fn(v, cond["value"]))


def dynamic_insights() -> list[dict]:
    """Evaluate every active cross_panel_rule against the person's latest values; fire the ones that hold."""
    L = engine.latest_values()
    out = []
    for f in _active("cross_panel_rule"):
        p = f["payload"]
        conds = p.get("conditions", [])
        if not conds or not all(_cond_holds(c, L) for c in conds):
            continue
        markers = p.get("markers", [c["marker"] for c in conds if c.get("marker") in MARKERS])
        ev = [{"type": "marker", "marker_id": m, "name": MARKERS[m][0], "value": _val(L, m), "unit": MARKERS[m][2],
               "day": L[m]["collected_on"], "status": L[m]["status"]} for m in markers if m in L]
        # fill {marker} and {marker.value} placeholders in the body
        body = p.get("body", "")
        for m in markers:
            if m in MARKERS:
                body = body.replace("{" + m + "}", str(_val(L, m))).replace("{" + m + ".name}", MARKERS[m][0])
        out.append({
            "id": engine._iid("science", f["id"]), "kind": "cross_panel", "title": p.get("title", "Finding"),
            "body": body + f"  (Added from the literature: {f.get('citation', '')}.)", "confidence": float(p.get("confidence", 0.6)),
            "n": len(ev), "direction": p.get("direction", "neutral"), "medical": bool(p.get("medical", True)), "evidence": ev,
            "receipts": {"method": "Science-registry rule (added as data, not code)", "rule_id": f["id"],
                         "citation": f.get("citation"), "evidence_grade": f.get("evidence"), "version": engine.ENGINE_VERSION}})
    return out


# ---- cellular-effect extensions ---------------------------------------------------------------------------------

def extra_cellular_effects() -> list[dict]:
    out = []
    for f in _active("cellular_effect"):
        p = f["payload"]
        if p.get("name") and p.get("markers"):
            out.append({"evidence": f.get("evidence", "C"), "citation": f.get("citation", ""), **p})
    return out


# ---- registry management ----------------------------------------------------------------------------------------

def add_finding(kind: str, payload: dict, citation: str, evidence: str = "C", added_by: str = "api", note: str = "") -> dict:
    init()
    if kind not in ("cross_panel_rule", "marker_range", "cellular_effect"):
        raise ValueError("kind must be cross_panel_rule, marker_range or cellular_effect")
    if evidence not in ("A", "B", "C", "D"):
        raise ValueError("evidence must be A, B, C or D")
    if kind == "marker_range" and payload.get("marker") not in MARKERS:
        raise ValueError("unknown marker")
    if kind == "cross_panel_rule":
        for c in payload.get("conditions", []):
            if c.get("marker") not in MARKERS:
                raise ValueError(f"unknown marker in condition: {c.get('marker')}")
            if c.get("op") not in list(_OPS) + ["high", "low", "present"]:
                raise ValueError(f"bad op: {c.get('op')}")
    fid = db.exec_("INSERT INTO science_findings (kind, payload, citation, evidence, added_by, added_on, active, note) VALUES (?,?,?,?,?,?,1,?)",
                   (kind, json.dumps(payload), citation[:300], evidence, added_by[:60], engine.now_iso(), note[:300]))
    engine.regenerate_insights()
    return {"id": fid, "kind": kind, "active": True}


def list_findings(include_inactive: bool = False) -> list[dict]:
    init()
    q = "SELECT * FROM science_findings" + ("" if include_inactive else " WHERE active = 1") + " ORDER BY id DESC"
    return [{**r, "payload": json.loads(r["payload"]) if r["payload"] else {}} for r in db.rows(q)]


def set_active(fid: int, active: bool) -> dict:
    db.exec_("UPDATE science_findings SET active = ? WHERE id = ?", (1 if active else 0, fid))
    if not active:  # regenerate_insights only upserts; a removed rule's insight must be pruned explicitly
        try:
            db.exec_("DELETE FROM insights WHERE id = ?", (engine._iid("science", fid),))
        except Exception:  # noqa: BLE001
            pass
    engine.regenerate_insights()
    return {"id": fid, "active": active}
