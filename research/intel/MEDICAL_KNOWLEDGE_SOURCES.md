# Medical Knowledge Sources for a Clinical-Evidence RAG + Q&A Engine
### Exhaustive source catalog + a pragmatic ingestion/"training" plan for the Telomy stack

**Honesty flag:** licenses change — re-verify on the source's own page before ingesting/redistributing. The genuinely treacherous ones (NICE, SNOMED/UMLS, DrugBank full, OMIM, StatPearls-NC) are flagged. As of Jan 2026 knowledge.

Legend: 🟢 **INGEST FREELY** (open/PD/CC0/CC-BY, commercial OK) · 🟡 **WITH CARE** (attribution/share-alike/registration/non-commercial/no-bulk-redistribution) · 🔴 **DO NOT COPY** (link out / license).

---

## PART 1 — SOURCE CATALOG

### A. Primary literature / abstracts
- **PubMed/MEDLINE** 🟢 — E-utilities API (we have it) + annual baseline bulk FTP (`ftp.ncbi.nlm.nih.gov/pubmed/baseline`) + daily updates. ~37M citations. Abstracts/metadata free to use+cite (don't republish as your own). Titles/abstracts/MeSH/pub-types(=grade signal)/journal/year. **The citation backbone.**
- **PMC Open Access — Commercial subset** 🟢 — bulk `ftp.ncbi.nlm.nih.gov/pub/pmc/oa_bulk/`; **filter to CC-BY/CC0 ("comm") packages** for a paid product. ~5M+ full-text. **Richest free full-text corpus.**
- **Europe PMC** 🟢 — REST API + bulk; mirrors PubMed+PMC+preprints, has an annotations (NER) API. Best single API for abstracts+OA full text+preprints.
- **Semantic Scholar S2AG/S2ORC** 🟡 — S2AG metadata ODC-BY; S2ORC full-text = OA only, API key + agreement. Citation graph (authority ranking), TLDRs. Filter to biomed.
- **bioRxiv/medRxiv** 🟡 — API + S3; per-paper CC (some all-rights-reserved) → filter CC-BY/CC0; **not peer-reviewed → low grade, label as preprint.**
- **Cochrane full reviews** 🔴 (Wiley). Abstracts/Plain-Language-Summaries are free + in PubMed → ingest the abstracts as high-grade signals, link out for full text.

> Keep our `clinevidence.py` E-utilities client for **live/fresh** lookups (rate-limited: per-query tool, not the corpus). The corpus = PMC-OA bulk + MEDLINE baseline.

### B. Textbooks / encyclopedias / reference
- **StatPearls** (NCBI Bookshelf) 🟡 — ~10k+ peer-reviewed clinical chapters, the "textbook answer." **CC-BY-NC-ND 4.0 → non-commercial + no-derivatives; chunking for a paid product is legally grey.** Safe internal; for commercial, get clarity or link-out. **The single biggest value-vs-license call.**
- **NCBI Bookshelf open books** 🟡 — mixed per-book license; check each (GeneReviews etc.).
- **MSD/Merck Manuals** 🔴 proprietary → alt: StatPearls + MedlinePlus + Wikipedia.
- **Wikipedia (WikiProject Medicine) / Wikidata** 🟢 — CC-BY-SA / CC0; lay synonyms + free entity graph (drug↔disease↔gene, RxNorm/MeSH/ICD xrefs). Tag tertiary/low-grade.
- **MedlinePlus** (NLM) 🟢 PD — patient-education + drug pages; Connect API maps codes→consumer info. Plain-language layer.
- **Gray's Anatomy (1918)** 🟢 PD but dated → anatomy only.
- **WikiDoc** 🟡 CC-BY-SA, variable quality → low-med grade. **Radiopaedia** 🔴 bulk (link-out). **UpToDate/DynaMed/ClinicalKey/BMJ Best Practice** 🔴 proprietary.

### C. Drugs / pharmacology
- **RxNorm** 🟢 — download + RxNav REST API (free); name normalization, brand↔generic, ingredients. **The spine.**
- **RxNav** 🟡 — NLM **discontinued the RxNorm drug-drug *interaction* API in 2024** → use DDInter/openFDA/DrugCentral for interactions. RxClass (ATC/MoA) still free.
- **DailyMed (FDA SPL labels)** 🟢 PD — bulk + REST; full labels (indications/dosing/contraindications/warnings/interactions). **Tier-1 ingest.**
- **openFDA** 🟢 PD — labels + **FAERS** adverse events + recalls/NDC. Label FAERS as "reported, not incidence." *(We now use openFDA + RxNorm live in `drugref.py`.)*
- **DrugBank** 🟡/🔴 — open vocab CC0 🟢; full DB proprietary/paid 🔴.
- **DrugCentral** 🟢 CC-BY-SA — open DrugBank substitute (indications/mechanisms/some interactions).
- **DDInter** 🟡 — free academic (verify commercial); clean DDI w/ severity+mechanism. *(Already in-repo.)*
- **SIDER** 🟡 CC-BY-NC-SA → or derive side-effects from DailyMed/openFDA (PD) yourself.
- **MED-RT** 🟢 (replaces NDF-RT) — MoA/therapeutic-intent ontology.
- **ATC/DDD (WHO)** 🔴/🟡 redistribution restricted → expose via RxClass mappings.
- **ChEMBL** 🟢 CC-BY-SA — bioactivity/mechanisms (optional).
- **India:** **CDSCO** 🟡 (approved drugs, **banned FDC list** — clinically critical, scrape/download), **NPPA** 🟡 (DPCO ceiling prices), **Indian Pharmacopoeia** 🔴 (copyrighted, name only), **Jan Aushadhi** 🟡 (generic list+prices, affordability), **1mg/Netmeds/PharmEasy** 🔴 (scraping = ToS/copyright).

### D. Guidelines
- **USPSTF** 🟢 PD — screening/prevention with explicit A–D/I grades. **Perfect for a graded engine. Tier-1.**
- **CDC / MMWR / schedules** 🟢 PD — public health, ID, immunization. Tier-1.
- **WHO** 🟡 CC-BY-NC-SA 3.0 IGO (non-commercial caveat); Essential Medicines List is clean + structured.
- **NICE** 🔴 — © NICE, commercial reuse prohibited. **DO NOT INGEST. Link out.** (Known trap.)
- **ESC/ACC/AHA/ADA/KDIGO/GOLD/GINA** 🟡 — many published OA in journals (free to read/cite); **society retains copyright → ingest OA version where its license permits (check PMC) else author summary + citation + link.**
- **India:** **ICMR** 🟡 (AMR/antibiotic, diabetes, cancer — PDFs), **MoHFW/NHM Standard Treatment Guidelines** 🟡 (NTEP-TB, NACO-HIV, NPCDCS-NCD, RMNCH — maps to how Indian clinicians practice). **India Tier-1.**

> Treat guidelines as a **separate high-authority layer** with explicit grade metadata. For restricted ones, store your own structured summary + exact citation + link, not verbatim text.

### E. Ontologies / terminologies (entity linking, synonyms, query expansion)
- **MeSH** 🟢 (in PubMed data) · **MONDO** 🟢 CC-BY (disease, xmaps ICD/OMIM/SNOMED) · **HPO** 🟢 (phenotypes→disease, commercial OK) · **ICD-10-CM** 🟢 PD (CMS) · **Orphanet** 🟢 CC-BY · **RxNorm** 🟢 — **build the entity/synonym layer from these (all free + commercial).**
- **LOINC** 🟡 (free registration, redistribution restricted) · **ICD-11** 🟡 (WHO API, registration).
- **SNOMED CT** 🔴 **LICENSE TRAP** — free only in Member countries; **India status unclear/lapsed → likely needs paid affiliate license for commercial.** **UMLS Metathesaurus** 🟡/🔴 — aggregates SNOMED/CPT; doesn't launder their restrictions → use open subset (category 0) only. **Avoid SNOMED/UMLS-SNOMED/CPT in a commercial corpus unless licensed.**

### F. Trials / registries
- **ClinicalTrials.gov** 🟢 PD — new v2 REST API + bulk, ~500k trials.
- **India CTRI** 🟡 (free read, no API) · **WHO ICTRP** 🟡 (aggregates incl. CTRI, bulk on request).

### G. Nutrition / supplements / food
- **USDA FoodData Central** 🟢 PD (likely already have SR Legacy) · **NIH ODS supplement fact sheets** 🟢 PD (graded, referenced — **high value for the supplement/Bonphul angle, Tier-1**) · **DSLD** 🟢 PD (~150k supplement labels) · **IFCT 2017** 🟡 (NIN/ICMR, already in stack — India nutrition).

### H. Genomics
- **ClinVar** 🟢 PD · **PharmGKB** 🟡 CC-BY-SA (PGx, drug↔gene) · **CPIC** 🟢 (gene-based dosing) · **gnomAD** 🟢 (allele freq, TB-scale → summaries only) · **OMIM** 🔴 (commercial license needed → alt MONDO+Orphanet+ClinVar+HPO).

### I. Images / multimodal (lower priority)
- **Open-i** 🟡 (per-image PMC-OA license) · **ROCO/PMC-OA figures** 🟢 · **MIMIC** 🔴 (credentialed + DUA, research env only, never in a public corpus).

---

## PART 2 — "TRAIN IT": WHAT IT MEANS + RECOMMENDED PATH

**Path A — RAG corpus ingestion (retrieve → ground the LLM). ✅ PRIMARY, do this.** Keep Claude as reasoner, give it the right evidence at query time. No GPUs, citations fall out, knowledge stays fresh. OpenEvidence/Vera are fundamentally RAG over a curated literature+guideline corpus — not bespoke pretrained models.

**Path B — fine-tune / use a medical SLM. 🟡 Optional, later, NOT for factual grounding.** Open models: Meditron, BioMistral, OpenBioLLM, MMed/MedLlama. Worth it only as an **on-device/cheap component** (NER to tag chunks, query rewriting, offline triage, cutting Claude token cost) — we already run on-device SLMs. **Fine-tuning does not make a model factually reliable or current and still hallucinates citations → never fine-tune *instead of* RAG for a fact engine.**

### Concrete RAG pipeline for our stack
**Hard constraint:** the 512 MB Oracle box can't host a vector index of millions of chunks, an embedding model, or a vector server. Split the architecture:
```
INGEST/INDEX BOX (new, bigger)              PRODUCTION (512MB Oracle VM)
- download bulk sources                     FastAPI + Claude wrapper
- clean / chunk / dedup            ──ship──▶ - retrieval.py (BM25 today)
- build index artifact + grade tag   index  - queries a read-only index file
- compute embeddings                        - OR calls index box /search over HTTP
```
**Two shapes:** (1) **SQLite FTS5 index file shipped to the box** — dependency-free, memory-mapped, multi-GB index runs fine in 512 MB; a drop-in upgrade from in-process BM25 `retrieval.py`; add BM25 + rank-by-grade. **Start here.** (2) **Separate index/search service with vectors** (sqlite-vec / LanceDB embedded, or Qdrant on the index box) when lexical recall misses paraphrased questions; embeddings via a hosted API (Voyage/OpenAI) or a small CPU model (BGE/GTE-small) on the index box. **Hybrid BM25 + dense + reciprocal-rank fusion** wins on biomedical retrieval (MIRAGE/MedRAG). Never put Qdrant/embeddings on the 512 MB box.

**Chunking:** abstracts = 1 chunk; full-text/StatPearls/guidelines = section-aware ~512–800 tok, 75 overlap, never split a recommendation; drug labels = by SPL section. Prepend a header ("Source | Topic | Section") to every chunk.

**Metadata on every chunk (what makes it *clinical*):** `chunk_id, source, title, section, url, pub_year, pub_type, evidence_grade, license, region(global/india), retrieval_text, display_citation`.

**Evidence grading:** derive from pub_type+source (Graded guideline > SR/meta-analysis > RCT > cohort > case report > preprint > tertiary). **Rank retrieval partly by grade** (`final = retrieval_score × grade_weight`). LLM must cite `[title, year, source]` + show grade per claim; refuse if unsupported.

**Dedup:** DOI→PMID→PMCID→title-hash; MinHash/SimHash for near-dupes; keep full-text over abstract.

**Freshness:** daily PubMed updates + ClinicalTrials v2 + DailyMed deltas → incremental index → ship new `.db`; keep `clinevidence.py` live client as the "latest on X" fallback; quarterly re-pull guideline PDFs + ODS sheets.

**Eval before trusting it:** **MedQA(USMLE), MedMCQA (Indian AIIMS/NEET-PG — directly relevant), PubMedQA, MMLU-med, MIRAGE/MedRAG (the RAG benchmark — tune the retriever), PubMedRS-200, BioASQ.** Build a small internal India eval set mapped to MoHFW STGs.

---

## PART 3 — PRIORITIZED INGESTION ROADMAP

**TIER 1 (ingest now — free, clean, high value):** PMC-OA commercial subset · MEDLINE baseline+daily · DailyMed · openFDA (labels+FAERS) · USPSTF · CDC · NIH ODS supplement sheets · USDA FoodData Central · ontology layer (RxNorm+MeSH+MONDO+HPO+ICD-10-CM+Orphanet, **no SNOMED/UMLS-SNOMED**) · ClinicalTrials.gov · DrugCentral · Wikipedia-med+Wikidata.

**TIER 1-INDIA (parallel — the differentiation):** MoHFW/NHM Standard Treatment Guidelines · ICMR guidelines · CDSCO approved + **banned-FDC** list · IFCT 2017 · Jan Aushadhi + NPPA prices · MedMCQA (eval).

**TIER 2 (soon, with a caveat):** Europe PMC · **StatPearls** (resolve NC-ND/commercial first) · bioRxiv/medRxiv (CC-filtered, low grade) · DDInter · specialty guidelines via PMC-OA · PharmGKB+CPIC · DSLD · S2AG/S2ORC · WHO guidelines+EML · MedlinePlus · ClinVar.

**TIER 3 (later/niche):** ChEMBL/ChEBI · gnomAD summaries · Open-i/ROCO images · S2ORC full bulk · LOINC/ICD-11.

**🔴 DO-NOT-INGEST → open alternative:** UpToDate/DynaMed/ClinicalKey/BMJ/Merck → StatPearls(NC)+PMC-OA+guidelines+MedlinePlus · Cochrane full → Cochrane abstracts(PubMed)+PMC-OA SRs · NICE → USPSTF+CDC+ICMR+MoHFW+OA society · SNOMED/UMLS-SNOMED/CPT → MONDO+HPO+ICD-10-CM+RxNorm+Orphanet+MeSH · DrugBank full → open vocab+DrugCentral+DailyMed+openFDA · OMIM → MONDO+Orphanet+ClinVar+HPO · Indian Pharmacopoeia → CDSCO+DailyMed+RxNorm · 1mg/Netmeds → CDSCO+JanAushadhi+DailyMed · Radiopaedia bulk → Wikipedia+Open-i · MIMIC → research env only.

## Bottom line (5 decisions)
1. **RAG, not fine-tuning** (fine-tune only a small on-device NER/rewrite/triage component later).
2. **Separate ingest/index box; keep the 512 MB VM a thin query layer.** Ship it a **SQLite FTS5 index file** first; add sqlite-vec/LanceDB hybrid on the index box when needed. Never host a vector server/embedding model on the 512 MB box.
3. **Start corpus = Tier-1 + Tier-1-India.**
4. **Every chunk carries source+citation+grade+license+region;** rank partly by grade, filter by license at query time.
5. **Clear 3 license landmines before launch: StatPearls (NC-ND vs commercial), SNOMED/UMLS (India licensing), NICE (do not ingest).**

Files to evolve: `backend/app/retrieval.py` (BM25 → SQLite-FTS5/hybrid), `backend/app/clinevidence.py` (keep as live PubMed fallback).
