"""
Peer-review report (docs/JANUS.md v3).

Review mode critiques conversationally. This turns the whole project into a
formal, downloadable mock-reviewer report — the kind a journal or a science
fair judge would write. It assembles every fact on record (question, design,
runs, confounder checks, validation, hypotheses, bibliography) and asks the
model to file a structured review against a fixed rubric.

The point is that a student can pressure-test their work before a human ever
sees it. The report never invents results: it is told to reason only from the
facts provided, and to call out MISSING evidence as a weakness rather than
papering over it. Degrades to a deterministic structural checklist when no AI
provider is configured.
"""

import json
from datetime import date

from janus import store

_RUBRIC = (
    "You are an experienced peer reviewer for a remote-sensing journal, writing "
    "a fair but rigorous review of a student's satellite-radar research project. "
    "Reason ONLY from the facts provided; never invent a result, citation, or "
    "number. Treat missing pieces (no validation, no confounder check, no stated "
    "baseline) as weaknesses to name explicitly. Write in Markdown with EXACTLY "
    "these sections, in order:\n"
    "### Summary\nOne paragraph: what the project set out to do and what it found.\n"
    "### Strengths\n'- ' bullets.\n"
    "### Weaknesses and threats to validity\n'- ' bullets. Be specific: baseline "
    "leakage, unaddressed confounders, overclaiming, missing validation, "
    "coarse-vs-fine resolution mismatches.\n"
    "Also press the questions real SAR reviewers ask: Was incidence-angle / "
    "orbit-geometry variation between compared scenes accounted for? What is "
    "the minimum mapping unit, and are quoted areas more precise than 10 m "
    "pixels justify? How are mixed boundary pixels handled? Could layover, "
    "foreshortening or radar shadow contaminate detections in steep terrain? "
    "Is the claimed change statistically distinguishable from speckle and "
    "seasonal variation (a trend test or uncertainty range), or merely "
    "visually different? Are Sentinel-1/PALSAR data properly cited with the "
    "processing level (GRD amplitude, not coherence) stated?\n"
    "### Required revisions\nNumbered, concrete, each doable in Kairos/Janus.\n"
    "### Suggested revisions\nNumbered, optional improvements.\n"
    "### Verdict\nOne of: Accept, Minor revisions, Major revisions, Reject — with "
    "one sentence of justification.\n"
    "Keep it under 450 words. No em dashes."
)


def _facts(project_id: int) -> str:
    project = store.get_project(project_id)
    design = project.get("design") or {}
    lines = [
        f"Title: {project['title']}",
        f"Stage: {project['stage']}",
    ]
    if project.get("question"):
        lines.append(f"Research question: {project['question']}")
    if design:
        lines.append("Study design: " + json.dumps(
            {k: v for k, v in design.items() if k != "last_run"}
        ))

    runs, validations, confounders = [], [], []
    for msg in store.get_messages(project_id):
        for ev in msg.get("tool_events") or []:
            tool = ev.get("tool")
            if tool == "run_analysis" and ev.get("result"):
                r = ev["result"]
                hs = r.get("headline_stat") or {}
                runs.append(
                    f"{r.get('display_name')} over {r.get('bbox')} "
                    f"{r.get('start_date')}..{r.get('end_date')}: "
                    f"{hs.get('label')}={hs.get('value')} {hs.get('unit')}, "
                    f"confidence {r.get('confidence')}, imagery {r.get('data_date')}"
                )
            elif tool == "run_ground_truth_validation" and ev.get("validation"):
                m = (ev["validation"].get("metrics") or {})
                validations.append(
                    f"IoU={m.get('iou')}, precision={m.get('precision')}, "
                    f"recall={m.get('recall')}, F1={m.get('f1')}"
                )
            elif tool == "check_confounders" and ev.get("confounders"):
                c = ev["confounders"]
                confounders.append(
                    f"overall concern {c.get('overall_concern')}: "
                    + "; ".join(f["finding"] for f in c.get("findings", []))
                )

    if runs:
        lines.append("Analyses run:\n- " + "\n- ".join(runs))
    else:
        lines.append("Analyses run: NONE.")
    lines.append(
        "Ground-truth validation: " + ("; ".join(validations) if validations else "NONE.")
    )
    lines.append(
        "Confounder checks: " + ("; ".join(confounders) if confounders else "NONE.")
    )

    hyps = store.get_hypotheses(project_id)
    if hyps:
        lines.append(
            "Hypotheses: "
            + "; ".join(f"[{h['status']}] {h['statement']}" for h in hyps)
        )
    biblio = store.get_bibliography(project_id)
    lines.append(f"References on file: {len(biblio)}.")
    return "\n".join(lines)


