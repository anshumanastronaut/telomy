# Telomy — Notification & Alerting Specification

*Prepared 28 Oct 2026. Scope: every notification each of the three roles (user/patient, doctor, centre) should receive across every channel, plus the inbound report/result flows that generate them. India-first (70/30), DPDP-governed, single-worker 512MB–1GB Oracle micro box. Audit line-refs are to `/Users/anshuman/telomy-app`.*

---

## PART A — What exists today (repo audit)

### A.1 The one notification surface that exists
Telomy has a single, **pull-model, in-app-only** notification system. There is no stored notification record, no delivery, no channels beyond the app screen.

- **Builder:** `backend/app/features.py:159` `notifications(today)`. Recomputes the full list on every request by scanning source tables. Six kinds, all patient-facing:
  - `shared_doc` — from `sharedocs.pending()` (`sharedocs.py:46`): doctor-shared docs awaiting the patient's confirm. Route `/shared`.
  - `retest` — from `derived.retest_nudges()` (`derived.py:126`): out-of-range markers past 60% of their retest interval. Route `/(tabs)/vault`.
  - `review` — rows in `review_thread` where author ∉ {You, Sinc} (a clinician acted on a Sinc draft). Route `/insight/{id}`.
  - `insight` — top `cross_panel` insights with confidence ≥ 0.75 (`engine.list_insights()`). Route `/insight/{id}`.
  - `appointment` — future, non-cancelled rows in `appointments`. Route `/care`.
  - `medication` — active meds with doses still due today (`features.meds()`). Route `/meds`.
- **Endpoints:** `main.py:1574` `GET /notifications` → `features.notifications(today())`; `main.py:1579` `POST /notifications/read` writes keys into `notif_read`.
- **Read-state storage:** `db.py:70` `CREATE TABLE notif_read (key TEXT PRIMARY KEY)`. Key = `f"{kind}:{title}"` (`features.py:187`). This is a dedup/read set only — **no per-notification row, no timestamp, no channel, no per-user audit, no "delivered" state.** Because the key is `kind:title`, two different nudges that render the same title collide, and a title that changes (e.g. marker count) resets read-state.
- **Client:** `mobile/src/app/notifications.tsx` renders the list, marks read on tap, routes. Icon map covers only {retest, review, insight, appointment, medication} — `shared_doc` falls through to a default bell. No badge count, no grouping, no filtering.

### A.2 Channels: only in-app. Nothing else is wired.
Exhaustive grep for `smtp|sendgrid|twilio|mailgun|whatsapp|expo-notifications|getExpoPushToken|device_token|push_token|firebase|fcm|apns|msg91|gupshup|dlt` across `backend/**/*.py` and `mobile/src` returns **zero senders**.
- **Push:** none. `mobile/package.json` has no `expo-notifications`; no push token registration anywhere.
- **Email/SMS/WhatsApp:** none. The only SMS references are UI copy strings — OTP verify error "Check the SMS and try again" (`main.py:261`) and appointment booking returning `"Requested. The clinic confirms by SMS."` (`main.py:4092`). **No SMS is actually sent.**
- **OTP is stubbed:** `/auth/otp/send` returns `dev_hint: use 000000`; `/auth/otp/verify` only accepts `000000` (`main.py:253–262`). There is no real OTP/SMS provider.

### A.3 Webhook / interop infra exists but is inert
`backend/app/interop.py` implements outbound webhooks (`add_webhook`, `fire()` signing payloads with HMAC) and advertises events `order.updated, booking.created, note.signed, lab.result`, plus FHIR R4 export (`fhir_patient/observations/bundle`, exposed at `/interop/fhir/Patient`, `/interop/fhir/Bundle`). **`fire()` has zero callers** — no event is ever emitted. The plumbing for "notify an external EHR when a lab result lands" exists but is not triggered.

### A.4 Consent model exists; notification preferences do not
- **Consent:** `main.py:3999` `PURPOSES` defines 8 purposes: `wearable_sync, lab_analysis, sinc_ai, clinician_sharing, research, family_sharing, cycle_tracking, marketing`. Endpoints `GET/POST /consents`, `GET /consents/history`; stored in `consents` + `consent_history` (`db.py:44`). Revoke message promises deletion within 24h. `marketing` ("Product emails") already a separate opt-in — good DPDP posture.
- **Preferences:** **no per-category / per-channel / quiet-hours notification preference model** on the patient side. Staff side has coarse booleans only: `DOCTOR_SETTINGS_DEFAULTS` has `notify_findings, notify_bookings, notify_labs`; `CENTRE_SETTINGS_DEFAULTS` has `notify_bookings, notify_cancellations, notify_outstanding` (`main.py:2768–2785`) — flags with no delivery behind them.

