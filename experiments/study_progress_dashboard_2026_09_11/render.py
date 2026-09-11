"""Render the study progress dashboard HTML from an aggregated payload."""

from __future__ import annotations

from typing import Any

from experiments.study_progress_dashboard_2026_09_11.constants import (
    CELL_LABELS,
    PARTY_DEMOCRAT,
    PARTY_LABELS,
    PARTY_ORDER,
    PARTY_REPUBLICAN,
    STANCE_LABELS,
    TOXICITY_LABELS,
)


def fmt_int(value: object) -> str:
    """Format a count with thousands separators."""
    if value is None:
        return "n/a"
    return f"{int(value):,}"


def fmt_pct(value: object, digits: int = 1) -> str:
    """Format a 0-1 rate as a percentage."""
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.{digits}f}%"


def fmt_num(value: object, digits: int = 1) -> str:
    """Format a float, or n/a when missing."""
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def _party_name(party: str) -> str:
    return PARTY_LABELS.get(party, party)


def _plural(n: object, singular: str, plural: str) -> str:
    count = 0 if value_is_missing(n) else int(n)
    word = singular if count == 1 else plural
    return f"{fmt_int(count)} {word}"


def value_is_missing(value: object) -> bool:
    return value is None


def _td(value: str, numeric: bool = False) -> str:
    cls = ' class="num"' if numeric else ""
    return f"<td{cls}>{value}</td>"


def _table(headers: list[str], rows: list[list[str]], numeric: set[int] | None = None) -> str:
    numeric = numeric or set()
    head = "".join(f"<th{(' class=\"num\"' if i in numeric else '')}>{h}</th>" for i, h in enumerate(headers))
    body_rows = []
    for row in rows:
        cells = "".join(_td(cell, i in numeric) for i, cell in enumerate(row))
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _summary(stats: dict[str, Any], *, as_pct: bool = False, digits: int = 1) -> str:
    fmt = (lambda v: fmt_pct(v, digits)) if as_pct else (lambda v: fmt_num(v, digits))
    return _table(
        ["Mean", "SD", "Min", "P25", "Median", "P75", "Max", "People"],
        [
            [
                fmt(stats.get("mean")),
                fmt(stats.get("std")),
                fmt(stats.get("min")),
                fmt(stats.get("p25")),
                fmt(stats.get("p50")),
                fmt(stats.get("p75")),
                fmt(stats.get("max")),
                fmt_int(stats.get("n")),
            ]
        ],
        numeric=set(range(8)),
    )


def _progress_bar(share: float | None, color: str = "var(--accent)") -> str:
    pct = 0.0 if share is None else max(0.0, min(1.0, float(share))) * 100
    return (
        f'<div class="bar-track"><span style="width:{pct:.1f}%;background:{color}"></span>'
        f'<em>{fmt_pct(share)}</em></div>'
    )


def _hist_html(all_bins: list[dict[str, Any]], by_party: dict[str, list[dict[str, Any]]]) -> str:
    d_bins = {row["bin"]: row for row in by_party[PARTY_DEMOCRAT]}
    r_bins = {row["bin"]: row for row in by_party[PARTY_REPUBLICAN]}
    max_share = 0.0
    for row in all_bins:
        max_share = max(max_share, float(row.get("share") or 0))
        max_share = max(max_share, float(d_bins.get(row["bin"], {}).get("share") or 0))
        max_share = max(max_share, float(r_bins.get(row["bin"], {}).get("share") or 0))
    if max_share <= 0:
        max_share = 1.0
    cols = []
    for row in all_bins:
        label = row["bin"]
        d_share = float(d_bins.get(label, {}).get("share") or 0)
        r_share = float(r_bins.get(label, {}).get("share") or 0)
        d_count = int(d_bins.get(label, {}).get("count") or 0)
        r_count = int(r_bins.get(label, {}).get("count") or 0)
        cols.append(
            "<div class=\"bin\">"
            f'<div class="bars">'
            f'<div class="bar dem" style="height:{d_share / max_share * 100:.1f}%" title="Democrat {d_count}"></div>'
            f'<div class="bar rep" style="height:{r_share / max_share * 100:.1f}%" title="Republican {r_count}"></div>'
            "</div>"
            f'<div class="bin-label">{label}</div>'
            f'<div class="bin-count">{d_count} / {r_count}</div>'
            "</div>"
        )
    return (
        '<div class="hist-wrap">'
        '<div class="hist-legend">'
        '<span class="item"><span class="swatch dem"></span>Democrat share of Democrat finishers</span>'
        '<span class="item"><span class="swatch rep"></span>Republican share of Republican finishers</span>'
        "</div>"
        f'<div class="hist">{"".join(cols)}</div>'
        "</div>"
    )


