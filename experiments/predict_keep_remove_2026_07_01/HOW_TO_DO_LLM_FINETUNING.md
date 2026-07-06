# How to do LLM fine-tuning

Here, we do a deeper dive on our approach for LLM fine-tuning.

This is a subset of the work done in `HOW_TO_TRAIN_LANGUAGE_MODELS.md`, more geared towards specific details and instructions.

I'm thinking we use two models:

- `mistral.ministral-3-8b-instruct`
- `mistral.ministral-3-14b-instruct`
- `Qwen/Qwen3-8B`
- `qwen.qwen3-32b-v1:0`

## High-level setup

The basic setup would be something like running a SageMaker training job with the proper configurations.

- Pulls the model from Hugging Face
- Reads train/test/validation datasets from S3
- Runs fine-tuning
- Streams metrics to Weights & Biases
- Saves LoRA adapter on the SageMaker instance and then uploads to S3.

We'll put this in `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/finetuning/`

### Tools

Let's use Sagemaker Training Jobs + HuggingFace. We'll track the experiments using Weights and Biases.

We'll use the following libraries

### Library 1: TRL

TRL: HuggingFace's post-training library. We'll be using `SFTTrainer`. For adapter training, it integrates with PEFT.

The TRL part can look something like this:

```python
from trl import SFTConfig, SFTTrainer

training_args = SFTConfig(
    output_dir=args.output_dir,
    num_train_epochs=3,
    max_seq_length=2048,
    report_to=["wandb"],
    ...
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    peft_config=peft_config,
    processing_class=tokenizer,
)

trainer.train()
```

TRL helps with the experimental scaffolding around fine-tuning, such as reading examples, applying chat/instruction formatting, tokenizing, loss, evaluation loop, and logging. TRL is also what's used to run PEFT on the models itself.

### Library 2: PEFT

PEFT ("Parameter-efficient fine tuning") is a library for adapting large pretrained models without having to fine-tune all model parameters. PEFT is the general library, while LoRA is one PEFT method.

For example, this might be how it looks:

```markdown
from peft import LoraConfig

peft_config = LoraConfig(
    r=16,
    lora_alpha=32, # 2 * r
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
)
```

For our task, let's include both attention and MLP modules as target modules for the LoRA.

We can first try LoRA, and then try QLoRA, to see what the difference in performance is.

### Ablations

Let's shuffle the LoRA ranks between 8, 16, 32, and 48. For the alpha, let's use 2 * rank

## Setup deep-dive

I'm thinking a setup of something like this:

```markdown
{base path}/finetuning/
  models/
    {qwen 8b, mistral, etc}/
      config.py
      runner.py
      outputs/
        {timestamp}/
          metrics.json
          outputs.csv
          metadata.json
        
  runner.py
  dataloader.py
  metrics.py
```

I'm thinking that we can do ablations and testing on one model, and then run on the rest. Let's start with Qwen 3 8b.

Ablations:

- Qwen 3 8b: baseline (done in Step 1).
- Qwen 3 8b: LoRA fine-tuning (across r=8, 16, 32, and 48).
- Qwen 3 8b: LoRA (bfloat16) vs. QLoRA (nf4).

Once we've got a set of optimal parameters, let's train the Mistral + Qwen models.

For SFT, we should mask the prompt tokens and compute loss only on the answer tokens.

Our next step is to explore explainability, especially with respect to the language models. However, that's out of scope of the current work and we'll be doing that in the next set of tasks.
