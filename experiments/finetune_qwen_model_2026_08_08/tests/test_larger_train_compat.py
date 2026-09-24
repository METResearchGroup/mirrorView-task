"""Regression tests for larger-finetune wrappers calling prior train helpers."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

from experiments.finetune_qwen_model_2026_08_08.train import run_training
from experiments.larger_finetune_qwen_model_2026_08_08.src.train_config import (
    default_hyperparams,
)


def test_run_training_accepts_omitted_chat_template_kwargs() -> None:
    """Larger Part 2 wrapper omits chat_template_kwargs; prior API must accept it."""
    signature = inspect.signature(run_training)
    assert signature.parameters["chat_template_kwargs"].default is None


def test_larger_train_main_calls_run_training_without_type_error(tmp_path: Path) -> None:
    """Larger train.py call style must bind run_training without starting training."""
    train_jsonl = tmp_path / "chat_train.jsonl"
    train_jsonl.write_text(
        '{"messages": [{"role": "user", "content": "hi"}]}\n',
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    with patch(
        "experiments.larger_finetune_qwen_model_2026_08_08.train.run_training"
    ) as mock_run_training:
        from experiments.larger_finetune_qwen_model_2026_08_08 import train as larger_train

        larger_train.main(
            [
                "--train-jsonl",
                str(train_jsonl),
                "--output-dir",
                str(output_dir),
            ]
        )

    mock_run_training.assert_called_once_with(
        train_jsonl=train_jsonl,
        output_dir=output_dir,
        hyperparams=default_hyperparams(),
        max_steps=None,
        chat_template_kwargs=None,
    )
