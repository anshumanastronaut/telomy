# Data model

Generated from the SQLite schema by `scripts/gen_docs.py`. JSON columns (`data`, `params`, `features`, `trace`…) hold
structured payloads documented in the owning module.

## `access_log` (1 fixture rows)

```sql
CREATE TABLE access_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, who TEXT, what TEXT)
```

## `accounts` (3 fixture rows)

```sql
CREATE TABLE accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, name TEXT, phone TEXT, org TEXT, data TEXT)
```

## `activity_sessions` (20 fixture rows)

```sql
CREATE TABLE activity_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, type_id TEXT, ts TEXT, minutes REAL, values_json TEXT,
  vitals TEXT, notes TEXT, source TEXT)
```

## `activity_types` (2 fixture rows)

```sql
CREATE TABLE activity_types (id TEXT PRIMARY KEY, name TEXT, category TEXT, fields TEXT, scores TEXT, created_at TEXT, created_by TEXT)
```

## `appointments` (1 fixture rows)

```sql
CREATE TABLE appointments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, clinician_id TEXT, ts TEXT, kind TEXT, status TEXT, reason TEXT)
```

## `band_captures` (0 fixture rows)

```sql
CREATE TABLE band_captures (
  id TEXT NOT NULL, user_id INTEGER NOT NULL DEFAULT 1, therapy TEXT, started_at TEXT, duration_s REAL, meta TEXT, bundle TEXT,
  received_at TEXT, PRIMARY KEY (user_id, id))
```

## `band_events` (0 fixture rows)

```sql
CREATE TABLE band_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL DEFAULT 1, type TEXT NOT NULL, start_ts TEXT NOT NULL,
  end_ts TEXT NOT NULL, detail TEXT, source TEXT, UNIQUE (user_id, type, start_ts))
```

## `band_minutes` (0 fixture rows)

```sql
CREATE TABLE band_minutes (
  user_id INTEGER NOT NULL DEFAULT 1, ts TEXT NOT NULL, hr REAL, rmssd REAL, sdnn REAL, beats INTEGER,
  quality TEXT, artefact_pct REAL, source TEXT, PRIMARY KEY (user_id, ts))
```

## `band_recordings` (0 fixture rows)

```sql
CREATE TABLE band_recordings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL DEFAULT 1, start_ts TEXT NOT NULL, duration_s REAL,
  beats INTEGER, mean_hr REAL, rmssd REAL, sdnn REAL, artefact_pct REAL, rr TEXT, source TEXT, sleep TEXT,
  UNIQUE (user_id, start_ts))
```

## `bookings` (4207 fixture rows)

```sql
CREATE TABLE bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, service_id TEXT, ts TEXT, status TEXT, price INTEGER)
```

## `chats` (0 fixture rows)

```sql
CREATE TABLE chats (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, title TEXT)
```

## `checklist` (400 fixture rows)

```sql
CREATE TABLE checklist (day TEXT, item_id TEXT, done INTEGER, PRIMARY KEY (day, item_id))
```

## `clinical_notes` (1 fixture rows)

```sql
CREATE TABLE clinical_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, author TEXT, ts TEXT, text TEXT)
```

## `clinicians` (4 fixture rows)

```sql
CREATE TABLE clinicians (id TEXT PRIMARY KEY, data TEXT)
```

## `consent_history` (4 fixture rows)

```sql
CREATE TABLE consent_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, purpose TEXT, granted INTEGER, ts TEXT)
```

## `consents` (8 fixture rows)

```sql
CREATE TABLE consents (purpose TEXT PRIMARY KEY, granted INTEGER, updated_at TEXT)
```

## `consults` (0 fixture rows)

```sql
CREATE TABLE consults (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, mode TEXT, reason TEXT, requested_at TEXT,
  scheduled_at TEXT, doctor TEXT, status TEXT, price INTEGER, covered INTEGER, notes TEXT)
```

## `device_keys` (0 fixture rows)

```sql
CREATE TABLE device_keys (device_id TEXT PRIMARY KEY, key_hash TEXT, created_at TEXT, last_seen TEXT)
```

## `devices` (28 fixture rows)

```sql
CREATE TABLE devices (id TEXT PRIMARY KEY, modality TEXT, name TEXT, room TEXT, capacity INTEGER, status TEXT,
  last_service TEXT, next_service TEXT, telemetry TEXT)
```

## `documents` (1 fixture rows)

```sql
CREATE TABLE documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, title TEXT, day TEXT, filename TEXT, summary TEXT, data TEXT, created_at TEXT)
```

## `ecg_strips` (0 fixture rows)

```sql
CREATE TABLE ecg_strips (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL DEFAULT 1, ts TEXT NOT NULL, fs REAL NOT NULL,
  duration_s REAL, hr REAL, rmssd REAL, quality TEXT, samples TEXT NOT NULL, note TEXT, source TEXT)
```

## `events` (299 fixture rows)

```sql
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT, label TEXT, severity INTEGER,
  data TEXT, source TEXT DEFAULT 'manual')
```

## `exposure` (0 fixture rows)

```sql
CREATE TABLE exposure (day TEXT, place TEXT, pm25 REAL, pm10 REAL, no2 REAL, o3 REAL, uv_max REAL, temp_mean REAL,
  temp_min REAL, humidity REAL, source TEXT, PRIMARY KEY (day, place))
```

## `imaging` (2 fixture rows)

```sql
CREATE TABLE imaging (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)
```

## `insights` (64 fixture rows)

```sql
CREATE TABLE insights (
  id TEXT PRIMARY KEY, created_at TEXT, kind TEXT, title TEXT, body TEXT, confidence REAL,
  evidence TEXT, receipts TEXT, review_state TEXT, medical INTEGER DEFAULT 0, dismissed INTEGER DEFAULT 0)
```

