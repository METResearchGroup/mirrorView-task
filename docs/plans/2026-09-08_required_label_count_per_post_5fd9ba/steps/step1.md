# Step 1: Add the load, count, and upload command

## Scope

- **Caller:** `experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py` `main`
- **Task:** Load the old catalog and old results, download the pinned 10,200-row new sample parquet, count unique `prolific_id` raters per old post, give every new post 5 remaining labels, drop remaining counts of 0 or less, write local `required_label_count_per_stimulus_post.csv`, upload that file to S3, print totals, write `RESULTS.md`, and add `README.md`.
- **Out of scope:** pytest, study phase 2 part 1, generating mirrors, changing product scripts, overwriting the new sample parquet, looking up new-sample ids in the old results file.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-08_required_label_count_per_post_5fd9ba/plan.md` | Confirmed decisions, unique rater rule, expected totals |
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_STIMULI`, `STUDY_PHASE_2_PART_2_RESULTS_FULL` |
| `/workspace/shared/data/dataloader.py` | `load_dataset` |
| `/workspace/shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` | Old catalog. Id column `post_primary_key`. 10,000 unique ids |
| `/workspace/shared/data/raw/study_phase_2_part_2/results/full.csv` | Old results. Id column `post_id`. Rater column `prolific_id` |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/RESULTS.md` | Pinned new sample SHA-256 `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9`, 10,200 rows |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/load_raw_candidate_dataset.py` | Download, hash check, local cache, `CampaignObjectStore.get` |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/sources.py` | `CandidateSource`, combined column names |
| `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/write.py` | Local bytes, `put_new`, `RESULTS.md` shape |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `CampaignObjectStore`, `parse_s3_uri`, `put_new` |
| `/workspace/data_platform/utils/object_store.py` | `sha256_hex` |
| `/workspace/lib/constants.py` | `REPO_ROOT` |
| `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/README.md` | Run-command README shape |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner and required-file list |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/README.md` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/constants.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/load.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/calculate.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/write.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/.gitignore` (new)
- `/workspace/.gitignore` (ignore local cache under this experiment folder only)

## Files forbidden to change

- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/shared/data/registry.py`
- `/workspace/shared/data/dataloader.py`
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/**`
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/**`
- `/workspace/data_platform/curate/**`
- `/workspace/tests/**`
- The new sample S3 object
- `/workspace/CHANGELOG.md` until Step 2 has a live S3 object and `RESULTS.md`

## README contract

Write `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/README.md` first, then implement the modules to match it.

The README must:

1. Start with the same agent read-only banner used in `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. Say the study needs 5 labels on every stimulus post, and that this value lives in `constants.py`.
3. Describe the old batch: unique ids from `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv`, remaining labels equal 5 minus the number of unique `prolific_id` raters for that id in `shared/data/raw/study_phase_2_part_2/results/full.csv`.
4. Describe the new batch: every post in the 10,200-row parquet from pull request 267 needs 5 labels.
5. Name the output columns `id`, `number_of_times_to_label`, and `batch`, and say rows with remaining count of 0 or less are dropped.
6. Name the S3 bucket `mirrorview-experimental-artifacts` and the prefix `experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/`.
7. Name the output file `required_label_count_per_stimulus_post.csv`.
8. List these required files: `constants.py`, `load.py`, `calculate.py`, `write.py`, `run.py`.
9. Include the run command from the Main caller section below.

After this README is committed, later steps must not edit it.

## Pinned new sample

| Field | Value |
|-------|-------|
| Object | `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` |
| SHA-256 | `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9` |
| Rows | 10200 |
| Id column | `record_id` |

A hash mismatch or a wrong row count raises `ValueError`. A missing source object raises `FileNotFoundError`. Duplicate `record_id` values raise `ValueError`.

## Old catalog and results contract

Load the old catalog with `load_dataset("STUDY_PHASE_2_PART_2_STIMULI")`. The id column is `post_primary_key`. Strip values. Drop empty cells and the literal `"nan"`. There must be 10,000 unique ids. Duplicate catalog ids raise `ValueError`. A missing `post_primary_key` column raises `ValueError`.

Load the old results with `load_dataset("STUDY_PHASE_2_PART_2_RESULTS_FULL")`. Required columns are `post_id` and `prolific_id`. Missing columns raise `ValueError`.

## Unique rater contract

A rater is `prolific_id`, not `participant_id`. Two study sessions by the same Prolific account count as one rater.

Keep results rows whose `post_id` and `prolific_id` are both non-empty after strip, and whose stripped values are not `"nan"`. For each `post_id`, count unique `prolific_id` values. Catalog ids that never appear get count 0.

Remaining labels for an old post equal `REQUIRED_LABELS_PER_POST` minus that unique rater count. Drop rows whose remaining count is 0 or less.

On the current files, unique rater counts on catalog ids are:

| Unique raters | Posts |
| ------------: | ----: |
| 0 | 1209 |
| 1 | 2414 |
| 2 | 2392 |
| 3 | 1796 |
| 4 | 1088 |
| 5 or more | 1101 |

Expected old remaining posts: 8899. Expected old remaining labels: 27557. Expected dropped old posts: 1101.

Do not filter by trial type.

## New batch contract

Every new `record_id` gets remaining labels equal to `REQUIRED_LABELS_PER_POST`, which is 5. Expected new posts: 10200. Expected new labels: 51000.

Do not look up new ids in the old results file.

## Combine contract

Output columns, in this order:

1. `id`
2. `number_of_times_to_label`
3. `batch`

`batch` is `old` or `new`. Old ids come from catalog `post_primary_key`. New ids come from parquet `record_id`.

If any id appears in both batches, raise `ValueError`.

Keep only rows where `number_of_times_to_label` is greater than 0.

Sort by `batch` with `old` first, then by `id`, with `kind="mergesort"`. Reset the index.

Expected combined rows: 19099. Expected combined labels: 78557. Expected old rows: 8899. Expected new rows: 10200.

## Outputs

| Output | Path |
|--------|------|
| Local CSV | `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv` |
| S3 CSV | `s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv` |
| S3 key | `experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv` |
| Report | `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/RESULTS.md` |
| Cache | `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/cache/` (gitignored) |

Write the CSV with `index=False`. Upload with `CampaignObjectStore.put_new`. The write fails if the S3 key already exists.

Gitignore `cache/` under this experiment folder in both `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/.gitignore` and `/workspace/.gitignore`. Root `.gitignore` already ignores `*.csv`, so the local CSV is not committed.

## RESULTS.md

`RESULTS.md` must include:

- The run command
- New sample URI, SHA-256, and row count
- Old catalog path and unique id count
- Unique rater rule: count unique `prolific_id` per `post_id`
- Local path, S3 URI, and SHA-256 of the CSV
- Total remaining labels
- Remaining labels for the old batch
- Remaining labels for the new batch
- Row counts overall, old, and new

Stdout prints `old_posts=8899`, `old_labels=27557`, `new_posts=10200`, `new_labels=51000`, `total_posts=19099`, `total_labels=78557`, the S3 URI, and the CSV SHA-256.

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
```

Expected stdout includes `old_posts=8899`, `old_labels=27557`, `new_posts=10200`, `new_labels=51000`, `total_posts=19099`, `total_labels=78557`, `s3_uri=s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv`, and `csv_sha256=`.

## Work

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then live checks below, written in the `run.py` module docstring.

### Modules

Keep functions under 20 lines. Use a frozen dataclass for the pinned new sample. Do not pass unstructured dictionaries for source identity.

`constants.py` holds required labels per post (5), registry names, column names, batch values `old` and `new`, the pinned new-sample URI, SHA-256, and row count, and the output S3 key.

`load.py` loads the old catalog and old results through `load_dataset`, and downloads the new sample through `load_raw_candidate_dataset` with this experiment's pin and `cache_dir` under this experiment folder.

`calculate.py` counts unique `prolific_id` values per old `post_id`, builds remaining counts for both batches, fails on overlapping ids, drops remaining counts of 0 or less, and sorts the table.

`write.py` writes local CSV bytes, uploads with `put_new`, and writes `RESULTS.md`.

`run.py` is the caller: load old, load new, calculate, write, print.

Reuse `CampaignObjectStore`, `parse_s3_uri`, `sha256_hex`, `load_dataset`, and `load_raw_candidate_dataset`. Do not copy a new S3 client.

### Live given / when / then (Phase 4)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned new sample parquet exists at SHA-256 9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9
when PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
then old_posts=8899
and old_labels=27557
and new_posts=10200
and new_labels=51000
and total_posts=19099
and total_labels=78557
and local required_label_count_per_stimulus_post.csv exists
and S3 object experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv exists
and its SHA-256 matches the local file
and every number_of_times_to_label value is greater than 0
and RESULTS.md contains total remaining labels 78557
and RESULTS.md contains old remaining labels 27557
and RESULTS.md contains new remaining labels 51000
and stdout prints those counts

given the S3 CSV key already exists
when the command is run again
then the process raises FileExistsError and does not change the new sample parquet
```

## Must pass

- Imports from `run.py` resolve.
- `README.md` exists and names unique `prolific_id` raters, required labels per post of 5, and the S3 prefix.
- New sample SHA-256 and row count are checked before counting.
- Old remaining labels use unique `prolific_id` per `post_id`, not row counts and not `participant_id`.
- Output columns are `id`, `number_of_times_to_label`, and `batch` in that order.
- Product scripts, the old catalog, the old results file, and the new sample parquet are unchanged.

## Must fail

- Hash mismatch on the new sample parquet.
- Wrong new sample row count.
- Missing `post_primary_key`, `post_id`, `prolific_id`, or `record_id`.
- Duplicate catalog ids or duplicate new `record_id` values.
- The same id in both batches.
- Second upload to the same S3 key.

## Implement-from-spec notes

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds the five Python modules with stub bodies and a thin `main` that calls load, calculate, write, print. Write `README.md` in this phase so the file list is locked.

Phase 3 locks the pinned new-sample dataclass and the public function signatures. Continue without a pause because this run is full auto.

Phase 4 writes the given/when/then block in the `run.py` docstring. Do not add files under `tests/`.

Phase 5 implements in this order, one commit per unit of work:

1. `README.md` and `constants.py`
2. load old catalog and old results
3. unique `prolific_id` counts and old remaining labels
4. download and hash/row checks for the new sample
5. new remaining labels, overlap check, drop remaining counts of 0 or less, sort
6. local CSV write
7. S3 `put_new`
8. `RESULTS.md` writer and `main`

Phase 6 is complete when the modules exist, imports resolve, `README.md` is present, and Step 2 can run the live command.
