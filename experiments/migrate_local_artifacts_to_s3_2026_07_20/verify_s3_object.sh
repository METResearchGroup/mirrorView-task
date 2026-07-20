#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
verify_s3_object.sh --bucket NAME --key S3_KEY --local LOCAL_PATH [--region R] [--profile P]

Verify an S3 object matches a local file (ContentLength + sha256 download).

Exit 0 on match; exit 1 on mismatch / missing remote; exit 2 on usage errors.
EOF
}

bucket=""
key=""
local_path=""
region="us-east-2"
profile=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket) bucket="${2:-}"; shift 2 ;;
    --key) key="${2:-}"; shift 2 ;;
    --local) local_path="${2:-}"; shift 2 ;;
    --region) region="${2:-}"; shift 2 ;;
    --profile) profile="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$bucket" || -z "$key" || -z "$local_path" ]]; then
  echo "Missing required args." >&2
  usage
  exit 2
fi

if [[ ! -f "$local_path" ]]; then
  echo "Local file not found: $local_path" >&2
  exit 2
fi

sha256() {
  shasum -a 256 "$1" | cut -d' ' -f1
}

file_size() {
  if stat -f%z "$1" >/dev/null 2>&1; then
    stat -f%z "$1"
  else
    stat -c%s "$1"
  fi
}

profile_args=()
if [[ -n "$profile" ]]; then
  profile_args=(--profile "$profile")
fi

content_length="$(
  aws s3api head-object \
    --bucket "$bucket" \
    --key "$key" \
    --region "$region" \
    "${profile_args[@]}" \
    --query ContentLength \
    --output text
)"

local_size="$(file_size "$local_path")"
local_sha256="$(sha256 "$local_path")"

if [[ "$local_size" != "$content_length" ]]; then
  echo "FAIL: local size != S3 ContentLength ($local_size != $content_length)" >&2
  exit 1
fi

tmp="$(mktemp)"
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT

aws s3 cp "s3://$bucket/$key" "$tmp" \
  --region "$region" \
  "${profile_args[@]}" \
  >/dev/null

dl_sha256="$(sha256 "$tmp")"
if [[ "$local_sha256" != "$dl_sha256" ]]; then
  echo "FAIL: sha256 mismatch (local != downloaded)" >&2
  exit 1
fi

echo "PASS: S3 object matches local file."
