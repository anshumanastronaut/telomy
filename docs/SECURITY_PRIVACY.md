# Security & privacy

Telomy processes health data — sensitive personal data under India's **DPDP Act 2023 / Rules 2025** (penalties up to ₹250 crore).
Telomy acts as Data Fiduciary; partner clinics are joint fiduciaries for their patients.

## Hard rules for this repository
1. **No real personal or health data** — ever. Seed data, test PDFs and screenshots must be fictitious and marked TEST DATA.
   `.gitignore` excludes competitor-teardown screenshots (`research/ultrahuman/shots/`), databases (`*.db`) and QA captures.
2. **No secrets** — API keys, device keys, signing certificates, `.env` files. Use `backend/.env` (git-ignored) and `.env.example` for names only.
   If a secret is committed: rotate it immediately, then remove it from history.
3. **Licensed data stays local** — `backend/data/ddinter/` (CC BY-NC-SA, non-commercial) is git-ignored and must be replaced by a commercially
   licensed interaction source before launch.
4. Personal routines, voice samples and real user text typed during testing live only in local databases.

## Product controls (implemented)
- Per-purpose consent with history (`/consents`): wearable sync, lab analysis, Sinc AI, clinician sharing, research, family sharing, cycle, marketing;
  voice logging and voice-stress analysis are separate purposes.
- Scoped, time-boxed, revocable sharing with an access log (`/shares`).
- Voice: raw audio is never stored — only text and numeric acoustic features.
- Device telemetry authenticated per device (SHA-256-hashed keys, shown once); unknown channels discarded.
- Clinician sign-off required for medical-adjacent outputs; deterministic safety screens.

## Required before production
- Authentication (OTP + role claims) and per-patient authorisation on every endpoint (prototype trusts the role chosen in the app).
- TLS everywhere; encryption at rest (AES-256); India-region hosting; key management (KMS).
- Immutable audit log export; 72-hour breach workflow; data-subject rights portal (access, correction, erasure within DPDP timelines).
- DPIA, DPO appointment, vendor DPAs (LLM provider: no training on data; India/region options), penetration test.
- Rate limiting, input size limits on uploads, malware scanning of PDFs.

## Reporting
Report vulnerabilities privately to the maintainers (do not open a public issue).
