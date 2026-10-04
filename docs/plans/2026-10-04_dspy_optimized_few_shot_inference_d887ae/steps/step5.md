# Step 5: Analyze and publish the completed run

## Proposal sections implemented

- Cross-cutting concerns, Models and analysis
- Cross-cutting concerns, Demonstration overlap
- File structure, S3
- Step 5, Analyze and report the run
- Expected results

## Scope

- Caller: `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step3_analysis/main.py` `main`
- Task: Analyze the two completed model folders, verify the five stored analysis artifacts, and publish measured results in `RESULTS.md`.
- Out of scope: new inference, prompt edits, metric changes, cost estimates without a dated source, and changes to existing experiment artifacts.

## Files to inspect

- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/docs/plans/2026-10-04_dspy_optimized_few_shot_inference_d887ae/proposal.md`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/RESULTS.md`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/RESULTS.md`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`

## Files allowed to change

- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/RESULTS.md`

The analysis caller may create or verify these S3 objects below `analysis/study2-dspy-optimized-few-shot-2026-10-04/`:

- `label_counts.csv`
- `split_remove_vote_counts.csv`
- `model_metrics.csv`
- `results_fragment.md`
- `analysis_manifest.json`

## Files and objects forbidden to change

- Every repository file except the optimized experiment `RESULTS.md`
- All prediction, failure, model-run, and prepared-input objects
- Existing baseline few-shot, zero-shot, and DSPy optimization objects
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`

## Preflight

Use the same `OPTIMIZED_RUN_ID` and `OPTIMIZED_RUN_LOG_DIR` from Step 4. Confirm both logs contain `expected=13992 unique_valid_predictions=13992 unresolved_failures=0` and one `real` timing line. Run the Step 1 and Step 2 test files together before analysis:

```bash
PYTHONPATH=. uv run pytest -q \
  experiments/zero_shot_llm_inference_2026_09_30/tests/test_model_selection.py \
  experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/tests/test_prompt_and_config.py
```

The command must report twelve passed tests.

## Run analysis

```bash
PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step3_analysis.main --run-id "$OPTIMIZED_RUN_ID"
```

Expected stdout is one line containing this S3 prefix and these counts:

```text
s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/analysis/study2-dspy-optimized-few-shot-2026-10-04/ input_rows=13992 unanimous_rows=4051 split_rows=9941 models=2 metric_rows=6 artifacts=5 metric_all_rows=13987 metric_unanimous_rows=4046 metric_split_rows=9941 exclusions=5
```

Run the same command again. It must print the same line and verify the existing immutable bytes without adding a sixth analysis object.

## Download and verify the analysis bundle

```bash
ANALYSIS_VERIFY_DIR=$(mktemp -d)
export ANALYSIS_VERIFY_DIR
aws s3 cp "s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/analysis/$OPTIMIZED_RUN_ID/" "$ANALYSIS_VERIFY_DIR/" --recursive --region us-east-2 --no-progress
find "$ANALYSIS_VERIFY_DIR" -maxdepth 1 -type f -print | sort
```

The directory must contain exactly the five allowed filenames. Verify their contents:

