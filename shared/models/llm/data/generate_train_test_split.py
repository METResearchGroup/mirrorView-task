"""Write an 80/20 train/test split for each upsampled Study 2 dataset.

Upsampling copies rows and keeps the source ``post_id``, so the same id can
appear more than once. The split is on unique post IDs, separately for each
dataset and each ``keep_remove_label`` class. Test receives
``floor(0.2 * unique ids)`` from that class. Every copied row follows its
post ID, so train and test row counts can differ from 80/20.

Run from the repo root::

    PYTHONPATH=. uv run python shared/models/llm/data/generate_train_test_split.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from shared.data.dataloader import (
    STUDY_DATA_BUCKET,
    _use_lab_credentials_when_unset,
    load_dataset,
)
from shared.models.llm.data.dataloader import Split
from shared.models.llm.data.registry import (
    SOURCE_DATASETS,
    resolve_split_path,
    split_relative_path,
)

TEST_FRACTION = 0.2
RANDOM_SEED = 1
POST_ID_COLUMN = "post_id"
CLASS_LABEL_COLUMN = "keep_remove_label"


def assign_train_test(
    frame: pd.DataFrame,
    *,
    test_fraction: float = TEST_FRACTION,
    random_seed: int = RANDOM_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assign every row to train or test by unique post ID within each class.

    Parameters
    ----------
    frame
        Upsampled keep/remove rows. The function does not modify it.
    test_fraction
        Fraction of unique post IDs in each class assigned to test. The count
        is ``floor(test_fraction * n_unique)`` for that class.
    random_seed
        Shuffle seed used independently inside each class.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Train frame, then test frame. Each keeps the source columns, dtypes,
        and row order, with a fresh ``RangeIndex``.

    Raises
    ------
    KeyError
        When ``post_id`` or ``keep_remove_label`` is missing.
    ValueError
        When a post ID is null, a post ID has more than one class, or a class
        is too small to fill both sides of the split.
    """
    _require_columns(frame)
    _reject_null_ids_or_labels(frame)
    _assert_one_class_per_post(frame)
    test_ids = _test_post_ids(frame, test_fraction, random_seed)
    post_ids = frame[POST_ID_COLUMN].astype(str)
    test_mask = post_ids.isin(test_ids)
    train = frame.loc[~test_mask].reset_index(drop=True)
    test = frame.loc[test_mask].reset_index(drop=True)
    return train, test


def write_split_frames(
    dataset_name: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    root: Path | None = None,
) -> dict[Split, Path]:
    """Write ``train.csv`` and ``test.csv`` for one dataset.

    Parameters
    ----------
    root
        Directory that contains ``shared/``. Defaults to the repository root.

    Returns
    -------
    dict[Split, pathlib.Path]
        Absolute paths keyed by ``Split.TRAIN`` then ``Split.TEST``.
    """
    frames = {Split.TRAIN: train, Split.TEST: test}
    written: dict[Split, Path] = {}
    for split, split_frame in frames.items():
        path = resolve_split_path(dataset_name, split.value, root=root)
        path.parent.mkdir(parents=True, exist_ok=True)
        split_frame.to_csv(path, index=False)
        written[split] = path
    return written


def generate_train_test_splits(*, root: Path | None = None) -> dict[str, dict[Split, Path]]:
    """Load each upsampled dataset, split it, and write both CSV files.

    Returns
    -------
    dict[str, dict[Split, pathlib.Path]]
        Absolute paths keyed by source registry name, in ``SOURCE_DATASETS``
        order.
    """
    return {
        dataset_name: _generate_one(dataset_name, root=root)
        for dataset_name in SOURCE_DATASETS
    }


