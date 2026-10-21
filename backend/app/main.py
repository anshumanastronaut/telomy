"""Telomy API (FastAPI). Run: uvicorn app.main:app --host 0.0.0.0 --port 8787"""
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

import math
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from . import config  # noqa: F401  (loads backend/.env first)
from . import whoop
from . import cgm
from . import accounts as acctmod  # noqa: E402  (module; /accounts route shadows the name)
from . import vitals as vitalsmod  # noqa: E402
from . import bioage  # noqa: E402
from . import platform as pform  # noqa: E402
from . import centre as centremod  # noqa: E402
from . import clinic as clinicmod  # noqa: E402
from . import fulfillment, goals, interop, staff as staffmod, tenancy as tenancymod, billing as billingmod  # noqa: E402
from . import science  # noqa: E402
from . import telomy_llm  # noqa: E402
from . import trackers  # noqa: E402
from . import activities, band, brief, db, derived, devices, diagnostics, engine, exposome, features, food, plans, predict, roles, routine, rx, seed, sinc, summaries, therapy, twin, voice
from .catalog_ext import RETEST_PREP
from .catalog import MARKERS, PANELS, RISK_GENOTYPES
from .labparse import parse_pdf

@asynccontextmanager
async def lifespan(_app):
    db.init()
    roles.init()
    plans.init()
    therapy.init()
    rx.init()
    summaries.init()
    acctmod.init()
    for mod in (voice, routine, activities, exposome, devices, band, whoop, cgm, trackers, science, vitalsmod, pform, centremod, clinicmod, fulfillment, goals, interop, staffmod, tenancymod, billingmod):
        mod.init()
    if not db.one("SELECT 1 AS x FROM profile"):
        seed.run(reset=False)
    # warm the seeded physiology validation off the request path (~8 s on the 1-core server, then cached)
    import threading
    from . import physio
    threading.Thread(target=physio.validate_prior, args=(20,), daemon=True).start()

    def _warm_whoop_day():   # keep today's WHOOP day engine warm so the app never waits ~10 s for it
        import time as _t
        from . import whoop_day
        while True:
            try:
                if db.one("SELECT 1 AS x FROM whoop_rows LIMIT 1"):
                    whoop_day.day()
                    whoop_day.store_signals()     # finished days → strain / exercise signals for the load models
                    whoop.nights(21)        # stages each new WHOOP night once (cached) so the app never waits
            except Exception:  # noqa: BLE001 — no WHOOP data / table yet
                pass
            _t.sleep(540)
    threading.Thread(target=_warm_whoop_day, daemon=True).start()
    yield


app = FastAPI(title="Telomy API", version="0.1.0", lifespan=lifespan)

# 3D twin anatomy model (BodyParts3D, © DBCLS, CC BY 4.0). Served instead of embedded in the app bundle; cached hard.
from pathlib import Path as _P
_ANATOMY = _P(__file__).resolve().parent.parent / "static" / "telomy_anatomy.glb"


@app.get("/static/telomy_anatomy.glb")
def anatomy_glb():
    if not _ANATOMY.exists():
        raise HTTPException(404, "anatomy model not built")
    return Response(_ANATOMY.read_bytes(), media_type="model/gltf-binary",
                    headers={"Cache-Control": "public, max-age=604800", "Access-Control-Allow-Origin": "*"})
# ---------------------------------------------------------------- access password (hosted deployments)
# Off when TELOMY_ACCESS_PASSWORD is unset (local Mac dev, unchanged). When set, every request needs
# `Authorization: Bearer <token>`; the token comes from POST /auth/password with the right password. The token is an
# HMAC of the password with a server secret, so changing either revokes every session. Constant-time compares and a
# small delay on failure blunt guessing.
import hashlib as _hl, hmac as _hm, os as _os, time as _t
from fastapi import Request as _Req
from fastapi.responses import JSONResponse as _JR
_PW = _os.environ.get("TELOMY_ACCESS_PASSWORD", "")
_SECRET = _os.environ.get("TELOMY_SECRET", "") or _hl.sha256(("telomy:" + _PW).encode()).hexdigest()
_OPEN = {"/auth/password", "/auth/status", "/docs", "/openapi.json", "/static/telomy_anatomy.glb", "/whoop/push", "/mgmt/auth/login", "/mgmt/auth/signup", "/mgmt/auth/status"}  # /whoop/push has its own bearer token  # model: public CC-BY anatomy, nothing personal


def _token() -> str:
    return _hm.new(_SECRET.encode(), ("v1:" + _PW).encode(), _hl.sha256).hexdigest()


@app.middleware("http")
async def _require_password(request: _Req, call_next):
    if acctmod.enabled() or not _PW or request.method == "OPTIONS" or request.url.path in _OPEN or request.url.path.startswith(("/nightscout/", "/console", "/cal")):
        return await call_next(request)
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer ") and (_hm.compare_digest(auth[7:], _token()) or staffmod.whoami(auth[7:])):
        return await call_next(request)
    return _JR({"detail": "Telomy is locked. Enter your access password."}, status_code=401)


class _PwBody(BaseModel):
    password: str


@app.get("/auth/status")
def auth_status():
    return {"password_required": bool(_PW) and not acctmod.enabled(), "accounts_enabled": acctmod.enabled(),
            "accounts_available": True}


@app.post("/auth/password")
def auth_password(body: _PwBody):
    if not _PW:
        return {"token": "", "password_required": False}
    if not _hm.compare_digest(body.password.encode(), _PW.encode()):
        _t.sleep(1.0)
        raise HTTPException(401, "That password isn't right.")
    return {"token": _token(), "password_required": True}

# ---------------------------------------------------------------- multi-user (per-user database)
# Turns on automatically once an account exists. A global dependency resolves the bearer token to a user and binds that
# user's database for the request (db.set_db); it runs in the request context so every sync endpoint + db.* call uses
# the right file. Open paths (auth, health, device push) don't require a user.
from fastapi import Depends as _Dep, Header as _Hdr  # noqa: E402
_USER_OPEN = {"/", "/health", "/auth/password", "/auth/status", "/auth/signup", "/auth/login", "/auth/logout",
              "/docs", "/openapi.json", "/redoc", "/static/telomy_anatomy.glb", "/whoop/push"}


# Management plane auth is independent of consumer multi-user mode. These are the only /mgmt paths without a staff token.
_MGMT_OPEN = {"/mgmt/auth/login", "/mgmt/auth/signup", "/mgmt/auth/status"}


def _bearer(authorization: str) -> str:
    return authorization[7:] if authorization.startswith("Bearer ") else ""


async def _bind_user(request: _Req, authorization: str = _Hdr(default="")):
    db.set_db(None)                                           # default; overridden below for an authenticated user
    path = request.url.path
    # ---- C1: the /mgmt management plane ALWAYS requires a valid staff token, in every mode. This runs as a global
    # dependency (not the password middleware, which exits early in multi-user mode), so it can't be bypassed. ----
    if path.startswith("/mgmt") and request.method != "OPTIONS" and path not in _MGMT_OPEN:
        me = staffmod.whoami(_bearer(authorization))
        if not me:
            raise HTTPException(401, "Sign in to the console.")
        request.state.staff = me
        # ---- C2: a staff member is scoped to their own org (a super-admin may address any org). Reject any org the
        # caller doesn't own, whether it arrives as a query param or in the JSON body. Starlette caches the body, so
        # the endpoint's own parsing still works. This single global check covers every /mgmt route. ----
        if me["role"] != "super_admin":
            q_org = request.query_params.get("org")
            if q_org and q_org != me["org"]:
                raise HTTPException(403, "You can only access your own organisation.")
            if request.method in ("POST", "PUT", "PATCH"):
                try:
                    body = await request.json()
                except Exception:  # noqa: BLE001  (no/invalid JSON body — nothing to scope)
                    body = None
                if isinstance(body, dict) and body.get("org") and body["org"] != me["org"]:
                    raise HTTPException(403, "You can only access your own organisation.")
    if not acctmod.enabled():
        return                                                # single-user mode unchanged
    if request.method == "OPTIONS" or path in _USER_OPEN or path.startswith(("/nightscout/", "/console", "/mgmt", "/interop", "/cal")):
        return
    uid = acctmod.user_for_token(_bearer(authorization))
    if not uid:
        raise HTTPException(401, "Please sign in.")
    db.set_db(acctmod.user_db_path(uid))
    request.state.user_id = uid


app.router.dependencies.append(_Dep(_bind_user))

from . import telomy_ml as _telomy_ml  # noqa: E402  trained-ML engines (additive /me/* routes, per-user)
# starlette 1.7's include_router doesn't transfer routes here; add them directly (reliable).
for _r in _telomy_ml.router.routes:
    app.add_api_route(_r.path, _r.endpoint, methods=list(_r.methods), tags=["telomy-ml"])


class _SignupBody(BaseModel):
    email: str
    password: str
    name: str = ""


class _LoginBody(BaseModel):
    email: str
    password: str


@app.post("/auth/signup")
def auth_signup(body: _SignupBody):
    try:
        return acctmod.signup(body.email, body.password, body.name)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/auth/login")
def auth_login(body: _LoginBody):
    try:
        return acctmod.login(body.email, body.password)
    except ValueError as e:
        raise HTTPException(401, str(e))


@app.post("/auth/logout")
def auth_logout(authorization: str = _Hdr(default="")):
    if authorization.startswith("Bearer "):
        acctmod.logout(authorization[7:])
    return {"ok": True}


app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve the web console (centre + doctor) as static files at /console; it authenticates to the API itself.
from fastapi.staticfiles import StaticFiles as _SF  # noqa: E402
import os as _os3  # noqa: E402
_console_dir = _os3.path.join(_os3.path.dirname(__file__), "..", "webconsole")
if _os3.path.isdir(_console_dir):
    app.mount("/console", _SF(directory=_console_dir, html=True), name="console")


def now():
    return engine.now_iso()


def today():
    return engine.last_signal_day() or date.today().isoformat()

# ------------------------------------------------------------------ meta

@app.get("/health")
def health():
    return {"ok": True, "version": app.version, "engine": engine.ENGINE_VERSION,
            "sinc": telomy_llm.model_name() if telomy_llm.available() else "telomy-retrieval (grounded composer)"}


@app.post("/admin/reset")
def reset():
    seed.run(reset=True)
    return {"ok": True}


class OtpIn(BaseModel):
    phone: str
    code: str | None = None


@app.post("/auth/otp/send")
def otp_send(body: OtpIn):
    return {"sent": True, "dev_hint": "Development build: use code 000000"}


@app.post("/auth/otp/verify")
def otp_verify(body: OtpIn):
    if body.code != "000000":
        raise HTTPException(400, "That code didn't match. Check the SMS and try again.")
    return {"token": "dev-token", "profile": engine.profile()}


@app.get("/accounts")
def accounts():
    return db.rows("SELECT id, role, name, org FROM accounts ORDER BY id")


# ------------------------------------------------------------------ prediction

@app.get("/predict")
def predict_me():
    return predict.run(predict.inputs_from_vault())


@app.post("/predict/what-if")
def what_if(body: dict):
    return predict.what_if(body)


@app.get("/predict/patient/{pid}")
def predict_patient(pid: int):
    if not db.one("SELECT id FROM patients WHERE id = ?", (pid,)):
        raise HTTPException(404, "Patient not found")
    return roles.predictions(pid)


# ------------------------------------------------------------------ plans, monthly reports, consults

@app.get("/plans")
def get_plans():
    return {"plans": plans.PLANS, "on_demand": plans.ON_DEMAND, "centre": plans.CENTRE_PLANS, "doctor_seat": plans.DOCTOR_SEAT,
            "test_mode": True, "subscription": plans.subscription()}


class SubIn(BaseModel):
    plan: str
    billing: str = "month"


@app.post("/subscription")
def subscribe(body: SubIn):
    try:
        return plans.subscribe(body.plan, body.billing if body.billing in ("month", "year") else "month", today())
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/monthly-reports")
def monthly_reports():
    return plans.list_monthly()


@app.post("/monthly-reports/{period}/generate")
def monthly_generate(period: str):
    try:
        return plans.generate_monthly(period)
    except PermissionError as e:
        raise HTTPException(402, str(e))


@app.get("/monthly-reports/{period}")
def monthly_get(period: str):
    r = plans.get_monthly(period)
    if not r:
        raise HTTPException(404, "No report for that month yet")
    return r


class SignIn(BaseModel):
    note: str
    doctor: str = "Dr. Meera Rao"


@app.post("/monthly-reports/{period}/sign")
def monthly_sign(period: str, body: SignIn):
    try:
        return plans.sign_monthly(period, body.doctor, body.note)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


class ConsultIn(BaseModel):
    kind: str = "gp"
    mode: str = "video"
    reason: str = ""


@app.post("/consults")
def consult(body: ConsultIn):
    try:
        return plans.request_consult(body.kind, body.mode, body.reason, today())
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/consults")
def consult_list():
    return plans.consults()


class DoneIn(BaseModel):
    notes: str


@app.post("/consults/{cid}/complete")
def consult_done(cid: int, body: DoneIn):
    try:
        return plans.complete_consult(cid, body.notes)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ------------------------------------------------------------------ doctor

@app.get("/doctor/today")
def doctor_today():
    return roles.doctor_today(today())


@app.get("/doctor/work")
def doctor_work():
    return {"monthly_reports": [r for r in plans.list_monthly() if r["state"] == "awaiting_doctor"],
            "consults": [c for c in plans.consults() if c["status"] == "scheduled"],
            "therapy_plans": therapy.plans("awaiting_doctor"), "rx_plans": rx.list_plans("awaiting_doctor")}


@app.get("/doctor/patients")
def doctor_patients():
    return roles.doctor_patients()


