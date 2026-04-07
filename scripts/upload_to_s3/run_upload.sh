#!/usr/bin/env bash
# Orchestrate staging, S3 upload, and post-upload verification.
# Run from repository root: bash scripts/upload_to_s3/run_upload.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

uv python install 3.12 >/dev/null
uv sync --quiet

PYTHONPATH=. uv run python scripts/upload_to_s3/stage_public_for_s3.py
PYTHONPATH=. uv run python scripts/upload_to_s3/upload_public_to_s3.py
PYTHONPATH=. uv run python scripts/upload_to_s3/verify_s3_upload.py

echo "Upload and verification finished."
