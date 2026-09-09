# Test separability of original vs mirror posts

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

This experiment asks the default OpenAI model (`gpt-5.4-nano`) and the default Bedrock model (`us.amazon.nova-micro-v1:0`) which of two presented social media posts was written by a human and which is an AI political mirror of the human post.

## Catalog

The input catalog is `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` with SHA-256 `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139` and 10,000 rows. Human text is `original_text`. AI text is `mirrored_text`.

## Presentation

Presentation order is shuffled once with seed 42, stored in `presentations.parquet`, and reused by both engines. Each model returns `human_slot` (`first` or `second`) and a one-sentence `reason`.

## S3 layout

Bucket: `mirrorview-experimental-artifacts`. Prefix: `experiments/test_separability_original_mirror_posts_2026_09_09/`.

## Required files

- `constants.py`
- `schema.py`
- `prompts.py`
- `loader.py`
- `write.py`
- `openai_runner.py`
- `bedrock_runner.py`
- `score.py`
- `run.py`

## Commands

Run from the repo root. Export AWS keys from `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`. Set `OPENAI_API_KEY` before any OpenAI command.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --write-presentation
```

The command downloads the pinned catalog, writes 10,000 presentation rows, uploads the presentation parquet, and prints `wrote 10000 presentations`. A second run exits non-zero because the presentation key exists.

```bash
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine openai --smoke
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine bedrock --smoke
```

Each command writes 10 labels under that engine's `smoke/` prefix and prints `labeled 10 of 10`.

```bash
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine openai
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine bedrock
```

Each command writes `part-00000` through `part-00004` and `final.parquet`, and prints `labeled 10000`. If some rows were content-filtered, the printout is the scored count plus the failed count.

```bash
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --score
```

The command prints the overall table and both cell tables, then writes `RESULTS.md`.
