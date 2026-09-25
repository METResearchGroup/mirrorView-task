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

1. **GEPA train/val scoring (adapter per-example score):**
   - **R1 (primary):** `1 - |P(remove) - remove_share|` (requires `remove_share` on `JevDataInst`).
   - **R2:** majority-label probability times example weight: `weight = 0.5` when `abs(n_keep - n_remove) == 1`, else `1.0`.
   - **R7 (approved):** majority-label probability with weight `1.0` always (Stage B `probability` mode on union cohort, all other rebuild settings unchanged).
2. **Candidate ranking during optimization:** same per-example scores aggregated on val subsample (see eval policy below).
3. **Final selection:** split dev 50/50 into dev-A and dev-B (stratified by label, seed `20260924`). Dev-A tunes the F1 threshold at natural prevalence; dev-B confirms the same threshold on the shortlisted candidates only. Preselect the **top 10 accepted candidates** by validation subsample score, then drop any with val-dev balanced-accuracy gap above **VAL_DEV_GAP_MAX** (0.15; see Guards). Tune threshold on dev-A for F1 at natural prevalence for survivors; confirm ranking on dev-B F1 at the same threshold. Scoring every accepted candidate on the full 1,927-post dev set would cost about **190,000** post scorings (~10x the R1 optimize budget). **Test read once** per ablation after selection.

Implement dev-A/dev-B columns in parquet or a sidecar split file under `experiments/predict_keep_remove_jev_gepa_2026_09_23/data/`.

## GEPA 0.1.4 (verified in `.venv`, package version 0.1.4)

Signature checked via `uv run python -c "import gepa, inspect; print(inspect.signature(gepa.optimize))"`.

### Options that exist

| Parameter | Built-in choices | Notes |
|-----------|------------------|-------|
| `val_evaluation_policy` | `"full_eval"` only as string | Resolves to `FullEvaluationPolicy` (all val ids every eval). **No** built-in sampled-val string. |
| `val_evaluation_policy` | Custom `EvaluationPolicy` instance | Implement `get_eval_batch`, `get_best_program`, `get_valset_score` to score a fixed-size random subset (plan: 100 val posts on accept only, seed-driven, refresh subset every N iterations). |
| `acceptance_criterion` | `"strict_improvement"`, `"improvement_or_equal"` | Both compare **sums of adapter `scores`** on the reflection minibatch (soft scores today). |
| `acceptance_criterion` | Custom `AcceptanceCriterion` | Implement `should_accept(proposal, state)` using hard labels at 0.5 and accuracy with margin **+2** correct vs parent on the 25-post reflection minibatch. |
| `reflection_minibatch_size` | int | Used with `batch_sampler="epoch_shuffled"`. Current runner uses 10; rebuild uses **25**. |
| `batch_sampler` | `"epoch_shuffled"` or custom `BatchSampler` | Custom sampler can prefer misclassified, high-confidence errors, close vote splits, and contrastive near-duplicate pairs (build index from train parquet). |
| `module_selector` | GEPA default (omit kwarg) | **R1 to R3, R5 to R7:** single `study_instruction` key only. |
| `module_selector` | `"round_robin"` | **R4 only:** multi-key `seed_candidate`; one component mutates per iteration. |
| `module_selector` | `"all"` or custom `ReflectionComponentSelector` | Not used in this rebuild unless experiments require it. |
| `candidate_selection_strategy` | `pareto`, `current_best`, `epsilon_greedy`, `top_k_pareto` | Keep `pareto` unless dev experiments show otherwise. |
| `use_merge`, `max_merge_invocations` | bool / int | Optional; merge needs overlapping val ids when not `full_eval`. |
| `max_metric_calls`, `max_reflection_cost` | numeric | Primary budget knobs (**posts** for metric calls). |
| `cache_evaluation` | bool | Can reduce repeat scoring when re-evaluating same (candidate, example). |

### Options that do **not** exist (do not plan on these)

- No `val_evaluation_policy="sampled"` or similar preset.
- No built-in hard-label or margin acceptance mode (only soft sum).
- No built-in error-focused or contrastive minibatch sampler (custom `BatchSampler` required).

## Strict acceptance (recommended implementation)

Reflection here means the GEPA step where the reflection language model proposes edits to the study instruction after seeing scored minibatch errors.

1. Register a custom `AcceptanceCriterion` in the rebuilt optimize runner.
2. On proposal, score parent and child on a **25-post** reflection minibatch (**50 posts** total).
3. Use hard-label accuracy at threshold 0.5 on that minibatch; accept only if `acc_after >= acc_before + 2` (locked margin on 25 posts).
4. On accept only, run **100-post** validation subsample (counts toward post budget).
5. Keep GEPA `acceptance_criterion` as custom class; do not rely on `"strict_improvement"` on soft probability scores.

At **20% to 30%** acceptance, mean cost per iteration is about **70 to 80 posts** (50 always + 100 × accept rate).
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
| Val-dev gap (selection only) | When preselecting the **top 10 accepted** candidates by validation subsample score, score each on dev-A at threshold **0.5** and compute **balanced accuracy** on (a) that candidate's validation subsample (**100** posts from the accept-only policy, or full **300**-post val if that candidate was fully scored) and (b) the full dev-A split. **Reject** the candidate from the top-10 pool if `val_balanced_acc - dev_a_balanced_acc > VAL_DEV_GAP_MAX` (**0.15**). Do not mix soft val aggregate scores with dev F1 in this check. |

