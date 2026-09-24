# Step 6: Label all posts and run self-consistency check

Use the approved shared codebook to label all 18,899 posts: original text and mirrored text separately (37,798 LLM calls). Each call assigns present or absent for every codebook feature. The codebook is a fixed, cacheable prompt prefix. Labeling is resumable (skip post ids already written). Write per-arm label runner outputs under `outputs/<arm>/label/` and assemble `outputs/shared/label_matrix.parquet`. Run a 20-text cost smoke before full labeling; stop if projected total cost exceeds $25. After labeling, re-label 200 random texts (seed 42) and report per-feature agreement; flag features below 90% in `outputs/shared/self_consistency/` without dropping them from the codebook.

## Scope

- **Caller / entrypoint:** `label_posts` CLI and `self_consistency` CLI (`if __name__ == "__main__"`).
- **In scope:** Approval-gate check; smoke labeling (20 texts); full labeling with resume; cost cap enforcement via `llm_client`; per-arm label shards; shared wide label matrix; self-consistency relabel and scores JSON; tests with mocked LLM and S3.
- **Out of scope:** Human validation or kappa (deferred); held-out analysis (Step 7); codebook edits after approval; Part 2 theme mapping (Step 7).

## Files to inspect (read-only)

- `docs/plans/2026-09-24_llm_feature_generation_phase_2_part_3_2f71ad/plan.md`: Step 6, cost estimate, provisional-label caveat.
- `/tmp/step_contract.md`: Section 6.8, 6.9, 6.10, Step 6 commands, Gate B, spend cap.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/llm_client.py`: `run_structured`, cost log, `SpendCapExceeded`.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/schemas.py`: add `PostLabelResult` model.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/prompts.py`: labeling prompt pattern; codebook prefix block.
- `experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py`: reference batch labeling structure (copy ideas, do not import).
- `outputs/shared/codebook/approved_<run_timestamp>/codebook.json`: input codebook (Step 5).
- `outputs/shared/codebook/approved_<run_timestamp>/approval.json`: required gate file.
- `outputs/<arm>/cohort/<run_timestamp>/cohort.parquet`: post texts, `split`, `modal_decision`.
- `data/post_split/discovery_post_ids.csv`, `data/post_split/test_post_ids.csv`: split membership.

## Files allowed to change

- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/label_posts.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/self_consistency.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/schemas.py`: add labeling schemas only.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/prompts.py`: add `build_labeling_prompt(codebook, text, text_surface)` only if not added in Step 3.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_label_posts.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_self_consistency.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/<arm>/label/`: runner output trees.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/shared/label_matrix.parquet`: assembled matrix.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/shared/self_consistency/`: relabel run and scores.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/shared/cost_log.jsonl`: append lines (via `llm_client`).

## Files forbidden to change

- `shared/`, other `experiments/*`.
- `docs/plans/.../plan.md`, sibling step files.
- `src/build_codebook.py`, `map_part2_themes.py`, `analyze.py`, `write_results.py`.
- `data/post_split/*`, `data/feature_synonyms.csv`.
- `src/llm_client.py` (Step 3 owner; call it, do not edit).

## Implementation phases (TDD: mandatory order)

| Phase | Goal | Gate |
|-------|------|------|
| 1: Scope | Name callers, file tree, out-of-scope | Callers + tree listed |
| 2: Scaffold | Create `label_posts.py`, `self_consistency.py`; stubs only | Imports resolve |
| 3: Contracts | Label schemas, CLI flags, resume keys | Stubs only |
| 4: Test design | Failing tests below | Fail for right reason |
| 5: Implement | One unit per commit | Targeted tests green |
| 6: Done | Step pytest + smoke CLI on fixtures | Pass/fail criteria met |

### Phase 4: Named tests and assertions

| Test name | Given | When | Assert |
|-----------|-------|------|--------|
| `test_label_posts_requires_approval_marker` | Codebook path without `approved_*/approval.json` | `label_posts.main(...)` | Raises `ApprovalRequiredError` |
| `test_build_prompt_prefix_stable_across_calls` | Fixed codebook JSON | Two calls to `build_labeling_prompt` | Codebook block byte-identical; only post text differs |
| `test_smoke_labels_twenty_posts` | Cohort fixture with 25 posts | `label_posts --smoke --limit 20` | Exactly 40 LLM calls (20 posts x 2 surfaces); writes shard JSON |
| `test_projected_cost_under_cap_after_smoke` | Mock cost log with smoke totals | `project_labeling_cost(smoke_calls=40, n_remaining=37758)` | `projected_total_usd < 25.00`; if `>= 25.00`, CLI exits non-zero before production |
| `test_resume_skips_labeled_post_ids` | Existing shard with `post_id` A labeled | `label_posts` rerun | No second LLM call for post A; new posts still labeled |
| `test_label_result_schema` | Mock LLM returning `PostLabelResult` | Parse row | Each `labels` key is `cb_*`; values are bool |
| `test_assemble_label_matrix_wide_format` | Shards for original + mirror | `assemble_label_matrix(...)` | Parquet has columns `post_id`, `text_surface`, `split`, `modal_decision`, `cb_*`; 18899 x 2 rows |
| `test_spend_cap_raises_on_exceed` | Mock cumulative cost 25.01 | Next `llm_client` call | Raises `SpendCapExceeded` |
| `test_self_consistency_sample_size_200_seed_42` | Labeled matrix fixture | `self_consistency --seed 42` | Sample size 200; reproducible post ids |
| `test_self_consistency_agreement_rate` | Relabel agrees on 180/200 for `cb_001` | `compute_agreement` | `agreement_rate=0.90` for `cb_001` |
| `test_features_below_threshold_listed` | Feature at 0.85 agreement | `write_scores_json` | `features_below_threshold` contains that `feature_id` |
| `test_runner_timestamp_format` | Any new output dir | After write | Directory name matches `%Y-%m-%dT%H-%M-%S` |

### Phase 5: Implementation units (dependency order)

1. `require_approved_codebook(codebook_path)`: glob `outputs/shared/codebook/approved_*/approval.json`.
2. `build_labeling_prompt`: fixed codebook prefix (name + definition per feature); user block = one post text + `text_surface`.
3. `label_single_post` via `llm_client.run_structured`: model `openai/gpt-6-luna`, `reasoning_effort="none"`, `stage="label"`.
4. `iter_posts_to_label`: all 18,899 posts; surfaces `original` and `mirror`; map to arm cohort text columns.
5. `write_label_shard` under `outputs/<arm>/label/<run_timestamp>/` (JSONL rows) and resume index `labeled_ids.json`.
6. `project_labeling_cost` from smoke `cost_log.jsonl` lines.
7. `assemble_label_matrix` to `outputs/shared/label_matrix.parquet`.
8. `self_consistency`: sample 200 (`post_id`, `text_surface`) pairs with seed 42; relabel; write `scores.json`.

**Arm assignment for label outputs:** For each post, write the label row to the arm folder matching the codebook feature's `discovery_arm` when labeling for analysis traceability; also write a unified copy into the shared matrix (primary consumer is Step 7 via `label_matrix.parquet`). If a post is labeled once for both surfaces, store both rows in the shared matrix regardless of arm folder duplication.

## Pass / fail criteria

### Must pass

- `PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_label_posts.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_self_consistency.py -q` exits 0.
- Smoke: 20 posts x 2 surfaces = 40 calls complete; cost projection printed; production blocked if projected total `>= $25.00`.
- Full run: 37,798 labeling calls (or fewer on resume after partial run).
- `outputs/shared/label_matrix.parquet` has 37,798 rows and one `cb_*` column per codebook feature.
- `outputs/shared/self_consistency/<run_timestamp>/scores.json` exists with `sample_size=200`.
- Features with agreement `< 0.90` listed in `features_below_threshold`; none removed from codebook.
- All LLM calls go through `llm_client` only; cost lines append to `outputs/shared/cost_log.jsonl`.
- Resume: re-running `label_posts` does not relabel existing `post_id` + `text_surface` pairs.

### Must fail (until implemented)

- `label_posts` without approval marker.
- `label_posts --production` when smoke projection `>= $25.00`.
- `llm_client` call when cumulative cost `>= SPEND_CAP_USD`.

## Commands (exact)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

CODEBOOK=outputs/shared/codebook/approved_<run_timestamp>/codebook.json

# Smoke: 20 posts, cost projection (must stay under $25 for full run)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts \
  --codebook "$CODEBOOK" \
  --text-surfaces original mirror \
  --smoke \
  --limit 20 \
  --seed 42

# Review stdout: projected_total_usd=... (must be < 25.00)
# Review outputs/shared/cost_log.jsonl cumulative line

# Production labeling (resumable)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts \
  --codebook "$CODEBOOK" \
  --text-surfaces original mirror \
  --production

# Assemble shared matrix (idempotent)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts \
  --codebook "$CODEBOOK" \
  --assemble-matrix

# Self-consistency on 200 texts (seed 42)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.self_consistency \
  --codebook "$CODEBOOK" \
  --label-matrix outputs/shared/label_matrix.parquet \
  --sample-size 200 \
  --seed 42

# Upload labeling artifacts
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.s3_sync \
  --paths outputs/shared/label_matrix.parquet outputs/shared/self_consistency outputs/original_only/label outputs/mirror_only/label outputs/paired/label outputs/shared/cost_log.jsonl

# Tests
PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_label_posts.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_self_consistency.py -q
```

