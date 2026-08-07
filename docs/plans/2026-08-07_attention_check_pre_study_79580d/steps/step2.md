# Step 2: Build the attention-check trial UI in the pre-survey module

## Goal

Create the jsPsych trial object that renders the Political Expression attention check (callout + select-all checkboxes + Continue), scoring via Step 1 helpers on finish, and writing shared data properties. Do not insert it into the timeline yet.

## Caller / unit of work

**Main caller (this step):** the trial’s own `on_finish` (invoked by jsPsych when the participant continues).

1. Build HTML with title, grey callout with purple left bar, prompt (“Select all that apply”), six checkbox options in fixed order Q1→Q6, Continue button.
2. Use `jsPsychSurveyHtmlForm` (already loaded in `/workspace/webapp/public/index.html`) — do **not** add `plugin-survey-multi-select.js`.
3. On finish: read checked option ids → call `scorePoliticalExpressionAttentionCheck` → `jsPsych.data.addProperties({ attention_check_passed, attention_check_selected })`.
4. Export the trial as `politicalExpressionAttentionCheck`.

**Out of scope:** timeline `push` in `main.js`; `columnsToKeep`; live screenshots; blocking on fail.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/webapp/public/pre_surveys.js` | Step 1 helpers + `politicalAffiliation` HTML/style conventions |
| `/workspace/webapp/public/index.html` | Confirms `plugin-survey-html-form.js` is already loaded |
| `/workspace/webapp/public/meriel.css` | Existing `.multi-select-options` rules; reuse or extend lightly |
| `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_ui.png` | Visual target |
| `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/mockups/attention_check_ui.html` | Markup/style reference for the callout + option cards |

## Files allowed to change

- `/workspace/webapp/public/pre_surveys.js` (add trial object + export it)
- `/workspace/webapp/public/meriel.css` (only if needed for attention-check callout/option classes; keep minimal; prefer inline styles mirroring `politicalAffiliation` if that avoids CSS churn)
- `/workspace/webapp/public/pre_surveys_attention_check.test.js` (optional: assert trial export exists and `data.trial_type` is set)

## Files forbidden to change

- `/workspace/webapp/public/main.js` (timeline insert is Step 3)
- `/workspace/webapp/public/index.html` (no new plugin script)
- `/workspace/webapp/public/consent.js`
- `/workspace/webapp/lambdas/**`
- `/workspace/scripts/export_study_results.py`

## Contracts to freeze

### Trial object

| Field | Value |
|-------|-------|
| Export name | `politicalExpressionAttentionCheck` |
| `type` | `jsPsychSurveyHtmlForm` |
| `button_label` | `Continue` (or `Continue >` to match party survey — pick one and keep consistent with mockup’s “CONTINUE”) |
| `data.trial_type` | `political-expression-attention-check` |
| Require ≥1 selection before submit | yes (HTML `required` on the checkbox group or form validation equivalent) |

### Shared properties written in `on_finish`

| Property | Type | Meaning |
|----------|------|---------|
| `attention_check_passed` | `0` or `1` | Exact correct set |
| `attention_check_selected` | string | Pipe-joined sorted ids from scorer |

**Critical:** do not call `jsPsych.endExperiment`, do not swap stimulus to an error page, do not conditional-timeline on `passed`. Always allow Continue to advance.

### Visual requirements (must match mockup intent)

1. Title: **Political Expression**
2. Callout defining political expression on social media (posts, reposts, comments)
3. Prompt emphasizing: do not judge agreement; select all that apply
4. Six options with exact Step 1 label strings
5. Card-like option rows; checked state visually distinct

## Exact commands

```bash
cd /workspace

node --test webapp/public/pre_surveys_attention_check.test.js
```

**Expected:** exit `0` (Step 1 tests still green; any new export assertions green).

Syntax / export smoke:

```bash
node -e "
const m = require('./webapp/public/pre_surveys.js');
if (!m.politicalExpressionAttentionCheck) throw new Error('missing trial');
if (m.politicalExpressionAttentionCheck.data.trial_type !== 'political-expression-attention-check') {
  throw new Error('bad trial_type');
}
console.log('trial export OK');
"
```

**Expected:** `trial export OK`

## Pass / fail for this step

**Pass when:**

1. Trial exports and uses `jsPsychSurveyHtmlForm`.
2. Finish handler only scores + `addProperties`; never aborts.
3. Option labels match Step 1 constants (single source of truth — generate checkbox HTML from `ATTENTION_CHECK_OPTIONS`, do not duplicate strings).
4. Step 1 tests still pass.
5. `index.html` unchanged.

**Fail if:**

1. New plugin script added to `index.html`.
2. Timeline edited in `main.js` (belongs in Step 3).
3. Hardcoded duplicate option strings diverge from constants.

## Screenshots

Before implementing UI polish, keep the plan mockup as the target:

- Target: `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_ui.png`

Live capture is deferred to Step 4 (needs timeline wiring from Step 3).
