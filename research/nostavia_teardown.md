# Nostavia Health — Functional & UX Teardown
Captured 2026-10-06 via iPhone Mirroring (iOS). Reference for Telomy — feature/flow spec only; Telomy uses its own code, visuals and brand.

## Global
- Visual language: dark navy/indigo gradient background, glassmorphism cards (translucent, 1px light border, ~24px radius), large white numerals, small uppercase tracked labels (e.g. "BIOLOGICAL AGE", "DAILY BLUEPRINT").
- Each intelligence card has its own saturated color: purple (Blueprint), green (Food), red (Cardiovascular), blue (Performance).
- Floating pill tab bar (Home, Protocol, Labs, Wearables) + separate circular "+" FAB at bottom right. Tab bar hides on scroll down.

## 1. Home
Header
- "Welcome, User" (name from profile).
- Pill badge "N 74" — likely a Nostavia score / points (to verify on tap).
- Settings gear (top right).

Biological Age hero card
- Dropdown chip "BIOLOGICAL AGE ▾" (switchable metric — verify options).
- (i) info button.
- Big value: "--" when no data; caption "Calculated from markers".
- "Aging Speed 1.00x" (green) — pace-of-aging metric.

Quick actions (4 circular icon buttons): Diet Plan · Log Meal (camera) · Ask AI (sparkles) · Meditate.

"Intelligence Modules" sheet (scrollable, rounded top)
1. DAILY BLUEPRINT (purple) — "Adjust" button. Checklist rows with icon + title + subtitle + completion circle:
   - Lifestyle — "Circadian essentials"
   - Diet — "Nutritional windows"
   - Fitness — "Movement & activity"
   - Supplements — "No tasks for today" (no checkbox when empty)
2. FOOD INTELLIGENCE (green, chevron →) — semicircle gauge "0 kcal", state chip "FASTING", headline "Your body is repairing", contextual copy ("Good morning! Your body spent the night repairing. You're primed and ready for your first meal."), macro row Protein / Carbohydrates / Fats (g).
3. CARDIOVASCULAR INTELLIGENCE (red, chevron →) — score "59/100", status chip "RESILIENT", overnight HR line chart 10PM–7AM with annotated points SLEEP-START, MAX SLEEP DIP, VAGAL TONE; headline "Cardiovascular vagal tone is highly optimal"; explanation vs 30-day baseline (64 bpm); metric row HRV 52 ms ✓ · Resting HR 64 bpm ✓ · VO2 Max -- ✓.
4. PERFORMANCE INTELLIGENCE (blue, chevron →) — "Performance Readiness 51%", chip "Low", 24h readiness curve (12AM–12AM) annotated PEAK / SLUMP / REBOUND; headline "Performance capacity is currently reduced."; advice copy; row Focus High ✓ · Energy Low ⚠ · Reaction Optimal ✓.

### Home – hero metric switcher
Dropdown options (each swaps value/unit/secondary stat; (i) opens a bottom sheet "WHAT IT IS / WHY IT MATTERS" + "Got it"):
| Metric | Unit caption | Secondary stat |
|---|---|---|
| Biological Age | "Calculated from markers" | Aging Speed 1.00x |
| VO2 Max | ml/kg/min | Fitness Level (Unknown) |
| HRV | ms (RMSSD) | Stress State (Normal) |
| Energy Burned | kcal today | Move Goal % |
| Steps | steps today | Daily Goal % |
Empty state shows "--".

## 2. Leagues & Rewards (tap "N 74" badge; also in Settings)
- Hero: glowing medal orb, "RANK #1" chip, tier name "BRONZE", "25 DAYS UNTIL RESET" (monthly league).
- XP card: Current XP 590 / Next Tier 2000 + progress bar.
- Badge Collection: horizontal carousel (Silver, Gold, Platinum… locked = greyed).
- League Roadmap: vertical timeline: Bronze (ACTIVE) → Silver 2000 XP → Gold 6000 → Platinum 12000 → Diamond 18000 → Legendary 25000 (LOCKED chips).
- Note: header badge number (74) ≠ XP; likely a separate score (streak/health score) — TBC.

