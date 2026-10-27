# Telomy's own small language model (Sinc) — plan (2026-10-19)

## Principle
The language model never computes health numbers. Engines (sleep fusion, recovery, effect table, Banister,
two-process, risk models) compute; the SLM explains, plans and talks — grounded in those outputs and the Vault.

## Evidence so far
- Small models (≈ 1–4 B) can approach large-model quality on wearable-health tasks after instruction tuning, and run on
  phones with acceptable memory/latency; weak spots: class imbalance, few-shot cases (HealthSLM-Bench, arXiv 2509.07260).
- Fine-tuning shapes behaviour and style; retrieval keeps medical content current — use both.
- Time-series-native models (e.g. OpenTSLM) are reported to beat text-only models on ECG / sleep / activity at ~1 B
  (secondary claim — verify before relying on it).

## Architecture
1. **On device (Cactus, already integrated for speech):** an open-weight 1–2 B instruct model (Qwen/Gemma family —
   licence checked for commercial health use) quantised int4, LoRA-tuned. Offline answers, private by default.
2. **Grounding:** a tool layer exposes engine outputs as JSON (today, nights, recovery contributors, effects with CIs,
   dynamics, labs with status). The prompt carries only what the question needs.
3. **Server fallback:** larger model through the backend for long reports, never with raw identifiers.

## Training data (no real user data without explicit consent)
- The synthetic cohort (backend/sim): 100+ fictional people × 120 days × engine outputs → generated question/answer
  pairs whose every number is copied from engine output (programmatic, then reviewed).
- Telomy clinician-reviewed explanations (evidence.py, catalog notes).
- Refusal / escalation set: red-flag symptoms → "see a doctor now"; never diagnose; never change medication.

## Evaluation (pre-registered, rule 1 of NOOP_STUDY §4)
- Grounding: 100 % of numbers in answers must match the engine JSON (automatic check).
- Safety: red-flag escalation recall ≥ 99 % on a held-out set; zero medication-change advice.
- Helpfulness: blind preference vs the current server Sinc on 200 synthetic-cohort questions.
- On-device: < 2 GB RAM, < 1.5 s to first token on iPhone 13.

## Steps
1. Tool-layer JSON for every engine (exists partly as API endpoints).
2. Generate grounded Q&A from the cohort (needs an LLM — OmniRoute free providers once keys are added; synthetic data only).
3. LoRA fine-tune (needs PyTorch + a GPU or a rented one); export GGUF/Cactus format.
4. Run the evaluation suite above; ship behind a toggle only if every gate passes.
