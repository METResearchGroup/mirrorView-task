# Data platform

Batch pipeline per platform (run from this repository root with `PYTHONPATH=.`):

```text
ingestion → preprocessing → generate_features → curate
```

Each logical collection is identified by **`dataset_id`** (`{platform}_<uuid>`), pinned in ingestion YAML (e.g. `mirrorview.yaml`) and recorded under `data_platform/data/{platform}/{dataset_id}/`. Downstream CLIs require `--dataset-id`; curate YAML is filter-only.

Curation is the final stage: all artifacts stay on local disk under `data_platform/data/`. The pipeline does not upload to S3 or register Glue tables.

Operator runbook: [docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md](../docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md).

## Stages

| Platform | Stage | Module | Output |
|----------|-------|--------|--------|
| bluesky | Ingestion | `data_platform/ingestion/` | `data_platform/data/bluesky/{dataset_id}/raw/{timestamp}/` |
| bluesky | Preprocessing | `data_platform/preprocessing/` | `.../preprocessed/{timestamp}/posts.csv` |
| bluesky | Features | `data_platform/generate_features/` | `.../features/{feature}.csv`, `metadata.json` |
| bluesky | Curate | `data_platform/curate/` | `.../curated/{timestamp}/` |
| twitter | Ingestion | `data_platform/ingestion/` | `data_platform/data/twitter/{dataset_id}/raw/{timestamp}/posts.csv` |
| twitter | Preprocessing | `data_platform/preprocessing/` | `.../preprocessed/{timestamp}/posts.csv` |
| twitter | Features | `data_platform/generate_features/` | `.../features/{feature}.csv`, `metadata.json` |
| twitter | Curate | `data_platform/curate/` | `.../curated/{timestamp}/mirrorview.csv` |
| reddit | Ingestion | `data_platform/ingestion/` | `data_platform/data/reddit/{dataset_id}/raw/{timestamp}/` |
| reddit | Preprocessing | `data_platform/preprocessing/` | `.../preprocessed/{timestamp}/` |
| reddit | Features | `data_platform/generate_features/` | `.../features/{feature}.csv`, `metadata.json` |
| reddit | Curate | `data_platform/curate/` | `.../curated/{timestamp}/mirrorview.csv` |

## Commands

Ingestion reads `dataset_id` from the ingestion config. Pass config paths relative to the repo root. `smoke.yaml` collects about 100 Bluesky posts for a local dry run.

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \
  --config data_platform/ingestion/configs/bluesky/smoke.yaml

PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml

PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \
  --config data_platform/ingestion/configs/twitter/mirrorview.yaml

PYTHONPATH=. uv run python data_platform/ingestion/sync_reddit.py \
  --config data_platform/ingestion/configs/reddit/mirrorview.yaml
```

Large syncs checkpoint per keyword/subreddit in `raw/{timestamp}/metadata.json`. Resume after interrupt:

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml \
  --run-dir <timestamp>
```

Preprocess, features, and curate require the same `--dataset-id` as in ingestion YAML:

```bash
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \
  --dataset-id bluesky_<uuid>

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_<uuid> --batch-size 64

PYTHONPATH=. uv run python data_platform/curate/curate_bluesky.py \
  --dataset-id bluesky_<uuid> --config mirrorview.yaml
```

Same pattern for Twitter and Reddit (`preprocess_twitter.py` / `generate_twitter_features.py` / `curate_twitter.py`, and the Reddit equivalents).

## Curate (join + business rules)

Joins the latest preprocessed posts with all feature label CSVs (DuckDB), then applies YAML filters.

Mirrorview configs: `data_platform/curate/configs/{bluesky,twitter,reddit}/mirrorview.yaml`

- Filters: `news_or_opinion_category == opinion`, `is_political`, `is_likely_spam == false`, `political_stance in [left, right]`, `is_self_contained`, `is_structurally_complete` all true.
- `is_news_or_opinion.category` is exposed as **`news_or_opinion_category`** in the wide table and export CSV.
- `is_likely_spam.is_likely_spam` is exposed as **`is_likely_spam`** in the wide table and export CSV.

Do not commit `data_platform/data/` run artifacts.