def upload_split_files(written: dict[str, dict[Split, Path]]) -> None:
    """Upload written CSV files to their registry keys.

    Parameters
    ----------
    written
        Paths from ``generate_train_test_splits`` or ``write_split_frames``.
        Keys are source registry names. Upload order follows that mapping,
        then train before test.
    """
    _use_lab_credentials_when_unset()
    store = S3(STUDY_DATA_BUCKET, region_name=DEFAULT_REGION_NAME)
    for dataset_name, splits in written.items():
        for split, path in splits.items():
            key = split_relative_path(dataset_name, split.value).as_posix()
            store.upload_file(path, key)
            print(f"uploaded s3://{STUDY_DATA_BUCKET}/{key}")


def main() -> None:
    """Write the six CSV files, upload them, and print row counts."""
    written = generate_train_test_splits()
    for dataset_name, splits in written.items():
        for split, path in splits.items():
            _print_written_split(dataset_name, split, path)
    upload_split_files(written)


def _generate_one(dataset_name: str, *, root: Path | None) -> dict[Split, Path]:
    """Load one registered table, split it, and write both CSV files."""
    frame = load_dataset(dataset_name, low_memory=False)
    train, test = assign_train_test(frame)
    return write_split_frames(dataset_name, train, test, root=root)


def _print_written_split(dataset_name: str, split: Split, path: Path) -> None:
    """Print the registry name, split, path, row count, and class counts."""
    frame = pd.read_csv(path, low_memory=False)
    unique_ids = frame[POST_ID_COLUMN].astype(str).nunique()
    counts = frame[CLASS_LABEL_COLUMN].value_counts().sort_index().to_dict()
    print(
        f"{dataset_name} split={split.value} path={path.resolve()} "
        f"rows={len(frame)} unique_post_ids={unique_ids} class_counts={counts}"
    )


def _require_columns(frame: pd.DataFrame) -> None:
    """Raise KeyError when the split columns are missing."""
    missing = {POST_ID_COLUMN, CLASS_LABEL_COLUMN} - set(frame.columns)
    if missing:
        raise KeyError(f"Dataset is missing required columns: {sorted(missing)}")


def _reject_null_ids_or_labels(frame: pd.DataFrame) -> None:
    """Raise ValueError when ``post_id`` or the class column contains nulls."""
    if bool(frame[POST_ID_COLUMN].isna().any()):
        raise ValueError(f"{POST_ID_COLUMN} contains null values")
    if bool(frame[CLASS_LABEL_COLUMN].isna().any()):
        raise ValueError(f"{CLASS_LABEL_COLUMN} contains null values")


def _assert_one_class_per_post(frame: pd.DataFrame) -> None:
    """Raise ValueError when one post ID has more than one class label."""
    classes_per_post = frame.groupby(frame[POST_ID_COLUMN].astype(str), dropna=False)[
        CLASS_LABEL_COLUMN
    ].nunique()
    conflicts = classes_per_post[classes_per_post != 1]
    if not conflicts.empty:
        example = str(conflicts.index[0])
        raise ValueError(
            f"{POST_ID_COLUMN} {example!r} has more than one {CLASS_LABEL_COLUMN}"
        )


def _test_post_ids(frame: pd.DataFrame, test_fraction: float, random_seed: int) -> set[str]:
    """Return the test post IDs, taking the same fraction from each class."""
    test_ids: set[str] = set()
    for class_value in sorted(frame[CLASS_LABEL_COLUMN].unique().tolist()):
        class_rows = frame.loc[frame[CLASS_LABEL_COLUMN] == class_value]
        unique_ids = class_rows[POST_ID_COLUMN].astype(str).drop_duplicates()
        n_unique = len(unique_ids)
        n_test = int(test_fraction * n_unique)
        if n_test <= 0 or n_test >= n_unique:
            raise ValueError(
                f"{CLASS_LABEL_COLUMN}={class_value!r} has {n_unique} unique "
                f"post IDs, which cannot fill a {test_fraction:.0%} test split"
            )
        chosen = unique_ids.sample(n=n_test, random_state=random_seed)
        test_ids.update(chosen.tolist())
    return test_ids


if __name__ == "__main__":
    main()
