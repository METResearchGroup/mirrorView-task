# Setup

Required data (load with `shared.data.dataloader.load_dataset` from `s3://mirrorview-experimental-artifacts/`):

| Registry name | Role | Counts |
| --- | --- | --- |
| `STUDY_PHASE_2_PART_2_AND_3_STIMULI` | Stimulus catalog (`post_primary_key`, `original_text`, `mirrored_text`, facets) | 20,000 unique posts: Part 2 catalog 10,000, Part 3 catalog 18,899, overlap 8,899 identical texts/facets. On overlap, the union keeps the Part 2 row. |
| `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` | Linked-fate session export | 168,871 rows, 5,051 Prolific accounts (1,176 Part 2 only, 3,875 Part 3 only, no account overlap). Includes 108,213 scored `linked_fate` ratings. |
| `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS` | Modal keep/remove per post (outcomes only; not used to fit topics) | 20,000 posts, 103,060 ratings, 15,140 keep / 4,860 remove. Every post has at least 3 raters. |

Keep/remove labels are built from the combined results table with `shared/data/transformed/study_phase_2_part_2_and_3/transform.py` (materializes `shared/data/transformed/study_phase_2_part_2_and_3/keep_remove_labels.csv`).

S3 keys for the raw CSVs follow the repo layout under `shared/data/raw/study_phase_2_part_2_and_3/`. See `shared/data/raw/study_phase_2_part_2_and_3/README.md`.

## Pipeline commands

Run from the repo root. Set `EXP=experiments/bertopic_original_mirror_part3_2026_09_24`. Titan backfill and DynamoDB identity lookups need AWS credentials:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

**Embeddings** (all 20,000 union stimuli, before dedupe). Seed from the Part 3-only on-disk role cache, then fill gaps from the identity cache, then Bedrock when `--backfill` is set:

```bash
PYTHONPATH=. uv run --extra bertopic python $EXP/src/load_embeddings.py \
  --text-role original \
  --seed-from-local-cache $EXP/outputs/embeddings/original \
  --refresh-from-identity-cache --backfill
PYTHONPATH=. uv run --extra bertopic python $EXP/src/load_embeddings.py \
  --text-role mirror \
  --seed-from-local-cache $EXP/outputs/embeddings/mirror \
  --refresh-from-identity-cache --backfill
PYTHONPATH=. uv run --extra bertopic python $EXP/src/load_embeddings_minilm.py \
  --text-role original \
  --seed-from-local-cache $EXP/outputs/embeddings_minilm/original
PYTHONPATH=. uv run --extra bertopic python $EXP/src/load_embeddings_minilm.py \
  --text-role mirror \
  --seed-from-local-cache $EXP/outputs/embeddings_minilm/mirror
```

**Fits** (`--seed 42`):

```bash
for ROLE in original mirror joint; do
  PYTHONPATH=. uv run --extra bertopic python $EXP/src/fit_bertopic.py \
    --text-role "$ROLE" --seed 42
done
```

**Labels** (`gpt-5.4-nano`; pass each fit’s `outputs/topics/<role>/<run_id>`):

```bash
PYTHONPATH=. uv run --extra bertopic python $EXP/src/label_topics_llm.py \
  --text-role original --topics-run-dir $EXP/outputs/topics/original/<run_id>
# repeat for mirror and joint
```

**Mirror assignment via original model:**

```bash
PYTHONPATH=. uv run --extra bertopic python $EXP/src/assign_mirrors.py \
  --original-topics-run-dir $EXP/outputs/topics/original/<run_id>
```

**Analyses and figures** (union production example run IDs: original `20260924T135151Z`, mirror `20260924T135244Z`, joint `20260924T135414Z`, mirror assignments `20260924T135936Z`):

```bash
PYTHONPATH=. uv run --extra bertopic python $EXP/src/analyze_cross_role.py \
  --original-topics-run-dir $EXP/outputs/topics/original/<run_id> \
  --mirror-topics-run-dir $EXP/outputs/topics/mirror/<run_id> \
  --joint-topics-run-dir $EXP/outputs/topics/joint/<run_id> \
  --mirror-assignments-run-dir $EXP/outputs/assignments/mirror_via_original/<run_id>

PYTHONPATH=. uv run --extra bertopic python $EXP/src/compare_part2.py \
  --topics-run-dir $EXP/outputs/topics/original/<run_id>

PYTHONPATH=. uv run --extra bertopic python $EXP/src/analyze_outcomes.py \
  --topics-run-dir $EXP/outputs/topics/original/<run_id> \
  --joint-topics-run-dir $EXP/outputs/topics/joint/<run_id> \
  --n-bootstrap 2000 --bootstrap-seed 42

for ROLE in original mirror joint; do
  PYTHONPATH=. uv run --extra bertopic python $EXP/src/visualize_clusters.py \
    --text-role "$ROLE" \
    --topics-run-dir $EXP/outputs/topics/$ROLE/<run_id> \
    --labels-run-dir $EXP/outputs/labels/$ROLE/<labels_run_id>
done
```

**Ablations and S3 upload:**

```bash
PYTHONPATH=. uv run --extra bertopic python $EXP/src/run_ablations.py \
  --ablation all \
  --production-original-run-dir $EXP/outputs/topics/original/<run_id> \
  --production-joint-run-dir $EXP/outputs/topics/joint/<run_id> \
  --seed 42

PYTHONPATH=. uv run --extra bertopic python $EXP/src/upload_outputs.py
# optional: add --dry-run
```

Large artifacts (`embeddings.npy`, BERTopic `model/` trees, `umap_2d.npy`, HTML figures) are gitignored and mirrored under `s3://mirrorview-experimental-artifacts/$EXP/`.
