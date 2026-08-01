"""
Deterministic answers for Foresight follow-up questions.

The outlook already carries its own numbers, so the common questions ("is that
bad?", "how do you know?", "when does it peak?") can be answered from the data
alone. That makes the AI a nice-to-have rather than a dependency: a missing API
key or an exhausted quota degrades the wording, never the substance.
"""

HAZARD_WORDS = {
    "flood": "flooding",
    "wildfire": "wildfire",
    "drought": "drought",
    "subsidence": "sinking ground",
}

LEVEL_MEANING = {
    "low": (
        "Low means the satellite record shows little history of this hazard "
        "here compared with other places."
    ),
    "moderate": (
        "Moderate means there is a real but limited history of this hazard "
        "here. Worth knowing about, not worth losing sleep over."
    ),
    "high": (
        "High means this hazard shows up often in the record for this area. "
        "It is worth having a plan."
    ),
    "very high": (
        "Very high means this is one of the more exposed places for this "
        "hazard in the satellite record. Preparation matters here."
    ),
}

TOPICS = {
    "score": (
        "bad", "what does", "score mean", "mean?", "meaning", "how serious",
        "worry", "worried", "compare", "average", "normal",
    ),
    "action": (
        "what should i do", "what do i do", "prepare", "preparing", "protect",
        "insurance", "evacuat", "safe", "safer", "next step", "action",
    ),
    "method": (
        "how do you know", "how is this", "how was this", "measure", "data",
        "source", "accurate", "accuracy", "reliable", "trust", "work out",
        "calculated", "computed", "where does",
    ),
    "trend": ("getting worse", "worse", "trend", "over time", "improving", "better"),
    "season": ("when", "month", "season", "time of year", "peak"),
    "why": ("why", "cause", "reason", "driving", "because"),
}


def _classify(question: str) -> str:
    q = question.lower()
    for topic, keys in TOPICS.items():
        if any(k in q for k in keys):
            return topic
    return "summary"


def _place(ctx: dict) -> str:
    return ctx.get("place_name") or "this area"


def _hazard_word(ctx: dict) -> str:
    return HAZARD_WORDS.get(ctx.get("hazard"), "this hazard")


def _score_answer(ctx: dict) -> str:
    level = (ctx.get("level") or "").lower()
    parts = [
        f"The exposure score for {_hazard_word(ctx)} at {_place(ctx)} is "
        f"{ctx.get('score')} out of 100, which Kairos labels {level}.",
        LEVEL_MEANING.get(level, ""),
        "The score comes from how often this hazard actually appears in the "
        "satellite record for this exact area, so it describes measured "
        "history and current exposure. It is not a prediction that something "
        "will happen on a particular day.",
    ]
    return " ".join(p for p in parts if p)


def _action_answer(ctx: dict) -> str:
    return (
        f"Open the 'What to do about it' checklist below the score. It is "
        f"split into what to do before, during and after {_hazard_word(ctx)}, "
        "and the before section is the part worth doing this week. "
        f"With a {(ctx.get('level') or '').lower()} score, the highest-value "
        "steps are usually knowing your route out, checking what your "
        "insurance actually covers, and signing up for your county's "
        "emergency alerts."
    )


def _method_answer(ctx: dict) -> str:
    parts = []
    if ctx.get("method"):
        parts.append(ctx["method"])
    if ctx.get("data_years"):
        parts.append(f"The record used covers {ctx['data_years']}.")
    parts.append(
        "Every number here is computed live from public satellite archives "
        "when you press the button, so anyone can check it against the same "
        "data."
    )
    return " ".join(parts)


def _trend_answer(ctx: dict) -> str:
    if ctx.get("trend_summary"):
        return (
            f"Here is the trend test Kairos ran on the record for {_place(ctx)}: "
            f"{ctx['trend_summary']} Two independent tests are used, and they "
            "only report a trend when it clears the usual statistical "
            "significance bar."
        )
    return (
        f"Kairos did not find enough years of comparable data at {_place(ctx)} "
        "to run a trend test for this hazard, so it does not claim one either "
        "way."
    )


def _season_answer(ctx: dict) -> str:
    peaks = ctx.get("peak_months") or []
    if peaks:
        return (
            f"In the record for {_place(ctx)}, {_hazard_word(ctx)} clusters in "
            f"{', '.join(peaks)}. That is when the historical signal is "
            "strongest, so it is the sensible window to be ready in. It does "
            "not mean other months are impossible."
        )
    return (
        f"The seasonal pattern for {_hazard_word(ctx)} at {_place(ctx)} is "
        "spread through the year rather than concentrated in particular "
        "months, so there is no single season to watch."
    )


def _why_answer(ctx: dict) -> str:
    drivers = ctx.get("drivers") or []
    if drivers:
        return (
            f"The score for {_place(ctx)} comes from these measurements: "
            + " ".join(drivers)
        )
    return _score_answer(ctx)


def _summary_answer(ctx: dict) -> str:
    parts = [_score_answer(ctx)]
    peaks = ctx.get("peak_months") or []
    if peaks:
        parts.append(f"It peaks in {', '.join(peaks)}.")
    if ctx.get("trend_summary"):
        parts.append(ctx["trend_summary"])
    parts.append("The checklist below turns that into things you can actually do.")
    return " ".join(parts)


BUILDERS = {
    "score": _score_answer,
    "action": _action_answer,
    "method": _method_answer,
    "trend": _trend_answer,
    "season": _season_answer,
    "why": _why_answer,
    "summary": _summary_answer,
}


def fallback_answer(ctx: dict) -> str:
    """Answer from the outlook's own numbers when the AI is unavailable."""
    topic = _classify(ctx.get("question") or "")
    return BUILDERS[topic](ctx)