def _hour_label(hour: str) -> str:
    text = str(hour).replace(" UTC", "")
    if len(text) >= 16:
        return text[5:16]
    if len(text) >= 13:
        return text[5:13]
    return text


def _hour_chart(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class=\"muted\">No assignment timestamps yet.</p>"
    max_count = max(int(r[PARTY_DEMOCRAT]) + int(r[PARTY_REPUBLICAN]) for r in rows)
    if max_count <= 0:
        max_count = 1
    bars = []
    for row in rows:
        d = int(row[PARTY_DEMOCRAT])
        r = int(row[PARTY_REPUBLICAN])
        total = d + r
        bars.append(
            "<div class=\"hour\">"
            f'<div class="hour-label">{_hour_label(str(row["hour"]))}</div>'
            '<div class="hour-bars">'
            f'<span class="dem" style="width:{d / max_count * 100:.1f}%"></span>'
            f'<span class="rep" style="width:{r / max_count * 100:.1f}%"></span>'
            "</div>"
            f'<div class="hour-n">{total}</div>'
            "</div>"
        )
    return f'<div class="hours">{"".join(bars)}</div>'


def render_html(payload: dict[str, Any]) -> str:
    """Return a self-contained HTML dashboard for the aggregated payload."""
    study = payload["study"]
    progress = payload["progress"]
    export = payload["export"]
    all_m = payload["all"]
    by_party = payload["by_party"]
    d = by_party[PARTY_DEMOCRAT]
    r = by_party[PARTY_REPUBLICAN]
    pace = payload.get("assignment_pace") or {}
    att = payload["attention_remove_share"]
    cov = payload["post_coverage"]

    party_progress_rows = []
    for party in PARTY_ORDER:
        m = by_party[party]
        party_progress_rows.append(
            [
                _party_name(party),
                fmt_int(m["assigned"]),
                fmt_int(m["n_completers"]),
                fmt_int(m["target_slots"]),
                fmt_pct(m["assigned"] / m["target_slots"] if m["target_slots"] else None),
                fmt_pct(m["n_completers"] / m["assigned"] if m["assigned"] else None),
            ]
        )

    affiliation_rows = []
    for party in PARTY_ORDER:
        aff = by_party[party]["affiliation"]
        affiliation_rows.append(
            [
                _party_name(party),
                fmt_int(aff["democrat"]),
                fmt_int(aff["republican"]),
                fmt_int(aff["other"]),
                fmt_int(by_party[party]["n_completers"]),
            ]
        )

    decision_rows = []
    for party in PARTY_ORDER:
        m = by_party[party]
        td = m["trial_decisions"]
        decision_rows.append(
            [
                _party_name(party),
                fmt_int(td["n_keep"]),
                fmt_int(td["n_remove"]),
                fmt_int(td["n_trials"]),
                fmt_pct(td["keep_share"]),
                fmt_pct(td["remove_share"]),
                fmt_pct(m["user_keep_rate"]["mean"]),
                fmt_pct(m["user_remove_rate"]["mean"]),
                fmt_int(m["always_keep"]),
                fmt_int(m["always_remove"]),
            ]
        )
    td_all = all_m["trial_decisions"]
    decision_rows.append(
        [
            "All",
            fmt_int(td_all["n_keep"]),
            fmt_int(td_all["n_remove"]),
            fmt_int(td_all["n_trials"]),
            fmt_pct(td_all["keep_share"]),
            fmt_pct(td_all["remove_share"]),
            fmt_pct(all_m["user_keep_rate"]["mean"]),
            fmt_pct(all_m["user_remove_rate"]["mean"]),
            fmt_int(all_m["always_keep"]),
            fmt_int(all_m["always_remove"]),
        ]
    )

    tox_rows = []
    for row in payload["remove_rate_by_toxicity"]:
        tox_rows.append(
            [
                _party_name(row["party"]),
                TOXICITY_LABELS.get(row["sample_toxicity_type"], row["sample_toxicity_type"]),
                fmt_int(row["n_trials"]),
                fmt_int(row["n_keep"]),
                fmt_int(row["n_remove"]),
                fmt_pct(row["remove_share"]),
            ]
        )

    mix_rows = []
    for row in payload.get("toxicity_mix", []):
        mix_rows.append(
            [
                _party_name(row["party"]),
                TOXICITY_LABELS.get(row["sample_toxicity_type"], row["sample_toxicity_type"]),
                fmt_int(row["n_trials"]),
                fmt_pct(row["share"]),
            ]
        )

    stance_rows = []
    for row in payload["remove_rate_by_stance"]:
        stance_rows.append(
            [
                _party_name(row["party"]),
                STANCE_LABELS.get(row["sampled_stance"], row["sampled_stance"]),
                fmt_int(row["n_trials"]),
                fmt_int(row["n_keep"]),
                fmt_int(row["n_remove"]),
                fmt_pct(row["remove_share"]),
            ]
        )

    fine_rows = []
    for row in payload["remove_rate_by_party_stance_toxicity"]:
        fine_rows.append(
            [
                _party_name(row["party"]),
                STANCE_LABELS.get(row["sampled_stance"], row["sampled_stance"]),
                TOXICITY_LABELS.get(row["sample_toxicity_type"], row["sample_toxicity_type"]),
                fmt_int(row["n_trials"]),
                fmt_pct(row["remove_share"]),
            ]
        )

    cell_rows = []
    for row in payload["cell_coverage"]:
        cell_rows.append(
            [
                str(row["cell"]),
                CELL_LABELS.get(row["cell"], str(row["cell"])),
                fmt_int(row["n_labels"]),
                fmt_int(row["target_slots"]),
                fmt_pct(row["progress"]),
            ]
        )

    gender_rows = []
    genders = sorted(set(all_m["gender"]) | set(d["gender"]) | set(r["gender"]))
    for gender in genders:
        gender_rows.append(
            [
                gender,
                fmt_int(d["gender"].get(gender, 0)),
                fmt_int(r["gender"].get(gender, 0)),
                fmt_int(all_m["gender"].get(gender, 0)),
            ]
        )

    edu_rows = []
    edus = sorted(set(all_m["education"]) | set(d["education"]) | set(r["education"]))
    for edu in edus:
        edu_rows.append(
            [
                edu,
                fmt_int(d["education"].get(edu, 0)),
                fmt_int(r["education"].get(edu, 0)),
                fmt_int(all_m["education"].get(edu, 0)),
            ]
        )

    keep_hist = _hist_html(
        all_m["keep_rate_histogram"],
        {
            PARTY_DEMOCRAT: d["keep_rate_histogram"],
            PARTY_REPUBLICAN: r["keep_rate_histogram"],
        },
    )
    remove_hist = _hist_html(
        all_m["remove_rate_histogram"],
        {
            PARTY_DEMOCRAT: d["remove_rate_histogram"],
            PARTY_REPUBLICAN: r["remove_rate_histogram"],
        },
    )

    busiest_hour = pace.get("busiest_hour")
    busiest_label = _hour_label(str(busiest_hour)) if busiest_hour else "n/a"
    labels_per_post = cov.get("labels_per_post") or {}

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MirrorView September 2026 study progress</title>
  <style>
    :root {{
      --bg: #0f1419;
      --panel: #1a222c;
      --panel-2: #222c38;
      --line: #314155;
      --text: #e8eef5;
      --muted: #9aabc0;
      --accent: #7ab8ff;
      --ok: #3dd68c;
      --bad: #ff6b7a;
      --dem: #6ea8ff;
      --rep: #ff9b6b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    header, main, footer {{ max-width: 1120px; margin: 0 auto; padding: 1.25rem; }}
    header h1 {{ margin: 0 0 0.35rem; font-size: 1.45rem; }}
    header p, .muted, footer {{ color: var(--muted); }}
    nav {{
      display: flex; flex-wrap: wrap; gap: 0.5rem 0.85rem;
      margin: 0.9rem 0 0; font-size: 0.9rem;
    }}
    nav a {{ color: var(--accent); text-decoration: none; }}
    nav a:hover {{ text-decoration: underline; }}
    h2 {{ font-size: 1.15rem; margin: 1.6rem 0 0.5rem; font-weight: 650; }}
    h3 {{ font-size: 1rem; margin: 1.1rem 0 0.4rem; font-weight: 600; }}
    p {{ margin: 0.45rem 0 0.7rem; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 0.75rem;
    }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 0.85rem 1rem;
    }}
    .card .label {{ color: var(--muted); font-size: 0.8rem; }}
    .card .value {{ font-size: 1.35rem; font-weight: 650; margin-top: 0.15rem; }}
    .card .sub {{ color: var(--muted); font-size: 0.8rem; margin-top: 0.2rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ text-align: left; padding: 0.42rem 0.4rem; border-bottom: 1px solid var(--line); }}
    th {{ color: var(--muted); font-weight: 600; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .bar-track {{
      position: relative; height: 18px; background: var(--panel-2);
      border-radius: 99px; overflow: hidden; margin: 0.35rem 0 0.7rem;
    }}
    .bar-track span {{ display: block; height: 100%; }}
    .bar-track em {{
      position: absolute; right: 8px; top: 0; font-size: 0.75rem;
      font-style: normal; line-height: 18px; color: var(--text);
    }}
    .hist-wrap {{ margin: 0.5rem 0 1rem; }}
    .hist-legend {{
      color: var(--muted); font-size: 0.85rem; margin-bottom: 0.4rem;
      display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;
    }}
    .hist-legend .item {{ display: flex; align-items: center; gap: 0.35rem; }}
    .swatch {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; }}
    .swatch.dem, .bar.dem, span.dem {{ background: var(--dem); }}
    .swatch.rep, .bar.rep, span.rep {{ background: var(--rep); }}
    .hist {{ display: flex; align-items: flex-end; gap: 0.35rem; height: 190px; }}
    .bin {{ flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; height: 100%; }}
    .bars {{ display: flex; gap: 2px; align-items: flex-end; width: 100%; height: 140px; }}
    .bar {{ flex: 1; border-radius: 3px 3px 0 0; min-height: 1px; }}
    .bin-label {{ font-size: 0.65rem; color: var(--muted); text-align: center; margin-top: 0.25rem; }}
    .bin-count {{ font-size: 0.65rem; color: var(--muted); font-variant-numeric: tabular-nums; }}
    .hours {{ display: flex; flex-direction: column; gap: 0.25rem; }}
    .hour {{ display: grid; grid-template-columns: 120px 1fr 40px; gap: 0.4rem; align-items: center; }}
    .hour-label {{ font-size: 0.78rem; color: var(--muted); font-variant-numeric: tabular-nums; }}
    .hour-bars {{ display: flex; height: 12px; background: var(--panel-2); border-radius: 99px; overflow: hidden; }}
    .hour-bars span {{ display: block; height: 100%; }}
    .hour-n {{ text-align: right; font-variant-numeric: tabular-nums; font-size: 0.8rem; }}
    .note {{
      background: var(--panel-2); border-left: 3px solid var(--accent);
      padding: 0.6rem 0.8rem; border-radius: 8px; margin: 0.7rem 0;
    }}
    ul {{ margin: 0.3rem 0 0.8rem 1.1rem; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.85em; }}
    footer {{ font-size: 0.85rem; padding-bottom: 2rem; }}
  </style>
</head>
<body>
  <header>
    <h1>MirrorView September 2026 study progress</h1>
    <p>Snapshot {payload["generated_at"]} UTC. Iteration <code>{study["iteration_id"]}</code>. Combined export {export["timestamp"]}. {fmt_int(export["files"])} saved files, {fmt_int(export["unique_completers"])} distinct Prolific ids.</p>
    <nav>
      <a href="#progress">Progress</a>
      <a href="#party">Party</a>
      <a href="#keep-remove">Keep and remove</a>
      <a href="#distributions">Per-user rates</a>
      <a href="#toxicity">Toxicity</a>
      <a href="#stance">Stance</a>
      <a href="#attention">Attention</a>
      <a href="#time">Time</a>
      <a href="#demographics">People</a>
      <a href="#coverage">Post coverage</a>
      <a href="#notes">Notes</a>
    </nav>
  </header>
  <main>
    <p>Each finished participant makes 20 linked-fate decisions. Linked fate means the original post and its political mirror share one keep or remove outcome. The assignment file has {fmt_int(study["target_users"])} feeds ({fmt_int(study["target_democrat_slots"])} Democrat, {fmt_int(study["target_republican_slots"])} Republican). The task writes a file when the session finishes, so people still in the task are not in the export.</p>

    <h2 id="progress">Progress</h2>
    <div class="cards">
      <div class="card"><div class="label">Assigned (valid)</div><div class="value">{fmt_int(progress["assigned_valid"])}</div><div class="sub">of {fmt_int(study["target_users"])} feeds</div></div>
      <div class="card"><div class="label">Finished</div><div class="value">{fmt_int(progress["completers"])}</div><div class="sub">{fmt_pct(progress["user_progress"])} of target feeds</div></div>
      <div class="card"><div class="label">Labels this wave</div><div class="value">{fmt_int(progress["labels"])}</div><div class="sub">{fmt_pct(progress["label_progress"])} of {fmt_int(study["target_labels"])}</div></div>
      <div class="card"><div class="label">Missing from export</div><div class="value">{fmt_int(progress["missing_from_export"])}</div><div class="sub">{fmt_pct(progress["attrition_rate_raw"])} of assigned</div></div>
    </div>
    <p>Feeds handed out</p>
    {_progress_bar(progress["assignment_progress"])}
    <p>Finished participants</p>
    {_progress_bar(progress["user_progress"], "var(--ok)")}
    <p>Labels collected</p>
    {_progress_bar(progress["label_progress"], "var(--rep)")}
    <p>{_plural(progress["assignments_in_grace_window"], "assignment falls", "assignments fall")} inside the {progress["grace_minutes"]}-minute grace window before the export timestamp. After dropping the grace-window rows, {fmt_int(progress["missing_after_grace"])} assigned people still have no export file ({fmt_pct(progress["attrition_rate_after_grace"])} of eligible assignments).</p>
    {_hour_chart(payload["assignment_hourly"])}
    <p class="muted">Assignment counts by UTC hour, stacked Democrat then Republican. The busiest hour is {busiest_label} UTC, with {fmt_int(pace.get("busiest_n"))} assignments. Assignments in the three busiest hours are {fmt_pct(pace.get("top3_share"))} of assigned people.</p>

    <h2 id="party">Party breakdown</h2>
    <p>Party here is the study group used for assignment, <code>party_group</code>. People who selected Other and then a lean are counted in the lean party. Prolific is filling Democrat feeds faster than Republican feeds, even though the assignment file is nearly even ({fmt_int(study["target_democrat_slots"])} vs {fmt_int(study["target_republican_slots"])}).</p>
    {_table(
        ["Party", "Assigned", "Finished", "Target feeds", "Assigned / target", "Finished / assigned"],
        party_progress_rows,
        numeric=set([1, 2, 3, 4, 5]),
    )}
    <h3>How people described their party</h3>
    {_table(
        ["Study group", "Self Democrat", "Self Republican", "Other (then leaned)", "Finished"],
        affiliation_rows,
        numeric=set([1, 2, 3, 4]),
    )}

    <h2 id="keep-remove">Keep and remove</h2>
    <p>Trial share is the fraction of all keep or remove decisions. User mean is the unweighted mean of each person's keep or remove rate, which is the right number when you are comparing typical people. {_plural(all_m["always_keep"], "person kept", "people kept")} every scored post, and {_plural(all_m["always_remove"], "person removed", "people removed")} every scored post.</p>
    {_table(
        ["Party", "Keep", "Remove", "Trials", "Trial keep", "Trial remove", "User mean keep", "User mean remove", "Always keep", "Always remove"],
        decision_rows,
        numeric=set(range(1, 10)),
    )}
    <div class="note">Democrat user-mean remove rate is {fmt_pct(d["user_remove_rate"]["mean"])}. Republican user-mean remove rate is {fmt_pct(r["user_remove_rate"]["mean"])}. Democrat feeds currently have more high-toxicity posts, because odd original user ids map to Democrat. The Democrat recipe uses 3 high-toxicity posts per side instead of 2. Once you split by toxicity, the party rates sit close together.</div>
    <h3>User keep rate (all finished people)</h3>
    {_summary(all_m["user_keep_rate"], as_pct=True)}
    <h3>User keep rate by party</h3>
    <p>Democrat</p>
    {_summary(d["user_keep_rate"], as_pct=True)}
    <p>Republican</p>
    {_summary(r["user_keep_rate"], as_pct=True)}
    <h3>User remove rate by party</h3>
    <p>Democrat</p>
    {_summary(d["user_remove_rate"], as_pct=True)}
    <p>Republican</p>
    {_summary(r["user_remove_rate"], as_pct=True)}

    <h2 id="distributions">Per-user keep and remove rate distributions</h2>
    <p>Each bar pair is the share of one party whose personal keep rate, or remove rate, falls in the bin. Height is relative to the largest party share in the chart, so Democrat and Republican remain comparable when the finished counts differ. Counts under each bin are Democrat / Republican. A keep rate of exactly 50% lands in the 40 to 50% bin, because bins are closed on the right.</p>
    <h3>Keep rate per user</h3>
    {keep_hist}
    <h3>Remove rate per user</h3>
    {remove_hist}

    <h2 id="toxicity">Remove rate by toxicity</h2>
    <p>Within a toxicity band, Democrat and Republican remove rates are close. High-toxicity posts are removed about half the time in both groups. Low-toxicity posts are removed about 15 to 17% of the time. Democrat feeds have a larger high-toxicity share, which raises the pooled Democrat remove rate.</p>
    {_table(
        ["Party", "Toxicity", "Trials", "Keep", "Remove", "Remove share"],
        tox_rows,
        numeric=set([2, 3, 4, 5]),
    )}
    <h3>Share of each party's labeled trials by toxicity</h3>
    {_table(
        ["Party", "Toxicity", "Trials", "Share of party trials"],
        mix_rows,
        numeric=set([2, 3]),
    )}

    <h2 id="stance">Remove rate by original-post stance</h2>
    <p>Under linked fate, left originals and right originals should be removed at similar rates if people are applying one rule to the pair. The current sample is close to the one-rule pattern in both parties.</p>
    {_table(
        ["Party", "Original stance", "Trials", "Keep", "Remove", "Remove share"],
        stance_rows,
        numeric=set([2, 3, 4, 5]),
    )}
    <h3>Party, stance, and toxicity</h3>
    <p>Republican high-toxicity cells have fewer trials, so the Republican high-toxicity rates move around more.</p>
    {_table(
        ["Party", "Original stance", "Toxicity", "Trials", "Remove share"],
        fine_rows,
        numeric=set([3, 4]),
    )}

    <h2 id="attention">Attention check</h2>
    <p>The pre-task check asks people to mark which of six sentences are political. Pass requires exactly the four political items. {fmt_int(all_m["attention_failed"])} of {fmt_int(all_m["n_completers"])} finishers failed ({fmt_pct(1 - (all_m["attention_pass_rate"] or 0))}). Failures are more common among Republican finishers ({fmt_pct(1 - (r["attention_pass_rate"] or 0))} vs {fmt_pct(1 - (d["attention_pass_rate"] or 0))} for Democrats).</p>
    {_table(
        ["Party", "Passed", "Failed", "Pass rate"],
        [
            [_party_name(party), fmt_int(by_party[party]["attention_passed"]), fmt_int(by_party[party]["attention_failed"]), fmt_pct(by_party[party]["attention_pass_rate"])]
            for party in PARTY_ORDER
        ]
        + [["All", fmt_int(all_m["attention_passed"]), fmt_int(all_m["attention_failed"]), fmt_pct(all_m["attention_pass_rate"])]],
        numeric=set([1, 2, 3]),
    )}
    {_table(
        ["Attention", "Trials", "Keep", "Remove", "Remove share"],
        [
            ["Passed", fmt_int(att["passed"]["n_trials"]), fmt_int(att["passed"]["n_keep"]), fmt_int(att["passed"]["n_remove"]), fmt_pct(att["passed"]["remove_share"])],
            ["Failed", fmt_int(att["failed"]["n_trials"]), fmt_int(att["failed"]["n_keep"]), fmt_int(att["failed"]["n_remove"]), fmt_pct(att["failed"]["remove_share"])],
        ],
        numeric=set([1, 2, 3, 4]),
    )}
    <p>People who failed the check remove more often ({fmt_pct(att["failed"]["remove_share"])} vs {fmt_pct(att["passed"]["remove_share"])}). User-mean remove among people who passed is {fmt_pct(all_m.get("passed_user_remove_rate", {}).get("mean"))} for the full sample. Democrat passers are at {fmt_pct(d.get("passed_user_remove_rate", {}).get("mean"))}, and Republican passers are at {fmt_pct(r.get("passed_user_remove_rate", {}).get("mean"))}. {fmt_int(all_m.get("always_keep_passed"))} of the {fmt_int(all_m["always_keep"])} always-keep finishers passed the attention check, and {fmt_int(all_m.get("always_keep_failed"))} failed it.</p>

    <h2 id="time">Time and influence</h2>
    <p>Session length is the largest <code>time_elapsed</code> in the file, in minutes. Median decision time is the per-person median of <code>response_time_ms</code> on scored trials. Influence is the 1 to 7 rating for "how much did seeing both versions influence your decisions?"</p>
    <h3>Session minutes</h3>
    <p>All</p>
    {_summary(all_m["session_minutes"], as_pct=False)}
    <p>Democrat</p>
    {_summary(d["session_minutes"], as_pct=False)}
    <p>Republican</p>
    {_summary(r["session_minutes"], as_pct=False)}
    <h3>Median decision time (ms)</h3>
    <p>All</p>
    {_summary(all_m["median_rt_ms"], as_pct=False, digits=0)}
    <p>Democrat</p>
    {_summary(d["median_rt_ms"], as_pct=False, digits=0)}
    <p>Republican</p>
    {_summary(r["median_rt_ms"], as_pct=False, digits=0)}
    <h3>Influence rating (1 to 7)</h3>
    <p>All, mean {fmt_num(all_m["influence"]["mean"])}. Democrat mean {fmt_num(d["influence"]["mean"])}. Republican mean {fmt_num(r["influence"]["mean"])}.</p>
    {_summary(all_m["influence"], as_pct=False)}

    <h2 id="demographics">Who finished</h2>
    <p>Age, gender, and education come from the end-of-study form. Ideology is a 1 to 7 item (1 more liberal, 7 more conservative). The tables describe who finished so far.</p>
    <h3>Age</h3>
    <p>All</p>
    {_summary(all_m["age"], as_pct=False)}
    <p>Democrat</p>
    {_summary(d["age"], as_pct=False)}
    <p>Republican</p>
    {_summary(r["age"], as_pct=False)}
    <h3>Ideology</h3>
    <p>Democrat</p>
    {_summary(d["ideology"], as_pct=False)}
    <p>Republican</p>
    {_summary(r["ideology"], as_pct=False)}
    <h3>Gender</h3>
    {_table(["Gender", "Democrat", "Republican", "All"], gender_rows, numeric=set([1, 2, 3]))}
    <h3>Education</h3>
    {_table(["Education", "Democrat", "Republican", "All"], edu_rows, numeric=set([1, 2, 3]))}

    <h2 id="coverage">Post coverage</h2>
    <p>Finishers have labeled {fmt_int(cov["unique_posts_labeled"])} of {fmt_int(cov["target_posts"])} catalog posts ({fmt_pct((cov["unique_posts_labeled"] or 0) / cov["target_posts"] if cov.get("target_posts") else None)}). Mean labels per labeled post is {fmt_num(labels_per_post.get("mean"), 2)} (median {fmt_num(labels_per_post.get("p50"), 0)}). Most labeled posts have a single label so far. Consensus of 3 agreeing labels is still rare, which is expected this early.</p>
    {_table(
        ["Posts with 1 label", "Posts with 2 labels", "Posts with 3 or more", "Unlabeled this wave"],
        [[
            fmt_int(cov["posts_with_1_label"]),
            fmt_int(cov["posts_with_2_labels"]),
            fmt_int(cov["posts_with_3_or_more"]),
            fmt_int(cov["posts_unlabeled_this_wave"]),
        ]],
        numeric=set([0, 1, 2, 3]),
    )}
    <h3>Labels vs assignment slots by cell</h3>
    {_table(
        ["Cell", "Mix", "Labels now", "Assignment slots", "Progress"],
        cell_rows,
        numeric=set([2, 3, 4]),
    )}
    <p>Every current finisher is on a 10 left / 10 right feed, so left and right cell counts match. Left-only feeds start at original user 3203 and have not been handed out yet.</p>

    <h2 id="notes">Notes</h2>
    <ul>
      <li>{_plural(all_m["n_repeat_submitters"], "Prolific id saved", "Prolific ids saved")} two sessions, so the file count ({fmt_int(export["files"])}) exceeds distinct people ({fmt_int(export["unique_completers"])}). Both sessions are in the label counts. User rates for repeat ids use all of their scored trials.</li>
      <li>Practice trials (no post id) are excluded from keep/remove rates.</li>
      <li>The dashboard has no Prolific ids, post text, or free-response answers.</li>
      <li>Prolific is filling Democrat slots faster than Republican slots. Left-only feeds have not been assigned yet, so the left vs right comparison here is within the 10 left / 10 right linked-fate mix.</li>
      <li>Rerun <code>PYTHONPATH=. uv run python experiments/study_progress_dashboard_2026_09_11/run.py</code> to refresh the snapshot.</li>
    </ul>
  </main>
  <footer>
    Snapshot {payload["generated_at"]}. Regenerated from S3 and DynamoDB. The dashboard is a static file. Refresh by re-running <code>python experiments/study_progress_dashboard_2026_09_11/run.py</code> and committing the new <code>index.html</code>.
  </footer>
</body>
</html>
"""
