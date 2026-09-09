# Step 4: Count cells and write the 10,000 row catalog, or stop

## Scope

- **Caller:** `experiments/curate_study_2_phase_3_stimuli/run.py` `main`
- **Task:** Join the 10,200 post sample to its existing flips, join the unified 2,300 posts to the new flips, count stance by toxicity among posts that have a flip, stop with a non-zero exit if any cell is short of its target, otherwise sample the 10,000 row mix and write `flips.csv`.
- **Out of scope:** pytest, Perspective, Bedrock, remaining-label v2, copying the catalog into `shared/data/` or the webapp, overwriting the 10,200 sample or either flips parquet.

## Dependencies

Step 3 `RESULTS.md` has the named unified flips URI and SHA-256. Pin that digest. Existing sample flips stay pinned at SHA-256 `f3b791f226f8f69d3ddaf0737aab0a3aaf20ebb36d45a6d9b42dec8d1e148702`, 10,182 rows.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-08_upsample_medium_toxicity_stimuli_dca950/plan.md` | Cell targets, column mapping, pause rule |
| `/workspace/shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` | Columns `post_primary_key`, `original_text`, `sample_toxicity_type`, `sampled_stance`, `mirrored_text` |
| `/workspace/shared/flip_generation/models.py` | Flip parquet columns |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/load_raw_candidate_dataset.py` | Download and hash pattern |
| `/workspace/experiments/generate_flips_2026_09_08/RESULTS.md` | Existing flips URI |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/curate_study_2_phase_3_stimuli/README.md` (new)
- `/workspace/experiments/curate_study_2_phase_3_stimuli/sources.py` (new)
- `/workspace/experiments/curate_study_2_phase_3_stimuli/load.py` (new)
- `/workspace/experiments/curate_study_2_phase_3_stimuli/join_flips.py` (new)
- `/workspace/experiments/curate_study_2_phase_3_stimuli/sample_catalog.py` (new)
- `/workspace/experiments/curate_study_2_phase_3_stimuli/write.py` (new)
- `/workspace/experiments/curate_study_2_phase_3_stimuli/run.py` (new)
- `/workspace/experiments/curate_study_2_phase_3_stimuli/.gitignore` (new)
- `/workspace/.gitignore` (ignore cache and local `flips.csv` under this folder)
- `/workspace/experiments/curate_study_2_phase_3_stimuli/RESULTS.md` after a live run that writes the catalog, or after a stop that records the shortfall
- `/workspace/CHANGELOG.md` after a successful catalog upload

## Files forbidden to change

- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/shared/data/registry.py`
- `/workspace/webapp/**`
- `/workspace/experiments/generate_flips_2026_09_08/2026_09_08-20:31:31/flips.parquet` on S3
- `/workspace/tests/**`

## README contract

Write `README.md` first. Start with the same agent read-only banner as the filter-posts README. After it is committed, later steps must not edit it.

The README must name the six cell targets, the pause if a cell is short, the five output columns, and the run command.

## Join contract

Load the 10,200 sample and inner-join it to `s3://mirrorview-experimental-artifacts/experiments/generate_flips_2026_09_08/2026_09_08-20:31:31/flips.parquet` on `record_id`. Load the unified 2,300 posts and inner-join them to `s3://mirrorview-experimental-artifacts/experiments/generate_flips_2026_09_08/flips_unified_upsampled_posts.parquet` on `record_id`.

Keep toxicity from the original post table, not from a stale value. The 300 promoted posts must count as high. Concatenate the two joined tables. Fail if the same `record_id` appears in both pieces.

Print a stance by toxicity table of posts that have a flip.

## Cell targets and pause

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 1250 | 2500 | 1250 | 5000 |
| right | 1250 | 2500 | 1250 | 5000 |
| total | 2500 | 5000 | 2500 | 10000 |

If any cell has fewer rows than its target, print the available table, write `RESULTS.md` with that table and a sentence that the catalog was not written, exit with code 1, and do not upload `flips.csv`. Do not start Step 5.

If every cell meets its target, sample each cell with seed 42, without replacement. Sort the 10,000 rows by `post_primary_key` with `kind="mergesort"`.

## Catalog columns

Output columns, in this order:

1. `post_primary_key` from `record_id`
2. `original_text` from `original_text` on the flip row, which must equal `text` on the post row
3. `sample_toxicity_type` from `llm_toxicity_tier` using `low` to `sample_low_toxicity`, `medium` to `sample_middle_toxicity`, `high` to `sample_high_toxicity`
4. `sampled_stance` from `political_stance`, still `left` or `right`
5. `mirrored_text` from the flip row

If `original_text` and post `text` disagree, raise `ValueError`. Empty `mirrored_text` raises `ValueError`.

## Outputs

| Output | Path |
|--------|------|
| Local CSV | `experiments/curate_study_2_phase_3_stimuli/flips.csv` |
| S3 CSV | `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` |
| Report | `experiments/curate_study_2_phase_3_stimuli/RESULTS.md` |

Upload with `put_new` only when the catalog is written. A second upload of that key must fail.

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/curate_study_2_phase_3_stimuli/run.py
```

If the catalog is written, expected stdout includes `catalog_rows=10000`, `left=5000`, `right=5000`, `medium=5000`, `low=2500`, `high=2500`.

If a cell is short, expected stdout includes `catalog_written=false` and a non-zero exit.

## Live given / when / then (Phase 4)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the 10200 sample flips and the unified flips exist
when PYTHONPATH=. uv run python experiments/curate_study_2_phase_3_stimuli/run.py
then stdout prints the available stance by toxicity table
and if every cell meets its target then catalog_rows=10000
and the CSV has the five old-catalog columns
and S3 object experiments/curate_study_2_phase_3_stimuli/flips.csv exists
and if any cell is short then exit code is 1
and flips.csv is not uploaded
```

## Must pass

- Inner join drops posts with no flip.
- The 300 promoted posts count as high.
- Pause path writes no CSV when a cell is short.
- Success path writes 10,000 rows with the mapped toxicity names.

## Must fail

- Duplicate `record_id` across the sample join and the unified join.
- Text mismatch between post and flip.
- Second upload to the catalog key after a successful write.
- Starting Step 5 after a pause.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not add pytest.

Phase 1 names `run.py` `main` as the caller: load, join, count, maybe sample, write or stop.

Phase 2 scaffolds stubs with that wiring.

Phase 3 locks signatures. Continue without a pause.

Phase 5 implements in this order, one commit per unit of work:

1. Pinned sources
2. Load and inner join
3. Cell count and pause
4. Per-cell sample and column mapping
5. CSV `put_new`, `RESULTS.md`, `main`
6. README and `.gitignore`

Phase 6 is complete when the live command either writes the 10,000 row catalog or stops with the shortfall table. Commit `RESULTS.md` in either case.
