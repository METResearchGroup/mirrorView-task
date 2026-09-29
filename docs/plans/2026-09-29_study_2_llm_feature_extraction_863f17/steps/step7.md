# Step 7: Analyze the labels and publish the Vercel page

Step 7 answers the four questions in the plan from the step 6 label table, draws one chart per question, and writes one static page that Vercel serves at `/study-2-features`. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step7_analyze_post_features/run.py`. Step 7 calls no model.

Out of scope are new labels, new features, and any page other than `/study-2-features`.

## Decisions

The analyses read three inputs:

- The label table from step 6, which has 20,000 pairs.
- `sampled_stance` and `sample_toxicity_type` from `STUDY_2_STIMULI`, joined on `post_id`. In the stimulus file, 11,550 pairs lean left and 8,450 lean right. There are 5,000 low, 10,000 medium, and 5,000 high toxicity pairs, where medium is `sample_middle_toxicity`.
- Human decisions from `STUDY_2_RESULTS_FULL`, passed through `select_scored_trials` and `dedupe_labeler_post` from `experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py`. The two functions keep one decision per person and pair. On 2026-09-29 the deduplicated table has 101,020 decisions, with 53,080 from Democrats and 47,940 from Republicans by `party_group`.

The analyses answer the four questions this way:

1. For prevalence, count, for each feature, the pairs where it is 1 and divide by 20,000.
2. For lean, compute, for each feature, the share among left pairs and among right pairs, and the difference, left minus right, in percentage points. The 95% interval uses the unpooled normal approximation. The p-value is the two-sided two-proportion z-test with the pooled variance.
3. For toxicity, compute, for each feature, the share in each toxicity level and the high minus low difference in percentage points. The p-value is the chi-square test of independence on the 2 by 3 table of feature present or absent by level, from `scipy.stats.chi2_contingency`.
4. For party, compute, for each feature and party, the remove rate on decisions about pairs with the feature, the remove rate on decisions about pairs without it, and the difference in percentage points. A positive difference means that party removed pairs with the feature more often, and a negative difference means that party kept them more often. One person makes many decisions, so the decisions are not independent, and this table has no p-values.

For questions 2 and 3, adjust the p-values across features with the Benjamini and Hochberg method, and call a feature different when the adjusted value is below 0.05. Implement the method in `stats.py`, which takes about ten lines, so the experiment adds no package.

The charts follow the evident-charts skill at `https://github.com/rhiever/evident-charts/blob/main/skills/evident-charts/SKILL.md`. Read that `SKILL.md` before writing any chart. Clone the repository once with `git clone --depth 1 https://github.com/rhiever/evident-charts.git /tmp/evident-charts`, and import `evident` from `/tmp/evident-charts/skills/evident-charts/scripts`. The clone is not committed. Each chart is its own script, because `check_chart.py` runs a chart script and inspects the figures it makes. Every chart uses the `blog` preset and has a title that states the main result in words, built from the data. It also has a subtitle with the measure, the units, and the number of pairs, and a source line that reads "Source: MirrorView Study 2, Jev labels at a 0.7 cutoff". The charts are these:

- The prevalence chart has horizontal bars for the 20 most common features. Each bar is labeled with the feature name and category, and with its share as a percentage.
- The lean chart shows the left minus right difference, with 95% interval whiskers and a zero line, for the 20 features with the largest absolute difference among those with an adjusted p-value below 0.05.
- The toxicity chart has one row per feature, with three dots for low, medium, and high. It shows the 15 features with the largest absolute high minus low difference among those with an adjusted p-value below 0.05.
- The party chart has one row per feature, with a Democrat dot and a Republican dot for the remove rate difference. It shows the 15 features with the largest absolute difference for either party, among features with at least 100 decisions on pairs with the feature for each party.

Each chart script writes an SVG. `render.py` puts the SVG text inside the page, so the page is one self-contained HTML file.

The page template is three files in `src/step7_analyze_post_features/webapp/`, which the issue allows: `index.html`, `styles.css`, and `app.js`. `index.html` has the placeholders `{{STYLES}}`, `{{SCRIPT}}`, `{{CHARTS}}`, and `{{DATA_JSON}}`. `render.py` fills them in and writes `/workspace/public/study-2-features.html`. The page has one section per question with its chart and a short answer. It ends with a table of every feature, showing the name, the category, the definition, the prevalence, the lean difference, and the high minus low difference. `app.js` reads the embedded JSON and lets you filter the table by category, search it by text, and sort it by any column. The page loads no outside script, font, or file.