@app.get("/doctor/patients/{pid}")
def doctor_patient(pid: int):
    p = roles.doctor_patient(pid)
    if not p:
        raise HTTPException(404, "Patient not found")
    return p


class NoteIn(BaseModel):
    text: str
    author: str = "Dr. Meera Rao"


@app.post("/doctor/patients/{pid}/notes")
def add_note(pid: int, body: NoteIn):
    if not body.text.strip():
        raise HTTPException(400, "Write a note first.")
    db.exec_("INSERT INTO clinical_notes (patient_id, author, ts, text) VALUES (?,?,?,?)", (pid, body.author, now(), body.text.strip()))
    return {"ok": True}


# ------------------------------------------------------------------ wellness centre

@app.get("/centre/dashboard")
def centre_dashboard():
    return roles.centre_dashboard(today())


@app.get("/centre/members")
def centre_members():
    return roles.centre_members()


@app.get("/centre/services")
def centre_services():
    return roles.services()


@app.get("/centre/services/{sid}/outcomes")
def centre_service_outcomes(sid: str):
    return roles.service_outcomes(sid)


@app.get("/centre/bookings")
def centre_bookings(day: str | None = None):
    d = day or today()
    return db.rows("""SELECT b.*, s.name AS service, s.minutes, p.name FROM bookings b JOIN services s ON s.id = b.service_id
                      JOIN patients p ON p.id = b.patient_id WHERE substr(b.ts,1,10) = ? ORDER BY b.ts""", (d,))


class BookingIn(BaseModel):
    patient_id: int
    service_id: str
    ts: str


@app.post("/centre/bookings")
def centre_book(body: BookingIn):
    s = db.one("SELECT * FROM services WHERE id = ?", (body.service_id,))
    if not s or not db.one("SELECT id FROM patients WHERE id = ?", (body.patient_id,)):
        raise HTTPException(400, "Unknown member or service.")
    taken = db.one("SELECT COUNT(*) AS n FROM bookings WHERE service_id = ? AND ts = ? AND status != 'cancelled'", (body.service_id, body.ts))["n"]
    if taken >= s["capacity"]:
        raise HTTPException(409, f"{s['name']} is full at that time ({s['capacity']} places).")
    bid = db.exec_("INSERT INTO bookings (patient_id, service_id, ts, status, price) VALUES (?,?,?,?,?)",
                   (body.patient_id, body.service_id, body.ts, "booked", s["price"]))
    return {"id": bid, "message": f"Booked {s['name']}."}


class StatusIn(BaseModel):
    status: str


@app.post("/centre/bookings/{bid}/status")
def centre_booking_status(bid: int, body: StatusIn):
    if body.status not in ("booked", "checked_in", "completed", "no_show", "cancelled"):
        raise HTTPException(400, "Unknown status")
    db.exec_("UPDATE bookings SET status = ? WHERE id = ?", (body.status, bid))
    return {"ok": True}

# ------------------------------------------------------------------ therapies (centre machines, in-session physiology)

@app.get("/therapy")
def therapy_home(patient_id: int = 1):
    return therapy.therapy_home(patient_id)


@app.get("/therapy/catalogue")
def therapy_catalogue(patient_id: int = 1):
    return therapy.catalogue(patient_id)


@app.get("/therapy/catalogue/{mid}")
def therapy_modality(mid: str, patient_id: int = 1):
    m = next((x for x in therapy.catalogue(patient_id) if x["id"] == mid), None)
    if not m:
        raise HTTPException(404, "Unknown therapy")
    m["sessions"] = [{k: x[k] for k in ("id", "ts", "params", "features", "subjective", "adverse")}
                     for x in therapy._sessions(patient_id, mid)][::-1]
    m["response"] = next((r for r in therapy.response(patient_id) if r["modality"] == mid), None)
    return m


@app.get("/therapy/working")
def therapy_working(patient_id: int = 1):
    return therapy.response(patient_id)


@app.get("/therapy/safety")
def therapy_safety(patient_id: int = 1):
    return {"conditions": therapy.conditions_for(patient_id), "screen": therapy.screen(patient_id)}


@app.get("/therapy/sessions/{sid}")
def therapy_session(sid: int):
    r = therapy.session(sid)
    if not r:
        raise HTTPException(404, "Session not found")
    return r


@app.get("/therapy/hsai")
def therapy_hsai(patient_id: int = 1):
    return therapy.hsai(patient_id)


@app.get("/therapy/goals")
def therapy_goals():
    return [{"id": k, "label": v} for k, v in therapy.GOALS.items()]


class PlanIn(BaseModel):
    goal: str
    per_week: int = 4
    patient_id: int = 1


@app.post("/therapy/plans/preview")
def therapy_plan_preview(body: PlanIn):
    try:
        return therapy.build_plan(body.patient_id, body.goal, max(1, min(10, body.per_week)))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/therapy/plans")
def therapy_plan_submit(body: PlanIn):
    try:
        return therapy.save_plan(body.patient_id, body.goal, max(1, min(10, body.per_week)))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/therapy/plans")
def therapy_plans(state: str | None = None):
    return therapy.plans(state)


class DecideIn(BaseModel):
    approve: bool
    note: str


@app.post("/therapy/plans/{plan_id}/decide")
def therapy_plan_decide(plan_id: int, body: DecideIn):
    try:
        return therapy.decide_plan(plan_id, body.approve, body.note)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


class StartIn(BaseModel):
    modality: str
    params: dict = {}
    patient_id: int = 1


@app.post("/therapy/sessions")
def therapy_start(body: StartIn):
    try:
        return therapy.start_session(body.patient_id, body.modality, body.params)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))


class SamplesIn(BaseModel):
    samples: list[dict]
    source: str = "device"


@app.post("/therapy/sessions/{sid}/samples")
def therapy_ingest(sid: int, body: SamplesIn):
    try:
        return therapy.ingest(sid, body.samples, body.source)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


class FinishIn(BaseModel):
    subjective: dict = {}
    adverse: str | None = None


@app.post("/therapy/sessions/{sid}/finish")
def therapy_finish(sid: int, body: FinishIn):
    try:
        return therapy.finish_session(sid, body.subjective, body.adverse)
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.get("/centre/floor")
def centre_floor():
    return therapy.live_floor()


@app.get("/centre/devices")
def centre_devices():
    return db.rows("SELECT * FROM devices ORDER BY room, id")


@app.get("/centre/therapy-outcomes")
def centre_therapy_outcomes():
    return therapy.modality_outcomes()


@app.get("/centre/research/phenotypes")
def centre_phenotypes():
    return therapy.phenotypes()


# ------------------------------------------------------------------ tests & scans catalogue

@app.get("/tests")
def tests_catalogue():
    return diagnostics.catalogue()


@app.get("/tests/recommended")
def tests_recommended():
    return diagnostics.recommend()


class TestBookIn(BaseModel):
    test_id: str
    day: str


@app.post("/tests/book")
def tests_book(body: TestBookIn):
    try:
        return diagnostics.book(body.test_id, body.day)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(409, str(e))

# ------------------------------------------------------------------ Telomy Rx: supplements, medicines, IVs (doctor-certified)

@app.get("/rx/goals")
def rx_goals():
    return [{"id": k, "label": v} for k, v in rx.GOALS.items()]


@app.get("/rx/recommend")
def rx_recommend(goal: str = "longevity"):
    try:
        return rx.recommend(goal)
    except ValueError as e:
        raise HTTPException(400, str(e))


class RxIn(BaseModel):
    goal: str
    items: list[str] | None = None


@app.post("/rx/plans")
def rx_submit(body: RxIn):
    try:
        return rx.submit(body.goal, 1, body.items)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/rx/plans")
def rx_plans(state: str | None = None):
    return rx.list_plans(state)


@app.get("/rx/plans/{plan_id}")
def rx_plan(plan_id: int):
    r = rx.get(plan_id)
    if not r:
        raise HTTPException(404, "Plan not found")
    return r


class RxDecideIn(BaseModel):
    approve: bool
    note: str
    keep: list[str] | None = None
    doses: dict | None = None


@app.post("/rx/plans/{plan_id}/decide")
def rx_decide(plan_id: int, body: RxDecideIn):
    try:
        return rx.decide(plan_id, body.approve, body.note, body.keep, body.doses)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/rx/plans/{plan_id}/order")
def rx_order(plan_id: int):
    try:
        return rx.order(plan_id)
    except PermissionError as e:
        raise HTTPException(403, str(e))


@app.get("/rx/plans/{plan_id}/prescription.pdf")
def rx_pdf(plan_id: int):
    try:
        return Response(rx.prescription_pdf(plan_id), media_type="application/pdf")
    except PermissionError as e:
        raise HTTPException(403, str(e))


@app.get("/rx/tracking")
def rx_tracking():
    return rx.tracking()

# ------------------------------------------------------------------ doctor: reports with AI summaries

@app.get("/doctor/patients/{pid}/summary")
def doctor_patient_summary(pid: int):
    s = summaries.patient_summary(pid)
    if not s:
        raise HTTPException(404, "Patient not found")
    return s


@app.get("/doctor/patients/{pid}/reports")
def doctor_patient_reports(pid: int):
    return summaries.patient_reports(pid)


@app.get("/reports/{rid}/summary")
def report_summary(rid: int):
    s = summaries.report_summary(rid)
    if not s:
        raise HTTPException(404, "Report not found")
    return s


class ReportReviewIn(BaseModel):
    action: str
    note: str


@app.post("/reports/{rid}/review")
def report_review(rid: int, body: ReportReviewIn):
    try:
        return summaries.review_report(rid, body.action, body.note)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ------------------------------------------------------------------ WHOOP via NOOP self-hosted push (app/whoop.py)

def _push_err(e: "whoop.PushError"):
    return _JR({"type": "error", "protocolVersion": whoop.VERSION, "code": e.code}, status_code=e.status)


def _bind_whoop_user():
    """NOOP's WHOOP push authenticates with its own token, not a user login, so in multi-user mode it would write to the
    default (legacy) DB and the signed-in member would never see their WHOOP data. Bind the configured owner's Vault
    (TELOMY_WHOOP_USER_ID) so the push lands where the app reads it. Single-user mode is unchanged (no-op)."""
    uid = _os3.environ.get("TELOMY_WHOOP_USER_ID")
    if uid and acctmod.enabled():
        try:
            db.set_db(acctmod.user_db_path(int(uid)))
        except Exception:  # noqa: BLE001
            pass


@app.get("/whoop/push")
def whoop_caps(request: _Req):
    if not whoop.token_ok(request.headers.get("authorization")):
        return _push_err(whoop.PushError(401, "unauthorized"))
    _bind_whoop_user()
    try:
        return whoop.capabilities(request.headers.get("noop-push-accept-version"))
    except whoop.PushError as e:
        return _push_err(e)


class _CalIngest(BaseModel):
    session_id: str
    readings: list[dict]


@app.post("/cal/ingest")
async def cal_ingest(body: _CalIngest):
    """Telomy Recorder streams time-aligned readings here (patch/band/ring/WHOOP/reference on one clock)."""
    _bind_whoop_user()
    from . import cal
    return {"session_id": body.session_id, "stored": cal.ingest(body.session_id, body.readings)}


@app.get("/cal/whoop_latest")
def cal_whoop_latest():
    """Latest decoded WHOOP raw (SpO2 ratio, temp raw, HRV, HR) for the recorder to show on the same timeline."""
    _bind_whoop_user()
    from . import cal
    return cal.whoop_latest()


@app.post("/whoop/push")
async def whoop_push(request: _Req):
    if not whoop.token_ok(request.headers.get("authorization")):
        return _push_err(whoop.PushError(401, "unauthorized"))
    _bind_whoop_user()
    body = await request.body()
    if len(body) > whoop.MAX_NDJSON + 64 * 1024:
        return _push_err(whoop.PushError(413, "too_large"))
    try:
        return whoop.receive(body, request.headers.get("content-encoding"))
    except whoop.PushError as e:
        return _push_err(e)


# ------------------------------------------------------------------ CGM via Nightscout-compatible upload (app/cgm.py)

def _ns_auth(request: _Req):
    if not cgm.secret_ok(request.headers.get("api-secret"), request.query_params.get("token")):
        raise HTTPException(401, "Unauthorized")


@app.get("/nightscout/api/v1/status.json")
@app.get("/nightscout/api/v1/status")
def ns_status(request: _Req):
    _ns_auth(request)
    return cgm.status()


@app.post("/nightscout/api/v1/entries")
@app.post("/nightscout/api/v1/entries.json")
async def ns_add_entries(request: _Req):
    _ns_auth(request)
    body = await request.json()
    return {"ok": True, "n": cgm.add_entries(body)}


@app.get("/nightscout/api/v1/entries")
@app.get("/nightscout/api/v1/entries.json")
@app.get("/nightscout/api/v1/entries/sgv.json")
def ns_entries(request: _Req, count: int = 10):
    _ns_auth(request)
    return cgm.entries(count)


@app.get("/cgm/summary")
def cgm_summary(days: int = 14):
    return cgm.summary(days)


@app.get("/whoop/status")
def whoop_status():
    return whoop.status()


@app.get("/whoop/day")
def whoop_day(day: str | None = None):
    """Day strain, auto-detected workouts, calories and HR-based stress from the WHOOP 1 Hz stream."""
    from . import whoop_day as wd
    whoop.init()
    return wd.day(day)


@app.get("/whoop/nights")
def whoop_nights(days: int = 30):
    from . import sleep_fusion
    fused = sleep_fusion.fuse(whoop.nights(days))   # split real overnight nights from daytime naps; flag/reject false ones
    return {**fused, "daily": whoop.daily(days)}


# ------------------------------------------------------------------ Sinc voice (any language, say anything)

