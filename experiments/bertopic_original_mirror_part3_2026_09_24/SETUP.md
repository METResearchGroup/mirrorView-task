# Setup

Required data:

- `STUDY_PHASE_2_PART_3_STIMULI`: 18,899 posts (`post_primary_key`, `original_text`, `mirrored_text`)
- `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS`: 18,866 rated posts, used as outcome overlays only
- `STUDY_PHASE_2_PART_3_RESULTS_FULL`: rater-party cuts in later steps

Install the topic-model extra:

```bash
uv sync --extra bertopic
```

Stage 1 caches Titan and MiniLM vectors for all 18,899 stimulus posts, before dedupe:

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py \
  --text-role original --refresh-from-identity-cache --backfill
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings_minilm.py \
  --text-role original
```

Repeat both commands with `--text-role mirror`. Embedding backfill needs AWS credentials:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

Large artifacts (`embeddings.npy`, BERTopic `model/` directories, `umap_2d.npy`) are gitignored. They live in S3 at `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/` with the same relative paths. Small artifacts stay in git: `index.parquet`, `metadata.json`, the dedupe report, assignments, topic info, labels, analysis tables, and figure PNGs.
