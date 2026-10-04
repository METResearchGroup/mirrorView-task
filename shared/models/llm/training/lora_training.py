"""LoRA SFT trainer for Hugging Face Jobs."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from lib.telemetry.wandb import start_run

# SFT LoRA from the TRL guide: every linear layer, rank 256, and a learning
# rate above the full fine-tuning default.
# LORA_RANK = 256
# LORA_ALPHA = 16
# LORA_TARGET_MODULES = "all-linear"
# LEARNING_RATE = 2e-4

# WANDB_GROUP = "trl_lora_training"
# RUN_NAME = f"{MODEL_NAME.rsplit('/', 1)[-1]}_lora_{get_current_timestamp()}"

# ARTIFACT_PREFIX = "cookbooks/fine_tuning_llms/trl_lora_training"
# OUTPUT_DIR = Path("/tmp") / RUN_NAME


# def artifact_s3_uri() -> str:
#     """Return the S3 prefix for this run's saved adapter."""
#     return f"s3://{DEFAULT_BUCKET}/{ARTIFACT_PREFIX}/{RUN_NAME}"


class LoraTrainer:

    def __init__(self, config: dict):
        self.lora_rank = config["lora"]["rank"]
        self.lora_alpha = config["lora"]["alpha"]
        self.lora_target_modules = config["lora"]["target_modules"]

        self.learning_rate = config["lr"]
        self.max_length = config["max_length"]
        self.model_name = config["model_name"]
        self.dataset_name = config["dataset_name"]
        self.output_dir = config["output_dir"]

        self.wandb_project = config["wandb"]["project"]
        self.wandb_group = config["wandb"]["group"]
        self.wandb_run_name = config["wandb"]["run_name"]
        # One A10G has 24 GB. The library batch of 8 does not fit at this
        # sequence length, so the step is one example and the effective batch
        # stays 8. 8-bit Adam keeps the optimizer state small.
        self.per_device_train_batch_size = int(config.get("per_device_train_batch_size", 1))
        self.gradient_accumulation_steps = int(config.get("gradient_accumulation_steps", 8))
        self.num_train_epochs = float(config.get("num_train_epochs", 3))
        self.artifact_s3_uri = config.get("artifact_s3_uri")

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
                "max_length": self.max_length,
                "lora_r": self.lora_rank,
                "lora_alpha": self.lora_alpha,
                "lora_target_modules": self.lora_target_modules,
            },
        ):

            self.training_args = SFTConfig(
                output_dir=str(self.output_dir),
                learning_rate=self.learning_rate,
                max_length=self.max_length,
                num_train_epochs=self.num_train_epochs,
                per_device_train_batch_size=self.per_device_train_batch_size,
                gradient_accumulation_steps=self.gradient_accumulation_steps,
                gradient_checkpointing=True,
                optim="adamw_8bit",
                bf16=True,
                save_strategy="no",
                report_to="wandb",
                run_name=self.wandb_run_name,
                logging_strategy="steps",
                logging_steps=10,
            )

            # The checkpoint's declared class is the vision-language model.
            # CausalLM loads the text backbone, which is what this text task trains.
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                dtype=torch.bfloat16,
            )
            self.trainer = SFTTrainer(
                model=model,
                processing_class=tokenizer,
                args=self.training_args,
                train_dataset=self.dataset,
                peft_config=self.peft_config,
            )
            self.trainer.model.print_trainable_parameters()

            self.trainer.train()
            self.trainer.save_model(self.output_dir)
            if self.artifact_s3_uri:
                upload_directory(self.output_dir, self.artifact_s3_uri, DEFAULT_REGION_NAME)


def upload_directory(local_dir: str, s3_uri: str, region: str) -> list[str]:
    """Upload every file under ``local_dir`` to ``s3_uri``.

    The job filesystem is removed when the job ends, so the adapter has to
    land in S3 before the process exits.
    """
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/").rstrip("/")
    root = Path(local_dir)
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise FileNotFoundError(f"No adapter files to upload in {local_dir}")
    store = S3(bucket, region_name=region)
    uploaded: list[str] = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        key = f"{prefix}/{relative}" if prefix else relative
        store.upload_file(path, key)
        uri = f"s3://{bucket}/{key}"
        print(f"Uploaded {uri}", flush=True)
        uploaded.append(uri)
    return uploaded
