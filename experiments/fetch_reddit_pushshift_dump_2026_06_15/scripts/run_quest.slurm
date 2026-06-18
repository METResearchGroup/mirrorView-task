#!/bin/bash
#SBATCH --account=p32375
#SBATCH --partition=normal
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --job-name=reddit-toxic
#SBATCH --output=logs/reddit-toxic-%j.out
#
# Production orchestration: 2025 comment months only (RC_2025-01 .. RC_2025-06).
# Requires $REPO/.env with GOOGLE_API_KEY.
#
# Submit from repo root:
#   mkdir -p logs
#   sbatch experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/run_quest.slurm
#
# See HOW_TO_RUN_ACTUAL_DATA.md for full Quest instructions.

set -euo pipefail

REPO_ROOT="${SLURM_SUBMIT_DIR:-/projects/p32375/mirrorView-task}"
cd "${REPO_ROOT}"

module load python/3.12.3 2>/dev/null || true

# Use project uv (>=0.11) so dependency-groups and uv.lock are honored.
export PATH="${HOME}/.local/bin:${PATH}"
export UV_LINK_MODE=copy
uv sync --frozen --no-dev

mkdir -p logs experiments/fetch_reddit_pushshift_dump_2026_06_15/outputs

PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/main.py \
  --max-files 0 \
  --stem-prefix RC_2025
