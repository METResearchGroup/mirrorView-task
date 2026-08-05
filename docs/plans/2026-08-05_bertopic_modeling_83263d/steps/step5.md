# Step 5: Implement three-overlay cluster visualizations

## Goal

Implement `experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py` to load one shared `umap_2d.npy` from a topics run plus topic assignments and overlay columns, then emit **six** figure files (HTML + PNG × three overlays) under `outputs/figures/original/<UTC_TS>/`. Recolor only — do not recompute UMAP or recluster.

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py \
  --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>
```

Optional: `--labels-run-dir` if topic-color legend should show LLM labels (not required for scatter coordinates). Overlay colors for keep/remove and unanimous come from `data.load_posts_with_unanimous()`, not from Stage 3.

**In scope:** Stage-4 Plotly HTML + PNG exports.

**Out of scope:** refitting, relabeling, Bedrock, mirror, `RESULTS.md`, any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` | Three overlays; HTML+PNG; color meanings |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/data.py` | `decision`, `is_unanimous` join |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/paths.py` | `figures_dir` |
| Topics-run `umap_2d.npy` + `assignments.parquet` | Shared projection + topic ids |
| Plotly / kaleido (installed via `--extra bertopic`) | HTML write + static PNG export |

## Files allowed to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py`
- `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` (Stage-4 CLI + figure names)
- Runtime artifacts under `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/figures/original/`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/pyproject.toml` (plotly/kaleido already in Step-1 extra)
- `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/topics/**` (read-only)
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py`
- Do **not** create `experiments/bertopic_modeling_2026_08_05/tests/`

## Contracts

### Inputs

1. Load `umap_2d.npy` shape `(n, 2)` and `assignments.parquet` from `--topics-run-dir`.
2. Join overlay columns on `message_id`:
   - `topic` from assignments
   - `decision` ∈ {`keep`, `remove`} from modal labels
   - `is_unanimous` bool from Step-1 unanimous join (`UNANIMOUS_RULE_ID`)
3. Row order for plotting must match `umap_2d` / assignments alignment from the topics run. Raise `ValueError` on length mismatch or missing join keys.

### Three overlays (exact colors)

| File stem | Color rule |
|-----------|------------|
| `clusters_by_topic` | discrete color per `topic` id (include −1 as its own category, visually distinct) |
| `clusters_by_keep_remove` | `keep` → green; `remove` → red |
| `clusters_by_unanimous` | `is_unanimous=True` → green; `False` → red |

Hover (HTML) should include at least: `message_id`, `topic`, `decision`, `is_unanimous`. Optional: LLM label if `--labels-run-dir` provided.

### Outputs

`experiments/bertopic_modeling_2026_08_05/outputs/figures/original/<UTC_TS>/`

```text
clusters_by_topic.html
clusters_by_topic.png
clusters_by_keep_remove.html
clusters_by_keep_remove.png
clusters_by_unanimous.html
clusters_by_unanimous.png
metadata.json
```

`metadata.json` required keys: `source_topics_run`, `source_labels_run` (nullable), `unanimous_rule_id` (= `all_linked_fate_raters_same_decision`), `n_points`, figure filenames, color legend description.

### Rendering rules

1. Use **one** coordinate matrix (`umap_2d.npy`) for all three overlays.
2. Prefer Plotly scatter for HTML; export PNG via kaleido (`fig.write_image`).
3. Do not fit a new UMAP inside this stage.
4. Titles must name the overlay (topic / keep-remove / unanimous).

## Exact commands

### Offline wiring

```bash
cd /workspace

PYTHONPATH=. uv run --extra bertopic python -c "
from experiments.bertopic_modeling_2026_08_05.src import visualize_clusters as m
import plotly
import kaleido
assert hasattr(m, 'main') or hasattr(m, 'run_visualize_clusters')
print('visualize_clusters wiring OK')
"
```

### Live viz (requires a topics run from Step 3)

```bash
cd /workspace

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py \
  --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/UTC_TS
```

Verify six non-empty figure files:

```bash
FIG=experiments/bertopic_modeling_2026_08_05/outputs/figures/original
RUN=$(ls -1 "$FIG" | tail -1)
for f in \
  clusters_by_topic.html clusters_by_topic.png \
  clusters_by_keep_remove.html clusters_by_keep_remove.png \
  clusters_by_unanimous.html clusters_by_unanimous.png
do
  test -s "$FIG/$RUN/$f" && echo "OK $f" || echo "MISSING $f"
done
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Shared UMAP | all three overlays use same `umap_2d.npy` | Refit UMAP per overlay |
| Colors | keep/unanimous green; remove/not-unanimous red | Arbitrary palette without mapping |
| Six files | HTML+PNG × 3, all non-empty | Missing PNG or HTML |
| Metadata | records `unanimous_rule_id` + source topics run | Missing provenance |
| No reclustering | does not import/fit BERTopic/HDBSCAN | Fit inside viz |

## Done when

- Stage 4 writes six figure files from one 2-D projection with the three contracted overlays.
- Metadata records unanimous rule id and source topics run.
- Offline wiring passes; live viz succeeds against a topics run.
- README documents Stage-4 CLI and exact filenames.
