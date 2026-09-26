# Step 2: Confirm post-level splits and chat datasets

Notation: `E` = `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/`, `P` = `/workspace/experiments/finetune_qwen_model_2026_08_08/`, `W` = `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/`.

## Scope

- **Caller:** `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/build_splits.py` `main` with `--force`, then `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/create_chat_dataset.py` `main` with `--force`
- **Task:** Assign train and test once at post level on the Part 2 and Part 3 union modal label pool (stratified by modal label, 80/20, seed 1). Derive unanimous train and test as subsets of those post ids. Balance each train and test set with all removes plus equal sampled keeps (seed 1). Build Experiment 3 train by sampling modal train-split posts to match Experiment 1 balanced row counts. Write split CSVs, three experiment train CSVs, chat JSONL for all train sets and both shared test sets, print counts, write `README.md` and `SETUP.md`, and sync data to S3.
- **Out of scope:** SageMaker launcher, Dockerfile, `run_config.py`, `launch_sagemaker.py`, `entrypoint.sh`, training, inference, `RESULTS.md` scoring, editing prior package P or wrapper W, editing shared union label builders from Step 1, infra Terraform, adapter or prediction outputs.

## Dependencies

Step 1 must be complete:

- Union label CSVs on S3 at `shared/data/transformed/study_phase_2_part_2_and_3/keep_remove_labels.csv` (modal, 20,000 posts: 15,196 keep / 4,804 remove; includes `n_raters`) and `keep_remove_labels_unanimous_min3.csv` (unanimous min-3, 5,715 posts: 5,280 keep / 435 remove)
- Registry entries `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS` and `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` in `/workspace/shared/data/registry.py`
- Step 1 pytest green: `PYTHONPATH=. uv run pytest shared/data/transformed/study_phase_2_part_2_and_3/tests -q`

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/plan.md` | Decisions and pool table; Step 2 scope and S3 prefix |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/build_splits.py` | Import `balance_keep_remove`, `RANDOM_SEED`, `TRAIN_FRACTION`; do not call `build_and_write_splits` (row-level split, not post-level) |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py` | Import `row_to_chat_record`, `write_chat_jsonl`; chat record shape |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/prompt.py` | `SYSTEM_CONTENT`, `generate_user_prompt`; Post 1 = original, Post 2 = mirror |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/data/train.csv` | Target columns: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`, `n_raters` |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/src/build_splits.py` | Thin wrapper pattern: import helpers from P, own `main` and output paths |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner for E `README.md` |
| `/workspace/AGENTS.md` | Experiment README/SETUP rules; AWS cred export pattern |

## Files allowed to change

- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/__init__.py` (new)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/README.md` (new)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/SETUP.md` (new)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/__init__.py` (new)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/build_splits.py` (new)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/create_chat_dataset.py` (new)
- Generated under E: `data/split_manifest.csv`, `data/test_unanimous.csv`, `data/test_modal.csv`, `data/chat_test_unanimous.jsonl`, `data/chat_test_modal.jsonl`, `experiment1_unanimous/data/{train.csv,chat_train.jsonl}`, `experiment2_modal/data/{train.csv,chat_train.jsonl}`, `experiment3_modal_size_matched/data/{train.csv,chat_train.jsonl}`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/tests/test_build_splits.py` (new)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/tests/test_create_chat_dataset.py` (new)

## Files forbidden to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/**` (package P)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/**` (wrapper W)
- `/workspace/shared/data/registry.py` and `/workspace/shared/data/transformed/**` (Step 1 only)
- `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/plan.md`
- `/workspace/tests/**`, `/workspace/CHANGELOG.md`

## Public contracts

Load modal labels via `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS` and unanimous labels via `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3`. Treat `message_id` as post id.

**Post-level split (once, seed 1):** On the modal pool, stratify by modal `decision`, assign 80% of each class to train using `n_train = int(0.8 * n_class)` (same cut as P `stratified_balanced_split`). Write `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/data/split_manifest.csv` with columns `post_id`, `split` (`train` or `test`), `modal_label`, `in_unanimous` (post in unanimous-min3 CSV).

**Unanimous subset:** Unanimous train = modal-train posts in the unanimous CSV; unanimous test = modal-test posts in the unanimous CSV. Unanimous test post ids must be a subset of modal test post ids.

**Balancing (seed 1):** Reuse P `balance_keep_remove` on each split. Train: all removes in that split plus equal sampled keeps. Test: all test removes plus equal sampled test keeps. Exp2 train uses modal train posts; `test_modal.csv` uses modal test posts. Exp1 train uses unanimous train posts; `test_unanimous.csv` uses unanimous test posts.

**Experiment 3 size match:** Sample from modal train-split posts eligible for Exp2 balanced train. Match Exp1 remove count and keep count (about 351 each, 702 total), seed 1, 1:1 balance.

**Train and test CSV columns:** `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`, `n_raters` (same order as P `train.csv`). Copy `n_raters` from the label CSVs (modal and unanimous both include it after Step 1).

**Chat JSONL:** Reuse P `row_to_chat_record` and P `prompt.py`. Write `chat_train.jsonl` beside each experiment `train.csv`. Write `data/chat_test_unanimous.jsonl` and `data/chat_test_modal.jsonl` from shared test CSVs.

### README and SETUP

`README.md`: agent read-only banner from `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`, then one or two lines naming the Part 2 and Part 3 union LoRA experiment and redirecting to `SETUP.md` and `RESULTS.md`.

`SETUP.md`: Step 1 union label CSVs on S3 and registry keys as prerequisites; post-level split and balance rules; approximate counts (modal 20,000; unanimous 5,715; exp1 and exp3 train about 702; exp2 train about 7,686; unanimous test about 84 removes before keep sampling, about 168 balanced rows; modal test about 1,922 balanced rows); S3 bucket `mirrorview-experimental-artifacts`, prefix `experiments/finetune_lora_phase2_part3_2026_09_24`; and Main caller commands below.

## Pytest files

Under `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/tests/`. Use tiny in-memory frames; patch `load_dataset` when needed. Do not load full union label CSVs.

### `tests/test_build_splits.py`

Classes `TestPostLevelSplit`, `TestBalanceOutputs`, `TestExperimentThreeSizeMatch`, `TestLeakage`.

```text
given tiny modal and unanimous frames
when post-level split runs with seed 1
then split_manifest.csv has one row per modal post
and per-class train counts equal int(0.8 * n_class)
and in_unanimous is true only for unanimous posts

given balanced outputs
when row counts are checked
then each CSV has equal keep and remove
and exp1 train rows equal exp3 train rows
and exp1 remove count equals exp3 remove count

given test post ids from split_manifest.csv and three chat_train.jsonl files
when message_ids are scanned
then no test post id appears in any chat_train.jsonl (leakage test)

given unanimous and modal test post ids from split_manifest.csv
when set difference is taken
then unanimous test ids minus modal test ids is empty
```

### `tests/test_create_chat_dataset.py`

Classes `TestRowToChatRecord`, `TestWriteChatJsonl`.

```text
given one train.csv row
when row_to_chat_record runs via E wrapper
then user content has Post 1 original and Post 2 mirror
and assistant content is keep or remove
and user content lacks "Allow Or Remove?"

given tiny train.csv
when write_chat_jsonl runs with force
then JSONL line count equals CSV rows
and each line has message_id and messages keys
```

## Main caller

Pytest:

```bash
PYTHONPATH=. uv run pytest experiments/finetune_lora_phase2_part3_2026_09_24/tests -q
```

Expected: exit 0.

Build splits:

```bash
PYTHONPATH=. uv run python experiments/finetune_lora_phase2_part3_2026_09_24/shared/build_splits.py --force
```

Expected stdout includes: `modal_posts=20000`, `unanimous_posts=5715`, `exp1_train_rows=702`, `exp2_train_rows=7686`, `exp3_train_rows=702`, `test_unanimous_rows=168`, `test_modal_rows=1922`. Pytest asserts relationships; the script prints exact integers.

Build chat datasets:

```bash
PYTHONPATH=. uv run python experiments/finetune_lora_phase2_part3_2026_09_24/shared/create_chat_dataset.py --force
```

Expected: three `chat_train.jsonl` row counts match train CSVs; both shared test chat files match test CSV row counts.

Upload data (after AWS cred export per `AGENTS.md`):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

for dir in data experiment1_unanimous/data experiment2_modal/data experiment3_modal_size_matched/data; do
  aws s3 sync "experiments/finetune_lora_phase2_part3_2026_09_24/${dir}/" \
    "s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/${dir}/" \
    --region us-east-2
done
```

Expected: sync summary listing `split_manifest.csv`, test CSVs, chat JSONL, and three train CSV sets under the prefix.

## Must pass

- E shared module imports resolve; `README.md` redirects to `SETUP.md` and `RESULTS.md`.
- Post-level split on modal pool; unanimous sets are post-id subsets.
- Leakage test: no test post id in any `chat_train.jsonl`.
- Exp3 train rows and remove count match Exp1; unanimous test posts subset modal test posts.
- Each train and test CSV is 1:1 keep/remove balanced.
- P and W unchanged.

## Must fail

- Calling P `build_and_write_splits` or row-level `stratified_balanced_split` without prior post-level assignment.
- Test-split post in any train CSV or `chat_train.jsonl`.
- Exp3 counts differ from Exp1; unbalanced CSV; user prompt with `Allow Or Remove?`.
- Overwrite without `--force`; editing Step 1 shared transforms or registry.

## Implement-from-spec notes

Follow `/workspace/.cursor/skills/implement-from-spec/SKILL.md` in full auto mode. Phase 1: callers above. Phase 2: scaffold E, stubs, `README.md`, `SETUP.md`. Phase 3: lock signatures (`post_level_split`, balance writers, exp3 sampler, chat CLI); bodies `NotImplementedError`. Phase 4: pytest from given/when/then blocks. Phase 5 (one commit each): (1) post-level split and `split_manifest.csv`, (2) balanced CSV writers, (3) Exp3 sampler, (4) chat writer, (5) `main` counts, (6) S3 docs in `SETUP.md`. Phase 6: pytest green, both CLIs with `--force`, S3 sync succeeds.
