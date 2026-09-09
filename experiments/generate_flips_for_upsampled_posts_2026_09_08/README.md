# Generate flips for upsampled posts

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

Generate politically mirrored posts for the unified 2,300 post upsample (2,000 unused medium posts plus 300 promoted right-high posts). Run a 10 post smoke first, then the full job under a new timestamp run id. Do not reuse `--run-id smoke` for the full 2,300 post job.

Pinned input: `s3://mirrorview-experimental-artifacts/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/unified_upsampled_posts.parquet`

Parts are written under `s3://mirrorview-experimental-artifacts/experiments/generate_flips_for_upsampled_posts_2026_09_08/{run_id}/`. After a full run, the concatenated file is also written to `s3://mirrorview-experimental-artifacts/experiments/generate_flips_2026_09_08/flips_unified_upsampled_posts.parquet`. A second upload of that named key fails. The 10 post smoke does not write that named object.

## Smoke

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --run-id smoke --max-posts 10
```

## Full run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --run-id 2026_09_09-HH:MM:SS
```

Use a timestamp run id. Omit `--max-posts`.
