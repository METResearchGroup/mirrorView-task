# Step 7: Count the top features per group and publish the Vercel page

Step 7 answers the three questions in the plan with counts from the step 6 label table. It draws two charts and writes one static page that Vercel serves at `/study-2-features`. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step7_analyze_post_features/run.py`. Step 7 calls no model.

Out of scope are statistical tests, p-values, confidence intervals, feature shares of all 20,000 pairs, rater party, new labels, new features, and any page other than `/study-2-features`.

## Decisions

Every analysis is one count. For each group of pairs, count the pairs in the group where each feature is 1, and keep the 10 features with the highest counts. Break ties by `feature_key` in alphabetical order. A table row holds the group, the rank, the feature name, the category, and the count, and each table header gives the number of pairs in the group. Counts in different groups are not compared with each other, because the groups differ in size.

The three analyses group the pairs this way:

1. By lean, from `sampled_stance` in `STUDY_2_STIMULI`, joined on `post_id`. On 2026-09-29 there are 11,550 left pairs and 8,450 right pairs.
2. By toxicity, from `sample_toxicity_type` in `STUDY_2_STIMULI`. There are 5,000 low, 10,000 medium, and 5,000 high pairs, where medium is `sample_middle_toxicity`.
3. By remove votes, from `n_remove` in the step 1 cohort, which holds only the 15,113 pairs with exactly five labels. On 2026-09-29 the groups have 3,986 pairs with 0 removes, 4,592 with 1, 3,332 with 2, 1,929 with 3, 950 with 4, and 324 with 5.

The charts follow the evident-charts skill at `https://github.com/rhiever/evident-charts/blob/main/skills/evident-charts/SKILL.md`. Read that `SKILL.md` before writing any chart. Clone the repository once with `git clone --depth 1 https://github.com/rhiever/evident-charts.git /tmp/evident-charts`, and import `evident` from `/tmp/evident-charts/skills/evident-charts/scripts`. The clone is not committed. Each chart is its own script, because `check_chart.py` runs a chart script and inspects the figures it makes. Both charts use the `blog` preset. Each has a title that names the grouping, a subtitle that says the bars count pairs and gives each group's pair count, and a source line that reads "Source: MirrorView Study 2, Jev labels at a 0.7 cutoff". The two charts are these:

- The lean chart has two panels side by side, left and right. Each panel has horizontal bars for its top 10 features, labeled with the feature name and the count.
- The toxicity chart has three panels, low, medium, and high, drawn the same way.

The remove votes analysis has six groups, so it is a table only, as the issue asks.

Each chart script writes an SVG. `render.py` puts the SVG text inside the page, so the page is one self-contained HTML file.

The page template is three files in `src/step7_analyze_post_features/webapp/`, which the issue allows: `index.html`, `styles.css`, and `app.js`. `index.html` has the placeholders `{{STYLES}}`, `{{SCRIPT}}`, `{{CHARTS}}`, and `{{DATA_JSON}}`. `render.py` fills them in and writes `/workspace/public/study-2-features.html`. The page has one section per question. The lean and toxicity sections each show the chart and the top 10 tables. The remove votes section shows six top 10 tables. The page ends with a table of every approved feature, showing the name, the category, and the definition. `app.js` reads the embedded JSON and lets you filter the feature table by category and search it by text. The page loads no outside script, font, or file.

Vercel serves `public/` because `vercel.json` sets `"outputDirectory": "public"`. Add rewrites from `/study-2-features` and `/study-2-features/` to `/study-2-features.html`, following the existing `/study-progress` rewrites. Add `!public/study-2-features.html` to `.vercelignore`, next to `!public/study-progress.html`.

The three analysis tables go to `outputs/analyses/` and to the `analyses/` key under the S3 prefix, as the issue asks. The SVGs and a copy of the page also go to S3 under `step7_analyze_post_features/`.

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `/tmp/evident-charts/skills/evident-charts/SKILL.md` | Chart rules and the check workflow |
| `/tmp/evident-charts/skills/evident-charts/scripts/evident.py` | `figure`, `titles`, `value_labels`, `save` |
| `/workspace/experiments/study_progress_dashboard_2026_09_11/render.py` | An earlier static page renderer in this repository |
| `/workspace/vercel.json` and `/workspace/.vercelignore` | The existing `/study-progress` route and allow lines |
| `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/constants.py` | `LABEL_TO_DETAIL`, `COHORT_KEY`, `POST_FEATURE_LABELS_KEY` |

## Files allowed to change

Paths under `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/`:

- Edit `shared/constants.py` to add the constants in the Contracts section
- Create `src/step7_analyze_post_features/__init__.py`, `analyses.py`, `render.py`, and `run.py`
- Create `src/step7_analyze_post_features/charts/__init__.py`, `common.py`, `lean_chart.py`, and `toxicity_chart.py`
- Create `src/step7_analyze_post_features/webapp/index.html`, `styles.css`, and `app.js`
- Edit `SETUP.md` to add the step 7 commands, and edit `RESULTS.md` under `## Step 7: analyses`

Paths elsewhere:

- Create `/workspace/public/study-2-features.html`, only through `render.py`
- Edit `/workspace/vercel.json` to add the two rewrites
- Edit `/workspace/.vercelignore` to add one allow line
- Edit `/workspace/CHANGELOG.md` to add one entry under the date the page ships
- Create `/workspace/docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/images/before/study-2-features.png` and `images/after/study-2-features.png`

## Files forbidden to change

