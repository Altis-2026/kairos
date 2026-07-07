import os
from datetime import date
from pathlib import Path
from openai import OpenAI
from ai.parser import ParsedQuery, parse_query_response

MODEL = "anthropic/claude-haiku-4.5"
_PROVIDER_PREFS = None
_SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"

_client = None
_system_prompt = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Add it to backend/.env to enable "
                "natural language queries. The sidebar wizard works without it."
            )
        _client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
    return _client

def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return _system_prompt

def _history_messages(history: list = None) -> list:
    if not history:
        return []
    messages = []
    for turn in history:
        role = "assistant" if turn.get("role") == "kairos" else "user"
        content = (turn.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content})
    return messages


def parse_natural_language(
    query: str, viewport_bbox: list = None, history: list = None
) -> ParsedQuery:
    client = _get_client()
    system = _get_system_prompt()

    context_lines = [f"Today's date: {date.today().isoformat()}"]
    if viewport_bbox:
        context_lines.append(f"viewport_bbox: {viewport_bbox}")
    user_message = "\n".join(context_lines) + f"\n\nUser query: {query}"

    prior = _history_messages(history)
    messages = [{"role": "system", "content": system}]
    messages.extend(prior)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1000,
        messages=messages,
        extra_body=_PROVIDER_PREFS,
    )
    text = response.choices[0].message.content

    try:
        return parse_query_response(text)
    except Exception as first_error:
        retry = client.chat.completions.create(
            model=MODEL,
            max_tokens=1000,
            messages=[
                *messages,
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": (
                        f"Your response failed validation: {first_error}. "
                        "Respond again with ONLY the corrected JSON object, "
                        "exactly matching the schema."
                    ),
                },
            ],
            extra_body=_PROVIDER_PREFS,
        )
        return parse_query_response(retry.choices[0].message.content)

def narrate_result(result: dict) -> str:
    import json as _json
    client = _get_client()
    system = _get_system_prompt()

    slim = {k: v for k, v in result.items() if k != "stats"}
    slim["stats"] = {
        k: v
        for k, v in result.get("stats", {}).items()
        if not isinstance(v, (dict, list)) or k == "headline_stat"
    }

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=400,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": "NARRATE: " + _json.dumps(slim, default=str)},
        ],
        extra_body=_PROVIDER_PREFS,
    )
    return response.choices[0].message.content.strip()


_INTERPRET_SYSTEM = (
    "You are Kairos, a satellite radar analyst explaining a finished Sentinel-1 "
    "analysis to a curious non-expert. Write exactly three short markdown "
    "sections with these headers, in order:\n"
    "### What this shows\n### Likely trend\n### Possible causes\n"
    "Ground every statement in the numbers you are given. Sentinel-1 measures "
    "radar backscatter, not water or damage directly, so be honest about "
    "uncertainty and name the common false positives for this analysis type "
    "(for example, ploughed or rain-wet farmland can mimic flooding or surface "
    "change). Never invent specific dates, casualty counts, or news you were not "
    "given. Keep the whole answer under 130 words, calm and clear."
)

_CONTEXT_SYSTEM = (
    "You are Kairos, a careful geospatial research assistant. Use web search to "
    "find real, recent context for a satellite detection. Only state facts you "
    "can support from search results and cite each one inline like [source]. "
    "Never fabricate sources or events. If you find nothing relevant, say so "
    "plainly rather than guessing."
)


def _result_facts(result: dict, method_description: str = "", place_name: str = None) -> str:
    hs = result.get("headline_stat") or {}
    lines = [
        f"Analysis: {result.get('display_name') or result.get('analysis_type')}",
        f"Method: {method_description}" if method_description else "",
        f"Location: {place_name}" if place_name
        else f"Bounding box: {result.get('bbox')}",
        f"Dates analysed: {result.get('start_date')} to {result.get('end_date')}",
        f"Imagery date: {result.get('data_date')}",
        f"Headline result: {hs.get('label')} = {hs.get('value')} {hs.get('unit')}",
        f"Model confidence: {result.get('confidence')}",
    ]
    stats = result.get("stats") or {}
    scalars = {
        k: v for k, v in stats.items() if isinstance(v, (int, float, str, bool))
    }
    if scalars:
        lines.append(
            "Other figures: " + ", ".join(f"{k}={v}" for k, v in scalars.items())
        )
    return "\n".join(line for line in lines if line)


def interpret_result(
    result: dict, method_description: str = "", place_name: str = None
) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        messages=[
            {"role": "system", "content": _INTERPRET_SYSTEM},
            {"role": "user", "content": _result_facts(result, method_description, place_name)},
        ],
        extra_body=_PROVIDER_PREFS,
    )
    return response.choices[0].message.content.strip()


def search_regional_context(result: dict, place_name: str = None) -> str:
    client = _get_client()
    hs = result.get("headline_stat") or {}
    phenomenon = (result.get("display_name") or "the detected change").lower()
    where = place_name or f"the area at bounding box {result.get('bbox')}"
    prompt = (
        f"Using web search, find recent (roughly the last 6 months) news, official "
        f"reports, or environmental trends about {phenomenon} in or near {where}. "
        f"A Sentinel-1 radar analysis there found {hs.get('label')} = "
        f"{hs.get('value')} {hs.get('unit')} around {result.get('data_date')}. "
        "Summarise anything genuinely relevant (official warnings, news coverage, "
        "long-term trends, or local concerns) and cite each source inline like "
        "[source]. If nothing relevant turns up, say so plainly. 160 words max."
    )
    response = client.chat.completions.create(
        model=MODEL + ":online",
        max_tokens=700,
        messages=[
            {"role": "system", "content": _CONTEXT_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        extra_body=_PROVIDER_PREFS,
    )
    return response.choices[0].message.content.strip()


def fallback_interpretation(result: dict, method_description: str = "") -> str:
    hs = result.get("headline_stat") or {}
    label = hs.get("label", "Detection")
    value = hs.get("value", 0)
    unit = hs.get("unit", "")
    name = result.get("display_name") or result.get("analysis_type") or "This analysis"
    conf = result.get("confidence")
    conf_pct = f"{round(conf * 100)}%" if isinstance(conf, (int, float)) else "an estimated"
    trend = (
        "No meaningful change was detected in this window, which can be the real "
        "answer for a quiet period, not a failure."
        if not value
        else f"The radar flagged {value} {unit} of change between "
        f"{result.get('start_date')} and {result.get('end_date')}."
    )
    method = method_description or (
        "Sentinel-1 radar backscatter was compared against a baseline period."
    )
    return (
        f"### What this shows\n{name} measured **{label}: {value} {unit}** from "
        f"Sentinel-1 imagery dated {result.get('data_date')}, with {conf_pct} "
        f"model confidence. {method}\n\n"
        f"### Likely trend\n{trend}\n\n"
        "### Possible causes\nRadar measures surface roughness and moisture, not "
        "the phenomenon directly, so confirm with the Optical overlay before acting. "
        "Agricultural activity, soil moisture and wind can all mimic a real signal. "
        "_(AI provider not configured, this is a rule-based summary.)_"
    )
