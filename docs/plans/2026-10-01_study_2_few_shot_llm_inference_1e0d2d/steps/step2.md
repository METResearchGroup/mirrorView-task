# Step 2: Add few-shot setup and copy the input

## Proposal sections implemented

- Cross-cutting concerns: Prompt identity and demonstration overlap
- Cross-cutting concerns: Data and S3 isolation
- File structure
- Step 2: Add the few-shot prompt and thin entry points
- Step 3: Prepare an identical input package

## Scope

- **Caller:** `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step1_setup/main.py` `main`
- **Task:** Add the exact issue 329 prompt and few-shot configuration, expose reusable setup and byte-copy functions, add the experiment documentation scaffold, and create the verified few-shot input package in S3.
- **Out of scope:** Bedrock inference, analysis output, final results, and unit tests.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_llm_inference_1e0d2d/proposal.md`
- [Issue 329](https://github.com/METResearchGroup/mirrorView-task/issues/329), for the exact prompt
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/prepare.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/SETUP.md`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/prepare.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/README.md` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/SETUP.md` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/__init__.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/config.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/prompts.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step1_setup/__init__.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step1_setup/main.py` (new)

## Files forbidden to change

- All zero-shot files not listed above
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/RESULTS.md` until Step 5
- `/Users/mark/src/work/mirrorview-wt/data_platform/`
- `/Users/mark/src/work/mirrorview-wt/shared/`
- Every `tests/` directory and every new test file
- All existing zero-shot S3 objects

## Prompt and configuration contract

Copy the prompt from issue 329 exactly, without a final newline after `Allow Or Remove?`. Preserve all ten demonstrations, their order, their labels, the two placeholders, spacing, punctuation, and line breaks. Name it `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT`. Its UTF-8 SHA-256 must be `ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3`. The formatter substitutes only the two post placeholders.

Define `FEW_SHOT_VARIANT` with:

- Bucket `mirrorview-experimental-artifacts`
- Root `experiments/few_shot_llm_inference_2026_09_30/`
- Prediction schema `study2-few-shot-prediction-v1`
- Failure schema `study2-few-shot-failure-v1`
- Model-run schema `study2-few-shot-model-run-v1`
- Analysis schema `study2-few-shot-analysis-v1`
- The prompt name, approved prompt digest, and these five exclusion IDs:
  - `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
  - `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
  - `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
  - `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
  - `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

`README.md` must contain only a title and links to `SETUP.md` and `RESULTS.md`. `SETUP.md` covers required data, the four model folders, expected counts, and S3 locations. Environment setup and run commands remain outside `SETUP.md`.

## Setup contract

Expose `run_setup(variant)` for the existing zero-shot setup and `copy_prepared_input(source, target)` for the few-shot caller. The copy function reads and validates the source manifest, verifies source bytes and counts, writes those exact bytes under the target key, and writes a target manifest that names the target key but preserves the digest, counts, source information, first ID, and last ID. Do not parse and reserialize `records.jsonl` before writing it.

Initial setup requires an empty target prefix. Immutable writes must fail closed if a target object exists. Do not delete or overwrite a target object to make a rerun pass.

## Preflight

Run from `/Users/mark/src/work/mirrorview-wt` with AWS credentials mapped from `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`:

```bash
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY"
aws sts get-caller-identity --output json
aws s3api head-object --bucket mirrorview-experimental-artifacts --key experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl --region us-east-2 --query '{ContentLength:ContentLength,ETag:ETag}'
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl - --region us-east-2 --no-progress | shasum -a 256
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix experiments/few_shot_llm_inference_2026_09_30/ --region us-east-2 --query 'length(Contents || `[]`)' --output text
```

Expected content length is `8516715`. Expected SHA-256 is `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`. The final command must print `0` before the first setup run. Any mismatch or nonzero target count blocks setup and requires review.

## Main caller

```bash
PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step1_setup.main
```

Expected stdout contains:

```text
records_key=experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl manifest_key=experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/manifest.json rows=13992 unique_post_ids=13992 unanimous_rows=4051 split_rows=9941
```

## Target verification

```bash
INPUT_VERIFY_TMP=$(mktemp -d)
export INPUT_VERIFY_TMP
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl "$INPUT_VERIFY_TMP/source.jsonl" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl "$INPUT_VERIFY_TMP/target.jsonl" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/manifest.json "$INPUT_VERIFY_TMP/source-manifest.json" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/manifest.json "$INPUT_VERIFY_TMP/target-manifest.json" --region us-east-2 --no-progress
cmp "$INPUT_VERIFY_TMP/source.jsonl" "$INPUT_VERIFY_TMP/target.jsonl"
shasum -a 256 "$INPUT_VERIFY_TMP/source.jsonl" "$INPUT_VERIFY_TMP/target.jsonl"
PYTHONPATH=. uv run python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["INPUT_VERIFY_TMP"])
source = json.loads((root / "source-manifest.json").read_text())
target = json.loads((root / "target-manifest.json").read_text())
assert source["records_s3_key"] != target["records_s3_key"]
for field in ("records_sha256", "total_record_count", "unanimous_record_count", "split_record_count", "source_dataset_names", "first_post_id", "last_post_id"):
    assert source[field] == target[field]
