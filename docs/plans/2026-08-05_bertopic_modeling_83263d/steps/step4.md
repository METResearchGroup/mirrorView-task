# Step 4: Implement post-hoc LLM topic labeling

## Goal

Implement `experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py` to label topics **after** fit via `topic_model.update_topics(..., representation_model=...)` using `bertopic.representation.OpenAI` with model `gpt-5.4-nano`. Skip HDBSCAN noise topic `-1`. Write artifacts under `outputs/labels/original/<UTC_TS>/` with a pointer to the source topics run. Do **not** re-run UMAP/HDBSCAN.

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py \
  --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>
```

Requires `OPENAI_API_KEY` via repo-root `.env` (`lib/load_env_vars.py`).

**In scope:** Stage-3 labeling only.

**Out of scope:** re-fitting BERTopic, visualization, Bedrock, mirror, `RESULTS.md`, any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` | OpenAI representation kwargs + prompt template |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py` | How model was saved; how to reload docs/embeddings alignment |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/paths.py` | `labels_dir` |
| `/workspace/lib/load_env_vars.py` | `OPENAI_API_KEY` loading pattern |
| BERTopic LLM representation docs | `update_topics` + `OpenAI` parser expecting `topic: <label>` |

## Files allowed to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py`
- `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` (Stage-3 CLI)
- Runtime artifacts under `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/labels/original/`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/pyproject.toml`
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py` (do not fold LLM into fit)
- `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/topics/**` (read-only; do not overwrite fit artifacts)
- Do **not** create `experiments/bertopic_modeling_2026_08_05/tests/`

## Contracts

### Representation model (exact)

```python
from bertopic.representation import OpenAI
import openai

client = openai.OpenAI()  # OPENAI_API_KEY from env / .env
representation_model = OpenAI(
    client,
    model="gpt-5.4-nano",
    chat=True,
    nr_docs=4,
    diversity=0.1,
    doc_length=150,
    tokenizer="whitespace",
    prompt="""I have a topic that contains the following documents:
[DOCUMENTS]
The topic is described by the following keywords: [KEYWORDS]

Based on the information above, extract a short topic label in the following format:
topic: <topic label>
""",
)
```

Model id must be exactly `gpt-5.4-nano` (same id as `experiments/create_llm_features_2026_08_05` / July-31 feature gen).

### Update path

1. Resolve `--topics-run-dir` (required, or default to latest under `topics_dir("original")` if documented).
2. Load saved BERTopic model from `{topics_run}/model/`.
3. Rebuild `docs` in the **same message_id order** as that topics run’s `assignments.parquet` (reload `original_text` from dataset by id; reload embeddings only if `update_topics` requires them — prefer docs-only update path).
4. Call `topic_model.update_topics(docs, representation_model=representation_model)` (or the BERTopic version-appropriate signature that updates representations without reclustering).
5. **Skip topic `-1`:** do not spend an LLM call on noise; write `llm_label` as null / `"noise"` / omit — pick one and record as `noise_label_policy` in metadata. Preferred: `llm_label=null` for topic `-1`, zero OpenAI calls for noise.
6. Do not change `assignments.parquet` topic ids.

### Output layout

`experiments/bertopic_modeling_2026_08_05/outputs/labels/original/<UTC_TS>/`

| File | Content |
|------|---------|
| `metadata.json` | `model="gpt-5.4-nano"`, prompt text (or hash + path), `source_topics_run` (absolute or repo-relative path), `nr_docs`, `diversity`, `doc_length`, `tokenizer`, `noise_label_policy`, `n_topics_labeled`, `unanimous_rule_id` unused/null |
| `topic_labels.parquet` | `topic_id`, `ctfidf_name`, `llm_label`, `n_docs` |
| `prompts.jsonl` | optional audit: one JSON object per labeled topic with prompt/response |

### Prompt freeze

The prompt string above is the source of truth from `experiments/bertopic_modeling_2026_08_05/README.md`. Keep the trailing `topic: <topic label>` line so BERTopic’s OpenAI parser extracts the label. Do not invent a second prompt without updating the README in the same change.

## Exact commands

### Offline wiring

```bash
cd /workspace

PYTHONPATH=. uv run --extra bertopic python -c "
from experiments.bertopic_modeling_2026_08_05.src import label_topics_llm as m
assert getattr(m, 'DEFAULT_MODEL', 'gpt-5.4-nano') == 'gpt-5.4-nano'
src = open('experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py').read()
assert 'gpt-5.4-nano' in src
assert 'topic: <topic label>' in src or 'topic: <topic label>' in open('experiments/bertopic_modeling_2026_08_05/README.md').read()
print('label_topics_llm wiring OK')
"
```

### Live smoke label (requires OPENAI_API_KEY + Step-3 topics run)

```bash
cd /workspace

# Replace UTC_TS with the smoke topics run from Step 3 / Step 6
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py \
  --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/UTC_TS
```

Expect `outputs/labels/original/<NEW_TS>/` with `metadata.json` pointing at the source topics run and `topic_labels.parquet` containing non-null `llm_label` for every `topic_id != -1` that has documents.

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Model | exactly `gpt-5.4-nano` | Other model id |
| Post-hoc | uses `update_topics`; does not call `fit_transform` | Reclusters |
| Noise | topic `-1` not LLM-labeled | OpenAI called for −1 |
| Pointer | `source_topics_run` set | Orphan labels |
| Fit untouched | `git status` shows no mods under existing topics run files that were already committed (new labels dir only) | Overwrote topic_info in topics run |
| Prompt | contains `[DOCUMENTS]`, `[KEYWORDS]`, `topic: <topic label>` | Custom prompt without parser trailer |

## Done when

- Stage 3 labels non-noise topics via `bertopic.representation.OpenAI` / `gpt-5.4-nano`.
- Artifacts land under `outputs/labels/original/<UTC_TS>/` with source topics pointer.
- Offline wiring passes; live smoke succeeds when credentials and a topics run exist.
- README documents Stage-3 CLI.
