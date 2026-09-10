# Step 1: Convert the pull request 278 file into party assignment files and a combined catalog

## Scope

- **Caller:** `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/run.py` `main`
- **Task:** Download the pinned pull request 278 CSV, hash-check it, split odd original user ids to Democrats and even ids to Republicans, rewrite row ids to `{party}-training_assisted-{index:04d}`, write the two `assignments.csv` files plus `config.yaml`, union the old June catalog and the pull request 273 catalog, and fail if any assigned post id is missing `original_text` or `mirrored_text`.
- **Out of scope:** Creating the study bucket (Step 2), web app hardcoded copies (Step 3), S3 upload of the batch to `jspsych-mirror-view-2026-09-09` (Step 4), editing `study_participant_assignment_interface`, and editing the pull request 278 generator.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-09-09_init_study_assignments_7db8f4/plan.md` | Confirmed split, id rewrite, catalog union |
| `/Users/mark/src/work/mirrorView-task/experiments/generate_study_user_assignments_2026_09_08/RESULTS.md` | Pinned assignment CSV URI and SHA-256 `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce` |
| `/Users/mark/src/work/mirrorView-task/experiments/generate_study_user_assignments_2026_09_08/constants.py` | Source columns, `user-` id prefix, `training_assisted`, empty party |
| `/Users/mark/src/work/mirrorView-task/experiments/generate_study_user_assignments_2026_09_08/write.py` | How source rows are written |
| `/Users/mark/Documents/work/study_participant_assignment_interface/jobs/mirrorview/generate_assignment_ids.py` | Runtime id format `{party}-{condition}-{index:04d}`, 1-based |
| `/Users/mark/Documents/work/study_participant_assignment_interface/lambdas/get_study_assignment/handler.py` | Counter after increment is the index; `assigned_post_ids` JSON list of strings |
| `/Users/mark/Documents/work/study_participant_assignment_interface/jobs/mirrorview/config_loader.py` | `MirrorViewConfig` fields the batch `config.yaml` must parse |
| `/Users/mark/src/work/mirrorView-task/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/load.py` | Download, hash check, cache for the new catalog |
| `/Users/mark/src/work/mirrorView-task/shared/data/dataloader.py` | `load_dataset` for `STUDY_PHASE_2_PART_2_STIMULI` |
| `/Users/mark/src/work/mirrorView-task/shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` | Old catalog columns, including `original_text` and `mirrored_text` |
| `/Users/mark/src/work/mirrorView-task/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner to copy into the experiment README |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/README.md` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/constants.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/load.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/split.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/catalog.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/write.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/run.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/.gitignore` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/tests/__init__.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/tests/test_split.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/tests/test_rewrite_ids.py` (new)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/tests/test_catalog.py` (new)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/experiments/generate_study_user_assignments_2026_09_08/**`
- `/Users/mark/src/work/mirrorView-task/experiments/curate_study_2_phase_3_stimuli/**`
- `/Users/mark/src/work/mirrorView-task/shared/data/raw/study_phase_2_part_2/**`
- `/Users/mark/src/work/mirrorView-task/webapp/**`
- `/Users/mark/Documents/work/study_participant_assignment_interface/**`
- The pinned assignment CSV on S3
- The pull request 273 catalog on S3

## README contract

Write `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/README.md` first.

The README must:

1. Start with the same agent read-only banner used in `/Users/mark/src/work/mirrorView-task/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. Say the command does not generate feeds. It converts the pull request 278 CSV.
3. Name the source object `s3://mirrorview-experimental-artifacts/experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv` and SHA-256 `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce`.
4. Say odd original user ids go to `democrat` and even original user ids go to `republican`. Original user 1 is Democrat. Original user 2 is Republican.
5. Say expected counts are 1,940 Democrat rows and 1,939 Republican rows, 1,601 mixed feeds each, 339 leftover-left Democrat feeds, and 338 leftover-left Republican feeds.
6. Say rewritten ids are `democrat-training_assisted-0001` through `democrat-training_assisted-1940` and `republican-training_assisted-0001` through `republican-training_assisted-1939`, sorted by original user id inside each party.
7. Name local output layout under `experiments/load_study_assignments_2026_09_09/batch/`: `config.yaml`, `democrat/training_assisted/assignments.csv`, `republican/training_assisted/assignments.csv`, and `catalog.csv`.
8. Name catalog sources: `STUDY_PHASE_2_PART_2_STIMULI` and `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` (SHA-256 `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139`).
9. Include the pytest command and the live run command from Main caller below.

## Public contracts

Keep functions under 20 lines. Use frozen dataclasses. Reuse `CampaignObjectStore`, `parse_s3_uri`, `sha256_hex`, `load_dataset`, and the pull request 273 catalog download from `/Users/mark/src/work/mirrorView-task/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/load.py`. Reuse that object store. A second S3 client is forbidden.

### `constants.py`

Pinned values:

- `PINNED_ASSIGNMENTS_S3_URI` = `s3://mirrorview-experimental-artifacts/experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv`
- `PINNED_ASSIGNMENTS_SHA256` = `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce`
- `EXPECTED_SOURCE_ROWS` = 3879
- `EXPECTED_TEN_TEN` = 3202
- `EXPECTED_LEFT_ONLY` = 677
- `DEMOCRAT_ROW_COUNT` = 1940
- `REPUBLICAN_ROW_COUNT` = 1939
- `DEMOCRAT_LEFT_ONLY_COUNT` = 339
- `REPUBLICAN_LEFT_ONLY_COUNT` = 338
- `CONDITION` = `training_assisted`
- `PARTY_DEMOCRAT` = `democrat`
- `PARTY_REPUBLICAN` = `republican`
- `STUDY_BUCKET` = `jspsych-mirror-view-2026-09-09`
- `ASSIGNMENT_PREFIX` = `precomputed_assignments`
- `POSTS_PER_FEED` = 20
- `USER_ID_PREFIX` = `user-`
- `CATALOG_COLUMNS` = `post_primary_key`, `original_text`, `sample_toxicity_type`, `sampled_stance`, `mirrored_text`

Leftover-left detection: a source row whose `assigned_post_ids` JSON list has 20 left catalog stances and 0 right catalog stances. Mixed 10:10 has 10 and 10. Any other mix fails the run.

### `split.py`

- `parse_original_user_id(assignment_id: str) -> int` strips `user-` and parses the integer. Fail if the prefix is missing or the integer is less than 1.
- `party_for_user_id(user_id: int) -> str` returns `democrat` when `user_id % 2 == 1`, else `republican`.
- `split_by_party(rows) -> tuple[list, list]` partitions without copying a row to both lists. Sort each list by original user id.
- `rewrite_ids(rows, party: str) -> list` sets `id` to `generate_single_assignment_id` equivalent `{party}-training_assisted-{index:04d}` with `index` from 1, sets `political_party` to `party`, keeps `assigned_post_ids`, `condition`, and `created_at`.

Do not import from `/Users/mark/Documents/work/study_participant_assignment_interface`. Copy the id format into this experiment's constants and a one-line formatter. The assignment-service package is not a dependency of this repo.

### `catalog.py`

- Load old catalog through `load_dataset(STUDY_PHASE_2_PART_2_STIMULI)`.
- Load new catalog through the pinned pull request 273 download (hash and 10,000 rows).
- Fail if a `post_primary_key` appears in both catalogs.
- Union the five catalog columns.
- Collect every post id from every rewritten `assigned_post_ids` list.
- Fail if any assigned id is missing from the union, or if `original_text` or `mirrored_text` is empty.
- Write only the rows whose ids appear in at least one assignment, sorted by `post_primary_key`.

### `write.py`

Write:

```text
experiments/load_study_assignments_2026_09_09/batch/config.yaml
experiments/load_study_assignments_2026_09_09/batch/democrat/training_assisted/assignments.csv
experiments/load_study_assignments_2026_09_09/batch/republican/training_assisted/assignments.csv
experiments/load_study_assignments_2026_09_09/batch/catalog.csv
```

`config.yaml` must parse as `MirrorViewConfig` in the assignment-service repo. Required shape:

```yaml
name: mirrorview_2026_09_09
input_posts_path: experiments/load_study_assignments_2026_09_09/batch/catalog.csv
local_data_dir: experiments/load_study_assignments_2026_09_09/batch
s3:
  bucket: jspsych-mirror-view-2026-09-09
  prefix: precomputed_assignments
cells:
  - political_party: democrat
    condition: training_assisted
    count: 1940
  - political_party: republican
    condition: training_assisted
    count: 1939
```

`input_posts_path` is required by that Pydantic model. The Lambda does not read the catalog from it at runtime. Still point it at the local catalog path so the file is a real path in this repo.

Assignment CSV columns, in order: `id`, `assigned_post_ids`, `political_party`, `condition`, `created_at`.

## Tests that must pass

```bash
PYTHONPATH=. uv run pytest experiments/load_study_assignments_2026_09_09/tests -q
```

Expected: exit 0.

Cover at least:

- Odd original user 1 maps to `democrat-training_assisted-0001`. Even original user 2 maps to `republican-training_assisted-0001`.
- 3,879 synthetic source rows yield 1,940 Democrat rows and 1,939 Republican rows.
- Users 3203 through 3879 are leftover-left in the live math. After the odd/even split, Democrat leftover-left count is 339 and Republican leftover-left count is 338. Prove this with a fixture that marks those user ids leftover-left.
- A source row must not appear in both party files (compare `assigned_post_ids` JSON strings).
- Catalog builder raises if an assigned id is absent, duplicated across catalogs, or missing mirror text.
- Rewritten Democrat ids are exactly `democrat-training_assisted-0001` through `democrat-training_assisted-1940` with no gaps.

## Live command that must pass

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/run.py
```

Expected stdout includes `democrat_rows=1940`, `republican_rows=1939`, `catalog_rows=` equal to the number of distinct assigned post ids, and a local path under `experiments/load_study_assignments_2026_09_09/batch/`.

Expected files exist:

```bash
test -f experiments/load_study_assignments_2026_09_09/batch/config.yaml
test -f experiments/load_study_assignments_2026_09_09/batch/democrat/training_assisted/assignments.csv
test -f experiments/load_study_assignments_2026_09_09/batch/republican/training_assisted/assignments.csv
test -f experiments/load_study_assignments_2026_09_09/batch/catalog.csv
```

Row counts:

```bash
PYTHONPATH=. uv run python -c "import pandas as pd; d=pd.read_csv('experiments/load_study_assignments_2026_09_09/batch/democrat/training_assisted/assignments.csv'); r=pd.read_csv('experiments/load_study_assignments_2026_09_09/batch/republican/training_assisted/assignments.csv'); assert len(d)==1940 and len(r)==1939; assert d['id'].iloc[0]=='democrat-training_assisted-0001'; assert r['id'].iloc[0]=='republican-training_assisted-0001'"
```

Expected: exit 0.

A second run may overwrite the local `batch/` tree. Upload to `jspsych-mirror-view-2026-09-09` in Step 4, not here.

## Fail

The step fails on a hash mismatch of the pinned assignment CSV, a source row count other than 3,879, a feed that is neither 10:10 nor leftover-left, missing catalog text, or an import of `study_participant_assignment_interface`.
