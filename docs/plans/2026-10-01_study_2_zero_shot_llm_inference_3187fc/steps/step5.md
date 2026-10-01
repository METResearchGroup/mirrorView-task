# Step 5: Write results and verify the experiment

Finish the experiment by reproducing the approved analysis from S3, writing the three documentation files, and checking the entire implementation. Step 5 changes documentation only, so it must not repair production code. Return each failure to the step that owns the failing file.

## Scope

- **Main caller:** `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py` command line entry point.
- **Task:** reproduce the Step 4 analysis artifact for one run, publish its `results_fragment.md` tables in `RESULTS.md`, document the required data in `SETUP.md`, add the short `README.md`, and run final checks.
- **Owned files:** `README.md`, `SETUP.md`, and `RESULTS.md` in `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/`.
- **Out of scope:** changing calculations, schemas, S3 keys, model definitions, inference behavior, dependency files, registered datasets, or generated artifacts.

## Files to inspect

Read these files before making changes:

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/plan.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step1.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step2.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step3.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step4.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/SETUP.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/RESULTS.md`

The last three files define the local experiment documentation pattern. They do not override this plan's artifact, heading, or table contracts.

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/SETUP.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/RESULTS.md`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/REPORT.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/**`
- `/Users/mark/src/work/mirrorview-wt/shared/**`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- Every path outside `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/`

Generated data, prediction batches, failure batches, manifests, and analysis tables remain in `s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/`. Do not add them to Git.

## Confirmed contracts

Do not begin the documentation pass until Steps 1 through 4 are complete and their public contracts are confirmed. Step 5 consumes those contracts and cannot change them.

### Analysis caller contract

The Step 4 analysis caller accepts one complete run ID, reads its prepared input and four model outputs from the experiment's S3 prefix, validates them before calculation, and writes these five artifacts below `s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/analysis/RUN_ID/`:

- `analysis_manifest.json`
- `label_counts.csv`
- `split_remove_vote_counts.csv`
- `model_metrics.csv`
- `results_fragment.md`

Repeating the caller against unchanged S3 inputs must produce byte-for-byte identical artifacts. Step 5 publishes `results_fragment.md` without editing its computed tables.

The caller must reject the run before writing `RESULTS.md` when any of these conditions holds:

- The prepared input does not contain exactly 13,992 unique post IDs.
- The unanimous subset does not contain exactly 4,051 posts.
- The split subset does not contain exactly 9,941 posts.
- The unanimous and split ID sets overlap or their union differs from the prepared input IDs.
- Any requested model lacks exactly one valid prediction for each prepared post ID.
- A stored failure remains unresolved.
- A count, proportion, or metric table fails its Step 4 invariant.

### `README.md` contract

`README.md` must contain only one title line and one redirect line. The redirect line must link to `SETUP.md` for data requirements and `RESULTS.md` for output tables. The file must not describe commands, implementation details, or environment setup.

### `SETUP.md` contract

`SETUP.md` must describe data requirements only. It must name:

- The prepared five-labeler Study 2 input manifest.
- The required completed run ID.
- The four required model folders: `amazon_nova_micro`, `qwen3_32b`, `openai_gpt_5_6_terra`, and `claude_sonnet_5_5`.
- The requirement for 13,992 unique valid predictions per model and no unresolved failures.
- The Step 4 analysis artifact below `s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/analysis/RUN_ID/`.
- The rule that generated artifacts stay in S3 and are not checked into Git.

Do not include dependency installation, Python setup, AWS authentication setup, shell profile changes, or editor instructions.

### `RESULTS.md` contract

Generate `RESULTS.md` from the Step 4 artifact. Do not copy values from terminal output or calculate values by hand. Include the run ID and S3 analysis location so another researcher can identify the source artifact.

The document must contain these sections in this order:

1. `# Zero-shot keep or remove inference for Study 2`
2. `## Run provenance`
3. `## Human label distribution`
4. `## Split remove-vote distribution`
5. `## Model metrics`
6. `### All five-labeler posts`
7. `### Unanimous posts`
8. `### Split posts`

The human label table must report keep and remove counts and proportions for all five-labeler, unanimous, and split datasets. Their counts must sum to 13,992, 4,051, and 9,941 respectively. Within each dataset, keep and remove proportions must sum to 1 within the six-decimal precision fixed by Step 4.

The split remove-vote table must contain rows for one, two, three, and four remove votes. Its post counts must sum to 9,941, and its proportions must sum to 1 within six-decimal precision.

Each of the three model metric tables must contain exactly one row for each requested model and the columns Model, N, F1, Accuracy, Recall, and Precision. Display all metrics to six decimals. Treat remove as the positive class. Every metric must be between zero and one. Preserve the stable model and dataset order defined in Step 4.

## Implementation sequence

### 1. Confirm the caller and artifact before editing prose

Read the Step 4 caller, renderer, and schemas. Record the completed run ID selected for publication. Confirm that the S3 run and analysis artifact satisfy the confirmed contracts. Stop if the run is incomplete or if reproducing it would require a source-code change.

### 2. Reproduce `RESULTS.md` from S3

Run the confirmed analysis command with the selected run ID. Download `results_fragment.md`, prepend only the fixed title and run record, and write `RESULTS.md`. Do not hand-edit computed tables. If any generated heading or table must change, make that change in the owning Step 4 renderer, rerun the Step 4 verification commands, and return to Step 4 review before continuing.

### 3. Write `SETUP.md`

Document the input manifest, complete model outputs, and analysis artifact required to reproduce the published result. Keep environment setup out of this file.

### 4. Write `README.md`

Add the title and the single redirect sentence only. Confirm the file has two nonblank lines.

### 5. Verify the task and the complete experiment

Run a second S3 reproduction, table and heading checks, repository content checks, and forbidden-file checks. A check failure blocks completion. Route the repair to the step that owns the failing file rather than expanding Step 5's edit scope.

### 6. Commit the documentation

Commit only the three owned Markdown files after every check passes. Use a separate commit from any Step 4 code or generated artifact changes.

## Commands and expected output

Run every command from `/Users/mark/src/work/mirrorview-wt` and prefix every Python command with `PYTHONPATH=.`. Replace `<approved-run-id>` with the single completed run ID recorded in `RESULTS.md`.

### Reproduce the analysis

```bash
export EXPERIMENT_RUN_ID=<approved-run-id>
export EXPERIMENT_ANALYSIS_URI="s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/analysis/$EXPERIMENT_RUN_ID"
export EXPERIMENT_ANALYSIS_CHECK_DIR="$(mktemp -d)"
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze \
  --run-id "$EXPERIMENT_RUN_ID"
aws s3 cp "$EXPERIMENT_ANALYSIS_URI/results_fragment.md" "$EXPERIMENT_ANALYSIS_CHECK_DIR/results_fragment.md"
PYTHONPATH=. uv run python - <<'PY'
import os
from pathlib import Path

run_id = os.environ["EXPERIMENT_RUN_ID"]
analysis_uri = os.environ["EXPERIMENT_ANALYSIS_URI"]
check_dir = Path(os.environ["EXPERIMENT_ANALYSIS_CHECK_DIR"])
fragment = (check_dir / "results_fragment.md").read_text(encoding="utf-8").lstrip()
results = (
    "# Zero-shot keep or remove inference for Study 2\n\n"
    "## Run provenance\n\n"
    f"- Run ID: `{run_id}`\n"
    f"- Analysis artifacts: `{analysis_uri}/`\n\n"
    f"{fragment}"
)
Path("experiments/zero_shot_llm_inference_2026_09_30/RESULTS.md").write_text(
    results,
    encoding="utf-8",
)
PY
```

Expected: all commands exit 0. The analysis command prints the analysis prefix plus `input_rows=13992`, `unanimous_rows=4051`, `split_rows=9941`, `models=4`, `metric_rows=12`, and `artifacts=5`. The copy command downloads `results_fragment.md` into the temporary check directory. The final command writes `RESULTS.md` from that fragment without invoking Bedrock or placing generated data in the repository.

### Prove deterministic rendering

```bash
cp "$EXPERIMENT_ANALYSIS_CHECK_DIR/results_fragment.md" "$EXPERIMENT_ANALYSIS_CHECK_DIR/results_fragment.before.md"
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze \
  --run-id "$EXPERIMENT_RUN_ID"
aws s3 cp "$EXPERIMENT_ANALYSIS_URI/results_fragment.md" "$EXPERIMENT_ANALYSIS_CHECK_DIR/results_fragment.after.md"
cmp "$EXPERIMENT_ANALYSIS_CHECK_DIR/results_fragment.before.md" "$EXPERIMENT_ANALYSIS_CHECK_DIR/results_fragment.after.md"
```

Expected: all commands exit 0 and `cmp` prints nothing. Run the publication commands again after this check and confirm the resulting `RESULTS.md` is unchanged.

### Verify required headings and documentation shape

```bash
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path

root = Path("experiments/zero_shot_llm_inference_2026_09_30")
readme_lines = [line for line in (root / "README.md").read_text().splitlines() if line]
assert len(readme_lines) == 2, readme_lines
assert readme_lines[0].startswith("# "), readme_lines[0]
assert "[SETUP.md](SETUP.md)" in readme_lines[1], readme_lines[1]
assert "[RESULTS.md](RESULTS.md)" in readme_lines[1], readme_lines[1]

setup = (root / "SETUP.md").read_text()
for required in (
    "13,992",
    "amazon_nova_micro",
    "qwen3_32b",
    "openai_gpt_5_6_terra",
    "claude_sonnet_5_5",
    "s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/",
):
    assert required in setup, required

results = (root / "RESULTS.md").read_text()
headings = [
    "# Zero-shot keep or remove inference for Study 2",
    "## Run provenance",
    "## Human label distribution",
    "## Split remove-vote distribution",
    "## Model metrics",
    "### All five-labeler posts",
    "### Unanimous posts",
    "### Split posts",
]
positions = [results.index(heading) for heading in headings]
assert positions == sorted(positions), positions
for required in ("13,992", "4,051", "9,941"):
    assert required in results, required
assert results.count("| Model | N | F1 | Accuracy | Recall | Precision |") == 3
print("documentation structure verified")
PY
```

Expected: exit code 0 and exactly `documentation structure verified` on stdout. The published S3 table checks below are the authority for numeric table sums, model row counts, stable ordering, metric bounds, and the remove-positive-class rule.

### Verify the published S3 tables

```bash
aws s3 cp "$EXPERIMENT_ANALYSIS_URI/" "$EXPERIMENT_ANALYSIS_CHECK_DIR/" \
  --recursive \
  --exclude '*' \
  --include 'label_counts.csv' \
  --include 'split_remove_vote_counts.csv' \
  --include 'model_metrics.csv'
PYTHONPATH=. uv run python - <<'PY'
import csv
import os
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

root = Path(os.environ["EXPERIMENT_ANALYSIS_CHECK_DIR"])

with (root / "label_counts.csv").open(newline="", encoding="utf-8") as stream:
    labels = list(csv.DictReader(stream))
assert list(labels[0]) == ["dataset", "label", "count", "dataset_total", "proportion"]
expected_labels = {
    ("all", "keep"): (11024, 13992),
    ("all", "remove"): (2968, 13992),
    ("unanimous", "keep"): (3743, 4051),
    ("unanimous", "remove"): (308, 4051),
    ("split", "keep"): (7281, 9941),
    ("split", "remove"): (2660, 9941),
}
assert [(row["dataset"], row["label"]) for row in labels] == list(expected_labels)
proportions = defaultdict(Decimal)
for row in labels:
    key = (row["dataset"], row["label"])
    assert (int(row["count"]), int(row["dataset_total"])) == expected_labels[key]
    proportions[row["dataset"]] += Decimal(row["proportion"])
assert all(abs(total - Decimal("1")) <= Decimal("0.000001") for total in proportions.values())

with (root / "split_remove_vote_counts.csv").open(newline="", encoding="utf-8") as stream:
    votes = list(csv.DictReader(stream))
assert list(votes[0]) == ["remove_votes", "count", "split_total", "proportion"]
assert [(int(row["remove_votes"]), int(row["count"])) for row in votes] == [
    (1, 4244),
    (2, 3037),
    (3, 1777),
    (4, 883),
]
assert all(int(row["split_total"]) == 9941 for row in votes)
assert sum(int(row["count"]) for row in votes) == 9941
assert abs(sum(Decimal(row["proportion"]) for row in votes) - Decimal("1")) <= Decimal("0.000001")

with (root / "model_metrics.csv").open(newline="", encoding="utf-8") as stream:
    metrics = list(csv.DictReader(stream))
assert list(metrics[0]) == [
    "dataset",
    "model",
    "sample_count",
    "true_positive",
    "false_positive",
    "true_negative",
    "false_negative",
    "f1",
    "accuracy",
    "recall",
    "precision",
]
datasets = ["all", "unanimous", "split"]
models = ["amazon_nova_micro", "qwen3_32b", "openai_gpt_5_6_terra", "claude_sonnet_5_5"]
sample_counts = {"all": 13992, "unanimous": 4051, "split": 9941}
assert [(row["dataset"], row["model"]) for row in metrics] == [
    (dataset, model) for dataset in datasets for model in models
]
for row in metrics:
    assert int(row["sample_count"]) == sample_counts[row["dataset"]]
    assert sum(int(row[key]) for key in ("true_positive", "false_positive", "true_negative", "false_negative")) == int(row["sample_count"])
    assert all(Decimal("0") <= Decimal(row[key]) <= Decimal("1") for key in ("f1", "accuracy", "recall", "precision"))
print("published analysis tables verified")
PY
```

Expected: the S3 copy downloads exactly the three named CSV files; the Python command exits 0 and prints `published analysis tables verified`. A wrong total, row order, schema, model count, sample count, confusion-matrix sum, proportion sum, or metric bound fails the command.

### Confirm the pull request contains only Python and Markdown files in the experiment

```bash
git diff --name-only --diff-filter=ACMRTUXB origin/main...HEAD -- experiments/zero_shot_llm_inference_2026_09_30 \
  | PYTHONPATH=. uv run python -c 'import pathlib, sys; paths=[pathlib.Path(line.strip()) for line in sys.stdin if line.strip()]; bad=[str(path) for path in paths if path.suffix not in {".py", ".md"}]; assert paths, "no experiment files in branch diff"; assert not bad, bad; print(f"verified {len(paths)} experiment files")'
```

Expected: exit code 0 and `verified N experiment files`, where `N` is the number of changed `.py` and `.md` files in the final branch. Any other suffix fails the command.

### Confirm the three documentation files are the only Step 5 changes

```bash
git diff --name-only HEAD^..HEAD -- experiments/zero_shot_llm_inference_2026_09_30 | sort
```

Expected, in lexicographic order after sorting: only `experiments/zero_shot_llm_inference_2026_09_30/README.md`, `experiments/zero_shot_llm_inference_2026_09_30/RESULTS.md`, and `experiments/zero_shot_llm_inference_2026_09_30/SETUP.md`.

### Confirm the protected untracked files are unchanged and untracked

```bash
shasum -a 256 experiments/zero_shot_llm_inference_2026_09_30/REPORT.md experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py
test -z "$(git ls-files -- experiments/zero_shot_llm_inference_2026_09_30/REPORT.md experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py)"
```

Expected hashes:

```text
23f143cb8f01f34404297f4a4a2f18572cf6cb30287368bd68bb72180b436473  experiments/zero_shot_llm_inference_2026_09_30/REPORT.md
8382df9f726d7402bbf6afa8ca32572fbee9e445c4786e1db3fe528e6e1d410a  experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py
```

Expected: both commands exit 0. The second command prints nothing, proving neither protected file is tracked.

### Confirm no generated data is tracked below the experiment directory

```bash
git ls-files experiments/zero_shot_llm_inference_2026_09_30 \
  | PYTHONPATH=. uv run python -c 'import pathlib, sys; paths=[pathlib.Path(line.strip()) for line in sys.stdin if line.strip()]; bad=[str(path) for path in paths if path.suffix not in {".py", ".md"}]; assert not bad, bad; print(f"verified {len(paths)} tracked experiment files")'
```

Expected: exit code 0 and `verified N tracked experiment files`. Any generated data file or other suffix fails the command.

## Pass

Step 5 passes only when all of the following are true:

- The S3 reproduction exits 0 without a Bedrock call and writes `RESULTS.md` from the approved Step 4 artifact.
- A second reproduction is byte-for-byte identical.
- `README.md` has exactly the required title and redirect lines.
- `SETUP.md` contains data requirements and no environment setup.
- `RESULTS.md` contains the run record section, the human-label and split remove-vote tables, and three model metric tables in the required order.
- The Step 4 numeric invariants pass for all totals, proportions, distributions, model rows, and metric bounds.
- The branch adds only `.py` and `.md` files below the experiment directory.
- The final Step 5 commit changes only `README.md`, `SETUP.md`, and `RESULTS.md`.
- `REPORT.md` and `probe_bedrock_models.py` retain their recorded hashes and remain untracked.
- No generated artifact is tracked in Git.

## Fail

Stop and do not mark the experiment complete if any of these conditions holds:

- The selected run is incomplete, has unresolved failures, or differs from the run recorded in `RESULTS.md`.
- Reproduction requires a Bedrock call, a manual calculation, or an edit to a generated table.
- Repeated rendering changes `RESULTS.md`.
- Any required total, proportion, distribution, model row, metric, or heading check fails.
- A direct verification command reveals that a prior step's contract changed.
- Step 5 changes a Python file, dependency file, shared file, data-platform file, or path outside its three owned Markdown files.
- The branch contains generated data or an experiment file whose suffix is not `.py` or `.md`.
- `REPORT.md` or `probe_bedrock_models.py` changes, becomes tracked, or no longer matches its recorded hash.

When a failure belongs to Steps 1 through 4, return it to that step with the failing command and output. Rerun all Step 5 checks after the owning step is fixed.
