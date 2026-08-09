# Step 3: Insert into the study timeline and persist export columns

## Goal

Wire `politicalExpressionAttentionCheck` into the MirrorView timeline immediately after political affiliation and before participant-id assignment, and ensure `attention_check_passed` / `attention_check_selected` survive CSV creation via the column allowlist. Failures never alter control flow.

## Caller / unit of work

**Main caller:** `/workspace/webapp/public/main.js` → `setupExperiment` timeline assembly (the block that currently does `timeline.push(politicalAffiliation)`).

1. After `timeline.push(politicalAffiliation)`, push `politicalExpressionAttentionCheck`.
2. Extend `columnsToKeep` with `attention_check_passed` and `attention_check_selected` (place near `party_group`).
3. Confirm existing `flattenResponses` + `addProperties` path already spreads the fields onto later trials (same as `party_group`).
4. Do not add any `conditional_function` / branch that ends the experiment on fail.

**Out of scope:** changing assignment Lambda payloads; filtering inside `scripts/export_study_results.py`; live screenshot capture (Step 4).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/webapp/public/main.js` | Timeline order (~L449–456) and `columnsToKeep` (~L129–175) |
| `/workspace/webapp/public/pre_surveys.js` | Trial export from Step 2 |
| `/workspace/webapp/public/index.html` | Script load order (`pre_surveys.js` before `main.js`) |
| `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_data_field.png` | Target data-field appearance |
| `/workspace/scripts/export_study_results.py` | Confirm no schema allowlist that would drop unknown columns (read-only; do not change unless a hard drop is discovered) |

## Files allowed to change

- `/workspace/webapp/public/main.js` (timeline insert + `columnsToKeep` only)
- `/workspace/docs/runbooks/MANUAL_TESTING.md` (optional one-line note: attention check appears after party; always continue; filter on `attention_check_passed` later)

## Files forbidden to change

- `/workspace/webapp/lambdas/**`
- `/workspace/webapp/public/consent.js`
- `/workspace/webapp/public/plugins/**`
- Scoring/option constants in `/workspace/webapp/public/pre_surveys.js` (already frozen in Steps 1–2; only touch if a wiring bug requires a one-line fix)
- `/workspace/scripts/export_study_results.py` (unless inspection proves columns are stripped — then document the finding and stop for plan revision)

## Contracts to freeze

### Timeline order (pre-task prefix)

1. Welcome
2. Consent
3. Political affiliation
4. **Political expression attention check** ← insert
5. Assign participant id
6. Fetch assigned posts
7. Condition instructions → practice → main trials → …

### CSV columns (append to allowlist)

- `attention_check_passed`
- `attention_check_selected`

### Behavior on fail

Identical path to pass: next timeline node runs. No alert, no redirect, no early `on_finish` termination.

## Exact commands

Static wiring checks (no browser):

```bash
cd /workspace

# Timeline insert present after politicalAffiliation
node -e "
const fs = require('fs');
const src = fs.readFileSync('webapp/public/main.js','utf8');
const iParty = src.indexOf('timeline.push(politicalAffiliation)');
const iAtt = src.indexOf('timeline.push(politicalExpressionAttentionCheck)');
if (iParty < 0) throw new Error('politicalAffiliation push missing');
if (iAtt < 0) throw new Error('attention check push missing');
if (iAtt < iParty) throw new Error('attention check must come after politicalAffiliation');
if (!src.includes(\"'attention_check_passed'\" ) && !src.includes('\"attention_check_passed\"')) {
  // allow either quote style in array
}
if (!/attention_check_passed/.test(src) || !/attention_check_selected/.test(src)) {
  throw new Error('columnsToKeep missing attention check fields');
}
// Ensure no fail-abort pattern introduced nearby
const abortHits = src.match(/attention_check_passed[^\n]{0,80}endExperiment/g);
if (abortHits) throw new Error('found endExperiment tied to attention check');
console.log('timeline + columns OK');
"

node --test webapp/public/pre_surveys_attention_check.test.js
```

**Expected:**

```text
timeline + columns OK
# … tests pass …
```

Optional local serve smoke (if implementing agent has a static server):

```bash
cd /workspace/webapp/public && python3 -m http.server 8765
# Open http://127.0.0.1:8765/?PROLIFIC_PID=manual-test-attention-1
# Walk Welcome → Consent (agree) → Party → Attention check → confirm Continue advances
```

## Pass / fail for this step

**Pass when:**

1. Attention check is the next trial after political affiliation.
2. Both new columns are in `columnsToKeep`.
3. No code path ends the experiment based on `attention_check_passed === 0`.
4. Step 1–2 tests still pass.
5. Lambdas untouched.

**Fail if:**

1. Attention check is placed after instructions/practice (too late) or before consent.
2. Columns omitted (fields would be scored but stripped from CSV).
3. Export script changed without necessity.

## Screenshots

Not live yet. Confirm plan mockups still present:

- `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/before/no_attention_check_timeline.png`
- `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_ui.png`
- `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_data_field.png`

Step 4 replaces the after images with live captures.
