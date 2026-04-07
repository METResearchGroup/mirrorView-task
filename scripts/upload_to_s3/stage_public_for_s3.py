"""Validate public/config.js against AWS, then stage public/ under s3_upload/<timestamp>/ with manifest.json."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.upload_to_s3.constants import (
    API_NAME,
    API_STAGE,
    AWS_REGION,
    PROTECTED_PREFIXES,
    SKIP_STAGING_NAMES,
    SOURCE_PUBLIC_DIR,
    STAGING_ROOT,
    TARGET_BUCKET,
)


@dataclass(frozen=True)
class ConfigUrls:
    api_base_url: str
    post_assignments_url: str
    save_data_url: str


def _run_aws_json(args: list[str]) -> Any:
    cmd = ["aws", *args, "--region", AWS_REGION, "--output", "json"]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def fetch_config_urls_from_aws() -> ConfigUrls:
    data = _run_aws_json(["apigatewayv2", "get-apis"])
    items = data.get("Items") or []
    match = None
    for item in items:
        if item.get("Name") == API_NAME:
            match = item
            break
    if not match:
        names = [i.get("Name") for i in items]
        raise SystemExit(
            f"No HTTP API named {API_NAME!r} in {AWS_REGION}. Known names: {names!r}"
        )
    base = (match.get("ApiEndpoint") or "").rstrip("/")
    if not base:
        raise SystemExit("API response missing ApiEndpoint")
    post = f"{base}/{API_STAGE}/get-post-assignments"
    save = f"{base}/{API_STAGE}/save-jspsych-data"
    return ConfigUrls(api_base_url=base, post_assignments_url=post, save_data_url=save)


def parse_config_js_urls(config_path: Path) -> tuple[str, str]:
    text = config_path.read_text(encoding="utf-8")
    post_m = re.search(
        r"POST_ASSIGNMENTS_URL\s*:\s*['\"]([^'\"]+)['\"]", text
    )
    save_m = re.search(r"SAVE_DATA_URL\s*:\s*['\"]([^'\"]+)['\"]", text)
    if not post_m or not save_m:
        raise SystemExit(
            f"Could not parse POST_ASSIGNMENTS_URL / SAVE_DATA_URL from {config_path}"
        )
    return post_m.group(1), save_m.group(1)


def assert_config_file_matches(config_urls: ConfigUrls, config_path: Path) -> None:
    post, save = parse_config_js_urls(config_path)
    bad: list[str] = []
    if post != config_urls.post_assignments_url:
        bad.append(
            f"POST_ASSIGNMENTS_URL\n  expected: {config_urls.post_assignments_url}\n"
            f"  actual:   {post}"
        )
    if save != config_urls.save_data_url:
        bad.append(
            f"SAVE_DATA_URL\n  expected: {config_urls.save_data_url}\n"
            f"  actual:   {save}"
        )
    if bad:
        print("config.js does not match deployed API URLs:\n", file=sys.stderr)
        print("\n\n".join(bad), file=sys.stderr)
        raise SystemExit(1)


def _is_protected_key(rel_posix: str) -> bool:
    return any(rel_posix.startswith(p) for p in PROTECTED_PREFIXES)


def prepare_files_for_upload() -> Path:
    if not SOURCE_PUBLIC_DIR.is_dir():
        raise SystemExit(f"Missing source directory: {SOURCE_PUBLIC_DIR}")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    release_dir = STAGING_ROOT / ts
    release_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(SOURCE_PUBLIC_DIR.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(SOURCE_PUBLIC_DIR)
        rel_posix = rel.as_posix()
        if path.name in SKIP_STAGING_NAMES:
            continue
        if _is_protected_key(rel_posix):
            raise SystemExit(
                f"Refusing to stage path under protected prefix {PROTECTED_PREFIXES!r}: {rel_posix}"
            )
        dest = release_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

    return release_dir


def build_release_manifest(release_dir: Path) -> dict[str, Any]:
    files: list[str] = []
    for path in sorted(release_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(release_dir)
        key = rel.as_posix()
        if _is_protected_key(key):
            raise SystemExit(f"Manifest build found protected key {key!r}")
        files.append(key)

    ts = release_dir.name
    return {
        "timestamp": ts,
        "bucket": TARGET_BUCKET,
        "staged_dir": str(release_dir.as_posix()),
        "files": files,
    }


def write_manifest(release_dir: Path, manifest: dict[str, Any]) -> Path:
    path = release_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def print_staging_summary(release_dir: Path, manifest: dict[str, Any]) -> None:
    n = len(manifest["files"])
    print(f"Release directory: {release_dir}")
    print(f"Manifest: {release_dir / 'manifest.json'}")
    print(f"Staged files: {n}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate public/config.js against live API Gateway, then copy public/ "
            "into s3_upload/<timestamp>/ and write manifest.json."
        )
    )
    parser.add_argument(
        "--validate-config-only",
        action="store_true",
        help="Fetch API URLs from AWS and compare to public/config.js; then exit.",
    )
    args = parser.parse_args()

    config_path = SOURCE_PUBLIC_DIR / "config.js"
    if not config_path.is_file():
        raise SystemExit(f"Missing {config_path}")

    config_urls = fetch_config_urls_from_aws()

    if args.validate_config_only:
        assert_config_file_matches(config_urls, config_path)
        print("public/config.js matches deployed API URLs.")
        return

    assert_config_file_matches(config_urls, config_path)
    release_dir = prepare_files_for_upload()
    manifest = build_release_manifest(release_dir)
    write_manifest(release_dir, manifest)
    print_staging_summary(release_dir, manifest)


if __name__ == "__main__":
    main()
