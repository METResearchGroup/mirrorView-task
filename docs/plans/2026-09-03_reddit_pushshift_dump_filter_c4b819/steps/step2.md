# Step 2: Sample 500,000 keepers per month file and write filtered parquet

## Goal

Process one dump file at a time: stream comments, drop deleted or removed, reservoir-sample up to 500,000 keepers with a fixed seed, map onto the ingest model, and write parquet. Add a CLI that defaults to the two named month files. Ignore dump artifacts in git. Point the stimuli runbook at the dump directory from the spec.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/data_dumps/reddit/process_dump.py` `main`, which calls `process_dump_file` once per input file.

**Task:** prove filter → sample → map → parquet for one file, then the default two-file CLI dispatch.

**Out of scope:** Live PRAW ingest. Changing Step 1 contracts. Editing the spec README. Changing `SyncRedditCommentModel`. The old toxicity experiment. Running against the real monthly dump files (they are not in the repo). `CHANGELOG.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/data_dumps/reddit/README.md` | Output names `filtered/RC_2025-{05/06}.parquet`, 500,000 sample, process files separately |
| `/workspace/data_platform/ingestion/data_dumps/reddit/reader.py` | `iter_dump_comments` |
| `/workspace/data_platform/ingestion/data_dumps/reddit/filters.py` | `keep_dump_comment` |
| `/workspace/data_platform/ingestion/data_dumps/reddit/transform.py` | `dump_comment_to_sync_row` |
| `/workspace/data_platform/utils/storage.py` | `_write_parquet` column order from the model field list |
| `/workspace/lib/timestamp_utils.py` | `get_current_timestamp` for `sync_timestamp` |
| `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` | Currently says dumps live in `data_platform/ingestion/dumps` |
| `/workspace/.gitignore` | Add dump zst and filtered parquet ignores |
| `/workspace/tests/data_platform/ingestion/test_reddit_data_dump.py` | Extend with sample, write, and CLI tests |

## Files allowed to change

- `/workspace/data_platform/ingestion/data_dumps/reddit/sample.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/process_dump.py`
- `/workspace/tests/data_platform/ingestion/test_reddit_data_dump.py`
- `/workspace/.gitignore`
- `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`
- `/workspace/data_platform/ingestion/data_dumps/reddit/filtered/.gitkeep`

Do not edit the plan package during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/data_dumps/reddit/README.md`
- `/workspace/data_platform/ingestion/data_dumps/reddit/models.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/reader.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/filters.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/transform.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/models/sync.py`
- `/workspace/experiments/fetch_reddit_pushshift_dump_2026_06_15/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add in `sample.py`:

```text
DEFAULT_SAMPLE_SIZE = 500_000
DEFAULT_SAMPLE_SEED = 20260615

def reservoir_sample(items: Iterator[T], sample_size: int, rng: random.Random) -> list[T]:
```

- If `sample_size` is less than 1, raise `ValueError` matching `"sample_size"`.
- Algorithm R: keep the first `sample_size` items, then for item number `i` (1-based) replace a uniform index in `[0, i)` when that index is less than `sample_size`.
- If the stream is shorter than `sample_size`, return all items in stream order.
- Do not load the full stream into a list first.

Add in `process_dump.py`:

```text
DUMP_DIR = Path("data_platform/ingestion/data_dumps/reddit")
FILTERED_DIR = DUMP_DIR / "filtered"
DEFAULT_DUMP_STEMS = ("RC_2025-05", "RC_2025-06")

