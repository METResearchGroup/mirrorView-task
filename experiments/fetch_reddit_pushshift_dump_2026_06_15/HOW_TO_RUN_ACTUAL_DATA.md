# How to Run on Quest HPC (Production Data)

Use this guide when running the Reddit toxicity pipeline on **Northwestern Quest** with Bolun's pre-filtered package. **Production scoring targets 2025 comment months only** (`RC_2025-01` through `RC_2025-06`). For local smoke tests, see [README.md](README.md).

## Overview

| Phase | What | Where |
|-------|------|--------|
| 1. Ingest | Download/extract Bolun tar.zst, stage `RC_*.zst` | `data/bolun/`, `data/raw/bolun/comments/` |
| 2. Calibrate | Slurm single-month run on one `RC_2025-*.zst` | `outputs/{stem}/` |
| 3. Score | Slurm orchestration on all 2025 months | `outputs/{stem}/`, `outputs/total_metadata.json` |
| 4. Stop | 50k high-toxic comments **or** 1M API calls per session | `outputs/total_metadata.json` |

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

# Install deps once per clone (uses pyproject.toml + uv.lock)
curl -LsSf https://astral.sh/uv/install.sh | sh   # once, if uv < 0.11
export PATH="${HOME}/.local/bin:${PATH}"
export UV_LINK_MODE=copy
uv sync --frozen --no-dev   # pipeline runtime deps only (no torch/spacy)

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
  --download --extract --stage --inventory --skip-row-counts
```

This will:

1. Download `data/bolun/bolun_package.tar.zst` from Google Drive
2. Extract to `data/bolun/extracted/`
3. Symlink comment files → `data/raw/bolun/comments/RC_*.zst`
4. Print an inventory table (file sizes; row counts skipped) and cache `data/bolun/inventory.json`

Row counting on the full package can take **hours**. Run overnight if you need exact row counts:

```bash
PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/prepare_bolun_package.py \
  --inventory
```

## Step 2 — Verify staged 2025 inputs

Bolun's package includes comment months through **2025-06**. Confirm the six 2025 files are staged:

```bash
ls experiments/fetch_reddit_pushshift_dump_2026_06_15/data/raw/bolun/comments/RC_2025-*.zst
```

Expected stems (6 files):

```text
RC_2025-01.zst
RC_2025-02.zst
RC_2025-03.zst
RC_2025-04.zst
RC_2025-05.zst
RC_2025-06.zst
```

Inspect inventory (sizes for 2025 months):

```bash
cat experiments/fetch_reddit_pushshift_dump_2026_06_15/data/bolun/inventory.json | grep RC_2025
```

`main.py` discovers all `data/raw/**/RC_*.zst` but production Slurm passes **`--stem-prefix RC_2025`** so only 2025 months are scored. Ensure Academic Torrents smoke samples are not mixed into `data/raw/` (or move them aside) so they are not picked up accidentally without the prefix filter.

## Step 3 — Single-month calibration (Slurm)

Before the full 2025 orchestration, submit a one-month job to measure filter pass rate, high-toxic yield, and API time on Quest.

Default month: **`RC_2025-06`** (most recent in Bolun's package). Override with `INPUT_STEM`:

```bash
mkdir -p logs

# Default: RC_2025-06
sbatch experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/run_quest_one_month.slurm

# Alternate month, e.g. RC_2025-03
sbatch --export=ALL,INPUT_STEM=RC_2025-03 \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/run_quest_one_month.slurm
```

Slurm template: `scripts/run_quest_one_month.slurm` (8h wall time, 16G RAM). Requires `$REPO/.env` with `GOOGLE_API_KEY` — the job does **not** export the key; `perspective.py` loads it via `lib/load_env_vars.py`.

Monitor:

```bash
squeue -u $USER
tail -f logs/reddit-toxic-1mo-*.out
```

Check outputs when the job completes:

```bash
cat experiments/fetch_reddit_pushshift_dump_2026_06_15/outputs/RC_2025-06/metadata.json
```

Use `rows_read`, `rows_after_filter`, `rows_scored`, and `rows_high_toxic` to estimate how many 2025 months are needed to reach 50k high-toxic (see **Estimates** below).

Re-running the same month skips scoring if `metadata.json` exists. Delete `outputs/{stem}/` to force a re-run.

## Step 4 — Full 2025 orchestration (Slurm)

After calibration looks reasonable, submit the production job. It processes **`RC_2025-01` through `RC_2025-06` in sorted order**, stopping at 50k high-toxic or 1M API calls.

```bash
mkdir -p logs
sbatch experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/run_quest.slurm
```

Slurm template: `scripts/run_quest.slurm` (48h wall time). Runs:

```bash
PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/main.py \
  --max-files 0 \
  --stem-prefix RC_2025
