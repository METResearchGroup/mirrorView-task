"""Write balanced Study 2 keep/remove tables from the registered sources.

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_2/upsample_keep_remove_labels.py
"""

from __future__ import annotations

import pandas as pd

from shared.data import dataloader, registry
from shared.utils.upsample import upsample_df


def write_upsampled_keep_remove_label_datasets() -> dict[str, pd.DataFrame]:
    """Load each source, balance it, resolve the output path, and write the CSV."""
    # load → balance → resolve → write
    ...


def main() -> None:
    """Run the local load, balance, resolve, and write path."""
    write_upsampled_keep_remove_label_datasets()
    ...


if __name__ == "__main__":
    main()
