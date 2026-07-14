"""
Citation formatting for the project bibliography.

Turns the saved references into a formatted, paste-ready reference list in a
chosen style. Deterministic string formatting from the fields already stored
(authors, year, title, venue, url) — no model call, so it is fast and cannot
drift. Styles cover the ones Earth-observation students actually submit in:
APA 7, AGU (the American Geophysical Union house style), and IEEE.
"""

from janus import store

STYLES = ("apa", "agu", "ieee")


def _authors_list(authors: str) -> list:
    if not authors:
        return []
    return [a.strip() for a in authors.replace(" and ", ", ").split(",") if a.strip()]


def _apa(ref: dict) -> str:
    authors = _authors_list(ref.get("authors") or "")
    who = ", ".join(authors) if authors else "Unknown author"
    year = f"({ref['year']})." if ref.get("year") else "(n.d.)."
    title = f" {ref['title']}."
    venue = f" {ref['venue']}." if ref.get("venue") else ""
    url = f" {ref['url']}" if ref.get("url") else ""
    return f"{who} {year}{title}{venue}{url}".strip()


def _agu(ref: dict) -> str:
    # AGU: Authors (Year), Title, Venue, doi.
    authors = _authors_list(ref.get("authors") or "")
    who = ", ".join(authors) if authors else "Unknown author"
    year = f"({ref['year']})," if ref.get("year") else "(n.d.),"
    title = f" {ref['title']},"
    venue = f" {ref['venue']}," if ref.get("venue") else ""
    url = f" {ref['url']}" if ref.get("url") else ""
    return f"{who} {year}{title}{venue}{url}".strip().rstrip(",") + "."


def _ieee(ref: dict, n: int) -> str:
    # IEEE: [n] A. Author, "Title," Venue, year.
    authors = _authors_list(ref.get("authors") or "")
    who = ", ".join(authors) if authors else "Unknown author"
    title = f'"{ref["title"]},"'
    venue = f" {ref['venue']}," if ref.get("venue") else ""
    year = f" {ref['year']}." if ref.get("year") else ""
    url = f" [Online]. Available: {ref['url']}" if ref.get("url") else ""
    return f"[{n}] {who}, {title}{venue}{year}{url}".strip()


def format_bibliography(project_id: int, style: str = "apa") -> dict:
    """Return the project's references formatted in the requested style."""
    style = style.lower()
    if style not in STYLES:
        style = "apa"
    refs = store.get_bibliography(project_id)
    lines = []
    for i, ref in enumerate(refs, 1):
        if style == "apa":
            lines.append(_apa(ref))
        elif style == "agu":
            lines.append(_agu(ref))
        else:
            lines.append(_ieee(ref, i))
    if style != "ieee":
        lines.sort()
    return {"style": style, "count": len(lines), "references": lines}