## 3. Settings (gear)
- Header: back, "Settings", bell with unread count badge (24).
- Upsell banner: "Nostavia Plus — Smart. Personal. Pro." + Upgrade.
- PROFILE: avatar (camera to change photo) + name → profile; Leagues & Rewards; Activity Goals (daily Move, Training, Steps targets); Nutrition Goals (daily Energy and Macro targets); Longevity Profile (6-Pillar assessment); Meditation Stats (history/progress); My Lab Records (uploaded lab reports); Export Health Data (clinical PDF snapshot for doctor); Organization (Selected: Nostavia → multi-tenant / clinic orgs).
- INTELLIGENCE: AI Memories (view/manage what AI remembers).
- INTEGRATIONS: Connections (Apple Health & WHOOP).
- NOTIFICATIONS: Push Notifications toggle.
- DASHBOARD CUSTOMIZATION: Intelligence Modules Order — drag handles to reorder: Protocol Group (Timeline & Blueprint), Food, Cardiovascular, Performance.
- APPEARANCE: App Icon picker (Default / N PLUS alternate icon).
- SUPPORT: Help Center (FAQs), Review Onboarding, Contact Us.
- LEGAL: Terms, Privacy, Refund Policy, Telehealth Consent, Open Source Licenses.
- Sign Out; Delete Account (red); version "v2.1.15 (262)".

## 4. Onboarding (6 pages, light theme, page dots + full-width dark "Continue" pill)
1. Splash: app icon + "Your Personal Health Intelligence".
2. Lab Intelligence — "Visualize your health trajectory…": Vitamin D 42.5 ng/mL OPTIMAL with Jan–Dec trend line; LDL 97.8 mg/dL OPTIMAL sparkline.
3. Food Intelligence — "Scan meals, get molecular breakdowns. Understand toxin exposures. Predict metabolic responses.": meal score ring 85 (Avocado Toast 320 kcal), macro bars (P/C/F), Digestion Time 2.5 hrs, Energy Curve Stable.
4. Wearables Sync — Apple Watch, Oura, Whoop: RR 15.0 rpm, RHR 54 bpm (Normal), "Today's stress" Highest/Lowest/Average + ring score 46 Low, battery-style energy bar 85%.
5. AI Health Concierge — "trained on your biomarkers, wearables, nutrition, risk factors": prompt card "What would you like to know?", History →, Start Chat.
6. Privacy & Data Security — Trusted AI partners (HIPAA-compliant Azure OpenAI & Google Gemini), Health data processing disclosure, Privacy Shield (never used to train public models, encrypted at rest/in transit); mandatory consent checkbox; "Get Started" blocked with toast "Please accept the privacy terms to continue."

## 5. Protocol tab
- Title "Protocol — Your personalized health protocol".
- Active protocol card: "Phase 1" chip, "All Protocols ›", name "The Longevity Engine", tags "VO2 Max Optimization • LIFE EXTENSION", primary CTA "Start Protocol".
- Segmented pillars: Lifestyle · Diet · Fitness · Supplements (icons).
  - Lifestyle: expandable cards (title, cadence, description): "Pranayama Breathwork — Daily — Ayurvedic breath control & recovery optimization"; "Sleep Focus — Night (Post-Training) — Prioritize sleep quality the night after Zone 5 sessions".
  - Diet: Macros ring + rules ("Carbs High (Zone 5)", "Carbs Low (Zone 2)"); Principles checklist ("Fuel Zone 5 with Carbs", "Fast/Low Carb for Zone 2"); "Your Weekly Menu ›".
  - Fitness: "Foundational Zone 2 — 3-4X/WEEK — 45-60 min brisk incline walk… Talk Test"; "The Peak (Zone 5) — 1X/WEEK — Norwegian 4×4"; "Low Impact Option — As Needed — Bike/Rower/Swim".
  - Supplements: empty state (inbox icon) "No supplements for this phase."
