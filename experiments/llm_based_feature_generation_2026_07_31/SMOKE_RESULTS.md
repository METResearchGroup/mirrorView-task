# Smoke test results

**Date:** 2026-08-01  
**Status:** Passed (`smoke: ok`)  
**Prompt version:** Six fixed category checklists from `experiments/followup_model_error_analysis_2026_07_15/extract/prompts.py`; max **8 keep + 8 remove** features per batch (no `confidence` field)

**Command:**

```bash
PYTHONPATH=. uv run python \
  experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py
```

**Parameters:** `--sample-fraction 0.005 --keep-per-batch 10 --remove-per-batch 10 --seed 42`  
**Model:** `gpt-5.4-nano`

## Summary

The smoke run sampled **45 posts**, formed **1 batch** of **10 keep + 10 remove** posts (20 unique `message_id`s), and completed both stages end-to-end. Stage 1 returned exactly **8 keep_features + 8 remove_features** (16 total). Stage 2 synthesized **8 themes** plus **3 cross-cutting themes**. No `data/sampled_subset.csv` was created.

| Stage | Output directory | Result file |
| ----- | ---------------- | ----------- |
| 1 — feature generation | `outputs/2026_08_01-13:33:18.099196/` | `00000_2026_08_01-13:33:27.390065.json` |
| 2 — theme synthesis | `outputs/2026_08_01-13:33:27.391014/` | `00000_2026_08_01-13:33:35.677164.json` |

Paths are relative to `experiments/llm_based_feature_generation_2026_07_31/`.

## Stage 1 — features (8 keep + 8 remove)

Source: `outputs/2026_08_01-13:33:18.099196/00000_2026_08_01-13:33:27.390065.json`

### keep_features (8)

| message_id | feature_name | category |
| ---------- | ------------ | -------- |
| `twitter_2059359537673744708` | `approximate_token_length_band` | surface_lexical |
| `twitter_2059359537673744708` | `primary_policy_domain` | topic_subject |
| `reddit_1u225u5_oqvbe3g` | `profanity_or_taboo_language` | surface_lexical |
| `reddit_1u225u5_oqvbe3g` | `causal_claim_present` | semantic_content |
| `bluesky_1aab0671d390797381f7a9885df2c15cb2da318d77779bc4621061c0846b6d25` | `normative_moral_language` | semantic_content |
| `bluesky_1aab0671d390797381f7a9885df2c15cb2da318d77779bc4621061c0846b6d25` | `conditional_if_then_structure` | compositional_syntax |
| `twitter_2061828323722838316` | `us_vs_them_framing` | target_directionality |
| `twitter_2061188597785502107` | `second_person_direct_address` | compositional_syntax |

### remove_features (8)

| message_id | feature_name | category |
| ---------- | ------------ | -------- |
| `reddit_1kjndle_mrp2vs3` | `informal_register_or_slang` | surface_lexical |
| `reddit_1kjndle_mrp2vs3` | `ridicule_or_mockery` | pragmatics_intent |
| `reddit_1lmjifa_n092opi` | `profanity_or_taboo_language` | surface_lexical |
| `reddit_1lo82x1_n0nk59o` | `target_directionality` | target_directionality |
| `twitter_2060149644953272762` | `specific_event_or_bill_reference` | topic_subject |
| `twitter_2060149644953272762` | `conspiratorial_framing` | semantic_content |
| `reddit_1lb8wyo_mxr2wwj` | `emphatic_outrage` | pragmatics_intent |
| `twitter_2061799295783698746` | `factual_assertion_vs_speculation` | semantic_content |

## Stage 2 — synthesized themes

Source: `outputs/2026_08_01-13:33:27.391014/00000_2026_08_01-13:33:35.677164.json`

| id | Theme | keep | remove |
| -- | ----- | ---- | ------ |
| 1 | Profanity / taboo language used for emphasis or insults | 1 | 4 |
| 2 | Political blame via us-vs-them / targeted attribution | 1 | 1 |
| 3 | Conspiratorial or hidden-coordination claims | 0 | 1 |
| 4 | Election/voter process claims (voter ID, registration, participation mechanics) | 0 | 1 |
| 5 | Causal/evidence-oriented economic or policy linkage | 1 | 0 |
| 6 | Accountability / oversight as a normative requirement | 1 | 0 |
| 7 | Conditional policy if-then downstream effects | 1 | 0 |
| 8 | Event-claiming with quoted/foreknowledge framing | 0 | 1 |

### Cross-cutting themes

1. Use of political framing (blame attribution, election process discussion) spans multiple themes and appears in both keep and remove groups.
2. Hostile rhetoric escalation (profanity/insults/ridicule) strongly clusters in remove-rated examples and intersects with targeted directionality.
3. Risky belief-structure claims (conspiracy framing, strong event-assertion/foreknowledge) appear in remove-rated themes.

## Interpretation (smoke-scale)

On a single 10+10 batch, the model respected the **8+8 feature cap** and tagged checklist features (no `confidence` field). Remove-rated themes skew toward profanity, ridicule, conspiracy framing, and election-process claims; keep-rated themes skew toward policy/causal argumentation and accountability language. This is one batch only — not evidence about corpus-wide separability.

## Artifacts on disk

```
experiments/llm_based_feature_generation_2026_07_31/outputs/
├── 2026_08_01-13:33:18.099196/          # stage 1 run
│   ├── metadata.json
│   └── 00000_2026_08_01-13:33:27.390065.json
└── 2026_08_01-13:33:27.391014/          # stage 2 run
    ├── metadata.json
    └── 00000_2026_08_01-13:33:35.677164.json
```

## Next step

Per the plan approval gate, **do not start Step 5** (50% production run + `RESULTS.md`) until you explicitly approve these smoke results.
