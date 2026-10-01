# Step 1: Confirm setup, input, prompt, schema, model, and storage contracts

## Goal

Build the deterministic setup path that loads the three registered Study 2 datasets, selects the five-labeler universe, validates its partition, renders the exact issue prompt, and writes an immutable input package to S3. Step 1 also confirms the shared response, model, path, and storage contracts used by later steps.

## Scope

- **Main caller:** `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/prepare.py::main`
- **Happy-path task:** load registered data, validate the five-labeler partition, sort records, validate records, serialize JSONL and its manifest, then create both S3 objects without replacing an existing object.
- **Unit of work:** one prepared input package for all 13,992 eligible Study 2 posts.
- **Out of scope:** Bedrock calls, inference, model smoke checks, metrics, result rendering, generated local data, and changes to registered source datasets.

## Repository evidence

The implementation must use these existing contracts rather than reproduce their behavior:

- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py` loads registry entries.
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` defines `STUDY_2_KEEP_REMOVE_LABELS`, `STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS`, and `STUDY_2_KEEP_REMOVE_SPLIT_LABELS`.
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/split_keep_remove_labels.py` defines the five-labeler partition rules.
- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py` provides the existing Boolean-only `IsRemoveResult` example.
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/s3_feature_campaign.py` provides `CampaignObjectStore`, including immutable `put_new`, sorted `list_keys`, and object reads.
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/prompts.py` is the issue-named source for the baseline prompt.

The current registered files contain 20,000 modal-label rows. Filtering to exactly five labelers yields 13,992 unique posts. The registered unanimous and split datasets contain 4,051 and 9,941 rows, respectively. Their ID sets are disjoint and their union equals the five-labeler universe.

## Exact file tree

Create only the following files in this step:

```text
/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/
  shared/
    __init__.py
    constants.py
    prompts.py
    schemas.py
    storage.py
  src/
    step1_setup/
      __init__.py
      prepare.py
```

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/plan.md`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/README.md`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/split_keep_remove_labels.py`
- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/s3_feature_campaign.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/prompts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/REPORT.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py`

