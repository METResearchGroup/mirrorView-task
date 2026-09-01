# Notes and gotchas, Bluesky data-platform smoke

These notes are from running the smoke pipeline on 2026-08-28 in the Cursor Cloud Agent environment. They are meant to help the next person rerun this path without rediscovering the same traps.

## Where the docs live

Read these first:

- `docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md` has the copy-paste commands and env vars.
- `docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` explains stages, disk layout, checkpoints, and the smoke example.
- `data_platform/README.md` is the module map.
- `docs/runbooks/HISTORY_OF_STUDY.md` explains why the filters exist (English, 100 to 300 characters, opinion, political, self-contained, complete, toxicity tiers).

The architecture doc already documents the smoke `dataset_id`: `bluesky_c0ffee00-0000-4000-8000-000000000100`.

This smoke stops at curated Bluesky output. It does not run `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`. That script globs curated exports for Bluesky, Twitter, and Reddit together.

## Environment and secrets

- Always run from the repo root with `PYTHONPATH=.`. Imports resolve `data_platform/` and `lib/`.
- `uv sync --no-dev` is enough for this pipeline. The default `uv sync` also installs the `dev` group (torch, transformers, spaCy), which is large and unused here.
- Runbooks tell you to put keys in a repo-root `.env`. `lib/load_env_vars.py` loads `.env` if present, then reads `os.getenv`. In this Cloud Agent environment there was no `.env` file. `OPENAI_API_KEY` and `GOOGLE_API_KEY` were already in the process environment, and that was sufficient.
- Feature generation needs `OPENAI_API_KEY` (LangChain `gpt-5.4-nano`) and `GOOGLE_API_KEY` (Perspective API). Ingestion does not need those keys.
- Bluesky login is optional. If both `BLUESKY_HANDLE` and `BLUESKY_PASSWORD` are set, `init_bluesky_client()` logs into the account PDS. If both are unset, it uses the public AppView at `https://api.bsky.app`. If only one is set, it raises.
- This environment had both Bluesky vars set. Login succeeded against the lab account PDS (`*.host.bsky.network`), not the public AppView.
- AWS credentials are not used. Curated files stay on local disk. Do not expect S3, Glue, or Athena writes.

## Git and artifact storage

- `data_platform/data/` is gitignored. The pipeline writes there. This experiment copies the dataset into `experiments/data_ingestion_smoke_2026_08_28/data/` so the PR can include raw, preprocessed, feature, and curated files.
- The repo-wide `*.csv` rule would drop those copies. `.gitignore` now has an exception for this experiment folder.
- `*.log` is also gitignored. The same exception re-includes `run_logs/*.log`. Stage logs live in `run_logs/` rather than `logs/` because a repo-wide `logs` ignore rule would hide a directory named `logs`.
- Do not commit `data_platform/data/` itself.

## Ingestion gotchas

- The smoke config asks for `limit: 25` posts per keyword and `max_rows: 100` across four keywords (`climate change`, `gun control`, `abortion`, `immigration`). That is 100 requested rows. This run wrote 97 unique rows because 3 posts matched more than one keyword (`posts_skipped_as_duplicates: 3`). `gun control` collected 25 and appended 22.
- Keywords with spaces are quoted before `searchPosts`. That is handled in `sync_bluesky.py`.
- Each keyword is its own checkpoint task in `raw/<timestamp>/metadata.json`. A completed run sets `sync_status: completed`. Resume with `--run-dir <timestamp>` only for an incomplete run.
- If you rerun `sync_bluesky.py` against the same `dataset_id` after a completed smoke, the CLI starts a new timestamped raw directory. Preprocess then loads **all** raw run directories, not just the latest. Reusing the pinned smoke `dataset_id` will mix collections unless you delete the old raw runs first.
- `hits_total` was `10000` for every keyword. Treat that as a Bluesky search ceiling, not a true hit count.
- `smoke.yaml` has `date: "2026-08-16"`. That is the config authorship date, not the run date.
- Raw `posts.csv` contains multiline post text. `wc -l` overcounts rows. Use pandas or the `row_count` field in `metadata.json`.

