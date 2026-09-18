"""Tests for generation_seed(), chunking, and vLLM sampling kwargs."""

from __future__ import annotations

from types import SimpleNamespace

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    INFERENCE_ENGINE,
    QWEN_MIN_P,
    QWEN_MODEL_ID,
    QWEN_PRESENCE_PENALTY,
    QWEN_REPETITION_PENALTY,
    QWEN_TEMPERATURE,
    QWEN_TOP_K,
    QWEN_TOP_P,
    ROLE_MIRROR,
    ROLE_ORIGINAL,
    SamplingConfig,
    STATUS_VALID,
    UINT32_MODULUS,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.runner import (
    chunk_posts,
    complete_posts,
    generation_seed,
    sampling_kwargs_for_vllm,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.tests.test_count_thinking_tokens import (
    CLOSE_ID,
    OPEN_ID,
    FakeTokenizer,
)

INNER_ID = 11


class ChatTokenizer(FakeTokenizer):
    """Fake tokenizer that also renders a chat string and decodes ids."""

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        tokenize: bool = False,
        add_generation_prompt: bool = True,
        enable_thinking: bool = False,
    ) -> str:
        return f"chat:{messages[0]['content']}:think={enable_thinking}"

    def decode(self, ids: list[int], skip_special_tokens: bool = False) -> str:
        return "<think>hello</think>Allow"


class FakeOutput:
    """One vLLM-style completion."""

    def __init__(self, token_ids: list[int]) -> None:
        self.outputs = [SimpleNamespace(token_ids=token_ids)]


class FakeLLM:
    """Records generate() prompts and returns tagged token ids."""

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.params: list[object] = []

    def generate(self, prompts: list[str], params: list[object]) -> list[FakeOutput]:
        self.prompts = list(prompts)
        self.params = list(params)
        return [FakeOutput([OPEN_ID, INNER_ID, CLOSE_ID]) for _ in prompts]


class TestGenerationSeed:
    """Tests for generation_seed function."""

    def test_same_post_is_stable_uint32(self) -> None:
        """Verifies two calls match and the seed fits in 32 bits."""
        first = generation_seed("A")
        second = generation_seed("A")

        assert first == second
        assert 0 <= first < UINT32_MODULUS


class TestSamplingKwargsForVllm:
    """Tests for vLLM sampling kwargs."""

    def test_keeps_qwen_presence_penalty(self) -> None:
        """Verifies Qwen presence_penalty is passed through to vLLM."""
        sampling = SamplingConfig(
            QWEN_TEMPERATURE,
            QWEN_TOP_P,
            QWEN_TOP_K,
            QWEN_MIN_P,
            QWEN_PRESENCE_PENALTY,
            QWEN_REPETITION_PENALTY,
        )
        kwargs = sampling_kwargs_for_vllm(sampling)
        assert kwargs["presence_penalty"] == QWEN_PRESENCE_PENALTY
        assert kwargs["temperature"] == QWEN_TEMPERATURE
        assert kwargs["top_k"] == QWEN_TOP_K
        assert kwargs["min_p"] == QWEN_MIN_P
        assert kwargs["repetition_penalty"] == QWEN_REPETITION_PENALTY


class TestChunkPosts:
    """Tests for chunk_posts."""

    def test_splits_into_contiguous_chunks(self) -> None:
        """Verifies a leftover tail stays in the last chunk."""
        posts = [{"post_id": str(index)} for index in range(5)]
        chunks = chunk_posts(posts, 2)
        assert len(chunks) == 3
        assert [post["post_id"] for post in chunks[-1]] == ["4"]


class TestCompletePosts:
    """Tests for complete_posts with a fake engine."""

    def test_batches_and_counts_thinking_tokens(self, monkeypatch: object) -> None:
        """Verifies one generate call yields a valid think-span count."""
        from experiments.reasoning_during_moderation_2026_09_15.shared import runner

        monkeypatch.setattr(runner, "_sampling_params", lambda *args, **kwargs: object())
        llm = FakeLLM()
        post = {
            "post_id": "p1",
            "group": "split",
            "original_text": "original",
            "mirror_text": "mirror",
            "post_1_role": ROLE_ORIGINAL,
            "post_2_role": ROLE_MIRROR,
        }
        records = complete_posts(
            [post], QWEN_MODEL_ID, False, 8, ChatTokenizer(), llm
        )
        assert len(records) == 1
        assert records[0].status == STATUS_VALID
        assert records[0].thinking_token_count == 1
        assert records[0].inference_engine == INFERENCE_ENGINE
        assert len(llm.prompts) == 1
        assert "think=True" in llm.prompts[0]