- "Health Disclaimer" pill → bottom sheet (educational only, consult a professional) + "I Understand".
- Protocol Library (All Protocols): "Advanced Protocols — Personalized by your physician" (empty: "No protocol yet. Complete onboarding.") and "Mini Protocols — Simple routines for specific goals" list with Active chip.

### Weekly Menu
- Horizontal day picker (MON 5, TUE 6 … selected = green glow).
- Meal cards per time slot (08:00 AM, 01:00 PM, 07:30 PM): Indian meals (Ragi Dosa + Chutney; Arhar Dal + Rice + Sabzi; Chana Masala + Roti), description, "Metabolic Power" kcal + stacked macro bar (Protein/Carbs/Fats grams).
- "SWAP" per meal → sheet "Swap Meal — Any preferences for the replacement of '…'?" free-text (e.g. 'Make it high protein', "I'm out of eggs") → "GENERATE SWAP" (AI regenerates single meal).

## 6. Labs tab ("Health Data")
- Title is a panel switcher: "Health Data ▾ — Tap to switch panel • Biomarkers"; green "Upload" button.
- Switch Diagnostic Panel sheet: Standard Blood Panel (metabolic, lipid & hormone) · Gut Microbiome (phylum ratios, diversity, pathogens) · Genetic & Methylation (one-time SNP) · Biological Age (epigenetic clocks & pace of aging) · Heavy Metals (provoked urine toxicity) · Environmental Toxins (mycotoxins, pesticides, plasticizers).
- Summary card: status headline ("Needs Focus" / "Optimal"), "All Reports ›", narrative ("1 out of 2 markers are in the ideal range"), 3 tiles OPTIMAL / NORMAL / OUTLIERS counts, % legend + stacked bar, "Latest report analyzed on <date>" + AI one-liner.
- Search biomarkers field; category filter chips (All, General, …).
- Biomarker rows: name, status chip (OPTIMAL green / IN-RANGE amber / outlier red), value+unit coloured by status, expand chevron → Reference Range, Category, Last Sync, "Ask Intelligence" → inline streamed "Intelligence Summary" paragraph → "Deep Dive" (opens chat pre-filled with marker + summary context).
- Empty panel: "No Health Data Yet" + "Show sample values" + persistent "VISUALIZE SAMPLE REPORT" toggle at bottom (sample data mode).
- Gut sample: Microbiome Diversity card (Shannon 3.8/5.0), phylum composition stacked bar (Bacteroidetes 58%, Firmicutes 32%, Actinobacteria 6%, Proteobacteria 4%); markers Akkermansia, Bifidobacterium, Faecalibacterium (%).

## 7. Intelligence (AI chat)
- Header: back, "Intelligence", ⋯ menu (New Chat, History).
- Greeting bubble "Hello! I'm your AI health assistant…", thumbs up/down feedback on AI messages.
- User bubble right-aligned with border; AI answers as rich markdown (bold lead, H2/H3 sections), "Regenerate response".
- Composer: "Ask anything", attachment (photo picker — images/collections), send button (becomes stop while streaming).
- History list: title (first prompt), date ("Today"), preview snippet.

### Labs – Upload
- Full-screen "Lab Intelligence — Upload your lab report to generate deep physiological insights." Big circular drop zone "Select Report" (file icon) → disabled "Analyze Report" until a file is chosen.

## 8. Wearables tab ("Live Tracking")
- Header: "Live Tracking", "● Synced 7m ago", calendar (date picker) and refresh buttons.
- Activity rings card: Move 0/500 CAL, Training 0/30 MIN, Steps 0/10000 + 3 concentric rings (red/orange/green).
- Performance — "Daily strain & recovery": 3 ring gauges Strain %, Recovery %, Sleep %.
- Stress & Energy — "Body battery & stress levels": "Today's stress" card (Highest / Lowest / Average + semicircle dial with state label e.g. "Rest", → detail); body-battery segmented bar "--%".
- Health Monitor — "Key vitals at a glance": 2-col tiles each with icon, value, status ("No data"/"Lower") and a vertical mini range slider: RR, RHR, HRV, SpO2, Active kcal, Sleep, Exercise min, Skin Temp.
- Cardio — Cardio Load (chart card ›), Cardio Focus (min ›), HRR (heart-rate recovery ›), Cardio Fitness ("Waiting for Apple Watch data": VO2 Max ml/kg/min, Level, Percentile).
- Fitness — two-month activity heatmap calendar (Sep/Oct, legend 1 / 2 / 3+ activities, today outlined); Activity Summary (total time 30-day window, trend, chart); Strain Performance (% + "On Track" + line).