### Expected output (representative lines)

```
approval=outputs/shared/codebook/approved_2026-09-24T12-40-00/approval.json
smoke_posts=20 surfaces=original,mirror label_calls=40
projected_total_usd=18.42 cap_usd=25.00
# production:
label_calls=37798 surfaces=original,mirror
resumed_skipped=0
Wrote outputs/shared/label_matrix.parquet rows=37798 features=...
Wrote outputs/original_only/label/2026-09-24T14-00-00/
self_consistency sample_size=200 seed=42 mean_agreement=0.94
features_below_90pct=['cb_042', 'cb_107']
Wrote outputs/shared/self_consistency/2026-09-24T15-00-00/scores.json
```

## Artifact contract (this step's outputs)

### Label runner shard (`outputs/<arm>/label/<run_timestamp>/`)

| File | Schema |
|------|--------|
| `labels.jsonl` | One JSON per line: `post_id`, `text_surface` (`original` \| `mirror`), `arm`, `labels` map `{ "cb_001": true, ... }`, `labeled_at` |
| `labeled_ids.json` | `{ "labeled": [{"post_id": "...", "text_surface": "original"}, ...] }` for resume |
| `metadata.json` | `model`, `reasoning_effort`, `codebook_version`, `n_calls`, `stage`, `built_at` |

