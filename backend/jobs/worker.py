"""
Background job worker.

Run with:  python -m jobs.worker   (from the backend/ directory, venv active)
Requires a running Redis (REDIS_URL in .env).

The worker initializes GEE itself because it is a separate process
from the API server.
"""

import os

import ee
from dotenv import load_dotenv
from redis import Redis
from rq import Worker, Queue

load_dotenv()


def job_run_analysis(analysis_type: str, bbox: list, start_date: str, end_date: str):
    """Job function — importable by rq from this module path."""
    from api.analyze import run_analysis

    return run_analysis(analysis_type, bbox, start_date, end_date)


def job_run_simulation(bbox: list, start_date: str, params: dict | None = None):
    """
    Job function for a forward flood simulation — importable by rq from this
    module path. Kept separate from `job_run_analysis` because a simulation
    needs its parameter dict and returns a much larger payload.
    """
    from api.analyze import run_analysis

    return run_analysis(
        analysis_type="flood_simulation",
        bbox=bbox,
        start_date=start_date,
        end_date=start_date,
        params=params or {},
    )


def main():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT not set in .env")
    ee.Initialize(project=project)
    print(f"Worker: GEE initialized for {project}")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    conn = Redis.from_url(redis_url)
    worker = Worker([Queue("kairos", connection=conn)], connection=conn)
    print("Worker: listening on queue 'kairos'")
    worker.work()


if __name__ == "__main__":
    main()