## 9. "+" FAB quick-action sheet (blurred overlay, FAB becomes ×)
Describe food (T) · Import food (image) · Voice food log (mic) · Meditate · Ask Nostavia (glowing orb, centre) · Scan food (camera frame) · Book Doctor (stethoscope) · Shop (bag).
- Describe food → dialog "Describe your meal" multiline ("e.g., 2 eggs and a piece of toast"), hint "AI will analyze nutrients and longevity impact.", Cancel / Analyze.

## 10. Hospital & Specialist Hub (Book Doctor)
- Eyebrow "NOSTAVIA HEALTH", title; segmented "Book Consultation" | "My Appointments (count badge)".
- Search "doctor, specialty, or hospital"; Partner Hospital Networks carousel ("All Hospitals — 4 Affiliated Networks", named institutes w/ city); specialty filter chips (All, Longevity & Anti-Aging, Preventive Care…); "Available Specialists (5)" + filter icon.
- Specialist card: photo, rating badge, name+credentials, specialty (accent), institute, bio, "Next Slot Today, 2:30 PM", "Book Now ›".
- Specialist Profile: share icon; stats Experience / Rating / Reviews; consultation type (Hospital Visit / Video Call / Home Lab Visit); date strip; time-slot chips; sticky footer "Verified Hospital Fee $220/visit" + "Confirm & Book →".
- My Appointments: card with specialty chip, status chip CONFIRMED, doctor, institute, date/time, visit type, expandable.

## 11. Shop (from + → Shop) — generic e-commerce
- Own sub-app with bottom nav (Shop, Search, Wishlist, Account); pincode/address picker, bell, wishlist, cart.
- Search "supplements, brands, products…", category tabs (All, Grooming, Fashion, Luxe, Clinical…), round category bubbles, promo banners, brand chips.
- Product grid: badge BESTSELLER, rating (count), name, description, price ₹ with strike-through + % off, "Price dropped by ₹X", View Details; sort by Popularity + Filter; quick chips On Offer / Price Drop / New.
- Observation: generic beauty/fashion catalog with mismatched imagery — low trust; Telomy should NOT copy (replace with clinician-curated Protocol Marketplace + Formulas).

## 12. Meditation
- "MINDFULNESS / Meditation" header + stats icon; large circular timer (10:00); duration chips 5/10/15/30/45/60 min; "START MEDITATION"; "SILENT SYNC" toggle (mute).
- Meditation Stats: Today's Goal 0/10 min + bar; tiles Streak (days) / Total (min) / Sessions; Last 7 days bar chart; Recent sessions list.

## 13. Log Meal ("Food Intelligence")
- Scanner glyph, "Log Your Meal — Get an instant deep-science breakdown of everything on your plate", lens chips (Longevity, Hormones, Bio-Hacks, Circadian).
- Inputs: big camera shutter (centre), Gallery, Voice, Describe Food.
- Result format (from onboarding): meal score ring /100, kcal, macro bars, Digestion Time, Energy Curve.

## Not captured (phone in use) — inferred / TODO
- Detail pages behind Food / Cardiovascular / Performance cards, Daily Blueprint "Adjust", Settings sub-pages (Activity/Nutrition goals, Longevity Profile 6-pillar assessment, AI Memories, Connections, Export PDF, Notifications inbox, Plus paywall).

