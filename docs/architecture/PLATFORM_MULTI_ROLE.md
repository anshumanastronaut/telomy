# Telomy Platform — Multi-Role System Design

**Status:** implemented (backbone) · **Owner:** platform · **Last updated:** 2026-10-19

This is the authoritative design for the four cooperating surfaces of Telomy — **User**, **Doctor**,
**Centre**, and **Super-admin** — and the one data backbone that keeps them in sync with no
communication breakage. It is written so a new engineer (or a teammate's repo) can pick up any one
surface without breaking the others.

---

## 1. The four workspaces

| Workspace | Who | App surface | Signs in via |
|-----------|-----|-------------|--------------|
| **platform** | Telomy super-admin | Network console (`/console`, platform nav) | `super_admin` staff account |
| **doctor** | Clinicians, clinic admins | Doctor console (`/console`, doctor nav) + mobile later | `doctor`, `clinic_admin` |
| **centre** | Wellness-centre staff of every kind | Centre console (`/console`, centre nav) | `centre_admin`, `centre_manager`, `centre_staff`, `therapist`, `operator`, `nurse`, `physio`, `nutritionist`, `trainer` |
| **user** | The person being cared for | Telomy mobile app (RN/Expo) | `accounts.py` per-user Vault |

**Logins are separate by design.** One staff login resolves to exactly one workspace
(`staff.ROLES[role].workspace`). A doctor never sees the centre console and vice-versa; the
super-admin lives in the platform workspace. The console enforces this in `boot()` (`S.allowedWs =
[S.ws]`) and in `route()` (a hash into a disallowed workspace bounces home). The backend enforces it
in `_guard_staff_creation()` and the `_require_*` dependencies — the UI gate is convenience, the API
gate is the real boundary.

---

## 2. Identity model (three distinct identity planes — intentional)

1. **Staff** (`staff.py`, shared management DB) — everyone who operates a console. PBKDF2-HMAC-SHA256,
   opaque bearer tokens (`staff_tokens`). Scoped to an `org` (a centre slug) or to `platform`.
2. **Patients / people** (`roles.py:patients`, shared management DB) — the clinical record of a
   person. May be a seeded panel patient or a real app user, linked by `data.user_ref`.
3. **App users** (`accounts.py`, **per-user SQLite** selected by a contextvar) — the consumer's Vault:
   wearables, labs, bio-age, trackers. Physically isolated per user.

These are deliberately separate: clinical/management data is multi-tenant and shared within an org;
a consumer's raw Vault is private and isolated. The **care graph** (below) is the bridge.

---

## 3. The care graph — the single source of truth for "who is connected to whom"

`tenancy.py` holds the whole network as a small set of edges, so either side always sees the full
picture and numbers can never drift.

```
centres(slug=org) ──< provider_centre >── staff(role=doctor)        doctor ⇄ centre (M:N affiliation)
        │                                         │
        │ care_edges(kind='centre')               │ care_edges(kind='doctor')
        ▼                                         ▼
      patients ◀───────────────────────── patients.doctor_id
        │
        └─ care_edges mirror into c_members (centre.py) so centre screens see them
staff(delivers) ──< staff_duties(duty_kind in {service,resource}) >── catalog(service_type|resource)
```

**Two symmetric onboarding flows, one table:**

- **Doctor intake → centre.** A doctor intakes a patient (`POST /mgmt/patients/onboard`) and refers
  them to a centre (`assign_to_centre`). This opens a `care_edges(kind='centre')` edge and mirrors the
  person into that centre's `c_members`, so the centre sees them immediately.
- **Centre onboard → doctor.** A centre onboards a walk-in and assigns them to an affiliated doctor
  (`assign_to_doctor`), which sets `patients.doctor_id` and opens a `care_edges(kind='doctor')` edge, so
  the patient appears on that doctor's panel immediately.

A person has at most **one active centre edge** and **one active doctor edge**; reassigning closes the
prior edge (`status='ended'`) — history is preserved, nothing is deleted. `patient_graph(pid)` returns
the live centre, doctor, and full edge history for any view that needs the thread.

---

## 4. Role capabilities (RBAC)

Enforced server-side (`main.py` `_require_staff` / `_require_org_admin` / `_require_super` and
`_guard_staff_creation`):

- **super_admin** — onboards centres (`/mgmt/admin/centres`), mints & affiliates doctors
  (`/mgmt/admin/doctors`), sees the whole network (`/mgmt/admin/overview`). Only a super-admin can
  create platform accounts or affiliate across orgs.
- **centre_admin / centre_manager** — full centre: onboard people, add centre-side staff of every kind,
  build therapies & machines, assign duties, affiliate-view doctors, see performance & revenue.
  **Cannot** create doctor-side or platform accounts, nor touch another org.
- **centre_staff / therapist / operator / nurse / physio / nutritionist / trainer** — operate the
  centre (schedule, members, check-in, orders); the `delivers=True` roles accrue performance + revenue.
- **clinic_admin** — full doctor side incl. doctor-side staff.
- **doctor** — own panel: intake, chart, prescribe, refer to centre. Not an admin.

Privilege escalation is structurally impossible through the staff-creation endpoints: a non-super admin
can only create roles **in their own workspace and own org**, and never `super_admin`.

---

## 5. One app runs the whole centre (no separate billing tool)

Everything a centre needs is in the centre workspace and rolls up from the operational ledger, so
there is **no separate bookkeeping to reconcile**:

- **Revenue** (`centre_revenue`) = paid invoices (`c_invoices`) + delivered-session value
  (`c_bookings` in `checked_in|completed`) + fulfilled orders (`fulfillment.orders`) − outstanding.
- **Staff performance** (`staff_performance`) = per-staff booked / delivered / no-show / revenue, from
  `c_bookings.staff_id × price`. Derived on read — it can never disagree with operations.
- Machines/rooms (`catalog:resource`), therapies (`catalog:service_type`), memberships, scheduling,
  fulfilment, goals, interop (FHIR/API-keys/webhooks) are all modules toggled per centre (`platform.py`).

---

## 6. Connecting the user side (no communication breakage)

The consumer app's Vault stays isolated. The management side references a user by `patients.data.user_ref`
and pulls a **read-only snapshot** through the user-scoped API when a clinician needs it — the Vault is
never copied wholesale into the shared DB. This keeps the privacy boundary intact while letting the
doctor chart and the centre plan therapy against real signals. The care-queue the doctor sees is built
from the user's own insights, surfaced (not duplicated) via the clinical inbox.

**Integration contract for the team repo (mclarenmervin/Telomy, Supabase):** the care graph tables
(`centres`, `provider_centre`, `care_edges`, `staff_duties`) map 1:1 onto Supabase tables with RLS keyed
by `org` and `staff_id`; the FastAPI layer can run as-is against Supabase/Postgres by swapping `db.py`.
See `docs/ARCHITECTURE_HANDOFF.md`.

---

## 7. Proprietary aging model — design (PINN-grounded, app stays small)

Today's bio-age engine is a **validated, declarative rule system** (PhenoAge/KDM/Homeostatic
Dysregulation, NHANES-validated — `docs/research/BIOAGE_RESEARCH.md`). The next step is a **proprietary
hybrid** that stays scientifically honest and keeps the app small:

