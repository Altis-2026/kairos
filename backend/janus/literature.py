"""
Literature search for the Janus mentor — real papers, verifiable, or nothing.

Backed by OpenAlex (free, no API key, covers essentially all of scholarly
publishing including arXiv). The mentor's hard rule is that it may only cite
works returned by this module, so a fabricated citation cannot reach the
student: everything shown carries the DOI/URL OpenAlex itself returned.
"""

import os

import httpx

OPENALEX_URL = "https://api.openalex.org/works"
# OpenAlex asks polite users to identify themselves; gets the faster pool.
_MAILTO = os.getenv("OPENALEX_MAILTO", "altisorbital@gmail.com")


def _reconstruct_abstract(inverted: dict, max_words: int = 80) -> str:
    """OpenAlex stores abstracts as {word: [positions]}; rebuild the text."""
    if not inverted:
        return ""
    positions = []
    for word, indexes in inverted.items():
        for i in indexes:
            positions.append((i, word))
    positions.sort()
    words = [w for _, w in positions[:max_words]]
    text = " ".join(words)
    return text + ("…" if len(positions) > max_words else "")


def search_literature(query: str, year_from: int = None, limit: int = 5) -> list:
    """
    Search scholarly literature. Returns [] on any failure — the mentor is
    instructed to say "I couldn't reach the literature index" rather than
    improvise references.
    """
    params = {
        "search": query,
        "per-page": max(1, min(limit, 10)),
        "sort": "relevance_score:desc",
        "mailto": _MAILTO,
        "select": (
            "title,authorships,publication_year,primary_location,doi,"
            "cited_by_count,abstract_inverted_index"
        ),
    }
    if year_from:
        params["filter"] = f"from_publication_date:{year_from}-01-01"

    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.get(OPENALEX_URL, params=params)
            resp.raise_for_status()
            works = resp.json().get("results", [])
    except Exception:
        return []

    papers = []
    for w in works:
        authorships = w.get("authorships") or []
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in authorships[:4]
            if a.get("author")
        ]
        if len(authorships) > 4:
            authors.append("et al.")
        location = w.get("primary_location") or {}
        source = (location.get("source") or {}).get("display_name")
        papers.append(
            {
                "title": w.get("title") or "Untitled",
                "authors": ", ".join(a for a in authors if a),
                "year": w.get("publication_year"),
                "venue": source,
                "doi": w.get("doi"),
                "cited_by": w.get("cited_by_count", 0),
                "abstract_snippet": _reconstruct_abstract(
                    w.get("abstract_inverted_index")
                ),
            }
        )
    return papers


def _dedupe(papers: list) -> list:
    """Drop duplicate papers across query results, keyed by normalized title."""
    seen, unique = set(), []
    for p in papers:
        key = "".join(c for c in (p.get("title") or "").lower() if c.isalnum())
        if key and key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def systematic_review(queries: list, year_from: int = None, per_query: int = 6) -> dict:
    """
    A small systematic-review pass: run several related queries, pool and
    dedupe the results, and return the corpus sorted by citation impact plus a
    coverage summary. The mentor synthesizes the narrative and gap statement
    from this; every paper here is real and carries its DOI.

    Returns: {queries, paper_count, papers, most_cited, newest}
    """
    pooled = []
    for q in queries[:5]:
        pooled.extend(search_literature(q, year_from=year_from, limit=per_query))
    papers = _dedupe(pooled)
    papers.sort(key=lambda p: (p.get("cited_by") or 0), reverse=True)

    with_year = [p for p in papers if p.get("year")]
    newest = max((p["year"] for p in with_year), default=None)
    oldest = min((p["year"] for p in with_year), default=None)
    return {
        "queries": queries[:5],
        "paper_count": len(papers),
        "papers": papers[:20],
        "most_cited": papers[0] if papers else None,
        "year_span": [oldest, newest] if with_year else None,
    }
