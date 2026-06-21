"""Pydantic response models. FastAPI uses these for serialization + docs."""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class HeadlineStat(BaseModel):
    label: str
    value: float
    unit: str


class ContextLayer(BaseModel):
    """
    A reference layer shipped alongside the main detection result so a single
    query renders the finding *plus* its context (e.g. permanent water under a
    flood result). Rendered as an additional raster layer on the globe.
    """

    id: str
    name: str
    tile_url: str
    color: str
    kind: str = "reference"


class AnalysisResult(BaseModel):
    """Returned by POST /analyze and embedded in POST /query responses."""

    analysis_type: str
    display_name: str
    bbox: List[float]
    start_date: str
    end_date: str
    tile_url: str
    data_date: str
    confidence: float
    headline_stat: HeadlineStat
    # Reference overlays drawn beneath the detection layer (may be empty):
    context_layers: List[ContextLayer] = []
    # Analysis-specific extras (flood_area_km2, vessel_count, vessel_points, ...)
    stats: Dict[str, Any] = {}


class QueryResponse(BaseModel):
    """Returned by POST /query."""

    understood: bool
    # When Claude needs more information instead of running an analysis:
    clarification: Optional[str] = None
    # The parameters Claude extracted (useful for the frontend to display):
    parameters: Optional[Dict[str, Any]] = None
    # The full analysis result, when one was run:
    result: Optional[AnalysisResult] = None
    # Plain-language narrative explanation written by Claude:
    explanation: Optional[str] = None


class SceneInfo(BaseModel):
    """One available Sentinel-1 scene, for the Preview Scenes sidebar step."""

    scene_id: str
    date: str
    orbit_direction: str   # ASCENDING or DESCENDING
    instrument_mode: str
    polarizations: List[str]


class ScenesResponse(BaseModel):
    bbox: List[float]
    start_date: str
    end_date: str
    scene_count: int
    scenes: List[SceneInfo]
