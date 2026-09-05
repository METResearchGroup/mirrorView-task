# Step 2: Sample kept dump comments at the end of Reddit preprocess

## Goal

Reddit preprocess reads the dump YAML, runs the current filter path, then samples up to 200,000 kept comments per source raw run before writing. Live `--dataset-id` runs still write every filtered row.

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/preprocess_reddit.py` `main`, which loads either `--config` or `--dataset-id` and calls `preprocess_records`. Sampling happens in `data_platform/preprocessing/runner.py` after integration-specific filters and before `export_preprocessed_records`.

**Task:** YAML sample size and seed → filter as today → sample per source raw run → write. No sample when `--dataset-id` is used.

**Out of scope:** Promoting dump files (step 1). Running the million-row dump (step 3). Bluesky and Twitter preprocess CLIs. Changing Reddit validators or length policy. Editing `data_platform/preprocessing/README.md`. `CHANGELOG.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-03_preprocess_reddit_dump_3d8a2c/plan.md` | Parent plan |
| `/workspace/docs/plans/2026-09-03_preprocess_reddit_dump_3d8a2c/steps/step1.md` | Dump YAML keys `preprocess.sample_size` and `preprocess.sample_seed` |
| `/workspace/data_platform/preprocessing/preprocess_reddit.py` | Typer `--dataset-id` entry. Add `--config` as the other exclusive option |
| `/workspace/data_platform/preprocessing/runner.py` | `preprocess_records` filter then export. Sampling goes after `apply_integration_specific_filters` |
| `/workspace/data_platform/preprocessing/runner.py` `load_raw_records` | Concatenates raw runs. Must keep a source-run column through filters so sampling can group |
| `/workspace/data_platform/utils/config_paths.py` | `load_yaml_config`, `resolve_config_path` |
| `/workspace/lib/constants.py` | `REPO_ROOT` for resolving `--config` |
| `/workspace/data_platform/ingestion/data_dumps/reddit/sample.py` | Reservoir sampler is for streams. Do not import it for an in-memory frame |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py` | Existing `--dataset-id` path must stay green |
| `/workspace/tests/data_platform/conftest.py` | `data_root` fixture |

## Files allowed to change

- `/workspace/data_platform/preprocessing/preprocess_reddit.py`
- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/data_platform/preprocessing/sample_records.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_sample.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py` only if `--dataset-id` tests need a default `sample_size=None` call

Plan package files under `/workspace/docs/plans/2026-09-03_preprocess_reddit_dump_3d8a2c/` may already be on this branch. Do not rewrite them during implementation.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/README.md`
- `/workspace/data_platform/preprocessing/validators/**`
- `/workspace/data_platform/preprocessing/content_filter_policy.py`
- `/workspace/data_platform/preprocessing/preprocess_bluesky.py`
- `/workspace/data_platform/preprocessing/preprocess_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/process_dump.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/README.md`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Decision (locked)

Sampling is per source raw run, not one cap across both months. Default dump YAML value is 200,000. Seed is 20260903.

If a run has fewer kept rows than `sample_size`, keep every remaining row from that run in the current order. Do not shuffle a short group.

The source-run column is an internal preprocess column. Drop it before `export_preprocessed_records` so `PreprocessedRedditCommentModel` still forbids extra fields.

`--config` and `--dataset-id` are mutually exclusive. Passing both raises `typer.BadParameter`. Passing neither raises `typer.BadParameter`. `--config` reads `dataset_id`, `preprocess.sample_size`, and `preprocess.sample_seed` from the dump YAML.

`sample_size` must be an integer >= 1 when present. Missing `preprocess` on the `--dataset-id` path means no sampling.

Do not change Bluesky or Twitter CLIs.

## Contracts to lock

`/workspace/data_platform/preprocessing/sample_records.py`:

```text
SOURCE_RAW_RUN_COLUMN = "source_raw_run"

def sample_records_per_source_run(
    records: pd.DataFrame,
    sample_size: int,
    sample_seed: int,
    source_column: str,
) -> pd.DataFrame
```

- Raise `ValueError` matching `"sample_size"` when `sample_size < 1`.
- Raise `KeyError` when `source_column` is missing.
- For each distinct source-run value, in sorted source-run order, if that group has more rows than `sample_size`, take a pandas sample of `sample_size` rows with `random_state=sample_seed`. If it has `sample_size` or fewer, keep those rows in current order.
- Concatenate the per-run frames and reset the index.
- Do not modify the input frame.

`/workspace/data_platform/preprocessing/runner.py` `load_raw_records`:

- Add `SOURCE_RAW_RUN_COLUMN` on every loaded row. The value is the run directory name (`Path.name`), for example `2025_05_01-00:00:00`.
- Empty datasets still return an empty frame. Include the source column in the empty-frame columns.

`/workspace/data_platform/preprocessing/runner.py` `preprocess_records`:

```text
def preprocess_records(
    dataset_id: str,
    spec: PreprocessPlatformSpec,
    sample_size: int | None,
    sample_seed: int | None,
) -> Path
```

- After `apply_integration_specific_filters`, if `sample_size` is None, do not sample.
- If `sample_size` is an int, `sample_seed` must also be an int. Call `sample_records_per_source_run`.
- Drop `SOURCE_RAW_RUN_COLUMN` after sampling and before export.
- `row_counts.input` stays the post-dedupe pre-filter count. `row_counts.output` is the row count after sampling.

Existing callers that only pass `dataset_id` and `spec` must pass `sample_size=None` and `sample_seed=None` from `preprocess_reddit.preprocess_records` when `--dataset-id` is used.

`/workspace/data_platform/preprocessing/preprocess_reddit.py` `main`:

```text
--dataset-id  optional
--config      optional Path
```

- Resolve `--config` with `resolve_config_path(config, REPO_ROOT)`.
- Load YAML with `load_yaml_config`.
- `dataset_id` comes from YAML `dataset_id`.
- `sample_size` and `sample_seed` come from YAML `preprocess.sample_size` and `preprocess.sample_seed`.

Numpy docstrings on the new public functions. The Reddit preprocess module docstring must show both run lines:

```bash
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_reddit.py \
  --dataset-id reddit_<uuid>

PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_reddit.py \
  --config data_platform/ingestion/data_dumps/reddit/pushshift_dump.yaml
```

## Tests that must pass

Keep `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py` green, including `test_preprocess_records_writes_output`.

Add `/workspace/tests/data_platform/preprocessing/test_preprocess_sample.py`:

1. `sample_records_per_source_run` with two source runs of 5 keepers each and `sample_size=2` returns 2 rows per run, 4 total. The same seed returns the same ids.
2. A source run with 1 keeper and `sample_size=2` keeps that 1 row unshuffled.
3. `sample_size=0` raises `ValueError`.
4. Missing source column raises `KeyError`.
5. Full Reddit preprocess on two completed parquet raw runs, through `--config`, writes at most `sample_size` rows per source run after validators. Use bodies that pass the existing Reddit validators from `test_preprocess_reddit.py`.
6. Full Reddit preprocess with `--dataset-id` and no sample still writes every keeper, matching `test_preprocess_records_writes_output`.

Run:

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing/test_preprocess_sample.py tests/data_platform/preprocessing/test_preprocess_reddit.py -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing -q
```

Expected: exit 0 with no new failures.

## Pass / fail

Pass when dump YAML preprocess samples per source run after filters, live `--dataset-id` writes every keeper, designed tests are green, and the source-run column is absent from written records.

Fail if sampling happens before validators, if both months share one 200,000 cap, if Bluesky or Twitter CLIs change, or if `PreprocessedRedditCommentModel` validation fails because the source-run column was left on the frame.