Vercel serves `public/` because `vercel.json` sets `"outputDirectory": "public"`. Add rewrites from `/study-2-features` and `/study-2-features/` to `/study-2-features.html`, following the existing `/study-progress` rewrites. Add `!public/study-2-features.html` to `.vercelignore`, next to `!public/study-progress.html`.

The analysis tables go to `outputs/analyses/` and to the `analyses/` key under the S3 prefix, as the issue asks. The SVGs and a copy of the page also go to S3 under `step7_analyze_post_features/`.

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `/tmp/evident-charts/skills/evident-charts/SKILL.md` | Chart rules and the check workflow |
| `/tmp/evident-charts/skills/evident-charts/scripts/evident.py` | `figure`, `titles`, `value_labels`, `save` |
| `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py` | `select_scored_trials`, `dedupe_labeler_post` |
| `/workspace/experiments/study_progress_dashboard_2026_09_11/render.py` | An earlier static page renderer in this repository |
| `/workspace/vercel.json` and `/workspace/.vercelignore` | The existing `/study-progress` route and allow lines |
| `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/constants.py` | `LABEL_TO_DETAIL`, `FEATURE_PRESENT_THRESHOLD` |

## Files allowed to change

Paths under `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/`:

- Edit `shared/constants.py` to add the constants in the Contracts section
- Create `src/step7_analyze_post_features/__init__.py`, `analyses.py`, `stats.py`, `render.py`, and `run.py`
- Create `src/step7_analyze_post_features/charts/__init__.py`, `common.py`, `prevalence_chart.py`, `lean_chart.py`, `toxicity_chart.py`, and `party_chart.py`
- Create `src/step7_analyze_post_features/webapp/index.html`, `styles.css`, and `app.js`
- Create `tests/test_stats.py`, `tests/test_analyses.py`, and `tests/test_render.py`
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
STANCE_LEFT = "left"
STANCE_RIGHT = "right"
TOXICITY_LEVELS = {"sample_low_toxicity": "low", "sample_middle_toxicity": "medium",
                   "sample_high_toxicity": "high"}
PARTY_GROUPS = ("democrat", "republican")
EXPECTED_SCORED_DECISIONS = 101020
SIGNIFICANCE_Q = 0.05
MIN_DECISIONS_FOR_RANKING = 100
PREVALENCE_CHART_TOP_N = 20
LEAN_CHART_TOP_N = 20
TOXICITY_CHART_TOP_N = 15
PARTY_CHART_TOP_N = 15
EVIDENT_CHARTS_SCRIPTS_DIR = Path("/tmp/evident-charts/skills/evident-charts/scripts")
CHART_PRESET = "blog"
CHART_SOURCE = "Source: MirrorView Study 2, Jev labels at a 0.7 cutoff"
ANALYSES_PREFIX = "analyses/"
PAGE_PATH = REPO_ROOT / "public" / "study-2-features.html"
PAGE_KEY = "step7_analyze_post_features/study-2-features.html"
```

`src/step7_analyze_post_features/stats.py`:

```text
benjamini_hochberg(p_values: np.ndarray) -> np.ndarray
two_proportion_test(successes_a: int, n_a: int, successes_b: int, n_b: int) -> tuple[float, float, float, float]
  Return difference_pp, ci_low_pp, ci_high_pp, p_value.
```

`src/step7_analyze_post_features/analyses.py`:

```text
feature_prevalence(labels: pd.DataFrame, details: dict[str, dict[str, str]]) -> pd.DataFrame
  Columns feature_key, name, category, n_pairs, share, sorted by share descending.
