# Superpower → Telomy biomarker gap — implementation spec

*Prepared 29 Oct 2026 from superpower.com/biomarkers vs Telomy's catalog. Paste-ready additions + exact wiring. Telomy already has ~260 markers / 24 panels.*

## Already ahead — do NOT add
Epigenetic clocks (Horvath/GrimAge/DunedinPACE/PhenoAge) + telomere; **proteomic organ-age panel**; cardiac CT (CAC+CCTA); MRI (brain/liver PDFF/whole-body); FibroScan; 14-day CGM; CPET/VO2max + grip/gait/STS/balance; ECG/Holter/echo/ABI/PWV/ABPM; spirometry; home sleep study; gut-taxa microbiome; full Indian CBC indices.

## Already derived (belongs in `derived.py`, NOT MARKERS)
TG/HDL, AIP, TyG, ApoB/ApoA1, FIB-4, NLR, ANC, cystatin-C eGFR, HOMA-IR are already computed. Also-derivable (add to `derived()` if wanted): Castelli I/II, atherogenic coefficient, non-HDL/ApoB, Free Androgen Index, T/E₂, corrected calcium, FTI, METS-IR, UHR, PLR/LMR/SII/SIRI, bilirubin:albumin, ferritin:albumin, GGT:HDL.

## TIER 1 — add to `catalog_ext.py` EXT_MARKERS / `catalog_more.py` MORE_MARKERS (clinically solid, paste-ready)
```python
# cardiometabolic (advanced/blood)
"vldl": ("VLDL cholesterol","blood","mg/dL",2,30,"low",["vldl cholesterol","vldl"],"13458-5"),
"nonhdl": ("Non-HDL cholesterol","blood","mg/dL",0,130,"low",["non-hdl cholesterol","non hdl cholesterol"],"43396-1"),
"ox_ldl": ("Oxidized LDL","advanced","U/L",0,50,"low",["oxidized ldl","oxldl","ox-ldl"],""),
"cpeptide": ("C-peptide (fasting)","advanced","ng/mL",0.5,2.0,"mid",["c-peptide","c peptide"],"1986-9"),
"fructosamine": ("Fructosamine","advanced","µmol/L",200,250,"low",["fructosamine"],"14959-1"),
"adiponectin": ("Adiponectin","advanced","µg/mL",5,30,"high",["adiponectin"],""),
"leptin": ("Leptin","advanced","ng/mL",1,12,"low",["leptin"],""),          # sex/BMI-dependent → ZONES
"adma": ("ADMA","advanced","µmol/L",0.4,0.75,"low",["adma","asymmetric dimethylarginine"],""),
"sdma": ("SDMA","advanced","µmol/L",0.3,0.6,"low",["sdma","symmetric dimethylarginine"],""),
# brain/Alzheimer's (advanced; grade C; gate like neuro_bio)
"abeta_ratio": ("Amyloid-β 42/40 ratio (plasma)","advanced","ratio",0.08,1.0,"high",["abeta 42/40 ratio","amyloid beta 42/40 ratio","aβ42/40"],""),
"abeta42": ("Amyloid-β 42 (plasma)","advanced","pg/mL",None,None,"info",["abeta 42","amyloid beta 42"],""),
"abeta40": ("Amyloid-β 40 (plasma)","advanced","pg/mL",None,None,"info",["abeta 40","amyloid beta 40"],""),
# vitamins (micronutrients)
"vitc": ("Vitamin C (ascorbic acid)","micronutrients","mg/dL",0.4,2.0,"mid",["vitamin c","ascorbic acid"],"1897-8"),
"vitk1": ("Vitamin K1 (phylloquinone)","micronutrients","ng/mL",0.1,2.2,"mid",["vitamin k","vitamin k1","phylloquinone"],"2888-6"),
"vitb6": ("Vitamin B6 (PLP)","micronutrients","µg/L",5,50,"high",["vitamin b6","pyridoxal-5-phosphate","plp"],"2064-7"),
"rbc_folate": ("RBC folate","micronutrients","ng/mL",280,900,"high",["rbc folate","red cell folate","erythrocyte folate"],"2285-5"),
# sex hormones (hormones) — FAI & T/E2 are derived
"dht": ("Dihydrotestosterone (DHT)","hormones","ng/dL",30,85,"mid",["dihydrotestosterone","dht"],"13932-9"),
"ohp17": ("17-Hydroxyprogesterone","hormones","ng/dL",0,220,"mid",["17-hydroxyprogesterone","17-ohp","17 ohp"],"1668-3"),
"psa_free": ("Free PSA","hormones","ng/mL",None,None,"info",["psa free","free psa"],"10886-0"),
"psa_pct_free": ("% Free PSA","hormones","%",25,100,"high",["psa % free","% free psa","percent free psa"],"12841-3"),
# thyroid (hormones) — FTI could be derived
"t3_uptake": ("T3 uptake","hormones","%",24,39,"mid",["t3 uptake","thyroid uptake"],"3050-2"),
"fti": ("Free thyroxine index","hormones","",1.2,4.9,"mid",["free thyroxine index","fti","ft4 index"],"3027-0"),
# autoimmune (immune)
"ccp_ab": ("Anti-CCP antibody","immune","U/mL",0,20,"low",["cyclic citrullinated peptide","anti-ccp","ccp antibody"],"33935-8"),
"dsdna_ab": ("Anti-dsDNA antibody","immune","IU/mL",0,30,"low",["double-stranded dna antibodies","anti-dsdna","dsdna"],"5131-8"),
"rf": ("Rheumatoid factor","immune","IU/mL",0,14,"low",["rheumatoid factor","rf"],"11572-5"),
"iga_serum": ("Immunoglobulin A (serum)","immune","mg/dL",70,400,"mid",["immunoglobulin a","serum iga"],"2458-8"),
"ena_ssa_ro": ("Anti-SS-A (Ro)","immune","",None,None,"absent",["anti-ro (ss-a)","anti-ss-a","ss-a"],""),
"ena_ssb_la": ("Anti-SS-B (La)","immune","",None,None,"absent",["anti-ss-b","ss-b","la antibody"],""),
"ena_sm": ("Anti-Smith (Sm)","immune","",None,None,"absent",["smith antibody","anti-sm"],""),
"ena_rnp": ("Anti-RNP","immune","",None,None,"absent",["rnp antibody","anti-rnp"],""),
# urine microscopy/dipstick (urine)
"u_ketones": ("Urine ketones","urine","",None,None,"absent",["urine ketones"],"2514-8"),
"u_nitrite": ("Urine nitrite","urine","",None,None,"absent",["urine nitrite"],"5802-4"),
"u_leuk_est": ("Urine leukocyte esterase","urine","",None,None,"absent",["urine leukocyte esterase","leukocyte esterase"],"5799-2"),
"u_bilirubin": ("Urine bilirubin","urine","",None,None,"absent",["urine bilirubin"],"5770-3"),
"u_urobilinogen": ("Urobilinogen","urine","mg/dL",0,1.0,"low",["urobilinogen"],"19161-9"),
"u_rbc": ("Urine RBCs","urine","/hpf",0,2,"low",["urine rbcs","urine red blood cells"],"13945-1"),
"u_epithelial": ("Urine epithelial cells","urine","/hpf",0,5,"low",["urine epithelial cells","urine squamous epithelial cells"],"20453-7"),
"u_casts": ("Urine casts","urine","",None,None,"absent",["urine granular casts","urine hyaline casts","urine casts"],""),
"u_bacteria": ("Urine bacteria","urine","",None,None,"absent",["urine bacteria"],"5769-5"),
"u_crystals": ("Urine crystals","urine","",None,None,"absent",["urine crystals"],""),
```
Also set per-row **EVIDENCE** grades, **ZONES** (sex-specific for leptin, %free PSA, abeta_ratio), and **CONCERNS** mappings (Heart & arteries / Blood sugar & metabolism / Brain & cognition) in the same module.

