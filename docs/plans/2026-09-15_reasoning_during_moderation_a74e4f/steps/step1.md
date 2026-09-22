# Step 1: Pin the September three-group cohort

## Scope

- **Caller:** `experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py` `main`
- **Task:** Download the latest September Prolific CSVs with `--since-date 2026-09-09`, drop invalid workers, keep linked-fate keep or remove moderation trials, keep one rating per worker and post, drop worker-post pairs whose decisions conflict, require four or more raters, assign the three analysis groups, shuffle Post 1 and Post 2 per post with a deterministic seed, write the cohort and slim trials, print counts, and upload the cohort to the experimental S3 prefix.
- **Out of scope:** Model prompts, Hugging Face Jobs, thinking-token counting, human time tables, bag-of-words, `RESULTS.md`, editing `webapp/`, editing `shared/data/registry.py`, writing to `s3://jspsych-mirror-view-2026-09-09/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md` | Confirmed groups, September export, shuffle lock, snapshot counts |
| `/workspace/scripts/export_study_results.py` | Reuse `list_csv_keys`, `download_csvs`, `validate_loaded_csv`, `filter_manual_test_rows`, `INVALID_PROLIFIC_SUBSTRINGS`, `utc_midnight_ms` |
| `/workspace/webapp/public/plugins/plugin-moderation-trial.js` | Linked-fate rows shuffle Post 1 / Post 2 in the browser. The model cohort assigns its own stored order. Do not copy the human `pair_order` column. |
| `/workspace/webapp/public/main.js` | Real trials use `trial_type` `moderation-trial`. Practice uses `moderation-practice`. Time field is `response_time_ms`. |
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py` | Slim linked-fate keep or remove gate and per-post keep and remove counts. Do not copy the four-cell rules or the Phase 2 Part 2 registry load. |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/write.py` | `CampaignObjectStore.put_new` and `sha256_hex` |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Arrange-act-assert and one test class per function. The reasoning-token plan requires pytest under the experiment folder even though that file says experiment code often skips tests. |
| `/workspace/AGENTS.md` | Experiment `README.md` is one or two lines plus a redirect to `SETUP.md` and `RESULTS.md`. `SETUP.md` names required data. |

## Files allowed to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/README.md` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/SETUP.md` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/.gitignore` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/__init__.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/constants.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/__init__.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/conftest.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_slim_trials.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_dedupe_worker_post.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_assign_group.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_pair_order.py` (new)
- `/workspace/.gitignore` (ignore cache and outputs under this experiment folder only)

## Files forbidden to change

- `/workspace/webapp/**`
- `/workspace/shared/data/registry.py`
- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/scripts/export_study_results.py`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/**`
- `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md`
- Objects under `s3://jspsych-mirror-view-2026-09-09/`

## README and SETUP contract

Write `README.md` first. After this step, later steps must not rewrite the algorithm in `README.md`.

`README.md` must:

1. Start with the same agent read-only banner used in `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. Use one or two lines that name the experiment, then redirect to `SETUP.md` and `RESULTS.md`.

`SETUP.md` must:

1. Say labels come from the latest September 2026 Prolific export through `scripts/export_study_results.py` with `--since-date 2026-09-09`. Say the command does not load the registered Phase 2 Part 2 CSV.
2. Name the live study bucket as read-only: `s3://jspsych-mirror-view-2026-09-09/data/prolific/`.
3. Name the experimental bucket `mirrorview-experimental-artifacts` and prefix `experiments/reasoning_during_moderation_2026_09_15/`.
4. Say a post needs at least four unique raters after one rating per worker and post.
5. Name the three groups: `split` only for vote patterns 2 keep and 2 remove, 3 keep and 2 remove, or 2 keep and 3 remove; `unanimous_keep`; `unanimous_remove`. Say other disagreements stay out.
6. Say worker-post pairs with both keep and remove are dropped.
7. Say Post 1 and Post 2 order is shuffled per post with seed 0, stored on the cohort, and reused by both models and both prompt arms.
8. Name the snapshot counts from 2026-09-15: `csv_files=3075`, `split=2200`, `unanimous_keep=2256`, `unanimous_remove=208`, `eligible_posts=4664`. Say a later export may print larger counts. Say the command fails if any group is empty, or if `csv_files` is less than 3075.
9. Include the cohort command and the pytest command from the Main caller section.

