# Step 2: Map dump rows, load hive raw runs, and sample before preprocess writes

## Goal

Teach Bluesky preprocess to read hive-partitioned dump parquet from a raw run, map warehouse columns onto the Bluesky ingest record shape, and sample kept rows after filters immediately before write. Wire `--config` so the dump YAML supplies dataset id and sample settings. Keyword `--dataset-id` preprocess still writes every kept row.

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/preprocess_bluesky.py` `main` → `preprocess_records` → `data_platform/preprocessing/runner.py` `preprocess_records`.

**Task:** prove dump hive load → map to `SyncBlueskyPostModel` → existing preprocess filters → optional sample → write.

**Out of scope:** Running preprocess on the 3,450,253-row dump (Step 3). Changing Bluesky length, language, URL, or phone validators. Twitter and Reddit preprocess CLIs. Keyword Bluesky ingest. Feature generation. Curation. `CHANGELOG.md`. Editing Step 1 YAML keys.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/preprocessing/runner.py` | `load_raw_records`, `preprocess_records`, `export_preprocessed_records` |
| `/workspace/data_platform/preprocessing/preprocess_bluesky.py` | `--dataset-id` CLI |
| `/workspace/data_platform/models/sync.py` | `SyncBlueskyPostModel` fields, `extra="forbid"` |
| `/workspace/data_platform/ingestion/generate_record_id.py` | `attach_record_id(row, INTEGRATION_BLUESKY)` |
| `/workspace/data_platform/ingestion/integrations/bluesky.py` | Live URL shape `https://bsky.app/profile/{handle}/post/{rkey}` |
| `/workspace/data_platform/ingestion/data_dumps/reddit/sample.py` | Algorithm R to copy, not import |
| `/workspace/data_platform/ingestion/data_dumps/reddit/transform.py` | Dump-to-ingest mapper pattern |
| `/workspace/data_platform/utils/config_paths.py` | `load_yaml_config`, `resolve_config_path` |
| `/workspace/data_platform/utils/storage.py` | `load_records` expects `posts.parquet` today |
| `/workspace/lib/constants.py` | `REPO_ROOT` |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_bluesky.py` | Existing `--dataset-id` path must still pass |
| `/workspace/tests/data_platform/conftest.py` | `make_post_row`, `data_root` |

## Files allowed to change

- `/workspace/data_platform/ingestion/data_dumps/bluesky/transform.py` (new)
- `/workspace/data_platform/ingestion/data_dumps/bluesky/load_raw.py` (new)
- `/workspace/data_platform/preprocessing/sample.py` (new)
- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/data_platform/preprocessing/preprocess_bluesky.py`
- `/workspace/tests/data_platform/ingestion/test_bluesky_dump_preprocess.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_bluesky.py` only if an existing test must keep compiling after the `preprocess_records` signature change

Do not edit the plan package during implementation.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/publish_dump_to_raw.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/preprocessing/preprocess_reddit.py`
- `/workspace/data_platform/preprocessing/preprocess_twitter.py`
- `/workspace/data_platform/models/sync.py`
- `/workspace/data_platform/ingestion/generate_record_id.py`
- `/workspace/data_platform/preprocessing/validators/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Decision (locked)

- Mapping happens at preprocess load, not in the Step 1 copy.
- `did` is not kept on the ingest row. `author_handle` is the DID string. `url` is `https://bsky.app/profile/{did}/post/{rkey}` where `rkey` is the last `/` segment of `uri`.
- `like_count`, `repost_count`, `reply_count`, and `quote_count` are `0`.
- `sync_timestamp` is the raw run directory name.
- `created_at` is UTC ISO-8601 from the dump timestamp, using `datetime.isoformat` like Reddit dump.
- Sample after `apply_integration_specific_filters` and before `export_preprocessed_records`.
- Do not import `data_platform.ingestion.data_dumps.reddit.sample`. Copy Algorithm R into `data_platform/preprocessing/sample.py`.

## Contracts to lock

Add `dump_post_to_sync_row(row: Mapping[str, object], sync_timestamp: str) -> dict[str, object]` in `transform.py`.

- Required dump keys: `uri`, `did`, `created_at`, `text`.
- Raise `KeyError` when a required key is missing.
- Raise `ValueError` when `uri` or `did`, after strip, is empty, or when `uri` has no `/`.
- `created_at` conversion: if the value is a `datetime`, use timezone-aware UTC `isoformat()`. If it is a string, parse with `pandas.to_datetime(..., utc=True)` then `isoformat()`.
- Call `attach_record_id` with `INTEGRATION_BLUESKY`.
- Return a dict that `SyncBlueskyPostModel.model_validate` accepts. Do not include `did`.

Add `load_hive_dump_posts(run_dir: Path, sync_timestamp: str) -> list[dict[str, object]]` in `load_raw.py`.

- Find `run_dir.rglob("*.parquet")`, skip `metadata.json`.
- Raise `FileNotFoundError` when no parquet files exist.
- Read each file with `pandas.read_parquet`.
- Drop a row when `uri`, `did`, or `text` is null or a blank string after strip. Do not raise on those rows.
- Map remaining rows with `dump_post_to_sync_row`.
- Concatenate in sorted parquet path order.

Change `load_raw_records` in `runner.py`:

- For each raw run dir, if `run_dir / raw_storage.records_filename` exists, keep today's load.
- Else if the run dir contains a child directory whose name starts with `date=`, load with `load_hive_dump_posts(run_dir, run_dir.name)` and extend `validated_rows`.
- Else keep today's `if not records_path.exists(): continue`.