```

### Stop conditions (built into pipeline)

- **`GLOBAL_STOP_COUNT = 50_000`** — stop after 50k high-toxic comments (`prob_toxic >= 0.7`) across all files
- **`MAX_SESSION_API_CALLS = 1_000_000`** — stop after 1M Perspective API calls in one `main.py` session (includes retries)
- **Per-file skip** — if `outputs/{stem}/metadata.json` exists, that month is skipped (including months finished in Step 3)

To process more after a partial run: delete specific `outputs/{stem}/` dirs to re-score those months, or increase limits in `config.py`.

## Step 5 — Monitor progress

```bash
squeue -u $USER
tail -f logs/reddit-toxic-*.out

cat experiments/fetch_reddit_pushshift_dump_2026_06_15/outputs/total_metadata.json
```

`tqdm` batch progress appears in Slurm stdout when scoring runs.

## Estimates (2025-only scope)

These are planning numbers until Step 3 calibration completes. Bolun's 2025 months are recent political subreddit activity and are typically **denser per month** than the long-run average across 2005–2025.

| Item | Estimate |
|------|----------|
| Input months | 6 (`RC_2025-01` … `RC_2025-06`) |
| Single-month API calls | ~150k–400k (depends on `rows_after_filter` in calibration metadata) |
| Single-month wall clock (Slurm) | ~2–6 h (Perspective batches dominate) |
| Full run API calls | Up to **1M** (session cap) or fewer if 50k high-toxic reached first |
| Full run wall clock | ~**6–24 h** depending on yield; 48h Slurm limit is generous |
| Output parquet (50k rows total) | ~**25–150 MB** across processed months |

**Yield math:** if calibration shows `rows_high_toxic / rows_scored ≈ R`, you need roughly `50_000 / R` scored comments. At `R = 5%`, ~1M API calls and 50k high-toxic align. At lower `R`, you may need a second Slurm session (completed months are skipped automatically).

## Bolun package contents (reference)

| Format | Role in pipeline |
|--------|------------------|
| `RC_*.zst` (JSONL) | **Input** — staged to `data/raw/bolun/comments/` |
| `RS_*.zst` (JSONL) | Submissions only; not scored by this pipeline |
| Comment Parquet | Analysis-ready; optional future adapter |
| Submission Parquet | Not used by toxicity pipeline |

Bolun's data is **already filtered** to six subreddits (`Conservative`, `Republican`, `AskConservatives`, `politics`, `liberal`, `democrats`). The pipeline still applies body length (20–300 chars) and deleted-author/body filters before calling Perspective.

## Alternative — Academic Torrents on Quest

Not recommended for this 2025 production path. Bolun's package is pre-filtered to the six subreddits. Raw AT month files (e.g. `RC_2024-06.zst`, ~29 GiB) are unfiltered and much larger.

## Troubleshooting

| Issue | Action |
|-------|--------|
| `GOOGLE_API_KEY` missing | Add `GOOGLE_API_KEY=...` to `$REPO/.env`; verify with `EnvVarsContainer.get_env_var('GOOGLE_API_KEY', required=True)` |
| `Input file not found` (one-month job) | Run Step 1 ingest; confirm `RC_2025-*.zst` under `data/raw/bolun/comments/` |
| Job killed (OOM) | Increase `#SBATCH --mem`; pipeline streams JSONL and should not load full months into RAM |
| Duplicate scoring | Remove `outputs/{stem}/metadata.json` (or whole `outputs/{stem}/`) to force re-run |
| Step 3 month skipped in Step 4 | Expected — `metadata.json` from calibration counts toward totals; orchestrator continues with remaining 2025 months |
| Slow inventory | Use `--skip-row-counts`; count rows per file later |
| API quota / rate limit | Pipeline retries individually; reduce batch load via `PERSPECTIVE_DELAY_SECONDS` in `config.py` |

## After scoring

High-toxic deliverables:

```text
outputs/RC_2025-01/
  high_toxic_comments.parquet   # mirrorview 13 cols + prob_toxic
  metadata.json
outputs/RC_2025-02/
  ...
outputs/total_metadata.json
```

Downstream mirrorview curation can consume these parquet files the same way as other Reddit curated exports.