prevalence_by_lean(labels: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame
  Columns feature_key, share_left, share_right, difference_pp, ci_low_pp, ci_high_pp, p_value, q_value.
prevalence_by_toxicity(labels: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame
  Columns feature_key, share_low, share_medium, share_high, high_minus_low_pp, p_value, q_value.
remove_rate_by_party(labels: pd.DataFrame, decisions: pd.DataFrame) -> pd.DataFrame
  One row per feature_key and party_group, with columns n_with, remove_rate_with,
  remove_rate_without, difference_pp.
```

Each function raises `ValueError` when a pair in `labels` has no matching row in the other input.

Each chart script has `main()`, loads its CSV from `outputs/analyses/`, and writes its SVG to `outputs/step7_analyze_post_features/figures/`. `charts/common.py` has `load_evident()`, which adds `EVIDENT_CHARTS_SCRIPTS_DIR` to `sys.path`, imports `evident`, and raises `FileNotFoundError` with the clone command when the folder is missing.

`src/step7_analyze_post_features/render.py`:

```text
build_page_data(prevalence, lean, toxicity, party, details) -> dict
render_page(template: str, styles: str, script: str, charts: dict[str, str], data: dict) -> str
  Raise ValueError when a placeholder is left in the output or a chart is missing.
```

`src/step7_analyze_post_features/run.py` has `main()`. It downloads the label table, the stimuli, and the results, checks the decision count against `EXPECTED_SCORED_DECISIONS`, and writes and uploads the four analysis CSVs. It then runs the four chart scripts, renders and writes `PAGE_PATH`, uploads the SVGs and the page, and prints one line.

## Tests

- `tests/test_stats.py`: `TestBenjaminiHochberg` checks that p-values `[0.01, 0.04, 0.03, 0.20]` give q-values `[0.04, 0.0533, 0.0533, 0.20]` to 4 decimals. `TestTwoProportionTest` checks that 60 of 100 against 40 of 100 gives a difference of 20.0 points and a p-value below 0.01, and that equal shares give 0.0 and 1.0.
- `tests/test_analyses.py`: `TestFeaturePrevalence` checks the share and the sort order. `TestPrevalenceByLean` checks the left and right shares on a 4-pair frame. `TestPrevalenceByToxicity` checks that all three levels appear and that high minus low is computed. `TestRemoveRateByParty` checks that a party whose decisions are all remove on pairs with the feature and all keep on pairs without it gets 100.0 points. `TestJoins.test_missing_stimulus_raises` checks the `ValueError`.
- `tests/test_render.py`: `TestRenderPage` checks that every placeholder is filled, that the output holds each SVG, and that a missing chart raises `ValueError`. `TestBuildPageData` checks one feature record per key in `details`.

No test reads S3 or needs the evident-charts clone.

## Commands

```bash
git clone --depth 1 https://github.com/rhiever/evident-charts.git /tmp/evident-charts
PYTHONPATH=. uv run pytest experiments/study_2_llm_based_feature_extraction_2026_09_29/tests -q
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step7_analyze_post_features/run.py
for chart in prevalence lean toxicity party; do
  PYTHONPATH=. uv run python /tmp/evident-charts/skills/evident-charts/scripts/check_chart.py \
    experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step7_analyze_post_features/charts/${chart}_chart.py \
    --cwd /workspace --dest blog
done
```

The run prints this line:

```text
pairs=20000 decisions=101020 features=F page=public/study-2-features.html
```

Each `check_chart.py` run exits 0. Fix every failure, then follow the review loop in the evident-charts `SKILL.md`. The review loop opens each rendered chart image, fixes each P0 and P1 problem, and stops after a round with none, at most 3 rounds.

## Page check

1. Before the change is deployed, take a screenshot of `/study-2-features` on the current Vercel production site, which shows a not found page, and save it to `images/before/study-2-features.png`.
2. Push the branch and wait for the Vercel preview deployment of the pull request. Find its URL in the Vercel comment on the pull request, or with `gh pr view --comments`.
3. Open `<preview URL>/study-2-features`. Check that the four charts and the feature table show, that the category filter changes the rows, and that the browser console has no errors. Save a screenshot to `images/after/study-2-features.png`.

## Results

Under `## Step 7: analyses` in `RESULTS.md`, write one short answer and one table of the top 10 rows for each question. Link the Vercel page and list the S3 keys of the analysis tables. Add one `CHANGELOG.md` entry that names the page and the approved feature count.

## Pass

The pytest command exits 0, the run prints the line in the Commands section, all four chart checks exit 0, and the preview page shows the four charts and a table that you can filter.

## Fail

The step fails when a chart check fails, when the page loads a file from outside the page, when `public/index.html` or `public/study-progress.html` changes, or when a p-value appears in the party table.
