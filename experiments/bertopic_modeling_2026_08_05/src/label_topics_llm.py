"""Stage 3: post-hoc LLM topic labels via bertopic.representation.OpenAI.

Fits are not re-run. Labels use ``gpt-5.4-nano`` and skip HDBSCAN noise topic ``-1``.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py \\
      --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from bertopic import BERTopic
from bertopic.representation import OpenAI
import openai

from experiments.bertopic_modeling_2026_08_05.src import data as data_mod
from experiments.bertopic_modeling_2026_08_05.src import paths
from lib.load_env_vars import EnvVarsContainer

TEXT_ROLE = paths.TEXT_ROLE_V1
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
    """Paths from a Stage-3 labeling run."""

    run_dir: Path
    source_topics_run: Path
    n_topics_labeled: int


def _latest_topics_run() -> Path:
    root = paths.topics_dir(TEXT_ROLE)
    runs = sorted([p for p in root.iterdir() if p.is_dir() and (p / "metadata.json").is_file()])
    if not runs:
        raise FileNotFoundError(f"No topics runs under {root}")
    return runs[-1]


def _docs_for_topics_run(topics_run: Path) -> list[str]:
    """Rebuild docs in the same message_id order as the topics assignments."""
    assignments = pd.read_parquet(topics_run / "assignments.parquet")
    message_ids = assignments["message_id"].astype(str).tolist()
    posts = data_mod.load_keep_remove_posts()
    text_by_id = {
        str(row.message_id): str(row.original_text)
        for row in posts.itertuples(index=False)
    }
    missing = [mid for mid in message_ids if mid not in text_by_id]
    if missing:
        raise ValueError(
            f"message_ids missing from dataset: n={len(missing)} examples={missing[:5]}"
        )
    return [text_by_id[mid] for mid in message_ids]


def run_label_topics_llm(topics_run_dir: Path | None) -> LabelResult:
    """Label non-noise topics with OpenAI representation model.

    Parameters
    ----------
    topics_run_dir
        Source Stage-2 run directory. When None, uses the latest topics run.

    Returns
    -------
    LabelResult
        New labels run directory and counts.
    """
    _ = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)

    topics_run = topics_run_dir if topics_run_dir is not None else _latest_topics_run()
    model_dir = topics_run / "model"
    if not model_dir.is_dir():
        raise FileNotFoundError(f"Missing saved BERTopic model at {model_dir}")

    docs = _docs_for_topics_run(topics_run)
    topic_model = BERTopic.load(str(model_dir))
    ctfidf_info = topic_model.get_topic_info().copy()
    ctfidf_name_by_topic = {
        int(row.Topic): str(row.Name) for row in ctfidf_info.itertuples(index=False)
    }

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
    # BERTopic defaults stop="\n" when stop is missing/falsy; gpt-5.4-nano rejects stop.
    representation_model.generator_kwargs.pop("stop", None)

    _orig_extract = representation_model.extract_topics

    def _extract_skip_noise(topic_model, documents, c_tf_idf, topics):
        representation_model.generator_kwargs.pop("stop", None)
        filtered = {
            topic_id: words
            for topic_id, words in topics.items()
            if int(topic_id) != NOISE_TOPIC_ID
        }
        labeled = _orig_extract(topic_model, documents, c_tf_idf, filtered)
        if NOISE_TOPIC_ID in topics or str(NOISE_TOPIC_ID) in topics:
            noise_key = NOISE_TOPIC_ID if NOISE_TOPIC_ID in topics else str(NOISE_TOPIC_ID)
            labeled[noise_key] = topics[noise_key]
        return labeled

    representation_model.extract_topics = _extract_skip_noise  # type: ignore[method-assign]
    topic_model.update_topics(docs, representation_model=representation_model)

    topic_info = topic_model.get_topic_info()
    assignments = pd.read_parquet(topics_run / "assignments.parquet")
    n_docs_by_topic = assignments.groupby("topic").size().to_dict()

    rows: list[dict] = []
    n_labeled = 0
    for _, row in topic_info.iterrows():
        topic_id = int(row["Topic"])
        ctfidf_name = ctfidf_name_by_topic.get(topic_id, str(row.get("Name", "")))
        n_docs = int(n_docs_by_topic.get(topic_id, row.get("Count", 0)))
        if topic_id == NOISE_TOPIC_ID:
            llm_label = None
        else:
            llm_label = str(row.get("Name", "")).strip() or None
            if "Representation" in topic_info.columns:
                representation = row["Representation"]
                if isinstance(representation, list) and representation:
                    llm_label = str(representation[0])
                elif isinstance(representation, str) and representation.strip():
                    llm_label = representation.strip()
            n_labeled += 1
        rows.append(
            {
                "topic_id": topic_id,
                "ctfidf_name": ctfidf_name,
                "llm_label": llm_label,
                "n_docs": n_docs,
            }
        )
    run_dir = paths.labels_dir(TEXT_ROLE) / paths.new_run_timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    labels_df = pd.DataFrame(rows)
    labels_df.to_parquet(run_dir / "topic_labels.parquet", index=False)

    metadata = {
        "model": DEFAULT_MODEL,
        "prompt": LLM_PROMPT,
        "source_topics_run": str(topics_run),
        "nr_docs": NR_DOCS,
        "diversity": DIVERSITY,
        "doc_length": DOC_LENGTH,
        "tokenizer": TOKENIZER,
        "noise_label_policy": NOISE_LABEL_POLICY,
        "n_topics_labeled": n_labeled,
        "unanimous_rule_id": None,
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"labels_run_dir={run_dir}")
    print(f"source_topics_run={topics_run} n_topics_labeled={n_labeled}")
    return LabelResult(
        run_dir=run_dir,
        source_topics_run=topics_run,
        n_topics_labeled=n_labeled,
    )


def main() -> None:
    """CLI entrypoint for Stage 3."""
    parser = argparse.ArgumentParser(
        description="Post-hoc LLM topic labels (gpt-5.4-nano); skips topic -1."
    )
    parser.add_argument(
        "--topics-run-dir",
        type=Path,
        default=None,
        help="Stage-2 topics run directory (default: latest under outputs/topics/original/).",
    )
    args = parser.parse_args()
    run_label_topics_llm(topics_run_dir=args.topics_run_dir)


if __name__ == "__main__":
    main()
