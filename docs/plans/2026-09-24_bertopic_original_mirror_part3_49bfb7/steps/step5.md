# Step 5: Cross-role analyses (Q2 to Q4)

## Goal

Implement `analyze_cross_role.py` to compute Q2 pair topic agreement, ARI/NMI with Hungarian topic matching, Q3 joint-model role shares and co-assignment, and Q4 within-topic keyword contrasts. Write CSV/parquet artifacts and `summary.json` under `outputs/analyses/cross_role/<UTC_TS>/`. Cover with synthetic unit tests (no network).

## Prerequisites

Assume Steps 1 to 4 are complete (production runs exist; user approved smoke):

1. **Step 1:** Part 3 keep/remove labels registered with `post_id`, `decision`, `original_text`, `mirror_text`, plus metadata columns from Step 1 schema.
2. **Step 4 production outputs:**
   - `outputs/topics/original/<PROD_TS>/` (saved model + assignments)
   - `outputs/topics/mirror/<PROD_TS>/`
   - `outputs/topics/joint/<PROD_TS>/`
   - `outputs/assignments/mirror_via_original/<PROD_TS>/pair_assignments.parquet`
3. Deduped corpus is identical across all production fits (same `dedupe_report.json` content).

Record absolute or repo-relative paths to these runs in `analyze_cross_role.py` CLI defaults, or require explicit `--*-run-dir` flags.

## Caller / unit of work

**Main caller:**

```bash
cd /workspace
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/analyze_cross_role.py \
  --original-topics-run-dir outputs/topics/original/<PROD_TS> \
  --mirror-topics-run-dir outputs/topics/mirror/<PROD_TS> \
  --joint-topics-run-dir outputs/topics/joint/<PROD_TS> \
  --mirror-assignments-run-dir outputs/assignments/mirror_via_original/<PROD_TS> \
  --seed 42 \
  --bootstrap-n 1000
```

**In scope:** `analyze_cross_role.py`, pure helper module if needed (`src/cross_role_metrics.py`), unit tests, analysis artifacts.

