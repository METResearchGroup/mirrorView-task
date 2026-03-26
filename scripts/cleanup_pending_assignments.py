#!/usr/bin/env python3
"""
Clean up locally-synced `pending_assignments.json`.

Deletes pending entries that are no longer needed, so pending-aware condition/post
balancing doesn't drift due to abandoned sessions.

This script is intentionally LOCAL-ONLY (no S3 upload). It assumes you have a
separate sync process that pulls/pushes JSON files to S3.

Safety model:
- We never delete a pending ID if it already appears as completed in
  `post_assignments.json` (participants history).
- We only delete IDs you explicitly provide (e.g. from Prolific “returned/abandoned” list).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def read_ids(ids_path: Path) -> list[str]:
    text = ids_path.read_text(encoding="utf-8")
    text_stripped = text.strip()
    # Accept newline-separated IDs or a JSON array.
    if text_stripped.startswith("["):
        arr = json.loads(text_stripped)
        return [str(x).strip() for x in arr if str(x).strip()]
    ids: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s:
            ids.append(s)
    return ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dir",
        required=True,
        help='Directory containing both "pending_assignments.json" and "post_assignments.json" (e.g., ".../test" or ".../prolific").',
    )
    parser.add_argument("--ids", required=True, help="Path to a newline-separated list (or JSON array) of Prolific IDs to delete from pending.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be removed; do not write changes.")
    args = parser.parse_args()

    target_dir = Path(args.dir).expanduser().resolve()
    pending_path = target_dir / "pending_assignments.json"
    post_path = target_dir / "post_assignments.json"

    if not pending_path.exists():
        print(f"Missing file: {pending_path}", file=sys.stderr)
        return 2
    if not post_path.exists():
        print(f"Missing file: {post_path}", file=sys.stderr)
        return 2

    ids_path = Path(args.ids).expanduser().resolve()
    if not ids_path.exists():
        print(f"Missing IDs file: {ids_path}", file=sys.stderr)
        return 2
    ids_to_delete = set(read_ids(ids_path))
    if not ids_to_delete:
        print("No IDs provided; nothing to do.")
        return 0

    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    post = json.loads(post_path.read_text(encoding="utf-8"))

    if not isinstance(pending, dict):
        print("Unexpected pending JSON shape (expected object at root).", file=sys.stderr)
        return 1
    if not isinstance(post, dict) or not isinstance(post.get("participants", {}), dict):
        print('Unexpected post JSON shape (expected {"participants": {...}}).', file=sys.stderr)
        return 1

    completed_ids = set(post.get("participants", {}).keys())

    to_delete: list[str] = []
    skipped_completed: list[str] = []
    missing_from_pending: list[str] = []

    for pid in ids_to_delete:
        if pid in completed_ids:
            skipped_completed.append(pid)
            continue
        if pid not in pending:
            missing_from_pending.append(pid)
            continue
        to_delete.append(pid)

    print(f"Target dir: {target_dir}")
    print(f"Pending entries before: {len(pending)}")
    print(f"Completed participants: {len(completed_ids)}")
    print(f"Requested IDs: {len(ids_to_delete)}")
    print(f"Will delete (present in pending, not completed): {len(to_delete)}")
    if skipped_completed:
        print(f"Skipped (already completed): {len(skipped_completed)}")
    if missing_from_pending:
        print(f"Not found in pending (already removed or never pending): {len(missing_from_pending)}")

    if args.dry_run:
        if to_delete:
            print("IDs to delete:", to_delete)
        print("Dry run: not writing changes.")
        return 0

    for pid in to_delete:
        pending.pop(pid, None)

    pending_path.write_text(json.dumps(pending, indent=2), encoding="utf-8")
    print(f"Pending entries after: {len(pending)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

