# OpenAI Batch smoke results

## 2026-09-05 batch size benchmark

The benchmark submitted six independent OpenAI Batch jobs in sequence. Each job
classified the first requested number of posts from
`shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` as news, opinion, or
neither. All 2,500 submitted requests returned a valid
`LlmIsNewsOrOpinionModel`.

Model: `gpt-5.4-nano`

| Batch size | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Total tokens |
| ---------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ |
| 100 | 93.55 | 1.07 | 371.44 | 329.53 | 17.95 | 34,748 |
| 200 | 108.88 | 1.84 | 637.12 | 328.90 | 17.97 | 69,373 |
| 300 | 98.89 | 3.03 | 1,052.95 | 329.13 | 17.96 | 104,127 |
| 400 | 156.42 | 2.56 | 889.20 | 329.76 | 17.95 | 139,086 |
| 500 | 120.00 | 4.17 | 1,446.53 | 329.20 | 17.96 | 173,582 |
| 1,000 | 165.91 | 6.03 | 2,091.10 | 328.97 | 17.96 | 346,931 |

The six jobs took 743.65 seconds in total. Batch completion time varied between
jobs because OpenAI schedules each Batch asynchronously. The 400 post job took
longer than the 500 post job, so one run per size does not establish a stable
latency curve.

## Command

Run each size from the repository root:

```bash
for n in 100 200 300 400 500 1000; do
  PYTHONPATH=. uv run --no-dev python \
    data_platform/generate_features/smoke_openai_engine.py \
    --posts-csv shared/data/raw/study_phase_2_part_2/stimuli/flips.csv \
    --post-count "$n" \
    --id-column post_primary_key \
    --text-column original_text
done
```
