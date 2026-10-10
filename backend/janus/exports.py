from __future__ import annotations

import html
import re
from datetime import date

from janus import figures, store

_LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _tex(s) -> str:
    if s is None:
        return ""
    out = []
    for ch in str(s):
        out.append(_LATEX_SPECIAL.get(ch, ch))
    return "".join(out).replace("°", r"\textdegree{}")


def _slug(project: dict) -> str:
    return figures.project_slug(project)


def _cite_key(ref: dict, index: int) -> str:
    authors = ref.get("authors") or ""
    first = re.split(r"[,\s]+", authors.strip())[0] if authors.strip() else "ref"
    first = re.sub(r"[^A-Za-z]", "", first) or "ref"
    year = str(ref.get("year") or "").strip() or "nd"
    return f"{first.lower()}{year}_{index}"


LATEX_JOURNALS = ("article", "ieee")


def build_latex(project_id: int, journal: str = "article") -> str:
    project = store.get_project(project_id)
    design = project.get("design") or {}
    runs = figures.collect_runs(project_id)
    vals = figures.collect_validations(project_id)
    biblio = store.get_bibliography(project_id)
    avail = figures.available_figures(project_id)
    journal = journal if journal in LATEX_JOURNALS else "article"

    L: list[str] = []
    add = L.append
    add(r"% Kairos + Janus, Overleaf-ready manuscript.")
    add(r"% Generated " + date.today().isoformat() + r" by Janus, the Kairos research mentor.")
    add(r"% Figures: download the SVGs Janus exports for this project and place")
    add(r"%   them next to this .tex file. Names are referenced below.")
    if journal == "ieee":
        add(r"\documentclass[journal]{IEEEtran}")
    else:
        add(r"\documentclass[11pt]{article}")
        add(r"\usepackage[margin=1in]{geometry}")
    add(r"\usepackage{graphicx}")
    add(r"\usepackage{svg}          % renders the Kairos figure SVGs (Overleaf: on)")
    add(r"\usepackage{booktabs}")
    add(r"\usepackage{textcomp}")
    add(r"\usepackage{hyperref}")
    add(r"\usepackage{caption}")
    add(r"\title{" + _tex(project.get("title", "Untitled study")) + r"}")
    add(r"\author{Prepared with Kairos + Janus}")
    add(r"\date{" + date.today().strftime("%B %Y") + r"}")
    add(r"\begin{document}")
    add(r"\maketitle")

    if project.get("question"):
        add(r"\begin{abstract}")
        add(_tex(project["question"]))
        add(r"\end{abstract}")

    add(r"\section{Study design}")
    design_rows = []
    if design.get("hypothesis"):
        design_rows.append(("Hypothesis", design["hypothesis"]))
    if design.get("place"):
        design_rows.append(("Study area", design["place"]))
    if design.get("bbox"):
        design_rows.append(("Bounding box", str(design["bbox"])))
    if design.get("start_date") and design.get("end_date"):
        design_rows.append(("Time window", f"{design['start_date']} to {design['end_date']}"))
    if design.get("analysis_types"):
        design_rows.append(("Methods", ", ".join(design["analysis_types"])))
    if design.get("confounders"):
        design_rows.append(("Confounders considered", "; ".join(design["confounders"])))
    if design.get("validation_plan"):
        design_rows.append(("Validation plan", design["validation_plan"]))
    if design_rows:
        add(r"\begin{itemize}")
        for k, v in design_rows:
            add(r"  \item \textbf{" + _tex(k) + r":} " + _tex(v))
        add(r"\end{itemize}")
    else:
        add(r"\emph{Study design not yet specified.}")

    add(r"\section{Methods}")
    add(
        "All analyses were run in Kairos on free Copernicus Sentinel-1 GRD "
        "synthetic-aperture-radar amplitude backscatter (and, where noted, "
        "fused optical or multi-sensor products), computed server-side on "
        "Google Earth Engine. Each detection below is reproducible from the "
        "parameters given."
    )

    add(r"\section{Results}")
    if runs:
        if "results" in avail:
            add(r"\begin{figure}[h]")
            add(r"  \centering")
            add(
                r"  \includesvg[width=0.9\textwidth]{"
                + figures.figure_filename(project, "results").rsplit(".", 1)[0]
                + r"}"
            )
            add(r"  \caption{Headline results for each analysis run in this project.}")
            add(r"\end{figure}")
        add(r"\begin{table}[h]")
        add(r"  \centering")
        add(r"  \begin{tabular}{llll}")
        add(r"    \toprule")
        add(r"    Analysis & Result & Confidence & Imagery date \\")
        add(r"    \midrule")
        for r in runs:
            val = ""
            if r["value"] is not None:
                val = f"{figures._fmt(r['value'])} {r['unit']}".strip()
            conf = ""
            if r["confidence"] is not None:
                conf = (
                    f"{int(round(r['confidence'] * 100))}\\%"
                    if r["confidence"] <= 1
                    else figures._fmt(r["confidence"])
                )
            add(
                "    "
                + _tex(r["display_name"])
                + " & "
                + _tex(val)
                + " & "
                + conf
                + " & "
                + _tex(r["data_date"] or "")
                + r" \\"
            )
        add(r"    \bottomrule")
        add(r"  \end{tabular}")
        add(r"  \caption{Analyses run in this project, drawn from the Kairos method trail.}")
        add(r"\end{table}")
    else:
        add(r"\emph{No analyses have been run in this project yet.}")

    if "study_area" in avail:
        add(r"\begin{figure}[h]")
        add(r"  \centering")
        add(
            r"  \includesvg[width=0.9\textwidth]{"
            + figures.figure_filename(project, "study_area").rsplit(".", 1)[0]
            + r"}"
        )
        add(r"  \caption{Study area and global location.}")
        add(r"\end{figure}")

    if vals:
        add(r"\section{Validation}")
        if "validation" in avail:
            add(r"\begin{figure}[h]")
            add(r"  \centering")
            add(
                r"  \includesvg[width=0.8\textwidth]{"
                + figures.figure_filename(project, "validation").rsplit(".", 1)[0]
                + r"}"
            )
            add(r"  \caption{Detector skill against independent benchmark events.}")
            add(r"\end{figure}")
        for v in vals:
            parts = []
            for k in ("iou", "precision", "recall", "f1"):
                if v.get(k) is not None:
                    parts.append(f"{k.upper()} {figures._fmt(v[k])}")
            add(r"\noindent\textbf{" + _tex(v["region"]) + r":} " + _tex(", ".join(parts)) + r"\\")

    add(r"\section{Limitations}")
    add(r"\begin{itemize}")
    add(
        r"  \item SAR amplitude backscatter is a proxy for surface conditions, "
        r"not a direct measurement; detections carry known false-positive modes "
        r"(e.g.\ wet farmland resembling flood, calm wind resembling an oil slick)."
    )
    add(
        r"  \item Confidence scores and any uncertainty ranges are model "
        r"estimates, not formal statistical confidence intervals."
    )
    add(
        r"  \item Reproducing a result re-runs against the live Sentinel-1 "
        r"archive; if ESA reprocesses a scene, a re-run may differ slightly."
    )
    add(r"\end{itemize}")

    if biblio:
        add(r"\begin{thebibliography}{99}")
        for i, ref in enumerate(biblio, 1):
            key = _cite_key(ref, i)
            bits = []
            if ref.get("authors"):
                bits.append(_tex(ref["authors"]))
            if ref.get("year"):
                bits.append(f"({_tex(ref['year'])})")
            bits.append(_tex(ref.get("title") or ""))
            if ref.get("venue"):
                bits.append(_tex(ref["venue"]) + ".")
            if ref.get("url"):
                bits.append(r"\url{" + str(ref["url"]) + r"}")
            add(r"  \bibitem{" + key + r"} " + " ".join(bits))
        add(r"\end{thebibliography}")

    add(r"\end{document}")
    return "\n".join(L)


