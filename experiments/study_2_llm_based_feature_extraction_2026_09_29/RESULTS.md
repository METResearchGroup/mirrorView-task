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

| Value | Low | Median | High |
| --- | --- | --- | --- |
| Runtime (minutes) | 12.3 | 15.4 | 18.4 |
| Input tokens | 647,936 | 809,920 | 971,904 |
| Output tokens | 180,992 | 226,240 | 271,488 |
| Price (USD) | $3.47 | $4.33 | $5.20 |

The runtime median scales the smoke wall time by the number of groups of 8 requests (40 groups for 320 requests versus 1 group for the 5-request smoke).

## Step 3: embed candidates

## Step 4: cluster features

## Step 5: name clusters

## Step 6: Jev labels

## Step 7: analyses
