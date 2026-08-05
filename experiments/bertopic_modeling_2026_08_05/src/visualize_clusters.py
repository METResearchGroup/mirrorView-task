"""Stage 4: three cluster-map overlays from a shared 2-D UMAP projection.

Implemented in Step 5 of the experiment plan.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py \\
      --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>
"""

from __future__ import annotations


def run_visualize_clusters() -> None:
    """Emit Plotly HTML + PNG overlays for topic / keep-remove / unanimous."""
    raise NotImplementedError("Implemented in Step 5")


def main() -> None:
    """CLI entrypoint."""
    run_visualize_clusters()


if __name__ == "__main__":
    main()