**Out of scope:** Q1 Part 2 comparison, Q5 outcome overlays (Step 6), ablations (Step 7), `RESULTS.md` (Step 8), refitting BERTopic.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md` | Q2 to Q4 definitions |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original/<PROD_TS>/assignments.parquet` | Original topic ids per pair |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/assignments/mirror_via_original/<PROD_TS>/pair_assignments.parquet` | Q2 primary input |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/joint/<PROD_TS>/assignments.parquet` | Q3 role shares, co-assignment |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/data.py` | Reload texts for Q4 |
| BERTopic saved models | Topic keywords via `get_topic()` or `topic_info` for Q4; download `model/` from S3 if missing locally |

## Files allowed to change

- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/analyze_cross_role.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/cross_role_metrics.py` (create, optional pure helpers)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_cross_role_q2.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_cross_role_q3.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_cross_role_q4.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_hungarian_topic_match.py` (create)
- Runtime artifacts under `experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/cross_role/`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/pyproject.toml`
- `/workspace/experiments/bertopic_modeling_2026_08_05/**`
- Production topics/labels/figures runs from Step 4 (read-only)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/RESULTS.md`

## Implementation details

### Module layout

| Symbol | Responsibility |
|--------|----------------|
| `analyze_cross_role.run_analyze_cross_role(...)` | Orchestrator; writes output dir |
| `compute_q2_pair_agreement(pair_df, bootstrap_n, seed)` | Agreement rates + CIs |
| `match_topics_hungarian(orig_model, mirror_model, paired_topics)` | Centroid cosine similarity matrix; `scipy.optimize.linear_sum_assignment` on cost `1 - cosine_sim` |
| `compute_ari_nmi(orig_topics, mirror_topics, mapping)` | On paired posts after mapping |
| `compute_q3_role_shares(joint_assignments)` | Per-topic original share; binomial test vs 0.5; BH FDR |
| `compute_q3_coassignment(joint_assignments)` | Pair same-topic rate under joint model |
| `compute_q4_keyword_contrast(docs_by_role, joint_topics)` | Per-topic log-odds with Dirichlet prior |

CLI flags: `--original-topics-run-dir`, `--mirror-topics-run-dir`, `--joint-topics-run-dir`, `--mirror-assignments-run-dir`, `--seed` (default 42), `--bootstrap-n` (default 1000), `--output-dir` (optional; default `outputs/analyses/cross_role/<UTC_TS>/`).

### Q2: Pair topic agreement (primary metric)

**Input:** `pair_assignments.parquet` from `assign_mirrors.py`.

| Metric | Definition |
|--------|------------|
| `agreement_rate_all` | fraction where `original_topic == mirror_topic` (includes -1) |
| `agreement_rate_excl_noise` | same, excluding pairs where either topic is -1 |
| `n_pairs`, `n_agree`, `n_agree_excl_noise` | counts |

**Bootstrap CI:** resample `post_id` with replacement `bootstrap_n` times (seeded RNG); recompute each rate; report 2.5th and 97.5th percentiles.

**Output:** `q2_pair_agreement.parquet`

| Column | Type |
|--------|------|
| `metric` | str (`agreement_rate_all`, `agreement_rate_excl_noise`) |
| `point_estimate` | float |
| `ci_low` | float |
| `ci_high` | float |
| `n_pairs` | int |
| `bootstrap_n` | int |
| `seed` | int |

### Q2 supplement: ARI and NMI after Hungarian matching

On deduped pairs present in both original and mirror production assignments:

1. Build topic centroids: mean embedding per topic (exclude -1) from each model's fit corpus.
2. Cosine similarity matrix between original topics (rows) and mirror topics (cols).
3. `linear_sum_assignment(1 - sim)` yields `orig_topic -> mirror_topic` mapping (unmapped topics omitted).
4. Remap mirror topic ids on paired posts; compute `sklearn.metrics.adjusted_rand_score` and `normalized_mutual_info_score` on the paired topic label vectors.

**Output:** `q2_ari_nmi.json`

```json
{
  "n_pairs": 0,
  "n_original_topics_matched": 0,
  "n_mirror_topics_matched": 0,
  "ari": 0.0,
  "nmi": 0.0,
  "topic_mapping": [{"original_topic": 0, "mirror_topic": 1, "cosine_sim": 0.0}]
}
```

### Q3: Joint-model role signature

**Per-topic role share** from joint `assignments.parquet`:

For each `topic` (exclude -1 optional; include but flag in metadata):

| Column | Type |
|--------|------|
| `topic` | int |
| `n_docs` | int |
| `n_original` | int |
| `n_mirror` | int |
| `original_share` | float (`n_original / n_docs`) |
| `binomial_pvalue` | float (two-sided `scipy.stats.binomtest` vs p=0.5) |
| `q_value_bh` | float (Benjamini-Hochberg across topics) |
| `role_dominated_flag` | bool (`original_share` outside [0.35, 0.65] AND `q_value_bh < 0.05) |

**Pair co-assignment rate:** fraction of pairs where joint model assigns the same `topic` to original and mirror rows.

**Outputs:**

- `q3_role_shares.parquet` (schema above)
- `q3_coassignment.json`: `{"pair_coassignment_rate": 0.0, "n_pairs": 0, "n_coassigned": 0}`

### Q4: Within-topic keyword contrast

For each joint topic `t` (exclude -1):

1. Collect `original_text` and `mirror_text` for docs assigned topic `t`.
2. Build class-based TF-IDF counts per role (same vectorizer settings as fit: english stopwords, `min_df=2` applied within the topic subset or use precomputed c-TF-IDF terms from BERTopic if available).
3. For each term, compute log-odds ratio with informative Dirichlet prior (Monroe et al. style):

