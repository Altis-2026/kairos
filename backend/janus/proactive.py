import os
import threading
import time

from janus import store

WATCH_INTERVAL_HOURS = float(os.getenv("JANUS_WATCH_INTERVAL_HOURS", "12"))
FIRST_WATCH_DELAY_SECONDS = int(os.getenv("JANUS_WATCH_FIRST_DELAY_SECONDS", "120"))
MAX_PER_CYCLE = int(os.getenv("JANUS_WATCH_MAX_PER_CYCLE", "25"))

_running = threading.Event()


def _latest_pass(bbox: list, since: str) -> str | None:
    import ee

    from gee import common

    geometry = common.bbox_geometry(bbox)
    start = ee.Date(since).advance(1, "day")
    coll = common.s1_collection(geometry).filterDate(
        start, ee.Date(time.strftime("%Y-%m-%d")).advance(1, "day")
    )
    if coll.size().getInfo() == 0:
        return None
    return common.latest_image_date(coll)


def check_project(project: dict) -> bool:
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
            print(f"[janus] watch cycle: {checked} projects, {new_insights} new insights")
        return {"started": True, "checked": checked, "insights": new_insights}
    finally:
        _running.clear()


def check_now(project_id: int) -> dict:
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
