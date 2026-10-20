# Telomy — Engineering Handbook

How we build: one longevity platform, several repos, a defined team, and a deep-tech operating cadence.
This is the map every contributor (human or agent) reads first.

## 1. The product in one paragraph
Telomy measures biological aging from inexpensive signals (routine blood panel, body composition,
wearables, meal photos), explains it through an on-device tool-grounded SLM, and runs the clinical
workflow (patients ↔ doctors ↔ centres ↔ platform) end to end. Core principle across every component:
**numbers come from validated models/tables, never from a language model's imagination.**

## 2. Repository map (the monorepo-of-repos)
| Repo / path | Owns | Stack |
|---|---|---|
| `telomy-app/backend` | FastAPI API, multi-tenant care graph, billing, auth, device endpoints | Python, FastAPI, SQLite(WAL) |
| `telomy-app/mobile` | iOS/RN app, native BLE modules (ring/patch), 3D twin, on-device SLM host | React Native, Swift, expo |
| `telomy-app/deploy` | Oracle cloud deploy, nightly backups, keepalive | bash, systemd, Caddy |
| `telomy-app/research/ageclock` | blood aging-clock family + PhenoAge | Python, sklearn (HGB) |
| `telomy-app/research/muscleclock` | muscular-age clock (DXA/grip/anthropometry) | Python, sklearn |
| `telomy-slm` | Telomy-LLX tool-grounded longevity SLM | Qwen2.5, QLoRA, MLX/llama.cpp |
| `telomy-vision` | meal-photo→nutrition, medical-image/report ingestion, genomics annotation | CLIP, USDA/IFCT, pydicom, torchxrayvision |
| `telomy-lab` | signal R&D (ECG/PPG/sleep staging, validation) | Python, Swift |

Trained models live beside their training code; `telomy-slm/assets` and `telomy-vision/assets` carry
the deployable artifacts.

## 3. The team (virtual engineering org — `.claude/agents/`)
Specialists, each with a charter, owned surface, and the skills/plugins they use. Invoke by name for
scoped work; they are the durable org, not one-off spawns.
| Agent | Mandate |
|---|---|
| `ml-research` | aging clocks, SLM, model training/validation, honest benchmarking |
| `data-engineering` | dataset ingestion (NHANES/USDA/IFCT/IndiGenomes), pipelines, feature stores |
| `backend-eng` | FastAPI, tenancy/billing/care-graph, auth & tenant isolation |
| `mobile-eng` | RN app, Swift BLE device modules, on-device model integration |
| `devops-sre` | cloud deploy, backups, monitoring, CI, incident response |
| `clinical-regulatory` | evidence, validation-study design, DPDP/CDSCO, safety guardrails |
| `qa-security` | test strategy, authz/negative tests, security audits |

## 4. Tooling (skills & plugins we operate on)
Enabled: **Engineering** plugin (architecture, system-design, code-review, deploy-checklist,
testing-strategy, tech-debt, incident-response, standup, documentation) and **Data** plugin (analyze,
sql-queries, statistical-analysis, build-dashboard). Recommended to add for the team: a dedicated
**code-review** plugin and **finecomb** security-audit skill (see `/code-review ultra` for deep
multi-agent review on a branch/PR).

## 5. Operating cadence (deep-tech discipline)
1. **Spec before code** — a short design note (use the `system-design`/`architecture` skills) for any
   new model or service; state the honest accuracy target and the dataset.
2. **Reproducible by construction** — every model ships with its training script, dataset provenance,
   held-out metrics and a `results.json`. No metric without a rerun path.
3. **Grounding rule** — user-facing numbers come from a validated model/table with provenance; the SLM
   explains, it does not compute.
4. **Review gate** — `code-review` / `qa-security` on every change touching auth, billing, or a
   clinical output; authz negative tests required for tenant-scoped endpoints.
5. **Honest claims** — benchmarks are stated against the literature; roadmap items gated on data are
   labelled as such. Credibility is the asset.
6. **Guardrails** — no autonomous diagnosis; medicines need a signed Rx; health data stays on-device
   where possible; DPDP/GDPR by default.

## 6. Roadmap (live)
See `research/ageclock/DPR.md §5`. Near-term: cystatin C → blood MAE <8y; wearable-fusion features;
Telomy-LLX fine-tune + on-device export; Indian food recipe DB (IFCT covers ingredients, not dishes);
IndiGenomes-based variant annotation; external validation on Indian cohorts; CDSCO pathway.

## 7. Definition of done
Code reviewed · tests (incl. negative/authz where relevant) · reproducible metrics · provenance
documented · honest claim · guardrails intact · entry added to the relevant repo README/DPR.
