# OpenAI Batch smoke results

## 2026-09-05 batch size benchmark

The benchmark submitted eight independent OpenAI Batch jobs in sequence. Each job
classified the first requested number of posts from
`shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` as news, opinion, or
neither. All 9,500 submitted requests returned a valid
`LlmIsNewsOrOpinionModel`.

Model: `gpt-5.4-nano`

Cost uses the published GPT-5.4 nano Batch API rates on 2026-09-05:
$0.20 per million input tokens and $1.25 per million output tokens. None of
these jobs reported cached input tokens.

| Batch size | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ---------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 100 | 93.55 | 1.07 | 371.44 | 329.53 | 17.95 | 32,953 | 1,795 | 34,748 | $0.0088 |
| 200 | 108.88 | 1.84 | 637.12 | 328.90 | 17.97 | 65,779 | 3,594 | 69,373 | $0.0176 |
| 300 | 98.89 | 3.03 | 1,052.95 | 329.13 | 17.96 | 98,738 | 5,389 | 104,127 | $0.0265 |
| 400 | 156.42 | 2.56 | 889.20 | 329.76 | 17.95 | 131,904 | 7,182 | 139,086 | $0.0354 |
| 500 | 120.00 | 4.17 | 1,446.53 | 329.20 | 17.96 | 164,602 | 8,980 | 173,582 | $0.0441 |
| 1,000 | 165.91 | 6.03 | 2,091.10 | 328.97 | 17.96 | 328,972 | 17,959 | 346,931 | $0.0882 |
| 2,000 | 228.81 | 8.74 | 3,054.73 | 331.52 | 17.96 | 663,043 | 35,925 | 698,968 | $0.1775 |
| 5,000 | 733.72 | 6.81 | 2,393.37 | 333.23 | 17.98 | 1,666,155 | 89,904 | 1,756,059 | $0.4456 |

The eight jobs took 1,706.18 seconds in total and used 3,322,874 tokens. Their
combined estimated cost was $0.8438. Batch completion time varied between
jobs because OpenAI schedules each Batch asynchronously. The 400 post job took
longer than the 500 post job, so one run per size does not establish a stable
latency curve.

Cost formula:

```text
(input tokens × $0.20 / 1,000,000)
  + (output tokens × $1.25 / 1,000,000)
```

Pricing source:
https://developers.openai.com/api/docs/models/gpt-5.4-nano

## Command

Run each size from the repository root:

```bash
for n in 100 200 300 400 500 1000 2000 5000; do
  PYTHONPATH=. uv run --no-dev python \
    data_platform/generate_features/smoke_openai_engine.py \
    --posts-csv shared/data/raw/study_phase_2_part_2/stimuli/flips.csv \
    --post-count "$n" \
    --id-column post_primary_key \
    --text-column original_text
done
```
