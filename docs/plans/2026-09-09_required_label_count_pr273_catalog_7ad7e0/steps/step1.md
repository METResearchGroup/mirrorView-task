# Step 1: Add the load, count, and upload command

## Scope

- **Caller:** `experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/run.py` `main`
- **Task:** Fail if the output S3 key exists. Load the old catalog and old results, download the pinned 10,000-row catalog from pull request 273, count unique `prolific_id` raters per old post, give every new post 5 remaining labels, drop remaining counts of 0 or less, write local `required_label_count_per_stimulus_post.csv`, upload that file to S3, print totals, write `RESULTS.md`, and add `README.md`.
- **Out of scope:** pytest, study phase 2 part 1, generating mirrors, changing product scripts, overwriting the v1 or v2 remaining-label CSVs, looking up new-catalog ids in the old results file.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-09_required_label_count_pr273_catalog_7ad7e0/plan.md` | Confirmed decisions, unique rater rule, expected totals |
| `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/run.py` | Caller shape and live given/when/then |
| `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/calculate.py` | Unique rater math, overlap check, drop remaining 0 or less |
| `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/load.py` | Old catalog, old results, and CSV catalog loader |
| `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/write.py` | CSV bytes, `put_new`, `RESULTS.md` |
| `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/constants.py` | `REQUIRED_LABELS_PER_POST = 5` and pinned catalog identity |
| `/workspace/experiments/curate_study_2_phase_3_stimuli/RESULTS.md` | Pinned catalog SHA-256 `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139` |
| `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/write.py` | `require_output_keys_absent` before expensive work |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/README.md` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/constants.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/load.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/calculate.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/write.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/run.py` (new)
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/.gitignore` (new)
- `/workspace/.gitignore` (ignore cache and local CSV under this experiment folder only)

## Files forbidden to change

- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/**`
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/**`
- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/tests/**`
- The v1 remaining-label S3 object
- The v2 remaining-label S3 object
- The 10,000-row catalog S3 object
- `/workspace/CHANGELOG.md` until Step 2 has a live S3 object and `RESULTS.md`

## README contract

Write `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/README.md` first, then implement the modules to match it.

The README must:

1. Start with the same agent read-only banner used in `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. Say the study needs 5 labels on every stimulus post, and that this value lives in `constants.py`.
3. Describe the old batch: unique ids from `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv`, remaining labels equal 5 minus the number of unique `prolific_id` raters for that id in `shared/data/raw/study_phase_2_part_2/results/full.csv`.
4. Describe the new batch: every post in the 10,000-row catalog from pull request 273 needs 5 labels.
5. Name the output columns `id`, `number_of_times_to_label`, and `batch`, and say rows with remaining count of 0 or less are dropped.
6. Name the S3 bucket `mirrorview-experimental-artifacts` and the prefix `experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/`.
7. Name the output file `required_label_count_per_stimulus_post.csv`.
8. List these required files: `constants.py`, `load.py`, `calculate.py`, `write.py`, `run.py`.
9. Include the run command from the Main caller section below.

After this README is committed, later steps must not edit it.

## Pinned new catalog

| Field | Value |
|-------|-------|
| Object | `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` |
| SHA-256 | `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139` |
| Rows | 10000 |
| Id column | `post_primary_key` |

A hash mismatch, a wrong row count, or duplicate ids raises `ValueError`. A missing source object raises `FileNotFoundError`.

## Contracts

Copy remaining-label math from `experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/` rather than importing it.

`REQUIRED_LABELS_PER_POST` is 5.

Old catalog: `load_dataset("STUDY_PHASE_2_PART_2_STIMULI")`, id column `post_primary_key`, 10,000 unique ids.

Old results: `load_dataset("STUDY_PHASE_2_PART_2_RESULTS_FULL")`. Rater is `prolific_id`. Empty `post_id` or `prolific_id` cells do not count.

New catalog: download the pinned CSV. Id column `post_primary_key`. Expected 10,000 unique ids. Every new id gets remaining labels 5.

If any id appears in both batches, raise `ValueError`. Drop remaining counts of 0 or less. Sort by `batch` with `old` first, then by `id`, `kind="mergesort"`.

Call `require_output_key_absent` before loading. A second run must raise `FileExistsError` before the catalog download.

Expected totals on the current old files:

| Batch | Posts | Remaining labels |
| ----- | ----: | ---------------: |
| old | 8899 | 27557 |
| new | 10000 | 50000 |
| total | 18899 | 77557 |

## Outputs

| Output | Path |
|--------|------|
| Local CSV | `experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv` |
| S3 CSV | `s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv` |
| Report | `experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/RESULTS.md` |

Upload with `put_new`. A second upload of that key must fail.

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/run.py
```

Expected stdout includes `old_posts=8899`, `old_labels=27557`, `new_posts=10000`, `new_labels=50000`, `total_posts=18899`, `total_labels=77557`.

## Live given / when / then

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and pull request 273 wrote the 10000 row catalog
when PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/run.py
then old_posts=8899
and old_labels=27557
and new_posts=10000
and new_labels=50000
and total_posts=18899
and total_labels=77557
and every number_of_times_to_label value is greater than 0
and the S3 CSV SHA-256 matches the local file
and RESULTS.md records those totals

given the S3 CSV key already exists
when the command is run again
then the process raises FileExistsError
and the v1 remaining-label CSV is unchanged
and the v2 remaining-label CSV is unchanged
```

## Must pass

- Old remaining labels still 27,557 on 8,899 posts.
- New remaining labels 50,000 on 10,000 posts.
- V1 and v2 remaining-label experiment files are unchanged.

## Must fail

- Overlap between old catalog ids and new catalog ids.
- Second run after the S3 key exists.
- Hash mismatch or row-count mismatch on the pinned catalog.
