# Qwen3-4B keep/remove ablation on one modal eval set

- Model: `Qwen/Qwen3-4B-Instruct-2507`
- Shared eval set: frozen modal balanced splits from `experiments/larger_finetune_qwen_model_2026_08_08/data/` (`STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`; seed=1; 80/20; train 4500 / test 1126)
- Positive class: remove
- Arms:
  - `baseline`: no LoRA
  - `unanimous_lora`: PR 54 adapter `passrole_probe3` (trained on unanimous min-3 labels)
  - `modal_lora`: PR 57 adapter `modal_larger_1ep_2026_08_09` (trained on modal labels)
- No retraining in this experiment
- Unanimous infer job: `qwen-lora-infer-adapter-2026-08-12-16-13-38-540`

## Train

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| baseline | 0.6027 | 0.5641 | 0.9031 | 0.6945 |
| unanimous_lora | 0.6920 | 0.7379 | 0.5956 | 0.6591 |
| modal_lora | 0.7293 | 0.7382 | 0.7107 | 0.7242 |

## Test

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| baseline | 0.6385 | 0.5871 | 0.9343 | 0.7210 |
| unanimous_lora | 0.7123 | 0.7581 | 0.6234 | 0.6842 |
| modal_lora | 0.7016 | 0.7090 | 0.6838 | 0.6962 |

## Notes

On this shared modal test set, baseline remove-F1 is highest (0.7210). Both LoRA arms raise accuracy and precision, and both lower remove recall and remove-F1 relative to baseline. The unanimous adapter edges the modal adapter on test accuracy (0.7123 vs 0.7016) and precision, while the modal adapter is closer to baseline on recall.

Baseline and modal test numbers match `experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md` (baseline F1 0.7210; modal F1 0.6962).