### A.5 Doctor / centre queues exist (as screens, not alerts)
- Care-review queue: `GET /care/queue` (`main.py:1867`) returns insights where `review_state='awaiting'`. Dashboards surface `awaiting_reviews`/`pending_reviews` counts (`roles.py:142–180`, `main.py:1369`, `clinic.py:102`).
- Doctor "act" surface: `main.py:2639+` returns findings awaiting review + Rx drafts; sign-off at `main.py:2662`; co-sign/approval gate at `main.py:2590`.
- Centre: `centre.py` (members, subscriptions, bookings), `clinic.py` tasks (`cl_tasks`). These are **polled screens** — nothing pushes to the clinician.

### A.6 Inbound ingestion today (detail in Part D)
- **Lab reports: PDF only.** `labparse.py` (pypdf) via `POST /labs/parse` (multipart), `/labs/parse_b64` (base64 JSON — the reliable RN path), `/labs/save` (persists + `engine.regenerate_insights()`). `/documents/parse` classifies PDFs (prescription/discharge/imaging/lab) and extracts meds.
- **No EML / email / CSV / inbound-HL7 ingest path exists.** CSV appears only for internal reference data (`rx.py` DDInter, nutrition DB).
- **Device inbound (not notifications):** `/cal/ingest`, `/whoop/push` (+ `GET` capabilities), `/nightscout/api/v1/entries` (CGM), `/vitals/ingest`. `DEVICE_SOURCES` includes Apple Health / Apple Watch (`main.py:1716`) — ingested as signals, no HealthKit sync service in-repo.
- **Critical-value flagging at ingest: none.** Marker `status` is taken from whatever the client sends or defaults to `"unknown"` (`seed.py:36–42`); out-of-range/optimal zoning is computed later for display (`derived.zone_for`, `engine`). There is **no "critical/panic" tier** and no safety alert on ingest.

### A.7 Offline durability (client)
`mobile/src/lib/api.ts:118+` has a durable outbox (AsyncStorage `telomy.outbox.v1`, cap 2000, oldest-dropped, flush on app-active). This is for **outbound device uploads**, not notification delivery — but it's the pattern to reuse for client-side notification-preference sync.

### A.8 Infra constraints that shape everything
`deploy/oracle/setup.sh`: single `uvicorn … --workers 1`, systemd + Caddy + `cron`, Oracle Always-Free micro (≤1GB, swap added). **No job queue, no Celery/Redis, no background worker.** SQLite with WAL + 30s busy-timeout (`db.py:76`), per-user DB selected by contextvar. Implication: notification generation and digests must be **cron-driven batch jobs**, and sends must be **cheap, rate-limited, and outsourced to a provider API**, never a resident worker pool.

**Summary — built vs missing**

| Capability | Status |
|---|---|
| In-app notification list (6 patient kinds) | Built (`features.py:159`) |
| Read-state | Partial — dedup set only, no per-notif row/ts/channel (`notif_read`) |
| Stored, timestamped, per-user notification records | Missing |
| Push (APNs/FCM/expo) | Missing |
| Email transactional | Missing |
| SMS (DLT) | Missing (copy only; OTP stubbed) |
| WhatsApp (BSP + templates) | Missing |
| Per-category/channel preferences + quiet hours | Missing (staff booleans only) |
| DPDP consent model | Built (8 purposes, incl. marketing opt-in) |
| Critical-value tier / auto-flag on ingest | Missing |
| Doctor/centre push alerts | Missing (polled queues only) |
| Outbound webhooks / FHIR export | Built but inert (`fire()` has no callers) |
| EML / CSV / inbound-HL7 / email ingest | Missing (PDF-only) |
| Client offline outbox | Built (device uploads) |

---

## PART B — Benchmarks & India channel/regulatory research

*Caveat: most product-behavior claims below are from secondary sources (vendor docs, comparison sites); India regulatory points are from law-firm/BSP summaries, not primary statute text. Verify template/DLT specifics against the live Meta and operator DLT portals, and DPDP against the notified Rules, before build. Sources at the end.*

