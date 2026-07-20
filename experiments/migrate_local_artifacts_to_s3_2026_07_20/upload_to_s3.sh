#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
upload_to_s3.sh --bucket NAME --key S3_KEY --local LOCAL_PATH [--region R] [--profile P] [--dry-run]

Upload a single local file to s3://BUCKET/KEY via AWS CLI.

Required:
  --bucket   S3 bucket name
  --key      Object key (repo-relative path; may contain ':')
  --local    Path to local file (absolute or relative to CWD)

Optional:
  --region   AWS region (default: us-east-2, or AWS_DEFAULT_REGION / AWS_REGION if set)
  --profile  AWS shared-credentials profile (passed as --profile to aws)
  --dry-run  Print the aws s3 cp command that would run; exit 0; no network
  -h|--help  Print usage; exit 0
EOF
}

bucket=""
key=""
local_path=""
region=""
profile=""
dry_run=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket) bucket="${2:-}"; shift 2 ;;
    --key) key="${2:-}"; shift 2 ;;
    --local) local_path="${2:-}"; shift 2 ;;
    --region) region="${2:-}"; shift 2 ;;
    --profile) profile="${2:-}"; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$bucket" || -z "$key" || -z "$local_path" ]]; then
  echo "Missing required args (--bucket, --key, --local)." >&2
  usage
  exit 2
fi

if [[ ! -f "$local_path" ]]; then
  echo "Local file not found: $local_path" >&2
  exit 2
fi

if [[ -z "$region" ]]; then
  if [[ -n "${AWS_DEFAULT_REGION:-}" ]]; then
    region="$AWS_DEFAULT_REGION"
  elif [[ -n "${AWS_REGION:-}" ]]; then
    region="$AWS_REGION"
  else
    region="us-east-2"
  fi
fi

profile_args=()
profile_display=""
if [[ -n "$profile" ]]; then
  profile_args=(--profile "$profile")
  profile_display=" --profile '$profile'"
fi

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN: aws s3 cp '$local_path' 's3://$bucket/$key' --region '$region'$profile_display"
  exit 0
fi

aws s3 cp "$local_path" "s3://$bucket/$key" \
  --region "$region" \
  "${profile_args[@]}" \
  --only-show-errors