@app.post("/voice/audio")
async def voice_audio(file: UploadFile = File(...), language: str | None = None):
    data = await file.read()
    if len(data) < 2000:
        raise HTTPException(400, "Recording too short.")
    try:
        return voice.from_audio(data, file.filename or "audio.m4a", language)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(422, f"Couldn't read that audio ({type(e).__name__}). Try again a little closer to the mic.")


class VoiceText(BaseModel):
    text: str
    language: str | None = None
    features: dict | None = None     # acoustic features computed on the phone (raw audio never sent)
    source: str | None = None        # "typed" | "voice-ondevice" | "checkin"
    model: str | None = None


@app.post("/voice/command")
def voice_command(body: VoiceText):
    if not body.text.strip():
        if body.features:   # a voice check-in with no words still gives a stress reading
            return {"text": "", "actions": [], "stress": voice.record_stress(body.features, body.source or "checkin")}
        raise HTTPException(400, "Say or type something first.")
    out = voice.command(body.text, body.features, body.language, body.source or "typed")
    if body.model:
        out["transcription"] = {"text": body.text, "language": body.language, "model": body.model}
    out["features"] = body.features
    return out


@app.get("/voice/stress")
def voice_stress():
    return voice.stress_trend()


@app.get("/voice/design")
def voice_design():
    return voice.DESIGN

# ------------------------------------------------------------------ routine

class RoutineIn(BaseModel):
    text: str
    apply_to_profile: bool = True


@app.post("/routine/parse")
def routine_parse(body: RoutineIn):
    return routine.parse(body.text)


@app.post("/routine")
def routine_save(body: RoutineIn):
    if len(body.text.strip()) < 20:
        raise HTTPException(400, "Describe your day in a sentence or two.")
    return routine.save(body.text, body.apply_to_profile)


@app.get("/routine")
def routine_get():
    return routine.active() or {}


@app.get("/routine/today")
def routine_today(day: str | None = None, drinking: bool | None = None):
    return routine.today(day, drinking)


class RoutineMark(BaseModel):
    day: str
    key: str
    status: str


@app.post("/routine/mark")
def routine_mark(body: RoutineMark):
    try:
        return routine.confirm(body.day, body.key, body.status)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))

# ------------------------------------------------------------------ custom activities

@app.get("/activities")
def activities_list():
    return {"mine": activities.overview(), "templates": [{"id": k, "name": v["name"]} for k, v in activities.TEMPLATES.items()]}


class ActTypeIn(BaseModel):
    name: str = ""
    template: str | None = None
    fields: list[dict] | None = None


@app.post("/activities")
def activities_create(body: ActTypeIn):
    try:
        return activities.create_type(body.name, body.fields, body.template)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/activities/{tid}")
def activities_detail(tid: str):
    try:
        return activities.detail(tid)
    except LookupError as e:
        raise HTTPException(404, str(e))


class ActSessIn(BaseModel):
    values: dict = {}
    minutes: float | None = None
    hr: list[float] | None = None
    hrv: list[float] | None = None
    notes: str = ""


@app.post("/activities/{tid}/sessions")
def activities_log(tid: str, body: ActSessIn):
    try:
        return activities.log_session(tid, body.values, body.minutes, body.hr, body.hrv, notes=body.notes)
    except LookupError as e:
        raise HTTPException(404, str(e))

# ------------------------------------------------------------------ environment / exposome

@app.get("/environment")
def environment():
    exposome.ensure()
    return exposome.personal()


@app.get("/environment/compare")
def environment_compare(a: str = "Delhi", b: str = "Bengaluru"):
    if a not in exposome.CITIES or b not in exposome.CITIES:
        raise HTTPException(400, f"Cities available: {', '.join(exposome.CITIES)}")
    return exposome.compare(a, b, exposome.live_week())


# ------------------------------------------------------------------ digital twin

@app.get("/twin")
def twin_overview():
    return twin.overview()


class TwinIn(BaseModel):
    changes: dict = {}
    years: float = 5
    preset: str | None = None


@app.post("/twin/simulate")
def twin_simulate(body: TwinIn):
    ch = dict(twin.PRESETS[body.preset][1]) if body.preset in twin.PRESETS else {}
    ch.update(body.changes or {})
    bad = [k for k in ch if k not in twin.LEVERS]
    if bad:
        raise HTTPException(400, f"Unknown lever: {', '.join(bad)}")
    return twin.simulate(ch or None, max(0.25, min(10, body.years)))


@app.get("/twin/projections")
def twin_projections(step_days: int = 10, horizon_days: int = 90):
    """Labelled lab projections every 10 days from your latest REAL measurements (never stored as reports).
    Cached 1 h per (inputs fingerprint): the twin simulation takes seconds on the 1-core server."""
    import time as _t
    key = (db.db_path(), step_days, horizon_days, db.one("SELECT COUNT(*) AS n, MAX(id) AS m FROM results")["m"],
           db.one("SELECT COUNT(*) AS n FROM signals")["n"])
    hit = _PROJ_CACHE.get(key)
    if hit and _t.time() - hit[0] < 3600:
        return hit[1]
    out = {**twin.projections(max(5, min(step_days, 30)), max(30, min(horizon_days, 365))), "accuracy": twin.projection_accuracy()}
    _PROJ_CACHE.clear(); _PROJ_CACHE[key] = (_t.time(), out)
    return out


_PROJ_CACHE: dict = {}


@app.get("/twin/day")
def twin_day(drinking: bool = False, day: str | None = None):
    return twin.day(drinking, day)


@app.get("/twin/mirror")
def twin_mirror():
    return twin.mirror()


# ------------------------------------------------------------------ machine telemetry (centre devices) — see docs/DEVICE_INTEGRATION.md

class TelemetryIn(BaseModel):
    samples: list[dict]


