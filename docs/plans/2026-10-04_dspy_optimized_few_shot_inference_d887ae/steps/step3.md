# Step 3: Prepare the optimized experiment input

## Proposal sections implemented

- Cross-cutting concerns, Data and S3 isolation
- File structure, S3
- Step 3, Prepare an identical input package

## Scope

- Caller: `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step1_setup/main.py` `main`
- Task: Copy the verified baseline few-shot input bytes into the optimized experiment S3 root and verify the target manifest.
- Out of scope: repository code changes, Bedrock requests, model-run objects, analysis objects, and deletion of any S3 object.

## Files to inspect

- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/docs/plans/2026-10-04_dspy_optimized_few_shot_inference_d887ae/proposal.md`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step1_setup/main.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/config.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/prepare.py`

## Files allowed to change

No repository file may change in this step. The caller may create only these new S3 objects:

- `s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/inputs/study_2_five_labeler/records.jsonl`
- `s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/inputs/study_2_five_labeler/manifest.json`

## Files and objects forbidden to change

- Every repository file
- Every object under `experiments/few_shot_llm_inference_2026_09_30/`
- Every optimized experiment S3 key outside `inputs/study_2_five_labeler/`
- Any existing object under the target prefix

## Source contract

The completed baseline input has these measured properties:

| Property | Value |
| --- | --- |
| Records size | 8,516,715 bytes |
| Records SHA-256 | `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395` |
| Total rows | 13,992 |
| Unanimous rows | 4,051 |
| Split rows | 9,941 |
| First post ID | `bluesky_002eaa517e7af0d595febeab38ffb3c75e3bd04f05d024c3317172f41c8bc7e1` |
| Last post ID | `twitter_2097136116071534748` |

The target records object must be a byte copy. The target manifest changes only the records key while preserving the source digest, dataset names, counts, first post ID, and last post ID.

## Preflight

Run from `/Users/mark/.codex/worktrees/39d9/mirrorview-wt`:

```bash
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
[[ -n "$AWS_ACCESS_KEY_ID" && -n "$AWS_SECRET_ACCESS_KEY" ]]
aws sts get-caller-identity --output json
aws s3api head-object --bucket mirrorview-experimental-artifacts --key experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl --region us-east-2 --query '{ContentLength:ContentLength,ETag:ETag}'
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl - --region us-east-2 --no-progress | shasum -a 256
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/ --region us-east-2 --query 'length(Contents || `[]`)' --output text
```

The head request must report `ContentLength` 8,516,715. The hash command must report `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`. The final command must print `0`. Stop if the target count is nonzero, and do not delete existing objects to make the preflight pass.

## Run setup

```bash
PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step1_setup.main
```

Expected stdout contains one summary with the target records and manifest keys, followed by `rows=13992 unique_post_ids=13992 unanimous_rows=4051 split_rows=9941`.

## Verify the target

```bash
INPUT_VERIFY_DIR=$(mktemp -d)
export INPUT_VERIFY_DIR
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl "$INPUT_VERIFY_DIR/source.jsonl" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/inputs/study_2_five_labeler/records.jsonl "$INPUT_VERIFY_DIR/target.jsonl" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/manifest.json "$INPUT_VERIFY_DIR/source-manifest.json" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/inputs/study_2_five_labeler/manifest.json "$INPUT_VERIFY_DIR/target-manifest.json" --region us-east-2 --no-progress
cmp "$INPUT_VERIFY_DIR/source.jsonl" "$INPUT_VERIFY_DIR/target.jsonl"
shasum -a 256 "$INPUT_VERIFY_DIR/source.jsonl" "$INPUT_VERIFY_DIR/target.jsonl"
PYTHONPATH=. uv run python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["INPUT_VERIFY_DIR"])
source = json.loads((root / "source-manifest.json").read_text())
target = json.loads((root / "target-manifest.json").read_text())
assert source["records_s3_key"] != target["records_s3_key"]
for field in (
    "records_sha256",
    "total_record_count",
    "unanimous_record_count",
    "split_record_count",
    "source_dataset_names",
    "first_post_id",
    "last_post_id",
):
    assert source[field] == target[field]
assert target["records_s3_key"] == "experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/inputs/study_2_five_labeler/records.jsonl"
print("optimized-input-ok rows=13992 unanimous=4051 split=9941")
PY
```

`cmp` must exit 0. Both hash lines must contain the source digest. The final command must print exactly `optimized-input-ok rows=13992 unanimous=4051 split=9941`.

Run the setup caller a second time. It must fail with `FileExistsError` or the existing immutable-write error, and the two target object hashes must remain unchanged.

## Must pass

- Source and target records are byte-identical.
- The target manifest points to the optimized records key and preserves all source identity fields.
- The target prefix contains exactly the two input objects after setup.
- A setup rerun fails without changing either object.

## Must fail

- Missing AWS credentials or inaccessible source objects.
- A nonzero target object count before the first setup run.
- Any source digest, count, first-ID, or last-ID mismatch.
- Any overwrite or deletion attempt.
