"""Step 7 entrypoint: count top features and write the static page.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step7_analyze_post_features/run.py
"""

from __future__ import annotations

from experiments.compare_jev_human_uncertainty_2026_09_25.jev_labels import (
    use_lab_credentials,
)

use_lab_credentials()

import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    COHORT_KEY,
    EXPECTED_FIVE_LABEL_PAIRS,
    EXPECTED_REMOVE_VOTE_COUNTS,
    EXPECTED_STANCE_COUNTS,
    EXPECTED_STIMULUS_PAIRS,
    EXPECTED_TOXICITY_COUNTS,
    LABEL_TO_DETAIL,
    LEAN_CHART_KEY,
    LOCAL_OUTPUT_DIR,
    PAGE_KEY,
    PAGE_PATH,
    POST_FEATURE_LABELS_KEY,
    REMOVE_VOTE_LEVELS,
    REMOVE_VOTE_PROPORTION_CHART_KEY,
    REMOVE_VOTE_PROPORTION_KEY,
    STANCE_LEVELS,
    TOP_BY_LEAN_KEY,
    TOP_BY_REMOVE_VOTES_KEY,
    TOP_BY_TOXICITY_KEY,
    TOP_FEATURES_PER_GROUP,
    TOXICITY_CHART_KEY,
    TOXICITY_LEVELS,
    TOXICITY_PROPORTION_CHART_KEY,
    TOXICITY_PROPORTION_KEY,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.storage import (
    download_artifact,
    local_path,
    upload_artifact,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.analyses import (
    check_group_counts,
    feature_proportions,
    top_features_by_group,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.charts.remove_votes_proportion_chart import (
    main as draw_remove_proportions,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.charts.toxicity_proportion_chart import (
    main as draw_toxicity_proportions,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.charts.lean_chart import (
    main as draw_lean,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.charts.toxicity_chart import (
    main as draw_toxicity,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.render import (
    build_page_data,
    render_page,
)
from shared.data.dataloader import load_dataset

WEBAPP = (
    LOCAL_OUTPUT_DIR.parent
    / "src"
    / "step7_analyze_post_features"
    / "webapp"
)


def _write_table(frame: pd.DataFrame, relative_key: str) -> None:
    path = local_path(relative_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    upload_artifact(relative_key)


def main() -> None:
    """Build the three count tables, two charts, and the static page."""
    labels = pd.read_parquet(download_artifact(POST_FEATURE_LABELS_KEY))
    labels["post_id"] = labels["post_id"].astype(str)
    stimuli = load_dataset("STUDY_2_STIMULI")
    stimuli["post_id"] = stimuli["post_primary_key"].astype(str)
    cohort = pd.read_parquet(download_artifact(COHORT_KEY))
    cohort["post_id"] = cohort["post_id"].astype(str)

    stance = stimuli.set_index("post_id")["sampled_stance"]
    stance = stance.loc[stance.index.isin(labels["post_id"])]
    stance = stance.loc[stance.isin(STANCE_LEVELS)]
    check_group_counts(stance, EXPECTED_STANCE_COUNTS)

    toxicity = stimuli.set_index("post_id")["sample_toxicity_type"].map(TOXICITY_LEVELS)
    toxicity = toxicity.dropna()
    toxicity = toxicity.loc[toxicity.index.isin(labels["post_id"])]
    check_group_counts(toxicity, EXPECTED_TOXICITY_COUNTS)

    remove_votes = cohort.set_index("post_id")["n_remove"].astype(int)
    remove_votes = remove_votes.loc[remove_votes.isin(REMOVE_VOTE_LEVELS)]
    check_group_counts(remove_votes, EXPECTED_REMOVE_VOTE_COUNTS)

    by_lean = top_features_by_group(labels, stance, LABEL_TO_DETAIL, TOP_FEATURES_PER_GROUP)
    by_toxicity = top_features_by_group(labels, toxicity, LABEL_TO_DETAIL, TOP_FEATURES_PER_GROUP)
    by_remove = top_features_by_group(labels, remove_votes, LABEL_TO_DETAIL, TOP_FEATURES_PER_GROUP)
    _write_table(by_lean, TOP_BY_LEAN_KEY)
    _write_table(by_toxicity, TOP_BY_TOXICITY_KEY)
    _write_table(by_remove, TOP_BY_REMOVE_VOTES_KEY)
    _write_table(
        feature_proportions(labels, toxicity, LABEL_TO_DETAIL, ["low", "medium", "high"]),
        TOXICITY_PROPORTION_KEY,
    )
    _write_table(
        feature_proportions(
            labels,
            remove_votes,
            LABEL_TO_DETAIL,
            list(REMOVE_VOTE_LEVELS),
        ),
        REMOVE_VOTE_PROPORTION_KEY,
    )

    draw_lean()
    draw_toxicity()
    draw_toxicity_proportions()
    draw_remove_proportions()
    upload_artifact(LEAN_CHART_KEY)
    upload_artifact(TOXICITY_CHART_KEY)
    upload_artifact(TOXICITY_PROPORTION_CHART_KEY)
    upload_artifact(REMOVE_VOTE_PROPORTION_CHART_KEY)

    charts = {
        "lean": (LOCAL_OUTPUT_DIR / LEAN_CHART_KEY).read_text(encoding="utf-8"),
        "toxicity": (LOCAL_OUTPUT_DIR / TOXICITY_CHART_KEY).read_text(encoding="utf-8"),
        "toxicity_lines": (LOCAL_OUTPUT_DIR / TOXICITY_PROPORTION_CHART_KEY).read_text(encoding="utf-8"),
        "remove_lines": (LOCAL_OUTPUT_DIR / REMOVE_VOTE_PROPORTION_CHART_KEY).read_text(encoding="utf-8"),
    }
    page = render_page(
        (WEBAPP / "index.html").read_text(encoding="utf-8"),
        (WEBAPP / "styles.css").read_text(encoding="utf-8"),
        (WEBAPP / "app.js").read_text(encoding="utf-8"),
        charts,
        build_page_data(by_lean, by_toxicity, by_remove, LABEL_TO_DETAIL),
    )
    PAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PAGE_PATH.write_text(page, encoding="utf-8")
    page_copy = local_path(PAGE_KEY)
    page_copy.parent.mkdir(parents=True, exist_ok=True)
    page_copy.write_text(page, encoding="utf-8")
    upload_artifact(PAGE_KEY)
    print(
        f"pairs={EXPECTED_STIMULUS_PAIRS} five_label_pairs={EXPECTED_FIVE_LABEL_PAIRS} "
        f"features={len(LABEL_TO_DETAIL)} tables=3 page=public/study-2-features.html"
    )


if __name__ == "__main__":
    main()