The final two files are read-only context. Do not incorporate or rewrite them.

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/prompts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/prepare.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/**`
- `/Users/mark/src/work/mirrorview-wt/shared/**`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/REPORT.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py`
- Every file outside `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/`

## Confirmed contracts

### Constants and models

`shared/constants.py` must define these fixed values:

- Bucket: `mirrorview-experimental-artifacts`
- S3 root: `experiments/zero_shot_llm_inference_2026_09_30/`
- Input records key: `experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl`
- Input manifest key: `experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/manifest.json`
- Expected counts: 13,992 all, 4,051 unanimous, and 9,941 split.
- Model registry entries, in a stable tuple, with display name, folder name, and exact issue model ID:
  - Amazon Nova Micro, `amazon_nova_micro`, `us.amazon.nova-micro-v1:0`
  - Qwen 3 32B, `qwen3_32b`, `qwen.qwen3-32b-v1:0`
  - OpenAI GPT-5.6 Terra, `openai_gpt_5_6_terra`, `us.openai.gpt-5.6-terra`
  - Claude Sonnet 5.5, `claude_sonnet_5_5`, `us.anthropic.claude-sonnet-5-5`

`shared/schemas.py` must define strict Pydantic models with extra fields rejected:

- `ModelDefinition`: `display_name: str`, `folder_name: str`, and `model_id: str`.
- `Study2InputRecord`: `post_id: str`, `post_1_text: str`, `post_2_text: str`, `gold_is_remove: bool`, `n_keep: int`, `n_remove: int`, `n_raters: int`, and `is_unanimous: bool`.
- `RemovePrediction`: `is_remove: bool` and `p_remove: float`.
- `InputManifest`: schema version, source dataset names, S3 records key, SHA-256 of the exact JSONL bytes, total count, unanimous count, split count, and ordered first and last post IDs.

Validation must enforce these invariants:

1. Each input text and post ID is nonempty.
2. `n_raters` equals 5 and `n_keep + n_remove` equals 5.
3. `gold_is_remove` equals `n_remove > n_keep`.
4. `is_unanimous` equals `n_remove in {0, 5}`.
5. `p_remove` is within the closed interval from 0 through 1.
6. `is_remove` is true when `p_remove >= 0.5` and false when `p_remove < 0.5`.

Do not round `p_remove` during validation or serialization.

### Prompt

`shared/prompts.py` must define `BASELINE_ZERO_SHOT_KEEP_REMOVE_PROMPT` as the exact prompt from issue 326, including paragraph breaks, examples, apostrophes, the hyphen in `not a response`, the placeholders `{post_1_text}` and `{post_2_text}`, and the final `Allow Or Remove?` line. It must also expose one formatter that accepts two strings and performs only placeholder substitution. Do not paraphrase the prompt, add a JSON instruction, swap post order, trim post text, or add model-specific text. `converse_label` adds its own schema-derived JSON instruction in Step 2.

### Prepared input

`prepare.py` must expose typed functions for these boundaries:

1. Load each dataset through `shared.data.dataloader.load_dataset` and the three registry constants.
2. Select `n_raters == 5` from the all-posts dataset.
3. Reject duplicate or empty `post_id` values.
4. Assert the unanimous and split ID sets are disjoint and their union is exactly the selected all-posts ID set.
5. Assert every row agrees across shared source columns when compared by `post_id`.
6. Map `original_text` to `post_1_text`, `mirror_text` to `post_2_text`, and `keep_remove_label == 1` to `gold_is_remove`.
7. Sort by `post_id` with a stable sort before constructing `Study2InputRecord` objects.
8. Serialize one compact JSON object per line as UTF-8 with sorted keys and a final newline.
9. Construct the manifest from the exact serialized bytes.
10. Call `CampaignObjectStore.put_new` for records first and manifest second.

The public preparation function must accept an injected `CampaignObjectStore` so its behavior can be checked without changing the storage boundary. The CLI caller may construct the real store. If either target key exists, fail without replacing it and print no success message. A partial state with records present and the manifest absent must also fail closed. Recovery requires a human to inspect the exact object and choose a new approved procedure. Do not add deletion or overwrite behavior.

### Storage helpers

`shared/storage.py` must own pure key construction, standardized JSON and JSONL serialization, SHA-256 calculation, and immutable byte writes through the injected store. Key builders must reject empty path segments, `.` segments, `..` segments, leading or trailing whitespace, slashes inside a segment, and a `run_id` or model folder not supplied as one complete segment. Keys must always remain below the fixed experiment root.

No wrapper may access `CampaignObjectStore._client` or reproduce its conditional-write behavior.

`shared/storage.py` must also expose a credential adapter that copies `LAB_AWS_ACCESS_KEY_ID` to `AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` to `AWS_SECRET_ACCESS_KEY` only when the matching standard variable is empty. It must never print or return a secret. Each real CLI calls the adapter before constructing an S3 store or Bedrock client.

## Caller-first implementation phases

### Phase 0: Confirm scope

Name `prepare.py::main` as the only caller. Record the file tree, the setup task, and the out-of-scope work above. Do not create inference or analysis modules.

**Gate:** exactly one caller, one setup task, and the seven allowed files are named.

### Phase 1: Scaffold

Create the package files, imports, typed public signatures, and a thin `main` path that shows load, validate, serialize, and write calls. Bodies must be `...` or raise `NotImplementedError`.

Run:

```bash
PYTHONPATH=. uv run python -c "from experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare import main; from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import RemovePrediction; print('step1-imports-ok')"
```

Expected output:

```text
step1-imports-ok
```

**Gate:** imports resolve, the caller shows the full sequence, and no data or storage behavior exists.

### Phase 2: Confirm contracts

Add only the Pydantic models, public signatures, fixed constants, exact prompt constant, and documented exceptions. Keep all transforms and writes stubbed.

**Gate:** fields, model IDs, folder names, S3 keys, function boundaries, and validation rules match this step. Stop for plan review before Phase 3 unless the reviewer has approved this step file without revisions.

### Phase 3: Implement pure contracts

Implement the pure behavior needed to satisfy these scenarios:

1. Given all, unanimous, and split frames with five-labeler records, when the public prepare function runs, then it emits records in ascending `post_id` order and writes records before the matching manifest.
2. Given the registered datasets, when preparation runs against a fake store, then the counts are 13,992, 4,051, and 9,941 and the partition is exact.
3. Given the issue's two post strings, when the prompt formatter runs, then its output equals a literal expected prompt and preserves both strings unchanged.
4. Given each model registry entry, when it is validated, then its display name, folder, and exact issue model ID match the confirmed tuple order.
5. Given `p_remove` at 0, below 0.5, at 0.5, and at 1, when `RemovePrediction` validates, then only threshold-consistent labels pass.
6. Given a missing ID, duplicate ID, wrong labeler count, vote-total mismatch, modal-label mismatch, or overlap or gap in the partition, when preparation validates, then it raises `ValueError` before any store write.
7. Given bytes already stored at either immutable input key, when preparation runs, then it raises `FileExistsError` and never replaces bytes.
8. Given unsafe path segments, when a key builder runs, then it raises `ValueError`.
9. Given lab AWS credentials and empty standard variables, when the credential adapter runs, then it sets both standard variables without printing their values. Given existing standard variables, it leaves them unchanged.

### Phase 4: Implement one unit at a time

Implement in caller dependency order. After each unit, run an import check or a focused read-only Python command against the public function that was completed.

1. Schema invariants and confirmed model registry.
2. Exact prompt constant and formatter.
3. AWS credential adapter, safe key builders, and standardized serialization.
4. Dataset loading and five-labeler selection.
5. Partition and row validation.
6. Deterministic record and manifest construction.
7. Immutable records and manifest writes.
8. `prepare.py::main` CLI wiring.

Do not combine units or refactor inspected source modules.

### Phase 5: Verify the caller

Run:

```bash
PYTHONPATH=. uv run python -c "from shared.data import dataloader; from shared.data.registry import STUDY_2_KEEP_REMOVE_LABELS, STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, STUDY_2_KEEP_REMOVE_SPLIT_LABELS; names=(STUDY_2_KEEP_REMOVE_LABELS, STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, STUDY_2_KEEP_REMOVE_SPLIT_LABELS); frames=[dataloader.load_dataset(name, low_memory=False) for name in names]; all_ids=set(frames[0].loc[frames[0]['n_raters'].eq(5), 'post_id'].astype(str)); unanimous_ids=set(frames[1]['post_id'].astype(str)); split_ids=set(frames[2]['post_id'].astype(str)); assert not (unanimous_ids & split_ids); assert all_ids == unanimous_ids | split_ids; print(len(all_ids), len(unanimous_ids), len(split_ids))"
```

Expected output:

```text
13992 4051 9941
```

Do not run the real preparation CLI until the read-only checks pass because it writes S3 objects. Confirm the AWS identity and inspect the input prefix:

```bash
aws sts get-caller-identity --query 'Account' --output text
test -z "$(aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/ --query 'Contents[].Key' --output text --region us-east-2)"
```

Expected output: the first command prints the approved AWS account ID. The second command prints nothing and exits zero, which proves both fixed input keys are absent. Then run the deliberate preparation command once:

```bash
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare
```

Expected output:

```text
records_key=experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl manifest_key=experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/manifest.json rows=13992 unique_post_ids=13992 unanimous_rows=4051 split_rows=9941
```

The command must exit nonzero and print no success line if either object already exists or any write fails. Do not delete or replace the partial state. Inspect the stored bytes before approving a recovery procedure.

## Pass

- The exact file tree exists and imports resolve.
- The input schema rejects every stated invariant violation.
- Prompt rendering is byte-for-byte equal to the issue prompt after placeholder substitution.
- The stable model registry contains exactly the four issue model IDs and folder names.
- The prepared IDs are unique, ordered, and exactly partitioned into 4,051 unanimous and 9,941 split IDs.
- Standardized serialization produces repeatable bytes and a matching SHA-256 manifest value.
- Direct checks confirm that records and manifest writes are immutable and fail closed on an existing object.

## Fail

- Any observed count differs from 13,992, 4,051, or 9,941.
- Any five-labeler ID is missing from or duplicated across the registered subsets.
- Prompt whitespace or wording differs from issue 326.
- A schema accepts an out-of-range probability or a label inconsistent with the 0.5 threshold.
- Record order depends on source CSV order.
- Code overwrites, deletes, or mutates an existing S3 object.
- Generated data is written to the repository.
- Any forbidden file changes.
