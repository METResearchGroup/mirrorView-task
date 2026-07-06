"""Embedding-derived feature builders for classical ML ablations."""

from experiments.predict_keep_remove_2026_07_01.embeddings.features.concat_cosine import (
    ConcatCosineFeatureBuilder,
    build_xy_from_joined as build_xy_concat_cosine,
)
from experiments.predict_keep_remove_2026_07_01.embeddings.features.difference import (
    DifferenceEmbeddingFeatureBuilder,
    build_xy_from_joined as build_xy_difference_embedding,
)
from experiments.predict_keep_remove_2026_07_01.embeddings.features.only_original import (
    OnlyOriginalEmbeddingFeatureBuilder,
    build_xy_from_joined as build_xy_only_original_embedding,
)

__all__ = [
    "ConcatCosineFeatureBuilder",
    "DifferenceEmbeddingFeatureBuilder",
    "OnlyOriginalEmbeddingFeatureBuilder",
    "build_xy_concat_cosine",
    "build_xy_difference_embedding",
    "build_xy_only_original_embedding",
]
