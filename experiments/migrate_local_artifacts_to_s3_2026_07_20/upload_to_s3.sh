#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Upload a single local file to S3.

Usage:
  upload_to_s3.sh --bucket BUCKET --key KEY --local PATH [--region REGION] [--profile PROFILE] [--dry-run]

Flags:
  --bucket    Destination bucket name.
  --key       Destination object key.
  --local     Local file path.
  --region    AWS region. Precedence: CLI > AWS_DEFAULT_REGION > AWS_REGION > us-east-2.
  --profile   Optional AWS profile.
  --dry-run   Print the aws s3 cp command without executing it.
  -h, --help  Show this help text.
EOF
}

BUCKET=""
KEY=""
LOCAL_PATH=""
CLI_REGION=""
PROFILE=""
DRY_RUN=0

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
    --dry-run)
      DRY_RUN=1
      shift
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
PROFILE_FRAGMENT=""
if [[ -n "$PROFILE" ]]; then
  PROFILE_FRAGMENT=" --profile '$PROFILE'"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf "DRY-RUN: aws s3 cp '%s' '%s' --region '%s'%s
" "$LOCAL_PATH" "$S3_URI" "$REGION" "$PROFILE_FRAGMENT"
  exit 0
fi

AWS_ARGS=(s3 cp "$LOCAL_PATH" "$S3_URI" --region "$REGION" --only-show-errors)
if [[ -n "$PROFILE" ]]; then
  AWS_ARGS+=(--profile "$PROFILE")
fi

aws "${AWS_ARGS[@]}"
