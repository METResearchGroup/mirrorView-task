#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Verify a single uploaded S3 object against a local file.

Usage:
  verify_s3_object.sh --bucket BUCKET --key KEY --local PATH [--region REGION] [--profile PROFILE]

Checks:
  1. S3 head-object ContentLength matches local size.
  2. Downloaded object sha256 matches local sha256.
EOF
}

BUCKET=""
KEY=""
LOCAL_PATH=""
CLI_REGION=""
PROFILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket)
      [[ $# -ge 2 ]] || { echo "Missing value for --bucket" >&2; exit 2; }
      BUCKET="$2"
      shift 2
      ;;
    --key)
      [[ $# -ge 2 ]] || { echo "Missing value for --key" >&2; exit 2; }
      KEY="$2"
      shift 2
      ;;
    --local)
      [[ $# -ge 2 ]] || { echo "Missing value for --local" >&2; exit 2; }
      LOCAL_PATH="$2"
      shift 2
      ;;
    --region)
      [[ $# -ge 2 ]] || { echo "Missing value for --region" >&2; exit 2; }
      CLI_REGION="$2"
      shift 2
      ;;
    --profile)
      [[ $# -ge 2 ]] || { echo "Missing value for --profile" >&2; exit 2; }
      PROFILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$BUCKET" || -z "$KEY" || -z "$LOCAL_PATH" ]]; then
  echo "Missing required arguments. Need --bucket, --key, and --local." >&2
  usage >&2
  exit 2
fi

REGION="${CLI_REGION:-${AWS_DEFAULT_REGION:-${AWS_REGION:-us-east-2}}}"
if [[ ! -f "$LOCAL_PATH" ]]; then
  echo "Local file not found: $LOCAL_PATH" >&2
  exit 2
fi

S3_URI="s3://${BUCKET}/${KEY}"
AWS_HEAD_ARGS=(s3api head-object --bucket "$BUCKET" --key "$KEY" --query ContentLength --output text --region "$REGION")
AWS_CP_ARGS=(s3 cp "$S3_URI")
if [[ -n "$PROFILE" ]]; then
  AWS_HEAD_ARGS+=(--profile "$PROFILE")
fi

remote_size="$(aws "${AWS_HEAD_ARGS[@]}")"
local_size="$(wc -c < "$LOCAL_PATH" | tr -d '[:space:]')"
if [[ "$remote_size" != "$local_size" ]]; then
  echo "Size mismatch for $S3_URI: remote=$remote_size local=$local_size" >&2
  exit 1
fi

tmp_file="$(mktemp)"
cleanup() {
  rm -f "$tmp_file"
}
trap cleanup EXIT

AWS_CP_ARGS+=("$tmp_file" --region "$REGION" --only-show-errors)
if [[ -n "$PROFILE" ]]; then
  AWS_CP_ARGS+=(--profile "$PROFILE")
fi
aws "${AWS_CP_ARGS[@]}"

local_sha="$(shasum -a 256 "$LOCAL_PATH" | awk '{print $1}')"
remote_sha="$(shasum -a 256 "$tmp_file" | awk '{print $1}')"
if [[ "$local_sha" != "$remote_sha" ]]; then
  echo "SHA mismatch for $S3_URI: remote=$remote_sha local=$local_sha" >&2
  exit 1
fi

echo "Verified $S3_URI"
