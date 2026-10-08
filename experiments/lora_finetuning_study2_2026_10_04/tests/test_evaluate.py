"""CPU unit tests for Study 2 vLLM eval helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import torch
from safetensors.torch import load_file, save_file

from experiments.lora_finetuning_study2_2026_10_04 import evaluate as evaluate_mod
from experiments.lora_finetuning_study2_2026_10_04.constants import LORA_TARGET_MODULES


def test_rewrite_adapter_key_for_vllm_flattens_peft_default() -> None:
    key = (
        "base_model.model.model.language_model.layers.0.self_attn.q_proj"
        ".lora_A.default.weight"
    )
    assert evaluate_mod.rewrite_adapter_key_for_vllm(key).endswith(".lora_A.weight")
    assert "language_model" in evaluate_mod.rewrite_adapter_key_for_vllm(key)


def test_rewrite_adapter_key_for_vllm_keeps_flat_keys() -> None:
    key = (
        "base_model.model.model.language_model.layers.0.linear_attn.in_proj_qkv"
        ".lora_A.weight"
    )
    assert evaluate_mod.rewrite_adapter_key_for_vllm(key) == key


def test_prompt_truncation_leaves_room_for_completion() -> None:
    kwargs = evaluate_mod.prompt_truncation_kwargs()
    limit = evaluate_mod.MAX_LENGTH - evaluate_mod.MAX_NEW_TOKENS
    assert kwargs["truncate_prompt_tokens"] == limit
    assert kwargs["truncation_side"] == "left"


def test_chat_template_kwargs_disable_thinking() -> None:
    assert evaluate_mod.CHAT_TEMPLATE_KWARGS == {"enable_thinking": False}


def test_eval_job_config_uses_l4_and_eight_hour_timeout() -> None:
    with patch.object(
        evaluate_mod.EnvVarsContainer,
        "get_env_var",
        side_effect=lambda name, required=False: f"secret-{name}",
    ):
        config = evaluate_mod.eval_job_config("unanimous", "run-a", limit=32)
    assert config.flavor == "l4x1"
    assert config.timeout == "8h"
    assert "WANDB_API_KEY" not in config.secrets
    assert config.command[-2:] == ("--limit", "32")
    assert "--in-job" in config.command


def test_eval_job_command_omits_limit_by_default() -> None:
    command = evaluate_mod.eval_job_command("split", "run-b")
    assert "--limit" not in command
    assert command == (
        *evaluate_mod.EVAL_COMMAND,
        "--ablation",
        "split",
        "--run-name",
        "run-b",
        "--in-job",
    )


def test_rewrite_adapter_for_vllm_rewrites_and_requires_targets(tmp_path: Path) -> None:
    src = tmp_path / "raw"
    dest = tmp_path / "vllm"
    src.mkdir()
    (src / "adapter_config.json").write_text("{}", encoding="utf-8")
    tensors = {
        (
            f"base_model.model.model.language_model.layers.0.mod.{target}"
            f".lora_A.default.weight"
        ): torch.zeros((2, 2))
        for target in LORA_TARGET_MODULES
    }
    tensors.update(
        {
            (
                f"base_model.model.model.language_model.layers.0.mod.{target}"
                f".lora_B.default.weight"
            ): torch.zeros((2, 2))
            for target in LORA_TARGET_MODULES
        }
    )
    save_file(tensors, src / "adapter_model.safetensors")

    evaluate_mod.rewrite_adapter_for_vllm(src, dest)
    rewritten = load_file(dest / "adapter_model.safetensors")
    assert any(key.endswith(".lora_A.weight") for key in rewritten)
    assert not any(".default.weight" in key for key in rewritten)
    assert (dest / "adapter_config.json").is_file()


def test_rewrite_adapter_for_vllm_fails_when_target_missing(tmp_path: Path) -> None:
    src = tmp_path / "raw"
    dest = tmp_path / "vllm"
    src.mkdir()
    save_file(
        {
            "base_model.model.model.language_model.layers.0.self_attn.q_proj"
            ".lora_A.weight": torch.zeros((2, 2)),
            "base_model.model.model.language_model.layers.0.self_attn.q_proj"
            ".lora_B.weight": torch.zeros((2, 2)),
        },
        src / "adapter_model.safetensors",
    )
    with pytest.raises(RuntimeError, match="missing trained LoRA targets"):
        evaluate_mod.rewrite_adapter_for_vllm(src, dest)


def test_parse_generation_and_metrics() -> None:
    assert evaluate_mod.parse_generation("keep\n") == "keep"
    assert evaluate_mod.parse_generation("<think>\n") is None
    metrics = evaluate_mod.compute_classification_metrics(
        ["keep", "remove"],
        ["keep", None],
    )
    assert metrics["n"] == 2
    assert metrics["n_invalid"] == 1


def test_build_parser_accepts_limit_and_flavor() -> None:
    args = evaluate_mod.build_parser().parse_args(
        ["--ablation", "unanimous", "--limit", "32", "--flavor", "a100-large"]
    )
    assert args.limit == 32
    assert args.flavor == "a100-large"


def test_docker_build_eval_command_points_at_dockerfile_eval() -> None:
    command = evaluate_mod.docker_build_eval_command("example/eval:latest")
    assert command[command.index("-f") + 1].endswith("Dockerfile.eval")
