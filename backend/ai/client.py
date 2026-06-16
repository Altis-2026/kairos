import os
from datetime import date
from pathlib import Path
from openai import OpenAI
from ai.parser import ParsedQuery, parse_query_response

MODEL = "anthropic/claude-3-5-haiku"
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

def parse_natural_language(query: str, viewport_bbox: list = None) -> ParsedQuery:
    client = _get_client()
    system = _get_system_prompt()

    context_lines = [f"Today's date: {date.today().isoformat()}"]
    if viewport_bbox:
        context_lines.append(f"viewport_bbox: {viewport_bbox}")
    user_message = "\n".join(context_lines) + f"\n\nUser query: {query}"

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    text = response.choices[0].message.content

    try:
        return parse_query_response(text)
    except Exception as first_error:
        retry = client.chat.completions.create(
            model=MODEL,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
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
    )
    return response.choices[0].message.content.strip()
