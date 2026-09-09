# Step 1: Add the load, shuffle, assign, upload command, and invariant tests

## Scope

- **Caller:** `experiments/generate_study_user_assignments_2026_09_08/run.py` `main`
- **Task:** Load remaining labels, join them to the old catalog and the pull request 273 catalog, shuffle with seed 0, fill 10:10 feeds then left-only feeds, shuffle each feed, write one row per user, upload the CSV with `put_new`, and add pytest files that prove the party-mix rules on in-memory remaining tables.
- **Out of scope:** The live S3 remaining-labels run (Step 2), editing catalogs, editing the remaining labels CSV, editing the assignment Lambda, adding files under the repo-root `tests/` folder.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-09_study_user_assignments_ac7f04/plan.md` | Confirmed feed-kind math, recipes, steal rule |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/load.py` | Download, hash check, cache, `load_new_catalog`. If this folder is missing on the branch, read it from `origin/main` (pull request 279). |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/write.py` | Local bytes, `put_new`, `RESULTS.md` shape |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/constants.py` | `NewCatalogSource`, pinned catalog URI, SHA-256, row count |
| `/workspace/shared/data/dataloader.py` | `load_dataset` for the old catalog |
| `/workspace/shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` | Old catalog columns `post_primary_key`, `sampled_stance`, `sample_toxicity_type` |
| `/workspace/lib/timestamp_utils.py` | `get_current_timestamp` |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `CampaignObjectStore`, `parse_s3_uri`, `put_new` |
| `/workspace/data_platform/utils/object_store.py` | `sha256_hex` |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/test_parse_prediction.py` | Test class layout |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Arrange-act-assert and one test class per function. The usual "experiments skip pytest" rule does not apply. The user required tests for the party-mix rules. |

## Files allowed to change

- `/workspace/experiments/generate_study_user_assignments_2026_09_08/README.md` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/constants.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/load.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/assign.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/write.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/run.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/.gitignore` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/tests/__init__.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/tests/conftest.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/tests/test_count_feed_kinds.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/tests/test_join_remaining.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/tests/test_assign_feeds.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/tests/test_shuffle_feed.py` (new)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/tests/test_parse_args.py` (new)
- `/workspace/.gitignore` (ignore cache under this experiment folder only)

## Files forbidden to change

