# Filter posts used for stimulus dataset, results

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py
```

## Candidate source

Object `s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet` SHA-256 `f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0` has 55573 rows.

## Cleanup

| Step | Rows dropped | Rows remaining |
| ---- | -----------: | -------------: |
| Start | 0 | 55573 |
| Previously used record ids | 0 | 55573 |
| Previously used original text | 42 | 55531 |
| Duplicate record ids | 571 | 54960 |
| Duplicate text | 488 | 54472 |

## Filtered parquet

| File | Path | SHA-256 |
| ---- | ---- | ------- |
| Local parquet | `experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` | `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9` |
| S3 parquet | `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` | `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9` |

Sampled row count is 10200. Aimed total is 10200.

## Cleaned political stance by LLM toxicity tier

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 17644 | 16903 | 3638 | 38185 |
| right | 9022 | 6203 | 1062 | 16287 |
| total | 26666 | 23106 | 4700 | 54472 |

## Sampled political stance by LLM toxicity tier

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 1700 | 1700 | 1700 | 5100 |
| right | 1700 | 2338 | 1062 | 5100 |
| total | 3400 | 4038 | 2762 | 10200 |

Operators kept every cleaned post in the cell for right stance and high toxicity, because the cell had 1062 posts. 1062 is fewer than 1700.

Operators sampled 638 extra posts from the cell for right stance and medium toxicity so that left and right both have the same number of posts, and the sample has 10200 posts.