Long-format runner alternative under `outputs/<arm>/label/outputs/<run_timestamp>/` is allowed if matching Step 3 discovery layout; prefer flat `<run_timestamp>/` above unless runner wrapper requires `/outputs/`.

### Shared label matrix (`outputs/shared/label_matrix.parquet`)

| Column | Type |
|--------|------|
| `post_id` | str |
| `text_surface` | str (`original` \| `mirror`) |
| `split` | str (`discovery` \| `test`) |
| `modal_decision` | str |
| `cb_<feature_id>` | int 0/1 (one column per codebook feature, e.g. `cb_001`) |

### Self-consistency (`outputs/shared/self_consistency/<run_timestamp>/scores.json`)

```json
{
  "sample_size": 200,
  "seed": 42,
  "per_feature": {
    "cb_001": {"agreement_rate": 0.95, "n_pairs": 200}
  },
  "features_below_threshold": ["cb_042"]
}
```

Also write `relabeled.jsonl` with both passes for audit.

### Cost log (`outputs/shared/cost_log.jsonl`)

Each line: `timestamp`, `stage` (`label` or `self_consistency`), `arm`, `model`, `input_tokens`, `output_tokens`, `reasoning_tokens`, `cost_usd`, `cumulative_cost_usd`.

## Human gates (if any)

None in this step. Step 5 Gate B must be satisfied before `label_posts` runs.

**Spend gate (automated):** `llm_client` stops at `$25.00` cumulative; smoke must project under cap before `--production`.

## Commit message template

`step6: label all posts with smoke cost check and self-consistency`

## Handoff to Step 7

- `outputs/shared/label_matrix.parquet` (37,798 rows)
- `outputs/shared/codebook/approved_<run_timestamp>/codebook.json`
- `outputs/shared/self_consistency/<run_timestamp>/scores.json`
- Discovery-half rows in matrix: for description and Part 2 overlap description only
- Test-half rows (`split == test`): sole input for Q1 to Q7 hypothesis tests in Step 7