## Public contracts

Keep functions under 20 lines. Use frozen dataclasses. Reuse `list_csv_keys`, `download_csvs`, `validate_loaded_csv`, `filter_manual_test_rows`, `INVALID_PROLIFIC_SUBSTRINGS`, `utc_midnight_ms`, `CampaignObjectStore.put_new`, `s3_uri`, and `sha256_hex`. Do not copy a new S3 client. Do not call `load_dataset` on a registry name. Do not edit the export script.

### `constants.py`

Pinned values:

- `SINCE_DATE` is `datetime.date(2026, 9, 9)`
- `STUDY_BUCKET` is `jspsych-mirror-view-2026-09-09`
- `STUDY_PREFIX` is `data/prolific/`
- `OUTPUT_S3_BUCKET` is `mirrorview-experimental-artifacts`
- `EXPERIMENT_S3_PREFIX` is `experiments/reasoning_during_moderation_2026_09_15`
- `COHORT_S3_KEY` is `experiments/reasoning_during_moderation_2026_09_15/outputs/cohort/three_group_cohort.parquet`
- `SLIM_TRIALS_S3_KEY` is `experiments/reasoning_during_moderation_2026_09_15/outputs/cohort/slim_trials.parquet`
- `METADATA_S3_KEY` is `experiments/reasoning_during_moderation_2026_09_15/outputs/cohort/export_metadata.json`
- `PAIR_ORDER_SEED` is `0`
- `MIN_CSV_FILES` is `3075`
- `MIN_RATERS` is `4`
- Snapshot expected counts: `split=2200`, `unanimous_keep=2256`, `unanimous_remove=208`

Frozen dataclasses at least:

- `CohortCounts` with `csv_files`, `split`, `unanimous_keep`, `unanimous_remove`, `eligible_posts`
- `PairOrder` with `post_1_role` and `post_2_role`, each `original` or `mirror`, and they must differ
- `CohortRunResult` with counts, local cohort path, local slim-trials path, local metadata path, cohort S3 URI, and SHA-256

### `cohort.py`

- `slim_trials(frame)` keeps a row only when all of these hold after lowercasing and stripping string fields: `evaluation_mode` is `linked_fate`, `decision` is `keep` or `remove`, `post_id` is non-empty and not the literal `nan`, `prolific_id` is non-empty, `trial_type` is `moderation-trial`. Raise `KeyError` when a required column is missing.
- `assert_stable_pair_text(trials)` asserts each kept `post_id` has exactly one distinct `original_text` and one distinct `mirror_text`. Raise `ValueError` on conflict. Raise `ValueError` when either text is empty.
- `drop_conflicting_worker_posts(trials)` drops every `(post_id, prolific_id)` pair that has more than one distinct `decision`.
- `dedupe_worker_post(trials)` sorts remaining rows by `post_id`, `prolific_id`, `time_elapsed`, `trial_index` with `kind="mergesort"`, then keeps the first row per `(post_id, prolific_id)`.
- `assign_group(keep_count, remove_count)` returns `split` when `(keep_count, remove_count)` is `(2, 2)`, `(3, 2)`, or `(2, 3)`; `unanimous_keep` when `remove_count == 0` and `keep_count >= 4`; `unanimous_remove` when `keep_count == 0` and `remove_count >= 4`; otherwise `None`.
- `build_cohort(trials)` aggregates `n_raters`, `keep_count`, and `remove_count` per `post_id`, keeps `n_raters >= 4`, assigns groups, drops rows whose group is `None`, and attaches `original_text`, `mirror_text`, and pair order. `n_raters` must equal `keep_count + remove_count`.
- `pair_order_for_post(post_id, seed=PAIR_ORDER_SEED)` hashes `f"{seed}:{post_id}"` with SHA-256, builds `numpy.random.Generator(numpy.random.PCG64(int.from_bytes(digest[:8], "big")))`, draws `rng.integers(0, 2)`, and returns `("original", "mirror")` when the draw is 0, else `("mirror", "original")`.
- `write_cohort(cohort, slim, metadata, experiment_dir)` writes local parquet and json under `experiments/reasoning_during_moderation_2026_09_15/outputs/cohort/`.
- `upload_cohort(body, key, store)` calls `store.put_new`. Raise `FileExistsError` when the key exists.
- `main` downloads or reuses the export CSVs, builds the cohort, refuses an empty group, refuses `csv_files < 3075`, writes local files, uploads with `put_new`, and prints counts.