def process_dump_file(
    input_path: Path,
    output_path: Path,
    sample_size: int,
    sample_seed: int,
    sync_timestamp: str,
) -> Path:
```

Behavior of `process_dump_file`:

- Raise `FileNotFoundError` if `input_path` is not a file.
- Raise `FileExistsError` if `output_path` already exists.
- Stream `iter_dump_comments(input_path)`, keep rows where `keep_dump_comment` is True, reservoir-sample with `random.Random(sample_seed)` and `sample_size`.
- Map sampled dump comments with `dump_comment_to_sync_row(..., sync_timestamp)`.
- Validate each mapped dict with `SyncRedditCommentModel.model_validate` and `model_dump()`.
- Create parent directories of `output_path`. Write parquet with pandas, `index=False`, columns in `SyncRedditCommentModel.model_fields` order.
- Return `output_path`.

CLI `main(argv: list[str] | None = None) -> None`:

- `--input-file` may be passed multiple times. Each value is a path.
- `--output-dir` defaults to `FILTERED_DIR`.
- `--sample-size` defaults to `DEFAULT_SAMPLE_SIZE`.
- `--seed` defaults to `DEFAULT_SAMPLE_SEED`.
- If no `--input-file`, process `DUMP_DIR / f"{stem}.zst"` for each stem in `DEFAULT_DUMP_STEMS`. Output name is `{stem}.parquet` under `--output-dir`.
- If `--input-file` is set, process those paths in order. Output name is `{input_path.stem}.parquet` under `--output-dir`.
- `sync_timestamp` is `get_current_timestamp()` once per `process_dump_file` call.
- `if __name__ == "__main__": main()`.

Module docstring on `process_dump.py` must include:

```text
PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/reddit/process_dump.py
```

and the single-file form with `--input-file`.

`.gitignore` additions:

```text
data_platform/ingestion/data_dumps/reddit/*.zst
data_platform/ingestion/data_dumps/reddit/filtered/*.parquet
```

Keep `filtered/.gitkeep` tracked.

In `docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`, replace `data_platform/ingestion/dumps` with `data_platform/ingestion/data_dumps`. Keep the sentence that dump rows follow the same models as other ingest.

## Test design

Add test classes `TestReservoirSample`, `TestProcessDumpFile`, `TestMain`. Reuse the Step 1 zst fixture helper. Monkeypatch `get_current_timestamp` in process tests. Call `main` with argv lists and `tmp_path` files. Do not read real month dumps.

```text
given a stream of 5 items and sample_size 3 and Random(0)
when reservoir_sample(iter(items), 3, Random(0))
then length is 3
and running again with Random(0) returns the same 3 items

given a stream of 2 items and sample_size 5
when reservoir_sample(...)
then return both items in stream order

given sample_size 0
when reservoir_sample(...)
then raise ValueError matching "sample_size"

given a zst with 4 keepers and 1 deleted comment, sample_size 2, seed 1
when process_dump_file(input, output, 2, 1, "2026_09_03-12:00:00")
then output parquet exists
and row count is 2
and every row passes SyncRedditCommentModel
and no row author or body is [deleted] or [removed]
and sync_timestamp on every row is the argument

given 2 keepers and sample_size 10
when process_dump_file(...)
then parquet row count is 2

given output_path already exists
when process_dump_file(...)
then raise FileExistsError
and the existing file is unchanged

given a missing input file
when process_dump_file(...)
then raise FileNotFoundError

given two zst files passed as --input-file and --output-dir tmp
when main(argv)
then two parquet files named after the input stems exist
and get_current_timestamp is used for sync_timestamp
```

Step 1 tests stay green.

## Implementation notes (implement-from-spec)

Scaffold means adding `sample.py` and `process_dump.py` with `raise NotImplementedError` bodies, plus `filtered/.gitkeep`. Do not implement sampling or write in scaffold.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope.
2. Phase 2 scaffold. Stub `reservoir_sample` and `process_dump_file` / `main`. Add `filtered/.gitkeep`. Commit.
3. Phase 3 contracts. Confirm signatures and constants. Bodies stay stubs. Full auto. Commit only if signatures change.
4. Phase 4 test design. Add the new tests. They must fail for `NotImplementedError`. Commit.
5. Phase 5 units, in this order, one commit each:
   1. Implement `reservoir_sample`. Its tests pass.
   2. Implement `process_dump_file`. File processor tests pass. Sample tests stay green.
   3. Implement `main`, gitignore, runbook path, and CLI tests. All Step 2 tests pass.
6. Phase 6. Run the must-pass commands. Confirm README, live ingest, models, and experiment tree are untouched.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_reddit_data_dump.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0.

```bash
cd /workspace
git diff --name-only origin/main -- data_platform/ingestion/data_dumps/reddit/README.md
```

Expected: that path is listed only because it already existed on the dump branch. `git diff origin/get-reddit-data-dumps -- data_platform/ingestion/data_dumps/reddit/README.md` is empty.

## Must fail / not happen

- README edited.
- Live Reddit ingest or `SyncRedditCommentModel` edited.
- Experiment package edited.
- Output overwrite when the parquet already exists.
- Loading the full keeper stream into a list before sampling.
- Committing `.zst` or filtered `.parquet` files.
- Calling Perspective or any other comment filter beyond deleted or removed.
