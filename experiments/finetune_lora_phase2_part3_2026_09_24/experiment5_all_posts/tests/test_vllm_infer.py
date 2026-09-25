"""Unit tests for experiment5 prompt rendering and resume logic."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.constants import (
    CHAT_TEMPLATE_KWARGS,
    PRED_COLUMNS,
)
from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.vllm_infer import (
    PromptRecord,
    records_pending_resume,
    render_prompts,
    rows_from_generations,
    run_chunked_inference,
)
from experiments.finetune_qwen_model_2026_08_08.inference import messages_for_generation
from experiments.finetune_qwen_model_2026_08_08.train import _bind_chat_template_kwargs


def _sample_messages() -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "user text"},
        {"role": "assistant", "content": "keep"},
    ]


class _FakeTokenizer:
    """Minimal tokenizer that records apply_chat_template kwargs."""

    def __init__(self) -> None:
        self.last_kwargs: dict[str, Any] = {}

    def apply_chat_template(self, messages, *args, **kwargs):
        self.last_kwargs = dict(kwargs)
        return f"PROMPT:{len(messages)}"


class TestPromptRendering:
    """Prompt construction without downloading model weights."""

    def test_messages_for_generation_drops_assistant(self) -> None:
        trimmed = messages_for_generation(_sample_messages())
        roles = {m["role"] for m in trimmed}
        assert roles == {"system", "user"}

    def test_chat_template_kwargs_disable_thinking(self) -> None:
        assert CHAT_TEMPLATE_KWARGS["enable_thinking"] is False

    def test_bind_chat_template_forwards_enable_thinking(self) -> None:
        tokenizer = _FakeTokenizer()
        bound = _bind_chat_template_kwargs(tokenizer, CHAT_TEMPLATE_KWARGS)
        bound.apply_chat_template(
            _sample_messages()[:2],
            tokenize=False,
            add_generation_prompt=True,
        )
        assert tokenizer.last_kwargs["enable_thinking"] is False

    def test_render_prompts_uses_generation_roles_only(self) -> None:
        tokenizer = _FakeTokenizer()
        records = [{"message_id": "m1", "messages": _sample_messages()}]
        rendered = render_prompts(records, tokenizer)
        assert len(rendered) == 1
        assert rendered[0].prompt_text == "PROMPT:2"
        assert rendered[0].gold_decision == "keep"
        assert rendered[0].gold_label == 0


class TestRowsAndResume:
    """CSV row building and resume skipping."""

    def test_rows_from_generations_parses_keep(self) -> None:
        prompts = [
            PromptRecord("a", "keep", 0, "p"),
        ]
        rows = rows_from_generations(prompts, ["keep extra"])
        assert rows[0]["predicted_decision"] == "keep"
        assert rows[0]["predicted_label"] == 0

    def test_resume_skips_existing_message_ids(
        self,
        tmp_path: Path,
    ) -> None:
        output_csv = tmp_path / "out.csv"
        with output_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(PRED_COLUMNS))
            writer.writeheader()
            writer.writerow({col: "" for col in PRED_COLUMNS} | {"message_id": "done"})

        records = [
            {"message_id": "done", "messages": _sample_messages()},
            {"message_id": "pending", "messages": _sample_messages()},
        ]
        pending = records_pending_resume(records, output_csv)
        assert [r["message_id"] for r in pending] == ["pending"]

        tokenizer = _FakeTokenizer()
        prompts = render_prompts(pending, tokenizer)

        def fake_generate(texts: list[str]) -> list[str]:
            assert texts == ["PROMPT:2"]
            return ["remove"]

        written = run_chunked_inference(
            prompts,
            output_csv,
            generate_fn=fake_generate,
            chunk_size=32,
        )
        assert written == 1
        with output_csv.open(encoding="utf-8") as handle:
            lines = handle.readlines()
        assert len(lines) == 3