Cohort column order:

| Column | Meaning |
|--------|---------|
| `post_id` | Post id |
| `original_text` | Stable original text |
| `mirror_text` | Stable mirror text |
| `group` | `split`, `unanimous_keep`, or `unanimous_remove` |
| `n_raters` | Integer at least 4 |
| `keep_count` | Integer |
| `remove_count` | Integer |
| `post_1_role` | `original` or `mirror` |
| `post_2_role` | The other role |

Slim-trial column order, after the worker-post cleanup, only for posts that remain in the cohort:

| Column | Meaning |
|--------|---------|
| `post_id` | Post id |
| `prolific_id` | Worker id |
| `decision` | `keep` or `remove` |
| `response_time_ms` | Numeric trial time |
| `trial_index` | jsPsych trial index |
| `time_elapsed` | jsPsych elapsed time |
| `group` | Cohort group for that post |

`export_metadata.json` must include `since_date`, `csv_files`, `split`, `unanimous_keep`, `unanimous_remove`, `eligible_posts`, and `built_at`.

Do not downsample. Do not copy human `pair_order` from the export. Do not include practice trials. Do not keep 4 keep and 1 remove, 1 keep and 4 remove, or any other leftover disagreement.

## Pytest files

Tests live under `experiments/reasoning_during_moderation_2026_09_15/shared/tests/`. They must not download S3. They must not read the live study prefix. Build frames in `conftest.py`. Use Arrange-Act-Assert. Name test classes `Test{FunctionName}`. Use `result` and `expected`. Patch with `unittest.mock` when a test needs a fake store.

### `tests/conftest.py`

Factory `trial_row(...)` builds one linked-fate `moderation-trial` row. Include a fixture with:

- post `A`: four keep ratings, stable texts
- post `B`: two keep and two remove
- post `C`: three keep and two remove
- post `D`: two keep and three remove
- post `E`: four remove
- post `F`: four keep and one remove (must drop)
- post `G`: three keep (must drop for too few raters)
- one practice row
- one `single` evaluation_mode row
- one worker who rated post `B` twice with the same decision
- one worker who rated post `C` as keep and as remove

### `tests/test_slim_trials.py`

Class `TestSlimTrials`.

```text
given mixed evaluation modes, trial types, and empty post ids
when slim_trials
then only linked-fate moderation-trial keep or remove rows with a usable post id remain
and practice rows are gone
and single-mode rows are gone

given two rows for one post_id with different original_text
when assert_stable_pair_text
then raise ValueError
```

### `tests/test_dedupe_worker_post.py`

Class `TestDropConflictingWorkerPosts` and class `TestDedupeWorkerPost`.

```text
given one worker with keep and remove on the same post
when drop_conflicting_worker_posts
then that worker-post pair is absent

given two identical keep rows for one worker and post, later trial_index larger
when dedupe_worker_post
then one row remains
and it is the earlier trial_index
```

### `tests/test_assign_group.py`

Class `TestAssignGroup` and class `TestBuildCohort`.

```text
given keep_count and remove_count pairs (2,2), (3,2), (2,3), (4,0), (0,4), (4,1), (3,0)
when assign_group
then split, split, split, unanimous_keep, unanimous_remove, None, None

given the conftest fixture
when build_cohort
then posts A, B, C, D, E are present
and F and G are absent
and each remaining post has post_1_role and post_2_role that differ
```

