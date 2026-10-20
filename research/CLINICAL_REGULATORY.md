# Telomy — Clinical Validation & Regulatory Brief

**Date:** 2026-10-21 · Owner: `clinical-regulatory` agent. How each Telomy capability is classified,
what validation it needs, and the India/US regulatory + data-protection path. Written to be
diligence-ready and to keep us honest about claims.

## 1. Wellness vs Software-as-a-Medical-Device (SaMD)
Classification follows the **claim**, not the tech. We deliberately split the product:

| Capability | Posture | Why |
|---|---|---|
| Aging clocks (blood/muscle), PhenoAge, nutrition, meal-photo, fitness | **General wellness** | informational "biological age / nutrition" claims; low risk; not diagnosis |
| Disease-risk screen, 10-yr mortality risk | **SaMD (likely Class B/C)** | drives health decisions; must be validated + clinician-reviewed |
| Fall detection / emergency escalation | **SaMD / safety function** | acts on an acute event; false-negative/positive harm |
| Telomy-LLX narration | **Clinical Decision Support** | explains tool outputs to a clinician who can independently review the basis |
| Genome annotation | **informational + clinician referral** | PGx/ACMG flags → genetic counsellor, not autonomous |

**Design choice that lowers regulatory burden:** everything is **decision-support, clinician-in-the-
loop**, shows the *markers behind each number* (so a clinician can independently review the basis), makes
**no diagnosis or lifespan claim**, and keeps prescriptions behind a signed Rx. In the US this aims at the
**21st Century Cures CDS carve-out** (non-device when the clinician isn't relying primarily on the
software and can review the inputs). In India it keeps the wellness features outside device rules and
scopes only the risk/safety functions as SaMD.

## 2. India (primary market)
- **CDSCO — Medical Device Rules 2017**: SaMD is regulated; risk classes A/B/C/D. The risk-prediction and
  fall/emergency functions are plausibly **Class B/C** → require registration, a quality system
  (ISO 13485), and clinical evidence. Wellness features stay out of scope if claims stay wellness.
- **DPDP Act 2023** (data protection): Telomy is a Data Fiduciary — needs explicit consent, purpose
  limitation, breach reporting, and data-principal rights. **On-device processing (Telomy-LLX, local
  storage) is a direct compliance asset** — minimizes data transfer and cross-border exposure.
- **Clinical Establishments Act / telemedicine**: doctor consults follow the 2020 Telemedicine Practice
  Guidelines; prescriptions by registered practitioners only.
- **ICMR** ethics approval for any prospective study; **DGFT/legal** for any device import.

## 3. US / EU (expansion)
- **US FDA**: pursue the CDS non-device path for narration/risk-display; if we make device-level
  diagnostic claims, that triggers 510(k)/De Novo. Fall detection ≈ general-wellness unless marketed for
  a medical condition. **HIPAA** if handling US PHI.
- **EU**: MDR for any medical claim; **GDPR** for data (on-device helps). CE marking if sold as a device.

## 4. Validation roadmap (what converts demos into evidence)
1. **Analytical validation — DONE.** Held-out + 5-fold metrics with provenance for every model
   (clocks MAE, disease AUC/PR-AUC, mortality AUC) — reproducible from `research/`.
2. **Calibration — IN PROGRESS.** Rigor pass (`diseasemodel/eval_rigor.py`) showed strong *ranking*
   (guess-the-disease top-3 recall 92%) but **miscalibrated absolute probabilities for rare conditions**
   → add `CalibratedClassifierCV` (isotonic) before showing percentages; present ranked risk meanwhile.
3. **External + prospective clinical validation.** Independent **Indian cohort**; recalibrate reference
   ranges; report calibration, not just AUC; **benchmark vs standard-of-care** (Pooled Cohort Equations,
   QRISK3 for CV; PhenoAge for aging). Add **cystatin C** (needs a cohort that measured it — NHANES in
   our cycles does not).
4. **Fall/emergency study.** Validate on **real-fall data (FARSEEING)** + a prospective daily-life study;
   primary endpoints **false-alarms/day** and sensitivity; IRB + consent.
5. **Device signal validation.** Patch ECG / ring PPG HRV & SpO₂ vs reference (already partly in
   `telomy-lab`); needed before any clinical reliance on the wearable-fusion overlay.

## 5. Risk management & labelling
- **ISO 14971** risk file; deterministic safety rules (interactions, alarms) are tested code, never LLM
  output; human override on every emergency escalation.
- **Labelling / claims:** "informational, not a diagnosis"; no cure/lifespan claims; probabilities framed
  as screening/risk; emergency features "assistive, not a substitute for calling emergency services."
- **Longevity interventions** (see `LONGEVITY_INTERVENTIONS.md`): we never administer/sell unproven
  therapies; evidence grades shown; prescriptions clinician-gated.

## 6. Near-term regulatory actions (next 90 days)
Freeze wellness-vs-SaMD claim boundaries in copy · draft the ISO 14971 risk file + intended-use
statements · scope the CDSCO Class B/C submission for the risk engine · DPDP consent + data-flow map
(highlight on-device) · design the external-validation and fall-study protocols with an ICMR-aligned
partner. Owner: `clinical-regulatory` agent; gating most of the "pending" items in DPR §7.
