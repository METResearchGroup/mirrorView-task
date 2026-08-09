# Step 1: Freeze scoring contract and pure helpers

## Goal

Add a pure attention-check scorer and frozen option catalog in `/workspace/webapp/public/pre_surveys.js`, with Node-runnable unit tests that lock the correct set to the four political statements from the lab mockup. No timeline or UI wiring in this step.

## Caller / unit of work

**Main caller (this step):** Node test harness importing helpers from `pre_surveys.js`.

1. Export option ids/labels and the correct id set as frozen constants.
2. Export `scorePoliticalExpressionAttentionCheck(selectedIds)` → `{ passed: 0|1, selected: string }`.
3. Tests cover exact pass, missing political option, extra non-political option, empty selection, and order-independence.

**Out of scope:** DOM/HTML trial object; `main.js` timeline; CSS; screenshots; Lambda.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/webapp/public/pre_surveys.js` | Existing `determinePartyGroup` + `module.exports` pattern to extend |
| `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_ui.png` | Canonical option wording + correct selections |
| `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/plan.md` | Pass-always / filter-later policy |

## Files allowed to change

- `/workspace/webapp/public/pre_surveys.js` (add constants + scorer + extend `module.exports` only; do not alter `politicalAffiliation` behavior)
- `/workspace/webapp/public/pre_surveys_attention_check.test.js` (create; Node assert tests)

## Files forbidden to change

- `/workspace/webapp/public/main.js`
- `/workspace/webapp/public/index.html`
- `/workspace/webapp/public/meriel.css`
- `/workspace/webapp/lambdas/**`
- `/workspace/scripts/**`

## Contracts to freeze

### Option catalog (exact strings)

| Id | Label | Political? |
|----|-------|------------|
| `Q1` | `I thought the new ice cream place was pretty good but not great.` | no |
| `Q2` | `Hot take: Winter is simply the best season. I can't wait for the cold weather.` | no |
| `Q3` | `I support Democrats' positions to protect basic human rights.` | yes |
| `Q4` | `It's so awful how Texas is taking away Women's rights. I won't stand for it any longer!` | yes |
| `Q5` | `It completely breaks my heart to see how immigrants are treated these days.` | yes |
| `Q6` | `I stand with Republicans who support our second amendment rights.` | yes |

### Correct set

Exact set equality with `{Q3, Q4, Q5, Q6}`. Any missing yes-option or any selected no-option → fail.

### Function signature

```text
scorePoliticalExpressionAttentionCheck(selectedIds: string[] | iterable) ->
  { passed: 0 | 1, selected: string }
```

- `selected`: sorted unique ids joined with `|` (e.g. `Q3|Q4|Q5|Q6`). Empty → `""`.
- `passed`: `1` only on exact set match; otherwise `0`.
- Unknown ids in input → fail (`passed: 0`); still include them in `selected` for audit.
- Do **not** throw on bad input; coerce non-arrays to empty.

### Export surface

Extend existing:

```text
module.exports = {
  politicalAffiliation,
  determinePartyGroup,
  ATTENTION_CHECK_OPTIONS,           // frozen array of { id, label, isPolitical }
  ATTENTION_CHECK_CORRECT_IDS,       // frozen Set or sorted array ['Q3','Q4','Q5','Q6']
  scorePoliticalExpressionAttentionCheck,
};
```

## Exact commands

```bash
cd /workspace

node --test webapp/public/pre_surveys_attention_check.test.js
```

**Expected:** all tests pass; exit code `0`.

Failing-first check before implementation (optional but preferred for TDD):

```bash
# After adding failing tests but before scorer exists:
node --test webapp/public/pre_surveys_attention_check.test.js
# Expected: FAIL (module missing export / assertion failures)
```

Manual contract smoke:

```bash
node -e "
const {
  scorePoliticalExpressionAttentionCheck,
  ATTENTION_CHECK_CORRECT_IDS,
} = require('./webapp/public/pre_surveys.js');
const ok = scorePoliticalExpressionAttentionCheck(['Q6','Q3','Q5','Q4']);
const bad = scorePoliticalExpressionAttentionCheck(['Q1','Q3','Q4','Q5','Q6']);
console.log(ok, bad);
if (ok.passed !== 1 || ok.selected !== 'Q3|Q4|Q5|Q6') process.exit(1);
if (bad.passed !== 0) process.exit(1);
console.log('scorer OK');
"
```

**Expected stdout ends with:** `scorer OK`

## Pass / fail for this step

**Pass when:**

1. `node --test webapp/public/pre_surveys_attention_check.test.js` exits 0.
2. Correct set is exactly Q3–Q6 with the frozen label strings above.
3. `politicalAffiliation` still exports and behaves unchanged (no edit to its `on_finish` beyond untouched).
4. No changes under `main.js` / `index.html`.

**Fail if:**

1. Scoring uses fuzzy/substring matching instead of id set equality.
2. Failures throw or block (there is no UI yet, but scorer must not throw).
3. Tests only cover the happy path.

## Screenshots

Not required in this step (no UI). Reference mockup remains `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_ui.png`.
