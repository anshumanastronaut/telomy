# Vera Health — Clinical AI Copilot Teardown (for Telomy doctor-platform integration)

**Research date:** 2026-10-28. Sources cited inline; most product/benchmark claims are vendor-reported (Vera's own site/blog) and flagged as such. No FDA clearance and no neutral third-party clinical validation of Vera's answers was found.

## 0. Disambiguation (confirmed the right company)

Target = **Vera Health** (legal entity "Veracity-Health, Inc."), at **verahealth.ai**, YC S24, founded 2024 by **Taieb Bennani** and **Maxime Allouch**. This is the clinical-AI-copilot / "OpenEvidence competitor". iOS bundle `io.vera.app`.

Not to be confused with: a women's/menopause telehealth brand, a cannabis "Vera/Verano", and assorted clinics. The clinical copilot is unambiguously verahealth.ai (ACEP partner, free-for-clinicians evidence search).

## 1. What it is & positioning

A **free, citation-first clinical decision-support search engine** — a "clinical copilot" that takes a natural-language clinical question and returns a short, structured, evidence-graded answer with inline citations to primary literature. Design principle: **retrieve → grade → answer** (sources pulled and ranked *before* the answer is generated), contrasted with tools that "generate advice first and add citations later." Answers deliberately short (~300 words median) ordered "**answer first, then the exceptions, then the evidence behind it**."

- **Target users:** licensed clinicians + trainees (MD, PA, NP, PharmD, students/residents). Beachhead = **emergency medicine** (official AI partner of **ACEP**), expanding to hospitalists, primary care, pharmacists, specialties.
- **Setting:** point-of-care, mobile-first (iOS/iPadOS/visionOS + Android) + web.
- **Promise:** current, trustworthy, cited answers in seconds, **free forever for clinicians**.
- **Traction (vendor-reported, figures conflict):** 250K–800K clinicians across sources; claims #1 clinical app on both stores since June 2026; ~1 in 4 physicians in Spain/Italy (unverified).
- **Funding:** **$32M total**, incl. **$28.5M Series A (Oct 27 2026)** led by Threshold Ventures (+ Mantis, SV Angel, YC, Gradient). Team ~12.
- **Differentiators vs field:** vs **OpenEvidence** — no pharma ads, global/multilingual, transparent grading-before-answer, 900+ calculators, curated news, built-in CME. vs **UpToDate/ClinicalKey AI** — AI-native, free, breadth-first. vs **Glass Health** — literature-answer-first (not a DDx scratchpad). vs **Dougall/Doximity GPT** — graded-retrieval pipeline + calculators + CME.
- **Independent caveat:** a June 2026 *Nature Medicine* study found frontier models beat OpenEvidence/UpToDate Expert AI; **Vera was not in it** — cross-tool ranking unestablished.

## 2. Every product feature & screen (main deliverable)

1. **Clinical Q&A search (core)** — free-text question → concise structured answer (bottom-line first, then exceptions, then graded evidence w/ inline citations); key points highlighted. Single search bar w/ a **paperclip/attach**; answer **streams** (continues when phone locked); selectable/copyable.
2. **Evidence grounding & inline citations** — statement-level links to primary sources; sources tagged by study type; references panel.
3. **Source grading** — ranks retrieved sources by design, recency, authority, population, relevance *before* composing; detects **superseded guidelines**.
4. **Patient-specific / context-adaptive reasoning** — tailors to specialty, patient profile, goal, region; **asks for missing parameters before answering** (e.g., apixaban → weight, SCr, valve history).
5. **Differential diagnosis & workup** — in patient-scenario queries (present but not primary surface).
6. **Treatment & dosing / medication checks** — dosing, **drug–drug interactions, contraindications, safety alerts**, prescribing-info excerpts.
7. **900+ medical calculators** — scores/risk/dosing, invokable in-context (major differentiator).
8. **Clinical trials matching** — browse trials, **check eligibility vs patient profile** ("Possible match", criteria met/to-verify).
9. **Clinical guidelines & society policies** — incl. **ACEP clinical policies** (official partner).
10. **Curated medical news / literature updates** — by specialty, summarizing what changed + practice impact.
11. **Deep Research mode** — multi-source workflow for complex questions (UI undocumented).
12. **Spaces (bring-your-own-corpus RAG, v1.3.6)** — curate team files/links, ask questions grounded in them; private/public; invite colleagues; pin from search bar. = team knowledge base.
13. **CME engine** — **+0.5 CME credits per search**, certificates, progress tracking.
14. **Multilingual answers** — EN/FR/DE/IT/ES/PT/JA/KO/zh-Hans + more.
15. **Attachments / iOS Share Extension** — attach content to a query; share into Vera from other apps.
16. **Cross-device + QR web sign-in** — iPhone/iPad/web/visionOS; scan QR to sign into web.
17. **Advisory council / governance** — ~19 physician advisors; Mount Sinai/ACEP endorsements.

**Confirmed gaps:** no ambient scribe / note generation, no patient handouts, no EHR write-back.

## 3. How it grounds answers

- **Corpus:** claims 60M+ peer-reviewed papers + guidelines (site) / 250M+ documents updated weekly (YC). Sources: literature, guidelines, drug refs, trial registries, care pathways.
- **Pipeline:** multi-model retrieval → source grading → synthesis ("retrieve and grade before generating").
- **Grading dims:** design, recency, authority, population, relevance; superseded-guideline detection. **No named user-facing scale** (unlike OpenEvidence's explicit "EvidenceGrade" GRADE-style letter — a gap Telomy could beat).
- **Citations:** inline, statement-level, link to primary source.
- **Confidence framing:** **no per-answer confidence score shown**; standard "doesn't replace clinical judgment / HCP-only" disclaimer. Internal QA = LLM "jury of judges" ensemble + clinician review (reported 92% clinician-clinician, 82% judge accuracy — internal, not user-facing).

## 4. Integrations & deployment

- **Platforms:** iOS 16.4+/visionOS/Android/web (macOS unverified).
- **EHR:** **none documented** (no SMART-on-FHIR, no write-back) — a real gap.
- **API:** none public.
- **SSO/enterprise:** none explicit; individual self-signup w/ credential verification; Spaces = light team collab; enterprise nascent.
- **Compliance (claimed):** HIPAA, GDPR, SOC 2, NIST AI RMF (trust.verahealth.ai). App Store "no data collected" (Apple-unverified).
- **Content partnerships:** ACEP; roadmap = publishers + societies + health systems.

## 5. Pricing & plans

- **Free for all licensed clinicians/trainees, worldwide, "forever"** — unlimited searches, updates, CME; access gated by credential verification.
- **No paid tier / per-seat / enterprise price found.** Explicitly **no advertising**. Monetization undisclosed (VC-funded).

## 6. Differentiators & weaknesses

**Praised** (App Store 4.9★ / ~2.1K): accuracy, few hallucinations, source transparency, switchers from UpToDate, on-par with OpenEvidence, fast/free/global/multilingual, calculators, CME.

**Weaknesses:** no scribe/documentation; no EHR/API/enterprise-SSO; no user-facing confidence/named grade scale; vendor numbers inconsistent (250K–800K users; 60M–250M docs); some benchmark tables cite implausible future model names — treat all accuracy claims (97.5% USMLE, 84.9% NEJM-AI, etc.) as **marketing**; **not FDA cleared**; no neutral validation; no patient-facing outputs.

## 7. Prioritized integration plan for the Telomy doctor platform

Build-type flags: **[LLM+grounding]** medical-grounded LLM/RAG · **[DATA]** external data/licensing · **[QW]** quick win. Regulatory umbrella: this is **clinician-facing clinical decision support** → India CDSCO + DPDP; globally keep it **non-device CDS** by always exposing citations + "review the source," never an unexplainable directive; audit-log every answer; "supports, does not replace clinical judgment."

**Tier 1 — high value, quick/medium effort (do first):**
1. **Cited clinical Q&A, retrieve→grade→answer** [LLM+grounding][DATA] — RAG over an evidence corpus; answer-first + exceptions + citations. Start with free corpora: PubMed/PMC OA, DailyMed (FDA labels), WHO/NICE/society open guidelines, India ICMR/NHM. Highest-scrutiny surface.
2. **Inline statement-level citations** [QW once RAG exists] — biggest trust driver.
3. **Explicit evidence-grade badge (beat Vera)** [LLM+grounding] — GRADE/Oxford-CEBM letter per claim + recency/superseded flag. Vera hides this; differentiator + regulatory asset.
4. **Drug info / dosing / interactions** [DATA] — license/integrate a drug DB (DailyMed/RxNorm/OpenFDA; India formulary). Safety-critical → source from DB, never free-text LLM.
5. **Clinical calculators library** [QW] — deterministic MDCalc-style scores; no LLM, low risk, high utility. Fast win.

**Tier 2 — high value, higher effort:**
6. **Patient-context-aware answering** [LLM+grounding] — prompt for missing params; Telomy's care-graph/patient data is a moat Vera lacks.
7. **Differential diagnosis & workup** [LLM+grounding] — Glass-style, grounded + cited; gate behind citations.
8. **Guideline/news updates by specialty** [DATA][LLM] — ingest guideline feeds + journal RSS, summarize change + impact.
9. **"Spaces" = clinic/team bring-your-own-corpus RAG** [LLM+grounding] — ground answers in a centre's own protocols; fits Telomy multi-tenant model (reuse `tenancy.py`, isolate per DPDP).

**Tier 3 — optional:**
10. **Clinical-trials matching** [DATA][LLM] — ClinicalTrials.gov + CTRI (India); LLM maps eligibility.
11. **CME credits per search** [partnership] — needs ACCME (US) / NMC (India) accreditation; licensing not engineering. Defer.
12. **Deep Research (agentic synthesis)** [LLM+grounding] — higher cost/latency; after Tier-1 quality proven.
13. **Multilingual (Hindi + regional)** [QW-ish] — valuable for 70% India footprint; verify medical-term fidelity.

**Skip/deprioritize** (Vera lacks them too): ambient scribe, patient handouts — separate product bets.

**Cross-cutting must-haves:** citations always visible (keeps non-device CDS) · no autonomous directive without reviewable basis · superseded-guideline detection · drug-safety from a maintained DB not the LLM · full audit log query→sources→answer · prominent judgment disclaimer · DPDP PHI handling + tenant isolation · documented clinician-review/QA loop before any answer surface ships.

## Key sources
verahealth.ai (home/product/about/blog); blog posts (vs-openevidence, $32M raise, grading, ACEP partnership, Italy/Spain expansion); App Store id6744374898 (4.9★); Google Play io.vera.app; ycombinator.com/companies/vera-health; trust.verahealth.ai; iatrox.com/blog/vera-health-vs-openevidence.

**Reliability caveats:** nearly all feature/corpus/benchmark/user-count claims are vendor-reported and partly inconsistent; no FDA clearance; no neutral validation; UI/screens under-documented; some benchmark tables cite implausible model names. App Store reviews are the main independent sentiment signal found.
