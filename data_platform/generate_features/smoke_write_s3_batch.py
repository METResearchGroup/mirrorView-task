"""Temporary live smoke for the campaign batch writer under a disposable S3 prefix.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_write_s3_batch.py \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \\
        --preprocessed-run 2026_09_03-23:51:30 \\
        --feature is_news_or_opinion \\
        --smoke-prefix s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/ \\
        --row-count 10
"""

from __future__ import annotations

import typer


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    typer.run(main)
