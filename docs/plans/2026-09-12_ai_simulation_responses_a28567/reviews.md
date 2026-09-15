# Reviews for the issue 290 plan

The reviews below were applied to the draft. The plan in the folder already includes the accepted cuts.

## Simplicity

### Bottom line

`acceptable`

Issue 290 already asks for four prompt variants, four models, a cost gate, and an error analysis. The packet keeps the issue's shape and adds one later process-match run. Experiment 6 repeats experiment 1 with one unnumbered pair per call. Shared code is one runner. Experiment folders are thin wrappers plus reports. Derived files use the same S3 bucket and path-equals-local-key rule as the other September 2026 experiments. Experiment 6 has its own cost file and approval gate, so it does not reopen the parent `COST_ESTIMATE.md`.

### What seems solid

- One cohort, the 20-pair schema plus a yes/no schema for experiment 6, and one scorer.
- Cost smoke and the experiment 2 prompt are hard gates.
- Campaign parquet layout is copied from the separability experiment.
- S3 keys copy the local tree under `experiments/ai_simulation_responses_2026_09_11/`. One helper, `put_new_mirrored`, writes both places. No second object store.
- Experiment 5 uses counts on existing fields. The split is 75 false-negative posts and 75 false-positive posts.

### What seems unproven or overbuilt

- Full labeling for experiments 1 to 4 is sixteen jobs. The jobs are expensive, and the issue named them. Experiment 6 adds 19,960 pair calls per remaining model, against experiment 1 only. The experiment 6 cost file is separate. The packet still omits a fifteenth model and still omits per-pair calls on experiments 2 through 4.
- Pytest under an experiment folder is an exception to `UNIT_TESTING_STANDARDS.md`. It is there because a 0-based index bug would invalidate every score.
- Uploading `COST_ESTIMATE.md` and `RESULTS.md` with `put_new` makes a second write fail. The same immutability already applies to cohort parquet and to presentation parquet in the separability experiment. A later score fix needs a deleted S3 key, which the plan does not add a command for.

### Simpler version I would ship

Keep the shared-runner design in `plan.md`. Do not add a prompt-strategy interface, a plugin registry, or significance tests. Experiment 6 needs a yes/no schema next to the existing remove-index schema. The runner stitches 20 answers back to the experiment 1 row shape. Do not spawn 16 implementation subagents for scaffolding. Parallel Cursor Grok High subagents start only in Step 3, after approval, and only one per experiment. Experiment 6 labeling is a later three-subagent split after `experiment6/APPROVAL.md`. Do not upload Python, tests, README, or SETUP to S3.

### Follow-up questions

No follow-up questions block the plan. The cohort target is 1,000 complete participants. Experiment 5 takes 75 false negatives and 75 false positives.

## Persona used

### `agents/personas/research/methodology/domain_specific/experimental_design_expert.md`

Selected because issue 290 is a prompt ablation against human keep/remove labels, not an infrastructure ticket.

### `agents/personas/ai_engineering/task_specific/model_performance_analysis_expert.md`

Selected as the second persona because the work is an evaluation of precision, recall, F1, score tables, and error analysis.

## Findings (highest severity first)

### Issue: humans judged one pair at a time, the model sees 20 pairs in one prompt

Impact: a model that looks consistent across the 20 pairs is not doing the same task the participant did. Comparing F1 still answers whether the prompt can match the labels. The comparison is not a process match.

Recommended fix: experiments 1 through 4 stay one call per user. State the mismatch in the experiment 1 through 4 `SETUP.md` files. Experiment 6 is the process-match run against experiment 1. Each call shows one unnumbered pair. The answer is JSON yes or no. Prompt content matches experiment 1. The models are OpenAI, Nova Micro, and Qwen. Claude is out. Compare experiment 6 to experiment 1 on the intersection of scored users. Do not add per-pair calls to experiments 2 through 4.

### Issue: first 1,000 completers are not a random sample

Impact: early Prolific completers can differ from later ones. External claims should stay inside the cohort.

Recommended fix: record `source_file_epoch_ms` range and drop counts in `SETUP.md`. Do not reweight. The target remains 1,000 complete participants. If fewer complete users exist, take all of them and record the count.

### Issue: user-level means and pooled post-level scores can disagree

Impact: reporting only one of them would hide majority-class behavior or hide users with extreme remove rates.

Recommended fix: keep both tables, and never label pooled F1 as user-level F1. Step 4 states the same rule.

### Issue: experiments 1 to 4 are not a causal test of demographics or reflection

Impact: a higher F1 in experiment 4 does not prove that demographics caused better simulation. The same people and the same posts are reused.

Recommended fix: describe them as prompt ablations. Do not add causal language to `RESULTS.md`.

### Issue: experiment 5 complementary errors

Impact: 150 posts of one error type would duplicate the first list.

Recommended fix: 75 false-negative posts and 75 false-positive posts. Confirmed.

## Open questions / assumptions

- Language, employment, and social-media survey items are not in `columnsToKeep`, so experiment 2 cannot include them.
- `scripts/export_study_results.py` expects 190 files. The live complete-participant count may be under 1,000. Experiment 6 reuses unique `prolific_id` values from that cohort (998 in the live write) and does not rebuild it.
- Qwen and Claude token prices are pinned from the Bedrock list and Marketplace page. Smoke token counts still drive the dollar table. Experiment 6 uses the same rates for the three remaining models.

## Suggested next actions

1. Approve the experiment 2 template in `steps/step1.md` early, so Step 2 is only a filled example plus cost.
2. After merge, implement Step 1, then stop at the Step 2 gate.

## Writing cleanup

Passes run on `plan.md`, `steps/`, and the pull request description:

1. Plain writing: everyday words, no dashes, no sentence-initial "This/That", no three-clause sentences, colon only for lists.
2. Anti-slop: removed importance language and parallel "not X but Y" setup. Split the experiment 6 pins so each paragraph names one contract.
3. Humanizer: kept claims, cut staged openers and clipped negative tails.
4. Osmani: named actors (operator, subagent, scorer), kept the two cost gates as the takeaway.
5. Vocabulary: "confirm" instead of "freeze", "run" instead of "invoke", "authoritative" instead of "canonical", "tables" instead of "slices".
