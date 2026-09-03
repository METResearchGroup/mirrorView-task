from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_platform.utils.deduplication import DedupeConfig, DedupeSession
from data_platform.utils.platform_specific_columns import STANDARDIZED_SOURCE_RECORD_ID_COLUMN
from data_platform.utils.storage import StorageManager


@dataclass(frozen=True)
class FeatureLabelQuery:
    """Query labeled record ids from feature files across timestamped runs.

    Feature generation skips unlabeled records with the same skip set session
    type that ingest and preprocess use.
    """

    feature_storage: StorageManager
    id_column: str = "uri"
    feature_file_id_column: str = STANDARDIZED_SOURCE_RECORD_ID_COLUMN

    def labeled_ids(self, feature_name: str) -> set[str]:
        """Return ids labeled for feature_name from timestamped feature run directories."""
        skip_set = DedupeSession(
            DedupeConfig(
                id_column=self.feature_file_id_column,
                filename=self.feature_storage.filename_for(feature_name),
            )
        )
        skip_set.load_seen_ids_from_all_runs(self.feature_storage)
        return set(skip_set.seen_ids)

    def filter_unlabeled(
        self,
        records: pd.DataFrame,
        feature_name: str,
    ) -> pd.DataFrame:
        """Return records whose id is not yet labeled for feature_name."""
        if records.empty:
            return records.copy()

        labeled = self.labeled_ids(feature_name)
        if not labeled:
            return records.copy()

        mask = ~records[self.id_column].astype(str).isin(list(labeled))
        return records.loc[mask].reset_index(drop=True)
