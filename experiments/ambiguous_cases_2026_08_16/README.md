# Ambiguous cases (2026-08-16)

Separate posts that sit near a shared keep/remove boundary from posts that only look disagreed on because of sampling noise, rater severity, or conflicting stated rules.

The design is in [`PROPOSAL.md`](./PROPOSAL.md). The implementation plan is in [`docs/plans/2026-08-16_ambiguous_cases_7c2e91/plan.md`](../../docs/plans/2026-08-16_ambiguous_cases_7c2e91/plan.md). Findings are in [`RESULTS.md`](./RESULTS.md).

## Scope

- Data: Study Phase 2 Part 2 linked-fate trials already in the repo
- Includes tied posts with three or more raters
- No new language-model API calls
- No shared registry changes

## How to run

From the repo root, in order:

```bash
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/build_analysis_frame.py
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e1_beta_binomial.py
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e2_rater_effects.py
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e3_response_time.py
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e4_rule_groups.py
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e5_text_predictability.py
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e6_model_difficulty.py
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e7_close_reading_sample.py
```

## Outputs

| Path | Contents |
|------|----------|
| `outputs/frames/trial_frame.csv` | Per-trial decisions and response times |
| `outputs/frames/post_frame.csv` | Per-post aggregates including ties |
| `outputs/e1/` | Beta-binomial scores and summary |
| `outputs/e2/` | Post and rater effects |
| `outputs/e3/` | Response-time slopes and contrasts |
| `outputs/e4/` | Rule-group mapping and disagreement test |
| `outputs/e5/` | Text predictability metrics |
| `outputs/e6/` | Model error bands and abstention curves |
| `outputs/e7/` | Close-reading sample export |
