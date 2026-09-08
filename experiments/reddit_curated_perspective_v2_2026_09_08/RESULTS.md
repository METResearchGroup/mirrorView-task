# Reddit curated Perspective v2 results

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --write-v2
```

The live run printed `promotions=3000`, `v2_rows=43061`, the v2 SHA-256 below, and the original SHA-256 unchanged.

## Objects

| Object | URI | SHA-256 |
| ------ | --- | ------- |
| Original curated parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview.parquet` | `1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f` |
| Curated v2 parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview_v2.parquet` | `e1d9b1494fd2ef030dc8fdc1f71980b55d972e4a01da23923fa6f61a693a3936` |

The v2 object was created with `put_new`. A re-download of the original object still matches the pinned hash. The v2 table differs from the original only in `llm_toxicity_tier` on the 3000 promoted rows.

## Rank rule

Score only comments whose original LLM toxicity tier is medium. Rank those comments together, left and right in one list, by Perspective `toxicity_prob` descending, then `source_record_id` ascending. Promote the first 3000 ids from medium to high. Ignore Perspective `toxicity_tier`.

Promotion count: 3000 (2415 left, 585 right).

## Original political stance × LLM toxicity tier

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 13423 | 15047 | 641 | 29111 |
| right | 7998 | 5680 | 272 | 13950 |
| total | 21421 | 20727 | 913 | 43061 |

## v2 political stance × LLM toxicity tier

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 13423 | 12632 | 3056 | 29111 |
| right | 7998 | 5095 | 857 | 13950 |
| total | 21421 | 17727 | 3913 | 43061 |

Medium falls from 20727 to 17727. High rises from 913 to 3913.

## Outputs

- `outputs/medium_perspective_scores.parquet`
- `outputs/promotion_source_record_ids.json`
