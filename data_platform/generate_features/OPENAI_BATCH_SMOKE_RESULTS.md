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

## 2026-09-05 parallel process benchmark

The follow-up experiment ran the existing smoke test in 2, 4, 6, and 8 spawned
Python processes. Every process independently submitted the same 2,000-post
slice as one OpenAI Batch job. Reusing the slice keeps request size and content
constant across ablations. All 40,000 requests across all 20 jobs returned
valid structured outputs.

Total wall time includes process startup, all concurrent Batch jobs, result
downloads, parsing, and process shutdown. The per-process elapsed time measures
that process's smoke-test run. The pricing assumptions are the same as in the
batch size benchmark.

### Aggregate results

| Processes | Posts | Wall seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| --------- | ----- | ------------ | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 2 | 4,000 | 412.12 | 9.71 | 3,392.05 | 331.52 | 17.96 | 1,326,086 | 71,850 | 1,397,936 | $0.3550 |
| 4 | 8,000 | 257.62 | 31.05 | 10,852.58 | 331.52 | 17.96 | 2,652,172 | 143,700 | 2,795,872 | $0.7101 |
| 6 | 12,000 | 275.93 | 43.49 | 15,198.58 | 331.52 | 17.96 | 3,978,258 | 215,548 | 4,193,806 | $1.0651 |
| 8 | 16,000 | 298.53 | 53.60 | 18,730.96 | 331.52 | 17.96 | 5,304,344 | 287,395 | 5,591,739 | $1.4201 |

The 8-process run processed four times as many posts as the 2-process run in
28% less wall time and delivered 5.52 times its throughput. Scaling was strong
through 8 processes, but not linear: 6 to 8 processes increased aggregate
throughput by 23.2%, versus the ideal 33.3%. Batch scheduling variance is
material—the two jobs in the 2-process run took 260.0 and 408.2 seconds—so
repeated trials are needed for stable capacity planning.

### 2-process run

| Process | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 1 | 408.20 | 4.90 | 1,712.33 | 331.52 | 17.96 | 663,043 | 35,925 | 698,968 | $0.1775 |
| 2 | 259.97 | 7.69 | 2,688.60 | 331.52 | 17.96 | 663,043 | 35,925 | 698,968 | $0.1775 |

Total wall time: 412.12 seconds.

### 4-process run

| Process | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 1 | 253.33 | 7.89 | 2,759.13 | 331.52 | 17.96 | 663,043 | 35,925 | 698,968 | $0.1775 |
| 2 | 237.90 | 8.41 | 2,938.05 | 331.52 | 17.96 | 663,043 | 35,927 | 698,970 | $0.1775 |
| 3 | 212.79 | 9.40 | 3,284.80 | 331.52 | 17.96 | 663,043 | 35,925 | 698,968 | $0.1775 |
| 4 | 151.00 | 13.25 | 4,629.00 | 331.52 | 17.96 | 663,043 | 35,923 | 698,966 | $0.1775 |

Total wall time: 257.62 seconds.

### 6-process run

| Process | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 1 | 249.26 | 8.02 | 2,804.12 | 331.52 | 17.96 | 663,043 | 35,924 | 698,967 | $0.1775 |
| 2 | 194.01 | 10.31 | 3,602.67 | 331.52 | 17.96 | 663,043 | 35,924 | 698,967 | $0.1775 |
| 3 | 269.60 | 7.42 | 2,592.61 | 331.52 | 17.96 | 663,043 | 35,926 | 698,969 | $0.1775 |
| 4 | 192.13 | 10.41 | 3,638.07 | 331.52 | 17.96 | 663,043 | 35,924 | 698,967 | $0.1775 |
| 5 | 141.33 | 14.15 | 4,945.48 | 331.52 | 17.96 | 663,043 | 35,926 | 698,969 | $0.1775 |
| 6 | 161.85 | 12.36 | 4,318.49 | 331.52 | 17.96 | 663,043 | 35,924 | 698,967 | $0.1775 |

Total wall time: 275.93 seconds.

### 8-process run

| Process | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 1 | 239.30 | 8.36 | 2,920.91 | 331.52 | 17.96 | 663,043 | 35,925 | 698,968 | $0.1775 |
| 2 | 261.37 | 7.65 | 2,674.29 | 331.52 | 17.96 | 663,043 | 35,926 | 698,969 | $0.1775 |
| 3 | 290.01 | 6.90 | 2,410.12 | 331.52 | 17.96 | 663,043 | 35,923 | 698,966 | $0.1775 |
| 4 | 203.92 | 9.81 | 3,427.71 | 331.52 | 17.96 | 663,043 | 35,921 | 698,964 | $0.1775 |
| 5 | 145.80 | 13.72 | 4,794.10 | 331.52 | 17.96 | 663,043 | 35,924 | 698,967 | $0.1775 |
| 6 | 287.35 | 6.96 | 2,432.49 | 331.52 | 17.96 | 663,043 | 35,926 | 698,969 | $0.1775 |
| 7 | 240.17 | 8.33 | 2,910.32 | 331.52 | 17.96 | 663,043 | 35,926 | 698,969 | $0.1775 |
| 8 | 202.87 | 9.86 | 3,445.31 | 331.52 | 17.96 | 663,043 | 35,924 | 698,967 | $0.1775 |

Total wall time: 298.53 seconds.

The complete experiment took 1,244.21 seconds of sequential wall time, used
13,979,353 tokens, and had an estimated cost of $3.5503. Raw metrics are in
`experiments/openai_batch_parallelization_2026_09_05/results.json`.

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

Run the process parallelization experiment from the repository root:

```bash
PYTHONPATH=. uv run --no-dev python \
  experiments/openai_batch_parallelization_2026_09_05/run_experiment.py
```
