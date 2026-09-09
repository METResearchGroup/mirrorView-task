# Step 3: Score labels and write RESULTS.md

## Scope

- **Caller:** the same `run.py` `main` from Step 1, with `--score`
- **Task:** Join each engine `final.parquet` to `presentations.parquet`, write the overall table and the two cell tables, commit `experiments/test_separability_original_mirror_posts_2026_09_09/RESULTS.md`, and add a CHANGELOG line.
- **Out of scope:** pytest, editing the experiment README, relabeling, rewriting presentations, changing product feature code

## Dependencies

Step 2 has written both final parquets. Do not start this step until these objects exist:

- `s3://mirrorview-experimental-artifacts/experiments/test_separability_original_mirror_posts_2026_09_09/outputs/labels/openai/final.parquet`
- `s3://mirrorview-experimental-artifacts/experiments/test_separability_original_mirror_posts_2026_09_09/outputs/labels/bedrock/final.parquet`

A missing final file raises `FileNotFoundError`.

## Files to inspect (read-only)

- `/workspace/docs/plans/2026-09-09_separability_original_mirror_dee07c/plan.md`
- `/workspace/docs/plans/2026-09-09_separability_original_mirror_dee07c/steps/step1.md`
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/score.py`
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/run.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py`
- `/workspace/CHANGELOG.md`

## Files allowed to change

- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/RESULTS.md` (written by `--score`, then committed)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/score.py` (only if a live join shows a bug)
- `/workspace/CHANGELOG.md` after `RESULTS.md` exists

## Files forbidden to change

- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/README.md`
- `/workspace/data_platform/**`
- `/workspace/shared/flip_generation/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/**`
- `/workspace/tests/**`
- `/workspace/docs/plans/2026-09-09_separability_original_mirror_dee07c/**`
- Both final parquet objects
- The presentation S3 object
- The catalog S3 object

## Scoring rules

Join on `source_record_id` = `post_primary_key`. Drop rows whose `human_slot` is missing or not `first` or `second`. Those dropped rows count as failed.

Positive class is 1 when the slot is `first`. `y_true` is 1 when `gold_human_slot` is `first`. `y_pred` is 1 when `human_slot` is `first`.

Call `accuracy_score`, `precision_score`, `recall_score`, and `f1_score` with `zero_division=0`. Format each metric to four decimal places.

Cell columns, left to right: left+low, left+medium, left+high, right+low, right+medium, right+high.

Cell table rows, top to bottom: accuracy, recall, precision, f1.

Map `sample_low_toxicity` to low, `sample_middle_toxicity` to medium, and `sample_high_toxicity` to high. Stance stays `left` or `right`.

Under every table, write `n_scored=` and `n_failed=`. Overall `n_scored` plus `n_failed` equals 10,000 for each engine.

## RESULTS.md contract

Write `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/RESULTS.md` with:

1. The four commands that produced presentations, smokes, full labels, and this score.
2. Pinned catalog URI and SHA-256.
3. Presentation URI and SHA-256.
4. OpenAI model `gpt-5.4-nano` and Bedrock model `us.amazon.nova-micro-v1:0`.
5. One overall markdown table, rows `openai` then `bedrock`, columns accuracy, precision, recall, F1, plus `n_scored` and `n_failed` under the table.
6. One OpenAI cell table, then one Bedrock cell table, with the column and row order above, plus `n_scored` and `n_failed` per cell or under each table.

## CHANGELOG

After `RESULTS.md` is committed, add one dated line to `/workspace/CHANGELOG.md` under `## 2026-09-09`. Say that operators now have OpenAI and Bedrock separability scores for original vs mirror posts on the 10,000-row catalog from pull request 273, and link the pull request that lands this experiment.

## Live command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --score
```

The command prints the overall table and both cell tables, then writes `RESULTS.md`. Copy stdout to `/opt/cursor/artifacts/separability_score.log`.

## Live given / when / then (Phase 4)

```text
given both engine final.parquet objects exist
and presentations.parquet has 10000 rows
when PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --score
then RESULTS.md exists
and the overall table has rows openai and bedrock
and each cell table has columns left+low, left+medium, left+high, right+low, right+medium, right+high
and each cell table has rows accuracy, recall, precision, f1
and n_scored plus n_failed equals 10000 for each engine
and presentations.parquet is unchanged
and both final.parquet objects are unchanged

given openai final.parquet is missing
when the score command is run
then the process raises FileNotFoundError
```

## Must pass

- `--score` exits 0 when both final files exist.
- `RESULTS.md` has the overall table and both cell tables in the stated order.
- `n_scored` plus `n_failed` equals 10,000 per engine.
- `README.md` is unchanged from Step 1.
- Catalog, presentations, and both final parquets are unchanged.
- `CHANGELOG.md` has the new line.

## Must fail

- `--score` when either final parquet is missing.
- Treating original as always human after unshuffling, which would force precision to 1.
- Adding pytest.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then block above. `score.py` already exists from Step 1. Phase 5 is the live `--score` run, then the CHANGELOG line, each as its own commit.

Phase 6 is complete when `RESULTS.md` and the CHANGELOG line are committed.
