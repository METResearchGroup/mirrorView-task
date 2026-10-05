# Results (figure index)

Short index of figures for the Study 2 writeup. Metrics live in the writeup and source experiment `RESULTS.md` files; this file records what each plot is for and shared styling.

## Zero-shot (`static/zero_shot/`)

- `f1_grouped_bars.png` — Compares zero-shot F1 across models and cohort slices (All, Unanimous, Split).
- `precision_recall_scatter.png` — Shows precision–recall tradeoffs for zero-shot models by slice.
- `predicted_remove_rate.png` — Implied remove rate from reported precision/recall and gold slice prevalence.
- `accuracy_f1_dumbbell.png` — Links majority-keep accuracy and F1 for zero-shot runs on each slice.

## Few-shot (`static/few_shot/`)

- `f1_slope_zero_to_few.png` — F1 change from zero-shot to few-shot by model and slice.
- `delta_heatmap.png` — Few-shot minus zero-shot F1 deltas across models and slices.
- `precision_recall_arrows.png` — Shift in precision and recall from zero-shot to few-shot.
- `f1_grouped_bars.png` — Few-shot F1 by model and slice, grouped for direct comparison.

## Prompt tuning (`static/prompt_tuning/`)

- `f1_three_stage.png` — F1 across zero-shot, few-shot, and GEPA-tuned prompting on the relevant cohorts.
- `terra_holdout_confusion.png` — Reconstructed confusion matrix for the 61-row Terra unanimous hold-out.
- `transfer_f1_delta.png` — Change in F1 on full-cohort Jev evaluation after Terra-targeted GEPA tuning.

## Fine-tuning (`static/fine_tuning/`)

- `train_eval_f1_heatmap.png` — Train-by-eval F1 matrix for adapters (columns: Unanimous, Split, All).
- `train_eval_other_metrics.png` — Same train-by-eval layout for non-F1 metrics.
- `ft_vs_prompting_f1.png` — Fine-tuned adapter F1 versus best prompting (Jev) by slice.
- `precision_recall_by_adapter.png` — Precision and recall by training adapter and eval slice.

## Cross-cutting (`static/cross_cutting/`)

- `approach_f1.png` — Best prompting versus fine-tuning F1 across approaches and slices.

### Takeaway

Prompting F1 stays about 0.50 to 0.66 for the best model (Jev); the all-label adapter reaches about 0.91 to 0.96. Prompt tuning does not beat few-shot Jev on any slice of the full cohort. The GEPA gain (about 0.68 to 0.84 F1) was on a 61-row unanimous Terra hold-out and did not carry over to the full-cohort Jev numbers.

## Omitted

- **Training curves** — no per-step loss logs.
- **Data-efficiency subsamples** — only three incomparable training sets (label filters), not a single-run subsample ladder.
- **Bootstrap confidence intervals** — not added because per-post predictions were not joined for this figure pack.

## Styling (for consistent edits)

**Models:** Nova `#4C78A8`, Qwen `#F58518`, Jev `#54A24B`, Terra `#E45756`, Sonnet `#B279A2`.

**Adapters:** Unanimous `#9e9ac8`, Split `#6baed6`, All-label `#2171b5`.

**Slice order:** All, Unanimous, Split.

**Train-by-eval heatmap columns:** Unanimous, Split, All (matrix orientation as requested).
