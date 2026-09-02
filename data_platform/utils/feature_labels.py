from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_platform.utils.paths import to_package_relative
from data_platform.utils.storage import StorageManager


@dataclass(frozen=True)
class FeatureLabelQuery:
    """Query labeled record ids from feature files at the features root."""

    feature_storage: StorageManager
    id_column: str = "uri"
    feature_file_id_column: str = "uri"

    def labeled_ids(self, export_filename: str) -> set[str]:
        """Return ids labeled in the package-relative feature export file."""
        relative_file_path = to_package_relative(
            self.feature_storage.root_dir / export_filename
        )
        return self.feature_storage.load_seen_ids_from_disk(
            relative_file_path,
            self.feature_file_id_column,
        )

    def filter_unlabeled(
        self,
        records: pd.DataFrame,
        export_filename: str,
    ) -> pd.DataFrame:
        """Return records whose id is not yet labeled in export_filename."""
        if records.empty:
            return records.copy()

        labeled = self.labeled_ids(export_filename)
        if not labeled:
            return records.copy()

        mask = ~records[self.id_column].astype(str).isin(list(labeled))
        return records.loc[mask].reset_index(drop=True)
