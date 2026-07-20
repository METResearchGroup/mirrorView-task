# Spec: Human-Readable LLM Error Analysis (2026-07-20)

**Experiment dir:** `experiments/human_readable_llm_error_analysis_2026_07_20/`  
**Builds on:** `experiments/followup_model_error_analysis_2026_07_15/` (V1 LLM feature corpus)  
**Status:** Spec only — do **not** implement or call APIs until accepted.

---

## Executive summary

**Question:** Can we turn the V1 extracted features into short, human-readable theme labels by (1) embedding each feature with Amazon Titan, (2) clustering in embedding space, (3) sampling *n* features per cluster, and (4) asking an LLM for a single ~5-word label that captures the cluster’s common theme?

**Why this now:** The 2026-07-15 follow-up produced 3,341 high-confidence feature rows (~3,099 unique `category:feature_name=feature_value` strings) and an LLM-over-corpus cluster writeup. That writeup is useful but expensive, hard to resume, and mixes interpretation with grouping. This experiment separates **geometric grouping** (Titan + clustering) from **label drafting** (cheap LLM calls on small exemplars), yielding stable, auditable theme names we can compare across confusion buckets (especially FP vs TN).

**Decision needed from you:** Approve this plan (and supply AWS/Bedrock credentials) before any embedding or labeling run.

---

## Environment readiness (checked 2026-07-20)

| Requirement | Status | Notes |
| --- | --- | --- |
| V1 feature CSVs on disk | **Ready** | `followup_.../outputs/llm_features/{fp,fn,tp,tn}/*.csv` |
| `OPENAI_API_KEY` | **Ready** | Present; sufficient for cluster-label LLM calls |
| Amazon Titan via Bedrock | **Blocked** | No `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / session token; no `~/.aws`; `boto3` reports **no credentials**. `SAGEMAKER_ROLE_ARN` alone cannot invoke Bedrock. |
| Reusable Titan cache for *features* | **None** | Existing Titan caches are **post-text** embeddings (`only_original`, etc.), not feature-string embeddings. Feature texts must be newly embedded. |

**Implication:** Spec and offline scaffolding can proceed; **Phase 1 (embed) cannot run in this environment** until AWS credentials with Bedrock `amazon.titan-embed-text-v2:0` access (region aligned with existing helpers, typically `us-east-1` for Titan helpers / `us-east-2` for other Bedrock work — lock one region in implementation) are injected.

---

## Proposed method (locked outline)

1. **Ingest** — Load V1 feature rows; canonicalize each row to an embeddable string  
   `category:feature_name=feature_value` (same convention as prior cluster “defining features”). Deduplicate exact strings; keep occurrence counts and per-bucket histograms.
2. **Embed** — Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`, **256-d**, `normalize=True`), reusing `create_embedding` from `experiments/simplified_predict_remove_2026_05_13/experiment_bedrock_embeddings.py`. Cache embeddings locally by content hash so runs are idempotent.
3. **Cluster** — Fit clustering in Titan space on the unique feature vectors (default: **k-means**; choose *k* via silhouette / elbow on a small grid, e.g. *k* ∈ {8, 12, 16, 24}). Persist cluster id per unique feature string.
4. **Sample** — For each cluster, draw a random set of **n** features (default **n=8**, seed fixed), stratified by occurrence weight if a cluster is huge; skip clusters below a min size threshold.
5. **Label** — One OpenAI call per cluster (primary model aligned with prior work: `gpt-5.5`):  
   *“Produce a single concise label (around 5 words) that captures the common theme of these features.”*  
   Structured output: `{label, rationale_one_sentence}`. No bulk re-reading of the full corpus.
6. **Report** — Table of `{cluster_id, label, size, n_sampled, bucket_mix, exemplar_features}` plus a short RESULTS.md comparing FP-enriched vs TN-enriched clusters.

**Out of scope (unless approved later):** V2 full-corpus feature extraction; re-embedding raw posts; re-running Qwen; replacing the prior LLM cluster essay wholesale.

---

## Contrast with prior clustering

| | 2026-07-15 Phase 3b | This experiment |
| --- | --- | --- |
| Grouping | LLM reads large feature shards | Titan geometry + k-means |
| Labels | Long multi-clause theme titles | ~5-word concise labels |
| Cost driver | Large context clustering (~$0.70 on V1 shard) | Titan embeds (~3k unique strings) + ~*k* short label calls |
| Auditability | Hard to reproduce grouping | Deterministic clusters given seed + *k* |

---

## Cost / risk sketch (order of magnitude)

- **Titan:** ~3,099 unique short strings → low Bedrock embedding spend (well under typical LLM clustering cost); exact $ TBD once credentials work and token counts are measured.
- **OpenAI labels:** ≈ *k* calls with tiny prompts (e.g. *k*=16 → ~16 calls) — expected **≪ $1** on `gpt-5.5`.
- **Main risk:** Feature strings are already semi-structured; Titan may over-cluster on shared `feature_name` prefixes rather than semantic `feature_value`. Mitigation: optional ablation that embeds `feature_value` only, or `feature_name + value` without category.

---

## Deliverables (when approved + AWS unblocked)

| Artifact | Path |
| --- | --- |
| This spec | `spec.md` (here) |
| Feature embedding cache | `outputs/embeddings/` |
| Cluster assignments | `outputs/clusters/assignments.csv` |
| Sampled exemplars + LLM labels | `outputs/clusters/labels.json` |
| Writeup | `RESULTS.md` |

---

## Acceptance gate

Approve this spec **and** provide working AWS credentials for Bedrock Titan before implementation. Until then, no embedding or labeling API calls.
