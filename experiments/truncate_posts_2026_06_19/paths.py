from __future__ import annotations

from enum import Enum
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = EXPERIMENT_DIR / "outputs"


class TruncationVersion(str, Enum):
    v1 = "truncation_v1"
    v2 = "truncation_v2"


def parse_version(version: str) -> TruncationVersion:
    normalized = version.strip().lower().replace("-", "_")
    aliases = {
        "v1": TruncationVersion.v1,
        "truncation_v1": TruncationVersion.v1,
        "1": TruncationVersion.v1,
        "v2": TruncationVersion.v2,
        "truncation_v2": TruncationVersion.v2,
        "2": TruncationVersion.v2,
    }
    if normalized not in aliases:
        valid = ", ".join(sorted({"v1", "v2", "truncation_v1", "truncation_v2"}))
        raise ValueError(f"Unknown truncation version {version!r}. Expected one of: {valid}")
    return aliases[normalized]


def version_dir(version: TruncationVersion) -> Path:
    return OUTPUTS_DIR / version.value


def flips_csv(version: TruncationVersion) -> Path:
    return version_dir(version) / "flips.csv"


def flips_with_flag_csv(version: TruncationVersion) -> Path:
    return version_dir(version) / "flips_with_flag.csv"


def differentials_png(version: TruncationVersion) -> Path:
    return version_dir(version) / "differentials.png"


def highest_absolute_differential_csv(version: TruncationVersion) -> Path:
    return version_dir(version) / "highest_absolute_differential.csv"


def sample_flips_csv(version: TruncationVersion) -> Path:
    return version_dir(version) / "sample_flips.csv"


def ensure_version_dir(version: TruncationVersion) -> Path:
    path = version_dir(version)
    path.mkdir(parents=True, exist_ok=True)
    return path
