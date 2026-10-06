# Fittr (Android, Galaxy A35) — teardown (in progress), 2026-10-06
Package `com.squats.fittr`. Account holds a real lab report (27 Oct 2024); structure only recorded.

## Navigation
Bottom tabs: **Home · Lab Tests · Get a Coach · My Health · Me**.

## My Health
- Segments: **Summary | Health Timeline**; "Share Health Summary" (share with coach/doctor for personalised advice); options menu.
- Score ring "82% — Within Range!" (share of markers in range), "Last report date".
- **Biological Age** (years, "Younger/Older" chip) + **Speed of Aging** (e.g. 0.92, "Slower/Faster") → "See how we calculate bio age", "See affecting factors".
- **Summary of disease risk levels** table — Disease | Risk level (Low / Moderate / High): Hypertension, Muscle Breakdown, Chronic Inflammation, Thyroid Dysfunction, Cardiovascular Disease, Kidney, Neurodegenerative, Osteoporosis, Type 2 Diabetes, Liver.
- AI narrative card "Healthy with minor notes" + paragraph summary.

## Adopt in Telomy
- **Disease-risk matrix** (10+ conditions) with transparent drivers per condition — Telomy version adds which markers/imaging drove each level, confidence, and missing inputs.
- Speed-of-ageing number paired with bio age (Telomy has DunedinPACE + PhenoAge history).
- Health Timeline (Telomy Vault timeline already).
- Share summary with a coach (Telomy Family Vault / clinician share).

## Pending (phone locked with pattern; resume when unlocked)
Lab Tests tab (booking/catalogue), Health Timeline, risk-row detail, affecting factors, Get a Coach, Home feed, Me/profile, logging (food, workouts, water, steps).

## Session 2 (phone reconnected)
- **Affecting factors** sheet (bio age): AI narrative + Strengths / Weaknesses / Lifestyle optimisation; states that missing VO2 max, HRV and sleep data limit precision.
- **Health Timeline**: list of uploaded documents (type chip LAB REPORT, filename, record date, upload date, AI one-line summary), Filters, sort by Upload/Record date, "+" upload FAB.
- **Upload**: "My Health Reports" — Lab reports, prescriptions, discharge summaries and more; multiple files; images or PDF; "file should not be password protected"; → "Hang tight, we're analysing your health data — we'll notify you" (background) → bottom status "Validating & categorising reports… Extracting data… Categorising reports" with View. Uploaded test report `02_Standard_Blood_Panel_2026-10-01.pdf` (TEST DATA).
- Accepted updated Fittr T&C (with user's permission).
- **Lab Tests** tab gated by mobile-number OTP verification (not entered).
- **Home**: coin balance; search, notifications, chat; shortcut bubbles Get a Coach / Lab Test / Fittr Shop / My Plan; date selector; tiles Steps (vs yesterday), Water (+250 ml quick add), HRV, Modify; Nutrition card (kcal consumed / left); Exercise card; Community feed (Highlights / All / Discussions / Transformations, "Coached by" coach card, likes, comments, share, bookmark). "+" = Start a discussion / Post an update / Post your transformation / Add a recipe (public — not used).
- **Nutrition**: week date strip; Food View | Nutri View; kcal consumed / remaining; Set Macros; protein/carbs/fat vs targets; quick tips ("log raw weights"); coach-planned meals per slot (Breakfast items with tick-to-consume, ⋯, + add). Nutri View: carbs → total sugar, added sugar, dietary fibre (% RDA); protein; fat → saturated / unsaturated / trans; RDA disclaimer. Logged dummy: milk 200 ml (ticked).
- **Me**: profile, bio age + speed of ageing ("You are ageing at a natural pace"), View My Health, Refer & earn, **Tools**: Progress & insights, Diet tool, Training tool, BMR, Body-fat, Goal, Macro, Calorie calculators; Your information: Orders & invoice, Package history, **Health Connect (connected)**, Bookmarks.

### Defects observed (Telomy must avoid)
1. Biological age inconsistent across screens: My Health 35 / 0.92 vs Me 28 / 1.00.
2. My Health summary "Last report date 27 Oct '24" while timeline has a 2026 report.
3. Home nutrition card still "0 kcal" after a meal was ticked as consumed.
4. Water quick-add tap gave no visible feedback.

### Adopt in Telomy
- Accept prescriptions + discharge summaries + images (multi-file) — not just lab PDFs.
- Background processing with a persistent status bar and notification.
- Coach-planned meals you tick off; Nutri View with sugar/added sugar/fibre and fat subtypes vs RDA.
- Calculators (BMR, body fat, macros) feeding goals.
- Single source of truth for every score (one engine endpoint, all screens read it).
