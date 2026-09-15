"""Tests for Hugging Face Jobs command construction."""

from __future__ import annotations

from experiments.reasoning_during_moderation_2026_09_15.shared.jobs import (
    hf_job_command,
    _remote_shell,
)

SCRIPT = "experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py"


class TestHfJobCommand:
    """Tests for hf_job_command and the remote shell."""

    def test_remote_shell_clones_branch_and_checks_out_commit(self) -> None:
        """Verifies the remote shell checks out the pinned commit on the branch."""
        shell = _remote_shell(
            "abc123",
            "cursor/implement-reasoning-moderation-fae5",
            SCRIPT,
            ["--smoke", "--limit", "3", "--model", "qwen"],
        )
        assert "--branch cursor/implement-reasoning-moderation-fae5" in shell
        assert "--single-branch" in shell
        assert "git checkout abc123" in shell
        assert "--smoke --limit 3 --model qwen" in shell
        assert "python3 -m pip install --quiet boto3 pandas pyarrow" in shell
        assert "import torch, vllm" in shell
        assert "torch==2.6.0+cu124" not in shell
        assert "causal-conv1d" not in shell
        assert "uv python install" not in shell

    def test_command_includes_detach_and_label(self) -> None:
        """Verifies detach and label flags land before the remote shell."""
        command = hf_job_command(
            SCRIPT,
            ["--model", "qwen"],
            label="exp1-qwen-smoke",
            detach=True,
            timeout="2h",
        )
        assert command[0] == "hf"
        assert "--detach" in command
        assert command[command.index("--timeout") + 1] == "2h"
        label_index = command.index("--label")
        assert command[label_index + 1] == "exp1-qwen-smoke"
        image_index = command.index("vllm/vllm-openai:v0.17.0")
        assert command.index("--detach") < image_index
        assert command[image_index + 1 : image_index + 3] == ["bash", "-c"]
        assert "-lc" not in command
        assert "--name" not in command
