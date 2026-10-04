"""Training set for Study 2 keep/remove LoRA fine-tuning.

Loads one registered label table and converts every row into TRL's
conversational prompt-completion format. ``SFTTrainer`` then computes the
loss on the completion only. The returned dataset is the full table: there
is no train/eval split.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/dataloader.py
"""

from __future__ import annotations

import math

from datasets import Dataset

from shared.data.dataloader import load_dataset
from shared.data.registry import UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS
from shared.models.llm.prompt import STUDY_PROMPT_TEMPLATE, SYSTEM_CONTENT

_REQUIRED_COLUMNS = {"post_id", "original_text", "mirror_text", "decision"}
_DECISIONS = {"keep", "remove"}


def row_to_prompt_completion(row: dict) -> dict[str, list[dict[str, str]]]:
    """Map one label row to a conversational prompt and completion.

    The prompt is the Study 2 keep/remove instruction plus the original post
    and its mirror. The completion is the gold ``decision`` (``keep`` or
    ``remove``). TRL treats ``prompt`` and ``completion`` as the SFT fields
    and, by default, ignores prompt tokens in the loss.
    """
    decision = str(row["decision"]).lower().strip()
    if decision not in _DECISIONS:
        raise ValueError(
            f"Unexpected decision={decision!r} for post_id={row.get('post_id')!r}"
        )
    user_content = STUDY_PROMPT_TEMPLATE.format(
        ADD_KEEP_REMOVE_FEATURES_ADDENDUM="",
        post_1_text=_text(row["original_text"]),
        post_2_text=_text(row["mirror_text"]),
    )
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_CONTENT},
            {"role": "user", "content": user_content},
        ],
        "completion": [
            {"role": "assistant", "content": decision},
        ],
    }


def load_training_dataset(dataset_name: str) -> Dataset:
    """Return one registered label table in TRL SFT format."""
    frame = load_dataset(dataset_name)
    missing = _REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise KeyError(f"Dataset is missing required columns: {sorted(missing)}")
    records = [
        row_to_prompt_completion(row) for row in frame.to_dict(orient="records")
    ]
    return Dataset.from_list(records)


def _text(value: object) -> str:
    """Return ``value`` as text, using an empty string for missing cells."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value)


def main() -> None:
    """Load the training set and print its size."""
    dataset = load_training_dataset(UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS)
    print(f"train rows={len(dataset)} columns={dataset.column_names}")


if __name__ == "__main__":
    main()
