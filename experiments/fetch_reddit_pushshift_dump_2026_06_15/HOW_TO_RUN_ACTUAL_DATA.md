# How to Run on Quest HPC (Production Data)

Use this guide when running the Reddit toxicity pipeline on **Northwestern Quest** with Bolun's pre-filtered package or large Academic Torrents month files. For local smoke tests, see [README.md](README.md).

## Overview

| Phase | What | Where |
|-------|------|--------|
| 1. Ingest | Download/extract Bolun tar.zst, stage `RC_*.zst` | `data/bolun/`, `data/raw/bolun/comments/` |
| 2. Score | Perspective API on filtered comments | `outputs/{stem}/` |
| 3. Stop | 50k high-toxic comments **or** 1M API calls per session | `outputs/total_metadata.json` |

Production data path: **Bolun's Google Drive package** (~16GB tar.zst, ~109M pre-filtered comments). Raw Academic Torrents files work too but are not pre-filtered to the six subreddits.

## Prerequisites on Quest

```bash
# Login
ssh <netid>@quest.northwestern.edu

# Project storage (adjust if your allocation differs)
export QUEST_PROJECT=/projects/p32375
export REPO=$QUEST_PROJECT/mirrorView-task
cd $REPO

# Load Python (module name may vary by Quest policy)
module load python/3.12.3   # or: module avail python

# Install deps once per clone
uv sync --group dev

# Perspective API key — stored in repo-root .env (gitignored), loaded at runtime
# by lib/load_env_vars.py when perspective.py calls EnvVarsContainer.get_env_var(...)
cat > "$REPO/.env" <<'EOF'
GOOGLE_API_KEY=your-key-here
EOF

# Verify the key loads (do not commit .env)
PYTHONPATH=. uv run python -c \
  "from lib.load_env_vars import EnvVarsContainer; EnvVarsContainer.get_env_var('GOOGLE_API_KEY', required=True); print('GOOGLE_API_KEY ok')"
```

**Disk:** reserve at least **~80GB** on project storage:

- ~16GB tarball
- ~30–50GB extracted tree (verify after first extract)
- ~5GB+ pipeline outputs (depends on how many months you score)

## Step 1 — Download Bolun's package from Google Drive

Bolun's Drive link: `https://drive.google.com/file/d/17412qQBz9UTkDGCO0F-vHjWMkJNOdTgh/view`

```bash
cd $REPO
PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/prepare_bolun_package.py \
  --download --extract --stage --inventory
```

This will:

1. Download `data/bolun/bolun_package.tar.zst` from Google Drive
2. Extract to `data/bolun/extracted/`
3. Symlink comment files → `data/raw/bolun/comments/RC_*.zst`
4. Print an inventory table (file sizes + row counts) and cache `data/bolun/inventory.json`

Row counting on the full package can take **hours**. For a first pass, use:

```bash
PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/prepare_bolun_package.py \
  --download --extract --stage --inventory --skip-row-counts
```

Then run row counts overnight or on a subset.

## Step 2 — Verify staged inputs

```bash
ls experiments/fetch_reddit_pushshift_dump_2026_06_15/data/raw/bolun/comments/ | head
```

`main.py` discovers all `data/raw/**/RC_*.zst`. To run **Bolun only** (exclude Academic Torrents samples):

```bash
# Process only Bolun-staged months (filenames under bolun/comments/)
# Easiest: move AT samples out of data/raw temporarily, or use stem prefixes for AT files only.
PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/main.py \
  --max-files 0
```

Inspect inventory:

```bash
cat experiments/fetch_reddit_pushshift_dump_2026_06_15/data/bolun/inventory.json | head
```

## Step 3 — Run the toxicity pipeline (interactive test)

Test one month before submitting a long job:

```bash
PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/runner.py \
  --input-file experiments/fetch_reddit_pushshift_dump_2026_06_15/data/raw/bolun/comments/RC_2024-06.zst
```

