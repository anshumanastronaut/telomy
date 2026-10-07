# API reference

Generated from the FastAPI OpenAPI schema by `scripts/gen_docs.py` — do not edit by hand.
Interactive docs: run the backend and open `http://127.0.0.1:8787/docs`. 171 operations.

## /accounts

| Method | Path | Summary |
|---|---|---|
| GET | `/accounts` | Accounts |

## /action-plan

| Method | Path | Summary |
|---|---|---|
| GET | `/action-plan` | Action Plan |

## /activities

| Method | Path | Summary |
|---|---|---|
| GET | `/activities` | Activities List |
| POST | `/activities` | Activities Create |
| GET | `/activities/{tid}` | Activities Detail |
| POST | `/activities/{tid}/sessions` | Activities Log |

## /admin

| Method | Path | Summary |
|---|---|---|
| POST | `/admin/reset` | Reset |

## /appointments

| Method | Path | Summary |
|---|---|---|
| GET | `/appointments` | Appointments |
| POST | `/appointments` | Book |
| POST | `/appointments/{aid}/cancel` | Cancel |

## /auth

| Method | Path | Summary |
|---|---|---|
| POST | `/auth/otp/send` | Otp Send |
| POST | `/auth/otp/verify` | Otp Verify |

## /brief

| Method | Path | Summary |
|---|---|---|
| GET | `/brief` | Brief List |
| GET | `/brief/{specialty}.json` | Brief Json |
| GET | `/brief/{specialty}.pdf` | Brief Pdf |

## /calculators

| Method | Path | Summary |
|---|---|---|
| GET | `/calculators` | Calculators |

## /care

| Method | Path | Summary |
|---|---|---|
| GET | `/care/queue` | Care Queue |

## /categories

| Method | Path | Summary |
|---|---|---|
| GET | `/categories` | Categories |
| GET | `/categories/{name}` | Category |

## /centre

| Method | Path | Summary |
|---|---|---|
| GET | `/centre/bookings` | Centre Bookings |
| POST | `/centre/bookings` | Centre Book |
| POST | `/centre/bookings/{bid}/status` | Centre Booking Status |
| GET | `/centre/dashboard` | Centre Dashboard |
| GET | `/centre/devices` | Centre Devices |
| POST | `/centre/devices/{device_id}/key` | Device Key |
| GET | `/centre/devices/{device_id}/telemetry` | Device Recent |
| GET | `/centre/floor` | Centre Floor |
| GET | `/centre/members` | Centre Members |
| GET | `/centre/research/phenotypes` | Centre Phenotypes |
| GET | `/centre/services` | Centre Services |
| GET | `/centre/services/{sid}/outcomes` | Centre Service Outcomes |
| GET | `/centre/therapy-outcomes` | Centre Therapy Outcomes |

## /clinician-notes

| Method | Path | Summary |
|---|---|---|
| GET | `/clinician-notes` | Clinician Notes |

## /clinicians

| Method | Path | Summary |
|---|---|---|
| GET | `/clinicians` | Clinicians |

## /completeness

| Method | Path | Summary |
|---|---|---|
| GET | `/completeness` | Completeness |

## /consents

| Method | Path | Summary |
|---|---|---|
| GET | `/consents` | Consents |
| GET | `/consents/history` | Consent History |
| POST | `/consents/{purpose}` | Set Consent |

## /consults

| Method | Path | Summary |
|---|---|---|
| GET | `/consults` | Consult List |
| POST | `/consults` | Consult |
| POST | `/consults/{cid}/complete` | Consult Done |

## /dashboard

| Method | Path | Summary |
|---|---|---|
| GET | `/dashboard` | Dashboard |

## /devices

| Method | Path | Summary |
|---|---|---|
| GET | `/devices/channels` | Device Channels |
| POST | `/devices/{device_id}/telemetry` | Device Telemetry |

## /doctor

| Method | Path | Summary |
|---|---|---|
| GET | `/doctor/patients` | Doctor Patients |
| GET | `/doctor/patients/{pid}` | Doctor Patient |
| POST | `/doctor/patients/{pid}/notes` | Add Note |
| GET | `/doctor/patients/{pid}/reports` | Doctor Patient Reports |
| GET | `/doctor/patients/{pid}/summary` | Doctor Patient Summary |
| GET | `/doctor/today` | Doctor Today |
| GET | `/doctor/work` | Doctor Work |

## /documents

