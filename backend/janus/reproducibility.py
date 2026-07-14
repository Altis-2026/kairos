"""
Reproducibility pack (docs/JANUS.md §4, v2).

Assembles a project's complete method trail into a Markdown research pack a
student can hand to a teacher or a reviewer: the question, the study design,
every real analysis that was run (with its exact parameters, the imagery date
used, and the headline result), any ground-truth validation, the annotated
bibliography, and reproducible Kairos links so anyone can re-run each step.

The point is defensibility. A reviewer's first question is "how did you get
this number?" and this document answers it, step by step, with links that
reproduce the exact map. Everything is drawn from stored tool events, so the
pack cannot claim a run that did not happen.
"""

import os
from datetime import date

from janus import store

# Where reproducible links point. Set to the deployed frontend origin.
_APP_ORIGIN = os.getenv("FRONTEND_ORIGIN", "https://kairos.altis.earth")


def _case_link(analysis_type: str, bbox: list, start: str, end: str) -> str:
    if not (analysis_type and bbox and start and end):
        return ""
    bbox_str = ",".join(str(round(float(x), 4)) for x in bbox)
    return (
        f"{_APP_ORIGIN}/#task={analysis_type}&bbox={bbox_str}"
        f"&start={start}&end={end}"
    )


def _collect_runs(project_id: int) -> tuple:
    """Pull every analysis / validation run out of the stored tool events."""
    runs, validations = [], []
    for msg in store.get_messages(project_id):
        for ev in msg.get("tool_events") or []:
            if ev.get("tool") == "run_analysis" and ev.get("result"):
                r = ev["result"]
                hs = r.get("headline_stat") or {}
                runs.append(
                    {
                        "analysis_type": r.get("analysis_type"),
                        "display_name": r.get("display_name"),
                        "bbox": r.get("bbox"),
                        "start_date": r.get("start_date"),
                        "end_date": r.get("end_date"),
                        "data_date": r.get("data_date"),
                        "confidence": r.get("confidence"),
                        "headline": f"{hs.get('label')}: {hs.get('value')} {hs.get('unit')}",
                    }
                )
            elif ev.get("tool") == "run_ground_truth_validation" and ev.get(
                "validation"
            ):
                v = ev["validation"]
                validations.append(
                    {
                        "region": (v.get("benchmark") or {}).get("region"),
                        "metrics": v.get("metrics") or {},
                    }
                )
    return runs, validations


def build_pack(project_id: int) -> str:
    """Return the full reproducibility pack as a Markdown string."""
    project = store.get_project(project_id)
    design = project.get("design") or {}
    biblio = store.get_bibliography(project_id)
    runs, validations = _collect_runs(project_id)

    lines = [
        f"# {project['title']}",
        "",
        f"*Kairos + Janus research pack — generated {date.today().isoformat()}*",
        "",
    ]

    if project.get("question"):
        lines += ["## Research question", "", project["question"], ""]

    # --- Study design ---
    lines += ["## Study design", ""]
    if design.get("hypothesis"):
        lines.append(f"- **Hypothesis:** {design['hypothesis']}")
    if design.get("place"):
        lines.append(f"- **Study area:** {design['place']}")
    if design.get("bbox"):
        lines.append(f"- **Bounding box:** {design['bbox']}")
    if design.get("start_date") and design.get("end_date"):
        lines.append(
            f"- **Time window:** {design['start_date']} to {design['end_date']}"
        )
    if design.get("analysis_types"):
        lines.append(f"- **Methods:** {', '.join(design['analysis_types'])}")
    if design.get("confounders"):
        lines.append(
            "- **Confounders considered:** " + "; ".join(design["confounders"])
        )
    if design.get("validation_plan"):
        lines.append(f"- **Validation plan:** {design['validation_plan']}")
    if len(lines) and lines[-1] == "":
        pass
    lines.append("")

    # --- Analyses run ---
    lines += ["## Analyses run", ""]
    if not runs:
        lines += ["_No analyses were run in this project yet._", ""]
    for i, r in enumerate(runs, 1):
        link = _case_link(
            r["analysis_type"], r["bbox"], r["start_date"], r["end_date"]
        )
        lines += [
            f"### {i}. {r['display_name']}",
            "",
            f"- **Result:** {r['headline']}",
            f"- **Model confidence:** {r['confidence']}",
            f"- **Bounding box:** {r['bbox']}",
            f"- **Analysis window:** {r['start_date']} to {r['end_date']}",
            f"- **Sentinel-1 imagery date:** {r['data_date']}",
        ]
        if link:
            lines.append(f"- **Reproduce this exact result:** [{link}]({link})")
        lines.append("")

    # --- Validation ---
    if validations:
        lines += ["## Ground-truth validation", ""]
        for v in validations:
            m = v["metrics"]
            lines += [
                f"### {v['region']}",
                "",
                f"- IoU: {m.get('iou')}",
                f"- Precision: {m.get('precision')}",
                f"- Recall: {m.get('recall')}",
                f"- F1: {m.get('f1')}",
                "",
            ]

    # --- Bibliography ---
    if biblio:
        lines += ["## Bibliography", ""]
        for b in biblio:
            cite = b["title"]
            if b.get("authors"):
                cite = f"{b['authors']} — {cite}"
            if b.get("year"):
                cite += f" ({b['year']})"
            if b.get("venue"):
                cite += f". {b['venue']}"
            lines.append(f"- {cite}")
            if b.get("url"):
                lines.append(f"  - {b['url']}")
            if b.get("note"):
                lines.append(f"  - _{b['note']}_")
        lines.append("")

    # --- Honest limitations footer ---
    lines += [
        "## Method notes and limitations",
        "",
        "- All analyses run on Sentinel-1 GRD amplitude backscatter, a proxy "
        "for surface conditions, not a direct measurement. Detections carry "
        "known false-positive modes (e.g. wet farmland mimicking flood, calm "
        "wind mimicking oil).",
        "- Confidence scores and any uncertainty ranges are model estimates, "
        "not formal statistical intervals.",
        "- Reproducible links re-run the same analysis against the live "
        "Sentinel-1 archive; if ESA reprocesses a scene, a re-run may differ "
        "slightly.",
        "",
        "*Generated by Janus, the Kairos research mentor.*",
    ]

    return "\n".join(lines)


def pack_filename(project: dict) -> str:
    slug = "".join(
        c.lower() if c.isalnum() else "-" for c in project["title"]
    ).strip("-")[:50] or "project"
    return f"kairos-research-pack-{slug}.md"
