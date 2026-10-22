# Longevity Therapeutics — evidence-graded corpus

The research backbone for the geroprotector / biohacking / wellness layer that steers doctors, members and
centres to the **right** therapy, protocol, supplement or drug — and onto a **proper n-of-1 trial** rather than
a guess. Engine: [`backend/app/llx/geroprotectors.py`](../../backend/app/llx/geroprotectors.py). Served at
`/me/longevity`, `/me/longevity/trial`, `/me/longevity/catalog`, and inside the doctor assessment
(`/mgmt/clinic/assess` → `longevity` block). Current to the 2023–2026 literature.

## How to read this

Every intervention carries a **grade** and a **scope** — the grade is for a *specific* claim, and that claim is
usually a biomarker, not a hard outcome. **No intervention here has proven human lifespan extension; the corpus
says so explicitly.** The claims firewall is the same as the rest of the clinic engine: *supports / consider /
discuss / tracks response* — never *treats / cures / prescribes / extends lifespan*.

| Grade | Means |
|---|---|
| **A** | Strong human RCT or guideline-level evidence (for the stated scope) |
| **B** | Moderate human evidence |
| **C** | Small / mechanistic / mixed human evidence |
| **D** | Weak, contested, or animal-only |

**Tiers** (how the recommender groups output, and the order to act in):

1. **Foundation** — lifestyle. Strongest evidence, lowest risk. Do these first.
2. **Clinical** — approved drugs & hormones. For an *indication*, prescriber-led.
3. **Optional** — consumer supplements. Biomarker-driven; benefit is usually at the biomarker level.
4. **Experimental** — off-label / investigational / unapproved. Informed-consent, trial-grade, clinician-only.

## The honest picture — what the 2023–2026 evidence actually shows

### Foundation (A/B) — the real longevity drugs are behaviours
- **Aerobic fitness / VO₂max (A).** The single highest-yield lever. Each +1 MET ≈ **13% lower all-cause
  mortality** (Kodama, *JAMA* 2009); least-fit ≈ **5× death risk** vs elite-fit (Mandsager, *JAMA Netw Open*
  2018). Nothing in the drug or supplement columns comes close to this evidence base.
- **Resistance training (A).** Strength and muscle mass track survival; each ~5 kg lower grip strength ≈ 16%
  higher mortality (PURE). Protects independence.
- **Sleep regularity (A)**, **Mediterranean pattern (A, PREDIMED ~30% fewer CV events)**, **protein adequacy
  (B)**, **smoking cessation / alcohol moderation (A)**.
- **Caloric restriction (B).** CALERIE-2: ~2 yr of ~12% CR slowed the DunedinPACE pace-of-aging. **TRE /
  fasting (B)** — most human benefit tracks the calorie deficit, not the clock.

### Clinical (approved drugs / hormones) — powerful *for an indication*, not vanity
- **GLP-1 / GIP agonists (A for cardiometabolic).** SELECT: semaglutide cut **all-cause death (HR 0.81)** and
  MACE −20% in obese CVD patients without diabetes. A genuine mortality signal — but it is a cardiometabolic
  drug; "anti-aging" is inference, not direct evidence. Protect muscle during rapid loss.
- **SGLT2 inhibitors (A cardiorenal).** Strong HF/renal mortality benefit; canagliflozin extended *male* mouse
  lifespan (NIA ITP). Healthy-person geroprotection unproven.
- **Metformin (A for dysglycemia; C/D as a geroprotector).** First-line for diabetes/prevention. But **TAME is
  still unfunded and has enrolled no one (2026)**, and **MASTERS (2019) showed metformin blunts
  resistance-training gains** — it can work *against* a muscle goal. Depletes B12.
- **TRT (A for confirmed hypogonadism).** TRAVERSE showed CV safety in that population. It treats a deficiency;
  it is **not** anti-aging for normal levels. Raises hematocrit, suppresses fertility.
- **Growth hormone (D — steered away).** Longevity biology links *lower* IGF-1 to longer life (Laron). GH
  raises insulin resistance and cancer-risk concerns. Flagged NOT recommended for longevity.

### Experimental (off-label / investigational) — interesting, unproven, clinician-only
- **Rapamycin (C).** Most consistent lifespan drug in mice (ITP, both sexes). **PEARL** human RCT (48 wk, weekly
  5–10 mg): relatively safe; modest gains (lean mass, pain) in women on 10 mg; **primary visceral-fat endpoint
  not met**; industry-affiliated authors. Immunosuppressant — infection / wound-healing / lipid risk.
- **Acarbose (C)**, **17α-estradiol (mouse-only)**, **canagliflozin** — the NIA **Interventions Testing
  Program** gold-standard mouse results, strongly **sex-dependent** (mostly male). Mouse ≠ human.
- **Senolytics — Dasatinib+Quercetin (C), Fisetin (C).** Clear senescent-cell *clearance* on biomarkers, but
  the randomized post-menopausal bone trial **missed its primary endpoint** (benefit only in a high-burden
  subgroup); fisetin OA trial null. **No adequately-powered RCT shows a clinical benefit yet.** Dasatinib is a
  chemotherapeutic — trial-grade only.