**Proposal guards** (length, memorization): implement in a GEPA callback or by wrapping the custom acceptance criterion and returning reject with reason logged. Val-dev gap runs in selection after optimize, not on every proposal.

## Multi-component ablation (R4)

GEPA 0.1.4 supports multiple string components in `seed_candidate` (e.g. `study_instruction`, `remove_criteria`, `keep_criteria`, `mirror_note`). **R4 only:** set `module_selector="round_robin"` so one section mutates per iteration. **R1, R2, R3, R5, R6, R7:** single `study_instruction` key; use GEPA **default** module selector (do not pass round-robin). Seed `remove_criteria` / `keep_criteria` as short bullets; `mirror_note` clarifies opposite-stance mirroring. Reflection templates must name which `<curr_param>` is edited.

## Production run order (Step 6)

| Phase | Runs | Rate limit | Notes |
|-------|------|------------|-------|
| Wave 1 (parallel) | R1, R2, R3, R7 | **200** Jev request starts/min per job; **≤1,000**/min total | **30,000** post budget each; each job runs optimize, dev-A/dev-B top-10 selection, **one** test read |
| Wave 2 | R4 | same | Only after Step 5 R4 round-robin smoke passes |
| Wave 3 (optional) | R5, R6 | same | **15,000** posts each; only if R1 confirmed dev-B F1 is strictly greater than Stage A union A1 test F1 **0.538** |

## Logging and artifacts

| Item | Destination |
|------|-------------|
| Wandb group | `jev_gepa_rebuilt` |
| S3 prefix | `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/` |
| Per reflection call | `gepa_run/reflection_usage.jsonl` (input/output tokens, USD per call); LiteLLM usage via reflection LM wrapper |
| Per proposal | `gepa_run/acceptance_log.jsonl` (accepted/rejected, hard-margin outcome, guard reason) |
| R4 only | `gepa_run/component_update_log.jsonl` (iteration, module selected, key snapshot hash) |
| Stop reason | `gepa_run/stop_reason.json` (post budget, `max_reflection_cost`, `gepa.stop`, composite) |
| Selection | `dev_selection.json`, `candidate_dev_scores.jsonl` (top 10 after val-dev gap filter) |
| Dev split | `experiments/predict_keep_remove_jev_gepa_2026_09_23/data/dev_ab_split.json` (written Step 4, uploaded to S3) |
| Smoke (Step 5) | `jev_gepa_rebuilt/outputs/_smoke/` (`token_measurement.json`, `r1_smoke_report.json`, `r4_smoke_passed.json`, `r5_r6_skipped.json`, `cost_reestimate_notes.txt`) |
| Per candidate (Wandb) | dev-A F1 at tuned threshold, dev-B F1, val subsample score, instruction char length |

Also mirror existing `gepa_run/gepa_result.json` per ablation; test eval writes `test_results.json` (Step 6).

## Cost model (union pair view)

**Budget unit:** one metric call = one post scored by Jev (adapter reports post count).

Assumptions (100-post union smoke measured 2026-09-24):

| Quantity | Value |
|----------|-------|
| Input tokens per post at seed | **491.4 measured** (p50 488.3, p90 521.6) |
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
| Iterations | 30,000 / **~60 measured** (R1 smoke) | **~500** |
| Jev optimize tokens | 30,000 × **491.4 measured** | **~14.7M** |
| Jev optimize USD | 14.7e6 / 1e6 × 0.042 | **~$0.62 measured** |
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
| R2, R4, R7 | 30,000 | same as R1 | same Luna cap as R1 | ~$3 each |
| **R1 to R6** | | | | **~$40** typical; **~$60** hard ceiling |
| **R7 included above** | 30,000 | same as R1 | same Luna cap as R1 | **~$3** (approved) |

**Locked post budget:** 30,000 posts for full runs (not 60,000). Re-measure input tokens per post after prompt flip with a 100-post smoke before production runs.

**R5/R6 gate:** run half-budget jobs only when R1's confirmed dev-B F1 is strictly greater than Stage A union A1 test F1 **0.538**.

## Folder layout (new)

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/
  jev_gepa_rebuilt/
    adapter.py
    optimize.py
    evaluate.py
    policies/          # val subsample, acceptance, batch sampler
    outputs/
      _smoke/          # Step 5 token measurement and smoke pass reports
      R1_gepa_pair/
        gepa_run/
          gepa_result.json
          reflection_usage.jsonl
          acceptance_log.jsonl
          stop_reason.json
          component_update_log.jsonl   # R4 only
        dev_selection.json
        candidate_dev_scores.jsonl
        test_results.json              # Step 6 evaluate
      R2_majority_weighted/
      R3_gepa_pair_terra/
      R4_gepa_multi_component/
      R5_gepa_original/
      R6_gepa_mirror/
      R7_plain_majority/
  data/
    cohort_union_splits.parquet
    dev_ab_split.json                  # Step 4
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
