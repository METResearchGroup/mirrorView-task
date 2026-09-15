"""Run thinking-mode completions for the reasoning-during-moderation experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DEEPSEEK_MODEL_ID,
    DEEPSEEK_TEMPERATURE,
    DEEPSEEK_TOP_P,
    GENERATION_SEED_BYTES,
    PROMPT_ARM_CRITERIA,
    PROMPT_ARM_STUDY,
    QWEN_MIN_P,
    QWEN_MODEL_ID,
    QWEN_PRESENCE_PENALTY,
    QWEN_REPETITION_PENALTY,
    QWEN_TEMPERATURE,
    QWEN_TOP_K,
    QWEN_TOP_P,
    SamplingConfig,
    THINK_CLOSE_TAG,
    THINK_OPEN_SUFFIX,
    THINK_OPEN_TAG,
    UINT32_MODULUS,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.prompt import (
    render_prompt,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.thinking import (
    count_thinking_tokens,
)

SAMPLING_BY_MODEL = {
    QWEN_MODEL_ID: SamplingConfig(
        QWEN_TEMPERATURE,
        QWEN_TOP_P,
        QWEN_TOP_K,
        QWEN_MIN_P,
        QWEN_PRESENCE_PENALTY,
        QWEN_REPETITION_PENALTY,
    ),
    DEEPSEEK_MODEL_ID: SamplingConfig(
        DEEPSEEK_TEMPERATURE,
        DEEPSEEK_TOP_P,
        None,
        None,
        None,
        None,
    ),
}


@dataclass(frozen=True)
class TraceRecord:
    """One stored completion for a post and model."""

    post_id: str
    group: str
    model_id: str
    prompt_arm: str
    post_1_role: str
    post_2_role: str
    generation_seed: int
    status: str
    thinking_token_count: int
    thinking_text: str
    completion_text: str
    max_new_tokens: int


def generation_seed(post_id: str) -> int:
    """Return a stable 32-bit seed from a post id."""
    digest = hashlib.sha256(f"gen:{post_id}".encode()).digest()
    return int.from_bytes(digest[:GENERATION_SEED_BYTES], "big") % UINT32_MODULUS


def complete_post(
    post: dict[str, object],
    model_id: str,
    add_criteria: bool,
    max_new_tokens: int,
    tokenizer: object,
    model: object,
) -> TraceRecord:
    """Generate one thinking-mode completion and count thinking tokens."""
    prompt = render_prompt(
        str(post["original_text"]),
        str(post["mirror_text"]),
        str(post["post_1_role"]),
        add_criteria,
    )
    seed = generation_seed(str(post["post_id"]))
    generated_ids = _generate_ids(
        prompt, model_id, tokenizer, model, seed, max_new_tokens
    )
    return _trace_from_generation(post, model_id, add_criteria, seed, generated_ids, tokenizer, max_new_tokens)


def _trace_from_generation(
    post: dict[str, object],
    model_id: str,
    add_criteria: bool,
    seed: int,
    generated_ids: list[int],
    tokenizer: object,
    max_new_tokens: int,
) -> TraceRecord:
    counted = count_thinking_tokens(generated_ids, tokenizer, max_new_tokens)
    decoded = tokenizer.decode(generated_ids, skip_special_tokens=False)
    arm = PROMPT_ARM_CRITERIA if add_criteria else PROMPT_ARM_STUDY
    return TraceRecord(
        str(post["post_id"]), str(post["group"]), model_id, arm,
        str(post["post_1_role"]), str(post["post_2_role"]), seed,
        counted.status, counted.thinking_token_count,
        _thinking_text(decoded), decoded, max_new_tokens,
    )


def trace_to_dict(record: TraceRecord) -> dict[str, object]:
    """Return a json-serializable trace row."""
    return asdict(record)


def _generate_ids(
    prompt: str,
    model_id: str,
    tokenizer: object,
    model: object,
    seed: int,
    max_new_tokens: int,
) -> list[int]:
    import torch

    inputs = _prompt_inputs(tokenizer, prompt, model_id, model)
    sampling = _sampling_kwargs(SAMPLING_BY_MODEL[model_id], model.generation_config)
    pad_token_id = tokenizer.eos_token_id
    with torch.random.fork_rng():
        torch.manual_seed(seed)
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            pad_token_id=pad_token_id,
            **sampling,
        )
    return output[0][inputs["input_ids"].shape[-1]:].tolist()


def _prompt_inputs(
    tokenizer: object, prompt: str, model_id: str, model: object
) -> dict[str, object]:
    chat = _chat_prompt(tokenizer, prompt, model_id)
    inputs = tokenizer(chat, return_tensors="pt")
    return {key: value.to(model.device) for key, value in inputs.items()}


def _chat_prompt(tokenizer: object, prompt: str, model_id: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    if model_id == QWEN_MODEL_ID:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True,
        )
        return str(text)
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return _force_deepseek_think(str(text))


def _force_deepseek_think(text: str) -> str:
    if text.endswith(THINK_OPEN_TAG) or text.endswith(THINK_OPEN_SUFFIX):
        return text
    return text + THINK_OPEN_SUFFIX


def _sampling_kwargs(
    sampling: SamplingConfig, generation_config: object
) -> dict[str, float | int]:
    kwargs: dict[str, float | int] = {
        "temperature": sampling.temperature,
        "top_p": sampling.top_p,
    }
    if sampling.top_k is not None:
        kwargs["top_k"] = sampling.top_k
    if sampling.min_p is not None:
        kwargs["min_p"] = sampling.min_p
    if sampling.presence_penalty is not None:
        kwargs["presence_penalty"] = sampling.presence_penalty
    if sampling.repetition_penalty is not None:
        kwargs["repetition_penalty"] = sampling.repetition_penalty
    return {
        key: value
        for key, value in kwargs.items()
        if hasattr(generation_config, key)
    }


def _thinking_text(decoded: str) -> str:
    if THINK_CLOSE_TAG not in decoded:
        return ""
    before_close, _unused = decoded.split(THINK_CLOSE_TAG, 1)
    if THINK_OPEN_TAG in before_close:
        return before_close.split(THINK_OPEN_TAG, 1)[1]
    return before_close
