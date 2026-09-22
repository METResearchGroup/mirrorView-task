"""Write payload, dashboard HTML, RESULTS.md, and S3 copies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.study_progress_dashboard_2026_09_11.constants import (
    CELL_LABELS,
    DASHBOARD_FILENAME,
    OUTPUT_S3_BUCKET,
    OUTPUT_S3_PREFIX,
    PARTY_LABELS,
    PARTY_ORDER,
    PAYLOAD_FILENAME,
    RESULTS_FILENAME,
    STANCE_LABELS,
    TOXICITY_LABELS,
)
from experiments.study_progress_dashboard_2026_09_11.render import (
    fmt_int,
    fmt_num,
    fmt_pct,
    render_html,
)
from lib.aws.s3 import S3


def write_payload(payload: dict[str, Any], outputs_dir: Path) -> Path:
    """Write the aggregated JSON payload."""
    outputs_dir.mkdir(parents=True, exist_ok=True)
    export = payload.get("export")
    if isinstance(export, dict) and export.get("path"):
        payload = {
            **payload,
            "export": {**export, "path": Path(str(export["path"])).name},
        }
    path = outputs_dir / PAYLOAD_FILENAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def write_dashboard(
    payload: dict[str, Any],
    experiment_dir: Path,
    vercel_paths: list[Path] | None = None,
) -> Path:
    """Write ``index.html`` and any Vercel copies of the same HTML."""
    html = render_html(payload)
    path = experiment_dir / DASHBOARD_FILENAME
    path.write_text(html, encoding="utf-8")
    for vercel_path in vercel_paths or []:
        vercel_path.parent.mkdir(parents=True, exist_ok=True)
        vercel_path.write_text(html, encoding="utf-8")
    return path


def write_results_md(payload: dict[str, Any], experiment_dir: Path) -> Path:
    """Write RESULTS.md from the same payload as the dashboard."""
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(payload), encoding="utf-8")
    return path


def upload_dashboard_artifacts(local_paths: list[Path]) -> list[str]:
    """Upload dashboard files to the experiment prefix in S3."""
    store = S3(OUTPUT_S3_BUCKET, region_name="us-east-2")
    uris: list[str] = []
    for path in local_paths:
        key = f"{OUTPUT_S3_PREFIX}{path.name}"
        store.upload_file(path, key)
        uris.append(f"s3://{OUTPUT_S3_BUCKET}/{key}")
    return uris


def _results_markdown(payload: dict[str, Any]) -> str:
    study = payload["study"]
    progress = payload["progress"]
    export = payload["export"]
    all_m = payload["all"]
    by_party = payload["by_party"]
    cov = payload["post_coverage"]
    att = payload["attention_remove_share"]

    party_lines = [
        "| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |",
        "| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |",
    ]
    for party in PARTY_ORDER:
        m = by_party[party]
        assigned_share = m["assigned"] / m["target_slots"] if m["target_slots"] else None
        finish_share = m["n_completers"] / m["assigned"] if m["assigned"] else None
        party_lines.append(
            f"| {PARTY_LABELS[party]} | {fmt_int(m['assigned'])} | {fmt_int(m['n_completers'])} | "
            f"{fmt_int(m['target_slots'])} | {fmt_pct(assigned_share)} | {fmt_pct(finish_share)} |"
        )

    decision_lines = [
        "| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |",
        "| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |",
    ]
    for party in PARTY_ORDER:
        m = by_party[party]
        td = m["trial_decisions"]
        decision_lines.append(
            f"| {PARTY_LABELS[party]} | {fmt_int(td['n_keep'])} | {fmt_int(td['n_remove'])} | "
            f"{fmt_int(td['n_trials'])} | {fmt_pct(td['keep_share'])} | {fmt_pct(td['remove_share'])} | "
            f"{fmt_pct(m['user_keep_rate']['mean'])} | {fmt_pct(m['user_remove_rate']['mean'])} | "
            f"{fmt_int(m['always_keep'])} | {fmt_int(m['always_remove'])} |"
        )
    td = all_m["trial_decisions"]
    decision_lines.append(
        f"| All | {fmt_int(td['n_keep'])} | {fmt_int(td['n_remove'])} | {fmt_int(td['n_trials'])} | "
        f"{fmt_pct(td['keep_share'])} | {fmt_pct(td['remove_share'])} | "
        f"{fmt_pct(all_m['user_keep_rate']['mean'])} | {fmt_pct(all_m['user_remove_rate']['mean'])} | "
        f"{fmt_int(all_m['always_keep'])} | {fmt_int(all_m['always_remove'])} |"
    )

    tox_lines = [
        "| Party | Toxicity | Trials | Remove share |",
        "| ----- | -------- | -----: | -----------: |",
    ]
    for row in payload["remove_rate_by_toxicity"]:
        tox_lines.append(
            f"| {PARTY_LABELS[row['party']]} | {TOXICITY_LABELS[row['sample_toxicity_type']]} | "
            f"{fmt_int(row['n_trials'])} | {fmt_pct(row['remove_share'])} |"
        )

    stance_lines = [
        "| Party | Original stance | Trials | Remove share |",
        "| ----- | --------------- | -----: | -----------: |",
    ]
    for row in payload["remove_rate_by_stance"]:
        stance_lines.append(
            f"| {PARTY_LABELS[row['party']]} | {STANCE_LABELS[row['sampled_stance']]} | "
            f"{fmt_int(row['n_trials'])} | {fmt_pct(row['remove_share'])} |"
        )

    cell_lines = [
        "| Cell | Mix | Labels now | Assignment slots | Progress |",
        "| ---- | --- | ---------: | ---------------: | -------: |",
    ]
    for row in payload["cell_coverage"]:
        cell_lines.append(
            f"| {row['cell']} | {CELL_LABELS[row['cell']]} | {fmt_int(row['n_labels'])} | "
            f"{fmt_int(row['target_slots'])} | {fmt_pct(row['progress'])} |"
        )

    keep = all_m["user_keep_rate"]
    remove = all_m["user_remove_rate"]
    pace = payload.get("assignment_pace") or {}
    d = by_party[PARTY_ORDER[0]]
    r = by_party[PARTY_ORDER[1]]

    mix_lines = [
        "| Party | Toxicity | Trials | Share of party trials |",
        "| ----- | -------- | -----: | --------------------: |",
    ]
    for row in payload.get("toxicity_mix", []):
        mix_lines.append(
            f"| {PARTY_LABELS[row['party']]} | {TOXICITY_LABELS[row['sample_toxicity_type']]} | "
            f"{fmt_int(row['n_trials'])} | {fmt_pct(row['share'])} |"
        )

    return f"""# Study progress, September 2026 run

