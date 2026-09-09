# Generate flips for upsampled posts, results

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

PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --run-id 2026_09_09-00:51:31
```

## Pinned input

Object `s3://mirrorview-experimental-artifacts/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/unified_upsampled_posts.parquet` SHA-256 `853ae3e2b58bf8e4629c1a83c22bde28fbfdf57b10631511625ce97b72aaa007` has 2300 rows.

## Counts

| Field | Value |
| ----- | ----: |
| `part_count` | 92 |
| `row_count` | 2295 |
| `failed_count` | 5 |

`row_count` plus `failed_count` is 2300.

## Output

| File | URI | SHA-256 |
| ---- | --- | ------- |
| Run-prefix flips | `s3://mirrorview-experimental-artifacts/experiments/generate_flips_for_upsampled_posts_2026_09_08/2026_09_09-00:51:31/flips.parquet` | |
| Named sibling | `s3://mirrorview-experimental-artifacts/experiments/generate_flips_2026_09_08/flips_unified_upsampled_posts.parquet` | `67d43ccec1725670306c2fe15f52101cee7dc21f273448dd3f9221562d168120` |
