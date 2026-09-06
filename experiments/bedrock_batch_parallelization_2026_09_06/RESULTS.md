# Bedrock Nova Micro throughput results

These runs used Amazon Nova Micro (`us.amazon.nova-micro-v1:0`) through on-demand Converse in `us-east-2`. The posts and the news or opinion prompt match the OpenAI Batch experiment. Native Bedrock batch jobs were not used.

A Bedrock content-filter reply is stored as `neither`, so every submitted post still produces a valid label row. Mean output tokens drop slightly below 10 on the 2,000 and 5,000 post sizes because of those shorter filter messages. In production, we track posts that Nova Micro fails for content-filter reasons, and we can retry those posts with the OpenAI engine instead.

On-demand Ohio rates are $0.035 per million input tokens, and $0.14 per million output tokens.

## Size runs

Each size labeled the first requested number of posts from `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv`. All 9,500 submitted requests returned a valid `LlmIsNewsOrOpinionModel`.

The model is `us.amazon.nova-micro-v1:0`. Concurrency is 8 threads per size.

| Batch size | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ---------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 100 | 4.97 | 20.13 | 5,936.67 | 284.85 | 10.00 | 28,485 | 1,000 | 29,485 | $0.0011 |
| 200 | 8.98 | 22.27 | 6,538.13 | 283.55 | 10.00 | 56,710 | 2,000 | 58,710 | $0.0023 |
| 300 | 12.35 | 24.29 | 7,145.79 | 284.15 | 10.00 | 85,244 | 3,000 | 88,244 | $0.0034 |
| 400 | 15.59 | 25.65 | 7,574.59 | 285.25 | 10.00 | 114,102 | 4,000 | 118,102 | $0.0046 |
| 500 | 19.42 | 25.75 | 7,589.75 | 284.76 | 10.00 | 142,380 | 5,000 | 147,380 | $0.0057 |
| 1,000 | 37.75 | 26.49 | 7,798.27 | 284.36 | 10.00 | 284,364 | 10,000 | 294,364 | $0.0114 |
| 2,000 | 73.39 | 27.25 | 8,086.71 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 5,000 | 188.67 | 26.50 | 7,924.20 | 289.02 | 9.98 | 1,445,111 | 49,914 | 1,495,025 | $0.0576 |

The eight jobs took 361.11 seconds in total and used 2,824,812 tokens. Their combined estimated cost was $0.1088.

The matching OpenAI Batch size jobs took 1,706.18 seconds and cost $0.8438. Nova Micro Converse was cheaper and finished sooner on every size. The APIs are not the same. OpenAI Batch waits in a queue. Converse answers on demand with 8 concurrent calls.

## Process count runs

Each process labeled the same first 2,000 posts. Reusing that slice keeps request size and content constant across ablations. All 40,000 requests across all 20 jobs returned valid structured outputs.

Six and eight processes hit Bedrock `ThrottlingException`. The engine retried those calls, so wall time rose and aggregate posts per second fell after 4 processes.

### Aggregate results

| Processes | Posts | Wall seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| --------- | ----- | ------------ | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 2 | 4,000 | 82.54 | 48.46 | 14,380.30 | 286.76 | 9.99 | 1,147,024 | 39,980 | 1,187,004 | $0.0457 |
| 4 | 8,000 | 80.92 | 98.87 | 29,338.40 | 286.76 | 9.99 | 2,294,048 | 79,960 | 2,374,008 | $0.0915 |
| 6 | 12,000 | 164.67 | 72.87 | 21,625.63 | 286.76 | 9.99 | 3,441,072 | 119,940 | 3,561,012 | $0.1372 |
| 8 | 16,000 | 241.52 | 66.25 | 19,659.19 | 286.76 | 9.99 | 4,588,096 | 159,920 | 4,748,016 | $0.1830 |

Four processes delivered the highest aggregate throughput, at 98.87 posts per second. That is 2.04 times the 2-process rate, which is close to linear. Six and eight processes were slower than four because of throttling. The matching OpenAI Batch 8-process run reached 53.60 posts per second.

### 2-process run

| Process | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 1 | 78.69 | 25.42 | 7,542.73 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 2 | 78.60 | 25.44 | 7,550.82 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |

Total wall time: 82.54 seconds.

### 4-process run

| Process | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 1 | 76.88 | 26.01 | 7,719.47 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 2 | 76.89 | 26.01 | 7,718.97 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 3 | 76.69 | 26.08 | 7,738.77 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 4 | 76.52 | 26.14 | 7,756.18 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |

Total wall time: 80.92 seconds.

### 6-process run

| Process | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 1 | 158.33 | 12.63 | 3,748.54 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 2 | 156.15 | 12.81 | 3,800.90 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 3 | 155.00 | 12.90 | 3,829.15 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 4 | 157.88 | 12.67 | 3,759.26 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 5 | 156.50 | 12.78 | 3,792.34 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 6 | 151.29 | 13.22 | 3,922.87 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |

Total wall time: 164.67 seconds.

### 8-process run

| Process | Elapsed seconds | Posts per second | Tokens per second | Mean input tokens per request | Mean output tokens per request | Input tokens | Output tokens | Total tokens | Estimated cost (USD) |
| ------- | --------------- | ---------------- | ----------------- | ----------------------------- | ------------------------------ | ------------ | ------------- | ------------ | -------------------- |
| 1 | 233.00 | 8.58 | 2,547.24 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 2 | 221.78 | 9.02 | 2,676.12 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 3 | 226.98 | 8.81 | 2,614.77 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 4 | 229.84 | 8.70 | 2,582.29 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 5 | 228.91 | 8.74 | 2,592.78 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 6 | 222.35 | 8.99 | 2,669.27 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 7 | 229.93 | 8.70 | 2,581.20 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |
| 8 | 228.93 | 8.74 | 2,592.46 | 286.76 | 9.99 | 573,512 | 19,990 | 593,502 | $0.0229 |

Total wall time: 241.52 seconds.

The complete process experiment took 569.64 seconds of sequential wall time, used 11,870,040 tokens, and had an estimated cost of $0.4574. Size and process jobs together cost about $0.5662, which is close to the $0.5628 estimate in `COST_ESTIMATE.md`. Raw metrics are in `size_results.json` and `process_results.json`.

## Command

Size runs from the repository root:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py \
  --i-approve-the-cost-estimate
```

Process count runs from the repository root:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py \
  --i-approve-the-cost-estimate
```
