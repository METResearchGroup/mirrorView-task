# Step 6: Smoke end-to-end on 50 posts (approval gate)

## Goal

Run stages 1–4 on a fixed sample of **50** original posts. Confirm the Titan cache, topics run, LLM labels, and all six figure files land. **Stop and wait for explicit user approval.** Do **not** run the full-corpus production path. Do **not** write production `RESULTS.md`.

## Approval gate (mandatory)

**Do not start Step 7 until the user explicitly approves after reviewing smoke artifacts.**

Before any full-corpus invocation (Step 7):

1. Confirm Stage 1 cache exists under `outputs/embeddings/original/`.
2. Confirm Stage 2 smoke topics run used `--sample-size 50` (`metadata.json` `sample_size: 50`).
3. Confirm Stage 3 labels exist and skip topic `-1`.
4. Confirm all six Stage-4 figure files are non-empty.
5. Confirm the user has **explicitly approved** proceeding to production.
6. If approval is missing: **stop**. Do not omit `--sample-size`. Do not write production `RESULTS.md`.

## Caller / unit of work

**Smoke pins:**

| Flag / setting | Smoke value |
|----------------|-------------|
| Embedding cache | full original cache (Stage 1); fit samples 50 ids |
| `--sample-size` (fit) | `50` |
| `--seed` | `42` |
| HDBSCAN `min_cluster_size` | smoke override from Step 3 (`5` or documented formula) |
| LLM model | `gpt-5.4-nano` |
| Figures | six files under `outputs/figures/original/<TS>/` |

**Production sizes are Step 7 only** (all original posts in the cache). Do not invoke them here.

**In scope:** end-to-end smoke; README notes for smoke vs production + approval gate pointing to Step 7.

**Out of scope:** full-corpus fit; writing production `RESULTS.md`; mirror pipeline; `export_features.py`; editing `shared/**`; creating `tests/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| All four stage scripts under `experiments/bertopic_modeling_2026_08_05/src/` | CLI flags |
| Smoke artifact dirs under `outputs/{embeddings,topics,labels,figures}/original/` | Verify before asking for approval |
| `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` | Update smoke vs production commands |
| `/workspace/docs/plans/2026-08-05_bertopic_modeling_83263d/steps/step7.md` | Production path after approval |

## Files allowed to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` (smoke vs production + approval gate → Step 7)
- Runtime artifacts under `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/**` (smoke only)
- Minor CLI fixes in the four `src/` stage scripts **only** if smoke reveals broken flags/paths (no scope expansion)

## Files forbidden to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/RESULTS.md` — do **not** create/overwrite as production results in this step
- `/workspace/shared/**`
- `/workspace/pyproject.toml`
- `/workspace/experiments/predict_keep_remove_2026_07_01/**`
- Do **not** create `experiments/bertopic_modeling_2026_08_05/tests/`
- Do not run full-corpus `fit_bertopic.py` without `--sample-size`

## Smoke procedure (exact)

Run from repo root. Requires AWS only if Stage-1 cache is missing; requires `OPENAI_API_KEY` in repo-root `.env` for Stage 3.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

# --- Stage 1 ---
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py \
  --refresh-from-identity-cache
# If cache already complete, the default (no --refresh) path is enough:
# PYTHONPATH=. uv run --extra bertopic python \
#   experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py

# --- Stage 2 (50-post smoke) ---
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py \
  --sample-size 50 --seed 42
# Record TOPICS_RUN=.../outputs/topics/original/<TS>

# --- Stage 3 ---
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py \
  --topics-run-dir "$TOPICS_RUN"
# Record LABELS_RUN=.../outputs/labels/original/<TS>

# --- Stage 4 ---
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py \
  --topics-run-dir "$TOPICS_RUN" \
  --labels-run-dir "$LABELS_RUN"
# Record FIGURES_RUN=.../outputs/figures/original/<TS>
```

### Smoke pass checklist

| Check | Pass |
|-------|------|
| Stage 1 | `outputs/embeddings/original/{embeddings.npy,index.parquet,metadata.json}` exist; `dimensions=256` |
| Stage 2 | topics run `metadata.json` has `sample_size: 50`, `llm_used: false`; `umap_2d.npy` shape `(50, 2)` |
| Stage 3 | `topic_labels.parquet` has LLM labels for non-noise topics; metadata `model=gpt-5.4-nano`; `source_topics_run` set |
| Stage 4 | all six figure files non-empty; metadata `unanimous_rule_id=all_linked_fate_raters_same_decision` |
| No production | no full-corpus fit; no production `RESULTS.md` |

**Stop here and ask the user to review smoke artifacts (especially the three PNG overlays) before Step 7.**

## Exact verification commands

```bash
cd /workspace

test -f experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/embeddings.npy
test -f experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/index.parquet
test -f experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/metadata.json

TOPICS_ROOT=experiments/bertopic_modeling_2026_08_05/outputs/topics/original
TOPICS_RUN=$(ls -1 "$TOPICS_ROOT" | tail -1)
python -c "import json; m=json.load(open('$TOPICS_ROOT/$TOPICS_RUN/metadata.json')); assert m['sample_size']==50; assert m['llm_used'] is False; print('topics smoke OK', '$TOPICS_RUN')"

LABELS_ROOT=experiments/bertopic_modeling_2026_08_05/outputs/labels/original
LABELS_RUN=$(ls -1 "$LABELS_ROOT" | tail -1)
test -f "$LABELS_ROOT/$LABELS_RUN/topic_labels.parquet"
test -f "$LABELS_ROOT/$LABELS_RUN/metadata.json"

FIG_ROOT=experiments/bertopic_modeling_2026_08_05/outputs/figures/original
FIG_RUN=$(ls -1 "$FIG_ROOT" | tail -1)
for f in \
  clusters_by_topic.html clusters_by_topic.png \
  clusters_by_keep_remove.html clusters_by_keep_remove.png \
  clusters_by_unanimous.html clusters_by_unanimous.png
do
  test -s "$FIG_ROOT/$FIG_RUN/$f" && echo "OK $f"
done

# Must NOT claim production yet
test ! -f experiments/bertopic_modeling_2026_08_05/RESULTS.md \
  || ! grep -qi 'full.corpus\|production' experiments/bertopic_modeling_2026_08_05/RESULTS.md
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Smoke 50 | topics metadata `sample_size=50`; umap `(50,2)` | Full corpus or other N |
| Six figures | all non-empty | Missing PNG/HTML |
| Labels | gpt-5.4-nano; noise skipped | Wrong model / noise labeled |
| No production | no full fit; no production RESULTS | Step 7 done early |
| Approval gate | stop and wait | Production started without approval |

## Done when

- Tiny live smoke completed: Stage 1 cache + 50-post fit + LLM labels + six figures.
- User has been asked to review smoke artifacts; Step 7 is blocked until explicit approval.
- README documents smoke (`--sample-size 50`) vs production (full corpus) and the approval gate.
- Production full-corpus run and `RESULTS.md` are **not** done in this step.
