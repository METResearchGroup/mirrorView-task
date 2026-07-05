"""Single-text inference from a saved ModernBERT run directory.

Run from root::

    PYTHONPATH=. uv run --extra modernbert-training python \\
      experiments/predict_keep_remove_2026_07_01/models/modernbert/predict.py \\
      --run-dir experiments/predict_keep_remove_2026_07_01/models/modernbert/artifacts/modernbert-base/<timestamp> \\
      --text "example political post"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

DEFAULT_THRESHOLD = 0.5


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict keep/remove for a single original-text post."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Training run directory with saved model and tokenizer.",
    )
    parser.add_argument(
        "--text",
        required=True,
        help="Original post text to classify.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Decision threshold on remove probability (default 0.5).",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=256,
        help="Tokenizer max length.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run dir not found: {run_dir}")

    tokenizer = AutoTokenizer.from_pretrained(run_dir)
    model = AutoModelForSequenceClassification.from_pretrained(run_dir)
    model.eval()

    encoded = tokenizer(
        args.text,
        truncation=True,
        padding="max_length",
        max_length=int(args.max_length),
        return_tensors="pt",
    )
    with torch.no_grad():
        logits = model(**encoded).logits
        proba = torch.softmax(logits, dim=-1)[0, 1].item()

    predicted_label = int(proba >= float(args.threshold))
    payload = {
        "predicted_label": predicted_label,
        "predicted_remove_probability": float(proba),
    }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
