# Step 5: Operationalize into a shared codebook

Step 5 merges per-arm cluster outputs from Step 4 (`outputs/<arm>/normalize/<embed_timestamp>/`) into one shared codebook at `outputs/shared/codebook/`. Each codebook entry gets a short name (2 to 5 words), a one-sentence definition, two positive and two negative examples as `{post_id, text}` objects, the arm or arms where it was discovered, and source cluster ids. Because example text is stored in the codebook, Step 6 does not need to re-join cohort text for examples. The default policy is no merge across arms or clusters, and you record any confirmed merges in `data/feature_synonyms.csv`. You drop pure topic-only features (for example, "post is about guns") and write each drop to the audit output. Labeling stays blocked until the user approves the draft codebook with `build_codebook --approve`.

## Scope

- **Caller / entrypoint:** `build_codebook` CLI (`if __name__ == "__main__"`).
- **In scope:** Load Step 4 outputs from `outputs/<arm>/normalize/<embed_timestamp>/features.jsonl`, `.../clusters_seed_<seed>/assignments_hdbscan.json` (default seed `42`), and cluster labels at `.../clusters_seed_<seed>/labels/<label_timestamp>/` for all three arms and cluster seeds `42`, `43`, and `44`. Pick primary HDBSCAN cluster labels per seed, dedupe within each arm by `cluster_id`, and export per-arm snapshots under `outputs/<arm>/operationalize/`. Build a draft shared codebook under `outputs/shared/codebook/`. Define codebook data models (`CodebookFeature`, `CodebookDraft`, `DroppedFeature`) in `build_codebook.py`. Apply topic-only drop rules. Support optional merges through committed `data/feature_synonyms.csv`. Add a human approval gate (Gate B). Write unit tests with mocked LLM and S3.
- **Out of scope:** Part 2 theme mapping (`map_part2_themes.py`, Step 7), post labeling (Step 6), editing `llm_client.py` or discovery/normalize modules, and automatic LLM merge at runtime. Merges are human-confirmed and recorded in CSV only.

## Files to inspect (read-only)

