# Patient intake & the 360 summary

Pulls a patient's **real stored data** into the clinic — no retyping — and composes a grounded, clinician-gated
summary that combines labs, vitals, recovery/sleep, habits, reports and risk, with an AI narrative. The same view
is available to the member for their own data.

## How the data is pulled (the intake flow)

The care graph (`tenancy.py`) links a clinical `patients` row to an app user by `user_ref`. That user's live data
lives in their **own per-user SQLite DB** (`data/users/<id>.db`). [`patient_data.py`](../backend/app/patient_data.py)
resolves the link, **temporarily binds** to that DB (authorised because the doctor is assigned to the patient),
reads every domain, and restores the binding:

- `biomarkers(pid)` → latest labs as a flat, **engine-keyed** dict (`ldl`, `apob`, `hba1c`, `crp_mgL`,
  `vitamin_d_25oh`, `trig`, `egfr`, `albumin`, `almi`, `total_testosterone`, …) + `age/sex/weight_kg/height_cm`.
  Falls back to the clinical seed panel for patients with no linked live record. `source` is `live_vault` or `seed`.
- `overview(pid)` → the **360**: identity, risk models (`roles`/`predict`), labs (grouped + dated), vitals
  (7-day trend + **nocturnal SpO₂ min** + resting HR), recovery (today's HRV vs the person's own 7-day baseline),
  habits (activity/steps/smoking/alcohol/BP/statin), reports, and a grounded AI summary.
- `overview_me()` → the identical 360 for the signed-in **member**, read from their own bound Vault.

Research-grounded (digital-twin "patient 360" + sleep-biomarker + clinical-AI literature): longitudinal
**trajectories, not snapshots**; nocturnal SpO₂/HRV are first-class; and because **omission is the dominant AI
error in clinical summaries**, the narrative is a **deterministic grounded composer** — every statement traces to
a value in the record, facts never come from a model, and a clinician reviews and signs. It degrades honestly:
domains with no data show "—"/"not linked", never invented numbers.

## Endpoints
| Route | Who | Returns |
|---|---|---|
| `GET /mgmt/clinic/patients/{pid}/biomarkers` | doctor | intake auto-fill (engine-keyed latest labs) |
| `GET /mgmt/clinic/patients/{pid}/overview` | doctor | the full 360 + AI summary |
| `GET /me/overview` | member | their own 360 + AI summary |

## Using it in the console (Doctor → Longevity Rx)
1. Pick the **Patient**.
2. Click **↓ Pull from record** — the biomarker grid auto-fills from their stored labs, and the **360** renders
   above: AI summary (draft · grounded), recovery/resting-HR/nocturnal-SpO₂/steps, CVD/diabetes/FIB-4, the full
   labs table and reports.
3. Click **Run assessment** — evidence-graded longevity tiers (with FAERS safety chips), the n-of-1 trial
   designer, and the protein/fibre/fat macro fix, all from the pulled values.
4. Record a note and **Validate & record** to sign off (nothing reaches the member until you do).

The same 360 opens from **Patients → 360** for any patient.

## Member side ("as before")
`/me/overview` gives the member the identical combined view of their own data — the existing report/vitals screens
plus the AI summary — so the patient and clinic see the same picture. (Mobile wiring to this endpoint is the next
step; the backend is live.)
