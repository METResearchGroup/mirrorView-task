# Smoke test results

**Date:** 2026-07-31  
**Status:** Passed (`smoke: ok`)  
**Command:**

```bash
PYTHONPATH=. uv run python \
  experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py
```

**Parameters:** `--sample-fraction 1e-6 --keep-per-batch 1 --remove-per-batch 1 --seed 42`  
**Model:** `gpt-5.4-nano`

## Summary

The smoke run sampled **2 posts** from the full corpus (8,792 modal keep/remove rows), formed **1 batch** (1 keep + 1 remove), and completed both pipeline stages end-to-end. Stage 1 extracted **6 features** (3 per post). Stage 2 synthesized **6 themes** plus **2 cross-cutting themes**. No `data/sampled_subset.csv` was created.

| Stage | Output directory | Result file |
| ----- | ---------------- | ----------- |
| 1 — feature generation | `outputs/2026_07_31-21:40:56.846740/` | `00000_2026_07_31-21:41:01.900259.json` |
| 2 — theme synthesis | `outputs/2026_07_31-21:41:01.901175/` | `00000_2026_07_31-21:41:07.613266.json` |

Paths are relative to `experiments/llm_based_feature_generation_2026_07_31/`.

## Posts in the smoke batch

| message_id | Human label |
| ---------- | ----------- |
| `twitter_2059404130087801256` | keep |
| `bluesky_de734bc474bc703ef18a57dd0912b0e59942c19e460a057eda0be98463c587dc` | remove |

## Stage 1 — extracted features

Source: `outputs/2026_07_31-21:40:56.846740/00000_2026_07_31-21:41:01.900259.json`

### Keep-rated post (`twitter_2059404130087801256`)

| Feature | Category | Confidence | Evidence |
| ------- | -------- | ---------- | -------- |
| `targeted_personal_insult` — Uses a derogatory epithet to characterize a named individual | pragmatics_intent | 0.90 | "is a pusillanimous hypocrite" |
| `policy_focus_abortion_restrictions` — Centers on healthcare/pregnancy impacts of abortion bans | topic_subject | 0.92 | "Under Arkansas' Abortion Ban" |
| `medieval_or_barbaric_evaluative_framing` — Employs strong historical barbarism language for moral condemnation | semantic_content | 0.86 | "medieval" |

### Remove-rated post (`bluesky_de734bc474bc703ef18a57dd0912b0e59942c19e460a057eda0be98463c587dc`)

| Feature | Category | Confidence | Evidence |
| ------- | -------- | ---------- | -------- |
| `generic_group_attack` — Attacks a broad group with disparaging terms (e.g., gun owner/gun nut) | pragmatics_intent | 0.88 | "nutcase gun owner" |
| `anti_nra_directive` — Contains an instruction not to trust/heed a named organization | pragmatics_intent | 0.86 | "don't listen to NRA" |
| `causal_reductionism_about_guns` — Asserts a single-cause explanation ("It's always the guns") | semantic_content | 0.85 | "It's always the guns." |

## Stage 2 — synthesized themes

Source: `outputs/2026_07_31-21:41:01.901175/00000_2026_07_31-21:41:07.613266.json`

| id | Theme | keep | remove | Example post |
| -- | ----- | ---- | ------ | ------------ |
| 1 | Targeted disparagement / personal insults | 1 | 0 | `twitter_2059404130087801256` |
| 2 | Policy critique with healthcare/pregnancy impacts | 1 | 0 | `twitter_2059404130087801256` |
| 3 | Barbaric/medieval evaluative framing for condemnation | 1 | 0 | `twitter_2059404130087801256` |
| 4 | Generic group attacks via disparaging generalizations | 0 | 1 | `bluesky_de734bc474bc703ef18a57dd0912b0e59942c19e460a057eda0be98463c587dc` |
| 5 | Explicit distrust / directive not to heed an organization | 0 | 1 | `bluesky_de734bc474bc703ef18a57dd0912b0e59942c19e460a057eda0be98463c587dc` |
| 6 | Simplistic causal explanations about wrongdoing | 0 | 1 | `bluesky_de734bc474bc703ef18a57dd0912b0e59942c19e460a057eda0be98463c587dc` |

### Cross-cutting themes

1. Use of strong disparaging language (personal insults, generic group disparagement, or barbaric framing) across both keep/remove examples.
2. Directed negative stance toward a target (an individual, a broad group, and/or an organization) rather than purely informational discussion.

## Interpretation (smoke-scale)

On this tiny sample, stage 1 produced plausible, moderation-relevant features with quoted evidence spans. Stage 2 grouped them into label-aligned themes: the keep-rated post's features emphasize policy critique plus a personal insult toward a named figure; the remove-rated post's features emphasize generic group attacks, anti-NRA rhetoric, and causal reductionism about guns. This is only a 2-post sanity check — not evidence about broader keep/remove separability.

## Artifacts on disk

```
experiments/llm_based_feature_generation_2026_07_31/outputs/
├── 2026_07_31-21:40:56.846740/          # stage 1 run
│   ├── metadata.json
│   └── 00000_2026_07_31-21:41:01.900259.json
└── 2026_07_31-21:41:01.901175/          # stage 2 run
    ├── metadata.json
    └── 00000_2026_07_31-21:41:07.613266.json
```

Note: an earlier failed stage-1 attempt (`outputs/2026_07_31-21:40:43.258025/`) wrote only `metadata.json` before a schema fix; the successful run above is the one reported here.

## Next step

Per the plan approval gate, **do not start Step 5** (50% production run + `RESULTS.md`) until you explicitly approve these smoke results.
