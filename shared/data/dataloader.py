"""Loader for datasets registered in ``shared.data.registry``.

Each registered name is an object in ``mirrorview-experimental-artifacts``.
The object key is the repo-relative CSV path.
"""

from __future__ import annotations

import os
from io import BytesIO

import pandas as pd
from botocore.exceptions import ClientError

from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from shared.data import registry

STUDY_DATA_BUCKET = "mirrorview-experimental-artifacts"
_MISSING_OBJECT_CODES = frozenset({"404", "NoSuchKey", "NotFound"})


def load_dataset(name: str, *, low_memory: bool = False) -> pd.DataFrame:
    """Load a registered study CSV from S3 with no transforms.

    The object key is the registry path, for example
    ``shared/data/raw/study_phase_2_part_2/results/full.csv``.

    Raises:
        KeyError: If ``name`` is not in the registry.
        FileNotFoundError: If the S3 object is missing.
    """
    key = registry.get_dataset(name).relative_path.as_posix()
    body = _read_study_object(key)
    return pd.read_csv(BytesIO(body), low_memory=low_memory)


def _read_study_object(key: str) -> bytes:
    _use_lab_credentials_when_unset()
    store = S3(STUDY_DATA_BUCKET, region_name=DEFAULT_REGION_NAME)
    try:
        return store.get_bytes(key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in _MISSING_OBJECT_CODES:
            raise FileNotFoundError(
                f"Dataset object not found: s3://{STUDY_DATA_BUCKET}/{key}"
            ) from exc
        raise


def _use_lab_credentials_when_unset() -> None:
    """Copy lab AWS keys into the standard env vars when those are empty."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        access_key = os.environ.get("LAB_AWS_ACCESS_KEY_ID", "")
        if access_key:
            os.environ["AWS_ACCESS_KEY_ID"] = access_key
    if not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        secret_key = os.environ.get("LAB_AWS_ACCESS_KEY_SECRET", "")
        if secret_key:
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key
