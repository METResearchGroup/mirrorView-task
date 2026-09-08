# Generate politically mirrored posts from the filtered stimulus dataset

This folder runs flip generation on the fixed 10,200-post filtered input used for the stimulus study.

Run every command from the repository root.

## Prerequisites

Export lab AWS credentials before any run:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

## Pinned input

| Field | Value |
|-------|-------|
| URI | `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` |
| SHA-256 | `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9` |
| Rows | 10200 |

The script downloads this file (or reuses a matching local copy), checks the hash and row count, keeps only `record_id`, `text`, `political_stance`, and `llm_toxicity_tier`, and sends each row to Bedrock to generate a mirrored post.

## Output layout

Artifacts are written under:

`s3://mirrorview-experimental-artifacts/experiments/generate_flips_2026_09_08/{run_id}/`

Each finished batch becomes `batches/part-NNNNN.parquet`. Failures append to `errors.jsonl`. When every post is done, the script writes one combined file, `flips.parquet`.

## Resume behavior

Rerunning with the same `--run-id` skips S3 parts that already exist and does not rewrite them. Only unfinished batches call Bedrock. Do not reuse `--run-id smoke` for the full 10,200-post job. Use a new timestamp run id instead.

## Commands

Small test run (10 posts, fixed run id `smoke`):

```bash
PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --run-id smoke --max-posts 10
```

Full 10,200-post run (omit `--max-posts`; `--run-id` defaults to the current timestamp):

```bash
PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py
```

Help:

```bash
PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --help
```
