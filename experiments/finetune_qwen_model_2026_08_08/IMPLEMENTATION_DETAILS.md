# Implementation details

Canonical operator docs: see `README.md` in this folder.

(Generated from chatting back and forth with the AI agent)

Goal
Preliminary teachability test: can a small, high-purity, class-balanced set teach Qwen/Qwen3-4B-Instruct-2507 the keep/remove task at all, before scaling labels. Exploratory — compare baseline vs fine-tuned tables; no numeric success bar.

Data
Source: STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3 (shared/data/registry.py)
All 154 removes + 154 keeps (uniform random, seed=1) → n=308
80/20 split, both splits 1:1 keep/remove, seed=1 → data/{train,test}.csv
Chat: data/chat_{train,test}.jsonl with {"message_id", "messages": [system, user, assistant]}
Built locally, then uploaded to S3; test JSONL never used in trainer.train
Prompt / labels
Vendored rubric template (from prompt-eng v1/v2); closing line edited to ask for keep or remove only
Fixed post order: original → Post 1, mirror → Post 2
System: short moderation instruction (“answer with exactly keep or remove”)
Assistant target: keep or remove only
Positive class for metrics: remove
Training
TRL SFTTrainer + PEFT LoRA; assistant-only loss
LoRA: r=16, alpha=32, dropout=0.05, attn+MLP targets
bf16 LoRA (no QLoRA); 3 epochs; lr 2e-4; cosine + ~3–5% warmup; eff. batch 8 via batch=1 × grad_accum=8; max_seq_length=2048; train seed 1
No early stopping on test; W&B project mirrorview-finetune-qwen-2026-08-08 (WANDB_API_KEY via EnvVarsContainer)
Inference / eval
Greedy, small max_new_tokens; parse first token; __invalid__ → predicted_label NA; metrics count invalid as wrong
Pred CSVs: message_id, gold decision/label, raw_generation, predicted_decision, predicted_label
Local evaluate.py → RESULTS.md (train & test tables × baseline vs fine-tuned)
Infra
First green train on SageMaker; also both infer passes on SageMaker; metrics local
Custom Docker (repo-root context), ECR mirrorview-finetune_qwen_model_2026_08_08, modes train / infer_baseline / infer_adapter
launch_sagemaker.py --mode ...; instance ml.g5.xlarge; region us-east-2
S3: s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/ → shared data/, adapters/<run_id>/, preds/{baseline,fine_tuned}/...
Pass HF_TOKEN; fail fast if missing
