# Step 3: Generate flips for the unified 2,300 posts

## Scope

- **Caller:** `experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py` `main`
- **Task:** Download the pinned unified 2,300 post parquet, check SHA-256 and row count, call `shared/flip_generation/generate_flips.py`, run a 10 post smoke, then generate flips for all 2,300 posts, and copy the concatenated parquet to the named key next to the existing flips experiment.
- **Out of scope:** pytest, Perspective, the catalog, remaining labels, editing `shared/flip_generation/`, rewriting the 10,182 row flips parquet, editing the unified source object.

## Dependencies

Step 2 has uploaded `unified_upsampled_posts.parquet` and committed its SHA-256 in `experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/RESULTS.md`. Pin that SHA-256 here. Expected row count is 2300.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-08_upsample_medium_toxicity_stimuli_dca950/plan.md` | Unified input, S3 prefix, named output |
| `/workspace/experiments/generate_flips_2026_09_08/run.py` | Typer flags, `generate_flips` wiring, print lines |
| `/workspace/experiments/generate_flips_2026_09_08/load_filtered_dataset.py` | Download, hash, cache pattern |
| `/workspace/shared/flip_generation/generate_flips.py` | `BATCH_SIZE`, `MAX_CONCURRENCY`, `MAX_TOKENS`, `generate_flips` |
| `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/steps/step2.md` | Flag and print contract |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/generate_flips_for_upsampled_posts_2026_09_08/README.md` (new)
- `/workspace/experiments/generate_flips_for_upsampled_posts_2026_09_08/__init__.py` (new)
- `/workspace/experiments/generate_flips_for_upsampled_posts_2026_09_08/sources.py` (new)
- `/workspace/experiments/generate_flips_for_upsampled_posts_2026_09_08/load_unified_dataset.py` (new)
- `/workspace/experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py` (new)
- `/workspace/experiments/generate_flips_for_upsampled_posts_2026_09_08/.gitignore` (new)
- `/workspace/.gitignore` (ignore `cache/` under this folder)
- `/workspace/experiments/generate_flips_for_upsampled_posts_2026_09_08/RESULTS.md` after the live full run
- `/workspace/CHANGELOG.md` after the named flips object exists

## Files forbidden to change

- `/workspace/shared/flip_generation/**`
- `/workspace/experiments/generate_flips_2026_09_08/RESULTS.md`
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/README.md`
- `/workspace/tests/**`
- The unified source S3 object
- `experiments/generate_flips_2026_09_08/2026_09_08-20:31:31/flips.parquet`

## Pinned input

| Field | Value |
|-------|-------|
| Object | `s3://mirrorview-experimental-artifacts/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/unified_upsampled_posts.parquet` |
| SHA-256 | the digest recorded in the Step 2 `RESULTS.md` |
| Rows | 2300 |
| Columns | the 17 combined columns |
| Mapped columns | `record_id`, `text`, `political_stance`, `llm_toxicity_tier` |

A hash mismatch or wrong row count raises `ValueError`. A missing object raises `FileNotFoundError`.

Copy the download, cache, and hash pattern from `experiments/generate_flips_2026_09_08/load_filtered_dataset.py`. Do not import that loader, because it pins the 10,200 sample.

## CLI and S3 layout

Copy the Typer flags from `experiments/generate_flips_2026_09_08/run.py`: `--run-id`, `--max-posts`, `--bucket`.

`RUN_KEY_PREFIX` is `experiments/generate_flips_for_upsampled_posts_2026_09_08/`. `run_prefix` is `f"{RUN_KEY_PREFIX}{run_id}/"` and must end with `/`.

`SMOKE_RUN_ID` is `smoke`. `SMOKE_MAX_POSTS` is 10. Import `BATCH_SIZE`, `MAX_CONCURRENCY`, and `MAX_TOKENS` from `shared.flip_generation.generate_flips`. Import `DEFAULT_BEDROCK_SONNET_MODEL`.

After `generate_flips` returns a full run with `wrote_final` true, copy the concatenated bytes to `experiments/generate_flips_2026_09_08/flips_unified_upsampled_posts.parquet` with `put_new`. Do not copy that named object during the 10 post smoke. A second upload of the named key must fail.

## Commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --run-id smoke --max-posts 10
```

Expected stdout includes `run_prefix=experiments/generate_flips_for_upsampled_posts_2026_09_08/smoke/`, `part_count=1`, and `row_count=` plus `failed_count=` that sum to 10.

```bash
PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --run-id 2026_09_09-HH:MM:SS
```

Use a timestamp run id. Omit `--max-posts`. Expected: `row_count` plus `failed_count` equals 2300, `wrote_final=True`, and the named sibling object exists.

`RESULTS.md` must include the smoke command, the full-run id, the pinned unified URI and SHA-256, `part_count`, `row_count`, `failed_count`, the run-prefix `flips.parquet` URI, and the named sibling URI and SHA-256.

## Live given / when / then (Phase 4)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned unified parquet exists at 2300 rows
when PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --run-id smoke --max-posts 10
then part_count=1
and row_count + failed_count = 10
and S3 object experiments/generate_flips_for_upsampled_posts_2026_09_08/smoke/batches/part-00000.parquet exists
and the named sibling key is absent

given the same smoke command is run again
then existing smoke parts are not rewritten

given a new timestamp --run-id and no --max-posts
when the command runs
then row_count + failed_count = 2300
and S3 object experiments/generate_flips_2026_09_08/flips_unified_upsampled_posts.parquet exists
```

If every smoke row failed, `part-00000.parquet` is absent. Stop before the full run.

## Must pass

- `--help` exits 0.
- `run.py` imports `generate_flips` from `shared.flip_generation.generate_flips`.
- Unified SHA-256 and row count are checked before Bedrock.
- Smoke writes only under the `smoke/` prefix.
- `shared/flip_generation/` is unchanged.

## Must fail

- Hash mismatch on the unified parquet.
- Wrong unified row count.
- Reusing `--run-id smoke` for the full 2,300 post job.
- Overwriting `experiments/generate_flips_2026_09_08/2026_09_08-20:31:31/flips.parquet`.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not add pytest.

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds `sources.py`, `load_unified_dataset.py`, `run.py` with stub bodies: load, generate, print, copy named object.

Phase 3 locks the frozen source dataclass and signatures. Continue without a pause.

Phase 5 implements in this order, one commit per unit of work:

1. Pinned constants from Step 2
2. Download and hash checks
3. `main` wiring to `generate_flips`
4. Named sibling `put_new` after a full run
5. README and `.gitignore`

Phase 6 is complete when `--help` works, the smoke succeeds, the full run accounts for 2,300 ids, and `RESULTS.md` is committed. Do not start Step 4 until that report exists.
