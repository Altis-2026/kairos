from fastapi import APIRouter
from gee.registry import registry_as_json

router = APIRouter()


@router.get("/registry")
def get_registry():
    return registry_as_json()