### B.1 Consumer health apps
- **Function Health / Superpower (DTC labs):** results post to a dashboard with **every value flagged in-range vs out-of-range**; Function markets **clinician review of every result**, and reviews consistently frame any out-of-range value as "talk to a licensed clinician," explicitly **not a diagnosis** — results surfaced with context and a next step, never a bare "you're abnormal" push. The pattern Telomy's `clinician_notes()` TL;DR + review queue already mirrors.
- **Oura / Whoop (wearables):** daily **Readiness/Recovery score ready** push each morning; **anomaly nudges** (elevated resting HR, temperature deviation); **missing-night / sync reminders**; **streak/goal** engagement. Normal/low priority, batched to one morning summary rather than per-metric spam. Telomy already computes the equivalents (`features.dashboard` recovery/strain/stress, `retest.plan`) — just not delivered.

### B.2 India health apps — channel strategy
- WhatsApp is a **primary** report/appointment channel in Indian health apps (Apollo 24|7, Tata 1mg, Practo, Eka Care), alongside SMS and app push, because WhatsApp open/read rates far exceed email. Apollo 24|7 and Tata 1mg both advertise home collection with **progress updates and fast report delivery** and both run WhatsApp lines; public sources don't spell out the exact channel per event — treat "report-ready over WhatsApp + SMS fallback + app push" as the established-but-unconfirmed norm to validate.
- Practical India stack: **transactional SMS (DLT) for OTP and must-deliver events**, **WhatsApp utility templates for reports/appointments/reminders**, **app push for in-app engagement**, **email for records/exports and PDFs**.

### B.3 Clinical / EHR critical-value alerting (patient-safety)
- Accreditor expectation (CAP LAP / Joint Commission NPSG.02.03.01, per secondary sources): **≥90% of critical values reported within ~30 minutes of verification**; some policies target 15 min.
- **Closed-loop with read-back**: the receiver repeats the value back; the lab confirms and **documents date/time, who was notified, who notified**.
- Recipient must be a **licensed caregiver**; an **escalation policy** is required for non-acknowledgement.
- Verify exact timeframes/wording against current CAP and Joint Commission manuals.

### B.4 India regulatory specifics (must-honor)
- **DPDP Act 2023 + Rules (notified Nov 2025):** consent must be **free, specific, informed, unconditional, unambiguous, via clear affirmative action, and as easy to withdraw as to give**; a **notice precedes consent** (itemized data + purpose + rights + grievance path), and defective notice invalidates consent. Health-data processors are likely **Significant Data Fiduciaries** (DPO, audits, DPIA). **Medical-emergency / threat-to-life** processing is a legitimate use that does **not** require consent — the legal basis to let a true critical-value alert override an opt-out. Core consent/notice obligations (Rule 4) phase in toward **13 Nov 2026**.
- **TRAI TCCCPR 2018 / DLT:** three registrations — **entity, header (sender ID), content template**; carriers scrub and **block anything not matching a registered header+template**. Categories: **Transactional / Service(Implicit/Explicit) / Promotional**. Transactional & Service-Implicit can reach **DND** numbers 24×7; **Promotional requires explicit opt-in and is limited to 09:00–21:00 IST**. (A reported May-2025 header-suffix scheme `-T/-S/-P/-G` is single-sourced — verify.)
- **WhatsApp Business Platform:** every template is categorized **Utility / Authentication / Marketing**; **mixed/promotional content in a utility template gets reclassified to Marketing** (higher billing, stricter rules). **Opt-in is required** before business-initiated templates. A **user-initiated 24-hour customer-service window** lets you send free-form replies without a template. Authentication templates = OTP/essential-context only, no links/promo.
- **Email deliverability:** publish **SPF, DKIM, DMARC**; separate transactional vs marketing streams/subdomains.

### B.5 Cross-cutting best practices
Urgency tiering; **don't deliver alarming clinical results as a bare push** — notify "results ready, open to review with context," never "your LDL is dangerously high" on the lock screen; avoid diagnosis-by-notification; quiet hours for non-critical; batch low-value items into digests; strict separation of **transactional (must deliver)** vs **promotional (opt-in, quiet-hours, unsubscribe)**.

---

## PART C — The notification matrix (core deliverable)

**Legend — Priority:** Critical / High / Normal / Low. **Channels:** IA = in-app, PU = push, EM = email, SMS, WA = WhatsApp. **Timing:** RT = real-time, Dig = digest, Sch = scheduled. **Compliance tags:** TXN = transactional (DLT/WA-utility), PROMO = opt-in + quiet-hours, SAFETY = patient-safety override path, CONSENT = gated by a DPDP purpose.

