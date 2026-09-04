# Step 2: Join one classifier file into a training parquet

## Goal

Fill in the join helpers so one classifier file plus that dataset's preprocessed records become a training parquet. Prove the behavior on fixtures. Do not walk the full source folder.

## Caller / unit of work

The caller is `hydrate_classifier`, then `write_training_parquet`. Step 3's `build_training_sets` will call both.

You read a classifier csv and the preprocessed records (csv or parquet bytes). You drop duplicate ids inside the classifier file, join to text, and write parquet.

Out of scope:

- walking every dataset
- S3
- `SUMMARY.md`
- changing `main.py` beyond what is needed to keep imports resolving
- editing the experiment README
- reading the full source data folder in tests

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-09-04_create_feature_generation_training_sets_05074f/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-09-04_create_feature_generation_training_sets_05074f/steps/step1.md` | Locked names and signatures |
| `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/constants.py` | `PLATFORM_RECORD_COLUMNS` and `LABEL_COLUMNS` |
| `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/hydrate.py` | Stubs from step 1 |
| `/Users/mark/src/work/mirrorView-task/data_platform/utils/storage.py` | `load_records` csv vs parquet branch. `keep_default_na=False` on csv |
| `/Users/mark/src/work/mirrorView-task/data_platform/curate/consolidate.py` | Dedupe inside a file keeps the latest `label_timestamp` |
| `/Users/mark/src/work/mirrorView-task/data_platform/models/sync.py` | Preprocessed Bluesky has `uri` and `text`. Twitter has `tweet_id` and `text`. Reddit has `comment_fullname` and `body` |

Source-folder facts from the 2026-09-04 listing, for fixture design only:

- Classifier files use column `uri` as the id, including Twitter and Reddit.
- Twitter `uri` values match preprocessed `tweet_id`. Reddit `uri` values match preprocessed `comment_fullname`.
- Some Bluesky files named `posts.csv` start with bytes `PAR1` and are parquet.

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/hydrate.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/test_hydrate.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/conftest.py` if a shared tmp fixture helps
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/fixtures/**` if you write small csv or parquet fixtures as files rather than in-memory frames

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/README.md`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/constants.py` unless a test in this step finds a locked name is wrong, in which case stop and tell the user
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/walk.py` (step 3)
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/main.py` except a missing import that would break collection
- `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data/**`
- `/Users/mark/src/work/mirrorView-task/data_platform/**`
- `/Users/mark/src/work/mirrorView-task/lib/**`
- Any file outside the allowed list, except git commits of this work

## Decision (locked)

1. `read_table(path)` reads parquet when the first four bytes are `PAR1`, including when the suffix is `.csv`. Otherwise it reads csv with `keep_default_na=False`.
2. `load_preprocessed_records(dataset_dir, platform)` reads every `posts.csv`, `posts.parquet`, `comments.csv`, and `comments.parquet` under `dataset_dir / "preprocessed" / <run> /`. Skip `metadata.json`. Concatenate runs, cast the platform join id to string, and drop duplicate join ids while keeping the first row. For Reddit, copy `body` into a `text` column.
3. Classifier files join on their `uri` column, cast to string, against the platform join id.
4. Dedupe inside a file is on `uri`. Sort by `label_timestamp` descending, then `drop_duplicates(subset=["uri"], keep="first")`. Do not merge across classifier files or datasets.
5. Join with an inner join. Drop label rows with no matching preprocessed text. Drop rows whose `text` is missing after the join.
6. Output columns are `uri`, `label_timestamp`, `text`, then `LABEL_COLUMNS[classifier_name]` in that order. Do not rename `category`.
7. If a required label column is missing from the classifier file, raise `ValueError` that names the classifier and the missing column.
8. `write_training_parquet` creates parent folders and writes with `index=False`. It returns the path.
9. Tests build a tiny fake dataset folder. They do not open the source data folder.

## Contracts to lock

Signatures stay as in step 1. `hydrate_classifier` behavior:

```text
hydrate_classifier(
    labels: pd.DataFrame,
    records: pd.DataFrame,
    *,
    platform: str,
    classifier_name: str,
) -> pd.DataFrame
```

`platform` must be a key in `PLATFORM_RECORD_COLUMNS`. `classifier_name` must be a key in `LABEL_COLUMNS`. Unknown names raise `ValueError`.

If `labels` is empty, return an empty frame with the output columns and zero rows. Do not raise.

`load_preprocessed_records` returns a frame that at least has the platform join id and `text`. Extra preprocessed columns may be present, and `hydrate_classifier` ignores them.

## Test design

Build fixtures in pytest tmp paths. Do not seed private fields.

```text
given a csv whose header is uri,label_timestamp,is_political
and a Bluesky preprocessed csv with matching uri and text
when hydrate_classifier runs for bluesky / is_political
then columns are uri, label_timestamp, text, is_political
and the text column matches the preprocessed text
and row count is 1

given two label rows with the same uri and different label_timestamp
when hydrate_classifier runs
then one row remains
and it is the row with the later label_timestamp

given a label uri that is not in preprocessed records
when hydrate_classifier runs
then that row is absent from the result

given Twitter preprocessed records keyed by tweet_id
and a classifier file whose uri equals those tweet ids (possibly as ints)
when hydrate_classifier runs for twitter
then the join succeeds on the string forms of the ids

given Reddit preprocessed records with comment_fullname and body
when hydrate_classifier runs for reddit
then output text equals body
and output uri equals the classifier uri

given a posts.csv whose bytes start with PAR1
when read_table is called
then it returns the parquet rows
and it does not raise UnicodeDecodeError

given two preprocessed runs that share one uri with the same text
when load_preprocessed_records runs
then that uri appears once

given is_news_or_opinion labels with a category column
when hydrate_classifier runs
then the output has column category
and it does not have news_or_opinion_category

given is_toxic_tiered labels with toxicity_prob and toxicity_tier
when hydrate_classifier runs
then both label columns are in the output

given a classifier file missing is_political
when hydrate_classifier runs for is_political
then raise ValueError naming is_political

given an empty labels frame
when hydrate_classifier runs
then the result has zero rows
and it has the output columns

given a one-row hydrated frame and a tmp path
when write_training_parquet runs
then the path exists
and pd.read_parquet returns one row
and uri values are unique
```

## Implementation notes (implement-from-spec)

Phase order, one Git commit per phase that changes the repo:

1. Phase 1 scope. Confirm caller is `hydrate_classifier` plus `write_training_parquet`. No extra modules.
2. Phase 2 scaffold. Signatures already exist from step 1. Do not add new files unless tests need `conftest.py` or fixture files. Commit only if you add those.
3. Phase 3 contracts. No signature changes. Full auto. Skip a commit if nothing changed.
4. Phase 4 test design. Write `test_hydrate.py` so every scenario above fails for `NotImplementedError` or a wrong result, not for missing imports. Commit.
5. Phase 5 units, in this order, one commit each:
   1. `read_table` (csv and PAR1-as-csv).
   2. `load_preprocessed_records` (multi-run concat, Reddit `body` to `text`, duplicate join ids).
   3. `hydrate_classifier` (dedupe, inner join, column order, missing columns, empty labels).
   4. `write_training_parquet`.
6. Phase 6. Run the must-pass commands. `build_training_sets` still raises `NotImplementedError`.

## Must pass

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run pytest experiments/create_feature_generation_training_sets_2026_09_04/tests -q
```

Expected: exit 0. Walk and upload tests do not exist yet. `test_main` still expects `build_training_sets` to raise `NotImplementedError`.

## Must fail / not happen

- Tests open `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data`.
- Label column `category` is renamed.
- Duplicate `uri` values remain in a written parquet.
- Label rows without preprocessed text are kept.
- Cross-dataset or cross-file label merging.
- `walk.py` or S3 upload implemented.
- Experiment README edited.
- `data_platform/` edited.
