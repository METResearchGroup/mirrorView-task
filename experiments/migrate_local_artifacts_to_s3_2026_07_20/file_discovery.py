"""Discover experiment artifacts eligible for S3 migration."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from experiments.migrate_local_artifacts_to_s3_2026_07_20.constants import (
    DB_PATH,
    EXCLUDE_PATH_SUBSTRINGS,
    EXPERIMENT_ALLOWLIST,
    INCLUDE_SUFFIXES,
    INVENTORY_DIR,
    REPO_ROOT,
    SKIP_EMPTY_FILES,
)
from experiments.migrate_local_artifacts_to_s3_2026_07_20.migration_tracker import (
    MigrationStatus,
    MigrationTracker,
)


@dataclass(frozen=True, slots=True)
class DiscoveredFile:
    local_path: str
    s3_key: str
    file_size_bytes: int
    sha256: str | None
    mtime_ns: int
    experiment_prefix: str
    status: MigrationStatus


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_files(
    *,
    repo_root: Path,
    allowlist: Sequence[str] = EXPERIMENT_ALLOWLIST,
    exclude_substrings: Sequence[str] = EXCLUDE_PATH_SUBSTRINGS,
    include_suffixes: Sequence[str] = INCLUDE_SUFFIXES,
    skip_empty_files: bool = SKIP_EMPTY_FILES,
    compute_sha256: bool = True,
) -> list[DiscoveredFile]:
    repo_root = Path(repo_root).resolve()
    discovered: list[DiscoveredFile] = []

    for prefix in allowlist:
        prefix_path = repo_root / prefix
        if not prefix_path.exists():
            continue
        for path in sorted(prefix_path.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in include_suffixes:
                continue
            rel = path.relative_to(repo_root).as_posix()
            if any(fragment in rel for fragment in exclude_substrings):
                continue

            stat = path.stat()
            is_empty = stat.st_size == 0
            status = (
                MigrationStatus.SKIPPED
                if skip_empty_files and is_empty
                else MigrationStatus.PENDING
            )
            sha256 = None
            if compute_sha256 and status != MigrationStatus.SKIPPED:
                sha256 = _sha256_file(path)

            discovered.append(
                DiscoveredFile(
                    local_path=rel,
                    s3_key=rel,
                    file_size_bytes=int(stat.st_size),
                    sha256=sha256,
                    mtime_ns=int(stat.st_mtime_ns),
                    experiment_prefix=prefix,
                    status=status,
                )
            )

    discovered.sort(key=lambda item: item.local_path)
    return discovered


def register_discovered(
    tracker: MigrationTracker,
    discovered_files: Iterable[DiscoveredFile],
    *,
    refresh_metadata: bool = False,
) -> dict[str, int]:
    rows = []
    for item in discovered_files:
        row = asdict(item)
        row["status"] = str(item.status)
        rows.append(row)
    return tracker.register_files(rows, refresh_metadata=refresh_metadata)


def write_inventory_json(discovered_files: Iterable[DiscoveredFile], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for item in discovered_files:
        row = asdict(item)
        row["status"] = str(item.status)
        payload.append(row)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover experiment csv/json artifacts.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument(
        "--inventory-json",
        type=Path,
        default=INVENTORY_DIR / "discovered_files.json",
    )
    parser.add_argument("--allowlist", nargs="*")
    parser.add_argument("--refresh-metadata", action="store_true")
    parser.add_argument("--no-sha256", action="store_true")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--write-db", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    allowlist = tuple(args.allowlist) if args.allowlist else EXPERIMENT_ALLOWLIST
    discovered = discover_files(
        repo_root=args.repo_root,
        allowlist=allowlist,
        compute_sha256=not args.no_sha256,
    )
    inventory_path = write_inventory_json(discovered, args.inventory_json)

    pending = sum(1 for item in discovered if item.status == MigrationStatus.PENDING)
    skipped = sum(1 for item in discovered if item.status == MigrationStatus.SKIPPED)
    print(
        json.dumps(
            {
                "inventory_json": str(inventory_path),
                "total": len(discovered),
                "pending": pending,
                "skipped": skipped,
            },
            indent=2,
            sort_keys=True,
        )
    )

    if args.dry_run:
        return 0

    tracker = MigrationTracker(args.db)
    try:
        tracker.init_schema()
        summary = register_discovered(
            tracker,
            discovered,
            refresh_metadata=args.refresh_metadata,
        )
    finally:
        tracker.close()

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
