"""
Proactive monitoring — the piece that makes Janus feel alive (docs/JANUS.md
"honest risks": proactivity is the highest-leverage 'feels like a real AI'
upgrade).

A student can put a project on WATCH. On a schedule, Janus checks each watched
project for a fresh Sentinel-1 pass over its study area since the last analysis
it ran there. When a new pass lands, it writes a proactive insight the student
sees the next time they open the project: "A new Sentinel-1 pass on <date>
now covers your study area. Want me to re-run <analysis> and compare?"

Deliberately cheap: this only counts scenes and reads the latest scene date
(no full analysis, no getMapId), so watching many projects costs little GEE
time. The expensive re-run only happens if the student says yes. Disabled by
default in local/dev via JANUS_WATCH_ENABLED, exactly like the feed sweeper.
"""

import os
import threading
import time

from janus import store

WATCH_INTERVAL_HOURS = float(os.getenv("JANUS_WATCH_INTERVAL_HOURS", "12"))
FIRST_WATCH_DELAY_SECONDS = int(os.getenv("JANUS_WATCH_FIRST_DELAY_SECONDS", "120"))
MAX_PER_CYCLE = int(os.getenv("JANUS_WATCH_MAX_PER_CYCLE", "25"))

_running = threading.Event()


def _latest_pass(bbox: list, since: str) -> str | None:
    """
    Date (YYYY-MM-DD) of the newest Sentinel-1 scene over bbox strictly after
    `since`, or None. Import GEE lazily so this module loads without EE init.
    """
    import ee
    from gee import common

    geometry = common.bbox_geometry(bbox)
    start = ee.Date(since).advance(1, "day")
    coll = (
        common.s1_collection(geometry)
        .filterDate(start, ee.Date(time.strftime("%Y-%m-%d")).advance(1, "day"))
    )
    if coll.size().getInfo() == 0:
        return None
    return common.latest_image_date(coll)


def check_project(project: dict) -> bool:
    """
    Check one watched project for a new pass. Returns True if a fresh insight
    was written. Needs a recorded last_run (analysis + bbox + data_date) to
    know what to watch and from when.
    """
    last = (project.get("design") or {}).get("last_run")
    if not last or not last.get("bbox") or not last.get("data_date"):
        return False

    try:
        new_date = _latest_pass(last["bbox"], last["data_date"])
    except Exception as e:
        print(f"[janus] watch check failed (project {project['id']}): {e}")
        return False
    if not new_date:
        return False

    name = last.get("display_name") or last.get("analysis_type") or "your analysis"
    content = (
        f"A new Sentinel-1 pass on {new_date} now covers your study area, "
        f"after the {last['data_date']} scene your last {name} used. Want me "
        "to re-run it and compare what changed?"
    )
    action = {
        "type": "rerun_analysis",
        "analysis_type": last.get("analysis_type"),
        "bbox": last.get("bbox"),
        "start_date": last.get("start_date"),
        "end_date": new_date,
        "label": f"Re-run {name} on the {new_date} pass",
    }
    created = store.add_insight(
        project["id"],
        kind="new_pass",
        content=content,
        dedupe_key=f"new_pass:{new_date}",
        action=action,
    )
    if created:
        # Push to the owner's webhook too (Slack/Discord/custom). Never fatal,
        # and only for genuinely new insights so retries can't spam.
        try:
            import notify

            notify.notify_owner(
                project["owner"],
                {
                    "title": f"Kairos: new satellite pass over “{project['title']}”",
                    "summary": content,
                    "project_id": project["id"],
                    "kind": "new_pass",
                    "data_date": new_date,
                },
            )
        except Exception:
            pass
    return created


def run_cycle() -> dict:
    if _running.is_set():
        return {"started": False, "reason": "watch cycle already running"}
    _running.set()
    checked = new_insights = 0
    try:
        for project in store.all_watched_projects()[:MAX_PER_CYCLE]:
            checked += 1
            if check_project(project):
                new_insights += 1
        if checked:
            print(
                f"[janus] watch cycle: {checked} projects, "
                f"{new_insights} new insights"
            )
        return {"started": True, "checked": checked, "insights": new_insights}
    finally:
        _running.clear()


def check_now(project_id: int) -> dict:
    """On-demand check for a single project (the Watch toggle's instant path)."""
    project = store.get_project(project_id)
    created = check_project(project)
    return {"checked": True, "new_insight": created}


def _loop():
    time.sleep(FIRST_WATCH_DELAY_SECONDS)
    while True:
        try:
            run_cycle()
        except Exception as e:
            print(f"[janus] watch loop error: {e}")
        time.sleep(WATCH_INTERVAL_HOURS * 3600)


def start_scheduler():
    if os.getenv("JANUS_WATCH_ENABLED", "1") not in ("1", "true", "yes"):
        print("[janus] proactive watch disabled (JANUS_WATCH_ENABLED)")
        return
    threading.Thread(target=_loop, daemon=True).start()
    print(
        f"[janus] proactive watch scheduled every {WATCH_INTERVAL_HOURS}h, "
        f"first run in {FIRST_WATCH_DELAY_SECONDS}s"
    )
