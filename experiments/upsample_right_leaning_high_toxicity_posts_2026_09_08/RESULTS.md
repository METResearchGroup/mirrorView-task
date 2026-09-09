# Upsample right-leaning high toxicity posts, results

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/run.py
```

## Candidates

| Field | Count |
| ----- | ----: |
| Candidate rows | 2865 |
| Leftover right medium after 2000 upsample | 2865 |
| Pull request 260 ids dropped | 0 |
| Promotions | 300 |
| Unified rows | 2300 |
| Unified medium | 2000 |
| Unified high | 300 |

## Parquet files

| File | Path | SHA-256 |
| ---- | ---- | ------- |
| Local 300 row parquet | `experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/upsample_300_right_high_toxicity_posts.parquet` | `f97b8ce089f5ed49037fdb9eb9e48d19d78c2cee4a47d07245bcc832786b4df1` |
| S3 300 row parquet | `s3://mirrorview-experimental-artifacts/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/upsample_300_right_high_toxicity_posts.parquet` | `f97b8ce089f5ed49037fdb9eb9e48d19d78c2cee4a47d07245bcc832786b4df1` |
| Local unified parquet | `experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/unified_upsampled_posts.parquet` | `853ae3e2b58bf8e4629c1a83c22bde28fbfdf57b10631511625ce97b72aaa007` |
| S3 unified parquet | `s3://mirrorview-experimental-artifacts/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/unified_upsampled_posts.parquet` | `853ae3e2b58bf8e4629c1a83c22bde28fbfdf57b10631511625ce97b72aaa007` |

## Unified political stance by toxicity

The unified table has 1,000 left posts and 1,300 right posts. It has 2,000 medium posts and 300 high posts.
