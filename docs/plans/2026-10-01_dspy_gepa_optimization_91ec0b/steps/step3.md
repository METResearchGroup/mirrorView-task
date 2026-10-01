# Step 3: Build the DSPy program and GEPA metric

## Outcome

This step implements the seed classifier, GEPA feedback metric, balanced reflection sampler, proposal checks, and deterministic evaluation helpers. It verifies these contracts with local examples and fake predictions, so no paid model call is required.

## Caller and happy path

The caller is `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --validate-contracts`.

The command loads only the optimization and GEPA validation splits, then constructs the seed program and metric. It exercises valid and invalid predictions and samples several balanced reflection batches. It also checks proposal acceptance and rejection. The command must not load development or test data.

## Files

### Inspect

- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/prompts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/config.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/data.py`
- The installed DSPy 3.4.0 and GEPA 0.1.4 optimizer, metric, batch sampler, checkpoint, and program serialization APIs

### Allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/config.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/program.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/metric.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/evaluation.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py`

### Forbidden to change

- The issue 329 prompt and fixed examples
- `EXCLUDELIST_POST_IDS`, split membership, and uploaded input objects
- Step 1's model and telemetry settings
- Any test file or test directory
- Development or test artifacts

## Program and metric contracts

1. The seed program imports the issue 329 prompt and contains exactly 10 fixed demonstrations, with five keep and five remove examples.
2. GEPA may edit only the classifier instruction. Input names, output names, types, demonstrations, model settings, and threshold remain fixed.
3. Each fixed demonstration contains `is_remove` and `p_remove`. Use `p_remove=1.0` for a remove example and `p_remove=0.0` for a keep example because issue 329 supplies labels but no probabilities.
4. Derive the scored prediction from `p_remove >= 0.5`. Require the returned Boolean to agree with the derived prediction. Treat disagreement, a missing field, a nonfinite value, or a probability outside 0 to 1 as a contract failure.
5. Treat remove as the positive class. The metric score is 1.0 only when the prediction is correct and the output contract passes. Otherwise the score is 0.0.
6. Return GEPA feedback that states the gold label, predicted label, reported probability, and contract failure. Do not include test data or unsupported reasoning about the author.
7. Each reflection batch contains one deterministic keep row and one deterministic remove row from the optimization split. Confirm the GEPA 0.1.4 custom sampler API and set the direct reflection batch size option so the custom sampler controls the batch.
8. Use all five remove rows and five deterministically selected keep rows as the fixed balanced GEPA validation set.
9. Reject a candidate instruction if it changes the required contract, contains a 40-character span from an optimization post after whitespace normalization, or exceeds 125% of the seed instruction length.
10. Configure strict improvement, a fixed seed, `track_stats=True`, checkpoint storage, no prompt merge, and `candidate_selection_strategy="current_best"`. Let Weave trace the optimizer and keep GEPA's separate W&B integration off so one telemetry system owns the call record.
11. Break an exact validation score tie by shorter instruction length, then by the earlier candidate index.

## Implementation sequence

1. Convert the 10 prompt examples into fixed DSPy examples without duplicating their text outside the shared prompt module more than necessary.
2. Implement the seed module with one predictor and the confirmed language model settings.
3. Implement response parsing and validation before the metric. Keep the threshold in one configuration constant.
4. Implement hard correctness and plain feedback as the GEPA metric result.
5. Implement the balanced reflection sampler with deterministic class-specific cursors and seed-controlled reshuffling.
6. Build the fixed balanced validation subset and record its 10 post IDs in run configuration, not in a new source constant.
7. Implement proposal checks as pure functions. Log one reason for each rejected candidate and all applicable reasons when more than one check fails.
8. Implement metric aggregation for accuracy, precision, recall, and F1 with remove as positive. Define zero-denominator behavior explicitly as 0.0.
9. Add the local contract mode to the optimizer caller. It must check valid output, threshold boundaries, Boolean disagreement, invalid probabilities, metric feedback, batch balance, copied text, prompt length, and deterministic tie breaking.

## Smoke verification

```bash
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --validate-contracts
```

Expected output. The command reports 10 fixed demonstrations and a 10-row balanced validation set. Every sampled reflection batch has one keep and one remove. The output and metric checks pass, and copied, oversized, and contract-breaking prompts have the expected rejection reasons. The command reports zero paid calls and confirms that it did not load development or test data.

## Pass and stop conditions

Pass only when every local contract check succeeds, repeated runs select the same balanced validation IDs and batches, the threshold and positive class have one source of truth, and the command makes no paid call.

Stop if GEPA 0.1.4 cannot accept the required sampler or checkpoint settings. Also stop if GEPA can edit demonstrations or output fields, a malformed result can receive credit, a proposal check can read test data, or a repeated contract run changes its IDs or decisions.

## Commit

Suggested commit message. `experiment: add DSPy classifier and GEPA feedback`
