#!/usr/bin/env bash
# Periodically commit and push production-run artifacts to GitHub.
set -euo pipefail

REPO_ROOT="/workspace"
BRANCH="classify-with-llm-exp-2026-07-28"
EXP_DIR="experiments/llm_based_feature_generation_2026_07_31"
INTERVAL_SEC="${COMMIT_INTERVAL_SEC:-300}"
DONE_MARKER="${REPO_ROOT}/${EXP_DIR}/.production_complete"

cd "${REPO_ROOT}"

echo "commit watcher started $(date -u +%Y-%m-%dT%H:%M:%SZ)"

while true; do
  if [[ -f "${DONE_MARKER}" ]]; then
    echo "done marker found; final commit pass $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  fi

  if [[ -n "$(git status --porcelain "${EXP_DIR}" 2>/dev/null || true)" ]]; then
    git add \
      "${EXP_DIR}/data" \
      "${EXP_DIR}/outputs" \
      "${EXP_DIR}/RESULTS.md" \
      "${EXP_DIR}/production_run.log" \
      "${EXP_DIR}/.production_complete" \
      2>/dev/null || true

    if ! git diff --cached --quiet; then
      git commit -m "Checkpoint: 50% production run progress $(date -u +%Y-%m-%dT%H:%M:%SZ)" || true
      git push -u origin "${BRANCH}" || true
      echo "pushed checkpoint $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    fi
  fi

  if [[ -f "${DONE_MARKER}" ]]; then
    echo "commit watcher exiting $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    exit 0
  fi

  sleep "${INTERVAL_SEC}"
done
