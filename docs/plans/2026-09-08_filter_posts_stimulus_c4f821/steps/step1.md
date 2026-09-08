# Step 1: Add the load, cleanup, sample, and upload command

## Scope

- **Caller:** `experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py` `main`
- **Task:** Download the pinned combined stimulus parquet, check SHA-256 and row count, drop previously used posts, drop duplicate ids, drop duplicate text, sample up to 1700 posts per political-stance by LLM-toxicity cell, write local `dataset.parquet`, upload that file to S3 with `put_new`, print counts, and write `RESULTS.md`.
- **Out of scope:** pytest, editing the experiment README, relabeling, curation YAML edits, `sample_data_to_mirror.py`, generating mirrors, changing product curate scripts, overwriting the combined source parquet.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Required module names, S3 bucket, S3 prefix, 10200-post aim, 1700 per cell. Do not edit. |
| `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/load.py` | Download, hash check, local cache, `CampaignObjectStore.get` |
| `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/write.py` | Local parquet bytes, `put_new`, RESULTS.md shape |
| `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/crosstab.py` | Stance rows `left`/`right`, toxicity columns `low`/`medium`/`high` |
| `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/sources.py` | Combined column names, sort columns, bucket name |
| `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/RESULTS.md` | Pinned source SHA-256 `f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0`, 55573 rows |
| `/workspace/data_platform/preprocessing/previously_used_stimuli.py` | `load_previously_used_stimuli_ids` |
| `/workspace/shared/data/registry.py` | `DATASETS`, Part 1 and Part 2 stimuli entries |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `CampaignObjectStore`, `parse_s3_uri`, `put_new` |
| `/workspace/data_platform/utils/object_store.py` | `sha256_hex` |
| `/workspace/lib/constants.py` | `REPO_ROOT` |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py` (new)
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/sources.py` (new)
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/load_raw_candidate_dataset.py` (new)
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/cleanup_raw_candidate_dataset.py` (new)
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/sample_raw_candidate_dataset.py` (new)
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/upload_filtered_candidate_dataset.py` (new)
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/.gitignore` (new)
- `/workspace/.gitignore` (ignore local parquet and cache under this experiment folder only)

## Files forbidden to change

- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/curate/configs/**`
- `/workspace/data_platform/preprocessing/previously_used_stimuli.py`
- `/workspace/shared/data/registry.py`
- `/workspace/tests/**`
- The combined source S3 object
- `/workspace/CHANGELOG.md` until Step 2 has a live S3 object and RESULTS.md

## Pinned candidate source

| Field | Value |
|-------|-------|
| Object | `s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet` |
| SHA-256 | `f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0` |
| Rows | 55573 |
| Columns | the 17 combined columns in `COMBINED_COLUMNS` from `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/sources.py` |

A hash mismatch or a wrong row count raises `ValueError`. A missing source object raises `FileNotFoundError`.

## Cleanup contract

Apply these steps in this order. Sort once before dropping duplicates, using `integration` ascending, then `source_dataset_id` ascending, then `source_record_id` ascending, with `kind="mergesort"`. Reset the index after each drop that removes rows.

1. Drop rows whose `record_id` is in `load_previously_used_stimuli_ids(DATASETS)`.
2. Drop rows whose `text` equals an `original_text` value from any registry stimuli dataset (`STUDY_PHASE_2_PART_1_STIMULI` and `STUDY_PHASE_2_PART_2_STIMULI`). Compare as `str`.
3. Drop duplicate `record_id`, keep first.
4. Drop duplicate `text`, keep first.

Return a cleanup summary with integer counts for rows before cleanup, rows dropped at each step, and rows after cleanup.

On the pinned candidate file, expected live counts are:

| Stage | Rows remaining | Rows dropped at this step |
|-------|---------------:|--------------------------:|
| Start | 55573 | 0 |
| After previously used record ids | 55573 | 0 |
| After previously used original text | 55531 | 42 |
| After duplicate `record_id` | 54960 | 571 |
| After duplicate `text` | 54472 | 488 |

A missing required column raises `ValueError`.

## Sample contract

Cells are the six pairs of `political_stance` in (`left`, `right`) and `llm_toxicity_tier` in (`low`, `medium`, `high`).

`TARGET_PER_CELL = 1700`. `SAMPLE_SEED = 42`.

For each cell, if the cleaned cell has 1700 or more rows, sample 1700 rows without replacement with `random_state=SAMPLE_SEED`. If the cleaned cell has fewer than 1700 rows, keep every row in that cell. If a cell has 0 rows, raise `ValueError`.

Concatenate the six cell frames. Sort the sampled table by `integration`, `source_dataset_id`, `source_record_id` with `kind="mergesort"`. Reset the index.

On the pinned candidate file after the cleanup above, expected live cell sizes before sampling are:

| political_stance | low | medium | high |
|------------------|----:|-------:|-----:|
| left | 17644 | 16903 | 3638 |
| right | 9022 | 6203 | 1062 |