```bash
PYTHONPATH=. uv run python - <<'PY'
import csv
import hashlib
import json
import os
from pathlib import Path

from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.shared.config import OPTIMIZED_FEW_SHOT_VARIANT

root = Path(os.environ["ANALYSIS_VERIFY_DIR"])
run_id = os.environ["OPTIMIZED_RUN_ID"]
expected_files = {
    "label_counts.csv",
    "split_remove_vote_counts.csv",
    "model_metrics.csv",
    "results_fragment.md",
    "analysis_manifest.json",
}
assert {path.name for path in root.iterdir() if path.is_file()} == expected_files

with (root / "label_counts.csv").open(newline="") as handle:
    label_rows = list(csv.DictReader(handle))
with (root / "split_remove_vote_counts.csv").open(newline="") as handle:
    vote_rows = list(csv.DictReader(handle))
with (root / "model_metrics.csv").open(newline="") as handle:
    metric_rows = list(csv.DictReader(handle))

assert len(label_rows) == 6
assert len(vote_rows) == 4
assert len(metric_rows) == 6
assert [row["model"] for row in metric_rows] == [
    "amazon_nova_micro",
    "qwen3_32b",
    "amazon_nova_micro",
    "qwen3_32b",
    "amazon_nova_micro",
    "qwen3_32b",
]
assert [int(row["sample_count"]) for row in metric_rows] == [13_987, 13_987, 4_046, 4_046, 9_941, 9_941]
for row in metric_rows:
    confusion_total = sum(int(row[name]) for name in ("true_positive", "false_positive", "true_negative", "false_negative"))
    assert confusion_total == int(row["sample_count"])
    for name in ("f1", "accuracy", "recall", "precision"):
        assert 0.0 <= float(row[name]) <= 1.0

manifest = json.loads((root / "analysis_manifest.json").read_text())
assert manifest["run_id"] == run_id
assert manifest["experiment_name"] == OPTIMIZED_FEW_SHOT_VARIANT.experiment_name
assert manifest["prompt_name"] == OPTIMIZED_FEW_SHOT_VARIANT.prompt_name
assert manifest["prompt_sha256"] == OPTIMIZED_FEW_SHOT_VARIANT.prompt_sha256
assert manifest["metric_exclusion_post_ids"] == list(OPTIMIZED_FEW_SHOT_VARIANT.metric_exclusion_post_ids)
assert [entry["model_folder"] for entry in manifest["model_runs"]] == list(OPTIMIZED_FEW_SHOT_VARIANT.model_folders)

for filename, digest_field in (
    ("label_counts.csv", "label_counts_sha256"),
    ("split_remove_vote_counts.csv", "split_remove_vote_counts_sha256"),
    ("model_metrics.csv", "model_metrics_sha256"),
    ("results_fragment.md", "results_fragment_sha256"),
):
    digest = hashlib.sha256((root / filename).read_bytes()).hexdigest()
    assert digest == manifest[digest_field]
print("optimized-analysis-ok label_rows=6 vote_rows=4 metric_rows=6 artifacts=5")
PY
```

Expected stdout is exactly `optimized-analysis-ok label_rows=6 vote_rows=4 metric_rows=6 artifacts=5`.

## Publish `RESULTS.md`

Use `apply_patch` to replace the Step 2 placeholder. Do not type or recalculate generated table values. Copy the downloaded `results_fragment.md` bytes unchanged after the measured-usage section.

The file must include:

- Title `Study 2 DSPy optimized few-shot keep or remove inference results`
- Production run ID and analysis S3 URI
- Input key, SHA-256, and 13,992, 4,051, and 9,941 row counts
- Prompt name and SHA-256
- The five excluded post IDs and the metric-only exclusion rule
- A statement that each model predicted all 13,992 rows, for 27,984 valid predictions with no unresolved failures
- Nova and Qwen wall time from the Step 4 logs
- Input-token and output-token totals calculated from the stored prediction rows
- Cost only from a linked, dated, model-specific rate source. Otherwise use `Unavailable from the recorded Bedrock response and no documented rate was applied.`
- The downloaded results fragment without edits

After editing, prove that the table section is byte-identical to the stored fragment:

```bash
RESULTS_TABLES_FILE=$(mktemp)
awk '/^## Human label distribution/{copy=1} copy{print}' experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/RESULTS.md > "$RESULTS_TABLES_FILE"
cmp "$ANALYSIS_VERIFY_DIR/results_fragment.md" "$RESULTS_TABLES_FILE"
```

`cmp` must exit 0.

## Final verification

```bash
PYTHONPATH=. uv run pytest -q \
  experiments/zero_shot_llm_inference_2026_09_30/tests/test_model_selection.py \
  experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/tests/test_prompt_and_config.py
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --help >/dev/null
PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --help >/dev/null
PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step2_inference.main --help >/dev/null
git diff --check
git status --short
git diff --name-only
```

The tests must report twelve passed tests. Every help command must exit 0. `git diff --check` must print nothing. Review every changed path against the proposal file tree, and keep unrelated user files out of the commit.

## Must pass

- The two completed model folders contain 27,984 valid predictions and no unresolved failure.
- The analysis bundle has exactly five objects with matching digests, six metric rows, and the confirmed five exclusions.
- Repeated analysis is byte-identical.
- `RESULTS.md` uses stored tables and measured usage.
- Existing zero-shot and baseline few-shot commands and focused tests remain green.

## Must fail

- Any incomplete model folder, unresolved failure, duplicate or unknown post ID, or identity mismatch.
- Any analysis count, sample size, model order, digest, or exclusion mismatch.
- Any hand-edited generated table, unsupported cost, or usage total extrapolated from the smoke run.
- Any change outside the proposal file tree or any mutation of an existing experiment object.

## Commit

Commit the verified `RESULTS.md` separately with a message such as `docs: publish optimized few-shot results`.
