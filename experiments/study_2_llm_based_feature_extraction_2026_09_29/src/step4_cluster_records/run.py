"""Step 4 entrypoint: cluster feature embeddings with HDBSCAN.

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
    HDBSCAN_MIN_CLUSTER_SIZE,
    HDBSCAN_NOISE_LABEL,
    SEED,
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


def main() -> None:
    """Download step 3 artifacts, cluster, write outputs, and print counts."""
    use_lab_credentials()

    features_path = download_artifact(FEATURES_KEY)
    embeddings_path = download_artifact(EMBEDDINGS_KEY)
    feature_ids_path = download_artifact(FEATURE_IDS_KEY)

    features = pd.read_parquet(features_path)
    matrix = np.load(embeddings_path)
    feature_ids: list[str] = json.loads(feature_ids_path.read_text(encoding="utf-8"))

    assignments, params = assign_clusters(features, matrix, feature_ids)
    cluster_sizes = summarize_clusters(assignments, features)

    n_features = len(feature_ids)
    n_noise = int((assignments["cluster_id"] == HDBSCAN_NOISE_LABEL).sum())
    n_clusters = int(params["n_clusters"])

    metadata = {
        "SEED": SEED,
        "HDBSCAN_MIN_CLUSTER_SIZE": HDBSCAN_MIN_CLUSTER_SIZE,
        "params": params,
        "n_clusters": n_clusters,
        "n_noise": n_noise,
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

    print(f"features={n_features} clusters={n_clusters} noise={n_noise}")


if __name__ == "__main__":
    main()
