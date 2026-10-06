# Apple Health (iOS 26) — Functional teardown for Telomy
Captured 2026-10-06 via iPhone Mirroring. Capability reference only — Telomy uses its own code, visuals and brand (Apple's names, icons, illustrations and articles are not to be copied).

## Navigation
- 3 destinations: **Summary**, **Sharing**, **Search** (floating search button opens Browse + search field). Profile avatar (initials) top-right of Summary.

## 1. Summary (home feed)
1. **Pinned** (user-curated, "Edit"): cards per metric — coloured category label + icon, timestamp ("Today", "10:31 AM", "Yesterday"), headline value + unit, 7-bar sparkline with today highlighted; empty card says "No Data".
2. "Show All Health Data" row.
3. **Trends**: "Show All Health Trends" (long-term up/down trend detection per metric).
4. **Highlights**: auto-generated plain-language insight + chart ("You burned an average of 151 kilocalories a day over the last 7 days", bar chart T–M with average line); "Show All Highlights".
5. **Get More From Health**: dismissible feature-onboarding cards — Logging Emotions & Moods (Get Started), Set Up Medications (Add a Medication), Blood Pressure Log (Get Started).
6. **Health Checklist**: device safety features grouped Inactive / Active with status dot + Enable (Headphone notifications, Emergency SOS, Medical ID, …).
7. **Articles**: illustrated editorial cards → full-screen article sheet (sourced, e.g. Mayo Clinic).
8. **Apps**: suggested third-party apps that write to Health, with (i).

## 2. Browse — Health Categories
Activity · Body Measurements · Cycle Tracking · Hearing · Heart · Medications · Mental Wellbeing · Mobility · Nutrition · Respiratory · Sleep · Symptoms · Vitals · Other Data · **Clinical Documents** (separate).

Category page pattern: tinted header + title → "Today"/"Past 7 Days"/"Past 12 Months" sections with data cards (sparklines) → "No Data Available" list of every supported data type → Get More From Health cards → "About <category>" articles.

Data types observed:
- **Activity**: Activity rings (Move), Active Energy, Resting Energy, Steps, Walking + Running Distance, Stairs Climbed, Cardio Fitness, Cardio Recovery, cycling cadence/distance/FTP/power, skiing, swimming, workouts…
- **Heart**: Heart Rate, AFib History, Blood Pressure, Cardio Fitness (+ notifications), Cardio Recovery, ECG, HRV, High/Low HR notifications, Hypertension notifications, Irregular Rhythm notifications, Peripheral Perfusion Index, Resting HR, Walking HR Average.
- **Mobility**: Double Support Time, Walking Asymmetry, Walking Speed, Walking Step Length, Walking Steadiness (OK/Low/Very low band chart).
- **Nutrition**: ~40 nutrients (Caffeine, Calcium, Carbohydrates, Chloride, Chromium, Copper, Dietary Cholesterol, Energy, Sugar, Fibre, Folate, Iodine, Iron, Magnesium, Manganese, Molybdenum, Mono/Poly-unsaturated & saturated fat, Niacin, Pantothenic Acid, Phosphorus, Potassium, Protein, Riboflavin, Selenium, Sodium, Thiamin, Vitamins A/B6/B12/C/D/E/K, Water, Zinc…).
- **Sleep**: Sleep Score (daily), Sleep (stages); articles.
- **Vitals**: Heart Rate, Blood Glucose, Blood Oxygen, Blood Pressure, Body Temperature, Menstruation, Respiratory Rate, overnight "Vitals" (out-of-range detection).
- **Mental Wellbeing**: Anxiety Risk & Depression Risk (questionnaire results, e.g. "Minimal"), Exercise Minutes, Mindful Minutes, Sleep, State of Mind (mood logging), Time in Daylight.
- **Medications**: setup — track list, schedule + reminders, interaction check, encrypted.
- **Symptoms**: ~40 symptoms (Abdominal cramps, Acne, Appetite changes, Bloating, Body ache, Chest pain, Chills, Congestion, Constipation, Diarrhoea, Fatigue, Fever, Headache, …) each logged with severity.
- **Other Data**: Alcohol consumption, Blood alcohol, Blood glucose, Handwashing, Inhaler usage, Insulin delivery, Falls, Sexual activity, Time in daylight, Toothbrushing, UV index.
- **Clinical Documents**: Show All Records, Data Sources & Access; import CDA files from providers.

## 3. Metric detail (e.g. Heart Rate)
- Range selector **H / D / W / M / 6M / Y**; headline "RANGE 80–147 BPM" + date; min–max range bars per bucket with selected point; "Latest" pill; "Show More <metric> Data" (averages, ranges, by context).
- "About <metric>" explainer with source citation (Mayo Clinic), related articles, suggested apps.
- **Options**: Pin to Summary, Show All Data (raw sample list), Data Sources & Access (source priority order), Unit.
- **"+" Add Data**: manual entry sheet (Date, Time, value) with ✓/✕.

## 4. Sharing
- Health Sharing explainer: You're in Control; Dashboard & Notifications (shared data appears in their Health app, alerts on updates); Private & Secure (summary-level only, encrypted, stop any time).
- **Share with Someone**, **Ask Someone to Share**; Apps (read/write permissions per app); Research Studies; "Sharing With You" list.

## 5. Profile (known structure; personal data not captured)
Health Details (DOB, sex, height, weight, blood type), Medical ID (emergency info on lock screen), Health Records (provider FHIR connections), Features (notifications etc.), Devices, Apps & Services permissions, Research Studies, Privacy, Export All Health Data.

---
# Telomy adoption list (Apple Health → Telomy)
| Apple capability | Telomy version |
|---|---|
| Pinned summary + Edit | Home pinned cards (user-chosen), with provenance chip per card |
| Highlights (plain-language auto insights) | Sinc insights — same plain language plus confidence, evidence count, Receipts |
| Trends | Trend detection per biomarker/signal (30/90/365d), with significance not just direction |
| Full category taxonomy (14 categories, ~150 types) | Vault data model uses an equivalent taxonomy + lab panels + imaging + genetics |
| H/D/W/M/6M/Y detail charts, min–max bars, Show All Data, units | Biomarker/signal detail with the same ranges + personal baseline band + life-event overlay |
| Manual "+" entry for any type | Log sheet supports manual entry for every metric (source = manual) |
| Data Sources & Access priority | Provenance + source priority per metric |
| Medications (schedule, reminders, interactions) | Medications module + interaction check + N-of-1 launcher on start |
| Symptoms (severity) & State of Mind | Event log / daily reflection with severity + mood |
| Anxiety/Depression questionnaires (GAD-7/PHQ-9) | Mental-wellbeing assessments, results to clinician queue |
| Cycle tracking | Cycle module (opt-in consent) |
| Mobility / walking steadiness | Mobility signals from HealthKit |
| Clinical Documents / Health Records (CDA/FHIR) | Vault import: PDF labs + CDA/FHIR + DICOM |
| Health Sharing (summary-level, revocable) | Family Vault (scoped, time-boxed, access log) |
| Health Checklist | Vault Completeness checklist |
| Articles (sourced) | Evidence library linked from Open Methods |
| Medical ID | Emergency card (blood type, allergies, meds, contacts) |
| Export All Health Data | Specialist Pack (PDF + FHIR) + full data export |
| Apps permissions | Consent Centre (per-purpose, DPDP) |
