"""Parse and validate Claude's structured JSON response for /query."""

import json
import re
from typing import List, Optional
from pydantic import BaseModel, field_validator


class ParsedQuery(BaseModel):
    """The structured parameters Claude extracts from natural language."""

    understood: bool
    analysis_type: Optional[str] = None
    location_name: Optional[str] = None
    bbox: Optional[List[float]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    clarification: Optional[str] = None
    reasoning: Optional[str] = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        if v is None:
            return v
        if len(v) != 4:
            raise ValueError("bbox must have 4 values")
        min_lon, min_lat, max_lon, max_lat = v
        if min_lon >= max_lon or min_lat >= max_lat:
            raise ValueError("bbox ordering invalid")
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("longitude out of range")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("latitude out of range")
        return v


def extract_json(text: str) -> dict:
    """
    Pull a JSON object out of Claude's response, tolerating accidental
    markdown fences or surrounding prose.
    """
    cleaned = text.strip()

    # Strip markdown fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: find the outermost braces
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"No JSON object found in model response: {text[:200]}")
        return json.loads(cleaned[start : end + 1])


def parse_query_response(text: str) -> ParsedQuery:
    """Extract + validate. Raises ValueError on any problem (caller retries)."""
    data = extract_json(text)
    return ParsedQuery(**data)