- `/workspace/public/index.html` and `/workspace/public/study-progress.html`
- `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/label_to_detail.py`
- Everything under `src/step1_setup/` to `src/step6_label_posts_with_features/`
- `/workspace/shared/**` and `/workspace/webapp/**`

## Contracts

Add to `shared/constants.py`:

```text
STANCE_LEVELS = ("left", "right")
TOXICITY_LEVELS = {"sample_low_toxicity": "low", "sample_middle_toxicity": "medium",
                   "sample_high_toxicity": "high"}
REMOVE_VOTE_LEVELS = (0, 1, 2, 3, 4, 5)
EXPECTED_STANCE_COUNTS = {"left": 11550, "right": 8450}
EXPECTED_TOXICITY_COUNTS = {"low": 5000, "medium": 10000, "high": 5000}
EXPECTED_REMOVE_VOTE_COUNTS = {0: 3986, 1: 4592, 2: 3332, 3: 1929, 4: 950, 5: 324}
TOP_FEATURES_PER_GROUP = 10
EVIDENT_CHARTS_SCRIPTS_DIR = Path("/tmp/evident-charts/skills/evident-charts/scripts")
CHART_PRESET = "blog"
CHART_SOURCE = "Source: MirrorView Study 2, Jev labels at a 0.7 cutoff"
ANALYSES_PREFIX = "analyses/"
TOP_BY_LEAN_KEY = "analyses/top_features_by_lean.csv"
TOP_BY_TOXICITY_KEY = "analyses/top_features_by_toxicity.csv"
TOP_BY_REMOVE_VOTES_KEY = "analyses/top_features_by_remove_votes.csv"
PAGE_PATH = REPO_ROOT / "public" / "study-2-features.html"
PAGE_KEY = "step7_analyze_post_features/study-2-features.html"
```

`src/step7_analyze_post_features/analyses.py`:

```text
top_features_by_group(labels: pd.DataFrame, groups: pd.Series, details: dict[str, dict[str, str]],
                      top_n: int) -> pd.DataFrame
  groups is indexed by post_id. Columns group, n_group_pairs, rank, feature_key, name,
  category, n_pairs. Sort by n_pairs descending, then feature_key ascending, within each group.
  Raise ValueError when a post_id in groups has no row in labels.

check_group_counts(groups: pd.Series, expected: dict) -> None
  Raise ValueError when the pair count of any group differs from expected.
```

`run.py` calls `top_features_by_group` three times: with `sampled_stance`, with `sample_toxicity_type` mapped through `TOXICITY_LEVELS`, and with `n_remove` from the step 1 cohort. It calls `check_group_counts` before each call.

Each chart script has `main()`, loads its CSV from `outputs/analyses/`, and writes its SVG to `outputs/step7_analyze_post_features/figures/`. `charts/common.py` has `load_evident()`, which adds `EVIDENT_CHARTS_SCRIPTS_DIR` to `sys.path`, imports `evident`, and raises `FileNotFoundError` with the clone command when the folder is missing.

`src/step7_analyze_post_features/render.py`:

```text
build_page_data(by_lean, by_toxicity, by_remove_votes, details) -> dict
render_page(template: str, styles: str, script: str, charts: dict[str, str], data: dict) -> str
  Raise ValueError when a placeholder is left in the output or a chart is missing.
```

`src/step7_analyze_post_features/run.py` has `main()`. It downloads the label table, the stimuli, and the step 1 cohort, checks the group counts, and writes and uploads the three analysis CSVs. It then runs the two chart scripts, renders and writes `PAGE_PATH`, uploads the SVGs and the page, and prints one line.

## Commands

```bash
git clone --depth 1 https://github.com/rhiever/evident-charts.git /tmp/evident-charts
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step7_analyze_post_features/run.py
for chart in lean toxicity; do
  PYTHONPATH=. uv run python /tmp/evident-charts/skills/evident-charts/scripts/check_chart.py \
    experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step7_analyze_post_features/charts/${chart}_chart.py \
    --cwd /workspace --dest blog
done
```

The run prints this line, where `F` is the approved feature count:

```text
pairs=20000 five_label_pairs=15113 features=F tables=3 page=public/study-2-features.html
```

Each `check_chart.py` run exits 0. Fix every failure, then follow the review loop in the evident-charts `SKILL.md`. The review loop opens each rendered chart image, fixes each P0 and P1 problem, and stops after a round with none, at most 3 rounds.

## Page check

1. Before the change is deployed, take a screenshot of `/study-2-features` on the current Vercel production site, which shows a not found page, and save it to `images/before/study-2-features.png`.
2. Push the branch and wait for the Vercel preview deployment of the pull request. Find its URL in the Vercel comment on the pull request, or with `gh pr view --comments`.
3. Open `<preview URL>/study-2-features`. Check that the two charts, the eleven top 10 tables, and the feature table show, that the category filter changes the rows, and that the browser console has no errors. Save a screenshot to `images/after/study-2-features.png`.

## Results

Under `## Step 7: analyses` in `RESULTS.md`, write the top 10 table for each group, with one sentence per question that names the features at the top of each group. Link the Vercel page and list the S3 keys of the analysis tables. Add one `CHANGELOG.md` entry that names the page and the approved feature count.

## Pass

The run prints the line in the Commands section, both chart checks exit 0, and the preview page shows the two charts, the eleven top 10 tables, and a feature table that you can filter.

## Fail

The step fails when a group count differs from the pinned count, when a chart check fails, when the page loads a file from outside the page, when `public/index.html` or `public/study-progress.html` changes, or when a p-value, interval, or rater party column appears in any table.
