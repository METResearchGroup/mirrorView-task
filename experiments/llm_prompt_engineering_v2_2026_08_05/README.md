# LLM prompt engineering v2

Same as [v1](../llm_prompt_engineering_2026_08_05/README.md), except:

- 1,000-post evaluation subset (500 keep + 500 remove, seed 42)
- Model: `qwen/qwen3.6-plus` (research_tools / Bedrock)
- Logic imported from v1; only subset policy, defaults, and paths differ here

## Commands

Freeze the balanced subset:

```bash
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/build_subset.py
```

Smoke both arms on 5 rows (Bedrock AWS credentials required). Review metrics, then approve before production:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py \
  --arm both --limit 5 --model qwen/qwen3.6-plus
```

Production (full 1000 × both arms; only after smoke approval):

```bash
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py \
  --arm both --model qwen/qwen3.6-plus
```

Score one arm or write the two-row RESULTS table:

```bash
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py \
  --run-dir experiments/llm_prompt_engineering_v2_2026_08_05/outputs/control/outputs/<TS>

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py \
  --control-run-dir experiments/llm_prompt_engineering_v2_2026_08_05/outputs/control/outputs/<TS> \
  --tuned-run-dir experiments/llm_prompt_engineering_v2_2026_08_05/outputs/tuned/outputs/<TS> \
  --model qwen/qwen3.6-plus \
  --write-results experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md
```

Positive class for precision / recall / F1 is remove (`keep_remove_label=1`). See [RESULTS.md](RESULTS.md) after the production run.

Collapse per-item `NNNNN_*.json` files in a run folder into `predictions.jsonl` (then delete the per-item files; leaves `metadata.json`):

```bash
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/consolidate_predictions.py

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/consolidate_predictions.py \
  --run-dir experiments/llm_prompt_engineering_v2_2026_08_05/outputs/control/outputs/<TS>
```