def _split_authors(authors: str) -> list[str]:
    if not authors:
        return []
    if re.search(r"\s+and\s+|\s*&\s*", authors):
        parts = re.split(r"\s+and\s+|\s*&\s*", authors)
    else:
        parts = re.split(r"[;,]", authors)
    return [a.strip() for a in parts if a.strip()]


def _bib_authors(authors: str) -> str:
    return " and ".join(_split_authors(authors))


def build_bibtex(project_id: int) -> str:
    biblio = store.get_bibliography(project_id)
    if not biblio:
        return "% No references saved in this project yet.\n"
    out = ["% Kairos + Janus bibliography, import into Zotero, Mendeley, or \\input into LaTeX.", ""]
    for i, ref in enumerate(biblio, 1):
        key = _cite_key(ref, i)
        entry_type = "article" if ref.get("venue") else "misc"
        out.append(f"@{entry_type}{{{key},")
        out.append(f"  title = {{{ref.get('title') or 'Untitled'}}},")
        if ref.get("authors"):
            out.append(f"  author = {{{_bib_authors(ref['authors'])}}},")
        if ref.get("year"):
            out.append(f"  year = {{{ref['year']}}},")
        if ref.get("venue"):
            out.append(f"  journal = {{{ref['venue']}}},")
        if ref.get("url"):
            out.append(f"  url = {{{ref['url']}}},")
        if ref.get("note"):
            out.append(f"  note = {{{ref['note']}}},")
        out.append("}")
        out.append("")
    return "\n".join(out)


