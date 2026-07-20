"""Discover allowlisted experiment csv/json artifacts and register into SQLite."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class DiscoveredFile:
    local_path: str
    s3_key: str
    file_size_bytes: int
    sha256: str | None
    mtime_ns: int
    experiment_prefix: str
    status: str  # 'pending' | 'skipped'


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_excluded(local_path: str, exclude_substrings: tuple[str, ...] | list[str]) -> bool:
    return any(substr in local_path for substr in exclude_substrings)


def discover_files(
    *,
    repo_root: Path,
    allowlist: tuple[str, ...] | list[str],
    exclude_substrings: tuple[str, ...] | list[str] = (),
    compute_sha256: bool = True,
) -> list[DiscoveredFile]:
    """Pure discovery; no DB writes."""
    repo_root = Path(repo_root).resolve()
    discovered: list[DiscoveredFile] = []
    batch_keys: dict[str, str] = {}

    for prefix in allowlist:
        prefix_dir = repo_root / prefix
        if not prefix_dir.is_dir():
            print(f"WARNING: allowlist prefix missing, skipping: {prefix}", file=sys.stderr)
            continue

        for path in sorted(prefix_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in INCLUDE_SUFFIXES:
                continue

            local_path = path.relative_to(repo_root).as_posix()
            if _is_excluded(local_path, exclude_substrings):
                continue

            s3_key = local_path
            if s3_key in batch_keys and batch_keys[s3_key] != local_path:
                raise ValueError(
                    f"s3_key collision in discovery batch: {s3_key!r} "
                    f"from {batch_keys[s3_key]!r} and {local_path!r}"
                )
            batch_keys[s3_key] = local_path

            st = path.stat()
            size = int(st.st_size)
            sha: str | None = None
            if compute_sha256 and size > 0:
                sha = _sha256_file(path)
            elif compute_sha256 and size == 0:
                sha = hashlib.sha256(b"").hexdigest()

            status = (
                MigrationStatus.SKIPPED
                if SKIP_EMPTY_FILES and size == 0
                else MigrationStatus.PENDING
            )
            discovered.append(
                DiscoveredFile(
                    local_path=local_path,
                    s3_key=s3_key,
                    file_size_bytes=size,
                    sha256=sha,
                    mtime_ns=int(st.st_mtime_ns),
                    experiment_prefix=prefix,
                    status=str(status),
                )
            )

    return discovered


def register_discovered(
    tracker: MigrationTracker,
    files: list[DiscoveredFile],
    *,
    refresh_metadata: bool = False,
) -> dict[str, int]:
    """Convert dataclasses → register_files()."""
    rows = [asdict(f) for f in files]
    return tracker.register_files(rows, refresh_metadata=refresh_metadata)


def write_inventory_json(files: list[DiscoveredFile], out_path: Path) -> None:
    """Write list of dicts (same fields) for human review."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(f) for f in files]
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _print_summary(
    files: list[DiscoveredFile],
    register_counts: dict[str, int] | None = None,
) -> None:
    by_prefix: dict[str, Counter[str]] = defaultdict(Counter)
    for f in files:
        by_prefix[f.experiment_prefix][f.status] += 1

    for prefix in sorted(by_prefix):
        counts = by_prefix[prefix]
        pending = counts.get(MigrationStatus.PENDING, 0)
        skipped = counts.get(MigrationStatus.SKIPPED, 0)
        print(f"prefix={prefix}  pending={pending} skipped={skipped}")

    total_pending = sum(1 for f in files if f.status == MigrationStatus.PENDING)
    total_skipped = sum(1 for f in files if f.status == MigrationStatus.SKIPPED)
    if register_counts is None:
        print(f"TOTAL pending={total_pending} skipped={total_skipped}")
    else:
        print(
            f"TOTAL pending={total_pending} skipped={total_skipped} "
            f"already_present={register_counts.get('already_present', 0)} "
            f"inserted={register_counts.get('inserted', 0)}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover experiment csv/json for S3 migration")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument(
        "--prefix",
        action="append",
        dest="prefixes",
        default=None,
        help="Repeatable; default = full allowlist",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-db", action="store_true")
    parser.add_argument("--refresh-metadata", action="store_true")
    parser.add_argument("--export-inventory", type=Path, default=None)
    parser.add_argument("--no-sha256", action="store_true")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.write_db:
        print("error: require --dry-run or --write-db", file=sys.stderr)
        return 2

    allowlist: tuple[str, ...]
    if args.prefixes:
        unknown = [p for p in args.prefixes if p not in EXPERIMENT_ALLOWLIST]
        if unknown:
            print(f"error: unknown prefix(es) not in allowlist: {unknown}", file=sys.stderr)
            return 2
        allowlist = tuple(args.prefixes)
    else:
        allowlist = EXPERIMENT_ALLOWLIST

    try:
        files = discover_files(
            repo_root=args.repo_root,
            allowlist=allowlist,
            exclude_substrings=EXCLUDE_PATH_SUBSTRINGS,
            compute_sha256=not args.no_sha256,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    register_counts: dict[str, int] | None = None
    if args.write_db and not args.dry_run:
        tracker = MigrationTracker(args.db)
        try:
            tracker.init_schema()
            register_counts = register_discovered(
                tracker,
                files,
                refresh_metadata=args.refresh_metadata,
            )
        finally:
            tracker.close()

    export_path = args.export_inventory
    if export_path is None and args.write_db and not args.dry_run:
        export_path = INVENTORY_DIR / "artifacts_inventory.json"
    if export_path is not None:
        write_inventory_json(files, export_path)
        print(f"Wrote inventory: {export_path}")

    _print_summary(files, register_counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
