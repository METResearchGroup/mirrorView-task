"""Step 4 entrypoint: cluster kept-post and removed-post features with K-means.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step4_cluster_records/run.py
"""

from __future__ import annotations

import json

from experiments.compare_jev_human_uncertainty_2026_09_25.jev_labels import (
    use_lab_credentials,
)

use_lab_credentials()

import numpy as np
import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    ASSIGNMENTS_KEY,
    CLUSTER_METADATA_KEY,
    CLUSTER_SIZES_KEY,
    EMBEDDINGS_KEY,
    FEATURE_IDS_KEY,
    FEATURES_KEY,
    KMEANS_CLUSTERS_PER_SIDE,
    SEED,
    SIDE_KEPT,
    SIDE_REMOVED,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.storage import (
    download_artifact,
    local_path,
    upload_artifact,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step4_cluster_records.cluster import (
    assign_clusters,
    summarize_clusters,
)
from shared.feature_discovery.llm_based.cluster import KMEANS_N_INIT


def main() -> None:
    """Download step 3 artifacts, cluster each side, write outputs, and print counts."""
    use_lab_credentials()

    features_path = download_artifact(FEATURES_KEY)
    embeddings_path = download_artifact(EMBEDDINGS_KEY)
    feature_ids_path = download_artifact(FEATURE_IDS_KEY)

    features = pd.read_parquet(features_path)
    matrix = np.load(embeddings_path)
    feature_ids: list[str] = json.loads(feature_ids_path.read_text(encoding="utf-8"))

    assignments = assign_clusters(features, matrix, feature_ids)
    cluster_sizes = summarize_clusters(assignments, features)

    keep_features = int((assignments["side"] == SIDE_KEPT).sum())
    remove_features = int((assignments["side"] == SIDE_REMOVED).sum())
    n_clusters = int(assignments["cluster_key"].nunique())
    if n_clusters != KMEANS_CLUSTERS_PER_SIDE * 2:
        raise ValueError(f"expected 30 clusters, found {n_clusters}")
    if cluster_sizes.groupby("side")["cluster_key"].nunique().tolist() != [
        KMEANS_CLUSTERS_PER_SIDE,
        KMEANS_CLUSTERS_PER_SIDE,
    ]:
        raise ValueError("each side must have 15 clusters")

    metadata = {
        "SEED": SEED,
        "method": "kmeans",
        "clusters_per_side": KMEANS_CLUSTERS_PER_SIDE,
        "n_init": KMEANS_N_INIT,
        "scaled": False,
        "keep_features": keep_features,
        "remove_features": remove_features,
        "n_clusters": n_clusters,
        "n_noise": 0,
    }

    assignments_out = local_path(ASSIGNMENTS_KEY)
    assignments_out.parent.mkdir(parents=True, exist_ok=True)
    assignments.to_parquet(assignments_out, index=False)

    sizes_out = local_path(CLUSTER_SIZES_KEY)
    cluster_sizes.to_parquet(sizes_out, index=False)

    metadata_out = local_path(CLUSTER_METADATA_KEY)
    metadata_out.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    upload_artifact(ASSIGNMENTS_KEY)
    upload_artifact(CLUSTER_SIZES_KEY)
    upload_artifact(CLUSTER_METADATA_KEY)

    print(
        f"features={len(feature_ids)} keep_features={keep_features} "
        f"remove_features={remove_features} clusters={n_clusters} noise=0"
    )


if __name__ == "__main__":
    main()