**Global defaults applied across the matrix:**
- **Critical** → PU + SMS + WA simultaneously, RT, **bypass quiet hours**, closed-loop acknowledgement required, DPDP "medical emergency / vital interest" basis. Never put the clinical value itself in the lock-screen/SMS body — say "an important result needs your attention, open the app."
- **High** → PU primary, WA fallback if unread in N minutes, IA always. Respect quiet hours except time-sensitive (appointment in <2h, OTP).
- **Normal** → IA + PU, batched where sensible. Quiet hours honored.
- **Low / engagement** → IA + optional PU, **PROMO** (opt-in, quiet-hours 21:00–09:00 IST, unsubscribe). Digest by default.
- Every category has a per-category, per-channel user toggle except the SAFETY and security/OTP classes (always on).

### C.1 — USER / PATIENT

**1. Results & reports (inbound-driven — see Part D)**

| # | Notification | Trigger | Channels (default) | Priority | Timing | Consent/quiet-hours |
|---|---|---|---|---|---|---|
|U1|Lab result ready|Report ingested, parsed, markers persisted|**PU** + IA; WA fallback; EM with PDF|Normal|RT (minutes after ingest)|`lab_analysis` consent; quiet hours honored|
|U2|New report/document ingested (non-lab)|`/documents/parse` or share lands|IA + PU|Normal|RT|—|
|U3|**Abnormal value flagged**|Ingest marks a marker out_of_range|**PU** + IA; WA|High|RT, phrased "a result is outside range — review with Sinc/your clinician"|No value on lock screen|
|U4|**Critical / panic value**|Ingest hits critical threshold (K+ >6.0, glucose >400, Hb <7, platelets <20k…)|**PU + SMS + WA**, closed-loop ack; also alerts panel doctor (→D1)|**Critical / SAFETY**|RT, bypass quiet hours|Vital-interest basis; ack required; escalate if unacked|
|U5|Telomy Score / bio-age changed|Recompute crosses materiality threshold|IA + PU|Normal|RT or morning digest|Only on meaningful delta|
|U6|Retest due|`derived.retest_nudges`/`retest.plan` crosses due date|IA + PU; WA for long-overdue|Normal→High as overdue grows|Sch (weekly) + Dig|Quiet hours|
|U7|"What changed since last time"|`retest.plan` improving/worsening after a retest|IA + PU|Normal (good), High (worsening)|RT after retest ingested|Frame positively; worsening routes to care|

**2. Care & clinician**

| # | Notification | Trigger | Channels | Priority | Timing | Notes |
|---|---|---|---|---|---|---|
|U8|Doctor shared a document — **confirm to add**|`sharedocs.add()` → pending|IA + PU; WA|High|RT|Requires explicit patient accept. Today: IA-only.|
|U9|Doctor/centre message / consult recap ready|Consult scribe recap or secure message|IA + PU; WA|High|RT|Recap link, not clinical detail, on push|
|U10|Finding signed / care-plan updated|Doctor signs off, Rx/therapy plan approved|IA + PU|Normal|RT|—|
|U11|Sinc finding awaiting attention / sign-off visibility|`cross_panel` insight ≥0.75 or sent for review|IA + PU|Normal|RT/Dig|Current `insight`/`review` kinds|
|U12|Appointment reminders|`appointments` upcoming|IA + PU; **SMS + WA** at 24h and 2h|High|Sch (24h, 2h, on-booking)|TXN/WA-utility|
|U13|Appointment booked/confirmed/cancelled/rescheduled|Status change|IA + PU; WA|High|RT|Closes the `main.py:4092` fake-SMS gap|

**3. Medications & therapy**

| # | Notification | Trigger | Channels | Priority | Timing |
|---|---|---|---|---|---|
|U14|Medication/supplement dose reminder|`features.meds` dose due today & untaken|IA + PU (local scheduled)|Normal|Sch (per dose time)|
|U15|Adherence slipping|30-day adherence below threshold|IA + PU|Low|Dig weekly|
|U16|Therapy session / protocol step due|`therapy.py`/`protocols` schedule|IA + PU|Normal|Sch|
|U17|Drug-interaction / caution flag|`features.interactions()` match on active meds + events|IA + PU|High|RT on new med/event — "check with your clinician," never "stop taking"|

**4. Devices & wearables**

| # | Notification | Trigger | Channels | Priority | Timing |
|---|---|---|---|---|---|
|U18|Device disconnected / not syncing|No data from patch/ring/WHOOP/CGM for N hours|IA + PU|Low|Sch (once/day max)|
|U19|Device low battery|Device reports low battery (BLE)|IA (+ PU opt-in)|Low|RT, debounced|
|U20|Wearable night missing|No overnight sleep/HR block for last night|IA + PU|Low|Sch (morning)|
|U21|Recorder/overnight capture incomplete|`/cal` session gaps (TelomyRec)|IA|Low|Post-session|

