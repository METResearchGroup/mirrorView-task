# Step 5: Count remaining labels on the new catalog

## Scope

- **Caller:** `experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/run.py` `main`
- **Task:** Redo pull request 271 using the 10,000 row catalog from Step 4 as the new batch. Count unique `prolific_id` raters on the old catalog, give every new catalog id 5 remaining labels, drop remaining counts of 0 or less, write the CSV, upload it, and write `RESULTS.md`.
- **Out of scope:** pytest, study phase 2 part 1, looking up new catalog ids in the old results file, editing the old remaining-label CSV, generating flips, running this step after a Step 4 pause.

## Dependencies

Step 4 has written `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` with 10,000 unique `post_primary_key` values. Pin that file's SHA-256 from the Step 4 `RESULTS.md`. Do not start if Step 4 exited 1.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-08_upsample_stimuli_dca950/plan.md` | Expected totals 27557 old, 50000 new |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py` | Caller shape |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/calculate.py` | Unique rater math, overlap check, drop remaining 0 or less |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/load.py` | Old catalog and results loaders |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/write.py` | CSV bytes, `put_new`, `RESULTS.md` |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/constants.py` | `REQUIRED_LABELS_PER_POST = 5` |
| `/workspace/docs/plans/2026-09-08_required_label_count_per_post_5fd9ba/steps/step1.md` | Unique rater contract |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/README.md` (new)
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/constants.py` (new)
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/load.py` (new)
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/calculate.py` (new)
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/write.py` (new)
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/run.py` (new)
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/.gitignore` (new)
- `/workspace/.gitignore` (ignore cache under this folder)
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/RESULTS.md` after the live run
- `/workspace/CHANGELOG.md` after the live S3 object exists

## Files forbidden to change

- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/**`
- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/README.md`
- `/workspace/tests/**`
- The old remaining-label S3 object
- The 10,000 row catalog S3 object after it exists

## README contract

Write `README.md` first. Start with the same agent read-only banner as the filter-posts README. After it is committed, later steps must not edit it.

The README must say the study needs 5 labels per post, that this value lives in `constants.py`, that the old batch is unchanged from pull request 271, and that the new batch is the 10,000 row catalog from `experiments/curate_study_2_phase_3_stimuli/`. Name output columns `id`, `number_of_times_to_label`, and `batch`. Include the run command.

## Contracts

Reuse the unique rater rules from pull request 271. Copy `calculate.py` logic rather than importing it, so the v1 experiment stays untouched. `REQUIRED_LABELS_PER_POST` is 5.

Old catalog: `load_dataset("STUDY_PHASE_2_PART_2_STIMULI")`, id column `post_primary_key`, 10,000 unique ids.

Old results: `load_dataset("STUDY_PHASE_2_PART_2_RESULTS_FULL")`. Rater is `prolific_id`. Empty `post_id` or `prolific_id` cells do not count.

New catalog: download the pinned Step 4 CSV. Id column `post_primary_key`. Expected 10,000 unique ids. Every new id gets remaining labels 5.

If any id appears in both batches, raise `ValueError`. Drop remaining counts of 0 or less. Sort by `batch` with `old` first, then by `id`, `kind="mergesort"`.

Expected totals on the current old files, if the catalog has 10,000 new ids and no overlap:

| Batch | Posts | Remaining labels |
| ----- | ----: | ---------------: |
| old | 8899 | 27557 |
| new | 10000 | 50000 |
| total | 18899 | 77557 |

## Outputs

| Output | Path |
|--------|------|
| Local CSV | `experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv` |
| S3 CSV | `s3://mirrorview-experimental-artifacts/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv` |
| Report | `experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/RESULTS.md` |

Upload with `put_new`. A second upload of that key must fail.

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/run.py
```

Expected stdout includes `old_posts=8899`, `old_labels=27557`, `new_posts=10000`, `new_labels=50000`, `total_posts=18899`, `total_labels=77557`.

## Live given / when / then (Phase 4)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and Step 4 wrote the 10000 row catalog
when PYTHONPATH=. uv run python experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/run.py
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
and the old remaining-label CSV is unchanged
```

## Must pass

- Old remaining labels still 27,557 on 8,899 posts.
- New remaining labels 50,000 on 10,000 posts.
- V1 remaining-label experiment files are unchanged.

## Must fail

- Starting this step after a Step 4 pause.
- Overlap between old catalog ids and new catalog ids.
- Second upload to the v2 S3 key.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not add pytest.

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds `constants.py`, `load.py`, `calculate.py`, `write.py`, `run.py` with stub bodies: load old, load new catalog, count, write, print.

Phase 3 locks signatures. Continue without a pause.

Phase 5 implements in this order, one commit per unit of work:

1. Constants, including the pinned catalog SHA-256 from Step 4
2. Load old catalog, old results, and new catalog
3. Remaining-label count and overlap check
4. CSV `put_new`, `RESULTS.md`, `main`
5. README and `.gitignore`

Phase 6 is complete when the live command exits 0 with the expected totals and `RESULTS.md` is committed.
