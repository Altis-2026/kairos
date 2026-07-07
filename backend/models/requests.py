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


def _validate_bbox_values(v):
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


class AnalyzeRequest(BaseModel):
    """POST /analyze (also reused for /research/backscatter and /research/compare)"""

    analysis_type: str
    bbox: List[float]          # [min_lon, min_lat, max_lon, max_lat]
    start_date: str            # YYYY-MM-DD
    end_date: str              # YYYY-MM-DD
    # Optional free-hand polygon ring [[lon, lat], ...]; when present the
    # analysis runs on this exact shape and bbox is just its bounding box.
    polygon: Optional[List[List[float]]] = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _validate_bbox_values(v)

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, v):
        if v is None:
            return v
        if len(v) < 3:
            raise ValueError("polygon needs at least 3 vertices")
        if len(v) > 100:
            raise ValueError("polygon must have 100 vertices or fewer")
        for point in v:
            if len(point) != 2:
                raise ValueError("each polygon vertex must be [lon, lat]")
            lon, lat = point
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError("polygon vertex out of range")
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


class OpticalRequest(BaseModel):
    """POST /research/optical — Sentinel-2 true-color for a window."""

    bbox: List[float]
    start_date: str
    end_date: str

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _validate_bbox_values(v)

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


class ReportRequest(BaseModel):
    """POST /export/report — build a methodology report from a finished result."""

    analysis_type: str
    display_name: str
    bbox: List[float]
    start_date: str
    end_date: str
    data_date: str
    confidence: float
    headline_label: str
    headline_value: float
    headline_unit: str
    stats: Optional[dict] = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _validate_bbox_values(v)

    @field_validator("start_date")
    @classmethod
    def validate_start(cls, v):
        return _validate_date(v, "start_date")

    @field_validator("end_date")
    @classmethod
    def validate_end(cls, v):
        return _validate_date(v, "end_date")


class TimeSeriesRequest(BaseModel):
    """POST /research/timeseries — run an analysis across stepped time windows."""

    analysis_type: str
    bbox: List[float]
    end_date: str              # most recent frame ends here; frames step backward
    steps: int = 6             # number of frames
    interval_days: int = 12    # Sentinel-1 revisit cadence; also each frame's window

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _validate_bbox_values(v)

    @field_validator("end_date")
    @classmethod
    def validate_end(cls, v):
        return _validate_date(v, "end_date")

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v):
        if not (2 <= v <= 8):
            raise ValueError("steps must be between 2 and 8")
        return v

    @field_validator("interval_days")
    @classmethod
    def validate_interval(cls, v):
        if not (6 <= v <= 90):
            raise ValueError("interval_days must be between 6 and 90")
        return v


class AlertCheckRequest(BaseModel):
    """
    POST /alerts/check — has a new Sentinel-1 pass produced a fresh detection
    for a watched area since we last looked? Drives "alert mode".
    """

    analysis_type: str
    bbox: List[float]
    since_date: Optional[str] = None   # latest data_date already seen/notified
    end_date: Optional[str] = None     # window end; defaults to today (UTC)
    lookback_days: int = 24            # ~2 Sentinel-1 revisit cycles

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _validate_bbox_values(v)

    @field_validator("since_date")
    @classmethod
    def validate_since(cls, v):
        return _validate_date(v, "since_date") if v else v

    @field_validator("end_date")
    @classmethod
    def validate_end(cls, v):
        return _validate_date(v, "end_date") if v else v

    @field_validator("lookback_days")
    @classmethod
    def validate_lookback(cls, v):
        if not (6 <= v <= 90):
            raise ValueError("lookback_days must be between 6 and 90")
        return v


class EventsRequest(BaseModel):
    """POST /events/historical — past natural disasters near an area (NASA EONET)."""

    bbox: List[float]
    days: int = 3650           # how far back to look (default ~10 years)
    category: Optional[str] = None  # EONET category id (e.g. 'floods', 'wildfires')
    status: str = "all"        # 'open' (active), 'closed', or 'all'

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _validate_bbox_values(v)

    @field_validator("days")
    @classmethod
    def validate_days(cls, v):
        if not (1 <= v <= 7300):  # cap at ~20 years
            raise ValueError("days must be between 1 and 7300")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in ("open", "closed", "all"):
            raise ValueError("status must be 'open', 'closed' or 'all'")
        return v


class ImpactRequest(BaseModel):
    """POST /impact/population — people & buildings within a detection footprint."""

    analysis_type: str
    bbox: List[float]
    start_date: str
    end_date: str

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _validate_bbox_values(v)

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


class PopulationRequest(BaseModel):
    """POST /research/population — a population-density context tile for a bbox."""

    bbox: List[float]

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _validate_bbox_values(v)


class InterpretRequest(BaseModel):
    """
    POST /interpret and /interpret/context — turn a finished result into a
    plain-language explanation (and optionally live regional context).
    Carries the headline figures so the AI is grounded in real numbers.
    """

    analysis_type: str
    bbox: List[float]
    start_date: str
    end_date: str
    display_name: Optional[str] = None
    place_name: Optional[str] = None
    data_date: Optional[str] = None
    confidence: Optional[float] = None
    headline_label: Optional[str] = None
    headline_value: Optional[float] = None
    headline_unit: Optional[str] = None
    stats: Optional[dict] = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v):
        return _validate_bbox_values(v)

    @field_validator("start_date")
    @classmethod
    def validate_start(cls, v):
        return _validate_date(v, "start_date")

    @field_validator("end_date")
    @classmethod
    def validate_end(cls, v):
        return _validate_date(v, "end_date")


class ConversationTurn(BaseModel):
    """One prior message in the chat thread, sent so the parser has context."""

    role: str            # "user" or "kairos"
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("user", "kairos"):
            raise ValueError("role must be 'user' or 'kairos'")
        return v


class QueryRequest(BaseModel):
    """POST /query — natural language input"""

    query: str
    # Optional viewport context so "this area" resolves to what the user sees
    viewport_bbox: Optional[List[float]] = None
    # Prior turns of the conversation so follow-ups ("now show fires there",
    # "what about last year") resolve against earlier context. Most recent last.
    history: Optional[List[ConversationTurn]] = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        if len(v) > 2000:
            raise ValueError("query must be under 2000 characters")
        return v.strip()

    @field_validator("history")
    @classmethod
    def cap_history(cls, v):
        # Only the recent tail matters for follow-up resolution; keep it bounded.
        if v and len(v) > 12:
            return v[-12:]
        return v
