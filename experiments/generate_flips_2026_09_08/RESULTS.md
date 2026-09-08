# Generate flips for the filtered stimulus sample, results

## Smoke

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --run-id smoke --max-posts 10
```

`row_count=10`. `failed_count=0`.

## Full run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --run-id 2026_09_08-20:31:31
```

`FULL_RUN_ID` is `2026_09_08-20:31:31`.

## Pinned input

| Field | Value |
|-------|-------|
| URI | `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` |
| SHA-256 | `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9` |
| Rows | 10200 |

## Counts

| Field | Value |
|-------|------:|
| `part_count` | 408 |
| `row_count` | 10182 |
| `failed_count` | 18 |

`row_count` plus `failed_count` is 10200.

## Output

| File | URI | SHA-256 |
|------|------|---------|
| Combined flips | `s3://mirrorview-experimental-artifacts/experiments/generate_flips_2026_09_08/2026_09_08-20:31:31/flips.parquet` | `f3b791f226f8f69d3ddaf0737aab0a3aaf20ebb36d45a6d9b42dec8d1e148702` |

Parts under `experiments/generate_flips_2026_09_08/2026_09_08-20:31:31/batches/` are immutable. Rerunning the same `--run-id` skips existing parts and does not rewrite them.
