"""Tests for Study 2 SageMaker eval launcher (no AWS calls)."""

from __future__ import annotations

from experiments.lora_finetuning_study2_2026_10_04.launch_sagemaker import (
    EXECUTION_ROLE_ARN,
    IMAGE_URI,
    INSTANCE_TYPE_DEFAULT,
    MAX_RUNTIME_SECONDS,
    VOLUME_SIZE_GB,
    build_create_training_job_request,
    build_eval_container_arguments,
    build_job_config,
)


class TestBuildJobConfig:
    def test_smoke_defaults(self):
        env = {
            "AWS_ACCESS_KEY_ID": "ak",
            "AWS_SECRET_ACCESS_KEY": "sk",
            "AWS_DEFAULT_REGION": "us-east-2",
            "PYTHONPATH": "/app",
            "HF_TOKEN": "hf",
        }
        config = build_job_config(environment=env)
        assert config.image_uri == IMAGE_URI
        assert config.role_arn == EXECUTION_ROLE_ARN
        assert config.instance_type == INSTANCE_TYPE_DEFAULT
        assert config.volume_size_gb == VOLUME_SIZE_GB
        assert config.max_runtime_seconds == MAX_RUNTIME_SECONDS
        assert config.enable_network_isolation is False
        assert config.container_entry_point == ["python3"]
        assert "--in-job" in config.container_arguments
        assert "--limit" in config.container_arguments
        assert config.container_arguments[-1] == "32"
        assert config.environment["PYTHONPATH"] == "/app"
        assert "HF_TOKEN" in config.environment

    def test_create_training_job_request_shape(self):
        config = build_job_config(
            environment={
                "AWS_ACCESS_KEY_ID": "ak",
                "AWS_SECRET_ACCESS_KEY": "sk",
                "AWS_DEFAULT_REGION": "us-east-2",
                "PYTHONPATH": "/app",
                "HF_TOKEN": "hf",
            }
        )
        req = build_create_training_job_request(config, "study2-vllm-eval-smoke-test")
        assert req["TrainingJobName"] == "study2-vllm-eval-smoke-test"
        assert req["RoleArn"] == EXECUTION_ROLE_ARN
        algo = req["AlgorithmSpecification"]
        assert algo["TrainingImage"] == IMAGE_URI
        assert algo["ContainerEntrypoint"] == ["python3"]
        assert algo["ContainerArguments"] == build_eval_container_arguments()
        assert req["ResourceConfig"]["VolumeSizeInGB"] == 120
        assert req["ResourceConfig"]["InstanceType"] == INSTANCE_TYPE_DEFAULT
        assert req["EnableNetworkIsolation"] is False
        assert req["StoppingCondition"]["MaxRuntimeInSeconds"] == 7200

    def test_full_run_omits_limit_and_uses_four_hour_cap(self):
        config = build_job_config(
            limit=None,
            max_runtime_seconds=14400,
            job_name_prefix="study2-vllm-eval-full",
            environment={
                "AWS_ACCESS_KEY_ID": "ak",
                "AWS_SECRET_ACCESS_KEY": "sk",
                "AWS_DEFAULT_REGION": "us-east-2",
                "PYTHONPATH": "/app",
                "HF_TOKEN": "hf",
            },
        )
        assert "--limit" not in config.container_arguments
        assert config.max_runtime_seconds == 14400
        assert config.job_name_prefix == "study2-vllm-eval-full"