```
delta(w) = log((count_o(w) + alpha) / (N_o - count_o(w) + alpha)) -
           log((count_m(w) + alpha) / (N_m - count_m(w) + alpha))
```

Use `alpha = 0.01` (document in metadata). Rank by `abs(delta)`; keep top 15 terms favoring original and top 15 favoring mirror per topic.

**Output:** `q4_keyword_contrast.parquet`

| Column | Type |
|--------|------|
| `topic` | int |
| `term` | str |
| `role` | str (`original` or `mirror`) |
| `rank` | int (1..15 within role for that topic) |
| `log_odds` | float |
| `count_original` | int |
| `count_mirror` | int |

### `summary.json` (required for Steps 6 to 8)

`outputs/analyses/cross_role/<UTC_TS>/summary.json`:

```json
{
  "analysis_timestamp": "<UTC_TS>",
  "seed": 42,
  "bootstrap_n": 1000,
  "source_runs": {
    "original_topics": "...",
    "mirror_topics": "...",
    "joint_topics": "...",
    "mirror_assignments": "..."
  },
  "q2": {
    "agreement_rate_all": 0.0,
    "agreement_rate_excl_noise": 0.0,
    "ari": 0.0,
    "nmi": 0.0
  },
  "q3": {
    "n_role_dominated_topics": 0,
    "pair_coassignment_rate": 0.0
  },
  "q4": {
    "n_topics_contrasted": 0,
    "dirichlet_alpha": 0.01
  },
  "artifact_paths": {
    "q2_pair_agreement": "q2_pair_agreement.parquet",
    "q2_ari_nmi": "q2_ari_nmi.json",
    "q3_role_shares": "q3_role_shares.parquet",
    "q3_coassignment": "q3_coassignment.json",
    "q4_keyword_contrast": "q4_keyword_contrast.parquet"
  }
}
```

## TDD tests first

Use tiny synthetic frames (5 pairs, 3 topics). No BERTopic fit in tests; inject topic labels and term counts directly.

### `tests/test_analyze_cross_role_q2.py`

```python
class TestQ2PairAgreement:
    def test_agreement_rate_all_includes_noise_matches(self):
        df = pd.DataFrame({
            "original_topic": [-1, 0, 1],
            "mirror_topic": [-1, 0, 2],
        })
        assert compute_q2_pair_agreement(df, bootstrap_n=100, seed=42)["agreement_rate_all"] == 2/3

    def test_agreement_rate_excl_noise_drops_noise_rows(self):
        # pair with (-1, 0) excluded from denominator
        ...

    def test_bootstrap_ci_bounds_contain_point_estimate(self):
        ...
```

### `tests/test_hungarian_topic_match.py`

```python
class TestHungarianTopicMatch:
    def test_maps_high_cosine_topic_pairs(self):
        # 2x2 similarity [[1,0],[0,1]] -> identity mapping
        mapping = match_topics_hungarian(sim_matrix, orig_ids=[0,1], mirror_ids=[0,1])
        assert mapping[0] == 0 and mapping[1] == 1

    def test_ari_perfect_when_mapped_labels_match(self):
        assert adjusted_rand_score([0,0,1], [0,0,1]) == 1.0
```

### `tests/test_analyze_cross_role_q3.py`

```python
class TestQ3RoleShares:
    def test_original_share_0_5_when_balanced(self):
        # 10 docs topic 0: 5 original, 5 mirror -> share 0.5
        ...

    def test_role_dominated_flag_requires_q_below_0_05_and_share_outside_band(self):
        row = flag_role_dominated(original_share=0.9, q_value_bh=0.01)
        assert row is True
        assert flag_role_dominated(original_share=0.9, q_value_bh=0.10) is False

class TestQ3Coassignment:
    def test_coassignment_rate_one_when_same_topic(self):
        # 4 pairs all co-assigned -> rate 1.0
        ...
```

### `tests/test_analyze_cross_role_q4.py`

