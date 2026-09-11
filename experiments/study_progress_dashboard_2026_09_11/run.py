"""Export the live September 2026 study, aggregate it, and write the dashboard.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python experiments/study_progress_dashboard_2026_09_11/run.py
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from experiments.study_progress_dashboard_2026_09_11.analyze import build_payload
from experiments.study_progress_dashboard_2026_09_11.constants import (
    CACHE_DIRNAME,
    EXPERIMENT_DIRNAME,
    GRACE_MINUTES,
    OUTPUTS_DIRNAME,
    TIMESTAMP_FORMAT,
    experiment_dir,
)
from experiments.study_progress_dashboard_2026_09_11.load import (
    count_export_files,
    export_study_csv,
    load_export_csv,
    scan_assignments,
)
from experiments.study_progress_dashboard_2026_09_11.write import (
    upload_dashboard_artifacts,
    write_dashboard,
    write_payload,
    write_results_md,
)
from lib.timestamp_utils import get_current_timestamp


def parse_args() -> argparse.Namespace:
    """Parse CLI flags for a dashboard refresh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--export-csv",
        type=Path,
        default=None,
        help="Use this combined export instead of downloading from S3.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download every prolific CSV even when a local temp copy exists.",
    )
    parser.add_argument(
        "--since-date",
        type=date.fromisoformat,
        default=date(2026, 9, 9),
        metavar="YYYY-MM-DD",
        help="Export cutoff passed to the study export helper. Default 2026-09-09.",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip uploading HTML and JSON to S3.",
    )
    return parser.parse_args()


def main() -> int:
    """Refresh the study progress dashboard from live S3 and DynamoDB data."""
    args = parse_args()
    root = experiment_dir()
    cache_dir = root / CACHE_DIRNAME
    outputs_dir = root / OUTPUTS_DIRNAME

    if args.export_csv is not None:
        export_path = args.export_csv
    else:
        export_path = export_study_csv(
            cache_dir, since_date=args.since_date, force_download=args.force_download
        )

    export_df = load_export_csv(export_path)
    assignments = scan_assignments()
    generated_at = get_current_timestamp()
    export_timestamp = _timestamp_from_path(export_path)
    export_dt = datetime.strptime(export_timestamp, TIMESTAMP_FORMAT)
    cutoff = export_dt - timedelta(minutes=GRACE_MINUTES)

    payload = build_payload(
        export_df,
        assignments,
        generated_at=generated_at,
        export_path=export_path.name,
        export_files=count_export_files(export_df),
        export_timestamp=export_timestamp,
        grace_minutes=GRACE_MINUTES,
        cutoff=cutoff,
    )

    payload_path = write_payload(payload, outputs_dir)
    html_path = write_dashboard(payload, root)
    results_path = write_results_md(payload, root)

    print(f"Export: {export_path}")
    print(f"Assigned: {payload['progress']['assigned_valid']}")
    print(f"Finished: {payload['progress']['completers']}")
    print(f"Labels: {payload['progress']['labels']}")
    print(f"Wrote {payload_path}")
    print(f"Wrote {html_path}")
    print(f"Wrote {results_path}")
    print(
        "Dashboard path: "
        f"experiments/{EXPERIMENT_DIRNAME}/{html_path.name}"
    )

    if not args.skip_upload:
        uris = upload_dashboard_artifacts([html_path, payload_path, results_path])
        for uri in uris:
            print(f"Uploaded {uri}")
    return 0


def _timestamp_from_path(path: Path) -> str:
    name = path.stem
    # export_jspsych-mirror-view-2026-09-09_2026_09_11-02:27:54
    # or mirrorview_data_jspsych-mirror-view-2026-09-09_2026_09_11-02:27:54
    for prefix in (
        "export_jspsych-mirror-view-2026-09-09_",
        "mirrorview_data_jspsych-mirror-view-2026-09-09_",
    ):
        if name.startswith(prefix):
            return name[len(prefix):]
    return get_current_timestamp()


if __name__ == "__main__":
    raise SystemExit(main())