**5. Engagement, goals, education (PROMO / opt-in)**

| # | Notification | Trigger | Channels | Priority | Compliance |
|---|---|---|---|---|---|
|U22|Daily morning summary (score, recovery, plan, due items)|Cron each morning|PU + IA|Low|Opt-in; the primary batching surface for U5/U6/U20|
|U23|Goal / streak milestone|`session_stats` streak, ring goals|IA + PU|Low|PROMO; quiet hours|
|U24|Weekly/monthly report ready|`/monthly-reports/{period}/generate`|IA + PU + EM|Low|PROMO unless user treats as record|
|U25|Educational / product updates|Content/marketing|EM + IA|Low|**`marketing` consent**; unsubscribe; WA marketing template only if opted in|

**6. Consent, account, security, billing**

| # | Notification | Trigger | Channels | Priority | Compliance |
|---|---|---|---|---|---|
|U26|OTP / login code|`/auth/otp/send`|**SMS** (DLT transactional) + WA authentication template|High|Always on; no quiet hours; authentication category|
|U27|New-device / new login|Auth from new device|PU + EM; SMS if high-risk|High|Security — always on|
|U28|Password / security change|Credential change|EM + PU|High|Always on|
|U29|Consent request / change confirmation|New purpose needed or consent toggled|IA + EM|High (request), Normal (confirm)|DPDP notice-before-consent; records to `consent_history`|
|U30|Data export ready / data-deletion done|Export job / erasure request|IA + EM (secure link)|Normal|DPDP data-principal rights|
|U31|Family/shared-vault access granted or expiring|`shares` created / near `expires_on`|IA + PU + EM|Normal|`family_sharing` consent|
|U32|Billing / subscription (ok, failed, renewal, expiry)|Billing events (`billing.py`)|IA + EM; SMS/WA for failure|High (failure), Normal (receipt)|TXN; failure must deliver|

### C.2 — DOCTOR

| # | Notification | Trigger | Channels | Priority | Notes |
|---|---|---|---|---|---|
|D1|**Critical value on a panel patient**|Ingest flags critical for a linked patient|**PU + SMS + WA**, closed-loop ack, escalate to centre if unacked in N min|**Critical / SAFETY**|The single most important clinic alert. Honors accreditor ~30-min/read-back model. Not built.|
|D2|New patient assigned / linked|Patient links / centre assigns|IA + PU|Normal|Into care-queue|
|D3|Patient confirmed / declined a shared doc|`sharedocs.set_status`|IA + PU|Normal|Closes U8 loop back to sender|
|D4|Finding awaiting sign-off|Insight → `review_state='awaiting'`|IA + PU|High|Queue backlog count; gated by `notify_findings`|
|D5|Lab result back for an ordered test|Result ingested for a panel patient|IA + PU; EM digest|High|Ties ingest to the ordering doctor; gated by `notify_labs`|
|D6|New consult / message from patient|Patient message/consult request|IA + PU; WA opt-in|High|Thread-collapse|
|D7|Appointment booked / cancelled / rescheduled|`appointments` status for this doctor|IA + PU; SMS same-day|High|Gated by `notify_bookings`|
|D8|Care-queue backlog threshold|Awaiting reviews exceed threshold/age|IA + PU; EM daily|Normal|Uses `awaiting_reviews`/`pending_reviews`|
|D9|Co-sign / approval request|Treatment/therapy/supplement needs sign-off (`main.py:2590`)|IA + PU|High|Supervising-clinician flow|
|D10|Prescription / plan acknowledgement by patient|Patient acts on Rx/therapy|IA|Low|Dig|
|D11|Schedule reminder (next consult, prep)|Upcoming consult|IA + PU; SMS 30-min|Normal|—|
|D12|Monthly report awaiting doctor|`plans.list_monthly()` state `awaiting_doctor`|IA + PU|Normal|—|
|D13|Account/security (staff login, credential, biometric-lock)|Auth events|PU + EM|High|Always on|

### C.3 — CENTRE / CLINIC ADMIN

