# Setup (data)

## Source metrics

Plot scripts hardcode metrics transcribed from [docs/study_updates/STUDY_2_WRITEUP.md](../../docs/study_updates/STUDY_2_WRITEUP.md), cross-checked against:

- [experiments/zero_shot_llm_inference_2026_09_30/RESULTS.md](../zero_shot_llm_inference_2026_09_30/RESULTS.md)
- [experiments/few_shot_llm_inference_2026_09_30/RESULTS.md](../few_shot_llm_inference_2026_09_30/RESULTS.md)
- [experiments/zero_shot_jev_inference_2026_10_01/RESULTS.md](../zero_shot_jev_inference_2026_10_01/RESULTS.md)
- [experiments/few_shot_jev_inference_2026_10_01/RESULTS.md](../few_shot_jev_inference_2026_10_01/RESULTS.md)
- [experiments/dspy_gepa_balanced_labels_2026_10_02/RESULTS.md](../dspy_gepa_balanced_labels_2026_10_02/RESULTS.md)

Optimized full-cohort metrics (Nova, Qwen, Jev) and the fine-tune adapter matrix are taken from the writeup. They do not have a local `RESULTS.md` in this checkout.

## Derived quantities

**Predicted remove rates** are computed as `recall * gold_remove_rate / precision`.

Gold remove rates used:

| Slice     | Gold remove rate |
|-----------|------------------|
| All       | 0.212121         |
| Unanimous | 0.076031         |
| Split     | 0.267579         |

Majority-keep accuracy is `1 - remove_rate`.

**Terra hold-out confusion counts** are reconstructed from reported precision/recall and a 61-row test set with 30 remove and 31 keep labels. They were not published as counts.

## Unavailable inputs

- No per-step training loss is available, so there is no training-curve figure.
- No intermediate subsample evaluations are available, so there is no data-efficiency curve. The three training sizes (4051 unanimous, 9941 split, 13992 all) are different label filters, not subsamples of one run.

## Outputs

Each script writes PNGs under `experiments/study2_updates_2026_10_05/static/<section>/` and copies them to `docs/study_updates/static/study_2_writeup/<section>/` so pandoc, run from `docs/study_updates`, can include them as `static/study_2_writeup/...`.

## How to regenerate

From the repo root:

```bash
PYTHONPATH=. uv run python experiments/study2_updates_2026_10_05/scripts/plot_zero_shot.py
PYTHONPATH=. uv run python experiments/study2_updates_2026_10_05/scripts/plot_few_shot.py
PYTHONPATH=. uv run python experiments/study2_updates_2026_10_05/scripts/plot_prompt_tuning.py
PYTHONPATH=. uv run python experiments/study2_updates_2026_10_05/scripts/plot_fine_tuning.py
PYTHONPATH=. uv run python experiments/study2_updates_2026_10_05/scripts/plot_cross_cutting.py
```
