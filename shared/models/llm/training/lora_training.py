"""LoRA SFT trainer for Hugging Face Jobs."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from datasets import Dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer

from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from lib.telemetry.wandb import start_run


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Split ``s3://bucket/prefix`` into bucket and key prefix."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"Invalid S3 URI: {uri}")
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/").rstrip("/")
    return bucket, prefix


def upload_adapter_directory(local_dir: Path, adapter_s3_uri: str) -> None:
    """Upload every file under ``local_dir`` to ``adapter_s3_uri``.

    Relative paths under ``local_dir`` are preserved under the URI prefix.
    """
    bucket, prefix = parse_s3_uri(adapter_s3_uri)
    s3 = S3(bucket, region_name=DEFAULT_REGION_NAME)
    root = Path(local_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Adapter output directory not found: {root}")

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        key = f"{prefix}/{relative}" if prefix else relative
        s3.upload_file(path, key)

    print(adapter_s3_uri)


class LoraTrainer:

    def __init__(self, config: dict):
        self.lora_rank = config["lora"]["rank"]
        self.lora_alpha = config["lora"]["alpha"]
        self.lora_target_modules = config["lora"]["target_modules"]

        self.learning_rate = config["lr"]
        self.num_train_epochs = config["epochs"]
        self.max_length = config["max_length"]
        self.model_name = config["model_name"]
        self.dataset_name = config["dataset_name"]
        self.output_dir = config["output_dir"]

        self.wandb_project = config["wandb"]["project"]
        self.wandb_group = config["wandb"]["group"]
        self.wandb_run_name = config["wandb"]["run_name"]

        adapter_s3_uri = config.get("adapter_s3_uri")
        if not adapter_s3_uri:
            raise ValueError("adapter_s3_uri is required")
        self.adapter_s3_uri = adapter_s3_uri

        self.peft_config = LoraConfig(
            r=self.lora_rank,
            lora_alpha=self.lora_alpha,
            target_modules=self.lora_target_modules,
        )

    def load_dataset(self, dataset: Dataset) -> None:
        """Store the full training set.

        ``dataset`` is a Hugging Face ``Dataset`` in TRL prompt-completion
        form. This trainer does not hold an eval split.
        """
        self.dataset = dataset

    def run(self) -> None:
        with start_run(
            self.wandb_project,
            self.wandb_group,
            self.wandb_run_name,
            config={
                "model": self.model_name,
                "dataset": self.dataset_name,
                "learning_rate": self.learning_rate,
                "num_train_epochs": self.num_train_epochs,
                "max_length": self.max_length,
                "lora_r": self.lora_rank,
                "lora_alpha": self.lora_alpha,
                "lora_target_modules": self.lora_target_modules,
            },
        ):

            self.training_args = SFTConfig(
                output_dir=str(self.output_dir),
                learning_rate=self.learning_rate,
                num_train_epochs=self.num_train_epochs,
                max_length=self.max_length,
                bf16=True,
                save_strategy="no",
                report_to="wandb",
                run_name=self.wandb_run_name,
                logging_strategy="steps",
                logging_steps=10,
            )

            self.trainer = SFTTrainer(
                model=self.model_name,
                args=self.training_args,
                train_dataset=self.dataset,
                peft_config=self.peft_config,
            )

            self.trainer.train()
            self.trainer.save_model(self.output_dir)
            upload_adapter_directory(Path(self.output_dir), self.adapter_s3_uri)
