# Follow-up Model Error Analysis — LLM Feature Extraction (2026-07-15)

V1 pilot: extract interpretable linguistic features from Study 2 posts where Bedrock Qwen3 Next 80B is right vs wrong (especially false-positive removes).

**Default scope = V1 (20 extraction calls).** Do not run V2 (~552 calls, ~$140) without explicit cost approval.

## Quick start

```bash
# Phase 1 — confusion splits
PYTHONPATH=. uv run python experiments/followup_model_error_analysis_2026_07_15/split/split_confusion.py

# Phase 2 — V1 extraction (max 20 calls; skips existing batch CSVs)
PYTHONPATH=. uv run python experiments/followup_model_error_analysis_2026_07_15/extract/extract_features.py

# Dry-run budget only
PYTHONPATH=. uv run python experiments/followup_model_error_analysis_2026_07_15/extract/extract_features.py --dry-run

# Phase 3 — text mining + clustering (V1 feature subset)
PYTHONPATH=. uv run python experiments/followup_model_error_analysis_2026_07_15/analyze/text_mining.py
PYTHONPATH=. uv run python experiments/followup_model_error_analysis_2026_07_15/analyze/cluster_features.py

# Phase 4 — RESULTS.md
PYTHONPATH=. uv run python experiments/followup_model_error_analysis_2026_07_15/analyze/synthesize.py
```

Requires `OPENAI_API_KEY` via repo `.env` (`lib/load_env_vars.py`). Primary model: `gpt-5.5`.

See `spec.md` for full design, `progress.md` for run log, `RESULTS.md` for findings, and `DETAILED_RESULTS.md` for V1 example pairs + finer pattern taxonomy.