---
# Synthesis — what Nostavia gets right / wrong (for Telomy)
Right: one-tap capture (+ sheet), AI explanation inline on every biomarker, panel switcher for multi-modal labs, Indian meal plans with swap, protocol pillars, specialist booking with consult types, info sheets ("what it is / why it matters"), module reordering, export PDF for doctor.
Wrong (Telomy design system forbids or improves): XP leagues/badges/streaks (gamification), neon gradient "spa" backgrounds, bold scores with no confidence or provenance, sample data toggle that blends with real, AI output presented as final with no clinician loop, generic shop, "Aging speed 1.00x" with no data, no event tagging, no consent granularity beyond a single checkbox.

## 14. Food Intelligence detail → "Nutrition Trends"
- Segmented Calories / Protein / Carbs / Fat; "Daily Calories" bar chart with dashed target line + chip "TARGET: 2000KCAL"; tiles 7-DAY AVG and TARGET DIFF; "Meal History" grouped by day (YESTERDAY): score badge (coloured 0–100), name, kcal • time, chevron; floating "+ LOG MEAL" pill.
- Meal logging accepts non-food items too (alcohol, cigarettes) — scored.

### Meal Analysis (per logged item) — sections in order
1. Score ring "NOSTAVIA SCORE" x/100 (red low), name, kcal; share button.
2. INTELLIGENCE INSIGHT (collapsible paragraph).
3. MACRONUTRIENTS — Protein/Carbs/Fat bars (g).
4. CIRCADIAN ALIGNMENT — time-of-day + "Circadian Match %" bar, explanation, 💡 actionable tip.
5. OPTIMIZATION TIP — "BIO-HACK THIS MEAL" (+75% chip), headline, mechanism, how/when.
6. HORMONAL IMPACT — Insulin / Leptin / Ghrelin rows each with status chip (Stable / Blunted Response / Elevated) + explanation.
7. METABOLIC SIMULATION — "6-Hour Energy Simulation" curve (Now→+6h) with label (Energy Crash); Digestion Time, Energy Curve tiles.
8. ABSORPTION & PREP — Nutrient Absorption % bar; prep advice card ("Consume with dietary fat/protein").
9. PROCESSING SCORE — Processing Level bar + chip (Processed).
10. BIO-IMPACT ANALYSIS — system cards (Sleep Architecture, Mitochondrial Function, Gut Health) with headline + mechanism.
11. TOXIN RADAR — threat count; items with severity chip (HIGH) + name + explanation.
12. LONGEVITY & CELLULAR AGING — Longevity Score delta (−18 pts) + pathway chips Sirtuin (Suppressing) / mTOR (Inhibiting) / Inflam. (Pro) + explanation.
13. "Remove from Log" (destructive) · footer "Powered by Nostavia Lens · Food photos processed securely, not stored by AI providers."
Observation: highly assertive claims ("direct cellular toxin", "massive peak") with no confidence/evidence — Telomy must render the same depth with confidence + citations + "correlates with" language.

## 15. Cardiovascular Intelligence (detail)
- Header "Updated just now". Score 59/100 + "+3 pts from last week", status chip (Resilient), "CLINICAL REF" chip (shield) → reference; narrative paragraph.
- Trend chart with 30D/60D/90D toggle; scrub tooltip (bug: shows raw float "64.15308921378008").
- HEART AGE: Actual Age vs Heart Age (30 vs 30) slider, chip COMPATIBLE, explanation, "VIEW DETAILED CALCULATIONS ▾".
- Overnight Cardio Scans: profile type ("Standard Circadian Profile — expected recovery curve"), night selector chips (Last Night Oct 5 / 2 Nights Ago…), overnight HR curve 10PM–6AM with timestamped markers.
- The Four Pillars (weighted composite): Autonomic Flexibility 35% (RMSSD, Baseline Adaptability, Vagal Reactivity), Cardiac Efficiency 25% (VO2 Max, ACSM Cohort Norm "Top 40%", Resting Workload), Vascular Health 25% (LDL/HDL/TG — "MISSING LABS" chip), Recovery Rate 15% (Post-exercise HRR, Reactivation Speed, Recent Stress Events w/ duration chips). Each pillar has status chip + CLINICAL REF + interpretation.
- Wearable Signal Feed: 7D/30D/90D/365D; HRV area chart (avg + label + latest w/ trend arrow), Resting HR area chart, Nightly SpO2 bars.
- Lab Intelligence: LDL/HDL/TG rows; "CORRELATION INSIGHT" card linking labs and wearable trends.
- Integrity problems observed (Telomy differentiator): pillar says "RMSSD 0 ms — 100% below your 30-day avg" while Home shows HRV 52 ms; Vascular "MISSING LABS" yet copy says "Endothelial risk markers are normal"; lab values "--" yet chip "IN-RANGE"; score computed despite missing pillar. → Telomy: provenance chip on every value, confidence gradient, never state status for missing values, show which inputs are missing & re-weighting.