## `meals` (10 fixture rows)

```sql
CREATE TABLE meals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, name TEXT, analysis TEXT)
```

## `med_doses` (66 fixture rows)

```sql
CREATE TABLE med_doses (id INTEGER PRIMARY KEY AUTOINCREMENT, med_id INTEGER, ts TEXT)
```

## `medications` (3 fixture rows)

```sql
CREATE TABLE medications (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, dose TEXT, frequency TEXT, times TEXT, reason TEXT,
  prescriber TEXT, start_day TEXT, active INTEGER DEFAULT 1, source TEXT)
```

## `memories` (4 fixture rows)

```sql
CREATE TABLE memories (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, fact TEXT, source TEXT)
```

## `messages` (0 fixture rows)

```sql
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, ts TEXT, role TEXT, content TEXT, meta TEXT)
```

## `monthly_reports` (2 fixture rows)

```sql
CREATE TABLE monthly_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT UNIQUE, created_at TEXT,
  state TEXT, data TEXT, doctor TEXT, doctor_note TEXT, signed_at TEXT)
```

## `notif_read` (0 fixture rows)

```sql
CREATE TABLE notif_read (key TEXT PRIMARY KEY)
```

## `patients` (140 fixture rows)

```sql
CREATE TABLE patients (id INTEGER PRIMARY KEY, name TEXT, age REAL, sex TEXT, city TEXT, doctor_id INTEGER,
  member INTEGER DEFAULT 0, plan TEXT, data TEXT, joined TEXT)
```

## `profile` (1 fixture rows)

```sql
CREATE TABLE profile (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL)
```

## `protocols` (4 fixture rows)

```sql
CREATE TABLE protocols (id TEXT PRIMARY KEY, data TEXT, active INTEGER DEFAULT 0)
```

## `report_reviews` (0 fixture rows)

```sql
CREATE TABLE report_reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER, doctor TEXT, ts TEXT,
  action TEXT, note TEXT)
```

## `reports` (24 fixture rows)

```sql
CREATE TABLE reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, panel TEXT, collected_on TEXT, source TEXT,
  filename TEXT, is_test_data INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)
```

## `results` (254 fixture rows)

```sql
CREATE TABLE results (
  id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER REFERENCES reports(id) ON DELETE CASCADE,
  marker_id TEXT, value_num REAL, value_text TEXT, unit TEXT, ref_low REAL, ref_high REAL, ref_text TEXT,
  flag TEXT, status TEXT, note TEXT)
```

## `review_thread` (21 fixture rows)

```sql
CREATE TABLE review_thread (
  id INTEGER PRIMARY KEY AUTOINCREMENT, insight_id TEXT, ts TEXT, author TEXT, action TEXT, note TEXT)
```

## `routine_log` (0 fixture rows)

```sql
CREATE TABLE routine_log (day TEXT, item_key TEXT, status TEXT, PRIMARY KEY (day, item_key))
```

## `routines` (0 fixture rows)

```sql
CREATE TABLE routines (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, text TEXT, items TEXT, metrics TEXT,
  active INTEGER DEFAULT 1)
```

## `rx_orders` (0 fixture rows)

```sql
CREATE TABLE rx_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER, created_at TEXT, items TEXT, total INTEGER,
  status TEXT, channel TEXT)
```

## `rx_plans` (0 fixture rows)

```sql
CREATE TABLE rx_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, goal TEXT, created_at TEXT, state TEXT,
  plan TEXT, doctor TEXT, reg_no TEXT, note TEXT, decided_at TEXT)
```

## `services` (25 fixture rows)

```sql
CREATE TABLE services (id TEXT PRIMARY KEY, name TEXT, minutes INTEGER, price INTEGER, capacity INTEGER, category TEXT, evidence TEXT, targets TEXT)
```

## `sessions_log` (9 fixture rows)

```sql
CREATE TABLE sessions_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT, minutes REAL, data TEXT)
```

## `shares` (1 fixture rows)

```sql
CREATE TABLE shares (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, relation TEXT, scopes TEXT, expires_on TEXT,
  status TEXT, created_at TEXT)
```

## `signals` (1810 fixture rows)

```sql
CREATE TABLE signals (
  day TEXT, metric TEXT, value REAL, source TEXT, PRIMARY KEY (day, metric))
```

## `studies` (1 fixture rows)

```sql
CREATE TABLE studies (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, intervention TEXT, outcome TEXT, design TEXT,
  start_day TEXT, period_days INTEGER, status TEXT, data TEXT)
```

## `subscriptions` (1 fixture rows)

```sql
CREATE TABLE subscriptions (id INTEGER PRIMARY KEY CHECK (id = 1), plan TEXT, billing TEXT, since TEXT, renews TEXT)
```

## `telemetry` (0 fixture rows)

```sql
CREATE TABLE telemetry (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT, ts TEXT, data TEXT)
```

## `therapy_plans` (1 fixture rows)

```sql
CREATE TABLE therapy_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, goal TEXT, created_at TEXT,
  state TEXT, plan TEXT, doctor TEXT, note TEXT, decided_at TEXT)
```

## `therapy_sessions` (2628 fixture rows)

```sql
CREATE TABLE therapy_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, modality TEXT, device_id TEXT,
  booking_id INTEGER, ts TEXT, minutes REAL, params TEXT, features TEXT, trace TEXT, subjective TEXT, adverse TEXT, status TEXT,
  source TEXT)
```

## `voice_samples` (0 fixture rows)

```sql
CREATE TABLE voice_samples (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, language TEXT, text TEXT, features TEXT,
  stress REAL, intents TEXT, source TEXT)
```
