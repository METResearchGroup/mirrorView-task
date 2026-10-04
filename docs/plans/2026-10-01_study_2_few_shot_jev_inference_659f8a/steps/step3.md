# Step 3: Prepare the few-shot input

## Proposal sections implemented

- Cross-cutting concerns: Data and S3 isolation
- File structure: Repository and S3
- Schema and key interfaces: `InputManifest` and `copy_prepared_input`
- Step 3: Prepare an identical input package

## Scope

- **Caller:** `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step1_setup/main.py` `main`
- **Unit of work:** Read the verified zero-shot Jev input, copy the exact `records.jsonl` bytes into the few-shot Jev prefix, synthesize a target `InputManifest`, and print the copied input summary.
- **Out of scope:** Prompt compilation, Jev requests, inference, analysis, results publication, unit tests, and changes to an existing S3 object.

The work implements only the setup caller. Step 1 owns the reusable `copy_prepared_input` behavior, and Step 2 owns `FEW_SHOT_VARIANT`.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/proposal.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/steps/step1.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/steps/step2.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/config.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/config.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step1_setup/main.py` (new)

## Files forbidden to change

- Every file under `/Users/mark/src/work/mirrorview-wt/shared/models/jev/`
- Every file under `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/`
- Every few-shot Jev file not listed under files allowed to change
- Every `tests/` directory and every new test file
- Every existing zero-shot or few-shot S3 object
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`

## Input contract

The source objects are:

```text
s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl
s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json
```

The source records object is exactly 8,516,715 bytes with SHA-256 `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`. It contains 13,992 ordered unique post IDs, including 4,051 unanimous rows and 9,941 split rows.

The zero-shot Jev setup copied the original issue 326 manifest bytes. Its `records_s3_key` therefore names the original zero-shot LLM records object rather than the zero-shot Jev copy. Treat this as a known legacy field, not as permission to skip validation. The Step 1 copy function verifies that:

- The source records bytes match the manifest digest.
- The parsed rows match the manifest counts, first post ID, last post ID, and ascending unique post ID contract.
- The manifest reports 13,992 total rows, 4,051 unanimous rows, and 9,941 split rows.

The preflight below separately confirms that the legacy source manifest names the authoritative issue 326 key, `experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl`.

The target objects are:

```text
s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl
s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json
```

Copy `records.jsonl` byte for byte. Do not parse and reserialize it before writing. Build a new `InputManifest` whose `records_s3_key` is the few-shot Jev target key. Preserve the source `schema_version`, `source_dataset_names`, `records_sha256`, three counts, `first_post_id`, and `last_post_id`. Serialize the target manifest with the repository's standard JSON serializer.

Write both target objects with the existing immutable create operation. If either target key already exists, fail closed. Do not delete, overwrite, or repair an existing target object in this step.

## Caller contract

`main` creates one `CampaignObjectStore` for `FEW_SHOT_VARIANT.s3_bucket`, then calls:

```python
copy_prepared_input(
    store,
    source=ZERO_SHOT_VARIANT,
    target=FEW_SHOT_VARIANT,
)
```

The caller contains no copy, validation, or serialization logic. It maps the existing lab AWS credential variables before creating the store and prints one summary after both immutable writes succeed.

## Implementation phases

### Phase 1: Confirm the caller boundary

Name `main` as the only caller for this unit of work. Confirm that the reusable copy function and both variant records already exist from Steps 1 and 2. Stop if their signatures differ from the approved proposal.

### Phase 2: Scaffold the setup package

Step 2 already created `__init__.py`. Create `main.py`, add imports and a thin caller stub only, then run the import check before adding behavior.

### Phase 3: Wire the approved contract

Wire `main` to `copy_prepared_input` with `ZERO_SHOT_VARIANT` as the source and `FEW_SHOT_VARIANT` as the target. Keep every input invariant inside the reusable function from Step 1.

### Phase 4: Run inline contract checks

Use the commands below as the executable specification. Do not create a test file or a persistent smoke script.

### Phase 5: Execute the setup caller

Run the caller only after the source and empty-target preflight passes. A failed write never overwrites an existing object and blocks later steps. If a process interruption leaves only one target object, stop for review rather than deleting or repairing it.

### Phase 6: Verify the caller and repository scope

Compare the source and target bytes, validate the synthesized manifest, confirm immutable rerun rejection, and confirm that the step changed only its allowed file.

## Import check

Run this before implementation. It must fail because the new caller does not exist. Run it again after wiring; it must print `few-shot-jev-setup-import-ok`.

```bash
PYTHONPATH=. uv run python - <<'PY'
from experiments.few_shot_jev_inference_2026_10_01.src.step1_setup.main import main

assert callable(main)
print("few-shot-jev-setup-import-ok")
PY
```

## S3 preflight

Run from `/Users/mark/src/work/mirrorview-wt`:

```bash
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY"
aws sts get-caller-identity --output json
aws s3api head-object --bucket mirrorview-experimental-artifacts --key experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl --region us-east-2 --query '{ContentLength:ContentLength,ETag:ETag}'
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl - --region us-east-2 --no-progress | shasum -a 256
SOURCE_MANIFEST_TMP=$(mktemp)
export SOURCE_MANIFEST_TMP
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json "$SOURCE_MANIFEST_TMP" --region us-east-2 --no-progress
PYTHONPATH=. uv run python - <<'PY'
import json
import os
from pathlib import Path

manifest = json.loads(Path(os.environ["SOURCE_MANIFEST_TMP"]).read_text())
assert manifest["records_s3_key"] == "experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl"
assert manifest["records_sha256"] == "1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395"
assert (
    manifest["total_record_count"],
    manifest["unanimous_record_count"],
    manifest["split_record_count"],
) == (13_992, 4_051, 9_941)
print("zero-shot-jev-source-manifest-ok")
PY
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix experiments/few_shot_jev_inference_2026_10_01/ --region us-east-2 --query 'length(Contents || `[]`)' --output text
```