| Method | Path | Summary |
|---|---|---|
| GET | `/documents` | Documents |
| POST | `/documents/parse` | Doc Parse |

## /domains

| Method | Path | Summary |
|---|---|---|
| GET | `/domains/{key}` | Domain |

## /environment

| Method | Path | Summary |
|---|---|---|
| GET | `/environment` | Environment |
| GET | `/environment/compare` | Environment Compare |

## /events

| Method | Path | Summary |
|---|---|---|
| POST | `/events` | Add Event |
| GET | `/events` | Events |
| DELETE | `/events/{eid}` | Delete Event |

## /evidence

| Method | Path | Summary |
|---|---|---|
| GET | `/evidence/{kind}/{key}` | Evidence For |

## /health

| Method | Path | Summary |
|---|---|---|
| GET | `/health` | Health |

## /home

| Method | Path | Summary |
|---|---|---|
| GET | `/home` | Home |

## /imaging

| Method | Path | Summary |
|---|---|---|
| GET | `/imaging` | Imaging |

## /insights

| Method | Path | Summary |
|---|---|---|
| GET | `/insights` | Insights |
| GET | `/insights/{iid}` | Insight |
| POST | `/insights/{iid}/dismiss` | Dismiss |
| POST | `/insights/{iid}/review` | Review |

## /labs

| Method | Path | Summary |
|---|---|---|
| POST | `/labs/parse` | Labs Parse |
| POST | `/labs/save` | Labs Save |

## /longevity

| Method | Path | Summary |
|---|---|---|
| GET | `/longevity` | Longevity |

## /meals

| Method | Path | Summary |
|---|---|---|
| GET | `/meals` | Meals |
| POST | `/meals/analyze` | Meal Analyze |
| DELETE | `/meals/{mid}` | Delete Meal |

## /meds

| Method | Path | Summary |
|---|---|---|
| GET | `/meds` | Meds |
| POST | `/meds` | Add Med |
| POST | `/meds/{mid}/stop` | Stop Med |
| POST | `/meds/{mid}/taken` | Took |

## /memories

| Method | Path | Summary |
|---|---|---|
| GET | `/memories` | Memories |
| DELETE | `/memories/{mid}` | Forget |

## /menu

| Method | Path | Summary |
|---|---|---|
| GET | `/menu` | Menu |
| POST | `/menu/swap` | Menu Swap |

## /monthly-reports

| Method | Path | Summary |
|---|---|---|
| GET | `/monthly-reports` | Monthly Reports |
| GET | `/monthly-reports/{period}` | Monthly Get |
| POST | `/monthly-reports/{period}/generate` | Monthly Generate |
| POST | `/monthly-reports/{period}/sign` | Monthly Sign |

## /notifications

| Method | Path | Summary |
|---|---|---|
| GET | `/notifications` | Notifications |
| POST | `/notifications/read` | Notif Read |

## /nudges

| Method | Path | Summary |
|---|---|---|
| GET | `/nudges` | Nudges |

## /nutrition

| Method | Path | Summary |
|---|---|---|
| GET | `/nutrition/trends` | Nutrition Trends |

## /physio

| Method | Path | Summary |
|---|---|---|
| GET | `/physio/validation` | Physio Validation |

## /pins

| Method | Path | Summary |
|---|---|---|
| GET | `/pins` | Get Pins |
| PUT | `/pins` | Set Pins |

## /plans

| Method | Path | Summary |
|---|---|---|
| GET | `/plans` | Get Plans |

## /predict

| Method | Path | Summary |
|---|---|---|
| GET | `/predict` | Predict Me |
| GET | `/predict/patient/{pid}` | Predict Patient |
| POST | `/predict/what-if` | What If |

## /profile

| Method | Path | Summary |
|---|---|---|
| GET | `/profile` | Get Profile |
| PUT | `/profile` | Put Profile |

## /protocols

| Method | Path | Summary |
|---|---|---|
| GET | `/protocols` | Protocols |
| POST | `/protocols/{pid}/activate` | Activate |

## /reports

| Method | Path | Summary |
|---|---|---|
| GET | `/reports` | Reports |
| GET | `/reports/{rid}` | Report |
| DELETE | `/reports/{rid}` | Delete Report |
| POST | `/reports/{rid}/review` | Report Review |
| GET | `/reports/{rid}/summary` | Report Summary |

## /research

| Method | Path | Summary |
|---|---|---|
| GET | `/research` | Research |

## /risks

| Method | Path | Summary |
|---|---|---|
| GET | `/risks` | Risks |

