# Step 1: Add the command that writes 1000 extra feeds

## Scope

- **Caller:** `experiments/expand_study_user_assignments_2026_09_11/run.py` `main`
- **Task:** Replay the original 3879 fills, append 1000 mixed 10 left and 10 right feeds, write 4879 source rows, split odd original user ids to Democrats and even ids to Republicans, rewrite party ids, write a local batch tree, and add pytest files that prove original-feed identity and extra mix on in-memory tables.
- **Out of scope:** The live S3 remaining-labels run (Step 2), uploading to `jspsych-mirror-view-2026-09-09`, editing the lookup Lambda, editing catalogs, editing the remaining labels CSV, resetting DynamoDB, adding files under the repo-root `tests/` folder.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-11_expand_study_user_assignments_f4e3d7/plan.md` | Confirmed extra count, mix, append rule, party counts |
| `/workspace/experiments/generate_study_user_assignments_2026_09_08/assign.py` | `count_feed_kinds`, `_pool_state`, `_fill_kinds`, `_fill_kind`, `assign_feeds`, `shuffle_feed` |
| `/workspace/experiments/generate_study_user_assignments_2026_09_08/constants.py` | `CATALOG_SHUFFLE_SEED`, `USER_ID_START`, `FeedKind`, `UserAssignment`, recipes |
| `/workspace/experiments/generate_study_user_assignments_2026_09_08/load.py` | `load_remaining_labels`, `load_old_catalog_with_cells`, `load_new_catalog_with_cells`, `join_remaining_to_catalogs` |
| `/workspace/experiments/generate_study_user_assignments_2026_09_08/write.py` | Source CSV columns and `user-` id width |
| `/workspace/experiments/generate_study_user_assignments_2026_09_08/RESULTS.md` | Pinned 3879 counts and SHA-256 `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce` |
| `/workspace/experiments/load_study_assignments_2026_09_09/split.py` | `split_by_party`, `rewrite_ids`, `parse_original_user_id`, `party_for_user_id`, `feed_kind` |
| `/workspace/experiments/load_study_assignments_2026_09_09/constants.py` | `format_assignment_id`, `AssignmentRow`, live party counts |
| `/workspace/experiments/load_study_assignments_2026_09_09/catalog.py` | `build_assigned_catalog`, `load_old_catalog_rows`, `load_new_catalog_rows` |
| `/workspace/experiments/load_study_assignments_2026_09_09/write.py` | Party CSV columns and `config.yaml` shape |
| `/workspace/experiments/load_study_assignments_2026_09_09/upload.py` | Three relative keys under a timestamped prefix |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/test_parse_prediction.py` | Test class layout |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Arrange-act-assert and one test class per function. The usual experiments skip pytest rule does not apply. Identity of original feeds must be tested. |

## Files allowed to change

- `/workspace/experiments/expand_study_user_assignments_2026_09_11/README.md` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/constants.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/assign.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/split_batch.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/write.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/run.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/.gitignore` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/tests/__init__.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/tests/conftest.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/tests/test_assign_with_extra_ten_ten.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/tests/test_count_extra_party_rows.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/tests/test_append_party_rows.py` (new)
- `/workspace/experiments/expand_study_user_assignments_2026_09_11/tests/test_parse_args.py` (new)
- `/workspace/.gitignore` (ignore cache under this experiment folder only)

## Files forbidden to change

