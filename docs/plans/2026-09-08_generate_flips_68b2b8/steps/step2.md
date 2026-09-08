# Step 2: Add the experiment command

## Scope

- **Caller:** `experiments/generate_flips_2026_09_08/run.py` `main`
- **Task:** Download the pinned filtered 10,200-post parquet, check SHA-256 and row count, map columns, call `generate_flips`, and print part/row/failure counts. Support `--max-posts` and `--run-id`.
- **Out of scope:** pytest, live Bedrock (Step 3), editing the filter-posts README, changing `shared/flip_generation/` except import-only, changing June flip scripts.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/plan.md` | Pinned input URI, SHA-256, 10200 rows, S3 prefix |
| `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/steps/step1.md` | `generate_flips` signature, `FlipRunResult`, `run_prefix` rules |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/load_raw_candidate_dataset.py` | Download, hash check, local cache via `CampaignObjectStore.get` |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/RESULTS.md` | Pinned filtered SHA-256 `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9`, 10200 rows |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/sources.py` | Output URI and column names on the filtered parquet |
| `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/sources.py` | `COMBINED_COLUMNS` (filtered file keeps these 17 names) |
| `/workspace/shared/flip_generation/generate_flips.py` | Public caller from Step 1 |
| `/workspace/lib/constants.py` | `REPO_ROOT` |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/generate_flips_2026_09_08/__init__.py` (new)
- `/workspace/experiments/generate_flips_2026_09_08/sources.py` (new)
- `/workspace/experiments/generate_flips_2026_09_08/load_filtered_dataset.py` (new)
- `/workspace/experiments/generate_flips_2026_09_08/run.py` (new)
- `/workspace/experiments/generate_flips_2026_09_08/README.md` (new)
- `/workspace/experiments/generate_flips_2026_09_08/.gitignore` (new)
- `/workspace/.gitignore` (ignore `cache/` under this experiment folder only)

## Files forbidden to change

- `/workspace/shared/flip_generation/**` except if Step 1 left a signature mismatch that blocks the import (do not add behavior)
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` (gitignored; do not commit)
- `/workspace/experiments/scaled_mirrors_generation_2026_06_02/**`
- `/workspace/data_platform/generate_features/engines/bedrock_engine.py`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md` until Step 3
- `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/plan.md`

## Pinned input

| Field | Value |
|-------|-------|
| Object | `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` |
| SHA-256 | `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9` |
| Rows | 10200 |
| Columns | the 17 names in `COMBINED_COLUMNS` in that order |

A hash mismatch or wrong row count raises `ValueError`. A missing object raises `FileNotFoundError`.

Do not import `load_raw_candidate_dataset` from the filter experiment (that loader pins the 55,573-row combined file). Copy the download / cache / hash pattern from that module into `load_filtered_dataset.py` with this experiment's pin.

Cache bytes at `experiments/generate_flips_2026_09_08/cache/dataset.parquet`. Gitignore `cache/`.

## File-level constants (`sources.py` and `run.py`)

`sources.py`:

- `INPUT_S3_BUCKET = "mirrorview-experimental-artifacts"`
- `INPUT_S3_KEY = "experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet"`
- `INPUT_SHA256 = "9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9"`
- `INPUT_ROW_COUNT = 10200`
- `OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"`
- `RUN_KEY_PREFIX = "experiments/generate_flips_2026_09_08/"`
- `CACHE_FILENAME = "dataset.parquet"`
- `SMOKE_RUN_ID = "smoke"`
- `SMOKE_MAX_POSTS = 10`
- `POST_COLUMNS` tuple: `record_id`, `text`, `political_stance`, `llm_toxicity_tier`

`run.py` does not inline those strings or numbers. `--bucket` defaults to `OUTPUT_S3_BUCKET`. `--run-id` defaults by calling `get_current_timestamp()` in `main`, not as a Typer default of `None`.

## CLI

Typer command in `run.py`.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --help
```

Flags:

| Flag | Default | Meaning |
|------|---------|---------|
| `--run-id` | `get_current_timestamp()` inside `main` | S3 run folder name |
| `--max-posts` | omitted (full table) | Slice the loaded frame in `run.py` before calling `generate_flips`. Smoke uses `SMOKE_MAX_POSTS`. |
| `--bucket` | `OUTPUT_S3_BUCKET` | Bucket for `CampaignObjectStore` |

`run_prefix` is `f"{RUN_KEY_PREFIX}{run_id}/"` and must end with `/`.

Smoke uses `--run-id` `SMOKE_RUN_ID` and `--max-posts` `SMOKE_MAX_POSTS`. Full run omits `--max-posts`.

`main` does: load pinned parquet → keep `POST_COLUMNS` → if `--max-posts` was passed, take that many rows after the load (do not pass a nullable `max_posts` into `generate_flips`) → `create_bedrock_runtime_client()` → `generate_flips(posts, store, run_prefix, client, BATCH_SIZE, MAX_CONCURRENCY, MAX_TOKENS, DEFAULT_BEDROCK_SONNET_MODEL)` → print `run_prefix=`, `part_count=`, `row_count=`, `failed_count=`, `final_key=`, `wrote_final=`.

Import `BATCH_SIZE`, `MAX_CONCURRENCY`, and `MAX_TOKENS` from `shared.flip_generation.generate_flips`. Do not copy the numbers into `run.py`.

Do not write `RESULTS.md` in this step.

## README

Operator README at `experiments/generate_flips_2026_09_08/README.md`. Include:

- The two run commands (10-post smoke with `--run-id smoke --max-posts 10`, full run without `--max-posts`). Use the `SMOKE_RUN_ID` / `SMOKE_MAX_POSTS` names in code; the README may show the resolved command.
- The pinned input URI and SHA-256
- The S3 prefix `experiments/generate_flips_2026_09_08/{run_id}/`
- That rerunning the same `--run-id` resumes and does not rewrite existing parts

## Work

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then block in the `run.py` module docstring.

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds `sources.py`, `load_filtered_dataset.py`, `run.py` with stub bodies and a thin `main`: load → generate → print.

Phase 3 locks the frozen source dataclass (uri, sha256, expected_row_count) and `load_filtered_dataset` / `main` signatures.

Phase 5 implements in this order, one commit per unit of work:

1. Pinned source constants
2. Download and hash / row / column checks
3. `main` wiring to `generate_flips`
4. README and `.gitignore`

Phase 6 is complete when `--help` works and imports resolve. Do not call Bedrock.

## Live given / when / then (Phase 4, executed in Step 3)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned filtered parquet exists at SHA-256 9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9
when PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --run-id smoke --max-posts 10
then part_count=1
and row_count + failed_count = 10
and S3 object experiments/generate_flips_2026_09_08/smoke/batches/part-00000.parquet exists
and stdout prints run_prefix=experiments/generate_flips_2026_09_08/smoke/

given the same command is run again
then Bedrock is not called for those 10 ids
and part-00000 is not rewritten
```

## Must pass

- `--help` exits 0.
- `run.py` imports `generate_flips` from `shared.flip_generation.generate_flips`.
- Pinned SHA-256 and row count are checked before Bedrock.
- Filter-posts README is unchanged.

## Must fail

- Hash mismatch on the filtered parquet.
- Wrong filtered row count.
- Missing required mapped column.