assert target["records_s3_key"] == "experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl"
print("copied-input-ok")
PY
```

`cmp` exits 0, both hash lines contain `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`, and the final command prints exactly `copied-input-ok`.

## Prompt and overlap smoke contract

Add no test file. The approved prompt digest is the authority for all ten demonstrations, their order, labels, placeholders, and whitespace. This command also confirms that the configured five exact-match IDs exist in the copied input and are unanimous:

```bash
PYTHONPATH=. uv run python - <<'PY'
import hashlib

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT
from experiments.few_shot_llm_inference_2026_09_30.shared.prompts import (
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT,
    format_baseline_few_shot_keep_remove_prompt,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import load_verified_prepared_input

digest = hashlib.sha256(BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT.encode("utf-8")).hexdigest()
assert digest == "ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3"
rendered = format_baseline_few_shot_keep_remove_prompt("POST_ONE_SENTINEL", "POST_TWO_SENTINEL")
assert rendered.count("POST_ONE_SENTINEL") == 1
assert rendered.count("POST_TWO_SENTINEL") == 1
store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket, region_name="us-east-2")
_, records = load_verified_prepared_input(store, FEW_SHOT_VARIANT)
by_id = {record.post_id: record for record in records}
excluded = FEW_SHOT_VARIANT.metric_exclusion_post_ids
assert len(records) == 13_992
assert len(excluded) == len(set(excluded)) == 5
assert all(by_id[post_id].is_unanimous for post_id in excluded)
print("few-shot-prompt-ok rows=13992 overlaps=5 unanimous_overlaps=5")
PY
```

Expected stdout is exactly:

```text
few-shot-prompt-ok rows=13992 overlaps=5 unanimous_overlaps=5
```

Confirm immutable rerun behavior:

```bash
if PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step1_setup.main; then
  echo "setup rerun unexpectedly succeeded" >&2
  exit 1
else
  echo "setup-rerun-rejected"
fi
```

Expected final stdout is `setup-rerun-rejected`. The target object hashes remain unchanged.

## Must pass

- Prompt digest and configured exact-overlap audit match the approved values before any Bedrock call. The fixed digest is the demonstration-count authority.
- The few-shot and zero-shot key roots differ.
- The target records object is exactly 8,516,715 bytes with SHA-256 `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`.
- The target manifest points to the few-shot records key and reports 13,992, 4,051, and 9,941 rows.
- `README.md` and `SETUP.md` follow the repository experiment-document rules.

## Must fail

- A changed prompt byte, placeholder count, example order, or example label.
- A source digest, source count, first-ID, or last-ID mismatch.
- A nonempty target prefix before initial setup.
- Any attempt to overwrite an existing target object.

## Commit

Commit only the allowed repository files with a message such as `feat: add few-shot Study 2 setup`.
