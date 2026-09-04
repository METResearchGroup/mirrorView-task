# Step 4: Upload to S3 and write SUMMARY.md

## Goal

Upload every local training parquet to the locked bucket and prefix, then write `SUMMARY.md` with one table per classifier and one totals table.

## Caller / unit of work

The caller is `experiments/create_feature_generation_training_sets_2026_09_04/main.py` `main` with `--upload`.

After a successful `build_training_sets`, upload each written path. Then write `SUMMARY.md` from the local files. Row counts come from parquet. Size comes from the local file bytes.

Out of scope:

- changing join or walk rules
- editing the experiment README
- changing `lib/aws/s3.py`
- re-labeling source data

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-09-04_create_feature_generation_training_sets_05074f/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/README.md` | Bucket `met-ml-training`, prefix `mirrorview/create_feature_generation_training_sets_2026_09_04/`, SUMMARY tables |
| `/Users/mark/src/work/mirrorView-task/lib/aws/s3.py` | `S3.upload_file(local_path, key)` |
| `/Users/mark/src/work/mirrorView-task/experiments/finetune_qwen_model_2026_08_08/src/s3_upload.py` | Directory upload loop to copy the relative-key pattern from, not to import |
| `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/constants.py` | `S3_BUCKET`, `S3_PREFIX` |
| `/Users/mark/src/work/mirrorView-task/AGENTS.md` | Local AWS uses the default credential chain / `AWS_PROFILE`. Do not set a profile in code. |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/upload.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/summary.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/main.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/test_upload.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/test_summary.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/test_main.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/SUMMARY.md` (written by the production command, then committed)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/README.md`
- `/Users/mark/src/work/mirrorView-task/lib/aws/s3.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/hydrate.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/walk.py` unless `main` needs the returned path list and it already returns one
- `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data/**`
- `/Users/mark/src/work/mirrorView-task/data_platform/**`
- Any file outside the allowed list, except git commits of this work

## Decision (locked)

1. Reuse `lib.aws.s3.S3`. Construct `S3(S3_BUCKET)`. Do not add a second boto3 wrapper. Do not change `lib/aws/s3.py` to special-case parquet content type. Call `upload_file` without `content_type`, so bytes go up as they are.
2. The object key is `f"{S3_PREFIX}/{classifier_name}/{filename}"`, and `filename` is `{dataset_id}_{timestamp}.parquet`. Example: `mirrorview/create_feature_generation_training_sets_2026_09_04/is_political/bluesky_8ce4cf1f-8ab9-4373-a739-2a2ff2de400f_2026_09_04-12:00:00.parquet`.
3. Upload only paths returned by `build_training_sets`. Do not upload `.gitkeep`.
4. `size_mb` is `round(path.stat().st_size / 1_000_000, 2)` (decimal MB).
5. `n_rows` is `len(pd.read_parquet(path))`.
6. Each classifier table in `SUMMARY.md` has one row per uploaded file and columns `file`, `size_mb`, `n_rows`, `s3_prefix`. `s3_prefix` is the object key, which is the prefix plus classifier folder plus filename.
7. The final table has columns `category` and `n_rows`, and one row per classifier in `CLASSIFIER_NAMES` order. Classifiers with no files still appear with `n_rows` 0.
8. `SUMMARY.md` also states the bucket `met-ml-training` once at the top in a short sentence.
9. Fixture tests mock `S3.upload_file`. Fixture tests do not call AWS. The production command at the end of this step does call AWS.
10. `main --upload` builds local parquet, uploads, writes `SUMMARY.md`, and returns 0. Pass the same `--timestamp` used in step 3 so filenames match the files already on disk. If you do not know that timestamp, read it from any written parquet name rather than calling `get_current_timestamp` again. Do not add `--skip-build`.

## Contracts to lock

New `src/upload.py`:

```text
def s3_key_for(local_path: Path, output_root: Path) -> str
def upload_training_parquets(
    paths: list[Path],
    output_root: Path,
    *,
    s3_client: S3 | None = None,
) -> list[str]
```

`s3_key_for` takes a path under `output_root` and returns `S3_PREFIX / relative posix path`. `upload_training_parquets` uploads each file and returns the keys in the same order. Tests pass a fake `s3_client` with an `upload_file` method.

New `src/summary.py`:

```text
@dataclass(frozen=True)
class FileStat:
    classifier_name: str
    file: str
    size_mb: float
    n_rows: int
    s3_prefix: str

def collect_file_stats(paths: list[Path], output_root: Path) -> list[FileStat]
def render_summary_markdown(stats: list[FileStat]) -> str
def write_summary(stats: list[FileStat], path: Path) -> Path
```

`write_summary` writes `experiments/create_feature_generation_training_sets_2026_09_04/SUMMARY.md` by default.

`main` with `--upload`:

```text
paths = build_training_sets(...)
keys = upload_training_parquets(paths, output_root)
stats = collect_file_stats(paths, output_root)
write_summary(stats, experiment_root() / "SUMMARY.md")
```

## Test design

```text
given output_root/is_political/ds1_2026_09_04-12:00:00.parquet
when s3_key_for is called
then the key is mirrorview/create_feature_generation_training_sets_2026_09_04/is_political/ds1_2026_09_04-12:00:00.parquet

given two local parquets and a fake S3
when upload_training_parquets runs
then upload_file is called twice
and the keys match s3_key_for
and .gitkeep is not uploaded

given one political parquet with 3 rows and size known
when collect_file_stats runs
then n_rows is 3
and size_mb is round(bytes/1_000_000, 2)
and s3_prefix is the object key

given stats for is_political (10 rows) and is_likely_spam (0 files)
when render_summary_markdown runs
then there is a heading for is_likely_spam
and the is_likely_spam table has no file rows
and the totals table has is_likely_spam, 0
and the totals table has is_political, 10
and classifiers appear in CLASSIFIER_NAMES order

given main with --upload and a fake S3
when main runs against a tmp data root
then SUMMARY.md is written under the experiment folder path passed by a test seam
and upload_file was called
```

Add an optional `--summary-path` flag so tests do not overwrite a production SUMMARY. The production default is `experiments/create_feature_generation_training_sets_2026_09_04/SUMMARY.md`.

## Implementation notes (implement-from-spec)

Phase order, one Git commit per phase that changes the repo:

1. Phase 1 scope. Caller is `main --upload`.
2. Phase 2 scaffold. Add `src/upload.py` and `src/summary.py` with `NotImplementedError` bodies. Wire `main --upload` to call them. Commit.
3. Phase 3 contracts. Lock the signatures in this file. Full auto. Commit.
4. Phase 4 test design. Write `test_upload.py` and `test_summary.py`. Update `test_main.py`. Commit.
5. Phase 5 units, in this order, one commit each:
   1. `s3_key_for` and `upload_training_parquets`.
   2. `collect_file_stats`, `render_summary_markdown`, `write_summary`.
   3. `main --upload` wiring.
6. Phase 6. Fixture tests, then the production upload.

## Must pass

Fixture tests:

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run pytest experiments/create_feature_generation_training_sets_2026_09_04/tests -q
```

Expected: exit 0.

Production upload. Use the timestamp already present on the step 3 parquet names. Substitute `TS` from those filenames:

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run python experiments/create_feature_generation_training_sets_2026_09_04/main.py --upload --timestamp TS
```

Expected: exit 0. `SUMMARY.md` exists.

```bash
cd /Users/mark/src/work/mirrorView-task
aws s3 ls s3://met-ml-training/mirrorview/create_feature_generation_training_sets_2026_09_04/ --recursive | wc -l
```

Expected: the same N as local parquet count (52 on the 2026-09-04 listing).

`SUMMARY.md` contains seven classifier headings, a `file | size_mb | n_rows | s3_prefix` table under each, and a final `category | n_rows` table. Totals per classifier match `len(pd.read_parquet(...))` summed for that folder.

## Must fail / not happen

- Bucket or prefix other than `met-ml-training` and `mirrorview/create_feature_generation_training_sets_2026_09_04`.
- Keys that omit the classifier folder.
- `.gitkeep` or `README.md` uploaded.
- `lib/aws/s3.py` edited.
- Experiment README edited.
- Fixture tests calling live S3.
- A second timestamp helper.
- Source data folder written.
