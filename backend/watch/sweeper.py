import os
import threading
import time
from datetime import date, timedelta

import httpx

from watch import store
from watch.hotspots import EONET_ANALYSIS, HOTSPOTS, MIN_HEADLINE, WINDOW_DAYS

EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

SWEEP_INTERVAL_HOURS = float(os.getenv("FEED_SWEEP_INTERVAL_HOURS", "6"))
MAX_PER_SWEEP = int(os.getenv("FEED_MAX_PER_SWEEP", "6"))
FIRST_SWEEP_DELAY_SECONDS = int(os.getenv("FEED_FIRST_SWEEP_DELAY_SECONDS", "90"))

_sweeping = threading.Event()
_last_started_at = 0.0


def _iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _window(analysis_type: str) -> tuple:
    days = WINDOW_DAYS.get(analysis_type, 30)
    end = date.today()
    start = end - timedelta(days=days)
    return _iso(start), _iso(end)


def _eonet_targets(limit: int) -> list:
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                EONET_URL, params={"status": "open", "days": 30, "limit": 100}
            )
            resp.raise_for_status()
            events = resp.json().get("events", [])
    except Exception:
        return []

    targets = []
    for ev in events:
        cats = ev.get("categories") or [{}]
        analysis_type = EONET_ANALYSIS.get(cats[0].get("id", ""))
        if not analysis_type:
            continue
        geometry = ev.get("geometry") or []
        if not geometry:
            continue
        coords = geometry[-1].get("coordinates")
        gtype = (geometry[-1].get("type") or "").lower()
        try:
            if gtype == "point":
                lon, lat = float(coords[0]), float(coords[1])
            else:
                ring = coords[0]
                lon = sum(float(p[0]) for p in ring) / len(ring)
                lat = sum(float(p[1]) for p in ring) / len(ring)
        except (TypeError, ValueError, IndexError, ZeroDivisionError):
            continue
        if not (-179 < lon < 179 and -84 < lat < 84):
            continue
        d = 0.4
        targets.append(
            {
                "source": "eonet",
                "source_id": ev.get("id", ""),
                "source_title": ev.get("title", "Unnamed event"),
                "source_link": ev.get("link"),
                "region": ev.get("title", "Unnamed event"),
                "analysis_type": analysis_type,
                "bbox": [
                    round(lon - d, 4),
                    round(lat - d, 4),
                    round(lon + d, 4),
                    round(lat + d, 4),
                ],
            }
        )
        if len(targets) >= limit:
            break
    return targets


def _hotspot_targets(count: int, offset: int) -> list:
    targets = []
    for i in range(count):
        spot = HOTSPOTS[(offset + i) % len(HOTSPOTS)]
        targets.append(
            {
                "source": "watchlist",
                "source_id": spot["id"],
                "source_title": spot["region"],
                "source_link": None,
                "region": spot["region"],
                "analysis_type": spot["analysis_type"],
                "bbox": spot["bbox"],
            }
        )
    return targets


def _fallback_summary(result: dict, region: str) -> str:
    hs = result.get("headline_stat") or {}
    value = hs.get("value", 0)
    unit = hs.get("unit", "")
    label = (hs.get("label") or "detection").lower()
    name = result.get("display_name", "Analysis")
    return (
        f"{name} over {region}: {label} of {value} {unit} measured from the "
        f"Sentinel-1 pass on {result.get('data_date')}."
    ).replace("  ", " ")


def _summarize(result: dict, region: str) -> str:
    try:
        from ai.client import narrate_result

        text = narrate_result(result)
        if text and len(text) < 600:
            return text
    except Exception:
        pass
    return _fallback_summary(result, region)


def run_sweep_once() -> dict:
    global _last_started_at
    if _sweeping.is_set():
        return {"started": False, "reason": "sweep already running"}
    _sweeping.set()
    _last_started_at = time.time()
    sweep_id = store.start_sweep()
    targets_run = 0
    findings_saved = 0
    errors = 0
    try:
        from api.analyze import run_analysis

        eonet_share = max(1, MAX_PER_SWEEP // 2)
        targets = _eonet_targets(eonet_share)
        remaining = MAX_PER_SWEEP - len(targets)
        offset = store.sweep_count() * max(1, remaining)
        targets += _hotspot_targets(remaining, offset)

        for target in targets:
            targets_run += 1
            start_date, end_date = _window(target["analysis_type"])
            try:
                result = run_analysis(
                    analysis_type=target["analysis_type"],
                    bbox=target["bbox"],
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception as e:
                errors += 1
                print(f"[kairos] sweep target failed ({target['region']}): {e}")
                continue

            hs = result.get("headline_stat") or {}
            value = hs.get("value") or 0
            if value < MIN_HEADLINE.get(target["analysis_type"], 0.5):
                continue

            saved = store.save_finding(
                {
                    "dedupe_key": (
                        f"{target['source_id']}:{target['analysis_type']}:"
                        f"{result.get('data_date')}"
                    ),
                    "source": target["source"],
                    "source_title": target["source_title"],
                    "source_link": target["source_link"],
                    "region": target["region"],
                    "analysis_type": target["analysis_type"],
                    "display_name": result.get("display_name", ""),
                    "bbox": target["bbox"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "data_date": result.get("data_date"),
                    "headline_label": hs.get("label"),
                    "headline_value": value,
                    "headline_unit": hs.get("unit"),
                    "confidence": result.get("confidence"),
                    "summary": _summarize(result, target["region"]),
                }
            )
            if saved:
                findings_saved += 1

        print(
            f"[kairos] sweep done: {targets_run} targets, "
            f"{findings_saved} new findings, {errors} errors"
        )
        return {
            "started": True,
            "targets": targets_run,
            "findings": findings_saved,
            "errors": errors,
        }
    finally:
        store.finish_sweep(sweep_id, targets_run, findings_saved, errors)
        _sweeping.clear()


def sweep_status() -> dict:
    last = store.last_sweep()
    next_at = None
    if last and last.get("finished_at"):
        next_at = last["finished_at"] + SWEEP_INTERVAL_HOURS * 3600
    return {
        "sweeping": _sweeping.is_set(),
        "last_sweep": last,
        "next_sweep_at": next_at,
        "interval_hours": SWEEP_INTERVAL_HOURS,
        "finding_count": store.finding_count(),
    }


def trigger_sweep_async() -> dict:
    if _sweeping.is_set():
        return {"started": False, "reason": "sweep already running"}
    thread = threading.Thread(target=run_sweep_once, daemon=True)
    thread.start()
    return {"started": True}


def _loop():
    time.sleep(FIRST_SWEEP_DELAY_SECONDS)
    while True:
        try:
            run_sweep_once()
        except Exception as e:
            print(f"[kairos] sweep loop error: {e}")
        time.sleep(SWEEP_INTERVAL_HOURS * 3600)


def start_scheduler():
    if os.getenv("FEED_SWEEP_ENABLED", "1") not in ("1", "true", "yes"):
        print("[kairos] autonomous sweep disabled (FEED_SWEEP_ENABLED)")
        return
    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    print(
        f"[kairos] autonomous sweep scheduled every {SWEEP_INTERVAL_HOURS}h, "
        f"first run in {FIRST_SWEEP_DELAY_SECONDS}s"
    )
