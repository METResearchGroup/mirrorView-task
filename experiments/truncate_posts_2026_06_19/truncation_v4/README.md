# Truncation v4: topic-aligned mirror regeneration

## What this is

v4 is a **prompt intervention** on the manual-review sample from v3, not a new truncation algorithm. It asks whether mirrors stay on the same political issue when we explicitly instruct the model to flip stance without changing subject.

## Approach

1. **Input:** `outputs/truncation_v3/sample_flips.csv` — the 125-row review sample from `show_examples.py` (seed 42).
2. **Baseline column (`original_flip`):** copied from `outputs/truncation_v3/sample_new_flips_with_original_flips.csv` where available; otherwise generated with the original `FLIP_PROMPT` (no topic constraint) on `original_text`.
3. **Intervention (`new_flip`):**
   - Regenerate a mirror from `original_text` using `FLIP_PROMPT` plus:
     > Keep the mirror on the same political topic/issue as the original and flip only the stance, not the subject — switch to a different issue only when the original's topic has no natural opposite-stance position.
   - Truncate the generated mirror with **v3 sentence-first truncation** (`max_chars=300`, `sentence_overflow=20`), same as `truncation_v3.py`.
4. **Output:** `outputs/truncation_v4/sample_new_flips_with_original_flips.csv`

Generation uses the same Bedrock Sonnet setup and batch/resume behavior as `regenerate_sample_flips.py`.

## How this differs from other interventions

| Version | What changes | `original_flip` | `new_flip` |
|---|---|---|---|
| **v1–v3** | Truncation algorithm on pre-generated mirrors | — | — |
| **v3 sample (`regenerate_sample_flips.py`)** | Regenerate with original prompt; compare to v2 truncated mirrors | Fresh generation (original prompt) | v2 truncated mirror from `sample_flips.csv` |
| **v4 (this folder)** | Add topic-alignment instruction to prompt | Same as v3 sample (original prompt) | Fresh generation (topic-aligned prompt), v3-truncated |

So v4 isolates **prompt wording** (topic vs stance) while holding truncation fixed at v3. Comparing `original_flip` vs `new_flip` in the v4 output shows whether the new instruction reduces off-topic pivots (e.g. same-sex parenting → homeschooling) without changing the baseline generation.

## Run

From repo root:

```bash
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncation_v4/generate_sample_flips.py
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncation_v4/generate_sample_flips.py --force
```

The script resumes if interrupted: rows already present in the output CSV are skipped. Use `--force` to delete the output and regenerate all 125 rows.

## Output location

```
outputs/truncation_v4/sample_new_flips_with_original_flips.csv
```

Columns: `post_primary_key`, `original_text`, `sample_toxicity_type`, `sampled_stance`, `original_flip`, `new_flip`.