## TIER 2 — bulk panel expansions (uniform unit/direction; add en masse)
- **Metals** (panel `metals`, "µg/g creat", better low): Antimony, Barium, Beryllium, Bismuth, Cesium, Gadolinium, Palladium, Platinum, Tellurium, Thorium, Tin, Tungsten, Uranium, Cobalt, + **blood mercury**.
- **Env toxins** (`toxins`, "µg/g creat", low): BPS, methyl/ethyl/propyl/butyl-paraben, 3-PBA (pyrethroid), atrazine mercapturate, diphenyl phosphate, oxybenzone, MBP/MiBP/MEOHP phthalates, HEMA, methylhippuric (xylene), phenylglyoxylic (styrene).
- **Mycotoxins** (`toxins`, "ng/g creat", low): Chaetoglobosin A, Citrinin, Enniatin B, Gliotoxin, Mycophenolic acid, Roridin E, Sterigmatocystin, Verrucarin A.
- **Specific-IgE allergens** (`immune`, "kUA/L", low, 0→0.35): Alternaria, Aspergillus, D.farinae, D.pteronyssinus, Bermuda/Timothy grass, cat/dog dander, cockroach, pigweed, ragweed, cedar, mugwort, Penicillium, birch, sycamore, ash, elm, mulberry, oak.
- **OAT** (`functional`, grade C/D, mostly "info"): Krebs (citric/aconitic/isocitric/α-KG/succinic/fumaric/malic/HMG), FAO (adipic/suberic/sebacic/ethylmalonic), neurotransmitter (HVA/VMA/DOPAC/quinolinic), microbial (hippuric/4-cresol/HPHPA/DHPPA/arabinose/tartaric), B-vit (pyridoxic/pantothenic/glutaric). Label functional-medicine-grade.

## TIER 3 — new modalities (new TESTS, decision needed; may skip for evidence posture)
Vaginal microbiome; sperm analysis + DFI; WGS (likely skip — we have targeted SNPs/PRS).

## Wiring (exact files/functions)
- **Markers:** add to `catalog_ext.py` EXT_MARKERS (advanced/blood/brain), `catalog_more.py` MORE_MARKERS (hormones/micronutrients/immune/urine/functional), `catalog.py` metals+toxins sections (auto-merge via existing `MARKERS.update(...)`). Add report-name aliases to `catalog_routine.EXTRA_ALIASES`. Verify `catalog.match_marker()` (longest-alias, word-boundary) doesn't shadow existing ids — test `non-hdl cholesterol` vs `hdl`/`chol_total` on a real lab line.
- **Test-booking:** `diagnostics.py` TESTS — extend existing tests' `markers` lists and add new `T(...)`: Alzheimer's/brain package (`abeta_ratio,abeta42,abeta40,ptau217,nfl,apoe,homocysteine,b12`), advanced cardiometabolic, toxin-exposure (metals+env+myco), ENA panel, sperm, vaginal-microbiome. Add bundles under category "Bundles" (like `longevity_panel`). Update `recommend()` with risk-triggered rules (amyloid when apoe ε4+/age≥65; adv-cardio when apob>100 / tg_hdl>3; ENA when ana+).
- **Derived ratios:** add the also-derivable list to `derived.py::derived()`.
- **Mobile:** `tests.tsx` needs NO change — it renders `/tests` categories dynamically. Routes in `main.py` (`/tests`, `/tests/recommended`, `/tests/book`) unchanged.
