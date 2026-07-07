from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class HeadlineStat(BaseModel):
    label: str
    value: float
    unit: str


class ContextLayer(BaseModel):

    id: str
    name: str
    tile_url: str
    color: str
    kind: str = "reference"


class AnalysisResult(BaseModel):

    analysis_type: str
    display_name: str
    bbox: List[float]
    start_date: str
    end_date: str
    tile_url: str
    data_date: str
    confidence: float
    headline_stat: HeadlineStat
    context_layers: List[ContextLayer] = []
    stats: Dict[str, Any] = {}


class QueryResponse(BaseModel):

    understood: bool
    clarification: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[AnalysisResult] = None
    explanation: Optional[str] = None


class SceneInfo(BaseModel):

    scene_id: str
    date: str
    orbit_direction: str
    instrument_mode: str
    polarizations: List[str]


class ScenesResponse(BaseModel):
    bbox: List[float]
    start_date: str
    end_date: str
    scene_count: int
    scenes: List[SceneInfo]
