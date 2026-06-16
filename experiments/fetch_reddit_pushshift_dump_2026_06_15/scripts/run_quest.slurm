#!/bin/bash
#SBATCH --account=p32375
#SBATCH --partition=normal
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --job-name=reddit-toxic
#SBATCH --output=logs/reddit-toxic-%j.out
#
# Submit from repo root:
#   mkdir -p logs
#   export GOOGLE_API_KEY=...
#   sbatch experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/run_quest.slurm
#
# See HOW_TO_RUN_ACTUAL_DATA.md for full Quest instructions.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${REPO_ROOT}"

module load python/3.12.3 2>/dev/null || true
export GOOGLE_API_KEY="${GOOGLE_API_KEY:?Set GOOGLE_API_KEY before sbatch}"

mkdir -p logs experiments/fetch_reddit_pushshift_dump_2026_06_15/outputs

PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/main.py \
  --max-files 0
