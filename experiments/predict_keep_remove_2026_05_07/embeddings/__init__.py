"""Precompute and join OpenAI text embeddings for keep/remove modeling."""

from experiments.predict_keep_remove_2026_05_07.embeddings.join import (
    join_embeddings_to_dataframe,
)
from experiments.predict_keep_remove_2026_05_07.embeddings.instances import (
    build_text_instances_table,
)

__all__ = [
    "build_text_instances_table",
    "join_embeddings_to_dataframe",
]
