"""GET /registry — all available analysis types and their metadata."""

from fastapi import APIRouter
from gee.registry import registry_as_json

router = APIRouter()


@router.get("/registry")
def get_registry():
    """
    The frontend sidebar builds its task list from this response.
    Adding an entry to ANALYSIS_REGISTRY automatically appears here.
    """
    return registry_as_json()
