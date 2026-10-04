# Step 6: Analyze and report the complete run

The work implements proposal section "Step 5: Analyze and report the run," "Demonstration overlap," and the analysis part of "Expected results." It adds the thin few-shot analysis caller, runs the shared analysis against the complete production run from Step 5, excludes five prompt demonstrations from model metrics only, finishes `RESULTS.md`, and verifies the final repository and S3 state.

## Caller and scope

- Caller: `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step3_analysis/main.py` calls `run_analysis_cli(FEW_SHOT_VARIANT)`.
- Reusable boundary: `run_analysis_cli(variant: JevInferenceVariant) -> None` in `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py` owns argument parsing, AWS setup, object-store construction, analysis execution, and CLI errors.
- Happy path: validate the complete run, join all 13,992 predictions to prepared rows, build full human and usage tables, remove five exact prompt matches only from metric partitions, create or verify six immutable analysis artifacts, and copy the rendered values into `RESULTS.md`.
- Production run ID: `study2-jev-few-shot-2026-10-01`.
- No unit test file or persistent smoke script is allowed. A failing module run before the wrapper exists, followed by the real CLI and direct S3 assertions, provides the command-level red and green checks.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/proposal.md`, especially "Demonstration overlap," "Data and S3 isolation," "Schema and key interfaces," "Step 5: Analyze and report the run," and "Expected results."
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md`.
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/config.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/render.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`.

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step3_analysis/main.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md`.

## Files forbidden to change

- The reusable analysis implementation. If `run_analysis_cli(FEW_SHOT_VARIANT)` cannot satisfy this step, stop and return to Step 1 instead of patching it here.
- Every file under `/Users/mark/src/work/mirrorview-wt/shared/models/jev/`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/render.py`.
- Every file under `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/`.
- Any file under `tests/`, any `test_*.py` file, and any persistent smoke script.
- The zero-shot Jev S3 prefix, the issue 329 few-shot LLM S3 prefix, and the production run objects from Step 5.
- Local copies of CSV, JSON, JSONL, or rendered-fragment artifacts. They remain in S3.

## Contracts

### Thin caller

`main.py` contains no analysis logic. It imports `FEW_SHOT_VARIANT` and `run_analysis_cli`, then calls `run_analysis_cli(FEW_SHOT_VARIANT)` under the standard `if __name__ == "__main__"` guard. The shared CLI accepts `--run-id`, validates it as one safe path segment, applies lab AWS credentials when standard variables are unset, and creates the object store for the variant's bucket.

### Complete-run gate

Analysis rejects a missing run manifest, any manifest other than `complete`, any unresolved failure, a missing or duplicate prediction, a prediction with the wrong run or model identity, an input digest mismatch, or any run-manifest identity that differs from `FEW_SHOT_VARIANT`. The final run manifest remains the source of prompt name and prompt digests. `JevAnalysisManifest.final_run_manifest_key` points to it; the analysis manifest does not duplicate those prompt fields.

### Five metric-only exclusions

The analysis manifest stores these exact five unique IDs:

1. `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
2. `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
3. `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
4. `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
5. `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

All five must exist in the prepared input and belong to the unanimous partition. The analysis excludes them only while building the three model metric rows. Therefore:

- human label counts describe 13,992 rows and contain six rows;
- split remove-vote counts describe 9,941 rows and contain four rows;
- usage sums all 13,992 predictions and contains one row;
- metric sample counts are 13,987 for all, 4,046 for unanimous, and 9,941 for split;
- the analysis manifest records input counts of 13,992 all, 4,051 unanimous, and 9,941 split, plus the five exclusion IDs.

An exclusion that is missing, duplicated, or outside the unanimous partition is a hard failure. Human counts, split counts, and usage must not change when exclusions are applied.

### Immutable analysis bundle

The analysis prefix contains exactly these six artifact names:

```text
label_counts.csv
split_remove_vote_counts.csv
model_metrics.csv
usage.csv
results_fragment.md
analysis_manifest.json
```

Each absent object is created once. Each existing object must have the same SHA-256 as the newly rendered bytes. A mismatch fails without overwriting anything. Repeating the analysis command against unchanged inputs succeeds and verifies the same six objects.

## Implementation

### 1. Establish the caller-first red check

