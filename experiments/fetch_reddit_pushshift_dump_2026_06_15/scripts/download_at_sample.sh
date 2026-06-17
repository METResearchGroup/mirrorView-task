#!/usr/bin/env bash
set -euo pipefail

# Selectively download Pushshift comment month files from Academic Torrents.
#
# Usage:
#   bash experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/download_at_sample.sh
#   bash experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/download_at_sample.sh RC_2024-06.zst
#
# Requires: aria2 (brew install aria2)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${EXPERIMENT_ROOT}/data/raw"
TORRENT_URL="https://academictorrents.com/download/3d426c47c767d40f82c7ef0f47c3acacedd2bf44.torrent"
TORRENT_FILE="${OUT_DIR}/.pushshift.torrent"
TARGET_FILE="${1:-RC_2024-06.zst}"

mkdir -p "${OUT_DIR}"

if [[ ! -f "${TORRENT_FILE}" ]]; then
  echo "Fetching torrent metadata..."
  curl -sL -o "${TORRENT_FILE}" "${TORRENT_URL}"
fi

echo "Listing torrent files matching ${TARGET_FILE}..."
MATCH_LINE="$(aria2c --show-files "${TORRENT_FILE}" | grep "${TARGET_FILE}" | head -n 1 || true)"
if [[ -z "${MATCH_LINE}" ]]; then
  echo "Could not find ${TARGET_FILE} in torrent index." >&2
  echo "Try: aria2c --show-files ${TORRENT_FILE} | grep 'RC_'" >&2
  exit 1
fi

FILE_IDX="$(echo "${MATCH_LINE}" | awk -F'|' '{print $1}' | tr -d '[:space:]')"
echo "Selected file index ${FILE_IDX} for ${TARGET_FILE}"

aria2c \
  --select-file="${FILE_IDX}" \
  --seed-time=0 \
  --file-allocation=none \
  --dir="${OUT_DIR}" \
  "${TORRENT_FILE}"

EXPECTED_PATH="${OUT_DIR}/${TARGET_FILE}"
if [[ ! -f "${EXPECTED_PATH}" ]]; then
  FOUND="$(find "${OUT_DIR}" -name "${TARGET_FILE}" -print -quit || true)"
  if [[ -n "${FOUND}" ]]; then
    FLAT_PATH="${OUT_DIR}/${TARGET_FILE}"
    if [[ "${FOUND}" != "${FLAT_PATH}" ]]; then
      cp "${FOUND}" "${FLAT_PATH}"
      echo "Copied ${FOUND} -> ${FLAT_PATH}"
    fi
    echo "Downloaded ${FLAT_PATH}"
    exit 0
  fi
  echo "Expected ${EXPECTED_PATH} after download, but file not found." >&2
  exit 1
fi

echo "Downloaded ${EXPECTED_PATH}"
