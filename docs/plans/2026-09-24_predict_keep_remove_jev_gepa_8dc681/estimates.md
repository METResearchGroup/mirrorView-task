# Estimates: predict keep or remove with Jev and GEPA

Probe measured 2026-09-24 (seed 20260924, batch 10, model `jev-1.13.0`).

## Per-view probe (batch 10)

| View | Input tokens / request | Input tokens / post | Output tokens / request | Output tokens / post | Latency ms / request | Cost / 1k posts |
|------|------------------------|---------------------|-------------------------|----------------------|----------------------|-----------------|
| Pair | 4,904 | 490 | 184 | 18 | 186 to 365 | $0.021 |
| Original | 1,268 | 127 | 184 | 18 | 139 to 190 | $0.0053 |
| Mirror | 1,244 | 124 | 184 | 18 | 167 to 189 | $0.0052 |

Pricing: $0.042 per 1M input tokens, $0 output.

Run 100-post smoke per view in Step 4 before full Stage A. The A4 addendum assumes ~250 extra input tokens per post; measure that in smoke.

## Stage A (Jev baseline, cohort A = 14,941 posts)

| Ablation | View | Requests (batch 10) | Input tokens (M) | Notes |
|----------|------|---------------------|------------------|-------|
| A1 | Pair | 1,495 | 7.32 | |
| A2 | Original | 1,495 | 1.90 | |
| A3 | Mirror | 1,495 | 1.86 | |
| A4 | Pair + addendum | 1,495 | ~11.1 | ~250 extra tokens/post assumed |
| **Total** | | **5,980** | **~22.2** | ~1.1M output |

| Stage A summary | Value |
|-----------------|-------|
| Total input + output tokens | ~23.3M |
| Jev cost | ~$0.93 |
| API time at 1,000 req/min | ~6 min |
| Wall time (finalize + upload) | under 20 min |

At 1,000 requests per minute, the rate cap binds at about 1.5 min per ablation.

## Stage B (Jev + GEPA, per run)

| Component | Post-scorings | Jev tokens | Jev cost |
|-----------|---------------|------------|----------|
| GEPA metric calls | 9,000 | ~5.4M (@ ~600 tok/post evolved) | ~$0.23 |
| Dev selection (~15 candidates x 1,494) | ~22,410 | ~13.4M | ~$0.56 |
| Test (~2,988) | ~2,988 | ~1.8M | ~$0.08 |
| **Per run Jev subtotal** | **~34,000** | **~20M** | **~$0.87** |

Reflection assumptions (unchanged): ~150 to 250 calls per run, ~10k input + ~4k output tokens per call.

### GPT-6 Luna (B1, B2, B3, B4)

Source: https://developers.openai.com/api/docs/models/gpt-6-luna (checked 2026-09-24). Standard tier, up to 272K input: $0.10 per 1M input, $0.01 cached input, $0.50 per 1M output. LiteLLM id: `openai/gpt-6-luna`.

| Item | Value |
|------|-------|
| Cost per call | ~$0.001 input + ~$0.002 output = ~$0.003 |
| Cost per run | ~$0.45 to ~$0.75 |
| Hard cap per run | $5 (`max_reflection_cost`) |
| Tokens per run | ~2.1M to ~3.5M |

### GPT-5.6 Terra (B1-T only)

Source: https://developers.openai.com/api/docs/pricing. $2.00 per 1M input, $12.00 per 1M output. LiteLLM id: `openai/gpt-5.6-terra`.

| Item | Value |
|------|-------|
| Cost per call | ~$0.02 input + ~$0.048 output = ~$0.068 |
| Cost per run (B1-T) | ~$10 to ~$17 |
| Hard cap per run | $20 (`max_reflection_cost`) |
| Tokens per run | ~2.1M to ~3.5M |

If Luna uses more tokens than assumed, doubling tokens per call still keeps the four Luna runs under ~$6 total.

Paper reference (arXiv 2507.19457): 2,270 to 6,926 rollouts per task.

## Stage B totals (5 runs + transfer)

| Item | Value |
|------|-------|
| Jev tokens (5 runs) | ~100M (5 x ~20M) |
| Jev cost (5 runs) | ~$4.35 |
| Luna reflection (4 runs) | ~$1.80 to ~$3.00 (cap $20 total) |
| Terra reflection (B1-T) | ~$10 to ~$17 (cap $20) |
| Transfer evals | under $0.10 |
| **Stage B total** | **~$16 to ~$25** |
| **Hard ceiling (caps)** | **4 x $5 + $20 + ~$4.4 = ~$44.4** |
| Wall time (parallel) | ~2 to 3 h (reflection ~30 to 60 s/iteration, ~150 to 250 iterations) |
| Reflection tokens (5 runs) | ~10.5M to ~17.5M total (~2.1M to ~3.5M per run) |

## Project total

| Stage | Jev | Reflection | Wall |
|-------|-----|------------|------|
| A | ~$0.93 | $0 | ~20 min |
| B | ~$4.35 | ~$12 to ~$20 | ~2 to 3 h |
| **Total** | **~$5.3** | **~$12 to ~$20** | **~3 h** |

**Project total: ~$17 to ~$26. Hard ceiling: ~$46** (Stage A ~$0.93 + Stage B cap ~$44.4).
