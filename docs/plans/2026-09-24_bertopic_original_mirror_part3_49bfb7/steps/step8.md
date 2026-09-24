# Step 8: Write RESULTS.md and upload outputs to S3

## Goal

Write `experiments/bertopic_original_mirror_part3_2026_09_24/RESULTS.md` summarizing production counts, topic labels, Q1 through Q5 tables, ablation sensitivity, and limitations. Upload the full `outputs/` tree to `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/` with verification. Document what stays in git versus S3 only (large `embeddings.npy`, `model/` dirs, and `umap_2d.npy` are S3-primary). Run final checks: pytest for all Part 3 tests; confirm Part 2 experiment folder unchanged.

## Prerequisites

- Steps 1 through 7 complete: production fits, labels, figures, cross-role analyses, Q5/Q1 outcomes, ablations `summary.csv`, human review markdown (and ideally `review_notes.md`).
- AWS credentials available as `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`.
- Part 3 tests pass under `experiments/bertopic_original_mirror_part3_2026_09_24/tests/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/bertopic_modeling_2026_08_05/RESULTS.md` | Tone and table structure for production summary |
| `/workspace/experiments/generate_flips_2026_09_08/RESULTS.md` | S3 URI examples in this repo |
| `/workspace/lib/aws/s3.py` | `S3.upload_file`, `list_keys_ordered`, `object_exists` |
| `/workspace/AGENTS.md` | S3 bucket `mirrorview-experimental-artifacts`; prefix mirrors local folder |
| Production metadata under `outputs/topics/*/metadata.json` | Counts and hyperparameters |
| `outputs/ablations/summary.csv` | Ablation sensitivity table |
| `outputs/analyses/outcomes/*/metadata.json` | Q5 parameters |
| `outputs/analyses/part2_comparison/*/agreement_metrics.json` | Q1 ARI/NMI |
| `outputs/analyses/cross_role/*/metadata.json` | Q2 to Q4 metrics |

## Files allowed to change

- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/RESULTS.md` (overwrite stub with final report)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/upload_outputs.py` (new; optional thin wrapper around `lib.aws.s3.S3`)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_upload_outputs.py` (new; mock boto3)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/README.md` (S3 upload command block only)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/upload_manifest.json` (written by upload script)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md`
- `/workspace/experiments/bertopic_modeling_2026_08_05/**` (must remain unchanged)
- `/workspace/shared/**`
- `/workspace/pyproject.toml`
- Analysis logic in `src/analyze_*.py`, `src/run_ablations.py` (read-only unless upload bugfix)

## Implementation details

### RESULTS.md structure

Create `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/RESULTS.md` with these sections in order:

1. **Header:** date, status `Complete`, one-line corpus description (18,899 stimulus posts, original + mirror, deduped before fit).

2. **Setup table:** embedding model (`amazon.titan-embed-text-v2:0`, 256-d, L2-normalized), UMAP/HDBSCAN/vectorizer params (match production metadata), dedupe counts (173 duplicate originals, 35 identical pairs removed), LLM label model `gpt-5.4-nano`, fit corpus = all deduplicated stimuli, outcome analysis = rated posts with `n_raters >= 3`.

3. **Production counts table:**

| Role | n_docs fitted | n_topics (excl noise) | n_noise | noise_share |
|------|--------------:|----------------------:|--------:|------------:|
| original | | | | |
| mirror | | | | |
| joint | | | | |

4. **Topic labels table:** top 20 topics by size for original and joint (columns: `topic_id`, `n_docs`, `llm_label`); pointer to full `topic_labels.parquet` paths.

5. **Q1 Part 2 comparison:** carryover `n` (~8899), ARI, NMI, link to `outputs/analyses/part2_comparison/<TS>/`, note `part2_model_source` (local/refit/s3). Short interpretation: whether Part 3 shifts topic shares vs Part 2 on overlap.

6. **Q2 Mirror agreement:** pair topic agreement rate (original model assigns mirrors), link to cross-role run.

7. **Q3 Mirror signature:** joint-model role-dominated topics count, link to cross-role flags table.

8. **Q4 Vocabulary contrast:** pointer to within-topic c-TF-IDF CSV per cross-role run.