Change `preprocess_records` in `runner.py` to:

```text
def preprocess_records(
    dataset_id: str,
    spec: PreprocessPlatformSpec,
    sample_size: int | None = None,
    sample_seed: int | None = None,
) -> Path
```

- After `apply_integration_specific_filters`, if `sample_size` is `None`, write every kept row (today's behavior).
- If `sample_size` is not `None` and `sample_seed` is `None`, raise `ValueError` matching `"sample_seed"`.
- If `sample_size` is not `None`, call `sample_rows(records, sample_size, sample_seed)` then export.
- `input_count` in metadata remains the post-dedupe pre-filter count, as today.
- Add `row_counts.sampled` equal to `len(records)` after sampling when sampling ran. Omit that key when `sample_size` is `None`.
- Add `sample_size` and `sample_seed` to metadata only when sampling ran.

Add in `preprocessing/sample.py`:

```text
MIN_SAMPLE_SIZE = 1

def sample_rows(records: pd.DataFrame, sample_size: int, sample_seed: int) -> pd.DataFrame
```

- Raise `ValueError` matching `"sample_size"` when `sample_size < 1`.
- If `len(records) <= sample_size`, return `records` unchanged (same index reset not required if already reset).
- Otherwise convert rows to a list of dicts, run Algorithm R with `random.Random(sample_seed)`, and return a new DataFrame with the original columns. Do not import Reddit dump `reservoir_sample`.

Change Bluesky CLI `main` in `preprocess_bluesky.py`:

```text
--dataset-id optional
--config optional Path
--sample-size optional int
--sample-seed optional int
```

- If both `--dataset-id` and `--config` are missing, raise `typer.BadParameter` matching `"dataset-id"` and `"config"`.
- If both are set, raise `typer.BadParameter` matching `"dataset-id"` and `"config"`.
- `--config` is resolved with `resolve_config_path(config, REPO_ROOT)` then `load_yaml_config`.
- Dataset id comes from YAML `dataset_id` when `--config` is set.
- YAML `preprocessing_params.sample_size` and `preprocessing_params.sample_seed` are used when `--config` is set.
- `--sample-size` / `--sample-seed` override YAML when passed.
- `--dataset-id` without `--config` passes `sample_size=None` and `sample_seed=None` unless `--sample-size` is passed, in which case `--sample-seed` is required.
- Call `run_preprocess_records(dataset_id, BLUESKY_SPEC, sample_size, sample_seed)`.

Update `preprocess_bluesky.preprocess_records` to accept the same optional sample arguments and forward them.

## Test design

Extend `/workspace/tests/data_platform/ingestion/test_bluesky_dump_preprocess.py`.

Mapper:

```text
given uri at://did:plc:abc/app.bsky.feed.post/rkey1, did did:plc:abc, text hello, created_at 2026-09-01T00:00:00+00:00
when dump_post_to_sync_row(row, "2026_09_01-00:00:00")
then SyncBlueskyPostModel.model_validate accepts the result
and author_handle is did:plc:abc
and url is https://bsky.app/profile/did:plc:abc/post/rkey1
and record_id equals attach_record_id on uri
and like_count, repost_count, reply_count, quote_count are 0
and did is not a key
and sync_timestamp is 2026_09_01-00:00:00

given missing uri
when dump_post_to_sync_row
then raise KeyError

given uri without a slash
when dump_post_to_sync_row
then raise ValueError
```

Hive load:

```text
given a raw run dir with date=2026-09-01/hour=00/a.parquet and hour=01/b.parquet
when load_hive_dump_posts(run_dir, run_dir.name)
then rows from both files are returned in sorted path order
and each row validates as SyncBlueskyPostModel

given a blank text row among valid rows
when load_hive_dump_posts
then the blank row is dropped and valid rows remain

given a run dir with no parquet
when load_hive_dump_posts
then raise FileNotFoundError
```

Sample:

```text
given a 5-row frame and sample_size 3 and seed 20260901
when sample_rows
then len(result) is 3
and a second call with the same seed returns the same uri set

given 2 rows and sample_size 5
when sample_rows
then both rows are returned

given sample_size 0
when sample_rows
then raise ValueError matching sample_size
```

Preprocess integration with `data_root`:

```text
given a completed hive raw run of 3 valid-length English posts and sample_size 2 seed 20260901
when preprocess_records(dataset_id, BLUESKY_SPEC, 2, 20260901)
then the preprocessed file has 2 rows
and metadata row_counts.sampled is 2
and sample_size is 2

given the same raw run and sample_size None
when preprocess_records(dataset_id, BLUESKY_SPEC)
then all kept rows are written
and metadata has no sample_size key
```

Existing `/workspace/tests/data_platform/preprocessing/test_preprocess_bluesky.py` must still pass.

Tests fail with `NotImplementedError` / import errors until this step implements the units of work, then pass.

## Pass / fail

Pass:

- Hive dump raw runs load and map onto `SyncBlueskyPostModel`.
- Sampling runs after filters and before write when `sample_size` is set.
- `--dataset-id` without sample still writes every kept row.
- `PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_bluesky_dump_preprocess.py tests/data_platform/preprocessing/test_preprocess_bluesky.py -q` exits 0.
- `PYTHONPATH=. uv run pytest tests/data_platform/preprocessing -q` exits 0 with no new failures.

Fail:

- Keyword Bluesky ingest changes.
- Twitter or Reddit preprocess CLIs gain `--config`.
- Sampling happens before filters.
- Dump `did` remains on preprocessed rows.
