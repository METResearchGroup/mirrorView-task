# Step 2: Add the experiment adapter and prepare the input

## Goal

Create the experiment package `experiments/zero_shot_jev_inference_2026_10_01/` with four pieces:

- constants
- a keep or remove adapter over `shared.models.jev`
- S3 key builders rooted at this experiment
- a setup command that copies issue 326's prepared input into this experiment's input prefix

All paths are relative to the repository root. Run every command from the repository root.

## Scope

- **Main caller:** `experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py::main`
- **Main task:** read issue 326's prepared records and manifest from S3, verify the SHA-256 and counts, then create byte-identical copies under this experiment's input prefix without replacing an existing object.
- **Unit of work:** one prepared input package of 13,992 Study 2 pairs, plus the adapter that turns one prepared pair into one Jev request and one `JevResult` into one prediction row.
- **Out of scope:** Jev calls, thread pools, run folders, metrics, documentation files, and changes to issue 326 files or S3 objects.

## Preconditions

1. Issue 326's Step 1 files exist at `experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`, `shared/prompts.py`, `shared/storage.py`, and `shared/constants.py`.
2. Issue 326's prepared input exists at `s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl` and `.../manifest.json`.
3. Step 1 of this plan is merged into the working branch.

If issue 326's final public names differ from the names in this step, map them one to one and record the mapping in the commit message. If an issue 326 helper this step depends on is private, or is bound to issue 326's S3 root, stop and return to plan review. Do not copy it.

## Exact file tree

```text
experiments/zero_shot_jev_inference_2026_10_01/
  __init__.py
  shared/
    __init__.py
    constants.py
    schemas.py
    jev.py
    storage.py
  src/
    __init__.py
    step1_setup/
      __init__.py
      prepare.py
```

## Files to inspect

- `docs/plans/2026-10-01_study_2_zero_shot_jev_inference_41eb9f/proposal.md`
- `docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step1.md`
- `docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step2.md`
- `experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py`
- `experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `experiments/zero_shot_llm_inference_2026_09_30/shared/prompts.py`
- `experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `data_platform/generate_features/s3_feature_campaign.py` (`CampaignObjectStore.get`, `put_new`, `list_keys`)
- `shared/models/jev/__init__.py`

## Files allowed to change

- `experiments/zero_shot_jev_inference_2026_10_01/__init__.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/__init__.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/constants.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py`
- `experiments/zero_shot_jev_inference_2026_10_01/src/__init__.py`
- `experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/__init__.py`
- `experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py`

## Files forbidden to change

- `experiments/zero_shot_llm_inference_2026_09_30/**`
- `experiments/study_2_llm_based_feature_extraction_2026_09_29/**`
- `shared/**`
- `data_platform/**`
- `pyproject.toml`
- `uv.lock`

## Confirmed contracts

### Constants

`shared/constants.py` defines the proposal's values plus the S3 keys and run defaults:

| Name | Value |
| --- | --- |
| `EXPERIMENT_NAME` | `"zero_shot_jev_inference_2026_10_01"` |
| `S3_BUCKET` | `"mirrorview-experimental-artifacts"` |
| `S3_PREFIX` | `"experiments/zero_shot_jev_inference_2026_10_01/"` |
| `JEV_MODEL` | `ModelDefinition(display_name="Jev 1.13.0", folder_name="jev_1_13_0", model_id=JEV_MODEL_ID)` |
| `REMOVE_QUESTION_ID` | `"is_remove"` |
| `STATE_POST_1_KEY`, `STATE_POST_2_KEY` | `"post_1"`, `"post_2"` |
| `REMOVE_THRESHOLD` | `0.5` |
| `SOURCE_INPUT_RECORDS_KEY` | issue 326's input records key constant, imported, not retyped |
| `SOURCE_INPUT_MANIFEST_KEY` | issue 326's input manifest key constant, imported, not retyped |
| `INPUT_RECORDS_KEY` | `"experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl"` |
| `INPUT_MANIFEST_KEY` | `"experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json"` |
| `EXPECTED_ALL`, `EXPECTED_UNANIMOUS`, `EXPECTED_SPLIT` | `13992`, `4051`, `9941` |
| `DEFAULT_BATCH_SIZE` | `500` |
| `DEFAULT_MAX_WORKERS` | `8` |

### Schemas

`shared/schemas.py` holds one model, `JevRunManifest`. It is issue 326's `ModelRunManifest` with the configured max-token field replaced by `max_workers: int`. Jev has no max-token setting, so recording a placeholder value would misreport the run. Every other field, validator, and status rule matches issue 326's `ModelRunManifest`. All other schemas are imported from issue 326 or `shared.models.jev`.

`JevRunManifest` is a change from the approved proposal, which said to use `ModelRunManifest` unchanged. The change affects only the run manifest. Prediction and failure rows still use issue 326's `PredictionRecord` and `FailureRecord` unchanged.

### Adapter

`shared/jev.py` matches the proposal's "`experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py`" code exactly:

- `build_remove_instructions(prompt)` keeps everything before the pair block byte for byte. It raises `ValueError` unless the prompt ends with exactly `"Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\nAllow Or Remove?"`.
- `REMOVE_INSTRUCTIONS` is built once from `BASELINE_ZERO_SHOT_KEEP_REMOVE_PROMPT`.
- `build_remove_request(record)` puts `post_1_text` and `post_2_text` into `state` in prepared order. It asks one `Noul`, keyed `is_remove`, with `REMOVE_CRITERIA`.
- `to_prediction_record(run_id, record, result)` sets `is_remove = p_remove >= 0.5` and copies token counts from `result`.

