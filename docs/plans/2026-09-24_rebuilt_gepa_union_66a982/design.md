# Design: rebuilt GEPA on union cohort

Technical detail for `docs/plans/2026-09-24_rebuilt_gepa_union_66a982/plan.md`. Implementation lives under `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/` (new) alongside existing Stage A/B artifacts.

## What went wrong in Stage B (cohort A)

| Issue | Mechanism |
|-------|-----------|
| Wrong optimizable text | GEPA mutated the short per-post question (~264 chars). The study stimulus stayed inside scorer state via `render_pair_prompt`, so reflection never edited participant-facing instructions. |
| Val vs dev mismatch | GEPA Pareto tracking used mean soft probability score on a balanced 300-post valset. Final pick used dev F1 at fixed 0.5 on natural prevalence. Best val candidate often differed from best dev F1 (B1: val best idx 23 vs dev pick idx 14). |
| Budget spent on full val | Each accepted proposal triggered full 300-post val evaluation (~30 Jev requests). With a 9,000 post budget, only ~29 iterations completed; ~290 training posts ever reached reflection. |
| Loose acceptance | `acceptance_criterion="strict_improvement"` compares **sums of per-example soft scores** on a 10-post minibatch. All 29 proposals accepted. |
| Prompt bloat and memorization | Optimized questions grew to 1,789 to 11,265 characters and quoted training phrases. Jev repeats per-post instructions, so length increases cost and latency. |
| Thin logging | Reflection token usage and USD not persisted. Per-candidate dev F1 not saved. Stop reason was budget exhaustion only. |

## Union data (`data/cohort_union_splits.parquet`)

| Field | Value |
|-------|-------|
| Posts | 19,219 (keep 15,210, remove 4,009, 20.9% remove) |
| test | 3,841 |
| dev | 1,927 (split into dev-A / dev-B below) |
| GEPA pool | 13,451 |
| GEPA val | 300 balanced (150/150), from Part 3 picks where possible |
| GEPA train | 2,000 balanced (1000/1000), same cohort metadata |
| Extra columns | `n_raters`, `n_remove`, `remove_share`, Part 2/3 rater counts, `in_part3_cohort_a`, `label_changed_vs_part3` |

**Baseline to beat (Stage A union, test F1):** A1 pair **0.538** (n=3,841), A3 mirror **0.528**, A2 original **0.514** in `experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md`.

## Budget unit (posts, not API batches)

One GEPA **metric call** equals **one post scored by Jev**. The adapter increments the budget by the number of posts in each scoring batch (typically 10 per API request), not by one per HTTP call. All `max_metric_calls` values, Wandb logs, and cost models in this rebuild use **post scorings** as the unit.

## Prompt architecture (rebuild)

| Piece | Role | GEPA |
|-------|------|------|
| Study instruction | Exact `STUDY_INSTRUCTION` text from `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/prompt.py` (1,475 chars today) | **Optimizable seed** (single component key, e.g. `study_instruction`) |
| Per-post question | Fixed one-liner: pair-level remove yes/no (current `build_noul_instruction` pair wording without growing criteria lists) | **Not** optimized in R1 |
| Scorer state | Post text only: pair view renders Post 1 / Post 2 blocks and closing line **without** study paragraphs | Static |

Single-text views (optional R5/R6): use `STUDY_INSTRUCTION_SINGLE` as seed component and single-post state renderer.

Jev API shape unchanged: batch 10, `jev-1.13.0`, shared instruction string passed into `score_batch` with per-index `Consider posts[i].` prefix (see existing `jev_scorer.py`).

## Objective: ranking vs threshold

1. **GEPA train/val scoring (adapter per-example score):** primary = label-certainty score `1 - |P(remove) - remove_share|` (uses `remove_share` on `JevDataInst`). Ablation R2 = down-weight 3-2 splits (e.g. multiply score by 0.5 when `n_raters == 5` and minority vote is 2).
2. **Candidate ranking during optimization:** same per-example scores aggregated on val subsample (see eval policy below).
3. **Final selection:** split dev 50/50 into dev-A and dev-B (stratified by label, seed `20260924`). Preselect the **top 10 accepted candidates** by validation subsample score. Tune threshold on dev-A for F1 at natural prevalence for those 10 only; confirm ranking on dev-B F1 at the same threshold. Scoring every accepted candidate on the full 1,927-post dev set would cost about **190,000** post scorings (~10x the R1 optimize budget). **Test read once** per ablation after selection.

Implement dev-A/dev-B columns in parquet or a sidecar split file under `experiments/predict_keep_remove_jev_gepa_2026_09_23/data/`.

## GEPA 0.1.4 (verified in `.venv`, package version 0.1.4)

