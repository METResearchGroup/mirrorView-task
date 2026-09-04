# Step 3: Walk every platform, dataset, and classifier to local parquet

## Goal

Fill `build_training_sets` so it walks the source data folder, skips missing classifier files, and writes one local parquet per existing classifier file. Do not upload.

## Caller / unit of work

The caller is `experiments/create_feature_generation_training_sets_2026_09_04/main.py` `main` with `--upload` left off.

For each platform folder and each dataset folder, load preprocessed records once. Then, for each classifier in `CLASSIFIER_NAMES`, join and write if `features/{classifier}.csv` exists.

Out of scope:

- S3
- `SUMMARY.md`
- editing the experiment README
- changing join rules from step 2

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-09-04_create_feature_generation_training_sets_05074f/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-09-04_create_feature_generation_training_sets_05074f/steps/step2.md` | Join behavior to reuse |
| `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/walk.py` | Stub |
| `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/hydrate.py` | Join helpers |
| `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/main.py` | CLI flags |
| `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data` | Production tree. Read only. |

On 2026-09-04 the source folder had nine datasets and 52 classifier csv files. The `features/` folder also contains `metadata.json`, `deadletter.jsonl`, and on one Reddit dataset `config.yaml`. Ignore those extra files.

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/walk.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/main.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/test_walk.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/tests/test_main.py` (expect a successful local build when `--upload` is off)
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/training_data/**` as written output of the production command, gitignored parquet

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/README.md`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/src/hydrate.py` unless a walk bug shows a join bug, in which case add a fixture test in `test_hydrate.py` and fix `hydrate.py`
- `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data/**` (read only)
- `/Users/mark/src/work/mirrorView-task/data_platform/**`
- `/Users/mark/src/work/mirrorView-task/lib/**`
- `/Users/mark/src/work/mirrorView-task/experiments/create_feature_generation_training_sets_2026_09_04/SUMMARY.md` (step 4)
- Any file outside the allowed list, except git commits of this work

## Decision (locked)

1. Walk `data_root / platform / dataset_id` for `platform` in `PLATFORMS`. Skip names that are not directories.
2. Load preprocessed records once per dataset with `load_preprocessed_records`.
3. For each name in `CLASSIFIER_NAMES`, look for `dataset_dir / "features" / f"{name}.csv"`. If the file is missing, skip with a print that names the dataset and the classifier. Do not look for timestamped feature run directories, because the source folder has none.
4. If the csv exists, call `read_table`, then `hydrate_classifier`, then `write_training_parquet` to `output_root / name / f"{dataset_id}_{timestamp}.parquet"`. Use the same `timestamp` for every file in one `build_training_sets` call.
5. Skip `features/metadata.json`, `features/deadletter.jsonl`, and any other non-classifier file.
6. Return the list of written paths, sorted.
7. Print each written path and a final line `wrote N parquets`.
8. `main` without `--upload` calls `build_training_sets` and returns 0. It does not call S3.
9. Production `timestamp` is `get_current_timestamp()` once in `main`, then passed in. Tests pass an explicit timestamp string.

## Contracts to lock

```text
def build_training_sets(
    data_root: Path,
    *,
    timestamp: str,
    output_root: Path,
) -> list[Path]
```

`output_root` is the `training_data/` folder, not a classifier subfolder. `write_training_parquet` creates classifier subfolders as needed.

Ignore extra directories under `data_root` that are not in `PLATFORMS`.

If a dataset has no `preprocessed/` folder and also has no classifier files, skip it. If a classifier csv exists and preprocessed records are missing, `load_preprocessed_records` returns an empty frame, the inner join yields zero rows, and you still write a zero-row parquet so the file is accounted for. Print a warning that names the dataset and the classifier and says zero rows.

## Test design

Use a tmp data root that copies the source layout, not the real source folder.

```text
given tmp/bluesky/ds1/features/is_political.csv
and tmp/bluesky/ds1/preprocessed/run1/posts.csv with matching uri and text
and tmp/bluesky/ds1/features/metadata.json
when build_training_sets runs with timestamp "2026_09_04-12:00:00"
then it writes output_root/is_political/ds1_2026_09_04-12:00:00.parquet
and it does not write an is_likely_spam parquet for ds1
and the return list has length 1

given tmp/reddit/ds2/features/is_toxic_tiered.csv only
when build_training_sets runs
then it writes one parquet under is_toxic_tiered
and it prints a skip line for each other classifier on ds2

given two platforms each with one classifier file
when build_training_sets runs
then two parquets are written
and both use the same timestamp suffix

given main(["--data-root", tmp, "--output-root", out, "--timestamp", "2026_09_04-12:00:00"])
when main runs without --upload
then exit code is 0
and S3 is not constructed
```

## Implementation notes (implement-from-spec)

Phase order, one Git commit per phase that changes the repo:

1. Phase 1 scope. Caller is `main` without `--upload`.
2. Phase 2 scaffold. Signature already exists. Skip if nothing to add.
3. Phase 3 contracts. No signature change. Full auto.
4. Phase 4 test design. Write `test_walk.py` and update `test_main.py`. Tests fail for `NotImplementedError`. Commit.
5. Phase 5 units, in this order, one commit each:
   1. `build_training_sets` walk, skip, write.
   2. `main` success path when `--upload` is off.
6. Phase 6. Run fixture tests, then the production command.

## Must pass

Fixture tests:

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run pytest experiments/create_feature_generation_training_sets_2026_09_04/tests -q
```

Expected: exit 0.

Production walk (no upload):

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run python experiments/create_feature_generation_training_sets_2026_09_04/main.py
```

Expected: exit 0. Stdout ends with `wrote N parquets`. On the 2026-09-04 listing, N is 52. If the source tree has changed, N equals the number of `features/{classifier}.csv` files whose classifier name is in `CLASSIFIER_NAMES`, and you print that count. N is not 0.

Then:

```bash
cd /Users/mark/src/work/mirrorView-task
find experiments/create_feature_generation_training_sets_2026_09_04/training_data -name '*.parquet' | wc -l
```

Expected: the same N.

Spot-check one Bluesky political parquet:

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run python -c "import pandas as pd, glob; p=glob.glob('experiments/create_feature_generation_training_sets_2026_09_04/training_data/is_political/bluesky_8ce4cf1f-8ab9-4373-a739-2a2ff2de400f_*.parquet')[0]; df=pd.read_parquet(p); print(list(df.columns)); print(len(df)); print(df['uri'].is_unique)"
```

Expected: columns `['uri', 'label_timestamp', 'text', 'is_political']`. Row count 1923 after dropping 5 duplicate ids from 1928 source rows. `True` for unique `uri`.

## Must fail / not happen

- `--upload` must not be required to write local parquet.
- Missing classifiers are invented as empty files without a skip print.
- Timestamped `features/<run>/` directories are required (the source tree has none).
- Cross-dataset merging into one parquet per classifier.
- S3 upload.
- `SUMMARY.md` written.
- Source data files modified.
- Experiment README edited.
