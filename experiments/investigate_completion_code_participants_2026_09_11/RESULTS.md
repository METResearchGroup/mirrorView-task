# Completion-code participants, results

Both participants finished the September 2026 study. Their jsPsych CSVs are in `s3://jspsych-mirror-view-2026-09-09/data/prolific/`. The save-data Lambda wrote those objects, which is the same gate that shows the Prolific completion code `CE5XLP3L`.

Approve both submissions on Prolific. If a submission is still open, the completion URL is `https://app.prolific.com/submissions/complete?cc=CE5XLP3L`.

## Tests

`PYTHONPATH=. uv run pytest experiments/investigate_completion_code_participants_2026_09_11/tests -q` exited 0.

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/investigate_completion_code_participants_2026_09_11/run.py
```

## Recommendation

| Prolific id | Assignment | Saved session | Recommendation |
| ----------- | ---------- | ------------- | -------------- |
| `671be80dd312fef1ab1d7c31` | yes | yes, complete | approve |
| `69f769601fc86e145904de9a` | yes | yes, complete | approve |

## What "completed" means here

The browser only shows the completion code after `POST /save-jspsych-data` returns 200. `webapp/public/config.js` sets `PROLIFIC_COMPLETION_URL` to `null`, so there is no auto-redirect. `webapp/public/main.js` replaces the page with a thank-you message and a link to `https://app.prolific.com/submissions/complete?cc=CE5XLP3L`.

A saved CSV with 20 scored moderation trials (non-empty `post_id`), consent, an attention-check score, the pair reflection, demographics, ideology, and attitude items is a complete session. The practice trial has an empty `post_id` and does not count.

## Why they could not enter the code

This lookup cannot see Prolific submission state. On our side both people have complete sessions, so they should have been shown `CE5XLP3L` unless they left the tab after the last survey and before the thank-you page rendered.

If they went back to Prolific instead of clicking the link, they had to type `CE5XLP3L` into Prolific's box. Prolific rejects that code when the submission is already returned or timed out. Confirm the live Prolific study still uses `CE5XLP3L`.

## Participants

### `671be80dd312fef1ab1d7c31`

Assignment `democrat-training_assisted-0614` created `2026_09_10-23:24:32` (`democrat`, `training_assisted`).

| Field | Value |
| ----- | ----- |
| S3 object | `s3://jspsych-mirror-view-2026-09-09/data/prolific/data_1789083309732_42462e59-5fb7-49ca-bfd0-16fc60b5c587.csv` |
| Rows | 33 |
| Scored moderation trials | 20 scored, 20 unique |
| Posts match assignment | yes |
| Decisions | keep=15, remove=5 |
| Attention check passed | 1 (`Q3|Q4|Q5|Q6`) |
| Consented | 1 |
| Party / condition | democrat / training_assisted |
| Reflection | 58 words |
| Demographics / ideology / attitudes | yes / yes / yes |
| Session length | 11.5 min (`time_elapsed`) |
| Complete | yes |

### `69f769601fc86e145904de9a`

Assignment `democrat-training_assisted-0613` created `2026_09_10-23:18:08` (`democrat`, `training_assisted`).

| Field | Value |
| ----- | ----- |
| S3 object | `s3://jspsych-mirror-view-2026-09-09/data/prolific/data_1789082752039_4e2f276f-14cb-4c96-8097-389768ccad1c.csv` |
| Rows | 33 |
| Scored moderation trials | 20 scored, 20 unique |
| Posts match assignment | yes |
| Decisions | keep=20 |
| Attention check passed | 1 (`Q3|Q4|Q5|Q6`) |
| Consented | 1 |
| Party / condition | democrat / training_assisted |
| Reflection | 44 words |
| Demographics / ideology / attitudes | yes / yes / yes |
| Session length | 14.3 min (`time_elapsed`) |
| Complete | yes |


## Files

| File | Path |
| ---- | ---- |
| Study CSVs | `s3://jspsych-mirror-view-2026-09-09/data/prolific/` (1096 objects listed) |
| Findings JSON | `s3://mirrorview-experimental-artifacts/experiments/investigate_completion_code_participants_2026_09_11/findings.json` |
| Findings SHA-256 | `834377209f9fa2f3a1b5c62535c6c6f0160a77d36b8c231afa10018ad7f64b56` |

Study iteration is `mirrorview_2026_09_09`. Default ids: `671be80dd312fef1ab1d7c31`, `69f769601fc86e145904de9a`.