def build_ris(project_id: int) -> str:
    biblio = store.get_bibliography(project_id)
    if not biblio:
        return "TY  - GEN\nTI  - No references saved in this project yet.\nER  - \n"
    out = []
    for ref in biblio:
        out.append("TY  - JOUR" if ref.get("venue") else "TY  - GEN")
        for author in _split_authors(ref.get("authors") or ""):
            out.append(f"AU  - {author}")
        out.append(f"TI  - {ref.get('title') or 'Untitled'}")
        if ref.get("year"):
            out.append(f"PY  - {ref['year']}")
        if ref.get("venue"):
            out.append(f"T2  - {ref['venue']}")
        if ref.get("url"):
            out.append(f"UR  - {ref['url']}")
        if ref.get("note"):
            out.append(f"N1  - {ref['note']}")
        out.append("ER  - ")
        out.append("")
    return "\n".join(out)


def _h(s) -> str:
    return html.escape(str(s or ""))


def build_gdoc_html(project_id: int) -> str:
    project = store.get_project(project_id)
    design = project.get("design") or {}
    runs = figures.collect_runs(project_id)
    vals = figures.collect_validations(project_id)
    biblio = store.get_bibliography(project_id)

    css = (
        "body{font-family:Georgia,'Times New Roman',serif;max-width:7.5in;"
        "margin:0 auto;color:#111;line-height:1.5}"
        "h1{font-size:22pt}h2{font-size:15pt;border-bottom:1px solid #ccc;"
        "padding-bottom:2px;margin-top:22px}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #bbb;padding:6px 10px;text-align:left;font-size:11pt}"
        "th{background:#f0f3f0}.muted{color:#666;font-size:10pt}"
        "ul{margin:6px 0}"
    )
    P = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>{_h(project.get('title'))}</title><style>{css}</style></head><body>",
        f"<h1>{_h(project.get('title', 'Untitled study'))}</h1>",
        f"<p class='muted'>Prepared with Kairos + Janus · {date.today().isoformat()}</p>",
    ]
    if project.get("question"):
        P.append("<h2>Research question</h2>")
        P.append(f"<p>{_h(project['question'])}</p>")

    P.append("<h2>Study design</h2><ul>")
    rows = [
        ("Hypothesis", design.get("hypothesis")),
        ("Study area", design.get("place")),
        ("Bounding box", design.get("bbox")),
        (
            "Time window",
            f"{design.get('start_date')} to {design.get('end_date')}"
            if design.get("start_date") and design.get("end_date")
            else None,
        ),
        ("Methods", ", ".join(design["analysis_types"]) if design.get("analysis_types") else None),
        ("Confounders considered", "; ".join(design["confounders"]) if design.get("confounders") else None),
        ("Validation plan", design.get("validation_plan")),
    ]
    any_row = False
    for k, v in rows:
        if v:
            any_row = True
            P.append(f"<li><b>{_h(k)}:</b> {_h(v)}</li>")
    if not any_row:
        P.append("<li class='muted'>Not yet specified.</li>")
    P.append("</ul>")

    P.append("<h2>Methods</h2>")
    P.append(
        "<p>All analyses were run in Kairos on free Copernicus Sentinel-1 GRD "
        "SAR amplitude backscatter (and, where noted, fused optical or "
        "multi-sensor products), computed server-side on Google Earth Engine. "
        "Each detection below is reproducible from the parameters given.</p>"
    )

    P.append("<h2>Results</h2>")
    if runs:
        P.append("<table><tr><th>Analysis</th><th>Result</th><th>Confidence</th><th>Imagery date</th></tr>")
        for r in runs:
            val = f"{figures._fmt(r['value'])} {r['unit']}".strip() if r["value"] is not None else ""
            conf = ""
            if r["confidence"] is not None:
                conf = (
                    f"{int(round(r['confidence'] * 100))}%"
                    if r["confidence"] <= 1
                    else figures._fmt(r["confidence"])
                )
            P.append(
                f"<tr><td>{_h(r['display_name'])}</td><td>{_h(val)}</td>"
                f"<td>{_h(conf)}</td><td>{_h(r['data_date'] or '')}</td></tr>"
            )
        P.append("</table>")
        P.append(
            "<p class='muted'>Tip: paste the results, study-area, and validation "
            "figures Janus exports (SVG or PNG) directly beneath this table.</p>"
        )
    else:
        P.append("<p class='muted'>No analyses have been run in this project yet.</p>")

    if vals:
        P.append(
            "<h2>Validation</h2><table><tr><th>Benchmark</th><th>IoU</th>"
            "<th>Precision</th><th>Recall</th><th>F1</th></tr>"
        )
        for v in vals:
            P.append(
                "<tr><td>{r}</td><td>{iou}</td><td>{p}</td><td>{re}</td><td>{f1}</td></tr>".format(
                    r=_h(v["region"]),
                    iou=_h(figures._fmt(v["iou"]) if v.get("iou") is not None else ""),
                    p=_h(figures._fmt(v["precision"]) if v.get("precision") is not None else ""),
                    re=_h(figures._fmt(v["recall"]) if v.get("recall") is not None else ""),
                    f1=_h(figures._fmt(v["f1"]) if v.get("f1") is not None else ""),
                )
            )
        P.append("</table>")

    P.append("<h2>Limitations</h2><ul>")
    P.append(
        "<li>SAR amplitude backscatter is a proxy for surface conditions, not a direct measurement; detections carry known false-positive modes.</li>"
    )
    P.append(
        "<li>Confidence scores and uncertainty ranges are model estimates, not formal statistical intervals.</li>"
    )
    P.append(
        "<li>Reproducing a result re-runs against the live Sentinel-1 archive; a reprocessed scene may differ slightly.</li>"
    )
    P.append("</ul>")

    if biblio:
        P.append("<h2>References</h2><ol>")
        for ref in biblio:
            cite = _h(ref.get("title"))
            if ref.get("authors"):
                cite = f"{_h(ref['authors'])}, {cite}"
            if ref.get("year"):
                cite += f" ({_h(ref['year'])})"
            if ref.get("venue"):
                cite += f". {_h(ref['venue'])}"
            line = f"<li>{cite}"
            if ref.get("url"):
                line += f" <a href='{_h(ref['url'])}'>{_h(ref['url'])}</a>"
            line += "</li>"
            P.append(line)
        P.append("</ol>")

    P.append("<p class='muted'>Generated by Janus, the Kairos research mentor.</p>")
    P.append("</body></html>")
    return "\n".join(P)