- `docs/plans/2026-09-24_llm_feature_generation_phase_2_part_3_2f71ad/plan.md`: Step 5 description, Q1 context, ablation axes.
- [HOW_TO_MINE_TEXT_FOR_FEATURES.md](https://github.com/METResearchGroup/lab_wiki/blob/main/docs/manuals/methods/HOW_TO_MINE_TEXT_FOR_FEATURES.md): conservative merge guidance and operationalize checklist (name, definition, examples).
- `experiments/llm_based_feature_generation_2026_07_31/RESULTS.md`: Part 2 lesson that policy-topic clusters (Themes 6, 11, 43, 130) predicted remove weakly compared to rhetorical form.
- `experiments/create_llm_features_2026_08_05/src/schemas.py`: `ClusterLabelResult`, `FeatureCategory` (use `topic_subject` for topic-only drop rule).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/paths.py`: arm/stage helpers (from Step 1).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/constants.py`: `TEXT_ARMS`, `CLUSTER_SEEDS`, `LLM_MODEL_ID`.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/llm_client.py`: all LLM calls for optional merge-support prompts (Step 3).
- `outputs/<arm>/normalize/<embed_timestamp>/features.jsonl`, `.../clusters_seed_<seed>/assignments_hdbscan.json`, and `.../clusters_seed_<seed>/labels/<label_timestamp>/` (from Step 4).
- `outputs/<arm>/cohort/<run_timestamp>/cohort.parquet`: post texts and `split` column for example selection.
- `data/post_split/discovery_post_ids.csv`: restrict positive/negative examples to discovery half.

## Files allowed to change

- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/build_codebook.py`: create (includes codebook data models: `CodebookFeature`, `CodebookDraft`, `DroppedFeature`).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_build_codebook.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/data/feature_synonyms.csv`: create header row only until merges confirmed.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/<arm>/operationalize/<run_timestamp>/`: per-arm pre-merge exports written by this step.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/shared/codebook/`: draft and approved codebook trees.

## Files forbidden to change

- `shared/` (read only).
- Other `experiments/*` (no cross-experiment imports).
- `docs/plans/.../plan.md` and sibling step files written by other writers.
- `src/llm_client.py`, `prompts.py`, `schemas.py`, `label_posts.py`, `map_part2_themes.py`, `analyze.py`, `write_results.py` (owned by other steps).
- `data/post_split/*` (Step 1).

## Implementation phases (TDD: mandatory order)

Complete phases in order, with one git commit per phase (or per unit of work in Phase 5). Do not skip phases.

| Phase | Goal | Gate |
|-------|------|------|
| 1: Scope | Name caller, file tree, out-of-scope | Caller + tree listed |
| 2: Scaffold | Create `build_codebook.py`; stub bodies only | Imports resolve; `raise NotImplementedError` |
| 3: Contracts | Types, signatures, schemas; no business logic | Matches this step; stubs only |
| 4: Test design | Pseudocode to failing tests (happy + key failures) | Tests fail for the right reason |
| 5: Implement | One function/path per commit until green | Targeted tests pass |
| 6: Done | Full step pytest + CLI smoke on fixture dirs | All step pass/fail criteria met |

### Phase 4: Named tests and assertions

Write these in `tests/test_build_codebook.py`. Mock `llm_client.complete_structured` and `s3_sync` so tests do not call live AWS or an LLM.

| Test name | Given | When | Assert |
|-----------|-------|------|--------|
| `test_load_arm_cluster_labels_reads_normalize_label_json` | Fixture dir with `normalize/<embed_ts>/clusters_seed_42/labels/<label_ts>/00000_<ts>.json` containing `cluster_label_row` | `load_arm_cluster_labels(arm, normalize_embed_dir, seed=42)` | Returns `ClusterLabelResult` fields: `cluster_id`, `cluster_label`, `definition` |
| `test_select_primary_seed_prefers_seed_42` | Three normalize dirs for seeds 42/43/44 | `select_primary_cluster_run(arm, normalize_embed_dir)` | Picks seed `42` label output when all exist |
| `test_build_entry_assigns_discovery_examples` | Cohort fixture with `split=discovery` posts | `build_codebook_entry(cluster, members, cohort)` | `positive_examples` and `negative_examples` each length 2; each element is `{post_id, text}`; every `post_id` in discovery set; every `text` matches cohort row |
| `test_topic_only_drop_flags_topic_subject_without_rhetoric` | Cluster whose members are all `category=topic_subject` and definition mentions only policy domain | `is_topic_only_feature(entry)` | Returns `True`; entry listed in `dropped_features.json` not `codebook.json` |
| `test_no_auto_merge_without_synonym_row` | Two similar entries from different arms | `merge_codebook_entries(draft, synonyms=empty)` | Output feature count equals input count (no silent merge) |
| `test_synonym_csv_merge_combines_source_cluster_ids` | `feature_synonyms.csv` row linking `cb_001` and `cb_002` with `merged_to=cb_001` | `apply_synonym_merges(draft, synonyms_path)` | One surviving feature; `source_cluster_ids` union of both; synonym row unchanged on disk |
| `test_write_draft_emits_timestamped_dir` | Stub inputs | `main(--write-draft)` | Creates `outputs/shared/codebook/draft_<run_timestamp>/codebook.json` where `<run_timestamp>` matches `%Y-%m-%dT%H-%M-%S` |
| `test_approve_writes_approval_json` | Existing draft path | `main(--approve draft_path)` | Writes `outputs/shared/codebook/approved_<run_timestamp>/approval.json` with `approved_by`, `approved_at`, `codebook_version` |
| `test_approve_copies_codebook_to_approved_dir` | Draft with 3 features | `main(--approve ...)` | `approved_<ts>/codebook.json` feature count equals draft |
| `test_name_word_count_enforced` | Cluster label `"This is a very long cluster name beyond five words"` | `normalize_feature_name(label)` | Raises `ValueError` or truncates to 2 to 5 words per contract |

### Phase 5: Implementation units (dependency order)

1. `load_arm_cluster_labels(arm, normalize_embed_dir, seed=42)`, `load_cluster_members` (join cluster labels under `clusters_seed_<seed>/labels/<label_timestamp>/` to `features.jsonl` via `assignments_hdbscan.json`).
2. `is_topic_only_feature` and `select_example_posts` (discovery half only; positive examples come from member posts with feature evidence; negative examples come from discovery posts without cluster membership).
3. `build_codebook_entry` (assign `feature_id` `cb_NNN`, `name`, `definition`, examples, `discovery_arm`, `source_cluster_ids`, `member_feature_ids`).
4. `apply_synonym_merges` (read `data/feature_synonyms.csv`; no LLM merge at runtime).
5. `write_draft_codebook` and CLI `--write-draft`.
6. `approve_codebook` and CLI `--approve`.
7. Optional: `suggest_merge_pairs` helper that prints candidate pairs for human side-by-side review when embedding similarity is above 0.85 on name+definition. It does not merge without a CSV row.

## Pass / fail criteria

### Must pass

- `PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_build_codebook.py -q` exits 0.
- Draft codebook JSON validates against schema in Artifact contract below.
- Every codebook feature has exactly 2 positive and 2 negative examples; all example `post_id` values are in `discovery_post_ids.csv`.
- `data/feature_synonyms.csv` exists with header: `feature_id_a,feature_id_b,merged_to,confirmed_by,confirmed_at,notes`.
- Topic-only drops recorded in `outputs/shared/codebook/draft_<run_timestamp>/dropped_features.json`.
- After `--approve`, `outputs/shared/codebook/approved_<run_timestamp>/approval.json` exists.
- All run directories created by this step use timestamp format `%Y-%m-%dT%H-%M-%S` (orchestrator override; not the runner colon format).
- Any LLM call uses `llm_client` only (model `openai/gpt-6-luna`, `reasoning_effort="none"`).

### Must fail (until implemented)

- `build_codebook --write-draft` with missing Step 4 normalize embed or cluster label dirs exits non-zero.
- `build_codebook --approve` on nonexistent draft path exits non-zero.
- `test_no_auto_merge_without_synonym_row` fails if code auto-merges without CSV.

## Commands (exact)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

# Build draft codebook from latest Step 4 outputs (seeds 42, 43, 44)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.build_codebook \
  --seeds 42 43 44 \
  --write-draft

# Optional: print candidate merge pairs for human side-by-side review (no writes)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.build_codebook \
  --seeds 42 43 44 \
  --suggest-merges

# After human review: record confirmed merges in data/feature_synonyms.csv, then rebuild draft
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.build_codebook \
  --seeds 42 43 44 \
  --write-draft

# STOP: human gate (Gate B). Labeling blocked until approval.

# User approves draft (writes approval marker)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.build_codebook \
  --approve outputs/shared/codebook/draft_<run_timestamp>/codebook.json \
  --approved-by "<reviewer_name>"

# Upload codebook artifacts
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.s3_sync \
  --paths outputs/shared/codebook data/feature_synonyms.csv

# Tests
PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_build_codebook.py -q
```

### Expected output (representative lines)

```
arm=original_only seed=42 clusters=...
arm=mirror_only seed=42 clusters=...
arm=paired seed=42 clusters=...
topic_only_dropped=...
draft_features=...
arms_merged=3
Wrote outputs/shared/codebook/draft_2026-09-24T12-34-56/codebook.json
Wrote outputs/shared/codebook/draft_2026-09-24T12-34-56/dropped_features.json
# After --approve:
Wrote outputs/shared/codebook/approved_2026-09-24T12-40-00/codebook.json
Wrote outputs/shared/codebook/approved_2026-09-24T12-40-00/approval.json
```

## Artifact contract (this step's outputs)

### Per-arm pre-merge export (`outputs/<arm>/operationalize/<run_timestamp>/`)

| File | Content |
|------|---------|
| `clusters.jsonl` | One row per HDBSCAN cluster (seed 42 primary): `cluster_id`, `name`, `definition`, `n_members`, `member_feature_ids`, `seed` |
| `metadata.json` | `arm`, `normalize_embed_dir`, `label_timestamp_dir`, `seed`, `built_at` (`%Y-%m-%dT%H-%M-%S`) |

### Draft / approved codebook (`outputs/shared/codebook/draft_<run_timestamp>/codebook.json`)

```json
{
  "version": "2026-09-24T12-34-56",
  "features": [
    {
      "feature_id": "cb_001",
      "name": "profanity insults",
      "definition": "Post uses explicit profanity or taboo insults directed at a person or group.",
      "positive_examples": [
        {"post_id": "reddit_abc", "text": "..."},
        {"post_id": "twitter_xyz", "text": "..."}
      ],
      "negative_examples": [
        {"post_id": "reddit_def", "text": "..."},
        {"post_id": "bluesky_ghi", "text": "..."}
      ],
      "discovery_arm": "original_only",
      "source_cluster_ids": {"original_only": [1], "mirror_only": [], "paired": []},
      "member_feature_ids": ["feat_..."],
      "part2_theme_id": null
    }
  ]
}
```

**Example shape:** `positive_examples` and `negative_examples` are lists of `{post_id, text}` objects by design. The build step writes example text into the codebook so Step 6 does not need to re-join cohort text for examples.

**Topic-only drop rule:** Drop a feature when (a) all member features have `category == "topic_subject"` and no member has a non-topic category, or (b) the cluster `definition` matches a regex for pure policy-domain description with no rhetorical or moderation cue. The seed list in code includes `guns`, `immigration`, `abortion`, `climate`, and `election` as sole subject without tone or argument framing. Log each drop in `dropped_features.json`:

```json
{
  "dropped": [
    {
      "cluster_id": 6,
      "arm": "paired",
      "reason": "topic_only",
      "cluster_label": "Policy domain guns debate",
      "member_feature_ids": ["..."]
    }
  ]
}
```

### `data/feature_synonyms.csv`

| Column | Type |
|--------|------|
| `feature_id_a` | str |
| `feature_id_b` | str |
| `merged_to` | str |
| `confirmed_by` | str |
| `confirmed_at` | str (`%Y-%m-%dT%H-%M-%S`) |
| `notes` | str |

### Approval marker (`outputs/shared/codebook/approved_<run_timestamp>/approval.json`)

```json
{
  "approved_by": "reviewer_name",
  "approved_at": "2026-09-24T12-40-00",
  "codebook_version": "2026-09-24T12-34-56"
}
```

## Human gates (if any)

**Gate B (required before Step 6):**

1. Present `outputs/shared/codebook/draft_<run_timestamp>/codebook.json` and `dropped_features.json` for review.
2. For any proposed merge, show side-by-side positive and negative example texts for both features. After a human confirms the merge, add a row to `data/feature_synonyms.csv` and rebuild the draft.
3. The user runs `build_codebook --approve <draft_path>`, which writes `approved_<run_timestamp>/approval.json`.
4. `label_posts` (Step 6) MUST error if no `outputs/shared/codebook/approved_*/approval.json` exists.

## Commit message template

`step5: operationalize shared codebook with approval gate`

## Handoff to Step 6

- Approved codebook path: `outputs/shared/codebook/approved_<run_timestamp>/codebook.json`
- Approval marker: `outputs/shared/codebook/approved_<run_timestamp>/approval.json`
- `data/feature_synonyms.csv` committed (header plus any merge rows)
- Step 6 reads the approved codebook only and routes all labeling calls through `llm_client`.