Signature checked via `uv run python -c "import gepa, inspect; print(inspect.signature(gepa.optimize))"`.

### Options that exist

| Parameter | Built-in choices | Notes |
|-----------|------------------|-------|
| `val_evaluation_policy` | `"full_eval"` only as string | Resolves to `FullEvaluationPolicy` (all val ids every eval). **No** built-in sampled-val string. |
| `val_evaluation_policy` | Custom `EvaluationPolicy` instance | Implement `get_eval_batch`, `get_best_program`, `get_valset_score` to score a fixed-size random subset (plan: 100 val posts on accept only, seed-driven, refresh subset every N iterations). |
| `acceptance_criterion` | `"strict_improvement"`, `"improvement_or_equal"` | Both compare **sums of adapter `scores`** on the reflection minibatch (soft scores today). |
| `acceptance_criterion` | Custom `AcceptanceCriterion` | Implement `should_accept(proposal, state)` using hard labels at 0.5, accuracy or F1, and a margin (e.g. require +3 correct vs parent on the same minibatch). Optionally score a larger acceptance batch (50 posts) via extra adapter calls inside the criterion (counts toward post budget). |
| `reflection_minibatch_size` | int | Used with `batch_sampler="epoch_shuffled"`. Current runner uses 10; rebuild uses **25**. |
| `batch_sampler` | `"epoch_shuffled"` or custom `BatchSampler` | Custom sampler can prefer misclassified, high-confidence errors, close vote splits, and contrastive near-duplicate pairs (build index from train parquet). |
| `module_selector` | `"round_robin"`, `"all"` | With multi-key `seed_candidate`, `round_robin` updates one component per iteration; `all` updates every key each iteration. |
| `module_selector` | Custom `ReflectionComponentSelector` | For R4 multi-component ablation. |
| `candidate_selection_strategy` | `pareto`, `current_best`, `epsilon_greedy`, `top_k_pareto` | Keep `pareto` unless dev experiments show otherwise. |
| `use_merge`, `max_merge_invocations` | bool / int | Optional; merge needs overlapping val ids when not `full_eval`. |
| `max_metric_calls`, `max_reflection_cost` | numeric | Primary budget knobs (**posts** for metric calls). |
| `cache_evaluation` | bool | Can reduce repeat scoring when re-evaluating same (candidate, example). |

### Options that do **not** exist (do not plan on these)

- No `val_evaluation_policy="sampled"` or similar preset.
- No built-in hard-label or margin acceptance mode (only soft sum).
- No built-in error-focused or contrastive minibatch sampler (custom `BatchSampler` required).

## Strict acceptance (recommended implementation)

1. Register a custom `AcceptanceCriterion` in the rebuilt optimize runner.
2. On proposal, score parent and child on a **25-post** reflection minibatch (**50 posts** total).
3. Use hard-label accuracy at threshold 0.5 on that minibatch; accept only if `acc_after >= acc_before + margin` (margin default 2 on 25 posts) **or** `f1_after > f1_before` with tie-break margin.
4. On accept only, run **100-post** validation subsample (counts toward post budget).
5. Keep GEPA `acceptance_criterion` as custom class; do not rely on `"strict_improvement"` on soft probability scores.

At **20% to 30%** acceptance, mean cost per iteration is about **70 to 80 posts** (50 always + 100 × accept rate).

Optional: second-stage acceptance on a fixed 50-post acceptance batch drawn from train (extra post scorings, logged separately).

## Richer reflection feedback

Extend `make_reflective_dataset` / `_build_feedback` to include:

- Error vs correct; confident errors (`P(remove)` far from 0.5 on wrong side).
- Vote split (`n_keep`, `n_remove`, `remove_share`).
- Near-duplicate contrast: precompute pairs from train with high text similarity and opposite labels (offline index in `jev_gepa_rebuilt/data/`).

**Participant free text:** Moderation trials in `STUDY_PHASE_2_PART_3_RESULTS_FULL` and `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` have **no** per-trial explanation column and **no** per-post free-text explanations. `phase1_pair_reflection_text` is present but **empty on moderation trials** (non-null only for phase-1 trials). Participant-level reflection exists in registry `STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK` (~1,177 rows, not joinable per post). Rebuild feedback does **not** use per-decision free text; it uses **vote splits, confident errors, and contrastive pairs** instead. Optional future work could inject aggregate themes from the registry table into reflection context only.

## Guards (post-proposal, pre-accept)

| Guard | Rule |
|-------|------|
| Length | Reject if any optimized component exceeds **4,000 characters** (study instruction alone is about 1,750 characters today). |
| Memorization | Reject if candidate contains any substring of length >= 40 chars from GEPA train post texts (original or mirror). |
| Val-dev gap | After subsample val score is computed, reject if `|val_subsample_score - dev_A_f1_proxy| > 0.15` (proxy = quick dev-A eval on 200-post sample) or if dev-A F1 drops more than 0.05 vs parent. Tune constants in smoke. |