Expected sampled counts:

| political_stance | low | medium | high | total |
|------------------|----:|-------:|-----:|------:|
| left | 1700 | 1700 | 1700 | 5100 |
| right | 1700 | 1700 | 1062 | 4462 |
| total | 3400 | 3400 | 2762 | 9562 |

Expected `sampled_rows=9562`. Do not raise because the total is not 10200. Print `right_high_available=1062` and `right_high_shortfall=638`.

The sampled parquet keeps the same 17 columns in the same order as the candidate file.

## Outputs

| Output | Path |
|--------|------|
| Local parquet | `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` |
| S3 parquet | `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` |
| S3 key | `experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` |
| Report | `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/RESULTS.md` |
| Cache | `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/cache/` (gitignored) |

Upload with `CampaignObjectStore.put_new`. The write fails if the S3 key already exists.

Gitignore `cache/` and `dataset.parquet` under this experiment folder. Do not commit the parquet.

## Crosstab and RESULTS.md

Reuse `stance_by_toxicity` and `stance_by_toxicity_by_integration` from `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/crosstab.py`. Do not copy those functions.

`RESULTS.md` must include:

- The run command
- Candidate source URI, SHA-256, and row count
- Cleanup drop counts for each step
- Cleaned stance by toxicity table
- Sampled stance by toxicity table
- Sampled row count, local path, S3 URI, and SHA-256
- A sentence that the right-high cell kept every cleaned post because it had fewer than 1700 posts

Stdout prints `candidate_rows=55573`, `cleaned_rows=54472`, `sampled_rows=9562`, the S3 URI, SHA-256, and both JSON tables (cleaned and sampled).

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py
```

Expected stdout includes `candidate_rows=55573`, `cleaned_rows=54472`, `sampled_rows=9562`, `s3_uri=s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet`, and `dataset_sha256=`.

## Work

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then live checks below, written in the `run.py` module docstring.

### Modules

Keep functions under 20 lines. Use a frozen dataclass for the pinned candidate source. Do not pass unstructured dictionaries for source identity.

`sources.py` holds the pinned candidate URI, SHA-256, row count, output S3 key, `TARGET_PER_CELL`, `SAMPLE_SEED`, and sort columns.

`load_raw_candidate_dataset.py` downloads the pinned object through `CampaignObjectStore.get`, checks SHA-256 with `sha256_hex`, checks row count, and may cache bytes under `cache/`.

`cleanup_raw_candidate_dataset.py` applies the four cleanup steps and returns the cleaned frame plus the drop-count summary.

`sample_raw_candidate_dataset.py` samples each of the six cells and returns the sampled frame.

`upload_filtered_candidate_dataset.py` writes local parquet bytes, uploads with `put_new`, and writes `RESULTS.md`.

`run.py` is the caller: load, cleanup, sample, write, print.

Reuse `CampaignObjectStore`, `parse_s3_uri`, `sha256_hex`, `load_previously_used_stimuli_ids`, and the combine crosstab helpers. Do not copy a new S3 client.

### Live given / when / then (Phase 4)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned combined parquet exists at SHA-256 f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0
when PYTHONPATH=. uv run python experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py
then candidate_rows=55573
and cleaned_rows=54472
and sampled_rows=9562
and local dataset.parquet exists
and S3 object experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet exists
and its SHA-256 matches the local file
and RESULTS.md contains the cleaned stance by toxicity table
and RESULTS.md contains the sampled stance by toxicity table
and the sampled right-high cell has 1062 rows
and stdout prints both tables

given the S3 dataset.parquet key already exists
when the command is run again
then the process raises FileExistsError and does not change the combined source object
```

## Must pass

- Imports from `run.py` resolve.
- Combined source SHA-256 and row count are checked before cleanup.
- Cleanup drop order matches the contract.
- Sampled columns match the 17-name contract in order.
- Product curate files and the experiment README are unchanged.

## Must fail

- Hash mismatch on the candidate parquet.
- Wrong candidate row count.
- Missing required column.
- Empty stance by toxicity cell.
- Second upload to the same S3 key.

## Implement-from-spec notes

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds the six modules with stub bodies and a thin `main` that calls load, cleanup, sample, write, print.

Phase 3 locks `CandidateSource` and the public function signatures. Continue without a pause because this run is full auto.

Phase 4 writes the given/when/then block in the `run.py` docstring. Do not add files under `tests/`.

Phase 5 implements in this order, one commit per unit of work:

1. `CandidateSource` and pinned constants
2. download and hash/row checks
3. previously used id and original-text drops
4. duplicate `record_id` and duplicate `text` drops
5. per-cell sample
6. local parquet write
7. S3 `put_new`
8. RESULTS.md writer and `main`

Phase 6 is complete when the modules exist, imports resolve, and Step 2 can run the live command.
