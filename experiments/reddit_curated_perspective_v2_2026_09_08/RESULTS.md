# Reddit curated Perspective, second file, results

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --write-v2
```

The live run printed `promotions=3000` and `v2_rows=43061`. It also printed the SHA-256 of `mirrorview_v2.parquet`, shown in the table below, and it printed that the original SHA-256 was unchanged.

## Parquet files

| File | URI | SHA-256 |
| ---- | --- | ------- |
| Original curated parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview.parquet` | `1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f` |
| Second curated parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview_v2.parquet` | `e1d9b1494fd2ef030dc8fdc1f71980b55d972e4a01da23923fa6f61a693a3936` |

`mirrorview_v2.parquet` was uploaded with `put_new`, so the write fails if that key already exists. Downloading `mirrorview.parquet` again still matches the recorded SHA-256. `mirrorview_v2.parquet` differs from `mirrorview.parquet` only in `llm_toxicity_tier` on the 3,000 comments whose tier changed from medium to high.

## How comments were ranked

Score only comments whose original LLM toxicity tier is medium. Rank those comments in one list, mixing `political_stance` left and right. Sort by Perspective `toxicity_prob` from high to low, and by `source_record_id` from low to high when probabilities tie. Change the first 3,000 ids from medium to high. Do not use Perspective's own `toxicity_tier` label when ranking, because the rank key is the probability number.

The tier changed on 3,000 comments, 2,415 left and 585 right.

## Original political stance by LLM toxicity tier

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 13423 | 15047 | 641 | 29111 |
| right | 7998 | 5680 | 272 | 13950 |
| total | 21421 | 20727 | 913 | 43061 |

## Second file, political stance by LLM toxicity tier

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 13423 | 12632 | 3056 | 29111 |
| right | 7998 | 5095 | 857 | 13950 |
| total | 21421 | 17727 | 3913 | 43061 |

The medium count is 17,727 instead of 20,727, and the high count is 3,913 instead of 913.

## Outputs

- `outputs/medium_perspective_scores.parquet`
- `outputs/promotion_source_record_ids.json`