- **Low-dose lithium (C)** — narrow therapeutic index; renal/thyroid effects.
- **Peptides.** **BPC-157 (D)** — not FDA-approved, US compounding status unsettled (2026), almost no human
  data. **Thymosin α-1 (B)** — best-evidenced, approved in 30+ countries, not the US (regulatory gap).
  **Epitalon (D)** — unapproved, unreplicated, theoretical telomerase/cancer concern. Legal + sourcing risk.

### Optional (consumer supplements) — mostly biomarker movers
- **Vitamin D (A to correct deficiency)**, **Creatine (A for strength; B cognition)**, **Omega-3 (B** —
  DO-HEALTH: 1 g/day slowed several DNAm aging clocks by ~3–4 months over 3 yr, additive with vitamin D +
  exercise; lowers triglycerides**)**.
- **NMN / NR (A for raising NAD+, D for outcomes).** Reliably ~double circulating NAD+, but a 2024 meta-analysis
  of 12 NMN trials found **no clinically meaningful outcome**. FDA **relisted NMN as a lawful supplement, Sept
  2025**.
- **Urolithin A (C)** — mitophagy; modest, low-certainty muscle/endurance effect (some primaries missed).
  **GlyNAC (C)** — Baylor single-group trials; benefit recedes on stopping. **CoQ10 (B)** — statin myalgia / HF
  adjunct. **Magnesium (B)**, **Glycine (C)**, **Spermidine (C** — SmartAge cognition null; food-first**)**,
  **Sulforaphane (C)**, **Collagen (C)**, **Ca-AKG (D** — uncontrolled n≈42 human study**)**.
- **Taurine — the cautionary tale (D for longevity).** The 2023 *Science* mouse paper drove the hype; a **2025
  NIA rebuttal** (humans, monkeys, mice) found taurine does **not** reliably fall with age and is a poor aging
  biomarker. Modest blood-pressure lowering (C) is the most that survives.

## The model

**`recommend(profile, biomarkers)`** → safety-screened, evidence-graded candidates grouped into the four tiers
and ranked by grade within each. Triggers fire on goals (longevity / metabolic / muscle / cognitive /
cardiovascular / inflammation / sleep / immune / skin), biomarker thresholds (VO₂max, HbA1c, 25-OH-D, hs-CRP,
triglycerides, ALMI, testosterone, …), age and sex. A hard-coded screen **blocks** on contraindications and
**flags** drug interactions — never a model output. Drugs, hormones, peptides and off-label items are marked
`doctor_gate: true`.

**`design_trial(intervention_id, profile)`** → a real **n-of-1** protocol: two baseline measurements to pin
variability, a defined course (12 wk default; 16 for senolytics; 8 for peptides), adherence gating (≥80%),
washout + re-challenge where safe, explicit **stopping rules**, and a **response rule** (≥half the tracked
markers move beyond baseline variability with no stopping rule → RESPONSE, else deprescribe). Lifestyle and
consumer supplements can self-run; anything clinical/experimental is clinician-supervised. Results recalibrate
the member's plan and roll up (de-identified) into centre priors — the same n-of-1 loop as the modality and
supplement engines.

## Safety & claims posture
- Contraindications and interactions are deterministic and auditable, not inferred.
- Nothing reaches a member until a clinician validates it (the existing doctor gate).
- India: supplements = FSSAI nutraceutical (wellness claims only, drug-interaction warnings mandatory); drugs
  off-label = a prescriber's decision under CDSCO rules.
- Grades describe evidence for a **scope**, which is usually a biomarker. Human lifespan extension is unproven
  for every entry, and the corpus states this in its disclaimer.

## Extending the corpus
Add a record to `INTERVENTIONS` with the full schema (grade, scope, hallmarks, mechanism, effect with named
trials, dose, monitor markers, contra, interactions, triggers, one honest caution). Tests in
[`tests/test_geroprotectors.py`](../../backend/tests/test_geroprotectors.py) enforce the schema, the ranking,
the safety gating and the claims firewall.

## Key sources
Kodama *JAMA* 2009 (CRF/mortality); Mandsager *JAMA Netw Open* 2018; PURE (grip strength); CALERIE-2 2023;
PREDIMED 2018; SELECT 2023 (semaglutide); EMPA-REG/CREDENCE/DAPA-HF; DPP/DPPOS, MASTERS 2019 (metformin);
TRAVERSE 2023 (TRT); PEARL 2024/25 (rapamycin); NIA Interventions Testing Program; Mayo senolytic trials 2024;
NAD+ head-to-head RCT (*Nature Metab*) + 2024 NMN meta-analysis; urolithin-A RCTs + 2026 review; Baylor GlyNAC;
DO-HEALTH 2025 (*Nature Aging*); Singh 2023 *Science* + de Cabo 2025 *Science* rebuttal (taurine). Full links
in the research session log.
