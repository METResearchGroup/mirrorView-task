"""Regenerate all Study Phase 2 Part 2 transformed artifacts.

Runs keep/remove labels and user reflection feedback transforms.

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/main.py
"""

from __future__ import annotations

from shared.data.transformed.study_phase_2_part_2.transform import (
    OUTPUT_CSV,
    write_keep_remove_labels,
)
from shared.data.transformed.study_phase_2_part_2.transform_get_user_reflection_feedback import (
    USER_REFLECTION_FEEDBACK_CSV,
    write_user_reflection_feedback,
)


def main() -> None:
    labels = write_keep_remove_labels()
    print(f"Wrote {OUTPUT_CSV}")
    print(f"rows={len(labels)}")
    print(labels["decision"].value_counts().to_dict())
    print(f"columns={list(labels.columns)}")

    reflections = write_user_reflection_feedback()
    print(f"Wrote {USER_REFLECTION_FEEDBACK_CSV}")
    print(f"rows={len(reflections)}")
    print(f"columns={list(reflections.columns)}")


if __name__ == "__main__":
    main()
