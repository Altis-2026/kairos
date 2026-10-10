import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

router = APIRouter()

_DB = os.path.join(os.path.dirname(__file__), "..", "kairos_portfolios.db")
_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(os.path.abspath(_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _init():
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                sites TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()


class Site(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    bbox: list[float]
    analysis_type: str = "flood_extent"

    @field_validator("bbox")
    @classmethod
    def _bbox(cls, v):
        if len(v) != 4:
            raise ValueError("bbox must be [min_lon, min_lat, max_lon, max_lat]")
        return v


class PortfolioRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    sites: list[Site] = Field(min_length=1, max_length=50)


@router.post("/portfolios")
def create_portfolio(req: PortfolioRequest):
    _init()
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO portfolios (owner, name, sites, created_at) VALUES (?, ?, ?, ?)",
            (
                req.owner,
                req.name,
                json.dumps([s.model_dump() for s in req.sites]),
                time.time(),
            ),
        )
        conn.commit()
        pid = int(cur.lastrowid)
    return {"id": pid, "name": req.name, "site_count": len(req.sites)}


@router.get("/portfolios")
def list_portfolios(owner: str = Query(..., min_length=1, max_length=128)):
    _init()
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, sites, created_at FROM portfolios WHERE owner = ? ORDER BY id DESC",
            (owner,),
        ).fetchall()
    return {
        "portfolios": [
            {
                "id": r["id"],
                "name": r["name"],
                "site_count": len(json.loads(r["sites"])),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    }


def _get(portfolio_id: int, owner: str) -> dict:
    _init()
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No such portfolio.")
    if row["owner"] != owner:
        raise HTTPException(status_code=403, detail="Not your portfolio.")
    return {"id": row["id"], "name": row["name"], "sites": json.loads(row["sites"])}


@router.delete("/portfolios/{portfolio_id}")
def delete_portfolio(portfolio_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    _get(portfolio_id, owner)
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM portfolios WHERE id = ?", (portfolio_id,))
        conn.commit()
    return {"deleted": True}


@router.post("/portfolios/{portfolio_id}/digest")
def digest(portfolio_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    from gee import common

    p = _get(portfolio_id, owner)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    sites_out = []
    for site in p["sites"]:
        entry = {"name": site["name"], "analysis_type": site["analysis_type"]}
        try:
            geometry = common.bbox_geometry(site["bbox"])
            coll = common.s1_collection(geometry).filterDate(start, end)
            count = coll.size().getInfo()
            if count == 0:
                entry.update(scene_count=0, latest_pass=None, fresh=False)
            else:
                latest = common.latest_image_date(coll)
                age_days = (now.date() - datetime.strptime(latest, "%Y-%m-%d").date()).days
                entry.update(
                    scene_count=count,
                    latest_pass=latest,
                    fresh=age_days <= 3,
                )
        except Exception as e:
            entry.update(error=str(e)[:120])
        sites_out.append(entry)

    fresh = [s["name"] for s in sites_out if s.get("fresh")]
    return {
        "portfolio": p["name"],
        "checked_at": now.isoformat(),
        "sites": sites_out,
        "fresh_sites": fresh,
        "summary": (
            f"{len(fresh)} of {len(sites_out)} sites have imagery under 3 days "
            "old. Run full analyses there first."
        ),
    }
