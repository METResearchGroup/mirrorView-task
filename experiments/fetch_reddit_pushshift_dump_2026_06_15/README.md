# Academic Torrents Reddit Pushshift Toxicity Smoke Test

Chunked, resumable pipeline for raw Pushshift comment `.zst` files from [Academic Torrents](https://academictorrents.com/download/3d426c47c767d40f82c7ef0f47c3acacedd2bf44.torrent). Filters to six political subreddits, scores survivors with batched Perspective API (TOXICITY only, threshold >= 0.7), and writes per-file deliverables until 50,000 high-toxic comments are accumulated globally.

## Setup

```bash
brew install aria2
uv sync --group dev
```

Set `GOOGLE_API_KEY` in repo-root `.env`.

## Download sample data

```bash
bash experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/download_at_sample.sh
# or a specific month:
bash experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/download_at_sample.sh RC_2024-06.zst
```

Expected: `experiments/fetch_reddit_pushshift_dump_2026_06_15/data/raw/RC_2024-06.zst`

Tiny inspection files (e.g. `RC_2005-12.zst`) are also available in the torrent index.

## Run

```bash
# Unit tests (no network)
PYTHONPATH=. uv run pytest experiments/fetch_reddit_pushshift_dump_2026_06_15/tests/ -q

# Process one file
PYTHONPATH=. uv run python experiments/fetch_reddit_pushshift_dump_2026_06_15/runner.py \
  --input-file experiments/fetch_reddit_pushshift_dump_2026_06_15/data/raw/RC_2024-06.zst

# Orchestrator (default: max 10 files attempted)
PYTHONPATH=. uv run python experiments/fetch_reddit_pushshift_dump_2026_06_15/main.py

# Unlimited file cap (still stops at 50k high-toxic)
PYTHONPATH=. uv run python experiments/fetch_reddit_pushshift_dump_2026_06_15/main.py --max-files 0
```

## Outputs

For each scanned input file `RC_YYYY-MM.zst`:

```text
outputs/{stem}/
  metadata.json
  high_toxic_comments.parquet   # mirrorview 13 cols + prob_toxic, prob_toxic >= 0.7 only
outputs/total_metadata.json     # cumulative counts across files
```

Re-running a file whose `metadata.json` already exists logs `Skipping {stem}, metadata.json exists` and does not re-score.

## Background

Bolun's 16GB Google Drive package is deferred for this phase. We use Academic Torrents selective downloads instead so we can stream month files locally and scale up on Quest later.

Reference chat with Bolun (dataset scope, columns, torrent link) is preserved in git history of this README.
