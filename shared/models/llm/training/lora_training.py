"""LoRA SFT trainer for Hugging Face Jobs."""

from datasets import Dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer

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
            # upload_directory(
            #     OUTPUT_DIR,
            #     artifact_s3_uri(),
            #     region=DEFAULT_REGION_NAME,
            # )