### `tests/test_pair_order.py`

Class `TestPairOrderForPost`.

```text
given post_id "A" and seed 0
when pair_order_for_post is called twice
then both results are equal
and the two roles are original and mirror in some order

given twenty distinct post ids and seed 0
when pair_order_for_post
then both ("original", "mirror") and ("mirror", "original") appear at least once
```

## Main caller

Pytest:

```bash
PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests -q
```

Expected: exit 0. After later steps add more tests under `shared/tests`, this command still exits 0.

Live command, after AWS keys are exported as in `AGENTS.md`:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py --write-counts
```

Expected stdout includes `csv_files=3075`, `split=2200`, `unanimous_keep=2256`, `unanimous_remove=208`, and `eligible_posts=4664` when the export matches the 2026-09-15 snapshot. A later export may print larger counts. Fail if any of the three groups is empty. Fail if `csv_files` is less than 3075.

Expected local files:

```text
experiments/reasoning_during_moderation_2026_09_15/outputs/cohort/three_group_cohort.parquet
experiments/reasoning_during_moderation_2026_09_15/outputs/cohort/slim_trials.parquet
experiments/reasoning_during_moderation_2026_09_15/outputs/cohort/export_metadata.json
```

Expected S3 objects under `s3://mirrorview-experimental-artifacts/experiments/reasoning_during_moderation_2026_09_15/outputs/cohort/`.

A second live upload to the same keys raises `FileExistsError`.

## Must pass

- Imports from `cohort.py` resolve.
- `README.md` redirects to `SETUP.md` and `RESULTS.md`.
- `SETUP.md` names the September export, the three groups, the shuffle seed, and the snapshot counts.
- `PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests -q` exits 0.
- Pair order for one `post_id` is stable under seed 0.
- Both pair orders appear across twenty post ids.
- Posts with 4 keep and 1 remove are absent from the cohort.
- Practice trials are absent from slim trials.
- Product scripts, the website, the registry, and the live study bucket are unchanged.
- No file was added under `/workspace/tests/`.

## Must fail

- Loading labels from the registered Phase 2 Part 2 CSV.
- Including `moderation-practice` rows.
- Keeping a worker-post pair with both keep and remove.
- Assigning `split` to 4 keep and 1 remove.
- Keeping a post with fewer than four raters.
- Copying human `pair_order` from the export CSV into the cohort.
- Using a non-deterministic shuffle such as `Math.random` or `random.random()` without the SHA-256 seed.
- A second `put_new` to the same cohort S3 key.
- Upload to `jspsych-mirror-view-2026-09-09`.
- `csv_files` less than 3075.
- An empty analysis group.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `cohort.py` `main` as the caller.

Phase 2 scaffolds the Python modules with stub bodies and a thin `main` that calls download, slim, conflict drop, dedupe, build, write, print. Write `README.md` and `SETUP.md` in this phase so the file list is locked.

Phase 3 locks the dataclasses and public function signatures. Bodies stay `raise NotImplementedError`.

Phase 4 writes the pytest files from the given/when/then blocks above. Tests must fail for `NotImplementedError` or a wrong result, not for missing imports.

Phase 5 implements in this order, one commit per unit of work:

1. `README.md`, `SETUP.md`, `.gitignore`, and `constants.py`
2. `slim_trials` and `assert_stable_pair_text` until `test_slim_trials.py` is green
3. `drop_conflicting_worker_posts` and `dedupe_worker_post` until `test_dedupe_worker_post.py` is green
4. `assign_group` and `build_cohort` until `test_assign_group.py` is green
5. `pair_order_for_post` until `test_pair_order.py` is green
6. local parquet and metadata writers
7. experimental `put_new` helper and `main` wiring

Phase 6 is complete when the pytest command exits 0, `cohort.py` imports resolve, `README.md` and `SETUP.md` are present, and the live command can run.
