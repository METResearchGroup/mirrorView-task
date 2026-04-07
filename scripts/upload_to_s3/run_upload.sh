#!/usr/bin/env bash
# Orchestrate config validation, S3 upload, and post-upload verification.
# Run from repository root: bash scripts/upload_to_s3/run_upload.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is required (https://docs.astral.sh/uv/)" >&2
  exit 1
fi

uv python install 3.12 >/dev/null
uv sync --quiet

if ! PYTHONPATH=. uv run python scripts/upload_to_s3/upload_public_to_s3.py --validate-config-only; then
  echo "" >&2
  echo "public/config.js does not match the live API Gateway URLs." >&2
  echo "Update POST_ASSIGNMENTS_URL and SAVE_DATA_URL, then re-run." >&2
  read -r -p "Continue with upload anyway? [y/N] " _ans || true
  case "${_ans:-}" in
    [yY]|[yY][eE][sS]) ;;
    *) exit 1 ;;
  esac
fi

PYTHONPATH=. uv run python scripts/upload_to_s3/upload_public_to_s3.py
PYTHONPATH=. uv run python scripts/upload_to_s3/verify_s3_upload.py

echo "Upload and verification finished."
