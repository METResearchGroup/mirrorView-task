# Step 5: Run, analyze, and publish the experiment

## Proposal sections implemented

- Step 4: Run the four model folders
- Step 5: Analyze and report the run
- Expected results
- Confirmed decisions

## Scope

- **Caller:** The three few-shot command modules, in setup, inference, and analysis order
- **Task:** Run the complete four-model experiment, confirm deterministic resume and analysis, publish `RESULTS.md`, and perform final repository and S3 checks.
- **Out of scope:** New pipeline behavior, manual metric edits, model-response normalization, and unit tests.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_llm_inference_1e0d2d/proposal.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/SETUP.md`
- The few-shot S3 input, smoke run, production run, and analysis prefixes

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/RESULTS.md` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/README.md`, only if its links do not match the final files
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/SETUP.md`, only if its commands do not match the final callers

## Files forbidden to change

- All Python files unless a failed check sends the work back to the owning implementation step
- All zero-shot repository files and S3 objects
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/REPORT.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py`
- Every `tests/` directory and every new test file
- Generated predictions, failures, manifests, CSVs, fragments, or logs in Git

## Preconditions

Steps 1 through 4 pass. The few-shot input is verified. All four smoke calls completed with one valid prediction and no unresolved failure. Do not use the smoke run ID for production because its stored configured limit is 1.

Map AWS credentials and set fixed run variables:

```bash
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY"
export RUN_ID=study2-few-shot-2026-10-01
RUN_LOG_DIR=/tmp/mirrorview-few-shot-logs
mkdir -p "$RUN_LOG_DIR"
```

## Complete inference callers

Start one process per model. Each process owns only its model folder. Capture wall time and stdout in its log.

```bash
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$RUN_ID" --model amazon_nova_micro; } >"$RUN_LOG_DIR/amazon_nova_micro.log" 2>&1 &
AMAZON_PID=$!
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$RUN_ID" --model qwen3_32b; } >"$RUN_LOG_DIR/qwen3_32b.log" 2>&1 &
QWEN_PID=$!
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$RUN_ID" --model openai_gpt_5_6_terra; } >"$RUN_LOG_DIR/openai_gpt_5_6_terra.log" 2>&1 &
OPENAI_PID=$!
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$RUN_ID" --model claude_sonnet_5_5; } >"$RUN_LOG_DIR/claude_sonnet_5_5.log" 2>&1 &
CLAUDE_PID=$!