Snapshot {payload['generated_at']} UTC. Export {export['timestamp']}.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | {fmt_int(progress['assigned_valid'])} |
| Finished | {fmt_int(progress['completers'])} |
| Saved files | {fmt_int(export['files'])} |
| Labels | {fmt_int(progress['labels'])} |
| Target feeds | {fmt_int(study['target_users'])} |
| Target labels | {fmt_int(study['target_labels'])} |
| User progress | {fmt_pct(progress['user_progress'])} |
| Label progress | {fmt_pct(progress['label_progress'])} |
| Missing from export | {fmt_int(progress['missing_from_export'])} |
| Missing after {progress['grace_minutes']}-minute grace | {fmt_int(progress['missing_after_grace'])} |
| Attrition after grace | {fmt_pct(progress['attrition_rate_after_grace'])} |

Prolific has finished {fmt_int(progress['completers'])} of {fmt_int(study['target_users'])} feeds ({fmt_pct(progress['user_progress'])}). Prolific has assigned a larger share of Democrat slots ({fmt_pct(d['assigned'] / d['target_slots'] if d['target_slots'] else None)} assigned vs {fmt_pct(r['assigned'] / r['target_slots'] if r['target_slots'] else None)} Republican). The busiest assignment hour is {pace.get('busiest_hour') or 'n/a'}, and assignments in the three busiest hours are {fmt_pct(pace.get('top3_share'))} of assigned people.

## Party

{chr(10).join(party_lines)}

## Keep and remove

{chr(10).join(decision_lines)}

Per-user keep rate (all finished): mean {fmt_pct(keep['mean'])}, median {fmt_pct(keep['p50'])}, SD {fmt_pct(keep['std'])}.

Per-user remove rate (all finished): mean {fmt_pct(remove['mean'])}, median {fmt_pct(remove['p50'])}, SD {fmt_pct(remove['std'])}.

{fmt_int(all_m['always_keep'])} people kept every scored post. {fmt_int(all_m['always_remove'])} people removed every scored post.

## Toxicity

{chr(10).join(tox_lines)}

Pooled Democrat remove is {fmt_pct(d['trial_decisions']['remove_share'])} vs Republican {fmt_pct(r['trial_decisions']['remove_share'])}. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

{chr(10).join(mix_lines)}

## Stance

{chr(10).join(stance_lines)}

## Attention

Pass rate {fmt_pct(all_m['attention_pass_rate'])} ({fmt_int(all_m['attention_passed'])} passed, {fmt_int(all_m['attention_failed'])} failed).

Remove share among people who passed: {fmt_pct(att['passed']['remove_share'])}. Among people who failed: {fmt_pct(att['failed']['remove_share'])}.

{fmt_int(all_m.get('always_keep_passed'))} of {fmt_int(all_m['always_keep'])} always-keep finishers passed the attention check.

User-mean remove among people who passed: {fmt_pct(all_m.get('passed_user_remove_rate', {}).get('mean'))}. Democrat passers {fmt_pct(d.get('passed_user_remove_rate', {}).get('mean'))}. Republican passers {fmt_pct(r.get('passed_user_remove_rate', {}).get('mean'))}.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | {fmt_int(cov['unique_posts_labeled'])} |
| Catalog posts | {fmt_int(cov['target_posts'])} |
| Posts with 1 label | {fmt_int(cov['posts_with_1_label'])} |
| Posts with 2 labels | {fmt_int(cov['posts_with_2_labels'])} |
| Posts with 3 or more | {fmt_int(cov['posts_with_3_or_more'])} |

{chr(10).join(cell_lines)}

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean {fmt_num(all_m['influence']['mean'])} on a 1 to 7 scale. Median session {fmt_num(all_m['session_minutes']['p50'])} minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
"""