Before creating `main.py`, run the future public caller once.

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step3_analysis.main --help
```

Expected before implementation: a nonzero exit with `No module named experiments.few_shot_jev_inference_2026_10_01.src.step3_analysis.main`. If the module already exists from an earlier scaffold, inspect it instead and confirm that it contains only a stub or the exact thin caller contract. Do not add a test file to manufacture a failure.

### 2. Add the thin analysis caller

Step 2 already created `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step3_analysis/__init__.py`. Create `main.py` with the exact caller described above. Do not copy argument parsing, S3 access, joins, metric calculations, rendering, or writes into the wrapper.

Run the green import and CLI checks:

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python -m compileall -q \
  /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step3_analysis
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step3_analysis.main --help
```

Expected: both commands exit zero. Help lists the required `--run-id` option and describes one complete Jev Study 2 analysis. No network write occurs.

### 3. Run the read-only production and analysis-prefix preflight

The preflight proves AWS access, a complete production run, exact variant identity, and a safe analysis destination without printing credentials. An existing analysis prefix is allowed because the bundle is create-or-verify.

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
import boto3

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_jev_inference_2026_10_01.shared.schemas import JevRunManifest
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import apply_lab_aws_credentials_when_unset

run_id = "study2-jev-few-shot-2026-10-01"
apply_lab_aws_credentials_when_unset()
boto3.client("sts").get_caller_identity()
store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket)
run_prefix = f"{FEW_SHOT_VARIANT.s3_prefix}runs/{run_id}/jev_1_13_0/"
manifest_keys = [key for key in store.list_keys(run_prefix + "manifests/") if key.endswith(".json")]
assert manifest_keys, "run has no manifest"
stored = store.get(manifest_keys[-1])
assert stored is not None
manifest = JevRunManifest.model_validate_json(stored.body)
assert manifest.status.value == "complete"
assert manifest.requested_record_count == 13_992
assert manifest.completed_prediction_count == 13_992
assert manifest.unresolved_failure_count == 0
assert manifest.experiment_name == FEW_SHOT_VARIANT.experiment_name
assert manifest.prompt_name == FEW_SHOT_VARIANT.prompt_name
assert manifest.prompt_sha256 == FEW_SHOT_VARIANT.prompt_sha256
assert manifest.instructions_sha256 == FEW_SHOT_VARIANT.instructions_sha256
analysis_prefix = f"{FEW_SHOT_VARIANT.s3_prefix}analysis/{run_id}/"
existing = store.list_keys(analysis_prefix)
expected_names = {
    "label_counts.csv",
    "split_remove_vote_counts.csv",
    "model_metrics.csv",
    "usage.csv",
    "results_fragment.md",
    "analysis_manifest.json",
}
expected_keys = {f"{analysis_prefix}{name}" for name in expected_names}
assert set(existing).issubset(expected_keys), existing
state = "new" if not existing else "verify" if len(existing) == 6 else "resume"
print("aws_ok=true run_status=complete predictions=13992 unresolved_failures=0")
print(f"analysis_state={state} existing_objects={len(existing)} prefix=s3://{FEW_SHOT_VARIANT.s3_bucket}/{analysis_prefix}")
PY
```

Expected first line exactly: `aws_ok=true run_status=complete predictions=13992 unresolved_failures=0`. The second line reports `analysis_state=new` for zero objects, `analysis_state=resume` for one through five expected objects, or `analysis_state=verify` for all six. An unexpected object name or any assertion failure is a hard stop.

### 4. Run analysis and repeat it once

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. /usr/bin/time -p uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step3_analysis.main \
  --run-id study2-jev-few-shot-2026-10-01
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step3_analysis.main \
  --run-id study2-jev-few-shot-2026-10-01
```

Expected summary from both invocations:

```text
analysis_prefix=experiments/few_shot_jev_inference_2026_10_01/analysis/study2-jev-few-shot-2026-10-01/ input_rows=13992 unanimous_rows=4051 split_rows=9941 models=1 metric_rows=3 artifacts=6
```

The first run creates missing objects or verifies matching ones. The second run must verify the same bytes and exit zero. A different result on the second call indicates nondeterministic rendering or mutable output and fails the step.

### 5. Verify all six artifacts and their contents

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
import csv
import io

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_jev_inference_2026_10_01.shared.schemas import JevRunManifest
from experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze import JevAnalysisManifest
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    parse_study2_input_jsonl_bytes,
    sha256_hex,
)

