# Step 6: Read the traces with bag of words, then write results

## Scope

- **Caller:** `experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py` `main`
- **Task:** Score stored thinking traces from experiments 1 and 2 with the confirmed marker lists. Compare groups. Compare the two prompt arms on matched posts. Write `RESULTS.md` with the four experiment tables.
- **Out of scope:** New model runs, changing the marker lists after they are committed, editing the website, F1 scoring.

## Dependencies

Experiment 1 and experiment 2 traces exist. Experiment 3 wrote `response_time_summary.csv`. Load traces from the experiment output folders or the matching S3 objects.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md` | Marker families, experiment 2 versus experiment 1 comparison |
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/src/bow_tokens.py` | Import `tokenize_feature_value`. Do not copy the tokenizer. |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment1/summarize.py` | Token summary shape |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment3/summarize.py` | Human time summary shape |
| `/workspace/AGENTS.md` | `RESULTS.md` is tables and short statements |

## Files allowed to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment4/__init__.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment4/markers.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment4/summarize.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/RESULTS.md` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_score_markers.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/SETUP.md` (add the experiment 4 command only)

## Files forbidden to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/README.md`
- `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/src/bow_tokens.py`
- `/workspace/webapp/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md`
- Experiment 1, 2, and 3 trace and summary objects already uploaded
- Objects under `s3://jspsych-mirror-view-2026-09-09/`

## Marker contract

Score `thinking_text` on rows with `status=valid`. Lowercase the text before phrase search.

Confirmed phrase lists, matched as substrings of the lowercased thinking text:

- uncertainty phrases: `not sure`, `hard to say`, `on the other hand`, `could go either`, `i am unsure`, `i'm unsure`
- revision phrases: `on second thought`, `changed my mind`, `first i thought`, `i initially`
- tension phrases: `double standard`, `both posts`, `same standard`, `different standard`

Confirmed token lists, matched after `tokenize_feature_value(thinking_text)`:

- uncertainty tokens: `maybe`, `perhaps`, `unsure`, `uncertain`, `borderline`, `ambiguous`, `conflicted`, `however`, `probably`, `possibly`
- revision tokens: `wait`, `actually`, `reconsider`, `initially`, `instead`
- tension tokens: `tension`, `contradiction`, `conflict`, `inconsistent`, `opposite`, `conflicting`

A family flag is true when any phrase in that family matches or any token in that family is present. Do not add markers later without editing `markers.py` and this step file.

`score_trace(thinking_text)` returns a frozen `MarkerScore` with booleans `uncertainty`, `revision`, and `tension`.

`marker_rates(traces)` writes, for each `prompt_arm` × `model_id` × `group`, the fraction of valid traces with each family flag, plus `n_valid`.

`paired_arm_comparison(exp1, exp2)` inner-joins on `post_id` and `model_id` where both rows are `valid`, then writes mean thinking-token difference (experiment 2 minus experiment 1) and mean flag difference for each family, grouped by `model_id` and `group`.

Do not score `completion_text`. Do not tokenize with a different regex.

## Results file contract

Write `/workspace/experiments/reasoning_during_moderation_2026_09_15/RESULTS.md`.

The file must include:

1. A short title and the export metadata (`since_date`, `csv_files`, the three group counts).
2. Experiment 1 six-row token table, copied from `experiment1/outputs/token_summary.csv`.
3. Experiment 2 six-row token table, copied from `experiment2/outputs/token_summary.csv`.
4. Experiment 3 six-row human time table, copied from `experiment3/outputs/response_time_summary.csv`.
5. Experiment 4 marker-rate table and the paired arm comparison table.
6. One paragraph that states whether experiment 2 thinking-token means are lower than experiment 1 on the matched valid rows, by model and group. Use the paired table. Do not claim accuracy.

Say that F1 and accuracy were not measured.

Local experiment 4 paths:

```text
experiments/reasoning_during_moderation_2026_09_15/experiment4/outputs/marker_rates.csv
experiments/reasoning_during_moderation_2026_09_15/experiment4/outputs/arm_comparison.csv
```

S3 keys under `s3://mirrorview-experimental-artifacts/experiments/reasoning_during_moderation_2026_09_15/experiment4/`.

## Pytest files

### `tests/test_score_markers.py`

Class `TestScoreTrace` and class `TestPairedArmComparison`.

```text
given thinking_text "I am not sure. wait, the posts conflict."
when score_trace
then uncertainty is true
and revision is true
and tension is true

given thinking_text "Allow both."
when score_trace
then all three flags are false

given tokenize_feature_value stopwords
when score_trace on "maybe the original is fine"
then uncertainty is true because maybe is a token
and tension is false because original is a meta token dropped by tokenize_feature_value
and "the original" is not a tension phrase

given matched valid rows where experiment 2 count is 8 and experiment 1 count is 10
when paired_arm_comparison
then mean thinking-token difference is -2
```

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py
```

Expected stdout includes `wrote_results=true` and paths for both csv files. `RESULTS.md` exists and contains four experiment headings.

Pytest, full experiment suite:

```bash
PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests -q
```

Expected: exit 0.

## Must pass

- Marker lists in `markers.py` match this step file exactly.
- `tokenize_feature_value` is imported, not copied.
- `RESULTS.md` has the four tables and no F1 table.
- Pairwise comparison uses matched `post_id` and `model_id`.

## Must fail

- Scoring completion text instead of thinking text.
- Adding extra markers in `run.py` that are not in `markers.py`.
- Copying `bow_tokens.py`.
- Claiming a keep or remove accuracy number.
- Rewriting `README.md`.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `experiment4/run.py` `main` as the caller.

Phase 2 scaffolds `markers.py`, `summarize.py`, and `run.py`.

Phase 3 locks `MarkerScore` and the two output tables.

Phase 4 writes `test_score_markers.py`.

Phase 5 implements `score_trace`, then `marker_rates`, then `paired_arm_comparison`, then `RESULTS.md` writing.

Phase 6 is complete when the full shared pytest command exits 0 and `RESULTS.md` is written from the tables.
