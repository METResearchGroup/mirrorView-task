# Bluesky Data-Platform Smoke

**Date:** 2026-08-28
**Status:** Complete

## Summary

Ran the Bluesky smoke config through ingest, preprocess, feature generation, and MirrorView curation. The pipeline completed with no failed feature batches and no deadletter file.

The smoke collected 97 unique posts out of 100 requested. Preprocess kept 54. Feature generation labeled all 54 posts on all 7 features. Curation kept 30 posts. The curated set is usable as a dry-run export, but it is not ideology-balanced (28 left, 2 right).

## Purpose

Confirm that `data_platform/` works in this repository after it was landed from the lab ingest stack.

The run is intended to identify:

- Whether the documented smoke commands succeed against live Bluesky, OpenAI, and Perspective APIs
- How much of a 100-post keyword pull survives preprocess and curation
- Which operator gotchas should be recorded before a larger collection

## Setup

- Config: `data_platform/ingestion/configs/bluesky/smoke.yaml` (copy in `smoke.yaml`)
- Dataset id: `bluesky_c0ffee00-0000-4000-8000-000000000100`
- Platform: Bluesky keyword search (`sort: latest`)
- Keywords: `climate change`, `gun control`, `abortion`, `immigration`
- Per-keyword limit: 25
- Max rows: 100
- Curate rules: `data_platform/curate/configs/bluesky/mirrorview.yaml`
- Feature model: `gpt-5.4-nano` (temperature 0)
- Toxicity: Google Perspective API, tiers low (<= 0.1), medium (0.1 to 0.7), high (>= 0.7)
- Batch size: 64
- Max concurrency: 80
- Environment: Cursor Cloud Agent, 2026-08-28, logged-in Bluesky lab account, API keys from process environment

This is a single-condition smoke, not a comparison. Only Bluesky was run.

## Flow

```text
smoke.yaml
→ sync_bluesky.py (searchPosts per keyword, dedupe, checkpoint)
→ preprocess_bluesky.py (length, URL, English, phone)
→ generate_bluesky_features.py (7 labels)
→ curate_bluesky.py (DuckDB join + MirrorView filters)
→ copy artifacts into this experiment folder
```

## Run

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \
  --config data_platform/ingestion/configs/bluesky/smoke.yaml

PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \
  --dataset-id bluesky_c0ffee00-0000-4000-8000-000000000100

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_c0ffee00-0000-4000-8000-000000000100 --batch-size 64

PYTHONPATH=. uv run python data_platform/curate/curate_bluesky.py \
  --dataset-id bluesky_c0ffee00-0000-4000-8000-000000000100 --config mirrorview.yaml
```

Wall time on this machine: ingest ~4 s, preprocess ~1 s, features ~24 s, curate ~1 s.

## Results

### Pipeline funnel

| Stage | n | Notes |
| ----- | -: | ----- |
| Requested | 100 | `max_rows` |
| Fetched across keywords | 100 | 25 per keyword |
| Unique raw posts | 97 | 3 cross-keyword duplicates |
| Preprocessed | 54 | 43 failed validators |
| Feature-labeled | 54 | 7 features, 0 failed batches |
| Curated | 30 | MirrorView YAML filters |

### Ingestion

Raw run: `data/bluesky/bluesky_c0ffee00-0000-4000-8000-000000000100/raw/2026_08_28-16:45:41/`

| Keyword | Pages | Rows collected | Rows appended |
| ------- | ----: | -------------: | ------------: |
| climate change | 2 | 25 | 25 |
| gun control | 2 | 25 | 22 |
| abortion | 1 | 25 | 25 |
| immigration | 2 | 25 | 25 |

`sync_status` was `completed`. Raw text length ranged from 4 to 300 characters (median 246).

### Preprocess

Preprocessed run: `.../preprocessed/2026_08_28-16:45:56/`

Kept 54 of 97. Validator failures (a post can fail more than one check):

| Check | Failures |
| ----- | -------: |
| URL / domain-like token | 34 |
| Length not in 100 to 300 | 20 |
| Not English | 7 |
| Phone number | 0 |
| Any failure | 43 |

The URL check was the largest single drop. Surviving posts had length 104 to 300 (median 256).

### Features

Feature dir: `.../features/`

| Feature | n labeled | Failed batches | Distribution |
| ------- | --------: | -------------: | ------------ |
| `is_news_or_opinion` | 54 | 0 | opinion 42, news 10, neither 2 |
| `is_political` | 54 | 0 | true 52, false 2 |
| `is_likely_spam` | 54 | 0 | false 54 |
| `is_self_contained` | 54 | 0 | true 45, false 9 |
| `is_structurally_complete` | 54 | 0 | true 52, false 2 |
| `is_toxic_tiered` | 54 | 0 | low 26, medium 27, high 1 |
| `political_stance` | 54 | 0 | left 30, neutral 14, unclear 7, right 3 |

Toxicity probability on the 54 preprocessed posts: min 0.0069, median 0.1120, max 0.8300.

`features/metadata.json` has `sync_status: completed`. There is no `deadletter.jsonl`.

### Curation

Curated run: `.../curated/2026_08_28-16:48:17/`

| Filter | Before | After |
| ------ | -----: | ----: |
| `news_or_opinion_category == opinion` | 54 | 42 |
| `is_political == true` | 42 | 40 |
| `is_likely_spam == false` | 40 | 40 |
| `political_stance in [left, right]` | 40 | 33 |
| `is_self_contained == true` | 33 | 30 |
| `is_structurally_complete == true` | 30 | 30 |

Curated export (`mirrorview.csv`, 30 rows):

| Field | Value |
| ----- | ----- |
| Stance | left 28, right 2 |
| Toxicity tier | low 10, medium 19, high 1 |
| Toxicity probability | min 0.021, median 0.266, max 0.830 |
| Text length | min 104, median 290, max 300 |

Stance by toxicity in the curated file:

| Stance | high | low | medium |
| ------ | ---: | --: | -----: |
| left | 1 | 8 | 19 |
| right | 0 | 2 | 0 |

Outputs:

- `data/bluesky/bluesky_c0ffee00-0000-4000-8000-000000000100/dataset.json`
- `data/.../raw/2026_08_28-16:45:41/posts.csv`
- `data/.../raw/2026_08_28-16:45:41/metadata.json`
- `data/.../preprocessed/2026_08_28-16:45:56/posts.csv`
- `data/.../preprocessed/2026_08_28-16:45:56/metadata.json`
- `data/.../features/*.csv` and `metadata.json`
- `data/.../curated/2026_08_28-16:48:17/mirrorview.csv`
- `data/.../curated/2026_08_28-16:48:17/metadata.json`
- `run_logs/01_ingestion.log` through `run_logs/04_curate.log`

## Conclusion

The documented Bluesky smoke path works in this repository. Live search, preprocess gates, LLM labels, Perspective scoring, and MirrorView curation all completed.

Use this as a dry-run check, not as a stimuli sample. Thirty curated posts from latest-keyword search are enough to prove the plumbing. They are not enough, and not balanced enough, for a new study round. The next collection should keep the same stage commands, use a larger ingest config, and expect preprocess (especially the URL check) plus the left/right stance filter to remove a large share of raw rows.

Operator traps from this run are in [`NOTES.md`](./NOTES.md).
