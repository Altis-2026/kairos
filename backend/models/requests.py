"""Pydantic request models for every Kairos API endpoint."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator, model_validator


def _validate_date(value: str, field: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"{field} must be in YYYY-MM-DD format, got '{value}'")
    return value


class AnalyzeRequest(BaseModel):
    """POST /analyze"""

    analysis_type: str
    bbox: List[float]          # [min_lon, min_lat, max_lon, max_lat]
    start_date: str            # YYYY-MM-DD
    end_date: str              # YYYY-MM-DD

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        if len(v) != 4:
            raise ValueError(
                "bbox must have exactly 4 values: [min_lon, min_lat, max_lon, max_lat]"
            )
        min_lon, min_lat, max_lon, max_lat = v
        if min_lon >= max_lon:
            raise ValueError("min_lon must be less than max_lon")
        if min_lat >= max_lat:
            raise ValueError("min_lat must be less than max_lat")
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("longitude values must be between -180 and 180")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("latitude values must be between -90 and 90")
        return v

    @field_validator("start_date")
    @classmethod
    def validate_start(cls, v):
        return _validate_date(v, "start_date")

    @field_validator("end_date")
    @classmethod
    def validate_end(cls, v):
        return _validate_date(v, "end_date")

    @model_validator(mode="after")
    def validate_date_order(self):
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class QueryRequest(BaseModel):
    """POST /query — natural language input"""

    query: str
    # Optional viewport context so "this area" resolves to what the user sees
    viewport_bbox: Optional[List[float]] = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        if len(v) > 2000:
            raise ValueError("query must be under 2000 characters")
        return v.strip()
