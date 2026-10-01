# DSPy GEPA results

## Split audit

The setup manifest records 4,051 source rows, 10 exclusions, 4,041 eligible rows, and a 405-row cohort.

## Optimizer run

Smoke run `study2-dspy-gepa-2026-10-01-smoke-b` is awaiting user approval.
Baseline development rows: 61. Contract failures: 0.

| Program | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seed instruction | 61 | 0.285714 | 0.918033 | 0.200000 | 0.500000 |
The candidate GEPA accepted on the balanced validation subsample has the same instruction text as the seed. Its full validation score was 0.5, matching the seed, so it is not a distinct prompt.
The stored rejection log has 3 rows. One is a synthetic guard probe. The other two are optimizer rejections. Later runs will record optimizer rejections only.

## Cost estimates

Low $4.21, median $6.02, high $9.63.
These dollars scale task-call tokens from the task model history to 1,244 planned calls. They do not include reflection-call tokens. The 10-minute, 30-minute, and 2-hour figures are the preliminary planning ranges, not measurements from this smoke.
Preliminary cost ranges were $6, $9, and $18.

## Prompt comparison

Pending selection.

## Metrics

Pending the approved pilot and test evaluation.

## Trace links

Weave project: `mind_technology_lab/dspy_gepa_optimization_2026_09_30`.
