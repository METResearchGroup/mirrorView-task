# Step 3: Copy the prepared input

## Proposal sections implemented

- "Cross-cutting concerns: Rows and metrics"
- "File structure: S3"
- "Step 3: Copy the prepared input"
- "Confirmed decisions" 2

## Goal

Copy the verified zero-shot Jev records into the new prefix. The record bytes stay the same. The new manifest points at the new records key and keeps the source digest and counts.

Run every command from `/workspace` with `PYTHONPATH=.`.

## Scope

- **Main caller:** `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step1_setup/main.py`, function `main`.
- **Happy path:** `main` calls `copy_prepared_input` with `ZERO_SHOT_VARIANT` as the source and `OPTIMIZED_VARIANT` as the target, then prints one summary line.
- **Unit of work:** one command file that copies an existing input package.
- **Out of scope:** Jev calls, analysis, changes to `copy_prepared_input`, unit tests, and checked-in smoke scripts.

## Files to inspect

- `/workspace/docs/plans/2026-10-04_few_shot_jev_optimized_prompt_c35291/proposal.md`, "Rows and metrics" and "File structure: S3"
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/src/step1_setup/main.py`
- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py`, function `copy_prepared_input`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/config.py`

## Files allowed to change

- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step1_setup/main.py` (new)

## Files forbidden to change

- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/**`
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/**`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/**`
- `/workspace/shared/**`
- Every file that is not the new `main.py`
- Every `tests/` directory, every `test_*.py` file, and every checked-in smoke script

## Contracts

`main` parses no arguments. It calls `apply_lab_aws_credentials_when_unset`, builds a `CampaignObjectStore` for `OPTIMIZED_VARIANT.s3_bucket`, and calls:

```python
copy_prepared_input(store, source=ZERO_SHOT_VARIANT, target=OPTIMIZED_VARIANT)
```

It prints one line in the same field order as `/workspace/experiments/few_shot_jev_inference_2026_10_01/src/step1_setup/main.py`. A second call must fail with `FileExistsError` and must not overwrite either object. Do not reimplement the copy inside the new file.

## Checks

Run this before `main.py` exists. It must fail with `ModuleNotFoundError`. Run it again after the file exists and before the S3 copy. It must print `optimized-jev-setup-import-ok`.

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT
from experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step1_setup.main import main
from experiments.zero_shot_jev_inference_2026_10_01.shared.config import ZERO_SHOT_VARIANT

assert callable(main)
assert OPTIMIZED_VARIANT.input_records_key != ZERO_SHOT_VARIANT.input_records_key
assert OPTIMIZED_VARIANT.input_records_key.startswith(OPTIMIZED_VARIANT.s3_prefix)
print("optimized-jev-setup-import-ok")
PY
```

Confirm the source object, then confirm the target prefix is empty:

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY"
aws s3api head-object --bucket mirrorview-experimental-artifacts --key experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl --region us-east-2 --query ContentLength --output text
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix experiments/few_shot_jev_optimized_prompt_2026_10_04/ --region us-east-2 --query 'length(Contents || `[]`)' --output text
```

The head-object command prints `8516715`. The list command prints `0`. A different length or a nonempty target prefix stops the step.

## Run the copy

```bash
cd /workspace
PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step1_setup.main
```

Expected stdout is exactly:

```text
records_key=experiments/few_shot_jev_optimized_prompt_2026_10_04/inputs/study_2_five_labeler/records.jsonl manifest_key=experiments/few_shot_jev_optimized_prompt_2026_10_04/inputs/study_2_five_labeler/manifest.json rows=13992 unique_post_ids=13992 unanimous_rows=4051 split_rows=9941 sha256=1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395
```

## Verify the copy

```bash
cd /workspace
INPUT_VERIFY_TMP=$(mktemp -d)
export INPUT_VERIFY_TMP
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl "$INPUT_VERIFY_TMP/source.jsonl" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_optimized_prompt_2026_10_04/inputs/study_2_five_labeler/records.jsonl "$INPUT_VERIFY_TMP/target.jsonl" --region us-east-2 --no-progress
cmp "$INPUT_VERIFY_TMP/source.jsonl" "$INPUT_VERIFY_TMP/target.jsonl"
shasum -a 256 "$INPUT_VERIFY_TMP/source.jsonl" "$INPUT_VERIFY_TMP/target.jsonl"
PYTHONPATH=. uv run python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["INPUT_VERIFY_TMP"])
assert root.joinpath("source.jsonl").read_bytes() == root.joinpath("target.jsonl").read_bytes()
print("optimized-jev-input-bytes-ok")
PY
PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step1_setup.main
```

`cmp` exits 0. Both SHA-256 lines start with `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`. The inline check prints `optimized-jev-input-bytes-ok`. The second setup command exits nonzero because the objects already exist, and the existing bytes stay in place.

## Pass and fail

- Pass: the first setup command prints the expected line, the record files compare equal, and the second setup command does not overwrite them.
- Fail: the digest differs, the row counts differ, the target prefix already had objects before the first copy, or any forbidden file changes.