## /routine

| Method | Path | Summary |
|---|---|---|
| GET | `/routine` | Routine Get |
| POST | `/routine` | Routine Save |
| POST | `/routine/mark` | Routine Mark |
| POST | `/routine/parse` | Routine Parse |
| GET | `/routine/today` | Routine Today |

## /rx

| Method | Path | Summary |
|---|---|---|
| GET | `/rx/goals` | Rx Goals |
| POST | `/rx/plans` | Rx Submit |
| GET | `/rx/plans` | Rx Plans |
| GET | `/rx/plans/{plan_id}` | Rx Plan |
| POST | `/rx/plans/{plan_id}/decide` | Rx Decide |
| POST | `/rx/plans/{plan_id}/order` | Rx Order |
| GET | `/rx/plans/{plan_id}/prescription.pdf` | Rx Pdf |
| GET | `/rx/recommend` | Rx Recommend |
| GET | `/rx/tracking` | Rx Tracking |

## /sessions

| Method | Path | Summary |
|---|---|---|
| GET | `/sessions` | Sessions |
| POST | `/sessions` | Add Session |
| GET | `/sessions/stats` | Session Stats |

## /shares

| Method | Path | Summary |
|---|---|---|
| GET | `/shares` | Shares |
| POST | `/shares` | Add Share |
| POST | `/shares/{sid}/revoke` | Revoke |

## /signals

| Method | Path | Summary |
|---|---|---|
| GET | `/signals` | Signals |
| POST | `/signals` | Add Signal |
| GET | `/signals/{metric}` | Signal |

## /sinc

| Method | Path | Summary |
|---|---|---|
| POST | `/sinc/ask` | Ask |
| GET | `/sinc/chats` | Chats |
| GET | `/sinc/chats/{cid}` | Chat |
| POST | `/sinc/draft-for-clinician` | Draft |

## /studies

| Method | Path | Summary |
|---|---|---|
| GET | `/studies` | Studies |
| POST | `/studies` | New Study |

## /subscription

| Method | Path | Summary |
|---|---|---|
| POST | `/subscription` | Subscribe |

## /tests

| Method | Path | Summary |
|---|---|---|
| GET | `/tests` | Tests Catalogue |
| POST | `/tests/book` | Tests Book |
| GET | `/tests/recommended` | Tests Recommended |

## /therapy

| Method | Path | Summary |
|---|---|---|
| GET | `/therapy` | Therapy Home |
| GET | `/therapy/catalogue` | Therapy Catalogue |
| GET | `/therapy/catalogue/{mid}` | Therapy Modality |
| GET | `/therapy/goals` | Therapy Goals |
| GET | `/therapy/hsai` | Therapy Hsai |
| POST | `/therapy/plans` | Therapy Plan Submit |
| GET | `/therapy/plans` | Therapy Plans |
| POST | `/therapy/plans/preview` | Therapy Plan Preview |
| POST | `/therapy/plans/{plan_id}/decide` | Therapy Plan Decide |
| GET | `/therapy/safety` | Therapy Safety |
| POST | `/therapy/sessions` | Therapy Start |
| GET | `/therapy/sessions/{sid}` | Therapy Session |
| POST | `/therapy/sessions/{sid}/finish` | Therapy Finish |
| POST | `/therapy/sessions/{sid}/samples` | Therapy Ingest |
| GET | `/therapy/working` | Therapy Working |

## /today

| Method | Path | Summary |
|---|---|---|
| GET | `/today` | Today List |
| POST | `/today` | Check |

## /twin

| Method | Path | Summary |
|---|---|---|
| GET | `/twin` | Twin Overview |
| GET | `/twin/day` | Twin Day |
| GET | `/twin/mirror` | Twin Mirror |
| POST | `/twin/simulate` | Twin Simulate |

## /vault

| Method | Path | Summary |
|---|---|---|
| GET | `/vault/concerns` | Concerns |
| GET | `/vault/derived` | Derived Markers |
| GET | `/vault/marker/{mid}` | Marker |
| GET | `/vault/panel/{panel}` | Panel |
| GET | `/vault/panels` | Panels |
| GET | `/vault/timeline` | Timeline |

## /voice

| Method | Path | Summary |
|---|---|---|
| POST | `/voice/audio` | Voice Audio |
| POST | `/voice/command` | Voice Command |
| GET | `/voice/design` | Voice Design |
| GET | `/voice/stress` | Voice Stress |
