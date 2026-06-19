# Truncating posts

We've been doing experiments in `match_lengths_original_mirrors_2026_06_19/` to try to get the original and LLM-generated outputs to be approximately the same length. A simpler approach is to truncate both sides before export.

This experiment applies truncation to
`experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv`.

## Output layout

Each truncation version writes artifacts under `outputs/`:

```
outputs/truncation_v1/flips.csv
outputs/truncation_v1/flips_with_flag.csv
outputs/truncation_v1/differentials.png
outputs/truncation_v1/highest_absolute_differential.csv

outputs/truncation_v2/flips.csv
outputs/truncation_v2/flips_with_flag.csv
outputs/truncation_v2/differentials.png
outputs/truncation_v2/highest_absolute_differential.csv
```

Path helpers live in `paths.py`. Analysis scripts accept `--version v1` or `--version v2`.

## v1: last-period truncation (`truncate_flips.py`)

**Strategy:** truncate each side independently to 300 chars, cutting at the last `.` within the window (fallback: hard cut).

### Problem

Manual review of `highest_absolute_differential.csv` showed v1 fails badly when:

- A period appears early (`"Justified. How is this even..."` → `"Justified."`)
- Ellipses or double periods appear in openers (`"Welcome to America..."`, `"Right.."`)
- Decimals / version numbers appear (`"Reconstruction 2.0"` → `"Demolition 2."`)
- The mirror mimics the original's punctuation style and gets cut at the same bad boundary

The no-period fallback (hard cut at 300 chars) is less catastrophic than these early-period cuts.

### v1 usage

```bash
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncate_flips.py
```

Outputs: `outputs/truncation_v1/flips.csv`, `outputs/truncation_v1/flips_with_flag.csv`

### v1 results (10,000 posts)

**Rows truncated:** 5,682 (56.8%)

| Metric | Before | After |
|---|---|---|
| Avg original length | 247.5 chars | 188.7 chars |
| Avg mirrored length | 327.0 chars | 204.9 chars |
| ≥10% length diff | 8,686 (86.9%) | 7,563 (75.6%) |

Truncated-only ≥10% length diff: 4,052 / 5,682 (71.3%)

---

## v2: boundary cascade + min-keep + pair-aware mirror (`truncate_flips_v2.py`)

**Strategy:**

1. **Boundary cascade** on the original — prefer, in order: paragraph break (`\n\n`), line break (`\n`), sentence end (`.!?` with false-positive filtering), clause end (`;:`), word boundary.
2. **Min-keep rule** — reject any boundary that would discard more than 25% of the char window (`min_keep_ratio=0.75`). Filters early periods, ellipses, and decimals.
3. **Pair-aware mirror truncation** — after truncating the original, truncate the mirror to the **same char length** as the truncated original (using the same boundary logic).

Implementation: `truncation_v2.py` (core logic), `truncate_flips_v2.py` (CLI + metrics).

### v2 usage

```bash
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncate_flips_v2.py
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncate_flips_v2.py -o out.csv --include-truncated-flag
```

Outputs: `outputs/truncation_v2/flips.csv`, `outputs/truncation_v2/flips_with_flag.csv`

### v2 results (10,000 posts)

**Rows truncated:** 9,716 (97.2%)

| Metric | Before | After (v2) |
|---|---|---|
| Avg original length | 247.5 chars | 197.7 chars |
| Avg mirrored length | 327.0 chars | 193.2 chars |
| ≥10% length diff | 8,686 (86.9%) | **399 (4.0%)** |
| Exact char-length matches | — | 137 (1.4%) |
| Catastrophic truncations (<30% of cap) | — | original=0, mirrored=62 |

### Truncated posts only (`is_truncated=True`, 9,716)

| Metric | Before | After (v2) |
|---|---|---|
| Avg original length | 250.5 chars | 199.2 chars |
| Avg mirrored length | 332.5 chars | 194.8 chars |
| ≥10% length diff | 8,647 (89.0%) | **360 (3.7%)** |

### All posts by political lean (`sampled_stance`)

| | Left (6,550) | Right (3,450) |
|---|---|---|
| **After avg original / mirrored** | 199.7 / 195.2 | 193.9 / 189.4 |
| **≥10% length diff (after v2)** | 250 (3.8%) | 149 (4.3%) |

### Truncated posts only by political lean

| | Left (6,332) | Right (3,384) |
|---|---|---|
| **After avg original / mirrored** | 201.8 / 197.5 | 194.3 / 189.9 |
| **≥10% length diff (after v2)** | 214 (3.4%) | 146 (4.3%) |

### v1 vs v2 summary

| Metric | v1 (last period) | v2 (cascade + pair-aware) |
|---|---|---|
| ≥10% length diff (all posts) | 75.6% | **4.0%** |
| Avg \|orig − mirr\| after | ~16 chars | ~4 chars |
| Catastrophic mirror truncations | many (e.g. 292-char gaps) | 62 |

v2 fixes the worst absolute-differential cases from v1 (e.g. `"Right.."` → 7-char mirror is now ~296 chars with ~3-char gap). **Recommend v2 for export** — use `outputs/truncation_v2/flips.csv`.

### Differential histogram & tail review

```bash
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/visualize_differentials.py --version v2
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/highest_absolute_differentials_posts.py --version v2
```

| | v1 | v2 |
|---|---|---|
| Mean differential (mirrored − original) | +16.2 chars | **−4.5 chars** |
| Top-20 abs diff range | 292 – 245 | **271 – 35** |

**v2 histogram:** tightly centered near zero; mean slightly negative because pair-aware truncation caps mirror length to the truncated original length, and mirrors are often slightly shorter at that cap.

**v2 remaining tail (top abs diffs):** no longer truncation artifacts. The worst rows are **LLM under-generation** — e.g. original kept at ~298 chars while the mirror is naturally short (`"Canada's Green Straitjacket"`, 27 chars). Truncation cannot lengthen a short mirror; these are generation-length mismatches, not bad cut points.

## Other scripts

```bash
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/visualize_differentials.py --version v1
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/highest_absolute_differentials_posts.py --version v1 --top-n 20
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/validate_truncated_flips.py --version v2
```
