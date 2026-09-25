# Setup

## Required datasets

Load `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` and `STUDY_PHASE_2_PART_2_AND_3_STIMULI` only through `shared.data.dataloader.load_dataset`. Those tables are the June Part 2 collection and the September Part 3 collection as one results file and one stimulus catalog. Votes on the same `post_id` from both collections count as one post.

## Filtering

Rows are not filtered on `attention_check_passed` or `phase`. Failed attention checks remain in the rate denominators.

## Duplicate votes

The build drops worker-post pairs that contain both keep and remove, then keeps the earliest remaining row per worker and post.

## Modal platform labels

Modal platform labels use keep when `keep_count > remove_count`, otherwise remove (ties become remove). The modal rule matches Part 2 modal labels.

## Four-cell agreement table

The four-cell table uses raw vote counts, not modal labels. Posts need at least three raters. Exact ties (`keep_count == remove_count`) are excluded from the four-cell universe.

## Run

```bash
PYTHONPATH=. uv run python experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py
```