run_id = "study2-jev-few-shot-2026-10-01"
expected_names = {
    "label_counts.csv",
    "split_remove_vote_counts.csv",
    "model_metrics.csv",
    "usage.csv",
    "results_fragment.md",
    "analysis_manifest.json",
}
expected_exclusions = (
    "bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7",
    "bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c",
    "bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48",
    "bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b",
    "bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206",
)
apply_lab_aws_credentials_when_unset()
store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket)
prefix = f"{FEW_SHOT_VARIANT.s3_prefix}analysis/{run_id}/"
keys = store.list_keys(prefix)
assert {key.removeprefix(prefix) for key in keys} == expected_names
bodies = {}
for key in keys:
    stored = store.get(key)
    assert stored is not None, key
    bodies[key.removeprefix(prefix)] = stored.body
manifest = JevAnalysisManifest.model_validate_json(bodies["analysis_manifest.json"])
assert manifest.run_id == run_id
assert (manifest.input_row_count, manifest.unanimous_row_count, manifest.split_row_count) == (
    13_992,
    4_051,
    9_941,
)
assert manifest.metric_exclusion_post_ids == expected_exclusions
records_object = store.get(FEW_SHOT_VARIANT.input_records_key)
assert records_object is not None
records_by_id = {
    record.post_id: record for record in parse_study2_input_jsonl_bytes(records_object.body)
}
assert set(expected_exclusions) <= records_by_id.keys()
assert all(records_by_id[post_id].is_unanimous for post_id in expected_exclusions)
run_manifest_object = store.get(manifest.final_run_manifest_key)
assert run_manifest_object is not None, manifest.final_run_manifest_key
run_manifest = JevRunManifest.model_validate_json(run_manifest_object.body)
assert run_manifest.status.value == "complete"
assert run_manifest.completed_prediction_count == 13_992
assert run_manifest.unresolved_failure_count == 0
assert run_manifest.prompt_sha256 == FEW_SHOT_VARIANT.prompt_sha256
assert run_manifest.instructions_sha256 == FEW_SHOT_VARIANT.instructions_sha256
assert manifest.label_count_rows == 6
assert manifest.split_remove_vote_rows == 4
assert manifest.metric_rows == 3
assert manifest.usage_rows == 1
assert manifest.label_counts_sha256 == sha256_hex(bodies["label_counts.csv"])
assert manifest.split_remove_vote_counts_sha256 == sha256_hex(
    bodies["split_remove_vote_counts.csv"]
)
assert manifest.model_metrics_sha256 == sha256_hex(bodies["model_metrics.csv"])
assert manifest.usage_sha256 == sha256_hex(bodies["usage.csv"])
assert manifest.results_fragment_sha256 == sha256_hex(bodies["results_fragment.md"])
label_rows = list(csv.DictReader(io.StringIO(bodies["label_counts.csv"].decode("utf-8"))))
split_rows = list(
    csv.DictReader(io.StringIO(bodies["split_remove_vote_counts.csv"].decode("utf-8")))
)
metric_rows = list(csv.DictReader(io.StringIO(bodies["model_metrics.csv"].decode("utf-8"))))
usage_rows = list(csv.DictReader(io.StringIO(bodies["usage.csv"].decode("utf-8"))))
assert {(row["dataset"], row["label"]): int(row["count"]) for row in label_rows} == {
    ("all", "keep"): 11_024,
    ("all", "remove"): 2_968,
    ("unanimous", "keep"): 3_743,
    ("unanimous", "remove"): 308,
    ("split", "keep"): 7_281,
    ("split", "remove"): 2_660,
}
assert {int(row["remove_votes"]): int(row["count"]) for row in split_rows} == {
    1: 4_244,
    2: 3_037,
    3: 1_777,
    4: 883,
}
assert {row["dataset"]: int(row["sample_count"]) for row in metric_rows} == {
    "all": 13_987,
    "unanimous": 4_046,
    "split": 9_941,
}
assert len(usage_rows) == 1
assert int(usage_rows[0]["predictions"]) == 13_992
assert int(usage_rows[0]["input_tokens"]) > 0
assert manifest.final_run_manifest_key.endswith("/manifests/" + manifest.final_run_manifest_key.rsplit("/", 1)[-1])
print("artifacts=6 label_rows=6 split_rows=4 metric_rows=3 usage_rows=1")
print("metric_samples=13987,4046,9941 usage_predictions=13992 exclusions=5")
print(f"final_run_manifest={manifest.final_run_manifest_key}")
PY
```

Expected first two lines exactly:

```text
artifacts=6 label_rows=6 split_rows=4 metric_rows=3 usage_rows=1
metric_samples=13987,4046,9941 usage_predictions=13992 exclusions=5
```

The third line names the final run manifest. Its object must be the complete manifest verified in Step 5 and contains the prompt identity.

### 6. Complete `RESULTS.md`

Read the immutable rendered fragment without writing a local artifact:

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import apply_lab_aws_credentials_when_unset

run_id = "study2-jev-few-shot-2026-10-01"
apply_lab_aws_credentials_when_unset()
store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket)
key = f"{FEW_SHOT_VARIANT.s3_prefix}analysis/{run_id}/results_fragment.md"
stored = store.get(key)
assert stored is not None, key
print(stored.body.decode("utf-8"), end="")
PY
```

