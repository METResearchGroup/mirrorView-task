# Study 2 LLM-based feature extraction

## Step 1: cohort and batches

| Metric | Count |
| --- | --- |
| Five-label pairs | 15,113 |
| Modal keep | 11,910 |
| Modal remove | 3,203 |
| Mining batches | 320 |
| Keep pairs not in any batch | 8,710 |
| Remove pairs not in any batch | 3 |

## Step 2: mine candidate features

Smoke and full runs use OpenAI Batch `completion_window=1h` per the step 2 plan. On 2026-09-29 the Batch API returned HTTP 400: `Invalid value: '1h'. Supported values are: '24h'.` until that window is accepted, `--smoke` cannot produce the estimate table and `--full` cannot run.

## Step 3: embed candidates

## Step 4: cluster features

## Step 5: name clusters

## Step 6: Jev labels

## Step 7: analyses
