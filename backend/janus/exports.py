"""
Researcher-tool exports (docs/JANUS.md v5).

The reproducibility pack and notebook already document a project in Markdown and
runnable Python. This closes the last mile into the tools researchers actually
finish a paper in:

  * build_latex   — a complete, Overleaf-ready LaTeX article (title, question,
                    study design, a results table, figures via \\includesvg,
                    validation, honest limitations, and a thebibliography). It
                    compiles as-is; the reader drops in the figure SVGs Janus
                    exports alongside.
  * build_bibtex  — a .bib file of the project bibliography (Zotero, Mendeley,
                    BibLaTeX, and the LaTeX export itself).
  * build_ris     — an RIS file of the bibliography (Zotero / Mendeley / EndNote
                    "Import" understand RIS directly).
  * build_gdoc_html — a clean, self-contained HTML document whose headings map
                    onto Google Docs styles, so File → Open (or paste) lands a
                    properly-structured doc, not a wall of text.

All deterministic string building from stored project data — no model call, no
new dependency — so every export is fast and can only describe runs that
actually happened.
"""

from __future__ import annotations

import html
import re
from datetime import date

from janus import store, figures

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
    # ° reads fine in LaTeX as \textdegree when siunitx/textcomp is present; keep
    # it human by substituting the degree word-free symbol.
    return "".join(out).replace("°", r"\textdegree{}")


def _slug(project: dict) -> str:
    # Same slug the figures module and the frontend use, so cross-references
    # (e.g. a LaTeX \includesvg pointing at a downloaded figure) line up.
    return figures.project_slug(project)


def _cite_key(ref: dict, index: int) -> str:
    authors = ref.get("authors") or ""
    first = re.split(r"[,\s]+", authors.strip())[0] if authors.strip() else "ref"
    first = re.sub(r"[^A-Za-z]", "", first) or "ref"
    year = str(ref.get("year") or "").strip() or "nd"
    return f"{first.lower()}{year}_{index}"


# --------------------------------------------------------------------------- #
# LaTeX.
# --------------------------------------------------------------------------- #
def build_latex(project_id: int) -> str:
    project = store.get_project(project_id)
    design = project.get("design") or {}
    runs = figures.collect_runs(project_id)
    vals = figures.collect_validations(project_id)
    biblio = store.get_bibliography(project_id)
    avail = figures.available_figures(project_id)
    slug = _slug(project)

    L: list[str] = []
    add = L.append
    add(r"% Kairos + Janus — Overleaf-ready manuscript.")
    add(r"% Generated " + date.today().isoformat() + r" by Janus, the Kairos research mentor.")
    add(r"% Figures: download the SVGs Janus exports for this project and place")
    add(r"%   them next to this .tex file. Names are referenced below.")
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

    # Abstract-ish research question.
    if project.get("question"):
        add(r"\begin{abstract}")
        add(_tex(project["question"]))
        add(r"\end{abstract}")

    # Introduction / study design.
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

    # Methods (general, honest about the sensor).
    add(r"\section{Methods}")
    add(
        "All analyses were run in Kairos on free Copernicus Sentinel-1 GRD "
        "synthetic-aperture-radar amplitude backscatter (and, where noted, "
        "fused optical or multi-sensor products), computed server-side on "
        "Google Earth Engine. Each detection below is reproducible from the "
        "parameters given."
    )

    # Results table + figures.
    add(r"\section{Results}")
    if runs:
        if "results" in avail:
            add(r"\begin{figure}[h]")
            add(r"  \centering")
            add(r"  \includesvg[width=0.9\textwidth]{" + figures.figure_filename(project, "results").rsplit(".", 1)[0] + r"}")
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
        add(r"  \includesvg[width=0.9\textwidth]{" + figures.figure_filename(project, "study_area").rsplit(".", 1)[0] + r"}")
        add(r"  \caption{Study area and global location.}")
        add(r"\end{figure}")

    # Validation.
    if vals:
        add(r"\section{Validation}")
        if "validation" in avail:
            add(r"\begin{figure}[h]")
            add(r"  \centering")
            add(r"  \includesvg[width=0.8\textwidth]{" + figures.figure_filename(project, "validation").rsplit(".", 1)[0] + r"}")
            add(r"  \caption{Detector skill against independent benchmark events.}")
            add(r"\end{figure}")
        for v in vals:
            parts = []
            for k in ("iou", "precision", "recall", "f1"):
                if v.get(k) is not None:
                    parts.append(f"{k.upper()} {figures._fmt(v[k])}")
            add(
                r"\noindent\textbf{"
                + _tex(v["region"])
                + r":} "
                + _tex(", ".join(parts))
                + r"\\"
            )

    # Limitations.
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

    # Bibliography.
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


# --------------------------------------------------------------------------- #
# Author parsing.
# --------------------------------------------------------------------------- #
def _split_authors(authors: str) -> list[str]:
    """
    Split an author string into individual authors, handling the two formats
    the app actually produces:
      * literature pipeline: comma-separated full names ("John Smith, Alice Doe")
      * manual entry:        "and"-joined, possibly "Last, First" ("Smith, J. and Doe, A.")
    When " and " / " & " is present we treat that as the separator and keep any
    "Last, First" comma inside each name; otherwise we split on commas /
    semicolons.
    """
    if not authors:
        return []
    if re.search(r"\s+and\s+|\s*&\s*", authors):
        parts = re.split(r"\s+and\s+|\s*&\s*", authors)
    else:
        parts = re.split(r"[;,]", authors)
    return [a.strip() for a in parts if a.strip()]


# --------------------------------------------------------------------------- #
# BibTeX.
# --------------------------------------------------------------------------- #
def _bib_authors(authors: str) -> str:
    # BibTeX joins authors with " and ".
    return " and ".join(_split_authors(authors))


def build_bibtex(project_id: int) -> str:
    biblio = store.get_bibliography(project_id)
    if not biblio:
        return "% No references saved in this project yet.\n"
    out = ["% Kairos + Janus bibliography — import into Zotero, Mendeley, or \\input into LaTeX.", ""]
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


# --------------------------------------------------------------------------- #
# RIS (Zotero / Mendeley / EndNote).
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Google Docs-friendly HTML.
# --------------------------------------------------------------------------- #
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
        P.append("<h2>Validation</h2><table><tr><th>Benchmark</th><th>IoU</th>"
                 "<th>Precision</th><th>Recall</th><th>F1</th></tr>")
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
    P.append("<li>SAR amplitude backscatter is a proxy for surface conditions, not a direct measurement; detections carry known false-positive modes.</li>")
    P.append("<li>Confidence scores and uncertainty ranges are model estimates, not formal statistical intervals.</li>")
    P.append("<li>Reproducing a result re-runs against the live Sentinel-1 archive; a reprocessed scene may differ slightly.</li>")
    P.append("</ul>")

    if biblio:
        P.append("<h2>References</h2><ol>")
        for ref in biblio:
            cite = _h(ref.get("title"))
            if ref.get("authors"):
                cite = f"{_h(ref['authors'])} — {cite}"
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


# --------------------------------------------------------------------------- #
# Filenames.
# --------------------------------------------------------------------------- #
def latex_filename(project: dict) -> str:
    return f"kairos-manuscript-{_slug(project)}.tex"


def bibtex_filename(project: dict) -> str:
    return f"kairos-references-{_slug(project)}.bib"


def ris_filename(project: dict) -> str:
    return f"kairos-references-{_slug(project)}.ris"


def gdoc_filename(project: dict) -> str:
    return f"kairos-doc-{_slug(project)}.html"
