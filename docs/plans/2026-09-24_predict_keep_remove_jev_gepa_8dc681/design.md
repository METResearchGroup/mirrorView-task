# Design: predict keep or remove with Jev and GEPA

## Folder layout

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/
  README.md              # title + pointers to SETUP.md and RESULTS.md
  SETUP.md               # data requirements only
  RESULTS.md             # metric tables
  shared/
    cohort.py            # dedupe, majority/unanimous labels
    splits.py            # stratified split, GEPA balanced subsets
    prompt.py            # STUDY_INSTRUCTION, pair/original/mirror render
    jev_scorer.py        # batched client.system_one calls
    rate_limiter.py      # RequestStartLimiter 1000/min
    retries.py           # 3 attempts, 1/2/4 s backoff
    latency.py           # timed decorator, p50/p90/p99
    pricing.py           # $0.042/M input, $0 output
    metrics.py           # F1, AUC, slices, Spearman
    artifacts.py         # CampaignObjectStore, upload_under_prefix
    wandb_tracking.py    # groups, job_type, artifacts
    tests/
  jev_baseline/
    run.py               # Stage A runner per ablation id
    A1_pair_study_prompt/
    A2_original_only/
    A3_mirror_only/
    A4_pair_features_addendum/
  jev_gepa/
    adapter.py           # GEPAAdapter
    optimize.py          # gepa.optimize runner
    B1_gepa_pair/
    B2_gepa_original/
    B3_gepa_mirror/
    B4_gepa_asymmetric_reward/
  analysis/
    cluster_errors.py
    mine_gepa_criteria.py
```

S3 prefix mirrors the folder: `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/`.

| Subprefix | Contents |
|-----------|----------|
| `data/` | cohort parquet, splits parquet |
| `jev_baseline/<ablation_id>/` | labels.parquet, requests.parquet, results.json |
| `jev_gepa/<ablation_id>/` | gepa run_dir, candidates, final prompt, test labels |
| `analysis/` | cluster outputs, mined criteria |

## Data pipeline

| Dataset key | Path | Rows |
|-------------|------|------|
| `STUDY_PHASE_2_PART_3_RESULTS_FULL` | `shared/data/raw/study_phase_2_part_3/results/full.csv` | 131,175 |
| `STUDY_PHASE_2_PART_3_STIMULI` | `shared/data/raw/study_phase_2_part_3/stimuli/flips.csv` | 18,899 posts |

Collection record: frozen 2026-09-22 snapshot of `s3://jspsych-mirror-view-2026-09-09/data/prolific/`; collection 2026-09-10 to 2026-09-21.

Verification (2026-09-24): AWS STS as IAM user `mark_iam_credentials`, account 517478598677, region `us-east-2`; Wandb via Secrets Manager `wandb-api-key` as `markptorres1`; Jev via `jev-typesafe-api-key`; OpenAI via `OPENAI_API_KEY` and secret `openai-api-key`.

Load via `shared.data.dataloader.load_dataset`. Blueprint for label transforms: `shared/data/transformed/study_phase_2_part_2/transform.py` and `shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py` (no Part 3 transform exists yet).

| Filter | Value |
|--------|-------|
| `trial_type` | `moderation-trial` |
| `post_id` | non-empty |
| `decision` | `keep` or `remove` |
| Scored trials | 79,500 decisions, 3,875 participants, 18,866 posts |
| Prevalence | keep 69.6%, remove 30.4% |
| Median raters per post | 5 |
| Duplicate sessions | 98 participants with 40 to 60 decisions; 1,960 duplicate participant x post pairs; dedupe to first rating |
| Trial design | Linked-fate pair: participant sees original and mirror together, one keep/remove decision for the pair |

| Cohort | Rule | Posts | keep | remove | remove % |
|--------|------|-------|------|--------|----------|
| A (primary) | majority, >=3 raters, ties dropped | 14,941 | 11,772 | 3,169 | 21.2% |
| B (subset) | unanimous, >=3 raters | 4,889 | 4,411 | 478 | subset of A |

