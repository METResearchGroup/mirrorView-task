# Smoke test results

**Date:** 2026-08-01  
**Status:** Passed (`smoke: ok`)  
**Prompt version:** Six fixed category checklists from `experiments/followup_model_error_analysis_2026_07_15/extract/prompts.py` (plus `open_ended`)

**Command:**

```bash
PYTHONPATH=. uv run python \
  experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py
```

**Parameters:** `--sample-fraction 1e-6 --keep-per-batch 1 --remove-per-batch 1 --seed 42`  
**Model:** `gpt-5.4-nano`

## Summary

The smoke run sampled **2 posts** from the full corpus (8,792 modal keep/remove rows), formed **1 batch** (1 keep + 1 remove), and completed both pipeline stages end-to-end. Stage 1 extracted **31 features** using the fixed category checklists (`surface_lexical`, `topic_subject`, `semantic_content`, `pragmatics_intent`, `target_directionality`, `compositional_syntax`, plus `open_ended`). Stage 2 synthesized **7 themes** plus **5 cross-cutting themes**. No `data/sampled_subset.csv` was created.

| Stage | Output directory | Result file |
| ----- | ---------------- | ----------- |
| 1 — feature generation | `outputs/2026_08_01-13:21:54.416519/` | `00000_2026_08_01-13:22:13.854743.json` |
| 2 — theme synthesis | `outputs/2026_08_01-13:22:13.855934/` | `00000_2026_08_01-13:22:25.665480.json` |

Paths are relative to `experiments/llm_based_feature_generation_2026_07_31/`.

## Posts in the smoke batch

| message_id | Human label |
| ---------- | ----------- |
| `twitter_2059404130087801256` | keep |
| `bluesky_de734bc474bc703ef18a57dd0912b0e59942c19e460a057eda0be98463c587dc` | remove |

## Stage 1 — extracted features (by category)

Source: `outputs/2026_08_01-13:21:54.416519/00000_2026_08_01-13:22:13.854743.json`

### Keep-rated post (`twitter_2059404130087801256`) — 15 features

| Category | Features extracted |
| -------- | ------------------ |
| `surface_lexical` | `approximate_token_length_band` (long), `high_punctuation_intensity`, `hashtag_or_mention_pattern`, `named_proper_nouns_density` |
| `topic_subject` | `primary_policy_domain` (abortion), `specific_event_or_bill_reference` (Arkansas ban miscarriage), `geographic_scope` (Arkansas/California), `culture_war_topic_salience` |
| `semantic_content` | `normative_moral_language`, `factual_assertion_vs_speculation`, `victimhood_or_persecution_framing` |
| `pragmatics_intent` | `ridicule_or_mockery`, `persuasion_or_argumentation` |
| `target_directionality` | `target_directionality` (attacks @SaraHuckabeeAR; mirror attacks @GavinNewsom) |

### Remove-rated post (`bluesky_de734bc474bc703ef18a57dd0912b0e59942c19e460a057eda0be98463c587dc`) — 16 features

| Category | Features extracted |
| -------- | ------------------ |
| `surface_lexical` | `approximate_token_length_band` (short), `informal_register_or_slang`, `named_proper_nouns_density` (NRA) |
| `topic_subject` | `primary_policy_domain` (guns), `topic_subject_secondary_guns_policy` (open-ended) |
| `semantic_content` | `causal_claim_present`, `normative_moral_language`, `persuasion_or_argumentation` |
| `pragmatics_intent` | `call_to_action`, `ridicule_or_mockery` |
| `target_directionality` | `us_vs_them_framing`, `left_right_directional_cue`, `mirror_shift_direction` (open-ended) |
| `compositional_syntax` | `contrastive_but_however_structure`, `second_person_direct_address` |

## Stage 2 — synthesized themes

Source: `outputs/2026_08_01-13:22:13.855934/00000_2026_08_01-13:22:25.665480.json`

| id | Theme | keep | remove |
| -- | ----- | ---- | ------ |
| 1 | Partisan culture-war policy debates (abortion/guns) | 1 | 1 |
| 2 | Named individuals/organizations and direct @ handle mentions | 1 | 1 |
| 3 | Mockery/derogatory labeling and negative character judgment | 1 | 1 |
| 4 | Victimhood/persecution or harm framing (especially in abortion post) | 1 | 0 |
| 5 | Call to action / direct audience instruction | 0 | 1 |
| 6 | Argumentation via concrete case or causal explanation | 1 | 1 |
| 7 | Contrast/mirror framing with reversed blame | 1 | 1 |

### Cross-cutting themes

1. Partisan culture-war policy debates (abortion/guns)
2. Named individuals/organizations and direct @ handle mentions
3. Mockery/derogatory labeling and negative character judgment
4. Argumentation via concrete case or causal explanation
5. us_vs_them framing / ideological side cues (left/right labels and mirror shifts)

## Interpretation (smoke-scale)

With the aligned category checklists, stage 1 now tags features against the six fixed lists (e.g. `primary_policy_domain`, `mirror_shift_direction`, `contrastive_but_however_structure`) rather than ad-hoc feature names. The keep-rated post drew heavily from `topic_subject` and `semantic_content` around an Arkansas abortion-ban case; the remove-rated post used `target_directionality` and `compositional_syntax` around guns/NRA rhetoric with mirror reversal. This remains a 2-post sanity check only.

## Artifacts on disk

```
experiments/llm_based_feature_generation_2026_07_31/outputs/
├── 2026_08_01-13:21:54.416519/          # stage 1 run
│   ├── metadata.json
│   └── 00000_2026_08_01-13:22:13.854743.json
└── 2026_08_01-13:22:13.855934/          # stage 2 run
    ├── metadata.json
    └── 00000_2026_08_01-13:22:25.665480.json
```

## Next step

Per the plan approval gate, **do not start Step 5** (50% production run + `RESULTS.md`) until you explicitly approve these smoke results.
