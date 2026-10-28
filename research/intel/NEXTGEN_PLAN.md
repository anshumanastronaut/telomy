# Telomy Next-Gen — program plan (branch `telomy/nextgen`)

The umbrella project: evolve Telomy into a next-gen preventive/longevity platform that is, at once,
**(A) a clinician-grade Clinical Knowledge Engine** (OpenEvidence/Vera-class: retrieve → grade → cited answer over
the world's medical literature + guidelines + drug data) and **(B) a consumer Longevity super-app** (Superpower-class:
a composite bio-age score + named sub-scores, derived biomarker ratios, closed-loop retesting, AI+human concierge,
and a clinician-gated therapy/peptide recommender). Both ride a **shared AI + evidence + scoring foundation**.

Research backing: `research/intel/VERA_HEALTH.md`, `MEDICAL_KNOWLEDGE_SOURCES.md`, `SUPERPOWER.md`.

## Guardrails (non-negotiable, every milestone)
- **Non-device CDS:** citations always visible; no autonomous diagnosis/treatment directive without a reviewable basis.
- **Drug/dose/interaction facts** come from a maintained DB (DailyMed/openFDA/RxNorm/DDInter), **never** free-text LLM.
- **India CDSCO/DPDP:** anything peptide/Rx is clinician-gated, never auto-recommends unapproved substances; PHI is
  consented, tenant-isolated (`tenancy.py`), breach-guarded (engineer against Superpower's mis-delivered-PHI failure).
- **Honesty:** bio-age/scores framed as wellness/informational unless validated; state model MAEs plainly; label
  FAERS as "reported, not incidence"; preprints flagged low-grade.
- **License hygiene:** clear the 3 landmines before any corpus ships — StatPearls (NC-ND), SNOMED/UMLS (India), NICE
  (do-not-ingest). Carry `license` + `region` on every chunk; filter at query time.

## Shared foundation (both tracks depend on it)
1. **Knowledge layer** — a corpus RAG: ingest box builds a **SQLite-FTS5 index** (`knowledge.db`) of graded, cited
   chunks (PMC-OA, DailyMed, guidelines, India sources); the 512 MB query box queries it read-only. Live PubMed
   (`clinevidence.py`) stays as the freshness fallback. Hybrid BM25(+dense later). *(Longest pole — start now.)*
2. **Evidence/grading layer** — study-type→grade (A–D now; add Oxford-CEBM level + superseded-guideline flag),
   rank-by-grade, citation format standardized on `evidence.py`'s `{key, citation, finding}`.
3. **LLM grounding layer** — `telomy_llm.ask` with the citation guard (every cited id resolves to a retrieved source).
4. **Scoring layer** — aging-clock models + a composite **Telomy Score** + named sub-scores + derived biomarker ratios.
5. **Drug/safety layer** — `drugref.py` (openFDA/RxNorm/FAERS) + DDInter + FAERS signals, reused by both tracks.
6. **Audit + auth** — `/mgmt/clinic/*` staff auth + `copilot_log` audit trail for every clinician-facing answer.

## Track A — Clinical Knowledge Engine (phased)
- **A1. Corpus foundation** *(Milestone 1, in progress)* — `ingest/` package: SQLite-FTS5 schema + a seed ingester
  (PubMed/PMC) + `backend/app/kb.py` retriever; wire `clinevidence` to prefer the local KB, fall back to live PubMed.
- **A2. Bulk ingest + India corpus** — PMC-OA commercial subset, DailyMed, USPSTF/CDC, NIH ODS; India MoHFW/ICMR/CDSCO
  (incl. banned-FDC list). Dedup, section-aware chunking, grade+license+region metadata. Ingest box (separate VM).
- **A3. Hybrid retrieval + eval** — add dense vectors (sqlite-vec/LanceDB on the ingest box) + RRF; stand up the eval
  harness (MedQA, **MedMCQA for India**, PubMedQA, MIRAGE/PubMedRS-200) and gate quality before shipping.
- **A4. Grading++ & surfaces** — Oxford-CEBM level + superseded-guideline flag; wire the KB into Sinc (member) and the
  doctor evidence screen; drug monographs from the ingested DailyMed + live fallback.
- **A5. Staff auth + audit** — move `/clinical/*` under `/mgmt/clinic/*` + `_require_staff` + `copilot_log`.

## Track B — Longevity super-app (phased)
- **B1. Derived biomarker ratios engine** *(quick win)* — ApoB ratios, TyG, METS-IR, NLR/SII, atherogenic indices,
  cystatin-C eGFR, corrected calcium, A1C↔eAG — pure computation on imported labs; many "insights" at ~zero cost.
- **B2. Composite Telomy Score + sub-scores** — headline bio-age (reuse blood/muscle clocks) + 10–20 named precision
  scores (cardio, metabolic, inflammation, kidney, liver, hormones…), tracked across draws. Honest MAEs.
- **B3. Plain-language biomarker explainer + optimal-vs-normal ranges + trends** — Sinc auto-explains every marker,
  grounded in the Track-A evidence layer; optimal bands not just lab-normal.
- **B4. Closed-loop retest** — intervention → retest-in-3–6-mo prompt → before/after on the dashboard, tying labs +
  therapy tracking + wearables into one loop.
- **B5. Concierge care team** — AI (Sinc) + human (doctor platform) async inbox with an SLA.
- **B6. Therapy/peptide recommender (clinician-gated)** — evidence-graded options routed through a licensed doctor;
  **never** auto-recommend unapproved substances; India guardrails front-and-centre. Build only after A3 quality + B2.
- **B7. Marketplace / add-on attach** — supplements + partner-lab add-ons (India: IFCT-aware). Business-model lever.

## Sequencing (dependency-ordered)
1. **A1 corpus foundation** (now) + **B1 derived ratios** (parallel quick win) →
2. **A2 bulk+India ingest** + **B2 Telomy Score** →
3. **A3 hybrid+eval** + **B3 explainer/ranges** →
4. **A4/A5 surfaces+audit** + **B4 closed-loop** + **B5 concierge** →
5. **B6 recommender** + **B7 marketplace** (gated on evidence quality + regulatory sign-off).

## Reuse map (don't rebuild)
`retrieval.py` (BM25 → FTS5/hybrid) · `clinevidence.py` (live fallback) · `telomy_llm.py` (grounded gen + guard) ·
`evidence.py` (citations) · `calculators.py` + `drugref.py` (Tier-2, done) · aging-clock models (bio-age) ·
labs import + biomarker dashboards · Sinc (on-device + cloud) + file uploads · doctor/centre platform + `copilot.py`
+ `copilot_log` · therapy tracking · `tenancy.py` (isolation) · IFCT/FAERS/DDInter/DSLD data already in-repo.

## Progress log
- **A1 ✅ (M1)** — SQLite-FTS5 `knowledge.db` + `ingest/build_kb.py` + `backend/app/kb.py` (BM25 re-ranked by grade) +
  `clinevidence` prefers KB with live-PubMed fallback + `/clinical/kb/stats`. Vertical slice verified.
- **B1 ✅** — `backend/app/biomarkers.py` derived ratios (TC:HDL, LDL:HDL, TG:HDL, non-HDL, remnant, AIP, TyG, METS-IR,
  HOMA-IR, HbA1c→eAG) + `/biomarkers/ratios` + `mobile/src/app/ratios.tsx` ("Lab insights", Vault entry).
- **A2 (foundation ✅)** — multi-source ingest: `ingest/build_kb.py` now also loads **FDA drug labels** (openFDA/DailyMed,
  graded A) and a **guideline JSONL loader** (USPSTF/CDC/ICMR/MoHFW prepared entries). Flags: `--seed`, `--queries`,
  `--seed-drugs`/`--drugs`, `--jsonl`, `--text`, `--stats`. Verified 254 docs / 430 chunks (dailymed + pubmed).
- **A3 (started)** — `ingest/eval.py` accuracy harness (MedMCQA/PubMedQA via HF datasets-server; retrieval-coverage mode
  runs with no key, answer-accuracy mode with an LLM, optional `--rag`). Retrieval improvement: abbreviation/synonym
  expansion in `kb._fts_query` ("afib"→"atrial fibrillation"). **Remaining A3:** dense/hybrid vectors (sqlite-vec/
  LanceDB on the ingest box, pluggable embedding hook) + run the answer-accuracy eval with a key as the quality gate.
- **B2 ✅** — `backend/app/score.py`: composite **Telomy Score** (7 longevity-weighted domains, each marker scored vs
  its catalog optimal band) + biological age from the best available clock. `/score` + `mobile/src/app/score.tsx`
  (headline ring + bio-age Δ + domain bars, weakest-first) + entry card on `/age`.
- **B3 ✅ (already present)** — the marker detail screen (`mobile/src/app/marker/[id].tsx` ← `/vault/marker/{mid}`)
  already does plain-language `sinc_read`, optimal-band-vs-lab-range on the trend chart, history, and retest prep. No
  rebuild needed; the B2 Score → domain → marker flow now routes into it.
- **B4 ✅** — `backend/app/retest.py` closed loop: per-marker last-tested + next-due (sooner when out of optimal) +
  direction-aware improved/worsened since the previous draw (reuses `engine.marker_history`/`marker_trend`). `/retest`
  + `mobile/src/app/retest.tsx` (due now / improving / moved-wrong-way / schedule) + entry card on the Score screen.

### A2 — remaining (needs the ingest box)
The bulk corpus (PMC-OA commercial subset ~millions of chunks, full DailyMed, India guideline PDFs) is too large to
build or host on the 512 MB prod box. Provision a **separate ingest/index VM** (≥4 vCPU / 16 GB / 100 GB disk):
1. Pull bulk: PMC-OA `oa_comm` packages, MEDLINE baseline, DailyMed full, ClinicalTrials.gov v2, USPSTF/CDC, NIH ODS.
2. India: parse MoHFW/ICMR/CDSCO PDFs → JSONL (the `--jsonl` path), incl. the CDSCO banned-FDC list.
3. Section-aware chunk, dedup (DOI→PMID→PMCID→title-hash), grade+license+region tag → write `knowledge.db` (FTS5).
4. Ship the `.db` artifact to the query box (or expose a `/search` HTTP endpoint from the ingest box).
5. A3: add dense vectors (sqlite-vec/LanceDB) + RRF; stand up MedQA/MedMCQA/MIRAGE eval before shipping.
How to ship/host the KB to prod: set `TELOMY_KB_PATH` to the shipped `.db`; `kb.available()` picks it up; else live fallback.

## Deployment note
`telomy/nextgen` is a development branch — NOT deployed to the fragile Oracle prod box (which runs `main`). nextgen
features are validated by local tests; when a milestone is ready to ship we merge it to `main`, deploy, and rebuild the
app. The KB code is safe on prod regardless (`kb.available()` is False there → live PubMed fallback).
