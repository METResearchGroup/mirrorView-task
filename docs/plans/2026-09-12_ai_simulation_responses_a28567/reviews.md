# Reviews for the issue 290 plan

The reviews below were applied to the draft. The plan in this folder already includes the accepted cuts.

## Simplicity

### Bottom line

`acceptable`

Issue 290 already asks for four prompt variants, four models, a cost gate, and an error analysis. The plan keeps that shape and refuses extra machinery. Shared code is one runner. Experiment folders are thin wrappers plus reports.

### What seems solid

- One cohort, one schema, one scorer.
- Cost smoke and the experiment 2 prompt are hard gates.
- Campaign parquet layout is copied from the separability experiment, not redesigned.
- Experiment 5 uses counts on existing fields.

### What seems unproven or overbuilt

- Sixteen full labeling jobs are expensive, but the issue named those jobs. The plan does not add a fifteenth model or a per-pair call pattern that would multiply cost by 20.
- Pytest under an experiment folder is an exception to `UNIT_TESTING_STANDARDS.md`. It is there because a 0-based index bug would invalidate every score, not because a test framework was wanted for its own sake.

### Simpler version I would ship

Keep the shared-runner design in `plan.md`. Do not add a prompt-strategy interface, a plugin registry, a second schema, or significance tests. Do not spawn 16 implementation subagents for scaffolding. Parallel Cursor Grok High subagents start only in Step 3, after approval, and only one per experiment.

### Follow-up questions

None that block the plan. The issue's "1,000 rows" is pinned as 1,000 participants. If that was meant as 1,000 trial rows, the cost and the user-level tables change, and the user should say so on this pull request.

## Persona used

### `agents/personas/research/methodology/domain_specific/experimental_design_expert.md`

Selected because issue 290 is a prompt ablation against human keep/remove labels, not an infrastructure ticket.

### `agents/personas/ai_engineering/task_specific/model_performance_analysis_expert.md`

Selected as the second persona because the work is an evaluation: precision, recall, F1, slices, and error analysis.

## Findings (highest severity first)

### Issue: humans judged one pair at a time, the model sees 20 pairs in one prompt

Impact: a model that looks consistent across the 20 pairs is not doing the same task the participant did. Comparing F1 still answers "can this prompt match the labels," but it is not a process match.

Recommended fix: keep one call per user, because 20 calls per user times four experiments times four models would multiply the API bill by 20. State the mismatch in every `SETUP.md`. `plan.md` already records that limit.

### Issue: first 1,000 completers are not a random sample

Impact: early Prolific completers can differ from later ones. External claims should stay inside this cohort.

Recommended fix: record `source_file_epoch_ms` range and drop counts in `SETUP.md`. Do not reweight.

### Issue: user-level means and pooled post-level scores can disagree

Impact: reporting only one of them would hide majority-class behavior or hide users with extreme remove rates.

Recommended fix: keep both tables, and never label pooled F1 as user-level F1. Step 4 states the same rule.

### Issue: experiments 1 to 4 are not a causal test of demographics or reflection

Impact: a higher F1 in experiment 4 does not prove that demographics caused better simulation. The same people and the same posts are reused.

Recommended fix: describe them as prompt ablations. Do not add causal language to `RESULTS.md`.

### Issue: the issue's experiment 5 wording lists false negatives twice

Impact: 150 posts of one error type would duplicate the first list.

Recommended fix: 75 false negatives and 75 false positives, called out in `plan.md` so the user can correct it.

## Open questions / assumptions

- Language, employment, and social-media survey items are not in `columnsToKeep`, so experiment 2 cannot include them.
- `scripts/export_study_results.py` expects 190 files. The live complete-user count may be under 1,000.
- Qwen and Claude token prices are pinned from the Bedrock list and Marketplace page. Smoke token counts still drive the dollar table.

## Suggested next actions

1. Approve or correct the 1,000-participant reading and the 75 / 75 error split on this pull request.
2. Approve the experiment 2 template in `steps/step1.md` early, so Step 2 is only a filled example plus cost.
3. After merge, implement Step 1, then stop at the Step 2 gate.

## Writing cleanup

Passes run on `plan.md` and `steps/`:

1. Plain writing: everyday words, no dashes, no sentence-initial "This/That", no three-clause sentences.
2. Anti-slop: removed importance language and parallel "not X but Y" setup.
3. Humanizer: kept claims, cut staged openers.
4. Osmani: named actors (operator, subagent, scorer), kept the cost gate as the takeaway.
5. Vocabulary: "confirm" instead of "freeze", "run" instead of "invoke", "authoritative" instead of "canonical".
