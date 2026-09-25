# Step 7: Run Stage B (B1, B1-T, B2 to B4 plus transfer evals)

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py` `main` (production) and a new `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/evaluate.py` `main` (transfer and test reads)
- **Task:** Run five GEPA optimizations in parallel (tmux): `B1_gepa_pair`, `B1T_gepa_pair_terra`, `B2_gepa_original`, `B3_gepa_mirror`, `B4_gepa_asymmetric_reward`. Each process uses a per-process Jev rate cap of 200 requests per minute (1,000 total). Monitor runs to completion. Select the final prompt per ablation on dev F1 (from Step 6 `select_candidate_on_dev`). Score the test split once per ablation (`job_type=evaluate`). Run transfer evals on dev and test: B1 prompt on original and mirror views; B2 prompt on mirror; B3 prompt on original. Compare B1 and B1-T on dev and test F1 and reflection cost. Upload run dirs, candidates, and final prompts to S3. Write Stage B tables and a spend table in `RESULTS.md` (compare to `estimates.md`).
- **Out of scope:** Stage A rescoring, error clustering, criteria mining (Step 8), changing adapter scoring logic.

## Dependencies

- Step 6 complete: `adapter.py`, `optimize.py`, unit tests green, tiny-budget smokes passed for Luna and Terra ids
- Stage A `results.json` available for trivial baseline reference
- Frozen splits parquet unchanged

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/plan.md` | Transfer eval matrix, B1 vs B1-T question |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md` | Transfer eval rows, Wandb groups, S3 layout |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/estimates.md` | Stage B cost and wall time table |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py` | Production optimize entrypoint |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/adapter.py` | Scoring for evaluate pass |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/metrics.py` | Test metrics and dev-F1 |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/evaluate.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests/test_evaluate.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/outputs/**` (runtime artifacts)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md` (append Stage B section only)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/**`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/**`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/cohort.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py`
- `/workspace/pyproject.toml`
- `/workspace/webapp/**`

## Production optimize registry

| tmux window | `--ablation-id` | Reflection LM | `max_reflection_cost` | `max_metric_calls` |
|-------------|-----------------|---------------|----------------------|-------------------|
| `b1` | `B1_gepa_pair` | `openai/gpt-6-luna` | `5.0` | `9000` |
| `b1t` | `B1T_gepa_pair_terra` | `openai/gpt-5.6-terra` | `20.0` | `9000` |
| `b2` | `B2_gepa_original` | `openai/gpt-6-luna` | `5.0` | `9000` |
| `b3` | `B3_gepa_mirror` | `openai/gpt-6-luna` | `5.0` | `9000` |
| `b4` | `B4_gepa_asymmetric_reward` | `openai/gpt-6-luna` | `5.0` | `9000` |

Each process sets `rate_cap_per_min=200` inside `optimize.py` (total 1,000 across five processes).

## Transfer eval registry (fixed prompts, no new optimization)

| Transfer id | Prompt source ablation | Scoring view | Splits |
|-------------|------------------------|--------------|--------|
| `transfer_B1_on_original` | `B1_gepa_pair` selected candidate | `original` | dev, test |
| `transfer_B1_on_mirror` | `B1_gepa_pair` selected candidate | `mirror` | dev, test |
| `transfer_B2_on_mirror` | `B2_gepa_original` selected candidate | `mirror` | dev, test |
| `transfer_B3_on_original` | `B3_gepa_mirror` selected candidate | `original` | dev, test |

## Contracts

### `jev_gepa/evaluate.py`

```python
@dataclass(frozen=True)
class EvalConfig:
    ablation_id: str | None  # None for transfer rows
    transfer_id: str | None
    instruction: str
    view: ViewName
    split: Literal["dev", "test"]
    output_dir: Path

def load_selected_instruction(ablation_id: str) -> str:
    """Read instruction text from dev_selection.json + candidates list for that ablation."""

def evaluate_instruction(config: EvalConfig) -> dict[str, Any]:
    """
    Score all posts in split once with fixed instruction via jev_scorer.run_scoring_pass(
        ..., view=config.view, instruction=config.instruction, ablation_id=config.ablation_id or ""
    ) or equivalent batched calls to jev_scorer.score_batch(..., instruction=config.instruction)
    through the shared rate limiter and retries (same path as Stage A and GEPA adapter).
    Build results with shared.metrics.probability_metrics; labels.parquet matches Stage A schema
    (keep_remove_label, p_remove, sample_toxicity_type, split, etc.).
    Write labels.parquet, requests.parquet (Step 4 schema: latency_ms, latency_per_post_ms,
    input_tokens, output_tokens, estimated_cost_usd, instruction_sha256, etc.), and results.json under output_dir.
    Latency and cost in results.json read from requests.parquet column names above.
    Wandb: wandb_tracking.init_run(group jev_gepa, job_type evaluate); config includes transfer_id when set.
    Rate cap: MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT for single-process eval, or 200 when noted for parallel optimize only.
    """

def compare_b1_b1t() -> dict[str, Any]:
    """Return nested dict keyed by ablation_id (B1_gepa_pair, B1T_gepa_pair_terra) with dev_f1, test_f1, reflection_cost_usd."""

def main(argv: list[str] | None = None) -> None:
    """CLI: --ablation-id for primary test read; --transfer-id for transfer eval; --split dev|test."""
```

Primary test read output path:

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/outputs/<ablation_id>/test_eval/
```

Transfer output path:

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/outputs/transfers/<transfer_id>/<split>/
```

`final_prompt.txt` per ablation:

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/outputs/<ablation_id>/final_prompt.txt
```

S3 mirror prefix:

```text
s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/
```

## Tests to write first

### `jev_gepa/tests/test_evaluate.py`

Class `TestLoadSelectedInstruction`, `TestEvaluateInstruction`, `TestCompareB1B1t`.

```text
given dev_selection.json with selected_candidate_idx 2 and three candidates on disk
when load_selected_instruction
then returned string equals candidates[2].instruction

given FakeJevBatchScorer from jev_gepa.tests.fakes patched into jev_scorer.score_batch and evaluate_instruction on test split with two posts
when evaluate_instruction completes
then results.json headline_split is test
and labels.parquet row count equals test split size
and requests.parquet has columns latency_ms, latency_per_post_ms, estimated_cost_usd, instruction_sha256
and score_batch received instruction=config.instruction

given transfer config transfer_B1_on_original
when evaluate_instruction
then view is original
and instruction comes from B1_gepa_pair selected candidate

given mocked results for B1 and B1T with different dev F1 and reflection costs
when compare_b1_b1t
then each ablation entry has keys dev_f1, test_f1, reflection_cost_usd
```

## Implementation order

One Git commit per unit. Full auto.

1. Scaffold `evaluate.py` and `test_evaluate.py`.
2. Implement `load_selected_instruction` and `evaluate_instruction` until tests pass.
3. Implement `compare_b1_b1t` helper.
4. Launch five tmux optimize processes (production `max_metric_calls=9000`).
5. After all five complete: write `final_prompt.txt` per ablation from dev-selected candidate.
6. Run one test eval per ablation (`job_type=evaluate`).
7. Run eight transfer eval commands (four transfer ids times dev and test).
8. Upload all `jev_gepa/outputs/` artifacts to S3.
9. Append Stage B and spend tables to `RESULTS.md`.

## Commands

Unit tests:

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests/test_evaluate.py -q
```

Expected: exit 0.

### Parallel GEPA production (tmux)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

SESSION=jev-gepa-stage-b
tmux -f /exec-daemon/tmux.portal.conf has-session -t "=$SESSION" 2>/dev/null || \
  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$SESSION" -c /workspace

for WIN AB in \
  "b1 B1_gepa_pair" \
  "b1t B1T_gepa_pair_terra" \
  "b2 B2_gepa_original" \
  "b3 B3_gepa_mirror" \
  "b4 B4_gepa_asymmetric_reward"; do
  set -- $WIN
  tmux -f /exec-daemon/tmux.portal.conf new-window -t "$SESSION" -n "$1" -c /workspace 2>/dev/null || true
  tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$SESSION:$1" \
    "export AWS_ACCESS_KEY_ID=\"\$LAB_AWS_ACCESS_KEY_ID\"; export AWS_SECRET_ACCESS_KEY=\"\$LAB_AWS_ACCESS_KEY_SECRET\"; PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py --ablation-id $2" C-m
done
```

Monitor:

```bash
tmux -f /exec-daemon/tmux.portal.conf ls
# Poll until each window command exits 0 and dev_selection.json exists for all five ablations
for AB in B1_gepa_pair B1T_gepa_pair_terra B2_gepa_original B3_gepa_mirror B4_gepa_asymmetric_reward; do
  test -f experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/outputs/$AB/dev_selection.json
done
echo "all five GEPA runs complete"
```

Expected: all five `dev_selection.json` files exist; each `gepa_run/gepa_result.json` has `total_metric_calls` near 9000.

### Test reads (once per ablation)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

for AB in B1_gepa_pair B1T_gepa_pair_terra B2_gepa_original B3_gepa_mirror B4_gepa_asymmetric_reward; do
  PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/evaluate.py \
    --ablation-id "$AB" \
    --split test
done
```

Expected: five `test_eval/results.json` files; test split row counts match Stage A test (~2,988).

### Transfer evals

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

for TID in transfer_B1_on_original transfer_B1_on_mirror transfer_B2_on_mirror transfer_B3_on_original; do
  for SPLIT in dev test; do
    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/evaluate.py \
      --transfer-id "$TID" \
      --split "$SPLIT"
  done
done
```

Expected: eight transfer result folders under `jev_gepa/outputs/transfers/`.

### B1 vs B1-T comparison

```bash
PYTHONPATH=. uv run python -c "
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate import compare_b1_b1t
import json
print(json.dumps(compare_b1_b1t(), indent=2))
"
```

Expected: JSON with `B1_gepa_pair` and `B1T_gepa_pair_terra` dev F1, test F1, and `reflection_cost_usd`.

### S3 upload

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
from pathlib import Path
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts import upload_under_prefix
prefix = 'experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/'
root = Path('experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/outputs')
for path in root.rglob('*'):
    if path.is_file():
        upload_under_prefix(path, prefix)
print('uploaded jev_gepa outputs')
"
```

Expected: S3 lists objects under `jev_gepa/B1_gepa_pair/`, `jev_gepa/B1T_gepa_pair_terra/`, transfers, and `final_prompt.txt` files.

## RESULTS.md Stage B template

Append to `experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md`.

```markdown
## Stage B: Jev + GEPA (test split, threshold 0.5, positive class remove)

| Ablation | View | Dev F1 (selected) | Test F1 | Test ROC-AUC | Reflection LM | Reflection cost USD |
| --- | --- | --- | --- | --- | --- | --- |
| B1_gepa_pair | pair | 0.0000 | 0.0000 | 0.0000 | openai/gpt-6-luna | 0.00 |
| B1T_gepa_pair_terra | pair | 0.0000 | 0.0000 | 0.0000 | openai/gpt-5.6-terra | 0.00 |
| B2_gepa_original | original | 0.0000 | 0.0000 | 0.0000 | openai/gpt-6-luna | 0.00 |
| B3_gepa_mirror | mirror | 0.0000 | 0.0000 | 0.0000 | openai/gpt-6-luna | 0.00 |
| B4_gepa_asymmetric_reward | pair (asymmetric train) | 0.0000 | 0.0000 | 0.0000 | openai/gpt-6-luna | 0.00 |

### B1 vs B1-T (stronger reflection ablation)

| Metric | B1_gepa_pair | B1T_gepa_pair_terra | Delta (Terra - Luna) |
| --- | --- | --- | --- |
| Dev F1 | 0.0000 | 0.0000 | 0.0000 |
| Test F1 | 0.0000 | 0.0000 | 0.0000 |
| Reflection cost USD | 0.00 | 0.00 | 0.00 |

### Transfer evals (test split F1)

| Transfer | Prompt source | Scoring view | Test F1 |
| --- | --- | --- | --- |
| B1 on original | B1_gepa_pair | original | 0.0000 |
| B1 on mirror | B1_gepa_pair | mirror | 0.0000 |
| B2 on mirror | B2_gepa_original | mirror | 0.0000 |
| B3 on original | B3_gepa_mirror | original | 0.0000 |

## Spend vs estimates.md

| Item | Actual USD | estimates.md |
| --- | --- | --- |
| Stage A Jev | 0.00 | ~0.93 |
| Stage B Jev (5 runs) | 0.00 | ~4.35 |
| Luna reflection (4 runs) | 0.00 | ~1.80 to ~3.00 (cap 20 total) |
| Terra reflection (B1-T) | 0.00 | ~10 to ~17 (cap 20) |
| Transfer evals | 0.00 | <0.10 |
| **Project total** | **0.00** | **~17 to ~26 (hard ceiling ~46)** |
```

## Must pass

- Five GEPA runs complete with `max_metric_calls=9000` and `seed=20260924`.
- Final prompt per ablation chosen by dev F1, not val aggregate alone.
- Exactly one test eval per ablation before any RESULTS.md Stage B numbers.
- Eight transfer eval folders exist (dev and test for each transfer id).
- B1 vs B1-T table includes F1 and reflection cost.
- Wandb runs use group `jev_gepa` with `job_type=optimize` or `evaluate`.
- Combined Jev rate across five processes stays at or below 1,000 requests per minute.
- Total spend at or below ~$46 project cap.
- S3 upload covers run dirs, candidates, and `final_prompt.txt`.

## Must fail

- Second test eval on the same ablation after RESULTS.md is written (test set touched twice).
- Running transfer evals before parent ablation `dev_selection.json` exists.
- Selecting candidate using test F1.
- Exceeding `max_reflection_cost` caps ($5 Luna, $20 B1-T) without aborting the run.
- Starting Step 8 analysis before Stage B artifacts exist.

## Commit messages

1. `feat(jev-gepa): add GEPA evaluate runner for test and transfer reads`
2. `feat(jev-gepa): run production GEPA B1_gepa_pair`
3. `feat(jev-gepa): run production GEPA B1T_gepa_pair_terra`
4. `feat(jev-gepa): run production GEPA B2_gepa_original`
5. `feat(jev-gepa): run production GEPA B3_gepa_mirror`
6. `feat(jev-gepa): run production GEPA B4_gepa_asymmetric_reward`
7. `feat(jev-gepa): test eval and transfer evals for Stage B`
8. `docs(jev-gepa): Stage B RESULTS.md tables and spend summary`

## Implement-from-spec notes

Phase 1 names `jev_gepa/evaluate.py` `main` as the caller for post-optimize scoring; optimize production uses `optimize.py` `main`. Phase 2 scaffolds `evaluate.py` and tests. Phase 3 locks `EvalConfig` and the transfer registry. Phase 4 writes `test_evaluate.py`. Phase 5 builds evaluate helpers, then runs production orchestration commits. Phase 6 is complete when all five optimizations, test reads, transfer evals, S3 upload, and RESULTS.md Stage B are done.
