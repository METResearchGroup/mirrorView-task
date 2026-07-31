# RESULTS — LLM-based feature generation (1% pilot)

**Status:** 1% pilot succeeded. Full **50%** corpus run is **gated** (not run).

## Setup

| Item | Value |
|------|--------|
| Data | Study 2 training frame (`experiments/predict_keep_remove_2026_07_01/data/dataloader.py`) |
| Corpus size | 8791 posts (5978 keep / 2813 remove) |
| Sample fraction | **0.01** (seed 42) |
| Sample size | 89 posts → **2** full batches of 10 keep + 10 remove (40 posts used; 49 leftover) |
| Model | `gpt-5.4-nano` |
| Stage 1 output | `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_07_31-16:43:10.068964` |
| Stage 2 output | `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_07_31-16:44:11.247694` |

Duplicate prevention in this run: stratified sample without replacement; unique `message_id` across batches (asserted); ids recorded in stage-1 `metadata.json` → `run_metadata.message_ids`. Re-runs can pass `--exclude-ids-from` that metadata path.

## Pilot themes (n=9)

1. **Political contempt & competence attacks** — short dismissive judgments of actors’ competence/character (label mix keep 2 / remove 4).
2. **Profanity-heavy, emotionally escalating rhetoric** — expletives, all-caps, outrage interjections (keep 0 / remove 5).
3. **Rights/civil-liberties framing** — constitutional/moral stakes (keep 5 / remove 0).
4. **Conditional & contrastive discourse structure** — but/yet/if scaffolding (keep 4 / remove 2).
5. **Policy preference lists & concrete mechanisms** — actionable proposals (keep 6 / remove 0).
6. **Event/time anchoring & mobilization** — weekends, awareness months, campaign launches (keep 5 / remove 0).
7. **Delegitimization via org/group labels** — named institutions and categorical group labels (keep 2 / remove 4).
8. **Fear/harm prediction & extreme framing** — future-harm alarms, extreme comparisons (keep 1 / remove 3).
9. **Direct personal address & targeted attacks** — 2nd-person imperatives / personal attacks (keep 0 / remove 4).

### Cross-cutting

- Contrastive/conditional scaffolding appears in both keep and remove; structure alone is not decisive.
- Rights/policy framing aligns with keep when paired with non-abusive, mechanism-oriented content.
- High-intensity language is a recurring pathway to remove when combined with personal address or extreme delegitimization.

## Caveats

- Pilot only (2 batches / 40 posts). Themes are exploratory, not definitive population estimates.
- Leftover posts (49) did not fill another 10+10 batch under stratified 1% sampling (remove class is the bottleneck).
- Failed partial run folder `outputs/2026_07_31-16:42:31.178012` predates the schema fix (OpenAI required-all-properties); ignore it.

## Gate for 50%

Do **not** run `--sample-fraction 0.50` until cost/time is explicitly approved. Expected scale ≈ 50× this pilot’s LLM volume (roughly ~100+ stage-1 batches before leftovers).