- `/workspace/webapp/lambdas/lambda-get-post-assignments.mjs`
- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/**`
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/**`
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md` until Step 2 has a live S3 object and `RESULTS.md`
- The remaining labels S3 object
- The pull request 273 catalog S3 object

## README contract

Write `/workspace/experiments/generate_study_user_assignments_2026_09_08/README.md` first, then implement the modules to match it.

The README must:

1. Start with the same agent read-only banner used in `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. Say each user sees 20 posts.
3. Say the command fills as many 10 left and 10 right feeds as remaining right labels allow, then fills leftover left remaining into 20 left and 0 right feeds.
4. Say the command does not write 11:9 or 12:8 feeds.
5. Name the six cells and the `sampled_stance` / `sample_toxicity_type` map from the plan.
6. Name recipe 1 as 2, 5, 3, 2, 5, 3 and recipe 2 as 3, 5, 2, 3, 5, 2. Say odd 10:10 users inside the 10:10 block use recipe 1, and even 10:10 users use recipe 2. Say odd left-only users inside the left-only block prefer 4, 10, 6 from cells 1, 2, 3, and even left-only users prefer 6, 10, 4.
7. Say steal stays inside left cells 1 to 3, or inside right cells 4 to 6. Party mix does not slip. Toxicity may slip.
8. Say remaining count may go below 0, and those assignments are extra labels.
9. Say catalog shuffle uses seed 0, and each feed is shuffled with a numpy generator seeded by the user id.
10. Name output columns `id`, `assigned_post_ids`, `political_party`, `condition`, `created_at`.
11. Name the S3 object `s3://mirrorview-experimental-artifacts/experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv`.
12. List required files: `constants.py`, `load.py`, `assign.py`, `write.py`, `run.py`, and the pytest files under `tests/`.
13. Include the pytest command and the live run command from the Main caller section below.

After this README is committed, Step 2 may add only the live 10:10 count, left-only count, and assignment row count. Do not rewrite the algorithm.

## Public contracts

Keep functions under 20 lines. Use frozen dataclasses. Do not pass unstructured dictionaries for source identity. Reuse `CampaignObjectStore`, `parse_s3_uri`, `sha256_hex`, `load_dataset`, `get_current_timestamp`, and `load_new_catalog` / `pinned_new_catalog` from the remaining labels experiment. Do not copy a new S3 client. Do not import `load_old_catalog` from that experiment, because that loader returns only ids.

Odd and even are 1-based indexes inside the feed kind, not the global user id. User 1 is the first 10:10 feed and uses recipe 1. User 2 uses recipe 2. User 3203 is the first left-only feed and uses 4, 10, 6.

### `constants.py`

Pinned values: posts per feed 20, 10:10 split 10 and 10, left-only split 20 and 0, catalog shuffle seed 0, pinned remaining-labels URI and SHA-256 from the plan, pinned new catalog identity matching pull request 273, output S3 bucket and key, column names, recipe tuples, cell map.

Frozen dataclasses at least:

- `RemainingLabelsSource` with `s3_uri`, `sha256`, `expected_post_count`, `expected_label_count`
- `JoinedPost` with `post_id`, `remaining`, `cell`, `sampled_stance`, `sample_toxicity_type`
- `FeedKindCounts` with `ten_ten_count`, `left_only_count`, `leftover_left_remaining`, `user_count`
- `UserAssignment` with `user_id`, `post_ids`, `feed_kind`, `cell_counts`
- `AssignmentRunResult` with the stdout counts, local path, S3 URI, and SHA-256

Feed kind values are `ten_ten` and `left_only`.

### `load.py`

- `load_remaining_labels(path, store, cache_dir)` loads a local CSV or an S3 URI. Required columns are `id`, `number_of_times_to_label`, and `batch`. Fail if a column is missing, if an id repeats, or if any remaining count is less than 1. When `path` equals the pinned remaining-labels URI, check SHA-256 `188d627e8972d9b1ec5eb378814fd02fd588328df0a1ffc8603b0eba63d05c91`. When `path` is any other local path or S3 URI, load it without that hash check. On the pinned file, expected totals are 18,899 posts and 77,557 remaining labels.
- `load_old_catalog_with_cells()` loads `STUDY_PHASE_2_PART_2_STIMULI` through `load_dataset` and keeps `post_primary_key`, `sampled_stance`, and `sample_toxicity_type`.
- `load_new_catalog_with_cells(source, store, cache_dir)` downloads the pinned catalog by calling `load_new_catalog` from the remaining labels experiment and keeps the same three columns.
- `join_remaining_to_catalogs(remaining, old_catalog, new_catalog)` joins remaining `id` to `post_primary_key`. Fail if an id is in neither catalog. Fail if an id is in both catalogs. Map cells 1 through 6 from the plan. Return a table of joined posts.
- After the seed 0 shuffle, write `experiments/generate_study_user_assignments_2026_09_08/shuffled_stimuli.csv` with columns `post_primary_key`, `sampled_stance`, `sample_toxicity_type`, `number_of_times_to_label`, and `cell`. Keep that file out of git.

### `assign.py`

- `count_feed_kinds(left_remaining, right_remaining)` returns `FeedKindCounts`. The 10:10 count is the ceiling of right remaining divided by 10. Leftover left remaining equals left remaining minus 10 times that count. If leftover left remaining is less than 0, raise `ValueError`. Left-only count is the ceiling of leftover left remaining divided by 20, or 0 when leftover left remaining is 0. User count is the sum of the two counts. On 45,542 and 32,015, the result is 3,202, leftover 13,522, left-only 677, users 3,879.
- `preferred_cell_counts(feed_kind, index_within_kind)` returns the preferred counts for that 1-based index. Odd 10:10 is 2, 5, 3, 2, 5, 3. Even 10:10 is 3, 5, 2, 3, 5, 2. Odd left-only is 4, 10, 6, 0, 0, 0. Even left-only is 6, 10, 4, 0, 0, 0.
- `assign_feeds(joined)` shuffles joined rows with seed 0, splits by cell, fills every 10:10 feed first, then every left-only feed, steals inside the same party, wraps remaining 0 only after that party has no remaining labels left, subtracts one from remaining after each assignment, and returns one `UserAssignment` per user. Remaining may go below 0.
- `shuffle_feed(post_ids, user_id)` shuffles the 20 post ids with `numpy.random.Generator(numpy.random.PCG64(user_id))` and returns the shuffled list. User ids start at 1.

Steal order for a shortfall: other cells in the same party, in cell number order, that still have remaining greater than 0. A 10:10 feed never takes a right post in place of a left post, or a left post in place of a right post. A left-only feed never takes a right post. If the party still cannot fill the requested count after wrapping, raise `ValueError`. Skip a post already in the current user's feed.

### `write.py`

Write local `study_user_assignments.csv` with `index=False`. Columns, in this order: `id`, `assigned_post_ids`, `political_party`, `condition`, `created_at`. `id` is `user-0001` with four digits. `assigned_post_ids` is a JSON list of 20 post ids. `political_party` is empty. `condition` is `training_assisted`. `created_at` comes from one `get_current_timestamp()` call for the whole run. Sort by `id`. Upload with `CampaignObjectStore.put_new`. Write `RESULTS.md` in Step 2. Step 1 may include a `write_results_md` function that Step 2's live run calls.

### `run.py`

`parse_args(argv)` accepts `--remaining-labels`. If the operator omits the path, exit non-zero and print an error that names `s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv`.

`main` loads, joins, assigns, writes, uploads, and prints:

```text
ten_ten_count=
left_only_count=
user_count=
assignment_rows=
assignment_slots=
extra_labels=
unused_remaining=
s3_uri=
csv_sha256=
```

## Pytest files

Tests live under `experiments/generate_study_user_assignments_2026_09_08/tests/`. They must not download S3. They must not read the live remaining-labels object. Build remaining tables in `conftest.py`. Use Arrange-Act-Assert. Name test classes `Test{FunctionName}`. Use `result` and `expected`. `pytest-mock` is not a dependency, so patch with `unittest.mock` when a test needs a fake store.

The tests are the executable spec for the party-mix rules. A green suite means every feed is 10:10 or 20:0, 10:10 feeds come first, left-only feeds contain no right posts, steal never crosses party, leftover left remaining after the 10:10 feeds goes to left-only feeds, and the pull request 279 totals produce 3,202 then 677.

### `tests/conftest.py`

Factory `joined_posts_frame` builds a pandas table of `JoinedPost` rows. Give each cell a list of post ids and a remaining count per id. Stance is `left` for cells 1 to 3 and `right` for cells 4 to 6. Toxicity is low, middle, high in that cell order.

### `tests/test_count_feed_kinds.py`

Class `TestCountFeedKinds`.

```text
given left_remaining=45542 and right_remaining=32015
when count_feed_kinds
then ten_ten_count=3202
and leftover_left_remaining=13522
and left_only_count=677
and user_count=3879

given left_remaining=45542 and right_remaining=32015
when someone caps users at 3878 by using 3202 feeds at 10:10 and 676 left-only feeds
then leftover unused left remaining would be 2
and count_feed_kinds must not return 676 left-only feeds

given left_remaining=21 and right_remaining=10
when count_feed_kinds
then ten_ten_count=1
and leftover_left_remaining=11
and left_only_count=1
and user_count=2

given left_remaining=5 and right_remaining=20
when count_feed_kinds
then raise ValueError, because leftover left remaining would be less than 0
```

### `tests/test_join_remaining.py`

Class `TestJoinRemainingToCatalogs`.

```text
given a remaining id that is in neither catalog
when join_remaining_to_catalogs
then raise ValueError

given a remaining id that is in both catalogs
when join_remaining_to_catalogs
then raise ValueError

given a left middle-toxicity catalog row
when join_remaining_to_catalogs
then cell is 2
```

### `tests/test_assign_feeds.py`

Class `TestAssignFeeds`. Build a small remaining table with enough unique posts to fill the recipes without running S3. One fixture should use left remaining 21 and right remaining 10 so the assigner writes one 10:10 feed and one left-only feed. Another fixture should empty one preferred cell of remaining greater than 0, while another cell in the same party still has remaining.

```text
given a joined table whose count_feed_kinds result has both feed kinds
when assign_feeds
then every assignment is either 10 left and 10 right, or 20 left and 0 right
and no assignment is 11:9 or 12:8
and all 10:10 assignments come before all left-only assignments
and each feed has 20 posts
and no post id repeats inside one feed

given the 21 left and 10 right fixture
when assign_feeds
then user_count=2
and unused remaining labels=0
and extra labels=9 on the left and 0 on the right
and the second feed has 0 right posts

given a 10:10 preferred cell with remaining 0 and another cell in the same party with remaining greater than 0
when assign_feeds
then the shortfall is taken from the same party
and the feed still has 10 left and 10 right

given a left-only feed
when assign_feeds
then every post is left
and no right cell is used

given enough remaining in every cell to hit the preferred recipe
when assign_feeds
then the first 10:10 feed has cell counts 2, 5, 3, 2, 5, 3
and the second 10:10 feed has cell counts 3, 5, 2, 3, 5, 2
and the first left-only feed has cell counts 4, 10, 6, 0, 0, 0
and the second left-only feed has cell counts 6, 10, 4, 0, 0, 0
```

Measure left vs right from `sampled_stance` on the joined rows, not from string matching on post ids. Extra labels equal assigned slots minus original remaining, counted only where assigned slots exceed original remaining. Unused remaining equals original remaining minus assigned slots, counted only where original remaining exceeds assigned slots. Both of those must match `FeedKindCounts` for the fixture.

### `tests/test_shuffle_feed.py`

Class `TestShuffleFeed`.

```text
given a list of 20 post ids and user_id=1
when shuffle_feed is called twice
then both results are equal
and the result is a permutation of the input

given the same list and user_id=2
when shuffle_feed
then the order is not required to match user_id=1, and the result is still a permutation
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
PYTHONPATH=. uv run pytest experiments/generate_study_user_assignments_2026_09_08/tests -q
```

Expected: exit 0.

Live command (run in Step 2, not this step):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
  --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
```

A run with no remaining labels path exits non-zero and names that URI.

## Must pass

- Imports from `run.py` resolve.
- `README.md` names 10:10 then left-only, the steal-within-party rule, and the pytest command.
- `PYTHONPATH=. uv run pytest experiments/generate_study_user_assignments_2026_09_08/tests -q` exits 0.
- Every `TestAssignFeeds` case above is present and green.
- `count_feed_kinds(45542, 32015)` matches 3,202 / 13,522 / 677 / 3,879.
- Product scripts, catalogs, the remaining labels CSV, and the assignment Lambda are unchanged.
- No file was added under `/workspace/tests/`.

## Must fail

- Hash mismatch on the pinned remaining-labels URI.
- Hash mismatch or wrong row count on the pinned new catalog.
- Missing remaining-label columns, duplicate remaining ids, or remaining count less than 1.
- A remaining id in neither catalog, or in both catalogs.
- `count_feed_kinds` when leftover left remaining would be less than 0.
- A 10:10 feed that takes a right post for a left slot.
- A left-only feed that takes a right post.
- A feed with a repeated post id.
- Second upload to the same S3 key (live proof is Step 2).
- `PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py` with no `--remaining-labels`.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds the Python modules with stub bodies and a thin `main` that calls parse, load, join, assign, write, print. Write `README.md` in this phase so the file list is locked.

Phase 3 locks the dataclasses and public function signatures. Bodies stay `raise NotImplementedError`.

Phase 4 writes the pytest files from the given/when/then blocks above. Tests must fail for `NotImplementedError` or a wrong result, not for missing imports.

Phase 5 implements in this order, one commit per unit of work:

1. `README.md` and `constants.py`
2. `count_feed_kinds` until `test_count_feed_kinds.py` is green
3. `join_remaining_to_catalogs` until `test_join_remaining.py` is green
4. `assign_feeds` party mix, fill order, no duplicates, leftover left-only, extra labels, until those `TestAssignFeeds` cases are green
5. steal within party until the steal case is green
6. preferred recipes until the recipe cases are green
7. `shuffle_feed` until `test_shuffle_feed.py` is green
8. `load_remaining_labels` for a local CSV, plus pinned-hash check
9. old catalog and new catalog loaders
10. local assignment CSV writer
11. `parse_args` / missing-path error until `test_parse_args.py` is green
12. `put_new` upload and `main` wiring

Phase 6 is complete when the pytest command exits 0, `run.py` imports resolve, `README.md` is present, and Step 2 can run the live command.
