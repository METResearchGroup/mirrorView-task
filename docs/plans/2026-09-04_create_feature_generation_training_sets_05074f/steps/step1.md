# Step 1: Scaffold the experiment package, category folders, and join contract

## Goal

Create the experiment package, the seven training-data folders, and the function signatures the later steps will fill in. Freeze classifier names and output column names in tests. Do not join real records yet.

## Caller / unit of work

The caller is `experiments/create_feature_generation_training_sets_2026_09_04/main.py` `main`.

You parse CLI args and resolve the source data folder and the output folder. You then call `build_training_sets`. In this step `build_training_sets` and the join helpers raise `NotImplementedError`.

Out of scope:

- reading `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data`
- join logic
- S3 upload
- `SUMMARY.md`
- edits to the experiment README
- edits to `data_platform/generate_features/`

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-09-04_create_feature_generation_training_sets_05074f/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/README.md` | Classifier folder names, output filename shape, source folder, S3 prefix. Do not edit. |
| `/Users/mark/src/work/mirrorView-task/data_platform/generate_features/registry.py` | `FEATURE_REGISTRY` keys must match the seven folder names |
| `/Users/mark/src/work/mirrorView-task/data_platform/curate/consolidate.py` | Label column names per classifier (`category`, `is_political`, `toxicity_prob`, `toxicity_tier`, and the rest) |
| `/Users/mark/src/work/mirrorView-task/data_platform/utils/platform_specific_columns.py` | Bluesky `uri`, Twitter `tweet_id`, Reddit `comment_fullname`, shared text column `text` |
| `/Users/mark/src/work/mirrorView-task/lib/timestamp_utils.py` | `get_current_timestamp` is the only timestamp helper |
| `/Users/mark/src/work/mirrorView-task/lib/aws/s3.py` | `S3` upload helper for step 4. Import only. Do not change. |
| `/Users/mark/src/work/mirrorView-task/experiments/fetch_reddit_pushshift_dump_2026_06_15/.gitignore` | Pattern for a gitignore inside an experiment folder |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/__init__.py` | Experiment `src/` package marker |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/main.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/__init__.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/constants.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/paths.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/hydrate.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/walk.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/.gitignore`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/training_data/is_likely_spam/.gitkeep`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/training_data/is_news_or_opinion/.gitkeep`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/training_data/is_political/.gitkeep`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/training_data/is_self_contained/.gitkeep`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/training_data/is_structurally_complete/.gitkeep`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/training_data/is_toxic_tiered/.gitkeep`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/training_data/political_stance/.gitkeep`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/__init__.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/test_constants.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/test_paths.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/test_main.py`

Plan package files under `/Users/mark/src/work/mirrorView-task/docs/plans/2026-09-04_create_feature_generation_training_sets_05074f/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/README.md`
- `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data/**`
- `/Users/mark/src/work/mirrorView-task/data_platform/generate_features/**`
- `/Users/mark/src/work/mirrorView-task/data_platform/curate/**`
- `/Users/mark/src/work/mirrorView-task/lib/aws/s3.py`
- `/Users/mark/src/work/mirrorView-task/lib/timestamp_utils.py`
- `/Users/mark/src/work/mirrorView-task/.gitignore` (use the gitignore inside the experiment folder instead)
- Any file outside the allowed list, except git commits of this work

## Decision (locked)

1. Put experiment code under `experiments/create_feature_generation_training_sets_2026_09_04/`. Put tests under `experiments/create_feature_generation_training_sets_2026_09_04/tests/`.
2. Classifier names are exactly the seven `FEATURE_REGISTRY` keys, in this order: `is_likely_spam`, `is_news_or_opinion`, `is_political`, `is_self_contained`, `is_structurally_complete`, `is_toxic_tiered`, `political_stance`.
3. Platforms are exactly `bluesky`, `twitter`, `reddit`.
4. Default source folder is `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data`.
5. S3 bucket is `met-ml-training`. S3 prefix is `mirrorview/create_feature_generation_training_sets_2026_09_04` with no trailing slash.
6. Training output id column is `uri`. Label time column is `label_timestamp`. Text column is `text`.
7. Label columns stay as they are on the source classifier files. `is_news_or_opinion` keeps `category`. `is_toxic_tiered` keeps `toxicity_prob` and `toxicity_tier`.
8. Output path is `training_data/{classifier}/{dataset_id}_{timestamp}.parquet`, where `timestamp` comes from `get_current_timestamp`.
9. Ignore parquet files under `training_data/` in the experiment `.gitignore`. Track the `.gitkeep` files so the empty folders stay in git.
10. `main.py` accepts `--data-root`, `--output-root`, `--timestamp`, and `--upload`. Default `--data-root` is the source folder. Default `--output-root` is the experiment `training_data/` folder. Default `--timestamp` is `get_current_timestamp` taken once at process start. Default `--upload` is off. Step 3 leaves `--upload` off. Step 4 turns it on.

## Contracts to lock

In `src/constants.py`:

```text
CLASSIFIER_NAMES: tuple[str, ...]
PLATFORMS: tuple[str, ...]
DEFAULT_DATA_ROOT: Path
S3_BUCKET: str
S3_PREFIX: str
OUTPUT_ID_COLUMN: str          # "uri"
LABEL_TIMESTAMP_COLUMN: str    # "label_timestamp"
OUTPUT_TEXT_COLUMN: str        # "text"

# platform -> (join id column on preprocessed records, text column on preprocessed records)
PLATFORM_RECORD_COLUMNS: dict[str, tuple[str, str]]
# "bluesky" -> ("uri", "text")
# "twitter" -> ("tweet_id", "text")
# "reddit"  -> ("comment_fullname", "body")

LABEL_COLUMNS: dict[str, tuple[str, ...]]
# "is_likely_spam" -> ("is_likely_spam",)
# "is_news_or_opinion" -> ("category",)
# "is_political" -> ("is_political",)
# "is_self_contained" -> ("is_self_contained",)
# "is_structurally_complete" -> ("is_structurally_complete",)
# "is_toxic_tiered" -> ("toxicity_prob", "toxicity_tier")
# "political_stance" -> ("political_stance",)
```

In `src/paths.py` (real bodies are allowed, because they only join paths):

```text
def experiment_root() -> Path
def training_data_root() -> Path
def category_dir(classifier_name: str) -> Path
def output_parquet_path(classifier_name: str, dataset_id: str, timestamp: str) -> Path
```

`output_parquet_path` returns `training_data_root() / classifier_name / f"{dataset_id}_{timestamp}.parquet"`.

In `src/hydrate.py` (stubs only):

```text
def read_table(path: Path) -> pd.DataFrame
def load_preprocessed_records(dataset_dir: Path, platform: str) -> pd.DataFrame
def hydrate_classifier(
    labels: pd.DataFrame,
    records: pd.DataFrame,
    *,
    platform: str,
    classifier_name: str,
) -> pd.DataFrame
def write_training_parquet(df: pd.DataFrame, path: Path) -> Path
```

Each body is `raise NotImplementedError`.

In `src/walk.py` (stub only):

```text
def build_training_sets(
    data_root: Path,
    *,
    timestamp: str,
    output_root: Path,
) -> list[Path]
```

Body is `raise NotImplementedError`.

In `main.py`:

```text
def parse_args(argv: list[str] | None = None) -> argparse.Namespace
def main(argv: list[str] | None = None) -> int
```

`parse_args` is real. `main` parses args, then calls `build_training_sets`. If `--upload` is set, `main` raises `NotImplementedError` after the build call, and step 4 fills that in. Do not import S3 yet if that would force unused wiring. A comment in `main` that upload is step 4 is enough.

## Test design

Call public APIs only. Do not seed private fields.

```text
given CLASSIFIER_NAMES
when tests read the tuple
then it equals the seven FEATURE_REGISTRY keys in the locked order

given LABEL_COLUMNS["is_news_or_opinion"]
then it equals ("category",)

given LABEL_COLUMNS["is_toxic_tiered"]
then it equals ("toxicity_prob", "toxicity_tier")

given PLATFORM_RECORD_COLUMNS
then bluesky is ("uri", "text")
and twitter is ("tweet_id", "text")
and reddit is ("comment_fullname", "body")

given classifier "is_political", dataset_id "bluesky_abc", timestamp "2026_09_04-12:00:00"
when output_parquet_path is called
then the path ends with training_data/is_political/bluesky_abc_2026_09_04-12:00:00.parquet

given the experiment training_data tree
when tests list category folders
then the seven classifier folders exist

given hydrate_classifier with empty frames
when the stub is called
then raise NotImplementedError

given build_training_sets
when the stub is called
then raise NotImplementedError

given main([])
when main runs
then it calls build_training_sets
and it raises NotImplementedError from that call
and it does not read the source data folder
```

## Implementation notes (implement-from-spec)

Phase order, one Git commit per phase that changes the repo:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Create the files in the allowed list, with stub bodies on join and walk. Create the seven `.gitkeep` folders and the experiment `.gitignore`. Commit.
3. Phase 3 contracts. Put the signatures and constants in this file into the modules. Bodies of join and walk stay `NotImplementedError`. Path helpers may have real join bodies. Full auto. Do not wait for approval. Commit.
4. Phase 4 test design. Write the tests above. Join and walk tests fail with `NotImplementedError`. Constant and path tests can pass in this phase if Phase 3 already filled those values. Commit.
5. Phase 5 units, in this order, one commit each:
   1. Fill `constants.py` and `paths.py` so constant and path tests pass.
   2. Fill `parse_args` and the `main` call to `build_training_sets` so `test_main` sees the stub raise.
6. Phase 6. Run the must-pass commands.

## Must pass

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run pytest experiments/create_feature_generation_training_sets_2026_09_04/tests/test_constants.py experiments/create_feature_generation_training_sets_2026_09_04/tests/test_paths.py experiments/create_feature_generation_training_sets_2026_09_04/tests/test_main.py -q
```

Expected: exit 0.

```bash
cd /Users/mark/src/work/mirrorView-task
ls experiments/create_feature_generation_training_sets_2026_09_04/training_data
```

Expected: the seven classifier folder names, one per line, in any order.

## Must fail / not happen

- `experiments/create_feature_generation_training_sets_2026_09_04/README.md` is edited.
- `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data` is read or written.
- `hydrate_classifier` or `build_training_sets` returns a real dataframe or writes a parquet.
- S3 is called.
- `SUMMARY.md` is created.
- `data_platform/generate_features/` is edited.
- A new timestamp helper is added.
- Classifier names diverge from `FEATURE_REGISTRY`.
