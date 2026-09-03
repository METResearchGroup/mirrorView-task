# How to run data ingestion

Sync Bluesky, Twitter, and Reddit through preprocess → features → curate in this repository. Curated exports are written under `data_platform/data/`, and they are the input for `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`.

## Prerequisites

1. From repo root: `uv sync`
2. Always use `PYTHONPATH=.`
3. Put API keys in repo-root `.env`. Bluesky keyword search can run without
`BLUESKY_HANDLE` and `BLUESKY_PASSWORD`. In that case the client uses the
public Bluesky API at `https://api.bsky.app`. Set the Bluesky vars if you need a
logged-in session. Feature generation still needs `OPENAI_API_KEY` and
`GOOGLE_API_KEY`.

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

## Per-platform commands

Edit or clone ingestion YAML under `data_platform/ingestion/configs/<platform>/` (keywords, limits, `dataset_id`). Then run each stage with that `dataset_id`.

### Bluesky

```bash
# Small local smoke collection (~100 posts):
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \
  --config data_platform/ingestion/configs/bluesky/smoke.yaml

PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml

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

Feature generation writes each run into a new folder named `features/<timestamp>/`. `new-run` creates that folder, and it exits with an error if an unfinished feature run already exists. If a run stops partway through, `resume --checkpoint <timestamp>` reuses the same folder. `resume --latest` reuses the newest unfinished folder. You cannot reopen a completed feature run.

Feature generation still skips a post that already has a label, including labels written in earlier feature folders. A feature marked completed in this folder stays completed even if new posts appear. Those posts are labeled in a later `new-run`. When the same post appears in more than one feature folder, the curate step keeps the row with the latest `label_timestamp`.

If this dataset still has leftover files directly under `features/` from the old layout (`is_political.csv`, `metadata.json`, `deadletter.jsonl`), move them into a new `features/<timestamp>/` folder and delete the leftover files at the features root.

The smoke config uses `dataset_id: bluesky_c0ffee00-0000-4000-8000-000000000100`. Curation is the last stage. Files stay under `data_platform/data/`.

### Twitter

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \
  --config data_platform/ingestion/configs/twitter/mirrorview.yaml

PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_twitter.py \
  --dataset-id twitter_<uuid>

PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \
  new-run --dataset-id twitter_<uuid> --batch-size 64

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
  new-run --dataset-id reddit_<uuid> --batch-size 64

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

`sample_data_to_mirror.py` reads metadata under `data_platform/data/<platform>/<dataset_id>/curated/<timestamp>/metadata.json`, and it writes `concatenated_records/<timestamp>/records.csv` under the experiment folder.

Then run flip generation and balancing in that experiment. Promote a job CSV, and follow the runbooks below.

- [HOW_TO_REPLACE_STIMULI_DATASET.md](HOW_TO_REPLACE_STIMULI_DATASET.md)
- [SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md](SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md)

New post IDs require regenerating precomputed assignments in `study_participant_assignment_interface` and updating the assignment batch URI in the webapp / job YAML.
