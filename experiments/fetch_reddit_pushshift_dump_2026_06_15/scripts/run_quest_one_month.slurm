#!/bin/bash
#SBATCH --account=p32375
#SBATCH --partition=normal
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --job-name=reddit-toxic-1mo
#SBATCH --output=logs/reddit-toxic-1mo-%j.out
#
# Single-month calibration job (2025 data). Requires $REPO/.env with GOOGLE_API_KEY.
#
# Submit from repo root:
#   mkdir -p logs
#   sbatch experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/run_quest_one_month.slurm
#
# Override month (default RC_2025-06):
#   sbatch --export=ALL,INPUT_STEM=RC_2025-03 \
#     experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/run_quest_one_month.slurm
#
# See HOW_TO_RUN_ACTUAL_DATA.md for full Quest instructions.

set -euo pipefail

REPO_ROOT="${SLURM_SUBMIT_DIR:-/projects/p32375/mirrorView-task}"
cd "${REPO_ROOT}"

INPUT_STEM="${INPUT_STEM:-RC_2025-06}"
INPUT_FILE="${REPO_ROOT}/experiments/fetch_reddit_pushshift_dump_2026_06_15/data/raw/bolun/comments/${INPUT_STEM}.zst"

module load python/3.12.3 2>/dev/null || true

# Use project uv (>=0.11) so dependency-groups and uv.lock are honored.
export PATH="${HOME}/.local/bin:${PATH}"
export UV_LINK_MODE=copy
uv sync --frozen --no-dev

mkdir -p logs experiments/fetch_reddit_pushshift_dump_2026_06_15/outputs

if [[ ! -f "${INPUT_FILE}" ]]; then
  echo "Input file not found: ${INPUT_FILE}"
  echo "Run prepare_bolun_package.py --extract --stage first, or set INPUT_STEM to an available RC_2025-*.zst stem."
  exit 1
fi

echo "Processing single month: ${INPUT_STEM}"
echo "Input: ${INPUT_FILE}"

PYTHONPATH=. uv run python \
  experiments/fetch_reddit_pushshift_dump_2026_06_15/runner.py \
  --input-file "${INPUT_FILE}"
