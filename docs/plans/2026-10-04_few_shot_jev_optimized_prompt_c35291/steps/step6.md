# Step 6: Analyze and report the production run

## Proposal sections implemented

- "Cross-cutting concerns: Rows and metrics"
- "File structure: S3"
- "Step 5: Analyze the run"
- "Expected results"
- "Confirmed decisions" 4

## Goal

Analyze run `study2-jev-optimized-prompt-2026-10-04`. Count human labels and token use on all 13,992 predictions. Leave the five demonstration post ids out of model metrics. Write six analysis objects and fill `RESULTS.md` with the measured scores.

Run every command from `/workspace` with `PYTHONPATH=.`.

## Scope

- **Main caller:** `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step3_analysis/main.py`, function `main`.
- **Happy path:** `main` calls `run_analysis_cli(OPTIMIZED_VARIANT)`, which writes or verifies the six analysis objects and prints one summary line.
- **Unit of work:** one thin analysis command, then one production analysis and one repeat that verifies the same bytes.
- **Out of scope:** new metric math, changes to `run_analysis`, a second model, unit tests, and checked-in smoke scripts.

## Files to inspect

- `/workspace/docs/plans/2026-10-04_few_shot_jev_optimized_prompt_c35291/proposal.md`, "Rows and metrics" and "Expected results"
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/src/step3_analysis/main.py`
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md`, as the table shape only
- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py`, functions `run_analysis_cli` and `_print_success`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/config.py`

## Files allowed to change

- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step3_analysis/main.py` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/RESULTS.md`

## Files forbidden to change

- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/**`
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/**`
- `/workspace/shared/**`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/**`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step1_setup/**`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step2_inference/**`
- Every `tests/` directory, every `test_*.py` file, and every checked-in smoke script

## Contracts

`main` calls `run_analysis_cli(OPTIMIZED_VARIANT)` and contains no metric code. The shared CLI accepts `--run-id` and nothing else.

Human label counts and the usage row use all 13,992 predictions. Split-vote counts use the 9,941 split rows. Model metrics omit these five post ids and no others:

- `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
- `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
- `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
- `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
- `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

The metric row counts are 13,987 all rows, 4,046 unanimous rows, and 9,941 split rows. F1, recall, and precision treat remove as the positive label. The 405 balanced GEPA posts stay in the metric rows.

The six objects are:

- `label_counts.csv`
- `split_remove_vote_counts.csv`
- `model_metrics.csv`
- `usage.csv`
- `results_fragment.md`
- `analysis_manifest.json`

They live under `s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_optimized_prompt_2026_10_04/analysis/study2-jev-optimized-prompt-2026-10-04/`.

`RESULTS.md` keeps the Step 4 smoke measurement and the Step 5 production measurement. It adds the same section headings as `/workspace/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md`. Copy the headings and the column order. Use the measured numbers from this run, not the numbers from that file and not the proposal estimates.

## Checks

Run this before `main.py` exists. It must fail with `ModuleNotFoundError`. After wiring, it must print `optimized-jev-analysis-import-ok`, and `--help` must exit 0 without an AWS call.

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT
from experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step3_analysis.main import main

assert callable(main)
assert len(OPTIMIZED_VARIANT.metric_exclusion_post_ids) == 5
print("optimized-jev-analysis-import-ok")
PY
PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step3_analysis.main --help >/dev/null
```

## Run the analysis twice

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
PYTHONPATH=. /usr/bin/time -p uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step3_analysis.main --run-id study2-jev-optimized-prompt-2026-10-04
PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step3_analysis.main --run-id study2-jev-optimized-prompt-2026-10-04
```

Both calls exit 0 and print:

```text
analysis_prefix=experiments/few_shot_jev_optimized_prompt_2026_10_04/analysis/study2-jev-optimized-prompt-2026-10-04/ input_rows=13992 unanimous_rows=4051 split_rows=9941 models=1 metric_rows=3 artifacts=6
```

`unanimous_rows=4051` is the human-label count. It is not the metric sample size. The second call verifies the same six object bodies and writes nothing new. A changed byte on the second call fails the step.

## Verify the metric sample sizes

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import csv
import io

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT

store = CampaignObjectStore(OPTIMIZED_VARIANT.s3_bucket, region_name="us-east-2")
prefix = f"{OPTIMIZED_VARIANT.s3_prefix}analysis/study2-jev-optimized-prompt-2026-10-04/"
names = (
    "label_counts.csv",
    "split_remove_vote_counts.csv",
    "model_metrics.csv",
    "usage.csv",
    "results_fragment.md",
    "analysis_manifest.json",
)
for name in names:
    stored = store.get(prefix + name)
    assert stored is not None and stored.body
metrics = store.get(prefix + "model_metrics.csv")
rows = list(csv.DictReader(io.StringIO(metrics.body.decode())))
counts = {row["dataset"]: int(row["sample_count"]) for row in rows}
assert counts == {"all": 13987, "unanimous": 4046, "split": 9941}
usage = store.get(prefix + "usage.csv")
usage_rows = list(csv.DictReader(io.StringIO(usage.body.decode())))
assert len(usage_rows) == 1
assert int(usage_rows[0]["predictions"]) == 13992
print("optimized-jev-metric-counts-ok")
PY
```

`_metrics_csv` in `/workspace/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py` writes columns `dataset` and `sample_count`. The dataset values are `all`, `unanimous`, and `split`. The stored USD equals the production input tokens times `0.042 / 1000000`, rounded to 6 decimal places.

## Pass and fail

- Pass: both analysis calls print the summary above, the metric sample sizes are 13,987, 4,046, and 9,941, and `RESULTS.md` shows those sizes with the measured F1, accuracy, recall, precision, tokens, cost, and runtime.
- Fail: a metric row uses 13,992 or 4,051, the second call changes an object, the 405 GEPA posts are removed from the metrics, or any forbidden file changes.