@app.post("/devices/{device_id}/telemetry")
def device_telemetry(device_id: str, body: TelemetryIn, x_device_key: str | None = Header(default=None)):
    try:
        return devices.ingest(device_id, x_device_key, body.samples)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(401, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/centre/devices/{device_id}/key")
def device_key(device_id: str, x_admin_key: str | None = Header(default=None)):
    if x_admin_key != config.ADMIN_KEY:
        raise HTTPException(401, "Admin key required (X-Admin-Key).")
    try:
        return devices.issue_key(device_id)
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.get("/centre/devices/{device_id}/telemetry")
def device_recent(device_id: str, minutes: int = 120):
    try:
        return devices.recent(device_id, minutes)
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.get("/devices/channels")
def device_channels():
    return {m: {k: {"label": v[0], "unit": v[1], "limits": [v[2], v[3]]} for k, v in ch.items()} for m, ch in devices.CHANNELS.items()}


@app.get("/dynamics/load")
def dynamics_load(outcome: str = "hrv"):
    """Personal training-load → next-day HRV model (Banister impulse-response fitted to your data, with skill)."""
    from . import dynamics
    return dynamics.banister(outcome)


@app.get("/dynamics/sleep-pressure")
def dynamics_sleep_pressure():
    """Two-process sleep pressure from your recent WHOOP-detected sleep periods (needs 3 nights)."""
    import time
    from . import dynamics
    ns = [(n["start"], n["end"]) for n in whoop.nights(14) if n.get("end")]
    return dynamics.sleep_pressure(ns, time.time())


@app.get("/physio/validation")
def physio_validation():
    from . import physio
    return physio.validate_prior(20)


# ------------------------------------------------------------------ profile

@app.get("/profile")
def get_profile():
    p = engine.profile()
    p["age"] = round(engine.age_on() or 0, 1)
    return p


@app.put("/profile")
def put_profile(body: dict):
    p = {**engine.profile(), **body}
    db.exec_("INSERT OR REPLACE INTO profile (id, data) VALUES (1, ?)", (db.j(p),))
    return p

# ------------------------------------------------------------------ home

def _card(metric: str, as_of: str):
    s = engine.series(metric, (date.fromisoformat(as_of) - timedelta(days=13)).isoformat(), as_of)
    if not s:
        return {"id": metric, "label": engine.SIGNALS[metric][0], "value": None, "reason": "No data in the last 14 days"}
    base = engine.signal_baseline(metric, as_of, 30)
    src = db.one("SELECT source FROM signals WHERE metric = ? AND day = ?", (metric, s[-1][0]))
    lab, unit, better, dec = engine.SIGNALS[metric]
    v = s[-1][1]
    delta = round(v - base["mean"], dec or 1) if base else None
    return {"id": metric, "label": lab, "value": round(v, dec or 1) if dec else round(v), "unit": unit, "day": s[-1][0],
            "spark": [round(x[1], 2) for x in s[-7:]], "baseline": base["mean"] if base else None, "delta": delta,
            "source": src["source"] if src else None, "confidence": engine.confidence(len(s), 0, 0.85, 14)}


@app.get("/home")
def home(as_of: str | None = None):
    as_of = as_of or today()
    p = engine.profile()
    la = engine.longevity_age(as_of)
    def known_then(i):
        days = [e.get("day") for e in i["evidence"] if e.get("day")]
        return not days or max(days) <= as_of
    insights = [i for i in engine.list_insights() if i["kind"] in ("cross_panel", "event_effect", "lab_wearable") and known_then(i)]
    pick = insights[date.fromisoformat(as_of).toordinal() % max(len(insights), 1)] if insights else None
    latest = engine.latest_values(as_of)
    key = None
    for mid in ("hscrp", "apob", "hba1c", "ldl"):
        if mid in latest:
            r = latest[mid]
            t = engine.marker_trend(mid)
            key = {"id": mid, "label": MARKERS[mid][0], "value": r["value_num"], "unit": r["unit"], "status": r["status"],
                   "day": r["collected_on"], "trend": t if t and t["to_day"] <= as_of else None, "source": "lab"}
            break
    appt = db.one("SELECT a.*, c.data AS clin FROM appointments a JOIN clinicians c ON c.id = a.clinician_id "
                  "WHERE a.ts >= ? AND a.status != 'cancelled' ORDER BY a.ts LIMIT 1", (as_of,))
    if appt:
        appt["clinician"] = db.unj(appt.pop("clin"))
    week_start = (date.fromisoformat(as_of) - timedelta(days=6)).isoformat()
    last7 = {
        "events": db.one("SELECT COUNT(*) AS n FROM events WHERE ts >= ? AND ts <= ?", (week_start, as_of + "T23:59"))["n"],
        "alcohol_days": db.one("SELECT COUNT(DISTINCT substr(ts,1,10)) AS n FROM events WHERE kind='alcohol' AND ts >= ? AND ts <= ?",
                               (week_start, as_of + "T23:59"))["n"],
        "sleep_avg": _avg("sleep_hours", week_start, as_of), "steps_avg": _avg("steps", week_start, as_of),
        "hrv_avg": _avg("hrv", week_start, as_of), "hrv_prev": _avg("hrv", (date.fromisoformat(week_start) - timedelta(days=7)).isoformat(),
                                                                  (date.fromisoformat(week_start) - timedelta(days=1)).isoformat()),
    }
    domains = {k: {kk: v for kk, v in engine.domain_score(k, as_of).items() if kk in ("title", "score", "status", "confidence", "coverage")}
               for k in engine.DOMAINS}
    pending = db.one("SELECT COUNT(*) AS n FROM insights WHERE review_state = 'awaiting' AND dismissed = 0")["n"]
    return {"first_name": p.get("first_name"), "as_of": as_of, "is_test_profile": p.get("is_test_profile", False),
            "longevity": la, "cards": [_card("hrv", as_of), _card("sleep_score", as_of)], "key_biomarker": key,
            "insight": pick, "next_action": _next_action(), "pinned": [_card(m, as_of) for m in features.pins()],
            "last7": last7, "domains": domains, "appointment": appt, "pending_reviews": pending,
            "completeness": engine.completeness()["score"]}


def _avg(metric, start, end):
    v = [x for _, x in engine.series(metric, start, end)]
    return round(sum(v) / len(v), 1) if v else None


def _next_action():
    prot = db.one("SELECT data FROM protocols WHERE active = 1")
    if prot:
        p = db.unj(prot["data"])
        done = {r["item_id"] for r in db.rows("SELECT item_id FROM checklist WHERE day = ? AND done = 1", (today(),))}
        for pillar, items in p["pillars"].items():
            for it in items:
                if it["id"] not in done:
                    return {"title": it["title"], "when": it["when"], "pillar": pillar, "protocol": p["title"],
                            "item_id": it["id"]}
    return {"title": "Log how you feel today", "when": "Takes 10 seconds", "pillar": "Reflection"}

# ------------------------------------------------------------------ vault

@app.get("/vault/panels")
def panels():
    return [engine.panel_summary(p) for p in PANELS]


@app.get("/vault/panel/{panel}")
def panel(panel: str):
    if panel not in PANELS:
        raise HTTPException(404, "Unknown panel")
    out = engine.panel_summary(panel)
    latest = {}
    for r in db.rows("""SELECT r.*, rep.collected_on, rep.title AS report_title, rep.source FROM results r
                        JOIN reports rep ON rep.id = r.report_id WHERE rep.panel = ? ORDER BY rep.collected_on""", (panel,)):
        latest[r["marker_id"]] = r
    markers = []
    for mid, r in latest.items():
        hist = engine.marker_history(mid)
        markers.append({"id": mid, "name": MARKERS[mid][0], "value": r["value_num"] if r["value_num"] is not None else r["value_text"],
                        "unit": r["unit"], "status": r["status"], "day": r["collected_on"], "ref_text": r["ref_text"],
                        "flag": r["flag"], "n": len(hist), "spark": [h["value_num"] for h in hist if h["value_num"] is not None],
                        "trend": engine.marker_trend(mid), "source": r["source"],
                        "variant_note": RISK_GENOTYPES.get(mid, {}).get(r["value_text"]) if r["value_text"] else None})
    order = {"out_of_range": 0, "variant": 0, "detected": 0, "in_range": 1, "info": 2, "optimal": 3, "typical": 3, "absent": 3}
    out["items"] = sorted(markers, key=lambda m: (order.get(m["status"], 2), m["name"]))
    return out


WHAT_CHANGES = {
    "hscrp": ["Fibre diversity (30 plants a week)", "Sleep ≥ 7 h", "Fewer alcohol nights", "Zone 2 cardio 3× a week"],
    "apob": ["Soluble fibre 10 g/day", "Saturated fat < 15 g/day", "Discuss lipid-lowering therapy with cardiology"],
    "ldl": ["Soluble fibre 10 g/day", "Replace saturated fat with olive / mustard oil", "Weight loss if above target"],
    "hba1c": ["Post-meal 10-minute walks", "Protein-first breakfasts", "Strength training 2× a week", "Sleep regularity"],
    "homa_ir": ["Post-meal walks", "Strength training", "Lower refined-carb dinners"],
    "glucose": ["Post-meal walks", "Earlier dinners", "Protein with every meal"],
    "homocysteine": ["Methylated folate and B12 (clinician-guided)", "Leafy greens", "Re-test in 8–12 weeks"],
    "vitd": ["Midday sun 15–20 min", "D3 dose review with clinician", "Re-test 8 weeks after any change"],
    "tg": ["Less alcohol", "Fewer refined carbs at night", "Omega-3 rich fish 2× a week"],
    "ggt": ["Alcohol-free weeks", "Weight and visceral fat reduction", "Coffee (moderate) is associated with lower GGT"],
    "alt": ["Alcohol reduction", "Reduce fructose / sugary drinks", "Visceral fat reduction"],
    "shannon": ["30 different plants a week", "Fermented foods daily", "Fewer ultra-processed foods"],
    "butyrate": ["Resistant starch (cooled rice, green banana)", "Oats, legumes, onions"],
    "mercury": ["Swap large predatory fish for small fish", "Clinician review before any chelation"],
    "bpa": ["Glass/steel food containers", "Avoid heating food in plastic", "Decline thermal receipts"],
}


@app.get("/vault/marker/{mid}")
def marker(mid: str):
    if mid not in MARKERS:
        raise HTTPException(404, "Unknown marker")
    spec = MARKERS[mid]
    hist = engine.marker_history(mid)
    related = [i for i in engine.list_insights() if any(e.get("marker_id") == mid for e in i["evidence"])]
    last = hist[-1] if hist else None
    days_old = (date.fromisoformat(today()) - date.fromisoformat(last["collected_on"])).days if last else None
    conf = engine.confidence(len(hist) * 8, days_old, 0.95) if hist else 0
    read = None
    if last:
        val = last["value_num"] if last["value_num"] is not None else last["value_text"]
        status_txt = {"optimal": "is in the optimal band", "in_range": "is inside the lab range but outside the optimal band",
                      "out_of_range": "is outside the lab's reference range", "variant": "is a risk variant",
                      "typical": "is the typical genotype", "detected": "was detected", "absent": "was not detected"}.get(last["status"], "")
        nice = lambda v: (int(v) if isinstance(v, float) and v.is_integer() else v)
        day = lambda d: date.fromisoformat(d).strftime("%-d %b %Y")
        read = f"Your {spec[0]} of {nice(val)} {last['unit'] or ''} on {day(last['collected_on'])} {status_txt}."
        t = engine.marker_trend(mid)
        if t:
            read += f" It was {nice(t['from'])} on {day(t['from_day'])} ({'+' if t['delta'] > 0 else ''}{nice(t['delta'])})."
        if len(hist) < 3 and spec[5] not in ("variant", "absent"):
            read += " With fewer than three results I can't call this a trend yet."
    lastnum = last["value_num"] if last else None
    return {"zone": derived.zone_for(mid, lastnum), "concerns": derived.concerns_for(mid),
            "evidence_grade": derived.evidence_grade(mid), "retest_prep": RETEST_PREP.get(mid),
            "id": mid, "name": spec[0], "panel": spec[1], "panel_title": PANELS[spec[1]], "unit": spec[2],
            "optimal": [spec[3], spec[4]], "better": spec[5], "loinc": spec[7],
            "history": [{"day": h["collected_on"], "value": h["value_num"] if h["value_num"] is not None else h["value_text"],
                         "ref_low": h["ref_low"], "ref_high": h["ref_high"], "ref_text": h["ref_text"], "status": h["status"],
                         "flag": h["flag"], "report_id": h["report_id"], "report_title": h["report_title"],
                         "source": h["source"], "test_data": bool(h["is_test_data"])} for h in hist],
            "confidence": conf, "sinc_read": read, "what_changes": WHAT_CHANGES.get(mid, []), "related": related,
            "variant_note": RISK_GENOTYPES.get(mid, {}).get(last["value_text"]) if last and last["value_text"] else None}


@app.get("/vault/timeline")
def timeline(start: str | None = None, end: str | None = None, kinds: str | None = None):
    end = end or today()
    start = start or (date.fromisoformat(end) - timedelta(days=30)).isoformat()
    ev = db.rows("SELECT * FROM events WHERE ts >= ? AND ts <= ? ORDER BY ts DESC", (start, end + "T23:59:59"))
    if kinds:
        ks = set(kinds.split(","))
        ev = [e for e in ev if e["kind"] in ks]
    reps = db.rows("SELECT id, title, panel, collected_on FROM reports WHERE collected_on >= ? AND collected_on <= ?", (start, end))
    meals = db.rows("SELECT * FROM meals WHERE ts >= ? AND ts <= ? ORDER BY ts DESC", (start, end + "T23:59:59"))
    items = [{"type": "event", "ts": e["ts"], "kind": e["kind"], "label": e["label"], "severity": e["severity"], "id": e["id"],
              "kind_label": engine.EVENT_KINDS.get(e["kind"], e["kind"])} for e in ev]
    items += [{"type": "report", "ts": r["collected_on"] + "T08:00:00", "kind": "lab", "label": r["title"], "id": r["id"],
               "panel": r["panel"]} for r in reps]
    items += [{"type": "meal", "ts": m["ts"], "kind": "meal", "label": m["name"], "id": m["id"],
               "score": db.unj(m["analysis"], {}).get("score")} for m in meals]
    if not kinds or "imaging" in kinds:
        for im in db.rows("SELECT * FROM imaging"):
            d = db.unj(im["data"])
            if start <= d["day"] <= end:
                items.append({"type": "imaging", "ts": d["day"] + "T09:00:00", "kind": "imaging", "label": d["title"], "id": im["id"]})
    return sorted(items, key=lambda x: x["ts"], reverse=True)

@app.get("/dashboard")
def dashboard(day: str | None = None):
    return features.dashboard(day or today())


@app.get("/categories")
def categories():
    return features.categories()


@app.get("/categories/{name}")
def category(name: str):
    if name not in features.CATEGORIES:
        raise HTTPException(404, "Unknown category")
    return features.category(name)


@app.get("/pins")
def get_pins():
    return features.pins()


@app.put("/pins")
def set_pins(body: list[str]):
    bad = [x for x in body if x not in engine.SIGNALS]
    if bad:
        raise HTTPException(400, f"Unknown signals: {', '.join(bad)}")
    p = engine.profile()
    p["pins"] = body[:6]
    db.exec_("INSERT OR REPLACE INTO profile (id, data) VALUES (1, ?)", (db.j(p),))
    return p["pins"]


@app.get("/meds")
def meds():
    return {"items": features.meds(), "interactions": features.interactions()}


class MedIn(BaseModel):
    name: str
    dose: str = ""
    frequency: str = "once daily"
    times: list[str] = ["08:00"]
    reason: str = ""
    prescriber: str = ""


@app.post("/meds")
def add_med(body: MedIn):
    if not body.name.strip():
        raise HTTPException(400, "Add the medicine's name.")
    mid = db.exec_("INSERT INTO medications (name, dose, frequency, times, reason, prescriber, start_day, active, source) VALUES (?,?,?,?,?,?,?,1,'manual')",
                   (body.name.strip(), body.dose, body.frequency, db.j(body.times), body.reason, body.prescriber, today()))
    db.exec_("INSERT INTO events (ts, kind, label, data) VALUES (?,?,?,?)", (now(), "medication", f"Started {body.name} {body.dose}", db.j({})))
    return {"id": mid, "interactions": features.interactions(),
            "suggest": {"type": "n_of_1", "text": f"Want to see whether {body.name} changes your sleep or HRV? I can set up a study."}}


@app.post("/meds/{mid}/taken")
def took(mid: int):
    db.exec_("INSERT INTO med_doses (med_id, ts) VALUES (?,?)", (mid, now()))
    return {"ok": True, "message": "Logged."}


@app.post("/meds/{mid}/stop")
def stop_med(mid: int):
    db.exec_("UPDATE medications SET active = 0 WHERE id = ?", (mid,))
    return {"ok": True}


@app.get("/notifications")
def notifications():
    return features.notifications(today())


@app.post("/notifications/read")
def notif_read(body: list[str]):
    for k in body:
        db.exec_("INSERT OR IGNORE INTO notif_read (key) VALUES (?)", (k,))
    return {"ok": True}


@app.get("/clinician-notes")
def clinician_notes():
    return features.clinician_notes()


@app.get("/sessions/stats")
def session_stats():
    return features.session_stats(today())


@app.get("/documents")
def documents():
    rs = db.rows("SELECT * FROM documents ORDER BY day DESC")
    for r in rs:
        r["data"] = db.unj(r["data"], {})
    return rs


@app.post("/documents/parse")
async def doc_parse(file: UploadFile = File(...)):
    from .labparse import _text
    data = await file.read()
    if data[:5] != b"%PDF-":
        raise HTTPException(400, "Photos of documents need text recognition, which arrives with the Claude-connected build. Upload a PDF for now.")
    text = _text(data)
    kind = features.classify_document(text)
    if kind == "lab":
        return {"kind": "lab", "route": "/labs/parse", "message": "This looks like a lab report — use Add report."}
    return {"kind": kind, "title": file.filename, "meds": features.extract_meds(text), "excerpt": text[:600]}


@app.get("/evidence/{kind}/{key}")
def evidence_for(kind: str, key: str):
    from .evidence import EVENT_REFS, MARKER_REFS, RULE_REFS, cite
    table = {"rule": RULE_REFS, "marker": MARKER_REFS, "event": EVENT_REFS}.get(kind, {})
    return cite(table.get(key, []))


@app.get("/vault/derived")
def derived_markers():
    return derived.derived()


@app.get("/vault/concerns")
def concerns():
    return derived.concern_groups()


@app.get("/risks")
def risks():
    return derived.risk_matrix()


@app.get("/action-plan")
def action_plan():
    return derived.action_plan()


@app.get("/nudges")
def nudges(day: str | None = None):
    return derived.retest_nudges(day or today())


# ------------------------------------------------------------------ signals

RANGES = {"D": 1, "W": 7, "M": 30, "6M": 182, "Y": 365}


@app.get("/signals")
def signals():
    out = []
    for m, (label, unit, better, dec) in engine.SIGNALS.items():
        s = engine.series(m)
        if not s:
            out.append({"id": m, "label": label, "unit": unit, "value": None})
            continue
        src = db.one("SELECT source FROM signals WHERE metric = ? ORDER BY day DESC LIMIT 1", (m,))
        out.append({"id": m, "label": label, "unit": unit, "value": round(s[-1][1], dec or 1) if dec else round(s[-1][1]),
                    "day": s[-1][0], "spark": [x[1] for x in s[-7:]], "n": len(s), "source": src["source"]})
    return out


@app.get("/signals/{metric}")
def signal(metric: str, range: str = "M", end: str | None = None):
    if metric not in engine.SIGNALS:
        raise HTTPException(404, "Unknown signal")
    end = end or today()
    days = RANGES.get(range, 30)
    start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat()
    s = engine.series(metric, start, end)
    vals = [v for _, v in s]
    ev = db.rows("SELECT ts, kind, label FROM events WHERE ts >= ? AND ts <= ? AND kind NOT IN ('mood','meal','note') ORDER BY ts",
                 (start, end + "T23:59"))
    base = engine.signal_baseline(metric, end, 30)
    label, unit, better, dec = engine.SIGNALS[metric]
    effects = [e for e in engine.event_effects() if e["metric"] == metric]
    src = db.rows("SELECT DISTINCT source FROM signals WHERE metric = ?", (metric,))
    return {"id": metric, "label": label, "unit": unit, "better": better, "range": range, "start": start, "end": end,
            "points": [{"day": d, "value": v} for d, v in s], "events": ev,
            "stats": {"min": min(vals) if vals else None, "max": max(vals) if vals else None,
                      "avg": round(sum(vals) / len(vals), dec or 1) if vals else None, "n": len(vals)},
            "baseline": base, "effects": effects, "sources": [r["source"] for r in src],
            "target": engine.SIGNAL_TARGET.get(metric)}


class ManualSignal(BaseModel):
    metric: str
    value: float
    day: str | None = None


@app.post("/signals")
def add_signal(body: ManualSignal):
    if body.metric not in engine.SIGNALS:
        raise HTTPException(400, "Unknown signal")
    db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)",
             (body.day or today(), body.metric, body.value, "Manual entry"))
    return {"ok": True}

class DailyItem(BaseModel):
    day: str
    metric: str
    value: float
    source: str


class DailyBatch(BaseModel):
    items: list[DailyItem]


DEVICE_SOURCES = {"Telomy patch", "Telomy ring", "WHOOP", "Apple Health", "Apple Watch", "Telomy (fused)"}


