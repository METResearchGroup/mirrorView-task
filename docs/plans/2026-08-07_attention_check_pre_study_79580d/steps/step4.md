# Step 4: Capture live UI and data-field screenshots

## Goal

Prove the shipped attention check matches the plan mockups by capturing **live** screenshots of (1) the attention-check screen and (2) the pass/fail data field as it appears in saved/exported participant data. Overwrite the plan’s after images with these live captures. Do not change product behavior in this step except tiny visual fixes required for screenshot parity.

## Caller / unit of work

**Main caller:** manual browser session against the local (or deployed) MirrorView static app, driven by `/workspace/webapp/public/main.js` timeline.

1. Serve `/workspace/webapp/public` (or open the AWS static site if local config cannot save).
2. Complete Welcome → Consent (agree) → Political affiliation → **Attention check**.
3. Screenshot the attention-check viewport (full card visible) → write `images/after/attention_check_ui.png`.
4. Complete the check **correctly** once (`Q3–Q6` only); continue until data is available (local download or S3 object via save endpoint).
5. Complete a second run **incorrectly** (e.g. include `Q1` or omit a political option).
6. Screenshot a review view of `attention_check_passed` / `attention_check_selected` (CSV open in a simple HTML table, spreadsheet, or the existing data-field mockup page updated with live values) → write `images/after/attention_check_data_field.png`.
7. Confirm fail run still reached later trials / saved a full file.

**Out of scope:** new features; changing scoring; deploying to production Prolific; automating export pipeline filters.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/webapp/public/config.js` | Local vs AWS endpoints for save |
| `/workspace/docs/runbooks/MANUAL_TESTING.md` | Manual PID URL pattern |
| `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/mockups/attention_check_data_field.html` | Optional template for rendering live CSV rows into a screenshottable table |
| Steps 1–3 outputs | Must already be merged |

## Files allowed to change

- `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_ui.png` (overwrite with live UI)
- `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_data_field.png` (overwrite with live data field)
- `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/mockups/*` (optional: update mock HTML to embed live sample rows for the data screenshot)
- `/workspace/webapp/public/meriel.css` or trial HTML **only** for trivial visual fixes discovered while screenshotting (must not change scoring or timeline)

## Files forbidden to change

- `/workspace/webapp/public/main.js` timeline order / `columnsToKeep` (unless a bug found — then fix and note in the PR)
- `/workspace/webapp/lambdas/**`
- `/workspace/scripts/export_study_results.py` filter logic (do not add auto-drop of failers)

## Contracts to freeze

### Screenshot acceptance

**UI (`attention_check_ui.png`):**

- Shows title Political Expression, callout, select-all prompt, all six options, Continue.
- Captured from the **running** study (browser chrome optional; prefer page content only).
- Not the static plan mockup alone — must be live DOM from jsPsych.

**Data field (`attention_check_data_field.png`):**

- Clearly shows at least one row with `attention_check_passed = 1` and one with `0`.
- Shows `attention_check_selected` values consistent with those outcomes (pass ⇒ `Q3|Q4|Q5|Q6`).
- Labels the columns so a reviewer can filter post-hoc without reading code.

### Evidence note

Append a short note under the plan’s Screenshots table (or a one-line comment in the PR body) that after images are live as of this step.

## Exact commands

```bash
cd /workspace/webapp/public
python3 -m http.server 8765
```

In another terminal / browser:

```text
http://127.0.0.1:8765/?PROLIFIC_PID=manual-test-attention-pass
http://127.0.0.1:8765/?PROLIFIC_PID=manual-test-attention-fail
```

Headless capture example (adjust selector/timing as needed once the trial is on screen):

```bash
# After navigating to the attention-check trial in a headed session, or use Chrome DevTools Protocol.
# Minimum acceptable: save a full-page PNG from the live trial into the after/ path.
ls -la /workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/
file /workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_ui.png
file /workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_data_field.png
```

**Expected:** both files are PNGs with recent mtimes; UI shot shows live trial; data shot shows pass and fail rows.

If AWS save is required for a real CSV:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
# Then follow docs/runbooks/MANUAL_TESTING.md against the S3 website URL with a unique manual PID,
# locate the new data_*.csv under s3://jspsych-mirror-view-4/data/prolific/, and screenshot the two columns.
```

## Pass / fail for this step

**Pass when:**

1. Live UI screenshot replaces the mockup after image and clearly shows the attention check in-study.
2. Data-field screenshot shows `attention_check_passed` ∈ {0,1} with matching `attention_check_selected`.
3. Fail participant’s session still produced later trial rows / a saved file.
4. No new blocking behavior introduced.

**Fail if:**

1. Only mockup HTML was re-screenshotted without running the study.
2. Data screenshot omits the fail case.
3. Failures were ejected from the study during capture.

## Screenshots (required outputs)

| Role | Path |
|------|------|
| Before (unchanged) | `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/before/no_attention_check_timeline.png` |
| After UI (live) | `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_ui.png` |
| After data field (live) | `/workspace/docs/plans/2026-08-07_attention_check_pre_study_79580d/images/after/attention_check_data_field.png` |
