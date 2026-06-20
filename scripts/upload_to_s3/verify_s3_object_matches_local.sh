#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Verify an S3 object matches a local file (metadata + hash).

Example (run from repo root):
  bash scripts/upload_to_s3/verify_s3_object_matches_local.sh \
    --bucket jspsych-mirror-view-4 \
    --key img/flips_scaled_2026_06_18.csv \
    --local public/img/flips_scaled_2026_06_18.csv \
    --region us-east-2

Notes:
  - Always compares SHA-256 by downloading the S3 object.
  - If the S3 ETag looks like a single-part upload (no dash), it also compares local MD5 to the ETag.
EOF
}

bucket=""
key=""
local_path=""
region="us-east-2"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket) bucket="${2:-}"; shift 2 ;;
    --key) key="${2:-}"; shift 2 ;;
    --local) local_path="${2:-}"; shift 2 ;;
    --region) region="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
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

md5_hash() {
  if command -v md5 >/dev/null 2>&1; then
    md5 -q "$1"
  elif command -v md5sum >/dev/null 2>&1; then
    md5sum "$1" | cut -d' ' -f1
  else
    echo "missing-md5-tool"
  fi
}

file_size() {
  if stat -f%z "$1" >/dev/null 2>&1; then
    stat -f%z "$1"
  else
    stat -c%s "$1"
  fi
}

echo "## S3 metadata"
last_modified="$(
  aws s3api head-object \
    --bucket "$bucket" \
    --key "$key" \
    --region "$region" \
    --query LastModified \
    --output text
)"
content_length="$(
  aws s3api head-object \
    --bucket "$bucket" \
    --key "$key" \
    --region "$region" \
    --query ContentLength \
    --output text
)"
etag_raw="$(
  aws s3api head-object \
    --bucket "$bucket" \
    --key "$key" \
    --region "$region" \
    --query ETag \
    --output text
)"
etag="${etag_raw%\"}"
etag="${etag#\"}"

echo "bucket:         $bucket"
echo "key:            $key"
echo "region:         $region"
echo "LastModified:   $last_modified"
echo "ContentLength:  $content_length"
echo "ETag:           $etag"
echo

echo "## Local file"
local_sha256="$(sha256 "$local_path")"
local_md5="$(md5_hash "$local_path")"
local_size="$(file_size "$local_path")"
echo "path:   $local_path"
echo "size:   $local_size"
echo "sha256: $local_sha256"
echo "md5:    $local_md5"
echo

tmp="$(mktemp)"
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT

echo "## Download S3 object"
aws s3 cp "s3://$bucket/$key" "$tmp" --region "$region" >/dev/null
dl_sha256="$(sha256 "$tmp")"
dl_md5="$(md5_hash "$tmp")"
dl_size="$(file_size "$tmp")"
echo "download_path: $tmp"
echo "size:          $dl_size"
echo "sha256:        $dl_sha256"
echo "md5:           $dl_md5"
echo

echo "## Comparisons"
if [[ "$local_size" != "$content_length" ]]; then
  echo "FAIL: local size != S3 ContentLength ($local_size != $content_length)" >&2
  exit 1
fi
if [[ "$local_sha256" != "$dl_sha256" ]]; then
  echo "FAIL: sha256 mismatch (local != downloaded)" >&2
  exit 1
fi
echo "OK: sha256(local) == sha256(downloaded)"

if [[ "$etag" == *-* ]]; then
  echo "NOTE: ETag looks like multipart; skipping MD5==ETag check."
elif [[ "$local_md5" == "missing-md5-tool" ]]; then
  echo "NOTE: no MD5 tool available; skipping MD5==ETag check."
else
  if [[ "$local_md5" != "$etag" ]]; then
    echo "WARN: local MD5 != ETag (ETag may not be MD5 depending on upload mode)." >&2
  else
    echo "OK: md5(local) == ETag"
  fi
fi

echo
echo "PASS: S3 object matches local file."