### Storage

`shared/storage.py` adds only key builders rooted at `S3_PREFIX`:

- run folder: `runs/{run_id}/jev_1_13_0/`
- prediction, failure, and manifest object keys, with the six-digit sequence formats from issue 326 Step 2
- analysis prefix: `analysis/{run_id}/`

Each builder validates `run_id` with issue 326's public safe-segment validator. JSON and JSONL serialization, SHA-256, the lab credential adapter, and immutable writes are imported from `experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`.

### Prepare

`prepare.py` exposes `prepare_input(store: CampaignObjectStore) -> InputManifest` and `main()`:

1. Read both source objects with `store.get`. Raise `FileNotFoundError` when either is missing.
2. Parse the manifest as issue 326's `InputManifest`.
3. Check that the records bytes' SHA-256 equals the manifest's records SHA-256, and that the manifest reports 13,992 total, 4,051 unanimous, and 9,941 split rows. Otherwise raise `ValueError`.
4. Parse every records line as `Study2InputRecord`. Check for 13,992 unique `post_id` values in ascending order.
5. Call `store.put_new` for the records first and the manifest second, using the unchanged bytes. `FileExistsError` propagates unchanged, and nothing is deleted or replaced.
6. `main()` applies issue 326's credential adapter, builds `CampaignObjectStore(S3_BUCKET)`, calls `prepare_input`, and prints one summary line.

The copied manifest still names issue 326's records key, because it is a byte copy. Later steps identify the input by SHA-256 and by this experiment's key constants, not by that field.

## Caller-first implementation phases

### Phase 0: Confirm scope

Name `prepare.py::main` as the setup caller and `build_remove_request` and `to_prediction_record` as the adapter callers for Step 3.

The phase passes when the file tree and the list of issue 326 imports are recorded, and no issue 326 file is edited.

### Phase 1: Scaffold

Create the files with working imports and stub bodies, then commit.

```bash
PYTHONPATH=. uv run python -c "from experiments.zero_shot_jev_inference_2026_10_01.src.step1_setup.prepare import main; from experiments.zero_shot_jev_inference_2026_10_01.shared.jev import build_remove_request, to_prediction_record; from experiments.zero_shot_jev_inference_2026_10_01.shared.schemas import JevRunManifest; print('step2-imports-ok')"
```

Expected output:

```text
step2-imports-ok
```

### Phase 2: Confirm contracts

Fill in constants, `JevRunManifest`, key builder signatures, and the signatures of `prepare_input` and the adapter. Commit. Stop for plan review before Phase 3 unless this step file was approved without revisions.

### Phase 3: Direct checks to satisfy

Each check runs as a `PYTHONPATH=. uv run python -c` command against a fake store, an in-memory class with `get`, `put_new`, and `list_keys`. No check touches S3 or Jev.

1. Given issue 326's prompt, when `REMOVE_INSTRUCTIONS` is built, then it equals the prompt text before `Post 1: {post_1_text}`, followed by `REMOVE_QUESTION`.
2. Given a prompt with the pair block removed or followed by trailing text, when `build_remove_instructions` runs, then it raises `ValueError`.
3. Given one record, when `build_remove_request` runs, then `state == {"post_1": record.post_1_text, "post_2": record.post_2_text}` and the single question is a `Noul` keyed `is_remove`.
4. Given `JevResult` values with `nouls={"is_remove": 0.5}` and `{"is_remove": 0.49}`, when `to_prediction_record` runs, then `is_remove` is `True` and `False`, `model_folder == "jev_1_13_0"`, and `model_id == "jev-1.13.0"`.
5. Given a fake store holding valid source objects, when `prepare_input` runs, then the target keys hold byte-identical copies, written records first.
6. Given a records SHA-256 mismatch, a count mismatch, a duplicate `post_id`, or a missing source object, when `prepare_input` runs, then it raises before any `put_new`.
7. Given an existing target key, when `prepare_input` runs, then `FileExistsError` propagates and the existing bytes are unchanged.
8. Given `run_id` values `""`, `"."`, `".."`, `"a/b"`, or `" a"`, when a key builder runs, then it raises `ValueError`.

### Phase 4: Implement one unit at a time

Implement in this order, committing each unit separately: constants, `JevRunManifest`, adapter, key builders, `prepare_input`, `main`. Run the matching direct check after each unit.

### Phase 5: Verify and copy the input

```bash
test -z "$(aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/ --query 'Contents[].Key' --output text --region us-east-2 | grep -v None)"
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step1_setup.prepare
```

The first command should print nothing and exit 0. The second command should print the following line:

```text
records_key=experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl manifest_key=experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json rows=13992 unique_post_ids=13992 unanimous_rows=4051 split_rows=9941 sha256_matches_source=true
```

Running the command a second time must exit nonzero with `FileExistsError` and print no success line.

## Pass

- The adapter's request and prediction mapping match the proposal byte for byte.
- The copied input is byte-identical to issue 326's input, and its SHA-256 matches the manifest.
- Existing target objects are never replaced or deleted.
- No issue 326 file changes.

## Fail

- Any count differs from 13,992, 4,051, or 9,941.
- The instructions differ from issue 326's prompt before the pair block.
- `prepare_input` writes before every check passes.
- Code copies an issue 326 helper instead of importing it.
- Any forbidden file changes.
