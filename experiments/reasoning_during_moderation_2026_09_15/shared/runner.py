"""Run thinking-mode completions for the reasoning-during-moderation experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DEEPSEEK_MODEL_ID,
    DEEPSEEK_TEMPERATURE,
    DEEPSEEK_TOP_P,
    GENERATION_SEED_BYTES,
    INFERENCE_ENGINE,
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
    VLLM_GPU_MEMORY_UTILIZATION,
    VLLM_MAX_MODEL_LEN,
    VLLM_MAX_NUM_SEQS,
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
    inference_engine: str = INFERENCE_ENGINE


def generation_seed(post_id: str) -> int:
    """Return a stable 32-bit seed from a post id."""
    digest = hashlib.sha256(f"gen:{post_id}".encode()).digest()
    return int.from_bytes(digest[:GENERATION_SEED_BYTES], "big") % UINT32_MODULUS


def chunk_posts(
    posts: Sequence[dict[str, object]], chunk_size: int
) -> list[list[dict[str, object]]]:
    """Split posts into contiguous chunks of ``chunk_size``."""
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    return [list(posts[start : start + chunk_size]) for start in range(0, len(posts), chunk_size)]


def sampling_kwargs_for_vllm(sampling: SamplingConfig) -> dict[str, float | int]:
    """Return SamplingParams kwargs, including presence_penalty when set."""
    kwargs: dict[str, float | int] = {
        "temperature": sampling.temperature,
        "top_p": sampling.top_p,
        "presence_penalty": sampling.presence_penalty if sampling.presence_penalty is not None else 0.0,
        "repetition_penalty": sampling.repetition_penalty if sampling.repetition_penalty is not None else 1.0,
    }
    if sampling.top_k is not None:
        kwargs["top_k"] = sampling.top_k
    if sampling.min_p is not None:
        kwargs["min_p"] = sampling.min_p
    return kwargs


def complete_post(
    post: dict[str, object],
    model_id: str,
    add_criteria: bool,
    max_new_tokens: int,
    tokenizer: object,
    llm: object,
) -> TraceRecord:
    """Generate one thinking-mode completion and count thinking tokens."""
    return complete_posts(
        [post], model_id, add_criteria, max_new_tokens, tokenizer, llm
    )[0]


def complete_posts(
    posts: Sequence[dict[str, object]],
    model_id: str,
    add_criteria: bool,
    max_new_tokens: int,
    tokenizer: object,
    llm: object,
) -> list[TraceRecord]:
    """Generate thinking-mode completions for one vLLM batch."""
    sampling = SAMPLING_BY_MODEL[model_id]
    prompts: list[str] = []
    params: list[object] = []
    seeds: list[int] = []
    for post in posts:
        prompt = render_prompt(
            str(post["original_text"]),
            str(post["mirror_text"]),
            str(post["post_1_role"]),
            add_criteria,
        )
        seed = generation_seed(str(post["post_id"]))
        prompts.append(_chat_prompt(tokenizer, prompt, model_id))
        params.append(_sampling_params(sampling, seed, max_new_tokens))
        seeds.append(seed)
    outputs = llm.generate(prompts, params)
    records: list[TraceRecord] = []
    for post, seed, output in zip(posts, seeds, outputs, strict=True):
        generated_ids = list(output.outputs[0].token_ids)
        records.append(
            _trace_from_generation(
                post, model_id, add_criteria, seed, generated_ids, tokenizer, max_new_tokens
            )
        )
    return records


def _sampling_params(
    sampling: SamplingConfig, seed: int, max_new_tokens: int
) -> object:
    from vllm import SamplingParams

    return SamplingParams(
        max_tokens=max_new_tokens,
        seed=seed,
        **sampling_kwargs_for_vllm(sampling),
    )


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


def load_engine(model_id: str) -> tuple[object, object]:
    """Load a vLLM engine and its tokenizer on GPU."""
    import torch
    from vllm import LLM

    if not torch.cuda.is_available():
        raise RuntimeError("GPU required; use hf_job_command from jobs.py")
    kwargs: dict[str, object] = {
        "model": model_id,
        "dtype": "bfloat16",
        "max_model_len": VLLM_MAX_MODEL_LEN,
        "gpu_memory_utilization": VLLM_GPU_MEMORY_UTILIZATION,
        "enable_prefix_caching": True,
        "max_num_seqs": VLLM_MAX_NUM_SEQS,
        "trust_remote_code": True,
    }
    if model_id == QWEN_MODEL_ID:
        kwargs["language_model_only"] = True
    try:
        llm = LLM(**kwargs)
    except TypeError:
        kwargs.pop("language_model_only", None)
        llm = LLM(**kwargs)
    return llm.get_tokenizer(), llm


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


def _thinking_text(decoded: str) -> str:
    if THINK_CLOSE_TAG not in decoded:
        return ""
    before_close, _unused = decoded.split(THINK_CLOSE_TAG, 1)
    if THINK_OPEN_TAG in before_close:
        return before_close.split(THINK_OPEN_TAG, 1)[1]
    return before_close
