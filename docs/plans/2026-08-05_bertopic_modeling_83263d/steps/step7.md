# Step 7: Full-corpus production run and RESULTS.md

## Goal

Only after **explicit user approval** of Step-6 smoke artifacts: run stages 2–4 on **all** original posts present in the Stage-1 Titan cache (reuse embeddings; do not re-backfill unless cache incomplete), then write `experiments/bertopic_modeling_2026_08_05/RESULTS.md` with model/embedding ids, fit params, topic counts (including noise), label model, figure paths, and artifact run directories.

## Approval gate (mandatory)

**Do not start this step until Step 6 smoke succeeded and the user explicitly approved.**

Before any full-corpus `fit_bertopic.py` invocation:

1. Confirm Step 6 smoke completed (cache + 50-post topics + labels + six figures).
2. Confirm the user has **explicitly approved** proceeding to production.
3. If approval is missing: **stop**. Do not omit `--sample-size` accidentally while intending smoke. Do not write `RESULTS.md` as production.

## Pinned production settings (do not soften)

| Setting | Value |
|---------|-------|
| Corpus | **all** `message_id`s in `outputs/embeddings/original/` joined to `original_text` |
| Text role | `original` only |
| Embedding model | `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized |
| UMAP (fit) | `n_neighbors=15`, `n_components=5`, `min_dist=0.0`, `metric=cosine`, `random_state=42` |
| HDBSCAN | `min_cluster_size=15`, `metric=euclidean`, `cluster_selection_method=eom`, `prediction_data=True` |
| CountVectorizer | `stop_words=english`, `min_df=2` |
| Soft probs | `calculate_probabilities=True` |
| LLM label model | `gpt-5.4-nano` |
| Unanimous rule | `all_linked_fate_raters_same_decision` |
| Keep/remove & unanimous | visualization overlays **only** — never enter fit |

## Caller / unit of work

**In scope:** production Stages 2–4 on full original corpus; `RESULTS.md`; README production command block.

**Out of scope:** re-running 50-post smoke as the production claim; mirror pipeline; `export_features.py`; editing `shared/**`; changing default/dev deps; any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| All four stage scripts under `experiments/bertopic_modeling_2026_08_05/src/` | CLI flags |
| Step-6 smoke artifact dirs + PNGs | Confirm approval basis |
| `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` | Production commands |
| A sibling RESULTS tone reference, e.g. `/workspace/experiments/llm_based_feature_generation_2026_07_31/RESULTS.md` | Structure only |

## Files allowed to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/RESULTS.md` (create/overwrite with production summary)
- `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` (production block: full corpus, no `--sample-size`)
- Runtime artifacts under `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/{topics,labels,figures}/original/` (production runs)
- Stage-1 cache only if incomplete and refresh/backfill is required to cover the modal corpus

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/pyproject.toml`
- `/workspace/experiments/predict_keep_remove_2026_07_01/**`
- Do **not** create `experiments/bertopic_modeling_2026_08_05/tests/`
- Do **not** create `outputs/**/mirror/` in v1

## Production procedure (after approval only)

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

# Stage 1 — reuse cache; refresh only if incomplete
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py

# Stage 2 — FULL corpus (no --sample-size)
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py
# Record TOPICS_RUN=.../outputs/topics/original/<TS>
# Expect metadata.sample_size is null / absent; n_docs ≈ cache n_rows

# Stage 3
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py \
  --topics-run-dir "$TOPICS_RUN"
# Record LABELS_RUN=...

# Stage 4
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py \
  --topics-run-dir "$TOPICS_RUN" \
  --labels-run-dir "$LABELS_RUN"
# Record FIGURES_RUN=...
```

## RESULTS.md required contents

Create `/workspace/experiments/bertopic_modeling_2026_08_05/RESULTS.md` with:

1. Date; explicit note that Step-6 smoke (`--sample-size 50`) was approved before this production run.
2. Embedding: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized; path to `outputs/embeddings/original/`; `n_rows`; dropped ids count.
3. Fit params: UMAP / HDBSCAN / CountVectorizer values above; `calculate_probabilities=True`; `embedding_model=None`.
4. Topic counts: `n_docs`, `n_topics` (excluding −1), `n_noise` (topic −1 count).
5. Label model: `gpt-5.4-nano`; path to labels run; noise policy.
6. Unanimous rule id + short rule text; note that keep/remove and unanimous were overlays only.
7. Paths to the six production figures under `outputs/figures/original/<TS>/`.
8. Repo-relative paths to production `TOPICS_RUN`, `LABELS_RUN`, `FIGURES_RUN`.

## Exact verification commands

```bash
cd /workspace

TOPICS_ROOT=experiments/bertopic_modeling_2026_08_05/outputs/topics/original
TOPICS_RUN=$(ls -1 "$TOPICS_ROOT" | tail -1)
python -c "
import json
m=json.load(open('$TOPICS_ROOT/$TOPICS_RUN/metadata.json'))
assert m.get('sample_size') in (None, 'all') or 'sample_size' not in m or m['sample_size'] is None
assert m.get('llm_used') is False
assert m['n_docs'] > 50
print('production topics OK', m['n_docs'], 'topics', m.get('n_topics'), 'noise', m.get('n_noise'))
"

test -f experiments/bertopic_modeling_2026_08_05/RESULTS.md && echo 'RESULTS present'
grep -E 'gpt-5.4-nano|amazon.titan-embed-text-v2:0|min_cluster_size|unanimous|sample.size 50|approved' \
  experiments/bertopic_modeling_2026_08_05/RESULTS.md | head

FIG_ROOT=experiments/bertopic_modeling_2026_08_05/outputs/figures/original
FIG_RUN=$(ls -1 "$FIG_ROOT" | tail -1)
for f in \
  clusters_by_topic.png clusters_by_keep_remove.png clusters_by_unanimous.png
do
  test -s "$FIG_ROOT/$FIG_RUN/$f" && echo "OK $f"
done
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Approval | production only after explicit Step-6 approval | Full corpus without approval |
| Corpus | `n_docs` ≫ 50; no `--sample-size 50` in production metadata | Smoke presented as production |
| Fit isolation | `llm_used: false` on topics run | LLM inside fit |
| Labels | `gpt-5.4-nano`; noise skipped | Wrong model |
| Figures | six production files; RESULTS links them | Missing PNGs / wrong paths |
| RESULTS.md | records embedding id, fit params, topic/noise counts, label model, unanimous rule, artifact dirs | Missing numbers |
| Shared isolation | no diffs under `shared/` | Shared edits |
| Out of scope | no mirror tree; no `export_features.py` | Scope creep |

## Done when

- User approved Step-6 smoke.
- Production completed on **all** original cached posts: fit → LLM labels → three overlays.
- `RESULTS.md` summarizes production parameters and artifact paths.
- README documents the production command block (no `--sample-size`).
- v1 still has no mirror pipeline and no `export_features.py`.
