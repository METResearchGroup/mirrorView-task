"""Step 3 entrypoint: deduplicate candidate features and embed with Titan.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step3_embed_features/run.py
"""

from __future__ import annotations

import json
import time

from experiments.compare_jev_human_uncertainty_2026_09_25.jev_labels import (
    use_lab_credentials,
)

use_lab_credentials()

import numpy as np
import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    CANDIDATE_FEATURES_KEY,
    EMBED_MAX_WORKERS,
    EMBEDDINGS_KEY,
    FEATURE_IDS_KEY,
    FEATURES_KEY,
    TITAN_USD_PER_MILLION_TOKENS,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.storage import (
    download_artifact,
    local_path,
    upload_artifact,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step3_embed_features.dedupe import (
    dedupe_features,
    flatten_candidate_rows,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step3_embed_features.embed import (
    embed_texts,
)
from shared.embeddings.bedrock import create_embedding


def _load_candidate_rows() -> list[dict]:
    path = download_artifact(CANDIDATE_FEATURES_KEY)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    """Download candidates, dedupe, embed, upload artifacts, and print counts."""
    use_lab_credentials()
    rows = _load_candidate_rows()
    flat = flatten_candidate_rows(rows)
    candidate_records = len(flat)
    expected_candidate_records = 20573
    if candidate_records != expected_candidate_records:
        raise ValueError(
            f"expected {expected_candidate_records} candidate records, "
            f"found {candidate_records}"
        )

    features = dedupe_features(flat)
    texts = features["text"].tolist()
    embeddings, titan_tokens = embed_texts(
        texts,
        create_embedding,
        time.sleep,
        EMBED_MAX_WORKERS,
    )
    feature_ids = features["feature_id"].tolist()

    features_path = local_path(FEATURES_KEY)
    features_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(features_path, index=False)

    embeddings_path = local_path(EMBEDDINGS_KEY)
    np.save(embeddings_path, embeddings)

    feature_ids_path = local_path(FEATURE_IDS_KEY)
    feature_ids_path.write_text(json.dumps(feature_ids), encoding="utf-8")

    upload_artifact(FEATURES_KEY)
    upload_artifact(EMBEDDINGS_KEY)
    upload_artifact(FEATURE_IDS_KEY)

    distinct_features = len(features)
    titan_cost_usd = titan_tokens * TITAN_USD_PER_MILLION_TOKENS / 1_000_000
    print(
        f"candidate_records={candidate_records} distinct_features={distinct_features} "
        f"titan_tokens={titan_tokens} titan_cost_usd={titan_cost_usd}"
    )


if __name__ == "__main__":
    main()