- `/workspace/experiments/generate_study_user_assignments_2026_09_08/**`
- `/workspace/experiments/load_study_assignments_2026_09_09/**`
- `/workspace/webapp/lambdas/lambda-get-post-assignments.mjs` until Step 2 has a new prefix
- `/workspace/jobs/config/mirrorview_2026_09_09.yaml` until Step 2 has a new prefix
- `/workspace/webapp/infra/main.tf`
- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/**`
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md` until Step 2 has a live prefix and `RESULTS.md`
- The pull request 278 source CSV on S3
- The live prefix `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02/`
- DynamoDB tables `user_assignments` and `study_assignment_counter`

## README contract

Write `/workspace/experiments/expand_study_user_assignments_2026_09_11/README.md` first, then implement the modules to match it.

The README must:

1. Start with the same agent read-only banner used in `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. Say the live September feed count is 3879, and that this command adds 1000 extra mixed feeds, for a total of 4879.
3. Say extra feeds are 10 left and 10 right. Say the command does not write leftover-left extras.
4. Say the command replays the original 3879 fills with seed 0, then continues the wrap for the extra block.
5. Say extra user ids are 3880 through 4879. Odd original ids go to `democrat`. Even original ids go to `republican`. Extra Democrat count is 500. Extra Republican count is 500.
6. Say extras are appended at the end of each party file, so Democrat ids `democrat-training_assisted-0001` through `democrat-training_assisted-1940` keep the original `assigned_post_ids`.
7. Say the live prefix `2026_09_09-23:06:02` is left in place, because returning users still read that prefix from DynamoDB.
8. Name output columns `id`, `assigned_post_ids`, `political_party`, `condition`, `created_at`.
9. Name the experimental S3 object `s3://mirrorview-experimental-artifacts/experiments/expand_study_user_assignments_2026_09_11/study_user_assignments.csv`.
10. List required files: `constants.py`, `assign.py`, `split_batch.py`, `write.py`, `run.py`, and the pytest files under `tests/`.
11. Include the pytest command and the live run command from the Main caller section below.

After this README is committed, Step 2 may add only the live `batch_uri` and the party row counts. Do not rewrite the algorithm.

## Public contracts

Keep functions under 20 lines. Use frozen dataclasses. Do not pass unstructured dictionaries for source identity. Reuse `CampaignObjectStore`, `parse_s3_uri`, `sha256_hex`, `load_remaining_labels`, `join_remaining_to_catalogs`, `split_by_party`, `rewrite_ids`, `build_assigned_catalog`, and `get_current_timestamp`. Do not copy a new S3 client. Do not edit the original generator or the load experiment.

### `constants.py`

Pinned values: extra mixed count 1000, base user count 3879, extra first user id 3880, total user count 4879, Democrat row count 2440, Republican row count 2439, Democrat leftover-left count 339, Republican leftover-left count 338, Democrat mixed count 2101, Republican mixed count 2101, pinned remaining-labels URI and SHA-256, pinned source assignment URI and SHA-256, pinned new catalog identity, output experimental S3 bucket and key, study bucket `jspsych-mirror-view-2026-09-09`, assignment prefix `precomputed_assignments`, column names, four-digit user id width.

Frozen dataclasses at least:

- `ExtraFeedCounts` with `extra_ten_ten_count`, `extra_democrat_count`, `extra_republican_count`, `total_user_count`
- `ExpandRunResult` with `base_users`, `extra_ten_ten`, `user_count`, `democrat_rows`, `republican_rows`, `extra_labels`, `unused_remaining`, local path, experimental S3 URI, and SHA-256

### `assign.py`

- `count_extra_party_rows(extra_ten_ten_count, first_user_id)` returns `ExtraFeedCounts`. Odd user ids in that range are Democrat. Even user ids are Republican. On 1000 extras starting at 3880, both party extra counts are 500, and `total_user_count` is 4879. If `extra_ten_ten_count` is less than 1, raise `ValueError`.
- `assign_with_extra_ten_ten(joined, extra_ten_ten_count)` shuffles joined rows with seed 0, builds pool state with `_pool_state`, fills the original kinds with `_fill_kinds`, then fills `extra_ten_ten_count` mixed feeds with `_fill_kind(state, FeedKind.TEN_TEN, extra_ten_ten_count, first_user_id)`. `first_user_id` is `USER_ID_START` plus the original `user_count`. Return `base + extra`.
- After `assign_with_extra_ten_ten`, the first `len(assign_feeds(joined))` assignments must equal `assign_feeds(joined)` field for field, including `user_id`, `post_ids`, `feed_kind`, and `cell_counts`.
- Every extra assignment has `feed_kind` `ten_ten`, 20 posts, and no repeated post id inside the feed.

### `split_batch.py`

- Convert `UserAssignment` values to `AssignmentRow` values with empty party, condition `training_assisted`, and one shared `created_at`.
- Call `split_by_party` then `rewrite_ids`. Do not copy a row to both parties.
- `require_original_party_prefix(democrat, republican, original_democrat, original_republican)` compares parsed `assigned_post_ids` lists for the first 1940 Democrat rows and the first 1939 Republican rows. Raise `ValueError` on the first mismatch. Ignore `created_at`.
- Extra Democrat ids start at `democrat-training_assisted-1941`. Extra Republican ids start at `republican-training_assisted-1940`.

### `write.py`

Write local files with `index=False`:

```text
experiments/expand_study_user_assignments_2026_09_11/study_user_assignments.csv
experiments/expand_study_user_assignments_2026_09_11/batch/config.yaml
experiments/expand_study_user_assignments_2026_09_11/batch/democrat/training_assisted/assignments.csv
experiments/expand_study_user_assignments_2026_09_11/batch/republican/training_assisted/assignments.csv
experiments/expand_study_user_assignments_2026_09_11/batch/catalog.csv
```

`config.yaml` must parse as `MirrorViewConfig` in the assignment-service repo. Required shape:

```yaml
name: mirrorview_2026_09_09
input_posts_path: experiments/expand_study_user_assignments_2026_09_11/batch/catalog.csv
local_data_dir: experiments/expand_study_user_assignments_2026_09_11/batch
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

Source CSV `id` is `user-0001` through `user-4879` with four digits. `assigned_post_ids` is a JSON list of 20 post ids. `political_party` is empty on the source CSV. `condition` is `training_assisted`. `created_at` comes from one `get_current_timestamp()` call for the whole run. Sort the source CSV by `id`.

Upload of the experimental source CSV uses `CampaignObjectStore.put_new`. Write `RESULTS.md` in Step 2. Step 1 may include a `write_results_md` function that Step 2's live run calls.

### `run.py`

`parse_args(argv)` accepts `--remaining-labels`. If the operator omits the path, exit non-zero and print an error that names `s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv`.

`main` loads, joins, assigns with 1000 extras, splits, writes, uploads the experimental source CSV, and prints:

```text
base_users=
extra_ten_ten=
user_count=
democrat_rows=
republican_rows=
assignment_slots=
extra_labels=
unused_remaining=
s3_uri=
csv_sha256=
```

Step 1 may skip the experimental `put_new` until Step 2, but the function must exist. Tests must not download S3.

## Pytest files

Tests live under `experiments/expand_study_user_assignments_2026_09_11/tests/`. They must not download S3. They must not read the live assignment prefix. Build remaining tables in `conftest.py`. Use Arrange-Act-Assert. Name test classes `Test{FunctionName}`. Use `result` and `expected`. `pytest-mock` is not a dependency, so patch with `unittest.mock` when a test needs a fake store.

### `tests/conftest.py`

Copy the `joined_posts_frame` factory shape from `experiments/generate_study_user_assignments_2026_09_08/tests/conftest.py`. Do not import that conftest. Include a leftover-left fixture with 21 left remaining and 10 right remaining, unique posts, remaining 1. That fixture is enough for one original mixed feed, one leftover-left feed, and two extra mixed feeds that wrap.

### `tests/test_count_extra_party_rows.py`

Class `TestCountExtraPartyRows`.

```text
given extra_ten_ten_count=1000 and first_user_id=3880
when count_extra_party_rows
then extra_democrat_count=500
and extra_republican_count=500
and total_user_count=4879

given extra_ten_ten_count=2 and first_user_id=3
when count_extra_party_rows
then extra_democrat_count=1
and extra_republican_count=1

given extra_ten_ten_count=0
when count_extra_party_rows
then raise ValueError
```

### `tests/test_assign_with_extra_ten_ten.py`

Class `TestAssignWithExtraTenTen`.

```text
given the leftover-left fixture and extra_ten_ten_count=2
when assign_with_extra_ten_ten
then the first 2 assignments equal assign_feeds on the same table
and user_count=4
and assignments 3 and 4 are 10 left and 10 right
and each extra feed has 20 posts
and no post id repeats inside one extra feed
and extra user ids are 3 and 4

given the leftover-left fixture and extra_ten_ten_count=2
when assign_with_extra_ten_ten
then no extra feed is leftover-left
and no extra feed is 11 left and 9 right
```

Measure left versus right from `sampled_stance` on the joined rows. Extra labels equal assigned slots minus original remaining, counted only where assigned slots exceed original remaining.

### `tests/test_append_party_rows.py`

Class `TestAppendPartyRows`. Build four source rows with original user ids 1 through 4. Rows 1 and 2 are the original pair. Rows 3 and 4 are extras.

```text
given four source rows with user ids 1 through 4
when split_by_party and rewrite_ids
then Democrat ids are democrat-training_assisted-0001 and democrat-training_assisted-0002
and Republican ids are republican-training_assisted-0001 and republican-training_assisted-0002
and Democrat assigned_post_ids for index 0001 equals original user 1
and extras are the last row in each party list

given original Democrat assigned_post_ids for index 0001 that do not match the rewritten prefix
when require_original_party_prefix
then raise ValueError
```

### `tests/test_parse_args.py`

Class `TestParseArgs`.

```text
given argv with no --remaining-labels
when parse_args or main
then the process exits non-zero
and the error text names s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv

given argv with --remaining-labels pointing at a local CSV in tmp_path
when parse_args
then remaining_labels equals that path
```

## Main caller

Pytest:

```bash
PYTHONPATH=. uv run pytest experiments/expand_study_user_assignments_2026_09_11/tests -q
```

Expected: exit 0.

Live command (run in Step 2, not this step):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/expand_study_user_assignments_2026_09_11/run.py \
  --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
```

A run with no remaining labels path exits non-zero and names that URI.

## Must pass

- Imports from `run.py` resolve.
- `README.md` names 1000 extra mixed feeds, the append rule, and the pytest command.
- `PYTHONPATH=. uv run pytest experiments/expand_study_user_assignments_2026_09_11/tests -q` exits 0.
- `count_extra_party_rows(1000, 3880)` matches 500, 500, and 4879.
- `assign_with_extra_ten_ten` on the leftover-left fixture keeps the original `assign_feeds` prefix.
- Product scripts, catalogs, the remaining labels CSV, the original generator, the load experiment, and the lookup Lambda are unchanged.
- No file was added under `/workspace/tests/`.

## Must fail

- `extra_ten_ten_count` less than 1.
- An extra feed that is leftover-left, or 11 left and 9 right.
- A feed with a repeated post id.
- First N assignments that differ from `assign_feeds`.
- Rewritten original party prefix `assigned_post_ids` that differ from the original split of the first 3879 rows.
- Hash mismatch on the pinned remaining-labels URI during a live load.
- Second upload to the experimental S3 key (live proof is Step 2).
- `PYTHONPATH=. uv run python experiments/expand_study_user_assignments_2026_09_11/run.py` with no `--remaining-labels`.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds the Python modules with stub bodies and a thin `main` that calls parse, load, join, assign, split, write, print. Write `README.md` in this phase so the file list is locked.

Phase 3 locks the dataclasses and public function signatures. Bodies stay `raise NotImplementedError`.

Phase 4 writes the pytest files from the given/when/then blocks above. Tests must fail for `NotImplementedError` or a wrong result, not for missing imports.

Phase 5 implements in this order, one commit per unit of work:

1. `README.md` and `constants.py`
2. `count_extra_party_rows` until `test_count_extra_party_rows.py` is green
3. `assign_with_extra_ten_ten` identity with `assign_feeds` until that case is green
4. extra mix 10 left and 10 right, no leftover-left extras, no in-feed duplicates, until those cases are green
5. `split_by_party` and `rewrite_ids` wiring until extras are last in each party list
6. `require_original_party_prefix` until the mismatch case is green
7. local source CSV and batch writers
8. `parse_args` / missing-path error until `test_parse_args.py` is green
9. experimental `put_new` helper and `main` wiring

Phase 6 is complete when the pytest command exits 0, `run.py` imports resolve, `README.md` is present, and Step 2 can run the live command.
