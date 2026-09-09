# Step 2: Smoke ten pairs, then label all 10,000 pairs on both engines

## Scope

- **Caller:** the same `run.py` `main` from Step 1, with `--engine` and optional `--smoke`
- **Task:** Export AWS credentials and `OPENAI_API_KEY`. Run a ten-pair smoke for OpenAI and for Bedrock. If each smoke prints `labeled 10 of 10`, label all 10,000 pairs on each engine into five parquet parts and a final parquet. Copy logs to `/opt/cursor/artifacts/`.
- **Out of scope:** pytest, editing the experiment README, rewriting `presentations.parquet`, changing product feature code, running `--score`, writing `CHANGELOG.md`

## Dependencies

Step 1 has uploaded `s3://mirrorview-experimental-artifacts/experiments/test_separability_original_mirror_posts_2026_09_09/outputs/presentations.parquet` with 10,000 rows. Do not start this step until that object exists. Load presentations from that key. Do not shuffle again. Do not download the catalog.

## Files to inspect (read-only)

- `/workspace/docs/plans/2026-09-09_separability_original_mirror_dee07c/plan.md`
- `/workspace/docs/plans/2026-09-09_separability_original_mirror_dee07c/steps/step1.md`
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/run.py`
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/openai_runner.py`
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/bedrock_runner.py`
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/README.md`
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/constants.py`

## Files allowed to change

- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/run.py` (only if a live run shows a bug in the labeling loop)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/openai_runner.py` (same)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/bedrock_runner.py` (same)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/loader.py` (only if loading presentations from S3 is missing)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/write.py` (same)

Do not add files. Do not edit `README.md`.

## Files forbidden to change

- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/README.md`
- `/workspace/data_platform/**`
- `/workspace/shared/flip_generation/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-09_separability_original_mirror_dee07c/**`
- The catalog S3 object
- The presentation S3 object

## Live commands

Run from the repo root. OpenAI commands need `OPENAI_API_KEY`. Bedrock commands need AWS keys.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine openai --smoke
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine bedrock --smoke
```

Each smoke command must print `labeled 10 of 10`. Each smoke writes under that engine's `smoke/` prefix, including `batches/part-00000.parquet`. Do not start either full run until both smokes have 10 labels.

If a smoke prints `failed=` greater than 0, stop. Do not run the 10,000-pair jobs.

```bash
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine openai
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine bedrock
```

Each full command writes `part-00000` through `part-00004` and `final.parquet` under `outputs/labels/{openai,bedrock}/`. Print `labeled {n} of 10000` and `failed={n}`. Labeled plus failed must equal 10,000.

A second full run for an engine whose `final.parquet` already exists returns without labeling and does not rewrite parts.

Copy stdout to `/opt/cursor/artifacts/separability_openai_smoke.log`, `/opt/cursor/artifacts/separability_bedrock_smoke.log`, `/opt/cursor/artifacts/separability_openai_full.log`, and `/opt/cursor/artifacts/separability_bedrock_full.log`.

## Live given / when / then (Phase 4)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and OPENAI_API_KEY is set
and presentations.parquet has 10000 rows
when PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine openai --smoke
then labeled 10 of 10
and S3 prefix experiments/test_separability_original_mirror_posts_2026_09_09/outputs/labels/openai/smoke/ has a parquet part
and outputs/labels/openai/final.parquet is still absent

given the same setup
when PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine bedrock --smoke
then labeled 10 of 10
and S3 prefix experiments/test_separability_original_mirror_posts_2026_09_09/outputs/labels/bedrock/smoke/ has a parquet part
and outputs/labels/bedrock/final.parquet is still absent

given both smokes wrote 10 labels
when PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine openai
then part-00000 through part-00004 exist under outputs/labels/openai/batches/
and outputs/labels/openai/final.parquet exists
and labeled plus failed equals 10000

given both smokes wrote 10 labels
when PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine bedrock
then part-00000 through part-00004 exist under outputs/labels/bedrock/batches/
and outputs/labels/bedrock/final.parquet exists
and labeled plus failed equals 10000
and errors.jsonl has no OpenAI retry rows

given openai final.parquet already exists
when the OpenAI full command is run again
then the process returns without labeling
and the five part objects are unchanged
```

## Must pass

- Both smokes print `labeled 10 of 10` before any full run starts.
- OpenAI full run writes five parts of 2,000 rows and `final.parquet` at `s3://mirrorview-experimental-artifacts/experiments/test_separability_original_mirror_posts_2026_09_09/outputs/labels/openai/final.parquet`.
- Bedrock full run writes the matching objects under `.../outputs/labels/bedrock/`.
- Labeled plus failed equals 10,000 on each full run.
- Smoke objects stay under `smoke/` and are not copied into either full `final.parquet`.
- Presentation parquet and catalog CSV are unchanged.
- `README.md` is unchanged from Step 1.
- `data_platform/` is unchanged.

## Must fail

- Starting a full run after a smoke with `failed` greater than 0.
- Sending Bedrock content-filter ids to OpenAI.
- Rewriting `presentations.parquet`.
- Rewriting an engine's parts after that engine's `final.parquet` exists.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then block above. The coding phases add no new product files unless a live run shows a bug in the Step 1 loop.

Phase 6 is complete when both smokes have 10 labels, both `final.parquet` objects exist, and labeled plus failed equals 10,000 on each engine. Do not start Step 3 until both final files exist.