| # | Notification | Trigger | Channels | Priority | Notes |
|---|---|---|---|---|---|
|C1|**Critical-result escalation**|A patient's critical value unacknowledged by assigned doctor within SLA|PU + SMS + WA to on-call admin|**Critical / SAFETY**|Mandatory escalation path. Not built.|
|C2|New doctor onboarded / credential added|Staff added (`staff.py`, `centre.py`)|IA + EM|Normal|—|
|C3|New patient onboarded|Member added to centre|IA|Low|Dig|
|C4|Operations: test backlog / sample pending|Ordered tests not collected/resulted past threshold|IA + PU; EM digest|High|Centre ops core|
|C5|**TAT breach** (turnaround-time)|Result not delivered within target TAT|IA + PU; EM|High|Needs a TAT field on orders (not modeled yet)|
|C6|Appointment / booking activity & no-shows|`centre.py` bookings; cancellations|IA + PU|Normal|Gated by `notify_bookings`/`notify_cancellations`|
|C7|Billing / revenue (received, outstanding, credits low)|Billing + `subscriptions.credits_used` near total|IA + EM; SMS for large outstanding|High (outstanding), Normal (revenue)|Gated by `notify_outstanding`|
|C8|Outcomes / report-ready (centre monthly/outcomes)|Period report generated|IA + EM|Normal|—|
|C9|Staff activity / productivity|Sign-offs, consult volume, queue SLA|IA + EM weekly|Low|—|
|C10|Integration / device health|Device/push source silent, webhook failures (`webhook_log.status < 0`), ingest errors|IA + PU; EM|High|Reuse inert `webhook_log`|
|C11|**Compliance / consent / audit**|Consent revoked, DPDP erasure request, unusual `access_log` access, audit export|IA + EM|High|DPDP SDF duties; ties to `consents`/`access_log`|
|C12|Account/security (admin login, role change, API key created/revoked)|Auth + `interop.api_keys` events|PU + EM|High|Always on|

---

## PART D — Inbound report/result RECEIVING flows (what triggers the notifications)

**Principle: ingest → normalize → persist → auto-flag → notify**, with the notify tier decided by the auto-flag. Today only the PDF path exists and it stops at persist (no flag tier, no delivery).

### D.1 Source channels and how each should work
1. **PDF upload (built).** `/labs/parse` / `/labs/parse_b64` → `labparse.parse_pdf` → user confirms markers → `/labs/save` → `regenerate_insights`. **Add:** run auto-flag (D.2) on save, then emit U1/U3/U4 and (for panel patients) D5/D1.
2. **Email ingestion (build).** Per-user ingest address (e.g. `reports+<token>@in.telomy.health`) and/or a shared clinic inbox. An inbound-email provider (Mailgun/SES/Postmark inbound route → webhook) POSTs the parsed message to a new `POST /ingest/email`:
   - Verify sender against allow-list / SPF-DKIM pass; reject/queue-for-review otherwise (never auto-trust an attachment from an unknown sender — DPDP + injection safety).
   - Walk MIME parts: **PDF** → `labparse`; **CSV** → CSV parser (D.3); **EML attachment** (forwarded lab email) → parse the nested `message/rfc822`, recurse into its attachments; **HL7/FHIR** payloads → D.4.
   - On success → create report → auto-flag → **U1** (+U3/U4). On parse failure → notify "we received a report but couldn't read it — tap to upload the PDF."
3. **EML file / forwarded email (build).** Same parser as the email-part walker, uploaded as a file via `/documents/parse` extended to sniff `message_from_bytes`. For "patient forwards the lab's email."
4. **CSV (build).** Columns → markers map (test name, value, unit, ref range, date). For bulk/historical import and some lab portals. Same auto-flag + U1.
5. **HL7 v2 / FHIR R4 inbound (build).** Telomy already **exports** FHIR; add an **inbound** `POST /interop/fhir` (and an HL7 ORU^R01 adapter) accepting `DiagnosticReport`/`Observation` from partner labs/EHRs, authenticated by existing scoped **API keys** (`interop.verify_key`). Map Observations → markers, persist, auto-flag, notify. The clean B2B lab-integration path.
6. **Device APIs (built, keep distinct).** `/whoop/push`, `/cal/ingest`, `/nightscout/*`, `/vitals/ingest`, Apple Health. **Device telemetry, not clinical reports** — they feed U18–U21 and the score (U5), **not** U1/U4. Keep the critical-value tier scoped to lab markers, not raw wearable samples (a transient SpO2 dip is not a panic value).
7. **Manual upload / in-clinic entry (built partial).** Doctor/centre entering results directly → same persist + flag + notify.