@app.post("/signals/daily")
def add_daily(body: DailyBatch):
    """Daily summaries computed on the phone from the user's real devices (fused nights, recovery inputs, Apple
    Health activity). Idempotent upsert per (day, metric); only known metrics from labelled real sources."""
    ok = 0
    for it in body.items[:2000]:
        if it.metric not in engine.SIGNALS or it.source not in DEVICE_SOURCES or not math.isfinite(it.value):
            continue
        try:
            date.fromisoformat(it.day)
        except ValueError:
            continue
        db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)", (it.day, it.metric, it.value, it.source))
        ok += 1
    if ok:
        engine.regenerate_insights()
    return {"ok": True, "accepted": ok}

# ------------------------------------------------------------------ labs

def _parse_pdf_payload(data: bytes, filename: str) -> dict:
    if not data[:5] == b"%PDF-":
        raise HTTPException(400, "That file isn't a PDF. Upload the PDF your lab sent you.")
    try:
        parsed = parse_pdf(data, filename or "")
    except Exception as exc:
        raise HTTPException(422, f"I couldn't read that PDF ({type(exc).__name__}). If it's a scan, a photo upload is coming next.")
    if not parsed["markers"]:
        raise HTTPException(422, "I didn't find any biomarkers I recognise in that PDF.")
    dup = db.one("SELECT id FROM reports WHERE panel = ? AND collected_on = ?", (parsed["panel"], parsed["collected_on"]))
    parsed["duplicate_of"] = dup["id"] if dup else None
    parsed["filename"] = filename
    parsed["panel_title"] = PANELS[parsed["panel"]]
    return parsed


@app.post("/labs/parse")
async def labs_parse(file: UploadFile = File(...)):
    return _parse_pdf_payload(await file.read(), file.filename or "")


class LabB64(BaseModel):
    filename: str | None = None
    pdf_base64: str


@app.post("/labs/parse_b64")
def labs_parse_b64(body: LabB64):
    """JSON upload path: the phone sends the PDF base64-encoded in a JSON body. Multipart file upload from React
    Native over HTTPS was failing to reach the server; JSON POSTs are reliable, so this is the robust ingestion path."""
    import base64 as _b64
    try:
        data = _b64.b64decode(body.pdf_base64, validate=False)
    except Exception:
        raise HTTPException(400, "Could not read the uploaded file. Please try the PDF again.")
    return _parse_pdf_payload(data, body.filename or "")


class SaveReport(BaseModel):
    title: str
    panel: str
    collected_on: str
    filename: str | None = None
    is_test_data: bool = False
    markers: list[dict]
    replace_id: int | None = None


@app.post("/labs/save")
def labs_save(body: SaveReport):
    try:
        if date.fromisoformat(body.collected_on) > date.fromisoformat(today()) + timedelta(days=1):
            raise HTTPException(400, "That collection date is in the future. Check the date on your report.")
    except ValueError:
        raise HTTPException(400, "The collection date isn't a valid date (use YYYY-MM-DD).")
    if body.replace_id:
        db.exec_("DELETE FROM reports WHERE id = ?", (body.replace_id,))
    rid = seed.save_report(body.model_dump(), "Uploaded by you", body.filename or "")
    engine.regenerate_insights()
    return {"id": rid, "markers": len(body.markers), "panel": body.panel}


@app.get("/reports")
def reports():
    rs = db.rows("SELECT * FROM reports ORDER BY collected_on DESC")
    for r in rs:
        r["markers"] = db.one("SELECT COUNT(*) AS n FROM results WHERE report_id = ?", (r["id"],))["n"]
        r["panel_title"] = PANELS.get(r["panel"], r["panel"])
    return rs


@app.get("/reports/{rid}")
def report(rid: int):
    r = db.one("SELECT * FROM reports WHERE id = ?", (rid,))
    if not r:
        raise HTTPException(404, "Report not found")
    r["results"] = db.rows("SELECT * FROM results WHERE report_id = ?", (rid,))
    for x in r["results"]:
        x["name"] = MARKERS[x["marker_id"]][0]
    return r


@app.delete("/reports/{rid}")
def delete_report(rid: int):
    db.exec_("DELETE FROM reports WHERE id = ?", (rid,))
    engine.regenerate_insights()
    return {"ok": True}

# ------------------------------------------------------------------ insights & clinician review

@app.get("/insights")
def insights(kind: str | None = None):
    rs = engine.list_insights()
    return [i for i in rs if not kind or i["kind"] == kind]


@app.get("/insights/{iid}")
def insight(iid: str):
    i = next((x for x in engine.list_insights(include_dismissed=True) if x["id"] == iid), None)
    if not i:
        raise HTTPException(404, "Insight not found")
    return i


class Review(BaseModel):
    action: str  # request | signed | modified | rejected
    note: str = ""
    author: str = "Dr. Meera Rao"


@app.post("/insights/{iid}/review")
def review(iid: str, body: Review):
    if body.action == "rejected" and not body.note.strip():
        raise HTTPException(400, "A rejection needs a one-line note.")
    state = {"request": "awaiting", "signed": "signed", "modified": "signed", "rejected": "rejected"}[body.action]
    db.exec_("UPDATE insights SET review_state = ? WHERE id = ?", (state, iid))
    author = "You" if body.action == "request" else body.author
    note = body.note or ("Review requested." if body.action == "request" else "")
    db.exec_("INSERT INTO review_thread (insight_id, ts, author, action, note) VALUES (?,?,?,?,?)", (iid, now(), author, body.action, note))
    return insight(iid)


@app.post("/insights/{iid}/dismiss")
def dismiss(iid: str):
    db.exec_("UPDATE insights SET dismissed = 1 WHERE id = ?", (iid,))
    return {"ok": True}


@app.get("/care/queue")
def care_queue():
    """Telomy Care (clinician) queue — awaiting review, highest confidence first."""
    return [i for i in engine.list_insights() if i["review_state"] == "awaiting"]

# ------------------------------------------------------------------ events & meals

class EventIn(BaseModel):
    kind: str
    label: str
    ts: str | None = None
    severity: int | None = None
    data: dict | None = None


@app.post("/events")
def add_event(body: EventIn):
    ts = body.ts or now()
    eid = db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)",
                   (ts, body.kind, body.label, body.severity, db.j(body.data or {})))
    suggest = None
    if body.kind in ("supplement", "medication"):
        suggest = {"type": "n_of_1", "text": f"Run '{body.label}' as a 4-week study? I'd alternate weeks on and off "
                   "and compare your deep sleep and HRV.", "intervention": body.label}
    return {"id": eid, "message": "Saved. Sinc will look at it tonight.", "suggest": suggest}