Implement guards in a GEPA callback or by wrapping the custom acceptance criterion and returning reject with reason logged.

## Multi-component ablation (R4)

GEPA 0.1.4 supports multiple string components in `seed_candidate` (e.g. `study_instruction`, `remove_criteria`, `keep_criteria`, `mirror_note`). Use `module_selector="round_robin"` so one section mutates per iteration. Seed `remove_criteria` / `keep_criteria` as short bullets; `mirror_note` clarifies opposite-stance mirroring. Reflection templates must name which `<curr_param>` is edited.

## Logging and artifacts

| Item | Destination |
|------|-------------|
| Wandb group | `jev_gepa_rebuilt` |
| S3 prefix | `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/` |
| Per reflection call | Log LiteLLM/OpenAI usage (input/output tokens, USD) via wrapper on reflection LM or GEPA callback |
| Per candidate | dev-A F1 at tuned threshold, dev-B F1, val subsample score, instruction char length, accept/reject reason |
| Stop reason | Persist post budget exhaustion, `max_reflection_cost`, `gepa.stop`, or `NoImprovementStopper` if used |

Mirror existing `gepa_result.json`, `dev_selection.json`, and add `candidate_dev_scores.jsonl`.

## Cost model (union pair view)

**Budget unit:** one metric call = one post scored by Jev (adapter reports post count).

Assumptions (re-measure with 100-post smoke after prompt flip):

| Quantity | Value |
|----------|-------|
| Input tokens per post at seed | ~494 (study instruction now in per-post instruction; seed total unchanged) |
| Input tokens per post at 4,000 char cap | up to ~1,170 |
| Planning average | ~800 input tokens per post |
| Jev input price | $0.042 / 1M tokens |

### Per iteration (posts)

| Step | Posts |
|------|-------|
| Parent + child on 25-post reflection minibatch | 50 |
| 100-post val subsample (accept only) | 100 × accept rate |
| **Mean at 20 to 30% accept** | **~70 to 80** |

### R1 at 30,000 post budget

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Iterations | 30,000 / 70 to 80 | **375 to 430** |
| Jev optimize tokens | 30,000 × 800 | **~24M** |
| Jev optimize USD | 24e6 / 1e6 × 0.042 | **~$1.00** |
| Dev top-10 selection | ~10 × 1,927 posts × ~800 tok | **~15M tok, ~$0.65** |
| Test scoring | 3,841 posts × ~800 tok | **~$0.15** |
| Reflection (Luna) | ~400 calls × (~12k in + ~3k out) | **~$0.003/call, ~$1.10 total** (cap **$5**) |
| **Total R1** | | **~$3** |
| Wall time | 2 to 4.5 h at shared 1,000 req/min (200/job) | |

### Other runs

| Run | Post budget | Jev optimize | Reflection | Total (plan) |
|-----|-------------|--------------|------------|--------------|
| R3 Terra | 30,000 | ~$1.00 | ~400 × ~$0.06 ≈ **$24** (cap **$40**) | ~$26 |
| R5, R6 | 15,000 each | ~$0.50 | ~half Luna (~$0.55, cap ~$2.50) | **~$1.50** each |
| R2, R4 | 30,000 | same as R1 | same Luna cap as R1 | ~$3 each |
| **All six** | | | | **~$40** typical; **~$60** hard ceiling |

### 60,000 post option (decision)

| Quantity | Result |
|----------|--------|
| Iterations | **750 to 860** |
| Jev optimize USD | ~48M tok ≈ **$2.00** |
| Wall time | about **4 to 9 h** |

Re-measure input tokens per post after prompt flip with a 100-post smoke before locking post budget.

## Folder layout (new)

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/
  jev_gepa_rebuilt/
    adapter.py
    optimize.py
    evaluate.py
    policies/          # val subsample, acceptance, batch sampler
    outputs/
      R1_gepa_pair/
      R2_label_certainty/
      R3_gepa_pair_terra/
      ...
  data/
    cohort_union_splits.parquet
    dev_ab_split.json
```

## Tests

- Unit tests: prompt rendering (study only in candidate, posts only in state), label-certainty score, guards, custom acceptance on synthetic trajectories.
- Smoke: `--smoke --max-metric-calls 120` on R1 with 20-post val subsample (120 = 120 **posts**).

## Commands (verification)

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/ -q
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R1_gepa_pair --smoke --max-metric-calls 120
```

Expected smoke: completes without error, writes `gepa_run/gepa_result.json`, logs at least one reject with guard or strict acceptance, Wandb run in group `jev_gepa_rebuilt`.
