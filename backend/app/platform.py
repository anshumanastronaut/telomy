"""Platform configuration — the engine that makes the wellness-centre and doctor products modular and fully
customisable. Everything a centre or a doctor would want to tailor is DATA, not code:

  * org_config   — which modules are on for this org (scheduling, memberships, therapies, inventory, telehealth,
                   clinical notes, billing…), plus branding (name, colours, logo). Centres turn modules on/off.
  * catalog      — every configurable type: service/therapy types, membership plans & packages, rooms/resources,
                   staff roles & permissions, clinical note templates, appointment types. Add a new therapy or plan
                   in one row — no deploy. (Modelled on the "custom form builder" of DrChrono/Jane and the module
                   toggles of Zenoti/Mindbody.)
  * custom_fields— extra fields on any entity (member, patient, service, therapy, booking, clinical note), with type,
                   options, section and order — so a centre or doctor shapes the forms to their own taste.

Built so a non-engineer can configure a centre or a clinic end to end through these three tables; the operational
modules (centre.py, clinic.py) read this config to drive their screens, forms and pricing.
"""
import json
import time

from . import db, engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS org_config (org TEXT PRIMARY KEY, kind TEXT, modules TEXT, branding TEXT, settings TEXT, updated_at REAL);
CREATE TABLE IF NOT EXISTS catalog (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, kind TEXT, key TEXT, name TEXT,
  data TEXT, active INTEGER DEFAULT 1, sort INTEGER DEFAULT 0, created_at REAL);