9. **Q5 Outcome overlays:** overall keep rate, table of topics with highest/lowest keep rate (original model, BH-significant flagged), party split summary, facet findings (only cells with `>=30` posts). State **descriptive only, not causal**. Pair-level decisions apply (no per-text keep/remove).

10. **Ablation sensitivity:** embed or link `outputs/ablations/summary.csv`; bullet per ablation whether Q5 ranking (Spearman) and Q2/Q3 (A4) are stable.

11. **Human review:** link to `outputs/reviews/<TS>/review_original.md`, `review_joint.md`, and `review_notes.md` if present.

12. **Limitations:** post-hoc topics; pair-level moderation labels; multiple ratings per post; Titan cache backfill for new posts; UMAP stochasticity (mitigated by A1); MiniLM ablation (A3).

13. **Artifact paths:** repo-relative paths to latest production runs (topics, labels, figures per role), analyses, ablations, reviews.

14. **S3 storage:**  
    `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/`  
    with upload timestamp and `upload_manifest.json` key count.

### Git vs S3 policy

Per AGENTS.md, err on S3 for larger files. Use `experiments/bertopic_original_mirror_part3_2026_09_24/.gitignore` from Step 2.

| Artifact | Git | S3 |
|----------|-----|-----|
| `src/`, `tests/`, `README.md`, `SETUP.md`, `RESULTS.md` | yes | optional copy |
| `outputs/dedupe_report.json` | yes | yes |
| `outputs/topics/*/metadata.json`, `topic_info.parquet`, `assignments.parquet` | yes | yes |
| `outputs/topics/*/model/` (safetensors) | **no** (gitignored) | **yes (required)** |
| `outputs/topics/*/umap_2d.npy` | **no** (gitignored) | **yes (required)** |
| `outputs/embeddings/**/index.parquet`, `metadata.json` | yes | yes |
| `outputs/embeddings/**/embeddings.npy` | **no** (gitignored; uploaded Step 3) | **yes (required)** |
| `outputs/embeddings_minilm/**/index.parquet`, `metadata.json` | yes | yes |
| `outputs/embeddings_minilm/**/embeddings.npy` | **no** (gitignored; uploaded Step 3) | **yes (required)** |
| `outputs/labels/**` (parquet, metadata) | yes | yes |
| `outputs/figures/**/*.html` | no | yes |
| `outputs/figures/**/*.png` | yes | yes |
| `outputs/analyses/**` (CSV, parquet, json, summary) | yes | yes |
| `outputs/ablations/summary.csv` | yes | yes |
| `outputs/ablations/**` (other ablation artifacts, including `model/`) | no (large dirs gitignored) | full tree |
| `outputs/reviews/**` (markdown, parquet) | yes | yes |
| `outputs/assignments/**` | yes | yes |

Committed parquet/json summaries and figure PNGs stay in git. Large embedding arrays, BERTopic model weights, and `umap_2d.npy` are S3-primary under `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/` with the same relative paths.

### Upload script: `upload_outputs.py`

- Walk `experiments/bertopic_original_mirror_part3_2026_09_24/outputs/` recursively. Skip gitignored large files already uploaded in Steps 3 and 4 unless `--force`.
- S3 bucket: `mirrorview-experimental-artifacts`.
- Key prefix: `experiments/bertopic_original_mirror_part3_2026_09_24/` + relative path from `outputs/` (per AGENTS.md: prefix equals local folder path under experiment).
- Skip files already on S3 with matching size (optional etag) unless `--force`.
- Write `outputs/upload_manifest.json`: `uploaded_at`, `bucket`, `prefix`, `n_files`, `total_bytes`, `keys` (sorted list).

Also upload Part 2 production model if local and not yet on S3 (enables Q1 on fresh clones):

`experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/model/`  
to  
`s3://mirrorview-experimental-artifacts/experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/model/`

Do not modify Part 2 git-tracked files; only upload ignored model weights.

## TDD tests first

### `experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_upload_outputs.py`

