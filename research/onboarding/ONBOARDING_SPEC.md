# Onboarding / sign-up data capture — research + spec (user · doctor · clinic)

Goal: capture the maximum useful data at first sign-up so the engines (Sinc, risk, organ clocks, macros,
circadian) and the care graph are rich from day one — without a wall-of-form. **Design principles from the
research:** chunk into short steps; mark required vs optional; use conditional logic (only ask what's relevant);
mobile-first; validate required fields at entry; let people skip and finish later; voice-assisted where typing is
heavy (routine, history). India context: NMC (doctors), HFR/HPR/ABHA under ABDM (facilities + practitioners).

---
## 1) MEMBER / USER onboarding

Progressive steps (each skippable except Identity); a completion ring rewards finishing.

**Step 1 — Identity & contact** (required)
- Full name · date of birth (→ age) · **sex at birth** (male/female/intersex — drives reference ranges & clocks) ·
  **gender identity** (optional, separate from sex) · phone (+ OTP) · email · city/pincode · preferred language ·
  profile **photo** (optional; used for the Twin avatar & face-based vitals later) · emergency contact (name, phone, relation)

**Step 2 — Body** (anthropometrics + phenotype)
- Height (cm) · weight (kg) → BMI · waist (cm, optional) · **skin type (Fitzpatrick I–VI)** self-pick with a
  burn/tan descriptor (I burns-never-tans … VI never-burns; drives UV/vit-D & dermato logic) · **body type
  (somatotype)** ecto/meso/endo self-pick (Heath-Carter simplified) · blood group (optional)

**Step 3 — Lifestyle & routine**
- **Activity level** — IPAQ-style: sedentary / lightly active / moderately active / very active (maps to PAL &
  calorie basis) · typical workouts (type + days/week) · **daily routine** — wake/sleep times, work pattern
  (desk/shift/field); captured by **typing OR voice** (voice → transcribed → structured) · diet pattern
  (veg/non-veg/vegan/eggetarian; cuisines) · sleep (avg hours, quality) · smoking (never/ex/current + /day) ·
  alcohol (none/occasional/regular + units) · caffeine · stress (1–5) · gut (regularity, bloating, intolerances)

**Step 4 — Medical history**
- Existing **conditions/diagnoses** (searchable, ICD-lite: diabetes, hypertension, thyroid, PCOS, CVD, CKD,
  asthma, etc.) · **surgeries/procedures** (+ year) · **family history** (per condition + relation) · allergies
  (drug/food/environmental + reaction) · pregnancy/menstrual status (if applicable) · vaccinations (optional)

**Step 5 — Medications & supplements**
- **Current medications** (name · dose · frequency · since · prescriber) · **supplements** (name · dose · timing) ·
  adherence. Each becomes a Vault med/supplement and feeds interactions + the macro/longevity engines.

**Step 6 — Reports & data**
- Upload **existing lab reports / imaging / genetics** (PDF/photo → parsed into the Vault) · connect **ABHA** to
  pull records · prior wearable exports (WHOOP/Apple Health/Fitbit/Google).

**Step 7 — Devices**
- Link **Telomy patch / ring**, **WHOOP (via NOOP)**, phone health (iOS Apple Health; Android: *Health Connect —
  to build*). Clear "what each provides" (HR/HRV/ECG/SpO₂/sleep/steps).

**Step 8 — Goals & consent**
- Primary **goals** (longevity, reverse prediabetes, weight, heart, sleep, energy, fertility, strength…) ·
  target timeframe · **consent** (per-purpose: care, research, family sharing — revocable) · plan choice.

---
## 2) DOCTOR onboarding (India / NMC + ABDM HPR)

**Step 1 — Identity** — full name (must match the register) · photo · phone (+OTP) · email · languages · city.
**Step 2 — Credentials & verification** (the trust core)
- **NMC / State Medical Council registration number** + issuing **State Medical Council** + **year** → verify in
  real time against the **Indian Medical Register** (status active/lapsed). · **HPR ID** (ABDM Healthcare
  Professional Registry) if present. · Upload: **council registration certificate**, **degree certificate(s)**,
  government ID.
- **Qualifications** (MBBS, MD/MS, DM/MCh, DNB, diplomas) · **primary specialty** + **sub-specialty** (sub-specialty
  needs its own evidence) · **years of experience**.
**Step 3 — Practice** — current affiliations (clinics/hospitals; link to a centre on the platform) · consultation
modes (video / in-clinic / home visit) · **fees** per mode · availability (days/slots) · consult languages ·
scope (conditions treated) · registration council jurisdiction.
**Step 4 — Payouts & compliance** — bank/UPI for payouts · GST (if applicable) · signature (for Rx & reports) ·
agree to **NMC Telemedicine Practice Guidelines** · data-handling consent.

---
## 3) CLINIC / WELLNESS-CENTRE onboarding (India / Clinical Establishments + ABDM HFR + NABH)

**Step 1 — Organisation** — legal/registered **facility name** (exact) · brand/display name · type (clinic /
polyclinic / hospital / wellness/longevity centre / diagnostic lab) · **ownership** (private / govt / PPP / trust)
· owner/manager name + **Aadhaar-linked mobile** (KYC/OTP).
**Step 2 — Registration & accreditation** — **Clinical Establishments Act** registration no. (+ state authority) ·
**HFR** (Health Facility Registry) ID / register now · **NABH** accreditation (if any) · **CDSCO/PVHO/ASME** for
regulated devices (e.g. HBOT) · **PAN / GST** · drug licence & pharmacy licence (if dispensing) · uploads for each.
**Step 3 — Location & infrastructure** — full address + geo + branches · operating hours · capacity (consult rooms,
beds, ICU, OT if any) · **equipment / machines** (imaging, lab analysers, cryo, HBOT, red-light, PEMF…; each a
bookable resource) · **lab / pharmacy / imaging** on-site flags.
**Step 4 — Services & staff** — **services/modalities** offered (+ price, duration) · **memberships / packages /
plans** (+ price, billing cycle) · **staff** (doctors — link via HPR; therapists, nurses, operators, front desk —
roles) · affiliated doctors.
**Step 5 — Payments & delivery** — **payment gateways** (Razorpay/UPI/cards) + payout bank · tax config · delivery
/ home-service coverage (pincodes) for orders & home care · cancellation/refund policy.
**Step 6 — Branding & go-live** — logo, colours, about, photos · consent to platform terms · publish.

---
## Build order (this spec → code)
1. Member multi-step onboarding (the biggest engine payoff). 2. Doctor credential onboarding + NMC field +
verification stub. 3. Centre onboarding + HFR/CEA fields + services/plans/gateways. 4. Then payment methods +
address book (separate builds). Store everything in `profile`/`staff`/`centres` data JSON so the engines read it
immediately; gate verification (NMC/HFR) as async.

Sources: NexHealth & Knack intake guides; EyeWiki Fitzpatrick scale; Heath-Carter somatotype (topendsports);
IPAQ tiers (PMC); Decentro/Apify NMC Indian Medical Register verification; ABDM HFR SOP + HPR guides.