CREATE INDEX IF NOT EXISTS ix_catalog ON catalog(org, kind, active);
CREATE TABLE IF NOT EXISTS custom_fields (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, entity TEXT, key TEXT,
  label TEXT, type TEXT, options TEXT, required INTEGER DEFAULT 0, section TEXT, sort INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_custom_fields ON custom_fields(org, entity);
"""

# The modules a centre/clinic can switch on. Off ones simply don't render.
MODULES = {
    "scheduling": "Appointments & room/resource booking", "memberships": "Memberships, packages & recurring billing",
    "therapies": "Therapy / service delivery & outcomes", "clinical_notes": "Clinical charting & note templates",
    "eprescribing": "Prescriptions (clinician-signed)", "telehealth": "Video consults", "inventory": "Stock & retail",
    "billing": "Invoices & payments", "crm": "Leads, campaigns & retention", "reports": "Dashboards & analytics",
    "wearables": "Connected devices & longitudinal data", "labs": "Lab orders & results",
}
# Configurable catalog kinds and the shape of each item's `data`.
CATALOG_KINDS = {
    "service_type": "A bookable service/therapy (duration, price, resources, category, custom fields)",
    "membership_plan": "A plan/package (price, cycle, entitlements, freeze rules)",
    "resource": "A room, device or chair that a booking consumes",
    "role": "A staff role and its permissions",
    "note_template": "A clinical note template (sections/fields)",
    "appointment_type": "An appointment kind (duration, colour)",
    "module": "A custom module tab the org defined",
}
FIELD_TYPES = {"text", "number", "select", "multiselect", "bool", "date", "time", "duration", "money", "textarea", "rating"}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


# ---- org config -------------------------------------------------------------------------------------------------

def _now():
    return time.time()


def get_org(org: str = "default") -> dict:
    r = db.one("SELECT * FROM org_config WHERE org = ?", (org,))
    if not r:
        return {"org": org, "kind": "centre", "modules": {k: k in ("scheduling", "therapies", "memberships", "reports", "wearables") for k in MODULES},
                "branding": {"name": "Telomy Centre", "primary": "#137a5f"}, "settings": {}}
    return {"org": r["org"], "kind": r["kind"], "modules": db.unj(r["modules"], {}), "branding": db.unj(r["branding"], {}),
            "settings": db.unj(r["settings"], {})}


def set_org(org: str, kind: str | None = None, modules: dict | None = None, branding: dict | None = None, settings: dict | None = None) -> dict:
    cur = get_org(org)
    kind = kind or cur["kind"]
    modules = {**cur["modules"], **(modules or {})}
    branding = {**cur["branding"], **(branding or {})}
    settings = {**cur["settings"], **(settings or {})}
    db.exec_("INSERT OR REPLACE INTO org_config (org, kind, modules, branding, settings, updated_at) VALUES (?,?,?,?,?,?)",
             (org, kind, db.j(modules), db.j(branding), db.j(settings), _now()))
    return get_org(org)


def enabled_modules(org: str = "default") -> list[str]:
    m = get_org(org)["modules"]
    return [k for k, on in m.items() if on]


# ---- catalog (service types, plans, resources, roles, templates…) -----------------------------------------------

def add_catalog(org: str, kind: str, name: str, data: dict | None = None, key: str | None = None) -> dict:
    if kind not in CATALOG_KINDS:
        raise ValueError(f"kind must be one of {sorted(CATALOG_KINDS)}")
    if not name.strip():
        raise ValueError("name is required")
    import re
    key = key or re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]
    cid = db.exec_("INSERT INTO catalog (org, kind, key, name, data, active, sort, created_at) VALUES (?,?,?,?,?,1,?,?)",
                   (org, kind, key, name.strip(), db.j(data or {}), _catalog_count(org, kind), _now()))
    return catalog_item(cid)


def _catalog_count(org, kind):
    return db.one("SELECT COUNT(*) AS n FROM catalog WHERE org = ? AND kind = ?", (org, kind))["n"]


def catalog_item(cid: int) -> dict | None:
    r = db.one("SELECT * FROM catalog WHERE id = ?", (cid,))
    return {**r, "data": db.unj(r["data"], {})} if r else None


def list_catalog(org: str, kind: str, include_inactive: bool = False) -> list[dict]:
    q = "SELECT * FROM catalog WHERE org = ? AND kind = ?" + ("" if include_inactive else " AND active = 1") + " ORDER BY sort, id"
    return [{**r, "data": db.unj(r["data"], {})} for r in db.rows(q, (org, kind))]


def update_catalog(cid: int, name: str | None = None, data: dict | None = None, active: bool | None = None, sort: int | None = None) -> dict:
    it = catalog_item(cid)
    if not it:
        raise ValueError("no such catalog item")
    name = name if name is not None else it["name"]
    data = {**it["data"], **data} if data is not None else it["data"]
    active = it["active"] if active is None else (1 if active else 0)
    sort = it["sort"] if sort is None else sort
    db.exec_("UPDATE catalog SET name = ?, data = ?, active = ?, sort = ? WHERE id = ?", (name, db.j(data), active, sort, cid))
    return catalog_item(cid)


# ---- custom fields ----------------------------------------------------------------------------------------------

def add_field(org: str, entity: str, label: str, type: str, options: list | None = None, required: bool = False,
              section: str = "", key: str | None = None) -> dict:
    if type not in FIELD_TYPES:
        raise ValueError(f"type must be one of {sorted(FIELD_TYPES)}")
    import re
    key = key or re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40]
    sort = db.one("SELECT COUNT(*) AS n FROM custom_fields WHERE org = ? AND entity = ?", (org, entity))["n"]
    fid = db.exec_("INSERT INTO custom_fields (org, entity, key, label, type, options, required, section, sort) VALUES (?,?,?,?,?,?,?,?,?)",
                   (org, entity, key, label.strip(), type, db.j(options or []), 1 if required else 0, section, sort))
    return db.one("SELECT * FROM custom_fields WHERE id = ?", (fid,))


def fields_for(org: str, entity: str) -> list[dict]:
    return [{**r, "options": db.unj(r["options"], [])} for r in
            db.rows("SELECT * FROM custom_fields WHERE org = ? AND entity = ? ORDER BY sort, id", (org, entity))]


def delete_field(fid: int):
    db.exec_("DELETE FROM custom_fields WHERE id = ?", (fid,))


def validate_values(org: str, entity: str, values: dict) -> dict:
    """Validate a custom-field payload against the org's schema; returns the cleaned values or raises."""
    out = {}
    for f in fields_for(org, entity):
        v = values.get(f["key"])
        if v is None or v == "":
            if f["required"]:
                raise ValueError(f"{f['label']} is required")
            continue
        t = f["type"]
        if t == "number" or t in ("money", "rating", "duration"):
            out[f["key"]] = float(v)
        elif t == "bool":
            out[f["key"]] = bool(v)
        elif t == "select":
            if f["options"] and v not in [o["value"] if isinstance(o, dict) else o for o in f["options"]]:
                raise ValueError(f"{f['label']}: '{v}' is not an allowed option")
            out[f["key"]] = v
        elif t == "multiselect":
            out[f["key"]] = list(v) if isinstance(v, list) else [v]
        else:
            out[f["key"]] = str(v)
    return out


def form_schema(org: str, entity: str) -> dict:
    """A render-ready form schema (built-in + custom fields, grouped by section) so the app draws the form dynamically."""
    fields = fields_for(org, entity)
    sections: dict[str, list] = {}
    for f in fields:
        sections.setdefault(f["section"] or "Details", []).append(
            {"key": f["key"], "label": f["label"], "type": f["type"], "options": f["options"], "required": bool(f["required"])})
    return {"entity": entity, "sections": [{"title": s, "fields": fl} for s, fl in sections.items()]}


def overview(org: str = "default") -> dict:
    """One call for the config screen: modules, branding, and how much is configured."""
    cfg = get_org(org)
    return {**cfg, "catalog_counts": {k: _catalog_count(org, k) for k in CATALOG_KINDS},
            "custom_field_entities": {e: len(fields_for(org, e)) for e in
                                      ("member", "patient", "service", "therapy", "booking", "clinical_note")},
            "available_modules": MODULES, "catalog_kinds": CATALOG_KINDS, "field_types": sorted(FIELD_TYPES)}