## 16. Performance Intelligence (detail)
- Score 51/100 "+3 pts from last week", chip Low, CLINICAL REF; prescriptive narrative ("Central nervous system fatigue detected… HRV suppressed at 55 ms with sleep duration of 0.0h… Avoid high-intensity training").
- Trend 30/60/90D (flat line).
- Circadian Alertness Timeline: current phase card (e.g. "Sleep Consolidation" + explanation), "24-Hour Process C Alertness Curve" (12A–9P) with NOW marker, Peak/Dip labels.
- Four Pillars (expandable): Autonomic Readiness 35% (Resilient), Cognitive Capacity 25% (Impaired — Est. PVT Reaction Time 280 ms, Focus Stability Index 94 High, Attention Deficit Risk HIGH RISK + explanation "each hour of sleep loss below 7h adds ~10ms"), Circadian Alignment 20% (Misaligned), Energy Reserves 20% (Depleted).
- CLINICAL REF sheet: methodology paragraph + "Clinical Guidelines & Citations" cards (e.g. Dijk & Czeisler 1995; Halson 2014). ≈ Telomy "Open Methods", but no model version/confidence/inputs.
- Wearable Signal Feed 7D/30D/90D/1Y: HRV, RHR… (same component as cardio).
- Integrity issues: "sleep duration 0.0h" (missing data treated as zero → 'Depleted', 'Impaired' estimates from no sleep data); tooltip float bug repeats.

## 17. Lab upload flow — tested with 7 dummy reports (testdata/lab_reports, iCloud "Telomy Test Labs")
Flow: Upload → Select Report (iOS Files picker: Recents/Shared/Browse) → "Report Selected ✓ <filename>" → Analyze Report → processing screen ("Nostavia AI is processing your clinical data": steps Document Check → AI Vision Analysis → Bio-marker Mapping, progress "Analyzing pages 1–2 of 2… 90%", "Minimize — Continue in Background") → **Verify Results** (report title, test date editable, "N found", per-marker card: name, value field, delete, reference range, unit, status dropdown In-range/Outlier/Optimal, category tag, notes field, "+" add marker; mandatory "I verify that the extracted data matches my official laboratory report" → "Confirm & Save Report") → toast "Report verified and uploaded successfully! 🚀" + banner "Report Verified +500 XP • +50 Coins".
Extraction quality: good — all 31/17/14/8/8/11 markers, dates, units, ranges, genotypes ("C/T") and qualitative values ("Detected (low)") parsed correctly.

