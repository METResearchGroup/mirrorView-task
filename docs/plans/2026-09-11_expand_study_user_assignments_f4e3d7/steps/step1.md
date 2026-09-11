# Step 1: Add the command that writes 1000 extra mixed assignment rows

## Scope

- **Caller:** `experiments/upsample_mixed_study_feeds_2026_09_11/run.py` `main`
- **Task:** Load the pinned pull request 278 assignment CSV, copy the original 3879 rows unchanged, sample 1000 mixed 10 left and 10 right feeds without replacement, append those clones as extra assignment ids 3880 through 4879 so recruiting about 4000 starters does not exhaust the original 3879 rows, split odd original user ids to Democrats and even ids to Republicans, rewrite party ids, write a local batch tree, and add pytest files that prove mixed-only sampling and original-row identity on in-memory tables.
- **Out of scope:** The live S3 run (Step 2), uploading to `jspsych-mirror-view-2026-09-09`, editing the lookup Lambda, editing stimulus catalogs, remaining-label replay, resetting DynamoDB, adding files under the repo-root `tests/` folder.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-11_expand_study_user_assignments_f4e3d7/plan.md` | Confirmed clone count, mixed-only rule, append rule, party counts |
| `/workspace/experiments/load_study_assignments_2026_09_09/load.py` | `load_source_assignments` |
| `/workspace/experiments/load_study_assignments_2026_09_09/split.py` | `split_by_party`, `rewrite_ids`, `parse_original_user_id`, `party_for_user_id`, `feed_kind`, `parse_post_ids` |
| `/workspace/experiments/load_study_assignments_2026_09_09/constants.py` | `AssignmentRow`, `format_assignment_id`, `EXPECTED_TEN_TEN`, leftover user ids |
| `/workspace/experiments/load_study_assignments_2026_09_09/catalog.py` | `load_old_catalog_rows`, `load_new_catalog_rows`, `build_assigned_catalog`, `stance_by_id` |
| `/workspace/experiments/load_study_assignments_2026_09_09/write.py` | Party CSV columns and `config.yaml` shape |
| `/workspace/experiments/load_study_assignments_2026_09_09/upload.py` | Three relative keys under a timestamped prefix |
| `/workspace/experiments/generate_study_user_assignments_2026_09_08/assign.py` | `shuffle_feed` |
| `/workspace/experiments/generate_study_user_assignments_2026_09_08/RESULTS.md` | Users 1 through 3202 are mixed, users 3203 through 3879 are leftover-left |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/test_parse_prediction.py` | Test class layout |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Arrange-act-assert and one test class per function. Identity of original rows must be tested. |

## Files allowed to change

- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/README.md` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/constants.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/upsample.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/split_batch.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/write.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/run.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/.gitignore` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/tests/__init__.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/tests/conftest.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/tests/test_select_mixed_rows.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/tests/test_sample_mixed_feeds.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/tests/test_clone_mixed_feeds.py` (new)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/tests/test_append_party_rows.py` (new)
- `/workspace/.gitignore` (ignore cache under this experiment folder only)

## Files forbidden to change