def latex_filename(project: dict) -> str:
    return f"kairos-manuscript-{_slug(project)}.tex"


def bibtex_filename(project: dict) -> str:
    return f"kairos-references-{_slug(project)}.bib"


def ris_filename(project: dict) -> str:
    return f"kairos-references-{_slug(project)}.ris"


def gdoc_filename(project: dict) -> str:
    return f"kairos-doc-{_slug(project)}.html"


def build_policy_brief_html(project_id: int) -> str:
    project = store.get_project(project_id)
    design = project.get("design") or {}
    runs = figures.collect_runs(project_id)
    vals = figures.collect_validations(project_id)

    css = (
        "body{font-family:Arial,Helvetica,sans-serif;max-width:7.5in;margin:0 auto;"
        "color:#111;line-height:1.5}"
        "h1{font-size:20pt;margin-bottom:2px}"
        ".kicker{color:#0a7d6f;font-weight:bold;letter-spacing:1px;font-size:9pt}"
        ".headline{background:#eef7f5;border-left:4px solid #0a7d6f;padding:12px 16px;"
        "font-size:13pt;margin:14px 0}"
        "h2{font-size:12pt;text-transform:uppercase;letter-spacing:1px;color:#444;"
        "margin-top:20px}"
        ".honesty{background:#fdf6e7;border-left:4px solid #c8871a;padding:10px 14px;"
        "font-size:10pt}"
        ".muted{color:#666;font-size:9pt}"
        "td,th{font-size:10.5pt;padding:4px 10px;border:1px solid #ccc}"
        "table{border-collapse:collapse}"
    )
    P = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>Brief: {_h(project.get('title'))}</title><style>{css}</style></head><body>",
        "<div class='kicker'>SATELLITE EVIDENCE BRIEF · KAIROS</div>",
        f"<h1>{_h(project.get('title', 'Untitled'))}</h1>",
        f"<p class='muted'>{date.today().strftime('%B %d, %Y')} · prepared with Kairos + Janus "
        "· free Copernicus Sentinel satellite data</p>",
    ]

    if runs:
        lead = runs[-1]
        val = (
            f"{figures._fmt(lead['value'])} {lead['unit']}".strip()
            if lead["value"] is not None
            else "see results table"
        )
        conf = ""
        if lead["confidence"] is not None and lead["confidence"] <= 1:
            conf = f" (model confidence {int(round(lead['confidence'] * 100))}%)"
        P.append(
            f"<div class='headline'><b>{_h(lead['label'])}: {_h(val)}</b>{conf}, "
            f"measured from satellite imagery of {_h(design.get('place') or 'the study area')}"
            f" as of {_h(lead['data_date'] or 'the latest pass')}.</div>"
        )
    else:
        P.append(
            "<div class='headline'>No completed measurements yet. This brief "
            "updates automatically once analyses run.</div>"
        )

    P.append("<h2>What was measured</h2>")
    P.append(
        "<p>Radar satellites (Sentinel-1) image this area every 6–12 days, day or "
        "night, through cloud. Kairos compared recent passes against the area's "
        "own historical baseline to detect change on the ground.</p>"
    )
    if runs:
        P.append("<table><tr><th>Measurement</th><th>Result</th><th>Imagery date</th></tr>")
        for r in runs:
            v = f"{figures._fmt(r['value'])} {r['unit']}".strip() if r["value"] is not None else ""
            P.append(
                f"<tr><td>{_h(r['display_name'])}</td><td>{_h(v)}</td>"
                f"<td>{_h(r['data_date'] or '')}</td></tr>"
            )
        P.append("</table>")

    if vals:
        P.append("<h2>How reliable is this?</h2>")
        v = vals[0]
        f1 = v.get("f1")
        P.append(
            "<p>The same method was scored against an independently mapped real "
            f"event ({_h(v['region'])})"
            + (
                f", where it reached an F1 accuracy of {figures._fmt(f1)} (1.0 = perfect)."
                if f1 is not None
                else "."
            )
            + "</p>"
        )

    P.append("<h2>Suggested next steps</h2><ul>")
    P.append("<li>Treat mapped areas as priorities for ground verification, not as ground truth.</li>")
    P.append("<li>Re-run after the next satellite pass (6–12 days) to track change.</li>")
    P.append("<li>Request the full methods report for technical review or funding submissions.</li>")
    P.append("</ul>")

    P.append(
        "<div class='honesty'><b>Honest limits.</b> Radar measures surface "
        "change, not causes; wet ground can resemble flooding and cleared "
        "fields can resemble damage. Confidence percentages are model "
        "estimates, not guarantees. Every number above can be independently "
        "reproduced. The methods trail is attached to this project.</div>"
    )
    P.append("<p class='muted'>Generated by Janus, the Kairos research mentor.</p>")
    P.append("</body></html>")
    return "\n".join(P)


def policy_brief_filename(project: dict) -> str:
    return f"kairos-brief-{_slug(project)}.html"
