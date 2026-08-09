"""Regenerate all Study Phase 2 Part 2 transformed artifacts.

Runs keep/remove modal labels, user reflection feedback, and unanimous
min-3 keep/remove labels transforms.

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
from shared.data.transformed.study_phase_2_part_2.transform_keep_remove_labels_unanimous_min3 import (
    OUTPUT_CSV as UNANIMOUS_MIN3_CSV,
    write_keep_remove_labels_unanimous_min3,
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

    unanimous = write_keep_remove_labels_unanimous_min3()
    print(f"Wrote {UNANIMOUS_MIN3_CSV}")
    print(f"rows={len(unanimous)}")
    print(unanimous["decision"].value_counts().to_dict())
    print(f"columns={list(unanimous.columns)}")


if __name__ == "__main__":
    main()
