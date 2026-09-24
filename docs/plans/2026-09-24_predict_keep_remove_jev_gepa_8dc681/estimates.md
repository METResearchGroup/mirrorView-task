# Estimates: predict keep or remove with Jev and GEPA

Probe measured 2026-09-24 (seed 20260924, batch 10, model `jev-1.13.0`).

## Per-view probe (batch 10)

| View | Input tokens / request | Input tokens / post | Output tokens / request | Output tokens / post | Latency ms / request | Cost / 1k posts |
|------|------------------------|---------------------|-------------------------|----------------------|----------------------|-----------------|
| Pair | 4,904 | 490 | 184 | 18 | 186 to 365 | $0.021 |
| Original | 1,268 | 127 | 184 | 18 | 139 to 190 | $0.0053 |
| Mirror | 1,244 | 124 | 184 | 18 | 167 to 189 | $0.0052 |

Pricing: $0.042 per 1M input tokens, $0 output.

Run 100-post smoke per view in Step 4 before full Stage A. A4 addendum assumes ~250 extra input tokens per post; measure in smoke.

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

The rate cap binds at about 1.5 min per ablation.

## Stage B (Jev + GEPA, per run)

| Component | Post-scorings | Jev tokens | Jev cost |
|-----------|---------------|------------|----------|
| GEPA metric calls | 9,000 | ~5.4M (@ ~600 tok/post evolved) | ~$0.23 |
| Dev selection (~15 candidates x 1,494) | ~22,410 | ~13.4M | ~$0.56 |
| Test (~2,988) | ~2,988 | ~1.8M | ~$0.08 |
| **Per run Jev subtotal** | **~34,000** | **~20M** | **~$0.87** |

Reflection (`openai/gpt-5.4`: $2.50/M input, $15/M output per [OpenAI pricing](https://developers.openai.com/api/docs/models/gpt-5.4)):

| Item | Value |
|------|-------|
| Calls per run | ~150 to 250 |
| Tokens per call | ~10k input + ~4k output (incl. reasoning) |
| Cost per run | ~$13 to ~$21 (capped at $20) |
| Hard cap | `max_reflection_cost=$20` |

Paper reference (arXiv 2507.19457): 2,270 to 6,926 rollouts per task.

## Stage B totals (4 runs + transfer)

| Item | Value |
|------|-------|
| Jev tokens (4 runs) | ~80M |
| Jev cost (4 runs) | ~$3.4 |
| Reflection cost (4 runs) | ~$51 to $80 (cap $80) |
| Transfer evals | under $0.10 |
| **Stage B total** | **<= ~$85** |
| Wall time (parallel) | ~2 to 3 h (reflection ~30 to 60 s/iteration, ~150 to 250 iterations) |
| Reflection tokens (4 runs) | ~2 to 3.5M |

## Project total

| Stage | Jev | Reflection | Wall |
|-------|-----|------------|------|
| A | ~$0.93 | $0 | ~20 min |
| B | ~$3.4 | $40 to $80 | ~2 to 3 h |
| **Total** | **~$4.3** | **<= $80** | **~3 h** |

**Project cap: <= ~$90.**
