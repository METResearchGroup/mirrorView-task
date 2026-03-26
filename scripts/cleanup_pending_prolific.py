#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    # Assumes you run this from one directory up (mirrorView-raw-data/),
    # or pass an absolute path via --dir.
    cmd = [
        sys.executable,
        "-u",
        "scripts/cleanup_pending_assignments.py",
        "--dir",
        "prolific",
    ] + sys.argv[1:]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())

