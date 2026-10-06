# Ultrahuman (Android, Galaxy A35) — teardown, 2026-10-06
Driven over wireless ADB (`research/ultrahuman/a.sh`). The account holds a real Blood Vision report; only structure is recorded here, not the person's values.

## Shell
- Header: menu · "ULTRAHUMAN ▾" product switcher · profile switcher "Self ▾" (family members / other profiles).
- Products: **Ultrahuman Ring**, **Metabolism (M1 CGM)**, **Ultrahuman Home** (air quality, light, noise/snoring), **Blood Vision**. Ring/M1/Home require hardware; without it only store pages show (Ring PRO ₹28,499; Home ₹54,999).
- Bottom tabs inside Blood Vision: **Vision** | **Jade** (AI).

## Blood Vision
1. **Follow-up nudges**: "Immune markers need a follow-up — it's been 78 days since you last tested… WBC, Neutrophils, Lymphocytes… were out of range… A retest tells you whether the cause is still active" + marker chips + "RETEST <marker> + 50 MARKERS" (commerce CTA).
2. "Your PDF is now a visual report" (+ EDIT) — PDF upload converted to a visual report.
3. **Blood Age** hero (needs a full Blood Vision test; "Your Blood Age needs an update" + "Schedule your retest" when stale). Contributes to **Ultra Age**.
4. Summary counts: N biomarkers / Optimal / Borderline / Out of range + "Visualize".
5. **All Markers** with search · filter · share; grouped by **health concern** (one marker can appear in several groups): General Health, Sleep Status, Inflammation Status, Fatigue, Glucose Regulation, Hair Health, Cholesterol Assessment, Detox Panel, Micronutrients, Kidney Health, Thyroid Health, Complete Blood Health, Immune Regulation, Urine. Row = name (unit), value, status chip WITHIN RANGE / BORDERLINE / OUT OF RANGE, arrow.
6. **Marker detail**: value + unit, clinical-category label (e.g. "Elevated (Subclinical Hypothyroid)"), range slider, **multi-band ranges personalised to sex + age** ("Ranges · Male, 28 years": <0.4 Low (hyperthyroid) / 0.4–4.0 Normal / 4.0–10 Elevated (subclinical hypothyroid) / >10 High (hypothyroid)), TRENDS chart, "About <marker>".
7. **Clinician Notes** (AI): Top 3 Markers (priority, trend, plain explanation, "Related biomarkers that get affected"), TL;DR summary. **Action Plan**: Recommended Foods (food → *Targets <marker>* → *Contains <nutrients>* → HIGH/MODERATE/LOW IMPACT), Targeted Supplements (supplement → targets → dosage, including **"Avoid"** for contraindicated ones e.g. electrolytes when potassium is high → impact), Lifestyle Changes (incl. **retest preparation** e.g. avoid strenuous exercise/alcohol before retesting AST). Disclaimer "AI-powered… not medical advice".
8. Upload a Blood Report (**Vision Cloud**): explainer (encrypted, Blood Age, Clinician Summary & Supplement Report) → Lab Test Details sheet (Lab test name, Date collected dd/mm/yyyy) → file. Download PDF Report. Looking for assistance.

## Jade AI
- 4-page intro: unified intelligence across Ring, Blood Vision, Glucose and Home; **two modes** — Normal Chat (quick) and **Deep Research** (multi-domain, grounded in medical literature); privacy.
- Consent gate (updated T&C + "not for diagnosis") → "Preparing our model…".
- Chat: **credits** ("5.0 credits remaining · 0.0 used"), suggested prompts, History, Select model, New chat.
- Answer quality benchmark (cross-marker question): groups markers into **clusters/axes** (thyroid–metabolic, inflammation–immune, haematologic, liver–biliary, electrolyte–kidney), computes **derived ratios** (NLR, absolute neutrophil count, BUN/creatinine), explicitly states single-snapshot limitation ("no longitudinal trends… only one sample date").

## Adopt in Telomy
- Health-concern groups (many-to-many marker ↔ concern) alongside panels.
- Sex/age-personalised multi-band zones with clinical-category labels.
- Retest nudges with "days since tested" per out-of-range cluster + retest prep instructions.
- Action plan: foods/supplements/lifestyle each linked to target markers with impact level and explicit **Avoid** contraindications.
- Derived markers computed automatically (NLR, ANC, TG/HDL, AIP, ApoB/ApoA1, TyG, FIB-4, eGFR CKD-EPI 2021, BUN/Cr, HOMA-IR).
- Sinc Deep Research mode (literature-grounded, citations).
- Profile switcher (family) — maps to Family Vault.
- Unified score across sources (Ultra Age ≈ Telomy Longevity age).

## Not explored (hardware-gated / disconnected)
Ring dashboards, M1 glucose, Home environment, upload completion. ADB connection dropped at the upload date field (form not submitted).

## Session 2 — Vision Cloud upload completed (with user's consent to Vision Cloud T&C)
Flow: Upload a Blood Report → explainer → **Lab Test Details** sheet (Lab test name, Date collected via Material date picker — *allows future dates*) → **"What to know before uploading"**: summary has no clinician interpretation · supported biomarkers only · blood reports only · English PDF · one report per upload · ☐ I agree to T&C/Privacy → system file picker → "File Selected · CHANGE FILE · GENERATE REPORT" over a biomarker word-cloud → returns to Vision with "Your report is being generated. Your results are being reviewed and finalised. Some markers take longer — we'll notify you" (asynchronous; human/AI review).
Uploaded: `02_Standard_Blood_Panel_2026-10-01.pdf` as "TEST DATA Sample Diagnostics", collected 01/10/2026.
Jade credits after one question: 4.00 remaining · 1.00 used. Jade home prompts now personalised ("Is my cholesterol ratio healthy?", "Explain my health scores").

### Telomy takeaways
- Telomy should accept non-blood reports too (it already does: 15 types) and multiple files per upload — a clear advantage.
- Date validation: reject future collection dates.
- Async processing with notification is fine, but Telomy shows the extracted values immediately for verification (faster trust loop).
