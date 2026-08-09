# Fine-tune a Qwen model

We want to fine-tune a Qwen model (using LoRA).

For our fine-tuning, we'll start with the highest-quality data we have, so we intentionally filter our dataset to just the posts that have both at least 3 raters and also have unanimous labels.

From our latest Phase 2, Part 2, this resulted in 1,644 total posts, of which 1,490 were keep and 154 were remove. Given the sheer class imbalance and the fact that we actually want to prioritize the remove class, we'll do a 1:1 split between keeps and removes, making our training dataset n=308.

For our baseline, we'll use the same prompt as in [our prompt engineering experiment](../llm_prompt_engineering_v2_2026_08_05/). We found that using a rubric-based approach improved performance.

We'll use a smaller model this time. We'll train using LoRA. We'll be using the standard chat dataset format:

```python
{"messages":[
  {"role":"system","content":"You are a concise data assistant."},
  {"role":"user","content":"Write SQL to count active users by day."},
  {"role":"assistant","content":"SELECT DATE(created_at) AS day, COUNT(*) AS active_users\nFROM users\nWHERE active = TRUE\nGROUP BY 1\nORDER BY 1;"}
]}
```

For our model we'll use `MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"`.

Steps:

1. Filter the data from `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` in `shared/registry.py` and create a subset that has all the remove posts and an equal number of keep posts. Let's do a 80:20 split, but make sure that both the train and test sets have equal numbers of keep and remove posts, and keep the results in `data/{train,test}.csv`. Let's use `seed=1` as our random seed.
2. Create a chat dataset. We do this in `src/create_chat_dataset.py` and it creates a file `data/chat_dataset.jsonl`. We use the prompt-engineered prompt (as in, with the rubric criteria) that we used in [this past experiment](../llm_prompt_engineering_v2_2026_08_05/).
3. We'll have a training script, `train.py`. This trains the LoRA adapter. Let's use the default settings as well as a conservative rank (`r=16`) given how few samples we actually will use. Let's also use quantization (`bf16`).
4. We'll have an inference script, `inference.py`, that runs inference and generates labels. It should optionally either use the default model or the model + LoRA adapter.
5. We run twice, once for the default model and once for the model + adapter. We record the training and test set labels, in `preds/{baseline,fine_tuned}/{train,test}_labels.csv`.
6. Then we report two tables, the train table (two rows: baseline and fine-tuned, and scores accuracy, precision, recall, and F1) and test table (same setup). We report these in a RESULTS.md file.

For training, we use AWS Sagemaker. We package everything up in a Docker container that is run in AWS Sagemaker.

For AWS, we'll use the following:

- region: us-east-2
- ECR repo: mirrorview-finetune_qwen_model_2026_08_08
- S3 bucket: mirrorview-experimental-artifacts
- S3 prefix: mirrorview-finetune_qwen_model_2026_08_08/