def _deterministic(project_id: int) -> str:
    """A structural checklist used when no AI provider is configured."""
    project = store.get_project(project_id)
    design = project.get("design") or {}
    runs = [
        ev
        for msg in store.get_messages(project_id)
        for ev in (msg.get("tool_events") or [])
        if ev.get("tool") == "run_analysis"
    ]
    has_validation = any(
        ev.get("tool") == "run_ground_truth_validation"
        for msg in store.get_messages(project_id)
        for ev in (msg.get("tool_events") or [])
    )
    has_uncertainty = any(
        any(k.endswith("_low_km2") for k in (ev.get("result") or {}))
        for ev in runs
    )
    has_optical_check = any(
        (ev.get("result") or {}).get("optical_agreement_pct") is not None
        for ev in runs
    )
    checks = [
        ("A falsifiable question is stated", bool(project.get("question"))),
        ("A hypothesis is recorded", bool(design.get("hypothesis"))),
        ("An area of interest is defined", bool(design.get("bbox"))),
        ("At least one analysis was run", len(runs) > 0),
        ("Confounders are listed", bool(design.get("confounders"))),
        ("A validation was run against ground truth", has_validation),
        ("A validation plan is written", bool(design.get("validation_plan"))),
        ("Results carry uncertainty ranges, not single numbers", has_uncertainty),
        ("An independent (optical) cross-check was obtained", has_optical_check),
    ]
    lines = [
        f"# Peer-review checklist: {project['title']}",
        f"*Rule-based review, {date.today().isoformat()} "
        "(AI provider not configured for a full narrative review).*",
        "",
        "### Rigor checklist",
        "",
    ]
    passed = 0
    for label, ok in checks:
        lines.append(f"- [{'x' if ok else ' '}] {label}")
        passed += 1 if ok else 0
    verdict = (
        "Accept" if passed == len(checks)
        else "Minor revisions" if passed >= len(checks) - 2
        else "Major revisions"
    )
    lines += ["", f"### Verdict", "", f"{verdict} ({passed}/{len(checks)} checks passed)."]
    return "\n".join(lines)


def build_review(project_id: int) -> str:
    """A full peer-review report as Markdown (model-backed, with a fallback)."""
    import os

    if not os.getenv("OPENROUTER_API_KEY"):
        return _deterministic(project_id)
    try:
        from ai.client import MODEL, _get_client

        # Reviews are high-stakes reasoning: use the deep model.
        deep = "anthropic/claude-sonnet-4.6"
        client = _get_client()
        response = client.chat.completions.create(
            model=deep or MODEL,
            max_tokens=1100,
            messages=[
                {"role": "system", "content": _RUBRIC},
                {"role": "user", "content": _facts(project_id)},
            ],
            extra_body=None,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or _deterministic(project_id)
    except Exception:
        return _deterministic(project_id)


def review_filename(project: dict) -> str:
    slug = "".join(
        c.lower() if c.isalnum() else "-" for c in project["title"]
    ).strip("-")[:50] or "project"
    return f"kairos-peer-review-{slug}.md"
