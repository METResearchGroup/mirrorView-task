# Length-matching ablations

Character parity (≥10% relative diff) is the **primary** metric. Token parity is **diagnostic**.

Each ablation uses **25 posts** sampled from `combined_flips/flips.csv` with `random_state=42`.

| Ablation | Changes | Char fail | Token fail | Too long | Too short | Parse fail | Avg chars (mirr/orig) | Avg tokens (mirr/orig) | Output CSV |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| A0 | v1 baseline: prompt length line only; JSON with explanation; no max_tokens; batched | 68.0% | 32.0% | 64.0% | 4.0% | 0.0% | 418/381 | 84/83 | `outputs/ablations/A0_2026_06_19-15:19:58.csv` |
| B0 | v2 baseline: max_tokens = ceil(t×1.05)+20; JSON flipped_text only | 60.0% | 28.0% | 60.0% | 0.0% | 0.0% | 423/381 | 86/83 | `outputs/ablations/B0_2026_06_19-15:21:13.csv` |
| B1 | Tighter cap: max_tokens = t+12; JSON flipped_text only | 72.0% | 36.0% | 72.0% | 0.0% | 0.0% | 449/381 | 88/83 | `outputs/ablations/B1_2026_06_19-15:19:26.csv` |
| B2 | Minimal overhead: max_tokens = t+8; JSON flipped_text only | 76.0% | 36.0% | 76.0% | 0.0% | 0.0% | 434/381 | 86/83 | `outputs/ablations/B2_2026_06_19-15:22:29.csv` |
| B3 | Under-budget: max_tokens = ceil(t×0.95)+12; JSON flipped_text only | 64.0% | 40.0% | 64.0% | 0.0% | 0.0% | 425/381 | 85/83 | `outputs/ablations/B3_2026_06_19-15:23:43.csv` |
| B4 | Mid cap: max_tokens = ceil(t×1.00)+16; JSON flipped_text only | 64.0% | 32.0% | 64.0% | 0.0% | 0.0% | 426/381 | 85/83 | `outputs/ablations/B4_2026_06_19-15:24:53.csv` |
| C1 | Char bounds [0.9N, 1.1N] in prompt + max_tokens = t+12 | 28.0% | 28.0% | 28.0% | 0.0% | 0.0% | 439/381 | 86/83 | `outputs/ablations/C1_2026_06_19-15:26:16.csv` |
| C2 | Char bounds [0.9N, 1.1N] in prompt; no max_tokens | 32.0% | 28.0% | 32.0% | 0.0% | 0.0% | 428/381 | 85/83 | `outputs/ablations/C2_2026_06_19-15:27:33.csv` |
| C3 | Char bounds [0.9N, 1.1N] in prompt + max_tokens = t+8 | 28.0% | 28.0% | 28.0% | 0.0% | 0.0% | 439/381 | 87/83 | `outputs/ablations/C3_2026_06_19-15:28:47.csv` |
| D1 | max_tokens = t+12; retry with t+8 if mirror > 1.10× original chars | 52.0% | 24.0% | 52.0% | 0.0% | 0.0% | 427/381 | 86/83 | `outputs/ablations/D1_2026_06_19-15:30:51.csv` |
| D2 | max_tokens = t+12; second shorten pass if mirror > 1.10× original chars | 20.0% | 40.0% | 4.0% | 16.0% | 0.0% | 251/381 | 52/83 | `outputs/ablations/D2_2026_06_19-15:32:13.csv` |
| E1 | Plain text output + max_tokens = t+12 | 56.0% | 24.0% | 56.0% | 0.0% | 0.0% | 424/381 | 83/83 | `outputs/ablations/E1_2026_06_19-15:33:21.csv` |
| E2 | Plain text output + char bounds + max_tokens = t+12 | 28.0% | 24.0% | 28.0% | 0.0% | 0.0% | 413/381 | 81/83 | `outputs/ablations/E2_2026_06_19-15:34:31.csv` |
| F1 | Two-pass: initial flip (t+12), then length rewrite to char bounds | 32.0% | 36.0% | 32.0% | 0.0% | 0.0% | 429/381 | 84/83 | `outputs/ablations/F1_2026_06_19-15:36:40.csv` |
| G1 | Calibrated token estimate from Bedrock usage + max_tokens = cal(t)+12 | 60.0% | 20.0% | 60.0% | 0.0% | 0.0% | 424/381 | 85/83 | `outputs/ablations/G1_2026_06_19-15:38:08.csv` |

## Findings

**Run command:**

```bash
PYTHONPATH=. uv run python experiments/match_lengths_original_mirrors_2026_06_19/run_ablations.py --all
```

### Primary metric: character parity (≥10% failure rate)

| Rank | Ablation | Char fail | Notes |
|---:|---|---:|---|
| 1 | **D2** (shorten retry) | **20.0%** | Best char parity, but 16% too-short; avg mirror 251 vs 381 chars — over-shortens |
| 2 | **C1**, **C3**, **E2** | **28.0%** | Char bounds in prompt is the key lever |
| 4 | C2 | 32.0% | Char bounds alone (no cap) nearly as good as C1 |
| 5 | F1 | 32.0% | Two-pass rewrite did not beat char bounds |
| 6 | B0 | 60.0% | Best token-only cap sweep; still 60% char fail |
| 7 | G1 | 60.0% | Best token diagnostic (20% fail) but poor char parity |

**Token-only caps (B0–B4) do not solve character parity.** All cap-sweep variants scored 60–76% char failure. Failures were almost entirely **too long** (0% too-short except D2).

### What works

**Explicit character bounds `[0.9N, 1.1N]` in the prompt** is the single most effective intervention, cutting char failure from ~60–76% (cap-only) to **28–32%** regardless of output format (JSON C1/C3 or plain text E2).

- **C1** (char bounds + `t+12` cap): 28% char fail, 28% token fail — recommended starting point for production
- **E2** (plain text + char bounds + cap): 28% char fail, 24% token fail, lowest avg mirrored chars (413) among char-bounds variants
- **C2** (char bounds, no cap): 32% char fail — bounds alone nearly match C1; cap adds little once bounds are explicit

### What partially works

- **D2** (shorten pass on overrun): lowest char failure (20%) but **over-corrects** — avg mirror 251 chars vs 381 original, 16% too-short. Useful mechanism but needs a higher shorten floor.
- **D1** (retry with tighter cap): worse than char bounds (52%); regenerating the full flip is less effective than shortening.

### What does not help (on char parity)

- **Token caps alone** (B0–B4): 60–76% char failure; tighter caps (B2) performed *worse* than looser (B0).
- **G1** (Bedrock-calibrated token budget): best token diagnostic (20%) but 60% char failure — confirms token and char objectives diverge.
- **F1** (two-pass length rewrite): 32% — no improvement over single-pass char bounds.
- **Dropping JSON** without char bounds (E1): 56% — modest improvement over JSON cap-only, not enough alone.

### Recommended next step for production

Adopt **C1 or E2** (char bounds + moderate token cap). Optionally refine **D2** with a minimum shorten target (e.g. do not shorten below `0.9N`) to reduce the too-short tail while keeping low overrun.