```
        ┌─────────────────────────────────────────────────────────────┐
        │  Agentic layer (server-side, Anthropic API) — deep research  │
        │  retrieves/updates fact-cards & science registry rules       │
        └───────────────┬─────────────────────────────────────────────┘
                        │ new evidence as DATA (no redeploy)
        ┌───────────────▼───────────────┐     ┌──────────────────────────┐
        │  Rule engine (prior/guardrail) │ ──▶ │  PINN trajectory model    │
        │  PhenoAge/KDM/HD, registry     │     │  (physics-informed)       │
        └───────────────┬───────────────┘     └───────────┬──────────────┘
                        │                                   │
                        └──────────── reconciled bio-age ◀──┘
```

- **PINN = Physics-Informed Neural ODE** over the aging trajectory. The "physics" are the known
  constraints: monotone cumulative damage, bounded repair, mortality-hazard links (Gompertz), and the
  marker↔age relationships the rule engine already encodes. The network learns the **residual dynamics**
  the rules miss, regularised to never violate those constraints (loss = data term + physics-residual
  term + rule-prior term). This gives per-person *rate-of-aging* and forward trajectories, not just a
  point estimate.
- **Not rigid.** Rules live in the science registry (data). The agentic layer ingests new papers and
  edits rules/fact-cards; the PINN is periodically re-fit offline. New science enters without a code
  change.
- **App stays small.** Training is offline; the device ships **coefficients + a tiny inference head**
  (the heavy RAG/agent work is server-side via the Anthropic API). The on-device SLM keeps its
  number-grounding guard.
- **Honesty preserved.** GrimAge-class methylation outputs still require a methylation test; the PINN
  never fabricates a measured marker. Synthetic data stays `is_test_data=1`.

Model training/validation lives in `telomy-lab/`; see `docs/research/DATA_AND_MODELS_ROADMAP.md`.

---

## 8. Git branch strategy (per surface)

The backbone is cross-cutting (one care graph serves all four surfaces), so it lands on the integration
branch first; each surface then has a feature branch for its own iteration:

| Branch | Scope |
|--------|-------|
| `feat/super-admin-console` | platform workspace — network overview, onboard centres/doctors |
| `feat/centre-console` | centre workspace — people, staff, therapies, machines, duties, performance, revenue |
| `feat/doctor-console` | doctor workspace — intake, panel, charting, referral to centre, Rx |
| `feat/user-app` | consumer mobile app — Vault, wearables, bio-age, Sinc, home |

Shared code (`tenancy.py`, `staff.py`, `platform.py`, `db.py`) is owned by the integration branch;
surface branches rebase on it. See `docs/TASKS.md` for the live task list.

---

## 9. Endpoint map (management API)

```
auth      POST /mgmt/auth/signup|login|logout   GET /mgmt/auth/me|status
staff     GET/POST /mgmt/staff   POST /mgmt/staff/{id}/active|profile
admin     GET /mgmt/admin/overview|centres|staff   POST /mgmt/admin/centres|doctors
          POST /mgmt/admin/centres/{slug}/status
care      POST /mgmt/patients/onboard   POST /mgmt/assign/centre|doctor
          GET  /mgmt/patients/{id}/graph
          GET  /mgmt/centre/people|doctors   POST /mgmt/centre/doctors (affiliate)
          GET  /mgmt/doctor/patients|centres
duties    GET/POST/DELETE /mgmt/duties
business  GET /mgmt/centre/performance|revenue
(existing) /mgmt/centre/*, /mgmt/clinic/*, /mgmt/catalog, /mgmt/orders, /mgmt/goals, /mgmt/interop/*
```

All `/mgmt/*` require a staff bearer token; `/mgmt/admin/*` require `super_admin`; org-mutating routes
require an admin of that org (or a super-admin).
