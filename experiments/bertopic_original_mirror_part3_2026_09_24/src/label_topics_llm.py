"""Label BERTopic topics with gpt-5.4-nano. Noise topic -1 is not sent to the API.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/label_topics_llm.py \\
      --text-role original --topics-run-dir <topics run>
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import openai
import pandas as pd
from bertopic import BERTopic
from bertopic.representation import OpenAI

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from lib.load_env_vars import EnvVarsContainer

DEFAULT_MODEL = "gpt-5.4-nano"
NOISE_TOPIC_ID = -1
NOISE_LABEL_POLICY = "llm_label_null_skip_api"
NR_DOCS = 4
DIVERSITY = 0.1
DOC_LENGTH = 150
TOKENIZER = "whitespace"
LLM_PROMPT = """I have a topic that contains the following documents:
[DOCUMENTS]
The topic is described by the following keywords: [KEYWORDS]

Based on the information above, extract a short topic label in the following format:
topic: <topic label>
"""


@dataclass(frozen=True)
class LabelResult:
    """A labels run and how many topics were sent to the model."""

    run_dir: Path
    source_topics_run: Path
    n_topics_labeled: int


def docs_for_assignments(assignments: pd.DataFrame) -> list[str]:
    """Rebuild the document list from stimulus text and ``text_role``."""
    posts = data_mod.load_stimuli_posts().drop_duplicates("post_id").set_index("post_id")
    docs: list[str] = []
    for row in assignments.itertuples(index=False):
        column = "original_text" if row.text_role == "original" else "mirror_text"
        docs.append(str(posts.loc[str(row.post_id), column]))
    return docs


def _skip_noise_extract(representation_model: OpenAI, original_extract):
    """Return an extract_topics wrapper that does not call the API for topic -1."""

    def extract(topic_model, documents, c_tf_idf, topics):
        representation_model.generator_kwargs.pop("stop", None)
        filtered = {topic_id: words for topic_id, words in topics.items() if int(topic_id) != NOISE_TOPIC_ID}
        labeled = original_extract(topic_model, documents, c_tf_idf, filtered)
        if NOISE_TOPIC_ID in topics:
            labeled[NOISE_TOPIC_ID] = topics[NOISE_TOPIC_ID]
        return labeled

    return extract


def _llm_label_from_row(row: pd.Series) -> str | None:
    """Prefer the representation string, then the topic name."""
    representation = row.get("Representation")
    if isinstance(representation, list) and representation:
        return str(representation[0])
    if isinstance(representation, str) and representation.strip():
        return representation.strip()
    name = str(row.get("Name", "")).strip()
    return name or None


def run_label_topics_llm(role: str, topics_run_dir: Path) -> LabelResult:
    """Label one topics run and write ``topic_labels.parquet``.

    Parameters
    ----------
    role
        ``original``, ``mirror``, or ``joint``.
    topics_run_dir
        Directory containing ``model/`` and ``assignments.parquet``.

    Returns
    -------
    LabelResult
        New labels directory.
    """
    validated = paths.require_text_role(role)
    EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    assignments = pd.read_parquet(topics_run_dir / "assignments.parquet")
    topic_model = BERTopic.load(str(topics_run_dir / "model"))
    ctfidf_names = {int(row.Topic): str(row.Name) for row in topic_model.get_topic_info().itertuples(index=False)}
    client = openai.OpenAI()
    representation_model = OpenAI(
        client,
        model=DEFAULT_MODEL,
        chat=True,
        nr_docs=NR_DOCS,
        diversity=DIVERSITY,
        doc_length=DOC_LENGTH,
        tokenizer=TOKENIZER,
        prompt=LLM_PROMPT,
        generator_kwargs={"temperature": 1},
    )
    representation_model.generator_kwargs.pop("stop", None)
    representation_model.extract_topics = _skip_noise_extract(
        representation_model, representation_model.extract_topics
    )
    topic_model.update_topics(docs_for_assignments(assignments), representation_model=representation_model)
    topic_info = topic_model.get_topic_info()
    counts = assignments.groupby("topic").size().to_dict()
    rows = []
    n_labeled = 0
    for _, row in topic_info.iterrows():
        topic_id = int(row["Topic"])
        if topic_id == NOISE_TOPIC_ID:
            llm_label = None
        else:
            llm_label = _llm_label_from_row(row)
            n_labeled += 1
        rows.append(
            {
                "topic_id": topic_id,
                "ctfidf_name": ctfidf_names.get(topic_id, str(row.get("Name", ""))),
                "llm_label": llm_label,
                "n_docs": int(counts.get(topic_id, 0)),
            }
        )
    run_dir = paths.labels_dir(validated) / paths.new_run_timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(run_dir / "topic_labels.parquet", index=False)
    metadata = {
        "model": DEFAULT_MODEL,
        "text_role": validated,
        "source_topics_run": str(topics_run_dir),
        "noise_label_policy": NOISE_LABEL_POLICY,
        "n_topics_labeled": n_labeled,
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"labels_run_dir={run_dir}")
    print(f"source_topics_run={topics_run_dir} n_topics_labeled={n_labeled}")
    return LabelResult(run_dir, topics_run_dir, n_labeled)


def main() -> None:
    """CLI entry for post-hoc labels."""
    parser = argparse.ArgumentParser(description="Label topics with gpt-5.4-nano. Skips topic -1.")
    parser.add_argument("--text-role", choices=["original", "mirror", "joint"], required=True)
    parser.add_argument("--topics-run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_label_topics_llm(args.text_role, args.topics_run_dir)


if __name__ == "__main__":
    main()
