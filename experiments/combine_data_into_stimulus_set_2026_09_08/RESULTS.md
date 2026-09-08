# Combine curated data into a stimulus set, results

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/combine_data_into_stimulus_set_2026_09_08/run.py
```

## Sources

| Platform | Dataset id | Curated run | Object | SHA-256 | Rows |
| -------- | ---------- | ----------- | ------ | ------- | ---: |
| bluesky | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` | `2026_09_06-23:25:06` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/curated/2026_09_06-23:25:06/mirrorview.parquet` | `35e3f05111a16c27b95538894cda18db6d7295c8aad6be4fb7cb83ecafb1b3bc` | 9756 |
| twitter | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` | `2026_09_07-06:58:09` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/curated/2026_09_07-06:58:09/mirrorview.parquet` | `7639e54554869371fdb6397a1c2a497b32711679290322b999fb68ee173f39c9` | 1457 |
| twitter | `twitter_5901767a-e609-46fc-9a17-742516b548f2` | `2026_09_08-05:34:19` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/curated/2026_09_08-05:34:19/mirrorview.parquet` | `c2178c27165c26dd960bd470e3ee98791e7c98638a346eca0f0fafa1c065c8e2` | 1299 |
| reddit | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` | `2026_09_07-21:47:32` | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview_v2.parquet` | `e1d9b1494fd2ef030dc8fdc1f71980b55d972e4a01da23923fa6f61a693a3936` | 43061 |

Combined row count is 55573. Expected row count is 55573.

## Combined parquet

| File | Path | SHA-256 |
| ---- | ---- | ------- |
| Local parquet | `experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet` | `f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0` |
| S3 parquet | `s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet` | `f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0` |

## Overall political stance by LLM toxicity tier

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 18061 | 17071 | 3662 | 38794 |
| right | 9261 | 6374 | 1144 | 16779 |
| total | 27322 | 23445 | 4806 | 55573 |

## Political stance by LLM toxicity tier, by platform

| integration | political_stance | low | medium | high | total |
| ----------- | ---------------- | --: | -----: | ---: | ----: |
| bluesky | left | 3563 | 4179 | 585 | 8327 |
| bluesky | right | 529 | 755 | 145 | 1429 |
| bluesky | total | 4092 | 4934 | 730 | 9756 |
| reddit | left | 13423 | 12632 | 3056 | 29111 |
| reddit | right | 7998 | 5095 | 857 | 13950 |
| reddit | total | 21421 | 17727 | 3913 | 43061 |
| twitter | left | 1075 | 260 | 21 | 1356 |
| twitter | right | 734 | 524 | 142 | 1400 |
| twitter | total | 1809 | 784 | 163 | 2756 |
| total | total | 27322 | 23445 | 4806 | 55573 |