```python
# test_build_s3_key_prefix
# Given: local path outputs/topics/original/TS/assignments.parquet
# When: build_s3_key("experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original/TS/assignments.parquet")
# Then: key == "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original/TS/assignments.parquet"

# test_collect_files_excludes_nothing_by_default
# Given: tmp outputs/ with 2 files
# When: collect_output_files(tmp_outputs)
# Then: len == 2

# test_upload_manifest_counts
# Given: mock S3 client recording put_object calls
# When: upload_outputs(..., dry_run=False)
# Then: manifest n_files equals number of puts
```

No real AWS in tests; monkeypatch `boto3.client`.

## Exact commands

### 1. Run all Part 3 tests

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/bertopic_original_mirror_part3_2026_09_24/tests/ -q
```

Expected: all tests passed.

### 2. Confirm Part 2 unchanged

```bash
cd /workspace
git diff --stat -- experiments/bertopic_modeling_2026_08_05/
```

Expected: no output (empty diff). New refit run dirs under Part 2 `outputs/` are acceptable if only timestamp folders were added by Step 6 refit; **no changes to Part 2 `src/`**.

### 3. Upload outputs to S3

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/upload_outputs.py \
  --outputs-dir experiments/bertopic_original_mirror_part3_2026_09_24/outputs \
  --bucket mirrorview-experimental-artifacts \
  --prefix experiments/bertopic_original_mirror_part3_2026_09_24/
```

Optional Part 2 model upload:

```bash
PYTHONPATH=. uv run python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/upload_outputs.py \
  --outputs-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/model \
  --bucket mirrorview-experimental-artifacts \
  --prefix experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/model/
```

Expected stdout (example):

```text
upload_complete n_files=1247 total_bytes=...
manifest=experiments/bertopic_original_mirror_part3_2026_09_24/outputs/upload_manifest.json
s3_prefix=s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/
```

### 4. Verify S3 object count (AWS CLI)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 ls s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/ --recursive | wc -l
python -c "
import json
from lib.aws.s3 import S3
m=json.load(open('experiments/bertopic_original_mirror_part3_2026_09_24/outputs/upload_manifest.json'))
s3=S3('mirrorview-experimental-artifacts', region_name='us-east-2')
keys=s3.list_keys_ordered('experiments/bertopic_original_mirror_part3_2026_09_24/')
assert len(keys)==m['n_files'], (len(keys), m['n_files'])
print('S3 verify OK', len(keys), 'objects')
"
```

Expected: CLI line count equals `upload_manifest.json` `n_files` (within 0 if manifest lists only leaf objects; document if prefix includes directory markers).

### 5. Spot-check critical keys exist

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 ls s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/ablations/summary.csv
aws s3 ls s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original/ --recursive | grep model | head
aws s3 ls s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings/original/embeddings.npy
```

### 6. Write RESULTS.md (after upload so S3 section has real counts)

Populate RESULTS.md from latest metadata files. Grep check:

```bash
grep -E 'Q1|Q5|ablation|s3://mirrorview|n_raters >= 3|descriptive' \
  experiments/bertopic_original_mirror_part3_2026_09_24/RESULTS.md | head -20
```

## Pass/fail criteria

| Check | Pass | Fail |
|-------|------|------|
| RESULTS.md | All 14 sections present with numeric tables | Stub or missing Q1-Q5 |
| Limitations | States pair-level labels and non-causal Q5 | Implies causal claims |
| S3 upload | Manifest written; keys under correct prefix | Wrong bucket or prefix |
| S3 verify | `list_keys_ordered` count matches manifest | Silent upload failure |
| Model on S3 | Part 3 `model/` and `umap_2d.npy` uploaded; embedding `embeddings.npy` present from Step 3 | Large artifacts git-only |
| pytest | All Part 3 tests pass | Failures ignored |
| Part 2 src | `git diff experiments/bertopic_modeling_2026_08_05/src` empty | Part 2 code edited |
| Production integrity | No overwrites of production run dirs during Step 8 | RESULTS step reran fits |

## Commit messages

1. `test(part3-bertopic): add S3 upload manifest unit tests`
2. `feat(part3-bertopic): add outputs upload script for mirrorview S3 bucket`
3. `docs(part3-bertopic): write RESULTS.md with Q1-Q5 and ablation summary`
4. `chore(part3-bertopic): upload outputs and Part 2 model artifacts to S3`