Label convention: 1 = remove (positive), 0 = keep (issue #299, `experiments/llm_prompt_engineering_2026_08_05/evaluate.py`).

Metadata per post: `sampled_stance` (left/right), `sample_toxicity_type` (low/middle/high).

Text length: original mean 218 chars (~55 tokens); mirror mean 249 chars (~62 tokens).

## Splits (seed 20260924)

One frozen parquet, stratified by label x stance x toxicity. Uploaded to S3 and Wandb artifact.

| Split | % of A | Posts | Prevalence | Use |
|-------|--------|-------|------------|-----|
| test | 20% | ~2,988 | natural | final reporting only |
| dev | 10% | ~1,494 | natural | threshold tuning, GEPA candidate selection |
| GEPA pool | 70% | ~10,459 | natural | source for GEPA subsets |
| GEPA valset | from pool | 300 | balanced 150/150 | GEPA validation |
| GEPA trainset | from pool | up to 2,000 | balanced | reflection minibatches |

## Prompt rendering

| Source | Path |
|--------|------|
| Study instruction | `experiments/reasoning_during_moderation_2026_09_15/shared/prompt.py` (`STUDY_INSTRUCTION`, ~350 tokens) |
| Pair order | `PAIR_ORDER_SEED=0` hash pattern from `experiments/reasoning_during_moderation_2026_09_15/shared/constants.py` |
| Closing line | `Allow or Remove?` |
| Human-mined criteria (A4) | `KEEP_REMOVE_FEATURES_ADDENDUM` from `experiments/llm_prompt_engineering_2026_08_05/prompt.py` |

Jev optimizable component: instruction inside each `Noul` question. State holds post text only. Seed question: study instruction + yes/no "Should this pair be removed?" Single-text arms: minimal instruction edit referring to one post instead of a pair (document exact diff in step file; fidelity test against `webapp/public/main.js`).

## Jev scorer

Port from `METResearchGroup/mind_technology_lab_experiments` PR #23 (`experiments/speedup_jev_2026_09_23/`).

```python
client.system_one(
    state={"posts": [t0..t9]},
    questions={"post_i": Noul(instructions="Consider posts[i]. ...")},
    model="jev-1.13.0",
)
# response: answers[id].noul = P(remove)
```

| Setting | Value |
|---------|-------|
| SDK | `typesafe-sdk` 0.7.1 |
| Model | `jev-1.13.0` |
| API key | Secrets Manager `jev-typesafe-api-key` |
| SDK retries | `RetryPolicy(max_retries=0)` |
| Experiment retries | 3 extra, backoff 1/2/4 s; auth fails fast |
| Rate limiter | `RequestStartLimiter`, 60 s window, 1,000 starts/min |
| Concurrency | `ThreadPoolExecutor`, 8 workers, per-thread clients |
| Batch size | 10 posts per request |
| Resume | skip posts in `predictions.jsonl` |
| Outputs | predictions.jsonl, requests.jsonl, deadletter.jsonl, then labels.parquet, requests.parquet, results.json |
| Pricing | $0.042 / 1M input tokens, $0 output |

## Metrics

| Metric | Positive class |
|--------|----------------|
| F1, accuracy, precision, recall | remove (label 1) |
| Balanced accuracy, ROC-AUC, PR-AUC | from P(remove) |
| Confusion matrix | yes |
| Latency | p50/p90/p99 per request and per post; wall time per pass |
| Cost | tokens and dollars per pass |
| Trivial baselines | keep-all, remove-all, prevalence-random |
| Default threshold | 0.5; dev-tuned threshold is post-hoc ablation |
| Subgroups | stance, toxicity, unanimous vs non-unanimous, rater agreement |
| Correlation | Spearman between P(remove) and human remove-vote share |

## GEPA

| Setting | Value |
|---------|-------|
| Package | `gepa` 0.1.4 |
| Adapter | `GEPAAdapter`: `evaluate(batch, candidate, capture_traces)`, `make_reflective_dataset(...)` |
| Default score | P(gold label): P(remove) if gold remove, else 1 - P(remove) |
| Reflective feedback | post text(s), gold label, vote split, P(remove), stance, toxicity, threshold crossed |
| Reflection LM | `openai/gpt-5.4` (alt: Qwen3.5 4B on HF Jobs) |
| `reflection_minibatch_size` | 10 (one Jev request) |
| `candidate_selection_strategy` | `pareto` |
| `use_merge` | True |
| `max_metric_calls` | 9,000 (30 x valset 300) |
| `max_reflection_cost` | $20 per run |
| `seed` | 20260924 |
| Wandb | `use_wandb=True`, `wandb_attach_existing=True` inside lab run |
| Parallel runs | 4 processes, 250 req/min each (total 1,000/min) |
| Final candidate | highest dev F1 at 0.5 among accepted candidates; test reported once |

B4 asymmetric reward (issue #299): TP +1, FN -3, FP -1, TN +0.5.

Transfer evals (no new optimization): B1 prompt on original and mirror; B2 on mirror; B3 on original.

## Wandb conventions

| Field | Value |
|-------|-------|
| Project | `predict_keep_remove_jev_gepa_2026_09_23` |
| Groups | `jev_baseline`, `jev_gepa`, `analysis` |
| Run names | ablation id + slug (e.g. `A1_pair_study_prompt`, `B1_gepa_pair`) |
| `job_type` | `score`, `optimize`, `evaluate`, `analyze` |
| Config | model pin, batch size, rate cap, split hash, prompt hash |
| Artifacts | splits parquet, seed and candidate prompts, labels parquet |

## Analysis (wiki manuals)

| Task | Manual | Input |
|------|--------|-------|
| Feature mining | [HOW_TO_MINE_TEXT_FOR_FEATURES.md](https://github.com/METResearchGroup/lab_wiki/blob/main/docs/manuals/methods/HOW_TO_MINE_TEXT_FOR_FEATURES.md) | GEPA final prompts vs `KEEP_REMOVE_FEATURES_ADDENDUM` |
| Error clustering | [HOW_TO_CLUSTER_TEXT.md](https://github.com/METResearchGroup/lab_wiki/blob/main/docs/manuals/methods/HOW_TO_CLUSTER_TEXT.md) | A1 and B1 test false positives/negatives |

Clustering: embed with `all-MiniLM-L6-v2` (precomputed, seeded); K-means baseline then BERTopic; cluster original and mirror separately.

## Prior patterns reused

| Source | Reused |
|--------|--------|
| PR #23 (`experiments/speedup_jev_2026_09_23/`) | batching, limiter, latency, resume, pricing |
| [Jev classification post](https://markptorres.com/research/2026-09-19-using-jev-for-classification) | Jev F1 0.732, recall 0.880 on 1k Brady tweets; p50 130.9 ms, p90 186.6, p99 274.4 |
| `experiments/reasoning_during_moderation_2026_09_15` | study prompt, S3 artifacts, SETUP/RESULTS layout, shared/tests |
| `experiments/predict_keep_remove_2026_07_01` | label aggregation, API baseline runner, Wandb usage |
| `experiments/simplified_predict_remove_2026_05_13/splits.py` | stratified split |
| Issue #299 (`METResearchGroup/mirrorView-task`) | label convention, asymmetric reward, F1 primary, trivial baselines (DSPy MIPROv2 spec; GEPA chosen per user) |

## Risks

| Risk | Mitigation |
|------|------------|
| Jev batch effects (posts in a batch influence each other) | seeded shuffle; constant batch composition across ablations |
| GEPA overfitting valset | separate dev for candidate selection; single test read |
| Class imbalance | balanced GEPA train/val; natural prevalence on dev/test |
| Pair-view prompt length | probe measured ~490 input tokens/post; monitor in smoke |
| Duplicate sessions | dedupe to first rating per participant x post before aggregation |

## Dependencies

Add to `pyproject.toml` and refresh `uv.lock`:

- `typesafe-sdk`
- `gepa` 0.1.4

`wandb` already present.

## Verification

Shared unit tests must exit 0:

`PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests -q`

## Out of scope

Fine-tuning, other LLM classifiers, per-participant prediction.