Check outputs:

```bash
cat experiments/fetch_reddit_pushshift_dump_2026_06_15/outputs/RC_2024-06/metadata.json
```

Re-running the same file skips scoring if `metadata.json` exists (resumable).

## Step 4 — Submit a Slurm job (full orchestration)

Use `experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/run_quest.slurm`. Ensure `$REPO/.env` contains `GOOGLE_API_KEY` before submitting — the job does **not** export the key in the shell; `perspective.py` reads it via `lib/load_env_vars.py` at runtime.

```bash
#!/bin/bash
#SBATCH --account=p32375
#SBATCH --partition=normal
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --job-name=reddit-toxic
#SBATCH --output=logs/reddit-toxic-%j.out

set -euo pipefail
cd /projects/p32375/mirrorView-task

module load python/3.12.3

mkdir -p logs experiments/fetch_reddit_pushshift_dump_2026_06_15/outputs

PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/main.py \
  --max-files 0
```

Submit:

```bash
mkdir -p logs
sbatch experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/run_quest.slurm
```

### Stop conditions (built into pipeline)

- **`GLOBAL_STOP_COUNT = 50_000`** — stop after 50k high-toxic comments (`prob_toxic >= 0.7`) across all files
- **`MAX_SESSION_API_CALLS = 1_000_000`** — stop after 1M Perspective API calls in one `main.py` session (includes retries)
- **Per-file skip** — if `outputs/{stem}/metadata.json` exists, that month is skipped

To process more after a partial run: delete specific `outputs/{stem}/` dirs to re-score those months, or increase limits in `config.py`.

## Step 5 — Monitor progress

```bash
# Slurm
squeue -u $USER
tail -f logs/reddit-toxic-*.out

# Aggregate progress
cat experiments/fetch_reddit_pushshift_dump_2026_06_15/outputs/total_metadata.json
```

`tqdm` batch progress appears in Slurm stdout when scoring runs.

## Bolun package contents (reference)

| Format | Role in pipeline |
|--------|------------------|
| `RC_*.zst` (JSONL) | **Input** — staged to `data/raw/bolun/comments/` |
| `RS_*.zst` (JSONL) | Submissions only; not scored by this pipeline |
| Comment Parquet | Analysis-ready; optional future adapter |
| Submission Parquet | Not used by toxicity pipeline |

Bolun's data is **already filtered** to six subreddits (`Conservative`, `Republican`, `AskConservatives`, `politics`, `liberal`, `democrats`). The pipeline still applies body length (20–300 chars) and deleted-author/body filters before calling Perspective.

## Alternative — Academic Torrents on Quest

For single-month AT files instead of Bolun:

```bash
module load aria2   # if available, or install in user space
bash experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/download_at_sample.sh RC_2024-06.zst
```

Note: `RC_2024-06.zst` is **~29 GiB** per file. Prefer Bolun's pre-filtered package for production volume.

## Troubleshooting

| Issue | Action |
|-------|--------|
| `GOOGLE_API_KEY` missing | Add `GOOGLE_API_KEY=...` to `$REPO/.env`; verify with `EnvVarsContainer.get_env_var('GOOGLE_API_KEY', required=True)` |
| Job killed (OOM) | Increase `#SBATCH --mem`; pipeline streams JSONL and should not load full months into RAM |
| Duplicate scoring | Remove `outputs/{stem}/metadata.json` to force re-run |
| Slow inventory | Use `--skip-row-counts`; count rows per file later |
| API quota / rate limit | Pipeline retries individually; reduce batch load via `PERSPECTIVE_DELAY_SECONDS` in `config.py` |

## After scoring

High-toxic deliverables:

```text
outputs/{stem}/high_toxic_comments.parquet   # mirrorview 13 cols + prob_toxic
outputs/{stem}/metadata.json
outputs/total_metadata.json
```

Downstream mirrorview curation can consume these parquet files the same way as other Reddit curated exports.
