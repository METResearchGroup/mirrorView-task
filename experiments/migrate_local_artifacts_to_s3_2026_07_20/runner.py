"""CLI orchestrator for experiment artifact S3 migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.migrate_local_artifacts_to_s3_2026_07_20.constants import (
    BUCKET,
    DB_PATH,
    DEFAULT_REGION,
    EXCLUDE_PATH_SUBSTRINGS,
    EXPERIMENT_ALLOWLIST,
    INVENTORY_DIR,
    REPO_ROOT,
    UPLOAD_SCRIPT,
    VERIFY_SCRIPT,
)
from experiments.migrate_local_artifacts_to_s3_2026_07_20.file_discovery import (
    discover_files,
    register_discovered,
    write_inventory_json,
)
from experiments.migrate_local_artifacts_to_s3_2026_07_20.migration_tracker import (
    MigrationStatus,
    MigrationTracker,
)

_ERROR_TRUNCATE = 2000


def _resolve_allowlist(prefixes: list[str] | None) -> tuple[str, ...] | int:
    if not prefixes:
        return EXPERIMENT_ALLOWLIST
    unknown = [p for p in prefixes if p not in EXPERIMENT_ALLOWLIST]
    if unknown:
        print(f"error: unknown prefix(es) not in allowlist: {unknown}", file=sys.stderr)
        return 2
    return tuple(prefixes)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_upload_cmd(
    *,
    upload_script: Path,
    bucket: str,
    key: str,
    local: Path,
    region: str,
    profile: str | None,
    dry_run: bool,
) -> list[str]:
    cmd = [
        str(upload_script),
        "--bucket",
        bucket,
        "--key",
        key,
        "--local",
        str(local),
        "--region",
        region,
    ]
    if profile:
        cmd.extend(["--profile", profile])
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def _build_verify_cmd(
    *,
    verify_script: Path,
    bucket: str,
    key: str,
    local: Path,
    region: str,
    profile: str | None,
) -> list[str]:
    cmd = [
        str(verify_script),
        "--bucket",
        bucket,
        "--key",
        key,
        "--local",
        str(local),
        "--region",
        region,
    ]
    if profile:
        cmd.extend(["--profile", profile])
    return cmd


def _truncate_err(msg: str) -> str:
    msg = msg.strip()
    if len(msg) > _ERROR_TRUNCATE:
        return msg[:_ERROR_TRUNCATE] + "…"
    return msg


def _print_discovery_summary(
    files: list[Any],
    register_counts: dict[str, int] | None = None,
) -> None:
    by_prefix: dict[str, dict[str, int]] = defaultdict(lambda: {"pending": 0, "skipped": 0})
    for f in files:
        status = str(f.status)
        if status in by_prefix[f.experiment_prefix]:
            by_prefix[f.experiment_prefix][status] += 1
        else:
            by_prefix[f.experiment_prefix][status] = (
                by_prefix[f.experiment_prefix].get(status, 0) + 1
            )
    for prefix in sorted(by_prefix):
        c = by_prefix[prefix]
        print(
            f"prefix={prefix}  pending={c.get('pending', 0)} skipped={c.get('skipped', 0)}"
        )
    total_pending = sum(1 for f in files if str(f.status) == MigrationStatus.PENDING)
    total_skipped = sum(1 for f in files if str(f.status) == MigrationStatus.SKIPPED)
    if register_counts is None:
        print(f"TOTAL pending={total_pending} skipped={total_skipped}")
    else:
        print(
            f"TOTAL pending={total_pending} skipped={total_skipped} "
            f"already_present={register_counts.get('already_present', 0)} "
            f"inserted={register_counts.get('inserted', 0)}"
        )


def cmd_init(args: argparse.Namespace) -> int:
    allowlist = _resolve_allowlist(args.prefixes)
    if allowlist == 2:
        return 2

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
    if not args.dry_run:
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

    _print_discovery_summary(files, register_counts)

    export_path = args.export_inventory
    if export_path is None and not args.dry_run:
        export_path = INVENTORY_DIR / "artifacts_inventory.json"
    if export_path is not None:
        write_inventory_json(files, export_path)
        print(f"Wrote inventory: {export_path}")
    return 0


def _verify_one(
    *,
    row: dict[str, Any],
    repo_root: Path,
    bucket: str,
    region: str,
    profile: str | None,
    verify_script: Path,
) -> tuple[bool, str]:
    abs_local = repo_root / row["local_path"]
    cmd = _build_verify_cmd(
        verify_script=verify_script,
        bucket=bucket,
        key=row["s3_key"],
        local=abs_local,
        region=region,
        profile=profile,
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True, ""
    err = _truncate_err(result.stderr or result.stdout or f"verify exited {result.returncode}")
    return False, err


def cmd_upload(args: argparse.Namespace) -> int:
    if not Path(args.db).exists():
        print(f"error: DB not found: {args.db} (run init first)", file=sys.stderr)
        return 1

    upload_script = Path(args.upload_script)
    if not upload_script.is_file():
        print(f"error: upload script not found: {upload_script}", file=sys.stderr)
        return 2

    tracker = MigrationTracker(args.db)
    try:
        if args.force_reupload:
            n = tracker.force_reupload(args.force_reupload)
            print(f"force-reupload reset {n} row(s)")

        rows = tracker.get_files_to_upload(prefix=args.prefix, limit=args.limit)

        if args.dry_run:
            for row in rows:
                abs_local = (Path(args.repo_root) / row["local_path"]).resolve()
                cmd = _build_upload_cmd(
                    upload_script=upload_script,
                    bucket=args.bucket,
                    key=row["s3_key"],
                    local=abs_local,
                    region=args.region,
                    profile=args.profile,
                    dry_run=True,
                )
                result = subprocess.run(cmd, capture_output=True, text=True)
                line = (result.stdout or "").strip()
                if line:
                    print(line)
                elif result.returncode != 0:
                    print(
                        f"DRY-RUN: aws s3 cp '{abs_local}' "
                        f"'s3://{args.bucket}/{row['s3_key']}' --region '{args.region}'"
                    )
            print(f"dry-run planned uploads: {len(rows)}")
            return 0

        failures = 0
        for row in rows:
            local_path = row["local_path"]
            tracker.mark_started(local_path)
            abs_local = Path(args.repo_root) / local_path

            if not abs_local.is_file():
                tracker.mark_failed(local_path, f"preflight: local file missing: {abs_local}")
                failures += 1
                print(f"FAIL {local_path}: missing")
                continue

            actual_size = abs_local.stat().st_size
            if actual_size != int(row["file_size_bytes"]):
                tracker.mark_failed(
                    local_path,
                    f"preflight: size mismatch db={row['file_size_bytes']} disk={actual_size}",
                )
                failures += 1
                print(f"FAIL {local_path}: size mismatch")
                continue

            cmd = _build_upload_cmd(
                upload_script=upload_script,
                bucket=args.bucket,
                key=row["s3_key"],
                local=abs_local.resolve(),
                region=args.region,
                profile=args.profile,
                dry_run=False,
            )
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                err = _truncate_err(
                    result.stderr or f"upload_to_s3.sh exited {result.returncode}"
                )
                tracker.mark_failed(local_path, err)
                failures += 1
                print(f"FAIL {local_path}: {err}")
                continue

            tracker.mark_completed(local_path)
            print(f"OK   {local_path}")

            if args.verify:
                ok, verr = _verify_one(
                    row=row,
                    repo_root=Path(args.repo_root),
                    bucket=args.bucket,
                    region=args.region,
                    profile=args.profile,
                    verify_script=Path(args.verify_script),
                )
                if ok:
                    tracker.mark_verified(local_path)
                    print(f"VERIFIED {local_path}")
                else:
                    tracker.mark_failed(local_path, f"verify: {verr}")
                    failures += 1
                    print(f"FAIL verify {local_path}: {verr}")

        counts = tracker.summary_counts(prefix=args.prefix)
        print("summary:", json.dumps(counts, sort_keys=True))
        return 1 if failures else 0
    finally:
        tracker.close()


def cmd_status(args: argparse.Namespace) -> int:
    if not Path(args.db).exists():
        print(f"error: DB not found: {args.db}", file=sys.stderr)
        return 1

    tracker = MigrationTracker(args.db)
    try:
        counts = tracker.summary_counts(prefix=args.prefix)
        print("overall:", json.dumps(counts, sort_keys=True))

        rows = tracker.list_rows(prefix=args.prefix)
        by_prefix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for r in rows:
            by_prefix[r["experiment_prefix"]][r["status"]] += 1
        for prefix in sorted(by_prefix):
            print(f"prefix={prefix} {json.dumps(dict(by_prefix[prefix]), sort_keys=True)}")

        if args.show_failed:
            failed = [r for r in rows if r["status"] == MigrationStatus.FAILED]
            for r in failed:
                print(f"FAILED {r['local_path']}: {r.get('error_message') or ''}")

        if args.check_stale:
            stale = []
            for r in rows:
                if r["status"] not in (MigrationStatus.COMPLETED, MigrationStatus.VERIFIED):
                    continue
                path = Path(args.repo_root) / r["local_path"]
                if not path.is_file():
                    stale.append((r["local_path"], "missing on disk"))
                    continue
                size = path.stat().st_size
                if size != int(r["file_size_bytes"]):
                    stale.append(
                        (r["local_path"], f"size {size} != db {r['file_size_bytes']}")
                    )
                    continue
                if r.get("sha256"):
                    sha = _sha256_file(path)
                    if sha != r["sha256"]:
                        stale.append((r["local_path"], "sha256 mismatch"))
            if stale:
                print(f"stale count: {len(stale)}")
                for path, reason in stale:
                    print(f"STALE {path}: {reason}")
            else:
                print("stale count: 0")
        return 0
    finally:
        tracker.close()


def cmd_retry_failed(args: argparse.Namespace) -> int:
    if not Path(args.db).exists():
        print(f"error: DB not found: {args.db}", file=sys.stderr)
        return 1
    tracker = MigrationTracker(args.db)
    try:
        n = tracker.reset_failed_to_pending(prefix=args.prefix)
        print(f"reset {n} failed row(s) to pending")
        return 0
    finally:
        tracker.close()


def cmd_verify(args: argparse.Namespace) -> int:
    if not Path(args.db).exists():
        print(f"error: DB not found: {args.db}", file=sys.stderr)
        return 1
    verify_script = Path(args.verify_script)
    if not verify_script.is_file():
        print(f"error: verify script not found: {verify_script}", file=sys.stderr)
        return 2

    tracker = MigrationTracker(args.db)
    try:
        statuses = [MigrationStatus.COMPLETED]
        if not args.skip_verified:
            statuses.append(MigrationStatus.VERIFIED)

        rows: list[dict[str, Any]] = []
        for st in statuses:
            rows.extend(tracker.list_rows(status=st, prefix=args.prefix))
        rows.sort(key=lambda r: r["local_path"])
        if args.limit is not None:
            rows = rows[: args.limit]

        failures = 0
        for row in rows:
            ok, verr = _verify_one(
                row=row,
                repo_root=Path(args.repo_root),
                bucket=args.bucket,
                region=args.region,
                profile=args.profile,
                verify_script=verify_script,
            )
            if ok:
                tracker.mark_verified(row["local_path"])
                print(f"VERIFIED {row['local_path']}")
            else:
                tracker.mark_failed(row["local_path"], f"verify: {verr}")
                failures += 1
                print(f"FAIL {row['local_path']}: {verr}")
        return 1 if failures else 0
    finally:
        tracker.close()


def cmd_export(args: argparse.Namespace) -> int:
    if not Path(args.db).exists():
        print(f"error: DB not found: {args.db}", file=sys.stderr)
        return 1
    tracker = MigrationTracker(args.db)
    try:
        if args.prefix:
            allowed = {
                r["local_path"]
                for r in tracker.list_rows(prefix=args.prefix)
                if r["status"] in (MigrationStatus.COMPLETED, MigrationStatus.VERIFIED)
            }
            rows = [r for r in tracker.export_completed() if r["local_path"] in allowed]
        else:
            rows = tracker.export_completed()

        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(rows)} row(s) to {out}")
        return 0
    finally:
        tracker.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate experiment csv/json artifacts to S3")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--db", type=Path, default=DB_PATH)
        p.add_argument("--repo-root", type=Path, default=REPO_ROOT)

    p_init = sub.add_parser("init", help="Discover + register into SQLite")
    add_common(p_init)
    p_init.add_argument("--dry-run", action="store_true")
    p_init.add_argument("--refresh-metadata", action="store_true")
    p_init.add_argument("--export-inventory", type=Path, default=None)
    p_init.add_argument("--prefix", action="append", dest="prefixes", default=None)
    p_init.add_argument("--no-sha256", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_upload = sub.add_parser("upload", help="Upload pending/in_progress via upload_to_s3.sh")
    add_common(p_upload)
    p_upload.add_argument("--bucket", default=BUCKET)
    p_upload.add_argument("--region", default=DEFAULT_REGION)
    p_upload.add_argument("--profile", default=None)
    p_upload.add_argument("--prefix", default=None)
    p_upload.add_argument("--dry-run", action="store_true")
    p_upload.add_argument("--verify", action="store_true")
    p_upload.add_argument("--limit", type=int, default=None)
    p_upload.add_argument("--force-reupload", nargs="+", default=None)
    p_upload.add_argument("--upload-script", type=Path, default=UPLOAD_SCRIPT)
    p_upload.add_argument("--verify-script", type=Path, default=VERIFY_SCRIPT)
    p_upload.set_defaults(func=cmd_upload)

    p_status = sub.add_parser("status", help="Print summary")
    add_common(p_status)
    p_status.add_argument("--prefix", default=None)
    p_status.add_argument("--show-failed", action="store_true")
    p_status.add_argument("--check-stale", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_retry = sub.add_parser("retry-failed", help="Reset failed → pending")
    add_common(p_retry)
    p_retry.add_argument("--prefix", default=None)
    p_retry.set_defaults(func=cmd_retry_failed)

    p_verify = sub.add_parser("verify", help="Re-check completed/verified rows against S3")
    add_common(p_verify)
    p_verify.add_argument("--bucket", default=BUCKET)
    p_verify.add_argument("--region", default=DEFAULT_REGION)
    p_verify.add_argument("--profile", default=None)
    p_verify.add_argument("--prefix", default=None)
    p_verify.add_argument("--limit", type=int, default=None)
    p_verify.add_argument("--download-hash", action="store_true", default=True)
    p_verify.add_argument("--skip-verified", action="store_true")
    p_verify.add_argument("--verify-script", type=Path, default=VERIFY_SCRIPT)
    p_verify.set_defaults(func=cmd_verify)

    p_export = sub.add_parser("export", help="Dump completed/verified rows to JSON")
    add_common(p_export)
    p_export.add_argument("--out", type=Path, required=True)
    p_export.add_argument("--prefix", default=None)
    p_export.set_defaults(func=cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
