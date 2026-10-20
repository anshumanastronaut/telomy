# Wellness-centre & doctor platform — research + build (2026-10-19)

Two modular, fully-customisable products on the Telomy backend: a **wellness-centre management** platform and a
**doctor/clinic** platform. Built so a non-engineer configures a centre or clinic end to end — add therapies, modules,
users, fields, plans, templates — as **data, not code**.

## Research (what world-class software does)
- **Wellness/gym/spa (Zenoti, Mindbody, Vagaro, WellnessLiving):** multi-location; scheduling with rooms/resources and
  multi-room/couples booking; memberships with entitlements, packages/credits, recurring billing, freezes, renewals;
  staff roles & commissions; CRM/retention; billing with dunning; inventory; check-in; outcomes; reporting. Zenoti is
  the multi-location/wellness leader; Mindbody for marketplace leads. (zenoti.com, patientnow.com.)
- **Doctor/EHR (DrChrono, Jane, ModMed, Athena, Epic):** clinical charting with **customisable note templates** (SOAP
  and bespoke), per-doctor documentation styles, **custom form builder**, e-prescribing, scheduling, patient roster,
  labs review, telehealth, care plans, task inbox, billing/coding. DrChrono/Jane lead on configurability for small
  practices. (getfreed.ai, deepcura.com, techradar.)

The common thread in the best tools — and the explicit ask here — is **configurability**: a centre or doctor shapes
the catalog, the forms and the modules to their own taste without engineering.

## What's built (backend, deployed, 170 tests)
**Configuration engine — `platform.py` (`/mgmt/*`)** — the modular/customisable core:
- `org_config`: which **modules** are on (scheduling, memberships, therapies, clinical_notes, eprescribing, telehealth,
  inventory, billing, crm, reports, wearables, labs) + branding. Centres toggle modules; screens follow.
- `catalog`: every configurable **type** as data — service/therapy types, membership plans & packages, rooms/resources,
  staff roles, clinical note templates, appointment types, custom modules. Add a therapy or a plan in one row.
- `custom_fields`: extra fields on any entity (member, patient, service, therapy, booking, clinical note) with type,
  options, section, order; `form_schema()` renders the form dynamically; `validate_values()` enforces them.

**Centre operations — `centre.py` (`/mgmt/centre/*`)**: members (with custom fields), memberships (plans → credits,
invoice on enrol, freeze), **resource-aware scheduling** (double-book of a room/staff refused), check-in (spends a
membership credit or raises an invoice), invoices & payments, a live dashboard (active members, today's bookings,
revenue, outstanding).

**Clinic operations — `clinic.py` (`/mgmt/clinic/*`)**: clinical **notes from templates** (+ custom fields, sign),
a **task inbox**, the doctor inbox (roster + tasks + care-review queue + templates). A default SOAP template is seeded.

Everything is connected to Telomy: a member links to a `patient_id` (labs, wearables, trackers, bioage), therapies map
to the existing therapy engine, prescriptions to `rx.py`, the care queue to engine insights.

## What's next (the apps)
The backend platform is complete and tested. The two front-end apps (a centre console and a doctor app) are the next
phase — they are thin clients over `/mgmt/*`: the config screen reads `/mgmt/overview` + `/mgmt/form` to render
everything dynamically, so adding a therapy/module/field in the catalog immediately appears in the UI with no app
change. That dynamic-form approach is what makes them "fully customisable, easy and intuitive".