```python
class TestQ4KeywordContrast:
    def test_log_odds_positive_favors_original(self):
        delta = log_odds_with_dirichlet(count_o=10, count_m=0, n_o=20, n_m=20, alpha=0.01)
        assert delta > 0

    def test_top_15_per_role_per_topic(self):
        rows = compute_q4_keyword_contrast(synthetic_docs, topic_id=0)
        assert len(rows[rows.role == "original"]) == 15
```

Run before live analysis:

```bash
cd /workspace
PYTHONPATH=. uv run --extra bertopic pytest \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_cross_role_q2.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_hungarian_topic_match.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_cross_role_q3.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_cross_role_q4.py -q
```

Expected: all tests pass without network.

## Exact commands

### Unit tests

```bash
cd /workspace
PYTHONPATH=. uv run --extra bertopic pytest \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_cross_role_q2.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_hungarian_topic_match.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_cross_role_q3.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_cross_role_q4.py -q
```

Expected: `passed` with zero failures.

### Live cross-role analysis (requires Step 4 production runs)

```bash
cd /workspace
EXP=experiments/bertopic_original_mirror_part3_2026_09_24
ORIG=$(ls -1 $EXP/outputs/topics/original | tail -1)
MIR=$(ls -1 $EXP/outputs/topics/mirror | tail -1)
JOINT=$(ls -1 $EXP/outputs/topics/joint | tail -1)
ASN=$(ls -1 $EXP/outputs/assignments/mirror_via_original | tail -1)

PYTHONPATH=. uv run --extra bertopic python $EXP/src/analyze_cross_role.py \
  --original-topics-run-dir $EXP/outputs/topics/original/$ORIG \
  --mirror-topics-run-dir $EXP/outputs/topics/mirror/$MIR \
  --joint-topics-run-dir $EXP/outputs/topics/joint/$JOINT \
  --mirror-assignments-run-dir $EXP/outputs/assignments/mirror_via_original/$ASN \
  --seed 42 --bootstrap-n 1000
```

Expected stdout: `analysis_run_dir=.../outputs/analyses/cross_role/<UTC_TS>` and `summary.json` written.

Verify artifacts:

```bash
RUN=experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/cross_role/$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/cross_role | tail -1)
for f in q2_pair_agreement.parquet q2_ari_nmi.json q3_role_shares.parquet q3_coassignment.json q4_keyword_contrast.parquet summary.json; do
  test -f "$RUN/$f" && echo "OK $f" || echo "MISSING $f"
done
```

## Pass/fail criteria

| Check | Pass | Fail |
|-------|------|------|
| Q2 primary | uses `pair_assignments.parquet`; reports both agreement rates | Recomputes transform |
| Bootstrap | `bootstrap_n=1000`, `seed=42`; CIs in output | No CI or wrong seed |
| Hungarian | `linear_sum_assignment` on `1 - cosine_sim` | Greedy or label matching without centroids |
| ARI/NMI | computed on paired posts after mapping | Raw unmapped topic ids compared |
| Q3 FDR | BH correction across topics | Uncorrected p-values only |
| Q3 flag | `[0.35, 0.65]` band AND `q < 0.05` | Either condition alone |
| Q4 contrast | log-odds with Dirichlet `alpha=0.01`; 15 terms per role per topic | Raw count diff only |
| summary.json | lists all artifact paths and source runs | Missing source run metadata |
| Tests | pytest green on synthetic data | Live data required for unit tests |
| No refit | does not call `fit_transform` | Refits BERTopic |

## Commit messages

1. `test(bertopic-part3): add cross-role Q2 agreement unit tests`
2. `test(bertopic-part3): add Hungarian topic matching tests`
3. `test(bertopic-part3): add Q3 role share and coassignment tests`
4. `test(bertopic-part3): add Q4 keyword contrast tests`
5. `feat(bertopic-part3): implement analyze_cross_role for Q2 to Q4`
6. `chore(bertopic-part3): write cross_role analysis artifacts` (optional, if committing outputs)

Do not batch test and implementation commits together.