Edit `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md` so it contains:

- the production run ID and analysis S3 prefix;
- the measured smoke and production runtime, token, and cost records;
- all six human label rows and all four split-vote rows;
- the three model metric rows with sample counts 13,987, 4,046, and 9,941;
- the one usage row for all 13,992 predictions;
- a direct statement that the five prompt demonstrations are excluded only from metrics.

Copy measured values from the fragment and verified usage output. Do not manually recalculate rounded metrics and do not leave estimates in place of available measurements.

### 7. Verify the final working tree

Run syntax, caller, and whitespace checks before staging:

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python -m compileall -q \
  /Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01 \
  /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step1_setup.main --help
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step2_inference.main --help
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step3_analysis.main --help
git -C /Users/mark/src/work/mirrorview-wt diff --check
```

Expected: compile and all three help commands exit zero, and `git diff --check` prints nothing.

### 8. Stage exact files and commit

```bash
git -C /Users/mark/src/work/mirrorview-wt add -- \
  /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step3_analysis/main.py \
  /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
git -C /Users/mark/src/work/mirrorview-wt diff --cached --check
git -C /Users/mark/src/work/mirrorview-wt diff --cached --name-only
git -C /Users/mark/src/work/mirrorview-wt commit -m "Analyze few-shot Jev results"
```

Expected staged paths:

```text
experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
experiments/few_shot_jev_inference_2026_10_01/src/step3_analysis/main.py
```

Do not use `git add .`. The worktree may contain unrelated user files.

### 9. Verify the committed PR content

Run the PR scope and no-test-file check after the Step 6 commit so the comparison includes every implementation step:

```bash
git -C /Users/mark/src/work/mirrorview-wt diff --check origin/main...HEAD
PYTHONPATH=. uv run python - <<'PY'
import subprocess
from pathlib import PurePosixPath

repo = "/Users/mark/src/work/mirrorview-wt"
changed = subprocess.run(
    ["git", "-C", repo, "diff", "--name-only", "origin/main...HEAD"],
    check=True,
    capture_output=True,
    text=True,
).stdout.splitlines()
allowed_zero_shot = {
    "experiments/zero_shot_jev_inference_2026_10_01/shared/config.py",
    "experiments/zero_shot_jev_inference_2026_10_01/shared/constants.py",
    "experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py",
    "experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py",
    "experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py",
    "experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py",
    "experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py",
    "experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py",
}
allowed_prefix = "experiments/few_shot_jev_inference_2026_10_01/"
assert changed, "implementation diff is empty"
for path in changed:
    item = PurePosixPath(path)
    assert item.suffix in {".py", ".md"}, path
    assert not item.name.startswith("test_"), path
    assert "tests" not in item.parts, path
    assert path in allowed_zero_shot or path.startswith(allowed_prefix), path
print(f"pr_scope_ok=true changed_files={len(changed)} python_or_markdown_only=true test_files=0")
PY
```

Expected: `git diff --check` prints nothing, and the final command prints `pr_scope_ok=true changed_files=<positive integer> python_or_markdown_only=true test_files=0`. If the implementation follows a separate PR after the plan PR is merged, plan files are unchanged and do not appear in this diff.

## Pass and fail criteria

Pass only when all of the following are true:

- `main.py` is only the `run_analysis_cli(FEW_SHOT_VARIANT)` caller;
- both analysis invocations produce and verify the same six immutable objects;
- human counts, split counts, and usage cover all 13,992 predictions;
- only model metrics exclude the five exact demonstration IDs;
- metric sample counts are exactly 13,987, 4,046, and 9,941;
- the analysis manifest stores the five exclusions and points to the complete run manifest that stores prompt identity;
- `RESULTS.md` contains measured run identity, distributions, metrics, and usage;
- the PR contains only allowed Python and Markdown files and contains no test file;
- commit `Analyze few-shot Jev results` exists.

Fail and stop when the production run is incomplete, an exclusion invariant fails, an analysis object differs, repeated analysis is nondeterministic, `RESULTS.md` does not match stored artifacts, a forbidden file changed, or any final verification command fails.