@app.get("/events")
def events(limit: int = 50):
    return db.rows("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,))


@app.delete("/events/{eid}")
def delete_event(eid: int):
    db.exec_("DELETE FROM events WHERE id = ?", (eid,))
    return {"ok": True}


class MealIn(BaseModel):
    text: str
    ts: str | None = None
    save: bool = False


@app.post("/meals/analyze")
def meal_analyze(body: MealIn):
    when = datetime.fromisoformat(body.ts) if body.ts else datetime.fromisoformat(engine.now_iso())
    a = food.analyze(body.text, when)
    if body.save and a.get("items"):
        mid = db.exec_("INSERT INTO meals (ts, name, analysis) VALUES (?,?,?)", (when.isoformat(timespec="seconds"), body.text, db.j(a)))
        a["id"] = mid
    return a


@app.get("/meals")
def meals(limit: int = 30):
    rs = db.rows("SELECT * FROM meals ORDER BY ts DESC LIMIT ?", (limit,))
    for r in rs:
        r["analysis"] = db.unj(r["analysis"], {})
    return rs


@app.delete("/meals/{mid}")
def delete_meal(mid: int):
    db.exec_("DELETE FROM meals WHERE id = ?", (mid,))
    return {"ok": True}


@app.get("/nutrition/targets")
def nutrition_targets(goal: str = "maintain"):
    """Personal daily targets from body, labs and measured activity; with today's logged meals against them."""
    from . import nutrition
    if goal not in ("maintain", "lose"):
        raise HTTPException(400, "goal must be maintain or lose")
    return nutrition.today_vs_targets(goal)


@app.get("/nutrition/trends")
def nutrition_trends(days: int = 7):
    end = date.fromisoformat(today())
    out = []
    goals = engine.profile().get("nutrition_goals", {"kcal": 2000, "protein": 120, "carbs": 220, "fat": 70})
    for i in range(days - 1, -1, -1):
        d = (end - timedelta(days=i)).isoformat()
        ms = db.rows("SELECT analysis FROM meals WHERE substr(ts,1,10) = ?", (d,))
        tot = {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0}
        for m in ms:
            a = db.unj(m["analysis"], {})
            for k in tot:
                tot[k] += a.get(k) or 0
        out.append({"day": d, "logged": len(ms), **{k: round(v) for k, v in tot.items()}})
    return {"days": out, "goals": goals}


@app.get("/calculators")
def calculators():
    """BMR (Mifflin–St Jeor), protein from lean mass, macro split, body-fat (Navy if measurements exist)."""
    p = engine.profile()
    L = engine.latest_values()
    w = (engine.series("weight") or [(None, None)])[-1][1]
    age, h, sex = engine.age_on(), p.get("height_cm"), p.get("sex", "male")
    out = {"inputs": {"weight_kg": w, "height_cm": h, "age": round(age or 0, 1), "sex": sex}}
    if w and h and age:
        bmr = 10 * w + 6.25 * h - 5 * age + (5 if sex == "male" else -161)
        out["bmr"] = {"value": round(bmr), "method": "Mifflin–St Jeor"}
        steps = engine.signal_baseline("steps", days=14)
        factor = 1.55 if steps and steps["mean"] > 9000 else 1.375
        out["tdee"] = {"value": round(bmr * factor), "activity_factor": factor,
                       "method": f"BMR × {factor} (14-day steps {round(steps['mean']) if steps else 'n/a'})"}
    bf = L.get("body_fat_pct") or L.get("bca_body_fat")
    if bf and w:
        lean = w * (1 - bf["value_num"] / 100)
        out["lean_mass"] = {"value": round(lean, 1), "source": f"{MARKERS[bf['marker_id']][0]} {bf['value_num']}% on {bf['collected_on']}"}
        out["protein_target"] = {"value": round(lean * 2.0), "range": [round(lean * 1.6), round(lean * 2.2)],
                                 "method": "1.6–2.2 g per kg lean mass"}
    if "tdee" in out and "protein_target" in out:
        kcal = out["tdee"]["value"] - (300 if bf and bf["value_num"] > 20 else 0)
        prot = out["protein_target"]["value"]
        fat = round(kcal * 0.30 / 9)
        carbs = round((kcal - prot * 4 - fat * 9) / 4)
        out["macros"] = {"kcal": kcal, "protein": prot, "fat": fat, "carbs": carbs,
                         "note": "300 kcal deficit because body fat is above 20%" if kcal < out["tdee"]["value"] else "Maintenance"}
    return out


@app.get("/menu")
def menu(start: str | None = None):
    s = date.fromisoformat(start) if start else date.fromisoformat(today()) - timedelta(days=date.fromisoformat(today()).weekday())
    return food.week_menu(s)


class SwapIn(BaseModel):
    name: str
    preference: str = ""


@app.post("/menu/swap")
def menu_swap(body: SwapIn):
    return food.swap(body.name, body.preference)

# ------------------------------------------------------------------ Sinc

class Ask(BaseModel):
    question: str
    chat_id: int | None = None
    mode: str = "normal"  # normal | deep


@app.post("/sinc/ask")
def ask(body: Ask):
    if not body.question.strip():
        raise HTTPException(400, "Ask me something about your health data.")
    return sinc.ask(body.question.strip(), body.chat_id, body.mode if body.mode in ("normal", "deep") else "normal")


@app.get("/sinc/context")
def sinc_context(q: str = ""):
    return sinc.slm_context(q)


class OnDevice(BaseModel):
    question: str
    answer: str
    chat_id: int | None = None
    model: str = "on-device"


@app.post("/sinc/log")
def sinc_log(body: OnDevice):
    if not body.question.strip() or not body.answer.strip():
        raise HTTPException(400, "Question and answer are required.")
    return sinc.log_on_device(body.question.strip(), body.answer.strip()[:4000], body.chat_id, body.model[:60])


class Capture(BaseModel):
    text: str


@app.post("/sinc/capture")
def sinc_capture(body: Capture):
    """Statements only (used by on-device Sinc before it answers): set up / update trackers. {captured: false} otherwise."""
    r = trackers.capture(body.text.strip()) if body.text.strip() else None
    return {"captured": bool(r), **(r or {})}


@app.get("/trackers")
def trackers_list(active: bool = False):
    return trackers.all_trackers(active)


@app.get("/trackers/today")
def trackers_today():
    return trackers.today()


@app.get("/trackers/{tid}")
def tracker_get(tid: int):
    if not db.one("SELECT 1 AS x FROM trackers WHERE id = ?", (tid,)):
        raise HTTPException(404, "No such tracker.")
    return {**trackers.summary(tid), "drivers": trackers.drivers(tid),
            "entries": db.rows("SELECT ts, value, note, source FROM tracker_entries WHERE tracker_id = ? ORDER BY ts DESC LIMIT 60", (tid,))}


class TrackerEntry(BaseModel):
    value: float | None = None
    note: str | None = None


@app.post("/trackers/{tid}/entry")
def tracker_entry(tid: int, body: TrackerEntry):
    if not db.one("SELECT 1 AS x FROM trackers WHERE id = ?", (tid,)):
        raise HTTPException(404, "No such tracker.")
    trackers.log_entry(tid, body.value, note=body.note, source="app")
    return trackers.summary(tid)


@app.post("/trackers/{tid}/stop")
def tracker_stop(tid: int):
    db.exec_("UPDATE trackers SET active = 0 WHERE id = ?", (tid,))
    return trackers.summary(tid)


class ClientLog(BaseModel):
    area: str
    stage: str = ""
    message: str = ""
    model: str | None = None
    free_bytes: float | None = None


@app.post("/client/log")
def client_log(body: ClientLog):
    """App-side failures (e.g. the on-device model download) land here so they can be diagnosed without the phone.
    Technical messages only — the app never sends health data on this route."""
    db.exec_("CREATE TABLE IF NOT EXISTS client_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, area TEXT, stage TEXT, message TEXT, data TEXT)")
    db.exec_("INSERT INTO client_log (ts, area, stage, message, data) VALUES (?,?,?,?,?)",
             (engine.now_iso(), body.area[:40], body.stage[:40], body.message[:500], db.j({"model": body.model, "free_bytes": body.free_bytes})))
    return {"ok": True}


class Finding(BaseModel):
    kind: str
    payload: dict
    citation: str
    evidence: str = "C"
    note: str = ""


@app.get("/science")
def science_list(include_inactive: bool = False):
    return science.list_findings(include_inactive)


@app.post("/science")
def science_add(body: Finding):
    """Add a new finding (a paper/guideline) as data — it takes effect on the next request. Clinician/admin use."""
    try:
        return science.add_finding(body.kind, body.payload, body.citation, body.evidence, "api", body.note)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/science/{fid}/active")
def science_toggle(fid: int, active: bool = True):
    return science.set_active(fid, active)


class VitalsBatch(BaseModel):
    samples: list[dict]
    source: str


@app.post("/vitals/ingest")
def vitals_ingest(body: VitalsBatch):
    """A device batch of high-frequency vitals (ts, metric, value, step_s). Idempotent; fills the longitudinal record."""
    return vitalsmod.ingest(body.samples, body.source[:40] or "device")


@app.get("/vitals/day")
def vitals_day(day: str | None = None):
    return vitalsmod.day(day)


@app.get("/vitals/series")
def vitals_series(metric: str, start: int, end: int, max_points: int = 1000):
    return vitalsmod.series(metric, start, end, min(max_points, 5000))


@app.get("/vitals/coverage")
def vitals_coverage(days: int = 7):
    return vitalsmod.coverage(days)


# ---- Fulfillment & logistics (pickups/deliveries) ----
class OrderIn(BaseModel):
    org: str = "default"
    kind: str
    items: list[dict]
    member_id: int | None = None
    patient_id: int | None = None
    address: str = ""
    slot: str | None = None
    rx_plan_id: int | None = None
    partner: str = ""


@app.get("/mgmt/orders")
def mgmt_orders(org: str = "default", status: str | None = None, kind: str | None = None):
    return fulfillment.list_orders(org, status, kind)


@app.post("/mgmt/orders")
def mgmt_order_add(body: OrderIn):
    try:
        return fulfillment.create_order(body.org, body.kind, body.items, body.member_id, body.patient_id, body.address, body.slot, body.rx_plan_id, body.partner)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/mgmt/orders/{oid}")
def mgmt_order(oid: int):
    o = fulfillment.order(oid)
    if not o:
        raise HTTPException(404, "no such order")
    return o


@app.post("/mgmt/orders/{oid}/advance")
def mgmt_order_advance(oid: int, body: dict):
    try:
        return fulfillment.advance(oid, body.get("status", ""), body.get("note", ""), body.get("tracking"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/orders/from-rx/{plan_id}")
def mgmt_order_from_rx(plan_id: int, body: dict):
    try:
        return fulfillment.from_rx_plan(body.get("org", "default"), plan_id, body.get("address", ""), body.get("slot"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/sample-pickup")
def mgmt_sample_pickup(body: dict):
    try:
        return fulfillment.schedule_sample_pickup(body.get("org", "default"), int(body["patient_id"]), body.get("tests", []),
                                                   body.get("address", ""), body.get("slot", ""), body.get("partner", ""))
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


# ---- Goals ----
class GoalIn(BaseModel):
    org: str = "default"
    title: str
    owner_kind: str = "member"
    owner_id: int | None = None
    category: str = ""
    metric: str | None = None
    target: float | None = None
    deadline: str | None = None
    set_by: str = ""


@app.get("/mgmt/goals")
def mgmt_goals(org: str = "default", owner_kind: str | None = None, owner_id: int | None = None, status: str = "active"):
    return goals.list_goals(org, owner_kind, owner_id, status)


@app.post("/mgmt/goals")
def mgmt_goal_add(body: GoalIn):
    try:
        return goals.add_goal(body.org, body.title, body.owner_kind, body.owner_id, body.category, body.metric, body.target, body.deadline, body.set_by)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/goals/{gid}")
def mgmt_goal_update(gid: int, body: dict):
    try:
        return goals.update_goal(gid, body.get("status"), body.get("target"), body.get("deadline"))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- Interoperability (open to hospital/EHR systems) ----
@app.get("/interop/fhir/Patient")
def interop_fhir_patient():
    return interop.fhir_patient()


@app.get("/interop/fhir/Bundle")
def interop_fhir_bundle():
    return interop.fhir_bundle()


@app.get("/mgmt/api-keys")
def mgmt_keys(org: str = "default"):
    return interop.list_keys(org)


@app.post("/mgmt/api-keys")
def mgmt_key_add(body: dict):
    return interop.create_key(body.get("org", "default"), body.get("name", "integration"), body.get("scopes", ["read"]))


@app.delete("/mgmt/api-keys/{kid}")
def mgmt_key_del(kid: int):
    interop.revoke_key(kid); return {"ok": True}


@app.get("/mgmt/webhooks")
def mgmt_webhooks(org: str = "default"):
    return interop.list_webhooks(org)


@app.post("/mgmt/webhooks")
def mgmt_webhook_add(body: dict):
    return interop.add_webhook(body.get("org", "default"), body.get("url", ""), body.get("events", ["*"]))


# ---- Staff accounts & role-based login (centre vs doctor log in separately) ----
class StaffSignup(BaseModel):
    org: str = "default"
    role: str
    name: str
    email: str
    password: str


class StaffLogin(BaseModel):
    email: str
    password: str


@app.get("/mgmt/auth/status")
def mgmt_auth_status():
    return {"roles": staffmod.ROLES, "has_staff": staffmod.any_staff()}


@app.post("/mgmt/auth/signup")
def mgmt_auth_signup(body: StaffSignup, authorization: str = _Hdr(default="")):
    # first account bootstraps; after that, only an admin can add staff
    me = None
    if staffmod.any_staff():
        me = staffmod.whoami(authorization[7:] if authorization.startswith("Bearer ") else "")
        if not me or not me["admin"]:
            raise HTTPException(403, "Only an admin can add staff.")
    _guard_staff_creation(me, body.role, body.org)
    try:
        return staffmod.create_staff(body.org, body.role, body.name, body.email, body.password, by=(me or {}).get("email", "bootstrap"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/auth/login")
def mgmt_auth_login(body: StaffLogin):
    try:
        return staffmod.login(body.email, body.password)
    except ValueError as e:
        raise HTTPException(401, str(e))


@app.get("/mgmt/auth/me")
def mgmt_auth_me(authorization: str = _Hdr(default="")):
    me = staffmod.whoami(authorization[7:] if authorization.startswith("Bearer ") else "")
    if not me:
        raise HTTPException(401, "Not signed in.")
    return me


@app.post("/mgmt/auth/logout")
def mgmt_auth_logout(authorization: str = _Hdr(default="")):
    if authorization.startswith("Bearer "):
        staffmod.logout(authorization[7:])
    return {"ok": True}


@app.get("/mgmt/staff")
def mgmt_staff(org: str = "default"):
    return staffmod.list_staff(org)


@app.post("/mgmt/staff")
def mgmt_staff_add(body: StaffSignup, authorization: str = _Hdr(default="")):
    me = staffmod.whoami(authorization[7:] if authorization.startswith("Bearer ") else "")
    if staffmod.any_staff() and (not me or not me["admin"]):
        raise HTTPException(403, "Only an admin can add staff.")
    _guard_staff_creation(me, body.role, body.org)
    try:
        return staffmod.create_staff(body.org, body.role, body.name, body.email, body.password, by=(me or {}).get("email", "setup"))
    except ValueError as e:
        raise HTTPException(400, str(e))


def _guard_staff_creation(me: dict | None, role: str, org: str):
    """Privilege rules: only a super-admin creates super-admins or staff outside their own org/workspace."""
    if role not in staffmod.ROLES:
        raise HTTPException(400, "Unknown role.")
    if me is None:
        return  # bootstrap: the very first account may be anything (typically super_admin or a centre_admin)
    if me["role"] == "super_admin":
        return
    target_ws = staffmod.ROLES[role]["workspace"]
    if role == "super_admin" or target_ws == "platform":
        raise HTTPException(403, "Only a super-admin can create platform accounts.")
    if org != me["org"]:
        raise HTTPException(403, "You can only add staff to your own organisation.")
    if target_ws != me["workspace"]:
        raise HTTPException(403, f"A {me['workspace']} admin cannot create {target_ws}-side accounts.")


class StaffActive(BaseModel):
    active: bool = True


@app.post("/mgmt/staff/{sid}/active")
def mgmt_staff_active(sid: int, body: StaffActive, authorization: str = _Hdr(default="")):
    me = staffmod.whoami(authorization[7:] if authorization.startswith("Bearer ") else "")
    if not me or not me["admin"]:
        raise HTTPException(403, "Only an admin can change staff access.")
    if sid == me["staff_id"]:
        raise HTTPException(400, "You cannot disable your own account.")
    if not any(s["id"] == sid for s in staffmod.list_staff(me["org"])):
        raise HTTPException(404, "No such staff member in your organisation.")
    staffmod.set_active(sid, body.active)
    return {"ok": True, "id": sid, "active": body.active}


# ---- staff auth helpers (shared by the admin / assignment / performance endpoints) ----
def _staff(authorization: str) -> dict | None:
    return staffmod.whoami(authorization[7:] if authorization.startswith("Bearer ") else "")


def _require_staff(authorization: str) -> dict:
    me = _staff(authorization)
    if not me:
        raise HTTPException(401, "Sign in to the console first.")
    return me


def _require_super(authorization: str) -> dict:
    me = _require_staff(authorization)
    if me["role"] != "super_admin":
        raise HTTPException(403, "Super-admin only.")
    return me


def _require_org_admin(authorization: str, org: str) -> dict:
    """An admin of this org, or any super-admin."""
    me = _require_staff(authorization)
    if me["role"] == "super_admin":
        return me
    if not me["admin"] or me["org"] != org:
        raise HTTPException(403, "You must be an admin of this organisation.")
    return me


@app.post("/mgmt/staff/{sid}/profile")
def mgmt_staff_profile(sid: int, body: dict, authorization: str = _Hdr(default="")):
    me = _require_staff(authorization)
    tgt = staffmod.get_staff(sid)
    if not tgt:
        raise HTTPException(404, "No such staff member.")
    if not (me["role"] == "super_admin" or (me["admin"] and me["org"] == tgt["org"]) or me["staff_id"] == sid):
        raise HTTPException(403, "Not allowed.")
    return staffmod.update_profile(sid, name=body.get("name"), profile=body.get("profile") or {})


# ---- Super-admin: onboard & oversee the whole network ----
class CentreOnboard(BaseModel):
    name: str
    city: str = ""
    slug: str | None = None
    admin_name: str = ""
    admin_email: str = ""
    admin_password: str = ""


@app.get("/mgmt/admin/overview")
def mgmt_admin_overview(authorization: str = _Hdr(default="")):
    _require_super(authorization)
    return tenancymod.platform_overview()


@app.get("/mgmt/admin/centres")
def mgmt_admin_centres(authorization: str = _Hdr(default="")):
    _require_super(authorization)
    return tenancymod.list_centres()


@app.post("/mgmt/admin/centres")
def mgmt_admin_centre_add(body: CentreOnboard, authorization: str = _Hdr(default="")):
    me = _require_super(authorization)
    try:
        return tenancymod.onboard_centre(body.name, body.city, body.slug, body.admin_name, body.admin_email,
                                         body.admin_password, by=me["email"])
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/admin/centres/{slug}/status")
def mgmt_admin_centre_status(slug: str, body: dict, authorization: str = _Hdr(default="")):
    _require_super(authorization)
    tenancymod.set_centre_status(slug, body.get("status", "active"))
    return {"ok": True}


@app.get("/mgmt/admin/staff")
def mgmt_admin_staff(authorization: str = _Hdr(default="")):
    _require_super(authorization)
    return staffmod.all_staff()


class DoctorOnboard(BaseModel):
    name: str
    email: str
    password: str
    org: str | None = None          # affiliate to a centre on creation (optional)
    clinic_admin: bool = False


@app.post("/mgmt/admin/doctors")
def mgmt_admin_doctor_add(body: DoctorOnboard, authorization: str = _Hdr(default="")):
    me = _require_super(authorization)
    role = "clinic_admin" if body.clinic_admin else "doctor"
    org = body.org or "independent"
    try:
        doc = staffmod.create_staff(org, role, body.name, body.email, body.password, by=me["email"])
        if body.org:
            tenancymod.affiliate_doctor(doc["id"], body.org)
        return doc
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- The care graph: onboarding & assignments (doctor ⇄ centre ⇄ patient) ----
class PatientOnboard(BaseModel):
    name: str
    user_ref: str | None = None
    age: float | None = None
    sex: str | None = None
    city: str = ""
    org: str | None = None          # assign to this centre
    doctor_id: int | None = None    # assign to this doctor


@app.post("/mgmt/patients/onboard")
def mgmt_patient_onboard(body: PatientOnboard, authorization: str = _Hdr(default="")):
    me = _require_staff(authorization)
    # a centre person may only onboard into their own centre; a doctor may onboard freely (they then assign to a centre)
    if me["workspace"] == "centre":
        body.org = me["org"]
    by_role = me["role"]
    try:
        return tenancymod.onboard_patient(body.name, by_role, by=me["email"], user_ref=body.user_ref, age=body.age,
                                          sex=body.sex, city=body.city, org=body.org, doctor_id=body.doctor_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


class AssignCentre(BaseModel):
    patient_id: int
    org: str
    note: str = ""


@app.post("/mgmt/assign/centre")
def mgmt_assign_centre(body: AssignCentre, authorization: str = _Hdr(default="")):
    me = _require_staff(authorization)   # doctors assign their patients to a centre
    try:
        return tenancymod.assign_to_centre(body.patient_id, body.org, by=me["email"], note=body.note)
    except ValueError as e:
        raise HTTPException(400, str(e))


class AssignDoctor(BaseModel):
    patient_id: int
    doctor_id: int
    note: str = ""


@app.post("/mgmt/assign/doctor")
def mgmt_assign_doctor(body: AssignDoctor, authorization: str = _Hdr(default="")):
    me = _require_staff(authorization)   # centres assign their members to an affiliated doctor
    try:
        return tenancymod.assign_to_doctor(body.patient_id, body.doctor_id, by=me["email"], note=body.note)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/mgmt/patients/{pid}/graph")
def mgmt_patient_graph(pid: int, authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return tenancymod.patient_graph(pid)


@app.get("/mgmt/centre/people")
def mgmt_centre_people(org: str = "default", authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return tenancymod.centre_patients(org)


@app.get("/mgmt/doctor/patients")
def mgmt_doctor_patients(authorization: str = _Hdr(default="")):
    me = _require_staff(authorization)
    return tenancymod.doctor_patients(me["staff_id"])


@app.get("/mgmt/doctor/centres")
def mgmt_doctor_centres(authorization: str = _Hdr(default="")):
    me = _require_staff(authorization)
    # a doctor sees the centres they're affiliated to; a super-admin sees all
    if me["role"] == "super_admin":
        return tenancymod.list_centres()
    return tenancymod.doctor_centres(me["staff_id"])


# ---- doctor ⇄ centre affiliation ----
@app.get("/mgmt/centre/doctors")
def mgmt_centre_doctors(org: str = "default", authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return tenancymod.centre_doctors(org)


class Affiliate(BaseModel):
    doctor_id: int
    org: str


@app.post("/mgmt/centre/doctors")
def mgmt_centre_affiliate(body: Affiliate, authorization: str = _Hdr(default="")):
    _require_org_admin(authorization, body.org)
    try:
        return tenancymod.affiliate_doctor(body.doctor_id, body.org)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- operational staff ⇄ therapy / machine ----
class Duty(BaseModel):
    staff_id: int
    org: str
    duty_kind: str                  # 'service' | 'resource'
    ref_id: int


@app.get("/mgmt/duties")
def mgmt_duties(org: str = "default", staff_id: int | None = None, authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return tenancymod.staff_duties(org, staff_id)


@app.post("/mgmt/duties")
def mgmt_duty_add(body: Duty, authorization: str = _Hdr(default="")):
    _require_org_admin(authorization, body.org)
    try:
        return tenancymod.assign_duty(body.staff_id, body.org, body.duty_kind, body.ref_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/mgmt/duties")
def mgmt_duty_del(staff_id: int, duty_kind: str, ref_id: int, org: str = "default", authorization: str = _Hdr(default="")):
    _require_org_admin(authorization, org)
    tenancymod.remove_duty(staff_id, duty_kind, ref_id)
    return {"ok": True}


# ---- performance & revenue (one app runs the whole centre) ----
@app.get("/mgmt/centre/performance")
def mgmt_centre_performance(org: str = "default", since: str | None = None, authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return tenancymod.staff_performance(org, since=since)


@app.get("/mgmt/centre/revenue")
def mgmt_centre_revenue(org: str = "default", since: str | None = None, authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return tenancymod.centre_revenue(org, since=since)


# ---- Billing, payments & subscriptions ----
@app.get("/mgmt/billing/gateways")
def mgmt_billing_gateways(authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return billingmod.gateways()


@app.get("/mgmt/billing/plans")
def mgmt_billing_plans(org: str = "default", authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return {"memberships": pform.list_catalog(org, "membership_plan"),
            "packages": [s for s in pform.list_catalog(org, "service_type") if s["data"].get("category") == "Package"],
            "services": [s for s in pform.list_catalog(org, "service_type") if s["data"].get("category") != "Package"]}


@app.post("/mgmt/billing/seed-plans")
def mgmt_billing_seed(body: dict, authorization: str = _Hdr(default="")):
    org = body.get("org", "default")
    _require_org_admin(authorization, org)
    return billingmod.seed_plans(org)


class PayBody(BaseModel):
    org: str = "default"
    invoice_id: int
    gateway: str


@app.post("/mgmt/billing/pay")
def mgmt_billing_pay(body: PayBody, authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    try:
        return billingmod.record_payment(body.org, body.invoice_id, body.gateway)
    except ValueError as e:
        raise HTTPException(400, str(e))


class SubscribeBody(BaseModel):
    org: str = "default"
    member_id: int
    plan_id: int
    gateway: str


@app.post("/mgmt/billing/subscribe")
def mgmt_billing_subscribe(body: SubscribeBody, authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    try:
        return billingmod.create_subscription(body.org, body.member_id, body.plan_id, body.gateway)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/billing/run-cycle")
def mgmt_billing_run_cycle(body: dict, authorization: str = _Hdr(default="")):
    org = body.get("org", "default")
    _require_org_admin(authorization, org)
    return billingmod.run_billing_cycle(org, body.get("as_of", date.today().isoformat()))


@app.get("/mgmt/billing/payments")
def mgmt_billing_payments(org: str = "default", since: str | None = None, authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return billingmod.list_payments(org, since=since)


@app.get("/mgmt/billing/summary")
def mgmt_billing_summary(org: str = "default", since: str | None = None, authorization: str = _Hdr(default="")):
    _require_staff(authorization)
    return billingmod.summary(org, since=since)


# ---- Platform: modular, customisable config for centres & clinics ----
class OrgCfg(BaseModel):
    org: str = "default"
    kind: str | None = None
    modules: dict | None = None
    branding: dict | None = None
    settings: dict | None = None


class CatalogIn(BaseModel):
    org: str = "default"
    kind: str
    name: str
    data: dict | None = None
    key: str | None = None


class FieldIn(BaseModel):
    org: str = "default"
    entity: str
    label: str
    type: str
    options: list | None = None
    required: bool = False
    section: str = ""


@app.get("/mgmt/overview")
def mgmt_overview(org: str = "default"):
    return pform.overview(org)


@app.post("/mgmt/config")
def mgmt_config(body: OrgCfg):
    return pform.set_org(body.org, body.kind, body.modules, body.branding, body.settings)


@app.get("/mgmt/catalog")
def mgmt_catalog(org: str = "default", kind: str = "service_type", include_inactive: bool = False):
    return pform.list_catalog(org, kind, include_inactive)


@app.post("/mgmt/catalog")
def mgmt_catalog_add(body: CatalogIn):
    try:
        return pform.add_catalog(body.org, body.kind, body.name, body.data, body.key)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/catalog/{cid}")
def mgmt_catalog_update(cid: int, body: dict):
    try:
        return pform.update_catalog(cid, body.get("name"), body.get("data"), body.get("active"), body.get("sort"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/mgmt/fields")
def mgmt_fields(org: str = "default", entity: str = "member"):
    return pform.fields_for(org, entity)


@app.post("/mgmt/fields")
def mgmt_fields_add(body: FieldIn):
    try:
        return pform.add_field(body.org, body.entity, body.label, body.type, body.options, body.required, body.section)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/mgmt/fields/{fid}")
def mgmt_fields_del(fid: int):
    pform.delete_field(fid); return {"ok": True}


@app.get("/mgmt/form")
def mgmt_form(org: str = "default", entity: str = "member"):
    return pform.form_schema(org, entity)


# ---- Centre operations ----
class MemberIn(BaseModel):
    org: str = "default"
    name: str
    phone: str = ""
    email: str = ""
    patient_id: int | None = None
    fields: dict | None = None


class BookIn(BaseModel):
    org: str = "default"
    member_id: int
    service_id: int
    start_ts: str
    staff_id: int | None = None
    resource_id: int | None = None
    fields: dict | None = None


@app.get("/mgmt/centre/dashboard")
def mgmt_centre_dash(org: str = "default", day: str | None = None):
    return centremod.dashboard(org, day)


@app.get("/mgmt/centre/members")
def mgmt_members(org: str = "default"):
    return centremod.list_members(org)


@app.post("/mgmt/centre/members")
def mgmt_member_add(body: MemberIn):
    try:
        return centremod.add_member(body.org, body.name, body.phone, body.email, body.patient_id, body.fields)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/mgmt/centre/members/{mid}")
def mgmt_member(mid: int):
    m = centremod.member(mid)
    if not m:
        raise HTTPException(404, "no such member")
    return m


@app.post("/mgmt/centre/members/{mid}/enroll")
def mgmt_enroll(mid: int, body: dict):
    try:
        return centremod.enroll(body.get("org", "default"), mid, int(body["plan_id"]))
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@app.get("/mgmt/centre/schedule")
def mgmt_schedule(org: str = "default", day: str | None = None):
    return centremod.schedule(org, day)


@app.post("/mgmt/centre/book")
def mgmt_book(body: BookIn):
    try:
        return centremod.book(body.org, body.member_id, body.service_id, body.start_ts, body.staff_id, body.resource_id, body.fields)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/centre/bookings/{bid}/checkin")
def mgmt_checkin(bid: int):
    try:
        return centremod.check_in(bid)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/centre/bookings/{bid}/status")
def mgmt_book_status(bid: int, body: dict):
    try:
        return centremod.set_status(bid, body.get("status", ""))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/centre/invoices/{iid}/pay")
def mgmt_pay(iid: int, body: dict):
    return centremod.pay(iid, body.get("method", "card"))


# ---- Clinic (doctor) operations ----
@app.get("/mgmt/clinic/inbox")
def mgmt_inbox(org: str = "default", doctor_id: int = 2):
    return clinicmod.inbox(org, doctor_id)


@app.get("/mgmt/clinic/templates")
def mgmt_templates(org: str = "default"):
    return clinicmod.templates(org)


@app.get("/mgmt/clinic/patients/{pid}/notes")
def mgmt_notes(pid: int):
    return clinicmod.notes_for(pid)


@app.post("/mgmt/clinic/patients/{pid}/notes")
def mgmt_note_add(pid: int, body: dict):
    try:
        return clinicmod.add_note(body.get("org", "default"), pid, body.get("author", "Doctor"), body.get("template_id"),
                                  body.get("title", ""), body.get("content"), body.get("fields"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/clinic/notes/{nid}/sign")
def mgmt_note_sign(nid: int, body: dict):
    return clinicmod.sign(nid, body.get("by", "Doctor"))


@app.get("/mgmt/clinic/tasks")
def mgmt_tasks(org: str = "default", status: str = "open"):
    return clinicmod.tasks(org, status)


@app.post("/mgmt/clinic/tasks")
def mgmt_task_add(body: dict):
    try:
        return clinicmod.add_task(body.get("org", "default"), body.get("text", ""), body.get("patient_id"),
                                  body.get("assignee", ""), body.get("due"), int(body.get("priority", 1)))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/mgmt/clinic/tasks/{tid}/complete")
def mgmt_task_done(tid: int):
    return clinicmod.complete_task(tid)


@app.get("/bioage")
def bioage_all():
    """Every kind of age from your data — blood (PhenoAge, KDM, dysregulation), fitness, muscle, heart, organs."""
    return bioage.all_ages()


@app.get("/cellular/explain")
def cellular_explain(name: str):
    """What a supplement/medicine/food/stressor does at the cellular level, and which markers it moves."""
    from . import cellular
    return cellular.explain(name)


@app.get("/cellular/marker/{marker_id}")
def cellular_marker(marker_id: str):
    from . import cellular
    return cellular.for_marker(marker_id)


@app.get("/sinc/insights")
def sinc_insights():
    """The connected story — Sinc links labs, wearables, trackers and genetics into themed threads with evidence."""
    from . import retrieval
    return retrieval.connect()


@app.get("/sinc/retrieve")
def sinc_retrieve(q: str, k: int = 12):
    """What Sinc would ground on for a question (debug/transparency): the retrieved cards."""
    from . import retrieval
    return [{"id": c["id"], "kind": c["kind"], "title": c["title"], "text": c["text"]} for c in retrieval.retrieve(q, k)]


@app.get("/sinc/chats")
def chats():
    return db.rows("""SELECT c.*, (SELECT content FROM messages m WHERE m.chat_id = c.id AND role = 'assistant'
                      ORDER BY id DESC LIMIT 1) AS preview FROM chats c ORDER BY c.ts DESC""")


@app.get("/sinc/chats/{cid}")
def chat(cid: int):
    ms = db.rows("SELECT * FROM messages WHERE chat_id = ? ORDER BY id", (cid,))
    for m in ms:
        m["meta"] = db.unj(m["meta"], {})
    return ms


class DraftIn(BaseModel):
    message_id: int


@app.post("/sinc/draft-for-clinician")
def draft(body: DraftIn):
    m = db.one("SELECT * FROM messages WHERE id = ?", (body.message_id,))
    if not m:
        raise HTTPException(404, "Message not found")
    q = db.one("SELECT content FROM messages WHERE chat_id = ? AND id < ? AND role = 'user' ORDER BY id DESC LIMIT 1",
               (m["chat_id"], m["id"]))
    meta = db.unj(m["meta"], {})
    iid = engine._iid("sinc-draft", m["id"])
    db.exec_("""INSERT OR REPLACE INTO insights (id, created_at, kind, title, body, confidence, evidence, receipts, review_state,
                medical, dismissed) VALUES (?,?,?,?,?,?,?,?,?,?,0)""",
             (iid, now(), "sinc_draft", f"Question for your clinician: {(q or {}).get('content', '')[:70]}", m["content"],
              meta.get("confidence", 0.5), db.j([{"type": c["type"], "id": c["id"], "name": c["label"]} for c in meta.get("chips", [])]),
              db.j({"method": meta.get("engine"), "source": "Sinc chat"}), "awaiting", 1))
    db.exec_("INSERT INTO review_thread (insight_id, ts, author, action, note) VALUES (?,?,?,?,?)",
             (iid, now(), "You", "request", "Sent from Sinc chat."))
    return {"insight_id": iid, "message": "Drafted and sent to Dr. Meera Rao's queue."}


@app.get("/memories")
def memories():
    return db.rows("SELECT * FROM memories ORDER BY ts DESC")


@app.delete("/memories/{mid}")
def forget(mid: int):
    db.exec_("DELETE FROM memories WHERE id = ?", (mid,))
    return {"ok": True}

# ------------------------------------------------------------------ domains, longevity

@app.get("/domains/{key}")
def domain(key: str, as_of: str | None = None):
    if key not in engine.DOMAINS:
        raise HTTPException(404, "Unknown domain")
    d = engine.domain_score(key, as_of)
    names = {i["name"] for p in d["pillars"] for i in p["inputs"]}
    d["related"] = [i for i in engine.list_insights() if any(n.lower() in i["body"].lower() for n in names)][:6]
    return d


@app.get("/longevity")
def longevity(as_of: str | None = None):
    return engine.longevity_age(as_of)

# ------------------------------------------------------------------ protocols, today, sessions

@app.get("/protocols")
def protocols():
    out = []
    for r in db.rows("SELECT * FROM protocols"):
        p = db.unj(r["data"])
        p["active"] = bool(r["active"])
        out.append(p)
    return sorted(out, key=lambda p: not p["active"])


@app.post("/protocols/{pid}/activate")
def activate(pid: str):
    if not db.one("SELECT id FROM protocols WHERE id = ?", (pid,)):
        raise HTTPException(404, "Protocol not found")
    db.exec_("UPDATE protocols SET active = 0")
    db.exec_("UPDATE protocols SET active = 1 WHERE id = ?", (pid,))
    return {"ok": True, "message": "Requested. Your clinician confirms before it starts."}


@app.get("/today")
def today_list(day: str | None = None):
    day = day or today()
    r = db.one("SELECT data FROM protocols WHERE active = 1")
    if not r:
        return {"day": day, "protocol": None, "items": []}
    p = db.unj(r["data"])
    done = {x["item_id"] for x in db.rows("SELECT item_id FROM checklist WHERE day = ? AND done = 1", (day,))}
    items = [{**it, "pillar": pil, "done": it["id"] in done} for pil, its in p["pillars"].items() for it in its]
    return {"day": day, "protocol": {"id": p["id"], "title": p["title"], "clinician": p["clinician"]}, "items": items}


class Check(BaseModel):
    item_id: str
    done: bool
    day: str | None = None


@app.post("/today")
def check(body: Check):
    db.exec_("INSERT OR REPLACE INTO checklist (day, item_id, done) VALUES (?,?,?)", (body.day or today(), body.item_id, int(body.done)))
    return today_list(body.day)


class SessionIn(BaseModel):
    kind: str
    minutes: float
    data: dict | None = None


@app.post("/sessions")
def add_session(body: SessionIn):
    db.exec_("INSERT INTO sessions_log (ts, kind, minutes, data) VALUES (?,?,?,?)", (now(), body.kind, body.minutes, db.j(body.data or {})))
    db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?, 'mindful_min', COALESCE((SELECT value FROM "
             "signals WHERE day = ? AND metric = 'mindful_min'), 0) + ?, 'Telomy')", (today(), today(), body.minutes))
    return {"ok": True, "message": f"Session saved · {round(body.minutes)} min"}


@app.get("/sessions")
def sessions():
    rs = db.rows("SELECT * FROM sessions_log ORDER BY ts DESC LIMIT 30")
    total = db.one("SELECT COALESCE(SUM(minutes),0) AS m, COUNT(*) AS n FROM sessions_log")
    return {"items": rs, "total_minutes": round(total["m"]), "count": total["n"]}

# ------------------------------------------------------------------ N-of-1

@app.get("/studies")
def studies():
    out = []
    for s in db.rows("SELECT * FROM studies ORDER BY id DESC"):
        s["result"] = engine.analyse_study(s)
        s["outcome_label"] = engine.SIGNALS[s["outcome"]][0]
        out.append(s)
    return out


class StudyIn(BaseModel):
    title: str
    intervention: str
    outcome: str = "deep_sleep"
    period_days: int = 7
    start_day: str | None = None


@app.post("/studies")
def new_study(body: StudyIn):
    if body.outcome not in engine.SIGNALS:
        raise HTTPException(400, "Unknown outcome")
    base = engine.signal_baseline(body.outcome, days=60)
    if not base:
        raise HTTPException(400, "I need at least a few weeks of this signal before a study can detect anything.")
    detectable = round(2.8 * base["sd"] / (body.period_days * 2) ** 0.5, 2)
    start = body.start_day or (date.fromisoformat(today()) + timedelta(days=1)).isoformat()
    sid = db.exec_("""INSERT INTO studies (title, intervention, outcome, design, start_day, period_days, status, data)
                      VALUES (?,?,?,?,?,?,?,?)""", (body.title, body.intervention, body.outcome, "ABAB", start,
                                                   body.period_days, "scheduled", db.j({"min_detectable": detectable})))
    lab, unit, _, _ = engine.SIGNALS[body.outcome]
    return {"id": sid, "start_day": start, "min_detectable": detectable, "message":
            f"Scheduled. With your day-to-day variation, this design can detect a change of about {detectable} {unit} "
            f"in {engine.lc(lab)}. Weeks 1 and 3 are off, weeks 2 and 4 are on."}

# ------------------------------------------------------------------ consent, sharing, care, briefs

PURPOSES = {
    "wearable_sync": ("Wearable sync", "Heart rate, HRV, sleep and activity from your devices", "You, Sinc", "Until you revoke"),
    "lab_analysis": ("Lab analysis", "Reading your lab PDFs to extract biomarkers", "You, Sinc", "Until you delete the report"),
    "sinc_ai": ("Sinc AI", "Sending a context pack of your Vault to the language model to answer you", "Anthropic (processor), no training", "30 days"),
    "clinician_sharing": ("Clinician sharing", "Your clinician sees your Vault and Sinc's drafts", "Your linked clinicians", "Until revoked"),
    "research": ("Research", "De-identified data in approved studies", "Telomy research partners (IRB-approved)", "Study duration"),
    "family_sharing": ("Family Vault", "Scoped summaries to people you choose", "People you invite", "Per share expiry"),
    "cycle_tracking": ("Cycle tracking", "Menstrual cycle data and predictions", "You", "Until revoked"),
    "marketing": ("Product emails", "Occasional updates about Telomy", "Telomy", "Until unsubscribed"),
}


@app.get("/consents")
def consents():
    cur = {r["purpose"]: r for r in db.rows("SELECT * FROM consents")}
    return [{"purpose": k, "title": v[0], "what": v[1], "who": v[2], "retention": v[3],
             "granted": bool(cur.get(k, {}).get("granted")), "updated_at": cur.get(k, {}).get("updated_at")}
            for k, v in PURPOSES.items()]


class ConsentIn(BaseModel):
    granted: bool


@app.post("/consents/{purpose}")
def set_consent(purpose: str, body: ConsentIn):
    if purpose not in PURPOSES:
        raise HTTPException(404, "Unknown purpose")
    db.exec_("INSERT OR REPLACE INTO consents (purpose, granted, updated_at) VALUES (?,?,?)", (purpose, int(body.granted), now()))
    db.exec_("INSERT INTO consent_history (purpose, granted, ts) VALUES (?,?,?)", (purpose, int(body.granted), now()))
    msg = "Granted." if body.granted else "Revoked. Any copies held for this purpose are deleted within 24 hours."
    return {"ok": True, "message": msg}


@app.get("/consents/history")
def consent_history():
    return [{**r, "title": PURPOSES[r["purpose"]][0]} for r in db.rows("SELECT * FROM consent_history ORDER BY ts DESC, id DESC")]


@app.get("/shares")
def shares():
    rs = db.rows("SELECT * FROM shares ORDER BY created_at DESC")
    for r in rs:
        r["scopes"] = db.unj(r["scopes"], [])
    return {"shares": rs, "log": db.rows("SELECT * FROM access_log ORDER BY ts DESC, id DESC LIMIT 30")}


class ShareIn(BaseModel):
    name: str
    relation: str
    scopes: list[str]
    days: int = 30


@app.post("/shares")
def add_share(body: ShareIn):
    exp = (date.fromisoformat(today()) + timedelta(days=body.days)).isoformat()
    sid = db.exec_("INSERT INTO shares (name, relation, scopes, expires_on, status, created_at) VALUES (?,?,?,?,?,?)",
                   (body.name, body.relation, db.j(body.scopes), exp, "active", now()))
    return {"id": sid, "expires_on": exp}


@app.post("/shares/{sid}/revoke")
def revoke(sid: int):
    db.exec_("UPDATE shares SET status = 'revoked' WHERE id = ?", (sid,))
    return {"ok": True}


@app.get("/clinicians")
def clinicians():
    return [db.unj(r["data"]) for r in db.rows("SELECT * FROM clinicians")]


@app.get("/appointments")
def appointments():
    rs = db.rows("SELECT * FROM appointments ORDER BY ts")
    cl = {c["id"]: c for c in clinicians()}
    for r in rs:
        r["clinician"] = cl.get(r["clinician_id"])
    return rs


class ApptIn(BaseModel):
    clinician_id: str
    ts: str
    kind: str
    reason: str = ""


@app.post("/appointments")
def book(body: ApptIn):
    aid = db.exec_("INSERT INTO appointments (clinician_id, ts, kind, status, reason) VALUES (?,?,?,?,?)",
                   (body.clinician_id, body.ts, body.kind, "requested", body.reason))
    return {"id": aid, "status": "requested", "message": "Requested. The clinic confirms by SMS."}


@app.post("/appointments/{aid}/cancel")
def cancel(aid: int):
    db.exec_("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (aid,))
    return {"ok": True}


@app.get("/brief/{specialty}.pdf")
def brief_pdf(specialty: str):
    if specialty not in brief.SPECIALTIES:
        raise HTTPException(404, "Unknown specialty")
    return Response(brief.pdf(specialty), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="telomy-brief-{specialty}.pdf"'})


@app.get("/brief/{specialty}.json")
def brief_json(specialty: str):
    if specialty not in brief.SPECIALTIES:
        raise HTTPException(404, "Unknown specialty")
    return brief.fhir_bundle(specialty)


@app.get("/brief")
def brief_list():
    return [{"id": k, "title": v["title"]} for k, v in brief.SPECIALTIES.items()]

# ------------------------------------------------------------------ misc

@app.get("/completeness")
def completeness():
    return engine.completeness()


@app.get("/imaging")
def imaging():
    return [{"id": r["id"], **db.unj(r["data"])} for r in db.rows("SELECT * FROM imaging")]


@app.get("/research")
def research():
    granted = bool((db.one("SELECT granted FROM consents WHERE purpose = 'research'") or {}).get("granted"))
    return {"enrolled": granted, "studies": [
        {"title": "Alcohol and overnight HRV in South Asian adults", "status": "Recruiting", "your_data": "HRV, events", "n": 1240},
        {"title": "Gut diversity and hs-CRP", "status": "Analysis", "your_data": "Gut panel, blood panel", "n": 610},
        {"title": "Sauna frequency and deep sleep", "status": "Preprint published", "your_data": "Sleep, events", "n": 2875,
         "preprint": "medRxiv 2026.08.14 (test entry)"}]}


# ----------------------------------------------------------------------------- ECG band (KY-E-B1)

class BandMinutesIn(BaseModel):
    items: list[dict]


@app.post("/band/minutes")
def band_minutes_save(body: BandMinutesIn):
    try:
        return band.save_minutes(body.items)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@app.get("/band/minutes")
def band_minutes(hours: int = 24):
    return band.minutes(hours)


@app.get("/band/summary")
def band_summary():
    return band.summary()


@app.post("/band/strips")
def band_strip_save(body: dict):
    try:
        return band.save_strip(body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/band/strips")
def band_strips():
    return band.strips()


@app.get("/band/strips/{sid}")
def band_strip(sid: int):
    r = band.strip(sid)
    if not r:
        raise HTTPException(404, "ECG strip not found")
    return r


@app.post("/band/recordings")
def band_recording_save(body: dict):
    try:
        return band.save_recording(body)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@app.get("/band/recordings")
def band_recordings():
    return band.recordings()


class BandEventsIn(BaseModel):
    items: list[dict]


@app.post("/band/events")
def band_events_save(body: BandEventsIn):
    try:
        return band.save_events(body.items)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@app.post("/band/captures")
def band_capture_save(body: dict):
    try:
        return band.save_capture(body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/band/captures")
def band_captures():
    return band.captures()


@app.get("/band/captures/{cid}")
def band_capture(cid: str):
    b = band.capture_bundle(cid)
    if not b:
        raise HTTPException(404, "Capture not found")
    return b


@app.get("/band/events")
def band_events(days: int = 30):
    return band.events(days)
