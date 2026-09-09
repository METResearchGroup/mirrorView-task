# Upsample unused medium toxicity posts, results

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_medium_toxicity_posts_2026_09_08/run.py
```

## Upsampled parquet

| File | Path | SHA-256 |
| ---- | ---- | ------- |
| Local parquet | `experiments/upsample_medium_toxicity_posts_2026_09_08/upsample_2000_medium_toxicity_posts.parquet` | `54a3fe28e5570a19cdcbf1ec33bb910d27decb98902339b3d0fa75e775f113d6` |
| S3 parquet | `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/upsample_2000_medium_toxicity_posts.parquet` | `54a3fe28e5570a19cdcbf1ec33bb910d27decb98902339b3d0fa75e775f113d6` |

## Sampled unused medium posts

| Field | Count |
| ----- | ----: |
| Sampled rows | 2000 |
| Left medium | 1000 |
| Right medium | 1000 |
| Leftover left medium before sample | 15203 |
| Leftover right medium before sample | 3865 |
