"""Frozen run constants for Part 3 LoRA SageMaker jobs.

Run from root::

    PYTHONPATH=. uv run python -c \\
      "from experiments.finetune_lora_phase2_part3_2026_09_24.shared.run_config import MODEL_ID; print(MODEL_ID)"
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import Any

from experiments.finetune_qwen_model_2026_08_08.inference import (
    messages_for_generation,
)
from experiments.finetune_qwen_model_2026_08_08.src.train_config import (
    TrainHyperparams,
    default_hyperparams as prior_default_hyperparams,
)

MODEL_ID = "Qwen/Qwen3.5-4B"
CHAT_TEMPLATE_KWARGS: dict[str, bool] | None = {"enable_thinking": False}
S3_BUCKET = "mirrorview-experimental-artifacts"
S3_PREFIX = "experiments/finetune_lora_phase2_part3_2026_09_24"
ECR_REPO_NAME = "mirrorview-finetune-lora-phase2-part3"
WANDB_PROJECT = "mirrorview-finetune-lora-phase2-part3"
EXPERIMENT_EPOCHS: dict[str, int] = {
    "experiment1_unanimous": 3,
    "experiment2_modal": 1,
    "experiment3_modal_size_matched": 3,
}
RANDOM_SEED = 1
AWS_REGION = "us-east-2"
INSTANCE_TYPE = "ml.g5.xlarge"

EXPERIMENT_NAMES = tuple(EXPERIMENT_EPOCHS.keys()) + ("experiment4_cross_eval",)

_THINKING_BODY_PATTERN = re.compile(r"<think>\s*\S")


def default_hyperparams(experiment: str) -> TrainHyperparams:
    """Return Part 3 hyperparams derived from the August defaults.

    Parameters
    ----------
    experiment
        One of ``EXPERIMENT_NAMES`` with a train epoch override in
        ``EXPERIMENT_EPOCHS`` when training.

    Returns
    -------
    TrainHyperparams
        Frozen hyperparameter bundle with Part 3 model, seed, W&B, and epochs.
    """
    epochs = EXPERIMENT_EPOCHS.get(experiment)
    prior = prior_default_hyperparams()
    replacements: dict[str, object] = {
        "model_id": MODEL_ID,
        "seed": RANDOM_SEED,
        "wandb_project": WANDB_PROJECT,
    }
    if epochs is not None:
        replacements["num_train_epochs"] = epochs
    return replace(prior, **replacements)


def chat_template_kwargs_json() -> str:
    """Serialize chat-template kwargs for SageMaker environment.

    Returns
    -------
    str
        JSON object string, e.g. ``{"enable_thinking": false}``.
    """
    return json.dumps(CHAT_TEMPLATE_KWARGS or {})


def render_infer_prompt(
    tokenizer: Any,
    messages: list[dict[str, Any]],
    chat_template_kwargs: dict[str, Any] | None,
) -> str:
    """Render the inference prompt the same way ``inference.py`` does.

    Parameters
    ----------
    tokenizer
        Hugging Face tokenizer for ``MODEL_ID``.
    messages
        Full chat record including assistant gold turn.
    chat_template_kwargs
        Optional kwargs forwarded to ``apply_chat_template``; ``None`` keeps
        tokenizer defaults.

    Returns
    -------
    str
        Prompt text with generation prompt appended.
    """
    prompt_messages = messages_for_generation(messages)
    template_kwargs: dict[str, Any] = {}
    if chat_template_kwargs:
        template_kwargs["chat_template_kwargs"] = chat_template_kwargs
    return tokenizer.apply_chat_template(
        prompt_messages,
        tokenize=False,
        add_generation_prompt=True,
        **template_kwargs,
    )


def assert_no_thinking_body(prompt: str) -> None:
    """Reject prompts whose thinking block contains non-whitespace content.

    Parameters
    ----------
    prompt
        Rendered chat template text.

    Raises
    ------
    AssertionError
        When a ``<think>`` block contains visible thinking text.
    """
    assert _THINKING_BODY_PATTERN.search(prompt) is None