The source head response reports `ContentLength` 8,516,715. The hash command prints `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`. The inline check prints `zero-shot-jev-source-manifest-ok`. The final command must print `0` before the first setup run. A mismatch or nonzero target count blocks this step.

## Run the setup caller

```bash
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step1_setup.main
```

Expected stdout is one line containing:

```text
records_key=experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl manifest_key=experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json rows=13992 unique_post_ids=13992 unanimous_rows=4051 split_rows=9941 sha256=1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395
```

## Verify the copied input

```bash
INPUT_VERIFY_TMP=$(mktemp -d)
export INPUT_VERIFY_TMP
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl "$INPUT_VERIFY_TMP/source.jsonl" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl "$INPUT_VERIFY_TMP/target.jsonl" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json "$INPUT_VERIFY_TMP/source-manifest.json" --region us-east-2 --no-progress
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json "$INPUT_VERIFY_TMP/target-manifest.json" --region us-east-2 --no-progress
cmp "$INPUT_VERIFY_TMP/source.jsonl" "$INPUT_VERIFY_TMP/target.jsonl"
shasum -a 256 "$INPUT_VERIFY_TMP/source.jsonl" "$INPUT_VERIFY_TMP/target.jsonl"
PYTHONPATH=. uv run python - <<'PY'
import json
import os
from pathlib import Path

from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    parse_study2_input_jsonl_bytes,
)

root = Path(os.environ["INPUT_VERIFY_TMP"])
source = json.loads((root / "source-manifest.json").read_text())
target = json.loads((root / "target-manifest.json").read_text())
assert source["records_s3_key"] == "experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl"
assert target["records_s3_key"] == "experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl"
preserved = (
    "schema_version",
    "source_dataset_names",
    "records_sha256",
    "total_record_count",
    "unanimous_record_count",
    "split_record_count",
    "first_post_id",
    "last_post_id",
)
assert all(source[field] == target[field] for field in preserved)
assert target["records_sha256"] == "1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395"
assert (
    target["total_record_count"],
    target["unanimous_record_count"],
    target["split_record_count"],
) == (13_992, 4_051, 9_941)
records = parse_study2_input_jsonl_bytes((root / "target.jsonl").read_bytes())
by_id = {record.post_id: record for record in records}
exclusions = FEW_SHOT_VARIANT.metric_exclusion_post_ids
assert len(exclusions) == 5 and len(set(exclusions)) == 5
assert all(post_id in by_id for post_id in exclusions)
assert all(by_id[post_id].is_unanimous for post_id in exclusions)
print("few-shot-jev-input-ok rows=13992 unanimous=4051 split=9941 demonstrations=5")
PY
```

`cmp` exits 0. Both hash lines contain the approved records digest. The inline check prints exactly `few-shot-jev-input-ok rows=13992 unanimous=4051 split=9941 demonstrations=5`.

Record the target hashes, then prove that setup cannot overwrite either object:

```bash
for name in records.jsonl manifest.json; do
  aws s3 cp "s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/$name" - --region us-east-2 --no-progress | shasum -a 256
done > /tmp/few-shot-jev-input-hashes-before.txt
if PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step1_setup.main; then
  echo "setup rerun unexpectedly succeeded" >&2
  exit 1
else
  echo "setup-rerun-rejected"
fi
for name in records.jsonl manifest.json; do
  aws s3 cp "s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/$name" - --region us-east-2 --no-progress | shasum -a 256
done > /tmp/few-shot-jev-input-hashes-after.txt
cmp /tmp/few-shot-jev-input-hashes-before.txt /tmp/few-shot-jev-input-hashes-after.txt
```

Expected final stdout is `setup-rerun-rejected`, and the final `cmp` exits 0.

## Repository scope check

```bash
git diff --check
git diff --name-only -- experiments/few_shot_jev_inference_2026_10_01/src/step1_setup
PYTHONPATH=. uv run python - <<'PY'
import subprocess

allowed = {
    "experiments/few_shot_jev_inference_2026_10_01/src/step1_setup/main.py",
}
tracked = set(subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines())
untracked = set(
    subprocess.check_output(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "experiments/few_shot_jev_inference_2026_10_01/src/step1_setup",
        ],
        text=True,
    ).splitlines()
)
changed = tracked | untracked
assert changed == allowed, {"missing": sorted(allowed - changed), "unexpected": sorted(changed - allowed)}
print("step3-repository-scope-ok")
PY
```

The final command prints `step3-repository-scope-ok` when this step is reviewed in isolation from other plan steps.

## Must pass

- The source identity, length, digest, row counts, and ordered unique post IDs match the approved input.
- The target records bytes are byte-identical to the zero-shot Jev records bytes.
- The target manifest names the few-shot Jev records key and preserves every other approved source field.
- The second setup call fails without changing either target object.
- The caller contains no copy or validation logic, and the step adds no test file.

## Must fail

- Missing AWS credentials or failed AWS identity lookup.
- A source manifest key, digest, count, first ID, last ID, row order, or uniqueness mismatch.
- A nonempty few-shot Jev S3 prefix before the first setup run.
- An existing target key, partial target package, differing immutable target byte, or attempted overwrite.
- Any repository change outside the allowed file.

## Commit

After every check passes, commit only the allowed file with:

```bash
git add experiments/few_shot_jev_inference_2026_10_01/src/step1_setup/main.py
git commit -m "feat: add few-shot Jev setup caller"
```
