# Data platform

Batch pipeline per platform (run from this repository root with `PYTHONPATH=.`):

```text
ingestion → preprocessing → generate_features → curate
```

Each logical collection is identified by **`dataset_id`** (`{platform}_<uuid>`), pinned in ingestion YAML (e.g. `mirrorview.yaml`) and recorded under `data_platform/data/{platform}/{dataset_id}/`. Downstream CLIs require `--dataset-id`. Curate YAML files contain only filter rules.

Curation is the final stage. All artifacts stay on local disk under `data_platform/data/`. The pipeline does not upload to S3 or register AWS Glue tables.

See the operator runbook at [docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md](../docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md).

## Stages

| Platform | Stage | Module | Output |
|----------|-------|--------|--------|
| bluesky | Ingestion | `data_platform/ingestion/` | `data_platform/data/bluesky/{dataset_id}/raw/{timestamp}/` |
| bluesky | Preprocessing | `data_platform/preprocessing/` | `.../preprocessed/{timestamp}/posts.csv` |
| bluesky | Features | `data_platform/generate_features/` | `.../features/{timestamp}/{feature}.csv`, `metadata.json` |
| bluesky | Curate | `data_platform/curate/` | `.../curated/{timestamp}/` |
| twitter | Ingestion | `data_platform/ingestion/` | `data_platform/data/twitter/{dataset_id}/raw/{timestamp}/posts.csv` |
| twitter | Preprocessing | `data_platform/preprocessing/` | `.../preprocessed/{timestamp}/posts.csv` |
| twitter | Features | `data_platform/generate_features/` | `.../features/{timestamp}/{feature}.csv`, `metadata.json` |
| twitter | Curate | `data_platform/curate/` | `.../curated/{timestamp}/mirrorview.csv` |
| reddit | Ingestion | `data_platform/ingestion/` | `data_platform/data/reddit/{dataset_id}/raw/{timestamp}/comments.csv` |
| reddit | Preprocessing | `data_platform/preprocessing/` | `.../preprocessed/{timestamp}/` |
| reddit | Features | `data_platform/generate_features/` | `.../features/{timestamp}/{feature}.csv`, `metadata.json` |
| reddit | Curate | `data_platform/curate/` | `.../curated/{timestamp}/mirrorview.csv` |

## Commands

The ingestion CLI reads `dataset_id` from the ingestion config. Pass config paths relative to the repo root. The `smoke.yaml` config collects about 100 Bluesky posts for a local dry run.

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py new-run \
  --config data_platform/ingestion/configs/bluesky/smoke.yaml

PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py new-run \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml

PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \
  --config data_platform/ingestion/configs/twitter/mirrorview.yaml

PYTHONPATH=. uv run python data_platform/ingestion/sync_reddit.py \
  --config data_platform/ingestion/configs/reddit/mirrorview.yaml
```

Large syncs write a checkpoint per keyword or subreddit to `raw/{timestamp}/metadata.json`. Resume a named Bluesky run after interrupt:

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py resume \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml \
  --run-dir <timestamp>
```

Resume the latest unfinished Bluesky run instead:

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py resume \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml \
  --latest
```

Preprocess, features, and curate require the same `--dataset-id` as in ingestion YAML:

```bash
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \
  --dataset-id bluesky_<uuid>

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  new-run --dataset-id bluesky_<uuid> --batch-size 64

PYTHONPATH=. uv run python data_platform/curate/curate_bluesky.py \
  --dataset-id bluesky_<uuid> --config mirrorview.yaml
```

To continue an unfinished feature run, use `resume` with that folder's timestamp, or with `--latest`.

```bash
PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  resume --dataset-id bluesky_<uuid> --checkpoint <timestamp>

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  resume --dataset-id bluesky_<uuid> --latest
```

Twitter and Reddit use the same preprocess, feature, and curate scripts, with `twitter` or `reddit` in the script names. `new-run` creates a new `features/<timestamp>/` folder, and it exits with an error if an unfinished feature run already exists. `resume` keeps writing into an unfinished feature run folder. You cannot resume a completed feature run. Posts that already have labels in any feature folder are skipped. A completed feature stays closed for new posts, and those posts are labeled in a later `new-run`.

If a dataset still has leftover files directly under `features/` from the old layout, move them into a new `features/<timestamp>/` folder and delete the leftover files at the features root.

## Curate (join + business rules)

The curate step joins the latest preprocessed posts with all feature label CSVs using DuckDB, and then applies YAML filters.

Mirrorview configs: `data_platform/curate/configs/{bluesky,twitter,reddit}/mirrorview.yaml`

- Filters: `news_or_opinion_category == opinion`, `is_political`, `is_likely_spam == false`, `political_stance in [left, right]`, `is_self_contained`, `is_structurally_complete` all true.
- `is_news_or_opinion.category` is exposed as **`news_or_opinion_category`** in the wide table and export CSV.
- `is_likely_spam.is_likely_spam` is exposed as **`is_likely_spam`** in the wide table and export CSV.

Do not commit `data_platform/data/` run artifacts.