- `/workspace/experiments/generate_study_user_assignments_2026_09_08/**`
- `/workspace/experiments/load_study_assignments_2026_09_09/**`
- `/workspace/webapp/lambdas/lambda-get-post-assignments.mjs` until Step 2 has a new prefix
- `/workspace/jobs/config/mirrorview_2026_09_09.yaml` until Step 2 has a new prefix
- `/workspace/webapp/infra/main.tf`
- `/workspace/webapp/public/img/flips_2026_09_09.csv`
- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/**`
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md` until Step 2 has a live prefix and `RESULTS.md`
- The pull request 278 source CSV on S3
- The live prefix `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02/`
- DynamoDB tables `user_assignments` and `study_assignment_counter`

## README contract

Write `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/README.md` first, then implement the modules to match it.

The README must:

1. Start with the same agent read-only banner used in `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. Say a feed is assigned when a participant starts, so dropouts still consume a row. Say the command adds 1000 extra mixed assignment rows so recruiting about 4000 people does not exhaust the 3879 original rows. Say it does not add posts to the stimulus catalog.
3. Say mixed feeds are 10 left and 10 right. Say leftover-left feeds are not cloned.
4. Say sampling is 1000 mixed feeds without replacement, seed 0.
5. Say the original 3879 rows are copied unchanged. Extra user ids are 3880 through 4879. Odd original ids go to `democrat`. Even original ids go to `republican`. Extra Democrat count is 500. Extra Republican count is 500.
6. Say extras are appended at the end of each party file, so Democrat ids `democrat-training_assisted-0001` through `democrat-training_assisted-1940` keep the original posts.
7. Say the live prefix `2026_09_09-23:06:02` is left in place, because returning users still read that prefix from DynamoDB. Say DynamoDB counters are not reset.
8. Name output columns `id`, `assigned_post_ids`, `political_party`, `condition`, `created_at`.
9. Name the experimental S3 object `s3://mirrorview-experimental-artifacts/experiments/upsample_mixed_study_feeds_2026_09_11/study_user_assignments.csv`.
10. List required files: `constants.py`, `upsample.py`, `split_batch.py`, `write.py`, `run.py`, and the pytest files under `tests/`.
11. Include the pytest command and the live run command from the Main caller section below.

After this README is committed, Step 2 may add only the live `batch_uri` and the party row counts. Do not rewrite the algorithm.

## Public contracts

Keep functions under 20 lines. Use frozen dataclasses. Reuse `CampaignObjectStore`, `parse_s3_uri`, `sha256_hex`, `load_source_assignments`, `split_by_party`, `rewrite_ids`, `feed_kind`, `parse_post_ids`, `build_assigned_catalog`, `stance_by_id`, `shuffle_feed`, and `get_current_timestamp`. Do not copy a new S3 client. Do not edit the original generator or the load experiment. Do not import `_pool_state`, `_fill_kinds`, or `_fill_kind`.

### `constants.py`

Pinned values: clone count 1000, sample seed 0, base user count 3879, mixed source count 3202, leftover-left count 677, extra first user id 3880, total user count 4879, Democrat row count 2440, Republican row count 2439, Democrat leftover-left count 339, Republican leftover-left count 338, Democrat mixed count 2101, Republican mixed count 2101, pinned source assignment URI and SHA-256, study bucket `jspsych-mirror-view-2026-09-09`, assignment prefix `precomputed_assignments`, four-digit user id width.

Frozen dataclasses at least:

- `UpsampleCounts` with `base_users`, `mixed_source`, `cloned_feeds`, `total_user_count`, `extra_democrat_count`, `extra_republican_count`
- `UpsampleRunResult` with those counts, `democrat_rows`, `republican_rows`, `assignment_slots`, local path, experimental S3 URI, and SHA-256

### `upsample.py`

- `select_mixed_rows(rows, stance_by_post)` returns the rows whose `feed_kind` is mixed 10 left and 10 right. Call `feed_kind` on every row, so an 11 left and 9 right row raises `ValueError`. Do not require a mixed count of 3202 inside this function. The live `main` checks that the mixed count is 3202.
- `sample_mixed_feeds(mixed_rows, count, seed)` returns `count` rows sampled without replacement with `numpy.random.Generator(numpy.random.PCG64(seed))`. Raise `ValueError` when `count` is less than 1, or when `count` is greater than `len(mixed_rows)`.
- `clone_mixed_feeds(sampled_rows, first_user_id, created_at)` writes new `AssignmentRow` values with ids `user-3880` through `user-4879` on the live run, empty party, condition `training_assisted`, and `assigned_post_ids` equal to `shuffle_feed(parse_post_ids(source), new_user_id)`. The set of 20 post ids must equal the source set. `created_at` is the new timestamp for clones only.
- `concat_source_rows(base_rows, extra_rows)` returns `base_rows + extra_rows`. Do not mutate `base_rows`.

### `split_batch.py`

- Call `split_by_party` then `rewrite_ids` on the concatenated source rows.
- `require_original_party_prefix(democrat, republican, original_democrat, original_republican)` compares `id`, `assigned_post_ids`, `political_party`, and `condition` for the first 1940 Democrat rows and the first 1939 Republican rows. Raise `ValueError` on the first mismatch.
- Extra Democrat ids start at `democrat-training_assisted-1941`. Extra Republican ids start at `republican-training_assisted-1940`.

### `write.py`

Write local files with `index=False`:

```text
experiments/upsample_mixed_study_feeds_2026_09_11/study_user_assignments.csv
experiments/upsample_mixed_study_feeds_2026_09_11/batch/config.yaml
experiments/upsample_mixed_study_feeds_2026_09_11/batch/democrat/training_assisted/assignments.csv
experiments/upsample_mixed_study_feeds_2026_09_11/batch/republican/training_assisted/assignments.csv
experiments/upsample_mixed_study_feeds_2026_09_11/batch/catalog.csv
```

`config.yaml` must parse as `MirrorViewConfig` in the assignment-service repo. Required shape:

```yaml
name: mirrorview_2026_09_09
input_posts_path: experiments/upsample_mixed_study_feeds_2026_09_11/batch/catalog.csv
local_data_dir: experiments/upsample_mixed_study_feeds_2026_09_11/batch
s3:
  bucket: jspsych-mirror-view-2026-09-09
  prefix: precomputed_assignments
cells:
  - political_party: democrat
    condition: training_assisted
    count: 2440
  - political_party: republican
    condition: training_assisted
    count: 2439
```

Source CSV `id` is `user-0001` through `user-4879` with four digits. Rows 1 through 3879 are copied from the pinned file. `assigned_post_ids` is a JSON list of 20 post ids. Sort the source CSV by `id`.

Upload of the experimental source CSV uses `CampaignObjectStore.put_new`. Write `RESULTS.md` in Step 2. Step 1 may include a `write_results_md` function that Step 2's live run calls.

### `run.py`

`main` loads the pinned assignment CSV, loads catalog stance, selects mixed rows, samples 1000, clones them, concatenates, splits, writes, uploads the experimental source CSV, and prints:

```text
base_users=
mixed_source=
cloned_feeds=
user_count=
democrat_rows=
republican_rows=
assignment_slots=
s3_uri=
csv_sha256=
```

Step 1 may skip the experimental `put_new` until Step 2, but the function must exist. Tests must not download S3.

## Pytest files

Tests live under `experiments/upsample_mixed_study_feeds_2026_09_11/tests/`. They must not download S3. They must not read the live assignment prefix. Build assignment rows in `conftest.py`. Use Arrange-Act-Assert. Name test classes `Test{FunctionName}`. Use `result` and `expected`. `pytest-mock` is not a dependency, so patch with `unittest.mock` when a test needs a fake store.

### `tests/conftest.py`

Factory `source_row(user_id, post_ids, created_at)` builds an `AssignmentRow` with empty party and condition `training_assisted`. Factory `stance_by_post` maps post ids to `left` or `right`. Include a fixture with four mixed feeds (10 left and 10 right) and two leftover-left feeds (20 left). Mixed user ids are 1 through 4. Leftover-left user ids are 5 and 6.

### `tests/test_select_mixed_rows.py`

Class `TestSelectMixedRows`.

```text
given four mixed rows and two leftover-left rows
when select_mixed_rows
then the result has 4 rows
and none of the leftover-left user ids are in the result

given a row that is 11 left and 9 right
when select_mixed_rows
then raise ValueError
```

### `tests/test_sample_mixed_feeds.py`

Class `TestSampleMixedFeeds`.

```text
given four mixed rows and count=2 and seed=0
when sample_mixed_feeds is called twice
then both results have the same two source ids
and those ids are unique
and both ids came from the mixed rows

given four mixed rows and count=5
when sample_mixed_feeds
then raise ValueError

given four mixed rows and count=0
when sample_mixed_feeds
then raise ValueError
```

### `tests/test_clone_mixed_feeds.py`

Class `TestCloneMixedFeeds`.

```text
given two sampled mixed rows and first_user_id=3
when clone_mixed_feeds
then clone ids are user-0003 and user-0004
and each clone has the same 20 post ids as its source, possibly in a new order
and each clone is still 10 left and 10 right
and concat_source_rows keeps the original two rows first and unchanged
```

### `tests/test_append_party_rows.py`

Class `TestAppendPartyRows`. Use original user ids 1 through 4, where 1 and 2 are the original pair and 3 and 4 are clones.

```text
given four source rows with user ids 1 through 4
when split_by_party and rewrite_ids
then Democrat ids are democrat-training_assisted-0001 and democrat-training_assisted-0002
and Republican ids are republican-training_assisted-0001 and republican-training_assisted-0002
and Democrat assigned_post_ids for index 0001 equals original user 1
and clones are the last row in each party list

given original Democrat assigned_post_ids for index 0001 that do not match the rewritten prefix
when require_original_party_prefix
then raise ValueError
```

## Main caller

Pytest:

```bash
PYTHONPATH=. uv run pytest experiments/upsample_mixed_study_feeds_2026_09_11/tests -q
```

Expected: exit 0.

Live command (run in Step 2, not this step):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
```

## Must pass

- Imports from `run.py` resolve.
- `README.md` names 1000 cloned mixed feeds, the no-replacement rule, the append rule, and the pytest command.
- `PYTHONPATH=. uv run pytest experiments/upsample_mixed_study_feeds_2026_09_11/tests -q` exits 0.
- Sampling 2 from 4 mixed rows is deterministic under seed 0 and never includes leftover-left rows.
- `concat_source_rows` keeps the original prefix unchanged.
- Product scripts, catalogs, the original generator, the load experiment, and the lookup Lambda are unchanged.
- No file was added under `/workspace/tests/`.

## Must fail

- Sampling leftover-left feeds.
- Sampling with replacement.
- Clone count less than 1, or greater than the mixed pool.
- A clone whose post-id set differs from its source.
- A clone that is not 10 left and 10 right.
- Original 3879 rows that differ from the pinned source after concat.
- Rewritten original party prefix that differs from the original split of the first 3879 rows.
- Hash mismatch on the pinned source assignment URI during a live load.
- Second upload to the experimental S3 key (live proof is Step 2).

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds the Python modules with stub bodies and a thin `main` that calls load, select, sample, clone, concat, split, write, print. Write `README.md` in this phase so the file list is locked.

Phase 3 locks the dataclasses and public function signatures. Bodies stay `raise NotImplementedError`.

Phase 4 writes the pytest files from the given/when/then blocks above. Tests must fail for `NotImplementedError` or a wrong result, not for missing imports.

Phase 5 implements in this order, one commit per unit of work:

1. `README.md` and `constants.py`
2. `select_mixed_rows` until `test_select_mixed_rows.py` is green
3. `sample_mixed_feeds` until `test_sample_mixed_feeds.py` is green
4. `clone_mixed_feeds` and `concat_source_rows` until `test_clone_mixed_feeds.py` is green
5. `split_by_party` and `rewrite_ids` wiring until clones are last in each party list
6. `require_original_party_prefix` until the mismatch case is green
7. local source CSV and batch writers
8. experimental `put_new` helper and `main` wiring

Phase 6 is complete when the pytest command exits 0, `run.py` imports resolve, `README.md` is present, and Step 2 can run the live command.