## Preprocess gotchas

- Preprocess is gated on `require_all_runs_complete`. An in-progress raw sync will block it.
- Validators are all-or-nothing per post: length 100 to 300 characters, no URLs, English (`langdetect`), no phone numbers. There is no per-validator breakdown in `preprocessed/*/metadata.json`. This run kept 54 of 97. Recomputed drop reasons:

  - URL / domain-like token: 34
  - length outside 100 to 300: 20
  - not English: 7
  - phone number: 0
  - failed at least one check: 43

- The URL regex is aggressive. It matches `http(s)`, `www.`, and `[token].[tld]` patterns, so many posts with a domain mention are dropped even when they are otherwise usable.
- `HISTORY_OF_STUDY.md` describes length as measured after stripping URLs and phones. The code checks length on the raw text and separately rejects any post with a URL. Posts with links never get a length-after-strip second chance.
- The 300-character upper bound is also the Bluesky post cap, so the length filter is mostly a minimum-length filter plus rejection of very short posts.

## Feature generation gotchas

- Features write flat files under `features/{name}.csv` plus `features/metadata.json`. They are not timestamped like raw, preprocessed, and curated runs. Reruns append labels for unlabeled URIs and skip completed features.
- Default model is `gpt-5.4-nano` in `ml_tooling/llm/llm.py`. A one-call probe succeeded before the full run. Temperature is `0.0`.
- Registry order: `is_news_or_opinion`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `is_toxic_tiered`, `political_stance`.
- LLM features use LangChain `Runnable.batch` with `--batch-size 64` and `--max-concurrency 80`. This smoke had 54 preprocessed posts, so each LLM feature was a single atomic batch.
- If that batch fails after retries, all 54 URIs go to `features/deadletter.jsonl` and the feature is not marked complete. Curate then refuses to run (`require_features_complete`). Smaller `--batch-size` is more resilient for a first live run; the runbook still uses 64.
- `is_toxic_tiered` is not an LLM call. It uses the Perspective API via `GOOGLE_API_KEY`, with thread-pool concurrency up to 80 and HTTP retries on 429/5xx. This small run did not rate-limit.
- This run labeled 54/54 for all seven features with zero failed batches and no deadletter file. Wall time was about 24 seconds.

## Curate gotchas

- `--config mirrorview.yaml` is resolved under `data_platform/curate/configs/bluesky/`, not as a repo-root path.
- Curate joins the latest preprocessed posts to every feature CSV with DuckDB, then applies filters in YAML order. `is_news_or_opinion.category` is exposed as `news_or_opinion_category`.
- Filters kept 30 of 54 posts. Sequential drops:

  - `news_or_opinion_category == opinion`: 54 to 42
  - `is_political == true`: 42 to 40
  - `is_likely_spam == false`: 40 to 40
  - `political_stance in [left, right]`: 40 to 33 (drops `neutral` and `unclear`)
  - `is_self_contained == true`: 33 to 30
  - `is_structurally_complete == true`: 30 to 30

- If inputs have not changed, curate prints `already up to date, skipping` and does not write a new timestamp.
- The curated export for this smoke is heavily left-skewed (28 left, 2 right). Latest-post keyword search on these four terms is not a balanced ideology sample. Production collection still needs the later sampling/balancing step.

## Helpful commands

Confirm keys without printing them:

```bash
PYTHONPATH=. uv run python -c "from lib.load_env_vars import EnvVarsContainer as E; print('openai', bool(E.get_env_var('OPENAI_API_KEY', required=True))); print('google', bool(E.get_env_var('GOOGLE_API_KEY', required=True)))"
```

Inspect row counts from metadata rather than line counts:

```bash
PYTHONPATH=. uv run python -c "import json; from pathlib import Path; p=Path('data_platform/data/bluesky/bluesky_c0ffee00-0000-4000-8000-000000000100/raw'); print(json.loads(next(p.glob('*/metadata.json')).read_text())['row_count'])"
```
