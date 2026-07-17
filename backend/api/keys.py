"""
API key management + programmatic-access metering.

  POST   /keys                mint a key (full key shown once)
  GET    /keys?owner=         list key prefixes
  DELETE /keys/{prefix}       revoke
  GET    /keys/usage?owner=   30-day usage summary

Requests to data endpoints may carry `X-API-Key`; a middleware in main.py
resolves it and logs usage per owner. See docs/API.md for the full surface.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import apikeys

router = APIRouter()


class KeyRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    label: str = Field(default="", max_length=80)


@router.post("/keys")
def create_key(req: KeyRequest):
    minted = apikeys.create_key(req.owner, req.label)
    return {
        **minted,
        "note": "Store this key now — it is shown once and only a hash is kept.",
    }


@router.get("/keys")
def list_keys(owner: str = Query(..., min_length=1, max_length=128)):
    return {"keys": apikeys.list_keys(owner)}


@router.delete("/keys/{prefix}")
def revoke_key(prefix: str, owner: str = Query(..., min_length=1, max_length=128)):
    if not apikeys.revoke_key(owner, prefix):
        raise HTTPException(status_code=404, detail="No such key for this owner.")
    return {"revoked": True}


@router.get("/keys/usage")
def usage(
    owner: str = Query(..., min_length=1, max_length=128),
    days: int = Query(default=30, ge=1, le=365),
):
    return apikeys.usage_summary(owner, days)