wait "$AMAZON_PID"; AMAZON_STATUS=$?
wait "$QWEN_PID"; QWEN_STATUS=$?
wait "$OPENAI_PID"; OPENAI_STATUS=$?
wait "$CLAUDE_PID"; CLAUDE_STATUS=$?
test "$AMAZON_STATUS" -eq 0 && test "$QWEN_STATUS" -eq 0 && test "$OPENAI_STATUS" -eq 0 && test "$CLAUDE_STATUS" -eq 0
rg -n "expected=13992 unique_valid_predictions=13992 unresolved_failures=0|^real " "$RUN_LOG_DIR"/*.log
```

All four waits and the combined status check must exit 0. Each log contains the correct model identity and this summary before its final `real`, `user`, and `sys` timing lines:

```text
expected=13992 unique_valid_predictions=13992 unresolved_failures=0
```

If one process fails, rerun only that model with the identical production run ID and command. Resume must retain immutable completed batches. Do not analyze until each folder has 13,992 unique known post IDs, no duplicates or extras, the approved input and prompt digests, and no unresolved failure.

Run all four production commands once more after completion:

```bash
FULL_PREFIX="experiments/few_shot_llm_inference_2026_09_30/runs/$RUN_ID/"
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix "$FULL_PREFIX" --region us-east-2 --query 'sort_by(Contents[?contains(Key, `/predictions/`) || contains(Key, `/failures/`)],&Key)[].Key' --output text > /tmp/few-shot-full-keys-before.txt
for model in amazon_nova_micro qwen3_32b openai_gpt_5_6_terra claude_sonnet_5_5; do
  PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$RUN_ID" --model "$model"
done
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix "$FULL_PREFIX" --region us-east-2 --query 'sort_by(Contents[?contains(Key, `/predictions/`) || contains(Key, `/failures/`)],&Key)[].Key' --output text > /tmp/few-shot-full-keys-after.txt
cmp /tmp/few-shot-full-keys-before.txt /tmp/few-shot-full-keys-after.txt
```

Each command reports `expected=13992 unique_valid_predictions=13992 unresolved_failures=0`. `cmp` exits 0, which proves resume added no prediction or failure batch. The artifact check below confirms 55,968 predictions across the four folders.

## Analysis caller

```bash
PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step3_analysis.main --run-id "$RUN_ID"
```

Expected stdout includes the few-shot analysis URI and:

```text
input_rows=13992 unanimous_rows=4051 split_rows=9941 models=4 metric_rows=12 artifacts=5
```

If the success line includes metric partition details, they must be `metric_all_rows=13987 metric_unanimous_rows=4046 metric_split_rows=9941 exclusions=5`.

Capture the five object hashes, run analysis a second time, and compare:

```bash
ANALYSIS_URI="s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/analysis/$RUN_ID"
for name in label_counts.csv split_remove_vote_counts.csv model_metrics.csv results_fragment.md analysis_manifest.json; do
  aws s3 cp "$ANALYSIS_URI/$name" - --region us-east-2 --no-progress | shasum -a 256
done > /tmp/few-shot-analysis-hashes-before.txt
PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step3_analysis.main --run-id "$RUN_ID"
for name in label_counts.csv split_remove_vote_counts.csv model_metrics.csv results_fragment.md analysis_manifest.json; do
  aws s3 cp "$ANALYSIS_URI/$name" - --region us-east-2 --no-progress | shasum -a 256
done > /tmp/few-shot-analysis-hashes-after.txt
cmp /tmp/few-shot-analysis-hashes-before.txt /tmp/few-shot-analysis-hashes-after.txt
```

The second analysis command prints the same success summary, and `cmp` exits 0.

## Artifact checks

Download the five analysis objects to a temporary directory outside the repository:

```bash
ANALYSIS_TMP=$(mktemp -d)
export ANALYSIS_TMP
aws s3 cp "s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/analysis/$RUN_ID/" "$ANALYSIS_TMP/" --recursive --region us-east-2 --no-progress
find "$ANALYSIS_TMP" -maxdepth 1 -type f -print | sort
```

The final command lists exactly `analysis_manifest.json`, `label_counts.csv`, `model_metrics.csv`, `results_fragment.md`, and `split_remove_vote_counts.csv` under the temporary directory.

Run this exact check from the repository root:

```bash
PYTHONPATH=. uv run python - <<'PY'
import csv
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT

root = Path(os.environ["ANALYSIS_TMP"])
run_id = os.environ["RUN_ID"]
label_rows = list(csv.DictReader((root / "label_counts.csv").open()))
vote_rows = list(csv.DictReader((root / "split_remove_vote_counts.csv").open()))
metric_rows = list(csv.DictReader((root / "model_metrics.csv").open()))
manifest = json.loads((root / "analysis_manifest.json").read_text())

expected_labels = {
    ("all", "keep"): 11_024,
    ("all", "remove"): 2_968,
    ("unanimous", "keep"): 3_743,
    ("unanimous", "remove"): 308,
    ("split", "keep"): 7_281,
    ("split", "remove"): 2_660,
}
assert len(label_rows) == 6
assert {(row["dataset"], row["label"]): int(row["count"]) for row in label_rows} == expected_labels
for row in label_rows:
    expected_total = {"all": 13_992, "unanimous": 4_051, "split": 9_941}[row["dataset"]]
    assert int(row["dataset_total"]) == expected_total
    assert abs(float(row["proportion"]) - int(row["count"]) / expected_total) < 1e-12
assert len(vote_rows) == 4
assert {int(row["remove_votes"]): int(row["count"]) for row in vote_rows} == {1: 4_244, 2: 3_037, 3: 1_777, 4: 883}
for row in vote_rows:
    assert int(row["split_total"]) == 9_941
    assert abs(float(row["proportion"]) - int(row["count"]) / 9_941) < 1e-12

sample_counts = {"all": 13_987, "unanimous": 4_046, "split": 9_941}
model_order = ["amazon_nova_micro", "qwen3_32b", "openai_gpt_5_6_terra", "claude_sonnet_5_5"]
model_ids = {
    "amazon_nova_micro": "us.amazon.nova-micro-v1:0",
    "qwen3_32b": "qwen.qwen3-32b-v1:0",
    "openai_gpt_5_6_terra": "us.openai.gpt-5.6-terra",
    "claude_sonnet_5_5": "us.anthropic.claude-sonnet-5-5",
}
expected_order = [(dataset, model) for dataset in ("all", "unanimous", "split") for model in model_order]
assert len(metric_rows) == 12
assert [(row["dataset"], row["model"]) for row in metric_rows] == expected_order
for row in metric_rows:
    sample_count = int(row["sample_count"])
    assert sample_count == sample_counts[row["dataset"]]
    tp, fp, tn, fn = (int(row[name]) for name in ("true_positive", "false_positive", "true_negative", "false_negative"))
    assert tp + fp + tn + fn == sample_count
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / sample_count
    for name, expected in (("precision", precision), ("recall", recall), ("f1", f1), ("accuracy", accuracy)):
        assert 0.0 <= float(row[name]) <= 1.0
        assert abs(float(row[name]) - expected) < 1e-12

assert manifest["experiment_name"] == FEW_SHOT_VARIANT.experiment_name
assert manifest["prompt_name"] == FEW_SHOT_VARIANT.prompt_name
assert manifest["prompt_sha256"] == FEW_SHOT_VARIANT.prompt_sha256
assert tuple(manifest["metric_exclusion_post_ids"]) == FEW_SHOT_VARIANT.metric_exclusion_post_ids
analysis_prefix = f"{FEW_SHOT_VARIANT.s3_root}analysis/{run_id}/"
for field, filename in (
    ("label_counts_s3_key", "label_counts.csv"),
    ("split_remove_vote_counts_s3_key", "split_remove_vote_counts.csv"),
    ("model_metrics_s3_key", "model_metrics.csv"),
    ("results_fragment_s3_key", "results_fragment.md"),
    ("analysis_manifest_s3_key", "analysis_manifest.json"),
):
    assert manifest[field] == analysis_prefix + filename
fragment_digest = hashlib.sha256((root / "results_fragment.md").read_bytes()).hexdigest()
assert fragment_digest == manifest["results_fragment_sha256"]
for filename, field in (
    ("label_counts.csv", "label_counts_sha256"),
    ("split_remove_vote_counts.csv", "split_remove_vote_counts_sha256"),
    ("model_metrics.csv", "model_metrics_sha256"),
):
    assert hashlib.sha256((root / filename).read_bytes()).hexdigest() == manifest[field]

store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket, region_name="us-east-2")
run_prefix = f"{FEW_SHOT_VARIANT.s3_root}runs/{run_id}/"
usage = defaultdict(lambda: {"predictions": 0, "input_tokens": 0, "output_tokens": 0})
post_ids = defaultdict(set)
for key in store.list_keys(run_prefix):
    if "/predictions/" not in key or not key.endswith(".jsonl"):
        continue
    model_folder = key.split("/")[-3]
    stored = store.get(key)
    assert stored is not None
    for line in stored.body.decode("utf-8").splitlines():
        row = json.loads(line)
        assert row["schema_version"] == FEW_SHOT_VARIANT.prediction_schema_version
        assert row["run_id"] == run_id and row["model_folder"] == model_folder
        assert row["model_id"] == model_ids[model_folder]
        assert row["post_id"] not in post_ids[model_folder]
        post_ids[model_folder].add(row["post_id"])
        assert row["usage"]["total_tokens"] == row["usage"]["input_tokens"] + row["usage"]["output_tokens"]
        usage[model_folder]["predictions"] += 1
        usage[model_folder]["input_tokens"] += row["usage"]["input_tokens"]
        usage[model_folder]["output_tokens"] += row["usage"]["output_tokens"]
assert set(usage) == set(model_order)
assert all(values["predictions"] == 13_992 for values in usage.values())
assert all(len(ids) == 13_992 for ids in post_ids.values())
Path("/tmp/few-shot-usage.json").write_text(json.dumps(usage, indent=2, sort_keys=True) + "\n")
print("usage_totals=" + json.dumps(usage, sort_keys=True))
print("analysis-artifacts-ok predictions=55968 metrics=12 artifacts=5")
PY
```

The first output line records the measured per-model prediction and token totals for `RESULTS.md`. The second line is exactly `analysis-artifacts-ok predictions=55968 metrics=12 artifacts=5`.

The check proves:

- `label_counts.csv` has 6 data rows. All keep/remove counts are 11,024/2,968; unanimous counts are 3,743/308; split counts are 7,281/2,660.
- `split_remove_vote_counts.csv` has 4 data rows with counts 4,244, 3,037, 1,777, and 883 in vote-count order.
- `model_metrics.csv` has 12 ordered data rows. Every model has sample counts 13,987 all, 4,046 unanimous, and 9,941 split. Each confusion-matrix sum equals its sample count, each metric is in `[0, 1]`, and remove is the positive class.
- `analysis_manifest.json` has the few-shot experiment and prompt identity and the exact five exclusion IDs in configured order.
- `results_fragment.md` matches its digest in the analysis manifest.

## Publish `RESULTS.md`

Build `RESULTS.md` from the stored `results_fragment.md`. Prepend a fixed title and a short run-identity section. Do not manually copy or edit generated table values. Include:

- Production run ID and analysis S3 URI
- Input records key, SHA-256, and 13,992/4,051/9,941 counts
- Prompt name and SHA-256
- The exact five excluded post IDs and the metric-only exclusion rule
- The generated human-label, split-vote, and model-metric tables
- Per-model measured full-run wall time, input-token total, and output-token total
- Per-model cost only when calculated from a linked, dated, model-specific rate source. Otherwise write `Unavailable from the recorded Bedrock response and no documented rate was applied.`
- A note that the complete run stored 55,968 valid predictions and no unresolved failures

Token totals come from the stored prediction records, not estimates. Runtime comes from the captured logs. Do not infer production totals from the one-record smoke runs.

Generate the file from those measured inputs and the downloaded fragment:

```bash
export RUN_LOG_DIR
PYTHONPATH=. uv run python - <<'PY'
import json
import os
from pathlib import Path

from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT

models = ["amazon_nova_micro", "qwen3_32b", "openai_gpt_5_6_terra", "claude_sonnet_5_5"]
usage = json.loads(Path("/tmp/few-shot-usage.json").read_text())
log_dir = Path(os.environ["RUN_LOG_DIR"])
runtime = {}
for model in models:
    real_lines = [line for line in (log_dir / f"{model}.log").read_text().splitlines() if line.startswith("real ")]
    assert len(real_lines) == 1
    runtime[model] = float(real_lines[0].split()[1])

exclusions = "\n".join(f"- `{post_id}`" for post_id in FEW_SHOT_VARIANT.metric_exclusion_post_ids)
usage_rows = "\n".join(
    f"| `{model}` | {runtime[model]:.2f} | {usage[model]['input_tokens']} | {usage[model]['output_tokens']} | Unavailable from the recorded Bedrock response and no documented rate was applied. |"
    for model in models
)
fragment = (Path(os.environ["ANALYSIS_TMP"]) / "results_fragment.md").read_text()
body = f"""# Study 2 few-shot keep or remove inference results

Run ID: `{os.environ['RUN_ID']}`

Analysis: `s3://{FEW_SHOT_VARIANT.s3_bucket}/{FEW_SHOT_VARIANT.s3_root}analysis/{os.environ['RUN_ID']}/`

Input: `{FEW_SHOT_VARIANT.input_records_s3_key}` with SHA-256 `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`. It contains 13,992 rows: 4,051 unanimous and 9,941 split.

Prompt: `{FEW_SHOT_VARIANT.prompt_name}` with SHA-256 `{FEW_SHOT_VARIANT.prompt_sha256}`.

All 13,992 rows were predicted for each model. Model metrics alone exclude these five prompt-demonstration matches:

{exclusions}

The run stored 55,968 valid predictions and no unresolved failures.

## Measured usage

| Model folder | Wall time, seconds | Input tokens | Output tokens | Cost |
| --- | ---: | ---: | ---: | --- |
{usage_rows}

{fragment}"""
output = Path("experiments/few_shot_llm_inference_2026_09_30/RESULTS.md")
output.write_text(body if body.endswith("\n") else body + "\n")
print(output)
PY
```

Expected stdout is `experiments/few_shot_llm_inference_2026_09_30/RESULTS.md`. Compare every generated table in that file with the downloaded `results_fragment.md`; they must be byte-identical.

## Final repository checks

```bash
git diff --check
git status --short
git diff --name-only
rg -n "pytest|tests/test_|unittest" docs/plans/2026-10-01_study_2_few_shot_llm_inference_1e0d2d experiments/few_shot_llm_inference_2026_09_30
PYTHONPATH=. uv run python - <<'PY'
import subprocess

tracked = set(subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines())
untracked = set(subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], text=True).splitlines())
changed = tracked | untracked
assert not any("/tests/" in f"/{path}/" or path.startswith("tests/") or "/test_" in f"/{path}" for path in changed)
assert "experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py" not in changed
assert "experiments/zero_shot_llm_inference_2026_09_30/REPORT.md" not in tracked
assert "experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py" not in tracked
assert not any(path.startswith(("data_platform/", "shared/")) for path in tracked)
assert not ({"pyproject.toml", "uv.lock"} & tracked)
few_files = {path for path in changed if path.startswith("experiments/few_shot_llm_inference_2026_09_30/")}
assert few_files and all(path.endswith((".py", ".md")) for path in few_files)
print("repository-scope-ok")
PY
```

`git diff --check` prints nothing and exits 0. Review `git status` without changing unrelated user files. `git diff --name-only` must not include the zero-shot renderer, zero-shot documentation, user untracked zero-shot files, `data_platform/`, repo-level `shared/`, `pyproject.toml`, `uv.lock`, or a test file. The `rg` command may match the plan's explicit prohibition but must not identify an added test file or a pytest command. The final command prints exactly `repository-scope-ok`.

## Must pass

- Four production model folders contain 13,992 valid predictions each and no unresolved failure.
- Resume and repeated analysis are deterministic and do not overwrite differing immutable objects.
- The four payload digests match the analysis manifest, and all five analysis objects pass their count, identity, key, and metric checks.
- `RESULTS.md` is traceable to stored artifacts and measured usage.
- Repository scope matches the proposal and no unit test exists.

## Must fail

- Any incomplete model, invalid response, unresolved failure, duplicate or unknown post ID, or identity mismatch.
- Any analysis count, metric sample size, digest, or exclusion mismatch.
- A generated table edited by hand, a cost inferred without a dated rate source, or a production total extrapolated from smoke data.
- Any change to a forbidden file or existing zero-shot S3 object.

## Commit

After every check passes, commit the allowed documentation with a message such as `docs: record few-shot Study 2 results`.
