"""Score baseline vs fine-tuned prediction CSVs into RESULTS.md.

Reuses metric helpers from the prior experiment and writes a modal-label
data description line.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py \\
      --preds-dir experiments/larger_finetune_qwen_model_2026_08_08/preds \\
      --write-results experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md
"""

from __future__ import annotations

import sys
from pathlib import Path

from experiments.finetune_qwen_model_2026_08_08.evaluate import (
    evaluate_preds_dir,
    parse_args,
    render_results_markdown,
)

DATA_DESCRIPTION = (
    "modal keep/remove labels, balanced 1:1 (all removes + equal keeps); "
    "seed=1; 80/20"
)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    preds_dir = Path(args.preds_dir)
    write_path = Path(args.write_results)
    train_metrics, test_metrics = evaluate_preds_dir(preds_dir)
    markdown = render_results_markdown(
        train_metrics,
        test_metrics,
        data_description=DATA_DESCRIPTION,
    )
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote {write_path}")
    print(markdown)


if __name__ == "__main__":
    main(sys.argv[1:])
