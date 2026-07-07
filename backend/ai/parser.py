import json
import re
from typing import List, Optional
from pydantic import BaseModel, field_validator


def _check_bbox(v):
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


class ExtraAnalysis(BaseModel):

    analysis_type: str
    bbox: Optional[List[float]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _check_bbox(v)


class ParsedQuery(BaseModel):

    understood: bool
    analysis_type: Optional[str] = None
    location_name: Optional[str] = None
    bbox: Optional[List[float]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    extra_analyses: Optional[List[ExtraAnalysis]] = None
    clarification: Optional[str] = None
    reasoning: Optional[str] = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _check_bbox(v)

    @field_validator("extra_analyses")
    @classmethod
    def cap_extras(cls, v):
        if v and len(v) > 2:
            return v[:2]
        return v


def extract_json(text: str) -> dict:
    cleaned = text.strip()

    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"No JSON object found in model response: {text[:200]}")
        return json.loads(cleaned[start : end + 1])


def parse_query_response(text: str) -> ParsedQuery:
    data = extract_json(text)
    return ParsedQuery(**data)
