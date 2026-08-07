# How to run data ingestion

Sync Bluesky, Twitter, and Reddit through preprocess → features → curate in this repository. Curated exports land under `data_platform/data/` and feed the existing sample and stimuli path.

## Prerequisites

1. From repo root: `uv sync`
2. Always use `PYTHONPATH=.`
3. Put API keys in repo-root `.env`:

```text
BLUESKY_HANDLE=
BLUESKY_PASSWORD=
REDDIT_CLIENT_ID=
REDDIT_SECRET=
REDDIT_REDIRECT_URI=
REDDIT_USERNAME=
REDDIT_PASSWORD=
X_BEARER_TOKEN=
X_CONSUMER_KEY=
X_SECRET_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
```

AWS credentials are only needed if you enable Bluesky S3 upload (see below).

## Bluesky S3 default

Bluesky sync is local-only by default. It does not write to the shared lab S3 bucket unless you set:

```bash
export DATA_PLATFORM_BLUESKY_S3_UPLOAD=1
```

Twitter and Reddit are always local-disk pipelines. Successful local syncs are marked durable so preprocess can run without a cloud upload.

## Per-platform commands

Edit or clone ingestion YAML under `data_platform/ingestion/configs/<platform>/` (keywords, limits, `dataset_id`). Then run each stage with that `dataset_id`.

### Bluesky

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml

PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \
  --dataset-id bluesky_<uuid>

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_<uuid> --batch-size 64

PYTHONPATH=. uv run python data_platform/curate/curate_bluesky.py \
  --dataset-id bluesky_<uuid> --config mirrorview.yaml
```

### Twitter

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \
  --config data_platform/ingestion/configs/twitter/mirrorview.yaml

PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_twitter.py \
  --dataset-id twitter_<uuid>

PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \
  --dataset-id twitter_<uuid> --batch-size 64

PYTHONPATH=. uv run python data_platform/curate/curate_twitter.py \
  --dataset-id twitter_<uuid> --config mirrorview.yaml
```

### Reddit

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_reddit.py \
  --config data_platform/ingestion/configs/reddit/mirrorview.yaml

PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_reddit.py \
  --dataset-id reddit_<uuid>

PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py \
  --dataset-id reddit_<uuid> --batch-size 64

PYTHONPATH=. uv run python data_platform/curate/curate_reddit.py \
  --dataset-id reddit_<uuid> --config mirrorview.yaml
```

Confirm outputs:

```text
data_platform/data/<platform>/<dataset_id>/curated/<timestamp>/mirrorview.csv
data_platform/data/<platform>/<dataset_id>/curated/<timestamp>/metadata.json
```

Do not commit `data_platform/data/` run artifacts.

## Handoff to stimuli

After curated `mirrorview.csv` exists for all three platforms:

```bash
PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py
```

That discovers metadata under `data_platform/data/*/…/curated/*/metadata.json` and writes `concatenated_records/<timestamp>/records.csv` under the experiment folder.

Then continue with flip generation / balance in that experiment, promote a job CSV, and follow:

- [HOW_TO_REPLACE_STIMULI_DATASET.md](HOW_TO_REPLACE_STIMULI_DATASET.md)
- [SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md](SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md)

New post IDs require regenerating precomputed assignments in `study_participant_assignment_interface` and updating the assignment batch URI in the webapp / job YAML.
