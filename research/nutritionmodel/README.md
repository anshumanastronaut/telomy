# Telomy Nutrition-Quality Models — trained on Open Food Facts (>1M products)

Source: **Open Food Facts** (openfoodfacts.org, ODbL) — the world's largest open food database.
Streamed the full dump (**4,855,298 products**), kept 13 nutrition columns, NaN-tolerant plausibility →
**2,511,579 usable products**. Two HistGradientBoosting models from the per-100g nutrition panel:

| Model | Target | Trained on | Accuracy | macro-F1 |
|---|---|---:|---:|---:|
| `nutriscore` | Nutri-Score grade A–E (food quality) | **1,030,035** | 0.892 | 0.877 |
| `nova_processing` | NOVA group 1–4 (ultra-processing) | 703,003 | 0.811 | 0.777 |

- **Nutri-Score** clears the 1M-record bar; it largely reproduces OFF's own nutrient formula (a food-
  quality scorer + pipeline validation), framed honestly.
- **NOVA** is the genuinely *learned* signal — processing level isn't a nutrient formula, so estimating
  "how ultra-processed is this?" from the label is real and useful (class-4 ultra-processed F1 0.87).

Reproduce: `train_nutrition.py` (uses the ageclock `.venv`); re-stream with the full `curl | gunzip |
cut` pipeline (raw TSV deleted after training to save disk). Deployed scorer:
`telomy-vision/telomy_vision/food_quality.py::score(nutrients_per_100g)` → Nutri-Score + NOVA + verdict,
so Telomy can grade ANY logged/scanned food from its label and nudge toward better choices.