### Defects found (each is a Telomy opportunity)
1. Trend corruption: Hemoglobin shows 13.5 g/dL at 2026-07-02, 08-20 and 10-01 (true: 14.9, 13.5, 14.6); Vitamin D 35 at all three (true: 18, 35, 22). Each later upload appends another identical point → history is fabricated from latest value.
2. Reference range overwritten by internal defaults (12.0–17.5 vs report's 13–17).
3. Report replacement: the biomarker list shows only markers from the most recent upload (+2 legacy markers); after 6 uploads count went 31→19→13→2. Earlier reports' markers vanish from the list.
4. No panel routing: Gut / Genetic / Bio-age / Heavy-metals / Toxins reports are dumped into the Standard Blood list as category chips; the dedicated panels still say "No Health Data Yet".
5. Biological Age hero stays "--" and Aging Speed "1.00x" after uploading PhenoAge 37.9 / DunedinPACE 1.12.
6. Summary narrative static: "Your biomarker profile is improving" and "Latest report analyzed on 2026-08-20" regardless of uploads.
7. Cross-report AI: question about correlations across all reports → no response after 90 s, no error/spinner/retry (silent failure).
8. Gamification on medical data upload (+500 XP, coins). "N" header badge = coin balance (74 → 424).
9. Genetic variants shown as "Outlier" status (category error — genotypes aren't outliers).

## 18. Settings sub-pages
- Activity Goals: sliders Move kcal (100–2000), Training min (10–180), Steps (1000–30000).
- Nutrition Goals: "Daily Targets" numeric fields Energy/Protein/Carbs/Fat + "Ask AI" (AI suggests targets) + Save; info "goals serve as baseline for performance and metabolic recovery metrics".
- Longevity Assessment (~10 steps, progress bar, Back, X): Body composition (gender, DOB, weight, height, waist, hip, computed BMI) → Health baseline (self-rated health; energy pattern; sleep hours) → Lifestyle (weekly activity) → Stress (1–10 slider; responses multi-select) → Environment (drinking water source) → Goals ("top 3 priorities" — accepts 5, no validation) → Identity ("Do you believe aging is: genetic / modifiable") → "Assessment Complete — Protocol Engine ready… based on your 29 biomarkers" (Body Composition Synced, Lifestyle Analyzed, Stress Mapped, Environmental Load Calculated) → "Unlock Longevity Protocol" (returns to Settings; nothing visible).
- Notifications: tabs Activity (7) / Inbox (24), "Clear all"; activity feed = "Report Verified +500 XP +50 Coins", "Level Up! 🎉".
- Nostavia Plus paywall: 24/7 AI Health Concierge, Adaptive Intelligence Core, Digital Twin Simulation, Infinite Nutrition Scans, Advanced Dietary Insight; ₹399/month (7 days free) or ₹3,999/year (2 months free); Start 7-Day Free Trial; EULA/Privacy/Restore.
- My Lab Records: list by date (8 reports) — **every report shows "2 markers"** (data loss: 31/17/14/8/8/11 verified markers collapsed to 2), delete per report.
- Export Health Data ("Health Data Snapshot — Clinician-Ready Health Passport"): time range 7/30/90 days; section checklist (Patient Demographics, Longevity Intelligence, Lab Reports & Biomarkers, Wearable Vitals & Trends, Sleep Analysis, Nutrition & Diet, Active Health Protocols, Menstrual Cycle, Questionnaire Baseline, Appointments) → "Generate & Share PDF" → iOS share sheet.

### Export PDF audit (Nostavia_Health_Report_2026-10-06.pdf, 4 pages, dark theme)
- Patient "Patient", Age N/A, Bio Age "--", Longevity "--", Grade "--".
- Lab section lists "Biological Age — Epigenetic Clocks" report containing Hemoglobin + Vitamin D (wrong markers); only 2 markers per report.
- Wearable vitals in PDF (Avg steps 9,274, HRV 48.8 ms, RHR 62, sleep 7.2 h, sleep score 75, nutrition 1,823 kcal/day) contradict the app (0 steps, "No data", "sleep 0.0h") → **sample/demo data leaking into a clinician-facing document**.
- Protocol section lists supplements (Vitamin D3 5000 IU, Omega-3 2 g) while app shows "No supplements for this phase".
- Unicode en-dash renders as tofu boxes. Disclaimer present.
→ Telomy's Pre-Clinic Brief must carry provenance per value, never include sample data, and show "not available" honestly.
- AI Memories: empty state "Your AI is Learning — As you chat, I extract key facts about your health, goals, preferences" (refresh icon). No list/edit visible when empty.
- Organization: unstyled action sheet "Select Organization": Default / Test01 / Test02 (test tenants visible in production; current "Nostavia" not in list).
- Connections: "Wearable Integrations" → Connect Apple Health, Connect WHOOP.