### D.2 Critical-value auto-flagging on ingest (new, patient-safety)
A deterministic flag step that runs on **every** report-ingest path before notifying:
- Compare each marker to (a) its reference range and (b) a **critical/panic threshold table** (new, keyed by `marker_id`: K⁺, Na⁺, glucose, Hb, platelets, WBC, creatinine, troponin, calcium, INR). Extend the status vocabulary (`optimal/in_range/out_of_range/variant/detected`) with **`critical`**.
- Output tier: `critical` → U4 + D1 (+C1 escalation); `out_of_range` → U3; otherwise → U1 only.
- Record the flag with provenance (which rule, which threshold, source report) for audit (DPDP) and the closed-loop acknowledgement log. Reuse the inert `interop.fire('lab.result', …)` here to also notify subscribed external EHRs.
- **Safety copy rule:** the **patient** notification never states the dangerous number on push/SMS; it says "an important result needs attention, open Telomy." The **doctor** alert carries the clinical value.

### D.3 "Receiving a report by email/EML/CSV" — concrete spec
- **Addressing:** per-user `reports+<token>@in.telomy.health` (token → the user's per-user DB via `db.set_db`); a centre shared inbox routes by patient-id token or staff triage.
- **Security:** require SPF/DKIM pass; allow-list known lab domains for auto-ingest; everything else lands in a **review queue** (centre C-level) rather than auto-committing. Treat all attachments as untrusted (sandbox parse, size caps like the existing `MAX_NDJSON` guard on `/whoop/push`).
- **Parse:** MIME walk → dispatch by type → `labparse`/CSV-map/FHIR-map → candidate markers.
- **Confirm vs auto:** for patient self-forwarded reports, mirror today's "review extracted markers, then save" step; for API/FHIR partner feeds, auto-commit.
- **Notify:** success → U1 (+U3/U4); for an ordered test → D5 to the ordering doctor; failure → a "couldn't read this report" nudge with manual-upload fallback. Dedup by (source, collection date, panel) so a report arriving by both email and portal doesn't double-notify.

---

## PART E — Channels & delivery architecture + build roadmap

### E.1 Target architecture (fits a single-worker 512MB–1GB box)
No queue/worker, fragile box → do **not** add Celery/Redis. Instead:
1. **Notification store (new).** Replace compute-on-read with a real table:
   `notifications(id, user_scope, role, kind, category, priority, title, body, route, data_json, created_at, read_at, dedup_key, channels_json, delivered_json, ack_at)`. Keep the current `features.notifications()` builders, but have them **write rows** (idempotent on `dedup_key`) instead of recomputing; `/notifications` then just reads. `notif_read` migrates into `read_at`.
2. **Generation = cron, not daemon.** A lightweight `cron` job (how backups/keepalive already run) every few minutes scans for new triggers and inserts notification rows + enqueues channel sends into a **SQLite-backed outbox table** (`notif_outbox`). Mirrors the mobile outbox pattern; survives restarts.
3. **Delivery = thin provider calls, rate-limited.** A second cron drains `notif_outbox`, calling provider HTTP APIs with short timeouts (like `interop.fire`'s 5s urllib pattern), marking `delivered_json` per channel, retrying with backoff, dropping nothing on 5xx. No persistent connections.
4. **Critical path is synchronous + escalation.** U4/D1/C1 do **not** wait for cron — fire inline on ingest, open a closed-loop ack record; a cron escalation sweep promotes unacked critical alerts (doctor → centre) per SLA.

### E.2 Channel adapters to add (mapped to Part A gaps)
- **In-app (have):** add stored rows, badge counts, grouping, per-category read-state.
- **Push — APNs/FCM via `expo-notifications` (build).** Add the package to `mobile`, register device tokens (`POST /devices/push-token` → `push_tokens(user_scope, token, platform)`), send via **Expo Push API** (single HTTPS endpoint, no SDK on the box — cheapest for the micro). Local scheduled notifications for med/dose reminders (U14) to offload the server.
- **Email (build).** Transactional provider (Amazon SES or Postmark); SPF/DKIM/DMARC on `telomy.health`; templates for U1/U24/U30/U32 and the **EML/CSV send+receive** (SES/Mailgun **inbound** route → `/ingest/email`). Separate marketing subdomain/stream for U25.
- **SMS (build).** India **DLT-registered** transactional route via an Indian BSP/aggregator (MSG91/Gupshup/Kaleyra). Register entity + header + **content templates** for OTP (U26), appointment reminders (U12), critical "open the app" (U4), billing failure (U32). Transactional category → DND-exempt, 24×7.
- **WhatsApp (build).** Approved **WhatsApp Business via a BSP** (Gupshup/Meta Cloud API). Pre-approved **utility templates** (report-ready, appointment reminder/confirm, retest-due), an **authentication template** (OTP), and **marketing templates** only behind the `marketing` consent. Capture explicit WA opt-in; use the 24h service window for free-form consult replies. Keep template content non-promotional to avoid reclassification/billing.

### E.3 Preferences & consent model (build)
- New `notification_prefs(user_scope, category, channel, enabled, quiet_start, quiet_end, tz)` — default IST, quiet 21:00–09:00 for Normal/Low, **none** for Critical/OTP/security.
- Tie to DPDP: extend `PURPOSES` with explicit **`whatsapp_messaging`**, keep **`marketing`** separate; notice-before-consent at opt-in; honor withdrawal (as easy to revoke as grant) and the existing 24h-deletion promise. Transactional/safety classes ride the **vital-interest / legitimate-use** basis and are not user-disableable — document this in the notice.
- Dedup (`dedup_key`), batching (morning digest U22 absorbs U5/U6/U20/U23), and per-channel delivery receipts all live in the store.

### E.4 Prioritized build roadmap (fragile-box-aware)

**Phase 0 — storage & safety foundation (do first)**
1. Notification store + outbox tables; migrate `features.notifications()` to write/read; migrate `notif_read`→`read_at`. (Low risk, unblocks everything.)
2. **Critical-value threshold table + auto-flag on ingest (D.2)** and the `critical` status. Patient-safety; must precede any delivery so U4/D1 are correct.
3. Device push: token registration + Expo Push adapter. Highest-leverage channel, no DLT/WhatsApp approval latency.

**Phase 1 — the must-deliver transactional channels**
4. SMS via DLT-registered BSP: **OTP (replace the `000000` stub), appointment reminders, critical "open app," billing failure.**
5. Real appointment confirm/reminder pipeline (closes the fake `main.py:4092` "by SMS").
6. Email transactional + SPF/DKIM/DMARC: result-ready with PDF, data export, security, receipts.
7. Closed-loop **critical alert → doctor → centre escalation** (D1/C1) with acknowledgement log.

**Phase 2 — India primary channel + inbound reports**
8. WhatsApp Business via BSP with approved utility/auth templates + opt-in capture.
9. **Inbound email/EML/CSV ingest** (`/ingest/email`, per-user address, MIME walk) → auto-flag → U1/U3/U4/D5.
10. Preferences + quiet-hours model; morning-digest batching (U22).

**Phase 3 — integrations, engagement, ops**
11. Inbound **FHIR/HL7** (`POST /interop/fhir`) via existing API keys; **activate `interop.fire()`** so `lab.result/note.signed/booking.created` actually emit (external EHR + C10 integration-health alerts).
12. Centre ops alerts: TAT field + breach (C5), backlog (C4), compliance/audit (C11).
13. Engagement/marketing (U24/U25) behind `marketing` consent; streaks/goals.

### E.5 Open questions / flagged risks
- **Regulatory, verify before build:** exact CAP/Joint-Commission critical-value timeframe & read-back wording; DPDP Rule-4 effective date (~13 Nov 2026) and whether health data triggers SDF status at Telomy's scale; TRAI header-suffix scheme; WhatsApp 24h-window mechanics and current template-review SLAs. All cited below are secondary sources.
- **Patient-safety caveat:** critical-value alerting is a clinical-safety feature — Telomy is positioned as *wellness* ("not a diagnosis"). Decide deliberately whether Telomy **asserts** criticality (clinical liability, needs licensed-clinician loop) or **routes to a clinician** without asserting. Recommendation: the latter for patient-facing copy, the former only on the doctor/centre safety path where a licensed caregiver is in the loop.
- **Box capacity:** if critical synchronous sends + cron digests strain the 512MB instance under load (the known wedging failure mode), move the delivery cron to a tiny separate process or a managed function; keep the FastAPI worker doing only inline critical sends.
- **Threshold ownership:** the critical/panic threshold table needs clinical sign-off (age/sex-specific, India reference ranges) — not an engineering decision.

---

### Sources (Part B — secondary, verify against primary)
- WhatsApp template categories & window: linkmobility.com, sinch.com, help.meritto.com.
- TRAI/DLT SMS: telerivet.com, developer.exotel.com, messagecentral.com, moengage.com.
- DPDP Act/Rules & health data: ey.com, amlegals.com, ksandk.com, ca.hoganlovells.com.
- Critical-value reporting: casrai.org, captodayonline.com, academic.oup.com/labmed.
- Consumer/India apps: dtcetc.com, medicalnewstoday.us, similarweb.com / retailstore.1mg.com / indiacustomercare.com (Apollo 24|7, Tata 1mg — no official notification spec found).
